# Perfiles de Identidad UPeU — Modelado MidPoint IGA

> Documento vivo. Fuente: exploración directa Oracle LAMB (192.168.13.9:1521/UPEU) — solo lectura.
> Validado con midpoint-expert. Última actualización: 2026-05-20

---

## 1. Fuentes de datos en Oracle LAMB

Oracle LAMB es la **fuente de verdad única** para todos los perfiles de identidad de UPeU.

| Schema  | Dominio                          | Tablas clave                                               |
|---------|----------------------------------|------------------------------------------------------------|
| MOISES  | MDM de personas (núcleo)         | PERSONA, PERSONA_NATURAL, TRABAJADOR, CONDICION_LABORAL    |
| DAVID   | Académico / matrícula activa     | ACAD_MATRICULA, TIPO_PROGRAMA, ACAD_PROGRAMA_ESTUDIO, VW_SOLICITUD_INFRA |
| ELISEO  | RRHH / Nómina / Asistencia       | APS_EMPLEADO, APS_TRABAJADOR, APS_CARGO, APS_PLANILLA      |
| JOSUE   | Académico histórico / completo   | ACADEMICO_ESTUDIANTE, ACADEMICO_CARGA_ACADEMICA            |

> ⚠️ **NUNCA ejecutar INSERT / UPDATE / DELETE / DDL en Oracle LAMB.**

---

## 2. Entidad raíz: PERSONA

Toda identidad en UPeU tiene un `ID_PERSONA` en `MOISES.PERSONA`.
Es el identificador maestro que une todos los schemas.

### MOISES.PERSONA

| Campo          | Descripción                  | MidPoint                         |
|----------------|------------------------------|----------------------------------|
| ID_PERSONA     | PK interna de persona        | `extension/externalSystemId`     |
| NOMBRE         | Nombre(s)                    | `givenName`                      |
| PATERNO        | Apellido paterno             | `familyName`                     |
| MATERNO        | Apellido materno             | (parte de familyName extendido)  |
| CODIGO         | Código autogenerado LAMB     | `extension/universityIdCard`     |
| COD_DOC_SUNEDU | Código SUNEDU                | referencia regulatoria           |

### MOISES.PERSONA_NATURAL

| Campo             | Descripción                    | MidPoint                            |
|-------------------|--------------------------------|-------------------------------------|
| NUM_DOCUMENTO     | DNI / CE — **clave principal** | `extension/taxId` (indexed)         |
| ID_TIPODOCUMENTO  | Tipo doc (DNI, CE, Pasaporte)  | referencia                          |
| SEXO              | Género                         | `extension/demographics/gender`     |
| FEC_NACIMIENTO    | Fecha de nacimiento            | `extension/demographics/birthDate`  |
| CORREO            | Email personal                 | `extension/contactInfo/secondaryMail`|
| CORREO_INST       | **Email institucional**        | `emailAddress` (nativo)             |
| CELULAR           | Celular                        | `extension/contactInfo/phoneNumberAlt`|
| TELEFONO          | Teléfono fijo                  | (no sincronizar — uso interno)      |
| ID_UBIGEO         | Ubigeo Perú                    | `extension/demographics/province`   |
| ID_TIPOPAIS       | País                           | `extension/demographics/country`    |
| FOTO              | URL o BLOB foto                | `jpegPhoto` (nativo)                |
| ES_DOCENTE        | Flag: ¿es docente?             | afiliación computada (no mapear directo) |
| ESDISCAPACITADO   | Flag discapacidad              | `extension/compliance/isDisabled`   |
| PROTECCION_DATOS  | Consentimiento de datos        | `extension/compliance/dataProtectionConsent` — **bloqueante** |

**Claves de correlación:**
1. `NUM_DOCUMENTO` (DNI/CE) → `extension/taxId` — primaria
2. `CORREO_INST` → `emailAddress` — secundaria (cruce con Azure Entra ID)
3. `ID_PERSONA` → `extension/externalSystemId` — terciaria (siempre única)

---

## 3. Perfiles de Identidad

### 3.1 Trabajadores (MOISES.TRABAJADOR)

Conteo en Oracle LAMB (referencia, no refleja MidPoint):
- ~5.216 — Activo o Subsidiado
- ~186 — En Proceso de Contratación
- ~6.080 — Baja (histórico)

