# SSO Académico — Mapeo Schema v2.3 → SAML eduPerson para vendors

> **Contexto nuevo (2026-05-08)**: el proyecto SciBack "SSO Académico" usa Keycloak como IdP SAML 2.0 para federar el acceso a bases de datos científicas (Scopus, WoS, EBSCO, ScienceDirect, etc.). MidPoint UPeU es la **fuente de atributos enriquecidos** que Keycloak expone vía SAML a los vendors. Este documento mapea el schema v2.3 actual a los atributos eduPerson estándar que cada vendor espera.

## Resumen ejecutivo

El schema v2.3 (`urn:upeu:midpoint:person`) **ya cubre el 90%** de los atributos que requieren los vendors académicos. Solo se necesitan:

1. **Outbound mappings** desde MidPoint → Keycloak (provisionar atributos al user en Keycloak)
2. **Protocol mappers SAML** en Keycloak (exponer esos atributos como eduPerson en SAML responses)
3. **Cálculo derivado** de 2-3 atributos eduPerson que no existen literal en el schema (`eduPersonScopedAffiliation`, `eduPersonTargetedID`)

**No requiere modificación del schema XSD ni nuevos ComplexTypes.**

## Mapeo completo: Schema v2.3 → eduPerson SAML

### Atributos críticos (autenticación + autorización vendor)

| eduPerson SAML | URN OID | Source en schema v2.3 | Cálculo necesario |
|---|---|---|---|
| `eduPersonPrincipalName` (ePPN) | `urn:oid:1.3.6.1.4.1.5923.1.1.1.6` | `name` (UserType) | Concatenar `name + "@upeu.edu.pe"` si no incluye dominio |
| `eduPersonScopedAffiliation` (ePSA) | `urn:oid:1.3.6.1.4.1.5923.1.1.1.9` | `extension/primaryAffiliationCode` (AffiliationDataType) | **DERIVAR**: `primaryAffiliationCode + "@upeu.edu.pe"` (con scope por sede opcional) |
| `eduPersonAffiliation` | `urn:oid:1.3.6.1.4.1.5923.1.1.1.1` | `extension/primaryAffiliationCode` | Sin scope |
| `mail` | `urn:oid:0.9.2342.19200300.100.1.3` | `emailAddress` (UserType) | Directo |
| `displayName` | `urn:oid:2.16.840.1.113730.3.1.241` | `fullName` (UserType) | Directo o `givenName + " " + familyName` |
| `eduPersonTargetedID` (ePTID) | `urn:oid:1.3.6.1.4.1.5923.1.1.1.10` | (calculado por Keycloak) | Hash anonimizado por SP |

### Atributos para reportes COUNTER (segmentación de uso)

| eduPerson SAML | URN OID | Source en schema v2.3 |
|---|---|---|
| `eduPersonOrgUnitDN` | `urn:oid:1.3.6.1.4.1.5923.1.1.1.4` | `extension/faculty` (AcademicStatusType) |
| `departmentNumber` | `urn:oid:2.16.840.1.113730.3.1.2` | `extension/academicProgram` (AcademicStatusType) |
| `o` (organizationName) | `urn:oid:2.5.4.10` | constante: `"Universidad Peruana Unión"` |
| `ou` (organizationalUnit) | `urn:oid:2.5.4.11` | `extension/campus` (AffiliationDataType) |
| `l` (localityName) | `urn:oid:2.5.4.7` | `extension/campus` mapeado a ciudad |
| `schacHomeOrganization` | `urn:oid:1.3.6.1.4.1.25178.1.2.9` | constante: `"upeu.edu.pe"` |
| `schacHomeOrganizationType` | `urn:oid:1.3.6.1.4.1.25178.1.2.10` | constante: `"urn:schac:homeOrganizationType:int:university"` |
| `eduPersonEntitlement` | `urn:oid:1.3.6.1.4.1.5923.1.1.1.7` | derivado de `extension/academicPhase` para casos especiales |

### Atributos UPeU custom (algunos vendors los aceptan)

| Custom SAML attribute | Source en schema v2.3 | Vendor que lo usa |
|---|---|---|
| `upeuFaculty` | `extension/faculty` | EBSCO (reportes) |
| `upeuProgram` | `extension/academicProgram` | EBSCO, ProQuest |
| `upeuCampus` | `extension/campus` | EBSCO (3 sedes) |
| `upeuAcademicPhase` | `extension/academicPhase` | Vendors que diferencian pre/posgrado |
| `upeuOrcid` | `extension/orcid` (FederatedIdentityType) | Annual Reviews, Springer |

## Cálculo del eduPersonScopedAffiliation desde primaryAffiliationCode

**Mapeo de valores**:

```groovy
// Pseudocódigo del outbound mapping MidPoint → Keycloak
def affil = user.extension.primaryAffiliationCode

switch (affil) {
    case 'DOCENTE_TC':
    case 'DOCENTE_TP':
        return 'faculty@upeu.edu.pe'
    case 'ESTUDIANTE_PRE':
    case 'ESTUDIANTE_POS':
        return 'student@upeu.edu.pe'
    case 'ADMIN':
    case 'TRABAJADOR':
        return 'staff@upeu.edu.pe'
    case 'EGRESADO':
        return 'alum@upeu.edu.pe'
    default:
        return 'member@upeu.edu.pe'
}
```

### Variante con scope por sede (para EBSCO multi-sede)

