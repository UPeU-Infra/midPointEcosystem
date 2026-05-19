# AUDITORÍA DE CONSOLIDACIÓN — Modelo IGA UPeU

**Fecha:** 2026-05-19
**Autor:** midpoint-expert (consultando `iga-canonical-standards` v2026-05 + `midpoint-best-practices` v2024-11)
**Objeto:** Eliminar la confusión entre `SciBack/midpoint` y `UPeU-Infra/midPointEcosystem`, dejando UN solo repo con 2 capas (canonical/upeu) dentro de `midPointEcosystem`.
**Estado:** AUDIT ONLY — sin migrar, sin borrar.
**Autoridad:** Libro Semančík v2.3 (capítulos 6-10) + estándares (eduPerson 202208, SCHAC 1.6.0, NIST RBAC INCITS 359, ISO 24760, NIST 800-63-3, ISO 27001 A.5/A.8).

---

## TL;DR (lectura de 30 segundos)

1. **PROD opera exclusivamente desde `midPointEcosystem`** (verificado: `/home/juansanchez/midPointEcosystem/` en `192.168.15.166`). El repo padre `SciBack/midpoint` NO está clonado en PROD.
2. **El modelo IGA real está en PROD y en `midPointEcosystem`** (18 archetypes canónicos activos, 7 resources, 35.450 USER, 122 ORG, 72 ROLE, 2 schemas `urn:sciback:midpoint:person` + `urn:upeu:midpoint:local`). Los OIDs aplicados en PROD coinciden 1-a-1 con los XMLs de este repo.
3. **`SciBack/midpoint` quedó como sandbox de diseño** con XMLs canónicos "limpios" sin OIDs reales (drafts) + documentación rica (1.739 líneas de docs canónicos rescatables) + un conector keycloak-http archivado (decisión doctrinal 2026-05-11).
4. **La separación canonical/upeu YA EXISTE conceptualmente** en los schemas vivos en PROD: `urn:sciback:midpoint:person` (canónico) y `urn:upeu:midpoint:local` (overlay). La estructura propuesta del repo simplemente formaliza esta partición a nivel de directorios.
5. **MidPoint PROD está actualmente en OutOfMemoryError** (post-upgrade 4.10.2 que ocurrió hoy). El REST API no responde, pero el repo Postgres + LDAP fueron consultados directamente para producir esta auditoría.

---

## Metodología

- Skills consultadas ANTES de cualquier decisión: `iga-canonical-standards` (estándares), `midpoint-best-practices` (libro Semančík).
- Acceso REST a PROD: bloqueado (OOM, ver §8.1) → inventario hecho vía SQL directo sobre Postgres `midpoint`.
- Acceso OpenLDAP: `ldapsearch` desde dentro del contenedor `openldap` en `ldap-upeu` con bind admin.
- Acceso Keycloak: `kcadm.sh` desde dentro del contenedor `keycloak_app`.
- Acceso Oracle LAMB: bloqueado para Python 3 thin mode (Oracle 11g R2 no soportado). Gap documentado en §8.4. Política `policy_oracle_readonly.md` respetada: 0 escrituras.

---

## Sección 1 — Estado real de PROD (lo que está corriendo HOY)

### 1.1 MidPoint PROD — `192.168.15.166` (alias `midpoint-prod`)

| Item | Valor verificado |
|---|---|
| Hostname | `midpoint.upeu` |
| Kernel | Ubuntu 24.04, Linux 6.8.0-31 |
| Containers | `midpoint_server` (evolveum/midpoint:**4.10.2**-ubuntu, Up 5 h, **OOM**) + `midpoint-midpoint_data-1` (postgres:16-bullseye, Up 8 h, healthy) |
| Puertos host | 80 (nginx/reverse), 8080 (tomcat midpoint) |
| Repo en PROD | `/home/juansanchez/midPointEcosystem/` (corresponde a `UPeU-Infra/midPointEcosystem` main) |
| Backups en PROD | Solo logs y configs heredados; no repo `SciBack/midpoint` |

**Estado de salud:** `java.lang.OutOfMemoryError: Java heap space` en logs recientes. REST API responde `HTTP 000` (no responde). Ver §8.1.

**Inventario por tipo de objeto (DB directo, `m_object`):**

| Tipo objeto | Total | active | draft | archived | deprecated | sin lifecycle |
|---|---|---|---|---|---|---|
| USER | 35.450 | 34.624 | 719 | 106 | 0 | 1 |
| SERVICE | 741 | — | — | — | — | 741 |
| ORG | 122 | 16 | — | — | — | 106 |
| ARCHETYPE | 86 | 18 | — | — | — | 68 (built-in) |
| ROLE | 72 | 39 | — | — | 1 | 32 |
| TASK | 69 | — | — | — | — | 69 |
| MARK | 39 | — | — | — | — | 39 |
| OBJECT_COLLECTION | 31 | — | — | — | — | 31 |
| CONNECTOR | 15 | — | — | — | — | 15 |
| REPORT | 13 | — | — | — | — | 13 |
| RESOURCE | 7 | 5 | — | — | — | 2 (sin lifecycle) |
| LOOKUP_TABLE | 6 | — | — | — | — | 6 |
| POLICY | 3 | — | — | — | — | 3 |
| DASHBOARD | 2 | — | — | — | — | 2 |
| SCHEMA | 2 | 2 | — | — | — | — |
| OBJECT_TEMPLATE | 2 | 1 | — | — | — | 1 |
| CASE | 82 | — | — | — | — | 82 |
| Otros (POLICY, VALUE_POLICY, NODE, FUNC_LIB, SEC_POLICY, SYS_CONFIG) | varios | | | | | |

**Schemas activos en PROD (los únicos 2):**

| nameorig | oid | namespace | rol |
|---|---|---|---|
| SciBack IGA — Schema canónico universitario Perú v1.0 | `e800335c-9ca1-4a2d-b4ca-e06f6db42693` | `urn:sciback:midpoint:person` | **Capa canónica (agnóstica)** |
| UPeU — Schema local extensiones LAMB v1.0 | `64ed4155-147f-4081-89db-8d7e451d9c00` | `urn:upeu:midpoint:local` | **Capa overlay UPeU** |

> **Hallazgo doctrinal:** la separación canonical/upeu **ya está implementada a nivel de schema en PROD**. El refactor propuesto solo necesita formalizar esa partición en el árbol de directorios. Esto está alineado con `midpoint-best-practices` §1.4: extensions con namespace propio dentro del contenedor `<extension>`.

**Archetypes activos (18, todos lifecycle=active — alineado con `iga-canonical-standards` §10):**

| Familia | Archetypes | Modelo eduPerson | Cumple skill |
|---|---|---|---|
| User (8) | `archetype-user-student`, `…-employee-faculty`, `…-employee-staff`, `…-affiliate-partner-institution`, `…-affiliate-researcher`, `…-alumni`, `…-contractor`, `…-service-account` | student/faculty/staff/affiliate/alum + service-account custom (legítimo, NO eduPerson, NO publicar a SPs) | OK |
| Org (8) | `archetype-org-institution`, `…-campus`, `…-faculty`, `…-department`, `…-academic-unit`, `…-governance`, `…-partner-institution`, `…-project` | OrgType jerárquico canónico §5.3 | OK |
| Role (2) | `archetype-role-business`, `archetype-role-application` | RBAC INCITS 359 §6.4 — cascada BR→AR→Entitlement | OK |

**Archetypes built-in MidPoint (sin lifecycle, OOTB):** Person, Application, Business role, Application role, System role, System user, Position, Project, Team, Top-level organization, Organization, Organizational unit, Location, Academic-Program (custom), Affiliation-Role (custom), AuxAff-Alum, AuxAff-Faculty, AuxAff-Staff, AuxAff-Student (4 auxiliary archetypes).

> **Conflicto detectado con skill:** Los 4 `AuxAff-*` son **auxiliary archetypes** (multivalor). `midpoint-best-practices` §3.3 advierte: *"Auxiliary archetype soporte UI limitado en 4.9 — se recomienda **birthright roles** en su lugar."* En el repo se prefieren `R-Affiliation-*` (`R-Affiliation-Student`, etc.) como roles canónicos de afiliación. Hay redundancia entre los AuxAff-archetypes y los R-Affiliation-roles. Decidir en post-consolidación.

**Resources activos (7, los 5 con lifecycle=active son los principales):**

| Resource | OID | Lifecycle | Shadows en PROD |
|---|---|---|---|
| LDAP-IdentityCache-UPeU | `7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f` | (vacío) | 37.491 |
| UPEU-EntraID-Graph | `2f11c057-7b15-4641-a0eb-00c98a6fa4cb` | (vacío) | 37.304 |
| Oracle LAMB Egresados v3 | `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23` | active | 30.629 |
| Koha ILS | `9b5a7c81-47aa-42ac-9a08-4de8b64935af` | active | 5.421 |
| Oracle LAMB Trabajadores v3 | `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21` | active | 3.802 |
| Oracle LAMB Estudiantes v3 | `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22` | active | 1.679 |
| LAMB-Oracle-Posiciones | `f2422f42-90da-4ca4-a4db-78fe25a63245` | active | 738 |

**Connectors instalados (15):** Built-in (Async ×2, Manual) + CSV ×2 + LDAP ×2 + AD-LDAP ×2 + MSGraph ×1 + Koha (com.identicum.connectors.KohaConnector v1.2.0) ×1 + **Keycloak openstandia v1.1.7-SNAPSHOT (huérfano — NO hay Resource asociado)** + ScriptedSQL v2.2.10 + DatabaseTable ×2.

**Object templates (2):**
- `Person Object Template` (`00000000-0000-0000-0000-000000000380`) — built-in OOTB
- `UserTemplate-Person-Base` (`855caaca-68c4-4f7f-8ff8-b4e35dd7d390`, lifecycle=active) — el template real UPeU

> **Conflicto con skill:** `iga-canonical-standards` §10 y `midpoint-best-practices` §3.5 y §4.1 recomiendan **un object template por archetype** (granularidad por sub-tipo). UPeU tiene **un único template global** (`UserTemplate-Person-Base`). Es una decisión defendible (encapsulación) pero hay que justificarla. Ver §5 propuesta.

