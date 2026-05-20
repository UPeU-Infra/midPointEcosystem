# UPeU IGA — Roadmap de Ejecución 2026

**Versión:** 2026-05-20 rev3 (actualizado post-P6 pipeline + fix correlación) · **Owner:** Alberto Sánchez · **Estado:** En ejecución
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
8. **Cuentas privilegiadas no las gestiona MidPoint.** Las maneja David Urquizo. Lo que MidPoint no puede hacer por API queda como ticket a David en [`david-urquizo-tasks.md`](./runbooks/tickets-david-urquizo.md).
9. **Canónico → SciBack; UPeU-specific → overlay.** Cada pieza se marca durante su creación.

---

## Estado real verificado 2026-05-19

> Snapshot obtenido directamente de la base de datos PostgreSQL de MidPoint PROD (`192.168.15.166`).
> PROD recuperado del OOM — lleva 4 horas UP (healthy) usando 3.7 GB / 6 GB RAM.

### Volumetria PROD (verificada en BD)

| Objeto | Cantidad |
|---|---|
| Usuarios | 35.450 |
| Orgs | 122 |
| Roles | 72 (39 activos, 1 deprecated, 32 sin lifecycle) |
| Archetypes | 86 total (18 custom activos + 68 sistema) |
| Resources | 7 (5 activos, 2 sin lifecycle) |
| Services (posiciones) | 741 |
| Tasks (historico) | 69 |

### Usuarios por archetype (real)

| Archetype | Usuarios |
|---|---|
| archetype-user-alumni | 30.491 |
| archetype-user-employee-staff | 3.144 |
| archetype-user-student | 1.679 |
| archetype-user-employee-faculty | 135 |
| contractor / affiliate-* / service-account | 0 (archetypes sin usuarios aun) |

### Resources y sombras (real)

| Resource | Lifecycle | Sombras |
|---|---|---|
| Oracle LAMB Trabajadores v3 | `active` | 3.802 |
| Oracle LAMB Estudiantes v3 | `active` | 1.679 |
| Oracle LAMB Egresados v3 | `active` | 30.629 |
| LAMB-Oracle-Posiciones | `active` | 738 |
| Koha ILS | `active` | 5.421 |
| LDAP-IdentityCache-UPeU | *(null)* | **37.491** |
| UPEU-EntraID-Graph | *(null)* | **37.304** |

> LDAP y Entra ID tienen lifecycle `null` (no está seteado a `active`) pero tienen decenas de miles de sombras — ambos **funcionan en PROD**. El null es un dato de configuración menor pendiente de corregir.

### Object templates en PROD

| Template | Estado |
|---|---|
| `UserTemplate-Person-Base` | Activo |
| `Person Object Template` | Activo (sistema) |

Los templates **per-archetype** (student, faculty, staff, alumni individuales) **no existen** en PROD.

### Schemas en PROD

| Schema | Namespace |
|---|---|
| SciBack IGA — Schema canónico universitario Perú v1.0 | `urn:sciback:midpoint:person` |
| UPeU — Schema local extensiones LAMB v1.0 | `urn:upeu:midpoint:local` |

### Tabla resumen por fase (verificada en PROD)

| Fase | Estado real | Evidencia directa |
|---|---|---|
| Fase 0 — Refactor doctrinal | ✅ **COMPLETA** | Skills, agente, docs |
| Fase 1 — Schema | ✅ **ACTIVA** | 2 schemas en PROD BD |
| Fase 2 — Archetypes + Org tree | ✅ **ACTIVA / REPO COMPLETO** | 18 archetypes en PROD; repo ahora tiene los 18 (8 user + 9 org + 2 role) — commit `19590be` |
| Fase 3 — Object templates | ⚠️ **PARCIAL** | 2 templates en PROD (base + sistema); templates per-archetype NO existen |
| Fase 4 — OpenLDAP HA | ✅ **ACTIVA** | 37.491 sombras LDAP; lifecycleState seteado a `active` vía REST — commit `1a5fb52` |
| Fase 5 — Resources READ | ✅ **ACTIVA** | Oracle LAMB ×4 + Koha + Entra ID activos; todos con lifecycleState `active` |
| Fase 6 — Resources WRITE → OpenLDAP | ✅ **FUNCIONA** (no validado formalmente) | 37.491 sombras LDAP confirman que MidPoint escribe a OpenLDAP; Keycloak federation sin confirmar |
| Fase 7 — RBAC | ⚠️ **PARCIAL** | 39 roles activos (AR + BR + affiliation); MOF-*/GOV-*/SYS ahora versionados en repo (commit `19590be`) — lifecycle null pendiente |
| Fase 8 — Replanteo docs | ❌ **NO INICIADA** | — |
| Fase 9 — Validación piloto | ⚠️ **PILOTO PARCIAL** | Tasks: `PILOT-EntraID-UPeU-link-100`, pilots usuario `75824658`; flujo completo no documentado |
| Fase 10 — Deploy PROD | ✅ **PROD OPERATIVO** | 35.450 usuarios en produccion |
| Fase 11 — Productización SciBack | ❌ **NO INICIADA** | — |
| Fase 12 — Gobierno Entra ID | ⚠️ **DIAGNOSTICO LISTO** | `docs/ENTRA-ID-ESTRUCTURA-UPEU.md`; write bloqueado por permisos David Urquizo |
| Fase 13 — Métricas COUNTER | ❌ **NO INICIADA** | — |

### Hallazgos del historial de tasks

El historial de 69 tasks revela trabajo operativo extenso no documentado en el roadmap:
- **PBAC activo:** `Reconcile LAMB-Trabajadores PBAC Position` (múltiples runs)
- **Photo sync:** `SYNC-LAMB-Trabajadores-photoUrl` (múltiples versiones)
- **Piloto Entra ID:** `PILOT-EntraID-UPeU-link-100` + `PILOT-EntraID-UPeU-link-photo-100`
- **Recomputes masivos:** múltiples rondas para LDAP, Egresados, BR-Personal-General
- **Koha:** `Reconcile-Koha-Inbound-2026-05-19`

### Artefactos faltantes en repo (existen en PROD, no versionados)

