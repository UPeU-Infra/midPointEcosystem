# MidPoint — Contexto del Proyecto

> **Documento vivo:** `docs/roadmap-iga-2026.md` es la fuente de verdad operativa. Este `context.md` es la referencia estable del proyecto.

## Snapshot 2026-05-13 (auditado contra PROD real)

> **Política de infraestructura:** No existe ciclo DEV→PROD para este proyecto. El único ambiente es PROD (`192.168.15.166`). La instancia `192.168.15.230` es sandbox personal y no forma parte del modelo IGA canónico.

### Estado de fases (validado en PROD vía REST API + SSH)

| Fase | Estado | Evidencia real en PROD |
|---|---|---|
| **F0** Refactor doctrinal | ✅ | Skills publicadas, roadmap v2026-05-11, decisiones doctrinales registradas |
| **F1** Schema v3.0 | ✅ | OID `b7d55017-599f-4f2f-9493-9f64bba62c5b` activo. Schema `urn:upeu:midpoint:person:v3` + schema `urn:upeu:midpoint:lamb:v1` ambos activos en `m_ext_item` |
| **F2** Archetypes + Org tree | ✅ | 18 archetypes activos (8 UserType + 8 OrgType + 2 RoleType) · 91 orgs tipificadas |
| **F3** Object Templates | ✅ | 10 templates activos (1 base + 9 por archetype) |
| **F4** OpenLDAP HA | ❌ | Sin iniciar — sin VMs, sin docker-compose, sin DIT |
| **F5** Resources READ | 🟢 | **3 resources Oracle ScriptedSQL v2 production-ready** (trabajadores/estudiantes/egresados). Test connection success. 23 usuarios piloto importados (10 trabajadores + 9 estudiantes + 4 egresados), todos LINKED, 0 dead. Campos nuevos poblados. Tasks recon masiva siguen SUSPENDED (muestrario piloto completado — recon masiva es próximo paso) |
| **F6** Resources WRITE | ❌ | Sin iniciar. Resource Keycloak legacy (`a3f9c1d2-...`) aún presente en PROD — pendiente eliminar |
| **F7** RBAC bottom-up | ✅ | 20 AR + 11 BR activos · 3 BR legacy archivados · auto-asignación en templates |
| **F8** Replanteo docs | ❌ | Docs no actualizados post-F7 |
| **F9** Validación piloto | 🟢 | **Piloto de muestrario completado (2026-05-13).** 23 usuarios reales importados desde Oracle LAMB. Campos nuevos (nationality, disability, studyLevel, studyModality, lambPersonaId) verificados. Recon masiva pendiente de spec separada |
| **F10** Deploy PROD | N/A | Todo ya está en PROD desde F1 |
| **F11** SciBack blueprint | ❌ | Repo `sciback-iga-blueprint` sin crear |
| **F12** Gobierno Entra ID | ❌ | Diferido por diseño hasta F11 estable |

### Schema activo en PROD (2026-05-13)

| Schema | Namespace | Campos clave |
|---|---|---|
| Person v3.0 | `urn:upeu:midpoint:person:v3` | birthDate, gender, hireDate, terminationDate, taxId (URN SCHAC), nationality, disability, studyLevel, studyModality, studentCycle, academicProgramCode, studyModality |
| Lamb v1 | `urn:upeu:midpoint:lamb:v1` | lambPersonaId (ID en Oracle LAMB para correlación) |

> **Nota:** `lambDeptoCode` mencionado en planificación pero NO creado en schema lamb:v1 aún (solo existe `lambPersonaId`). Pendiente si se necesita para routing Koha/OpenLDAP.

### Campos nuevos disponibles para downstream (desde 2026-05-13)

Estos campos están ahora poblados en los usuarios MidPoint y disponibles para outbound mappings:

