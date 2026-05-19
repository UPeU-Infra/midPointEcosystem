# UPeU IGA — Roadmap de Ejecución 2026

**Versión:** 2026-05-11 · **Owner:** Alberto Sánchez · **Estado:** En ejecución
**Documento base:** [`iga-canonical-analysis-2026-05.md`](./iga-canonical-analysis-2026-05.md) · [`SKILL: iga-canonical-standards`](~/.claude/skills/iga-canonical-standards/SKILL.md) · [`SKILL: midpoint-best-practices`](~/.claude/skills/midpoint-best-practices/SKILL.md)

---

## Principios de ejecución

1. **Pre-prod primero, prod nunca primero.** Todo cambio se aplica en MidPoint DEV (`192.168.15.230`) antes que en PROD (`192.168.15.166`).
2. **GitOps.** Configuración va a `UPeU-Infra/midPointEcosystem` con commit + push + `git pull` en server. NUNCA `scp`.
3. **MidPoint UI Schemas, no XSD imports.** SchemaType se administra como objeto en repo (UI Admin / REST), no como archivos en `/var/schema/`.
4. **STOP antes de producción.** Confirmación explícita de Alberto antes de cada deploy productivo.
5. **Sin conector MidPoint→Keycloak.** Arquitectura: MidPoint→OpenLDAP→Keycloak User Federation.
6. **No tocar sistemas UPeU existentes.** Solo trabajamos en MidPoint + sistemas nuevos que implementemos (OpenLDAP, Keycloak nuestro). AD UPeU actual y Entra ID UPeU son **solo lectura** (correlación). Ningún write hasta decisión arquitectónica futura.
7. **Decisión AD diferida.** El AD UPeU actual no se usa globalmente, está mal estructurado, queda fuera del alcance. AD nuevo solo se construye si validamos que Entra ID NO alcanza como destino único. Por defecto: target principal = OpenLDAP + Entra ID (read-only de momento).
8. **Cuentas privilegiadas no las gestiona MidPoint.** Las maneja David Urquizo. Lo que MidPoint no puede hacer por API queda como ticket a David en [`david-urquizo-tasks.md`](./david-urquizo-tasks.md).
9. **Canónico → SciBack; UPeU-specific → overlay.** Cada pieza se marca durante su creación.

---

## Estado actual (snapshot 2026-05-11)

| Componente | Estado |
|---|---|
| Skills globales `iga-canonical-standards` + `midpoint-best-practices` | ✅ Publicadas |
| Agente `midpoint-expert` refactorizado | ✅ 231 líneas, delega a skills |
| Documento canónico `iga-canonical-analysis-2026-05.md` | ✅ Con correcciones del usuario |
| Schema extension v2.3 en MidPoint PROD | ⚠️ Activo pero a refactorizar a v3.0 canónico |
| Conector custom Keycloak `pe.upeu.connector.keycloak-http v1.0.0` | ⚠️ Funcional pero **a archivar** (decisión 2026-05-11) |
| Resource Keycloak (OID `a3f9c1d2-7e4b-4a8f-b6c3-2d1e9f0a5b87`) | ⚠️ A eliminar |
| Client Scope SAML `academic-databases-eduperson` | ✅ Funcional, se mantiene |
| Acceso Oracle LAMB (lectura) | ✅ 39 schemas — IIA principal |
| Acceso AD UPeU (LDAP) | ⚠️ Tengo lectura via cuenta Administrator pero **AD actual está OUT del alcance** (no es global, mal estructurado, no se toca) |
| Acceso Entra ID Graph (app-only) | ⚠️ El `msgraph.env` apunta al tenant **SciBack** (sandbox), NO al tenant UPeU real. Para tenant UPeU se necesitan credenciales separadas (ticket DU). |
| OpenLDAP Identity Cache | ❌ NO desplegado — destino canónico principal |

---

## Fases y dependencias

