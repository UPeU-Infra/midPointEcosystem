# FASE 3b — Onboarding CREATE-ONLY de matriculados sin borrower Koha

**Fecha:** 2026-06-04
**Operador:** midpoint-expert (Claude Code)
**Objetivo:** onboardear los matriculados vigentes (feed sem 267/279/283) que NO tienen borrower Koha (create-only LIMPIO, sin storm), por lotes. Crear focos + provisionar cuenta Koha canónica (student/faculty, cardnumber=código, BUL si Lima).
**Resultado:** pipeline end-to-end VALIDADO; ~47 estudiantes Lima onboardeados limpiamente. Mecanismo de masivo identificado (full-recon-in-limbo) pero NO ejecutado: requiere visto bueno por cambio de perfil de riesgo (toca el set con orphan→storm). Per-código probado pero INVIABLE a escala (~2-3 min/código por el sweep repoShadows).

---

## 0. Backups
- pg_dump MidPoint: `/home/juansanchez/backups/bkp_phase3b_20260604_161043.dump` (585 MB en host). Verificado.
- Koha: `mysqldump borrowers` previo en Fase 3 (`/tmp/koha_borrowers_phase3_20260604_154104.sql`), válido del día.
- capability delete Koha ya deshabilitada (Fase 2.5, commit 24c2f74) → ningún provisioning borra borrowers.

---

## 1. Definición del subconjunto create-only (fresca, no heredada)
Feed Oracle (DISTINCT pna.CODIGO, sem 267/279/283, aca.ESTADO='1') = **24,677 códigos**. Cruce por `lambDocNum` normalizado (DNI zfill8 / >8 tal cual, tipo-preservante) contra los 14,349 cardnumbers Koha (raw + normalizado, por código Y por DNI):

| Clase | N |
|---|---|
| Feed total | 24,677 |
| Con borrower Koha (excluir — riesgo storm) | 9,103 |
| **CREATE-ONLY LIMPIO** | **15,574** |
| — addFocus nuevo (doc ausente en MidPoint) | 10,103 |
| — link a foco existente (doc/código presente) | 5,471 |

Por sede (feed): Lima 12,858 · Juliaca 8,887 · Tarapoto 2,932. De los create-only addFocus: **Lima 5,294**, prov 4,809.

El conteo (15,574) es algo menor al 16,070 heredado de Fase 1 porque este cruce es ESTRICTO (excluye también DNI-as-card y código-normalizado), garantizando que ningún código con CUALQUIER forma de borrower entre al lote → cero riesgo de storm.

---

## 2. CANARY / BATCH — GATE: **PASS**

### 2.1 Hallazgo arquitectónico: el bootstrap-deadlock
Un `addFocus` por recon materializa el foco con los inbounds (`liveAffiliationStudent=student`, `campusStudent`, `institutionalCode`) pero **SIN archetype, SIN primaryAffiliation, lifecycle=NULL (limbo)**. Causa: NO hay object template default para `c:UserType`; el template (J3 deriva primaryAffiliation; D7 asigna archetype) sólo corre vía el archetypePolicy de un archetype YA asignado → deadlock. Confirma el irreducible #2 de MEMORY.

**Implicación de seguridad (positiva):** un foco en limbo NO provisiona Koha (sin inducement AR-Koha-Patron) → **un recon que sólo crea focos limbo es STORM-FREE**.

### 2.2 Pipeline canónico validado (2 fases)
1. **Recon scoped por `__UID__`=CODIGO** (el connector ScriptedSQL honra EqualsFilter sobre `__UID__`/`__NAME__` → empuja `pna.CODIGO=?` a Oracle) → addFocus (limbo) o link a foco existente.
   - NOTA: el `<import>` work NO escopea on-resource en 4.10 (error "Resource not defined in a search query"), ni con objectclass ni con kind/intent. **SÓLO `<reconciliation>` con `<kind>account</kind><intent>default</intent>`** lleva el binding de recurso que empuja el filtro al connector. (mismo patrón que el recon Koha por `ri:patron_id` de Fase 2).
2. **Bootstrap del archetype student** filtrado por `extension/sb:liveAffiliationStudent='student'` (la señal materializada PRE-template, NO primaryAffiliation que es derivado → deadlock) + sin archetype + lifecycle != archived → al asignarlo corre toda la cadena: base J3b/J3 deriva `affiliations`+`primaryAffiliation`, student template asigna business roles, gate Koha provisiona borrower **BUL** (Lima) con cardnumber=código.