| Campo | Fuente | Disponible para |
|---|---|---|
| `lamb:lambPersonaId` | Oracle LAMB (ID_PERSONA/ID_ALUMNO) | Correlación en reconciliaciones futuras |
| `upeu3:nationality` | Oracle LAMB (ID_TIPOPAIS → PER/etc.) | OpenLDAP → Keycloak (atributo SAML schacCountryOfResidence) |
| `upeu3:disability` | Oracle LAMB (DISCAPACIDAD) | Reportes institucionales |
| `upeu3:studyLevel` | Oracle LAMB (NIVEL_ENSENANZA) | Koha (categoría de patrón), OpenLDAP → Keycloak |
| `upeu3:studyModality` | Oracle LAMB (MODALIDAD_ESTUDIO) | Segmentación RBAC futura |
| `upeu3:taxId` | Oracle LAMB (NUM_DOCUMENTO → URN SCHAC) | Keycloak (atributo SAML schacPersonalUniqueID) |
| `upeu3:birthDate` | Oracle LAMB (FEC_NACIMIENTO) | Koha, reportes |

### Bloqueantes activos

| # | Bloqueante | Estado |
|---|---|---|
| **B1** | VMs OpenLDAP nodo 1+2 | ❌ IPs sin definir (sugerencia `.232/.233`) |
| **B2** | `ojdbc11.jar` en contenedor PROD | ✅ Instalado en `/opt/midpoint/var/lib/ojdbc11-23.6.0.24.10.jar` |
| **B3** | Credenciales Graph API tenant UPeU real | ❌ Pendiente ticket DU-001a (David Urquizo) |
| **B-NET** | **Firewall VLAN** `192.168.15.166 → 192.168.13.9:1521` | ✅ **RESUELTO 2026-05-12** — `nc -zv` confirma puerto 1521 accesible |

### Próximas 5 tareas priorizadas

1. **Phase C — Object Templates**: setear `lifecycleState=draft` en `UserTemplate-Person-Base` para usuarios recién importados de Oracle; definir transición a `active` vía validación RENIEC o workflow.
2. **Recon masiva Oracle LAMB** — abrir spec para activar `task-recon-trabajadores-v2` con filtro sede `LIM` completo (eliminar filtros de muestrario en `searchScript`). ~8475 trabajadores + ~3803 estudiantes Lima.
3. **Eliminar resource Keycloak legacy** — borrar OID `a3f9c1d2-7e4b-4a8f-b6c3-2d1e9f0a5b87` en PROD (decisión doctrinal 2026-05-11)
4. **Definir IPs OpenLDAP** — Alberto asigna nodos para desbloquear F4 (sugerencia `.232/.233`)
5. **Ticket DU-001a** — credenciales Graph API tenant UPeU real (David Urquizo)

### Tasks en PROD (inventario 2026-05-13)

| Task | Estado | OID |
|---|---|---|
| Trigger Scanner | suspended | `00000000-...-0007` |
| Validity Scanner | suspended | `00000000-...-0006` |
| Recompute all users | suspended | `13eef9d9-...` |
| task-recon-trabajadores (v1) | suspended | `6a91f7e1-...-0e11` |
| task-recon-estudiantes (v1) | suspended | `6a91f7e1-...-0e12` |
| task-recon-egresados (v1) | suspended | `6a91f7e1-...-0e13` |
| **task-recon-trabajadores-v2** | suspended | `6a91f7e1-...-0e31` |
| task-recon-estudiantes-v2 | suspended | `6a91f7e1-...-0e32` |
| task-recon-egresados-v2 | suspended | `6a91f7e1-...-0e33` |
| import-ola1-piloto-trabajadores-v2-run2 | closed (historial) | — |
| Cleanup | runnable | `00000000-...-0005` |

> **Nota:** 23 usuarios piloto importados vía reconciliaciones manuales y tasks de import one-off (no vía las tasks recon masiva). Las tasks recon masiva siguen SUSPENDED — se activarán en la siguiente spec (recon masiva Lima).

### Política local activa

Todo trabajo técnico se delega al sub-agente `midpoint-expert` (global), que consulta `iga-canonical-standards` + `midpoint-best-practices` antes de proponer cambios. Modelo canónico primero; datos UPeU se adaptan al modelo, nunca al revés.

## Modelo de Access Governance (decisión doctrinal 2026-05-12)

**Principio absoluto:** TODO acceso a apps, licencias y permisos se decide en MidPoint. Entra ID, OpenLDAP y Keycloak son **target systems** que solo ejecutan. Crear grupos manualmente en Entra ID o asignar licencias usuario por usuario **rompe la cadena de governance** (ISO 24760-2 §6.4).

### Modelo de 5 capas

