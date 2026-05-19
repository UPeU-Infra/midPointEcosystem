# UPeU IGA — Análisis Canónico y Plan de Replanteo

**Versión:** 2026-05-11
**Autor:** midpoint-expert (consultando `iga-canonical-standards` v2026-05 + `midpoint-best-practices`)
**Alcance:** sistema IGA UPeU sobre MidPoint 4.9.5, base canónica reusable para SciBack (`sciback-iga-blueprint`)

---

## 1. Decisión doctrinal

### 1.1 Principio rector

**El modelo canónico se diseña primero desde los estándares internacionales. Los datos institucionales (Oracle LAMB, MDM MOISES, nómina ELISEO) se mapean al modelo canónico vía transformations. NUNCA al revés.** (Cf. `iga-canonical-standards` §11 regla 1).

Esta decisión es **doctrinal**, no técnica: todo el código y XML producido para UPeU debe ser refactorizable para servir como esqueleto de cualquier otra universidad peruana. La especificidad UPeU vive en (a) overlays parametrizados, (b) mappings de inbound desde Oracle LAMB, (c) catálogos de sedes/facultades; jamás en el schema canónico ni en los arquetipos.

### 1.2 Estándares adoptados

| Estándar | Versión | Uso en este proyecto | Cita |
|---|---|---|---|
| ISO/IEC 24760-1/2/3 | 2025 | Terminología (identity, attribute, IIA, lifecycle) | `iga-canonical-standards` §1 |
| NIST SP 800-63-3 | rev 3 | IAL/AAL/FAL para casos de uso UPeU | `iga-canonical-standards` §2 |
| eduPerson | 202208 v4.4.0 | Atributos federados (ePPN, ePSA, eduPersonUniqueId, eduPersonAffiliation) | §3 |
| SCHAC | 1.6.0 | Atributos académicos (homeOrg, personalUniqueID DNI, personalUniqueCode) | §4 |
| SCIM 2.0 | RFC 7643/7644 | Modelo user core + Enterprise extension | §5 |
| NIST RBAC | INCITS 359-2012 (R2022) | Business/Application/Entitlement, SoD | §6 |
| ISO/IEC 27001:2022 | 2022 | Controles A.5.15–A.5.18, A.8.2–A.8.3 | §7 |
| REFEDS R&S | 1.3 | Liberación atributos a vendors académicos (Scopus, EBSCO, WoS) | §8.1 |

### 1.3 Reglas de oro adoptadas (vinculantes)

1. **Schema first, always** — extender solo lo que no exista en core ni en eduPerson/SCHAC/SCIM (Cf. `midpoint-best-practices` §6 regla 1).
2. **Una IIA por atributo** — documentar explícitamente en matriz IIA (§2.5).
3. **eduPerson + SCHAC obligatorios para SSO académico** (R&S/vendors).
4. **ePPN no es identificador de correlación inter-SP** — usar `eduPersonUniqueId`.
5. **Publicar ePSA, no ePPN ni grupos** (privacidad).
6. **Lifecycle desde la IIA** (Oracle LAMB), no `administrativeStatus` manual.
7. **Cascada Business → Application → Entitlement vía inducements** (no assignments).
8. **Archetype apenas se crea el objeto**, no después.
9. **Identifiers inmutables y persistentes** (`employeeNumber`, `studentID`) sobre human-friendly.
10. **DNI peruano va en `schacPersonalUniqueID` con formato URN**, no plano.
11. **No inventar atributos custom si el estándar tiene un namespace** registrable en REFEDS.
12. **Privilegios NO heredan por jerarquía org** — agregar inducement explícito.

---

## 2. Modelo canónico propuesto

### 2.1 Identidades — 8 arquetipos canónicos

Cf. `iga-canonical-standards` §10.1 + `midpoint-best-practices` §3.3 (un structural archetype por objeto).

| # | Archetype canónico | Subtipos UPeU (auxiliary o roles) | `eduPersonAffiliation` | IIA primaria (vista Oracle) | Criterio de pertenencia |
|---|---|---|---|---|---|
| 1 | **`student`** | undergrad, grad (maestría), doctoral | `student`, `member` | `DAVID.VW_PERSONA_ALUMNO` + `DAVID.VW_FICHA_MATRICULA` | Matrícula activa en `ACAD_MATRICULA` ciclo vigente |
| 2 | **`employee-faculty`** | docente ordinario (auxiliar/asociado/principal), docente contratado, docente visitante | `faculty`, `employee`, `member` | `MOISES.TRABAJADOR_PUESTO` + `ENOC.CAT_DOCENTE` | Contrato vigente con cargo docente en `APS_CARGO` |
| 3 | **`employee-staff`** | administrativo (jefatura, especialista, asistente), técnico, ejecutivo | `staff`, `employee`, `member` | `ELISEO.VW_APS_EMPLEADO` + `MOISES.TRABAJADOR_PUESTO` | Contrato vigente con cargo no-docente |
| 4 | **`affiliate-partner-institution`** | Colegio Unión, Clínica Good Hope, ISTAT, AGTU, convenios internacionales adventistas | `affiliate`, `member` | `MOISES.PERSONA` con `ORG_SEDE` ∈ {5,6} o convenio | Persona con vínculo formal NO contractual UPeU |
| 5 | **`affiliate-researcher`** | investigador visitante, CONCYTEC externo, proyecto sin contrato | `affiliate` | Alta manual + workflow aprobación | Proyecto/convenio con fecha fin |
| 6 | **`alumni`** | egresado pregrado, egresado posgrado | `alum` | `DAVID.VW_PERSONA_EGRESADO` | Lifecycle transition desde `student` con grado conferido |
| 7 | **`contractor`** | proveedor de servicios, consultor externo, prestador honorarios | `affiliate` | Alta manual (ERP futuro) | Contrato civil con fin explícito y `validTo` |
| 8 | **`service-account`** | cuentas técnicas (apps, daemons, integraciones) | (no aplica — no es persona) | Alta manual ITSM | Sin auth interactiva; solo API keys / cert |

**Reglas operacionales:**

- **Structural archetype único:** un usuario tiene exactamente UNO de los 8. Transiciones (estudiante → egresado → trabajador) son lifecycle events que **cambian archetype** (operación destructiva supervisada). Cf. `midpoint-best-practices` §3.5.
- **Subtipos NO son archetypes auxiliares.** Se modelan como **business roles** asignados, no como auxiliary archetypes (soporte UI limitado en 4.9, Cf. §3.3).
- **`eduPersonAffiliation` se calcula** desde el archetype + lifecycle, no se almacena denormalizado. `member` se asserta independientemente.
- **Doble afiliación legítima** (docente que estudia un doctorado): el archetype primario es `employee-faculty`; la condición de estudiante se modela vía **business role** `Estudiante-Doctorado` que añade `student` a `eduPersonAffiliation` por outbound mapping condicional.

