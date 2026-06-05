# FASE 3c — Bulk onboarding CREATE-ONLY de matriculados (ejecución final)

**Fecha:** 2026-06-04/05
**Operador:** midpoint-expert (Claude Code)
**Objetivo:** crear los ~10,081 focos de matriculados vigentes que aún NO existen en MidPoint (addFocus create-only) + provisionar su cuenta Koha (student/faculty, cardnumber=código, BUL si Lima), por lotes, con kill-switch.
**Precondición heredada (3b):** pipeline validado (full-import crea focos limbo storm-free; bootstrap por `liveAffiliationStudent` escapa el deadlock y provisiona Koha). Connector Koha v1.3.9 desplegado.

---

## 0. Backups
- **Baseline pre-bulk validado:** `/home/juansanchez/backups/bkp_phase3c_bulk_20260604_195047.dump` (2.3G, host). Integridad verificada con `pg_restore -l` (EXIT=0, 134 TABLE DATA). Captura el estado m_user 49,503 / Koha 14,398 / dup_card 0.
- Backups previos válidos del día: `bkp_phase3c_20260604_182853.dump` (860M, 18:36), `bkp_phase3b_20260604_161043.dump`.

### INCIDENTE de disco (resuelto, 0 daño) — LECCIÓN CRÍTICA
Mis primeros 3 intentos de `pg_dump` lanzados como `ssh "... &"` / `docker exec -d` **NO murieron al cerrarse el SSH** — siguieron vivos dentro del namespace del contenedor (invisibles a `ps` del host), corriendo 3-4 en paralelo, cada uno escribiendo su `.dump` a `/tmp` del contenedor data. Eso, sumado a ~25G de dumps temporales acumulados de fases previas (nunca limpiados), **saturó el disco al 100%**.
- **Síntoma:** `rm /tmp/*.dump` NO liberaba espacio (archivos held por fds de los pg_dump vivos); dumps "muertos" reaparecían creciendo.
- **Fix:** `sudo pkill -9 -f 'pg_dump -U midpoint'` (mató 3-4 huérfanos) + `docker exec -u root ... rm -f /tmp/*.dump` (los dumps son root-owned; rm como uid 1001 falla silencioso) → liberó 23G, disco 100%→61%.
- **REGLA:** (1) nunca lanzar pg_dump nuevo sin verificar que el anterior cerró (`ps aux|grep pg_dump`); (2) `/tmp` del contenedor data NO se auto-limpia — borrar dumps tras cada `docker cp`; (3) un pg_dump foreground en sesión SSH con `ServerAliveInterval` + verificación `pg_restore -l` es la vía robusta; (4) NUNCA acumular dumps en `/tmp` del contenedor — copiar a host y borrar inmediatamente.

---

## 1. BLOQUEANTE de fondo identificado (corrige la suposición del brief)
El brief asumía "storm neutralizado por connector v1.3.9 (adopt-by-email)". **FALSO para este caso.** Evidencia en logs durante el full-import:
```
ERROR AbstractKohaService: POST .../api/v1/patrons Status: 409 Conflict
Body: {"error":"A patron record matching these details already exists"}
```
El connector v1.3.9 **intenta CREATE (POST) y falla con 409** (no hace PATCH-adopt) cuando el match Koha es por "these details" (DNI/extended-attr), NO por cardnumber/userid/email. Es el **caso residual DNI-extended-attr** que koha-expert anticipó. El daño está prevenido por MidPoint (conflict-detection → Koha TOTAL/dup_card invariantes), NO por el connector. Pero el volumen de 409 satura logs y disparó el kill-switch de storm.

**Causa del 409:** el full-import procesa TODO el feed (24,677 filas), incluyendo los ~9,103 focos active-con-borrower (orphan-shadow Koha). Cada recompute de ese set dispara su `<existence>` outbound Koha → CREATE → 409.

---

