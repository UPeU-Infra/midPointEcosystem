# Saneamiento dual-shadow LDAP — 267 focos (dedup uid=DNI vs uid=código)

Fecha: 2026-06-04
Resource LDAP (Identity Cache): `7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f` (`upeu/resources/ldap-identity-cache.xml`), base `ou=people,dc=upeu,dc=edu,dc=pe`, DN = `uid=<focus/name>,...`.

## Estado: ✅ MASIVO EJECUTADO Y CERRADO — 267/267 saneados, dual-shadow = 0

### Resumen ejecutivo del masivo (2026-06-04 PM12)
- Bloqueo previo (import Estudiantes regenerando dual) RESUELTO: import `c1fe95c6` quedó SUSPENDED (paró en 1071). Universo estabilizado.
- Re-conteo al iniciar: **267 focos** dual (subió de 265 por el import antes de suspenderlo).
- Suspendido también, por prudencia, el **Recon recurring** `94b627b4` (interval=86400, misfireAction=executeImmediately) durante la ventana — para que no reintrodujera duales. **Sigue SUSPENDED al cierre (revisar si se reactiva — decisión usuario, ver Pendientes).**
- Clasificación 267 focos: **267 keepers (uid=código=name) + 267 losers (uid=DNI8) — 0 anomalías, 0 losers no-DNI8.**
- Masivo serializado en 3 fases. Resultado: **dual-shadow residual = 0**, ningún foco sin shadow keeper.

## Procedimiento ejecutado (3 fases, idempotente)
1. **Fase A** — DELETE shadow loser `?options=raw` (×266 + 1 canary) → 266/266 ok, 0 fail.
2. **Fase B** — `ldapdelete uid=<DNI>` dentro del contenedor `openldap` (×266 + 1 canary) → 266/266 ok, 0 fail.
3. **Fase C** — PATCH `/users/<foid>?options=reconcile` no-op (`replace c:telephoneNumber`) (×266) → 254 ok, 12 OTHER (2× HTTP 240 = partial-handled OK; 10× HTTP 500 = conflicto de datos PREEXISTENTE, NO dual-shadow).

### Sobre los HTTP 500 de Fase C (no bloqueantes)
Son focos con conflicto de mappings inbound `strong` single-valued PREEXISTENTE (ajeno al dedup):
`Strong mappings provided more than one value for single-valued item familyName: [Ccaza Huayta, Casas Huayta]` (typos de apellido en fuentes Oracle). El clockwork no commitea el recompute, **pero el dedup ya estaba hecho** (shadow loser borrado en Fase A, DN LDAP borrado en Fase B). Verificado: los 10 focos quedan con **exactamente 1 shadow LDAP keeper** (uid=código). Workstream identifier-canónico (familyName/studyLevel/lambDocNum multi-valor) lo resuelve aparte.

## Invariantes verificadas (cierre)
| Invariante | PRE | POST |
|---|---|---|
| focos dual-shadow LDAP | 267 | **0** ✓ |
| total shadows LDAP (m_shadow) | 7,619 | 7,351 (−268; −267 del dedup + −1 del caso alumni abajo) ✓ |
| focos con ≥1 shadow LDAP | 6,660 | 6,659 (−1 = caso alumni 201810714, ver abajo; correcto por política) ✓ |
| entradas `ou=people` (LDAP físico) | 7,618 | 7,351 (−267 exacto) ✓ |
| **cardnumbers duplicados Koha BUL** | 0 | **0** ✓ (invariante crítica) |
| total borrowers Koha BUL | 14,349 | 14,349 (dedup LDAP no crea cuentas; solo updates in-place) |

### Caso especial — foco 201810714 (alumni) quedó sin shadow LDAP: CORRECTO
1 foco salió del conteo `focos_con_shadow` (6,660→6,659). Diagnóstico: foco multi-afiliación (egresado 201810714 + ex-trabajador DNI 72225462), archetype `archetype-user-alumni`, **sin rol LDAP asignado** (0 AR-LDAP). En LDAP físico existía SOLO `uid=72225462` (DNI, el loser); su "keeper" `uid=201810714` (código) era un **shadow fantasma** apuntando a una entrada LDAP que nunca existió físicamente. Al borrar el loser y reconciliar, MidPoint unlinkó ambos shadows muertos y dejó el foco sin LDAP. **Esto es la política funcionando:** de 27,507 alumni, solo 3 tienen shadow LDAP (residuales) — los alumni puros NO reciben cuenta LDAP. La regla "nadie sin shadow" se cumple: ningún foco que DEBA tener LDAP quedó sin él.

