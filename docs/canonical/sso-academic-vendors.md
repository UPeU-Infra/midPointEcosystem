# SSO Académico — Mapeo Schema canónico → SAML eduPerson para vendors

> # ⛔ EL PASO 3 DE ESTE DISEÑO ESTÁ DESCARTADO (ADR-058, 17-jul-2026)
>
> Este documento es **el diseño de la Fase 13** y describe la cadena `MidPoint → OpenLDAP → **Keycloak User Federation** → protocol mappers SAML → vendor`. **El eslabón "Keycloak User Federation" ya no existe**: [ADR-058](../../../../../sciback/sciback-core-docs/docs/architecture/adrs/058-keycloak-solo-autentica.md) prohíbe federar LDAP en Keycloak. Keycloak solo autentica.
>
> **La Fase 13 se queda sin diseño. Es un coste asumido conscientemente, no un descuido.**
>
> **Si has llegado aquí para retomar la Fase 13, lee esto antes de tocar Keycloak.** El camino corto es poner `enabled=true` en la federación y seis mappers, y aparentará funcionar en una demo. **No lo hagas**, por tres razones:
>
> 1. **No funcionaba.** Estuvo encendida hasta julio 2026 y entregaba el claim `epuid` a **2 de las 32** personas que realmente entran. La causa —los espacios de username disjuntos: LDAP importa carnés sin `@`, el IdP crea correos con `@`, intersección **0**— no la arregla la federación.
> 2. **Falla en silencio.** Un claim ausente no da error: da string vacío. 14 clientes del realm llevan meses recibiendo vacíos sin que nadie se enterara. Una app que lee LDAP y no encuentra la entrada **falla y se ve**.
> 3. **Son dos problemas distintos.** La aserción SAML a un vendor externo no se resuelve metiendo atributos en el JWT del Keycloak que autentica a toda la universidad.
>
> **Lo que sigue vigente de este documento:** los pasos 1 y 2 (Oracle LAMB → MidPoint → OpenLDAP con mapeos eduPerson/SCHAC) y **todo el mapeo de atributos por vendor**, que es el trabajo de valor y sigue siendo necesario. Lo que hay que rediseñar es **quién emite la aserción**. Opciones a evaluar, ninguna decidida: (a) IdP/proxy SAML dedicado a vendors alimentado del LDAP, **fuera** del Keycloak institucional; (b) Shibboleth IdP separado (la herramienta natural para eduGAIN); (c) reabrir el ADR-058 con datos. Si la conclusión es federar, **eso supersede el ADR-058 y se escribe** — no se hace con un cambio de configuración.

> **Contexto histórico (2026-06-06, ya no vigente)**: Keycloak UPeU (192.168.12.88, realm `upeu`) actúa como IdP SAML 2.0 para federar el acceso a bases de datos científicas (Scopus, WoS, EBSCO, ScienceDirect, etc.). MidPoint 4.10.2 **provisiona los atributos enriquecidos a OpenLDAP HA** (Identity Cache N-Way Multimaster: Node1 192.168.15.168:389 + Node2 192.168.15.169:389, 37K+ entradas), y ~~Keycloak lee esos atributos vía **User Federation LDAP**~~ → **descartado por ADR-058** — no hay conector directo MidPoint→Keycloak (decisión arquitectural 2026-05-11, el conector HTTP custom fue archivado; **sigue vigente**). Este documento mapea el schema canónico a los atributos eduPerson que cada vendor espera.

## Resumen ejecutivo

El schema canónico (`urn:sciback:midpoint:person` + overlay `urn:upeu:midpoint:local`) **ya cubre los atributos fuente** que requieren los vendors académicos. La cadena de valor es:

1. **Inbound desde Oracle LAMB** → atributos en MidPoint (affiliation, faculty, campus, programa) — OPERATIVO
2. **Outbound desde MidPoint → OpenLDAP HA** (Identity Cache) con mapeos a eduPerson/SCHAC — OPERATIVO (37K+ sombras LDAP)
3. ~~**Keycloak User Federation** lee atributos del OpenLDAP — ACTIVA~~ → 🔴 **DESCARTADO (ADR-058).** Apagada el 13-jul-2026, no se vuelve a encender
4. ~~**Protocol mappers SAML** en Keycloak exponen esos atributos como eduPerson en SAML responses — PENDIENTE (Fase 13)~~ → 🔴 **SIN DISEÑO (ADR-058).** El scope `academic-databases-eduperson` (11 mappers) existe en el realm pero **no está asignado a ningún cliente**; se queda así