**En MidPoint PROD (2026-05-20):** staff 3.144 · faculty 135 (activos con sombra LAMB; la diferencia con Oracle se debe a la política de correlación: solo usuarios con código institucional válido (`name`/`personalNumber`) y DNI no-corrupto — llave de correlación vía `taxId` — se correlacionan).

#### Condición Laboral (`MOISES.CONDICION_LABORAL`)

| Código | Nombre                         | Arquetipo / Rol MidPoint         |
|--------|--------------------------------|----------------------------------|
| M      | **Misionero**                  | Arquetipo `MisionaryType`        |
| E      | Empleado                       | Arquetipo `AdministrativeStaffType` |
| C      | Contratado                     | Arquetipo `AdministrativeStaffType` + Rol `BR-Staff-Contratado` |
| CTC    | Contratado a Tiempo Completo   | Arquetipo `AdministrativeStaffType` + Rol `BR-Staff-Contratado` |
| TP     | Tiempo Parcial                 | Arquetipo `AdministrativeStaffType` + Rol `BR-Staff-Contratado` |
| P      | Prácticas Profesionales        | Arquetipo `AdministrativeStaffType` + Rol `BR-Staff-Practicante` |
| PP     | Prácticas Pre-Profesionales    | Arquetipo `AdministrativeStaffType` + Rol `BR-Staff-Practicante` |
| CND    | Contrato no Domiciliado        | Arquetipo `AdministrativeStaffType` + Rol `BR-Staff-Contratado` |
| N      | Ninguno                        | Caso especial — analizar          |

#### Tipo de Control Personal

| ID | Nombre                     | Relevancia IGA                         |
|----|----------------------------|----------------------------------------|
| 1  | Personal de Confianza      | Sin marcación obligatoria              |
| 2  | No sujeto a fiscalización  | —                                      |
| 3  | Sujeto a fiscalización     | Marcación biométrica requerida         |
| 4  | Personal de Dirección      | Sin marcación                          |
| 5  | Docente tiempo completo    | Doble shadow: trabajador + docente     |

#### Situación Laboral — acciones MidPoint

| ID | Nombre                                   | Acción MidPoint                     |
|----|------------------------------------------|-------------------------------------|
| 1  | Activo o Subsidiado                      | Usuario activo                      |
| P  | Proceso de Contratación                  | Pre-provisioning (sin acceso aún)   |
| 0  | Baja                                     | Leaver flow → desactivar            |
| 2  | Sin Vínculo Laboral (conceptos pend.)    | Desactivar (con retención temporal) |
| 3  | Suspensión Perfecta de Labores           | Suspender (no eliminar)             |
| C  | Categorización                           | Proceso especial — no automatizar   |

#### Tipo de Trabajador

| ID | Nombre                   | Notas                       |
|----|--------------------------|-----------------------------|
| 19 | Ejecutivo                | Alta dirección              |
| 20 | Obrero                   | Personal operativo          |
| 21 | Empleado                 | Administrativo / técnico    |
| 24 | Pensionista o Cesante    | Ex-empleado — Rol `BR-Pensioner` + `lifecycleState=archived` |
| 26 | Pensionista – Ley 28320  | Ídem                        |

---

### 3.2 Docentes (DAVID)

Un docente puede ser simultáneamente `TRABAJADOR` en MOISES (si es TC) — en ese caso tendrá **dos shadows**: uno en el resource de trabajadores y otro en el de docentes.

#### Tipos de Docente — activos

| Código | Nombre                                     |
|--------|--------------------------------------------|
| DP     | Docente Titular                            |
| DA     | Docente Adjunto                            |
| DDP    | Docente de Prácticas                       |
| DCP    | Docente Coordinador de Práctica            |
| JP     | Docente Jefe de Práctica                   |
| DTM    | Docente Titular Modular                    |
| DFA    | Docente Facilitador de Aprendizaje (online)|
| DTP    | Docente Tutor de Práctica                  |

#### Categorías Docente — activos

| Código | Nombre                       | Nivel SUNEDU |
|--------|------------------------------|--------------|
| DX     | Docente Extraordinario       | Ordinario    |
| PX     | Docente Auxiliar             | Ordinario    |
| PA     | Docente Asociado             | Ordinario    |
| PP     | Docente Principal            | Ordinario    |
| SC     | Contratado – sin Categoría   | Contratado   |

