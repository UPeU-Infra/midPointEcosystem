# UPeU IGA — Arquitectura del Sistema

**Versión:** 2026-06-06
**Estado:** Operativo en producción (192.168.15.166)

---

## 1. Diagrama de flujo general

```
============================================================
  FUENTES AUTORITATIVAS (solo lectura)
============================================================

Oracle LAMB (192.168.13.9:1521/UPEU) — ERP institucional
  Schemas: MOISES / DAVID / ELISEO / ENOC / JOSUE

  ├── MOISES  ─── Trabajadores (HR: contratos, puestos, nómina)
  ├── DAVID   ─── Estudiantes y Egresados (SIS: matrículas, grados)
  ├── ELISEO  ─── Org y Posiciones (estructura organizacional)
  ├── ENOC    ─── Carga docente (semestres, asignaciones)
  └── JOSUE   ─── Académico complementario

  Política: SOLO LECTURA. Nunca se escribe en Oracle LAMB.

============================================================
  NÚCLEO IGA
============================================================

MidPoint 4.10.2 (192.168.15.166:8080)
  Docker · Ubuntu 22.04 · ~6 GB RAM

  Resources INBOUND activos (6):
  ├── oracle-lamb/trabajadores.xml      → employee-faculty + employee-staff
  ├── oracle-lamb/estudiantes.xml       → student
  ├── oracle-lamb/egresados.xml         → alumni
  ├── oracle-lamb/grados.xml            → grados y títulos
  ├── oracle-lamb/org.xml               → OrgType (199 orgs tipificadas)
  └── oracle-lamb/posiciones.xml        → ServiceType (posiciones laborales)

  Población (2026-06-06):
  ├── ~50K+ usuarios (active ~41K / archived ~8K / draft ~1K)
  ├── 199 OrgType (institution + campus + faculties + departments + governance + partner-institutions)
  ├── ~70+ roles (ARs + BRs + MOFs + GOVs)
  └── 18 archetypes custom (8 user + 8 org + 2 role)

  Schemas:
  ├── urn:sciback:midpoint:person  (canónico — capa 1)
  └── urn:upeu:midpoint:local      (overlay UPeU — capa 2)

  Object Templates (5):
  ├── UserTemplate-Person-Base          (base común)
  ├── UserTemplate-Alumni               (archetype-user-alumni)
  ├── UserTemplate-Student              (archetype-user-student)
  ├── UserTemplate-Employee-Faculty     (archetype-user-employee-faculty)
  └── UserTemplate-Employee-Staff       (archetype-user-employee-staff)

  RBAC (Fase 7 — completa 2026-06-06):
  ├── ARs: DSpace-Editor, OJS-Author/Reader/Reviewer, Koha-Patron-*, LDAP-*
  ├── BRs: BR-Personal-General, BR-Docente-TC/TP, BR-Estudiante-*, BR-Bibliotecario...
  ├── MOFs: ~25 roles de función operativa
  ├── GOVs: GOV-APROBADOR, GOV-REVISOR, GOV-AUDITOR
  └── SoD: GOV-APROBADOR ⊥ GOV-REVISOR (ISO 27001 A.8.2 / NIST AC-5)

  Pipeline JML:
  ├── Trigger Scanner: cada 5 min
  ├── Validity Scanner: cada 15 min
  ├── Reconcile LAMB Trabajadores: cron 02:00 UTC
  ├── Reconcile LAMB Estudiantes: cron 02:00 UTC
  ├── Reconcile LAMB Egresados: cron 02:00 UTC
  └── Reconcile Koha: cron 03:00 UTC

============================================================
  TARGETS OUTBOUND
============================================================

Target 1 — OpenLDAP HA Identity Cache
  Node1: 192.168.15.168:389  ═══ N-Way Multimaster ═══  Node2: 192.168.15.169:389
  37K+ entradas · DIT: dc=upeu,dc=edu,dc=pe
  Cuentas: cn=midpoint (write) · cn=keycloak (read)
  Schemas LDAP: inetOrgPerson + eduPerson + SCHAC
  Resource LDAP en MidPoint: LDAP-IdentityCache-UPeU (lifecycleState=active)

Target 2 — Koha ILS (Biblioteca)
  192.168.15.x — Conector pe.upeu.connector.koha-http v1.3.10
  19,721 borrowers activos
  Categorías: student, faculty, staff, ESTUDI (legacy)
  Provisioning: outbound desde MidPoint activo
  Gate multi-campus: solo Lima (campusStudent='LIMA' || campusWorker='LIMA')

Target 3 — Entra ID UPeU (READ-ONLY por ahora)
  Tenant: upeu.edu.pe — App: MidPoint-UPeU (appId 94dd7b5b)
  ~50K shadows (21K LINKED · 28K UNMATCHED)
  Permisos actuales: User.Read.All + Group.Read.All + Directory.Read.All
  Write bloqueado hasta Fase 12 (permisos pendientes con David Urquizo)

Target 4 — OpenLDAP via Keycloak (SSO — Fase 13 pendiente)
  Ver sección 3 para flujo completo

============================================================
  SSO / FEDERACION
============================================================

Keycloak 26.6.1 (192.168.12.88, realm upeu)
  User Federation LDAP: ACTIVA → lee Node1 OpenLDAP
  Protocol mappers SAML: PENDIENTE (Fase 13)
      |
      | SAML 2.0 (PENDIENTE configurar SPs)
      v
Vendors académicos: Scopus · WoS · EBSCO · ProQuest · JSTOR · IEEE · ...
  Atributos requeridos: ePPN + ePSA + mail + displayName + schacHomeOrganization
```