```
NIVEL 5 — Sistema target ejecuta (Entra ID asigna licencia / RADIUS asigna VLAN / EZProxy autoriza)
        ↑
NIVEL 4 — Grupo en target (lic-zoom-pro-faculty, grp-wifi-estudiantes...)   ← MidPoint outbound
        ↑
NIVEL 3 — Application Role MidPoint (AR-Zoom-Licensed-Pro, AR-WiFi-Estudiantes...)
        ↑
NIVEL 2 — Business Role MidPoint (BR-Docente-TC, BR-Estudiante-Pregrado...)
        ↑
NIVEL 1 — Archetype MidPoint (employee-faculty, student) — auto-asignado desde Oracle LAMB
```

### Topología de apps por canal

| Canal | Apps |
|---|---|
| **Entra ID SSO directo** | M365 (Word/Excel/Teams/OneDrive/SharePoint), Power BI, Zoom, Adobe CC, Canva EDU, GitHub Enterprise |
| **Keycloak (broker)** | Koha (bul/buj/but/cia), Indico, OJS, DSpace, Moodle, GLPI, Documize, EZProxy → bases académicas (Scopus, WoS, IEEE, ProQuest, EBSCO) |
| **OpenLDAP/RADIUS directo** | FreeRADIUS Wi-Fi 802.1X, VPN, switches/firewalls (TACACS+/RADIUS), impresoras |

**Importante:** Keycloak NO autentica contra Entra ID. Keycloak autentica contra OpenLDAP. OpenLDAP es alimentado por MidPoint. Entra ID es target paralelo para el mundo Microsoft. Ambos consumen del mismo MidPoint upstream → consistencia garantizada.

### Estado de alineación con lo implementado

✅ **En PROD ya alineado:** 8 archetypes UserType, 11 Business Roles, 20 Application Roles (Koha, Indico, DSpace, OJS, Keycloak, Wi-Fi por perfil, M365 A1/A3, Vendor-Academic-Access).

❌ **Gaps identificados — pendientes F7.5 o F12:**
- AR-Zoom-Licensed-Pro / AR-Zoom-Licensed-Business
- AR-PowerBI-Pro
- AR-Adobe-CC-Designer
- AR-Canva-EDU-Teacher
- Desglose AR-Vendor-Academic-Access → AR-Vendor-Scopus, AR-Vendor-WoS, AR-Vendor-IEEE, AR-Vendor-ProQuest, AR-Vendor-EBSCO
- Administrative Units por campus en Entra ID
- App-specific role groups (Zoom-Admin, Teams-Phone-CallQueue, SharePoint-Owner, PowerBI-Workspace-Admin)

### ¿Quién hace qué?

| Acción | Quién | Cómo |
|---|---|---|
| Crear/modificar grupos Entra ID | MidPoint outbound exclusivamente | Resource Entra ID con shadow=group |
| Asignar licencia M365/Zoom/Adobe | MidPoint vía group membership | Group-based licensing de Entra ID |
| Audit de accesos | DTI Governance | MidPoint Reports + Entra ID Access Reviews trimestrales |
| Aprobar excepción de rol | Workflow MidPoint | Aprobador: jefe inmediato + DTI Security |
| Re-certificación anual | Vicerrectorado + DTI | MidPoint Access Certification campaigns |
| Admin manual en Entra ID | 🚫 PROHIBIDO | Solo break-glass account documentado |

### Detalle completo

Documento de memoria: `~/.claude/projects/-Users-alberto-proyectos-upeu-midpoint/memory/project_access_governance_model.md`

## Objetivo

Implementar MidPoint como IGA (Identity Governance & Administration) para UPeU como caso piloto real. UPeU es el primer despliegue; la arquitectura quedará replicable para otros clientes de SciBack que necesiten ciclo de vida de usuarios.

## Principios de diseño

Todo el proyecto se alinea desde el inicio a:
- **ISO/IEC 24760** — framework de identidad, nomenclatura y ciclo de vida
- **NIST SP 800-63** — niveles de aseguramiento de identidad (IAL/AAL)
- **NIST SP 800-207** — Zero Trust Architecture
- **Ley 29733** — Protección de datos personales (Perú)
- **RENATA/RedCLARA** — compatibilidad para futura federación académica peruana

