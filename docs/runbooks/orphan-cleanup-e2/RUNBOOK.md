# Orphan-cleanup E2 — bitácora de ejecución (2026-06-03)

## Objetivo
Retraer atributos LABORALES huérfanos (title de cargo, costCenter ID_AREA, email
personal/gmail) pegados en focos student/alum por los inbounds strong del resource
Trabajadores ANTES de estrechar el filtro `ID_ENTIDAD=7124`.

## Fix de raíz (commit d5464f0)
Los 3 mappings E2 (`E2-retract-orphan-title/costCenter/personal-email`) estaban
ARCHIVED por guard insegura: leían `extension/sciback:liveAffiliationWorker` como
`<source>`, que cae en **zero-set transitorio** en recompute focus-driven →
`null==null`=TRUE para trabajadores VIVOS → borraba su title/costCenter reales.

**Guard reescrita:** sin `<source>` (evita evaluación per-valor en zero-set). La
`<condition>` lee el valor PERSISTIDO de `liveAffiliationWorker` vía
`midpoint.getObjectByOid(UserType, focus.oid)` (repo committed) **y** el valor
relativo del foco; retrae SOLO si AMBOS son null. Un trabajador 7124 vivo tiene
`liveAffiliationWorker='faculty'/'staff'` persistido → guard FALSE → datos intactos.
Mappings reactivados (`archived`→`active`). Template PUT OID 855caaca... (HTTP 201).

## Canary doble (GATE)
| Caso | OID | Antes | Después | Veredicto |
|---|---|---|---|---|
| B — worker VIVO faculty 201420147 | 50dc8188 | cc=86, email=emanuelapaza@upeu.edu.pe, title=Jefe de Prácticas, liveWorker=faculty | **TODO INTACTO** | GATE PASS |
| A2 — alum orphan 201421037 | c66fbb62 | cc=86, email=raulzela1@gmail.com, title=Supervisor de Práctica | cc retraído, gmail retraído, title→Egresado | OK |
| A3 — dual student/alum orphan (con shadow LDAP) 9010360 | 4dcfd8ab | cc=7, email=silvia.chire@upeu.edu.pe, title=Coordinador Académico | cc retraído, email institucional INTACTO, title→Estudiante | OK |

## Masivo
- Universo: 1.996 focos active sin `liveAffiliationWorker` con orphan costCenter (1.861) o email no-@upeu (225).
- Método: recompute serializado vía REST PATCH no-op (`description` replace) que dispara el clockwork del foco. `/recompute` da 404 en 4.10; reconcile innecesario (problema focus-side).
- Resultado: ok=1.969 (HTTP 204), err=27 (Koha AlreadyExists 250 / Entra 409 — proyección, el foco igual recomputó). Retry: 9 más ok.
- Heap estable ~6.75 GiB / 10 GiB durante todo el run.

## Invariantes finales
| Métrica | PRE | POST |
|---|---|---|
| orphan costCenter (active, no worker) | 1.861 | **1** |
| orphan email no-@upeu (active, no worker) | 225 | **0** |
| live workers total (ext.216 no-null) | 3.965 | 3.965 (sin pérdida) |
| live workers SIN costCenter | 3 | 3 (mismos pre-existentes, no dañados) |

**GATE de seguridad: 0 trabajadores vivos perdieron title/costCenter/email.**

## Residual único (NO bloqueante, fuera de scope E2)
`001261673` (OID 7844b5da) — cc=712, title=Conductor. NO se limpió porque tiene
**dos shadows Entra ID duplicados** (2f11c057...) → conflicto de proyección en lens
context (409) aborta el commit del foco. Es una inconsistencia de shadow pre-existente,
no del guard E2. Además sus 3 liveAffiliation son null con lifecycleState=active
(anomalía aparte). Requiere shadow-dedup Entra ID separado. El guard E2 funciona; la
proyección lo bloquea.

## Reutilizable SciBack
Patrón "guard que lee valor PERSISTIDO (repo) en lugar de `<source>` relativo" para
mappings RETRACTIVOS en object templates → inmune al zero-set transitorio del
clockwork focus-driven. Aplicable a cualquier retracción autoritativa condicionada
por un item single-source IIA-poblado.