```
Fase 0 — Refactor doctrinal (1 día)            ✅ HECHO
   └─ Skills publicadas, agente actualizado, doc canónico

Fase 1 — Schema canónico v3.0 (3-4 días)       ◀── EMPEZAMOS AQUÍ
   └─ SchemaType vía UI MidPoint DEV → migrar v2.3 → v3.0

Fase 2 — Arquetipos y org tree (3-4 días)
   └─ 8 archetypes + jerarquía Institution→Site→Faculty→Department

Fase 3 — Object templates canónicos (2-3 días)
   └─ ePPN, ePUI, ePSA derivados (NO persistidos en schema)

Fase 4 — OpenLDAP HA Identity Cache (3 días)
   └─ 2 nodos N-Way Multimaster

Fase 5 — Resources read (Oracle LAMB, AD, Entra ID) (1 semana)
   └─ Solo INBOUND inicialmente. Reconcilia 18 usuarios locales Keycloak.

Fase 6 — Resources write controlled (3-4 días)
   └─ MidPoint → OpenLDAP (provisioning) + Keycloak federation de OpenLDAP

Fase 7 — RBAC bottom-up (1 semana)
   └─ ~15 application roles + 11 business roles + role mining LAMB_ROL

Fase 8 — Replanteo de documentos (3 días)
   └─ Schema docs, drawio, memorias, READMEs

Fase 9 — Validación end-to-end con piloto (2-3 días)
   └─ User de prueba completa el flujo: LAMB → MidPoint → OpenLDAP → Keycloak → SAML → Scopus

Fase 10 — Despliegue en PROD (1 día + ventana)  ◀── REQUIERE APROBACIÓN ALBERTO

Fase 11 — Productización SciBack (1 semana)
   └─ Extraer pieza canónica a sciback-iga-blueprint

Fase 12 — Gobierno Entra ID UPeU (cuando MidPoint esté maduro)
   └─ Reorganizar estructura/usuarios/licencias según modelo IGA
```

**Nota sobre Fase 12:** Cuando el modelo IGA en MidPoint esté estabilizado (Fases 1–11 OK + piloto validado + productización SciBack lista), Alberto coordinará con David Urquizo para **reorganizar Entra ID UPeU según el modelo canónico** que estamos adoptando (eduPerson, SCHAC, arquetipos, OUs canónicos, licenciamiento gobernado por archetype). Hasta entonces, Entra ID es **solo lectura** para correlación.

---

## Roadmap detallado (paso a paso)

### Fase 1 — Schema canónico v3.0

| # | Tarea | Archivos / objetos afectados | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 1.1 | **Auditar SchemaType v2.3 vigente** vía REST API en MidPoint DEV. Exportar XML. | Reporte `audit-schema-v2.3.md` | 1h | — | pre-prod auto |
| 1.2 | **Diseñar SchemaType v3.0 canónico** (`urn:upeu:midpoint:person` v3.0). Solo atributos UPeU-specific no presentes en eduPerson/SCHAC/SCIM core. **Eliminar** atributos derivables (ePPN, ePSA, scopedAffiliation, primaryAffiliationCode si se deriva). **Mantener:** studentCycle, hireDate/terminationDate, institutionalIdCard, studyModality, academicProgramCode, taxId (DNI). Documentar deprecations. | `schema/upeu-person-v3.0.xml` (draft) | 4h | 1.1 | Alberto |
| 1.3 | **Crear SchemaType v3.0 en MidPoint DEV vía UI Admin** (Schema → Edit → Apply). NO usar `<midpoint-home>/schema/*.xsd`. Persistir como objeto en repo BD. | DEV repo BD | 2h | 1.2 + Alberto OK | pre-prod auto |
| 1.4 | **Validar v3.0** con un user de prueba (`testuser01`) — todos los atributos accesibles vía UI y REST. | Test manual + reporte | 2h | 1.3 | pre-prod auto |

**Salida Fase 1:** SchemaType v3.0 activo en DEV, retro-compatible con v2.3.

### Fase 2 — Arquetipos y Org tree

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 2.1 | **8 archetypes UserType canónicos** definidos vía UI Admin / REST: student, employee-faculty, employee-staff, affiliate-partner-institution, affiliate-researcher, alumni, contractor, service-account. Configurar icon, color, label, lifecycleState applicable. | `archetypes/user/*.xml` | 4h | Fase 1 | pre-prod auto |
| 2.2 | **6 archetypes OrgType canónicos**: institution, campus, faculty, department, partner-institution, project. | `archetypes/org/*.xml` | 3h | Fase 1 | pre-prod auto |
| 2.3 | **OrgType bootstrap UPeU** — crear la jerarquía real: 1 institution (`UPeU`) → 3 campus internos (`C-LIM`, `C-JUL`, `C-TPP`) + 3 partner-institution (`P-CGH`, `P-ISTAT`, `P-AGTU`). Naming: 3 letras consistente con `ELISEO.ORG_SEDE.SIGLA`. | `orgs/bootstrap-upeu.xml` | 2h | 2.2 | Alberto |
| 2.4 | **Faculties + Departments UPeU** — modelar desde `ELISEO.ORG_DEPENDENCIA` (los 11 tipos misionales) y `ELISEO.ORG_ESCUELA_PROFESIONAL`. Sincronizar inicialmente vía import manual (luego se automatiza vía Resource Oracle). | `orgs/faculties-departments.xml` | 4h | 2.3 | Alberto |

