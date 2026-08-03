# Cleanup dual-archetype — jubilados alumni + employee-staff (2026-05-29)

## Problema
54 jubilados (motivoCese=jubilacion, primaryAffiliation=alum, lifecycleState=active)
quedaron con 2 archetypes estructurales por residuo de las tasks bootstrap (commit 6c8a19c):
- archetype-user-alumni        87552943-9600-493b-88ca-74b7d3ba93e4 (correcto)
- archetype-user-employee-staff 6460facf-3abf-4851-966e-0c95aa1a6c46 (residuo a remover)

MidPoint solo admite UN archetype estructural; el template fallaba con
"only a single one is supported".

## Solución ejecutada
Se removió el assignment DIRECTO al archetype employee-staff (no inducido) vía REST PATCH
(modificationType=delete, path=assignment, value con targetRef=6460facf) sobre cada uno de
los 54 usuarios. Enfoque preferido sobre task `single` por ser idempotente, verificable por
usuario y evitar la problemática de scheduling Quartz de tasks single vía REST.

El XML `task-cleanup-dual-staff-alumni.xml` queda como referencia del equivalente declarativo
(iterativeScripting + unassign), no fue el método de ejecución final.

## Resultado
- Backup: tag git `backup-pre-cleanup-dual-archetype-2026-05-29` + pg_dump m_assignment/m_ref_archetype
- Filtro matcheó exactamente 54
- Post-cleanup: dual-archetype alumni+employee-staff = 0
- Cada usuario quedó con archetype alumni único + primaryAffiliation=alum, lifecycleState=active