---

### 3.3 Estudiantes (DAVID)

Semestre 267: ~19.566 estudiantes matriculados activos en Oracle.

**En MidPoint PROD (2026-05-20):** student 1.679 activos (semestre vigente con correlación exitosa) · alumni 30.491 (egresados con archetype `alumni`). La volumetría total de usuarios MidPoint es 35.450.

#### Tipos de Programa — todos activos

| Código | Nombre                            | Nivel            | Rol MidPoint                |
|--------|-----------------------------------|------------------|-----------------------------|
| EP     | Escuela Profesional               | Pregrado         | `BR-Student-Pregrado`       |
| SP     | Escuela Profesional Semipresencial| Pregrado         | `BR-Student-Pregrado`       |
| AD     | Escuela Profesional a Distancia   | Pregrado         | `BR-Student-Pregrado`       |
| MG     | Maestría                          | Posgrado         | `BR-Student-Posgrado-Master`|
| DR     | Doctorado                         | Posgrado         | `BR-Student-Posgrado-Doctor`|
| SE     | Segunda Especialidad              | Posgrado         | `BR-Student-Posgrado`       |
| ESP    | Especialización                   | Posgrado         | `BR-Student-Posgrado`       |
| PM     | Pre-Maestría                      | Posgrado         | `BR-Student-Posgrado`       |
| DP     | Diplomado                         | Formación cont.  | `BR-Student-Formacion`      |
| D      | Diplomatura                       | Formación cont.  | `BR-Student-Formacion`      |
| C      | Capacitación                      | Formación cont.  | `BR-Student-Formacion`      |
| CC     | Capacitación Continua             | Formación cont.  | `BR-Student-Formacion`      |
| CE     | Capacitación Externa              | Formación cont.  | `BR-Student-Formacion`      |
| CPT    | Carrera Profesional Técnica       | Técnico          | `BR-Student-Tecnico`        |
| I      | Idiomas (Centro de Idiomas)       | Especial         | `BR-Student-Idiomas`        |
| CS     | Conservatorio                     | Especial         | `BR-Student-Conservatorio`  |
| CEP    | CEPRE (preuniversitario)          | Especial         | `BR-Student-CEPRE`          |
| S      | SALT                              | Especial         | `BR-Student-SALT`           |
| E      | Especialidad                      | Especial         | `BR-Student-Formacion`      |
| N      | Nivelación                        | Especial         | `BR-Student-Formacion`      |
| T      | Tesis                             | Investigación    | `BR-Student-Posgrado`       |
| INV    | Investigación                     | Investigación    | `BR-Student-Posgrado`       |

---

## 4. Modelado MidPoint

### 4.1 Arquetipos — estado actual en PROD (2026-05-20)

> Regla: los arquetipos definen **ciclo de vida y política de aprovisionamiento**, no permisos.
> Los permisos específicos van en Roles.

Los arquetipos canónicos activos en PROD son los nombres eduPerson estándar (sin sufijo `Type`):

| Arquetipo (canónico) | Perfil Oracle | Ciclo de vida | Usuarios PROD |
|---|---|---|---|
| `student` | Matriculados activos (DAVID) | Joiner=matrícula, Leaver=fin semestre + 6 meses | 1.679 |
| `faculty` | Docentes con carga académica (DAVID) | Leaver diferido 30 días, conservar correo inst. | 135 |
| `staff` | Personal E/C/CTC/TP/P/PP/CND/M (MOISES) | Leaver diferido 15 días | 3.144 |
| `alumni` | Ex-alumnos post-egreso (DAVID.VW_PERSONA_EGRESADO) | Solo lectura, acceso Alumni indefinido | 30.491 |
| `affiliate-partner-institution` | Clínica GH, Colegio Unión, ISTAT, AGTU | Alta manual + `validTo` | pendiente poblar |
| `contractor` | Prestadores de servicios sin relación laboral | Alta manual + `validTo` | pendiente poblar |
| `service-account` | Cuentas técnicas (apps, daemons) | Sin auth interactiva | pendiente poblar |