**Salida Fase 2:** Catálogo completo de archetypes + org tree base navegable en UI.

### Fase 3 — Object templates canónicos

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 3.1 | **commonUserTemplate** — genera derivados: `name`, `fullName`, `eduPersonPrincipalName` (ePPN = `<id>@upeu.edu.pe`), `eduPersonUniqueId` (ePUI = `<employeeNumber>@upeu.edu.pe`), `scopedAffiliation`, `schacHomeOrganization` (constante `upeu.edu.pe`), `schacPersonalUniqueID` URN-encoded (DNI). Usar `assignmentTargetSearch` para birthright. | `objectTemplates/commonUserTemplate.xml` | 4h | Fase 2 | pre-prod auto |
| 3.2 | **Templates por archetype** — uno por cada UserType archetype con specifics (e.g., `student.xml` genera `eduPersonAffiliation=student,member`; `employee-faculty.xml` agrega `+faculty,+employee,+member`). Composición vía `<includeRef>`. | `objectTemplates/per-archetype/*.xml` | 6h | 3.1 | pre-prod auto |
| 3.3 | **Iteration spec para ePPN únicos** — `<iterationSpecification>` para resolver colisiones. Token compartido entre mappings. Estrategia: usar `employeeNumber` (inmutable) cuando exista; fallback a iteration. | parte de `commonUserTemplate.xml` | 2h | 3.1 | pre-prod auto |
| 3.4 | **Validar templates** con 3 users de prueba (1 student, 1 faculty, 1 partner) — verificar derivados correctos. | Test report | 2h | 3.3 | pre-prod auto |

**Salida Fase 3:** Object templates produciendo atributos canónicos correctos.

### Fase 4 — OpenLDAP HA Identity Cache

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 4.1 | **Diseñar DIT canónico**: `dc=upeu,dc=edu,dc=pe` con `ou=people`, `ou=groups`, `ou=orgs`. Object classes: `inetOrgPerson`, `eduPerson`, `schacPersonalCharacteristics`, `upeuPerson` (auxiliary custom para extension). | `docs/openldap-dit-design.md` | 3h | Fase 3 | Alberto |
| 4.2 | **Desplegar OpenLDAP nodo 1** en VM dedicada (a definir con Alberto: ¿`192.168.15.232`?). Docker Compose. Schema eduPerson + SCHAC importados. Cuenta admin + cuenta `cn=midpoint,...` para escritura + cuenta `cn=keycloak,...` para lectura. | `~/proyectos/upeu/openldap/docker-compose.yml` | 4h | 4.1 + Alberto define VM | Alberto |
| 4.3 | **Desplegar OpenLDAP nodo 2** con replicación syncrepl N-Way Multimaster. Verificar replicación bidireccional. | nodo2 docker-compose | 4h | 4.2 | Alberto |
| 4.4 | **Documentar credenciales** en `~/.secrets/openldap-upeu.env`. | `~/.secrets/openldap-upeu.env` | 30min | 4.3 | — |

**Salida Fase 4:** OpenLDAP HA listo, 0 usuarios, schema cargado.

