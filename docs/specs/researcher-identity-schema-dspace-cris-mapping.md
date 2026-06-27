# Identidad de Investigador — Schema de extensión + mapeo a DSpace-CRIS

**Estado:** Aplicado en PROD (schema aditivo) · **Fecha:** 2026-06-27
**Schema canónico:** `urn:sciback:midpoint:person` — OID `e800335c-9ca1-4a2d-b4ca-e06f6db42693`
**Archivo:** `canonical/schemas/sciback-person-v1.0.xml` (v1.3)
**DSpace-CRIS destino:** `cris.upeu.edu.pe`
**Skills consultadas:** `iga-canonical-standards`, `midpoint-best-practices`

Este documento es la fuente única del "un solo lenguaje" de identidad de investigador entre
MidPoint (master IGA UPeU) y DSpace-CRIS. Es lo que se lleva al chat de DSpace-CRIS para crear
los metadatafields que faltan y configurar el futuro provisioning MidPoint→DSpace-CRIS.

---

## 0. Decisiones de diseño (validadas contra CERIF, PerúCRIS v1.1 §7.2.4, OpenAIRE Guidelines for CRIS Managers)

### 0.1 "Investigador" NO es sub-entidad — TRES EJES ORTOGONALES

En CERIF/DSpace-CRIS, `Person` es UNA entidad única; las poblaciones se distinguen por
ATRIBUTOS clasificatorios + relación de afiliación, nunca por subclases. Se modelan tres ejes
independientes entre sí:

| Eje | Qué representa | MidPoint | DSpace-CRIS |
|---|---|---|---|
| **1. Afiliación a UPeU** | relación Person↔OrgUnit | `parentOrgRef` / assignment a OrgType | `isPersonOfOrgUnit` / `oairecerif.person.affiliation` |
| **2. Estatus institucional del investigador** | `oficial-dgi` \| `detectado-autoria` \| `externo` (gobernado por DGI) | `sciback:researcherStatus` (multivalor) → `sciback:primaryResearcherStatus` (derivado) | `upeu.person.estatus` (a crear) |
| **3. Calificación RENACYT/CONCYTEC** | código, nivel, condición, CTI Vitae | `sciback:concytecId`, `renacytLevel`, `renacytStatus`, `ctiVitaeId` | `perucris.person.codigorenacyt`, `nivelrenacyt`, `upeu.person.condicionrenacyt` |

Independencia: se puede ser `oficial-dgi` sin RENACYT, o RENACYT sin docencia activa.

### 0.2 El lenguaje único se ancla en el schema **canónico SciBack**, no en uno UPeU paralelo

ORCID, RENACYT (código/nivel/estado), CTI Vitae y DNI **ya existen en PROD** dentro del schema
canónico `urn:sciback:midpoint:person` (no en el overlay `urn:upeu:midpoint:local`). Es lo
correcto: la identidad de investigador es canónica universitaria peruana (toda universidad con
DGI/RENACYT la tiene), no UPeU-específica. Regla "Schema is the law / no duplicar": se REUSAN
los atributos existentes y solo se agrega lo que falta.

### 0.3 `scopusAuthorId` NO se crea en MidPoint

Su IIA es **DSpace-CRIS** (detección por autoría/Scopus): el CRIS ya publica
`person.identifier.scopus-author-id` (cosechable CERIF, ya poblado). Crear `scopusAuthorId` en
MidPoint violaría "una sola IIA por atributo" (iga-canonical §1.3). Si en el futuro MidPoint
necesita el Scopus ID para enrutar provisioning, se trae como **inbound read-only desde el
resource DSpace-CRIS**, no como dato que MidPoint escribe.

### 0.4 `estatusInvestigador` (eje 2) es ATRIBUTO DE EXTENSIÓN multivalor, NO archetype, NO rol

Fundamento (best-practices Evolveum + canónico):

1. **No es estructural.** Un archetype define la naturaleza del objeto (student/faculty/staff…)
   y es de direct assignment único estructural. "Ser investigador" es ortogonal a la afiliación:
   un `faculty` puede ser `oficial-dgi`; un `staff` o externo sin contrato puede ser
   `detectado-autoria`. Meterlo como archetype rompería el modelo de los 18 archetypes activos
   (un usuario tiene UN archetype estructural).
2. **eduPersonAffiliation ya cubre rol/relación.** El estatus de investigador NO está en el
   vocabulario eduPerson de 8 valores → no es afiliación → no va por archetype/rol.
