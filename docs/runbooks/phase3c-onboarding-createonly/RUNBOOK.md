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

### Fase B-RELANZADA — server-side (sobrevive desconexion del cliente) — 2026-06-05 02:20Z
El driver Mac-side (guard `dup_card`) murio al suspenderse la laptop ~01:47Z; la task nativa de
MidPoint siguio, pero quedo detenida sin completar. **Estado al reanudar:** m_user 62,465; limbo
total 6,878; **6,579 focos Lima student en limbo** (sin archetype). Ademas **196 stragglers**:
student-archetyped Lima CON rol AR-Koha-Patron pero SIN borrower (POST interrumpido por el corte;
**0 pendingOperation -> sin corrupcion**, solo provisioning pendiente). Koha 14,607 / student 5,824 /
**dup_card=0**. Koha objectType[default]=active, connector v1.3.9. Sin daño del corte.

**Relanzado 100% SERVER-SIDE** (3 artefactos en `upeu/tasks/phase3c-onboarding/`, commit posterior):
1. **Task A** `phase3c-bootstrap-student-lima-relaunch` (OID `...3c1a3a`, iterativeScripting **assign**
   archetype student, **workerThreads=3**) — filtro `liveAffiliationStudent=student` + sin archetype +
   no archived (sin filtro de campus: el gate #65 en la construction del AR-Koha-Patron decide Koha
   por-foco). Idempotente. Las tasks nativas corren en el task manager de MidPoint -> ya estan
   desacopladas de cualquier cliente.
2. **Task B** `phase3c-recompute-straggler-lima-koha` (OID `...3c1b3b`, recomputation, wt=3) — recompute
   de los stragglers (student Lima active con rol Koha) -> dispara la construction Koha -> materializa
   el borrower faltante. Idempotente. Corre DESPUES de A.
3. **Driver+guard** `p3c-lima-guard-driver.sh` bajo `setsid nohup` en PROD (PID 365361, PPID reparenta
   a 1 -> sobrevive cierre SSH). Secuencia A->B; cada 30s vigila **dup_card** (desde el SHADOW CACHE,
   `m_shadow.attributes->'128'` = cardnumber, server-side sin mysql) y **mem**. `dup_card>0 -> suspende
   AMBAS` (kill-switch sagrado). `mem>=88% -> suspende` (OOM guard; reinicio MidPoint autorizado).
   Log a `~/phase3c-lima-bootstrap.log`.

**Throttle Koha = 3 threads** (confirmado: 4+ POST concurrentes -> `Read timed out`).

**Arranque sano verificado (02:20-02:23Z):** Task A RUNNING; limboStud 6,382->6,334 (~48 en 3 min);
koha_shadows 12,050->12,095 (+45 borrowers BUL); **dup_card=0 sostenido**; mem 57% estable. Driver
detached confirmado (sobrevivio al kill del SSH lanzador).

#### Monitoreo (SSH, sin depender del proceso)
```bash
source ~/.secrets/midpoint-upeu.env
# log de progreso
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "tail -20 ~/phase3c-lima-bootstrap.log"
# conteos en vivo
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tAc \"SELECT (SELECT count(*) FROM m_user u WHERE u.ext->>'217'='student' AND NOT EXISTS (SELECT 1 FROM m_ref_archetype ra WHERE ra.owneroid=u.oid) AND (u.lifecyclestate IS NULL OR u.lifecyclestate<>'archived')) AS limbo_stud, (SELECT count(*) FROM m_shadow WHERE resourcereftargetoid='9b5a7c81-47aa-42ac-9a08-4de8b64935af' AND (dead IS NULL OR dead='false')) AS koha_shadows, (SELECT count(*) FROM (SELECT attributes->'128' c FROM m_shadow WHERE resourcereftargetoid='9b5a7c81-47aa-42ac-9a08-4de8b64935af' AND attributes ? '128' AND (dead IS NULL OR dead='false') GROUP BY attributes->'128' HAVING count(*)>1) x) AS dup_card;\""
# driver vivo?
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "ps -o pid,etime,cmd -p 365361 | tail -1"
```
dup_card debe ser **0 SIEMPRE**. Cuando `limbo_stud -> ~0` y Task B cierra -> dren completo.

#### Como detener
```bash
# 1) matar el driver (deja de secuenciar/vigilar)
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "kill 365361 2>/dev/null; pkill -f p3c-lima-guard"
# 2) suspender las tasks nativas en MidPoint (siguen corriendo aunque muera el driver)
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "curl -s -X POST -u \$MIDPOINT_ADMIN_USER:\$MIDPOINT_ADMIN_PASS http://localhost:8080/midpoint/ws/rest/tasks/d1a2b3c4-3c00-4abc-9def-0000003c1a3a/suspend; curl -s -X POST -u \$MIDPOINT_ADMIN_USER:\$MIDPOINT_ADMIN_PASS http://localhost:8080/midpoint/ws/rest/tasks/d1a2b3c4-3c00-4abc-9def-0000003c1b3b/suspend"
```
**Auto-suspension del guard:** si `dup_card>0` el driver suspende AMBAS tasks solo y registra
`!!!! KILL-SWITCH dup_card=...` en el log. Si `mem>=88%` suspende la task en curso (reinicio MidPoint
autorizado para recuperar heap, luego re-`resume`).