**Gap con estado actual:** El proyecto actual tiene 4 arquetipos (`StudentType`, `ProfessorType`, `AdministrativeStaffType`, `TechnicalStaffType`). Faltan 4: `affiliate-partner-institution`, `affiliate-researcher`, `alumni`, `contractor`, `service-account`. Naming actual no canónico (terminados en `Type`, redundante).

### 2.2 Organizational tree canónico

Cf. `iga-canonical-standards` §10.2 + `midpoint-best-practices` §5.

**Jerarquía canónica universal:**

```
institution (raíz)
  └─ campus / site
       └─ faculty
            └─ department
                 └─ section (opcional, solo donde tenga sentido)
```

**Mapeo UPeU sobre tablas ELISEO/JOSUE:**

| Nivel canónico | Tabla origen | Identifier (persistente) | Ejemplo UPeU |
|---|---|---|---|
| `institution` | constante | `UPEU` | "Universidad Peruana Unión" |
| `campus` | `ELISEO.ORG_SEDE` filas {1,2,3} | `ORG_SEDE.cod` | Lima(1), Juliaca(2), Tarapoto(5) |
| `partner-institution` | `ELISEO.ORG_SEDE` filas {4,5,6} | `ORG_SEDE.cod` | ISTAT(8), Clínica GH(0), AGTU(9) |
| `faculty` | `ELISEO.ORG_DEPENDENCIA` tipo `MI` = FACULTAD | `ORG_DEPENDENCIA.id` | Facultad de Ingeniería |
| `department` | `ELISEO.ORG_ESCUELA_PROFESIONAL` + `ELISEO.ORG_DEPENDENCIA` tipo `MI` = UNIDAD/ÁREA | identificador estable | Escuela Prof. Ing. Sistemas |
| `section` | `ELISEO.ORG_SEDE_AREA` cuando aplique | identificador estable | (selectivo, no todas) |

**Decisión sobre instituciones afines (ISTAT/Clínica Good Hope/AGTU):**

- **NO son campus de UPeU** — son entidades legales separadas que comparten infraestructura/identidad.
- Se modelan como org tipo **`partner-institution`** colgando de la raíz `institution` (UPeU), **no debajo de un campus**.
- Sus usuarios reciben archetype `affiliate-partner-institution` y NO heredan `member`/`employee` de UPeU.
- `schacHomeOrganization` para esos usuarios: provisional `upeu.edu.pe` (no tienen FQDN federado propio) marcado vía `eduPersonAnalyticsTag` para distinguir analítica.

**Decisión sobre tipos de dependencia (SU=sustantivo, MI=misional):**

- `SU` (Investigación, Bienestar, Biblioteca, Centro Pre, etc.) → modelados como `department` colgando de `institution` directamente (transversales).
- `MI` (FACULTAD, ESCUELA PROFESIONAL, UNIDAD, etc.) → cada uno mapea al nivel canónico correspondiente.
- **Tipo `ORG_NIVEL_GESTION` (Estratégico/Táctico/Operativo) NO se modela en el árbol.** Se conserva como atributo de extensión `upeu:managementLevel` en el `OrgType` (sólo para reporting). Cf. `iga-canonical-standards` §11 regla 2.

**Archetypes para OrgType (siguiendo `midpoint-best-practices` §5.3):**
- `institution`, `campus`, `faculty`, `department`, `partner-institution`, `project`, `role-catalog`

**Convención de naming `OrgType.name` (Cf. `midpoint-best-practices` §5.2):**
- Campus: `C-LIM`, `C-JUL`, `C-TPP` (3 letras consistente con sigla `ELISEO.ORG_SEDE.SIGLA`)
- Faculty: `F-ING`, `F-CCS`, `F-TEO`
- Department: `D-ING-SIS`, `D-ING-AMB`
- Partner: `P-CGH`, `P-ISTAT`, `P-AGTU`
- Project: `PRJ-CONCYTEC-2026-001`

`identifier` separado de `name` (id estable de Oracle); `displayName` legible al usuario.

### 2.3 RBAC canónico

Cf. `iga-canonical-standards` §6 + `midpoint-best-practices` §2.

**Cascada canónica (regla de oro):**

```
User ──[assignment]──► Business Role
                          └─[inducement]─► Application Role
                                              └─[inducement]─► Entitlement (LDAP/AD group)
```

**Business Roles — lista mínima viable (catálogo canónico):**

| Business Role | Asignación | Contiene (inducements) | Ejemplo |
|---|---|---|---|
| `BR-Docente-TC` | Auto desde archetype `employee-faculty` + condición HR | M365-Faculty-A3, Koha-Staff, VPN-Docentes, OJS-Reviewer | Docente tiempo completo |
| `BR-Docente-TP` | Auto desde archetype `employee-faculty` + condición | M365-Faculty-A1, Koha-Patron | Docente tiempo parcial |
| `BR-Estudiante-Pregrado` | Auto desde archetype `student` + ciclo<=10 | M365-Student-A1, Koha-Patron-Student, Wi-Fi | |
| `BR-Estudiante-Posgrado` | Auto desde archetype `student` + tipo programa | + acceso bases científicas premium | |
| `BR-Estudiante-Doctorado` | Auto desde archetype `student` + tipo programa | + DSpace-Author, OJS-Author | |
| `BR-Admin-Area` | Auto desde `employee-staff` + `costCenter` (paramétrico) | Variable según área | Roles paramétricos (Cf. `midpoint-best-practices` §2.5) |
| `BR-Bibliotecario` | Manual + aprobación jefatura | Koha-Librarian, DSpace-Editor | |
| `BR-Investigador` | Auto si tiene `orcid` + `eduPersonAffiliation=faculty` | DSpace-Submitter, OJS-Reviewer, acceso WoS/Scopus | |
| `BR-Egresado` | Auto desde archetype `alumni` | Email-Alumni, OPAC-externo | |
| `BR-Decano` | Manual + aprobación rectoral | Heredado vía `relation=manager` del OrgType faculty | Cf. `midpoint-best-practices` §5.5 |
| `BR-Visitante-Investigacion` | Manual con `validTo` | Wi-Fi-Visitante, Email-Visitante, acceso restringido bases | |