3. **Es dato clasificatorio gobernado, no un permiso.** No otorga accesos por sí mismo (no es PA
   en RBAC). La DGI lo *clasifica*. Si más adelante `oficial-dgi` debe otorgar acceso (ej. módulo
   de proyectos), se resuelve con un business role asignado por `assignmentTargetSearch` que
   filtra por este atributo — patrón canónico, sin hardcodear, sin convertir el dato en estructura.
4. **Gobernanza humana DGI = Reality vs Policy con IIA propia.** El CRIS DETECTA
   (`detectado-autoria`) vía inbound desde el resource DSpace-CRIS; la DGI PROMUEVE
   (`oficial-dgi`) vía lista oficial (inbound strong que gana sobre la detección). Multivalor
   porque un foco puede portar más de un token transitoriamente durante la promoción. El template
   deriva `primaryResearcherStatus` single-value (mismo patrón `affiliations`→`primaryAffiliation`).

### 0.5 `condicionRenacyt` reusa `sciback:renacytStatus` (no se crea atributo nuevo en MidPoint)

`sciback:renacytStatus` ya tiene exactamente esa semántica (estado de vigencia en el padrón).
En DSpace SÍ hay que crear el metadato porque allá no existe (`upeu.person.condicionrenacyt`).

### 0.6 Normalización de vocabularios: en el inbound, no en el schema

Dataset real (`~/proyectos/upeu/calidad-upeu/scripts/renacyt/enriched.csv`): niveles = `I..VII` +
`Investigador Distinguido`; condición = `Activo`. El schema canónico ya define vocabularios
alineados al Reglamento RENACYT 2021 (`DISTINGUIDO | NIVEL_I..NIVEL_VII`, `ACTIVO | ACTIVO_AFILIADO
| NO_ACTIVO | EXCLUIDO`). La normalización (`VII`→`NIVEL_VII`, `Investigador Distinguido`→
`DISTINGUIDO`, `Activo`→`ACTIVO`) se hace en el inbound mapping del resource. El XSD NO se toca por
esto ("datos institucionales se adaptan al canónico, nunca al revés").

---

## 1. ENTREGABLE 1 — Schema de extensión revisado

### 1.A Atributos que YA EXISTEN en PROD (NO TOCAR)

Todos en `UserExtensionType`, schema OID `e800335c-9ca1-4a2d-b4ca-e06f6db42693`,
namespace `urn:sciback:midpoint:person` (prefijo `sciback:`).

| Nombre pedido | Atributo canónico EXISTENTE | Tipo / mult. | Indexed | Alineación eduPerson/SCHAC |
|---|---|---|---|---|
| `dni` | `sciback:identityDocuments` (container; `type='DNI'`, `number`, `verifiedBy='RENIEC'`) | container / 0..n | sí (number) | **SCHAC** `schacPersonalUniqueID` `urn:schac:personalUniqueID:pe:DNI:PE:{dni}`. PII — NO publicar a SPs |
| `orcid` | `sciback:orcid` (`0000-0000-0000-0000`, sin URL) | string / 0..1 | sí | **eduPerson** `eduPersonOrcid` (.1.16), URI `https://orcid.org/{orcid}` |
| `ctiVitaeId` | `sciback:ctiVitaeId` (int del perfil, ej. `161494` = int de `P0NNNNNN`) | string / 0..1 | sí | Interno CONCYTEC |
| `codigoRenacyt` | `sciback:concytecId` (`P0NNNNNN`, ej. `P0130769`) | string / 0..1 | sí | Interno RENACYT (opc. `schacPersonalUniqueCode` si se federa) |
| `nivelRenacyt` | `sciback:renacytLevel` (vocab `DISTINGUIDO|NIVEL_I..NIVEL_VII`) | string / 0..1 | sí | Interno |
| `condicionRenacyt` | `sciback:renacytStatus` (vocab `ACTIVO|ACTIVO_AFILIADO|NO_ACTIVO|EXCLUIDO`) | string / 0..1 | sí | Interno |
| (categoría institucional) | `sciback:researcherCategory` | string / 0..1 | sí | Interno institucional |

`scopusAuthorId`: **no se modela en MidPoint** (IIA = DSpace-CRIS, ver §0.3).

### 1.B Atributos NUEVOS agregados (S7b, S7c) — los únicos 2

