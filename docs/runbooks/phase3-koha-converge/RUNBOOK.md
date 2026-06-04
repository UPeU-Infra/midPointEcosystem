# FASE 3 — Convergencia categorías Koha legacy gobernables (anti-storm)

**Fecha:** 2026-06-04
**Operador:** midpoint-expert (Claude Code)
**Objetivo global:** convergencia categorías Koha legacy (ESTUDI/ADMINIST/VISITA/DOCEN/…) → canónicas eduPerson (student/faculty/staff/alum) gobernadas por MidPoint.
**Esta fase:** gobernar los borrowers legacy que SÍ son gobernables hoy (foco vivo + elegible) usando mecanismos que NO disparan el storm 409. Caracterizar el resto para Fase 4 / koha-expert / onboarding feed.

---

## 0. Backups

- Tag git: `phase3-pre-converge-2026-06-04` (pushed).
- Koha: `mysqldump borrowers` → `/tmp/koha_borrowers_phase3_20260604_154104.sql` (7.8 MB, host mariadb 192.168.12.130).
- MidPoint pg_dump válido del día (Fase 1): `/home/juansanchez/backups/bkp_phase1_estudiantes_20260604_130628.dump` + Fase 2 `bkp_phase2_pre_link_20260604_140001.dump`.
- capability `delete` del resource Koha YA deshabilitada (Fase 2.5, commit `24c2f74`) → ningún reconcile puede borrar borrowers.

---

## 1. Baseline (ANTES)

Koha borrowers por categoría (14,349 total):

| categorycode | N |
|---|---|
| student | 5,544 |
| **ESTUDI** | **3,386** |
| alum | 2,682 |
| staff | 1,423 |
| faculty | 1,114 |
| ADMINIST | 90 |
| VISITA | 73 |
| DOCEN | 23 |
| ANON | 5 · INVESTI 4 · ALUMNI 2 · JUBILADO 1 · ADMIN 1 · POSGRADO 1 | 14 |

Legacy gobernable-objetivo (ESTUDI+ADMINIST+VISITA+DOCEN+ALUMNI+POSGRADO+JUBILADO) = **3,576 borrowers**. De ellos 936 ESTUDI tienen historial de préstamos (NO borrables; deben converger por adopción).

---

## 2. Diagnóstico del universo legacy (cruce 3,576 borrowers ↔ MidPoint)

Cruce por `name`==cardnumber (código canónico) ∪ `lambDocNum`==cardnumber-as-DNI (zfill8).

| Clase | N | Significado |
|---|---|---|
| **con foco MidPoint** | **242** | correlacionable a una identidad |
| **NO-FOCUS** | **3,334** (3,259 ESTUDI) | personas sin identidad MidPoint → solo convergen al onboardear (feed) |

### Sub-clasificación de los 242 con-foco (clave de la fase)

| Sub-clase | N | Hallazgo |
|---|---|---|
| **reconcile-verdadero** (borrower legacy ES el shadow del foco; active+aff+Lima) | **13** | gobernable por PATCH reconcile |
| **dual-duplicado** (foco ya posee su borrower canónico card=código; el legacy card=DNI es gemelo) | **62** | EXCLUIR → merge koha-expert |
| **orphan-shadow eligible** (shadow live sin owner) | **17** | de ellos **16 = dual-risk encubierto** (foco ya tiene borrower canónico); **1** genuino (69871) bloqueado por connector |
| **archived/limbo con-shadow** | **75** | NO tocar (ex-trabajadores ADMINIST archived sin aff viva; convergen en Fase 4, NO a staff vigente) |
| active-sin-shadow eligible | ~21 | onboarding create-only / recon (Fase 5 feed) |

**HALLAZGO MAYOR (consistente con Fase 2):** la inmensa mayoría de los "legacy con foco" son **gemelos DNI de personas ya bien gobernadas** — el borrower canónico (card=código) ya está en categoría correcta. El verdadero gobierno nuevo posible es **pequeño**; el grueso es:
- **merge dual (koha-expert):** ≈62+16 borrowers legacy DNI que duplican a un canónico ya correcto.
- **onboarding (feed):** 3,259 ESTUDI no-focus.