**Roles (72 = 39 active + 32 sin lifecycle + 1 deprecated):**
- **Application Roles (24):** AR-Koha-Patron-Student/Faculty/Staff, AR-Koha-Librarian, AR-Indico-User/EventManager, AR-DSpace-Submitter/Editor, AR-OJS-Reader/Author/Reviewer, AR-LDAP-Person, AR-WiFi-Estudiantes/Docentes/Staff, AR-M365-Student-A1/Faculty-A3/Staff-A3/Alumni-A1, AR-Vendor-Academic-Access, AR-EntraID-User, AR-Zoom-Basic/Pro.
- **Business Roles (12):** BR-Docente-TC/TP, BR-Estudiante-Pregrado/Posgrado/Doctorado, BR-Admin-Area, BR-Bibliotecario, BR-Investigador, BR-Egresado, BR-Decano, BR-Visitante-Investigacion, BR-Personal-General.
- **Affiliation Roles (6, todas R-):** R-Affiliation-Affiliate-CU, Alumni, Employee, Faculty, Staff, Student.
- **Governance Roles (3):** GOV-APROBADOR-WORKITEMS, GOV-DELEGADOR-PRIVILEGIOS, GOV-REVISOR-CERTIFICACION.
- **MOF Roles (≈25 MOF-*):** Manual Operativo Funciones UPeU — Coordinador, Decano, DGBU, DGFilial, Director, Director-EP, Director-CRAI, Jefe, Rector, VRA, VRADM, Secretaria-CRAI, etc. (mapeo funcional UPeU).
- **System (1):** SYS-IGA-SUPERUSER.
- **Built-in:** End user.
- **Deprecated (1):** **`APP-KOHA-PATRON`** (legacy V1 — superseded por AR-Koha-Patron-{Student,Faculty,Staff}).

**Function Libraries:** `sb-program-resolver` (1, alineado con namespace canonical `sb:`).
**Lookup Tables custom:** `program-resolver-lamb` (UPeU-specific). OOTB: Languages, Lifecycle States, Locales, States, Timezones.
**Object Collections:** 31 (mayor: `collection-personas-upeu` + 30 reportes).

**Org tree — distribución por subtype declarado en `m_org.subtypes`:**
- `academic-program`: 23 (los SKOS desde VocBench)
- (el resto de 122-23 = ~99 orgs sin subtype operacional explícito — Functional tree UPeU según jerarquía via `parentOrgRef`)

**Tasks (69):** masivo el contexto de operación reciente — múltiples runs de recompute, recon LAMB, fix dual-archetype, sync LAMB-Trabajadores-photoUrl, PILOT-EntraID-UPeU-link-100/link-photo-100. Ver §1.5.

### 1.2 OpenLDAP — `192.168.15.168` (alias `ldap-upeu`)

| Item | Valor verificado |
|---|---|
| Hostname | `ldap-identity-trust` |
| User | `juansanchez` |
| Container | `openldap` (osixia/openldap:1.5.0, Up 20h, healthy) + `phpldapadmin` (osixia/phpldapadmin:0.9.0, Up 4d) |
| Base DN | `dc=upeu,dc=edu,dc=pe` |
| Admin DN | `cn=admin,dc=upeu,dc=edu,dc=pe` |

> **Nota:** memoria `reference_ldap_upeu.md` indicaba "bitnami" como image; PROD usa `osixia/openldap:1.5.0`. Actualizar memoria post-consolidación.

**Estructura DIT real (`ldapsearch -s one`):**

```
dc=upeu,dc=edu,dc=pe  (objectClass: top, dcObject, organization)
├── ou=people          → 34.579 inetOrgPerson (sincronizados desde MidPoint)
├── ou=groups          → 0 entradas (vacío)
├── ou=services        → entradas service-account
└── cn=keycloak        → bind DN para Keycloak User Federation (Fase 6 planeada)
```

**Hallazgos:**
1. `ou=people` plano (no jerárquico) — confirmado en commits recientes f774754/ee7d88b.
2. RDN = `uid` (no `cn`) — confirmado en config Keycloak federation.
3. `ou=groups` está VACÍO en PROD: las app roles aún no proyectan grupos LDAP. Estado de mapping outbound de `groups`. Resolver tras consolidación.
4. Schemas custom cargados: no se verificaron en este audit (gap; requiere `ldapsearch -b cn=schema,cn=config`).

### 1.3 Keycloak — `192.168.12.88` (alias `keycloak-prod`)

| Item | Valor verificado |
|---|---|
| Hostname | `keycloak.upeu` |
| Containers | `keycloak_app` (quay.io/keycloak/keycloak:**26.6.1**, Up 4w, healthy) + `keycloak_db` (postgres:16) |
| Realms | `master`, `upeu` (ambos enabled=true) |

**Clients realm `upeu`:**
- OOTB: `account`, `account-console`, `admin-cli`, `broker`, `realm-management`, `security-admin-console`
- Custom: **`koha-upeu`**, **`indico-upeu`**, **`midpoint-provisioner`** (client_credentials para que MidPoint llame Keycloak Admin REST), **`guia-node`** (chatbot GUIA UPeU).

**Identity Providers:**
- `MicrosoftUPeU` (oidc, enabled=true) — broker Entra ID UPeU. SSO con cuentas M365 UPeU.

**User Federation:**
- `UPeU AD ACADEMIC` (LDAP, providerType `UserStorageProvider`) → **enabled=false** (legacy del AD UPeU académico, deshabilitado). Bind DN: `CN=Administrator,CN=Users,DC=lim,DC=upeu,DC=edu,DC=pe`. Vendor=ad, lastSync=1693238203 (≈2023).
- **NO existe aún federation hacia `ldap-identity-trust`** (Fase 6 pendiente).

### 1.4 Oracle LAMB — `192.168.13.9:1521/UPEU`

| Item | Valor |
|---|---|
| Versión | Oracle 11g R2 (memoria `reference_oracle_lamb_structure.md`) |
| Acceso | `~/.secrets/oracle-lamb.env`, user `JUANSANCHEZ`, rol `DEVELOP_READ` |
| Política | **Solo lectura absoluta** (`policy_oracle_readonly.md`) |
| Schemas autoritativos | MOISES (MDM personas), DAVID (académico), ELISEO (RRHH/nómina), ENOC (cat. docente), JOSE (alumnos finanzas) |
| Vistas oro | `DAVID.VW_PERSONA_NATURAL/ALUMNO/DOCENTE/EGRESADO/COMUN/CONTRATO/GRADO`, `DAVID.VW_DATOS_IDENTIDAD_USUARIO`, `ELISEO.VW_APS_EMPLEADO` |

**Verificación en este audit:** intentada con `python-oracledb` thin mode → falla (`DPY-3010: connections to this database server version are not supported`). Sin acceso instantclient en Mac; verificación remota desde el contenedor MidPoint (que tiene `ojdbc11-23.6.0`) habría sido posible pero está OOM. **Gap marcado en §8.4 — no bloquea el audit.**

### 1.5 Tasks activas o recientes en PROD

69 tasks. Patrones clave (extraído del listado):

| Familia | Tasks | Significado |
|---|---|---|
| `Recompute All Users — *` | 8+ runs en 2026-05-17/18/19 | Reprocesos masivos por cambios template/policy. Indica que el modelo aún está estabilizándose. |
| `Reconcile LAMB-*` | 5+ tasks | Inbound reconciliation desde Oracle LAMB (los 3 resources v3 + Posiciones) |
| `LDAP Recompute Round N` | Rounds 1-5 (último Round 5 hoy) | Re-proyectar al LDAP Identity Cache tras fixes de outbound |
| `SYNC-LAMB-Trabajadores-photoUrl` | 3 runs | Hidratado de fotos híbridas (memoria `project_photo_architecture.md`) |
| `PILOT-EntraID-UPeU-link-{100,photo-100}` | 2 runs | Piloto correlación Entra ID |
| `FIX-J2-clearTaxId-piloto-*` | 4 runs | Saneamiento de DNI piloto |
| Built-in scanners | Trigger Scanner, Validity Scanner, Cleanup | OOTB |

---

## Sección 2 — Inventario `SciBack/midpoint` (repo padre)

Repo GitHub: `SciBack/midpoint`. Localmente: `/Users/alberto/proyectos/upeu/midpoint/`. **NO clonado en PROD.**

### 2.1 XMLs presentes (sin contar `midPointEcosystem/` ni `archive/`)

**`archetypes/` — 18 XMLs (8 user + 8 org + 2 role)**

| Archivo | Estado | Cumple canónico (skill) | Aplicado en PROD | Observación |
|---|---|---|---|---|
| `user/01-student.xml` | draft (sin OID) | ✅ contenido canónico eduPerson | ❌ no aplicado (PROD usa `archetype-user-student.xml` de midPointEcosystem) | Naming alineado a skill, pero no es la versión viva |
| `user/02-employee-faculty.xml` | draft | ✅ | ❌ | idem |
| `user/03-employee-staff.xml` | draft | ✅ | ❌ | idem |
| `user/04-affiliate-partner-institution.xml` | draft | ✅ | ❌ | idem |
| `user/05-affiliate-researcher.xml` | draft | ✅ | ❌ | idem |
| `user/06-alumni.xml` | draft | ✅ | ❌ | idem |
| `user/07-contractor.xml` | draft | ✅ | ❌ | idem |
| `user/08-service-account.xml` | draft | ✅ | ❌ | idem |
| `org/01-institution.xml`…`08-academic-unit.xml` | draft (sin OID) | ✅ subtype `institution/campus/faculty/...` alineado a §5.3 skill | ❌ no aplicados | Versiones canónicas; equivalentes en midPointEcosystem son los aplicados |
| `role/01-business-role.xml`, `02-application-role.xml` | draft | ✅ §6.4 cascada BR→AR | ❌ | meta-roles archetype para roles |

**`objectTemplates/` — 9 XMLs (1 base + 8 por archetype)**

| Archivo | Cumple canónico (skill §4.1) | Aplicado en PROD |
|---|---|---|
| `00-common-base.xml` | ✅ (puede ser includeRef en los demás) | ❌ |
| `01-student.xml` … `08-service-account.xml` | ✅ template por archetype (recomendado) | ❌ |
| `archive/...` | obsoletos | — |

> **Punto importante:** Esta arquitectura **un template por archetype** está más alineada con `iga-canonical-standards` §10 que el "template único global" de PROD (`UserTemplate-Person-Base`). Es uno de los activos de diseño más rescatables del repo padre.

**`orgs/` — 3 XMLs (partners)**
- `04-partner-cgh.xml`, `05-partner-istat.xml`, `06-partner-agtu.xml` — overlays UPeU partner-institutions (Clínica Good Hope, ISTAT, AGTU). Sin OID. **Aplicados en PROD bajo la nomenclatura de midPointEcosystem (Colegio Unión sí está, los 3 partners pendientes de verificar).**

**`resources/` — 8 XMLs**
- `oracle-lamb-{trabajadores,estudiantes,egresados}.xml` (v1, legacy) — **superseded por v3 en PROD**
- `oracle-lamb-{trabajadores,estudiantes,egresados}-v2.xml` (v2, legacy) — **superseded por v3 en PROD**
- `keycloak-resource.xml`, `resource-keycloak.xml` — conector keycloak-http archivado (decisión doctrinal 2026-05-11) — **NO en PROD**