Insertados en la sección S7 (INVESTIGACIÓN) tras `researcherCategory`.

```xml
<!-- S7b — ESTATUS INSTITUCIONAL DEL INVESTIGADOR (EJE 2, ortogonal). -->
<xsd:element name="researcherStatus" type="xsd:string" minOccurs="0" maxOccurs="unbounded">
    <xsd:annotation><xsd:appinfo>
        <a:displayName>Estatus institucional de investigador</a:displayName>
        <a:help>Vocabulario controlado: oficial-dgi | detectado-autoria | externo. Eje ortogonal
            a la afiliación eduPerson y a la calificación RENACYT. oficial-dgi lo promueve la DGI
            (lista oficial, IIA strong); detectado-autoria lo detecta el CRIS por autoría/Scopus
            (IIA DSpace-CRIS); externo = coautor sin afiliación contractual. No otorga accesos por
            sí mismo (no es rol); si se requiere acceso, derivar business role vía
            assignmentTargetSearch filtrando este atributo.</a:help>
        <a:indexed>true</a:indexed>
        <a:displayOrder>721</a:displayOrder>
    </xsd:appinfo></xsd:annotation>
</xsd:element>

<!-- S7c — Estatus principal derivado (single). Precedencia oficial-dgi > detectado-autoria > externo. -->
<xsd:element name="primaryResearcherStatus" type="xsd:string" minOccurs="0" maxOccurs="1">
    <xsd:annotation><xsd:appinfo>
        <a:displayName>Estatus de investigador principal (derivado)</a:displayName>
        <a:help>Valor único derivado por el object template desde researcherStatus (precedencia
            oficial-dgi > detectado-autoria > externo). Destino del outbound a DSpace
            (upeu.person.estatus) y de eventuales assignmentTargetSearch. No es IIA directa.</a:help>
        <a:indexed>true</a:indexed>
        <a:displayOrder>722</a:displayOrder>
    </xsd:appinfo></xsd:annotation>
</xsd:element>
```

Cambio **aditivo** (`minOccurs=0`), OID estable, no destructivo. Va en `canonical/` (concepto
canónico, blueprint SciBack), el overlay UPeU no requiere nada nuevo.

---

## 2. ENTREGABLE 2 — Tabla de mapeo definitiva (una fila por atributo)

Prefijo MidPoint: `extension/sciback:*` (namespace `urn:sciback:midpoint:person`).

| # | Atributo MidPoint (canónico) | Metadato DSpace-CRIS | Elemento CERIF / PerúCRIS v1.1 | eduPerson / SCHAC |
|---|---|---|---|---|
| 1 | `sciback:identityDocuments[type=DNI].number` (`dni`) | `perucris.person.dni` | PerúCRIS Identifier type `concytec/terminos#dni` (cosechable CERIF) | **SCHAC** `schacPersonalUniqueID` (`urn:schac:personalUniqueID:pe:DNI:PE:{dni}`) |
| 2 | `sciback:orcid` | `person.identifier.orcid` | CERIF `cfPersId_Class` ORCID (cosechable) | **eduPerson** `eduPersonOrcid` (URI) |
| 3 | *(DSpace-origin)* `person.identifier.scopus-author-id` | `person.identifier.scopus-author-id` | CERIF Scopus Author ID (cosechable) | — (interno; IIA = DSpace-CRIS) |
| 4 | `sciback:ctiVitaeId` | `perucris.person.ctivitae` (si existe; si no, interno) | PerúCRIS perfil interno (NO cosechable) | — |
| 5 | `sciback:concytecId` (`codigoRenacyt`, `P0NNNNNN`) | `perucris.person.codigorenacyt` | PerúCRIS perfil INTERNO (NO cosechable) | (opc.) `schacPersonalUniqueCode` |
| 6 | `sciback:renacytLevel` (`nivelRenacyt`) | `perucris.person.nivelrenacyt` | PerúCRIS perfil INTERNO | — |
| 7 | `sciback:renacytStatus` (`condicionRenacyt`) | **`upeu.person.condicionrenacyt`** (crear, §3) | Interno (no estándar PerúCRIS) | — |
| 8 | *(derivado en outbound, no atributo)* | `perucris.person.urlfichainvestigador` | PerúCRIS perfil INTERNO | — |
| 9 | `sciback:primaryResearcherStatus` (deriva de `researcherStatus` = `estatusInvestigador`) | **`upeu.person.estatus`** (crear, §3) | Interno institucional (clasificación DGI; no estándar PerúCRIS/CERIF) | — (NO es eduPersonAffiliation; eje ortogonal) |
| 10 | Afiliación: `parentOrgRef` / assignment a OrgType (eje 1) | `oairecerif.person.affiliation` / `isPersonOfOrgUnit` | CERIF `cfPers_OrgUnit` / OpenAIRE affiliation (cosechable) | **eduPerson** `eduPersonOrgUnitDN` + **SCHAC** `schacHomeOrganization` |