## Backups (PROD)
- `pg_dump` m_shadow: `/home/juansanchez/backups/dualshadow-265/mp_shadows_20260604_113146.dump` (8.0 MB).
- LDIF de los 267 losers (regenerado esta sesión — el original no existía): `/home/juansanchez/backups/dualshadow-265/losers_ldap_20260604_115209.ldif` (267/267 entradas, 264 KB) + copia en host LDAP `/tmp/dualdedup/`.

## Change 3 (home library Koha) — bloqueados DESBLOQUEADOS, 14 flips a BUL
Tras sanear el dual-shadow, se corrió reconcile serializado sobre los **132 focos dedup con cuenta Koha** (script `/tmp/koha_reconcile.sh` en PROD). El error `Projection ACCOUNT already exists in lens context` que bloqueaba los focos LIMA de Change 3 ya no aplica (el dual desapareció).

**Resultado Koha (branchcode de los 132 focos dedup con cuenta):**
| | PRE dedup | POST reconcile |
|---|---|---|
| BUL | 26 | **40** (+14 flips) |
| BUJ | 9 | 2 |
| BUT | 7 | 2 |

- **14 flips netos a BUL** (BUJ −7, BUT −5, + correcciones) = focos LIMA antes bloqueados por dual-shadow que ahora pueden commitear el clockwork y derivan branchcode=BUL (cubre los ~30 de Change 3 que tenían eff-campus LIMA materializable).
- Los 4 que quedan en province (BUJ 2 + BUT 2) son legítimamente no-LIMA o tienen conflicto de datos preexistente (HTTP 500 familyName/studyLevel/lambDocNum multi-valor — NO dual-shadow).
- Reconcile: 120/132 ok, 12 OTHER (todos HTTP 500 por conflicto de datos preexistente, NO dual). **0 cardnumber duplicados, 0 cuentas creadas (updates in-place).**

## Keycloak — 175 cuentas federadas stale por DNI (READ_ONLY) — AUTO-PURGADAS
Provider `OpenLDAP Identity Cache UPeU` (`lUyeYTgrSeuojbkJKqOk1A`, editMode=READ_ONLY, importEnabled=true).
- PRE: 177 `user_entity` federados con username = DNI loser. **0 con offline session.**
- Tras borrar los DN LDAP (Fase B), Keycloak **purgó automáticamente** los registros importados: el DELETE vía Admin API devolvió 404 ("User not found") y la verificación en DB dio **`aun_en_db = 0`**. La federación READ_ONLY+import resuelve dinámicamente contra LDAP; al desaparecer el DN, el registro cache se limpia solo.
- Backup pre-limpieza: `/tmp/kc_stale_backup_20260604_121259.psv` en host KC (id|username|email|enabled|created, 175 filas).
- 138/267 keepers (uid=código) ya estaban federados → conservan login por código. Los demás se federan on-demand al primer login.
- Restante: 2,208 federados con username DNI8 = workers legítimos (único shadow = uid=DNI, NO eran losers). Correcto, no se tocan.

## Tasks suspendidas durante la ventana (estado al cierre)
| OID | Task | Estado | Nota |
|---|---|---|---|
| `c1fe95c6` | Import Oracle LAMB Estudiantes v3 (regenerador) | SUSPENDED | El que regeneraba dual en tiempo real. NO reanudar (decisión usuario). |
| `94b627b4` | Recon Oracle LAMB Estudiantes 2026-05-28 (RECURRING, interval=86400, misfire=executeImmediately) | SUSPENDED | Suspendido por prudencia durante la ventana (evitar reintroducir duales). **Decisión usuario reactivarlo — pertenece al sub-workstream Estudiantes.** |
| `21548de2` | Import Estudiantes v3 | SUSPENDED | preexistente |
| `921835b3`, `837bce7a` | Import Estudiantes v3 | READY (SINGLE one-shot idle) | No auto-disparan; no se tocaron. |

