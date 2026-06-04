# FASE 2 — Link de borrowers Koha huérfanos a su foco MidPoint

**Fecha:** 2026-06-04
**Operador:** midpoint-expert (Claude Code)
**Objetivo global:** convergencia de categorías Koha legacy (ESTUDI/DOCEN/…) → canónicas (student/faculty/staff/alum) gobernadas por MidPoint.
**Esta fase:** resolver la causa raíz del storm 409/unique-constraint, linkear los huérfanos genuinamente gobernables, y dejar el camino limpio para Fase 3.

---

## 0. Backups

- `pg_dump -Fc` MidPoint: `/home/juansanchez/backups/bkp_phase2_pre_link_20260604_140001.dump` (6.0 GB — dominado por `ma_audit_delta_default` 5.6 GB).
- `pg_dump` previo Fase 1 (válido como punto de restauración del día): `/home/juansanchez/backups/bkp_phase1_estudiantes_20260604_130628.dump` (545 MB, 13:10).
- Tag git: `phase2-pre-orphan-link-2026-06-04`.
- Koha: operaciones no destructivas salvo 1 restore documentado (§4); `deletedborrowers` de Koha actuó como red de seguridad.

**INCIDENTE DE DISCO (resuelto):** el `docker cp` del dump de 6 GB al contenedor + copia de verificación llenó el disco a 100 %. Removidas las copias stray del overlay del contenedor (`/var/lib/docker/rootfs/overlayfs/<id>/tmp/`). Disco recuperado a 88 % (8.2 G libres). Postgres y MidPoint sobrevivieron sin corrupción (49,481 users intactos, containers healthy). **Lección: NUNCA `docker cp` un dump grande de vuelta al contenedor para verificar; usar `pg_restore --list` sobre el archivo del host o un contenedor efímero.**

---

## 1. Diagnóstico — causa raíz del storm (CONFIRMADA)

Recurso Koha OID `9b5a7c81-47aa-42ac-9a08-4de8b64935af`. Account: `__UID__`=`patron_id` (=borrowernumber=`primaryidentifiervalue`), naming=`userid`.

Estado de partida (cruce 14,349 borrowers ↔ 11,313 shadows Koha):

| Clase | N | Significado |
|---|---|---|
| owned_shadow | 10,744 | borrower con shadow + owner → ya linkeado |
| **orphan_shadow** | **538** | shadow LIVE con piv correcto pero **sin owner** → colisiona al linkear |
| **no_shadow** | **3,067** | borrower sin ningún shadow → dispara `create→409` |
| dangling (dead) | 2 | shadows muertos piv=85803/86155 (inocuos) |

**Mecanismo del storm (verificado con piv 69871):** un onboarding focus-driven evalúa el existence mapping → `eligible || existing!=null`. Para un foco eligible **sin** shadow linkeado, `existing=null` → existence=true → MidPoint intenta **create** → Koha responde **409 (patron already exists)** → fallback link → MidPoint intenta persistir un shadow nuevo con el `primaryidentifiervalue` del borrower → **choca el unique-constraint** porque ya existe un **orphan_shadow** con ese piv → marca recuperable → **reintenta en bucle**.

→ La cura es **linkear (adoptar) el shadow existente** o **descubrirlo vía recon**, NUNCA crear.

---

## 2. CORRECCIÓN DE ALCANCE (hallazgo mayor)

La premisa heredada "7,640 huérfanos a linkear" estaba **inflada**. Al correlacionar con las 3 capas del recurso (cardnumber=`name`, cardnumber-as-DNI=`lambDocNum`, DNI-extended=`lambDocNum`):

| Clase real (de 14,349) | N |
|---|---|
| Ya linkeados (owned) | 10,744 |
| **LINKABLE** (foco existe, 1:1, sin conflicto) | **196** |
| — orphan-shadow (import por OID) | 38 |
| — no-shadow (recon por patron_id) | 158 |
| DUAL-RISK (foco ya posee otro shadow Koha) — diferir | 60 |
| **NO-FOCUS** (sin identidad MidPoint → onboarding primero) | **3,301** (3,245 ESTUDI) |
| Cuentas de servicio (CR41$, AUTOPBUL1, ADMIN*UPEU$…) — dejar | 48 |

