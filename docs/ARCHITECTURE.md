# UPeU IGA — Análisis Canónico y Plan de Replanteo

**Versión:** 2026-05-20
**Autor:** midpoint-expert (consultando `iga-canonical-standards` v2026-05 + `midpoint-best-practices`)
**Alcance:** sistema IGA UPeU sobre MidPoint 4.10.2, base canónica reutilizable para otras universidades (`canonical/` en este repo)

---

## 1. Decisión doctrinal

### 1.1 Principio rector

**El modelo canónico se diseña primero desde los estándares internacionales. Los datos institucionales (Oracle LAMB, MDM MOISES, nómina ELISEO) se mapean al modelo canónico vía transformations. NUNCA al revés.** (Cf. `iga-canonical-standards` §11 regla 1).

Esta decisión es **doctrinal**, no técnica: todo el código y XML producido para UPeU debe ser refactorizable para servir como esqueleto de cualquier otra universidad peruana. La especificidad UPeU vive en (a) overlays parametrizados, (b) mappings de inbound desde Oracle LAMB, (c) catálogos de sedes/facultades; jamás en el schema canónico ni en los arquetipos.

### 1.0 Estado real en PROD (2026-05-20)

| Componente | Estado |
|---|---|
| MidPoint | 4.10.2 (actualizado 2026-05-19 desde 4.9.5) |
| Servidor | 192.168.15.166, Ubuntu 22.04, Docker, 9.7 GB RAM |
| Usuarios | 35.450 (alumni 30.491 · staff 3.144 · student 1.679 · faculty 135) |
| Orgs | 122 · Roles | 72 · Services (posiciones) | 741 |
| Schemas activos | `urn:sciback:midpoint:person` (canónico) + `urn:upeu:midpoint:local` (overlay LAMB) |
| Archetypes custom | 18 (8 user + 8 org + 2 role) |
| Resources activos | Oracle LAMB Trabajadores v3 · Oracle LAMB Estudiantes v3 · Oracle LAMB Egresados v3 · LAMB-Oracle-Posiciones · Koha ILS · LDAP-IdentityCache-UPeU · UPEU-EntraID-Graph |
| Sombras LDAP | 37.491 · Sombras Entra ID | 37.304 · Sombras Koha | 5.421 |
| Object Templates | UserTemplate-Person-Base (base) + 4 por archetype (alumni/student/faculty/staff) |
| Pipeline | Trigger Scanner 5 min · Validity Scanner 15 min · 3 crons LAMB 02:00 UTC · Koha cron 03:00 UTC |
| Keycloak federation | Activa: 192.168.12.88 → OpenLDAP 192.168.15.168:389 |
| Correlación | `personalNumber` (core) para activos; `extension/upeu:lambDocNum` trabajadores; `extension/sb:taxId` egresados |

---

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

**Estado actual en PROD (2026-05-20):** 18 archetypes custom desplegados. Arquetipos UserType activos: `alumni`, `student`, `faculty`, `staff` (4 canónicos con volumetría real). Arquetipos OrgType activos: 8 (institution, campus, faculty, department, partner-institution, project, role-catalog + governance). Arquetipos RoleType activos: 2 (application-role, business-role). Los arquetipos `affiliate-partner-institution`, `affiliate-researcher`, `contractor`, `service-account` están en el modelo canónico pero pendientes de poblar con datos reales en fases posteriores.

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
| Resource Keycloak directo (v1.0.0 HTTP custom) | MidPoint → OpenLDAP ← Keycloak User Federation (sin conector directo) | ✅ | alto | **IMPLEMENTADO**: OpenLDAP IdentityCache activo (192.168.15.168:389), Keycloak User Federation activa desde OpenLDAP. Resource Keycloak directo eliminado. |
| Sin `eduPersonUniqueId` | Obligatorio para correlación inter-SP | ❌ | alto | Pendiente — schema canónico `urn:sciback:midpoint:person` activo, mapping eduPersonUniqueId en backlog |
| Sin `schacHomeOrganization` | Obligatorio R&S | ❌ | alto | Pendiente — outbound a LDAP cache |
| Sin SoD policies | Obligatorio ISO 27001 A.8.2 | ❌ | medio | Pendiente — definir mínimo 2 reglas SSoD en F13 |
| Ausencia de archetypes `OrgType` | 8 archetypes orgs recomendados | ✅ | medio | **IMPLEMENTADO**: 8 archetypes OrgType activos |
| Sin business roles definidos | BR mínimos viables | ✅ | alto | **IMPLEMENTADO**: 72 roles activos en PROD (Application + Business) |
| Sin application roles separados | 1 por grupo destino | ✅ | alto | **IMPLEMENTADO**: roles por resource activos |
| Sin object templates | 1 per archetype | ✅ | alto | **IMPLEMENTADO**: 5 templates (base + alumni/student/faculty/staff) |