**Application Roles — uno por grupo destino (bottom-up):**

| App Role | Resource | Construction | Entitlement equivalente |
|---|---|---|---|
| `AR-M365-Student-A1` | Microsoft Entra ID + M365 | Licencia A1 for Students (gratis EDU) + Exchange + Teams + OneDrive | Entra ID licenseAssignment |
| `AR-M365-Faculty-A1` | Microsoft Entra ID + M365 | Licencia A1 for Faculty (gratis EDU) + Exchange + Teams | Entra ID licenseAssignment |
| `AR-M365-Faculty-A3` | Microsoft Entra ID + M365 | Licencia A3 (pagada) — Exchange + Teams + Office desktop + Intune | Entra ID licenseAssignment |
| `AR-M365-Staff-A3` | Microsoft Entra ID + M365 | Licencia A3 (pagada) personal administrativo | Entra ID licenseAssignment |
| `AR-EntraID-Group-Docentes` | Microsoft Entra ID | Membresía en grupo `grp-upeu-docentes` | Entra ID group |
| `AR-EntraID-Group-Estudiantes` | Microsoft Entra ID | Membresía en grupo `grp-upeu-estudiantes` | Entra ID group |
| `AR-EntraID-Group-Staff` | Microsoft Entra ID | Membresía en grupo `grp-upeu-staff` | Entra ID group |
| ~~`AR-AD-*`~~ | ~~Active Directory~~ | **OUT del alcance** — decisión 2026-05-11. AD UPeU actual no se usa globalmente, queda fuera. AD nuevo solo si Entra ID gobernado por MidPoint resulta insuficiente (decisión Fase 12). |  |
| `AR-Koha-Patron-Student` | Koha | categoría ST | tabla categories |
| `AR-Koha-Patron-Faculty` | Koha | categoría DC | |
| `AR-Koha-Librarian` | Koha | staff con permisos | |
| `AR-DSpace-Submitter` | DSpace | grupo "Submitters" | LDAP group |
| `AR-DSpace-Editor` | DSpace | grupo "Editors" | |
| `AR-OJS-Reviewer` | OJS | role reviewer en revista | |
| `AR-Indico-User` | Indico | grupo registered | LDAP group |
| `AR-Keycloak-realm-upeu` | Keycloak | rol realm | mapeo SAML (atributos vienen de OpenLDAP) |
| `AR-VPN-Docentes` | FreeRADIUS | grupo VPN | flat-file |

**Nota — Sistema académico interno:** UPeU NO usa Moodle. El sistema académico es **UPeU Lamb** (ERP propio, sobre Oracle 11g, schemas MOISES/DAVID/ELISEO/JOSUE/ENOC). Lamb es **fuente autoritativa** (IIA), NO destino de provisioning — los usuarios YA existen ahí. La docencia en línea se hace en **Google Classroom** (SaaS externo) integrado vía URLs registradas en `DAVID.ACAD_CARGA_PLAN_CLASSROOM` (79K registros) — pero las cuentas Google probablemente son personales de docentes, no gobernadas (ver DU-007). El stack de licenciamiento institucional es **Microsoft 365** (A1/A3), gobernado en Fase 12 cuando MidPoint esté maduro.

**Nota — AD UPeU (decisión 2026-05-11):** El AD actual (`192.168.13.150`, `lim.upeu.edu.pe`) NO se usa globalmente y está mal estructurado. Queda **OUT del alcance**. La decisión sobre construir AD nuevo se difiere a Fase 12: si Entra ID gobernado por MidPoint cubre todas las necesidades de directorio, NO se construye AD nuevo. Hasta entonces el destino principal de identidades canónicas es **OpenLDAP HA** (consumido por Keycloak vía User Federation) + **Entra ID UPeU** (read-only en Fases 1-11, write en Fase 12).

**Entitlements:** existen como `<entitlement>` en `schemaHandling` del resource (Cf. `midpoint-best-practices` §5.8). **Nunca se asignan directamente a usuarios.**

**Qué hacer con `ELISEO.LAMB_ROL` (656 roles):**

1. **NO importar masivamente.** Esos roles son del sistema legacy Lamb (autorización aplicativa interna a Lamb), no equivalentes 1:1 a application roles canónicos.
2. **Mantener Lamb como resource separado** con su propio set de application roles MidPoint (uno por rol Lamb que se decida gobernar). Probablemente <50 reales después de role mining.
3. **Role mining (Fase 4 First Steps Methodology, Cf. `midpoint-best-practices` §9):** análisis de `ELISEO.LAMB_USUARIOS` × `LAMB_ROL` para identificar patrones recurrentes → derivar business roles candidatos.
4. Filtrar roles obsoletos: nombres con `*` prefix (`*CAJERO PAGADOR`), TEST, duplicados.
5. **Ningún rol Lamb se asigna directamente a un usuario MidPoint.** Va vía inducement desde business roles.

**SoD canónica obligatoria (Cf. `iga-canonical-standards` §6.3):**

- Static SoD: `BR-Admin-Nomina` ⊥ `BR-Aprobador-Pagos` (no asignables al mismo user simultáneamente) → `policyRule` con `exclusion`.
- Static SoD: `BR-Auditor-Interno` ⊥ cualquier rol operativo del mismo dominio auditado.
- Dynamic SoD: revisión post-implementación con role mining real.

### 2.4 Mappings de atributos UPeU → canónico

Cf. `iga-canonical-standards` §3, §4, §5 + `midpoint-best-practices` §1.4.

Tabla exhaustiva del schema extension v2.3 actual vs canónico:

| Atributo actual v2.3 | Equivalente canónico | Decisión | Justificación | Fuente Oracle |
|---|---|---|---|---|
| **DemographicsType** | | | | |
| `birthDate` | `schacDateOfBirth` (OID `.3`) | **REEMPLAZAR** por SCHAC | Estándar académico | `MOISES.PERSONA_NATURAL.fec_nacimiento` |
| `gender` | (no estándar) | **MANTENER en extension** como `upeu:gender` ISO 5218 | No hay atributo canónico universal | `MOISES.PERSONA_NATURAL.gender` |
| `country` | `schacCountryOfCitizenship` (OID `.5`) ISO 3166 | **REEMPLAZAR** por SCHAC | Estándar | `MOISES.PERSONA_NATURAL` |
| `province` | (no estándar) | **MANTENER** `upeu:province` | Local | |
| `streetAddress` | SCIM `addresses[].streetAddress` | **REEMPLAZAR** por SCIM | Core SCIM | |
| **ContactInfoType** | | | | |
| `secondaryMail` | SCIM `emails[type=other]` | **REEMPLAZAR** | SCIM multivalor estándar | |
| `phoneNumberAlt` | SCIM `phoneNumbers[type=other]` | **REEMPLAZAR** | SCIM | |
| `personalWeb` | (no estándar) | **MANTENER** `upeu:personalWeb` | | |
| **EmploymentDataType** | | | | |
| `hireDate` | (extension) | **MANTENER** como `upeu:hireDate` | No estándar core | `MOISES.TRABAJADOR.fec_ingreso` |
| `terminationDate` | (extension; dispara `validTo` y archive) | **MANTENER** como `upeu:terminationDate` + mapping a `activation/validTo` | Lógica negocio | `MOISES.TRABAJADOR.fec_cese` |
| **AffiliationDataType** | | | | |
| `primaryAffiliationCode` | `eduPersonPrimaryAffiliation` | **REEMPLAZAR** por eduPerson core (vocabulario 8 valores) | Estándar federación | calculado desde archetype |
| `primaryAffiliationName` | n/a | **ELIMINAR** | Redundante, derivable del code | |
| `languageSkills` | (no estándar) | **MANTENER** `upeu:languageSkills` | | |
| `campus` | (no estándar) | **REEMPLAZAR** por `parentOrgRef` a OrgType campus | Modelar como org, no atributo | `ELISEO.ORG_SEDE` |
| `employeeType` (extension) | SCIM `userType` o core `employeeType` MidPoint | **ELIMINAR** del extension, usar core MidPoint | Duplicado | `MOISES.TRABAJADOR_PUESTO` |
| **AcademicStatusType** | | | | |
| `studentCycle` | (no estándar) | **MANTENER** `upeu:studentCycle` | Específico régimen peruano | `DAVID.ACAD_MATRICULA` |
| `academicProgram` | (no estándar) | **MANTENER** `upeu:academicProgram` (nombre) | | `DAVID.ACAD_PROGRAMA_ESTUDIO` |
| `academicProgramCode` | `schacPersonalUniqueCode` con type=`studentProgram` | **TRANSFORMAR** a URN SCHAC en outbound | Estándar SCHAC para códigos institucionales | |
| `alumniStatus` | derivable de archetype `alumni` + `eduPersonAffiliation=alum` | **ELIMINAR** | Redundante con archetype | |
| `studyModality` | (no estándar) | **MANTENER** `upeu:studyModality` | | |
| **FederatedIdentityType** | | | | |
| `orcid` | `eduPersonOrcid` (OID `.16`) URI | **REEMPLAZAR** por eduPerson | Estándar; transformar a URI `https://orcid.org/{id}` | manual / `MOISES.PERSONA` |
| **UniqueIdentifiersType** | | | | |
| `taxId` (DNI) | `schacPersonalUniqueID` URN `urn:schac:personalUniqueID:pe:DNI:PE:{value}` | **TRANSFORMAR** a URN SCHAC | Estándar | `MOISES.PERSONA_NATURAL.dni` |
| `institutionalIdCard` | `schacPersonalUniqueCode` URN `urn:schac:personalUniqueCode:pe:institutionalCard:upeu.edu.pe:{value}` | **TRANSFORMAR** a URN SCHAC | Estándar | |
| `universityIdCard` | redundante con `institutionalIdCard` | **ELIMINAR** | Consolidar | |
| `externalSystemId` | core `employeeNumber` (MidPoint) o `extension` (estudiantes) | **REEMPLAZAR** docentes por core `employeeNumber`; estudiantes mantener en `upeu:studentID` | Core SCIM/MidPoint para empleados | `MOISES.TRABAJADOR.cod_trabajador` / `DAVID.ACAD_*` |

**Atributos canónicos NUEVOS que faltan agregar:**

| Atributo | Estándar | Calculado en MidPoint | Justificación |
|---|---|---|---|
| `eduPersonPrincipalName` (ePPN) | eduPerson `.1.6` | `{employeeNumber|studentID}@upeu.edu.pe` | Federación |
| `eduPersonUniqueId` | eduPerson `.1.13` | `{personalID-stable}@upeu.edu.pe` | Identificador omnidireccional NO reasignable |
| `eduPersonAffiliation` (multi) | eduPerson `.1.1` | derivado de archetype + lifecycle | Federación obligatorio |
| `eduPersonScopedAffiliation` | eduPerson `.1.9` | `{affiliation}@upeu.edu.pe` | R&S obligatorio |
| `eduPersonAssurance` (multi) | eduPerson `.1.11` URI | constante según método proofing (RENIEC = nivel 3) | LoA federation |
| `eduPersonPrincipalNamePrior` | eduPerson `.1.12` | histórico ePPN | Rename hell mitigation |
| `eduPersonEntitlement` (multi) | eduPerson `.1.7` URI | desde business roles asignados | Acceso recursos federados |
| `schacHomeOrganization` | SCHAC `.9` | constante `upeu.edu.pe` | R&S obligatorio |
| `schacHomeOrganizationType` | SCHAC `.10` | `urn:schac:homeOrganizationType:eu:higherEducationalInstitution` (provisional hasta registrar `pe:`) | Federación |
| `schacUserStatus` | SCHAC `.19` | `urn:schac:userStatus:upeu.edu.pe:{state}` | Lifecycle federado |
| `schacExpiryDate` | SCHAC `.17` | derivado de `activation/validTo` | Account expiration |

### 2.5 Identity Information Authority (matriz IIA)

Cf. `iga-canonical-standards` §1.3 (cada atributo tiene UNA IIA).