**Estado actual (17-jul-2026):** Los pasos **1 y 2 están operativos** y siguen siendo el camino correcto. Los **pasos 3 y 4 están descartados por [ADR-058](../../../../../sciback/sciback-core-docs/docs/architecture/adrs/058-keycloak-solo-autentica.md)**: la cadena se corta en el OpenLDAP, y quien necesite los datos los lee de ahí con bind propio. **La emisión de aserciones eduPerson a vendors necesita un componente nuevo, aún sin diseñar** — no este Keycloak.

Sigue pendiente y **sigue siendo necesario**: completar los mapeos eduPerson derivados (ePPN, ePSA, `eduPersonAffiliation`, `schacHomeOrganization`) en el **outbound MidPoint→LDAP**. Ese trabajo no depende de Keycloak y es prerrequisito de cualquier rediseño de la Fase 13.

**Arquitectura sin conector MidPoint→Keycloak** — decisión 2026-05-11, **sigue vigente**: no hay conector directo.

⛔ **Pero el flujo SÍ se revirtió (ADR-058, 2026-07-17).** Esta línea decía *"no se revierte. El flujo es MidPoint→OpenLDAP←Keycloak(User Federation)→SAML→Vendor"*. **Ese flujo ya no existe**: no se federa LDAP en Keycloak. El flujo de datos es **MidPoint→OpenLDAP→app** (bind propio); Keycloak solo autentica. **El tramo `→SAML→Vendor` queda sin diseño** (Fase 13, coste asumido) — ver el aviso al inicio de este documento y [`ADR-058`](../../../../../sciback/sciback-core-docs/docs/architecture/adrs/058-keycloak-solo-autentica.md).

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

## Cálculo del eduPersonScopedAffiliation desde archetype

**Mapeo de valores** (derivado desde archetype MidPoint, no desde `primaryAffiliationCode` — atributo deprecado):

```groovy
// Outbound mapping MidPoint → OpenLDAP (atributo eduPersonScopedAffiliation)
// Fuente: archetype del foco (structural archetype único por usuario)
def archetype = focus.archetypeRef?.oid

switch (archetype) {
    case 'c93083ca-...':  // archetype-user-employee-faculty
        return ['faculty@upeu.edu.pe', 'employee@upeu.edu.pe', 'member@upeu.edu.pe']
    case '3037fbd2-...':  // archetype-user-student
        return ['student@upeu.edu.pe', 'member@upeu.edu.pe']
    case '6460facf-...':  // archetype-user-employee-staff
        return ['staff@upeu.edu.pe', 'employee@upeu.edu.pe', 'member@upeu.edu.pe']
    case '87552943-...':  // archetype-user-alumni
        return ['alum@upeu.edu.pe', 'member@upeu.edu.pe']
    default:
        return ['affiliate@upeu.edu.pe']
}
```

### Variante con scope por sede (para EBSCO multi-sede)

```groovy
// Derivado de parentOrgRef → OrgType con archetype org-campus
def campus = midpoint.findOrg(focus.parentOrgRef, 'campus')?.identifier
// → 'C-LIM' | 'C-JUL' | 'C-TPP'

def scopeMap = ['C-LIM': 'lima.upeu.edu.pe', 'C-JUL': 'juliaca.upeu.edu.pe', 'C-TPP': 'tarapoto.upeu.edu.pe']
def scope = scopeMap[campus] ?: 'upeu.edu.pe'

return "${role}@${scope}"
// → "student@lima.upeu.edu.pe"
```

## Estado actual de integración por vendor (2026-06-06)

| Vendor | Estado SSO | Bloqueante |
|---|---|---|
| Scopus (Elsevier) | Pendiente configuración SP | Protocol mappers SAML sin ePPN/ePSA aún |
| Web of Science (Clarivate) | Pendiente | Idem |
| EBSCOhost | Pendiente | Idem |
| ProQuest | Pendiente | Idem |
| JSTOR | Pendiente | Idem |
| IEEE Xplore | Pendiente | Idem |
| AccessMedicina (McGraw-Hill) | Pendiente | Idem |

**Prerrequisito para todos:** completar los outbound mappings eduPerson en Resource LDAP + configurar Client Scope SAML en Keycloak (Fase 13).

## Gap analysis — qué falta (estado 2026-06-06)

| Gap | Solución | Esfuerzo | Bloqueante |
|---|---|---|---|
| Outbound mappings `eduPersonAffiliation`, `ePPN`, `ePSA`, `schacHomeOrganization` en Resource LDAP | Agregar atributos al schemaHandling outbound del resource LDAP | 1 día | — |
| Protocol mappers SAML en Client Scope Keycloak | Configurar Client Scope `academic-databases-eduperson` en Keycloak (Fase 13.1) | 1 día | Outbound LDAP |
| Registrar SPs de cada vendor en Keycloak | 1 client SAML por vendor | 2-4h por vendor | — |
| Documentar diccionario de atributos UPeU oficial | Doc referencia para negociaciones con vendors | 1 día | — |