### Verificación dual-duplicado
Los 62 borrowers canónicos de los dual ya están en: 45 student + 6 staff + 6 alum + 5 faculty (categoría correcta). El trabajo de identidad ya está hecho; solo falta limpiar el borrower DNI gemelo (merge Koha).

---

## 3. CANARY — GATE: **PASS**

Foco `93423897…` (name=200110414, student, LIMA, active), borrower legacy 26241 card=200110414=código, ESTUDI. El borrower legacy ES su shadow (piv 26241 == borrower).

- PATCH `?options=reconcile` (no-op telephoneNumber idéntico) → **ESTUDI → student** ✓, BUL intacto, cardnumber preservado, shadow 1:1 (0 dual), total Koha 14,349 estable, **0 create, 0 delete**.

**Mecanismo validado:** PATCH `?options=reconcile` con delta idempotente (`description='phase3-converge-2026-06-04'`, atributo que NO alimenta ningún outbound Koha) → existence=true → el strong mapping `category-id-from-primary-affiliation` reescribe el categorycode por PATCH del borrower. NUNCA create.

---

## 4. MASIVO ejecutado — reconcile-verdadero (13)

PATCH reconcile serializado (sleep 1s, dentro de un solo ssh remoto).

| Resultado | N | Detalle |
|---|---|---|
| **convergidos** | **12** | 11 ESTUDI→student + 1 ESTUDI→staff (borrower 46503) |
| **bloqueado** | 1 | borrower 94400 (ADMINIST→staff) — ver §5 |

Borrowers convergidos: 26241, 22463, 22715, 25660, 26046, 26091, 27105, 28135, 29531, 29543, 67989 → **student**; 46503 → **staff**. Todos card=código preservado.

### Subconjunto orphan-shadow eligible (17)
- 16/17 resultaron **dual-risk encubierto**: el foco YA posee su borrower canónico (card=código en categoría correcta); el orphan (card=DNI) es un gemelo → importarlo daría dual-projection FATAL → **EXCLUIR → merge koha-expert**.
- 1/17 genuino (foco 9810042 / borrower 69871, ESTUDI→staff): `POST /shadows/{oid}/import` adoptó el shadow (HTTP 200) pero NO persistió el linkRef; el reconcile siguiente intentó **crear** un shadow nuevo con piv=69871 → chocó el unique-constraint contra el orphan existente → PARTIAL_ERROR, categoría no flipó. **Sin daño** (1 solo shadow, total estable). Diferido a koha-expert (mejora connector/existence §7).

---

## 5. Bloqueos encontrados (no son daño de esta fase)

### 5.1 — borrower 94400: dual-shadow Entra ID rompe el reconcile
El foco `2dba749b…` (00534601, staff, active, Lima) tiene **2 shadows ACCOUNT/default en Entra ID** (`2f11c057…`): `00534601@upeu.edu.pe` y `gabrielcortez@upeu.edu.pe`. El reconcile carga ambos → `PolicyViolationException: already exists in lens context` ANTES de procesar Koha → aborta el clockwork entero → categoría Koha nunca se aplica.
- Solo **3 focos en todo PROD** tienen dual-shadow Entra ID (problema marginal aislado).
- **NO es daño de Fase 3.** Entra ID es inbound-only/proposed (no provisiona), pero el dual-shadow rompe cualquier reconcile del foco.
- **Acción:** sub-workstream Entra ID dedup (mismo patrón que el dedup dual-shadow LDAP histórico). Fuera de scope Koha.

### 5.2 — borrower 69871: limitación connector/existence (storm root)
El existence mapping no resuelve un shadow orphan por `primaryidentifiervalue` antes de intentar create → choca unique-constraint. Es la **causa raíz del storm** documentada en Fase 1/2 §4/§6. Mejora durable para koha-expert (no recompilar aquí): resolver por piv (searchObjects) antes de create, e idempotencia del fallback 409.

---

## 6. Estado final — ANTES / DESPUÉS

### Koha categorías