| Atributo canónico | IIA | Vista/tabla Oracle exacta | Mecanismo MidPoint | Strength |
|---|---|---|---|---|
| `name` (username MidPoint) | MidPoint (calculado) | object template + iteration | computed | `strong` |
| `employeeNumber` | MOISES (HR) | `MOISES.TRABAJADOR.cod_trabajador` | Resource JDBC inbound | `strong` |
| `extension/upeu:studentID` | DAVID (SIS) | `DAVID.VW_DATOS_IDENTIDAD_USUARIO` | Resource JDBC inbound | `strong` |
| `givenName`, `familyName` | RENIEC (preferida) / MOISES (fallback) | RENIEC API / `MOISES.PERSONA_NATURAL` | Resource REST RENIEC → fallback JDBC | `strong` |
| `fullName` | MidPoint (calculado) | `basic.concatName(givenName, familyName)` | object template | `strong` |
| `schacPersonalUniqueID` (DNI) | RENIEC / MOISES | `MOISES.PERSONA_NATURAL.dni` | inbound + validación checksum DNI | `strong` |
| `schacDateOfBirth` | RENIEC / MOISES | `MOISES.PERSONA_NATURAL.fec_nacimiento` | inbound | `strong` |
| `emailAddress` | MidPoint (computed) | `{name}@upeu.edu.pe` o `@upeualumni.edu.pe` según archetype | object template | `strong` |
| `extension/upeu:secondaryMail` | el usuario (self-service) | n/a | UI self-service | `weak` |
| `activation/administrativeStatus` | MOISES + DAVID (derivado de lifecycle) | n/a | derivado de lifecycle | `strong` |
| `lifecycleState` | MOISES + DAVID | derivado de `terminationDate` / `matriculaActiva` | inbound condicional | `strong` |
| `parentOrgRef` (org) | ELISEO (estructura organizacional) | `ELISEO.VW_APS_EMPLEADO` + `ELISEO.ORG_*` | inbound `assignmentTargetSearch` | `strong` |
| `extension/upeu:academicProgram` | DAVID | `DAVID.ACAD_PROGRAMA_ESTUDIO` | inbound | `strong` |
| `extension/upeu:studentCycle` | DAVID | `DAVID.ACAD_MATRICULA` | inbound | `strong` |
| `eduPersonAffiliation` | MidPoint (derivado) | calculado desde archetype + roles | outbound a LDAP cache | `strong` |
| `eduPersonScopedAffiliation` | MidPoint (derivado) | calculado | outbound a LDAP cache | `strong` |
| `eduPersonPrincipalName` | MidPoint (calculado) | `{employeeNumber\|studentID}@upeu.edu.pe` | object template | `strong` |
| `eduPersonUniqueId` | MidPoint (calculado) | hash estable inmutable | object template | `strong` |
| `eduPersonOrcid` | el investigador (self-service + Moises) | `MOISES.PERSONA` (cuando esté) | inbound + UI | `normal` |
| `extension/upeu:campus` | ELISEO | `ELISEO.ORG_SEDE` | inbound como `parentOrgRef` | `strong` |
| `schacHomeOrganization` | constante | `upeu.edu.pe` | object template literal | `strong` |
| `extension/upeu:institutionalIdCard` | UPeU Carné Universitario (sistema) | (pendiente verificar tabla) | inbound | `strong` |
| `credentials/password` | usuario (self-service) | n/a | UI / Keycloak | n/a |

---

## 3. Gap analysis: actual vs canónico

### 3.1 Decisiones del proyecto vs estándares

Leyenda: ✅ correcto · ⚠️ aceptable · ❌ corregir.

| Decisión actual | Canónico | Estado | Impacto | Acción |
|---|---|---|---|---|
| Schema v2.3 con namespace `urn:upeu:midpoint:person` | Namespace propio OK | ✅ | bajo | Mantener namespace |
| 7 ComplexTypes en extension | Modularidad OK | ✅ | bajo | Mantener estructura |
| `taxId` plano | URN SCHAC `urn:schac:personalUniqueID:pe:DNI:PE:{value}` | ❌ | medio (no federable) | Transformar en outbound a LDAP cache |
| `birthDate` propio | `schacDateOfBirth` | ❌ | bajo | Renombrar/mapear |
| `country` propio | `schacCountryOfCitizenship` | ❌ | bajo | Renombrar |
| `orcid` plano | `eduPersonOrcid` URI completa | ❌ | medio | Transformar a URI `https://orcid.org/{id}` |
| `primaryAffiliationCode` custom | `eduPersonPrimaryAffiliation` vocabulario 8 valores | ❌ | alto (R&S vendors) | Mapear desde archetype |
| `primaryAffiliationName` custom | (eliminar — redundante) | ❌ | bajo | Eliminar |
| `externalSystemId` único | distinguir `employeeNumber` core (empleados) vs `studentID` extension (estudiantes) | ⚠️ | medio | Separar en dos atributos |
| `universityIdCard` + `institutionalIdCard` separados | uno solo (`institutionalIdCard`) | ⚠️ | bajo | Consolidar |
| `alumniStatus` atributo | derivado de archetype `alumni` | ❌ | bajo | Eliminar, derivar |
| `employeeType` en extension | core MidPoint `employeeType` ya existe | ❌ | medio | Migrar a core |
| `campus` como atributo string | `OrgType` archetype `campus` con `parentOrgRef` | ❌ | alto | Modelar como org |
| 4 arquetipos (`StudentType`, `ProfessorType`, ...) | 8 canónicos | ❌ | alto | Crear 4 faltantes |
| Naming arquetipos con sufijo `Type` | naming canónico sin sufijo (`student`, `employee-faculty`) | ❌ | medio (reusabilidad) | Renombrar |
| Resource Keycloak con 13 outbound mappings directos | Provisioning intermediario: MidPoint → LDAP cache → Keycloak | ❌ | alto | Replantear arquitectura |
| Conector custom HTTP `pe.upeu.connector.keycloak-http v1.0.0` (MidPoint→Keycloak directo) | **Sin conector** — MidPoint provisiona a OpenLDAP, Keycloak hace User Federation contra OpenLDAP (read). Decisión del usuario 2026-05-11: NO se construye nuevo conector y NO se reusa el oficial `openstandia/connector-keycloak`. | ❌ | alto | Deprecar conector custom; eliminar resource Keycloak en MidPoint |
| Client Scope SAML `academic-databases-eduperson` con 11 mappers en Keycloak | Mappers correctos pero dependen de atributos LDAP correctos | ⚠️ | medio | Mantener mappers, alimentar desde LDAP cache poblado por MidPoint |
| Sin `eduPersonUniqueId` | Obligatorio para correlación inter-SP | ❌ | alto | Agregar al schema canónico |
| Sin `eduPersonAssurance` | Recomendado para LoA en federación | ⚠️ | medio | Agregar |
| Sin `schacHomeOrganization` | Obligatorio R&S | ❌ | alto | Agregar al outbound |
| Sin `schacUserStatus` | Recomendado para lifecycle federado | ⚠️ | bajo | Agregar |
| Sin `eduPersonPrincipalNamePrior` | Recomendado (rename hell) | ⚠️ | bajo | Agregar |
| Sin role mining sobre `LAMB_ROL` 656 | Fase 4 First Steps Methodology | ❌ | medio | Programar role mining |
| Sin SoD policies | Obligatorio ISO 27001 A.8.2 | ❌ | medio | Definir mínimo 2 reglas SSoD |
| Provisioning directo a Keycloak (sin LDAP cache) | LDAP Identity Cache intermedio (memoria proyecto confirma esta arquitectura) | ❌ | alto | Implementar OpenLDAP intermediario |
| Ausencia de archetype `OrgType` | 6 archetypes orgs recomendados | ❌ | medio | Crear archetypes orgs |
| Sin business roles definidos | 11 BR mínimos viables | ❌ | alto | Definir y desplegar |
| Sin application roles separados | 1 por grupo destino | ❌ | alto | Crear de bottom-up |