## Caso de uso UPeU

Unificar el ciclo de vida de usuarios (alumnos, docentes, administrativos) usando como fuente de verdad la base de datos de **Lamb Academic** (SIS/ERP académico de UPeU), sincronizando hacia los sistemas destino y habilitando SSO vía OIDC.

### Sistemas destino (por prioridad)

| Sistema | Conector MidPoint | Protocolo auth |
|---------|------------------|----------------|
| Azure EntraID | Graph API connector | OIDC vía Keycloak |
| Active Directory | AD connector | — |
| Koha | JDBC / REST (connector-koha) | OIDC vía Keycloak |
| Moodle | JDBC / REST | OIDC vía Keycloak |
| DSpace 7 | REST API | OIDC vía Keycloak |
| OJS | JDBC | OIDC vía Keycloak |
| FreeRADIUS | LDAP / flat-file | EAP-TLS (proyecto SmartWifi) |

## Arquitectura actual (v1)

```
[DB Lamb Academic] ──JDBC──► [MidPoint IGA]
                                    │
                    ┌───────────────┼───────────────────┐
                    ▼               ▼                   ▼
             [Azure EntraID]  [AD on-premise]   [Koha / Moodle]
                    │
                    ▼
               [Keycloak]  ──OIDC──► [Apps finales]
```

Fases de implementación (según arquitectura del repo):
1. **Fase 1 — SIS CSV**: importar estudiantes y docentes desde CSV (actual)
2. **Fase 2 — RRHH y CRM**: fuentes CSV adicionales
3. **Fase 3 — EntraID**: propagación a nube vía Graph API
4. **Fase 4 — Optimización**: reconciliaciones periódicas, alertas, dashboards

## Esquema de identidad

### Estrategia de capas (decisión arquitectural)
- **Capa 1 — Nativos MidPoint**: `emailAddress`, `employeeNumber`, `title`, `employeeType`, `locality`, `activation` — usar sin duplicar
- **Capa 2 — Extensión custom** (`urn:upeu:midpoint:person`): todo lo que no es nativo — ya implementado en v2.2
- **Orientación futura**: alinear naming a eduPerson/SCHAC donde haya equivalencia directa, para facilitar federación con RENATA

### Schema activo: "Esquema de Extensión para Personas UPeU v2.2"
- **OID**: `b7d55017-599f-4f2f-9493-9f64bba62c5b`
- **Namespace**: `urn:upeu:midpoint:person`
- **Estado**: Active (production), última modificación 2026-02-09
- **Definido como SchemaType** en la GUI de MidPoint (no como XSD en carpeta `/var/schema/`)

#### Tipos definidos (7 ComplexType):

**DemographicsType** — datos demográficos
```
birthDate          (string, ISO 8601)    ≈ schacDateOfBirth
gender             (string, ISO 5218: 1=M, 2=F, 9=N/A)
country            (string, ISO 3166-1 alpha-3)   ≈ schacCountryOfResidence
province           (string)
streetAddress      (string)
```

**ContactInfoType** — contacto adicional
```
secondaryMail      (string, multivalor)
phoneNumberAlt     (string)
personalWeb        (string)
```

**EmploymentDataType** — fechas laborales
```
hireDate           (date)
terminationDate    (date)               → usar para Leaver policy
```

**AffiliationDataType** — afiliación institucional
```
primaryAffiliationCode  (string, indexed)   ≈ eduPersonPrimaryAffiliation
primaryAffiliationName  (string)
languageSkills          (string)
campus                  (string)            → sede/campus UPeU
employeeType            (string, multivalor, indexed)
```

**AcademicStatusType** — estado académico
```
studentCycle       (int, multivalor)    → ciclo académico actual
academicProgram    (string, multivalor) → nombre del programa
academicProgramCode (string, multivalor, indexed) → siglas
alumniStatus       (string)            → estado de egreso
studyModality      (string, multivalor) → presencial/virtual/etc
```

**FederatedIdentityType** — identidad federada
```
orcid              (string, indexed)    ≈ eduPersonOrcid
```

**UniqueIdentifiersType** — identificadores complementarios
```
taxId              (string, indexed)    ≈ schacPersonalUniqueCode (DNI/CE)
institutionalIdCard (string, indexed)  → ID institucional
universityIdCard   (string, indexed)   → carnet universitario
externalSystemId   (string, indexed)   → ID en sistema externo (SIS, ERP)
```

