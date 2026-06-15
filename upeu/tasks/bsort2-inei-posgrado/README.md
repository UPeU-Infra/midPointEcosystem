# Bsort2 → INEI — Migración posgrado + conflicto pregrado (2026-06-14)

Ronda posgrado de la migración Bsort2 P-code→INEI (continúa la ronda pregrado del 2026-06-14).

## Qué hace
Reconcilia (PATCH `?options=reconcile`, no-op en `description`) los estudiantes Lima
activos de posgrado cuyo P-code tiene INEI validado en `LT-Pcode-INEI`
(OID `e129d9e4-c2fd-4a02-9369-0ae5b8f59c06`), para que:

`academicProgramSuneduCode` (inbound Oracle `COALESCE(CODIGO_SUNEDU2,'P'||CODIGO_SUNEDU)`)
→ `academicProgramIneiCode` (template `UserTemplate-Person-Base` bloque D.1c, vía LT)
→ Koha `borrowers.sort2` (Bsort2, outbound `statistics2-outbound`).

## Scope (576 codes Lima active)
- Posgrado: P68×203, P74×125, P63×65, P90×28, P80×14, P91×1, P49×1 = 437
- Conflicto pregrado sin CODIGO_SUNEDU2 pero con INEI validado: P143×132 (Derecho, INEI 42100042), P05×7 (INEI 41600562) = 139

Scope derivado de Oracle LAMB (vistas de matrícula, semestres 267/279/283, sede LIMA).

## Prerrequisito crítico (bug fix)
El inbound `COALESCE(CODIGO_SUNEDU2,'P'||CODIGO_SUNEDU)` se desplegó con comillas
SIN escapar (`'P'`) dentro del string Groovy single-quoted `baseSelect` del searchScript
→ `groovy.lang.MissingPropertyException: No such property: P` → rompía TODA búsqueda
del resource Estudiantes. Fix: `\'P\'` (commit que acompaña esta ronda). Sin este fix
el canary posgrado falla con HTTP 500 (no es LDAP).

## Uso
```
bash driver-reconcile-bsort2-inei.sh <ADMIN_PASS>
```
Lee `/tmp/masivo_oid_map.tsv` (CODE\tOID\tLC), resumible vía `/tmp/masivo_done.txt`,
log en `/tmp/masivo_progress.log`. HTTP 204/200 = OK; HTTP 250 (partial error benigno
post-clockwork) se valida verificando que `academicProgramIneiCode` materializó.
0 borrowers nuevos, 0 dup-cardnumber (PATCH a description, atributo NO proyectado a Koha
salvo el outbound sort2).

## GAP conocido (ronda futura)
~1,449 estudiantes Lima posgrado activos en 31 P-codes SIN INEI validado en la LT
(P178×196, P171×112, P75×108, P164×89, P159×80, P73×73, P78×71, ...) → Bsort2 vacío
hasta nueva ronda de validación VocBench/INEI 2022. No es bug.