### 3.2 Resumen ejecutivo del gap (estado 2026-05-20)

Las fases 1-4 del roadmap están completadas (schema, archetypes, org tree, RBAC, object templates, resources LAMB × 4, LDAP cache, Koha, Entra ID). Los gaps pendientes son:

- **Críticos (alto impacto):** atributos eduPerson federados (ePPN, ePSA, ePUI, eduPersonAffiliation) pendientes de mapear en outbound LDAP; `schacHomeOrganization` pendiente de outbound.
- **Medios:** SoD policies (mínimo 2 reglas ISO 27001 A.8.2), permisos Entra ID write (4 de 7 pendientes David Urquizo), cuenta Oracle `MIDPOINT_IGA_RO` dedicada (actualmente usando `JUANSANCHEZ`).
- **Bajos:** archetypes affiliate/contractor/service-account sin poblar; namespace SCHAC `pe:` sin registrar en REFEDS.

---

## 4. Estado de implementación (2026-05-20)

> Esta sección reemplaza el plan original de replanteo. Los items completados se marcan ✅.

| # | Item | Estado | Detalle |
|---|---|---|---|
| 1 | Schema canónico | ✅ DONE | `urn:sciback:midpoint:person` (canónico) + `urn:upeu:midpoint:local` (overlay). Activos en PROD. |
| 2 | Archetypes UserType | ✅ DONE | 8 activos: alumni, student, faculty, staff + 4 estructurales pendientes de poblar (affiliate, contractor, etc.) |
| 3 | Archetypes OrgType | ✅ DONE | 8 activos en PROD |
| 4 | Archetypes RoleType | ✅ DONE | 2 activos (application-role, business-role) |
| 5 | Org tree | ✅ DONE | 122 orgs tipificadas (institution + campus + faculties + governance + academic-unit + department) |
| 6 | Object Templates | ✅ DONE | 5 templates activos (base + alumni/student/faculty/staff) |
| 7 | RBAC | ✅ DONE | 72 roles activos (Application + Business) con auto-asignación vía `assignmentTargetSearch` |
| 8 | Resources Oracle LAMB | ✅ DONE | 4 resources JDBC: Trabajadores v3, Estudiantes v3, Egresados v3, Posiciones |
| 9 | Resource LDAP Identity Cache | ✅ DONE | OpenLDAP 192.168.15.168:389 activo con 37.491 sombras |
| 10 | Resource Entra ID | ✅ DONE | 37.304 sombras (solo lectura; write pendiente David Urquizo) |
| 11 | Resource Koha | ✅ DONE | 5.421 sombras |
| 12 | Keycloak federation | ✅ DONE | User Federation activa contra OpenLDAP (NO conector directo MidPoint→Keycloak) |
| 13 | Pipeline JML | ✅ DONE | Trigger Scanner 5 min, Validity Scanner 15 min, crons LAMB 02:00 UTC, Koha 03:00 UTC |
| 14 | Outbound eduPerson LDAP | ⏳ PENDIENTE | ePPN, ePSA, ePUI, eduPersonAffiliation, schacHomeOrg — mappings en backlog |
| 15 | SoD policies | ⏳ PENDIENTE | Mínimo 2 reglas ISO 27001 A.8.2 — F13 del roadmap |
| 16 | Cuenta Oracle `MIDPOINT_IGA_RO` | ⏳ PENDIENTE | Diferido a antes de F10 (actualmente `JUANSANCHEZ`) |
| 17 | Entra ID write | ⏳ PENDIENTE | 4 de 7 permisos pendientes David Urquizo (DU-001a) |