**Conclusión clave:** los ~3,245 ESTUDI legacy mayoritarios pertenecen a **personas que NO tienen foco en MidPoint** (cohortes antiguas fuera del feed vigente). NO se pueden linkear; convergen solo cuando su identidad se onboardea (Fase 3). El "vaciado de ESTUDI" por link es modesto: solo gobierna los que ya tienen foco.

### Sub-segmentación de los 196 LINKABLE por elegibilidad Koha-Lima

El gate Koha (tarea #65) exige **afiliación viva (worker|student) en campus LIMA**. Linkear un foco **no-elegible** dispara el existence gate → **DELETE del borrower** (ver §4).

| Segmento | N | Acción |
|---|---|---|
| **ELIGIBLE** (live worker/student + Lima) | 88 | seguro de linkear |
| — archetyped + active (convergencia inmediata) | **32** | ← masivo Fase 2 |
| — limbo (NULL lifecycle / sin archetype) | 56 | linkear OK, pero categoría NO converge hasta bootstrap de archetype |
| **INELIGIBLE** (sin live aff, o live aff no-Lima) | 107 | **EXCLUIR** — linkear borraría su borrower |

---

## 3. CANARY — GATE: **PASS** (3 escenarios)

1. **Orphan-shadow limbo** (borrower 383, card 42689980, focus 200210468): `importShadowFromResource` por OID → shadow 0→1 owner, LINKED 1:1, 0 dual. (Categoría no flipó: foco en limbo sin archetype → primaryAffiliation no materializa.)
2. **Orphan-shadow archetyped** (borrower 11728, card 201810054 código, focus active staff): import por OID + reconcile (PATCH `?options=reconcile`) → **ESTUDI → staff**, BUL, 1 shadow, 0 dual. **Convergencia end-to-end OK.**
3. **No-shadow eligible** (borrower 1944, card 45788343, focus active student LIMA): recon on-resource scoped por `attributes/ri:patron_id` → shadow creado + LINKED, **branchcode BUJ→BUL** (sigue campusStudent), categoría student, **0 create-409, 0 delete**. Conteo Koha estable.

**Mecanismos validados:**
- orphan-shadow → `POST /shadows/{oid}/import` (resuelve por OID, adopta sin crear).
- no-shadow eligible → recon `<reconciliation>` scoped por `attributes/ri:patron_id` (= `__UID__`; el KohaConnector SÍ honra EqualsFilter sobre `__UID__`, a diferencia de `cardnumber`).
- categoría canónica → PATCH `?options=reconcile` (no-op description) sobre el foco eligible+archetyped (existence=true → PATCH borrower, NO create).

---

## 4. HALLAZGO CRÍTICO — recon-link sobre foco INELIGIBLE borra el borrower

Canary sobre borrower **22422** (card 73977362, focus 25f3f69f **archived**, liveWorker=∅ liveStudent=∅ campus=∅): el recon creó+linkeó el shadow, luego el clockwork del foco evaluó el existence gate → `eligible=false` y el guard `existing!=null` **NO protegió** (durante el mismo clockwork el shadow recién linkeado no se resuelve aún) → **existence=false → DELETE del borrower en Koha** (no disable).

- **Daño: reversible y revertido.** Borrower tenía 0 préstamos/historial. Restaurado desde `deletedborrowers` (INSERT…SELECT + DELETE). Conteo Koha 14,348→14,349. Shadow rollback automático (0 huérfano).
- **Consecuencia de diseño:** el masivo DEBE excluir foci no-elegibles. El gate "suma-nunca-resta" del recurso NO es suficiente protección bajo recon que crea-y-linkea en el mismo clockwork.
- **Recomendación durable (koha-expert):** endurecer el existence mapping para que un foco con shadow recién descubierto en recon nunca caiga a `false` (p.ej. consultar `midpoint.searchObjects` shadows por piv, no solo `getLinkedShadow`), o gobernar el deprovisioning de no-elegibles SOLO vía `administrativeStatus=disabled` (nunca existence=false→delete).

---

## 5. MASIVO ejecutado (set READY = 32 eligible+archetyped)

| Sub-set | N | Mecanismo | Resultado |
|---|---|---|---|
| orphan-shadow | 12 | `POST /shadows/{oid}/import` + reconcile | 12/12 linkeados + categoría canónica |
| no-shadow | 20 | recon por `patron_id` | **10/20** linkeados (los 10 restantes ya tenían categoría `student` correcta; el recon por patron_id no materializó shadow para ellos — limitación del connector, residual benigno) |

**12 orphan borrowers — categoría DESPUÉS:** 11728→staff, 25515→staff, 25634→faculty, 27293→faculty, 27723→staff, 27741→faculty, 28695→faculty, 28714→faculty, 29077→faculty, 29315→faculty, 30017→faculty, 30957→staff. Todos BUL, cardnumber=código preservado.

---

## 6. Estado final — ANTES / DESPUÉS

### Koha categorías

| categorycode | ANTES | DESPUÉS | Δ |
|---|---|---|---|
| student | 5,544 | 5,544 | 0 |
| **ESTUDI** | **3,395** | **3,386** | **−9** |
| alum | 2,682 | 2,682 | 0 |
| staff | 1,418 | 1,423 | +5 |
| faculty | 1,104 | 1,114 | +10 |
| **DOCEN** | **29** | **23** | **−6** |
| (resto legacy/sistema) | igual | igual | 0 |
| **TOTAL** | **14,349** | **14,349** | **0** |

15 borrowers legacy (9 ESTUDI + 6 DOCEN) convergieron a staff/faculty. **0 cardnumber duplicado.**

### MidPoint invariantes

| Invariante | ANTES | DESPUÉS |
|---|---|---|
| koha_shadows_total | 11,313 | 11,315 |
| koha_shadows_owned | 10,744 | 10,789 (+45) |
| koha_shadows_orphan (live) | 538 | 525 |
| **piv (cardnumber) dups** | 0 | **0** |
| **dual_owner_koha** (foco con 2 shadows Koha) | 0 | **0** |
| **m_user_total** | 49,481 | **49,481** |

**0 fusión de personas, 0 duplicado de cardnumber, 0 dual-projection, 0 cambio de m_user.**

---

## 7. Estado limpio

- Todas las tareas `GapB%` canary/batch **eliminadas**.
- Imports Estudiantes (`921835b3`, `837bce7a`) forzados a **SUSPENDED** en DB (no se reanudan).
- Recons (`94b627b4`, `09406c57`, `e8d054ba`) SUSPENDED.
- Containers healthy, disco 88 %.
- Recurso Koha íntegro (no se tocó el XML).

---

## 8. Qué queda para Fase 3

1. **Onboarding create-only de ~16,070 matriculados sin borrower** (focos con identidad, sin cuenta Koha) — `existence=create` NO chocará (no hay orphan-shadow que colisione tras Fase 2). Requiere reanudar el feed Estudiantes con el storm ya neutralizado para los gobernables.
2. **3,245 ESTUDI no-focus** → solo convergen tras onboardear su identidad (egresados/estudiantes pipeline). NO son linkeables hoy.
3. **56 eligible-limbo** → bootstrap de archetype (task `iterativeScripting assign` por afiliación) para que su categoría converja al linkear.
4. **60 DUAL-RISK** = misma persona con 2 borrowers Koha (uno card=código canónico + uno card=DNI legacy). Resolución = **merge de borrowers en Koha** (koha-expert), NO link (link daría dual-projection FATAL). Conservar card=código.
5. **10 no-shadow residuales** (28656,28706,28785,28950,29268,29312,29389,29390,29394,31408) ya tienen categoría `student` correcta; falta solo el shadow link. Reintentar con mecanismo de recon más robusto o `importShadowFromResource` tras un discovery previo.
6. **Mejora durable connector/existence** (§4): idempotencia del fallback 409 + protección anti-delete en recon de no-elegibles. Documentado para koha-expert; NO recompilar aquí.
7. **Vaciar/borrar categorías legacy** ya vacías — fase posterior (NO en Fase 2/3 hasta que ESTUDI/DOCEN bajen a ~0 gobernables).

---

## 9. Correlación canónica (recordatorio, `DECISION-canonical-identifier.md`)

- Correlación de entrada: 3 capas (`cardnumber==name`, `cardnumber-as-DNI==lambDocNum`, `DNI-extended==lambDocNum`). Sentinels `__NO_MATCH__` protegen cuentas de servicio.
- `cardnumber == name` (código institucional) es la llave canónica de salida; DNI es atributo secundario.
- NUNCA fusionar personas: el link solo adopta el shadow del MISMO borrower correlacionado 1:1.