> Los arquetipos `MisionaryType` y `TechnicalStaffType` de versiones anteriores fueron **consolidados en `staff`**. La condición laboral misionero (código M) se modela como business role `BR-Staff-Misionario` sobre el archetype `staff`.
>
> `ContractedStaffType`, `InternType`, `PensionerType` **NO son arquetipos** — son business roles asignados sobre el arquetipo base.

---

### 4.2 Roles propuestos

Los roles se asignan automáticamente desde el Object Template usando `assignmentTargetSearch`
filtrado por `TIPO_PROGRAMA_CODE` o `CONDICION_LABORAL_CODE` de las vistas Oracle.

#### Roles de Afiliación Estudiantil

```
BR-Student-Pregrado          — EP / SP / AD
BR-Student-Posgrado-Master   — MG
BR-Student-Posgrado-Doctor   — DR
BR-Student-Posgrado          — SE / ESP / PM / T / INV
BR-Student-Formacion         — DP / D / C / CC / CE / E / N
BR-Student-Tecnico           — CPT
BR-Student-Idiomas           — I
BR-Student-Conservatorio     — CS
BR-Student-CEPRE             — CEP
BR-Student-SALT              — S
```

#### Roles de Afiliación Laboral

```
BR-Staff-Misionario          — CONDICION M (activo)
BR-Staff-Empleado            — CONDICION E
BR-Staff-Contratado          — CONDICION C / CTC / TP / CND
BR-Staff-Practicante         — CONDICION P / PP
BR-Staff-Pensioner           — TIPO_TRABAJADOR 24 / 26
BR-Staff-Docente-Titular     — TIPO_DOCENTE DP
BR-Staff-Docente-Adjunto     — TIPO_DOCENTE DA
BR-Staff-Docente-JefePractica— TIPO_DOCENTE JP
BR-Staff-Docente-Online      — TIPO_DOCENTE DFA
BR-Staff-DirectorGeneral     — CARGO = Director General
```

#### Roles de Acceso a Sistemas (existentes)

```
APP-Koha-BUL / APP-Koha-BUJ / APP-Koha-BUT / APP-Koha-CIA
APP-EntraID-Member
APP-Keycloak-upeu
```

---

### 4.3 Diseño de Resources JDBC

**Decisión: dos resources JDBC separados** (no uno, no tres).

| Resource                | Vista Oracle          | Intent        | Arquetipo asignado          |
|-------------------------|-----------------------|---------------|-----------------------------|
| `Lamb-Trabajadores`     | VW_IGA_TRABAJADORES   | trabajador    | Según CONDICION_LABORAL      |
| `Lamb-Estudiantes`      | VW_IGA_ESTUDIANTES    | estudiante    | `StudentType` + rol por tipo |

Ventajas:
- Tasks de reconciliación independientes
- Si una vista falla, la otra no se afecta
- Un docente TC tendrá **dos shadows** (trabajador + docente en su matrícula de posgrado)

**Una fila por persona** en cada vista. Matrículas múltiples serializadas con `LISTAGG`:
```sql
LISTAGG(PE.CODIGO, '|') WITHIN GROUP (ORDER BY M.ID_SEMESTRE) AS CODIGOS_PROGRAMA
```
MidPoint deserializa en el mapping:
```groovy
input?.split('\\|')?.toList()
```

---

### 4.4 Schema Extension — ajustes sobre v2.2

#### Campos a agregar

**En `EmploymentDataType`** — campos faltantes de Oracle:
```xml
<xsd:element name="laboralStatus" type="xsd:string" minOccurs="0"/>
<!-- ACTIVO | BAJA | SIN_VINCULO | SUSPENSION | PROCESO_CONTRATACION -->

<xsd:element name="laboralCondition" type="xsd:string" minOccurs="0"/>
<!-- MISIONERO | EMPLEADO | CONTRATADO | TIEMPO_PARCIAL | PRACTICAS | etc. -->

<xsd:element name="jobTitle" type="xsd:string" minOccurs="0"/>
<!-- cargo/puesto de trabajo — usar si no hay conflicto con 'title' nativo -->
```

**En `AcademicStatusType`** — campos faltantes:
```xml
<xsd:element name="programType" type="xsd:string" minOccurs="0" maxOccurs="unbounded">
  <xsd:annotation><xsd:appinfo><a:indexed>true</a:indexed></xsd:appinfo></xsd:annotation>
</xsd:element>
<!-- EP | MG | DR | CEP | SALT | I | CS | etc. — multivalor para doble matrícula -->

<xsd:element name="currentSemester" type="xsd:string" minOccurs="0"/>
<!-- semestre académico vigente, ej. "2025-I" -->
```

