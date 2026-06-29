# Matriz IIA — Autoridad por atributo (UPeU)

**Fecha:** 2026-05-26
**Doctrina base:** Patrón B (Authority por atributo) — decisión de `midpoint-expert` validada contra Semančík cap. 6 + cap. 9, ISO 24760-2 §6.3, NIST 800-63A.
**Aplicabilidad:** todos los recursos del repo, incluyendo los que se desplieguen en el futuro (M365, Active Directory, etc.).

---

## 1. Principio doctrinal

> Un atributo del focus tiene **un único IIA (Identity Information Authority)** que escribe vía `<inbound>`. Otros recursos pueden *leer* el atributo (para correlación, `searchFilter` o validación), pero NO lo mapean al focus.

Las `strengths` (`strong/normal/weak`) **no son** mecanismo para repartir autoridad. Sirven para resolver el comportamiento del mapping ante valor previo (`weak` solo escribe si vacío, `normal` escribe si fuente cambió, `strong` siempre recomputa). Usarlas para "elegir ganador" entre múltiples IIAs del mismo atributo es anti-pattern (Semančík cap. 9, "Inbound mappings and authoritative sources").

### Excepción canónica permitida

Cuando un atributo tiene **autoridad principal + autoridad de override legal/jurídica**, se permite el patrón:

- IIA principal: `strength=strong` (o `normal` si la principal recomputa frecuentemente)
- Autoridad de override: `strength=strong` (sobrescribe siempre que esté presente)
- Fuentes secundarias: `strength=weak` (fallback solo cuando ningún otro IIA tiene valor)

Esto NO viola Patrón B porque las semánticas son distintas: override (legal) prevalece, principal (curado) es default, fallback (weak) cubre transitorios.

> **⚠️ CORRECCIÓN 2026-06-29 (colisión de tildes en `givenName`/`familyName`).**
> La "excepción" de **dos `strong` (principal + override)** sobre un item **single-valued**
> es **inválida en MidPoint** y se retira. `strength` NO arbitra entre dos mappings que
> ambos producen valor: MidPoint intenta materializar **ambos** y lanza
> `SchemaException: Strong mappings provided more than one value for single-valued item`.
> Esto rompió el recompute en personas con doble afiliación (trabajador "Rubi Nélida"
> vs RENIEC "Rubi Nelida" sin tilde). Regla corregida y vigente:
> **un único `strong` por item single-valued; el resto `weak` (+ `condition` last-resort).**
> Para multi-IIA sobre single-valued, canonicalizar TODAS las fuentes con la misma función
> (`FunctionLibrary sb-name-normalizer`) para que valores coincidentes sean idénticos.
> Detalle: `docs/runbooks/givenName-collision-fix-2026-06-29.md`.

---

## 2. Tabla de autoridad por atributo

### 2.1 Atributos core de identidad