**`roles/` — 31 XMLs (20 application + 11 business)**

Listados alineados con `iga-canonical-standards` §6.4. Naming canónico (`01-AR-Koha-Patron-Student.xml`, etc.). **NO aplicados en PROD; PROD usa los `midPointEcosystem/midpoint/roles/{application,business}/AR-*.xml` y `BR-*.xml` equivalentes (sin numerar).**

**`schema/`**
- Solo `README-extension-guia.md` + `MAPPING-PLAN-lamb-to-extension.md`
- `archive/DEPRECATED-schemaType-v3.0.xml`, `DEPRECATED-schemaType-lamb-v1.xml`, `DEPRECATED-SPEC-v3.md`, `DEPRECATED-test-user-v3.xml`
- `backups/v2.2-*.xml`, `v2.3-after-put-*.xml`
> **PROD usa schemas `urn:sciback:midpoint:person` y `urn:upeu:midpoint:local`, NO los `v3.0` ni `v2.x` que aquí están deprecated.**

**`ldap/` — 2 XMLs**
- `resource-ldap-upeu.xml`, `role-ar-ldap-person.xml` — drafts que también existen en `midPointEcosystem/.../ldap/resource-ldap-identity-cache-upeu.xml` y `roles/application/AR-LDAP-Person.xml` (los aplicados).

**`tasks/` — 6 XMLs**
- `task-recon-{trabajadores,estudiantes,egresados}.xml` (v1, legacy) — **NO aplicados en PROD**
- `task-recon-{trabajadores,estudiantes,egresados}-v2.xml` — **NO aplicados**
- PROD usa tasks v3 + las múltiples runs ad-hoc registradas en §1.5

**`audit/` — ≈30 XMLs**
Backups y snapshots de resources/templates legacy (trabajadores-v2 pre/post-fix, egresados-v2 pre/post, schemaType-v3, etc.). **Histórico — archivar.**

**`connector-keycloak-http/`**
Proyecto Maven Java (conector custom `pe.upeu.connector.keycloak-http v1.0.0`). **Decisión doctrinal 2026-05-11: archivado. No se usa en PROD.**

**`scripts/db/`** — `reset-test-data.sh`, `seed-usuarios-ficticios.sql` (solo para dev).

### 2.2 Documentación (`docs/` y `doc/`)

**Material RICO rescatable (1.739 líneas combinadas):**

| Archivo | Líneas | Valor | Destino propuesto |
|---|---|---|---|
| `docs/roadmap-iga-2026.md` | 311 | Roadmap maestro con 9 principios de ejecución | `midPointEcosystem/docs/ROADMAP.md` |
| `docs/iga-canonical-analysis-2026-05.md` | 509 | Análisis canónico completo (decisión doctrinal, estándares adoptados, anti-patterns) | `midPointEcosystem/docs/ARCHITECTURE.md` |
| `docs/perfiles-identidad.md` | 578 | Catálogo de perfiles canónicos (afiliaciones, lifecycle, transitions) | `midPointEcosystem/canonical/README.md` o `docs/profiles.md` |
| `docs/eduperson-attributes-reference.md` | 151 | Referencia eduPerson para SSO | `midPointEcosystem/docs/eduperson-reference.md` |
| `docs/sso-academico-vendors-mapping.md` | 190 | Mapeo vendors→atributos R&S | `midPointEcosystem/docs/sso-vendors-mapping.md` |
| `docs/arquitectura.html` | (HTML interactivo) | Diagrama oficial UPeU | Conservar en `midPointEcosystem/docs/` (junto a `arquitectura-entraid-iga.html`) |
| `docs/david-urquizo-tasks.md` | — | Tickets a David (admin AD/Entra) | `midPointEcosystem/docs/runbooks/tickets-david-urquizo.md` |
| `docs/rudy-oracle-tasks.md` | — | Tickets a Rudy (Oracle/infra) | `midPointEcosystem/docs/runbooks/tickets-rudy.md` |
| `doc/specs/iga-canonical-model-upeu/01-spec.md` | — | Spec ClaudeFlow del modelo canónico | `midPointEcosystem/docs/specs/` |
| `doc/specs/sciback-iga-blueprint/01-iga-blueprint-peru.md` | — | Blueprint SciBack (referencia futura) | Conservar en repo padre antes de borrar; **rescatar a `sciback-iga-blueprint` cuando se reconstruya SciBack** |
| `doc/specs/multi-profile-canonical/0{1..7}-*.md` | — | Specs de multi-profile (afiliaciones múltiples) | `midPointEcosystem/docs/specs/multi-profile-canonical/` |
| `doc/specs/fix-resources-oracle-v2-scripts/0{1..5}-*.md` | — | Spec del fix Oracle v2 (ya superseded por v3) | **archivar a `midPointEcosystem/archive/specs/`** |
| `doc/specs/midpoint-prod-upeu/01-brainstorm.md` | — | Brainstorm del despliegue PROD | Histórico, archivar |
| `doc/runbooks/upgrade-midpoint-docker.md` | — | Runbook upgrade 4.9.5→4.10.2 (ejecutado HOY, ver §1.1) | `midPointEcosystem/docs/runbooks/upgrade-midpoint-docker.md` |
| `doc/catalogo-positions-upeu/index.html` | — | Catálogo 738 Positions UPeU | `midPointEcosystem/docs/catalogo-positions-upeu/` |
| `context.md` | — | Contexto estratégico | Histórico; rescatar partes útiles a `docs/CONTEXT.md` |

### 2.3 Confrontación con skills

✅ **Cumple:** naming canónico de archetypes (`01-student.xml`, `02-employee-faculty.xml`), 8 archetypes user alineados a vocabulario eduPerson §3.2, separación 3-capas RBAC §6.4, una template por archetype §4.1, identifiers persistentes en orgs §5.2, partners como `affiliate.partner-institution`.

❌ **Desvía:**
- Resources v1 y v2 obsoletos (PROD usa v3) — **NO migrar**, son ruido.
- `connector-keycloak-http` decisión revertida — **NO migrar**.
- Schemas `v3.0` y `lamb-v1` ya en `schema/archive/` con prefijo `DEPRECATED-` — **NO migrar**, ya están deprecated.
- Sin OIDs reales en XMLs (drafts) — los OIDs vivos están en `midPointEcosystem`.

---

## Sección 3 — Inventario `UPeU-Infra/midPointEcosystem`

Repo GitHub: `UPeU-Infra/midPointEcosystem`. Localmente: `/Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/`. **Clonado en PROD: `/home/juansanchez/midPointEcosystem/`.**

### 3.1 Mapeo carpeta-por-carpeta con PROD

| Carpeta | XMLs | OIDs reales | Aplicado en PROD | Comentarios |
|---|---|---|---|---|
| `midpoint/archetypes/` | 13 XMLs | ✅ todos con OID real | ✅ todos en PROD | Naming verboso: `archetype-user-*`, `archetype-org-*`, `archetype-position`, `archetype-person`, `aux-affiliation-*` |
| `midpoint/auth/oidc-entra-id.xml` | 1 | ? | (revisar) | Authentication config |
| `midpoint/dashboards/dashboard-operacion-iga.xml` | 1 | ? | ✅ (2 dashboards en PROD) | |
| `midpoint/function-libraries/sb-program-resolver.xml` | 1 | ? | ✅ | El único FuncLib en PROD |
| `midpoint/lookup-tables/program-resolver-lamb.xml` | 1 | ? | ✅ | |
| `midpoint/object-collections/collection-personas-upeu.xml` + `sysconfig-patch-...xml` | 2 | ? | ✅ (31 OC en PROD) | |
| `midpoint/object-templates/UserTemplate-Person-Base.xml` | 1 | `855caaca-68c4-4f7f-8ff8-b4e35dd7d390` | ✅ active en PROD | El único template propio UPeU |
| `midpoint/org/000-UPeU-root.xml`…`050-GobiernoAdmin.xml` | 6 | OID real (`1719a0bc-...` raíz) | ✅ | Top-level orgs |
| `midpoint/org/academic-programs/` | 1 (`-pregrado.xml`) | ? | ✅ (23 academic-programs) | |
| `midpoint/org/campus/*` | 5 | ? | ✅ (3 OU-CAMPUS-* + 2 units) | |
| `midpoint/org/colegio-union/*` | 16 | OID real | ✅ | Colegio Unión jerarquía completa |
| `midpoint/policies/policy-{owners-required,sod-basic}.xml` | 2 | ? | ✅ (3 POLICY en PROD) | |
| `midpoint/resources/ad/UPEU-AD.xml` | 1 | ? | (no en PROD active — verificar) | Decisión doctrinal: AD UPeU out-of-scope hasta Fase 12 |
| `midpoint/resources/db-{crm,rrhh,sis}/*.xml` | 4 | ? | ❌ (skeletons / legacy) | CSV samples — solo testing |
| `midpoint/resources/entra-id/UPEU-EntraID-Graph.xml` | 1 | `2f11c057-...` | ✅ | El resource real |
| `midpoint/resources/entra-id/resource-msgraph-legacy.xml` | 1 | (legacy OID) | ❌ | Reemplazado por UPEU-EntraID-Graph |
| `midpoint/resources/koha/resource-koha-ils-upeu.xml` | 1 | `9b5a7c81-...` | ✅ | |
| `midpoint/resources/ldap/resource-ldap-identity-cache-upeu.xml` | 1 | `7b4e1c2d-...` | ✅ | |
| `midpoint/resources/oracle-lamb/*-v3.xml` (4) | 4 | OIDs reales | ✅ todos | Los 4 resources Oracle LAMB v3 |
| `midpoint/roles/affiliation/R-*.xml` | 6 | ? | ✅ | Los 6 R-Affiliation-* |
| `midpoint/roles/application/AR-*.xml` | 20 | ? | ✅ | Application roles |
| `midpoint/roles/business/BR-*.xml` | 12 | ? | ✅ | Business roles |
| `midpoint/schema/schema-object-{sciback-person-v1.0,upeu-local-v1.0}.xml` | 2 | ✅ OID real | ✅ active | Schemas vivos |
| `midpoint/schema/archive/DEPRECATED-schema-object-upeu-person-v3.1.xml` | 1 | — | — | Ya archivado correctamente |
| `midpoint/services/positions/position-*.xml` | 13 | OID real | ✅ (subset; 738 positions totales en PROD via inbound LAMB) | Solo 13 positions "core" están versionadas; los 738 vienen via task `Import LAMB-Oracle-Posiciones` |
| `midpoint/simulations/README.md` | 1 | — | — | Placeholder |
| `midpoint/system/system-configuration.xml` | 1 | `00000000-0000-0000-0000-000000000001` | ✅ | |
| `midpoint/tasks/pilot-*.xml`, `task-import-SIS-simulation.xml`, `task-reconcile-*-simulation.xml`, `task-reconcile-oracle-lamb-{trabajadores,estudiantes,egresados}.xml` | 9 | ? | parcial (PROD tiene 69 tasks, 60+ son runs ad-hoc no versionadas) | Solo los pilot/reconcile-base están versionados |
| `datasets/csv/{sis,rrhh,crm}-sample.csv` | 3 | — | — | Datos sintéticos para testing |
| `datasets/postgresql_{academico,crm,rrhh}/scripts-db/` | varios | — | — | Datasets demo |

