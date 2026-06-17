# Resource DSpace-CRIS UPeU (outbound) — Fase 5

MidPoint como orquestador canónico hacia **DSpace-CRIS** (`https://cris.upeu.edu.pe/server/api`,
DSpace 9.2 / cris-2025.02.00, PerúCRIS v1.1). Provisiona **OrgUnit**, **Person** y la
**afiliación CERIF** persona↔unidad. La producción científica (publicaciones, patentes,
citas) **NO** va por MidPoint — la carga el CRIS desde OpenAlex/CONCYTEC aparte.

## Archivos

| Archivo | Rol |
|---|---|
| `cris-dspace.xml` | Resource MidPoint (OID `3f8b2d61-7c94-4a05-9e3b-6d1f8a2c5e70`), 2 objectTypes: `orgUnit` (OrgType) + `person` (UserType), outbound mappings PerúCRIS. |
| `scripts/CrisClient.groovy` | Helper: auth DSpace (CSRF+JWT), upsert por búsqueda, metadatos PerúCRIS, relaciones CERIF (relationshipType 5, place 0 = principal). |
| `scripts/Test.groovy` | Test Connection (login + root). |
| `scripts/Schema.groovy` | Object classes `orgUnit` / `person`. |
| `scripts/Search.groovy` | Resolución idempotente: OrgUnit por `organization.legalName`; Person por `person.identifier.orcid` → fallback `perucris.person.dni`. |
| `scripts/Create.groovy` | Crea item-entidad + relaciones CERIF (delega upsert si ya existe). |
| `scripts/Update.groovy` | Actualiza item existente + sincroniza afiliaciones. |

## Connector ScriptedREST — PRE-REQUISITO (no instalado en PROD)

PROD solo tiene ScriptedSQL, Koha, MSGraph, LDAP, CSV. Para este resource hace falta el
bundle ConnId **ScriptedREST** (`net.tirasa.connid.bundles.rest`):

1. Descargar `connector-rest-*.jar` (net.tirasa ScriptedREST) y copiar a
   `/opt/midpoint/var/icf-connectors/` en el container `midpoint_server`.
2. Reiniciar MidPoint (o el connector framework) para descubrir el bundle.
3. `GET /connectors` → obtener el OID real del `ScriptedRESTConnector` y reemplazar el
   `<connectorRef>` por-filtro de `cris-dspace.xml` con un `oid=` fijo.
4. Copiar `scripts/*.groovy` a `/opt/midpoint/var/cris-scripts/` en el container.
5. Setear vía REST/UI (NO en el repo): `username`, `password` (admin DSpace de
   `~/.secrets/upeu-dspace-cris.env`), `orgUnitCollectionUuid` (colección OrgUnit del CRIS).

> Alternativa si no se quiere ScriptedREST: compilar un connector Java a medida
> (patrón keycloak-http / koha). ScriptedREST se eligió para no mantener otro repo Java.

## Upsert idempotente (CRIS ya tiene 97 Person + 41 OrgUnit)

- **OrgUnit** → búsqueda Discovery por `organization.legalName` (restringida a `entityType=OrgUnit`).
- **Person** → `person.identifier.orcid`, fallback `perucris.person.dni`.
- Tras el primer create, el **shadow MidPoint guarda el uuid DSpace** (`__UID__`) → idempotente.
- Reconciliar los **16 "grupos" RENACYT** existentes (colgando de carreras) con los **7 Centros CII**
  es una **decisión del usuario** (ver REPORTE / pendientes) — el provisioning no los toca.

## Contrato PerúCRIS emitido (verificado)

- `dspace.entity.type` = `OrgUnit` | `Person` — **UN SOLO valor** (duplicarlo rompe la indexación).
- **OrgUnit**: `organization.legalName`, `organization.parentOrganization` (jerarquía),
  `perucris.orgunit.tiposubunidad`:
  - `#unidadDeInvestigacionOInnovacion` → DGI + 7 Centros CII (archetype `research-center`).
  - `#lineaDeInvestigacion` → líneas (archetype `research-line`).
  - Facultades/carreras → solo `parentOrganization` (sin tiposubunidad).
  - Solo raíz UPeU → `tipoinstitucion #06` + `naturaleza #privada` + `sector #ensenanzaSuperior` + RUC.
  - **NO** `organizationType` (vocab 404).
- **Person**: `dc.title` "Apellidos, Nombres", `person.givenName/familyName/email`,
  `person.identifier.orcid`, `perucris.person.dni`. Colección **Investigadores**
  (`6460c5ef-29d4-45b1-b92b-18ccd057f476`).
- **Afiliación**: relación CERIF `relationshipType=5` (`isOrgUnitOfPerson`/`isPersonOfOrgUnit`),
  repetible; **principal en `leftPlace 0`** (la dependencia laboral actual).

## Validación recomendada (antes de masivo)

Piloto **Charming** (ID_PERSONA 29266, ORCID 0000-0003-1208-9121, uuid Person ya existente
`3e32166c-6e65-446a-80ab-be299a67a94b`): su dependencia laboral activa es **DGI** (área 69) →
afiliación principal (place 0). No tiene fila en `DGI_INVESTIGADOR` (es staff/director DGI),
por lo que el inbound de investigación no le añade Centro CII automáticamente.