### 3.2 Resumen ejecutivo del gap

- **Críticos (alto impacto):** 11 ítems — replantear arquitectura provisioning Keycloak (LDAP cache), agregar atributos eduPerson core (ePPN, ePSA, ePUI, affiliation), modelar campus como org, completar 8 arquetipos, definir RBAC en 3 capas.
- **Medios:** 9 ítems — naming, redundancias, role mining Lamb, SoD policies, transformaciones URN SCHAC.
- **Bajos:** 6 ítems — eliminar atributos derivables, consolidar IDs.

---

## 4. Plan de replanteo de documentos

| # | Documento existente | Decisión | Detalle |
|---|---|---|---|
| 1 | `schema/` (extension XML v2.3) | **EDIT** | Renombrar a v3.0 canónico. Eliminar: `primaryAffiliationName`, `alumniStatus`, `universityIdCard`, `employeeType` (usar core). Renombrar: `birthDate`→derivado SCHAC, `country`→derivado SCHAC. Mantener UPeU-specific: `studentCycle`, `academicProgram`, `studyModality`, `gender`, `province`, `personalWeb`, `languageSkills`, `hireDate`, `terminationDate`, `institutionalIdCard`. Agregar `studentID` (replace `externalSystemId` para alumnos). **NO** agregar atributos eduPerson/SCHAC al extension — son outbound a LDAP cache. |
| 2 | `resources/keycloak-resource.xml` | **DELETE** | MidPoint NO se conecta a Keycloak. Toda la lógica eduPerson va al outbound mapping del **Resource OpenLDAP**. Keycloak se configura por separado en la UI Keycloak como **User Federation contra OpenLDAP** (lectura), y los SAML mappers leen del LDAP directamente. Eliminar el archivo, el OID del recurso, y los 13 outbound mappings actuales. Archivar el conector custom (`pe.upeu.connector.keycloak-http`) en `~/proyectos/upeu/midpoint/archive/` por trazabilidad. |
| 3 | `docs/ciclo-vida-sso-upeu.drawio` | **EDIT** | Actualizar diagrama: agregar OpenLDAP Identity Cache entre MidPoint y Keycloak. Marcar 8 arquetipos. Mostrar cascada Business→Application→Entitlement. |
| 4 | `docs/sso-academico-vendors-mapping.md` | **EDIT** | Verificar que los 11 mappers SAML del Client Scope consumen atributos LDAP cache (no Keycloak local). Reafirmar `eduPersonUniqueId` (NO ePPN) como identificador inter-SP. Agregar columna "fuente LDAP cache" por mapper. |
| 5 | `docs/eduperson-attributes-reference.md` | **KEEP** parcialmente / **EDIT** | Verificar que cubre los 18 atributos eduPerson 202208 v4.4.0 oficiales. Agregar OIDs `.1.13` (eduPersonUniqueId), `.1.11` (eduPersonAssurance), `.1.12` (eduPersonPrincipalNamePrior) si faltan. Sección nueva: vocabulario `eduPersonAffiliation` con 8 valores canónicos. |
| 6 | `schema/README-extension-guia.md` | **REPLACE** | Documentar v3.0 canónica con tabla "atributo extension → atributo canónico federado destino". Explicar regla de oro: extension solo para lo no-estandarizable. |
| 7 | `schema/MAPPING-PLAN-lamb-to-extension.md` | **EDIT** | Actualizar mapping plan con vistas oro confirmadas (`DAVID.VW_*`, `ELISEO.VW_APS_EMPLEADO`). Agregar columna IIA y strength por atributo. Eliminar mappings de atributos que se removerán. |
| 8 | `docs/perfiles-identidad.md` | **REPLACE** | Reescribir con 8 arquetipos canónicos (no 4), criterios de pertenencia explícitos basados en vistas Oracle, transiciones de lifecycle entre archetypes. |
| 9 | `docs/arquitectura.html` | **EDIT** | Reflejar: 8 arquetipos, OpenLDAP Identity Cache central, 3 capas RBAC, partner-institutions separadas de campus. |
| 10 | `docs/index.html` | **EDIT** | Índice actualizado tras renombres. |
| 11 | Memorias `.claude/projects/.../memory/*.md` | **EDIT** | Actualizar `project_arquitectura_iga.md`, `project_sso_academico.md`, `project_oracle_iga.md`, `project_schema_extension_guia.md` con: 8 archetypes, OpenLDAP cache obligatorio, SCHAC URN encoding, eduPersonUniqueId. |
| 12 | (nuevo) `docs/iga-canonical-blueprint.md` | **NEW** | Documento de productización SciBack (§6 de este análisis). |
| 13 | (nuevo) `archetypes/` directorio | **NEW** | 8 XMLs de archetype canónicos + 6 XMLs de OrgType archetypes. |
| 14 | (nuevo) `roles/business/` y `roles/application/` | **NEW** | 11 business roles + ~13 application roles canónicos. |
| 15 | (nuevo) `policy/sod/` | **NEW** | Mínimo 2 SSoD rules ISO 27001 A.8.2. |

---

## 5. Roadmap secuencial

**Restricción:** máximo 15 pasos, ordenados para minimizar riesgo y maximizar valor temprano.