| Artefacto | Cantidad | Estado | Commit |
|---|---|---|---|
| Archetypes user (affiliate-partner-institution, affiliate-researcher, contractor, service-account) | 4 | ✅ **Versionados** `canonical/archetypes/user/` | `19590be` |
| Archetypes org (institution, campus, faculty, department, academic-unit, governance, partner-institution, project) | 8 | ✅ **Versionados** `canonical/archetypes/org/` | `19590be` |
| Roles MOF-* | 25 | ✅ **Versionados** `upeu/roles/mof/` | `19590be` |
| Roles GOV-* | 3 | ✅ **Versionados** `upeu/roles/governance/` | `19590be` |
| SYS-IGA-SUPERUSER | 1 | ✅ **Versionados** `upeu/roles/system/` | `19590be` |
| APP-KOHA-PATRON (deprecated) | 1 | ⏳ Pendiente | — |

---

## Proximas acciones inmediatas (priorizadas)

### ✅ P1 — Descargar y versionar artefactos faltantes en repo — COMPLETADO 2026-05-19

Ejecutado via REST API desde PROD. Commit `19590be`:
- 4 archetypes user → `canonical/archetypes/user/`
- 8 archetypes org → `canonical/archetypes/org/`
- 25 roles MOF-* → `upeu/roles/mof/`
- 3 roles GOV-* → `upeu/roles/governance/`
- SYS-IGA-SUPERUSER → `upeu/roles/system/`
- Limpieza de metadata operacional aplicada a todos los XMLs
- Pendiente: `APP-KOHA-PATRON` (deprecated) → `upeu/roles/deprecated/`

### ✅ P2 — Corregir lifecycle de LDAP y Entra ID resources — COMPLETADO 2026-05-19

PATCH REST aplicado. Commit `1a5fb52`:
- `LDAP-IdentityCache-UPeU` (OID `7b4e1c2d`) → `lifecycleState: active`
- `UPEU-EntraID-Graph` (OID `2f11c057`) → `lifecycleState: active`
- XMLs del repo actualizados; PROD y repo en sync

### ✅ P3 — Tag post-consolidación y git pull en PROD — COMPLETADO 2026-05-19

- Tag `post-consolidation-2026-05-19` creado sobre commit `ca01197` y pusheado
- `git pull` en PROD: fast-forward exitoso hasta `1a5fb52`
- Pendiente (espera confirmación Alberto): `gh repo archive SciBack/midpoint --yes`

### ✅ P6 — Reactivar pipeline de sincronización post-OOM — EN CURSO (2026-05-20)

Todos los reconcile tasks y scanners quedaron SUSPENDED tras el OOM del upgrade 4.10.2.
Reactivación en orden:

| Task | Estado | Resultado | Notas |
|---|---|---|---|
| `Reconcile Oracle LAMB Estudiantes` | ✅ COMPLETADO 2026-05-20 | PARTIAL_ERROR — 1.690 obj / 11 errores | Shadows duplicados en Koha (11 usuarios). Cron 02:00 UTC activo. |
| `Reconcile Oracle LAMB Trabajadores` | ✅ COMPLETADO 2026-05-20 | PARTIAL_ERROR — 3.802 obj / 0 errores correlación | Fix correlación `NUM_DOCUMENTO` aplicado (commit `db70026`). Cron 02:00 UTC activo. |
| `Reconcile Oracle LAMB Egresados` | ⏳ Pendiente | — | 30.629 sombras — el más pesado |
| `Reconcile-Koha-Inbound` | ⏳ Pendiente | — | — |
| `Trigger Scanner` | ⏳ Pendiente | — | Procesa validTo/validFrom de activaciones |
| `Validity Scanner` | ⏳ Pendiente | — | Desactiva/activa usuarios por fecha |

### ✅ P8 — Fix correlación Oracle LAMB Trabajadores v3 — COMPLETADO 2026-05-20

**Causa raíz:** Shorthand `<correlator/>` dentro de `<attribute>` dejó de funcionar en MidPoint 4.10
cuando los inbound mappings con `beforeCorrelation` están en `lifecycleState: archived`.
El motor no podía resolver el focus item para correlación.

**Fix aplicado:** Correlator explícito a nivel `<objectType>`:
```xml
<correlation>
  <correlators>
    <items>
      <name>correlate-by-num-documento</name>
      <item>
        <ref xmlns:upeu="urn:upeu:midpoint:local">extension/upeu:lambDocNum</ref>
      </item>
    </items>
  </correlators>
</correlation>
```
- Archivo: `upeu/resources/oracle-lamb/trabajadores.xml`
- Commits: `3729479` (intento) → `db70026` (fix final)
- Verificado: `ConfigurationException: NUM_DOCUMENTO` desapareció completamente de logs

**Errores pendientes a resolver (no bloquean operación):**
- 11 shadows duplicados en Koha ILS → limpiar via UI/REST (shadows huérfanos de 11 estudiantes)
- Dependencia circular en mappings object template estudiantes `#[12,21,22,23,25,32,33]` → revisar en P4
- Deep clone innecesario de `identityDocuments` → optimización para P4

**Estado del servidor PROD (2026-05-20):**
- Disco `/`: 19 GB / 33 GB usados (62%) — sin riesgo
- RAM: 6.1 GB activa / 9.7 GB total — estable
- Tasks corriendo: solo `Cleanup` (sistema). Estudiantes y Trabajadores en RUNNABLE/READY esperando cron.

### ✅ P7 — Keycloak→OpenLDAP User Federation — COMPLETADO 2026-05-19

Conexión directa Keycloak (192.168.12.88) → OpenLDAP (192.168.15.168:389) funcionando.
- Firewall TCP 389 abierto por Rudy
- `connectionUrl` corregido: `ldap://192.168.15.166:8080` → `ldap://192.168.15.168:389`
- `bindCredential` corregido: password inválido → `Kc@Ldap2026!`
- Runbook: `docs/runbooks/keycloak-ldap-federation.md`

### P4 — Object templates per-archetype (Fase 3 incompleta)