**Nueva sección `ComplianceType`** — requerida por Ley 29733 y Ley 29973:
```xml
<xsd:complexType name="ComplianceType">
  <xsd:sequence>
    <xsd:element name="dataProtectionConsent" type="xsd:boolean" minOccurs="0"/>
    <!-- PROTECCION_DATOS de MOISES.PERSONA_NATURAL -->
    <!-- si false → limitar propagación a sistemas terceros -->
    <xsd:element name="isDisabled" type="xsd:boolean" minOccurs="0"/>
    <!-- ESDISCAPACITADO de MOISES.PERSONA_NATURAL -->
  </xsd:sequence>
</xsd:complexType>
```

#### Duplicidad a resolver

`employeeType` existe tanto en `AffiliationDataType` (custom) como en `UserType` nativo de MidPoint.
- Usar `UserType.employeeType` nativo para: `student` | `professor` | `staff` | `misionary`
- Usar `AffiliationDataType.laboralCondition` para la condición específica (MISIONERO, CONTRATADO, etc.)
- **Eliminar** `employeeType` de `AffiliationDataType` custom

#### Campos a evaluar para eliminar

- `ContactInfoType.personalWeb` — ningún sistema destino lo consume actualmente
- `institutionalIdCard` vs `universityIdCard` — verificar si son realmente distintos en UPeU; consolidar si no

---

### 4.5 Correlación y Reconciliación

#### Reglas de correlación por recurso (estado PROD 2026-05-20)

| Recurso | Atributo correlación | Campo MidPoint | Notas |
|---|---|---|---|
| LAMB Trabajadores v3 | NUM_DOCUMENTO (DNI/CE) | `extension/sb:taxId` / `extension/upeu:lambDocNum` | Correlación principal activos. El DNI NO es `personalNumber` (ver `DECISION-canonical-identifier.md`) |
| LAMB Trabajadores v3 | COD_TRABAJADOR | `extension/upeu:lambDocNum` | Correlación por código LAMB |
| LAMB Estudiantes v3 | NUM_DOCUMENTO (DNI/CE) | `extension/sb:taxId` / `extension/upeu:lambDocNum` | El DNI correlaciona vía `taxId`, NO `personalNumber` (= código institucional) |
| LAMB Egresados v3 | NUM_DOCUMENTO | `extension/sb:taxId` | Correlación legado egresados |
| LAMB Posiciones | ID_PUESTO | (ServiceType) | Resource de posiciones |
| Entra ID | userPrincipalName | `emailAddress` | Solo lectura |
| Koha ILS | EMAIL | `emailAddress` | |
| LDAP Identity Cache | uid | `name` | Outbound desde MidPoint |

#### Reacciones por situación

| Situación Oracle          | Acción MidPoint                    |
|---------------------------|------------------------------------|
| ACTIVO (1)                | Provisionar / activar              |
| PROCESO_CONTRATACION      | Pre-provisioning (sin acceso aún)  |
| BAJA (0)                  | Leaver flow → desactivar           |
| SUSPENSION_PERFECTA       | Suspender temporalmente            |
| Sin matrícula activa      | Inactivar estudiante               |

---

### 4.6 Campos críticos que deben pedirse al DBA

Estos campos no están en las tablas exploradas y son necesarios para el correcto funcionamiento:

| Campo necesario          | Uso en MidPoint                          | Dónde pedirlo             |
|--------------------------|------------------------------------------|---------------------------|
| `FECHA_MODIFICACION`     | **Sync incremental** — sin este solo hay reconciliación completa cada vez | Trigger o campo en MOISES/DAVID |
| `FECHA_TERMINO_CONTRATO` | Respaldo para Leaver si FECHA_FIN_EFECTIVO es null | ELISEO.APS_EMPLEADO.FEC_TERMINO |
| `ID_SEDEAREA` → nombre  | `extension/campus` para asignación de OUs | JOIN tabla de sedes        |
| `SEMESTRE_NOMBRE`        | `extension/currentSemester` legible      | JOIN DAVID.ACAD_SEMESTRE   |

---

## 5. Vistas IGA en PostgreSQL