### Mapeo a estándares (referencia)
| Campo v2.2 | Equivalente eduPerson/SCHAC | Nota |
|-----------|----------------------------|------|
| `taxId` | `schacPersonalUniqueCode` | DNI peruano |
| `birthDate` | `schacDateOfBirth` | |
| `country` | `schacCountryOfResidence` | |
| `orcid` | `eduPersonOrcid` | |
| `primaryAffiliationCode` | `eduPersonPrimaryAffiliation` | |
| `employeeType` | `eduPersonAffiliation` | multivalor |
| `externalSystemId` | — | ID en Lamb Academic |

## Fuente de verdad

- **Sistema**: DB Lamb Academic (SIS/ERP académico UPeU)
- **Estado actual**: réplica en `academico_db` (PostgreSQL, puerto 5433) corriendo en servidor de pruebas
- **Tipo de conexión**: por confirmar — ¿PostgreSQL directo vía JDBC o API REST?
- **Datos clave**: email institucional (IUD), DNI, código universitario, nombres, rol, estado de matrícula/contrato, fecha de expiración

## Estrategia de correlación

1. `extension/sisId` (Primary) — identificador único del SIS, evita colisiones
2. `emailAddress` (Secondary) — respaldo para fuentes sin sisId
3. DNI / `schacPersonalUniqueCode` (Sanity check)
4. Revisión manual — si no hay coincidencia, la tarea genera reporte y el operador decide

## Ciclo de vida

### Estudiantes (StudentType)
- **Joiner**: alumno se matricula → MidPoint crea cuenta
- **Mover**: cambio de carrera/rol → MidPoint actualiza atributos y roles
- **Leaver**: fin de matrícula → desactivar, mover a OU alumni, revocar roles; acceso 6 meses post-egreso

### Docentes (ProfessorType)
- **Alta**: desde SIS o RRHH
- **Suspensión**: `administrativeStatus=disabled` cuando RRHH reporte pausa
- **Leaver**: desactivación 30 días post fin de contrato; conservar correo para reingresos

### Personal Administrativo/Técnico
- **Alta**: desde RRHH
- **Leaver**: desactivación diferida 15 días para transferencia de conocimiento
- **Borrado**: manual post-auditoría

## Aprovisionamiento especial

- **JIT en Keycloak**: primer login crea usuario local mapeando atributos desde EntraID
- **Koha**: creación del registro de lector con email (IUD), DNI, cardnumber, nombres, expiración
- **Active Directory**: OU dinámica por arquetipo; grupos base por tipo de usuario

### OUs en AD
```
OU=Students,OU=Accounts,DC=upeu,DC=edu,DC=pe
OU=Professors,OU=Accounts,DC=upeu,DC=edu,DC=pe
OU=Staff,OU=Accounts,DC=upeu,DC=edu,DC=pe
OU=Groups,DC=upeu,DC=edu,DC=pe
```

### Grupos base
```
GRP-UPEU-Students-Base
GRP-UPEU-Professors-Base
GRP-UPEU-Staff-Base
```

## Infraestructura

### Servidor de PRODUCCIÓN ← activo desde 2026-04-15
- **Host**: 192.168.15.166 (user: juansanchez)
- **SSH alias**: `midpoint-prod`
- **Credenciales**: `~/.secrets/midpoint-upeu.env`
- **URL pública**: `https://identity.upeu.edu.pe/midpoint`
- **SSL**: wildcard `*.upeu.edu.pe` emitido por GoDaddy — gestionado por Rudy en `192.168.12.199`
- **RAM**: 9.7 GB / disco 17 GB

#### Contenedores en producción
| Contenedor | Imagen | Puerto |
|-----------|--------|--------|
| `midpoint_server` | evolveum/midpoint:4.9.5-ubuntu | 8080 (interno) |
| `midpoint-midpoint_data-1` | postgres:16-bullseye | 5432 (solo red Docker) |

