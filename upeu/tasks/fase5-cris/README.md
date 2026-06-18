# Fase 5 — Provisioning DGI/investigadores al DSpace-CRIS

Artefactos para proyectar la investigacion UPeU (OrgUnits + Person + afiliacion CERIF)
al CRIS `cris.upeu.edu.pe` via MidPoint.

## Estado (2026-06-18)

**Ejecutado (acotado a DGI, controlado):**
- 186 OrgUnit en CRIS con metadata PerúCRIS completa: DGI + 7 CII (`#unidadDeInvestigacionOInnovacion`)
  + 178 lineas (`#lineaDeInvestigacion`), con `organization.parentOrganization`,
  `dspace.entity.type=OrgUnit` (single), `legalName`, `esRaiz`, `ruc`. Upsert por
  `legalName` (los 3 CII minimos pre-existentes se enriquecieron, no se duplicaron).
- 4 investigadores piloto como Person en CRIS (entity.type single, dni, dc.title);
  1 con afiliacion CERIF reltype 5 rightPlace 0 verificada (Itler).

**NO ejecutado (preparado para otra ocasion):**
- Masivo de toda la poblacion (~3.776 investigadores) — `recompute-dgi-investigadores.xml`
  (estado `suspended`) + `driver-masivo-cris.sh`.
- Reconciliar 16 grupos RENACYT <-> 7 CII.

## Componentes nuevos en el modelo (commit fase 5 DGI)

| OID | Objeto | Rol |
|---|---|---|
| `bdfe5f18-99f1-437b-80e6-ccffb52215ad` | AR-CRIS-OrgUnit | construction kind=generic intent=orgUnit; gate research-center/line/DGI. Espejo de AR-CRIS-Person. |
| `c4e8f1a2-9b03-4d57-8e62-1a4f7c0d9e35` | AR-CRIS-Person | construction kind=account intent=person; gate RENACYT/research-center. |

## Orden de ejecucion del masivo (cuando se decida)

1. Suspender Entra daily/hourly + Koha cleanup (ver cabecera del XML).
2. Resource CRIS `proposed` -> `active` (PATCH `?options=raw`).
3. **OrgUnits primero**, en orden jerarquico (institucion -> facultades -> DGI -> CII -> lineas):
   `driver-masivo-cris.sh ORGUNIT <user> <pass> <oids_ordenados>`.
4. Materializar afiliaciones persona->CII (reconciliar inbound `investigadores-afiliacion`
   8c4f1a36) si aun no estan como assignment.
5. **Personas**: `driver-masivo-cris.sh PERSON <user> <pass> <oids_users>`.
6. Verificar en CRIS (matches por DNI=1, entity.type single, CERIF reltype 5 rightPlace 0).
7. Resource CRIS -> `proposed`. Reanudar tareas Entra/Koha.

## Lecciones (aplican al blueprint SciBack)

- El outbound del objectType orgUnit/person debe leer del `focus` directamente, NO de
  un `<source>`: el binding `input` no se expone fiablemente en construction outbound
  (`No such property: input`).
- Scripts que leen `focus.identifier` (solo en OrgType) deben guardarse con
  `instanceof OrgType` — el lens puede evaluar la condicion de un inducement con un
  foco UserType (persona afiliada al OrgType portador del AR) -> `No such property:
  identifier for UserType`.
- HTTP 240/250 del connector ScriptedREST = exito-con-ruido (shadow dead). Verificar
  el dato en el CRIS, no el codigo HTTP. Idempotente por legalName/dni.