### Fase 5 — Resources READ (fuentes autoritativas)

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 5.1 | **Resource Oracle LAMB JDBC — Trabajadores** (IIA empleados). Usa vistas `MOISES.*` + `ELISEO.VW_APS_EMPLEADO`. Solo inbound (lectura). Strong para datos canónicos. Correlación por `employeeNumber`. | `resources/oracle-lamb-trabajadores.xml` | 6h | Fase 3 + driver ojdbc11 instalado | Alberto |
| 5.2 | **Resource Oracle LAMB JDBC — Estudiantes** (IIA matrículas). Usa vistas `DAVID.VW_PERSONA_ALUMNO`, `DAVID.VW_FICHA_MATRICULA`. Solo inbound. Correlación por código estudiante. | `resources/oracle-lamb-estudiantes.xml` | 6h | Fase 3 | Alberto |
| 5.3 | **Resource Oracle LAMB JDBC — OrgUnits** (IIA estructura). Vistas `ELISEO.ORG_SEDE`, `ELISEO.ORG_SEDE_AREA`, `ELISEO.ORG_ESCUELA_PROFESIONAL`. Genera OrgType automáticamente. | `resources/oracle-lamb-orgs.xml` | 4h | Fase 3 | Alberto |
| 5.4 | ~~Resource AD LDAP~~ — **OUT del alcance** (AD UPeU actual no es global, mal estructurado, decisión 2026-05-11). El conocimiento se preserva en `docs/upeu-ad-snapshot.md` para auditoría histórica. | — | — | — | — |
| 5.5 | **Resource Entra ID Graph — READ ONLY** sobre tenant UPeU real (NO el sandbox SciBack). Reconciliar identidades + licencias M365 (A1/A3) + membresía grupos. **NO write** hasta Fase 12. | `resources/entraid-upeu-readonly.xml` | 6h | Fase 3 + credenciales tenant UPeU (ver DU-001a) | Alberto |
| 5.6 | **Import inicial + reconciliation** — desde Oracle LAMB Trabajadores, importar 50 users de prueba (un subset por sede). Verificar archetype assignment, mappings inbound, validación de DNI. | Tarea import | 3h | 5.1, 5.2, 5.3, 5.5 | Alberto |

**Salida Fase 5:** MidPoint tiene visión consolidada de identidades UPeU desde 4 fuentes (Oracle, AD, Entra ID + correlaciones).

### Fase 6 — Resources WRITE controlled

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 6.1 | **Resource OpenLDAP — provisioning** (write). Outbound mappings con todos los atributos eduPerson/SCHAC computados por object templates. Schema handling: `kind=account` + `entitlement` para groups. | `resources/openldap-identity-cache.xml` | 6h | Fase 4 + Fase 5 | Alberto |
| 6.2 | **Provisionar 5 users de prueba a OpenLDAP** desde MidPoint. Verificar atributos eduPerson en LDAP browser. | Test + ldapsearch | 1h | 6.1 | pre-prod auto |
| 6.3 | **Configurar Keycloak User Federation contra OpenLDAP** (en UI Keycloak admin). Mapeo de atributos eduPerson a SAML Client Scope `academic-databases-eduperson`. NO conector MidPoint→Keycloak. | Keycloak UI | 3h | 6.2 | Alberto |
| 6.4 | **Eliminar Resource Keycloak** en MidPoint DEV (`keycloak-resource.xml` con OID `a3f9c1d2-7e4b-4a8f-b6c3-2d1e9f0a5b87`). **Archivar** el conector custom `pe.upeu.connector.keycloak-http-1.0.0.jar` en `~/proyectos/upeu/midpoint/archive/`. | DELETE en MidPoint DEV + mv del JAR | 1h | 6.3 | Alberto |
| 6.5 | **Validar SAML response** con SAMLtest.id como SP de prueba. Verificar atributos eduPerson presentes (ePPN, ePSA, schacHomeOrganization, mail, displayName). | Test SAMLtest.id | 2h | 6.3 | pre-prod auto |
| 6.6 | ~~Resource AD LDAP — limited write~~ — **OUT del alcance** (AD actual no se toca; decisión 2026-05-11). Si Entra ID resulta insuficiente como destino global, se evaluará AD nuevo en una fase futura aparte. | — | — | — | — |
| 6.7 | ~~Resource Entra ID Graph — limited write~~ — **DIFERIDO a Fase 12**. Cuando MidPoint esté maduro y validado, se reorganiza Entra ID UPeU según el modelo IGA canónico (licencias por archetype, OUs, grupos). En Fase 6 Entra ID sigue siendo solo lectura. | — | — | — | — |

**Salida Fase 6:** Flujo completo MidPoint → OpenLDAP → Keycloak → SAML → Vendor funcionando con 5 usuarios de prueba. **No se escribe a AD ni Entra ID** (write a Entra ID se hace en Fase 12 cuando el modelo esté maduro).