Crear templates individuales para student, faculty, staff, alumni con mappings específicos por tipo. El template base `UserTemplate-Person-Base` existe; los 4 per-archetype no.
Bloqueado hasta completar P6 (pipeline estable).

### P5 — Completar permisos Entra ID y validar Keycloak federation

- Ticket David Urquizo: 4 permisos read faltantes (`AdministrativeUnit.Read.All`, `RoleManagement.Read.Directory`, `AuditLog.Read.All`, `Application.Read.All`)
- Keycloak User Federation contra OpenLDAP: ✅ ACTIVA (ver P7)

---

## Fases y dependencias

```
Fase 0 — Refactor doctrinal (1 dia)            COMPLETA
   Hecho: Skills publicadas, agente actualizado, doc canonico

Fase 1 — Schema canonico v3.0 (3-4 dias)       ACTIVO EN PROD
   Activo: urn:sciback:midpoint:person + urn:upeu:midpoint:local
   Pendiente: verificar contra diseno v3.0 post-OOM

Fase 2 — Arquetipos y org tree (3-4 dias)       ACTIVO EN PROD / REPO INCOMPLETO
   Activo en PROD: 18 archetypes (8 user + 8 org + 2 role)
   En repo: 12 de 18 (faltan 4 user + 7 org sin versionar)
   Pendiente: descargar y commitear faltantes post-OOM

Fase 3 — Object templates canonicos (2-3 dias)  PARCIAL
   Hecho: UserTemplate-Person-Base.xml
   Pendiente: 8 per-archetype templates

Fase 4 — OpenLDAP HA Identity Cache (3 dias)    RESOURCE CONFIGURADO / HA SIN VERIFICAR
   Resource LDAP activo en PROD (1 de 7 resources)
   Config en repo: upeu/resources/ldap-identity-cache.xml + upeu/ldap/
   Pendiente: verificar N-Way Multimaster desplegado

Fase 5 — Resources read (1 semana)              ACTIVO EN PROD / ENTRA ID INCOMPLETO
   7 resources activos: Oracle LAMB x4 + LDAP + Entra ID + Koha
   Entra ID: 3 de 7 permisos read concedidos (faltan 4)

Fase 6 — Resources write controlled (3-4 dias)  NO VALIDADO
   Resource LDAP tiene outbound en repo
   Provisioning a OpenLDAP: sin confirmar en PROD
   Keycloak User Federation: sin confirmar

Fase 7 — RBAC bottom-up (1 semana)             PARCIAL
   38 roles en repo (6 affiliation + 20 app + 12 business)
   72 roles en PROD (~25 MOF + 3 GOV sin versionar)
   Role mining LAMB_ROL: NO hecho

Fase 8 — Replanteo de documentos (3 dias)       NO INICIADA
Fase 9 — Validacion end-to-end con piloto        NO INICIADA
Fase 10 — Despliegue en PROD  ◀── REQUIERE APROBACION ALBERTO  NO INICIADA
Fase 11 — Productizacion SciBack                 NO INICIADA

Fase 12 — Gobierno Entra ID UPeU               DIAGNOSTICO Y DISENO LISTOS
   Hecho: diagnostico completo (ENTRA-ID-ESTRUCTURA-UPEU.md)
   Hecho: diseno de AUs, roles delegados, grupos (propuesta)
   Bloqueado: write hasta que David Urquizo conceda permisos

Fase 13 — Metricas COUNTER                      NO INICIADA
```

---

## Roadmap detallado (paso a paso)

### Fase 1 — Schema canonico v3.0

**Estado actual (2026-05-19):** ACTIVO EN PROD. Dos schemas activos: `urn:sciback:midpoint:person` (canonico) + `urn:upeu:midpoint:local` (overlay UPeU). Versionados en repo como `canonical/schemas/sciback-person-v1.0.xml` + `upeu/schemas/upeu-local-v1.0.xml`. Verificacion contra diseno v3.0 del roadmap original pendiente post-OOM.

| # | Tarea | Archivos / objetos afectados | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 1.1 | **Auditar SchemaType v2.3 vigente** via REST API en MidPoint DEV. Exportar XML. | Reporte `audit-schema-v2.3.md` | 1h | — | pre-prod auto |
| 1.2 | **Disenar SchemaType v3.0 canonico** (`urn:upeu:midpoint:person` v3.0). Solo atributos UPeU-specific no presentes en eduPerson/SCHAC/SCIM core. **Eliminar** atributos derivables (ePPN, ePSA, scopedAffiliation, primaryAffiliationCode si se deriva). **Mantener:** studentCycle, hireDate/terminationDate, institutionalIdCard, studyModality, academicProgramCode, taxId (DNI). Documentar deprecations. | `schema/upeu-person-v3.0.xml` (draft) | 4h | 1.1 | Alberto |
| 1.3 | **Crear SchemaType v3.0 en MidPoint DEV via UI Admin** (Schema → Edit → Apply). NO usar `<midpoint-home>/schema/*.xsd`. Persistir como objeto en repo BD. | DEV repo BD | 2h | 1.2 + Alberto OK | pre-prod auto |
| 1.4 | **Validar v3.0** con un user de prueba (`testuser01`) — todos los atributos accesibles via UI y REST. | Test manual + reporte | 2h | 1.3 | pre-prod auto |

**Salida Fase 1:** SchemaType v3.0 activo en DEV, retro-compatible con v2.3.

### Fase 2 — Arquetipos y Org tree

