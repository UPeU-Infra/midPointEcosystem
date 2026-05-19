# Implementation Summary: Fix searchScript / inbounds resources Oracle LAMB v2

**Spec:** doc/specs/fix-resources-oracle-v2-scripts/02-specification.md
**Tasks:** doc/specs/fix-resources-oracle-v2-scripts/03-tasks.md
**Created:** 2026-05-12
**Last Updated:** 2026-05-12

## Progress

| Status | Count |
|--------|-------|
| ✅ Completed | 3 |
| 🔄 In Progress | 0 |
| ⏳ Pending | 6 |
| **Total** | **9** |

Ola 1 (`trabajadores-v2`) completa. Ola 2 (`estudiantes-v2` + `egresados-v2`) y cierre/doc **pausados por decisión del usuario** ("parar aquí por hoy") y por el gate de `lifecycleState`.

**Sesión 2 (2026-05-13) — Trabajados fuera de spec formal:**
- Fix ORDER BY en `trabajadores-v2`: reemplazado `REGEXP_LIKE('^[0-9]{8}$')` por `CASE ID_TIPODOCUMENTO` basado en catálogo `ELISEO.TIPO_DOCUMENTO`. Desplegado a PROD (versión 110→111). Test connection 8/8 success.
- Fusión de 3 pares de focuses duplicados (una persona = un focus, ISO 24760): Alberto Sanchez (10867326+9610165), Veronica Chura (44303558+200720272), Freddy Colque (24893998+9810042). Patrón aplicado: preservar focus trabajador (IIA primaria HR), guardar código alternativo en `personalNumber`, eliminar focus secundario. Usuarios: 25→22.

## Session Log

### Session 1 — 2026-05-12

**Tasks completadas:**
- Task 1.1 — Reescribir `searchScript` de `trabajadores-v2` al patrón Tirasa (`return List<Map>`, sin `handler`/`ConnectorObjectBuilder`/`SearchResult`). Query: dedup `RN=1` + `WHERE ROWNUM=1` externo (límite temporal piloto) + filtro permanente del `COD_APS` centinela `00000000` (`NOT REGEXP_LIKE(TRIM(COD_APS),'^0+$')` + NOT NULL). SQL pasado a triple comilla simple para evitar interpolación GString del `$` del regex.
- Task 1.2 — Deploy a PROD. **El flujo difirió del plan:** PROD no tiene clon del repo de XMLs → deploy por REST `PUT /resources/6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21` (solo el bloque `searchScript`, sobre el XML de PROD con password cifrado). Resource versión 74→78. Contenedor NO reiniciado.
- Task 1.3 — Validación: test connection `success` end-to-end; import task one-off `success`, progress 1, 0 fatal_error; 1 shadow (`ee74543c-…`, `00016576`); focus UserType `095f4c8e-…` con `name`/`employeeNumber`=`00016576`, `givenName`=`ELISEO`, `familyName`=`SANCHEZ CHAVEZ` (AS-IS), `extension/upeu3:taxId`=`urn:schac:personalUniqueID:pe:DNI:PE:481651ESCCV6`, `extension/upeu3:hireDate`=`2015-02-01`, `activation/administrativeStatus`=`enabled`, `assignment` a `archetype-user-employee-staff` (`6460facf-…`), birthright `BR-Admin-Area` por template (AR roles sin construction wired → 0 proyección). **0 provisioning a Entra ID / Koha** (verificado: shadows de esos resources intactos, createTimestamp 2026-04-16). Limpiados 50 shadows huérfanos `00000000` + 2 import tasks de prueba.

**Archivos modificados:**
- `resources/oracle-lamb-trabajadores-v2.xml` — `<gen:searchScript>` reescrito. Commits en `SciBack/midpoint` rama `claude/festive-almeida-9f9cf3`: `0214095`, `fb2d6bf`, `65d911c` (pusheados).
- En PROD: resource `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21` versión 78 (vía REST).
- `doc/specs/fix-resources-oracle-v2-scripts/03-tasks.md` — statuses actualizados.

**Notas / decisiones:**
- Correlación: el resource correlaciona por `name` (= `COD_APS`, identificador inmutable).
- Aclaración: `extension/upeu3:taxId` lleva `NUM_DOCUMENTO` tal cual viene de la vista (`481651ESCCV6` en el caso piloto — valor no-numérico, así está en Oracle); el inbound solo antepone el prefijo URN SCHAC. Es lo especificado.
- El `WHERE ROWNUM=1` se queda en el XML, comentado como temporal; la futura spec de recon masiva debe quitar **solo** ese `ROWNUM=1` (conservar `RN=1` y el filtro del centinela).

## Known Issues

1. **Gate `lifecycleState`:** el focus importado quedó con `lifecycleState` vacío (= `active`), no `draft`. Ningún object template setea `lifecycleState`; la única lógica de lifecycle es `leaver-disable-on-terminationdate` → `activation/administrativeStatus`. La spec ordena detenerse aquí. **Decisión del usuario pendiente:** (a) añadir mapping `→ lifecycleState` en `UserTemplate-Person-Base` antes de Ola 2 (tarea de diseño nueva, consultar `iga-canonical-standards`), o (b) aceptar `active` (inocuo hoy: 0 provisioning) y tratar lifecycle en spec aparte. Usuario eligió **parar por hoy** y decidir después.
2. **Repo de XMLs:** los `resources/*.xml` están en `SciBack/midpoint`, no en `UPeU-Infra/midPointEcosystem` (CLAUDE.md del proyecto dice lo contrario — desfasado). PROD no tiene clon → deploy por REST. Conviene aclarar/actualizar la convención del proyecto.
3. **`estudiantes-v2` / `egresados-v2` sin corregir aún:** mismo bug `handler.handle()` en `searchScript` + 9 variables Groovy de inbounds en minúsculas que deben ser MAYÚSCULAS (Tasks 2.1 y 2.2).
4. **taxId de Veronica y Freddy (trabajadores) aún incorrecto:** el fix del ORDER BY en `trabajadores-v2` corrige el problema hacia el futuro, pero los focuses actuales de Veronica (44303558) y Freddy (24893998) tienen `taxId` con el CUSPP (código AFP) porque se importaron antes del fix. Se corregirá automáticamente en la próxima reconciliación del resource trabajadores-v2 (cuando se reactive el import sin ROWNUM=1).

## Next Steps

- [ ] Decidir el tema `lifecycleState` (gate) — ver Known Issue 1.
- [ ] Reanudar con `/spec:execute doc/specs/fix-resources-oracle-v2-scripts/03-tasks.md` → Tasks 2.1 + 2.2 (`estudiantes-v2` + `egresados-v2`), luego 2.3 deploy, 2.4 validar, 3.1 no-regresión, 3.2 reporte, 4.1 doc.
- [ ] (Spec aparte, futura) recon masiva de trabajadores: quitar `WHERE ROWNUM=1` de `trabajadores-v2`, activar `task-recon-trabajadores-v2` con criterio de batch acotado.
- [ ] Aclarar convención de repo (XMLs en `SciBack/midpoint` vs `midPointEcosystem`) en el CLAUDE.md del proyecto.