---

## 2. Capas del modelo

### Capa 1 — Canónica (agnóstica de institución)

Directorio: `canonical/`

Piezas reutilizables para cualquier universidad peruana:

| Artefacto | Ubicación | Descripción |
|---|---|---|
| Schema `urn:sciback:midpoint:person` | `canonical/schemas/sciback-person-v1.0.xml` | Atributos no cubiertos por eduPerson/SCHAC/SCIM |
| 8 archetypes UserType | `canonical/archetypes/user/` | student, faculty, staff, alumni, affiliate-*, contractor, service-account |
| 8 archetypes OrgType | `canonical/archetypes/org/` | institution, campus, faculty, department, academic-unit, governance, partner-institution, project |
| 2 archetypes RoleType | `canonical/archetypes/role/` | application-role, business-role |
| Object templates | `canonical/object-templates/` | UserTemplate-Person-Base + 4 per-archetype |
| Roles canónicos | `canonical/roles/` | Affiliation roles, Application roles genéricos |
| Policies | `canonical/policies/` | SoD policies, governance policies |

### Capa 2 — Overlay UPeU (específico de la universidad)

Directorio: `upeu/`

| Artefacto | Ubicación | Descripción |
|---|---|---|
| Schema `urn:upeu:midpoint:local` | `upeu/schemas/upeu-local-v1.0.xml` | Campos específicos LAMB (lambDocNum, laboralStatus, etc.) |
| Resources Oracle LAMB | `upeu/resources/oracle-lamb/` | 6 resources JDBC con vistas MOISES/DAVID/ELISEO/ENOC |
| Resource Koha ILS | `upeu/resources/koha-ils.xml` | Conector Koha v1.3.10 |
| Resource LDAP | `upeu/resources/ldap-identity-cache.xml` | OpenLDAP HA |
| Resource Entra ID | `upeu/resources/entra-id-graph.xml` | Microsoft Graph (read-only) |
| OrgTree UPeU | `upeu/orgs/` | 199 orgs del árbol institucional UPeU |
| Roles UPeU-específicos | `upeu/roles/` | MOFs, GOVs, application roles UPeU |
| Tasks | `upeu/tasks/` | Reconcile tasks, bootstrap tasks |
| LDAP config | `upeu/ldap/` | Docker Compose, LDIFs, config HA |

---