## 2. SOLUCIÓN: desconectar outbound Koha durante el bulk (patrón Entra ID)
**Decisión (autónoma, reversible, patrón ya probado en este proyecto con Entra ID):** poner el **objectType Koha account (id 11045)** en `lifecycleState=proposed` vía PATCH quirúrgico → desactiva TODO outbound Koha (incluido `<existence>`) → el import crea focos + reconcilia existentes con **0 POST a Koha = 0 storm garantizado**.

```
PATCH /resources/9b5a7c81-.../  replace schemaHandling/objectType[11045]/lifecycleState = proposed
```
Verificado: `kohaPOST=0` sostenido tras el PATCH. Inbound/correlación Koha siguen activos.

**Separa "crear identidad" (bulk, Koha off) de "provisionar cuenta" (controlado, Koha on)** — el patrón ideal que 3b §7 recomendó.

### Restaurar (fase de provisioning):
`PATCH ... replace schemaHandling/objectType[11045]/lifecycleState = active` → reconecta outbound. Luego bootstrap escopeado a limbo-nuevos provisiona Koha controladamente (solo Lima, gate #65).

---

## 3. Mecanismo del bulk (en ejecución)
1. **Full import Estudiantes** (`phase3c-full-import-estudiantes-limbo`, OID `...3c04`, **workerThreads=4**, Koha=proposed):
   - `unmatched` → `addFocus` → crea foco LIMBO con inbounds materializados (`liveAffiliationStudent`=item 217=student, `campusStudent`=item 219). **SIN archetype → sin inducement Koha → no provisiona.**
   - `linked`/`unlinked` existentes → reconcilia sin tocar Koha (proposed).
   - Throughput ~17 focos/min con 4 threads → ~10h para 10,081 (domina el reconcile de los ~14k existentes; el import no escopea on-resource en 4.10).
2. **Kill-switch server-side desacoplado** (`/home/juansanchez/p3c_killswitch.sh`, setsid, log `p3c_killswitch.log`): suspende si mem≥88% (OOM guard) o si Koha recibe POST>8/50s (leak guard — no debe ocurrir con proposed). Sobrevive al cierre de SSH.
3. **Bootstrap** (pendiente, tras restaurar Koha=active): `bootstrap-archetype-student-live.xml` asigna archetype student a focos limbo con `liveAffiliationStudent=student` → corre templates → provisiona Koha BUL solo Lima.

### NOTA monitoreo: extension por ID de item, no por nombre
`m_user.ext` almacena la extension con **IDs numéricos de item**, no nombres. Mapeo (m_ext_item):
- `217` = `liveAffiliationStudent`, `219` = `campusStudent`, `103` = `academicProgramRole`, `156` = `lambDocNum`.
- Query correcta: `ext->>'217'='student'` (NO `ext->>'liveAffiliationStudent'`, que da NULL).

---

## 4. Vías de throughput DESCARTADAS (validadas empíricamente)
| Vía | Resultado |
|---|---|
| `<import>` full sin query | Procesa todo → 409 storm del set orphan (resuelto con Koha=proposed, pero reconcilia 14k existentes innecesarios) |
| `<import>` scoped por `attributes/icfs:name` | progress=0 — import-work NO escopea on-resource en 4.10 (confirma 3b §7) |
| `<reconciliation>` scoped por `__UID__` | escopea (connector honra EqualsFilter) pero 151s/c por sweep repoShadows → inviable a escala |

El connector ScriptedSQL Estudiantes solo soporta EqualsFilter sobre `__NAME__`/`__UID__` (un código) o full-scan. No IN-list ni rango.

---

## 5. Resultados

### Fase A — Full import (creación de focos limbo) — COMPLETA
- Task `phase3c-full-import-estudiantes-limbo` OID `...3c04`, workerThreads=4, Koha objectType=**proposed** (outbound off).
- **m_user 49,503 → 62,465 (+12,962 focos limbo creados)**. TODOS sin archetype (limbo), storm-free.
- limboStud (`ext->>'217'='student'` sin archetype): **12,972** (LIMA 7,088 · JULIACA 4,496 · TARAPOTO 1,388).
- **0 duplicados:** 0 focos nuevos con lambDocNum pre-existente; m_user == names_distintos (62,465). Correlación íntegra.
- **El número real (12,962) excede el estimado (10,081)** porque el cruce co_split.json estaba desactualizado (~3h). Son matriculados vigentes legítimos, no duplicados.
- mem 56-57% estable toda la corrida, 0 POST a Koha. Kill-switch server-side desacoplado (`p3c_killswitch.sh`) detectó CLOSED limpio.
- **Throughput:** lento al inicio (reconcile de ~14k existentes), ráfagas de ~1000/min en zona addFocus. ~17min wall total.

### Fase B — Bootstrap (archetype student + provisioning Koha) — EN CURSO
- Restaurado Koha objectType[11045] → **active** (PATCH).
- **CANARY 30 OIDs LIMA: PASS.** → 30 focos active, archetype student structural + AuxAff-Student (0 dual-structural), Koha +13 borrowers BUL student cardnumber=código, **dup_card=0**. Storm mínimo (gemelos-DNI absorbidos sin crear dup).
- Bootstrap full `...3b00b6`, workerThreads=6, filtro `liveAffiliationStudent=student` + sin archetype + no archived.
- **Guard local** (`/tmp/bootstrap_guard_local.sh`, corre desde la Mac porque PROD no tiene sshpass): kill-switch con guard CRÍTICO `dup_cardnumber>0 → suspend` + mem≥88%. Lee Koha directo.
- Throughput ~56/min con 6 threads (provisioning Koha síncrono por foco Lima domina). ~3.8h estimadas.
- **PENDIENTE:** completar bootstrap → verificación final (testigos, invariantes) → restaurar tasks residuales suspendidas → memoria.

### Throughput bootstrap — SPLIT Lima/no-Lima (aplicado, reutilizable SciBack)
El bootstrap unificado a 2-6 threads era lento/problemático:
- **2 threads:** ~14/min, 0 timeouts, pero ~15h para todo.
- **6 threads:** la API Koha (`http://192.168.12.135:8001/api/v1/patrons`) da **`Read timed out`** → reintentos → throughput efectivo peor + focos en IN_PROGRESS. **La API Koha NO soporta 6 POST concurrentes sostenidos.** (host load 5+; connector v1.3.9). 0 duplicados igual (guard dup_card=0).

**SOLUCIÓN aplicada — 2 olas por campus:**
1. **Ola no-Lima** (Juliaca+Tarapoto, ~5,884): filtro `campusStudent != LIMA`, **8 threads**. NO provisiona Koha (gate #65) → 0 POST, 0 timeout → **~1,900/min, drenó en ~2 min**. CLOSED.
2. **Ola Lima** (~6,864): filtro `campusStudent == LIMA`, **3 threads** (balance: sin `Read timed out`, más rápido que 2). Provisiona Koha BUL. Guard dup_card externo. ~30/min.

**Lección SciBack:** separar provisioning-pesado (Koha síncrono) de bootstrap-ligero por campus/atributo; dimensionar threads al SLA del recurso destino, no al de MidPoint. La API Koha es el cuello, no MidPoint.

### Guard dup_card — corre desde la Mac (PROD sin sshpass)
PROD no tiene `sshpass` instalado → el kill-switch server-side no puede consultar Koha. El guard de `dup_cardnumber` (`/tmp/bootstrap_guard_local.sh`) corre desde la Mac (tiene sshpass + acceso a Koha + MidPoint REST): cada ciclo lee `dup_cardnumber` de Koha y suspende el bootstrap si >0. Mejora SciBack: instalar sshpass en PROD o usar un guard SQL nativo sobre el shadow cache.