| categorycode | ANTES | DESPUÉS | Δ |
|---|---|---|---|
| student | 5,544 | 5,555 | **+11** |
| **ESTUDI** | **3,386** | **3,374** | **−12** |
| staff | 1,423 | 1,424 | **+1** |
| (resto) | igual | igual | 0 |
| **TOTAL** | **14,349** | **14,349** | **0** |

12 borrowers ESTUDI convergieron a canónica. **0 cardnumber duplicado.** Total estable (0 create, 0 delete).

### MidPoint invariantes

| Invariante | Valor | Nota |
|---|---|---|
| m_user_total | 49,481 | = baseline → **0 fusión, 0 foco nuevo, 0 borrado** |
| dup_piv_koha | 0 | ✓ |
| dual_projection_koha | 13 | **pre-existente** (borrowers 97xxx/94xxx de runs previos); intersección con mis 13 tocados = ∅ → NO introducido por Fase 3 |
| running_tasks | 0 | limpio |

**0 fusión de personas, 0 duplicado de cardnumber, 0 dual-projection nuevo, 0 cambio de m_user.**

---

## 7. Por qué el vaciado de legacy es modesto (lección canónica)

El "vaciado de ESTUDI por gobierno MidPoint" es estructuralmente pequeño porque:
1. **3,259 ESTUDI no tienen foco** → no son linkeables; convergen SOLO al onboardear su identidad (feed Estudiantes/Egresados — Fase 5).
2. **~78 legacy con foco son gemelos DNI** de personas cuyo borrower canónico (card=código) YA está en categoría correcta → resolución = merge Koha (koha-expert), no MidPoint.
3. **75 con-shadow son archived/limbo** → no son afiliación vigente; no deben ir a categoría activa.
4. El gobierno nuevo efectivo de esta fase = **12 flips** (los reconcile-verdadero genuinos).

Esto NO es un fallo: es la realidad del dataset. El vaciado real de legacy ocurrirá por (a) onboarding masivo create-only del feed (16,070 sin borrower → student) y (b) merge dual-risk (koha-expert).

---

## 8. Qué queda para Fase 4 / otros workstreams

1. **3,259 ESTUDI no-focus** → onboarding create-only del feed Estudiantes (storm neutralizado para gobernables tras connector fix; o create-only puro para los 16,070 sin borrower).
2. **~78 dual-risk** (62 dual-duplicado + 16 orphan dual encubierto + 13 dual-projection ya adoptados) → **merge de borrowers Koha (koha-expert)**, conservando card=código. NUNCA link (daría dual-projection FATAL).
3. **3 focos dual-shadow Entra ID** (incl. 94400) → dedup Entra ID (sub-workstream).
4. **1 caso 69871** → mejora connector/existence (resolver por piv antes de create).
5. **75 ADMINIST/legacy archived** → re-stamp a categoría inactiva/`local` vía mecanismo seguro (NO borrado, tienen historial), o dejar como leaver archivado. Decisión Fase 4.
6. **Borrado de categorías legacy vacías** → Fase 4, SOLO cuando ESTUDI/DOCEN bajen a ~0 gobernables (hoy ESTUDI 3,374 = casi todo no-focus, lejos de vaciarse por esta vía).
7. **Colegio Unión escolares (menores)** → pendiente decisión Orrego CRAI (7a categoría).
8. **ANON 5 / ADMIN 1 / INVESTI 4** → cuentas sistema → `local`/dejar. Fase 4.

---

## 9. Mecanismos validados (reutilizable SciBack)

- **flip categoría sin storm:** PATCH `/users/{oid}?options=reconcile` con delta idempotente en atributo NO-proyectado (`description`). existence=true → PATCH borrower. Cero create.
- **NUNCA** linkear/importar un orphan-shadow a un foco que ya posee otro shadow del mismo resource → dual-projection FATAL.
- **correlación 3 capas** (`cardnumber==name`, `cardnumber-as-DNI==lambDocNum`, `DNI-extended==lambDocNum`) + zfill8 sigue siendo correcta; conservar card=código como llave canónica.
- diagnóstico previo OBLIGATORIO: distinguir "el borrower legacy ES el shadow del foco" (reconcile) vs "el foco ya tiene OTRO shadow" (dual → merge). El conteo `ya_tiene_shadow_koha` infla si no se desambigua por piv.