### 2.3 Evidencia
- Recons scoped crearon 15+5 focos limbo (canary 40 + batch 15). Tasks `p3b-onb-*` con OID determinista (md5 del código), `cleanupAfterCompletion PT5M`, guards storm/mem/backpressure (`driver-recon-batch.sh`).
- Bootstrap (`bootstrap-archetype-student-live.xml`, iterativeScripting, 2 threads) gobernó **180 focos limbo** → 0 limbo residual.
- **Koha: 14,349 → 14,398 (+49 borrowers nuevos), TODOS BUL, categorycode student/faculty correcto, cardnumber=código, 0 dup.** Las sedes Juliaca/Tarapoto NO recibieron cuenta (gate multi-campus #65 respetado).
- Testigos: borrower 97953 (cardnumber 201410997, student, BUL); 97958 (9310236, faculty, BUL — prioridad faculty>student respetada). Critsi (202613369) y Tito (200810869/DNI 43508613) intactos, active, LIMA.

### 2.4 Invariantes (ANTES → DESPUÉS)
| Invariante | ANTES | DESPUÉS |
|---|---|---|
| m_user total | 49,481 | 49,502 (+21 focos nuevos create-only) |
| dual-shadow Estudiantes | 0 | **0** |
| dual-shadow Koha | 13 | **13** (sin crecer) |
| Koha total | 14,349 | 14,398 |
| Koha cardnumber dup | 0 | **0** |
| Koha student | 5,555 | 5,602 |
| limbo students (no archetype) | — | **0** |

**0 fusión de personas, 0 duplicado cardnumber, 0 dual-projection nuevo, 0 storm.**

---

## 3. BLOQUEANTE de throughput (decisión pendiente del usuario)

El recon scoped por código es CORRECTO pero **cada ejecución tarda ~2-3 min wall** (dominado por la sub-actividad `repoShadows` de la reconciliation, que barre los ~11k shadows Estudiantes en cada corrida, sin importar que el filtro on-resource devuelva 1 objeto). A concurrencia 5: 15 códigos = 877 s.

→ **15,574 códigos por-código = ~10-20 días de cómputo continuo.** INVIABLE.

### Mecanismo de masivo recomendado (NO ejecutado, requiere visto bueno)
**Full-recon-in-limbo + bootstrap scoped:**
1. UNA recon completa del recurso Estudiantes (sin query) → crea TODOS los focos nuevos en **limbo** (storm-free, porque limbo no provisiona Koha). Materializa shadows+focos en una sola pasada bulk (rápida).
2. **Riesgo a validar ANTES:** la reacción `linked`/`unlinked` del full-recon TAMBIÉN toca los ~7,640 active-con-orphan-borrower (Fase 1 §4) → su proyección Koha intenta create→409→storm. El full-recon NO es automáticamente storm-free para el set YA-activo-con-orphan. Hay que (a) neutralizar ese set primero (link de orphans / merge dual, Fase 2/koha-expert), o (b) hacer el bootstrap (que dispara Koha) **scoped SÓLO a los códigos create-only** vía la lista `/tmp/create_only_codes.txt` (15,574), dejando a los limbo no-create-only sin provisionar hasta resolver su orphan.
3. Mejora durable connector/existence (koha-expert): idempotencia del fallback 409 + resolver shadow por piv antes de create → elimina el storm de raíz y habilita un onboarding masivo trivial.

**Por qué se detuvo aquí:** ejecutar el full-recon cambia el perfil de riesgo (toca el set con orphan→storm). Per regla de la tarea ("storm que no cede → para y consúltame"), se deja el pipeline validado y el sistema sano para decisión.

---

## 4. Estado final (limpio)
- 0 tareas de onboarding colgadas. Imports Estudiantes (4) + recons + phase1-canary SUSPENDED. Sólo Cleanup/Trigger/Validity RUNNABLE.
- Containers healthy, disco 89% (7.2 G libres), mem MidPoint 73%.
- 0 limbo students. Dual-shadow Est 0, Koha 13 (invariante).

## 5. Artefactos (repo)
- `upeu/tasks/phase3b-onboarding/recon-scoped-template.xml` — plantilla recon scoped por `__UID__`.
- `upeu/tasks/phase3b-onboarding/driver-recon-batch.sh` — driver batch (OID determinista, cleanup PT5M, guards storm/mem/backpressure). Sólo para lotes pequeños/medios; NO para 15k.
- `upeu/tasks/phase3b-onboarding/bootstrap-archetype-student-live.xml` — bootstrap student archetype filtrado por liveAffiliationStudent (escapa el deadlock). REUTILIZABLE para sweep de limbo.
- Listas operativas (local, no repo): `/tmp/create_only_codes.txt` (15,574), `/tmp/co_split.json` (addfocus/link), `/tmp/feed_sede.tsv`.

## 6. Qué queda
1. **Masivo create-only (15,574)** → mecanismo full-recon-in-limbo + bootstrap scoped (visto bueno usuario). Bloqueante de fondo = storm de orphans → resolver primero (koha-expert connector fix o neutralizar set orphan).
2. **9,103 con-borrower** (orphan-huérfano + dual-risk) → Fase 2/3/koha-expert (link/merge), NO en 3b.
3. **3 focos dual-shadow Entra ID** (incl. 94400) → dedup Entra.
4. **Inactivos antiguos #3** (no-focus cohortes viejas) → onboardean sólo si entran al feed vigente; los que no, fuera de horizonte.
5. **Colegio Unión escolares menores** → pendiente decisión Orrego CRAI (7a categoría).

## 7. Mecanismos validados (reutilizable SciBack)
- **Scoping de recon on-resource con connector ScriptedSQL:** sólo `<reconciliation>` (kind/intent) empuja el filtro; `<import>` no. Filtro por `attributes/icfs:uid` (el connector honra EqualsFilter sobre `__UID__`).
- **Escape del bootstrap-deadlock:** bootstrap del structural archetype filtrado por la señal de afiliación VIVA materializada por inbound (`liveAffiliationStudent`), NO por `primaryAffiliation` (derivada → deadlock).
- **Onboarding storm-free por diseño:** addFocus en limbo NO provisiona; el provisioning se dispara recién al asignar archetype → permite separar "crear identidad" (bulk) de "provisionar cuenta" (scoped/controlado).
- **NUNCA reusar OID de task con overwrite mientras corre:** corrompe el activity-state tree → FATAL_ERROR. Usar OID único determinista por objeto.