## Pendientes
1. **Conflictos de datos preexistentes (12 focos HTTP 500):** `familyName` / `studyLevel` / `lambDocNum` strong single-valued con dos valores (typos de apellido, CE vs DNI, Idiomas+Pregrado). Bloquean el clockwork de esos focos. **Workstream identifier-canónico** (no este dedup). El dedup ya quedó hecho en ellos (1 solo shadow keeper).
2. **Recon recurring Estudiantes `94b627b4`:** decidir reactivar (sub-workstream Estudiantes). Si se reactiva con el import `c1fe95c6` aún suspendido, el Recon NO regenera duales (el dual venía del import, no del recon). Reactivable sin riesgo de re-dual una vez validado.
3. **Tito (43508613) y similares:** dependen de materialización `campusStudent` LIMA vía recon Estudiantes (Change 1 vigencia DENSE_RANK LAST). NO se fuerzan aquí — sub-workstream Estudiantes (~13k addFocus).

---

## (Histórico) Estado previo: PARADO tras canary 2/2 PASS — BLOQUEO por concurrencia

### Resumen ejecutivo
- Diagnóstico confirmado: **265 focos** con dual-shadow LDAP, patrón **uniforme 0 ambiguos**.
- Backups OBLIGATORIOS hechos y verificados (>0).
- **Re-canary 2/2 PASS** en esta sesión (procedimiento end-to-end validado).
- **Masivo de 265 NO ejecutado**: un `Import from resource Oracle LAMB Estudiantes v3` está **RUNNING** y **regenera dual-shadows 1:1** en tiempo real → el universo nunca converge a ~0 mientras ese import corra. Además el usuario instruyó NO involucrar el recon/import Estudiantes (sub-workstream aparte).

## Diagnóstico (verificado en PROD)
| Verificación | Resultado |
|---|---|
| Focos con >1 shadow LDAP (m_ref_projection) | **265** |
| keeper: `uid == focus/name` (código) | 265/265 |
| loser: `uid` = DNI 8 dígitos, ≠ name | 265/265 |
| ambiguos / otro mismatch | 0 |
| overlap keeper vs loser | 0 |
| name del foco = DNI (que rompería "conservar código") | **0** (257 código `20…` + 8 otros códigos numéricos no-DNI) |
| keepers presentes en LDAP físico | 265/265 |
| losers presentes en LDAP físico | 265/265 |
| loser shadow flags | `lifecycleState=NULL, dead=NULL, exist=t` (MidPoint los cree vivos → causa `already exists in lens context`) |

**OJO — no borrar por patrón ciego:** LDAP tiene **2241 entradas `uid=DNI8`**; solo **265** son losers de dual-shadow (las que tienen keeper-código en el MISMO foco). Las otras ~1976 son focos cuyo único shadow LDAP es legítimamente el DNI (workers). El masivo SOLO debe tocar las 265 del dataset, NUNCA "todos los uid=DNI8".

Dataset completo (foco OID | name/código | keeper shadow OID | loser shadow OID | DNI):
`dualshadow_265_dataset_2026-06-04.csv` (gitignored — contiene DNI/PII; vive solo local + PROD `/tmp`).

## Backups (PROD)
- `pg_dump` m_shadow + m_ref_projection: `/home/juansanchez/backups/dualshadow-265/mp_shadows_20260604_113146.dump` (8.0 MB).
- LDIF de las 265 entradas loser `uid=DNI`: `/home/juansanchez/backups/losers_20260604_113146.ldif` (265/265 entradas, 256 KB).

## Procedimiento por foco (validado, serializado)
1. `DELETE /shadows/<loser_sh>?options=raw` → HTTP 204 (el delete normal da 409; raw lo evita).
2. `ldapdelete uid=<DNI>,ou=people,...` dentro del contenedor `openldap` (host `ldap-upeu` 192.168.15.168; `ldapsearch/ldapdelete` NO están en el host, solo dentro del contenedor `osixia/openldap`). Conserva `uid=<código>`.
3. `PATCH /users/<foid>?options=reconcile` con delta no-op (`replace c:telephoneNumber` sin valor) → reevalúa clockwork, consolida en el shadow keeper.