```groovy
def affil = user.extension.primaryAffiliationCode
def campus = user.extension.campus  // 'LIMA' | 'TARAPOTO' | 'JULIACA'

def role = mapAffil(affil)  // faculty | student | staff
def scope = campus ? "${campus.toLowerCase()}.upeu.edu.pe" : "upeu.edu.pe"

return "${role}@${scope}"
// → "student@tarapoto.upeu.edu.pe"
```

## Gap analysis — qué falta vs schema v2.3

| Gap | Solución | Esfuerzo |
|---|---|---|
| Mapeo `primaryAffiliationCode` → eduPerson roles | Outbound mapping con switch (script) | 1 día |
| Atributo derivado `eduPersonScopedAffiliation` con scope por sede | Script en outbound MidPoint o mapper Keycloak | 1 día |
| Provisionar todos estos atributos a Keycloak (resource Keycloak) | Configurar resource MidPoint→Keycloak con outbound | 2 días |
| Emitir como SAML attributes con URN OIDs correctos | Configurar Client Scope SAML en Keycloak | 1 día |
| Documentar diccionario de atributos institucional | Doc oficial UPeU | 2 días |

**Total estimado para tener atributos llenos en SAML responses**: 1-2 semanas.

## Arquitectura de provisionamiento

```
Lamb Academic (Oracle)
   │ vistas IGA_V_PERSONAS, etc.
   ▼
MidPoint UPeU (4.9.5)
   │ inbound mappings → schema v2.3
   │ - primaryAffiliationCode (calculado de TIPO_PERSONA)
   │ - faculty, academicProgram, campus, academicPhase
   │ - institutionalIdCard, externalSystemId
   │
   │ outbound mapping → Keycloak resource
   ▼
Keycloak prod (identity.upeu.edu.pe)
   │ user attributes:
   │ - primaryAffiliation
   │ - faculty
   │ - academicProgram
   │ - campus
   │ - academicPhase
   │
   │ Client Scope SAML "academic-databases-eduperson"
   │ con mappers que exponen los atributos como eduPerson SAML
   ▼
SAML Response a vendor
   │ urn:oid:1.3.6.1.4.1.5923.1.1.1.6 = jsanchez@upeu.edu.pe
   │ urn:oid:1.3.6.1.4.1.5923.1.1.1.9 = faculty@lima.upeu.edu.pe
   │ urn:oid:1.3.6.1.4.1.5923.1.1.1.4 = Facultad de Ingeniería
   │ ...
   ▼
Vendor (Scopus, WoS, EBSCO, ScienceDirect, etc.)
```

## Recurso Keycloak necesario en MidPoint

**Falta crear**: un Resource MidPoint que provisiona users a Keycloak con los atributos enriquecidos. Hoy MidPoint UPeU no tiene este resource (los users en Keycloak son locales/manuales según diagnóstico 2026-05-08).

### Especificación del Resource Keycloak

```
Resource: Keycloak UPeU Producción
  Connector: ConnIdRESTConnector (o connector Keycloak custom)
  URL: https://identity.upeu.edu.pe/admin/realms/upeu
  Auth: client_credentials (service account)

  Schema:
    __ACCOUNT__:
      __NAME__         ← name (UserType)  [PRIMARY]
      email           ← emailAddress
      firstName       ← givenName
      lastName        ← familyName
      enabled         ← lifecycleState == "active"
      attributes:
        primaryAffiliation     ← extension/primaryAffiliationCode
        primaryAffiliationName ← extension/primaryAffiliationName
        faculty                ← extension/faculty
        academicProgram        ← extension/academicProgram
        campus                 ← extension/campus
        academicPhase          ← extension/academicPhase
        institutionalIdCard    ← extension/institutionalIdCard
        orcid                  ← extension/orcid
        scopedAffiliation      ← (calculated: see Groovy script above)
```

## Próximos pasos

1. **Definir formalmente los valores válidos de `primaryAffiliationCode`** con DTI/CRAI UPeU
2. **Crear Resource MidPoint → Keycloak** con outbound mappings
3. **Crear Client Scope SAML en Keycloak** con todos los mappers eduPerson
4. **Validar con un user real** que los atributos llegan correctamente a un SP de prueba (SAMLTest.id)
5. **Documentar el "diccionario de atributos UPeU"** como referencia oficial institucional

## Documentos relacionados

- [README-extension-guia.md](../schema/README-extension-guia.md) — Schema v2.3 completo
- [MAPPING-PLAN-lamb-to-extension.md](../schema/MAPPING-PLAN-lamb-to-extension.md) — Lamb → MidPoint inbound mappings
- [perfiles-identidad.md](perfiles-identidad.md) — Perfiles de identidad UPeU
- Producto SciBack canónico: `~/obsidian/sciback/proyectos/sso-academico/`
- Inventario CRAI UPeU 2026: `~/proyectos/upeu/unified-access-upeu/docs/inventario-crai-2026.md`

## Hallazgo crítico (2026-05-08)

El diagnóstico del Keycloak prod reveló:
- 20 users totales (mayoría locales sin federationLink)
- Mappers AD CRAI/ACADEMIC son mínimos (solo username, firstName, lastName, email)
- Scope OIDC `upeu` ya tiene mappers para los atributos enriquecidos, pero **los atributos nunca se llenan** porque ningún resource los provisiona
- MidPoint prod NO está conectado al Keycloak prod todavía

**Conclusión**: el schema v2.3 está perfecto y MidPoint puede ser la fuente. Lo que falta es el **Resource Keycloak en MidPoint** + el **Client Scope SAML en Keycloak**.
