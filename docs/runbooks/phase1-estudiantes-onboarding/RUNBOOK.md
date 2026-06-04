# FASE 1 — Onboarding controlado feed Estudiantes (canary + diagnóstico)

**Fecha:** 2026-06-04
**Operador:** midpoint-expert (Claude Code)
**Objetivo global:** convergencia categorías Koha — vincular ~3k borrowers huérfanos + onboardear matriculados sin cuenta → 6 categorías canónicas.
**Esta fase:** canary del pipeline + diagnóstico del universo + identificación del bloqueante de throughput.

---

## 0. Backup

- `pg_dump -Fc` MidPoint: `/home/juansanchez/backups/bkp_phase1_estudiantes_20260604_130628.dump` (521 MB en host, 508 MB en contenedor). Verificado >0.
- Tag git existente pre-orphan: `pre-orphan-cleanup-2026-06-03`.
- **NO** se tomó snapshot dump de Koha (operación no destructiva; el storm fue rechazado por 409 sin mutar Koha).

---

## 1. Snapshot pre-estado (baseline)

| Métrica | Valor |
|---|---|
| m_user total | 49,481 (active 41,222 / archived 7,290 / draft 700 / null 267 / proposed 2) |
| Shadows Estudiantes (`6a91f7e1…0e22`) | 11,266 (11,259 linkeados) |
| Shadows Koha (`9b5a7c81…35af`) | 11,313 |
| Dual-shadow Estudiantes | 0 |
| Koha borrowers total | 13,919 → 14,349 (los +430 son del run previo c1fe95c6, NO de esta sesión) |
| Koha categorías legacy | ESTUDI 3395, ADMINIST 90, VISITA 73, DOCEN 29, ALUMNI 2, POSGRADO 1, JUBILADO 1 |
| Koha categorías canónicas | student 5544, alum 2682, staff 1418, faculty 1104 |

---

## 2. Diagnóstico del universo (feed sem 267/279/283)

Feed = **24,676 códigos distintos** (≈ estimación 24,673). Cruce por `lambDocNum` normalizado (DNI zfill8 / >8 tal cual) contra MidPoint:

| Caso | N |
|---|---|
| addFocus nuevo (doc ausente en MidPoint) | **12,990** |
| Link a foco existente (doc presente) | **11,679** |
| — de ellos con foco activo | 11,374 |
| — de ellos sin foco activo (reactivación) | 305 |
| **Doc → múltiples focos (ambigüedad correlación)** | **3** |
| Feed con NUM_DOCUMENTO nulo | 7 |

### Cruce orphans Koha legacy (ESTUDI) ↔ feed
De 3,395 ESTUDI: **3,068 matchean feed por `cardnumber==código`** (gobernables Fase 1), 14 por DNI-as-card, 313 sin match (fuera de horizonte).

### Riesgo storm 409 (clave)
Cruce feed (24,676) ↔ borrowers Koha sin shadow:

| Resultado | N |
|---|---|
| Sin borrower Koha → create limpio | **16,070** |
| Borrower + shadow → relink seguro | 966 |
| **Borrower SIN shadow → riesgo 409-storm** | **7,640** |

Desglose de los 7,640 por categoría legacy: **student 4,486** (¡creados por runs previos pero shadow no persistido!), ESTUDI 3,024, alum 79, staff 29, faculty 17, DOCEN 4, POSGRADO 1.

---

## 3. CANARY — GATE: **PASS**

No fue posible aislar por-código (el ScriptedSQL connector solo soporta `EqualsFilter` sobre `__NAME__`; las queries de import-from-resource con filtro de atributo NO se empujan al connector en 4.10 → error "Resource not defined in a search query"). Se validó el pipeline sobre los objetos ya materializados por el run previo c1fe95c6 + 4 tocados en la ventana canary.

Evidencia (450 borrowers nuevos `borrowernumber>97500`, todos `student`, `cardnumber==código`):

- **0 cardnumber duplicado** en los 14,349 borrowers (invariante ✓).
- Home library correcto: 422 BUL / 19 BUJ / 9 BUT (deriva de `campusStudent`).
- **Critsi (202613369):** `student`, branchcode=**BUL** ✓ — la agregación vigencia-aware impidió que la CEPRE Juliaca vencida contaminara la home library.
- **Tito (200810869 / DNI 43508613):** `faculty`, BUL ✓ — prioridad faculty>student preservada; campusStudent=LIMA materializado.
- MidPoint: dual-shadow Estudiantes = 0; lambDocNum dups = 24 (pre-existentes legacy, no nuevos); m_user sin cambio.

**Conclusión canary:** el pipeline inbound→correlación(lambDocNum)→archetype→categorycode→home-library es CORRECTO. No fusiona personas. No duplica cardnumber.