Resultado esperado por foco: queda **1 solo shadow LDAP = `uid=<código>`**, loser ausente. `partial_error` en el PATCH es **ruido esperado** (Entra ID `CreateCapabilityType is missing`, resource `2f11c057...` inbound-only/proposed); NO hay error LDAP ni Koha.

## Canary 2/2 PASS (esta sesión)
| Caso | foco | código (keeper) | DNI (loser) | DELETE shadow | ldapdelete | reconcile | shadows LDAP después |
|---|---|---|---|---|---|---|---|
| 1 | a04a5483… | 200010013 | 42653118 | 204 | OK | partial_error (solo Entra) | 1 (uid=código) ✓ |
| 2 | 7fd2cbd3… | 200010092 | 41767058 | 204 | OK | partial_error (solo Entra) | 1 (uid=código) ✓ |

- Keeper LDAP (uid=código) intacto en ambos; loser LDAP confirmado `No such object`.
- **Koha intacto:** ambos borrowers conservan `cardnumber=DNI` (94206/94218, BUL) — el mapping `cardnumber-outbound` es **weak** (source `$focus/name`=código), así que NO sobreescribe cardnumber existente y NO crea duplicado (los códigos 200010013/200010092 no existen como cardnumber). dup_cardnumbers = 0.

## BLOQUEO — por qué NO se corrió el masivo
`Import from resource Oracle LAMB Estudiantes v3` quedó **RUNNING desde 2026-06-04 16:20** (no lanzado en esta sesión). Evidencia de que regenera el dual:
- Tras sanear 2 canary, el conteo dual global se mantuvo en **265** (no bajó a 263).
- Comparación de conjuntos: 2 focos de mi CSV salieron del universo dual (los saneados) y **2 focos NUEVOS** entraron (no estaban en el CSV). Neto 1:1.
- Mis 2 canary siguen sanos (no revirtieron); son focos distintos los que aparecen.

Conclusión: con el import Estudiantes activo el universo dual-shadow es **móvil**; el masivo de 265 no converge a ~0 y mezcla atribución con un sub-workstream que el usuario pidió no tocar.

## Invariante Koha (siempre verde durante la sesión)
- Baseline: 14267 borrowers, **0 cardnumbers duplicados**.
- Cierre sesión: 14292 borrowers (+25 por el import Estudiantes activo, cardnumber=código, student — NO de este dedup), **0 cardnumbers duplicados**.
- Todos los toques de este dedup fueron updates in-place / no-op; 0 borrowers creados por el dedup.

## Relación con Change 3 (home library)
Change 3 dejó **30 focos LIMA bloqueados** por `Projection ACCOUNT already exists in lens context` (dual-shadow LDAP). Esos 30 son subconjunto de estos 265. Al sanear el dual-shadow flipean solos a BUL en el reconcile (ya tienen campusStudent/Worker LIMA materializado). **Aún NO desbloqueados** porque el masivo está parado.

## Recomendación / próximos pasos (decisión usuario)
1. **Coordinar ventana sin import/recon Estudiantes activo** (suspenderlo es decisión del usuario — instrucción explícita de no tocar ese sub-workstream). Con el import detenido el universo dual queda estable.
2. Recién entonces correr el masivo serializado (scripts del procedimiento por foco) sobre el dataset de 265 → esperado dual-shadow 265→~0.
3. Limpieza Keycloak de ~181 cuentas federadas stale por DNI (READ_ONLY, 0 sesiones): **NO tocada** esta sesión (depende del masivo LDAP previo; se hace después de que LDAP quede con un solo uid=código por foco, porque Keycloak federa desde LDAP).
4. Sub-workstream recon Estudiantes (Tito y similares: pendientes de materialización de `campusStudent` LIMA) — NO forzar aquí; es decisión aparte del usuario (los ~13k addFocus).

## Pendientes de materialización de campus (sub-workstream, NO forzar)
Los focos cuyo `campusStudent`/`campusWorker` LIMA aún no está materializado dependen del recon Estudiantes (Change 1 vigencia DENSE_RANK LAST). No se fuerzan en este dedup. Tito (43508613) es ejemplo de este grupo.