#### Verificacion final (al drenar)
- **Testigos:** Critsi (202613369) y Tito (200810869 / DNI 43508613) intactos, active, LIMA, borrower BUL.
- **Invariantes:** `dup_card=0`; 0 dual-structural; m_user names_distintos == m_user total (correlacion intacta);
  dual-shadow Estudiantes 0; limbo_stud -> ~0 (solo residuos sin campus materializado, no Lima provisionables).
- **Conteos ANTES->DESPUES:** Koha total 14,607->~21k (segun cuantos Lima); student 5,824->+(~6,5k);
  faculty 1,119->+ (prioridad faculty>student); dup_card 0->**0**.

### Guard dup_card — corre desde la Mac (PROD sin sshpass)
PROD no tiene `sshpass` instalado → el kill-switch server-side no puede consultar Koha. El guard de `dup_cardnumber` (`/tmp/bootstrap_guard_local.sh`) corre desde la Mac (tiene sshpass + acceso a Koha + MidPoint REST): cada ciclo lee `dup_cardnumber` de Koha y suspende el bootstrap si >0. Mejora SciBack: instalar sshpass en PROD o usar un guard SQL nativo sobre el shadow cache.

---

## Addendum 2026-06-04 — FALSO POSITIVO del kill-switch + guard refinado

### Qué pasó
El primer relanzamiento server-side abortó a las **02:25:08Z** cuando el driver
`p3c-lima-guard-driver.sh` detectó `dup_card=1` en el shadow-cache
(`m_shadow.attributes->'128'`). Suspendió ambas tasks (fail-safe correcto).

**Era un FALSO POSITIVO, transitorio del `create-or-adopt` de KohaConnector v1.3.9.**
Durante el adopt, por un instante coexisten **2 shadows VIVOS** con el mismo
cardnumber (el nuevo recién creado + el que se va a adoptar) ANTES de que el viejo
se marque `dead`. El guard viejo —que solo filtraba `dead IS NULL OR dead='false'`—
los contó como duplicado y abortó.

### Verificación post-mortem (estado limpio confirmado)
- **Koha: 0 cardnumbers duplicados** (verdad dura).
- **MidPoint: 0 duplicados REALES vivos.** Los 12 cardnumbers con >1 shadow en cache
  son pares **tombstone + live**: cada uno tiene exactamente 1 shadow vivo
  (`dead IS NOT TRUE AND exist=true`) + 1 muerto/pending del adopt.
  Query de la verdad:
  ```sql
  SELECT attributes->>'128', COUNT(*) FROM m_shadow
   WHERE attributes ? '128' AND dead IS NOT TRUE AND exist=true
   GROUP BY attributes->>'128' HAVING COUNT(*)>1;   -- vacío = 0 dup reales
  ```
- Tasks `relaunch` + `straggler` SUSPENDED, `full-import` CLOSED, driver muerto. 0 daño.
- Limbo restante: ~6,2-6,3k focos student Lima sin archetype/cuenta Koha.

### Guard refinado (distingue transitorio de real)
Tres barreras en `run_guarded()`:
1. **Detector barato (cada ciclo):** dup en shadow-cache contando solo shadows
   `dead IS NOT TRUE AND exist=true`. Si 0 → OK. Si >0 → NO aborta: pasa a (2).
2. **Verdad dura de KOHA via REST (`koha_confirm_real`):** por cada cardnumber
   sospechoso consulta `GET /api/v1/patrons?cardnumber=X` → header `x-total-count`.
   - algún cardnumber con `x-total-count >= 2` en Koha → **DUP REAL → KILL inmediato**.
   - todos `<= 1` → transitorio del adopt → **CONTINÚA**.
   - Koha no responde → `UNKNOWN`, cae a (3).
3. **Anti-transitorio por persistencia (`STREAK_MAX=2`):** si el MISMO set de
   cardnumbers dup persiste `>= 2` ciclos consecutivos → KILL (no converge).
   Defensa en profundidad por si Koha REST fallara.

Se mantienen: **mem-guard (88%)**, kill-switch real (dup persistente/Koha-confirmado
SÍ suspende ambas tasks), secuencia Task A → Task B.

**Nuevas vars de entorno del driver:** `KOHA_URL`, `KOHA_CID`, `KOHA_SECRET`
(de `~/.secrets/koha-prod.env`: `KOHA_PROD_URL`, `KOHA_PROD_CLIENT_ID`, `KOHA_PROD_SECRET`).
El host MidPoint alcanza Koha REST (HTTP 200) directamente — no requiere mysql/sshpass.

### Relanzamiento
```bash
source ~/.secrets/midpoint-upeu.env
source ~/.secrets/koha-prod.env
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod \
 "cd ~/midPointEcosystem && git pull --ff-only && \
  cd upeu/tasks/phase3c-onboarding && chmod +x p3c-lima-guard-driver.sh && \
  MP_AU='$MIDPOINT_ADMIN_USER' MP_AP='$MIDPOINT_ADMIN_PASS' \
  KOHA_URL='$KOHA_PROD_URL' KOHA_CID='$KOHA_PROD_CLIENT_ID' KOHA_SECRET='$KOHA_PROD_SECRET' \
  setsid nohup ./p3c-lima-guard-driver.sh >> ~/phase3c-lima-bootstrap.log 2>&1 < /dev/null & \
  sleep 1; echo launched"
```