> **Actualizado Abril 2026:** Las vistas ya NO se crean en Oracle. Se crean en el schema `iga`
> de PostgreSQL, sobre las tablas replicadas vía CDC en el schema `lamb`.
> SQL completo: `oracle-cdc/docs/vistas-iga.sql`

**Dos vistas** con una fila por persona, campos clave normalizados. En PostgreSQL se usa `string_agg` en lugar del `LISTAGG` de Oracle.

### VW_IGA_TRABAJADORES

Cubre: empleados, contratados, misioneros, practicantes, pensionistas.

```sql
CREATE OR REPLACE VIEW DAVID.VW_IGA_TRABAJADORES AS
SELECT
    -- Identidad (nombres AS-IS: formato oficial RENIEC/DNI en ALL CAPS)
    -- La normalización estética (INITCAP, lower, etc.) se aplica en los
    -- outbound mappings de MidPoint según lo requiera cada sistema destino.
    P.ID_PERSONA,
    P.NOMBRE                          AS NOMBRE,
    P.PATERNO                         AS PATERNO,
    P.MATERNO                         AS MATERNO,
    P.PATERNO || ' ' || P.MATERNO || ', ' || P.NOMBRE AS NOMBRE_COMPLETO,
    P.CODIGO                          AS COD_LAMB,
    PN.NUM_DOCUMENTO,
    PN.ID_TIPODOCUMENTO,
    PN.SEXO,
    PN.FEC_NACIMIENTO,
    PN.CORREO                         AS EMAIL_PERSONAL,
    LOWER(PN.CORREO_INST)             AS EMAIL_INSTITUCIONAL,
    PN.CELULAR,
    PN.FOTO,
    PN.PROTECCION_DATOS,
    PN.ESDISCAPACITADO,
    -- Datos laborales
    T.ID_TRABAJADOR,
    T.FECHA_INGRESO,
    T.FECHA_FIN_EFECTIVO,
    T.FECHA_FIN_PREVISTO,
    S.NOMBRE                          AS SITUACION_LABORAL,      -- 'Activo o Subsidiado', 'Baja', etc.
    CL.ID_CONDICION_LABORAL           AS CONDICION_LABORAL_CODE, -- 'M', 'E', 'C', 'TP', etc.
    CL.NOMBRE                         AS CONDICION_LABORAL,
    TCP.ID_TIPO_CONTROL_PERSONAL      AS TIPO_CONTROL_CODE,
    TCP.NOMBRE                        AS TIPO_CONTROL,
    TT.NOMBRE                         AS TIPO_TRABAJADOR,        -- Ejecutivo, Obrero, Empleado, Pensionista
    AC.NOMBRE                         AS CARGO_NOMBRE,
    -- Contrato ELISEO
    AE.ID_TIPOCONTRATO                AS TIPO_CONTRATO_CODE,
    AE.FEC_INICIO                     AS FECHA_INICIO_CONTRATO,
    AE.FEC_TERMINO                    AS FECHA_TERMINO_CONTRATO,
    AE.ESTADO                         AS ESTADO_CONTRATO,
    -- Campus / sede
    T.ID_SEDEAREA
FROM MOISES.PERSONA P
JOIN MOISES.PERSONA_NATURAL PN ON P.ID_PERSONA = PN.ID_PERSONA
JOIN MOISES.TRABAJADOR T ON P.ID_PERSONA = T.ID_PERSONA
JOIN MOISES.SITUACION_TRABAJADOR S ON T.ID_SITUACION_TRABAJADOR = S.ID_SITUACION_TRABAJADOR
LEFT JOIN MOISES.CONDICION_LABORAL CL ON T.ID_CONDICION_LABORAL = CL.ID_CONDICION_LABORAL
LEFT JOIN MOISES.TIPO_CONTROL_PERSONAL TCP ON T.ID_TIPO_CONTROL_PERSONAL = TCP.ID_TIPO_CONTROL_PERSONAL
LEFT JOIN MOISES.TIPO_TRABAJADOR TT ON T.ID_TIPO_TRABAJADOR = TT.ID_TIPO_TRABAJADOR
LEFT JOIN ELISEO.APS_CARGO AC ON T.ID_PUESTO = AC.ID_CARGO
LEFT JOIN ELISEO.APS_EMPLEADO AE ON P.ID_PERSONA = AE.ID_PERSONA
    AND AE.ESTADO = 'A'  -- solo contrato activo
WHERE T.ID_SITUACION_TRABAJADOR IN (1, 'P')  -- Activos + En proceso
  AND T.ID_PERSONA = (
      SELECT MAX(T2.ID_PERSONA) FROM MOISES.TRABAJADOR T2
      WHERE T2.ID_PERSONA = T.ID_PERSONA
  ); -- una fila por persona (el registro más reciente si hay duplicados)
```

