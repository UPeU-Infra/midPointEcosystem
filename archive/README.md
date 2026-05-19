# `archive/` — Material histórico (NO aplicar a PROD)

**Fecha:** 2026-05-19 (consolidación)

Este directorio contiene material preservado por **valor histórico/forense** pero que **NO debe re-importarse en PROD**.

## Contenido

### `previous/`
Material legacy ya existente antes de la consolidación 2026-05-19:
- `initial-objects/` — schemas e users de demo descartados.
- `resources-ldap-legacy/` — OpenLDAP legacy (configs Docker, dump pre-2026).
- `DEPRECATED-extension-upeu-person-v3.1.xsd` — extension XSD pre-namespace canónico.
- `DEPRECATED-schema-object-upeu-person-v3.1.xml` — schema object obsoleto (superseded por `urn:sciback:midpoint:person` + `urn:upeu:midpoint:local`).
- `resource-msgraph-legacy.xml` — Entra ID legacy (superseded por `UPEU-EntraID-Graph`).
- `resource-academico-legacy.xml` — testing CSV antiguo.
- `legacy-ms_entraid-README.md` — doc del entra-id legacy.

### `backups-2026-05/`
Snapshots forenses **críticos** preservados del repo padre `SciBack/midpoint/audit/`:
- `resource-trabajadores-v2-{pre,post}-schemaScript-fix-prod-*.xml` — pre/post fix histórico en PROD.
- `resource-trabajadores-v2-post-schema-and-sql-fix-prod-*.xml`.
- `schema-v3.0-current.xml` — snapshot del schema v3.0 deprecated.
- `legacy-UserTemplate-UPEU-*.xml` — template anterior al `UserTemplate-Person-Base`.
- `2026-05-11/` — audit org hierarchy + schemaType prod snapshots.

> Los ~25 audit XMLs restantes del repo padre (`legacy-deletes/`, `*v2-pre-fix*`, `*current*`, etc.) **NO se preservaron** por baja densidad informativa.

### `specs/`
Specs ClaudeFlow ya **completadas y superseded**:
- `fix-resources-oracle-v2-scripts/` — superseded por v3 (vigente en `upeu/resources/oracle-lamb/`).

### `connector-keycloak-http/`
Conector Java ConnId `pe.upeu.connector.keycloak-http v1.0.0` archivado por **decisión doctrinal 2026-05-11**: la arquitectura final es MidPoint→OpenLDAP←Keycloak (User Federation), **NO** push directo MidPoint→Keycloak.

Se preserva código por historial. **NO instalar en PROD.**

### `infra/`
Configs históricas (FreeRADIUS) — pendientes para Fase posterior.

## Política de archivo

- Cualquier XML aquí lleva nombre con prefijo `DEPRECATED-` o sufijo `-legacy` o vive en subdirectorio que ya lo marca como histórico.
- **Nunca importar archivos de `archive/` a MidPoint en PROD.** Si necesitas algo de aquí, refactoriza al naming canónico y promueve a `canonical/` o `upeu/`.
- Borrado periódico: cada 12 meses re-evaluar si los snapshots forenses siguen siendo necesarios.