Notas:
- Filas 3 y 8 no generan atributo nuevo en MidPoint. Scopus es DSpace-origin (inbound si se
  necesita). La URL de ficha RENACYT se compone en el outbound (p. ej. desde `ctiVitaeId`).
- Fila 7: en MidPoint reusa `renacytStatus`; en DSpace se crea el campo.
- Fila 9: el outbound a DSpace emite el derivado single `primaryResearcherStatus`, no el multivalor.

---

## 3. ENTREGABLE 3 — Metadatafields a crear en DSpace-CRIS (schema institucional `upeu`)

No ensuciar `perucris` (perfil nacional normado). Crear schema propio `upeu`
(namespace institucional sugerido `https://upeu.edu.pe/cris/terms`).

### 3.1 `upeu.person.estatus` (eje 2)

| Propiedad | Valor |
|---|---|
| schema | `upeu` |
| element | `person` |
| qualifier | `estatus` |
| field name | `upeu.person.estatus` |
| type / repeatable | text / **no repetible** (recibe el derivado single `primaryResearcherStatus`) |
| vocabulario controlado | `oficial-dgi` \| `detectado-autoria` \| `externo` |
| cosechable CERIF | **NO** (interno institucional) |
| scope note | "Estatus institucional del investigador asignado por la Dirección General de Investigación (DGI). `oficial-dgi`: investigador reconocido en la lista oficial DGI (SINEACE E22/E24, SUNEDU). `detectado-autoria`: persona detectada por el CRIS por autoría/Scopus, pendiente de validación DGI. `externo`: coautor o colaborador sin afiliación contractual con UPeU. Eje ortogonal a la afiliación eduPerson y a la calificación RENACYT. Fuente autoritativa (IIA): MidPoint, derivado de `extension/sciback:researcherStatus`. No determina permisos por sí mismo." |

### 3.2 `upeu.person.condicionrenacyt`

| Propiedad | Valor |
|---|---|
| schema | `upeu` |
| element | `person` |
| qualifier | `condicionrenacyt` |
| field name | `upeu.person.condicionrenacyt` |
| type / repeatable | text / no repetible |
| vocabulario controlado | `ACTIVO` \| `ACTIVO_AFILIADO` \| `NO_ACTIVO` \| `EXCLUIDO` (el padrón usa "Activo" → normalizar a `ACTIVO`) |
| cosechable CERIF | NO (interno) |
| scope note | "Condición/estado de vigencia del investigador en el padrón RENACYT/CONCYTEC. Distinta de `perucris.person.nivelrenacyt` (nivel I–VII / Distinguido). Solo `ACTIVO`/`ACTIVO_AFILIADO` habilitan liderar proyectos y asesorar tesis (Reglamento RENACYT). Fuente autoritativa (IIA): lista anual DGI, vía MidPoint `extension/sciback:renacytStatus`." |

Registro: *Metadata Registry* → registrar schema `upeu` (namespace + short name) → añadir ambos
`metadatafield`. Alternativa backend: `dspace metadata-import` o UI Administración → Metadata Registry.

---

## 4. Pendientes (no parte de este cambio de schema)

- **Resource DSpace-CRIS en MidPoint** (re-crear; el anterior OID `3f8b2d61-7c94-4a05-9e3b-6d1f8a2c5e70`
  fue borrado y provisionaba OrgUnits). Inbound `detectado-autoria` + scopus; outbound de identidad.
- **Inbound lista oficial DGI** → `researcherStatus = oficial-dgi` (strength strong).
- **Object template**: derivación `primaryResearcherStatus` desde `researcherStatus` (precedencia
  `oficial-dgi > detectado-autoria > externo`).
- **Crear los 2 metadatafields** en DSpace-CRIS (§3) — coordinación en el chat de DSpace-CRIS.