## 3. Flujo SSO académico (estado y pendientes)

### Flujo completo (cuando Fase 13 esté implementada)

```
Usuario (browser)
      |
      | 1. Solicita acceso a Scopus/WoS/EBSCO
      v
Keycloak 26.6.1 (IdP SAML 2.0)
      |
      | 2. Consulta OpenLDAP (User Federation)
      v
OpenLDAP HA (Identity Cache)
      |  uid, mail, displayName, eduPersonAffiliation,
      |  eduPersonScopedAffiliation, schacHomeOrganization, ...
      |
      | [estos atributos los provisiona MidPoint]
      v
MidPoint 4.10.2
      |  - archetype = employee-faculty → ePSA = faculty@upeu.edu.pe
      |  - parentOrgRef → ou = Facultad de Ingeniería
      |  - name@upeu.edu.pe → ePPN
      v
Oracle LAMB (fuente original)
```

### Estado actual de cada paso

| Paso | Estado | Notas |
|---|---|---|
| Oracle LAMB → MidPoint (inbound) | OPERATIVO | 6 resources activos, reconcile 02:00 UTC |
| MidPoint → OpenLDAP (outbound) | OPERATIVO | 37K+ sombras, resource activo |
| OpenLDAP HA Multimaster | OPERATIVO | Node1 + Node2, replicación bidireccional |
| Keycloak User Federation LDAP | ACTIVA | Lee de Node1 OpenLDAP |
| Outbound mappings eduPerson en LDAP | PENDIENTE | ePPN, ePSA, schacHomeOrg no mapeados aún |
| Protocol mappers SAML en Keycloak | PENDIENTE | Fase 13 |
| Registro de SPs de vendors | PENDIENTE | Fase 13 |

---

## 4. Resources activos en PROD

| Resource | Tipo | Lifecycle | Shadows | Notas |
|---|---|---|---|---|
| Oracle LAMB Trabajadores | JDBC inbound | active | ~4K | Schemas MOISES/ENOC/ELISEO |
| Oracle LAMB Estudiantes | JDBC inbound | active | ~12K | Schema DAVID |
| Oracle LAMB Egresados | JDBC inbound | active | ~31K | Schema DAVID |
| Oracle LAMB Grados | JDBC inbound | active | — | Grados y títulos (DAVID) |
| Oracle LAMB Org | JDBC inbound | active | 199 orgs | Schema ELISEO |
| Oracle LAMB Posiciones | JDBC inbound | active | ~741 | Schema ELISEO |
| LDAP-IdentityCache-UPeU | LDAP outbound | active | 37K+ | OpenLDAP HA |
| Koha ILS | HTTP outbound | active | 19.7K | Conector v1.3.10 |
| UPEU-EntraID-Graph | Graph inbound | active | 50K+ | Read-only. Write: Fase 12 |

---

## 5. Árbol organizacional UPeU (resumen)

```
UPeU (institution)
├── Campus Lima (C-LIM)
│   ├── Facultad de Ingeniería y Arquitectura (FIA)
│   ├── Facultad de Ciencias Empresariales (FCE)
│   ├── Facultad de Teología (FACTEO)
│   ├── ... (5 facultades + EPG + unidades académicas)
│   ├── DTI (department / governance)
│   └── ... (unidades de gestión)
├── Campus Juliaca (C-JUL)
│   └── ... (facultades + unidades)
├── Campus Tarapoto (C-TPP)
│   └── ... (facultades + unidades)
└── Partner Institutions (org-partner-institution)
    ├── Colegio Unión (AREA-97)
    ├── CAT (Centro Adventista Tarapoto)
    └── CU-Tarapoto
```

Total: 199 OrgType activos — 1 institution + 3 campus + 5 faculty + 5 partner-institution + 13 governance + 33 academic-unit + 116 department + 23 academic-program.

---

## 6. Decisiones arquitecturales (no negociables)