**Total estimado para tener atributos llenos en SAML responses**: 3-5 días.

## Arquitectura de provisionamiento (estado 2026-06-06)

```
Oracle LAMB (fuente de verdad, solo lectura — 192.168.13.9:1521/UPEU)
   │ JDBC directo — 6 resources activos (Trabajadores, Estudiantes, Egresados,
   │                                      Grados, Org, Posiciones)
   ▼
MidPoint 4.10.2 (192.168.15.166:8080) — 50K+ usuarios
   │ inbound mappings → schema canónico
   │ - archetype estructural único (student/faculty/staff/alumni)
   │ - campus/faculty desde OrgType (parentOrgRef) → 199 orgs tipificadas
   │ - academicProgram, studentCycle desde LAMB Estudiantes
   │ - RBAC Fase 7 completa: ~70+ roles (ARs/BRs/MOFs/GOVs), SoD policies
   │
   │ outbound → OpenLDAP HA Identity Cache (Resource LDAP activo)
   ▼
OpenLDAP HA Identity Cache
   Node1: 192.168.15.168:389  ─── N-Way Multimaster ───  Node2: 192.168.15.169:389
   37K+ entradas; replicacion bidireccional verificada
   │ User Federation LDAP (Keycloak lee en tiempo real)
   ▼
Keycloak 26.7.0 (AWS 18.218.108.85, realm upeu)   ← el on-prem .88 quedó retirado (caído 7-jul)
   │ User Federation LDAP: ACTIVA → lee de OpenLDAP Node1
   │ Client Scope SAML "academic-databases-eduperson"
   │ PENDIENTE Fase 13: protocol mappers eduPerson desde atributos LDAP
   ▼
SAML Response a vendor (PENDIENTE Fase 13 — SP registration + mappers)
   │ urn:oid:1.3.6.1.4.1.5923.1.1.1.6 = jsanchez@upeu.edu.pe       (ePPN)
   │ urn:oid:1.3.6.1.4.1.5923.1.1.1.9 = faculty@upeu.edu.pe        (ePSA)
   │ urn:oid:1.3.6.1.4.1.5923.1.1.1.4 = Facultad de Ingeniería     (orgUnitDN)
   │ ...
   ▼
Vendor (Scopus, WoS, EBSCO, ScienceDirect, etc.)
```

**NO hay Resource MidPoint→Keycloak** — decisión arquitectural 2026-05-11. El conector HTTP custom `pe.upeu.connector.keycloak-http v1.0.0` fue archivado. MidPoint solo escribe en OpenLDAP; Keycloak lee de OpenLDAP.

**Entra ID UPeU**: Resource activo en modo READ-ONLY (50K+ shadows, 21K LINKED / 28K UNMATCHED). Write bloqueado hasta Fase 12 (permisos Graph API pendientes con David Urquizo).

**Koha ILS**: 19,721 borrowers activos, conector v1.3.10, provisioning outbound activo desde MidPoint.

## Próximos pasos para SSO vendedores académicos (Fase 13)

1. **Completar outbound mappings eduPerson en Resource LDAP**: agregar atributos `eduPersonPrincipalName`, `eduPersonScopedAffiliation`, `eduPersonAffiliation`, `schacHomeOrganization`, `eduPersonOrgUnitDN` al outbound del Resource LDAP-IdentityCache-UPeU. Los valores se derivan desde archetype + parentOrgRef.
2. **Configurar Client Scope SAML en Keycloak**: mapear los atributos LDAP a URN OIDs eduPerson en el Client Scope `academic-databases-eduperson`. Uno por vendor como Client SAML separado.
3. **Registrar SPs de cada vendor**: obtener metadata SAML de Scopus, WoS, EBSCO, ProQuest. Configurar en Keycloak como SAML clients.
4. **Validar con SAMLtest.id**: verificar que los atributos llegan correctamente antes de conectar a vendors reales.
5. **Configurar atributos COUNTER**: `upeuFaculty`, `upeuProgram`, `upeuCampus` para reporting de uso por facultad/sede.

## Documentos relacionados

- [eduperson-reference.md](eduperson-reference.md) — Diccionario canónico de atributos eduPerson
- [../ARCHITECTURE.md](../ARCHITECTURE.md) — Arquitectura completa del sistema IGA
- [../runbooks/keycloak-ldap-federation.md](../runbooks/keycloak-ldap-federation.md) — Runbook Keycloak User Federation
- [../runbooks/openldap-ha-replication.md](../runbooks/openldap-ha-replication.md) — Runbook OpenLDAP HA N-Way Multimaster