#### Estructura en el servidor
```
/opt/midpoint/
├── docker-compose.yml   → compose de producción con mem_limits, healthchecks
├── .env                 → secretos (chmod 600) — NO versionar
└── connectors/
    └── connector-koha-1.1.0.jar
/var/lib/docker/volumes/
├── midpoint_midpoint_data/   → datos PostgreSQL (permanente)
└── midpoint_midpoint_home/   → var/ de MidPoint: keystore, logs, config
```

#### Notas de operación (prod)
- `JAVA_OPTS=-Xms1g -Xmx2560m` — heap controlado
- `restart: unless-stopped` en todos los servicios
- Logging con rotación: json-file max-size 100m, max-file 5
- Firewall: reglas iptables para subnet Docker `172.18.0.0/16` guardadas en `/etc/iptables/rules.v4`
- `publicHttpUrlPattern` vacío — MidPoint usa la URL del request (sin redirecciones forzadas)

### Migración futura a AWS
- Stack Docker Compose es directamente portable a EC2
- Exportar volúmenes `midpoint_data` y `midpoint_home` + mismo docker-compose.yml

## Repositorios

| Repo | Rol | Estado |
|------|-----|--------|
| `UPeU-Infra/midPointEcosystem` | Config GitOps UPeU (principal) | Activo, 63 commits |
| `UPeU-Infra/connector-koha` | Conector Java ConnId para Koha | Activo, v1.0.2 |
| `UPeU-Infra/upeu-midpoint-config` | Backup legacy | Archivar |
| `SciBack/midpoint` (este repo) | Plantilla genérica SciBack | En construcción |

### Estrategia de repos
- `midPointEcosystem` → config específica UPeU, variables parametrizadas (`{{AD_HOSTNAME}}`, etc.)
- `connector-koha` → artefacto Java independiente con su propio ciclo de release
- `upeu-midpoint-config` → archivar en GitHub
- Este repo (`sciback/midpoint`) → plantilla replicable para nuevos clientes SciBack

## Objetos MidPoint configurados en midPointEcosystem

### Arquetipos
- `StudentType`, `ProfessorType`, `AdministrativeStaffType`, `TechnicalStaffType`

### Recursos
- `UPEU-EntraID-Graph.xml` — Graph API (EntraID)
- `UPEU-AD.xml` — Active Directory
- `SIS-CSV.xml` — SIS vía CSV (activo en fase 1)
- `resource-academico-legacy.xml` — SIS vía JDBC (fase futura)
- `CRM-CSV-skeleton.xml`, `RRHH-CSV-skeleton.xml` — fase 2

### Roles
- `Role-Student`, `Role-Professor`, `Role-Staff`

### Organización
- `000-UPeU-root`, `010-Facultades`, `020-Rectorado`, `030-AreaTecnologia`, `040-Posgrado`

### Tareas (todas en modo simulación)
- `task-import-SIS-simulation`
- `task-reconcile-SIS-simulation`
- `task-reconcile-AD-simulation`

### Auth
- `oidc-entra-id.xml` — autenticación OIDC con EntraID

### Templates y políticas
- `UserTemplate-UPEU.xml` — plantilla de usuario
- `policy-sod-basic.xml`, `policy-owners-required.xml`

### Mapeo de atributos (estado actual — pendiente migrar a esquema SCIM+eduPerson+upeu:)

**Inbound SIS CSV → MidPoint:**
| CSV | MidPoint actual | MidPoint objetivo |
|-----|-----------------|-------------------|
| `givenName` | `c:givenName` | `name.givenName` (SCIM) |
| `familyName` | `c:familyName` | `name.familyName` (SCIM) |
| `email` | `c:emailAddress` | `emails[work]` (SCIM) |
| `uid` | `extension/sisId` | `upeu:codigoUniversitario` |
| `archetype` | `archetypeRef` | `archetypeRef` |
| `orgCode` | `extension/orgCode` | `upeu:facultad` |

**Outbound MidPoint → AD:**
| MidPoint | AD |
|----------|----|
| `name` | `sAMAccountName` |
| `name` + sufijo | `userPrincipalName` → `@upeu.edu.pe` |
| `fullName` | `cn` |
| `emailAddress` | `mail` |
| `archetypeRef` | `ou` (dinámica) |
| `assignments` | `group` (entitlement) |

## Gestión de configuración (GitOps)