| Decisión | Fecha | Detalle |
|---|---|---|
| Sin conector MidPoint→Keycloak | 2026-05-11 | Arquitectura: MidPoint→OpenLDAP←Keycloak. Conector HTTP custom archivado. |
| AD UPeU fuera del alcance | 2026-05-11 | AD actual (192.168.13.150) mal estructurado, no global. Sin reads ni writes. Decisión sobre AD nuevo diferida a Fase 12. |
| Entra ID read-only hasta Fase 12 | 2026-05-11 | Solo correlación e inventario. Write requiere permisos Graph API (pendiente David Urquizo). |
| Oracle LAMB solo lectura | Siempre | Política absoluta. Nunca se escribe en Oracle. |
| GitOps | Siempre | Config → commit → push → git pull en PROD. Nunca scp. |
| Identificador canónico = código institucional | 2026-06-01 | `name == código LAMB`. DNI va en `identityDocuments[]` / `schacPersonalUniqueID`. Ver `DECISION-canonical-identifier.md`. |
| Archetype estructural único | Siempre | Un structural archetype por usuario. Transiciones = lifecycle events. |
| Stack Microsoft 365 | 2026-05-11 | UPeU usa M365 (A1/A3), no Google Workspace. Koha ILS como target de biblioteca. |

---

## 7. Servidor de producción

| Parámetro | Valor |
|---|---|
| Host alias SSH | `midpoint-prod` |
| IP | 192.168.15.166 |
| Usuario | juansanchez |
| MidPoint URL | http://192.168.15.166:8080/midpoint |
| Versión MidPoint | 4.10.2 |
| Runtime | Docker · Ubuntu 22.04 · ~9 GB RAM |
| Repo GitOps | `/home/juansanchez/midPointEcosystem/` |
| Credenciales | `~/.secrets/midpoint-upeu.env` (`$MIDPOINT_PROD_PASS`) |

Acceso SSH:
```bash
source ~/.secrets/midpoint-upeu.env
sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod "<comando>"
```

---

## 8. Estado de fases del roadmap (2026-06-06)

| Fase | Descripción | Estado |
|---|---|---|
| 0 | Refactor doctrinal | COMPLETA |
| 1 | Schema canónico | ACTIVO EN PROD |
| 2 | Archetypes + Org tree | COMPLETA |
| 3 | Object templates | COMPLETA |
| 4 | OpenLDAP HA Identity Cache | COMPLETA |
| 5 | Resources READ | ACTIVO EN PROD |
| 6 | Resources WRITE OpenLDAP | VALIDADO |
| 7 | RBAC bottom-up | COMPLETA (2026-06-06) |
| 8 | Replanteo documentación | COMPLETA (2026-06-06) |
| 9 | Validación piloto end-to-end | PENDIENTE |
| 10 | Deploy PROD ordenado | PROD YA OPERATIVO (deploy incremental en curso) |
| 11 | Productización SciBack | PENDIENTE |
| 12 | Gobierno Entra ID (write) | DIAGNÓSTICO LISTO — bloqueado por permisos David Urquizo |
| 13 | Métricas COUNTER + SSO vendors | PENDIENTE |

---

## 9. Documentos relacionados

- `docs/ROADMAP.md` — Roadmap detallado con estimaciones y tareas por fase
- `docs/DECISION-canonical-identifier.md` — Decisión sobre `name == código institucional`
- `docs/canonical/sso-academic-vendors.md` — Mapeo eduPerson para vendors académicos
- `docs/canonical/eduperson-reference.md` — Diccionario de atributos eduPerson
- `docs/ENTRA-ID-ESTRUCTURA-UPEU.md` — Diagnóstico Entra ID UPeU
- `docs/runbooks/openldap-ha-replication.md` — Runbook OpenLDAP HA
- `docs/runbooks/keycloak-ldap-federation.md` — Runbook Keycloak User Federation
- `docs/runbooks/upgrade-midpoint-docker.md` — Runbook upgrade MidPoint
- `docs/specs/sciback-iga-blueprint/01-iga-blueprint-peru.md` — Blueprint IGA para universidades peruanas