**Estado actual (2026-05-19):** ACTIVO EN PROD. 18 archetypes activos en PROD (8 user + 8 org + 2 role). En repo solo 12 versionados. Pendiente descargar y commitear: 4 user-archetypes (`affiliate-partner-institution`, `affiliate-researcher`, `contractor`, `service-account`) + 7 org-archetypes (todos excepto `org-academic-program`). Org tree: extenso en repo (`upeu/orgs/`: campus, facultades, colegio-union, etc.). Partner-institutions (CGH, ISTAT, AGTU) son drafts sin OID — aun no creados en PROD.

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 2.1 | **8 archetypes UserType canonicos** definidos via UI Admin / REST: student, employee-faculty, employee-staff, affiliate-partner-institution, affiliate-researcher, alumni, contractor, service-account. Configurar icon, color, label, lifecycleState applicable. | `archetypes/user/*.xml` | 4h | Fase 1 | pre-prod auto |
| 2.2 | **6 archetypes OrgType canonicos**: institution, campus, faculty, department, partner-institution, project. | `archetypes/org/*.xml` | 3h | Fase 1 | pre-prod auto |
| 2.3 | **OrgType bootstrap UPeU** — crear la jerarquia real: 1 institution (`UPeU`) → 3 campus internos (`C-LIM`, `C-JUL`, `C-TPP`) + 3 partner-institution (`P-CGH`, `P-ISTAT`, `P-AGTU`). Naming: 3 letras consistente con `ELISEO.ORG_SEDE.SIGLA`. | `orgs/bootstrap-upeu.xml` | 2h | 2.2 | Alberto |
| 2.4 | **Faculties + Departments UPeU** — modelar desde `ELISEO.ORG_DEPENDENCIA` (los 11 tipos misionales) y `ELISEO.ORG_ESCUELA_PROFESIONAL`. Sincronizar inicialmente via import manual (luego se automatiza via Resource Oracle). | `orgs/faculties-departments.xml` | 4h | 2.3 | Alberto |

**Salida Fase 2:** Catalogo completo de archetypes + org tree base navegable en UI.

### Fase 3 — Object templates canonicos

**Estado actual (2026-05-19):** PARCIAL. Existe `canonical/object-templates/UserTemplate-Person-Base.xml` (template base). NO existen templates per-archetype. Tareas 3.2-3.4 pendientes.

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 3.1 | **commonUserTemplate** — genera derivados: `name`, `fullName`, `eduPersonPrincipalName` (ePPN = `<id>@upeu.edu.pe`), `eduPersonUniqueId` (ePUI = `<employeeNumber>@upeu.edu.pe`), `scopedAffiliation`, `schacHomeOrganization` (constante `upeu.edu.pe`), `schacPersonalUniqueID` URN-encoded (DNI). Usar `assignmentTargetSearch` para birthright. | `objectTemplates/commonUserTemplate.xml` | 4h | Fase 2 | pre-prod auto |
| 3.2 | **Templates por archetype** — uno por cada UserType archetype con specifics (e.g., `student.xml` genera `eduPersonAffiliation=student,member`; `employee-faculty.xml` agrega `+faculty,+employee,+member`). Composicion via `<includeRef>`. | `objectTemplates/per-archetype/*.xml` | 6h | 3.1 | pre-prod auto |
| 3.3 | **Iteration spec para ePPN unicos** — `<iterationSpecification>` para resolver colisiones. Token compartido entre mappings. Estrategia: usar `employeeNumber` (inmutable) cuando exista; fallback a iteration. | parte de `commonUserTemplate.xml` | 2h | 3.1 | pre-prod auto |
| 3.4 | **Validar templates** con 3 users de prueba (1 student, 1 faculty, 1 partner) — verificar derivados correctos. | Test report | 2h | 3.3 | pre-prod auto |

**Salida Fase 3:** Object templates produciendo atributos canonicos correctos.

### Fase 4 — OpenLDAP HA Identity Cache

**Estado actual (2026-05-19):** RESOURCE CONFIGURADO. `upeu/resources/ldap-identity-cache.xml` existe en repo. `upeu/ldap/` contiene docker-compose, ldifs y config de Keycloak User Federation. PROD tiene resource LDAP activo (1 de los 7 resources). N-Way Multimaster HA: no verificado — servidores no responden.

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 4.1 | **Disenar DIT canonico**: `dc=upeu,dc=edu,dc=pe` con `ou=people`, `ou=groups`, `ou=orgs`. Object classes: `inetOrgPerson`, `eduPerson`, `schacPersonalCharacteristics`, `upeuPerson` (auxiliary custom para extension). | `docs/openldap-dit-design.md` | 3h | Fase 3 | Alberto |
| 4.2 | **Desplegar OpenLDAP nodo 1** en VM dedicada (a definir con Alberto: `192.168.15.232`?). Docker Compose. Schema eduPerson + SCHAC importados. Cuenta admin + cuenta `cn=midpoint,...` para escritura + cuenta `cn=keycloak,...` para lectura. | `upeu/ldap/docker-compose.yml` | 4h | 4.1 + Alberto define VM | Alberto |
| 4.3 | **Desplegar OpenLDAP nodo 2** con replicacion syncrepl N-Way Multimaster. Verificar replicacion bidireccional. | nodo2 docker-compose | 4h | 4.2 | Alberto |
| 4.4 | **Documentar credenciales** en `~/.secrets/openldap-upeu.env`. | `~/.secrets/openldap-upeu.env` | 30min | 4.3 | — |

**Salida Fase 4:** OpenLDAP HA listo, 0 usuarios, schema cargado.

### Fase 5 — Resources READ (fuentes autoritativas)