---

## 5. Próximas fases (desde 2026-05-20)

> Para el roadmap completo ver `docs/ROADMAP.md`. Esta sección solo lista las próximas acciones.

| Fase | Descripción | Bloqueante principal |
|---|---|---|
| F5 — eduPerson outbound | Mapear ePPN, ePSA, ePUI, eduPersonAffiliation, schacHomeOrg en outbound LDAP | Diseño de mappings |
| F6 — Entra ID write | Provisioning real a Entra ID (licencias, grupos) | Permisos Graph API (David Urquizo) |
| F7 — Role mining LAMB | Análisis `ELISEO.LAMB_ROL` × `LAMB_USUARIOS` (656 roles) para derivar BR UPeU-specific | Oracle acceso |
| F8 — SoD policies | Mínimo 2 reglas SSoD (Admin-Nomina ⊥ Aprobador-Pagos; Auditor ⊥ Operativo) | F6 estable |
| F9 — OpenLDAP HA | 2do nodo OpenLDAP (N-Way Multimaster) | VM Rudy (D-14) |
| F10 — Cuenta Oracle dedicada | Crear `MIDPOINT_IGA_RO` y rotar desde `JUANSANCHEZ` | Rudy (RU-001) |

---

## 6. Reutilización institucional (capa canónica)

### 6.1 Modelo de capas

Este repositorio (`github.com/UPeU-Infra/midPointEcosystem`) tiene dos capas:

- `canonical/` — modelo agnóstico a cualquier universidad peruana (eduPerson/SCHAC/SCIM/RBAC)
- `upeu/` — overlay UPeU: vistas Oracle LAMB, catálogos de sedes/facultades, particularidades de la red adventista

Cualquier otra universidad que adopte el modelo replica el proceso: clonar el repo, aplicar `canonical/` sin modificar, agregar su propio overlay.

### 6.2 Estructura real del repo (2026-05-20)

```
midPointEcosystem/
├── canonical/         ← Capa 1: archetypes, schema, roles, templates, resources canónicos
├── upeu/              ← Capa 2: overlays UPeU (LAMB resources, orgs, catálogos propios)
├── docs/              ← ROADMAP, ARCHITECTURE, runbooks, specs
├── datasets/          ← CSV/PG demo
└── archive/           ← Material histórico (NO importar a PROD)
```

### 6.3 Pieza canónica vs UPeU-specific

| Pieza | Capa | Razón |
|---|---|---|
| 8 archetypes UserType | `canonical/archetypes/` | Universal universitario |
| 8 archetypes OrgType | `canonical/archetypes/` | Universal |
| Schema `urn:sciback:midpoint:person` | `canonical/schema/` | Atributos no cubiertos por eduPerson/SCHAC/SCIM |
| Object templates (base + por archetype) | `canonical/object-templates/` | Estándares ePPN/ePUI/ePSA |
| Roles Application y Business | `canonical/roles/` | Universales parametrizables |
| Resource LDAP Identity Cache template | `canonical/resources/` | Genérico `${SCOPE}`, `${BASE_DN}` |
| Schema `urn:upeu:midpoint:local` | `upeu/schema/` | LAMB-specific (laboralStatus, lambDocNum) |
| Resources Oracle LAMB × 4 | `upeu/resources/` | Vistas MOISES/ELISEO/DAVID UPeU-only |
| Org bootstrap UPeU (122 orgs) | `upeu/orgs/` | Catálogo real UPeU |
| Partner institutions (Colegio Unión, Clínica GH, ISTAT, AGTU) | `upeu/orgs/` | Red adventista UPeU-only |

### 6.4 Reglas de mantenimiento

1. Toda mejora generalizable va a `canonical/` primero.
2. Lo específico de LAMB/UPeU queda en `upeu/` y nunca sube a `canonical/`.
3. OIDs estables — el filename puede cambiar; el OID nunca.
4. Nuevas universidades: clonan el repo, no hacen fork. Agregan su propio directorio al nivel de `upeu/`.

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
