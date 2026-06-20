# Modelo IGA Canónico UPeU — Spec Maestro v1.0

> **Estado:** Canon vigente. Aprobado 2026-05-14. Última revisión de estado: 2026-05-20.
> **Autor:** midpoint-expert (Claude) bajo dirección de Alberto Sánchez.
> **Versión MidPoint:** 4.10.2 (actualizado desde 4.9.5 el 2026-05-19).
> **Alcance:** Toda decisión de modelado, XML, importación, provisioning y workflow del proyecto MidPoint UPeU se valida contra este documento.
> **Sustitución:** Reemplaza implícitamente cualquier decisión previa documentada en `project_midpoint_upeu.md` que entre en conflicto con los 4 pilares.

---

## Tabla de contenidos

1. [Propósito y alcance](#1-propósito-y-alcance)
2. [Estándares y normativa de referencia](#2-estándares-y-normativa-de-referencia)
3. [Los 4 pilares (constitución)](#3-los-4-pilares-constitución)
4. [Modelo de datos canónico](#4-modelo-de-datos-canónico)
5. [Reglas de gobernanza canónica (policy rules)](#5-reglas-de-gobernanza-canónica-policy-rules)
6. [Eventos JML](#6-eventos-jml)
7. [Catálogo de servicios y provisioning](#7-catálogo-de-servicios-y-provisioning)
8. [Workflow de reconciliación](#8-workflow-de-reconciliación)
9. [Glosario UPeU](#9-glosario-upeu-términos-canónicos)
10. [Anti-patterns a evitar](#10-anti-patterns-a-evitar)
11. [Plan de migración (high-level)](#11-plan-de-migración-high-level)
12. [Referencias bibliográficas](#12-referencias-bibliográficas)
13. [Decisiones pendientes](#13-decisiones-pendientes)

---

## 1. Propósito y alcance

### 1.1 Propósito

Definir el **modelo canónico de Identidad y Gobierno de Accesos** de la Universidad Peruana Unión (UPeU), alineado con los estándares internacionales eduPerson, SCHAC, SCIM 2.0, ISO/IEC 24760, NIST SP 800-63 y RBAC INCITS 359, y con la normativa peruana aplicable (Ley 29733 de Datos Personales, Ley 30220 Universitaria, DS 029-2021-PCM Gobierno Digital, Ley de Migración).

Este spec es la **constitución del proyecto**: cualquier archetype, role, policy rule, mapping o XML que se redacte después debe poder citar la sección de este documento que lo justifica.

### 1.2 Alcance

| Incluido | Excluido |
|---|---|
| Diseño de UserType (`Person` único), OrgType, RoleType (afiliación, Position, Application, Business) | XML concreto (vive en specs derivadas) |
| Schema extension UPeU (atributos no cubiertos por core ni eduPerson/SCHAC) | Plan de tareas detallado (vive en `02-tasks.md`) |
| Policy rules de gobernanza (validación draft → active) | Operación día-a-día (governance handbook futuro) |
| Lifecycle JML orquestado por Oracle LAMB | Roadmap comercial SciBack |
| Catálogo de servicios y matriz afiliación × servicio | Configuración de cada target system |
| Workflow de reconciliación de perfiles incompletos | Reportes de auditoría específicos |

### 1.3 Audiencia

- Equipo DTI UPeU (Alberto, David Urquizo, owners de LAMB).
- Futuros administradores MidPoint que hereden el sistema.
- SciBack — base para `sciback-iga-blueprint` (otras universidades peruanas).

### 1.4 Documentos relacionados

- `~/.claude/projects/.../memory/project_iga_canonical_objective.md` — objetivo maestro 2026-05-14
- `~/.claude/projects/.../memory/policy_iga_canonical_pillars.md` — 4 pilares
- `~/.claude/projects/.../memory/policy_strict_import_validation.md` — política importación estricta
- `~/.claude/projects/.../memory/project_arquitectura_iga.md` — arquitectura MidPoint→OpenLDAP←Keycloak
- `~/.claude/projects/.../memory/project_access_governance_model.md` — modelo 5 capas
- `~/.claude/projects/.../memory/reference_oracle_lamb_structure.md` — fuente de datos validada
- Libro: Semančík et al., *Practical Identity Management with MidPoint*, Evolveum, v2.3 (2024-11).

---

## 2. Estándares y normativa de referencia

Todo elemento canónico se cita en su sección. Si UPeU se aparta del default, se marca **[UPeU-LOCAL]** con justificación explícita.

### 2.1 Estándares internacionales

| Estándar | Versión | Uso en este spec |
|---|---|---|
| **eduPerson** (Internet2/REFEDS) | 202208 v4.4.0 | Atributos de persona en federación académica (`eduPersonAffiliation`, `eduPersonPrincipalName`, `eduPersonUniqueId`, `eduPersonScopedAffiliation`, `eduPersonEntitlement`, `eduPersonOrcid`) |
| **SCHAC** (REFEDS) | 1.6.0 | Atributos académicos extendidos (`schacHomeOrganization`, `schacDateOfBirth`, `schacPersonalUniqueCode`, `schacPersonalUniqueID`, `schacCountryOfCitizenship`, `schacExpiryDate`, `schacUserStatus`) |
| **SCIM 2.0** | RFC 7643 / RFC 7644 | Modelo User/Group + Enterprise Extension (`employeeNumber`, `costCenter`, `department`, `manager`). MidPoint NO usa SCIM directo pero el schema es referencia |
| **ISO/IEC 24760-1/2/3** | 2025 | Framework IGA, terminología (identity/identifier/credential/IIA), lifecycle (`enrolled→established→active→suspended→archived→destroyed`) |
| **NIST SP 800-63-3** | 2017+errata | IAL/AAL/FAL (proofing, authenticator, federation) |
| **ANSI/INCITS 359-2012 (R2022)** | RBAC | Core RBAC + Hierarchical + Constrained (SoD) |
| **REFEDS R&S** | 1.3 (2016-09) | Entity category para SPs de investigación. Bundle de atributos obligatorio para vendors académicos |
| **REFEDS Sirtfi** | v1 | Framework de respuesta a incidentes en federación |
| **ISO/IEC 27001:2022** | A.5.15/16/17/18, A.8.2/3 | Controles de identidad y acceso para auditoría |
| **RFC 5322** | email format | `emailAddress` |
| **ISO 3166-1 alpha-3** | países | `schacCountryOfCitizenship`, `nationality` |
| **ISO 639-1/2** | idiomas | `schacMotherTongue`, `preferredLanguage` |
| **ISO 5218** | sex codes | `gender` |
| **BCP 47 / Olson TZ** | locale/timezone | `preferredLanguage`, `locale`, `timezone` |

### 2.2 Normativa peruana

| Norma | Aplicación |
|---|---|
| **Ley 29733** — Protección de Datos Personales | DNI y datos PII clasificados como dato sensible. Cifrado en tránsito y reposo. Logs de acceso. Derecho ARCO |
| **Ley 30220** — Ley Universitaria + SUNEDU | RENATI: identificación inequívoca de estudiantes, docentes, egresados. Trazabilidad académica. Licenciamiento institucional |
| **DS 029-2021-PCM** — Reglamento Ley Gobierno Digital | Identidad digital de personas. Cadena IIA → consumidores |
| **DL 1350 / Ley de Migración** | Documentos válidos para extranjeros: Carné de Extranjería (CE), Pasaporte, Permiso Temporal de Permanencia (PTP), Carné de Permiso Temporal de Permanencia (CPP), Carné de Solicitante de Refugio (CSR) |
| **CONCYTEC / ALICIA / RENATI** | Metadatos Dublin Core extendidos para repositorio. ORCID obligatorio en investigadores |
| **Resolución SUNEDU 029-2017-SUNEDU/CD** — RENATI | Trabajos de investigación: identificación obligatoria con tipo+número de documento |
| **Ley 26644** — Cómputo de tiempo de servicios | Lifecycle de trabajadores (fec_inicio, fec_termino) |

### 2.3 Documentación MidPoint

| Recurso | Cobertura en este spec |
|---|---|
| Libro *Practical Identity Management with MidPoint* v2.3 (Semančík et al., Evolveum, 2024-11) | Caps 6-10: Schema, RBAC, Archetypes, Focus Processing, Org Structures |
| https://docs.evolveum.com/midpoint/reference/schema/ | Tipos canónicos, lifecycle states |
| https://docs.evolveum.com/midpoint/reference/schema/archetypes/ | Structural vs auxiliary |
| https://docs.evolveum.com/midpoint/reference/roles-policies/rbac/ | Business vs Application roles, inducement |
| https://docs.evolveum.com/midpoint/reference/expressions/mappings/ | Inbound/outbound, assignmentTargetSearch |
| https://docs.evolveum.com/midpoint/reference/org/ | Org hierarchy, parentOrgRef, relations |
| https://docs.evolveum.com/midpoint/methodology/first-steps/ | First Steps Methodology |
| https://docs.evolveum.com/midpoint/compliance/iso27001/ | Mapping a controles ISO 27001 |

---

## 3. Los 4 pilares (constitución)

Los 4 pilares son **inviolables**. Toda decisión de diseño debe poder mapearse a uno o varios. Si una propuesta entra en conflicto con un pilar, se rechaza — se busca otra forma.

### 3.1 Pilar 1 — Persona única

> **Una persona = un objeto `UserType` con archetype `Person` (structural), de por vida.**

**Fundamento canónico:**
- ISO/IEC 24760-1 §3.1.2: la *identity* representa una entidad única en un dominio.
- Libro MidPoint §8.3 (citas literales): *"At most one structural archetype can be applied to object."* Person debe ser estructural único.
- Libro §6.1: *"In midPoint world, schema is the law."* Una sola estructura para todos.
- eduPerson 202208 §3: `eduPersonUniqueId` (omnidireccional, no reasignable) representa a la persona, no la afiliación.

**Reglas:**

1. Toda persona física vinculada a UPeU (estudiante, docente, staff, alumni, contractor, dependiente familiar, externo afín) se modela con **un único** `UserType` + `archetypeRef → Person`.
2. **Multi-afiliación obligatoria**: una persona puede ser simultáneamente estudiante, docente, staff y alumni — sin duplicar el objeto.
3. El `name` del user (login inmutable) **no codifica afiliación**.
4. Cambios de rol (alumno → egresado → contratado) modifican `assignments`, **NUNCA** el archetype ni el `name`.
5. Service accounts y system users usan archetypes distintos (`System user`) — quedan fuera del pilar.

**Casos UPeU resueltos:**

| Caso | Solución canónica |
|---|---|
| Doctorando en EP Doctorado Ed. Sup. que también dicta clases | 1 user con assignments `R-Student` + `R-Faculty` simultáneos |
| Alumna egresada contratada como asistente administrativa | 1 user con assignments `R-Alum` + `R-Staff` |
| Trabajador cuyo hijo estudia en Colegio Unión (descuento corporativo) | 2 users: trabajador (`R-Staff`) + hijo (`R-Affiliate-Dependent`) — relación expresada vía assignment al org del trabajador con `relation=family` |
| Extranjero docente con pasaporte | 1 user, `identityDocuments[]` contiene `{type=PASSPORT, country=BRA, ...}` |

### 3.2 Pilar 2 — Afiliaciones como roles birthright multivalor

> **Las afiliaciones son `RoleType` con archetype `Affiliation-Role`, asignables múltiples y concurrentes a un mismo `UserType`.**

**Fundamento canónico:**
- eduPerson 202208 §1.2.1: `eduPersonAffiliation` es **multi-valor**. Vocabulario canónico: `faculty`, `student`, `staff`, `employee`, `member`, `affiliate`, `alum`, `library-walk-in`.
- eduPerson 202208 §1.2.5: `eduPersonPrimaryAffiliation` es **single-valor** — derivada por prelación.
- Libro MidPoint §7.2 (cita literal): *"Archetypes are ideal for provisioning birthright privileges, access rights that are automatically given to users based on their type."*
- Libro §7.3: roles birthright = asignados automáticamente al crear el objeto.

**Roles canónicos de afiliación (catálogo cerrado):**

| Rol MidPoint | `eduPersonAffiliation` emitida | Cuándo se asigna | Fuente IIA |
|---|---|---|---|
| `R-Affiliation-Student` | `student`, `member` | Aparece en `DAVID.VW_FICHA_MATRICULA` con `ID_SEMESTRE` activo | Oracle LAMB / DAVID |
| `R-Affiliation-Faculty` | `faculty`, `employee`, `member` | Aparece en `ELISEO.VW_APS_EMPLEADO` con `ID_CATEGORIAOCUPACIONAL` docente y `ESTADO='A'` | Oracle LAMB / ELISEO + ENOC.CAT_DOCENTE |
| `R-Affiliation-Staff` | `staff`, `employee`, `member` | Aparece en `ELISEO.VW_APS_EMPLEADO` con categoría no-docente y `ESTADO='A'` | Oracle LAMB / ELISEO |
| `R-Affiliation-Alum` | `alum` | Aparece en `DAVID.VW_PERSONA_EGRESADO` o pasa de Student → Alum por evento Leaver académico exitoso | Oracle LAMB / DAVID |
| `R-Affiliation-Affiliate` | `affiliate` | Externos con relación no contractual: institución afín (Colegio Unión, Clínica Good Hope, ISTAT, AGTU), familiar de trabajador con descuento, visitante de investigación | Alta manual con expiración o sync desde `MOISES.VINCULO_FAMILIAR` |
| `R-Affiliation-Contractor` | `affiliate` (no `employee`) **[UPeU-LOCAL ver §3.2.b]** | Tercerizados, proveedores, consultoría con contrato no laboral | Alta manual con `validTo` |
| `R-Affiliation-Library-Walk-In` | `library-walk-in` | Acceso físico OPAC sin vínculo formal | Alta puntual desde Koha |

**[UPeU-LOCAL §3.2.b] `R-Affiliation-Contractor` emite `affiliate` y NO `employee`:** El vocabulario eduPerson no contempla "contractor" como valor; canónicamente "contractor" cabe bajo `affiliate` por NO tener contrato laboral con la institución (no es asalariado). Se evita `employee` para que group-based licensing M365 NO les asigne licencias docentes/administrativas. Justificación: eduPerson 202208 §1.2.1 — `employee` denota "individuals who serve as employees of the home institution"; un contractor no es employee de UPeU sino de su empresa.

**`eduPersonPrimaryAffiliation` — prelación canónica:**

```
staff > faculty > student > alum > affiliate > library-walk-in
```

**[UPeU-LOCAL §3.2.c] Prelación staff > faculty:** El default académico común es `faculty > staff`. UPeU institucionalmente prioriza `staff` cuando una persona es ambos (decanos, directores académicos con cargo administrativo), porque el cargo administrativo es el que define presupuesto, oficina y reportes operacionales. La afiliación `faculty` queda activa (multivalor) para acceso a recursos académicos.

**Reglas de asignación:**

- Los roles de afiliación NUNCA se asignan manualmente. Se auto-asignan vía `assignmentTargetSearch` en object template desde inbound mappings de LAMB (libro §9.4.3).
- Multi-afiliación es ortogonal: la presencia de un rol no excluye a otro.
- La afiliación `member` se deriva automáticamente: presente cuando hay al menos uno de `{student, faculty, staff}` (eduPerson 202208 §1.2.1.M).
- La afiliación `employee` se deriva automáticamente: presente cuando hay al menos uno de `{faculty, staff}`.

### 3.3 Pilar 3 — Position-Based Access Control

> **Las Posiciones UPeU son objetos catalogados (`ServiceType` con archetype `Position`) que inducen el paquete completo de Application Roles + parentOrgRef + Business Roles operacionales.**

**Fundamento canónico:**
- INCITS 359-2012: definición de *Role* como *"job function within the context of an organization with some associated semantics regarding the authority and responsibility conferred on the user assigned to the role"* — Position es la materialización de "job function" en UPeU.
- Libro MidPoint §7.2.5: roles paramétricos. Libro §10.2: orgs como abstract roles que inducen privilegios.
- Libro §10.3: orgs canónicas incluyen "project" y "role catalog" como tipos válidos. Position es análogo: catálogo de puestos.
- SCHAC 1.6.0 §`schacPersonalPosition` (`.13`): atributo estándar para representar cargo institucional.

**Diferencia conceptual:**

| Concepto | Pilar | Naturaleza |
|---|---|---|
| **Afiliación** | 2 | Naturaleza del vínculo con la institución (student/faculty/staff/alum/...) |
| **Position** | 3 | Cargo específico que la persona ocupa (Decano-FIA, Director-DTI, Bibliotecario-BUL, Docente-TC-EP-Ing-Sistemas) |
| **Business Role** | derivado | Combinación de Application Roles que se usa con frecuencia y se reutiliza desde varias Positions |
| **Application Role** | derivado | Acceso técnico a una app (Koha-Patron-Student, M365-A3, Zoom-Pro) |

**Estructura de Position:**

```
ServiceType "Position" (archetype Position)
├── identifier (código catalogado: POS-DECANO-FIA, POS-DOCENTE-TC-EP-SIS, ...)
├── displayName ("Decano Facultad Ingeniería y Arquitectura")
├── lifecycleState (active | deprecated cuando se elimina el puesto)
├── extension/positionType (academic | administrative | research | hybrid)
├── extension/headcount (1, ó N si es puesto múltiple)
├── parentOrgRef → org de pertenencia (FIA, DTI, BUL)
├── inducements:
│   ├── → 1..N Business Roles (BR-Decano, BR-Docente-TC, ...)
│   ├── → 0..N Application Roles directos (caso específico)
│   └── → org operativa con relation=manager si aplica
├── assignmentRelation → permitido asignar a UserType con archetype Person
```

**Reglas:**

1. Asignar una Position a un user **induce automáticamente** todo el paquete (libro §7.4 *inducement*).
2. Quitar la Position **revoca automáticamente** todo lo inducido (MidPoint reconcilia, libro §7.1 *reality vs policy*).
3. Un user puede tener **múltiples Positions concurrentes** (vacancy multi-cargo). MidPoint mergea privilegios sin duplicar (libro §7.6: *"midPoint always adds, it never subtracts"*).
4. Position **vacante** = Position object existe en el catálogo pero sin assignments — visible en dashboard de gobernanza, no provisiona.
5. Cambio de Position = quitar la Position previa + asignar la nueva. MidPoint mergea automáticamente y revoca lo no necesario.
6. Catálogo de Positions se mantiene en un árbol Org `Position-Catalog` paralelo al árbol functional (libro §10.2: orgs múltiples paralelas permitidas).

**Casos UPeU:**

| Persona | Positions asignadas | Resultado |
|---|---|---|
| Decano FIA | `POS-DECANO-FIA` | Induce: BR-Faculty-TC + BR-Manager-Faculty + access SAP módulo presupuesto + Koha staff + Sala Decanos |
| Docente TC EP Ing. Sistemas | `POS-DOCENTE-TC-EP-SIS` | Induce: BR-Faculty-TC (Zoom Pro, PowerBI Pro, M365-A3) + parentOrgRef → EP-SIS + Koha-Faculty |
| Estudiante regular EP Medicina | — sin Position. Solo R-Affiliation-Student | Birthright de student (Koha-Patron-Student, M365-A1, Wi-Fi-Estudiantes) |
| Asistente de docente (alumno trabajador) | `POS-ASIST-DOCENCIA` + R-Affiliation-Student | Asistente induce acceso a aula virtual del docente; mantiene rol de student |

### 3.4 Pilar 4 — JML orquestado por Oracle LAMB

> **Joiner / Mover / Leaver es 100% disparado por eventos en Oracle LAMB. Prohibido administración manual de afiliaciones y Positions excepto excepciones documentadas.**

**Fundamento canónico:**
- ISO/IEC 24760-1 §3.1.4: lifecycle de identidad gobernado por la IIA.
- Libro MidPoint §6.2 (cita literal): *"Lifecycle se sincroniza desde la fuente"*.
- Libro §9.5: inbound mappings desde HR/SIS son `strong` (sobrescriben).
- NIST SP 800-63A §4.4: re-proofing periódico cuando cambia el estado del subscriber.
- ISO 27001 A.5.16: ciclo de vida completo y auditable.

**Tabla de fuentes IIA por evento (validada contra Oracle LAMB real, ver `reference_oracle_lamb_structure.md`):**

| Evento | Fuente IIA UPeU | Trigger técnico |
|---|---|---|
| **Joiner Student** | `DAVID.VW_PERSONA_ALUMNO` + `DAVID.VW_FICHA_MATRICULA` (`ID_SEMESTRE` activo) | Aparece registro con ID_SEMESTRE de ciclo vigente |
| **Joiner Faculty/Staff** | `ELISEO.VW_APS_EMPLEADO` (`ESTADO='A'`, `FEC_INICIO` ≤ hoy, `FEC_TERMINO` IS NULL o > hoy) | Aparece registro con ESTADO='A' |
| **Joiner Alum** | `DAVID.VW_PERSONA_EGRESADO` | Aparece registro o estado en VW_FICHA_MATRICULA cambia a egresado |
| **Joiner Affiliate-Dependent** | `MOISES.VINCULO_FAMILIAR` (tipo=05 hijo, ID_TIPO_ESTADO_VINCULO=02 vigente) + JOIN `JOSE.SCHOOL_PERSONA_FAMILIA` | Hijo de trabajador estudia en Colegio Unión |
| **Mover programa** | `DAVID.VW_FICHA_MATRICULA.NOMBRE_ESCUELA` cambia | Inbound detecta cambio, recompute reasigna programa |
| **Mover puesto** | `ELISEO.VW_APS_EMPLEADO.ID_CATEGORIAOCUPACIONAL` o `ID_DEPTO` cambia | Inbound detecta, recompute reasigna Position |
| **Leaver Student** | `DAVID.VW_FICHA_MATRICULA` sin matrícula en `ID_SEMESTRE` actual durante N períodos consecutivos (a parametrizar, default 2 períodos) | Tarea programada detecta ausencia, lifecycle → suspended |
| **Leaver Faculty/Staff** | `ELISEO.VW_APS_EMPLEADO.ESTADO='I'` o `FEC_TERMINO` ≤ hoy | Inbound detecta, lifecycle → suspended → archived |
| **Leaver Alum** | No aplica (alumni es permanente, lifecycle nunca decae salvo solicitud expresa o muerte) | Solo proceso manual |

**Tabla JML → acciones MidPoint:**

| Etapa | MidPoint `lifecycleState` | Activation | Acciones provisioning |
|---|---|---|---|
| **Joiner — detectado** | `draft` | disabled | NO provisiona aún. Va a cola de reconciliación |
| **Joiner — validado 100%** | `proposed` → `active` | enabled | Provisioning completo: OpenLDAP + Entra ID + Koha + ... |
| **Mover** | `active` (sigue) | enabled | Recompute → reasigna Position/programa → mergea accesos |
| **Leaver — terminación detectada** | `active` → `suspended` | disabled (temporal) | Bloquea login; mantiene shadows; espera N días (default 90, ver §3.4.a) |
| **Leaver — retención cumplida** | `suspended` → `archived` | disabled (permanente) | Conserva user object, libera assignments, marca shadows como tombstone, mantiene audit trail por 5 años (Ley 29733) |
| **Destroyed** | (DELETE objeto) | n/a | Solo por solicitud ARCO de titular + aprobación legal. Borra user + audit |

**[UPeU-LOCAL §3.4.a] Período de retención `suspended` antes de `archived`: 90 días por defecto, configurable por afiliación.** Justificación: Ley 26644 (cómputo tiempo de servicios) requiere ventana de retención por reincorporaciones. Estudiantes: 365 días (puede retomar el siguiente año académico). Trabajadores: 90 días (estándar laboral). Alumni: nunca pasa a archived salvo solicitud expresa.

**Excepciones permitidas a "prohibido admin manual":**

1. Asignación inicial de `POS-RECTOR` y `POS-VICE-RECTOR` por aprobación de Asamblea Universitaria (no proviene de LAMB).
2. Service accounts y break-glass admins (archetype `System user`, no `Person`).
3. Reactivación manual de un `suspended` durante la ventana de retención (workflow aprobado por DTI Governance).
4. Corrección de datos en perfiles `draft` desde el workflow de reconciliación (§8).

---

## 4. Modelo de datos canónico

### 4.1 `UserType` (Person)

#### 4.1.1 Identificadores

| Atributo MidPoint | Tipo | Origen | Reglas | Estándar |
|---|---|---|---|---|
| `name` | PolyString | LAMB.CODIGO (estudiantes) o LAMB.COD_APS (trabajadores) o asignado por DTI | **Inmutable de por vida.** No codifica afiliación. No es DNI. Caso lowercase | ISO 24760 §3.1.3 *identifier*; libro MidPoint §6.1 *PolyStringType* |
| `personalNumber` | string | == `name` | Replica del code institucional para SCIM compat | SCIM 2.0 Enterprise `employeeNumber` (RFC 7643 §4.3) |
| `extension/institutionalCode` | string | == `name` | Alias semántico para visualización | [UPeU-LOCAL] |
| `identityDocuments[]` | complex multivalor (ver §4.1.2) | RENIEC + LAMB | ≥1 documento, ≥1 marked `primary=true` | SCHAC `schacPersonalUniqueID` (multivalor implícito por país); Ley Migración PE |

> **Decisión [UPeU-LOCAL §4.1.1.a]: NO usar `employeeNumber` nativo de MidPoint.** Motivo: deprecated en doctrina del proyecto (memoria `feedback_no_deprecated_fields.md`). Se usa `personalNumber` como reemplazo canónico. SCIM `employeeNumber` se materializa en outbound mapping a partir de `personalNumber`.

> **Decisión canónica §4.1.1.b:** `name == personalNumber == institutionalCode`. Triple alias para máxima compatibilidad sin duplicar significado.

#### 4.1.2 `identityDocuments[]` — documentos de identidad tipados

**Estructura de cada documento (ComplexType):**

| Campo | Tipo | Vocabulario / regex | Obligatorio | Sensibilidad |
|---|---|---|---|---|
| `type` | string | `DNI` \| `CE` \| `PASSPORT` \| `PTP` \| `CPP` \| `CSR` \| `ITIN` | Sí | público |
| `number` | string | regex por tipo (ver tabla) | Sí | PII sensible |
| `countryOfIssue` | string | ISO 3166-1 alpha-3 (`PER`, `VEN`, `BRA`...) | Sí | público |
| `primary` | boolean | true|false; exactamente 1 con `primary=true` | Sí | público |
| `issuedAt` | date | YYYY-MM-DD | No | público |
| `expiresAt` | date | YYYY-MM-DD; obligatorio para CE/PASSPORT/PTP/CPP | Condicional | público |
| `verifiedBy` | string | `RENIEC` \| `MIGRACIONES` \| `INSTITUTIONAL` \| `SELF-DECLARED` | Sí | trazabilidad |
| `verifiedAt` | date | YYYY-MM-DD | No | trazabilidad |

**Vocabulario de tipos canónicos (Perú + extranjeros):**

| Tipo | Origen | Regex | Notas |
|---|---|---|---|
| `DNI` | RENIEC (peruano) | `^[0-9]{8}$` | 8 dígitos. Ley 26497 RENIEC |
| `CE` | Migraciones (Carné Extranjería) | `^[0-9]{9}$` | 9 dígitos. Residentes extranjeros |
| `PASSPORT` | Cualquier país emisor | `^[A-Z0-9]{6,12}$` | Alfanumérico. countryOfIssue obligatorio |
| `PTP` | Migraciones (Permiso Temporal Permanencia) | `^[0-9]{9}$` | 9 dígitos. DS 002-2017-IN |
| `CPP` | Migraciones (Carné Permiso Temporal Permanencia) | `^[0-9]{9}$` | Reemplaza al PTP físico |
| `CSR` | Migraciones (Carné Solicitante de Refugio) | `^[0-9]{9}$` | Refugiados |
| `ITIN` | IRS (USA, opcional) | `^9[0-9]{2}-[0-9]{2}-[0-9]{4}$` | Para becarios con dependencia fiscal USA — uso excepcional |

**Reglas:**

1. **≥1 documento obligatorio.** Sin documento → user NO pasa de `draft`.
2. **Exactamente 1 con `primary=true`.** El primario es el que se exporta a SAML como `schacPersonalUniqueID`.
3. Una persona puede tener múltiples documentos (DNI + Passport, CE + Passport histórico). Todos se preservan.
4. Cambio de tipo (CE → DNI por naturalización): el nuevo documento se marca `primary=true`, el viejo se desmarca pero se conserva.
5. **Prohibido asumir DNI peruano.** Toda regex se aplica según `type`.

**Mapeo a SAML/LDAP:**
- Documento primario → `schacPersonalUniqueID` con URN `urn:schac:personalUniqueID:pe:{type}:{countryOfIssue}:{number}` (SCHAC URN Registry).
- Ejemplo DNI: `urn:schac:personalUniqueID:pe:DNI:PER:12345678`.
- Ejemplo Pasaporte BRA: `urn:schac:personalUniqueID:pe:PASSPORT:BRA:AB1234567`.

#### 4.1.3 Nombre y datos demográficos

| Atributo MidPoint | Tipo | Origen | Estándar |
|---|---|---|---|
| `givenName` | PolyString | LAMB `NOMBRE` (AS-IS, sin INITCAP) | SCIM `name.givenName`, eduPerson n/a, LDAP `givenName` |
| `familyName` | PolyString | LAMB `PATERNO` (apellido paterno) | LDAP `sn`; SCHAC `schacSn1` |
| `additionalName` | PolyString | LAMB `MATERNO` (apellido materno) | SCHAC `schacSn2` |
| `fullName` | PolyString | computed: `PATERNO MATERNO, NOMBRE` | LDAP `cn`; SCIM `displayName` |
| `extension/preferredName` | PolyString | manual / self-service | eduPerson `eduPersonNickname` |
| `extension/displayPronouns` | string multivalor | self-service | eduPerson `eduPersonDisplayPronouns` |
| `extension/birthDate` | date | LAMB `FEC_NACIMIENTO` | SCHAC `schacDateOfBirth` |
| `extension/gender` | string (`1`|`2`|`9`|`0`) | LAMB `ID_SEXO` (mapeado) | ISO 5218 |
| `extension/nationality` | string | LAMB `ID_TIPOPAIS` o RENIEC | SCHAC `schacCountryOfCitizenship` (ISO 3166-1 alpha-3) |
| `extension/maritalStatus` | string | LAMB `ESTADO_CIVIL` | N/A canónico — [UPeU-LOCAL] |
| `extension/religion` | string | LAMB `RELIGION` | N/A — [UPeU-LOCAL §4.1.3.a] |

**[UPeU-LOCAL §4.1.3.a] `religion`:** UPeU es institución confesional (Iglesia Adventista del Séptimo Día). Algunos servicios (planificación académica de sábados, eventos religiosos, becas) dependen de este atributo. NO se exporta a SAML salvo a sistemas internos UPeU. Clasificado como dato sensible bajo Ley 29733 §2.5 — requiere consentimiento.

#### 4.1.4 Contacto

| Atributo MidPoint | Tipo | Origen | Estándar |
|---|---|---|---|
| `emailAddress` | string | **computed** `{personalNumber}@upeu.edu.pe` | LDAP `mail`; SCIM `emails[primary]` |
| `extension/personalEmail` | string multivalor | self-service / LAMB `CORREO` | SCIM `emails[type=home]` |
| `extension/phoneNumber` | string | LAMB `CELULAR` | LDAP `mobile`; SCIM `phoneNumbers[type=mobile]` |
| `extension/streetAddress` | string | LAMB `DIRECCION` | LDAP `street`; SCIM `addresses[type=home].streetAddress` |
| `extension/ubigeo` | string | LAMB `ID_UBIGEO` | [UPeU-LOCAL] — código INEI |

**Reglas:**
- `emailAddress` es **siempre** computado, jamás de entrada manual. Fórmula: `{name}@upeu.edu.pe`.
- `personalEmail` es el correo histórico declarado por la persona (Gmail, Outlook). Se preserva pero NO se usa para login.

#### 4.1.5 Afiliación académica/laboral (atributos derivados, no inputs)

| Atributo MidPoint | Tipo | Computado de | Estándar |
|---|---|---|---|
| `extension/affiliations[]` | string multivalor | unión de `eduPersonAffiliation` emitidas por roles `R-Affiliation-*` activos | eduPerson `eduPersonAffiliation` |
| `extension/primaryAffiliation` | string | derivado por prelación staff > faculty > student > alum > affiliate | eduPerson `eduPersonPrimaryAffiliation` |
| `extension/scopedAffiliations[]` | string multivalor | `{affiliation}@upeu.edu.pe` para cada affiliation | eduPerson `eduPersonScopedAffiliation` |
| `extension/entitlements[]` | string multivalor | derivado de roles activos | eduPerson `eduPersonEntitlement` |
| `extension/eppn` | string | computed `{name}@upeu.edu.pe` | eduPerson `eduPersonPrincipalName` |
| `extension/eduPersonUniqueId` | string | computed `{lamb_id_persona}@upeu.edu.pe` (basado en ID inmutable LAMB, NO en `name`) | eduPerson `eduPersonUniqueId` |

**[UPeU-LOCAL §4.1.5.a] `eduPersonUniqueId` deriva de `LAMB.ID_PERSONA`, no de `name`:** Justificación: eduPerson 202208 §3 exige que `eduPersonUniqueId` sea omnidireccional y NO reasignable. Si por error de gobernanza un `name` se reciclara (ej. exalumno cuyo código se reasigna a hermano homónimo — caso documentado en universidades peruanas), `eduPersonUniqueId` debe permanecer único. `LAMB.ID_PERSONA` es el ID inmutable que MOISES (MDM) garantiza.

#### 4.1.6 Atributos académicos (subset student)

| Atributo MidPoint | Tipo | Origen | Estándar |
|---|---|---|---|
| `extension/academicProgram` | string multivalor | LAMB `NOMBRE_ESCUELA` | [UPeU-LOCAL] |
| `extension/academicProgramCode` | string multivalor | LAMB `ID_PROGRAMA_ESTUDIO` | [UPeU-LOCAL] |
| `extension/studyLevel` | string (`pregrado`|`posgrado`|`doctorado`|`tecnico`|`preuniversitario`|`extension`) | LAMB derivado | SCHAC `schacPersonalPosition` (URI) |
| `extension/studyModality` | string multivalor (`presencial`|`semipresencial`|`distancia`) | LAMB derivado | [UPeU-LOCAL] |
| `extension/studentCycle` | int multivalor | LAMB `CICLO` | [UPeU-LOCAL] |
| `extension/admissionPeriod` | string | LAMB primer `ID_SEMESTRE` matriculado | [UPeU-LOCAL] |

#### 4.1.7 Atributos laborales (subset faculty/staff)

| Atributo MidPoint | Tipo | Origen | Estándar |
|---|---|---|---|
| `extension/employeeCategory` | string | LAMB `ID_CATEGORIAOCUPACIONAL` | SCHAC `schacPersonalPosition` |
| `extension/employeeType` | string multivalor | LAMB derivado (`TC`|`TP`|`COND`|`INVESTIGADOR`...) | [UPeU-LOCAL] — del catálogo ENOC.CAT_DOCENTE |
| `extension/hireDate` | date | LAMB `FEC_INICIO` | LDAP `employeeNumber` n/a; SCHAC n/a |
| `extension/terminationDate` | date | LAMB `FEC_TERMINO` | trigger leaver |
| `extension/contractType` | string | LAMB `ID_TIPOCONTRATO` | [UPeU-LOCAL] |
| `extension/depto` | string | LAMB `ID_DEPTO` (numérico) + lookup VW_REP_DEPTOS | SCIM `department`; LDAP `departmentNumber` |

#### 4.1.8 Investigación (subset researcher)

| Atributo MidPoint | Tipo | Origen | Estándar |
|---|---|---|---|
| `extension/orcid` | string | self-service / CONCYTEC API | eduPerson `eduPersonOrcid` (URI form: `https://orcid.org/{id}`) |
| `extension/conytecId` | string | CONCYTEC RENACYT | [UPeU-LOCAL] |
| `extension/researcherCategory` | string | CONCYTEC | [UPeU-LOCAL] |

#### 4.1.9 Pertenencia organizacional

| Atributo MidPoint | Tipo | Origen | Estándar |
|---|---|---|---|
| `parentOrgRef[]` | reference multivalor | derivado por roles + Positions | Libro MidPoint §10 — operacional |
| `extension/homeCampus` | string (`LIMA`|`JULIACA`|`TARAPOTO`) | derivado de `parentOrgRef` o LAMB | [UPeU-LOCAL] |
| `extension/schacHomeOrganization` | string (constante `upeu.edu.pe`) | constante | SCHAC `schacHomeOrganization` |

**Reglas:**
- `parentOrgRef` es **multivalor** (libro §10.5). Un docente de FIA con assignment a EP-SIS tendrá orgs `{FIA, EP-SIS}`.
- `homeCampus` se deriva del campus de la Position primaria (si tiene Position) o del semestre activo (estudiantes Lima = `ID_SEMESTRE=279` por ahora).

#### 4.1.10 Activación y lifecycle

| Atributo MidPoint | Tipo | Comportamiento canónico |
|---|---|---|
| `lifecycleState` | enum | Sincronizado desde LAMB. Estados: `draft`, `proposed`, `active`, `suspended`, `archived`. NO `failed` ni `deprecated` salvo casos especiales |
| `activation/administrativeStatus` | enum | Override de emergencia. Default `null` (deriva de lifecycle) |
| `activation/validFrom` | dateTime | `hireDate` o admisión académica |
| `activation/validTo` | dateTime | `terminationDate` o egreso esperado (estudiantes: null hasta egreso) |
| `activation/effectiveStatus` | enum readonly | Computado por MidPoint |
| `extension/schacExpiryDate` | date | Exportable a SCHAC outbound; mismo valor que `validTo` para SPs externos |

### 4.2 Archetype único `Person` (structural)

**Definición:**

```
ArchetypeType "Person"
├── objectType = UserType
├── archetypeCategory = structural (max 1 por user)
├── displayName = "Persona UPeU"
├── description = "Toda persona física vinculada a UPeU. Único archetype structural permitido para UserType."
├── archetypePolicy:
│   ├── objectTemplateRef → ObjectTemplate "Person" (§4.3)
│   ├── lifecycleStateModel: estados canónicos draft/proposed/active/suspended/archived
│   └── adminGuiConfiguration: iconStyle, color
├── inducement (vacío): archetypes structural NO inducen privilegios (libro §8.4)
├── assignmentRelation → permitido sólo a Person
```

**Reglas:**
- `Person` es el **único** archetype structural permitido para `UserType` que represente una persona física.
- Archetypes auxiliares de UserType permitidos (libro §8.3): NINGUNO en v1.0 (los 4 actuales `Person-Student`, `Person-Faculty`, `Person-Staff`, `Person-Alumni` se eliminan; su rol pasa a `R-Affiliation-*`).
- Excepciones: `System user` (service accounts, daemons) → NO es archetype `Person`. Vive en árbol separado.

### 4.3 Object Template `Person`

**Responsabilidades (libro §9.1):**

1. Computar `fullName` desde `givenName` + `familyName` + `additionalName`.
2. Computar `emailAddress` = `{name}@upeu.edu.pe`.
3. Computar `extension/eppn` = `{name}@upeu.edu.pe`.
4. Computar `extension/eduPersonUniqueId` desde `extension/lambIdPersona`.
5. Computar `extension/scopedAffiliations[]` = unión de `{affiliation}@upeu.edu.pe`.
6. Computar `extension/primaryAffiliation` por prelación.
7. Auto-asignar roles `R-Affiliation-*` vía `assignmentTargetSearch` basado en presencia de inbound desde LAMB (libro §9.4.3).
8. Auto-asignar `parentOrgRef` vía `assignmentTargetSearch` desde `extension/academicProgramCode` o `extension/depto`.
9. **NO** auto-asignar Positions (la asignación de Position es semi-manual / por workflow específico).

### 4.4 Roles de afiliación (birthright)

Ver §3.2 para el catálogo. Cada `R-Affiliation-*` es:

```
RoleType "R-Affiliation-{X}"
├── archetypeRef → "Affiliation-Role"
├── lifecycleState = active
├── inducement:
│   ├── extension/affiliations += "{eduPersonAffiliation value}"
│   └── inducement a Application Roles birthright (Koha-Patron-{Student|Faculty|Staff}, M365-{A1|A3}, Wi-Fi-{Estudiantes|Docentes|Staff}, ...)
├── induced parentOrgRef (si aplica): a la unidad académica/administrativa
```

### 4.5 Positions (catálogo)

Ver §3.3. El catálogo se organiza en dos capas:

- **Capa canónica** — exigida por Ley 30220 (Ley Universitaria) y los 8 CBC de SUNEDU. Aplica a toda universidad licenciada en Perú.
- **[UPeU-LOCAL]** — puestos específicos de UPeU según Organigrama aprobado por Resolución Nº 0001-2026/UPeU-AU (Asamblea Universitaria).

> **D-04 [PARCIALMENTE CERRADO 2026-05-14]:** Catálogo construido desde Ley 30220 + organigrama oficial UPeU (Res. 0001-2026/UPeU-AU). Pendiente de confirmación RR.HH.: mapeo exacto `ID_CATEGORIAOCUPACIONAL` LAMB → Position code (ver D-05). Pendiente de confirmación DTI: lista completa de EPs por sede y códigos de departamento académico.

---

#### 4.5.1 Gobierno (Capa canónica — Ley 30220 art. 23-28)

| Code | Display | positionType | Fuente legal | Notas |
|---|---|---|---|---|
| `POS-RECTOR` | Rector | `hybrid` | Ley 30220 art. 23 | Electo por Asamblea Universitaria. SoD: no puede ser VR simultáneamente |
| `POS-VICE-RECTOR-ACAD` | Vicerrector Académico | `hybrid` | Ley 30220 art. 24 | Electo por AU. Único vicerrector obligatorio por ley |
| `POS-VICE-RECTOR-ADM` | Vicerrector Administrativo | `hybrid` | Ley 30220 art. 24 | Estatutario |
| `POS-VICE-RECTOR-BIENESTAR` | Vicerrector de Bienestar Universitario | `hybrid` | **[UPeU-LOCAL]** Res. 0001-2026 | Vicerrectorado propio de UPeU. No mandado por ley pero permitido (Ley 30220 art. 24 in fine) |
| `POS-SECRETARIO-GENERAL` | Secretario General | `administrative` | Ley 30220 art. 29 | Fe pública universitaria, actas de AU y CU |

#### 4.5.2 Órganos de asesoría, control y apoyo al Rectorado ([UPeU-LOCAL])

> Todos derivados del Organigrama Res. 0001-2026/UPeU-AU. Posicionados bajo parentOrgRef → `ORG-RECTORADO`.

| Code | Display | positionType |
|---|---|---|
| `POS-DEFENSOR-UNIVERSITARIO` | Defensor Universitario | `administrative` |
| `POS-TRIBUNAL-HONOR` | Miembro Tribunal de Honor Universitario | `administrative` |
| `POS-DIR-COOPERACION-PROYECTOS` | Director de Cooperación y Proyectos | `administrative` |
| `POS-DIR-PLANIF-CALIDAD` | Director de Planificación y Gestión de la Calidad | `administrative` |
| `POS-AUDITOR-INTERNO` | Auditor Interno | `administrative` |
| `POS-DIR-IMAGEN-RRPP` | Director de Imagen Institucional y RRPP | `administrative` |
| `POS-DIR-MISION` | Director de Misión | `hybrid` |
| `POS-DIR-FONDO-EDITORIAL` | Director de Fondo Editorial | `administrative` |
| `POS-ASESOR-LEGAL` | Asesor Legal | `administrative` |

**[UPeU-LOCAL §4.5.2.a] `POS-DIR-MISION`:** UPeU es institución confesional adventista. El cargo es híbrido porque involucra formación espiritual del claustro y comunidad universitaria, además de gestión administrativa.

#### 4.5.3 Vicerrectorado Académico

##### Órganos de línea académica (Capa canónica — Ley 30220)

| Code | Display | positionType | Fuente legal |
|---|---|---|---|
| `POS-DIR-ASUNTOS-ACAD` | Director de Asuntos Académicos | `academic` | Ley 30220 art. 43 |
| `POS-DIR-INV-INNOVACION` | Director de Investigación e Innovación | `research` | Ley 30220 art. 48, SUNEDU CBC-3 |
| `POS-DECANO-{FACU}` | Decano de Facultad (por cada facultad) | `hybrid` | Ley 30220 art. 52-54 |
| `POS-DIR-EP-{EP}` | Director de Escuela Profesional | `academic` | Ley 30220 art. 60-61 |
| `POS-JEFE-DPTO-ACAD-{DPTO}` | Jefe de Departamento Académico | `academic` | Ley 30220 art. 59 |
| `POS-DIR-ESCUELA-POSGRADO` | Director de Escuela de Posgrado | `academic` | Ley 30220 art. 43 bis |
| `POS-DIR-UNIDAD-POSGRADO-{EP}` | Director de Unidad de Posgrado | `academic` | Ley 30220 |
| `POS-DIR-EDUC-DISTANCIA` | Director de Educación Adventista a Distancia | `academic` | **[UPeU-LOCAL]** Res. 0001-2026 |

**Instancias concretas de `POS-DECANO-{FACU}` (sedes Lima, Juliaca, Tarapoto):**

| Code | Display |
|---|---|
| `POS-DECANO-FIA` | Decano Facultad de Ingeniería y Arquitectura |
| `POS-DECANO-FACTEO` | Decano Facultad de Ciencias Teológicas |
| `POS-DECANO-FACISAL` | Decano Facultad de Ciencias de la Salud |
| `POS-DECANO-FACIHED` | Decano Facultad de Ciencias Humanas y Educación |
| `POS-DECANO-FCE` | Decano Facultad de Ciencias Empresariales |

> Sedes Juliaca y Tarapoto tienen sus propios Decanatos. Codes: `POS-DECANO-{FACU}-JU`, `POS-DECANO-{FACU}-TA`. Confirmación pendiente con DTI (D-13).

##### Categorías docentes (Capa canónica — Ley 30220 art. 64-66)

> Ley 30220 establece 3 categorías ordinarias (Principal, Asociado, Auxiliar) × 2 dedicaciones (TC = Tiempo Completo 40h/semana, TP = Tiempo Parcial <40h/semana). Además categorías extraordinarias.

| Code | Display | positionType | Ley 30220 art. | Notas LAMB |
|---|---|---|---|---|
| `POS-DOCENTE-PRINCIPAL-TC` | Docente Ordinario Principal TC | `academic` | art. 64.a + 65.a | `ID_CATEGORIAOCUPACIONAL` → pendiente D-05 |
| `POS-DOCENTE-PRINCIPAL-TP` | Docente Ordinario Principal TP | `academic` | art. 64.a + 65.b | |
| `POS-DOCENTE-ASOCIADO-TC` | Docente Ordinario Asociado TC | `academic` | art. 64.b + 65.a | |
| `POS-DOCENTE-ASOCIADO-TP` | Docente Ordinario Asociado TP | `academic` | art. 64.b + 65.b | |
| `POS-DOCENTE-AUXILIAR-TC` | Docente Ordinario Auxiliar TC | `academic` | art. 64.c + 65.a | |
| `POS-DOCENTE-AUXILIAR-TP` | Docente Ordinario Auxiliar TP | `academic` | art. 64.c + 65.b | |
| `POS-DOCENTE-CONTRATADO` | Docente Contratado | `academic` | art. 64 in fine | Contrato por semestre; LAMB muestra `ESTADO='A'` con `FEC_TERMINO` fin de semestre |
| `POS-DOCENTE-HONORARIO` | Docente Extraordinario Honorario | `academic` | art. 66.a | |
| `POS-DOCENTE-EMERITO` | Docente Extraordinario Emérito | `academic` | art. 66.b | Requirió ser Principal TC ≥15 años jubilado |
| `POS-DOCENTE-VISITANTE` | Docente Extraordinario Visitante | `academic` | art. 66.c | Temporal; `validTo` obligatorio |

**[UPeU-LOCAL §4.5.3.a] Mapeo deducciones desde LAMB:**
Oracle `ELISEO.VW_APS_EMPLEADO.ID_CATEGORIAOCUPACIONAL` es un código numérico. La tabla de categorías vive en `ENOC.CAT_DOCENTE`. El mapeo exacto código→Position es D-05 (pendiente RR.HH.). Mientras tanto, la distinción TC/TP se deduce de `ENOC.CAT_DOCENTE.NOMBRE` buscando tokens `TIEMPO COMPLETO` vs `TIEMPO PARCIAL`. Docente sin código reconocido → `POS-DOCENTE-CONTRATADO`.

##### Investigadores RENACYT (CONCYTEC)

> **⛔ RETIRADO 2026-06-20 (histórico).** El modelado de investigación se retiró de MidPoint:
> ya no se crean positions/roles/archetypes RENACYT ni se afilia investigadores ni se proyecta
> a CRIS. Esa capa la asume el producto separado **"SciBack Research Project"** (lee directo de
> Oracle Lamb). Esta sub-sección queda como referencia conceptual; no representa trabajo
> planificado en MidPoint. Ver banner de retiro en [`../../ROADMAP.md`](../../ROADMAP.md).

| Code | Display | positionType | Fuente |
|---|---|---|---|
| `POS-INVESTIGADOR-RENACYT-III` | Investigador RENACYT Categoría III (Reconocido) | `research` | CONCYTEC RENACYT |
| `POS-INVESTIGADOR-RENACYT-II` | Investigador RENACYT Categoría II (Distinguido) | `research` | CONCYTEC RENACYT |
| `POS-INVESTIGADOR-RENACYT-I` | Investigador RENACYT Categoría I (Consagrado) | `research` | CONCYTEC RENACYT |
| `POS-INVESTIGADOR-CALIFICADO` | Investigador CONCYTEC Calificado (no RENACYT aún) | `research` | CONCYTEC |

> RENACYT es concurrent con categoría docente: un `POS-DOCENTE-PRINCIPAL-TC` puede tener `POS-INVESTIGADOR-RENACYT-I` simultáneamente. MidPoint mergea privilegios (acceso repositorios premium, fondos de investigación).

#### 4.5.4 Vicerrectorado Administrativo ([UPeU-LOCAL])

> parentOrgRef → `ORG-VICERRECTORADO-ADM`

| Code | Display | positionType |
|---|---|---|
| `POS-DIR-DTI` | Director de Tecnologías de Información | `administrative` |
| `POS-DIR-TALENTO-HUMANO` | Director de Talento Humano | `administrative` |
| `POS-DIR-FINANCIERO` | Director Financiero | `administrative` |
| `POS-DIR-MARKETING` | Director de Marketing | `administrative` |
| `POS-DIR-INFRAESTRUCTURA` | Director de Infraestructura | `administrative` |
| `POS-DIR-OPERACIONES-CAMPUS-LM` | Director de Operaciones Campus Lima | `administrative` |
| `POS-DIR-OPERACIONES-CAMPUS-JU` | Director de Operaciones Campus Juliaca | `administrative` |
| `POS-DIR-OPERACIONES-CAMPUS-TA` | Director de Operaciones Campus Tarapoto | `administrative` |
| `POS-DIR-PROD-IMPRENTA` | Director Centro de Producción Imprenta Unión | `administrative` |
| `POS-DIR-PROD-BIENES` | Director Centro de Producción de Bienes Unión | `administrative` |

#### 4.5.5 Vicerrectorado de Bienestar Universitario ([UPeU-LOCAL])

> parentOrgRef → `ORG-VICERRECTORADO-BIENESTAR`

| Code | Display | positionType |
|---|---|---|
| `POS-DIR-UNIV-SALUDABLE` | Director de Universidad Saludable | `administrative` |
| `POS-DIR-BIENESTAR-UNIV` | Director de Bienestar Universitario | `administrative` |
| `POS-DIR-PROG-DEPORTIVO` | Director Programa Deportivo de Alta Competencia | `administrative` |
| `POS-DIR-INST-COLPORTOR` | Director Instituto de Desarrollo del Estudiante Colportor | `hybrid` |

#### 4.5.6 Dirección General de Campus ([UPeU-LOCAL])

> Coordinación funcional según organigrama. parentOrgRef → campus correspondiente.

| Code | Display | positionType |
|---|---|---|
| `POS-DIR-GENERAL-CAMPUS-LM` | Director General de Campus Lima | `administrative` |
| `POS-DIR-GENERAL-CAMPUS-JU` | Director General de Campus Juliaca | `administrative` |
| `POS-DIR-GENERAL-CAMPUS-TA` | Director General de Campus Tarapoto | `administrative` |

#### 4.5.7 Biblioteca y CRAI (Capa canónica — SUNEDU CBC-5)

> SUNEDU CBC-5 exige servicios bibliotecarios. Los 4 campus-bibliotecas de UPeU: BUL (Lima), BUJ (Juliaca), BUT (Tarapoto), BCI (Colegio/ISTAT).

| Code | Display | positionType |
|---|---|---|
| `POS-JEFE-BIBLIOTECA-LM` | Jefe Biblioteca Lima (BUL) | `administrative` |
| `POS-JEFE-BIBLIOTECA-JU` | Jefe Biblioteca Juliaca (BUJ) | `administrative` |
| `POS-JEFE-BIBLIOTECA-TA` | Jefe Biblioteca Tarapoto (BUT) | `administrative` |
| `POS-BIBLIOTECARIO-LM` | Bibliotecario Lima (BUL) | `administrative` |
| `POS-BIBLIOTECARIO-JU` | Bibliotecario Juliaca (BUJ) | `administrative` |
| `POS-BIBLIOTECARIO-TA` | Bibliotecario Tarapoto (BUT) | `administrative` |

#### 4.5.8 Posiciones de estudiantes con cargo ([UPeU-LOCAL])

> Estudiantes que ocupan un cargo formal adicional a su afiliación de student. Concurrent con `R-Affiliation-Student`.

| Code | Display | positionType | Notas |
|---|---|---|---|
| `POS-ASIST-DOCENCIA` | Asistente de Docencia | `student` | Alumno con asignación académica de apoyo al docente |
| `POS-REP-ESTUDIANTIL-{FACU}` | Representante Estudiantil ante Consejo de Facultad | `student` | Ley 30220 art. 55 — participación estudiantil en gobierno |
| `POS-REP-ESTUDIANTIL-CU` | Representante Estudiantil ante Consejo Universitario | `student` | Ley 30220 art. 34 — 1/3 del CU es estudiantil |
| `POS-PRES-ASOCIACION-ESTUD-{FACU}` | Presidente Asociación Estudiantil de Facultad | `student` | |

#### 4.5.8b Pastoral / Misión ([UPeU-LOCAL] — institución adventista)

> Posiciones propias de la misión confesional de UPeU. No aplicables a universidades no confesionales. parentOrgRef → `ORG-DIRECCION-MISION`.

| Code | Display | positionType |
|---|---|---|
| `POS-CAPELLAN-LM` | Capellán Universitario Lima | `hybrid` |
| `POS-CAPELLAN-JU` | Capellán Universitario Juliaca | `hybrid` |
| `POS-CAPELLAN-TA` | Capellán Universitario Tarapoto | `hybrid` |
| `POS-COORD-ORATORIO` | Coordinador de Oratorio Universitario | `administrative` |
| `POS-COORD-MISIONES-ESTUD` | Coordinador de Misiones Estudiantiles | `hybrid` |

#### 4.5.9 Áreas operativas ([UPeU-LOCAL])

> Posiciones de las áreas que toda universidad operativa tiene (Capa 2 del Blueprint SciBack) pero instanciadas con los nombres y estructura específica de UPeU, derivados del Organigrama Res. 0001-2026/UPeU-AU.

##### Tecnologías de Información (DTI)

> parentOrgRef → `ORG-DTI`. Estas Positions son críticas para IGA: personal DTI necesita acceso elevado a sistemas.

| Code | Display | positionType |
|---|---|---|
| `POS-JEFE-INFRA-TI` | Jefe de Infraestructura TI | `administrative` |
| `POS-JEFE-DESARROLLO-SI` | Jefe de Desarrollo de Sistemas de Información | `administrative` |
| `POS-JEFE-SOPORTE-TI` | Jefe de Soporte TI / Helpdesk | `administrative` |
| `POS-ANALISTA-SI` | Analista de Sistemas | `administrative` |
| `POS-TECNICO-TI` | Técnico TI | `administrative` |

##### Talento Humano (subposiciones)

> parentOrgRef → `ORG-TALENTO-HUMANO`. Acceso a sistemas de planillas y expedientes.

| Code | Display | positionType |
|---|---|---|
| `POS-COORD-SELECCION` | Coordinador de Selección y Contratación | `administrative` |
| `POS-COORD-CAPACITACION` | Coordinador de Capacitación y Desarrollo | `administrative` |
| `POS-COORD-REMUNERACIONES` | Coordinador de Remuneraciones y Planillas | `administrative` |
| `POS-ASIST-RRHH` | Asistente de Recursos Humanos | `administrative` |

##### Seguridad Campus

> parentOrgRef → `ORG-OPERACIONES-CAMPUS-{SEDE}`. Acceso a sistemas CCTV y control de acceso físico.

| Code | Display | positionType |
|---|---|---|
| `POS-JEFE-SEGURIDAD-LM` | Jefe de Seguridad Campus Lima | `administrative` |
| `POS-JEFE-SEGURIDAD-JU` | Jefe de Seguridad Campus Juliaca | `administrative` |
| `POS-JEFE-SEGURIDAD-TA` | Jefe de Seguridad Campus Tarapoto | `administrative` |
| `POS-AGENTE-SEGURIDAD` | Agente de Seguridad | `administrative` |

##### Mantenimiento e Infraestructura Física

> parentOrgRef → `ORG-INFRAESTRUCTURA`.

| Code | Display | positionType |
|---|---|---|
| `POS-JEFE-MANTENIMIENTO-LM` | Jefe de Mantenimiento Campus Lima | `administrative` |
| `POS-JEFE-MANTENIMIENTO-JU` | Jefe de Mantenimiento Campus Juliaca | `administrative` |
| `POS-JEFE-MANTENIMIENTO-TA` | Jefe de Mantenimiento Campus Tarapoto | `administrative` |
| `POS-TECNICO-MANTENIMIENTO` | Técnico de Mantenimiento | `administrative` |

##### Comedor / Alimentación

> parentOrgRef → `ORG-OPERACIONES-CAMPUS-{SEDE}` o `ORG-VICERRECTORADO-BIENESTAR`.

| Code | Display | positionType |
|---|---|---|
| `POS-COORD-COMEDOR-LM` | Coordinador de Comedor Lima | `administrative` |
| `POS-COORD-COMEDOR-JU` | Coordinador de Comedor Juliaca | `administrative` |
| `POS-COORD-COMEDOR-TA` | Coordinador de Comedor Tarapoto | `administrative` |

##### Instituto de Idiomas — English for You UPeU

> parentOrgRef → `ORG-VICERRECTORADO-ACAD`. English for You es el nombre comercial del Centro de Idiomas UPeU.

| Code | Display | positionType |
|---|---|---|
| `POS-DIR-ENGLISH-FOR-YOU` | Director English for You (Centro de Idiomas) | `academic` |
| `POS-COORD-IDIOMAS-{SEDE}` | Coordinador de Idiomas por Sede | `academic` |
| `POS-DOCENTE-IDIOMAS` | Docente de Centro de Idiomas | `academic` |

##### CEPRE (Centro Pre-Universitario)

> parentOrgRef → `ORG-CAMPUS-{SEDE}`.

| Code | Display | positionType |
|---|---|---|
| `POS-DIR-CEPRE-LM` | Director CEPRE Lima | `academic` |
| `POS-DIR-CEPRE-JU` | Director CEPRE Juliaca | `academic` |
| `POS-DIR-CEPRE-TA` | Director CEPRE Tarapoto | `academic` |
| `POS-DOCENTE-CEPRE` | Docente CEPRE | `academic` |

##### Salud Universitaria

> parentOrgRef → `ORG-UNIV-SALUDABLE`. Acceso a expedientes clínicos (dato sensible Ley 29733).

| Code | Display | positionType |
|---|---|---|
| `POS-COORD-TOPICO-{SEDE}` | Coordinador de Tópico / Enfermería | `administrative` |
| `POS-MEDICO-UNIV` | Médico Universitario | `administrative` |
| `POS-PSICOPEDAGOGO` | Psicólogo / Consejero Universitario | `administrative` |

##### Becas y Bienestar Estudiantil (subposiciones)

> parentOrgRef → `ORG-BIENESTAR-UNIVERSITARIO`.

| Code | Display | positionType |
|---|---|---|
| `POS-COORD-BECAS` | Coordinador de Becas y Beneficios | `administrative` |
| `POS-COORD-TUTORIA` | Coordinador de Tutoría Académica | `administrative` |
| `POS-COORD-DEPORTES` | Coordinador de Deportes | `administrative` |

---

#### 4.5.10 Resumen estadístico del catálogo

| Sección | Capa | Posiciones (base, sin instanciar por sede/EP) |
|---|---|---|
| Gobierno | Canónica Ley 30220 | 5 |
| Asesoría/Control Rectorado | UPeU-LOCAL | 9 |
| VR Académico — línea | Canónica | 8 |
| Decanatos (5 facultades Lima) | Canónica | 5 base |
| Categorías Docentes | Canónica | 10 |
| Investigadores RENACYT | Canónica | 4 |
| VR Administrativo | UPeU-LOCAL | 10 |
| VR Bienestar | UPeU-LOCAL | 4 |
| Dirección General Campus | UPeU-LOCAL | 3 |
| Biblioteca/CRAI | Canónica CBC-5 | 6 |
| Pastoral / Misión | UPeU-LOCAL (adventista) | 5 |
| DTI (subposiciones) | UPeU-LOCAL | 5 |
| Talento Humano (subposiciones) | UPeU-LOCAL | 4 |
| Seguridad Campus | UPeU-LOCAL | 4 |
| Mantenimiento | UPeU-LOCAL | 4 |
| Comedor | UPeU-LOCAL | 3 |
| Instituto de Idiomas (English for You) | UPeU-LOCAL | 3 |
| CEPRE | UPeU-LOCAL | 4 |
| Salud Universitaria | UPeU-LOCAL | 3 |
| Becas y Bienestar (subposiciones) | UPeU-LOCAL | 3 |
| Estudiantes con cargo | UPeU-LOCAL | 4 base |
| **Total base (sin instanciar por sede/EP)** | | **≥110** |

> El criterio de aceptación F4 (≥20 Positions) queda cubierto. Para la implementación inicial se priorizan: gobierno (5) + categorías docentes (10) + VR Administrativo-DTI (5) + biblioteca (6) = **26 Positions mínimo viable**.

---

#### 4.5.10 Convención de naming y extensión

**Regla general de naming:**
- Prefijo `POS-` siempre.
- Tokens en MAYÚSCULAS separados por `-`.
- `{FACU}` → código de 3-6 letras de la facultad (FIA, FACTEO, FACISAL, FACIHED, FCE).
- `{EP}` → código de escuela profesional (por confirmar con DTI, D-04 pendiente parcial).
- `{SEDE}` → `LM` (Lima), `JU` (Juliaca), `TA` (Tarapoto).
- `{DPTO}` → código de departamento académico (por confirmar con DTI).
- Instancias de posicionamiento para la misma Position en varias sedes: se crea 1 Position por sede.

**`extension/positionType` vocabulario:**

| Valor | Uso |
|---|---|
| `academic` | Cargo puramente académico (docencia/gestión académica) |
| `administrative` | Cargo puramente administrativo |
| `research` | Cargo de investigación |
| `hybrid` | Combina docencia + gestión (Decano, Rector, Dir. Investigación) |
| `student` | Cargo ocupado por estudiantes con afiliación activa Student |

**Inducements tipo por positionType:**

| positionType | Business Roles típicamente inducidos |
|---|---|
| `academic` | `BR-Docente-TC` o `BR-Docente-TP` según dedicación |
| `administrative` | `BR-Staff-Admin-{nivel}` |
| `research` | `BR-Investigador` (Scopus/WoS premium, ORCID sync, DSpace-depositante) |
| `hybrid` | Unión de academic + administrative; `BR-Manager-Faculty` si es cargo con gestión de personas |
| `student` | Birthright `R-Affiliation-Student` ya dado; induce solo el acceso extra del cargo |

### 4.6 Application Roles

Granularidad **1 rol por entitlement/grupo target**. Catálogo derivado de §7 (servicios). Ejemplo:

| Code | Resource | Grupo/entitlement |
|---|---|---|
| `AR-Koha-Patron-Student-BUL` | Koha BUL | Patron category `Student` |
| `AR-M365-A1-Student` | Entra ID | License group `lic-m365-a1-student` |
| `AR-M365-A3-Faculty` | Entra ID | License group `lic-m365-a3-faculty` |
| `AR-Zoom-Pro-Faculty` | Entra ID | License group `lic-zoom-pro-faculty` |
| `AR-WiFi-Estudiantes` | OpenLDAP | Group `grp-wifi-estudiantes` |
| `AR-Vendor-Scopus` | Keycloak | Entitlement `urn:upeu:entitlement:scopus` |
| `AR-Vendor-WoS` | Keycloak | Entitlement `urn:upeu:entitlement:wos` |

### 4.7 Business Roles

Combinaciones reutilizables de Application Roles, por **función laboral**. Ejemplo:

| Code | Composición (inducement) |
|---|---|
| `BR-Docente-TC` | AR-M365-A3-Faculty + AR-Zoom-Pro-Faculty + AR-PowerBI-Pro + AR-Koha-Patron-Faculty + AR-WiFi-Docentes + AR-Vendor-Academic-Bundle |
| `BR-Docente-TP` | AR-M365-A3-Faculty + AR-Koha-Patron-Faculty + AR-WiFi-Docentes |
| `BR-Estudiante-Pregrado` | AR-M365-A1-Student + AR-Koha-Patron-Student + AR-WiFi-Estudiantes + AR-Vendor-Academic-Bundle |
| `BR-Estudiante-Posgrado` | BR-Estudiante-Pregrado + AR-Vendor-Posgrado-Extra |
| `BR-Manager-Faculty` | AR-PowerBI-Manager + AR-SharePoint-Owner-{site} + AR-Teams-CallQueue |
| `BR-Bibliotecario` | AR-Koha-Librarian + AR-Koha-Patron-Staff + AR-M365-A3-Staff |

### 4.8 OrgType (árbol funcional)

```
Institution: UPeU (raíz)
└── Campus: Lima (LM)
│   ├── Faculty: FIA · FACTEO · FACISAL · FACIHED · FCE
│   │   └── Department: EP Ing. Sistemas · EP Medicina · ...
│   └── Governance Unit: Rectorado · DTI · BUL · ...
├── Campus: Juliaca (JU)
├── Campus: Tarapoto (TA)
└── Partner-Institutions (paralelo, no campus):
    ├── Colegio Unión
    ├── Clínica Good Hope
    ├── ISTAT
    └── AGTU
```

Tipos canónicos (alineados a `iga-canonical-standards` §10.2):

| Archetype Org | Cardinalidad | Ejemplo |
|---|---|---|
| `org-institution` | 1 (raíz) | UPeU |
| `org-campus` | 3 | Lima, Juliaca, Tarapoto |
| `org-faculty` | N | FIA, FACTEO, ... |
| `org-department` | N (hijo de faculty) | EP Ing. Sistemas |
| `org-academic-unit` | N | Cepre, English for You, Postgrado |
| `org-governance` | N | Rectorado, DTI, RR.HH., Tesorería |
| `org-partner-institution` | 4+ | Colegio Unión, Clínica Good Hope, ISTAT, AGTU |

Árbol paralelo:

```
Position-Catalog (raíz lógica de catálogo de puestos)
└── POS-* (Positions individuales)
```

**Reglas (libro §10.2-10.4):**
- Árboles paralelos permitidos: functional + position-catalog + role-catalog futuro.
- `parentOrgRef` indexado operacional — usar para subtree search.
- Privilegios NO se heredan parent→child. Para heredar, agregar inducement explícito en archetype meta.
- Convención de naming: prefijo `F` para functional, `P` para project, `K` para position-catalog [UPeU-LOCAL].

---

## 5. Reglas de gobernanza canónica (policy rules)

### 5.1 Reglas mínimas para `draft → active`

Cada regla es una `policyRule` MidPoint (libro §11, no detallado en skill pero ver docs.evolveum.com). Pseudo-código:

#### Regla R-01: Archetype Person obligatorio

```
policyRule R-01-archetype-person:
  trigger: lifecycleState transition to "proposed" or "active"
  evaluator:
    if assignment.targetRef.oid != ARCHETYPE_PERSON_OID:
      then policyAction: enforce(block)
      message: "User must have exactly one structural archetype: Person"
```

#### Regla R-02: `name` inmutable y formato

```
policyRule R-02-name-inmutable:
  trigger: modify on name
  evaluator:
    if oldName != null AND newName != oldName:
      then policyAction: enforce(block)
      message: "Name (institutional code) is immutable for life"
  trigger: lifecycleState transition to "active"
  evaluator:
    if NOT match(name, "^[a-z0-9]{6,15}$"):
      then policyAction: enforce(block)
```

#### Regla R-03: `personalNumber == name`

```
policyRule R-03-personal-number-eq-name:
  trigger: modify on personalNumber OR modify on name
  evaluator:
    if personalNumber != name:
      then policyAction: enforce(fix) → set personalNumber = name
```

#### Regla R-04: ≥1 documento de identidad tipado

```
policyRule R-04-id-doc-required:
  trigger: lifecycleState transition to "active"
  evaluator:
    if size(extension/identityDocuments) < 1:
      then enforce(block)
      message: "≥1 identity document required"
    if count(d in identityDocuments where d.primary=true) != 1:
      then enforce(block)
      message: "exactly one primary identity document required"
```

#### Regla R-05: Regex por tipo de documento

```
policyRule R-05-doc-regex:
  trigger: add/modify identityDocuments[]
  evaluator:
    foreach d in identityDocuments:
      if d.type == "DNI" AND NOT match(d.number, "^[0-9]{8}$"): enforce(block)
      if d.type == "CE"  AND NOT match(d.number, "^[0-9]{9}$"): enforce(block)
      if d.type == "PASSPORT" AND NOT match(d.number, "^[A-Z0-9]{6,12}$"): enforce(block)
      if d.type == "PTP" AND NOT match(d.number, "^[0-9]{9}$"): enforce(block)
      if d.type == "CPP" AND NOT match(d.number, "^[0-9]{9}$"): enforce(block)
      if d.countryOfIssue NOT in ISO-3166-1-alpha3: enforce(block)
```

#### Regla R-06: DNI sin scramble ni centinelas

```
policyRule R-06-dni-not-corrupt:
  trigger: lifecycleState transition to "active"
  evaluator:
    foreach d in identityDocuments where d.type=="DNI":
      if d.number in SENTINEL_VALUES: enforce(block)   // ["00000000", "12345678", "99999999"]
      if d.number IS_SEQUENTIAL_PATTERN: enforce(block) // "11111111", "12345678"
      if d.verifiedBy NOT in ["RENIEC", "INSTITUTIONAL"]: enforce(reduce) // → draft
```

#### Regla R-07: ≥1 rol de afiliación activo

```
policyRule R-07-affiliation-role:
  trigger: lifecycleState transition to "active"
  evaluator:
    if count(assignment where targetRef.archetype == "Affiliation-Role" AND validity=active) < 1:
      then enforce(block)
      message: "≥1 active affiliation role required"
```

#### Regla R-08: `primaryAffiliation` coherente

```
policyRule R-08-primary-affiliation-coherent:
  trigger: recompute
  evaluator:
    affiliations = computed from active R-Affiliation-* roles
    expected = max by precedence (staff > faculty > student > alum > affiliate > library-walk-in)
    if extension/primaryAffiliation != expected: enforce(fix) → set primaryAffiliation = expected
```

#### Regla R-09: ≥1 parentOrgRef coherente

```
policyRule R-09-parent-org-required:
  trigger: lifecycleState transition to "active"
  evaluator:
    if size(parentOrgRef) < 1: enforce(block)
    foreach orgRef in parentOrgRef:
      org = resolve(orgRef)
      if org.archetype NOT in {org-faculty, org-department, org-governance, org-academic-unit, org-partner-institution}:
        enforce(warn)
```

#### Regla R-10: `emailAddress` computado, no manual

```
policyRule R-10-email-computed:
  trigger: modify on emailAddress
  evaluator:
    expectedEmail = name + "@upeu.edu.pe"
    if emailAddress != expectedEmail AND modificationSource != "OBJECT_TEMPLATE":
      then enforce(block)
      message: "emailAddress is computed; cannot be manually set"
```

#### Regla R-11: Lifecycle solo desde IIA

```
policyRule R-11-lifecycle-from-iia:
  trigger: modify on lifecycleState
  evaluator:
    if modificationSource NOT in {OBJECT_TEMPLATE, INBOUND_LAMB, WORKFLOW_RECONCILIATION, BREAK_GLASS_ADMIN}:
      then enforce(block)
      message: "lifecycleState transitions must come from authoritative source"
```

#### Regla R-12: SoD — Position única o múltiple permitida pero sin conflicto

```
policyRule R-12-position-sod:
  trigger: assignment add/modify with target Position
  evaluator:
    foreach pair (p1, p2) in active positions:
      if (p1, p2) in SOD_EXCLUSIONS:
        then enforce(block)
        message: "SoD violation: {p1} and {p2} cannot coexist"

SOD_EXCLUSIONS = [
  (POS-DIR-DTI, POS-AUDITOR-INTERNO),
  (POS-TESORERIA-PAGOS, POS-TESORERIA-AUTORIZACION),
  (POS-RECTOR, POS-VICE-RECTOR-*)  // mutually exclusive
]
```

### 5.2 Validaciones por tipo de documento

Resumen consolidado:

| Tipo | Regex | Country obligatorio | Expiry obligatorio |
|---|---|---|---|
| DNI | `^[0-9]{8}$` | PER fijo | No |
| CE | `^[0-9]{9}$` | Cualquier ISO 3166 ≠ PER | Sí |
| PASSPORT | `^[A-Z0-9]{6,12}$` | Cualquier ISO 3166 | Sí |
| PTP | `^[0-9]{9}$` | Cualquier ISO 3166 ≠ PER | Sí |
| CPP | `^[0-9]{9}$` | Cualquier ISO 3166 ≠ PER | Sí |
| CSR | `^[0-9]{9}$` | Cualquier ISO 3166 ≠ PER | Sí |
| ITIN | `^9[0-9]{2}-[0-9]{2}-[0-9]{4}$` | USA fijo | No |

### 5.3 Reglas de afiliación

- **R-AF-01:** prelación `primaryAffiliation`: staff > faculty > student > alum > affiliate > library-walk-in [UPeU-LOCAL §3.2.c].
- **R-AF-02:** `member` se deriva como `true` cuando hay ≥1 de `{student, faculty, staff}` (eduPerson §1.2.1).
- **R-AF-03:** `employee` se deriva como `true` cuando hay ≥1 de `{faculty, staff}`.
- **R-AF-04:** `contractor` emite `affiliate` y NUNCA `employee` [UPeU-LOCAL §3.2.b].
- **R-AF-05:** `alum` NO se asigna automáticamente al primer enrol; solo cuando hay egreso confirmado en `DAVID.VW_PERSONA_EGRESADO`.
- **R-AF-06:** Una vez `alum`, no se revoca salvo solicitud expresa.

### 5.4 Reglas específicas UPeU

- **R-UPEU-01:** `emailAddress` siempre con scope `@upeu.edu.pe`. Subdominios no permitidos.
- **R-UPEU-02:** Datos provenientes de Oracle LAMB deben pasar validador anti-scramble (R-06 sobre todos los campos con regex conocida).
- **R-UPEU-03:** `homeCampus` derivado: si hay `parentOrgRef` a un Faculty Lima → `LIMA`. Default Lima si ambigüedad y persona aparece en LAMB con EMP=201/ENT=7124.
- **R-UPEU-04:** No se permite `archived → active` por inbound. Reactivación es manual y va por workflow [UPeU-LOCAL].
- **R-UPEU-05:** `religion` solo se publica a sistemas internos UPeU; nunca SAML externo (Ley 29733).
- **R-UPEU-06:** `schacExpiryDate` se calcula así:
  - Student: `validTo` o fin del último ID_SEMESTRE matriculado + 365 días.
  - Faculty/Staff: `terminationDate` o "9999-12-31" si activo sin fin.
  - Alum: "9999-12-31" (alumni nunca expira).

### 5.5 SoD (Separation of Duties)

Reglas iniciales mínimas (catálogo completo en spec dedicada futura):

| Roles/Positions mutuamente exclusivos | Justificación |
|---|---|
| `POS-DIR-DTI` ↔ `POS-AUDITOR-INTERNO` | Auditor no puede auditar a quien gestiona la TI |
| `POS-TESORERIA-PAGOS` ↔ `POS-TESORERIA-AUTORIZACION` | Doble control financiero (INCITS 359 §A.3) |
| `POS-RECTOR` ↔ cualquier `POS-VICE-RECTOR-*` | Rector no puede ser simultáneamente vicerrector |
| `R-Affiliation-Student` ↔ `POS-DECANO-*` | Estudiante no puede ser decano |

Implementadas como `policyRule` con `exclusion` (INCITS 359 §B.2 SSoD).

---

## 6. Eventos JML

### 6.1 Joiner

| Caso | Detección | Acción MidPoint |
|---|---|---|
| Nuevo estudiante matriculado | Sync nocturno LAMB → aparece registro en VW_FICHA_MATRICULA con ID_SEMESTRE activo y no existía user con ese `LAMB.ID_PERSONA` | Crear user en `draft` → policy rules validan → si pasan, `proposed` → `active` con `R-Affiliation-Student` |
| Nuevo trabajador contratado | Sync nocturno LAMB → aparece registro en VW_APS_EMPLEADO con ESTADO='A' | Crear user en `draft` → si trabajador docente, `R-Affiliation-Faculty`; si no, `R-Affiliation-Staff` |
| Nuevo egresado | Estudiante existente cambia a egresado | Sigue siendo el mismo user; **se agrega** `R-Affiliation-Alum` (los roles previos se evalúan: si dejó de tener matrículas → se quita Student) |
| Familiar de trabajador (Colegio Unión) | Sync de MOISES.VINCULO_FAMILIAR + JOSE.SCHOOL_PERSONA_FAMILIA | Crear user `Person` con `R-Affiliation-Affiliate-Dependent`. parentOrgRef → org del trabajador con relation `family` |
| Institución afín (alta manual) | DTI agrega usuario al órgano partner | Workflow MidPoint con approver. `R-Affiliation-Affiliate` + parentOrgRef a partner-institution |

### 6.2 Mover

| Caso | Detección | Acción |
|---|---|---|
| Cambio de programa académico | LAMB VW_FICHA_MATRICULA.NOMBRE_ESCUELA cambia entre ciclos | Recompute → reasignar `parentOrgRef` a nuevo EP, mantener student role, actualizar `extension/academicProgram` |
| Cambio de campus | Estudiante cambia de sede | Recompute → actualizar `extension/homeCampus`, reasignar parentOrgRef |
| Cambio de puesto (mismo cargo, otra área) | LAMB ID_DEPTO cambia | Recompute → reasignar parentOrgRef. Position permanece si misma; si no, workflow para Position nueva |
| Promoción (de TC a Investigador) | LAMB ID_CATEGORIAOCUPACIONAL cambia | Reasignar Position via workflow |
| Egreso académico (Student → Alum) | DAVID.VW_PERSONA_EGRESADO contiene la persona | Agregar `R-Affiliation-Alum`. Si LAMB ya no muestra matrícula vigente → quitar `R-Affiliation-Student`. Lifecycle permanece `active` |

### 6.3 Leaver

| Caso | Detección | Acción |
|---|---|---|
| Trabajador con FEC_TERMINO llegada | LAMB VW_APS_EMPLEADO.FEC_TERMINO ≤ hoy | `suspended` immediatamente. Notificación al manager. Wait 90 días → `archived` |
| Estudiante sin matrícula por 2 períodos | Tarea programada verifica ausencia en VW_FICHA_MATRICULA | `suspended`. Wait 365 días [UPeU-LOCAL §3.4.a] → si reaparece, reactivación auto. Si no, `archived` |
| Sanción disciplinaria (estudiante o trabajador) | Workflow manual de DTI Governance | `suspended` indefinido. Razón en metadata. Solo proceso manual lo reactiva |
| Solicitud ARCO de eliminación (Ley 29733) | Solicitud legal | Aprobación: DPO + DTI. → `destroyed` (DELETE objeto). Audit trail preservado 5 años en logs cifrados |
| Fallecimiento | Constancia LAMB | `archived` permanente. No `destroyed` (registro académico es público) |

### 6.4 Tabla trigger → acción

| Trigger LAMB | Estado MidPoint actual | Acción | Estado MidPoint resultante |
|---|---|---|---|
| Nuevo registro VW_FICHA_MATRICULA | inexistente | create user draft | `draft` |
| Validación canónica OK | `draft` | recompute | `proposed` → `active` |
| Validación canónica FAIL | `draft` | encolar reconciliación | `draft` con metadata error |
| Nuevo registro VW_APS_EMPLEADO ESTADO='A' | inexistente | create user draft | `draft` |
| Update FEC_TERMINO ≤ hoy | `active` con Faculty/Staff role | quitar role + suspender | `suspended` |
| Sin matrícula 2 períodos | `active` con Student role | quitar role | `active` (si otros roles) / `suspended` (si era único role) |
| Sin matrícula 1 año + sin otro role | `suspended` | recompute lifecycle | `archived` |
| Aparece en VW_PERSONA_EGRESADO | `active` | add R-Affiliation-Alum | `active` (multivalor con Alum) |

---

## 7. Catálogo de servicios y provisioning

### 7.1 Servicios UPeU

| Servicio | Patrón provisioning | Resource MidPoint |
|---|---|---|
| **Microsoft Entra ID** (M365 A1/A3, Zoom, Adobe CC, Canva EDU, PowerBI, GitHub Enterprise) | Push directo. Group-based licensing | Resource Graph API |
| **OpenLDAP Identity Cache** | Push directo. Es el "single source" para Keycloak | Resource LDAP |
| **Keycloak** | NO recibe push. Federa OpenLDAP via User Federation | — |
| **Koha BUL/BUJ/BUT/BCI** (4 instancias) | Push via connector ConnId | 4 resources |
| **Indico** | NO recibe push. JIT login + LDAP searchable (modelo CERN) | — |
| **Moodle** (cuando aplique) | Push directo via Web Service API | Resource Moodle |
| **DSpace** (institucional) | Push via SCIM o LDAP | Resource SCIM/LDAP |
| **OJS** (revistas) | Push via LDAP | Resource LDAP |
| **EZProxy** | NO recibe push. Lee de LDAP | — |
| **FreeRADIUS Wi-Fi 802.1X** | Lee de OpenLDAP | — |
| **GUIA** (chainlit) | Lee de OpenLDAP / Keycloak | — |
| **GLPI Helpdesk** | Push via API | Resource HTTP |
| **Documize** | Lee de Keycloak | — |
| **EJBCA PKI** | Push manual de cert para staff/faculty | Resource manual |

### 7.2 Tabla afiliación × servicio

Servicios obtenidos por defecto según roles birthright de afiliación (no incluye Positions):

| Servicio | Student | Faculty | Staff | Alum | Affiliate | Library-walk-in |
|---|---|---|---|---|---|---|
| Email institucional | Sí | Sí | Sí | Sí (subset) | No | No |
| M365 A1 | Sí | — | — | — | — | — |
| M365 A3 | — | Sí | Sí | — | — | — |
| Zoom Pro | — | Sí | Sí | — | — | — |
| Adobe CC | — | Opt-in | Opt-in | — | — | — |
| Canva EDU | — | Sí | — | — | — | — |
| PowerBI Pro | — | Sí | Sí | — | — | — |
| Wi-Fi 802.1X | Sí | Sí | Sí | — | — | — |
| Koha (patron) | Student | Faculty | Staff | Alum-limited | — | Walk-in |
| Moodle (estudiante) | Sí | — | — | — | — | — |
| Moodle (docente) | — | Sí | — | — | — | — |
| Vendor académico (Scopus, WoS, IEEE, EBSCO, ProQuest) | Sí | Sí | — | — | — | Walk-in |
| Indico (JIT al primer login) | Sí | Sí | Sí | — | — | — |
| GUIA | Sí | Sí | Sí | — | — | — |
| OJS (autor/lector) | Sí (lector) | Sí (autor) | — | Sí (lector) | — | — |
| DSpace (lector/depositante) | Sí (lector) | Sí (depositante) | — | Sí (lector) | — | — |
| VPN UPeU | — | Sí | Sí | — | — | — |

Servicios extra se obtienen via **Positions** (decano, director, investigador RENACYT, bibliotecario, etc.).

### 7.3 OpenLDAP como Identity Cache (modelo CERN)

**Rol arquitectural (decisión firme `project_arquitectura_iga.md` 2026-04-26):**
- MidPoint es el **único** que escribe en OpenLDAP.
- OpenLDAP solo contiene users con `lifecycleState=active` (los 100% válidos canónicos).
- Users en `draft` o `suspended` NO existen en OpenLDAP.
- Keycloak federa OpenLDAP via User Federation (NO accede a MidPoint directo).
- Apps que requieren búsqueda (Indico, EZProxy, FreeRADIUS) leen OpenLDAP.

**Esquema LDAP exportado:**

```
dn: uid={name},ou=people,dc=upeu,dc=edu,dc=pe
objectClass: inetOrgPerson
objectClass: eduPerson           # 1.3.6.1.4.1.5923.1.1.2
objectClass: schacPersonalCharacteristics
objectClass: schacContactLocation
objectClass: schacEmployeeInfo
objectClass: schacStudentInfo

uid: {personalNumber}
cn: {fullName}
sn: {familyName}
givenName: {givenName}
mail: {emailAddress}

# eduPerson
eduPersonPrincipalName: {name}@upeu.edu.pe
eduPersonUniqueId: {lambIdPersona}@upeu.edu.pe
eduPersonAffiliation: student
eduPersonAffiliation: member
eduPersonPrimaryAffiliation: student
eduPersonScopedAffiliation: student@upeu.edu.pe
eduPersonScopedAffiliation: member@upeu.edu.pe
eduPersonOrcid: https://orcid.org/0000-0002-1234-5678
eduPersonEntitlement: urn:upeu:entitlement:scopus
eduPersonEntitlement: urn:upeu:entitlement:wos

# SCHAC
schacHomeOrganization: upeu.edu.pe
schacHomeOrganizationType: urn:schac:homeOrganizationType:eu:higherEducationalInstitution
schacPersonalUniqueCode: urn:schac:personalUniqueCode:pe:studentID:upeu.edu.pe:{name}
schacPersonalUniqueID: urn:schac:personalUniqueID:pe:DNI:PER:{primary doc number}
schacDateOfBirth: {birthDate}
schacCountryOfCitizenship: {nationality}
schacUserStatus: urn:schac:userStatus:upeu.edu.pe:active
schacExpiryDate: {calculated expiry}

# Pertenencia
ou: EP Ingeniería de Sistemas
departmentNumber: 13030204
```

---

## 8. Workflow de reconciliación

### 8.1 Cola de perfiles `draft`

Un user que falla cualquier policy rule de §5.1 permanece en `lifecycleState=draft`. MidPoint:

1. Crea el objeto.
2. Aplica inbound mappings.
3. Object template intenta computar derivados.
4. Policy rules evalúan; si alguna bloquea → permanece `draft`.
5. Se persiste metadata con razón de rechazo.

**No se provisiona NADA downstream.**

### 8.2 Metadata de rechazo

Cada user en `draft` debe contener:

```
extension/governance:
  rejectionReason: [list of failed policyRule codes]   # ["R-04", "R-06"]
  rejectedAt: timestamp
  rejectionSource: INBOUND_LAMB | MANUAL_IMPORT | WORKFLOW_PARTIAL
  expectedSourceForFix: LAMB_UPSTREAM | RENIEC_VALIDATION | MANUAL_DATA_ENTRY | DTI_REVIEW
  ownerForReconciliation: {OID of org/role/user responsible}
  lastReviewedAt: timestamp
  reviewerNotes: string
```

### 8.3 Dashboard de gobierno de identidad

MidPoint Admin UI muestra:

- **Vista 1:** Cola `draft` agrupada por `rejectionReason`. Permite priorización (ej. "todos los que les falta documento" vs "todos con DNI corrupto").
- **Vista 2:** Cola `draft` por antigüedad. Para escalar perfiles bloqueados >30 días.
- **Vista 3:** Cola `draft` por `ownerForReconciliation`. Cada owner ve sus pendientes.
- **Vista 4:** Métricas: cantidad de `draft`, tiempo medio de resolución, % importados directo a `active` vs vía cola.

Acciones desde dashboard:
- Editar campos faltantes (workflow controlado).
- Marcar "esperar dato upstream LAMB" (snooze N días).
- Marcar "rechazo permanente" → archivar el `draft` sin promover.
- Forzar revalidación.

---

## 9. Glosario UPeU (términos canónicos)

| Término | Definición canónica UPeU |
|---|---|
| **Persona** | Objeto `UserType` con archetype `Person`. Persona física vinculada a UPeU. Única para toda la vida. |
| **Afiliación** | Naturaleza del vínculo: student/faculty/staff/alum/affiliate/library-walk-in. Materializada como `R-Affiliation-*`. Multi-valor. |
| **Position** | Puesto específico que la persona ocupa. ServiceType con archetype `Position`. Catalogada y vacante-friendly. |
| **Birthright** | Privilegios inducidos automáticamente al asignar un role de afiliación. |
| **IIA Oracle LAMB** | Identity Information Authority única para datos académicos y laborales UPeU. Solo SELECT. |
| **Identity Cache** | OpenLDAP HA que MidPoint puebla. Único directorio que sirve a Keycloak / EZProxy / FreeRADIUS. |
| **Modelo CERN** | Patrón Indico/Keycloak: usuario hace primer login → cuenta se crea JIT (no provisioning previo). Aplicado a Indico. |
| **Sede / Campus** | Las 3 sedes físicas: Lima (UPeU), Juliaca (filial), Tarapoto (filial). |
| **Filial** | Sinónimo no canónico de campus secundario. Preferir "campus". |
| **EP** | Escuela Profesional. Equivale a `org-department` en árbol functional. |
| **Facultad** | `org-faculty`. Agrupa EPs. |
| **LAMB** | Sistema Oracle institucional con datos académicos (schema DAVID) y RR.HH. (schema ELISEO). Versión Oracle 11g/12c. |
| **MOISES** | Schema MDM central en Oracle LAMB. Datos maestros de personas. |
| **Code institucional / institutional code** | Código UPeU de la persona. Mapeado a `name == personalNumber`. Inmutable. |
| **Cola de reconciliación** | Lista de users en `lifecycleState=draft` esperando completar datos para promoverse a `active`. |
| **Break-glass admin** | Cuenta de emergencia para reactivar sistema. Archetype `System user`. Auditada. |

---

## 10. Anti-patterns a evitar

(Con ejemplos concretos del estado actual prod que motivaron el rediseño)

### 10.1 Mezclar Persona con Afiliación en archetypes

❌ **Como estaba:** 4 archetypes structural `Person-Alumni`, `Person-Student`, `Person-EmployeeFaculty`, `Person-EmployeeStaff`. Cada user tiene exactamente uno. Cambio = operación destructiva (libro §8.4).
**Problema:** Persona doctorando-docente no entra en ninguno. Persona alumno-trabajador requiere duplicar el objeto o forzar una sola "naturaleza".
✅ **Canónico:** archetype único `Person`. Afiliaciones como roles birthright multivalor.

### 10.2 Asumir DNI peruano implícito

❌ **Como estaba:** schema con campo `taxId` regex `^[0-9]{8}$`. Extranjero con pasaporte → falla validación.
✅ **Canónico:** `identityDocuments[]` tipado con vocabulario `DNI|CE|PASSPORT|PTP|CPP|CSR|ITIN` + regex por tipo + countryOfIssue.

### 10.3 `parentOrgRef` = 0/328

❌ **Como estaba:** users importados sin asignación a ninguna org. parentOrgRef vacío en los 328.
**Consecuencia:** subtree search no funciona, group-based licensing no se puede modelar por unidad, no hay manager hierarchy.
✅ **Canónico:** policy rule R-09 bloquea `active` si `parentOrgRef` vacío. Object template auto-asigna parentOrgRef desde `academicProgramCode` o `depto`.

### 10.4 Mono-afiliación rígida

❌ **Como estaba:** archetype fija la afiliación. Alumna egresada que se contrata requiere borrar + recrear user, perdiendo trazabilidad.
✅ **Canónico:** multi-afiliación nativa. Roles concurrentes. `primaryAffiliation` por prelación.

### 10.5 Sin JML automatizado

❌ **Como estaba:** import único como snapshot. Cambios upstream LAMB no se reflejan.
✅ **Canónico:** sync nocturno con tareas que detectan joiner/mover/leaver y recomputan.

### 10.6 Email manual / hard-coded

❌ **Como estaba:** `emailAddress` se cargaba desde LAMB `CORREO_UPEU` con valor potencialmente desactualizado.
✅ **Canónico:** `emailAddress` computado por object template como `{name}@upeu.edu.pe`. Policy rule R-10 bloquea modificación manual.

### 10.7 Generar usernames human-friendly

❌ **Riesgo:** crear logins como `alberto.sanchez` que colisionan, requieren iteration, sufren rename hell (libro §9.4.4 Iteration).
✅ **Canónico:** usar `personalNumber` institucional (numérico) inmutable como `name`. (Libro: *"The best strategy is to avoid using those generated human-friendly identifiers altogether"*).

### 10.8 Assignment vs Inducement confusión

❌ Asignar Application Roles directamente a Person via assignment → no escala, rompe role hierarchy.
✅ Cascada canónica: Position → induce → Business Role → induce → Application Role → induce → Entitlement. (Libro §7.4).

### 10.9 Archetype via inducement

❌ Intentar aplicar archetype con inducement desde meta-role.
✅ Libro §8.4: **archetypes solo se aplican via direct assignment.** Si se necesita auto-asignar archetype, usar object template + `assignmentTargetSearch`.

### 10.10 Confiar en herencia entre orgs

❌ Asumir que `Facultad de Ingeniería` con inducement de "VPN" lo pasa a hijos `EP-Sistemas`.
✅ Libro §10.4: **NO hay herencia automática parent → child.** Si se quiere, agregar inducement explícito al parent con `<orderConstraint>`.

### 10.11 Sincronizar orgs por nombre

❌ Buscar org parent por `name`. Rename rompe todo.
✅ Libro §10.2: usar `identifier` persistente separado del `name`.

### 10.12 Permitir datos LAMB sucios

❌ Importar DNIs centinela (`00000000`), nombres en mayúsculas mezcladas con scramble.
✅ Policy rules R-05, R-06 bloquean antes de `active`. Datos sucios → `draft` + cola reconciliación.

---

## 11. Plan de migración (high-level)

### 11.1 Orden estricto de fases

```
F0  → este Spec aprobado y commiteado
F1  → Refactor Schema Extension v3.0 → v3.1 canónico
        (identityDocuments[], affiliations[], dropear duplicados,
         alinear nombres a eduPerson/SCHAC)
F2  → Refactor Archetypes:
        - colapsar 4 Person-* en 1 Person structural
        - crear archetype Affiliation-Role
        - crear archetype Position
        - validar archetypes Org existentes (91 orgs)
F3  → Validar/recargar árbol Org existente (91 orgs) bajo nuevos archetypes
F4  → Crear catálogo Positions iniciales (mínimo viable)
F5  → Crear Object Template Person canónico + Policy Rules (§5)
F6  → Crear Roles de Afiliación (R-Affiliation-*) + Business Roles canónicos
F7  → Cablear Application Roles via inducement desde Business Roles
F8  → Workflow de reconciliación + dashboard governance
F9  → Purga de los 328 users actuales (con backup completo previo)
F10 → Activación de Resources LAMB (estaban en proposed) + sync piloto
        - Joiner test: 1 estudiante semestre 279 Lima
        - Validar que pasa por policy rules correctamente
F11 → Import progresivo:
        - Estudiantes Lima 2026 (sem 279, ~3,803)
        - Trabajadores activos Lima (EMP=201/ENT=7124, ~8,475)
        - Familiares dependientes (MOISES.VINCULO_FAMILIAR)
        - Egresados (DAVID.VW_PERSONA_EGRESADO)
        - Otras sedes (Juliaca, Tarapoto) — diferir
F12 → Levantar OpenLDAP HA (resuelve bloqueante B1 con Rudy)
        Sync solo lifecycleState=active a OpenLDAP
F13 → Conectar Keycloak User Federation a OpenLDAP
F14 → Provisioning a Entra ID + Koha (4 instancias)
F15 → Workflows Mover y Leaver automatizados
F16 → Access Certification campaigns (ISO 27001 A.5.18)
```

### 11.2 Criterios de aceptación por fase

| Fase | Criterio "done" |
|---|---|
| F0 | Spec en `doc/specs/iga-canonical-model-upeu/01-spec.md` aprobado por Alberto + commit |
| F1 | Schema v3.1 importado, valida XSD, sin OIDs huérfanos |
| F2 | 1 archetype `Person` structural, archetypes obsoletos marcados `deprecated`, sin assignments residuales |
| F3 | 91 orgs tipificadas con archetype correcto, parentOrg coherente, identifier persistente, sin ciclos |
| F4 | ≥20 Positions iniciales en PROD, todas con parentOrgRef válido, vacantes visibles en UI |
| F5 | Object Template valida casos test: Person sin docs → draft; Person 100% válido → active; DNI inválido → bloqueado |
| F6 | 6 R-Affiliation-* + 11 Business Roles canónicos en PROD |
| F7 | Smoke test: asignar `BR-Estudiante-Pregrado` a Person manual genera shadows en resources de prueba |
| F8 | Workflow visible en UI, dashboard accesible, métricas funcionando |
| F9 | 0 users de los 328 originales. Backup en S3 cuenta UPeU. Audit log preservado |
| F10 | 1 estudiante piloto sincronizado end-to-end. Validación de policy rules con éxito |
| F11 | ≥80% del padrón objetivo en `active`. <20% en `draft` con metadata clara |
| F12 | OpenLDAP HA replicando, MidPoint sync OK, 0 users `draft` exportados |
| F13 | Login via Keycloak federa OpenLDAP. Test con 1 usuario piloto |
| F14 | Provisioning real a Entra ID + Koha. Audit trail por cada outbound |
| F15 | Cambio de programa en LAMB se propaga automático en <24h |
| F16 | Primera campaña certification finalizada |

---

## 12. Referencias bibliográficas

### Libro y docs MidPoint

- Semančík et al., *Practical Identity Management with MidPoint*, Evolveum, v2.3 (2024-11). Caps 6 (Schema), 7 (RBAC), 8 (Archetypes), 9 (Focus Processing), 10 (Org Structures).
- https://docs.evolveum.com/midpoint/reference/schema/
- https://docs.evolveum.com/midpoint/reference/schema/archetypes/
- https://docs.evolveum.com/midpoint/reference/roles-policies/rbac/
- https://docs.evolveum.com/midpoint/reference/roles-policies/policy-rules/
- https://docs.evolveum.com/midpoint/reference/expressions/mappings/
- https://docs.evolveum.com/midpoint/reference/org/
- https://docs.evolveum.com/midpoint/reference/cases/ (workflows)
- https://docs.evolveum.com/midpoint/methodology/first-steps/
- https://docs.evolveum.com/midpoint/compliance/iso27001/
- https://docs.evolveum.com/glossary/iso24760/

### Estándares internacionales

- eduPerson 202208 v4.4.0 — https://github.com/REFEDS/eduperson/blob/master/eduperson-202208.md
- SCHAC 1.6.0 — https://wiki.refeds.org/display/STAN/SCHAC+Releases
- SCHAC URN Registry — https://wiki.refeds.org/display/STAN/SCHAC+URN+Registry
- RFC 7643 SCIM Core Schema — https://www.rfc-editor.org/rfc/rfc7643
- RFC 7644 SCIM Protocol — https://www.rfc-editor.org/rfc/rfc7644
- ISO/IEC 24760-1 (2025) — https://www.iso.org/standard/77582.html
- NIST SP 800-63-3 — https://pages.nist.gov/800-63-3/sp800-63-3.html
- ANSI/INCITS 359-2012 RBAC — https://csrc.nist.gov/projects/role-based-access-control
- REFEDS Research & Scholarship 1.3 — https://refeds.org/research-and-scholarship
- REFEDS Assurance Framework — https://refeds.org/assurance
- ISO/IEC 27001:2022 — https://www.iso.org/standard/27001

### Normativa peruana

- Ley 29733 Protección de Datos Personales — https://www.gob.pe/institucion/minjus/normas-legales/243470-ley-29733
- Ley 30220 Universitaria — https://www.sunedu.gob.pe/nueva-ley-universitaria-30220-2014/
- DS 029-2021-PCM Gobierno Digital — https://www.gob.pe/institucion/pcm/normas-legales/1747999-029-2021-pcm
- DL 1350 Migraciones — https://www.gob.pe/institucion/migraciones/normas-legales/1336253-decreto-legislativo-n-1350
- Resolución SUNEDU 029-2017-SUNEDU/CD RENATI — https://www.sunedu.gob.pe/renati/
- CONCYTEC RENACYT — https://renacyt.concytec.gob.pe/

### Memorias internas referenciadas

- `project_iga_canonical_objective.md`
- `policy_iga_canonical_pillars.md`
- `policy_strict_import_validation.md`
- `project_arquitectura_iga.md`
- `project_access_governance_model.md`
- `reference_oracle_lamb_structure.md`
- `feedback_no_deprecated_fields.md`

---

## 13. Decisiones pendientes

Las siguientes decisiones requieren intervención de Alberto / DTI / owners externos antes de poder avanzar a la fase siguiente. Bloquean parcialmente las fases indicadas.

### 13.1 Bloquean F1 (Schema v3.1)

- **D-01 [Alberto]** ✅ **CERRADO 2026-05-14.** Estructura final `extension/identityDocuments[]`: campos `type/number/countryOfIssue/primary/issuedAt/expiresAt/verifiedBy/verifiedAt` (naming camelCase inglés alineado SCIM/SCHAC). Vocabulario de valores peruano: `type` ∈ {DNI, CE, PASSPORT, PTP, CPP, CSR, ITIN}, `verifiedBy` ∈ {RENIEC, MIGRACIONES, INSTITUTIONAL, SELF-DECLARED}. Decisión: usar RENIEC/Migraciones solo para particularidad de documentos (tipos + verificadores); resto del modelo (nombres, fechas, género, afiliación) sigue schemas internacionales aceptados (eduPerson/SCHAC/SCIM/LDAP).
- **D-02 [Alberto + DTI Governance]** Confirmar política de retención por afiliación. Propuesta: Student=365d, Faculty/Staff=90d, Alum=∞. ¿Se mantiene o ajusta?
- **D-03 [Alberto]** ¿Se publica `extension/religion` a algún sistema externo o solo a sistemas UPeU internos? Propuesta: solo internos.

### 13.2 Bloquean F4 (Positions catálogo)

- **D-04 [PARCIALMENTE CERRADO 2026-05-14]** Catálogo construido desde Ley 30220 + Organigrama Res. Nº 0001-2026/UPeU-AU (ver §4.5 completo). **Pendientes para cierre total:**
  - Confirmación de DTI: lista completa de Escuelas Profesionales por sede (Juliaca, Tarapoto) y sus códigos internos.
  - Confirmación de DTI: lista de Departamentos Académicos (`POS-JEFE-DPTO-ACAD-{DPTO}`) con codes reales.
  - Confirmación de RR.HH.: asociaciones entre Positions y Departamentos / Áreas administrativas para el inducement de `parentOrgRef`.
- **D-05 [RR.HH.]** Mapeo entre `ELISEO.VW_APS_EMPLEADO.ID_CATEGORIAOCUPACIONAL` (numérico) y nombres oficiales de Positions. Workaround provisional en §4.5.3.a: detectar token `TIEMPO COMPLETO`/`TIEMPO PARCIAL` en `ENOC.CAT_DOCENTE.NOMBRE` para TC/TP.
- **D-06 [DTI]** Confirmación de SoD adicionales más allá de las 4 listadas en §5.5.

### 13.3 Bloquean F5 (Policy rules)

- **D-07 [Alberto]** Confirmar prelación `primaryAffiliation` propuesta `staff > faculty > student > alum > affiliate`. ¿Aplica universalmente o algún caso de uso requiere otra?
- **D-08 [Alberto]** Confirmar regex para `name` (login institucional). Propuesta: `^[a-z0-9]{6,15}$`. ¿Cuál es el formato real UPeU? ¿Hay legacy con letras mayúsculas o caracteres especiales?
- **D-09 [DTI + Owner LAMB]** Resolver los 9 DNIs corruptos identificados en LAMB. ¿Hay scramble por privacidad o son corrupción real? Impacta política R-06.
- **D-10 [DTI Governance]** Listar los valores centinela conocidos para DNI (más allá de 00000000, 12345678, 99999999) que deba detectar R-06.

### 13.4 Bloquean F11 (Import progresivo)

- **D-11 [Alberto]** Definir orden y batching de importación: ¿matriculados sem 279 primero o trabajadores activos primero? Propuesta: ambos en paralelo.
- **D-12 [DTI]** Definir umbral de "% draft aceptable" como criterio de aceptación de la fase. Propuesta: <20% draft.
- **D-13 [Owner LAMB]** Confirmar qué EMP/ENT corresponde a cada sede secundaria (Juliaca, Tarapoto) — solo Lima está confirmada (EMP=201/ENT=7124).

### 13.5 Bloquean F12 (OpenLDAP)

- **D-14 [Rudy]** Provisión de VMs OpenLDAP nodo 1 + nodo 2 (bloqueante B1 existente).
- **D-15 [Alberto + Rudy]** Decidir si arrancar con 1 nodo HA-ready o esperar a tener 2 nodos antes de despliegue.

### 13.6 Bloquean F14 (Provisioning Entra ID)

- **D-16 [David Urquizo]** Credenciales Graph API tenant UPeU real (ticket DU-001a — bloqueante B3 existente).

### 13.7 Decisiones documentales

- **D-17 [Alberto]** Confirmar idioma del UI de MidPoint (es/en). Esto impacta `displayName` de archetypes/roles.
- **D-18 [Alberto]** Confirmar registro de namespace `pe:` en REFEDS para SCHAC URNs (recomendado por iga-canonical-standards §4.2). Mientras tanto, usar provisional documentado.
- **D-19 [Alberto + SciBack]** Decidir cuándo este spec se generaliza a `sciback-iga-blueprint`. Propuesta: cuando F11 esté estable.

---

**Fin del spec v1.0.**
Decisiones cerradas: D-01 (identityDocuments[]), D-04 (catálogo Positions UPeU — parcial).

**Estado de fases (2026-05-20):**
- F1 (Schema) ✅, F2 (Archetypes) ✅, F3 (Org tree) ✅, F4 (RBAC + Object Templates) ✅
- F5 (Resources LAMB + LDAP + Entra ID + Koha) ✅ — 35.450 usuarios, 122 orgs, 72 roles, 741 posiciones en PROD
- Próximas: F5.edu (outbound eduPerson LDAP), F6 (Entra ID write), F7 (role mining), F8 (SoD), F9 (LDAP HA)

Bloqueantes activos: D-14 (Rudy — VMs OpenLDAP HA), D-16 (David Urquizo — Graph API write permisos).