### Fase 7 — RBAC bottom-up

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 7.1 | **Application Roles canónicos** — ~15 AR en `roles/application/`: M365-Student-A1, M365-Faculty-A1, M365-Faculty-A3, M365-Staff-A3, EntraID-Group-*, AD-Docentes/Estudiantes/Staff, Koha-Patron-Student/Faculty/Librarian, DSpace-Submitter/Editor, OJS-Reviewer, Indico-User, Keycloak-realm-upeu, FreeRADIUS-VPN-Docentes. Cada uno con archetype `application-role`. | `roles/application/*.xml` | 8h | Fase 6 | pre-prod auto |
| 7.2 | **Business Roles canónicos** — 11 BR en `roles/business/`: BR-Docente-TC, BR-Docente-TP, BR-Estudiante-Pregrado, BR-Estudiante-Posgrado, BR-Estudiante-Doctorado, BR-Admin-Area (paramétrico), BR-Bibliotecario, BR-Investigador, BR-Egresado, BR-Decano, BR-Visitante-Investigacion. Cada uno con archetype `business-role` + inducements a Application Roles. | `roles/business/*.xml` | 6h | 7.1 | pre-prod auto |
| 7.3 | **Auto-asignación vía object templates** — para cada archetype, configurar `assignmentTargetSearch` que asigna Business Roles automáticamente según condiciones (e.g., archetype=student + ciclo<=10 → BR-Estudiante-Pregrado). | upgrade `objectTemplates/per-archetype/*.xml` | 4h | 7.2 | pre-prod auto |
| 7.4 | **SoD policies** — 2 reglas SSoD mínimas (ISO 27001 A.8.2): Admin-Nomina ⊥ Aprobador-Pagos; Auditor-Sistemas ⊥ Operador-Sistemas. | `policy/sod/canonical-sod-rules.xml` | 2h | 7.2 | Alberto |
| 7.5 | **Role mining piloto sobre `ELISEO.LAMB_ROL`** — analizar combinaciones reales de los 656 roles legacy. Producir reporte con candidatos a Business Roles UPeU-specific. | Reporte `role-mining-lamb-piloto.md` + nuevos roles en `roles/business/upeu-specific/` | 8h | Fase 5 (Oracle resource activo) | Alberto |

**Salida Fase 7:** RBAC operacional. Un user con archetype=student recibe automáticamente BR-Estudiante-Pregrado + todas sus app roles + M365-A1 + Koha-Patron-Student + acceso a Wi-Fi.

### Fase 8 — Replanteo de documentos

| # | Tarea | Documento / archivo | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 8.1 | **Replantear `schema/README-extension-guia.md`** — refactorizar a v3.0 canónico. Eliminar atributos derivables. Documentar deprecations v2.3→v3.0. | `schema/README-extension-guia.md` | 2h | Fase 1 estable | pre-prod auto |
| 8.2 | **Replantear `docs/sso-academico-vendors-mapping.md`** — actualizar diagrama de flujo (MidPoint→OpenLDAP→Keycloak), nuevos archetypes, mappers SAML eduPerson finales. | `docs/sso-academico-vendors-mapping.md` | 2h | Fase 6 | pre-prod auto |
| 8.3 | **Replantear `docs/eduperson-attributes-reference.md`** — alinear con eduPerson 202208 (no inventar). Tabla de OIDs canónica. | `docs/eduperson-attributes-reference.md` | 1h | Fase 1 | pre-prod auto |
| 8.4 | **Replantear `docs/ciclo-vida-sso-upeu.drawio`** — agregar OpenLDAP como hub central, eliminar conector MidPoint→Keycloak. Mantener flujos 1-7. | `docs/ciclo-vida-sso-upeu.drawio` | 2h | Fase 6 | Alberto |
| 8.5 | **Actualizar memorias** del proyecto: `project_midpoint_upeu.md`, `project_sso_academico.md`, `project_schema_extension_guia.md`, `project_arquitectura_iga.md`, `project_oracle_iga.md`. Reflejar v3.0, OpenLDAP, sin conector Keycloak, M365 no Google. | `~/.claude/projects/-Users-alberto-proyectos-upeu-midpoint/memory/*.md` | 3h | Fase 6 estable | pre-prod auto |
| 8.6 | **Actualizar `MEMORY.md`** principal con índice de docs actualizados. | `~/.claude/projects/-Users-alberto-proyectos-upeu-midpoint/memory/MEMORY.md` | 30min | 8.5 | — |

**Salida Fase 8:** Documentación coherente con el modelo canónico.

### Fase 9 — Validación end-to-end con piloto