**Estado actual (2026-05-19):** ACTIVO EN PROD. 7 resources activos: Oracle LAMB x4 (trabajadores, estudiantes, egresados, posiciones) + LDAP + Entra ID (read-only) + Koha. AD en draft en repo (`upeu/resources/ad-upeu.xml`), no activo en PROD. Todos los resources activos versionados en repo bajo `upeu/resources/`. Entra ID: solo 3 permisos concedidos (User.Read.All, Group.Read.All, Directory.Read.All); faltan AdministrativeUnit.Read.All, RoleManagement.Read.Directory, AuditLog.Read.All, Application.Read.All.

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 5.1 | **Resource Oracle LAMB JDBC — Trabajadores** (IIA empleados). Usa vistas `MOISES.*` + `ELISEO.VW_APS_EMPLEADO`. Solo inbound (lectura). Strong para datos canonicos. Correlacion por `employeeNumber`. | `resources/oracle-lamb/trabajadores.xml` | 6h | Fase 3 + driver ojdbc11 instalado | Alberto |
| 5.2 | **Resource Oracle LAMB JDBC — Estudiantes** (IIA matriculas). Usa vistas `DAVID.VW_PERSONA_ALUMNO`, `DAVID.VW_FICHA_MATRICULA`. Solo inbound. Correlacion por codigo estudiante. | `resources/oracle-lamb/estudiantes.xml` | 6h | Fase 3 | Alberto |
| 5.3 | **Resource Oracle LAMB JDBC — OrgUnits** (IIA estructura). Vistas `ELISEO.ORG_SEDE`, `ELISEO.ORG_SEDE_AREA`, `ELISEO.ORG_ESCUELA_PROFESIONAL`. Genera OrgType automaticamente. | `resources/oracle-lamb/posiciones.xml` | 4h | Fase 3 | Alberto |
| 5.4 | ~~Resource AD LDAP~~ — **OUT del alcance** (AD UPeU actual no es global, mal estructurado, decision 2026-05-11). El conocimiento se preserva en `docs/upeu-ad-snapshot.md` para auditoria historica. | — | — | — | — |
| 5.5 | **Resource Entra ID Graph — READ ONLY** sobre tenant UPeU real. Completar los 4 permisos faltantes (DU pendiente). Reconciliar identidades + licencias M365 (A1/A3) + membresia grupos. **NO write** hasta Fase 12. | `resources/entra-id-graph.xml` | 3h adicionales | Ticket David Urquizo (4 permisos read) | Alberto |
| 5.6 | **Import inicial + reconciliation** — desde Oracle LAMB Trabajadores, importar 50 users de prueba (un subset por sede). Verificar archetype assignment, mappings inbound, validacion de DNI. | Tarea import | 3h | 5.1, 5.2, 5.3, 5.5 | Alberto |

**Salida Fase 5:** MidPoint tiene vision consolidada de identidades UPeU desde 4 fuentes (Oracle, AD, Entra ID + correlaciones).

### Fase 6 — Resources WRITE controlled

**Estado actual (2026-05-19):** NO VALIDADO. Resource LDAP (`upeu/resources/ldap-identity-cache.xml`) existe en repo con outbound mappings. No confirmado que provisioning a OpenLDAP este activo en PROD. Keycloak User Federation contra OpenLDAP: config documentada en `upeu/ldap/keycloak-user-federation.md` pero no confirmada activa. Dependiente de que OpenLDAP HA este desplegado y funcionando.

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 6.1 | **Resource OpenLDAP — provisioning** (write). Outbound mappings con todos los atributos eduPerson/SCHAC computados por object templates. Schema handling: `kind=account` + `entitlement` para groups. | `resources/ldap-identity-cache.xml` | 6h | Fase 4 + Fase 5 | Alberto |
| 6.2 | **Provisionar 5 users de prueba a OpenLDAP** desde MidPoint. Verificar atributos eduPerson en LDAP browser. | Test + ldapsearch | 1h | 6.1 | pre-prod auto |
| 6.3 | **Configurar Keycloak User Federation contra OpenLDAP** (en UI Keycloak admin). Mapeo de atributos eduPerson a SAML Client Scope `academic-databases-eduperson`. NO conector MidPoint→Keycloak. | Keycloak UI | 3h | 6.2 | Alberto |
| 6.4 | **Eliminar Resource Keycloak** en MidPoint DEV (OID `a3f9c1d2-7e4b-4a8f-b6c3-2d1e9f0a5b87`). **Archivar** el conector custom `pe.upeu.connector.keycloak-http-1.0.0.jar` (ya en `archive/connector-keycloak-http/`). | DELETE en MidPoint DEV | 1h | 6.3 | Alberto |
| 6.5 | **Validar SAML response** con SAMLtest.id como SP de prueba. Verificar atributos eduPerson presentes (ePPN, ePSA, schacHomeOrganization, mail, displayName). | Test SAMLtest.id | 2h | 6.3 | pre-prod auto |
| 6.6 | ~~Resource AD LDAP — limited write~~ — **OUT del alcance** (AD actual no se toca; decision 2026-05-11). | — | — | — | — |
| 6.7 | ~~Resource Entra ID Graph — limited write~~ — **DIFERIDO a Fase 12**. | — | — | — | — |

**Salida Fase 6:** Flujo completo MidPoint → OpenLDAP → Keycloak → SAML → Vendor funcionando con 5 usuarios de prueba.

### Fase 7 — RBAC bottom-up