| Atributo | IIA principal | Override | Fallback (weak) | Justificación |
|---|---|---|---|---|
| `name` (login) | `trabajadores` (COD_APS) / `estudiantes` (CODIGO) → CANON_KEY normalizado | — | — | Código institucional inmutable. **NO es el DNI.** Ver `DECISION-canonical-identifier.md` |
| `personalNumber` (== `name`, código institucional) | computed `= name` en object template | — | — | Réplica del código institucional para compat SCIM (`employeeNumber` RFC 7643 §4.3). **NO es el DNI.** Ver `DECISION-canonical-identifier.md` |
| `extension/institutionalCode` (== `name`) | computed `= name` en object template | — | — | Alias semántico para visualización. **NO es el DNI** |
| DNI / CE (documento legal) | `trabajadores` / `estudiantes` (`NUM_DOCUMENTO`) | `reniec-cache` (valida) | — | Va a `identityDocuments[]` → primario exportado como `schacPersonalUniqueID` (URN SCHAC) + `extension/sb:taxId`. **Llave de correlación, NO login.** Inmutable |
| `extension/upeu:lambDocNum` (clave doc type-aware, prefijo `CE:`/`PP:`) | **`trabajadores` `strong` (ÚNICO)** | — | `estudiantes`, `egresados` `weak` | Single-valued. Las 3 fuentes canonicalizan vía `FunctionLibrary sb-document-normalizer.toCanonicalDocNumber` → output byte-idéntico para igual `(num,type)`. **v2 2026-06-29:** un único strong + resto weak (se abandonó el `condition liveAffiliationWorker==null`, frágil: valor computado en el mismo wave → no suprimía → colisión CE vs DNI persistía). |
| `extension/upeu:lambDocType` (código tipo LAMB) | **`trabajadores` `strong` (ÚNICO)** | — | `estudiantes`, `egresados` `weak` | Mismo patrón. ⚠️ Limitación: ELISEO etiqueta extranjeros como DNI → en worker-CE el tipo queda mal (egresados con el CE correcto es weak y no compite). Remediación pendiente: MOISES>ELISEO para el tipo. Ver `docs/runbooks/lambDocNum-collision-fix-2026-06-29.md` |
| `extension/sb:taxId` (URN SCHAC, transporte→identityDocuments) | — (`trabajadores` archived; Bloque J2 lo limpia) | `reniec-cache` `normal` (solo `:DNI:`) | `estudiantes`, `egresados` `weak` (type-aware) | Single-valued. **v2 2026-06-29:** estudiantes/egresados pasan a weak (igual patrón); reniec `normal` solo emite DNI (RENIEC no tiene CE) → no colisiona con los weak `:CE:`. |
| `givenName` | **`trabajadores` `strong` (ÚNICO)** — NOMBRE canonicalizado (Title Case + NFC, conserva tildes) | — (RENIEC ya NO es override de nombre) | `estudiantes`, `egresados` `weak`; `reniec-cache` `weak`+`condition` last-resort | RENIEC entrega el nombre SIN diacríticos → degrada calidad y colisiona con trabajadores (single-valued). trabajadores ya trae el nombre con tildes correctas. Corrección 2026-06-29 |
| `familyName` | **`trabajadores` `strong` (ÚNICO)** | — | `estudiantes`, `egresados` `weak`; `reniec-cache` `weak`+`condition` last-resort | Ídem. Todas las fuentes pasan por `sb-name-normalizer.toCanonicalName` |
| `fullName` | computado en object template | — | — | Derivado de given + family |
| `emailAddress` | **`trabajadores` strong** (CORREO_INST) | — | — | Email institucional curado por RRHH. Egresados/estudiantes NO deben sobreescribirlo |
| `telephoneNumber` | `trabajadores` (CELULAR) | — | `estudiantes`, `egresados` (fallback) | Celular se actualiza más rápido en estudiantes activos |

### 2.2 Atributos de fecha y validación

| Atributo | IIA principal | Override | Fallback | Justificación |
|---|---|---|---|---|
| `extension/sb:birthDate` | `trabajadores` | **`reniec-cache` strong** | `estudiantes`, `egresados` (weak) | Fecha de nacimiento es dato legal RENIEC |
| `extension/sb:dataQualityStatus` | `reniec-cache` (único) | — | — | RENIEC marca el match/mismatch |
| `extension/sb:taxId` (URN SCHAC) | construido localmente | — | — | Derivado de DNI con namespace SCHAC |
| `activation/validFrom` | `trabajadores` (FEC_INGRESO) | — | `estudiantes` (FEC_MATRICULA) | Empleo es prioritario; estudio cubre el resto |
| `activation/validTo` | `trabajadores` (FEC_TERMINO + grace) | — | `egresados` (graduationDate + alumni policy) | Empleo activo NO debe vencer por alumni policy |
| `activation/administrativeStatus` | computed en template (Bloque F/H) | — | — | Lifecycle policy en focus, no en resource |

### 2.3 Atributos de afiliación y rol institucional

| Atributo | IIA principal | Override | Fallback | Justificación |
|---|---|---|---|---|
| `extension/sb:affiliations[]` | union de los 5 resources vía inbound `add` | — | — | Multivaluado natural — cada resource añade su afiliación |
| `extension/sb:primaryAffiliation` | **Bloque J3 del template** (computed desde affiliations[]) | Bloque K (jubilados override) | — | Derivado; NO debe venir de resource |
| `extension/sb:isResearcher` | `csv-investigadores-dgi` | — | — | Resource CSV separado, único IIA |
| `extension/sb:motivoCese` | `trabajadores` (vía JOIN PLLA_CESE) | — | — | Solo trabajadores tiene cese |