| # | Tarea | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|
| 9.1 | **Seleccionar 3 users piloto** (1 docente TC, 1 estudiante pregrado, 1 staff). | 30min | Fase 7 | Alberto |
| 9.2 | **Flujo completo end-to-end**: importar desde Oracle LAMB → auto-assign archetype → object template → birthright BR → app roles → outbound a OpenLDAP → Keycloak federation → SAML login a SAMLtest.id + Scopus piloto. | 4h | 9.1 | Alberto |
| 9.3 | **Documentar resultado** + screenshots + audit logs. Reporte para ISO 27001 evidence. | 2h | 9.2 | — |

### Fase 10 — Despliegue en PROD (192.168.15.166)

| # | Tarea | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|
| 10.1 | **STOP — Aprobación explícita Alberto** para tocar prod. | — | Fase 9 OK | **Alberto** |
| 10.2 | **Backup completo MidPoint PROD** (DB PostgreSQL + config). | 1h | 10.1 | — |
| 10.3 | **Aplicar configuración** vía GitOps (`git pull` en `/opt/midpoint/`). En orden: SchemaType v3.0 → archetypes → orgs → templates → resources → roles → policies. Pausar entre cada bloque para verificar. | 4-6h | 10.2 | Alberto |
| 10.4 | **Validación post-deploy** — flujo end-to-end en PROD con 1 user real. | 2h | 10.3 | Alberto |

### Fase 11 — Productización SciBack

| # | Tarea | Archivos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 11.1 | **Crear repo `~/proyectos/sciback/sciback-iga-blueprint`** con estructura overlay. | repo nuevo | 1h | Fase 10 | — |
| 11.2 | **Extraer piezas canónicas** (archetypes, object templates genéricos, application role templates `.tmpl`, SoD policies). Sustituir hardcodes UPeU por placeholders `${INSTITUTION_NAME}`, `${SCOPE}`, `${HOME_ORG_TYPE_URN}`. | en `sciback-iga-blueprint` | 6h | 11.1 | — |
| 11.3 | **Crear `~/proyectos/upeu/iga/`** como overlay UPeU. Contiene: schema extension UPeU-only, resources Oracle LAMB, orgs bootstrap UPeU, partner institutions, BR derivados de role mining Lamb. | overlay UPeU | 4h | 11.2 | — |
| 11.4 | **Documentación SciBack**: `README.md`, `INSTALL.md`, `OVERLAYS.md`. | docs blueprint | 2h | 11.3 | — |

### Fase 12 — Gobierno completo Entra ID UPeU (cuando MidPoint esté maduro)

**Pre-condición:** Fases 1–11 OK, piloto end-to-end validado, productización SciBack lista. Esta fase es la **adopción real** del modelo IGA en el tenant UPeU productivo.

| # | Tarea | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|
| 12.1 | **Diagnóstico estado actual Entra ID UPeU** — inventario completo: usuarios, grupos, OUs, licencias M365 asignadas/disponibles, MFA enrolment, conditional access policies. Reporte para auditoría. | 6h | Credenciales tenant UPeU (DU-001a) | Alberto + David |
| 12.2 | **Diseñar mapeo canónico → Entra ID UPeU** — qué OU/group existe, qué falta, qué renombrar, qué consolidar. Mapeo de archetypes a estructura Entra ID. Plan de migración sin disrupciones. | 8h | 12.1 | Alberto + David |
| 12.3 | **Crear estructura nueva en Entra ID** (manual via UI por David) — OUs según árbol canónico, grupos `grp-upeu-<archetype>`, nomenclatura consistente. NO migrar usuarios todavía. | 6h | 12.2 + ventana operativa | David (ejecuta) |
| 12.4 | **Resource Entra ID Graph WRITE en MidPoint** — outbound mappings para: `licenseAssignment`, group membership, atributos eduPerson custom (mediante extension attributes). | 8h | 12.3 + scopes write concedidos | Alberto |
| 12.5 | **Migración progresiva por archetype** — primero `service-account` (low impact), luego `affiliate-researcher`, luego `employee-staff`, luego `employee-faculty`, finalmente `student`. Cada bloque con validación + rollback documentado. | 16h | 12.4 + ventanas operativas | Alberto + David |
| 12.6 | **Decommissioning de estructura legacy Entra ID** — archivar grupos viejos, retirar licencias huérfanas, consolidar OUs duplicadas. | 4h | 12.5 completo | David |
| 12.7 | **Decisión sobre AD nuevo** — basado en lo aprendido: si Entra ID + MidPoint cubren 100% de necesidades, NO se construye AD nuevo. Si quedan brechas (Wi-Fi 802.1X, file shares legacy, NPS), planificar AD nuevo en sub-roadmap aparte. | 4h reunión | 12.5 | Alberto + dirección DTI |