### VW_IGA_ESTUDIANTES

Cubre: todos los matriculados en el semestre activo (pregrado, posgrado, idiomas, conservatorio, CEPRE, SALT, técnico, etc.).

```sql
CREATE OR REPLACE VIEW DAVID.VW_IGA_ESTUDIANTES AS
SELECT
    -- Identidad (nombres AS-IS: formato oficial RENIEC/DNI en ALL CAPS)
    -- La normalización estética (INITCAP, lower, etc.) se aplica en los
    -- outbound mappings de MidPoint según lo requiera cada sistema destino.
    P.ID_PERSONA,
    P.NOMBRE                          AS NOMBRE,
    P.PATERNO                         AS PATERNO,
    P.MATERNO                         AS MATERNO,
    P.PATERNO || ' ' || P.MATERNO || ', ' || P.NOMBRE AS NOMBRE_COMPLETO,
    P.CODIGO                          AS COD_LAMB,
    PN.NUM_DOCUMENTO,
    PN.ID_TIPODOCUMENTO,
    PN.SEXO,
    PN.FEC_NACIMIENTO,
    PN.CORREO                         AS EMAIL_PERSONAL,
    LOWER(PN.CORREO_INST)             AS EMAIL_INSTITUCIONAL,
    PN.CELULAR,
    PN.FOTO,
    PN.PROTECCION_DATOS,
    PN.ESDISCAPACITADO,
    -- Matrícula principal (programa de mayor jerarquía)
    MAX(PE.ID_NIVEL_ENSENANZA)        AS NIVEL_ENSENANZA_PRINCIPAL,
    MAX(TP.CODIGO)                    AS TIPO_PROGRAMA_PRINCIPAL,
    -- Todos los programas activos (multivalor serializado con |)
    LISTAGG(PE.NOMBRE, '|')
        WITHIN GROUP (ORDER BY PE.ID_NIVEL_ENSENANZA DESC) AS PROGRAMAS_ESTUDIO,
    LISTAGG(TP.CODIGO, '|')
        WITHIN GROUP (ORDER BY PE.ID_NIVEL_ENSENANZA DESC) AS TIPOS_PROGRAMA,
    LISTAGG(PE.CODIGO, '|')
        WITHIN GROUP (ORDER BY PE.ID_NIVEL_ENSENANZA DESC) AS CODIGOS_PROGRAMA,
    -- Semestre
    MAX(M.ID_SEMESTRE)                AS ID_SEMESTRE_ACTIVO
FROM DAVID.ACAD_MATRICULA M
JOIN DAVID.ACAD_PROGRAMA_ESTUDIO PE ON M.ID_PROGRAMA_ESTUDIO = PE.ID_PROGRAMA_ESTUDIO
JOIN DAVID.TIPO_PROGRAMA TP ON PE.ID_NIVEL_ENSENANZA = TP.ID_TIPO_PROGRAMA
JOIN MOISES.PERSONA P ON M.ID_PERSONA = P.ID_PERSONA
JOIN MOISES.PERSONA_NATURAL PN ON P.ID_PERSONA = PN.ID_PERSONA
WHERE M.ID_SEMESTRE = (
        SELECT MAX(S.ID_SEMESTRE) FROM DAVID.ACAD_SEMESTRE S WHERE S.ESTADO = 1
    )
  AND M.ESTADO = 1
GROUP BY
    P.ID_PERSONA, P.NOMBRE, P.PATERNO, P.MATERNO, P.CODIGO,
    PN.NUM_DOCUMENTO, PN.ID_TIPODOCUMENTO, PN.SEXO, PN.FEC_NACIMIENTO,
    PN.CORREO, PN.CORREO_INST, PN.CELULAR, PN.FOTO,
    PN.PROTECCION_DATOS, PN.ESDISCAPACITADO;
```