### 2.4 Atributos exclusivos de empleo

| Atributo | IIA único | Notas |
|---|---|---|
| `costCenter` | `trabajadores` | Formato `area.<ID_SEDEAREA>`; futuro: resolver a `OrgType` |
| `organizationalUnit` | `trabajadores` (NOMBRE_AREA) | Texto plano legible |
| `title` (jobTitle) | `trabajadores` (futuro: enrichment desde `ENOC.PLLA_PUESTO`) | Hoy vacío o manual |
| `extension/sb:hireDate` | `trabajadores` | FEC_INGRESO; warning si null en faculty/staff |
| `extension/sb:position` | `trabajadores` (NOMBRE_PUESTO) | Texto del puesto formal |
| `extension/sb:manager` | (futuro) `trabajadores` vía `ENOC.VW_PERFIL_PUESTO.ID_PERFIL_PUESTO_JEFE` | No implementado aún |

### 2.5 Atributos exclusivos académicos

| Atributo | IIA único | Resource |
|---|---|---|
| `extension/sb:academicProgram` | URI VocBench resuelto vía `sb-program-resolver` | `estudiantes` |
| `extension/sb:academicProgramCode` | notation EP-XXX | `estudiantes` |
| `extension/sb:admissionPeriod` | SEMESTRE de matrícula | `estudiantes` |
| `extension/sb:studyLevel` | TIPO_NIVEL_ENSENANZA | `estudiantes` |
| `extension/sb:graduationDate` | FEC_GRADUACION | `egresados` |
| `extension/sb:graduationSemester` | (revisar: hoy duplica admissionPeriod) | `egresados` |
| `extension/sb:degreeName` | NOMBRE_CERTIFICADO | `grados` |
| `extension/sb:degreeConferralDate` | FEC_CONFERIMIENTO | `grados` |

### 2.6 Atributos de localización

| Atributo | IIA principal | Fallback | Justificación |
|---|---|---|---|
| `locality` | `trabajadores` (SEDE_NOMBRE) | `estudiantes` (weak) | Sede donde trabaja > sede donde estudia |
| `extension/upeu:sedeId` | `trabajadores` (ID_SEDE) | `estudiantes` (weak) | Mismo principio |

### 2.7 Atributos de media

| Atributo | IIA principal | Override | Fallback | Justificación |
|---|---|---|---|---|
| `jpegPhoto` | `trabajadores` (LAMB-files staff) | — | `estudiantes` (weak, LAMB-files student) | Foto institucional staff es más curada |
| `extension/sb:photoUrl` | `trabajadores` | — | `estudiantes` (weak), `egresados` (weak) | Mismo principio |

---

## 3. Acciones derivadas de esta matriz

### 3.1 Para Ola 1 — Inbounds a modificar/eliminar

| Recurso | Atributo | Acción | Motivo |
|---|---|---|---|
| `estudiantes.xml` | `givenName`, `familyName` | strength `strong` → **`weak`** | RENIEC + trabajadores ganan; estudiantes solo fallback para student-only sin RENIEC |
| `estudiantes.xml` | `emailAddress` | **eliminar inbound** | trabajadores es IIA único de email institucional |
| `estudiantes.xml` | `telephoneNumber` | strength → **`weak`** | Fallback cuando trabajadores no tiene celular |
| `estudiantes.xml` | `locality` | strength → **`weak`** | Fallback cuando no es trabajador |
| `estudiantes.xml` | `jpegPhoto`, `photoUrl` | strength → **`weak`** | Fallback estudiante-only |
| `estudiantes.xml` | `birthDate` | strength → **`weak`** | RENIEC autoridad jurídica |
| `egresados.xml` | `givenName`, `familyName` | strength `strong` → **`weak`** | Mismo principio que estudiantes |
| `egresados.xml` | `emailAddress` | **eliminar inbound** | trabajadores IIA único |
| `egresados.xml` | `telephoneNumber` | strength → **`weak`** | Fallback |
| `egresados.xml` | `birthDate` | strength → **`weak`** | Fallback |
| `egresados.xml` | `jpegPhoto`, `photoUrl` | strength → **`weak`** | Fallback |
| `egresados.xml` | `locality`, `organizationalUnit` | strength → **`weak`** | Fallback |
| `grados.xml` | (solo `degreeName`, `conferralDate`) | sin cambios | Ya es exclusivo |