**Salida Fase 12:** Entra ID UPeU gobernado completamente por MidPoint según modelo canónico. Decisión definitiva sobre AD nuevo.

### Fase 13 — Métricas COUNTER de bases de datos académicas

**Objetivo:** reportes de uso de Scopus, WoS, IEEE, ProQuest, EBSCO con granularidad por facultad y programa académico para acreditaciones SUNEDU/SINEACE y renovación de licencias. Keycloak+LDAP pasa atributos SAML que EZProxy nunca pudo pasar — esta fase capitaliza esa ventaja.

**Pre-condición:** F4 OpenLDAP con `upeuAcademicProgramCode`/`upeuFacultyCode` en schema, F7 AR-Vendor-* desglosados (no genérico), migración EZProxy → Keycloak completa.

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 13.1 | **Configurar Protocol Mappers SAML** en Keycloak — por client de cada vendor: mapear `upeuAcademicProgramCode` y `ou` (facultad) como atributos SAML. NameFormat URI Reference. | Keycloak UI — clients Scopus, WoS, IEEE, EBSCO, ProQuest | 3h | F4 OpenLDAP + F6 Keycloak federation | Alberto |
| 13.2 | **Obtener credenciales SUSHI** de cada vendor — pedir en portal o a consultor: endpoint SUSHI v5, API key o user/password. Confirmar soporte COUNTER 5 (no 4). | `~/.secrets/sushi-vendors.env` | 2h gestión | — | Alberto |
| 13.3 | **Schema PostgreSQL** — tablas COUNTER 5: `tr_b1` (título), `dr_d1` (base de datos), `pr_p1` (plataforma), `ir_a1` (ítem). Join view con snapshot Oracle LAMB (programa, facultad, campus). | `metrics/schema-counter5.sql` | 3h | 13.2 | — |
| 13.4 | **Script Python SUSHI harvester** — `sushi-harvest.py` parametrizado por vendor. Harvest semanal vía cron. Guarda en PostgreSQL. | `metrics/sushi-harvest.py` | 6h | 13.2 + 13.3 | — |
| 13.5 | **Dashboards Grafana** — 3 vistas: "Uso por facultad", "Top recursos por programa académico", "Tendencia mensual por vendor". | `metrics/dashboards/*.json` | 4h | 13.4 | Alberto |
| 13.6 | **Procedimiento de reportes** — reporte ejecutivo trimestral para acreditaciones + checklist renovación de licencias con datos de uso real. | `docs/counter-reporting-procedure.md` | 2h | 13.5 | — |

**Nota sobre vendors y atributos SAML:** Scopus (Elsevier) y WoS (Clarivate) soportan segmentación por `ou`/custom attribute en sus reportes institucionales. EBSCO y ProQuest tienen soporte parcial — confirmar al configurar SP. Si el vendor no soporta atributos, el harvest SUSHI + join con Oracle LAMB (vía MidPoint snapshot) cubre cualquier dimensión igualmente.

**Salida Fase 13:** dashboard de uso de recursos académicos por facultad/programa, script de harvest automatizado, y reporte ejecutivo listo para presentar a acreditadoras o en negociación de licencias.

---

## Tiempos consolidados

| Fase | Estim | Acumulado |
|---|---|---|
| 0. Refactor doctrinal | (hecho) | — |
| 1. Schema v3.0 | 9h | 9h |
| 2. Archetypes + Org tree | 13h | 22h |
| 3. Object templates | 14h | 36h |
| 4. OpenLDAP HA | 11.5h | 47.5h |
| 5. Resources READ | 25h | 72.5h |
| 6. Resources WRITE | 13h | 85.5h |
| 7. RBAC bottom-up | 28h | 113.5h |
| 8. Replanteo docs | 10.5h | 124h |
| 9. Validación piloto | 6.5h | 130.5h |
| 10. Despliegue PROD | 8h + ventana | 138.5h |
| 11. Productización SciBack | 13h | 151.5h |
| 12. Gobierno Entra ID UPeU | 52h + ventanas | 203.5h |
| 13. Métricas COUNTER | 20h | 223.5h |