### 3.2 `archive/previous/` — Legacy correctamente archivado

| Archivo | Tipo | Comentario |
|---|---|---|
| `initial-objects/schemas/Esquema de Extensión para Personas UPeU.xml` | Schema legacy | Ya archivado correctamente |
| `initial-objects/usuario de pruebas para midpoint.xml` | Test user | Ya archivado |
| `resources-ldap-legacy/resource-openldap-legacy.xml` | LDAP legacy | Ya archivado |
| `resources-ldap-legacy/legacy-openldap/container-ldap_files/` | Configs Docker LDAP | Histórico |
| `infra/freeradius-server/` | FreeRADIUS configs | Histórico (FreeRADIUS pendiente Fase posterior) |

### 3.3 `docs/` — Documentación SKELETON

| Archivo | Líneas | Estado |
|---|---|---|
| `arquitectura.md` | 21 | Skeleton (placeholder) |
| `correlation-strategy.md` | 11 | Skeleton |
| `execution-guide.md` | 55 | Skeleton |
| `lifecycle-policies.md` | 22 | Skeleton |
| `mapping-rules.md` | 28 | Skeleton |
| `naming-conventions.md` | 24 | Skeleton |
| `arquitectura-entraid-iga.html` | (rich) | Documento Entra ID — vigente (commits recientes) |

> **Conclusión:** los docs principales de `midPointEcosystem/docs/` son **placeholders genéricos** sin contenido sustantivo. Toda la documentación rica vive en `SciBack/midpoint/docs/` (1.739 líneas) y debe MIGRARSE.

### 3.4 Confrontación con skills

✅ **Cumple:**
- OIDs persistentes y estables (skill `iga-canonical-standards` regla 10 + `midpoint-best-practices` §5.2)
- Resources canónicos v3 ScriptedSQL (versionados, bien estructurados)
- 18 archetypes activos con jerarquía Institution→Campus→Faculty→Department alineada a §5.3
- Schemas con `urn:` namespace propio (skill §1.4)
- Roles separados en affiliation/application/business (skill §6.4)
- Position como archetype ServiceType (memoria `policy_iga_canonical_pillars.md` PBAC)
- 6 R-Affiliation-* canónicos (alineado §3.2 eduPersonAffiliation vocabulary)

❌ **Desvía o requiere review:**
- **Naming inconsistente:** `archetype-user-student` (verboso) vs `R-Affiliation-Student` (mixed snake/Pascal) vs `AR-Koha-Patron-Student` vs `BR-Docente-TC`. Mantener convención al consolidar.
- **Schemas top-level mezclan canonical/upeu** en mismo directorio (`midpoint/schema/`). El refactor canonical/upeu lo resolverá.
- **4 `aux-affiliation-*`** son auxiliary archetypes; skill recomienda birthright roles. Coexisten con los 6 `R-Affiliation-*`. Redundancia a resolver post-consolidación (decisión técnica, no incluida en este audit).
- **`policy-sod-basic.xml`** existe pero no se valida en este audit que esté efectivamente activo. Verificar §8.5.
- **Object template único** (`UserTemplate-Person-Base`) vs 8 templates per-archetype del repo padre. Decisión arquitectónica pendiente; ver §5.

---

## Sección 4 — Mapeo viejo → canónico (concepto-por-concepto)