1. **MidPoint Studio** (IntelliJ) conectado a instancia local para editar XMLs
2. **Git** como fuente de verdad de todos los objetos
3. **ninja CLI** o **REST API** para importar/exportar al servidor

## Decisiones técnicas pendientes

- [ ] Confirmar tipo de acceso a DB Lamb Academic en producción (JDBC directo vs API)
- [ ] Confirmar si UPeU tiene AD on-premise activo (además de EntraID)
- [ ] Migrar atributos de `UserTemplate-UPEU.xml` al esquema SCIM 2.0 + eduPerson + SCHAC + `upeu:`
- [ ] Actualizar `naming-conventions.md` alineado a ISO 24760 y eduPerson
- [ ] Definir periodo oficial de retención post-egreso para alumnos (draft: 6 meses)
- [ ] Definir proceso formal de borrado de cuentas post-auditoría
- [ ] Parametrizar rutas CSV en docker-compose para despliegue GitOps
- [ ] Configurar restart automático de midpoint_server (cron o docker healthcheck policy)
- [ ] Archivar repo `upeu-midpoint-config` en GitHub
- [ ] Definir estrategia de OIDs para nuevos objetos (tabla en naming-conventions)

## Herramientas de Trabajo

### Agente especializado MidPoint
- **Ubicación:** `~/.claude/agents/midpoint-expert.md`
- **Capacidades:** consultoría, edición de XMLs, despliegue via REST API y ninja CLI
- **Conocimiento base:** libro "Practical Identity Management with MidPoint" v2.3 + contexto UPeU/SciBack
- **Cuándo usar:** cualquier tarea de configuración MidPoint en este proyecto

### Acceso REST API
```bash
# Base URL (desde el servidor)
http://localhost:8080/midpoint/ws/rest
# Credenciales pre-producción
administrator:Test5ecr3t
```

### ninja CLI (dentro del contenedor)
```bash
docker exec midpoint_server /opt/midpoint/bin/ninja.sh --help
```

## Estado real del servidor (auditado 2026-04-15)

### DESARROLLO (192.168.15.230)
| Objeto | Estado |
|--------|--------|
| Recurso Lamb Academic | UP — JDBC directo a `academico_db:5433`, tabla `estudiantes` |
| Recurso Azure EntraID | UP |
| Recurso Koha | UP — conector v1.1.0 (OID: bb389d70-04b3-44de-9dde-4789b1c46121) |
| Recurso AD | No importado (solo en Git) |
| Arquetipos de negocio | 4 activos: Docente, Estudiante, PersonalAdministrativo, Egresado |
| Orgunits | 88 (campus Lima, Juliaca, Tarapoto) |
| Roles | 67 (GOV-*, MOF-*, SYS-*) |
| Schema v2.2 | Activo y funcionando |
| Usuarios ficticios en BD | 10 cargados (prefijo sci-*) — dominio @sciback.edu |
| Validity Scanner | Suspendido |
| Trigger Scanner | Suspendido |

### PRODUCCIÓN (192.168.15.166) — desplegado 2026-04-15
| Objeto | Estado |
|--------|--------|
| MidPoint 4.9.5 | UP, healthy — `https://identity.upeu.edu.pe/midpoint` |
| PostgreSQL 16 | UP, healthy — solo red interna Docker |
| Conector Koha | v1.1.0 registrado en `/opt/midpoint/connectors/` |
| Recursos | Ninguno aún — fuente de verdad pendiente de definir |
| Arquetipos UPeU | 4 activos: Docente, Estudiante, PersonalAdministrativo, Egresado |
| Arquetipos built-in | 57 (MidPoint system archetypes) |
| OrgUnits | 88 (campus Lima, Juliaca, Tarapoto) |
| Roles | 35 (GOV-*, MOF-*, SYS-*, BR-*, APP-*) |
| Schema v2.2 | Activo — OID b7d55017 |
| Object Template | UserTemplate-UPEU — OID 11a9fc09 |
| Usuarios | Solo `administrator` |
| Validity Scanner | Suspendido |
| Trigger Scanner | Suspendido |
| Tasks limpias | Sin historial de dev (18 eliminadas) |