**Fases 1–11:** ~152h = ~4 sprints de 2 semanas (modelo IGA maduro en MidPoint + producto SciBack).
**Fase 12:** +52h adicionales = ~1 sprint (adopción Entra ID UPeU).
**Fase 13:** +20h adicionales = métricas COUNTER con granularidad institucional.
**Total proyectado:** ~224h.

---

## Bloqueantes y dependencias externas

| # | Bloqueante | Para qué fase | Acción / quién |
|---|---|---|---|
| B1 | VM para OpenLDAP nodo 1 + nodo 2 | Fase 4 | Alberto define IPs (sugerencia: `192.168.15.232` + `.233`) |
| B2 | `ojdbc11.jar` instalado en MidPoint dev + prod | Fase 5.1 | Descargar de Oracle.com + copiar a `lib/` |
| B3 | **Credenciales Graph API del tenant UPeU real** (no SciBack sandbox) | Fase 5.5 | Ticket DU-001a — David registra app-only en tenant UPeU con scopes mínimos read |
| B4 | Confirmar que `DAVID.VW_DATOS_IDENTIDAD_USUARIO` es leíble | Fase 5.1 | Probar con `SELECT` en sesión actual |
| B5 | Para Fase 12: scopes write en tenant UPeU + decisión migración | Fase 12 | Posterga a cuando MidPoint esté maduro |
| B6 | Convenio RENIEC para validación DNI (IAL 3) | futuro | Área Desarrollo UPeU (no bloqueante para piloto) |

**Bloqueantes RETIRADOS** (decisión 2026-05-11):
- ~~Cuenta de servicio `svc-midpoint-iga` en AD~~ — AD UPeU OUT del alcance.
- ~~Decisión cuenta para writes Entra ID~~ — diferido a Fase 12.

---

## Decisiones doctrinales registradas (no negociables)

1. **2026-05-11** — NO crear nuevo conector MidPoint→Keycloak. Tampoco usar `pe.upeu.connector.keycloak-http v1.0.0` ni `openstandia/connector-keycloak`. La arquitectura es **MidPoint → OpenLDAP ← Keycloak (User Federation)**.
2. **2026-05-11** — UPeU NO usa Moodle ni Google Workspace. El stack es **Microsoft 365** (licencias A1/A3) + **Google Classroom** (SaaS externo integrado vía URLs en Lamb).
3. **2026-05-11** — Campus codes 3 letras: `C-LIM`, `C-JUL`, `C-TPP` (consistente con `ELISEO.ORG_SEDE.SIGLA`).
4. **2026-05-11** — Cuentas privilegiadas las gestiona **David Urquizo**, no MidPoint. Tickets en `david-urquizo-tasks.md`.
5. **2026-05-11** — SchemaType se administra vía UI Admin (objeto en repo), no como XSD files.
6. **2026-05-11** — **AD UPeU actual queda OUT del alcance.** No se lee, no se escribe. Mal estructurado, no es global. La decisión sobre AD nuevo se difiere a Fase 12 cuando hayamos validado si Entra ID gobernado por MidPoint cubre necesidades.
7. **2026-05-11** — **Entra ID UPeU es solo lectura hasta Fase 12.** En Fase 5 se importa para correlación (identidades, licencias, grupos existentes). El gobierno completo (writes) comienza solo cuando el modelo IGA en MidPoint esté maduro y validado end-to-end. Antes de Fase 12 no se modifica ningún objeto en Entra ID UPeU.
8. **2026-05-11** — `msgraph.env` actual apunta al tenant **SciBack** (sandbox personal), NO al tenant UPeU real. Para tenant UPeU se necesita app registration separada (ver DU-001a).
9. **2026-05-11** — **No se modifica ningún sistema UPeU existente.** Solo MidPoint + sistemas nuevos (OpenLDAP HA). Keycloak existente (`192.168.12.88`) sí es nuestro y se reconfigura.

---

## Siguiente acción inmediata

**Tarea 1.1 — Auditar SchemaType v2.3 vigente.** Estimación 1h. No requiere aprobación. Salida: reporte con el XML completo del SchemaType actual + análisis de qué se mantiene en v3.0 y qué se elimina/migra.

Una vez tengamos la auditoría:
- Diseñar v3.0 (tarea 1.2, 4h)
- **STOP — Confirmación Alberto** del diseño v3.0
- Aplicar v3.0 en DEV (tarea 1.3)