> ⚠️ Las vistas son un borrador para revisar con Carlomagno (DBA). Los nombres exactos de tablas
> de semestres (`DAVID.ACAD_SEMESTRE`) y la lógica del contrato activo en ELISEO deben confirmarse.

---

## 6. Org Units — actual y pendiente

#### Estado en PROD (2026-05-20): 122 OUs tipificadas

```
UPeU (institution, raíz)
├── Lima / Juliaca / Tarapoto       (3 campus)
├── Instituciones afines            (3 partner-institution: Clínica GH, Colegio Unión, ISTAT)
├── Gobierno                        (12 governance: Rectorado, Decanatos, etc.)
├── Facultades                      (5 faculty con archetypes)
├── Unidades académicas             (31 academic-unit)
└── Departamentos                   (36 department)
```

Total: 1 institution + 3 campus + 3 partner + 12 governance + 5 faculty + 31 academic-unit + 36 department = 91 estructurales + ~31 adicionales = 122.

Los organismos especiales (Centro de Idiomas, Conservatorio, CEPRE, PROESAD, SALT, Productos Unión) están modelados como `academic-unit` o `department` según su naturaleza en el organigrama.

---

## 7. Pipeline — estado actual (2026-05-20)

> **Decisión arquitectural ejecutada:** MidPoint 4.10.2 se conecta **directamente a Oracle LAMB** vía JDBC (`ojdbc11` + driver bundled). El enfoque CDC (Debezium + Kafka) fue evaluado y descartado — no fue necesario: el driver ojdbc11 está disponible en MidPoint y Oracle 11g es accesible directamente desde el servidor PROD.

```
Oracle LAMB (fuente de verdad, solo lectura — 192.168.13.9:1521/UPEU)
    │  JDBC directo (ojdbc11) — cuenta JUANSANCHEZ/DEVELOP_READ
    ▼
MidPoint 4.10.2 (192.168.15.166:8080)
    │  Reconciliación — 3 crons LAMB a las 02:00 UTC
    │  Trigger Scanner — polling 5 min
    │  Validity Scanner — 15 min (lifecycles)
    │
    ├──► OpenLDAP Identity Cache (192.168.15.168:389) — 37.491 sombras
    │       └──► Keycloak 26.6.1 (User Federation LDAP)
    │
    ├──► Entra ID (Graph API, solo lectura) — 37.304 sombras
    │       └── write pendiente (David Urquizo, DU-001a)
    │
    └──► Koha ILS — 5.421 sombras (cron 03:00 UTC)
```

| Componente | Estado |
|---|---|
| Oracle LAMB Trabajadores v3 | ✅ Activo — 3.144 staff + 135 faculty |
| Oracle LAMB Estudiantes v3 | ✅ Activo — 1.679 student |
| Oracle LAMB Egresados v3 | ✅ Activo — 30.491 alumni |
| LAMB-Oracle-Posiciones | ✅ Activo — 741 ServiceType |
| LDAP Identity Cache | ✅ Activo — 37.491 sombras |
| Entra ID | ✅ Activo solo lectura — write pendiente |
| Koha ILS | ✅ Activo — 5.421 sombras |
| CDC Debezium/Kafka | ❌ Descartado — no necesario |

---

## 8. Checklist para próxima reunión con DBA (Carlomagno)

- [ ] ¿Hay ruta de red entre 192.168.15.166 (MidPoint prod) y 192.168.13.9 (Oracle)?
- [ ] ¿Existe campo `FECHA_MODIFICACION` o trigger de cambio en MOISES.TRABAJADOR / DAVID.ACAD_MATRICULA?
- [ ] ¿Cómo se llama la tabla de semestres? (`DAVID.ACAD_SEMESTRE` — confirmar)
- [ ] ¿La vista puede crearse en schema `DAVID` o se prefiere uno dedicado (ej. `IGA`)?
- [ ] ¿El usuario `JUANSANCHEZ` puede hacer SELECT sobre la vista una vez creada?
- [ ] ¿Se puede agregar un índice en `NUM_DOCUMENTO` en MOISES.PERSONA_NATURAL para acelerar correlación?

---

*Documento: `docs/perfiles-identidad.md` — proyecto `/Users/alberto/proyectos/upeu/midpoint`*