### OIDs clave
| Objeto | OID |
|--------|-----|
| Recurso Lamb Academic | e44293b6-0d8c-4e6e-b12f-8f69323a4a21 |
| Recurso Azure EntraID | 6927a3ed-8842-4a42-8594-39a48aa97585 |
| Recurso Koha | 63e8f5cc-4275-4526-88b8-57e76881eb08 |
| UserTemplate-UPEU | 11a9fc09-9b4b-4fe3-9ff5-8c9b5a4d440f |
| Schema extensión v2.2 | b7d55017-599f-4f2f-9493-9f64bba62c5b |

### Acciones completadas (2026-04-09)
- [x] connector-koha refactorizado → v1.1.0 (76 tests, 0 failures)
- [x] connector-koha v1.1.0 desplegado en MidPoint y recurso Koha actualizado
- [x] /etc/hosts configurado en pruebas-alberto-1: 192.168.15.135 bul.myDNSname.org
- [x] BD académica: email nullable + 10 usuarios ficticios sci-* cargados
- [x] Script reset: scripts/db/seed-usuarios-ficticios.sql + reset-test-data.sh
- [x] UserTemplate-UPEU: email validación/generación, nickName, activation default weak
- [x] SciBack/midpoint repo creado en GitHub + Vercel https://sciback-iga-demo.vercel.app
- [x] Configurar restart automático de `midpoint_server`
- [x] Suspender Validity Scanner (OID: `00000000-0000-0000-0000-000000000006`)
- [x] Suspender Trigger Scanner (OID: `00000000-0000-0000-0000-000000000007`)

### Acciones completadas (2026-04-15)
- [x] Servidor de producción 192.168.15.166 instalado con Docker + MidPoint 4.9.5
- [x] Docker Compose de producción: mem_limits, healthchecks, logging con rotación, secrets en .env
- [x] Connector Koha v1.1.0 copiado a `/opt/midpoint/connectors/`
- [x] Objetos UPeU importados desde dev: arquetipos, roles, orgUnits, template, schema, políticas, dashboard
- [x] Tasks de historial de dev eliminadas (18 eliminadas)
- [x] Validity Scanner y Trigger Scanner suspendidos en prod
- [x] Dominio `identity.upeu.edu.pe` configurado por Rudy (proxy en 192.168.12.199, SSL GoDaddy *.upeu.edu.pe)
- [x] Reglas iptables FORWARD para red Docker guardadas permanentemente
- [x] ClaudeFlow instalado globalmente en ~/.claude/
- [x] CLAUDE.md del proyecto creado
- [x] Agente midpoint-expert actualizado con servidor de producción

### Pendientes definidos
- [ ] Bloqueo por deuda Koha (debarred) → afecta acceso a servicios — **política sin definir, trabajar después**
- [ ] Ejecutar primera importación real desde BD académica (10 usuarios ficticios)
- [ ] Verificar end-to-end: email conservado/generado → EntraID → Koha
- [ ] Configurar activación/desactivación (Enabled/Disabled) en recursos
- [ ] Importar recurso AD
- [ ] Auditar `UserTemplate-UPEU.xml` → migrar atributos al esquema SCIM+eduPerson+upeu:
- [ ] Definir política de retención post-egreso (draft: 6 meses)
- [ ] Archivar repo `upeu-midpoint-config` en GitHub

## Próximos pasos inmediatos

1. **Importación end-to-end** — ejecutar importación de los 10 usuarios ficticios y verificar:
   - Email conservado vs generado según caso
   - Propagación a Azure EntraID
   - Propagación a Koha
2. Configurar activación/desactivación en los recursos (Enabled/Disabled)
3. Importar recurso AD

## Referencias

- Diagrama de arquitectura: `~/Downloads/Ciclo de vida y Autenticación de usuarios UPeU.drawio`
- Vault Obsidian: `~/obsidian/sciback/` (documentación estratégica)
- MidPoint docs: https://docs.evolveum.com/midpoint/
- MidPoint Studio (IntelliJ plugin): https://plugins.jetbrains.com/plugin/13809-midpoint-studio
- eduPerson spec: https://www.internet2.edu/media/medialibrary/2013/09/04/internet2-mace-dir-eduperson-201310.html
- SCHAC spec: https://wiki.refeds.org/display/STAN/SCHAC
- SCIM 2.0: RFC 7643 / RFC 7644
- RENATA (red académica Colombia/Latam): https://www.renata.edu.co
