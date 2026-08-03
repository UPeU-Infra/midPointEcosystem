# Barrido focos DUAL SUCIOS (student + worker) — 2026-06-15

Cierre operativo del fix de desempate IIA single-valued
(tag `iga-desempate-dual-email-doc-2026-06-15`, commits `a5a4e6f`→`c45ce31`).

## Problema
Personas con doble afiliación viva (`liveAffiliationStudent` + `liveAffiliationWorker`)
fallaban en PROJECTOR (INITIAL) con HTTP 500 por colisión de cardinalidad
single-valued (`emailAddress`, `lambDocNum/lambDocType`, `taxId`): dos IIAs
(Estudiantes y Trabajadores) alimentaban el mismo item con valores distintos.
El fix desempata por precedencia/strength (Trabajadores/MOISES gana con empleo vivo).

## Scope (reproducible)
`m_user where ext ? '216'(liveAffiliationWorker) and ext ? '217'(liveAffiliationStudent)
and lifecyclestate='active'` → **518 focos**.

`scope-dual-dirty-active.tsv`: `oid \t name(código) \t lifecycle \t [P|-]pcode \t [I|-]inei`.
De los 518: 194 con P-code, 189 ya con INEI, **5 con P-code SIN INEI** (canarios prioritarios).

## Driver
`driver-reconcile-dual-dirty.sh <ADMIN_PASS> [MAX]`
- PATCH `?options=reconcile` no-op en `description` (`dual-sweep-<ts>`). Idempotente, storm-free.
- Serializado (uno por uno), resumible vía `/tmp/dual_done.txt`, log `/tmp/dual_progress.log`.
- `MAX` opcional limita a los primeros N pendientes (canary).
- HTTP 204/200/250 = OK. HTTP 5xx con INEI materializado (P-code) o cuerpo
  `partial`/`without any attributes` = OK benigno (residual ortogonal empty-shadow-add,
  NO crea cuentas). HTTP 5xx con P-code SIN INEI = FAIL genuino.

## Baseline invariantes (pre)
- m_user = 62,465
- koha_bul borrowers = 19,876 · dup_cardnumber = 0 · sort2_populated = 9,644

## Restricciones
0 borrowers nuevos esperado, 0 dup-cardnumber, sin storm. Monitoreo cada 50 focos.
Si cualquier invariante se mueve mal → DETENER.

Relacionado: `upeu/tasks/bsort2-inei-posgrado/` (mismo mecanismo, ronda posgrado).