### 3.2 Recursos que se quedan como están

- `trabajadores.xml` — IIA principal, sus `strong` se mantienen.
- `reniec-cache.xml` — IIA jurídica de nombres y birthDate, sus `strong` se mantienen.

### 3.3 Para Ola 2 (M365 mañana) — regla nueva para recursos nuevos

> **Recursos nuevos NO declaran inbounds para atributos cuyo IIA ya está asignado en esta matriz.** Pueden leer el dato para correlación (`searchFilter`, identifier matching), pero el inbound al focus está prohibido salvo que la matriz se actualice explícitamente con una nueva fila.

Implicaciones inmediatas:
- `oracle-lamb-org.xml` (nuevo): `focus=OrgType`, no toca atributos de UserType.
- `m365.xml` (mañana): `focus=UserType` pero su única responsabilidad inbound serán los `extension/sb:m365License`, `extension/sb:teamsMemberOf` (atributos exclusivos M365). NO declara inbound a `emailAddress`, `givenName`, `familyName`, etc., aunque M365 los exponga.

### 3.4 Para Ola 3 — Validación

Después de Ola 1, monitorear durante 1 semana:
- ¿Hay usuarios que perdieron `familyName` al eliminar el `strong` de estudiantes/egresados? → señal de que falta RENIEC cache fetch.
- ¿Hay usuarios con `emailAddress` cambiado? → señal de que el inbound eliminado era el real autoritativo (raro).

Si las métricas son verdes durante 1 semana → considerar Ola 3.5: **eliminar los inbounds `weak` por completo** (no solo bajar strength), dejando solo el IIA principal y el override RENIEC.

---

## 4. Decisión sobre el caso borde: student-only sin RENIEC

**Escenario:** estudiante nuevo, DNI nunca consultado a RENIEC API, no es trabajador.

**Comportamiento actual:** `estudiantes.xml` con `strong` escribe `familyName` desde la matrícula.

**Comportamiento Ola 1 (strength `weak`):** si nadie escribió antes, `estudiantes.xml` escribe el nombre desde matrícula. Después, cuando reniec-cache fetchee, lo sobrescribe con el nombre legal.

**Comportamiento Ola 3.5 (eliminar weak):** el usuario se crea con `familyName=null` hasta que reniec-cache fetchee. Es transitoriamente correcto pero genera UX pobre.

**Política recomendada:** **mantener weak indefinidamente** para givenName/familyName/birthDate. Es un patrón canónicamente válido (Semančík cap. 9 — "mappings with weak strength provide non-authoritative defaults"). Eliminar weak solo si se garantiza RENIEC cache fetch antes de cualquier acceso al user.

---

## 5. Mantenimiento de esta matriz

- **Cada nuevo recurso DEBE proponer una entrada en esta matriz** antes de declararse cualquier `<inbound>`.
- **Cualquier cambio de strength o IIA** se documenta como ADR en `docs/specs/`.
- **Validación operativa:** task semanal `Reconcile-IIA-Audit` que compara los atributos del focus contra esta matriz y reporta divergencias.

---

## Referencias

- Semančík et al., "Practical Identity Management with MidPoint" v2.3, cap. 6 (Schema), cap. 9 (Focus Processing).
- ISO/IEC 24760-2:2015 §6.3 (Identity Information Authority).
- NIST SP 800-63A Rev. 4 §4 (Identity Resolution and Validation).
- Skill `iga-canonical-standards`, skill `midpoint-best-practices`.
- Decisión midpoint-expert agente `aa01e03f04f42e8e2` (2026-05-26).