| # | Paso | Archivos | Horas | Bloqueantes | Aprueba |
|---|---|---|---|---|---|
| 1 | **Replantear schema canónico v3.0** — refactor del XSD eliminando atributos redundantes (primaryAffiliationName, alumniStatus, universityIdCard, employeeType extension) y consolidando (institutionalIdCard, studentID separado de employeeNumber). | `schema/upeu-person-extension.xsd` | 4h | Ninguno | Alberto |
| 2 | **Crear 6 OrgType archetypes** (institution, campus, faculty, department, partner-institution, project) + estructura org canónica vacía. | `archetypes/org/*.xml` | 3h | Paso 1 | pre-prod auto |
| 3 | **Sincronizar estructura organizacional UPeU** desde `ELISEO.VW_APS_EMPLEADO` + `ELISEO.ORG_*` a OrgType. Modelar 6 sedes + 21 dependencias + 10 escuelas profesionales. | `resources/oracle-lamb-org.xml` + tarea CSV/JDBC | 6h | Paso 2 + vista oro | Alberto |
| 4 | **Crear 8 UserType archetypes canónicos** con object templates incluidos (1 per archetype). | `archetypes/user/*.xml`, `objectTemplates/*.xml` | 5h | Paso 1 | pre-prod auto |
| 5 | **Object template canónico común** — `commonUserTemplate.xml` con generación ePPN, eduPersonUniqueId, fullName, scopedAffiliation, schacHomeOrganization constante, schacPersonalUniqueID URN-encoded. | `objectTemplates/commonUserTemplate.xml` | 4h | Paso 4 | pre-prod auto |
| 6 | **Desplegar OpenLDAP Identity Cache** (instancia local pre-prod 192.168.15.230). | docker-compose en `midPointEcosystem` | 4h | Ninguno | Alberto |
| 7 | **Resource MidPoint → OpenLDAP** (provisioning) — outbound mappings para todos los atributos eduPerson/SCHAC canónicos derivados. | `resources/ldap-identity-cache.xml` | 6h | Pasos 4, 5, 6 | Alberto |
| 8 | **Configurar Keycloak User Federation desde OpenLDAP** (lectura). Mapear atributos eduPerson/SCHAC desde LDAP a SAML Client Scope `academic-databases-eduperson`. **NO usar conector MidPoint→Keycloak**: MidPoint solo provisiona a LDAP, Keycloak lee de LDAP. Eliminar resource Keycloak en MidPoint y archivar conector custom HTTP. | Keycloak admin UI + delete `keycloak-resource.xml` en MidPoint + archivar conector custom | 4h | Paso 7 | Alberto |
| 9 | **Resources JDBC Oracle LAMB** — 2 resources: Trabajadores (`MOISES` + `ELISEO`) y Estudiantes (`DAVID`). Inbound mappings strong desde vistas oro. Correlación por `employeeNumber`/`studentID`. | `resources/oracle-lamb-trabajadores.xml`, `resources/oracle-lamb-estudiantes.xml` | 8h | Pasos 1, 3, 4 + ojdbc11 instalado | Alberto |
| 10 | **Application Roles bottom-up** — crear ~15 application roles iniciales (Google Workspace, Entra ID, AD, Koha, DSpace, OJS, Indico, Keycloak, FreeRADIUS/VPN) con constructions a cada resource downstream. | `roles/application/*.xml` | 8h | Resources downstream existentes | pre-prod auto |
| 11 | **Business Roles canónicos** — 11 BR con inducements a app roles. Incluye auto-asignación vía object template + `assignmentTargetSearch`. | `roles/business/*.xml` | 6h | Paso 10 | pre-prod auto |
| 12 | **SoD policies mínimas ISO 27001 A.8.2** — 2 reglas SSoD (Admin-Nomina ⊥ Aprobador-Pagos; Auditor ⊥ Operativo). | `policy/sod/*.xml` | 2h | Paso 11 | Alberto |
| 13 | **Role mining piloto sobre `ELISEO.LAMB_ROL`** — análisis de combinaciones reales en `LAMB_USUARIOS` × `LAMB_ROL`, exportar candidatos a business roles UPeU-specific. | reporte + `roles/business/upeu-specific/*.xml` | 8h | Pasos 9, 11 | Alberto |
| 14 | **Replantear documentos** — actualizar `docs/perfiles-identidad.md`, `docs/arquitectura.html`, `docs/sso-academico-vendors-mapping.md`, `docs/ciclo-vida-sso-upeu.drawio`, READMEs schema, memorias proyecto. | (varios) | 5h | Pasos 1–13 estabilizados | Alberto |
| 15 | **Pipeline GitOps y productización SciBack** — extraer pieza canónica vs UPeU-specific, crear `sciback-iga-blueprint` repo en `~/proyectos/sciback/` con estructura overlay. | nuevo repo | 6h | Paso 14 | Alberto |

**Total estimado:** ~79 horas (~2 sprints de 2 semanas). Pasos 1–8 entregan valor temprano (federación funcional con atributos eduPerson). Pasos 9–13 entregan RBAC operacional. Pasos 14–15 consolidan documentación y productización.

---

## 6. Productización SciBack

### 6.1 Modelo de overlays

`sciback-iga-blueprint` (repo canónico en `github.com/SciBack/iga-blueprint`) contiene el modelo canónico universal **agnóstico a cualquier universidad peruana**. Cada cliente (UPeU, Univ. X, Univ. Y) tiene su propia carpeta hermana en `~/proyectos/<cliente>/` con sus overlays.

### 6.2 Estructura propuesta del repo `sciback-iga-blueprint`

```
sciback-iga-blueprint/
├── schema/
│   └── canonical-person-extension.xsd         ← namespace urn:sciback:iga:person, atributos NO estándar reusables
├── archetypes/
│   ├── user/
│   │   ├── student.xml
│   │   ├── employee-faculty.xml
│   │   ├── employee-staff.xml
│   │   ├── affiliate-partner-institution.xml
│   │   ├── affiliate-researcher.xml
│   │   ├── alumni.xml
│   │   ├── contractor.xml
│   │   └── service-account.xml
│   └── org/
│       ├── institution.xml
│       ├── campus.xml
│       ├── faculty.xml
│       ├── department.xml
│       ├── partner-institution.xml
│       └── project.xml
├── objectTemplates/
│   ├── commonUserTemplate.xml                  ← genera ePPN, ePUI, ePSA, scopedAffiliation
│   └── per-archetype/
│       └── student.xml ...                     ← un template por archetype con specifics
├── roles/
│   ├── business/                               ← 11 BR canónicos universitarios
│   └── application/                            ← templates Google Workspace / Entra ID / AD / Koha / DSpace / OJS / Indico / Keycloak / FreeRADIUS
├── resources/
│   ├── ldap-identity-cache.xml.tmpl            ← template con placeholders ${SCOPE}, ${BASE_DN}
│   ├── keycloak-federation.xml.tmpl
│   ├── entraid-graph.xml.tmpl                  ← Microsoft Graph API
│   ├── google-workspace.xml.tmpl               ← Google Admin SDK
│   ├── ad-ldap.xml.tmpl                        ← AD LDAP (opcional, para otras universidades que sí usen AD)
│   ├── koha.xml.tmpl
│   ├── dspace.xml.tmpl
│   └── oracle-erp-jdbc.xml.tmpl                ← template fuente autoritativa (UPeU Lamb / ERP equivalente)
├── policy/sod/
│   └── canonical-sod-rules.xml
├── docs/
│   ├── iga-canonical-blueprint.md              ← qué es canónico, qué no
│   ├── deployment-guide.md
│   └── customization-guide.md
└── .env.example                                ← variables por cliente
```

