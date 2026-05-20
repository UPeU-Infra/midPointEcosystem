# SSO Académico — Mapeo Schema canónico → SAML eduPerson para vendors

> **Contexto (2026-05-20)**: Keycloak UPeU (192.168.12.88, realm `upeu`) actúa como IdP SAML 2.0 para federar el acceso a bases de datos científicas (Scopus, WoS, EBSCO, ScienceDirect, etc.). MidPoint 4.10.2 **provisiona los atributos enriquecidos a OpenLDAP** (Identity Cache, 192.168.15.168:389), y Keycloak lee esos atributos vía **User Federation LDAP** — no hay conector directo MidPoint→Keycloak. Este documento mapea el schema canónico a los atributos eduPerson que cada vendor espera.

## Resumen ejecutivo

El schema canónico (`urn:sciback:midpoint:person` + overlay `urn:upeu:midpoint:local`) **ya cubre los atributos fuente** que requieren los vendors académicos. La cadena de valor es:

1. **Inbound desde Oracle LAMB** → atributos en MidPoint (affiliation, faculty, campus, programa)
2. **Outbound desde MidPoint → OpenLDAP** (Identity Cache) con mapeos a eduPerson/SCHAC (pendiente F5)
3. **Keycloak User Federation** lee atributos del OpenLDAP
4. **Protocol mappers SAML** en Keycloak exponen esos atributos como eduPerson en SAML responses

**Estado actual (2026-05-20):** el paso 1 está completo (37.491 usuarios en OpenLDAP). Los mapeos eduPerson en el outbound LDAP (paso 2) están **pendientes** — Keycloak ve los usuarios pero aún no los atributos enriquecidos.

**No requiere conector MidPoint→Keycloak** — la arquitectura es MidPoint→OpenLDAP←Keycloak.

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

## Arquitectura de provisionamiento (estado 2026-05-20)

```
Oracle LAMB (fuente de verdad, solo lectura — 192.168.13.9:1521/UPEU)
   │ JDBC directo — 4 resources activos
   ▼
MidPoint 4.10.2 (192.168.15.166:8080)
   │ inbound mappings → schema canónico
   │ - affiliation desde archetype (student/faculty/staff/alumni)
   │ - campus/faculty desde OrgType (parentOrgRef)
   │ - academicProgram, studentCycle desde LAMB Estudiantes v3
   │
   │ outbound → OpenLDAP Identity Cache (Resource LDAP activo)
   ▼
OpenLDAP Identity Cache (192.168.15.168:389) — 37.491 entradas
   │ User Federation LDAP (Keycloak lee en tiempo real)
   ▼
Keycloak 26.6.1 (192.168.12.88, realm upeu)
   │ Client Scope SAML "academic-databases-eduperson"
   │ PENDIENTE: mappers eduPerson desde LDAP attributes
   ▼
SAML Response a vendor
   │ urn:oid:1.3.6.1.4.1.5923.1.1.1.6 = jsanchez@upeu.edu.pe       (ePPN)
   │ urn:oid:1.3.6.1.4.1.5923.1.1.1.9 = faculty@upeu.edu.pe        (ePSA)
   │ urn:oid:1.3.6.1.4.1.5923.1.1.1.4 = Facultad de Ingeniería     (orgUnitDN)
   │ ...
   ▼
Vendor (Scopus, WoS, EBSCO, ScienceDirect, etc.)
```

**NO hay Resource MidPoint→Keycloak** — decisión arquitectural 2026-05-11. El conector HTTP custom `pe.upeu.connector.keycloak-http v1.0.0` fue archivado. MidPoint solo escribe en OpenLDAP; Keycloak lee de OpenLDAP.

## Próximos pasos (desde 2026-05-20)

1. **F5 — Outbound mappings eduPerson en Resource LDAP**: agregar atributos `ePPN`, `ePSA`, `eduPersonAffiliation`, `schacHomeOrganization` al outbound del Resource LDAP-IdentityCache-UPeU
2. **Configurar mappers SAML en Client Scope Keycloak**: mapear los atributos LDAP a URN OIDs eduPerson en el Client Scope `academic-databases-eduperson`
3. **Validar con un user real**: verificar que los atributos llegan correctamente a un SP de prueba (SAMLTest.id)
4. **Documentar el "diccionario de atributos UPeU"**: referencia oficial institucional para negociaciones con vendors

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