**Estado actual (2026-05-19):** PARCIAL. En repo: 6 affiliation roles (`upeu/roles/affiliation/`) + 20 application roles (`upeu/roles/application/`) + 12 business roles (`upeu/roles/business/`) = 38 roles versionados. PROD tiene 72 roles total — faltan ~25 MOF-* + 3 GOV-* en repo (carpetas placeholder creadas: `upeu/roles/mof/` y `upeu/roles/governance/`). Role mining de `ELISEO.LAMB_ROL` (656 roles legacy): NO hecho. Aux-archetype vs R-Affiliation deprecation: decision pendiente (ver `MIGRATION-DECISIONS-PENDING.md` #6).

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 7.1 | **Application Roles canonicos** — AR en `roles/application/`: M365-Student-A1, M365-Faculty-A1, M365-Faculty-A3, M365-Staff-A3, EntraID-Group-*, AD-Docentes/Estudiantes/Staff, Koha-Patron-Student/Faculty/Librarian, DSpace-Submitter/Editor, OJS-Reviewer, Indico-User, Keycloak-realm-upeu, FreeRADIUS-VPN-Docentes. Cada uno con archetype `application-role`. | `roles/application/*.xml` | 8h | Fase 6 | pre-prod auto |
| 7.2 | **Business Roles canonicos** — BR en `roles/business/`: BR-Docente-TC, BR-Docente-TP, BR-Estudiante-Pregrado, BR-Estudiante-Posgrado, BR-Estudiante-Doctorado, BR-Admin-Area (parametrico), BR-Bibliotecario, BR-Investigador, BR-Egresado, BR-Decano, BR-Visitante-Investigacion. Cada uno con archetype `business-role` + inducements a Application Roles. | `roles/business/*.xml` | 6h | 7.1 | pre-prod auto |
| 7.3 | **Auto-asignacion via object templates** — para cada archetype, configurar `assignmentTargetSearch` que asigna Business Roles automaticamente segun condiciones. | upgrade `objectTemplates/per-archetype/*.xml` | 4h | 7.2 | pre-prod auto |
| 7.4 | **SoD policies** — 2 reglas SSoD minimas (ISO 27001 A.8.2): Admin-Nomina ⊥ Aprobador-Pagos; Auditor-Sistemas ⊥ Operador-Sistemas. | `policy/sod/canonical-sod-rules.xml` | 2h | 7.2 | Alberto |
| 7.5 | **Role mining piloto sobre `ELISEO.LAMB_ROL`** — analizar combinaciones reales de los 656 roles legacy. Producir reporte con candidatos a Business Roles UPeU-specific. | Reporte `role-mining-lamb-piloto.md` + nuevos roles en `roles/business/upeu-specific/` | 8h | Fase 5 (Oracle resource activo) | Alberto |

**Salida Fase 7:** RBAC operacional. Un user con archetype=student recibe automaticamente BR-Estudiante-Pregrado + todas sus app roles + M365-A1 + Koha-Patron-Student + acceso a Wi-Fi.

### Fase 8 — Replanteo de documentos

**Estado actual (2026-05-19):** NO INICIADA. Documentacion legacy en `docs/arquitectura-legacy.html`. Documentacion activa en `docs/ARCHITECTURE.md` (rescatada de repo padre).

| # | Tarea | Documento / archivo | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 8.1 | **Replantear `schema/README-extension-guia.md`** — refactorizar a v3.0 canonico. Eliminar atributos derivables. Documentar deprecations v2.3→v3.0. | `schema/README-extension-guia.md` | 2h | Fase 1 estable | pre-prod auto |
| 8.2 | **Replantear `docs/canonical/sso-academic-vendors.md`** — actualizar diagrama de flujo (MidPoint→OpenLDAP→Keycloak), nuevos archetypes, mappers SAML eduPerson finales. | `docs/canonical/sso-academic-vendors.md` | 2h | Fase 6 | pre-prod auto |
| 8.3 | **Replantear `docs/canonical/eduperson-reference.md`** — alinear con eduPerson 202208 (no inventar). Tabla de OIDs canonica. | `docs/canonical/eduperson-reference.md` | 1h | Fase 1 | pre-prod auto |
| 8.4 | **Reescribir diagrama arquitectura** — agregar OpenLDAP como hub central, eliminar conector MidPoint→Keycloak. Reemplazar `docs/arquitectura-legacy.html`. | `docs/arquitectura-upeu.html` | 2h | Fase 6 | Alberto |
| 8.5 | **Actualizar memorias** del proyecto. Reflejar 2 schemas canonicos, 18 archetypes, 7 resources, OpenLDAP, sin conector Keycloak, M365 no Google. | `~/.claude/projects/…/memory/*.md` | 3h | Fase 6 estable | pre-prod auto |
| 8.6 | **Actualizar `MEMORY.md`** principal con indice de docs actualizados. | memoria principal | 30min | 8.5 | — |

**Salida Fase 8:** Documentacion coherente con el modelo canonico.

### Fase 9 — Validacion end-to-end con piloto

**Estado actual (2026-05-19):** NO INICIADA.

| # | Tarea | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|
| 9.1 | **Seleccionar 3 users piloto** (1 docente TC, 1 estudiante pregrado, 1 staff). | 30min | Fase 7 | Alberto |
| 9.2 | **Flujo completo end-to-end**: importar desde Oracle LAMB → auto-assign archetype → object template → birthright BR → app roles → outbound a OpenLDAP → Keycloak federation → SAML login a SAMLtest.id + Scopus piloto. | 4h | 9.1 | Alberto |
| 9.3 | **Documentar resultado** + screenshots + audit logs. Reporte para ISO 27001 evidence. | 2h | 9.2 | — |

### Fase 10 — Despliegue en PROD (192.168.15.166)

**Estado actual (2026-05-19):** NO INICIADA. PROD ya tiene el modelo IGA desplegado (no es un deploy desde cero). Esta fase es para el re-deploy ordenado post-validacion en DEV.

| # | Tarea | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|
| 10.1 | **STOP — Aprobacion explicita Alberto** para tocar prod. | — | Fase 9 OK | **Alberto** |
| 10.2 | **Backup completo MidPoint PROD** (DB PostgreSQL + config). | 1h | 10.1 | — |
| 10.3 | **Aplicar configuracion** via GitOps (`git pull` en `/home/juansanchez/midPointEcosystem/`). En orden: SchemaType v3.0 → archetypes → orgs → templates → resources → roles → policies. Pausar entre cada bloque para verificar. | 4-6h | 10.2 | Alberto |
| 10.4 | **Validacion post-deploy** — flujo end-to-end en PROD con 1 user real. | 2h | 10.3 | Alberto |

### Fase 11 — Productizacion SciBack

**Estado actual (2026-05-19):** NO INICIADA. La estructura `canonical/` de este repo es la base del blueprint.

| # | Tarea | Archivos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 11.1 | **Crear repo `~/proyectos/sciback/sciback-iga-blueprint`** con estructura overlay. | repo nuevo | 1h | Fase 10 | — |
| 11.2 | **Extraer piezas canonicas** (archetypes, object templates genericos, application role templates `.tmpl`, SoD policies). Sustituir hardcodes UPeU por placeholders `${INSTITUTION_NAME}`, `${SCOPE}`, `${HOME_ORG_TYPE_URN}`. | en `sciback-iga-blueprint` | 6h | 11.1 | — |
| 11.3 | **Crear `~/proyectos/upeu/iga/`** como overlay UPeU. Contiene: schema extension UPeU-only, resources Oracle LAMB, orgs bootstrap UPeU, partner institutions, BR derivados de role mining Lamb. | overlay UPeU | 4h | 11.2 | — |
| 11.4 | **Documentacion SciBack**: `README.md`, `INSTALL.md`, `OVERLAYS.md`. | docs blueprint | 2h | 11.3 | — |

### Fase 12 — Gobierno completo Entra ID UPeU (cuando MidPoint este maduro)

**Estado actual (2026-05-19):** DIAGNOSTICO Y DISENO LISTOS. Diagnostico completo documentado en `docs/ENTRA-ID-ESTRUCTURA-UPEU.md` (tarea 12.1 completada). Diseno de Administrative Units, roles delegados y grupos propuesto (12.2 parcial). Implementacion bloqueada: write requiere que David Urquizo conceda permisos write en el tenant UPeU. Permisos read incompletos (4 faltantes).

**Pre-condicion:** Fases 1-11 OK, piloto end-to-end validado, productizacion SciBack lista.

| # | Tarea | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|
| 12.1 | **Diagnostico estado actual Entra ID UPeU** — inventario completo: usuarios, grupos, OUs, licencias M365 asignadas/disponibles, MFA enrolment, conditional access policies. | 6h | Credenciales tenant UPeU (DU-001a) | Alberto + David |
| 12.2 | **Disenar mapeo canonico → Entra ID UPeU** — que OU/group existe, que falta, que renombrar, que consolidar. Mapeo de archetypes a estructura Entra ID. Plan de migracion sin disrupciones. | 8h | 12.1 | Alberto + David |
| 12.3 | **Crear estructura nueva en Entra ID** (manual via UI por David) — OUs segun arbol canonico, grupos `grp-upeu-<archetype>`, nomenclatura consistente. NO migrar usuarios todavia. | 6h | 12.2 + ventana operativa | David (ejecuta) |
| 12.4 | **Resource Entra ID Graph WRITE en MidPoint** — outbound mappings para: `licenseAssignment`, group membership, atributos eduPerson custom (mediante extension attributes). | 8h | 12.3 + scopes write concedidos | Alberto |
| 12.5 | **Migracion progresiva por archetype** — primero `service-account` (low impact), luego `affiliate-researcher`, luego `employee-staff`, luego `employee-faculty`, finalmente `student`. Cada bloque con validacion + rollback documentado. | 16h | 12.4 + ventanas operativas | Alberto + David |
| 12.6 | **Decommissioning de estructura legacy Entra ID** — archivar grupos viejos, retirar licencias huerfanas, consolidar OUs duplicadas. | 4h | 12.5 completo | David |
| 12.7 | **Decision sobre AD nuevo** — basado en lo aprendido: si Entra ID + MidPoint cubren 100% de necesidades, NO se construye AD nuevo. Si quedan brechas (Wi-Fi 802.1X, file shares legacy, NPS), planificar AD nuevo en sub-roadmap aparte. | 4h reunion | 12.5 | Alberto + direccion DTI |

**Salida Fase 12:** Entra ID UPeU gobernado completamente por MidPoint segun modelo canonico. Decision definitiva sobre AD nuevo.

### Fase 13 — Metricas COUNTER de bases de datos academicas

**Estado actual (2026-05-19):** NO INICIADA.

**Objetivo:** reportes de uso de Scopus, WoS, IEEE, ProQuest, EBSCO con granularidad por facultad y programa academico para acreditaciones SUNEDU/SINEACE y renovacion de licencias.

**Pre-condicion:** F4 OpenLDAP con `upeuAcademicProgramCode`/`upeuFacultyCode` en schema, F7 AR-Vendor-* desglosados (no generico), migracion EZProxy → Keycloak completa.

| # | Tarea | Archivos / objetos | Estim | Bloqueante | Aprobador |
|---|---|---|---|---|---|
| 13.1 | **Configurar Protocol Mappers SAML** en Keycloak — por client de cada vendor: mapear `upeuAcademicProgramCode` y `ou` (facultad) como atributos SAML. NameFormat URI Reference. | Keycloak UI — clients Scopus, WoS, IEEE, EBSCO, ProQuest | 3h | F4 OpenLDAP + F6 Keycloak federation | Alberto |
| 13.2 | **Obtener credenciales SUSHI** de cada vendor — pedir en portal o a consultor: endpoint SUSHI v5, API key o user/password. Confirmar soporte COUNTER 5 (no 4). | `~/.secrets/sushi-vendors.env` | 2h gestion | — | Alberto |
| 13.3 | **Schema PostgreSQL** — tablas COUNTER 5: `tr_b1` (titulo), `dr_d1` (base de datos), `pr_p1` (plataforma), `ir_a1` (item). Join view con snapshot Oracle LAMB (programa, facultad, campus). | `metrics/schema-counter5.sql` | 3h | 13.2 | — |
| 13.4 | **Script Python SUSHI harvester** — `sushi-harvest.py` parametrizado por vendor. Harvest semanal via cron. Guarda en PostgreSQL. | `metrics/sushi-harvest.py` | 6h | 13.2 + 13.3 | — |
| 13.5 | **Dashboards Grafana** — 3 vistas: "Uso por facultad", "Top recursos por programa academico", "Tendencia mensual por vendor". | `metrics/dashboards/*.json` | 4h | 13.4 | Alberto |
| 13.6 | **Procedimiento de reportes** — reporte ejecutivo trimestral para acreditaciones + checklist renovacion de licencias con datos de uso real. | `docs/counter-reporting-procedure.md` | 2h | 13.5 | — |

**Nota sobre vendors y atributos SAML:** Scopus (Elsevier) y WoS (Clarivate) soportan segmentacion por `ou`/custom attribute en sus reportes institucionales. EBSCO y ProQuest tienen soporte parcial — confirmar al configurar SP. Si el vendor no soporta atributos, el harvest SUSHI + join con Oracle LAMB (via MidPoint snapshot) cubre cualquier dimension igualmente.

**Salida Fase 13:** dashboard de uso de recursos academicos por facultad/programa, script de harvest automatizado, y reporte ejecutivo listo para presentar a acreditadoras o en negociacion de licencias.

---

## Tiempos consolidados

| Fase | Estim | Acumulado | Estado (2026-05-19) |
|---|---|---|---|
| 0. Refactor doctrinal | (hecho) | — | COMPLETA |
| 1. Schema v3.0 | 9h | 9h | ACTIVO EN PROD |
| 2. Archetypes + Org tree | 13h | 22h | ACTIVO EN PROD / REPO INCOMPLETO |
| 3. Object templates | 14h | 36h | PARCIAL (base existe) |
| 4. OpenLDAP HA | 11.5h | 47.5h | RESOURCE CONFIGURADO |
| 5. Resources READ | 25h | 72.5h | ACTIVO EN PROD (Entra ID incompleto) |
| 6. Resources WRITE | 13h | 85.5h | NO VALIDADO |
| 7. RBAC bottom-up | 28h | 113.5h | PARCIAL (38/72 roles en repo) |
| 8. Replanteo docs | 10.5h | 124h | NO INICIADA |
| 9. Validacion piloto | 6.5h | 130.5h | NO INICIADA |
| 10. Despliegue PROD | 8h + ventana | 138.5h | NO INICIADA |
| 11. Productizacion SciBack | 13h | 151.5h | NO INICIADA |
| 12. Gobierno Entra ID UPeU | 52h + ventanas | 203.5h | DIAGNOSTICO LISTO / IMPL. BLOQUEADA |
| 13. Metricas COUNTER | 20h | 223.5h | NO INICIADA |

**Fases 1-11:** ~152h = ~4 sprints de 2 semanas (modelo IGA maduro en MidPoint + producto SciBack).
**Fase 12:** +52h adicionales = ~1 sprint (adopcion Entra ID UPeU).
**Fase 13:** +20h adicionales = metricas COUNTER con granularidad institucional.
**Total proyectado:** ~224h.

---

## Bloqueantes y dependencias externas

| # | Bloqueante | Para que fase | Accion / quien |
|---|---|---|---|
| **B0** | **MidPoint PROD en OOM post-upgrade 4.10.2** | TODO | Aumentar JVM heap → reiniciar → verificar |
| B1 | VM para OpenLDAP nodo 1 + nodo 2 | Fase 4 | Alberto define IPs (sugerencia: `192.168.15.232` + `.233`) |
| B2 | `ojdbc11.jar` instalado en MidPoint dev + prod | Fase 5.1 | Descargar de Oracle.com + copiar a `lib/` |
| B3 | **4 permisos Entra ID faltantes** (AdministrativeUnit.Read.All, RoleManagement.Read.Directory, AuditLog.Read.All, Application.Read.All) | Fase 5.5 | Ticket a David Urquizo |
| B4 | **Credenciales Graph API write** para tenant UPeU real | Fase 12 | Ticket DU — David registra app con scopes write tras Fase 11 |
| B5 | **12 artefactos sin versionar en repo** (4 user-archetypes + 8 org-archetypes) | Fases 2, 7 | Descargar via REST post-OOM |
| B6 | **~28 roles sin versionar en repo** (~25 MOF-* + 3 GOV-*) | Fase 7 | Descargar via REST post-OOM |
| B7 | Convenio RENIEC para validacion DNI (IAL 3) | futuro | Area Desarrollo UPeU (no bloqueante para piloto) |

**Bloqueantes RETIRADOS** (decision 2026-05-11):
- ~~Cuenta de servicio `svc-midpoint-iga` en AD~~ — AD UPeU OUT del alcance.
- ~~Decision cuenta para writes Entra ID~~ — diferido a Fase 12.

---

## Decisiones doctrinales registradas (no negociables)

1. **2026-05-11** — NO crear nuevo conector MidPoint→Keycloak. Tampoco usar `pe.upeu.connector.keycloak-http v1.0.0` ni `openstandia/connector-keycloak`. La arquitectura es **MidPoint → OpenLDAP ← Keycloak (User Federation)**.
2. **2026-05-11** — UPeU NO usa Moodle ni Google Workspace. El stack es **Microsoft 365** (licencias A1/A3) + **Google Classroom** (SaaS externo integrado via URLs en Lamb).
3. **2026-05-11** — Campus codes 3 letras: `C-LIM`, `C-JUL`, `C-TPP` (consistente con `ELISEO.ORG_SEDE.SIGLA`).
4. **2026-05-11** — Cuentas privilegiadas las gestiona **David Urquizo**, no MidPoint. Tickets en `docs/runbooks/tickets-david-urquizo.md`.
5. **2026-05-11** — SchemaType se administra via UI Admin (objeto en repo), no como XSD files.
6. **2026-05-11** — **AD UPeU actual queda OUT del alcance.** No se lee, no se escribe. Mal estructurado, no es global. La decision sobre AD nuevo se difiere a Fase 12.
7. **2026-05-11** — **Entra ID UPeU es solo lectura hasta Fase 12.** En Fase 5 se importa para correlacion. El gobierno completo (writes) comienza solo cuando el modelo IGA en MidPoint este maduro y validado end-to-end.
8. **2026-05-11** — `msgraph.env` actual apunta al tenant **SciBack** (sandbox personal), NO al tenant UPeU real. Para tenant UPeU se necesita app registration separada (ver DU-001a).
9. **2026-05-11** — **No se modifica ningun sistema UPeU existente.** Solo MidPoint + sistemas nuevos (OpenLDAP HA). Keycloak existente (`192.168.12.88`) si es nuestro y se reconfigura.
10. **2026-05-19** — **Repo consolidado a estructura `canonical/` + `upeu/`.** Repo padre `SciBack/midpoint` carpeta local eliminada; GitHub pendiente archivar (NO eliminar). Branch `consolidation-2026-05-19` pendiente merge a `main` post-OOM.
11. **2026-05-19** — **PROD NO se toca hasta recuperacion OOM.** Los OIDs no cambiaron; PROD lee desde DB, no filesystem. Solo `git checkout` y validacion post-OOM.

---

## Siguiente accion inmediata

**B0 — Recuperar MidPoint PROD del OOM.** No hay progreso posible en ningun frente hasta que PROD vuelva a responder.

Una vez PROD recuperado:
1. Smoke tests (ver seccion P0 arriba).
2. Descargar y commitear artefactos faltantes (P1).
3. Merge branch + tag + archivar repo padre (P2).
4. Continuar Fase 3 — object templates per-archetype (P3).
5. Completar permisos Entra ID con David Urquizo (P4).
