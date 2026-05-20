# Blueprint IGA para Universidades Peruanas — v1.0

> **Propósito:** Modelo canónico de Identity Governance & Administration (IGA) aplicable a cualquier universidad peruana licenciada por SUNEDU. Basado en la implementación de referencia UPeU (ver `../iga-canonical-model-upeu/01-spec.md`).
>
> **Uso:** Cada institución instancia este blueprint reemplazando las variables `{UNIVERSITY_*}` y añadiendo su propia Capa 3 (LOCAL). Los pilares y la Capa 1 (Ley 30220) son **no negociables**.
>
> **Versión:** 1.0 — 2026-05-14 — derivado de UPeU (ref. implementation).

---

## Tabla de contenidos

1. [Los 4 pilares canónicos](#1-los-4-pilares-canónicos)
2. [Variables de instanciación](#2-variables-de-instanciación)
3. [Fuentes normativas con citas precisas](#3-fuentes-normativas-con-citas-precisas)
4. [Taxonomía de Positions — 3 capas](#4-taxonomía-de-positions--3-capas)
5. [Schema extension mínima](#5-schema-extension-mínima)
6. [Roles de afiliación estándar](#6-roles-de-afiliación-estándar)
7. [Policy rules mínimas](#7-policy-rules-mínimas)
8. [Árbol organizacional canónico](#8-árbol-organizacional-canónico)
9. [Checklist de instanciación](#9-checklist-de-instanciación)
10. [Cómo agregar una Capa 3 LOCAL](#10-cómo-agregar-una-capa-3-local)

---

## 1. Los 4 pilares canónicos

Inviolables para toda universidad peruana. No se modifican per-cliente.

### Pilar 1 — Persona única
- Un objeto `UserType` + archetype `Person` (structural) por persona física, **de por vida**.
- `name == personalNumber` = código institucional inmutable (no DNI, no código universitario de matrícula que cambia).
- Multi-afiliación: una persona puede ser simultáneamente student + faculty + staff.
- Documentos de identidad tipados multivalor: DNI / CE / PASSPORT / PTP / CPP / CSR / ITIN.
- **Fuente:** ISO/IEC 24760-1 §3.1.2; eduPerson `eduPersonUniqueId`; Ley 30220 art. 12 (trazabilidad académica).

### Pilar 2 — Afiliaciones como roles birthright multivalor
- Roles concurrentes: `R-Affiliation-Student`, `R-Affiliation-Faculty`, `R-Affiliation-Staff`, `R-Affiliation-Alum`, `R-Affiliation-Affiliate`, `R-Affiliation-Contractor`.
- `eduPersonAffiliation` multivalor (eduPerson 202208 §1.2.1).
- `eduPersonPrimaryAffiliation` único, prelación: staff > faculty > student > alum > affiliate.
- Auto-asignados vía `assignmentTargetSearch` desde inbound del SIS/HR. **Prohibido asignación manual.**
- **Fuente:** eduPerson 202208; RBAC INCITS 359; Libro MidPoint §7.3 (birthright roles).

### Pilar 3 — Position-Based Access Control
- Catálogo de Posiciones como `ServiceType` con archetype `Position`.
- Asignar una Position → induce automáticamente Business Roles → Application Roles → Entitlements.
- Position vacante existe en catálogo pero no provisiona.
- 3 capas: Canónica (Ley 30220) + Operativa Común + LOCAL (cada universidad).
- **Fuente:** RBAC INCITS 359 §4 (Job function); SCHAC `schacPersonalPosition`; Libro MidPoint §7.4 (inducement).

### Pilar 4 — JML orquestado por el SIS/HR
- **Joiner:** aparece en SIS/HR → `draft` → validación → `active`.
- **Mover:** cambio de programa/puesto en SIS/HR → recompute automático.
- **Leaver:** `FEC_TERMINO` / estado inactivo → `suspended` → N días → `archived`.
- Todo automático. **Prohibido administración manual de afiliaciones y Positions.**
- **Fuente:** ISO/IEC 24760-1 §3.1.4 (lifecycle); ISO 27001 A.5.16; Ley 26644 (retención laboral PE).

---

## 2. Variables de instanciación

Cada cliente SciBack define estas variables en su archivo de configuración.

| Variable | Ejemplo UPeU | Descripción |
|---|---|---|
| `{UNIVERSITY_DOMAIN}` | `upeu.edu.pe` | Dominio canónico. Usado en `emailAddress`, `eppn`, `schacHomeOrganization` |
| `{UNIVERSITY_CODE}` | `UPEU` | Código institucional corto (3-6 chars, uppercase) |
| `{UNIVERSITY_NAME}` | `Universidad Peruana Unión` | Nombre oficial |
| `{UNIVERSITY_RUC}` | `20158417912` | RUC SUNAT |
| `{SEDE_CODES[]}` | `[LM, JU, TA]` | Codes de campus. Mínimo 1 |
| `{SEDE_NAMES[]}` | `[Lima, Juliaca, Tarapoto]` | Nombres de campus |
| `{FACULTY_CODES[]}` | `[FIA, FCE, FACTEO, ...]` | Codes de facultades |
| `{SIS_SCHEMA}` | `DAVID` (Oracle) | Schema del SIS (estudiantes) |
| `{HR_SCHEMA}` | `ELISEO` (Oracle) | Schema del HR (trabajadores) |
| `{ACTIVE_SEMESTER_ID}` | `279` | ID del semestre activo en el SIS |
| `{CAMPUS_CODE_MAIN}` | `LM` | Sede principal |
| `{EMAIL_SUFFIX}` | `@upeu.edu.pe` | Calculado de `{UNIVERSITY_DOMAIN}` |
| `{SCHAC_HOME_ORG_TYPE}` | `urn:schac:homeOrganizationType:eu:higherEducationalInstitution` | SCHAC constante para universidades |
| `{NAMESPACE_URI}` | `urn:upeu:midpoint:person` | Namespace schema extension |
| `{EXTENSION_OID}` | `b7d55017-...` | OID del XSD de extensión (único por universidad) |

---

## 3. Fuentes normativas con citas precisas

### 3.1 Estándares internacionales

| Estándar | Versión | Artículos relevantes | Uso en el modelo |
|---|---|---|---|
| **eduPerson** (REFEDS/Internet2) | 202208 v4.4.0 | §1.2.1 `eduPersonAffiliation` (multivalor, vocabulario cerrado); §1.2.5 `eduPersonPrimaryAffiliation`; §3 `eduPersonUniqueId` (omnidireccional, no reasignable) | Afiliaciones, identidad federable, SAML a IdPs |
| **SCHAC** (REFEDS) | 1.6.0 | `schacPersonalUniqueID` (URN: `urn:schac:personalUniqueID:pe:{type}:{country}:{number}`); `schacPersonalUniqueCode`; `schacPersonalPosition`; `schacHomeOrganization`; `schacDateOfBirth`; `schacExpiryDate` | Identificadores únicos PE, cargo institucional, vigencia |
| **SCIM 2.0** | RFC 7643 / 7644 | §4.1 User schema; §4.3 Enterprise Extension (`employeeNumber` → NO usar, deprecated; usar `personalNumber`) | Modelo de referencia para atributos; interop con cloud vendors |
| **ISO/IEC 24760-1/2/3** | 2025 | §3.1.2 identity; §3.1.3 identifier; §3.1.4 lifecycle (enrolled→active→suspended→archived→destroyed) | Framework IGA, lifecycle states, trazabilidad |
| **NIST SP 800-63-3** | 2017+errata | §4 IAL (Identity Assurance Level); IAL1=self-declared, IAL2=RENIEC verificado, IAL3=presencial | Clasificar nivel de aseguramiento de identidad por tipo de documento |
| **RBAC INCITS 359-2012** | R2022 | §4 Core RBAC; §7 Job function; §A.3 SoD; §B.2 Static SoD | Roles de afiliación, Positions, Separation of Duties |
| **REFEDS R&S** | 1.3 (2016-09) | Bundle de atributos obligatorios: `eduPersonPrincipalName`, `eduPersonTargetedID`, `mail`, `displayName`, `eduPersonScopedAffiliation`, `eduPersonAffiliation` | Acceso a bases de datos académicas (Scopus, WoS, IEEE, ProQuest) |

### 3.2 Normativa peruana

| Norma | Artículos clave | Uso en el modelo |
|---|---|---|
| **Ley 30220 — Ley Universitaria** | Art. 23 (Rector); Art. 24 (Vicerrectores); Art. 29 (Secretario General); Art. 34 (Consejo Universitario, 1/3 estudiantil); Art. 43 (Dir. Académico); Art. 48 (Investigación, CBC-3); Art. 52-54 (Decano, elección, funciones); Art. 55 (Rep. estudiantil); Art. 59 (Jefe Dpto. Académico); Art. 60-61 (Dir. Escuela Profesional); Art. 64 (Categorías: Principal/Asociado/Auxiliar); Art. 65 (TC/TP); Art. 66 (Extraordinarios: Honorario/Emérito/Visitante); Art. 83 (Posgrado) | Capa canónica de Positions (obligatoria para todas las universidades licenciadas SUNEDU) |
| **SUNEDU — 8 CBC** | CBC-1 (Existencia legal, gobierno); CBC-2 (Oferta formativa); CBC-3 (Investigación); CBC-4 (Docentes competentes); CBC-5 (Infraestructura y servicios: biblioteca); CBC-6 (Transparencia); CBC-7 (Bienestar estudiantil); CBC-8 (Mecanismos de inserción laboral) | CBC-3 justifica posiciones RENACYT; CBC-5 justifica posiciones de biblioteca; CBC-7 justifica VR Bienestar |
| **Ley 29733 — Datos Personales** | Art. 2 (datos sensibles: religión, biometría, salud); Art. 13 (consentimiento); Art. 18 (derecho ARCO) | DNI, `religion`, `birthDate` clasificados como dato sensible. Lifecycle `destroyed` solo por ARCO aprobado |
| **DS 029-2021-PCM — Gobierno Digital** | Art. 9 (identidad digital); Art. 12 (autenticación); Anexo 2 (atributos de identidad digital) | `emailAddress` institucional computado; `eppn` como identidad digital de persona |
| **DL 1350 / Ley Migración** | Art. 5 (Carné Extranjería); Art. 11 (PTP, CPP); Art. 36 (Refugio, CSR) | Vocabulario `identityDocuments[].type`: CE, PTP, CPP, CSR para extranjeros residentes |
| **Ley 26644 — Cómputo servicios** | Art. 1 (tiempo servicios); Art. 12 (retención) | Período retención `suspended` antes de `archived`: trabajadores = 90 días mínimo |
| **SUNEDU Res. 029-2017 — RENATI** | Art. 3 (identificación inequívoca autor); Art. 5 (tipo+número documento obligatorio) | Campos `identityDocuments[]` obligatorios para investigadores y egresados en repositorio |
| **CONCYTEC — RENACYT** | Reglamento RENACYT 2019, art. 7-10 (categorías I/II/III); art. 15 (calificado) | Positions `POS-INVESTIGADOR-RENACYT-{I\|II\|III}` + `POS-INVESTIGADOR-CALIFICADO` |

### 3.3 Documentación MidPoint (Evolveum)

| Recurso | Uso |
|---|---|
| Semančík et al., *Practical Identity Management with MidPoint* v2.3 (2024-11) | Libro fundacional. Caps 6-10: Schema, RBAC, Archetypes, Focus Processing, Org Structures |
| §6.1 — *"Schema is the law"*; §6.2 Lifecycle; §6.3 Activation | Lifecycle states, `administrativeStatus` solo override de emergencia |
| §7.2 PD-RBAC; §7.3 birthright; §7.4 inducement; §7.6 *"MidPoint always adds"* | Roles de afiliación, Positions, cascada inducements |
| §8.3 Archetypes structural/auxiliary; §8.4 *"archetypes solo direct assignment"* | Archetype `Person` único structural; anti-pattern inducement |
| §9.1-9.4 Object Templates; `assignmentTargetSearch` | Auto-asignación de roles; `fullName`, `emailAddress` computados |
| §10.2-10.5 OrgType; parentOrgRef; manager via relation | Árbol funcional; relación manager; NO herencia automática parent→child |

---

## 4. Taxonomía de Positions — 3 capas

### Capa 1 — Mandatoria Ley 30220 (todas las universidades SUNEDU)

> Aplica a **cualquier** universidad peruana licenciada, sin excepción. Si una universidad no tiene estas Positions en el catálogo MidPoint, incumple la gobernanza de identidad para RENATI/SUNEDU.

| Grupo | Code (template) | Display (template) | positionType | Fuente Ley 30220 |
|---|---|---|---|---|
| **Gobierno** | `POS-RECTOR` | Rector | `hybrid` | Art. 23 |
| | `POS-VICE-RECTOR-ACAD` | Vicerrector Académico | `hybrid` | Art. 24 |
| | `POS-VICE-RECTOR-ADM` | Vicerrector Administrativo | `hybrid` | Art. 24 |
| | `POS-SECRETARIO-GENERAL` | Secretario General | `administrative` | Art. 29 |
| **Gobierno Facultad** | `POS-DECANO-{FACU}` | Decano de Facultad | `hybrid` | Art. 52-54 |
| | `POS-JEFE-DPTO-ACAD-{DPTO}` | Jefe de Departamento Académico | `academic` | Art. 59 |
| | `POS-DIR-EP-{EP}` | Director de Escuela Profesional | `academic` | Art. 60-61 |
| **Docentes ordinarios** | `POS-DOCENTE-PRINCIPAL-TC` | Docente Principal TC | `academic` | Art. 64.a + 65.a |
| | `POS-DOCENTE-PRINCIPAL-TP` | Docente Principal TP | `academic` | Art. 64.a + 65.b |
| | `POS-DOCENTE-ASOCIADO-TC` | Docente Asociado TC | `academic` | Art. 64.b + 65.a |
| | `POS-DOCENTE-ASOCIADO-TP` | Docente Asociado TP | `academic` | Art. 64.b + 65.b |
| | `POS-DOCENTE-AUXILIAR-TC` | Docente Auxiliar TC | `academic` | Art. 64.c + 65.a |
| | `POS-DOCENTE-AUXILIAR-TP` | Docente Auxiliar TP | `academic` | Art. 64.c + 65.b |
| | `POS-DOCENTE-CONTRATADO` | Docente Contratado | `academic` | Art. 64 in fine |
| **Docentes extraordinarios** | `POS-DOCENTE-HONORARIO` | Docente Honorario | `academic` | Art. 66.a |
| | `POS-DOCENTE-EMERITO` | Docente Emérito | `academic` | Art. 66.b |
| | `POS-DOCENTE-VISITANTE` | Docente Visitante | `academic` | Art. 66.c |
| **Investigación** | `POS-DIR-INV` | Director de Investigación | `research` | Art. 48, CBC-3 |
| | `POS-INVESTIGADOR-RENACYT-I` | Investigador RENACYT I (Consagrado) | `research` | CONCYTEC RENACYT |
| | `POS-INVESTIGADOR-RENACYT-II` | Investigador RENACYT II (Distinguido) | `research` | CONCYTEC RENACYT |
| | `POS-INVESTIGADOR-RENACYT-III` | Investigador RENACYT III (Reconocido) | `research` | CONCYTEC RENACYT |
| | `POS-INVESTIGADOR-CALIFICADO` | Investigador CONCYTEC Calificado | `research` | CONCYTEC |
| **Posgrado** | `POS-DIR-POSGRADO` | Director de Escuela de Posgrado | `academic` | Art. 43 |
| | `POS-DIR-UNIDAD-POSGRADO-{EP}` | Director de Unidad de Posgrado | `academic` | Art. 43 |
| **Biblioteca** (CBC-5) | `POS-JEFE-BIBLIOTECA-{SEDE}` | Jefe de Biblioteca | `administrative` | SUNEDU CBC-5 |
| | `POS-BIBLIOTECARIO-{SEDE}` | Bibliotecario | `administrative` | SUNEDU CBC-5 |
| **Representación estudiantil** | `POS-REP-ESTUDIANTIL-CU` | Rep. Estudiantil Consejo Universitario | `student` | Art. 34 |
| | `POS-REP-ESTUDIANTIL-{FACU}` | Rep. Estudiantil Consejo de Facultad | `student` | Art. 55 |

### Capa 2 — Operativa común (toda universidad, no mandada por ley)

> Puestos que **toda** universidad operativa tiene, aunque la Ley 30220 no los exija explícitamente. Son la base para la Capa 3 LOCAL. Cada universidad puede renombrarlos pero la función IGA es la misma.

#### 2a. Tecnologías de Información (TI/DTI/Sistemas)

| Code (template) | Display | positionType | Notas |
|---|---|---|---|
| `POS-DIR-TI` | Director de Tecnologías de Información | `administrative` | Puede llamarse Dir. DTI, Dir. SI, Dir. OTIC según universidad |
| `POS-JEFE-INFRAESTRUCTURA-TI` | Jefe de Infraestructura TI | `administrative` | Servidores, red, datacenter |
| `POS-JEFE-DESARROLLO-SI` | Jefe de Desarrollo de Sistemas | `administrative` | Software institucional |
| `POS-JEFE-SOPORTE-TI` | Jefe de Soporte TI / Helpdesk | `administrative` | |
| `POS-ANALISTA-SI` | Analista de Sistemas | `administrative` | |
| `POS-TECNICO-TI` | Técnico TI | `administrative` | |

#### 2b. Recursos Humanos / Talento Humano

| Code (template) | Display | positionType | Notas |
|---|---|---|---|
| `POS-DIR-RRHH` | Director de Recursos Humanos / Talento Humano | `administrative` | |
| `POS-COORD-SELECCION` | Coordinador de Selección y Contratación | `administrative` | |
| `POS-COORD-CAPACITACION` | Coordinador de Capacitación y Desarrollo | `administrative` | |
| `POS-COORD-REMUNERACIONES` | Coordinador de Remuneraciones y Planillas | `administrative` | Acceso a sistemas de nómina |
| `POS-ASIST-RRHH` | Asistente de Recursos Humanos | `administrative` | |

#### 2c. Finanzas y Tesorería

| Code (template) | Display | positionType | Notas |
|---|---|---|---|
| `POS-DIR-FINANZAS` | Director Financiero / Económico | `administrative` | |
| `POS-JEFE-TESORERIA` | Jefe de Tesorería | `administrative` | SoD: no puede autorizar Y pagar |
| `POS-JEFE-CONTABILIDAD` | Jefe de Contabilidad | `administrative` | |
| `POS-COORD-PAGOS` | Coordinador de Pagos | `administrative` | SoD con `POS-COORD-AUTORIZACION` |
| `POS-COORD-AUTORIZACION` | Coordinador de Autorización de Gastos | `administrative` | SoD con `POS-COORD-PAGOS` |
| `POS-ASIST-CAJA` | Asistente de Caja | `administrative` | |

#### 2d. Admisión y Registros Académicos

| Code (template) | Display | positionType | Notas |
|---|---|---|---|
| `POS-DIR-ADMISION` | Director de Admisión | `administrative` | |
| `POS-DIR-REGISTROS-ACAD` | Director de Registros Académicos / Oficina del Registrador | `administrative` | Acceso completo al SIS |
| `POS-COORD-MATRICULA` | Coordinador de Matrícula | `administrative` | |
| `POS-ASIST-REGISTROS` | Asistente de Registros Académicos | `administrative` | |

#### 2e. Seguridad / Vigilancia

| Code (template) | Display | positionType | Notas |
|---|---|---|---|
| `POS-JEFE-SEGURIDAD-{SEDE}` | Jefe de Seguridad Campus | `administrative` | Acceso a CCTV, control de acceso físico |
| `POS-AGENTE-SEGURIDAD-{SEDE}` | Agente de Seguridad | `administrative` | Acceso restringido: solo control de acceso |

#### 2f. Infraestructura / Mantenimiento

| Code (template) | Display | positionType | Notas |
|---|---|---|---|
| `POS-DIR-INFRAESTRUCTURA` | Director de Infraestructura / Planta Física | `administrative` | |
| `POS-JEFE-MANTENIMIENTO-{SEDE}` | Jefe de Mantenimiento Campus | `administrative` | |
| `POS-TECNICO-MANTENIMIENTO` | Técnico de Mantenimiento | `administrative` | |
| `POS-DIR-OPERACIONES-{SEDE}` | Director de Operaciones Campus | `administrative` | Gestiona el campus en terreno |

#### 2g. Bienestar Estudiantil (SUNEDU CBC-7)

| Code (template) | Display | positionType | Notas |
|---|---|---|---|
| `POS-DIR-BIENESTAR` | Director de Bienestar Universitario / Estudiantil | `administrative` | Mandado por CBC-7 |
| `POS-COORD-PSICOLOGIA` | Coordinador de Psicología y Consejería | `administrative` | Acceso a expedientes clínicos (dato sensible Ley 29733) |
| `POS-COORD-TUTORIA` | Coordinador de Tutoría Académica | `administrative` | Acceso a historial académico |
| `POS-COORD-DEPORTES` | Coordinador de Deportes y Recreación | `administrative` | |
| `POS-COORD-BECAS` | Coordinador de Becas y Beneficios | `administrative` | Acceso a datos socioeconómicos |
| `POS-COORD-COMEDOR-{SEDE}` | Coordinador de Comedor / Alimentación | `administrative` | Acceso a sistema de comedor |
| `POS-ASIST-BIENESTAR` | Asistente de Bienestar | `administrative` | |

#### 2h. Salud Universitaria

| Code (template) | Display | positionType | Notas |
|---|---|---|---|
| `POS-DIR-SALUD-UNIV` | Director de Salud Universitaria / Tópico | `administrative` | |
| `POS-MEDICO-UNIV` | Médico Universitario | `administrative` | Acceso a historial clínico (dato sensible Ley 29733) |
| `POS-ENFERMERO-UNIV` | Enfermero Universitario | `administrative` | |

#### 2i. Educación Continua / Extensión Universitaria

| Code (template) | Display | positionType | Notas |
|---|---|---|---|
| `POS-DIR-EXTENSION-UNIV` | Director de Extensión Universitaria | `academic` | |
| `POS-DIR-CENTRO-IDIOMAS` | Director de Centro/Instituto de Idiomas | `academic` | Ej.: English for You (UPeU), Instituto de Inglés |
| `POS-DOCENTE-IDIOMAS` | Docente de Centro de Idiomas | `academic` | No Ley 30220 ordinario; acceso a Moodle como instructor |
| `POS-DIR-CEPRE-{SEDE}` | Director CEPRE / Centro Pre-Universitario | `academic` | |
| `POS-DOCENTE-CEPRE` | Docente CEPRE | `academic` | Acceso limitado al SIS (solo módulo CEPRE) |
| `POS-DIR-CONSERVATORIO` | Director de Conservatorio / Escuela de Artes | `academic` | Donde aplique |
| `POS-DOCENTE-CONSERVATORIO` | Docente de Conservatorio | `academic` | |

#### 2j. Marketing, Comunicación e Imagen

| Code (template) | Display | positionType | Notas |
|---|---|---|---|
| `POS-DIR-MARKETING` | Director de Marketing / Imagen Institucional | `administrative` | |
| `POS-COORD-COMUNICACION` | Coordinador de Comunicación y RRPP | `administrative` | |
| `POS-COORD-REDES-SOCIALES` | Coordinador de Redes Sociales y Contenido | `administrative` | |

#### 2k. Planificación y Calidad

| Code (template) | Display | positionType | Notas |
|---|---|---|---|
| `POS-DIR-PLANIF-CALIDAD` | Director de Planificación y Gestión de la Calidad | `administrative` | SUNEDU CBC-1 (acreditación) |
| `POS-COORD-ACREDITACION` | Coordinador de Acreditación / SINEACE | `administrative` | |
| `POS-COORD-ESTADISTICA` | Coordinador de Estadística Institucional | `administrative` | Acceso solo-lectura a SIS/LAMB |

#### 2l. Asistente de Docencia (estudiante con cargo)

| Code (template) | Display | positionType | Notas |
|---|---|---|---|
| `POS-ASIST-DOCENCIA` | Asistente de Docencia | `student` | Concurrent con `R-Affiliation-Student` |
| `POS-MONITOR-ACADEMICO` | Monitor Académico | `student` | Tutoría entre pares |

### Capa 3 — LOCAL (específica de cada universidad)

> Esta capa la define **cada cliente** al instanciar el blueprint. Documenta los puestos que no caben en las capas 1-2. Siempre marcados con `[LOCAL]` en el spec del cliente.

**Ejemplos UPeU-LOCAL:**
- `POS-DIR-MISION` — Dirección de Misión (institución adventista)
- `POS-DIR-INST-COLPORTOR` — Instituto de Desarrollo del Estudiante Colportor
- `POS-CAPELLAN-{SEDE}` — Capellán universitario / Pastor campus
- `POS-COORD-ORATORIO` — Coordinador de Oratorio universitario
- `POS-VICE-RECTOR-BIENESTAR` — Vicerrectorado propio de UPeU (Bienestar como VR)
- `POS-DIR-EDUCACION-ADVENTISTA-DISTANCIA` — Educación Adventista a Distancia
- Instituciones paralelas: `POS-DIR-COLEGIO-UNION`, `POS-DIR-CLINICA-GOOD-HOPE`

**Patrón para definir una Capa 3:**
```
1. ¿Existe en la Ley 30220? → va en Capa 1
2. ¿Toda universidad operativa lo tiene? → va en Capa 2
3. ¿Es específico de esta institución/misión/historia? → va en Capa 3 LOCAL
```

---

## 5. Schema extension mínima

La extensión XSD que **toda** instancia SciBack-IGA debe tener. Los atributos ya cubiertos por `UserType` core (givenName, familyName, emailAddress, personalNumber) **NO** se repiten.

```xsd
<!-- Namespace: {NAMESPACE_URI}, OID: {EXTENSION_OID} (único por universidad) -->
<xs:complexType name="UserTypeExtension">
  <!-- Identidad -->
  <xs:sequence>
    <xs:element name="identityDocuments" type="tns:IdentityDocumentType"
                minOccurs="0" maxOccurs="unbounded" a:displayName="Documentos de identidad"/>
    <xs:element name="institutionalCode" type="xs:string"
                minOccurs="0" maxOccurs="1"  a:displayName="Código institucional"/>

    <!-- Datos demográficos (eduPerson/SCHAC) -->
    <xs:element name="birthDate"         type="xs:date"   minOccurs="0" a:displayName="Fecha de nacimiento"/>
    <xs:element name="gender"            type="xs:string" minOccurs="0" a:displayName="Género (ISO 5218)"/>
    <xs:element name="nationality"       type="xs:string" minOccurs="0" a:displayName="Nacionalidad (ISO 3166 alpha-3)"/>
    <xs:element name="preferredName"     type="xs:string" minOccurs="0"/>
    <xs:element name="displayPronouns"   type="xs:string" minOccurs="0" maxOccurs="unbounded"/>

    <!-- Contacto -->
    <xs:element name="personalEmail"     type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element name="phoneNumber"       type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element name="streetAddress"     type="xs:string" minOccurs="0"/>
    <xs:element name="ubigeo"            type="xs:string" minOccurs="0" a:help="Código INEI 6 dígitos"/>

    <!-- Afiliación (derivados) -->
    <xs:element name="affiliations"      type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element name="primaryAffiliation" type="xs:string" minOccurs="0"/>
    <xs:element name="scopedAffiliations" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element name="entitlements"      type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element name="eppn"              type="xs:string" minOccurs="0"/>
    <xs:element name="eduPersonUniqueId" type="xs:string" minOccurs="0"/>
    <xs:element name="schacHomeOrganization" type="xs:string" minOccurs="0"/>
    <xs:element name="schacExpiryDate"   type="xs:date"   minOccurs="0"/>

    <!-- Académico (student) -->
    <xs:element name="academicProgram"   type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element name="academicProgramCode" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element name="studyLevel"        type="xs:string" minOccurs="0"/>
    <xs:element name="studyModality"     type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element name="studentCycle"      type="xs:integer" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element name="admissionPeriod"   type="xs:string" minOccurs="0"/>

    <!-- Laboral (faculty/staff) -->
    <xs:element name="employeeCategory"  type="xs:string" minOccurs="0"/>
    <xs:element name="employeeType"      type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element name="hireDate"          type="xs:date"   minOccurs="0"/>
    <xs:element name="terminationDate"   type="xs:date"   minOccurs="0"/>
    <xs:element name="contractType"      type="xs:string" minOccurs="0"/>
    <xs:element name="depto"             type="xs:string" minOccurs="0"/>

    <!-- Investigación -->
    <xs:element name="orcid"             type="xs:string" minOccurs="0"/>
    <xs:element name="concytecId"        type="xs:string" minOccurs="0"/>
    <xs:element name="researcherCategory" type="xs:string" minOccurs="0"/>

    <!-- Org/campus -->
    <xs:element name="homeCampus"        type="xs:string" minOccurs="0"/>

    <!-- Governance (draft → active) -->
    <xs:element name="lambIdPersona"     type="xs:string" minOccurs="0"/>
    <xs:element name="externalSystemId"  type="xs:string" minOccurs="0"/>
    <xs:element name="disability"        type="xs:boolean" minOccurs="0"/>

    <!-- LOCAL: cada universidad agrega aquí sus extensiones propias -->
  </xs:sequence>
</xs:complexType>

<xs:complexType name="IdentityDocumentType">
  <xs:sequence>
    <xs:element name="type"          type="xs:string"/> <!-- DNI|CE|PASSPORT|PTP|CPP|CSR|ITIN -->
    <xs:element name="number"        type="xs:string"/>
    <xs:element name="countryOfIssue" type="xs:string"/> <!-- ISO 3166-1 alpha-3 -->
    <xs:element name="primary"       type="xs:boolean"/>
    <xs:element name="issuedAt"      type="xs:date"   minOccurs="0"/>
    <xs:element name="expiresAt"     type="xs:date"   minOccurs="0"/>
    <xs:element name="verifiedBy"    type="xs:string"/> <!-- RENIEC|MIGRACIONES|INSTITUTIONAL|SELF-DECLARED -->
    <xs:element name="verifiedAt"    type="xs:date"   minOccurs="0"/>
  </xs:sequence>
</xs:complexType>
```

---

## 6. Roles de afiliación estándar

| Role Code | `eduPersonAffiliation` emitida | Asignación | Fuente IIA típica |
|---|---|---|---|
| `R-Affiliation-Student` | `student`, `member` | Matrícula activa en SIS | SIS.VW_FICHA_MATRICULA |
| `R-Affiliation-Faculty` | `faculty`, `employee`, `member` | Contrato docente activo | HR.VW_EMPLEADO con cat. docente |
| `R-Affiliation-Staff` | `staff`, `employee`, `member` | Contrato no-docente activo | HR.VW_EMPLEADO con cat. admin |
| `R-Affiliation-Alum` | `alum` | Egreso confirmado en SIS | SIS.VW_EGRESADO |
| `R-Affiliation-Affiliate` | `affiliate` | Alta manual con `validTo` | Manual / MDM |
| `R-Affiliation-Contractor` | `affiliate` (NO `employee`) | Contrato no-laboral con `validTo` | Manual |
| `R-Affiliation-Library-Walk-In` | `library-walk-in` | Alta puntual desde Koha | Koha |

**Prelación `eduPersonPrimaryAffiliation`:** `staff > faculty > student > alum > affiliate > library-walk-in`

---

## 7. Policy rules mínimas

Las siguientes 12 reglas son **no negociables** para cualquier instancia del blueprint. Se documentan completas en el spec de referencia UPeU `01-spec.md §5`.

| Code | Descripción | Bloquea `draft→active` |
|---|---|---|
| R-01 | Archetype `Person` obligatorio | Sí |
| R-02 | `name` inmutable y regex válida | Sí |
| R-03 | `personalNumber == name` | Fix automático |
| R-04 | ≥1 `identityDocuments[]` + exactamente 1 `primary=true` | Sí |
| R-05 | Regex correcta por tipo de documento | Sí |
| R-06 | DNI sin centinelas ni scramble | Sí |
| R-07 | ≥1 rol de afiliación activo | Sí |
| R-08 | `primaryAffiliation` coherente con prelación | Fix automático |
| R-09 | ≥1 `parentOrgRef` coherente | Sí |
| R-10 | `emailAddress` computado, no manual | Sí |
| R-11 | `lifecycleState` solo desde IIA | Sí |
| R-12 | SoD entre Positions mutuamente exclusivas | Sí |

---

## 8. Árbol organizacional canónico

```
{UNIVERSITY_CODE} (raíz — org-institution)
├── Campus {SEDE_CODE} (org-campus) — 1 por sede
│   ├── Facultad {FACU} (org-faculty) — N facultades
│   │   └── EP / Depto (org-department) — N por facultad
│   ├── Escuela de Posgrado (org-academic-unit)
│   ├── Unidades de Gestión (org-governance) — TI, RRHH, Finanzas, ...
│   └── Centros de Extensión (org-academic-unit) — CEPRE, Idiomas, CRAI
├── Partner Institutions (org-partner-institution) — instituciones afines
└── Position-Catalog (raíz lógica del catálogo de puestos — árbol paralelo)
    └── POS-* (Positions individuales)
```

**Archetype Orgs:**

| Archetype | Cardinalidad | Herencia de privilegios |
|---|---|---|
| `org-institution` | 1 (raíz) | NO hereda automáticamente (libro §10.4) |
| `org-campus` | N sedes | Inducements explícitos para campus-wide |
| `org-faculty` | N | — |
| `org-department` | N (hijo de faculty) | — |
| `org-academic-unit` | N (CEPRE, CRAI, Idiomas, ...) | — |
| `org-governance` | N (TI, RRHH, Finanzas, ...) | — |
| `org-partner-institution` | N | — |

---

## 9. Checklist de instanciación

Para cada nuevo cliente SciBack-IGA:

- [ ] Definir variables §2 (domain, campus codes, faculty codes, SIS/HR schema names)
- [ ] Generar OID único para namespace schema extension
- [ ] Importar archetype `Person` (structural único)
- [ ] Importar archetype `Affiliation-Role`
- [ ] Importar archetype `Position`
- [ ] Crear árbol Org con archetypes correctos (§8)
- [ ] Importar schema extension v1.0 (§5) con namespace propio
- [ ] Crear Object Template Person con mappings de computación (fullName, emailAddress, eppn, primaryAffiliation)
- [ ] Importar roles `R-Affiliation-*` (§6)
- [ ] Configurar policy rules R-01 a R-12 (§7)
- [ ] Poblar catálogo Positions: Capa 1 obligatoria + Capa 2 aplicable + Capa 3 LOCAL
- [ ] Configurar Resource SIS (estudiantes) + Resource HR (trabajadores) en `proposed`
- [ ] Test piloto: 1 joiner student + 1 joiner faculty → validar policy rules
- [ ] Activar Resources y comenzar import progresivo (solo `active` a OpenLDAP)

---

## 10. Cómo agregar una Capa 3 LOCAL

Al crear el spec del cliente (`{cliente}/doc/specs/iga-canonical-model/01-spec.md`):

1. Copiar este blueprint como base.
2. Reemplazar todas las variables `{UNIVERSITY_*}`.
3. Agregar una sección `## Capa 3 LOCAL — {UNIVERSITY_CODE}` con:
   - Puestos específicos de la misión/historia/estructura de la universidad.
   - Justificación de cada puesto LOCAL (¿por qué no está en Capa 1 o 2?).
   - Mapeo al código interno del HR/SIS del cliente.
4. Marcar cada elemento LOCAL con `[{UNIVERSITY_CODE}-LOCAL]` para diferenciarlo claramente del canónico.

**Ejemplos de elementos típicamente LOCAL:**
- Puestos de capellanía / pastoral (universidades confesionales: UPeU, UCSS, UPC-Opus Dei, etc.)
- Institutos propios sin equivalente genérico (Instituto Colportor UPeU, Instituto de Idiomas Chinos de alguna universidad con convenio asiático)
- Centros de producción o empresas-escuela propias
- Cargos de gobierno atípicos adicionales (4° Vicerrectorado, Consejo de Seniors, etc.)

---

**Fin del Blueprint v1.0**
Implementación de referencia: `../iga-canonical-model-upeu/01-spec.md`
Mantenido por: SciBack Engineering — contacto `alberto@sciback.pe`