### 6.3 Mecanismo de overlay por cliente

Cada cliente (`~/proyectos/<cliente>/iga/`) contiene:

```
upeu/iga/
├── .env                                        ← scope=upeu.edu.pe, baseDN, dominio, IIAs Oracle
├── schema/
│   └── upeu-specific-extension.xsd             ← namespace urn:upeu:midpoint:person, atributos UPeU-only (studentCycle, gender, province, etc.)
├── resources/
│   ├── oracle-lamb-trabajadores.xml            ← UPeU-specific: vistas Oracle MOISES/ELISEO
│   └── oracle-lamb-estudiantes.xml             ← UPeU-specific: vistas Oracle DAVID
├── orgs/
│   └── upeu-org-bootstrap.xml                  ← 6 sedes UPeU, 21 dependencias, 10 escuelas
└── docs/
    └── upeu-deployment.md                      ← runbook propio
```

**Regla de oro de la productización (Cf. instrucciones globales del usuario):**
- Bug fixes y mejoras → siempre en `sciback-iga-blueprint` primero. Luego `git pull` en cada cliente.
- El cliente nunca es upstream de nada.
- Si UPeU necesita algo que parece generalizable → primero refactor en `sciback-iga-blueprint`. Solo si es estrictamente UPeU-specific (Lamb, peculiaridades MOISES, instituciones afines adventistas), queda en `~/proyectos/upeu/iga/`.

### 6.4 Pieza canónica vs UPeU-specific

| Pieza | Vive en | Razón |
|---|---|---|
| 8 archetypes user, 6 archetypes org | `sciback-iga-blueprint` | Universal universitario |
| Object template canónico (ePPN, ePUI, ePSA) | `sciback-iga-blueprint` | Estándares |
| Resources downstream templates (Google Workspace, Entra ID, AD LDAP, Koha, DSpace, OJS, Keycloak federation, OpenLDAP cache) | `sciback-iga-blueprint` | Genéricos parametrizables |
| 11 Business roles canónicos | `sciback-iga-blueprint` | Universal |
| Application roles templates | `sciback-iga-blueprint` | Genéricos |
| SoD policies canónicas | `sciback-iga-blueprint` | ISO 27001 universal |
| Schema extension UPeU (studentCycle, gender ISO 5218, province, personalWeb, languageSkills, hireDate, terminationDate, institutionalIdCard, studyModality, academicProgram, studentID) | `~/proyectos/upeu/iga/schema/` | Específico UPeU (régimen peruano, MOISES) |
| Resources Oracle LAMB JDBC (MOISES/ELISEO/DAVID) | `~/proyectos/upeu/iga/resources/` | UPeU-only |
| Estructura org bootstrap UPeU (6 sedes reales, 21 dependencias) | `~/proyectos/upeu/iga/orgs/` | UPeU-only |
| Business roles UPeU-specific derivados de role mining Lamb | `~/proyectos/upeu/iga/roles/` | UPeU-only |
| Partner institutions (Colegio Unión, Clínica GH, ISTAT, AGTU) | `~/proyectos/upeu/iga/orgs/` | UPeU-only (red adventista) |
| Mappers SAML para vendors académicos (Scopus, EBSCO, WoS, etc.) | `sciback-iga-blueprint` (Keycloak realm template) | Universal (mismos vendors para toda universidad) |

### 6.5 Reglas de oro de productización

1. **Schema canónico SciBack es agnóstico.** Si un atributo no existe en eduPerson/SCHAC/SCIM, va en `urn:sciback:iga:person` solo si es universal a universidades. Lo institucional específico va en `urn:<cliente>:midpoint:person`.
2. **Resources templates con `.tmpl`** — variables `${SCOPE}`, `${BASE_DN}`, `${INSTITUTION_NAME}`, `${HOME_ORG_TYPE_URN}` resueltas en deploy.
3. **Object templates canónicos referenciables vía `<includeRef>`** (Cf. `midpoint-best-practices` §4.1) — clientes solo agregan items institucionales.
4. **Tests automatizados de conformidad canónica** — un script verifica que todo cliente liberé el R&S attribute bundle a SPs marcados como `+sirtfi` `+coco` `+rs`.

---

## Anexos

### A. Casos de uso IAL/AAL/FAL — UPeU

Cf. `iga-canonical-standards` §2.

| Caso de uso UPeU | IAL | AAL | FAL | Mecanismo |
|---|---|---|---|---|
| OPAC público Koha BUL | 1 | 1 | 1 | Email self-attested |
| Google Classroom (sesión activa) | 2 | 2 | 2 | DNI verificado + MFA |
| Portal UPeU Lamb estudiante | 2 | 2 | n/a | DNI verificado + MFA (SSO Keycloak) |
| Wi-Fi 802.1X | 2 | 2 | n/a | EAP-TLS con cert UPeU |
| Bases científicas (Scopus, EBSCO, WoS) | 2 | 2 | 2 | SAML R&S bundle |
| Admin SINAI/PRLB financiero | 2 | 2-3 | n/a | MFA hardware token |
| Firma digital diplomas SUNEDU | 3 | 3 | 3 | EJBCA + token + RENIEC biometría |

`eduPersonAssurance` outbound:
- IAL 2 (DNI verificado): `https://refeds.org/assurance/IAP/medium`
- IAL 3 (RENIEC biométrico): `https://refeds.org/assurance/IAP/high`
- ePPN unique no-reassign: `https://refeds.org/assurance/ID/eppn-unique-no-reassign`

### B. Verificaciones pendientes

- [verificar después] Tabla origen de `institutionalIdCard` (carné universitario UPeU) — no aparece explícitamente en schemas Oracle leídos.
- [verificar después] Existencia y permisos sobre `DAVID.VW_DATOS_IDENTIDAD_USUARIO` (mencionada como vista oro, no consultada en este análisis).
- [verificar después] Registro de namespace SCHAC `pe:` en REFEDS URN Registry — actualmente NO existe; uso provisional acordado institucionalmente.
- [verificar después] Decisión sobre `schacHomeOrganizationType` para UPeU: `eu:higherEducationalInstitution` provisional o registrar `pe:`.

---

**Fin del documento.**