| Concepto IGA | En `SciBack/midpoint` | En `midPointEcosystem` | Refleja PROD | Versión que sobrevive | Justificación |
|---|---|---|---|---|---|
| Archetype `student` | `archetypes/user/01-student.xml` (draft, sin OID) | `midpoint/archetypes/archetype-user-student.xml` (OID `3037fbd2-...`) | midPointEcosystem | **midPointEcosystem renombrado a `canonical/archetypes/user-student.xml`** | OIDs reales mandan. Renombrar para limpieza. Skill §3.5 + regla 7 |
| Archetypes user (resto 7) | `archetypes/user/02-08-*.xml` | `archetype-user-{employee-faculty,employee-staff,affiliate-partner-institution,affiliate-researcher,alumni,contractor,service-account}.xml` (5 versionados — affiliate-researcher y contractor son drafts en SciBack/midpoint y NO en PROD) | midPointEcosystem (5) | **midPointEcosystem para los 5 vivos + crear 2 nuevos (affiliate-researcher, contractor) en `canonical/archetypes/` cuando se necesiten** | Los 8 archetypes de SciBack/midpoint son ambición; PROD tiene 6 user-archetypes vivos (los 5 + el faltante service-account que también existe) |
| Archetypes org | `archetypes/org/01-08-*.xml` (draft) | (sin XML versionado — `archetype-org-academic-program.xml` es el único, los demás se importaron solo via REST) | midPointEcosystem solo tiene 1 | **Crear 8 en `canonical/archetypes/org/` con OIDs reales de PROD** | Necesitamos versionar los 8 archetypes-org que sí están en PROD (academic-unit, campus, department, faculty, governance, institution, partner-institution, project) |
| Archetypes role | `archetypes/role/01-business-role.xml`, `02-application-role.xml` (draft) | (no versionados — built-in MidPoint con OIDs `00000000-...-000321` y `-000328`) | Built-in MidPoint | **Reusar built-in. No versionar.** | Skill §3.2 — los OOTB son suficientes para business-role + application-role |
| Auxiliary archetypes (4 AuxAff-*) | (no en repo padre) | `aux-affiliation-{alum,faculty,staff,student}.xml` | midPointEcosystem | **Mover a `upeu/archetypes/auxiliary/` PERO revisar redundancia con R-Affiliation-*. Posiblemente deprecate (skill §3.3 advertencia 4.9)** | UPeU-specific; auxiliary archetypes no son canónicos |
| Object Template | `objectTemplates/00-common-base.xml` + 8 per-archetype | `midpoint/object-templates/UserTemplate-Person-Base.xml` (1 único) | midPointEcosystem | **midPointEcosystem como base + ROADMAP: migrar progresivamente a un template per archetype como diseña SciBack/midpoint** | PROD tiene 1 template global. Diseño SciBack es más alineado a skill §4.1. Mantener PROD por compatibilidad y migrar incremental |
| Schema canónico | `schema/archive/DEPRECATED-schemaType-v3.0.xml` + `DEPRECATED-schemaType-lamb-v1.xml` | `midpoint/schema/schema-object-sciback-person-v1.0.xml` + `schema-object-upeu-local-v1.0.xml` | midPointEcosystem | **midPointEcosystem (schemas activos en PROD). Mover sciback a `canonical/schemas/` y upeu-local a `upeu/schemas/`** | PROD ya implementa la separación canonical/upeu en namespaces |
| Resource Oracle LAMB Trabajadores | `resources/oracle-lamb-trabajadores.xml` (v1) + `…-v2.xml` (v2) | `midpoint/resources/oracle-lamb/resource-oracle-lamb-trabajadores-v3.xml` | midPointEcosystem v3 | **midPointEcosystem v3 → `upeu/resources/oracle-lamb/trabajadores.xml`** | PROD usa v3. v1 y v2 son ruido. Es UPeU-specific (IIA Oracle LAMB) |
| Resource Oracle LAMB Estudiantes | idem | `…-estudiantes-v3.xml` | midPointEcosystem | **idem → `upeu/resources/oracle-lamb/estudiantes.xml`** | idem |
| Resource Oracle LAMB Egresados | idem | `…-egresados-v3.xml` | midPointEcosystem | **idem → `upeu/resources/oracle-lamb/egresados.xml`** | idem |
| Resource Posiciones | (no) | `…-posiciones-v1.xml` | midPointEcosystem | **midPointEcosystem → `upeu/resources/oracle-lamb/posiciones.xml`** | PBAC Pilar 3 |
| Resource OpenLDAP | `ldap/resource-ldap-upeu.xml` (draft) | `midpoint/resources/ldap/resource-ldap-identity-cache-upeu.xml` | midPointEcosystem | **midPointEcosystem → `upeu/resources/ldap-identity-cache.xml`** | LDAP UPeU es overlay (host específico); el connector LDAP es canónico |
| Resource Entra ID Graph | (no) | `midpoint/resources/entra-id/UPEU-EntraID-Graph.xml` | midPointEcosystem | **midPointEcosystem → `upeu/resources/entra-id-graph.xml`** | UPeU tenant-specific |
| Resource Koha | (no) | `midpoint/resources/koha/resource-koha-ils-upeu.xml` | midPointEcosystem | **midPointEcosystem → `upeu/resources/koha-ils.xml`** | 4 instancias Koha UPeU; UPeU-specific |
| Resource AD UPeU | (no) | `midpoint/resources/ad/UPEU-AD.xml` | (no aplicado en PROD activo) | **`upeu/resources/ad-upeu.xml` (lifecycle=draft, decisión doctrinal Fase 12)** | Decisión deferida |
| Resource Keycloak | `resources/keycloak-resource.xml` + `resource-keycloak.xml` (draft, conector custom archivado) | (no aplicado) | ❌ ningún resource Keycloak en PROD | **DESCARTAR ambos (lista negra §7)** | Decisión doctrinal: arquitectura es MidPoint→OpenLDAP←Keycloak User Federation. Keycloak NO recibe push directo |
| Resource CSV (db-sis/db-rrhh/db-crm) | (no) | `midpoint/resources/db-*/...skeleton.xml` | (testing only, no PROD) | **`upeu/resources/datasets/` o archivar a `archive/`** | Solo testing |
| Function library | (no) | `midpoint/function-libraries/sb-program-resolver.xml` | midPointEcosystem | **`canonical/function-libraries/sb-program-resolver.xml`** | Naming `sb:` indica canónico SciBack |
| Lookup table program-resolver-lamb | (no) | `midpoint/lookup-tables/program-resolver-lamb.xml` | midPointEcosystem | **`upeu/lookup-tables/program-resolver-lamb.xml`** | LAMB es UPeU-specific |
| Application Roles | `roles/application/0X-AR-*.xml` (20 drafts) | `midpoint/roles/application/AR-*.xml` (20 con OID real) | midPointEcosystem | **midPointEcosystem → `upeu/roles/application/`** | Vendor-specific (Koha, Indico, M365, etc.); cada AR depende de un resource. La estructura canónica del AR (archetype Application role) sí es canónica |
| Business Roles | `roles/business/0X-BR-*.xml` (11 drafts) | `midpoint/roles/business/BR-*.xml` (12 con OID real) | midPointEcosystem | **midPointEcosystem → `upeu/roles/business/`** | Función UPeU (Docente-TC, Estudiante-Pregrado, etc.). Modelo canónico (eduPerson) pero composición es UPeU |
| Affiliation Roles | (no) | `midpoint/roles/affiliation/R-Affiliation-*.xml` (6) | midPointEcosystem | **`upeu/roles/affiliation/` (provisional) — evaluar mover a `canonical/roles/` post-consolidación** | Vocabulario es canónico (skill §3.2). Implementación es UPeU-current; podría canonificarse |
| Org tree (UPeU root + facultades + colegio union) | `orgs/04-06-partner-*.xml` (3 drafts partner) | `midpoint/org/*` (≈22 XMLs jerarquía completa UPeU) | midPointEcosystem (122 orgs en PROD) | **midPointEcosystem → `upeu/orgs/`** + **partner-institution archetype a `canonical/archetypes/org/`** | UPeU-specific |
| Policies (owners-required, sod-basic) | (no) | `midpoint/policies/*.xml` (2) | midPointEcosystem | **`canonical/policies/`** | Estándar IGA (skill §7.1 controles A.5.18, A.8.2) |
| Positions UPeU (catálogo) | (no — solo doc HTML en `doc/catalogo-positions-upeu/`) | `midpoint/services/positions/position-*.xml` (13) | midPointEcosystem (738 en PROD) | **`upeu/services/positions/`** | UPeU-specific (Ley 30220, Resol. 0001-2026) |
| Tasks recon | `tasks/task-recon-{*}-v2.xml` (drafts legacy) | `midpoint/tasks/task-reconcile-oracle-lamb-*.xml` (3) | midPointEcosystem | **midPointEcosystem → `upeu/tasks/`** | Recon a IIA UPeU |
| Tasks simulación | (no) | `midpoint/tasks/task-*-simulation.xml` (3 SIS/AD/SIS-recon simulations) | (no aplicado) | **`upeu/tasks/simulations/` o archivar** | Testing |
| Tasks piloto | (no) | `midpoint/tasks/pilot-*.xml` (3) | parcial | **`upeu/tasks/pilots/` o archivar** | Pilotos puntuales |
| Roadmap, Architecture, ADRs | `docs/roadmap-iga-2026.md`, `iga-canonical-analysis-2026-05.md`, `perfiles-identidad.md`, `eduperson-attributes-reference.md`, `sso-academico-vendors-mapping.md` | `docs/arquitectura.md` (placeholder) + `arquitectura-entraid-iga.html` (rich) | docs ricas en SciBack/midpoint | **MIGRAR docs de SciBack/midpoint a midPointEcosystem/docs/** | Material crítico — ver §2.2 |
| Specs (ClaudeFlow) | `doc/specs/{iga-canonical-model-upeu,multi-profile-canonical,sciback-iga-blueprint,fix-resources-oracle-v2-scripts,midpoint-prod-upeu}/` | (no) | (histórico) | **MIGRAR a `midPointEcosystem/docs/specs/`** + archivar `fix-resources-oracle-v2-scripts` (superseded) | Histórico rescatable |
| Conector keycloak-http | `connector-keycloak-http/` (Maven project) | (no) | (no aplicado, decisión doctrinal archivado) | **DESCARTAR — lista negra §7** | Decisión 2026-05-11 |
| Audit XML backups | `audit/{30 XMLs}` | (no) | (histórico) | **MIGRAR críticos a `midPointEcosystem/archive/backups-2026-05/` y descartar el resto** | Forensic only |

---

## Sección 5 — Estructura propuesta del repo consolidado

### 5.1 Árbol propuesto

```
midPointEcosystem/                        ← repo único, fuente de verdad
├── README.md                              ← reescribir con estructura nueva
├── .gitignore
│
├── canonical/                             ← CAPA 1: agnóstico (eduPerson/SCHAC/RBAC/SCIM/ISO24760)
│   ├── README.md                          ← documenta el contrato canónico
│   ├── archetypes/
│   │   ├── user/
│   │   │   ├── user-student.xml           ← OID 3037fbd2-... (renombrado desde archetype-user-student)
│   │   │   ├── user-employee-faculty.xml
│   │   │   ├── user-employee-staff.xml
│   │   │   ├── user-affiliate-partner-institution.xml
│   │   │   ├── user-affiliate-researcher.xml
│   │   │   ├── user-alumni.xml
│   │   │   ├── user-contractor.xml
│   │   │   └── user-service-account.xml
│   │   └── org/
│   │       ├── org-institution.xml
│   │       ├── org-campus.xml
│   │       ├── org-faculty.xml
│   │       ├── org-department.xml
│   │       ├── org-academic-unit.xml
│   │       ├── org-governance.xml
│   │       ├── org-partner-institution.xml
│   │       └── org-project.xml
│   ├── schemas/
│   │   └── sciback-person-v1.0.xml        ← `urn:sciback:midpoint:person`, OID e800335c-...
│   ├── object-templates/
│   │   └── UserTemplate-Person-Base.xml   ← migrar; futuro split a per-archetype (ROADMAP)
│   ├── policies/
│   │   ├── policy-owners-required.xml     ← ISO 27001 A.5.18 / A.8.2
│   │   └── policy-sod-basic.xml           ← RBAC INCITS 359 §6.3 SoD
│   ├── function-libraries/
│   │   └── sb-program-resolver.xml        ← naming `sb:` indica canónico
│   └── roles/                             ← FUTURO: roles canónicos cuando se identifiquen
│       └── (vacío inicialmente — los R-Affiliation se mantienen en upeu/ hasta validar canonicidad)
│
├── upeu/                                  ← CAPA 2: overlay específico UPeU
│   ├── README.md                          ← documenta overrides + razones
│   ├── schemas/
│   │   └── upeu-local-v1.0.xml            ← `urn:upeu:midpoint:local`, OID 64ed4155-...
│   ├── archetypes/
│   │   └── auxiliary/                     ← aux-affiliation-* (decisión pendiente: deprecate vs mantener)
│   │       ├── aux-affiliation-student.xml
│   │       ├── aux-affiliation-faculty.xml
│   │       ├── aux-affiliation-staff.xml
│   │       └── aux-affiliation-alum.xml
│   ├── orgs/
│   │   ├── 000-UPeU-root.xml              ← Universidad Peruana Unión (institution)
│   │   ├── 010-Facultades.xml
│   │   ├── 020-Rectorado.xml
│   │   ├── 030-AreaTecnologia.xml
│   │   ├── 040-Posgrado.xml
│   │   ├── 050-GobiernoAdmin.xml
│   │   ├── campus/                        ← OU-CAMPUS-{LIMA,JULIACA,TARAPOTO} + units
│   │   ├── academic-programs/             ← 23 SKOS programas
│   │   ├── colegio-union/                 ← Colegio Unión jerarquía (16 orgs)
│   │   └── partners/                      ← (futuro) ISTAT, AGTU, CGH
│   ├── resources/
│   │   ├── oracle-lamb/
│   │   │   ├── trabajadores.xml           ← v3 renombrado limpio
│   │   │   ├── estudiantes.xml
│   │   │   ├── egresados.xml
│   │   │   └── posiciones.xml
│   │   ├── ldap-identity-cache.xml        ← OpenLDAP UPeU
│   │   ├── entra-id-graph.xml             ← Microsoft Graph (read-only)
│   │   ├── koha-ils.xml
│   │   ├── ad-upeu.xml                    ← lifecycle=draft (Fase 12)
│   │   └── datasets/                      ← CSVs testing (archivar si no se usan)
│   ├── roles/
│   │   ├── affiliation/                   ← R-Affiliation-* (6)
│   │   ├── application/                   ← AR-* (20)
│   │   ├── business/                      ← BR-* (12)
│   │   ├── governance/                    ← GOV-* (3)
│   │   ├── mof/                           ← MOF-* (≈25)
│   │   └── system/
│   │       └── SYS-IGA-SUPERUSER.xml
│   ├── object-templates/                  ← (futuro) overrides per-archetype específicos UPeU
│   ├── services/
│   │   └── positions/                     ← 13 positions versionados (738 vienen via task)
│   ├── lookup-tables/
│   │   └── program-resolver-lamb.xml
│   ├── object-collections/
│   │   └── collection-personas-upeu.xml
│   ├── dashboards/
│   │   └── dashboard-operacion-iga.xml
│   ├── auth/
│   │   └── oidc-entra-id.xml
│   ├── tasks/
│   │   ├── recon-oracle-lamb-trabajadores.xml
│   │   ├── recon-oracle-lamb-estudiantes.xml
│   │   ├── recon-oracle-lamb-egresados.xml
│   │   ├── recon-oracle-lamb-posiciones.xml
│   │   ├── simulations/                   ← task-*-simulation.xml
│   │   └── pilots/                        ← pilot-*.xml
│   └── system/
│       └── system-configuration.xml       ← UPeU-specific SystemConfiguration
│
├── docs/                                  ← documentación viva
│   ├── ARCHITECTURE.md                    ← reescrito desde iga-canonical-analysis-2026-05.md (SciBack/midpoint)
│   ├── ROADMAP.md                         ← unificado desde roadmap-iga-2026.md
│   ├── AUDIT-CONSOLIDATION-2026-05-19.md  ← este documento
│   ├── eduperson-reference.md             ← migrado
│   ├── schac-reference.md                 ← futuro
│   ├── sso-vendors-mapping.md             ← migrado
│   ├── profiles.md                        ← migrado desde perfiles-identidad.md
│   ├── catalogo-positions-upeu/           ← HTML interactivo
│   ├── arquitectura-entraid-iga.html      ← se mantiene
│   ├── correlation-strategy.md            ← actualizar (skeleton actual)
│   ├── lifecycle-policies.md              ← actualizar
│   ├── mapping-rules.md                   ← actualizar
│   ├── naming-conventions.md              ← actualizar con nueva estructura
│   ├── runbooks/
│   │   ├── upgrade-midpoint-docker.md
│   │   ├── tickets-david-urquizo.md
│   │   ├── tickets-rudy.md
│   │   └── recovery-oom-midpoint.md       ← NUEVO (ver §8.1)
│   └── specs/                             ← ClaudeFlow specs históricas
│       ├── iga-canonical-model-upeu/
│       ├── multi-profile-canonical/
│       └── midpoint-prod-upeu/
│
├── datasets/                              ← CSVs y datasets de demo/dev (sin cambios)
│   ├── csv/
│   ├── postgresql_academico/
│   ├── postgresql_crm/
│   └── postgresql_rrhh/
│
└── archive/
    ├── previous/                          ← ya existente, mantener
    ├── specs/
    │   └── fix-resources-oracle-v2-scripts/   ← spec superseded por v3
    ├── backups-2026-05/                   ← snapshots críticos de SciBack/midpoint/audit/
    ├── connector-keycloak-http/           ← código Maven archivado (decisión 2026-05-11)
    └── README.md                          ← inventario qué hay archivado y por qué
```

### 5.2 Justificación por decisión clave (contra skills)

| Decisión | Justificación |
|---|---|
| **2 capas `canonical/` + `upeu/`** | `iga-canonical-standards` regla 1 ("modelo canónico primero, institucional después") + ya implementado en schema namespaces |
| **`canonical/schemas/` solo `sciback-person`** | Es el schema agnóstico (`urn:sciback:midpoint:person`). El `upeu-local` es overlay tenant-specific |
| **Resources van TODOS a `upeu/`** | Toda Resource es por definición específica del tenant (host, credenciales, mapping a IIA). No puede ser canónica. |
| **Archetypes user/org van a `canonical/`** | Definen sub-types canónicos (Student, Faculty, Org-Institution, etc.). Las inducements UPeU-specific se agregan via meta-roles overlay (futuro) |
| **`aux-affiliation-*` van a `upeu/`** | Decisión UPeU-current de modelo. `iga-canonical-standards` no las mandata; `midpoint-best-practices` §3.3 advierte limited 4.9 support |
| **Object template inicialmente en `canonical/`** | `UserTemplate-Person-Base` es genérico aún (acepta cualquier archetype). Futuro: split a 8 templates per-archetype, los UPeU-specific irán a `upeu/object-templates/` |
| **Positions en `upeu/services/positions/`** | Catálogo UPeU (Resol. 0001-2026), no canónico |
| **R-Affiliation-* inicialmente en `upeu/`** | Vocabulario es canónico (eduPerson), pero implementación R-Affiliation-Student.xml actual contiene logic UPeU. Refactor a `canonical/` post-consolidación |
| **MOF-* roles en `upeu/roles/mof/`** | "Manual Operativo Funciones UPeU" — totalmente UPeU-specific |
| **GOV-* roles en `upeu/roles/governance/`** | Implementación específica; canónicamente la skill §6.4 las define como meta-roles, pendiente diseño abstracto |
| **Policies (`owners-required`, `sod-basic`) en `canonical/`** | Son patrones estándar IGA (ISO 27001 A.5.18, A.8.2) |
| **`canonical/` NO contiene OIDs ad-hoc cuando sea posible** | Para portabilidad multi-tenant futuro (SciBack blueprint). Pero los OIDs vivos en PROD se mantienen — no romper PROD |

### 5.3 Naming consistente (a aplicar en consolidación)

Decisión: usar **kebab-case sin prefijo de tipo** dentro de cada carpeta tipada.

```
canonical/archetypes/user/user-student.xml          (NO archetype-user-student)
canonical/archetypes/org/org-faculty.xml            (NO archetype-org-faculty)
upeu/orgs/colegio-union/colegio-union-root.xml      (NO org-COLEGIO-UNION)
upeu/resources/oracle-lamb/trabajadores.xml         (NO resource-oracle-lamb-trabajadores-v3)
upeu/roles/affiliation/affiliation-student.xml      (renombrar R-Affiliation-Student → más limpio)
upeu/roles/application/koha-patron-student.xml      (NO AR-Koha-Patron-Student)
upeu/roles/business/docente-tc.xml                  (NO BR-Docente-TC)
```

**Excepción:** el `displayName` y el `name` dentro del XML mantienen su valor actual (no romper referencias internas ni Frontend admin UI). Solo cambia el **filename** del XML.

---

## Sección 6 — Plan de migración (a ejecutar DESPUÉS de tu aprobación)

> **REGLA SUPREMA:** este plan **NO se ejecuta** hasta que Alberto apruebe explícitamente. Cuando se ejecute, **MidPoint PROD debe estar UP** (no OOM como ahora).

### Fase 6.1 — Pre-flight (sin tocar PROD)

1. **Resolver OOM de MidPoint PROD primero** (ver §8.1). Hasta que PROD esté UP, no se puede validar migración.
2. **Backup completo** repo `midPointEcosystem` actual:
   ```bash
   cd /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem
   git tag pre-consolidation-2026-05-19
   git push origin pre-consolidation-2026-05-19
   ```
3. **Backup DB MidPoint PROD** (pg_dump completo). El `midpoint_data-1` container Postgres puede dumpearse:
   ```bash
   sshpass -p $MIDPOINT_PROD_PASS ssh midpoint-prod "docker exec midpoint-midpoint_data-1 pg_dump -U midpoint -d midpoint -F c > /tmp/midpoint-pre-consolidation.dump"
   sshpass -p $MIDPOINT_PROD_PASS scp midpoint-prod:/tmp/midpoint-pre-consolidation.dump ./backups/
   ```
4. **Crear branch `consolidation-2026-05-19`** en `midPointEcosystem` para todo el trabajo. NO commitear a `main` directamente.

### Fase 6.2 — Crear estructura canonical/upeu (sobre branch)

5. Crear directorios vacíos según árbol §5.1.
6. Crear `canonical/README.md` y `upeu/README.md` documentando el contrato de cada capa.
7. Mover XMLs sin modificar contenido (solo path):
   ```bash
   # Schemas
   git mv midpoint/schema/schema-object-sciback-person-v1.0.xml canonical/schemas/sciback-person-v1.0.xml
   git mv midpoint/schema/schema-object-upeu-local-v1.0.xml upeu/schemas/upeu-local-v1.0.xml
   # Archetypes user
   git mv midpoint/archetypes/archetype-user-student.xml canonical/archetypes/user/user-student.xml
   git mv midpoint/archetypes/archetype-user-employee-faculty.xml canonical/archetypes/user/user-employee-faculty.xml
   # ... idem para los 5 user-archetypes versionados
   # Auxiliary archetypes
   git mv midpoint/archetypes/aux-affiliation-student.xml upeu/archetypes/auxiliary/aux-affiliation-student.xml
   # ... 4 aux
   # Object template
   git mv midpoint/object-templates/UserTemplate-Person-Base.xml canonical/object-templates/UserTemplate-Person-Base.xml
   # Policies
   git mv midpoint/policies/policy-owners-required.xml canonical/policies/policy-owners-required.xml
   git mv midpoint/policies/policy-sod-basic.xml canonical/policies/policy-sod-basic.xml
   # Function library
   git mv midpoint/function-libraries/sb-program-resolver.xml canonical/function-libraries/sb-program-resolver.xml
   # Lookup tables
   git mv midpoint/lookup-tables/program-resolver-lamb.xml upeu/lookup-tables/program-resolver-lamb.xml
   # Resources Oracle LAMB
   git mv midpoint/resources/oracle-lamb/resource-oracle-lamb-trabajadores-v3.xml upeu/resources/oracle-lamb/trabajadores.xml
   git mv midpoint/resources/oracle-lamb/resource-oracle-lamb-estudiantes-v3.xml upeu/resources/oracle-lamb/estudiantes.xml
   git mv midpoint/resources/oracle-lamb/resource-oracle-lamb-egresados-v3.xml upeu/resources/oracle-lamb/egresados.xml
   git mv midpoint/resources/oracle-lamb/resource-oracle-lamb-posiciones-v1.xml upeu/resources/oracle-lamb/posiciones.xml
   # Resources LDAP, Entra ID, Koha, AD
   git mv midpoint/resources/ldap/resource-ldap-identity-cache-upeu.xml upeu/resources/ldap-identity-cache.xml
   git mv midpoint/resources/entra-id/UPEU-EntraID-Graph.xml upeu/resources/entra-id-graph.xml
   git mv midpoint/resources/koha/resource-koha-ils-upeu.xml upeu/resources/koha-ils.xml
   git mv midpoint/resources/ad/UPEU-AD.xml upeu/resources/ad-upeu.xml
   # Roles affiliation, application, business
   git mv midpoint/roles/affiliation/* upeu/roles/affiliation/
   git mv midpoint/roles/application/* upeu/roles/application/
   git mv midpoint/roles/business/* upeu/roles/business/
   # Orgs UPeU
   git mv midpoint/org/000-UPeU-root.xml upeu/orgs/000-UPeU-root.xml
   git mv midpoint/org/010-Facultades.xml upeu/orgs/010-Facultades.xml
   # ... resto orgs
   git mv midpoint/org/colegio-union/* upeu/orgs/colegio-union/
   git mv midpoint/org/campus/* upeu/orgs/campus/
   git mv midpoint/org/academic-programs/* upeu/orgs/academic-programs/
   # Positions
   git mv midpoint/services/positions/* upeu/services/positions/
   # Dashboards, object-collections, auth, system
   git mv midpoint/dashboards/* upeu/dashboards/
   git mv midpoint/object-collections/* upeu/object-collections/
   git mv midpoint/auth/* upeu/auth/
   git mv midpoint/system/* upeu/system/
   # Tasks
   git mv midpoint/tasks/task-reconcile-oracle-lamb-trabajadores.xml upeu/tasks/recon-oracle-lamb-trabajadores.xml
   git mv midpoint/tasks/task-reconcile-oracle-lamb-estudiantes.xml upeu/tasks/recon-oracle-lamb-estudiantes.xml
   git mv midpoint/tasks/task-reconcile-oracle-lamb-egresados.xml upeu/tasks/recon-oracle-lamb-egresados.xml
   git mv midpoint/tasks/task-*-simulation.xml upeu/tasks/simulations/
   git mv midpoint/tasks/pilot-*.xml upeu/tasks/pilots/
   # Archive
   git mv midpoint/resources/entra-id/resource-msgraph-legacy.xml archive/previous/
   git mv midpoint/resources/db-sis/resource-academico-legacy.xml archive/previous/
   git mv midpoint/simulations archive/previous/ # solo README placeholder
   ```

### Fase 6.3 — Versionar 8 archetypes-org canónicos faltantes

8. Para los 8 `archetype-org-*` que SÍ están en PROD pero NO están versionados en `midPointEcosystem`, descargar XML real desde PROD vía REST y guardar en `canonical/archetypes/org/`:
   ```bash
   for archetype_oid in 04c304d1-9205-4097-9c1d-6dce6ba98c7f a0c2e4e3-911c-4146-9447-f91a1416feff ...; do
     # GET desde REST API (cuando PROD esté UP)
     curl -sk -u admin:pass "$URL/midpoint/ws/rest/archetypes/$archetype_oid" -o canonical/archetypes/org/...
   done
   ```

### Fase 6.4 — Migrar documentación rica (de SciBack/midpoint → midPointEcosystem)

9. Copiar (NO mover, son repos distintos) los 1.739 líneas de docs:
   ```bash
   cp /Users/alberto/proyectos/upeu/midpoint/docs/roadmap-iga-2026.md \
      /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/docs/ROADMAP.md
   cp /Users/alberto/proyectos/upeu/midpoint/docs/iga-canonical-analysis-2026-05.md \
      /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/docs/ARCHITECTURE.md
   cp /Users/alberto/proyectos/upeu/midpoint/docs/perfiles-identidad.md \
      /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/docs/profiles.md
   cp /Users/alberto/proyectos/upeu/midpoint/docs/eduperson-attributes-reference.md \
      /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/docs/eduperson-reference.md
   cp /Users/alberto/proyectos/upeu/midpoint/docs/sso-academico-vendors-mapping.md \
      /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/docs/sso-vendors-mapping.md
   # Specs y runbooks
   cp -r /Users/alberto/proyectos/upeu/midpoint/doc/specs/{iga-canonical-model-upeu,multi-profile-canonical,midpoint-prod-upeu} \
        /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/docs/specs/
   cp /Users/alberto/proyectos/upeu/midpoint/doc/runbooks/upgrade-midpoint-docker.md \
      /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/docs/runbooks/
   cp /Users/alberto/proyectos/upeu/midpoint/docs/{david-urquizo-tasks,rudy-oracle-tasks}.md \
      /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/docs/runbooks/
   cp -r /Users/alberto/proyectos/upeu/midpoint/doc/catalogo-positions-upeu \
        /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/docs/
   ```
10. Reescribir `midPointEcosystem/docs/{correlation-strategy,lifecycle-policies,mapping-rules,naming-conventions}.md` (los placeholders actuales) usando el material rich.

### Fase 6.5 — Archivar legacy y conector descartado

11. Mover spec superseded:
    ```bash
    cp -r /Users/alberto/proyectos/upeu/midpoint/doc/specs/fix-resources-oracle-v2-scripts \
         /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/archive/specs/
    ```
12. Archivar conector custom (preservar código por historial, NO usar):
    ```bash
    cp -r /Users/alberto/proyectos/upeu/midpoint/connector-keycloak-http \
         /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/archive/
    # Agregar README en archive/connector-keycloak-http/README.md explicando archivo
    ```
13. Archivar XMLs forensic críticos:
    ```bash
    cp /Users/alberto/proyectos/upeu/midpoint/audit/resource-trabajadores-v2-post-schemaScript-fix-prod-*.xml \
       /Users/alberto/proyectos/upeu/midpoint/midPointEcosystem/archive/backups-2026-05/
    # El resto del audit/ NO se migra (ruido)
    ```

### Fase 6.6 — Validación en branch (sin tocar PROD)

14. **Validación XML local:**
    ```bash
    # Validar que todos los XMLs son well-formed
    find canonical upeu -name '*.xml' -exec xmllint --noout {} \;
    ```
15. **Validación de referencias internas:**
    - Buscar `oid="..."` en archetypes refs, parentRef, targetRef. Confirmar que cada OID referenciado SÍ existe en algún XML del repo.
    - Específico: assignmentTargetSearch filter expressions, includeRef paths.
16. **Diff de OIDs** entre repo nuevo y PROD DB (consulta SQL §1.1) para asegurar 1-a-1 match.

### Fase 6.7 — Re-sincronización con PROD (requiere PROD UP)

17. **Pre-requisito:** PROD recuperado del OOM (§8.1 resuelto).
18. **NO re-importar XMLs vía REST PUT** — los OIDs no han cambiado, solo se renombraron archivos. PROD sigue siendo válido tal cual.
19. **En PROD: `git fetch origin && git checkout consolidation-2026-05-19`** en `/home/juansanchez/midPointEcosystem/`. Verificar que no haya cambios destructivos (`git diff` debe mostrar solo renames).
20. **Smoke test post-checkout:**
    - Recompute de 1 usuario piloto (`75824658`)
    - Verificar archetypes activos siguen siendo 18 (`SELECT … WHERE lifecyclestate=active`)
    - Verificar resources activos siguen siendo 5
    - Validar `UserTemplate-Person-Base` se sigue invocando

### Fase 6.8 — Merge a main + cleanup repo padre

21. Merge `consolidation-2026-05-19` → `main` via PR.
22. Tag `post-consolidation-2026-05-19`.
23. **Borrar repo `SciBack/midpoint`:**
    - GitHub: `gh repo delete SciBack/midpoint --confirm`
    - Local: `rm -rf /Users/alberto/proyectos/upeu/midpoint/{archetypes,objectTemplates,orgs,resources,roles,schema,tasks,ldap,audit,connector-keycloak-http,docs,doc,scripts,archive,context.md,.impeccable.md,vercel.json}` (mantener solo `midPointEcosystem/`, `CLAUDE.md`, `backups/`).
24. **Renombrar carpeta local** `/Users/alberto/proyectos/upeu/midpoint/` → mantener nombre, pero ahora SOLO contiene `midPointEcosystem/`. Considerar mover `midPointEcosystem/` a `/Users/alberto/proyectos/upeu/midpoint/` directamente (no anidado). Decisión post-aprobación.

### Fase 6.9 — Comunicación y limpieza memorias

25. Actualizar memorias:
    - `reference_ldap_upeu.md`: image es `osixia/openldap:1.5.0`, no bitnami
    - `project_midpoint_upeu.md`: schema activo es `urn:sciback:midpoint:person`, NO `urn:upeu:midpoint:person:v3`
    - `project_schema_architecture.md`: validar OIDs e800335c y 64ed4155
    - Crear nueva memoria: `policy_repo_structure_canonical_upeu.md`

---

## Sección 7 — Lista negra: qué se descarta sin reciclar

### 7.1 Código y artefactos del conector custom (decisión doctrinal 2026-05-11)

| Artefacto | Path | Acción |
|---|---|---|
| Conector custom `pe.upeu.connector.keycloak-http` | `/Users/alberto/proyectos/upeu/midpoint/connector-keycloak-http/` | **Archivar a `midPointEcosystem/archive/connector-keycloak-http/`** preservando código por historial. NO instalar en PROD. |
| Resource Keycloak SAML `a3f9c1d2-7e4b-4a8f-b6c3-2d1e9f0a5b87` | `resources/keycloak-resource.xml` y `resources/resource-keycloak.xml` | **DESCARTAR** ambos. No están aplicados en PROD (verificado SQL: OID `a3f9c1d2-...` no existe en `m_resource`). |
| Connector openstandia/connector-keycloak v1.1.7-SNAPSHOT instalado pero huérfano | (en PROD `m_connector`) | **Considerar uninstall via REST/UI** post-consolidación. No bloquea pero genera ruido. |
| Documentos SAML que aludan a este conector | `docs/PROMPT-onboarding-sso-academico.md` (revisar) | **Revisar y actualizar** o archivar. |

### 7.2 Resources legacy (superseded)

| Artefacto | Razón | Acción |
|---|---|---|
| `resources/oracle-lamb-{trabajadores,estudiantes,egresados}.xml` (v1) | superseded por v3 en PROD | **DESCARTAR** |
| `resources/oracle-lamb-{trabajadores,estudiantes,egresados}-v2.xml` (v2) | superseded por v3 en PROD | **DESCARTAR** |
| `tasks/task-recon-{trabajadores,estudiantes,egresados}.xml` (v1) y `…-v2.xml` (v2) | superseded por v3 + runs ad-hoc | **DESCARTAR** |
| `midPointEcosystem/midpoint/resources/entra-id/resource-msgraph-legacy.xml` | superseded por UPEU-EntraID-Graph | **DESCARTAR** (mover a `archive/previous/`) |
| `midPointEcosystem/midpoint/resources/db-sis/resource-academico-legacy.xml` | testing legacy | **DESCARTAR** (mover a `archive/previous/`) |

### 7.3 Schemas deprecated (decisión doctrinal: schemas como objetos en repo BD vía SchemaType, no archivos XSD)

| Artefacto | Razón | Acción |
|---|---|---|
| `schema/archive/DEPRECATED-schemaType-v3.0.xml` | superseded por `sciback-person-v1.0` (urn:sciback:midpoint:person) | **MANTENER en `archive/` con prefijo DEPRECATED** (ya está correcto) |
| `schema/archive/DEPRECATED-schemaType-lamb-v1.xml` | superseded por `upeu-local-v1.0` | **MANTENER en `archive/`** |
| `midPointEcosystem/midpoint/schema/archive/DEPRECATED-schema-object-upeu-person-v3.1.xml` | superseded | **MANTENER en `archive/`** |
| **Cualquier XSD en `<midpoint-home>/schema/` del contenedor MidPoint** | NO usar — schemas van como SchemaType objects | Verificar y limpiar si existe. Pendiente verificación. |

### 7.4 HTML obsoletos / a reescribir

| Artefacto | Razón | Acción |
|---|---|---|
| `docs/arquitectura.html` (en SciBack/midpoint) | Diagrama parcialmente obsoleto (no refleja Schema sciback + upeu-local, no refleja Position-Based Access Control PBAC Pilar 3 actual) | **Migrar a `midPointEcosystem/docs/` y REESCRIBIR post-consolidación** |
| `midPointEcosystem/docs/arquitectura-entraid-iga.html` | Recientemente actualizado (commits del audit Entra ID 2026-05-19) | **Mantener** |

### 7.5 Drafts duplicados

| Artefacto | Razón | Acción |
|---|---|---|
| Los 18 archetypes-draft de `SciBack/midpoint/archetypes/{user,org,role}/0X-*.xml` | Drafts sin OIDs. Los reales viven en midPointEcosystem con OIDs PROD | **DESCARTAR** todos. La capa canonical/ usa los XMLs con OIDs reales |
| Los 9 templates-draft de `SciBack/midpoint/objectTemplates/0X-*.xml` | Diseño aspiracional NO aplicado en PROD | **DESCARTAR** del repo padre. Conservar el **PRINCIPIO** (1 template por archetype) en ROADMAP.md como decisión arquitectónica futura |
| Los 31 roles-draft de `SciBack/midpoint/roles/{application,business}/0X-*.xml` | Drafts sin OIDs duplicados de midPointEcosystem | **DESCARTAR** |
| Los 3 partner-orgs-draft (`orgs/04-06-*.xml`) | Drafts; partners reales aún no en PROD (solo Colegio Unión) | **DESCARTAR drafts; crear nuevos XMLs en `upeu/orgs/partners/` cuando se necesite con OIDs propios** |

### 7.6 Audit XML forenses (volumen)

| Artefacto | Razón | Acción |
|---|---|---|
| 30 XMLs en `audit/` de SciBack/midpoint (snapshots pre/post-fix resources v2, schemaType v3 prod, legacy-deletes/, etc.) | Forensic histórico; valor decreciente | **Conservar 3-4 críticos** en `midPointEcosystem/archive/backups-2026-05/` (los `*-post-schemaScript-fix-prod` y `legacy-keycloak-a3f9c1d2-*`). **El resto DESCARTAR.** |

---

## Sección 8 — Riesgos y precauciones

### 8.1 RIESGO CRÍTICO: MidPoint PROD en OutOfMemoryError

**Estado:** verificado en logs del container `midpoint_server`:
```
Caused by: java.lang.OutOfMemoryError: Java heap space
```

**Causa probable:** upgrade reciente a 4.10.2 (hoy) + Round 5 recompute corriendo + 35.450 USER + 7 resources con shadows múltiples. La JVM no tiene heap suficiente.

**Impacto en migración:** **BLOQUEANTE.**
- No se puede hacer GET de XMLs desde REST API para verificación.
- No se puede ejecutar smoke tests post-migration.
- No se puede importar nuevos archetypes-org canónicos faltantes (Fase 6.3).

**Mitigación inmediata:**
1. Aumentar heap del container midpoint_server (`MP_MEM_INIT`, `MP_MEM_MAX` o `JAVA_OPTS -Xmx`)
2. Verificar setup actual:
   ```bash
   sshpass -p $MIDPOINT_PROD_PASS ssh midpoint-prod "docker exec midpoint_server env | grep -iE 'mem|xmx|heap'"
   ```
3. Si está en valores default (~2GB), elevar a 6-8 GB en `docker-compose.yml` y restart.
4. **Antes de restart:** `pg_dump` de la DB (paso 6.1.3 ya planificado).
5. Documentar en `docs/runbooks/recovery-oom-midpoint.md`.

**No avanzar con migración hasta que PROD esté UP y responda a REST.**

### 8.2 Backup obligatorio antes de cualquier `git mv`

- Tag `pre-consolidation-2026-05-19` en repo + push remoto.
- Backup local de `midPointEcosystem/` completo a `~/backups/`.
- pg_dump de PROD (no estrictamente necesario porque solo movemos archivos, no cambian OIDs; pero buena práctica defensiva).

### 8.3 OIDs son la columna vertebral — no cambiarlos NUNCA

- El plan §6 NO modifica OIDs. Solo renombra archivos y mueve directorios.
- PROD identifica objetos por OID, no por filename. Por eso renombrar es seguro.
- **Validación crítica:** después de `git mv`, hacer `grep -rE 'oid="[^"]+"' canonical/ upeu/ | sort -u` y comparar con consulta SQL `SELECT oid FROM m_object`. Debe haber match 1-a-1 para los XMLs versionados.

### 8.4 Gaps reconocidos (datos NO verificables en este audit)

| Gap | Razón | Mitigación |
|---|---|---|
| **No acceso REST a MidPoint PROD** | OOM en JVM (§8.1) | Inventario hecho vía SQL directo a Postgres. Suficiente para audit. |
| **No verificación Oracle LAMB** | Python thin mode no soporta 11g R2 | Confiar en memoria `reference_oracle_lamb_structure.md` (vigente). NO crítico para audit del repo. |
| **No verificación schemas custom OpenLDAP** | No se ejecutó `ldapsearch -b cn=schema,cn=config` | Pendiente post-OOM-fix. NO bloquea migración del repo. |
| **No inventario CASE/MARK/REPORT** | Volumen alto (82 cases, 39 marks, 13 reports) y no son versionables en repo (son operativos) | NO se incluyen en consolidación. Quedan en DB PROD. |
| **No verificación de includeRefs / scriptRefs internos** | Requeriría parser XML completo + cross-check | Hacer en Fase 6.6 (validación local + diff OIDs) |
| **No diff sobre 4 `aux-affiliation-*`** vs **6 `R-Affiliation-*`** | Redundancia detectada en §3.4 | Decisión post-consolidación, NO bloquea el rearreglo del repo |

### 8.5 Riesgos de orden de operaciones

| Riesgo | Mitigación |
|---|---|
| Mover XMLs antes de validar referencias rompe imports en PROD | NO importamos en PROD; solo movemos files locales. PROD lee desde su clone en `/home/juansanchez/midPointEcosystem/`. La validación post-checkout (paso 6.7.20) es el gate. |
| Cuando PROD haga `git pull` con la nueva estructura, MidPoint sigue funcionando (los OIDs son los mismos, los XMLs solo cambian de path) | OK — MidPoint no lee filesystem (a diferencia de Studio); usa DB. Sin embargo, si alguien tenía workflow de "edit file → ninja put" desde el repo, ese workflow se rompe hasta que actualice paths. Comunicar via runbook. |
| El connector Keycloak openstandia v1.1.7 huérfano puede generar errores en logs MidPoint si se referencia desde algún role | Verificar antes de uninstall que ningún AR-* lo referencia. |
| Las 4 `aux-affiliation-*` están asignadas a usuarios reales en PROD | NO TOCAR su contenido. Solo mover de path. Si decidimos deprecate, es un proyecto separado post-consolidación. |
| `MOF-*` roles tienen probablemente nodos huérfanos sin XML versionado (PROD tiene ≈25 MOF-* pero `roles/` no parece tenerlos todos) | Verificar antes de migración: descargar via REST cada MOF-* que falte y commitearlo. |

### 8.6 Plan de rollback

Si después de Fase 6.7 algo falla en PROD:
```bash
# En PROD:
cd /home/juansanchez/midPointEcosystem
git fetch origin
git checkout pre-consolidation-2026-05-19   # tag previo
# MidPoint sigue funcionando (DB intacta, OIDs intactos)

# Si la DB se corrompió por algún motivo (NO debería con git mv):
docker exec midpoint-midpoint_data-1 pg_restore -U midpoint -d midpoint -c /tmp/midpoint-pre-consolidation.dump
```

### 8.7 Validación post-migración (criterios de éxito)

| Criterio | Cómo verificar |
|---|---|
| **PROD UP** | `curl https://identity.upeu.edu.pe/midpoint/` retorna HTML, no 503 |
| **REST API responde** | `curl -u admin:pass …/users?paging=maxSize=1` retorna 200 con datos |
| **18 archetypes-activos siguen** | `SELECT COUNT(*) FROM m_archetype WHERE lifecyclestate='active'` = 18 |
| **5 resources-activos siguen** | `SELECT COUNT(*) FROM m_resource WHERE lifecyclestate='active'` = 5 |
| **35K+ usuarios siguen** | `SELECT COUNT(*) FROM m_user` ≥ 35.450 |
| **Recompute usuario piloto funciona** | Task manual recompute `75824658` completa OK |
| **Outbound LDAP/EntraID funciona** | Shadows nuevos se crean al recompute (verificar `m_shadow` count creciente o estable) |
| **No errores en log MidPoint** | `docker logs midpoint_server --tail 200 \| grep -iE 'ERROR\|FATAL\|OOM'` retorna 0 líneas críticas |

---

## Anexo A — Comandos de verificación rápida usados en este audit

```bash
# Inventario por tipo de objeto en PROD
sshpass -p $MIDPOINT_PROD_PASS ssh midpoint-prod \
  'docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tAc \
   "SELECT objecttype, COUNT(*) FROM m_object GROUP BY objecttype ORDER BY 2 DESC"'

# Archetypes activos
sshpass -p $MIDPOINT_PROD_PASS ssh midpoint-prod \
  'docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tAc \
   "SELECT nameorig, lifecyclestate FROM m_archetype WHERE lifecyclestate IS NOT NULL ORDER BY 2,1"'

# Shadows por resource
sshpass -p $MIDPOINT_PROD_PASS ssh midpoint-prod \
  'docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tAc \
   "SELECT r.nameorig, COUNT(s.*) FROM m_shadow s JOIN m_resource r ON r.oid=s.resourcereftargetoid GROUP BY r.nameorig ORDER BY 2 DESC"'

# OpenLDAP DIT y conteos
sshpass -p $MIDPOINT_PROD_PASS ssh ldap-upeu \
  "docker exec openldap ldapsearch -x -H ldap://localhost \
   -D 'cn=admin,dc=upeu,dc=edu,dc=pe' -w 'Ldap@dmin2026!' \
   -b 'ou=people,dc=upeu,dc=edu,dc=pe' '(objectclass=inetOrgPerson)' dn | grep -c '^dn:'"

# Keycloak realms/clients/IDPs/feds
sshpass -p $KC_SSH_PASS ssh keycloak-prod \
  "docker exec keycloak_app /opt/keycloak/bin/kcadm.sh config credentials --server 'http://localhost:8080' \
     --realm master --user $KC_ADMIN_USER --password $KC_ADMIN_PASS && \
   docker exec keycloak_app /opt/keycloak/bin/kcadm.sh get realms --fields realm,enabled && \
   docker exec keycloak_app /opt/keycloak/bin/kcadm.sh get clients -r upeu --fields clientId,enabled && \
   docker exec keycloak_app /opt/keycloak/bin/kcadm.sh get identity-provider/instances -r upeu --fields alias,providerId,enabled"
```

---

## Anexo B — Hallazgos críticos resumidos (5 bullets)

1. **PROD opera SOLO desde `midPointEcosystem`** (verificado en `/home/juansanchez/midPointEcosystem/` en `192.168.15.166`). El repo padre `SciBack/midpoint` nunca se desplegó. Los OIDs vivos están todos en `midPointEcosystem`.
2. **La separación canonical/upeu YA existe a nivel de schema en PROD** (`urn:sciback:midpoint:person` agnóstico + `urn:upeu:midpoint:local` overlay). La consolidación del repo en `canonical/` + `upeu/` solo formaliza esa partición existente en el árbol de directorios.
3. **MidPoint PROD está en OutOfMemoryError post-upgrade 4.10.2 de hoy** — bloquea cualquier validación REST y debe resolverse ANTES de iniciar migración (mitigación: aumentar heap JVM del container).
4. **Documentación rica (1.739 líneas) vive en `SciBack/midpoint/docs/`** (roadmap, análisis canónico, perfiles, eduperson, SSO vendors); los docs equivalentes en `midPointEcosystem/docs/` son **placeholders skeleton de 21-55 líneas**. Migrar el material rico a `midPointEcosystem/docs/` es la tarea de mayor valor inmediato.
5. **Lista negra confirmada para descartar:** conector custom `pe.upeu.connector.keycloak-http` (decisión doctrinal 2026-05-11), resource Keycloak SAML OID `a3f9c1d2-…` (nunca aplicado en PROD), todos los XMLs draft sin OID del repo padre (18 archetypes + 9 templates + 31 roles + 3 orgs partners), resources v1/v2 Oracle LAMB legacy (PROD usa v3), connector huérfano `openstandia/connector-keycloak v1.1.7` (uninstall post-consolidación).

---

**FIN DEL AUDIT.** Esperando aprobación de Alberto para ejecutar Sección 6 (Plan de Migración).