---

## 4. BLOQUEANTE Fase 1 — storm 409 + violación unique-constraint de shadow

Al reanudar el import completo, el worker quedó atascado en una **tormenta de reintentos** sobre orphans Koha:

```
AbstractKohaService: POST /api/v1/patrons → 409 Conflict
  "A patron record matching these details already exists"
RepoCommonUtils (recuperable): Couldn't add shadow object to the repository.
  duplicate key value violates unique constraint
  m_shadow_9b5a7c81…_primaryidentifiervalue_objectclassid_resourcereftargetoid_idx2
  Key (primaryidentifiervalue, objectclassid, resourcereftargetoid)=(69871, 10, 9b5a7c81…)
```

**Mecanismo:** borrower huérfano en Koha (existe, sin shadow MidPoint) → existence mapping decide `create` → Koha responde 409 → el fallback v1.3.8 intenta GET+link → MidPoint intenta persistir el shadow → choca unique-constraint en repo (ya existe shadow con ese `primaryidentifiervalue`) → marca "recuperable" → **reintenta en bucle tight (varias veces/seg)**, martillando la Koha API y bloqueando el avance del import.

- Suspendido de inmediato (`/suspend`); storm detenido (0 llamadas Koha post-suspend, CPU→0.24%).
- **Daño: ninguno.** Los 409 fueron RECHAZADOS por Koha → 0 borrowers basura creados por el storm. m_user, koha_shadows y Koha total sin crecimiento descontrolado. Los 4 borrowers de la ventana canary son canónicos y correctos.

**Por qué importa:** los 7,640 orphans dispararán este storm uno a uno → el mass import NO termina y hostiga la Koha API. Los **4,486 orphans ya en categoría `student`** revelan que runs previos crearon el borrower canónico pero **el shadow nunca se persistió** (mismo choque de constraint) → cada run reincide.

---

## 5. Estado final (limpio)

| Invariante | Valor |
|---|---|
| running_tasks | 0 |
| m_user | 49,481 (= backup) |
| est_shadows | 11,267 (+1 shadow de discovery, inocuo) |
| koha_shadows | 11,313 (sin cambio → confirma que el shadow no se persiste en el storm) |
| dual-shadow Estudiantes | 0 |
| lambDocNum dups | 24 (pre-existentes) |
| Koha total | 14,349 (estable) |
| cardnumber duplicados Koha | 0 |
| Task `phase1-canary-import-estudiantes` | SUSPENDED (OID en `/tmp/canary_import_oid.txt` del operador) |

---

## 6. Resultado Fase 1 (resumen para el usuario)

- **Gobernables identificados:** 3,068 ESTUDI (+14 DNI-as-card) + 4,486 student-orphan → convergen a categoría canónica al linkear su shadow.
- **Onboarding limpio disponible:** 16,070 matriculados sin borrower Koha (create directo, sin storm) + 966 relink seguro.
- **Huérfanos que quedan / bloqueo:** 7,640 borrowers sin shadow disparan el storm 409+constraint; 313 ESTUDI fuera de horizonte (no gobernables por este feed).
- **NO se borró ninguna categoría legacy** (es fase posterior).

---

## 7. Qué bloquea y plan Fase 2 (recomendado)

El mass import NO debe correrse tal cual: storm-and-hang en cada uno de los 7,640 orphans.

**Camino canónico (orden):**
1. **Linkear primero los 7,640 orphans** (vincular shadow al borrower existente) ANTES de onboardear, vía recon **on-resource** acotada por Koha (Gap B ya tiene `focus_oid` por orphan en `koha-gapB-orphan-link/`) o batch de `importShadowFromResource` por borrower OID. Esto persiste el shadow y elimina el `create→409`.
2. **Diagnosticar la violación de unique-constraint** (`primaryidentifiervalue` colisiona aunque el shadow no exista): posible shadow "muerto"/dead o índice con `primaryidentifiervalue` reusado. Limpiar shadows colgados antes de relink (ver `shadow-cleanup-koha-*`).
3. Recién con shadows linkeados, correr el **create-only** para los 16,070 sin borrower (existence=create no chocará).
4. Resolver los 3 doc→multi-foco (merge de identidad duplicada `name==DNI` archived vs canónico activo) — dedup aparte, no bloquea.
5. Vaciar y borrar categorías legacy (fase posterior).

**Mejora durable de connector/resource (SciBack):** el fallback 409 debe (a) hacer el shadow `link` idempotente sin re-insertar (manejar el unique-constraint como "ya existe → adoptar"), y (b) cortar el bucle de reintentos recuperables tras 1 intento de link. Hoy v1.3.8 reintenta indefinidamente.
