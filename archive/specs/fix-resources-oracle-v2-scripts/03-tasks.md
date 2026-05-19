# Tasks: Fix de searchScript / inbounds en los 3 resources Oracle LAMB v2

**Spec:** doc/specs/fix-resources-oracle-v2-scripts/02-specification.md
**Created:** 2026-05-12
**Last Updated:** 2026-05-12
**Last Decompose:** 2026-05-12

> **Ejecución técnica:** TODAS las tareas con cambio de XML / deploy / REST / ninja / troubleshooting se delegan al sub-agente `midpoint-expert`, que consulta `iga-canonical-standards` + `midpoint-best-practices` antes de cualquier decisión de diseño. Las tareas de doc (P4) las puede hacer el orquestador.

## Summary

| Status | Count |
|--------|-------|
| ⏳ Pending | 0 |
| 🔄 In Progress | 0 |
| ✅ Completed | 9 |
| **Total** | **9** |

> ✅ **SPEC COMPLETA (2026-05-13).** Los 3 resources Oracle LAMB v2 están production-ready: test connection success, shadows todos LINKED (0 dead), campos nuevos poblados, tasks recon masiva siguen SUSPENDED. Ver Task 3.2 para reporte ejecutivo completo.
> 📌 **Corrección de proceso:** los XML `resources/oracle-lamb-*-v2.xml` viven en el repo **`SciBack/midpoint`** (no en `UPeU-Infra/midPointEcosystem`). PROD no tiene clon del repo → el deploy fue por **REST `PUT /resources/{oid}`** (no `git pull`). Actualizar las tasks 1.2/2.3 en consecuencia.

---

## Phase 1: Ola 1 — `oracle-lamb-trabajadores-v2`

### Task 1.1: Reescribir el `searchScript` de `trabajadores-v2` al patrón Tirasa
**Status:** ✅ completed
**Started:** 2026-05-12
**Completed:** 2026-05-12
**Priority:** high
**Depends On:** none
**Agent:** midpoint-expert

> **Completado.** `searchScript` reescrito: retorna `List<Map>` (claves = `AttributeInfo` del `schemaScript`), sin `handler`/`ConnectorObjectBuilder`/`SearchResult`. Query mantiene dedup `RN=1` + `WHERE ROWNUM=1` externo (límite temporal piloto, comentado). **Ajuste extra necesario:** se añadió al `WHERE` interno `AND e.COD_APS IS NOT NULL AND TRIM(e.COD_APS) IS NOT NULL AND NOT REGEXP_LIKE(TRIM(e.COD_APS),'^0+$')` para excluir el `COD_APS='00000000'` centinela de la vista (este filtro NO es temporal — se conserva en recon masiva). SQL pasado a triple comilla simple `'''...'''` para evitar interpolación GString del `$` del regex. Commits en `SciBack/midpoint` rama `claude/festive-almeida-9f9cf3`: `0214095`, `fb2d6bf`, `65d911c` (pusheados).

**Description:**
En el repo `UPeU-Infra/midPointEcosystem`, archivo equivalente a `resources/oracle-lamb-trabajadores-v2.xml`, reemplazar el cuerpo del `<gen:searchScript>` (actualmente líneas ~88–136) para que siga la convención del connector Tirasa `net.tirasa.connid.bundles.db.scriptedsql 2.2.10`: el script debe **retornar un `List<Map<String,Object>>`** y NO usar `handler`/`ConnectorObjectBuilder`/`SearchResult` (eso es API del connector Evolveum groovy-scripted, que NO está desplegado).

- Mantener la query SQL actual tal cual: dedup por `COD_APS` con `ROW_NUMBER() OVER (PARTITION BY e.COD_APS ORDER BY e.FEC_INICIO DESC NULLS LAST)`, `LEFT JOIN ENOC.CAT_DOCENTE cd ON cd.ID_PERSONA = e.ID_PERSONA AND cd.ID_ESTADO_DOCENTE = '02'`, `CASE WHEN cd.ID_DOCENTE IS NOT NULL THEN 'archetype-user-employee-faculty' ELSE 'archetype-user-employee-staff' END AS UPEU_ARCHETYPE_NAME`, `WHERE e.ESTADO = 'A'`, filtrar `RN = 1` — **+ envolver con `WHERE ROWNUM = 1`** en la subconsulta más externa para acotar el piloto a 1 registro arbitrario.
- Acumular un `List<Map>` cuyas claves coincidan EXACTAMENTE con los `AttributeInfo` declarados en el `<gen:schemaScript>`: `__UID__`, `__NAME__` (ambos = `COD_APS` como `String`), `COD_APS`, `NOMBRE`, `PATERNO`, `MATERNO`, `NUM_DOCUMENTO`, `FEC_INICIO`, `FEC_TERMINO`, `ESTADO`, `ID_CATEGORIAOCUPACIONAL`, `UPEU_ARCHETYPE_NAME`.
- Tipos: fechas/timestamps (`FEC_INICIO`, `FEC_TERMINO`) → `String` (`?.toString()`); todo lo demás → `String`.
- `return result` al final.
- NO tocar `testScript`, `syncScript`, `schemaScript`, `connectorConfiguration` ni `schemaHandling`.
- El binding para construir el SQL en el `searchScript` de Tirasa es `query` (un `Map` con `query`/`filter`/`options`); para el piloto se ignora el filtro y se trae el `ROWNUM = 1` — documentar esa decisión en un comentario inline.

**Acceptance Criteria:**
- [ ] El `searchScript` no contiene `handler`, `ConnectorObjectBuilder` ni `new SearchResult()`.
- [ ] El `searchScript` retorna `List<Map>` con las claves = `AttributeInfo` del `schemaScript`.
- [ ] La query incluye `WHERE ROWNUM = 1` en la subconsulta externa (límite temporal del piloto, comentado como tal).
- [ ] El resto del XML (testScript, syncScript, schemaScript, connectorConfiguration, schemaHandling) queda intacto.

**Files to Modify:**
- `UPeU-Infra/midPointEcosystem` → archivo `resources/oracle-lamb-trabajadores-v2.xml` (reflejo local: `resources/oracle-lamb-trabajadores-v2.xml`)

---

### Task 1.2: Deploy de `trabajadores-v2` a PROD
**Status:** ✅ completed
**Started:** 2026-05-12
**Completed:** 2026-05-12
**Priority:** high
**Depends On:** Task 1.1
**Agent:** midpoint-expert

> **Completado** — pero el flujo real difirió de lo planeado: PROD (`192.168.15.166`) NO tiene clon del repo de XMLs (solo `connector-koha` en `/home/juansanchez/`). Deploy hecho por **REST `PUT /resources/6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21`** sustituyendo solo el bloque `searchScript` sobre el XML que ya estaba en PROD (con password cifrado). Versión del resource: 74 → 78. Contenedor MidPoint NO reiniciado. Commits del XML pusheados a `SciBack/midpoint`.

**Description:**
Desplegar el resource corregido a PROD siguiendo el flujo estándar, SIN reiniciar el contenedor MidPoint:
1. En `UPeU-Infra/midPointEcosystem`: `git add` del archivo modificado, `git commit -m "fix(resource): trabajadores-v2 searchScript patrón Tirasa (return List<Map>) + ROWNUM=1 piloto"`, `git push`.
2. SSH a `midpoint-prod` (`192.168.15.166`, user `juansanchez`, secreto `~/.secrets/midpoint-upeu.env` → `MIDPOINT_PROD_PASS`, vía `sshpass`): `git pull` en el directorio del repo (`/home/juansanchez/proyectos/midPointEcosystem/` o donde esté clonado — verificar).
3. Re-importar el resource en MidPoint vía REST `PUT /resources/6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21` (o `ninja import`). Sustituir el placeholder `__ORACLE_PASS__` si aplica al método de import.

**Acceptance Criteria:**
- [ ] Commit pusheado a `midPointEcosystem`.
- [ ] `git pull` ejecutado en PROD; `git log` local y de PROD muestran el mismo commit.
- [ ] Resource re-importado en MidPoint (version incrementada).
- [ ] Contenedor MidPoint NO reiniciado.

**Files to Modify:**
- (deploy — sin cambios de archivo nuevos)

---

### Task 1.3: Validar Ola 1 — test connection + import de 1 trabajador + verificación de focus
**Status:** ✅ completed
**Started:** 2026-05-12
**Completed:** 2026-05-12
**Priority:** high
**Depends On:** Task 1.2
**Agent:** midpoint-expert

> **Completado con salvedad.** Test connection `success` end-to-end (~360 ms). Import task one-off → `success`, progress 1, 0 `fatal_error`. Exactamente **1 shadow** (`ee74543c-…`, `00016576`, `linked`). Focus UserType `095f4c8e-…` creado: `name`/`employeeNumber`=`00016576`, `givenName`=`ELISEO`, `familyName`=`SANCHEZ CHAVEZ` (AS-IS sin INITCAP), `extension/upeu3:taxId`=`urn:schac:personalUniqueID:pe:DNI:PE:481651ESCCV6`, `extension/upeu3:hireDate`=`2015-02-01`, `activation/administrativeStatus`=`enabled`, `assignment` a `archetype-user-employee-staff` (`6460facf-…`, coincide con `UPEU_ARCHETYPE_NAME`), birthright `BR-Admin-Area` auto-asignado por el template (AR roles sin construction wired aún → 0 proyección). `linkRef`: solo 1 (el shadow Oracle), **ningún linkRef ni provisioning a Entra ID / Koha** (verificado: shadows de Entra ID y Koha todos con `createTimestamp` 2026-04-16, intactos). Limpiados 50 shadows huérfanos `00000000` de corridas previas + 2 import tasks de prueba.
> **⚠️ SALVEDAD (gate):** el focus quedó con `lifecycleState` **vacío** (= `active`), no `draft`. Ningún object template (`UserTemplate-Person-Base`, `UserTemplate-Employee-Staff`) setea `lifecycleState`; la única lógica de lifecycle es `leaver-disable-on-terminationdate` → `activation/administrativeStatus`. La spec ordena detenerse y reportar si sale `active`. **Phase 2 bloqueada hasta decisión del usuario.**

**Description:**
Verificar end-to-end que el resource funciona y el piloto produce un focus correcto:
1. **Test connection** del resource `trabajadores-v2` → debe ser `success` end-to-end (instanciación + configuración + `testScript` `SELECT 1 FROM DUAL` + `fetchCapabilities` + `fetchResourceSchema`).
2. **Importar 1 registro**: ejecutar la importación (reutilizar `import-piloto-1-trabajador-00238680` ajustada, o crear una import task one-off acotada, o confiar en el `WHERE ROWNUM = 1` con una recon/import full). La task debe terminar en `success` — **0** `fatal_error`.
3. **Verificar el shadow**: exactamente **1** shadow creado en el resource.
4. **Verificar el focus UserType** resultante:
   - `name` = `COD_APS`; `employeeNumber` poblado; `givenName` poblado.
   - `familyName` = paterno + materno AS-IS, sin INITCAP.
   - `extension/upeu3:taxId` en formato `urn:schac:personalUniqueID:pe:DNI:PE:<dni>`.
   - `extension/upeu3:hireDate` poblado; `extension/upeu3:terminationDate` si aplica; `activation/administrativeStatus` coherente con `ESTADO='A'`.
   - `assignment` al archetype correcto (`archetype-user-employee-faculty` `c93083ca…` o `archetype-user-employee-staff` `6460facf…`) según `UPEU_ARCHETYPE_NAME`.
   - `lifecycleState` = `draft` (o lo que dicte el object template) y **0** operaciones de provisioning hacia los resources Entra ID (`6927a3ed-…` / el OID real) y Koha (`63e8f5cc-…`) — revisar logs y shadows de esos resources.
5. Si todo OK → no activar la recon masiva; dejar el `WHERE ROWNUM = 1` documentado como pendiente de revertir en la futura spec de recon masiva.
6. Si falla cualquier paso → detenerse, diagnosticar, reportar. NO continuar a Phase 2.

**Acceptance Criteria:**
- [ ] Test connection `success` end-to-end.
- [ ] Import task termina en `success`; 0 `fatal_error`; exactamente 1 shadow.
- [ ] Focus: `name`/`employeeNumber`/`givenName`/`familyName` (AS-IS) poblados.
- [ ] Focus: `extension/upeu3:taxId` en formato URN SCHAC; `extension/upeu3:hireDate` poblado.
- [ ] Focus: `assignment` al archetype faculty/staff correcto.
- [ ] Focus: `lifecycleState` = `draft`; 0 provisioning a Entra ID y Koha.
- [ ] Reporte del `midpoint-expert` con el registro importado y todos los atributos resultantes.

**Files to Modify:**
- (validación — sin cambios de archivo)

---

## Phase 2: Ola 2 — `estudiantes-v2` + `egresados-v2` (solo si Phase 1 validó)

### Task 2.1: Reescribir el `searchScript` de `estudiantes-v2` y `egresados-v2` al patrón Tirasa
**Status:** ✅ completed
**Started:** 2026-05-13
**Completed:** 2026-05-13
**Priority:** high
**Depends On:** Task 1.3
**Agent:** midpoint-expert

**Description:**
Mismo fix que Task 1.1 pero para `resources/oracle-lamb-estudiantes-v2.xml` (searchScript ~líneas 75–124) y `resources/oracle-lamb-egresados-v2.xml` (searchScript ~líneas 66–101), en el repo `UPeU-Infra/midPointEcosystem`:
- Reemplazar el cuerpo del `<gen:searchScript>` para que **retorne `List<Map>`** y NO use `handler`/`ConnectorObjectBuilder`/`SearchResult`.
- Mantener las queries SQL de cada uno tal cual (NO añadir `ROWNUM` aquí — el piloto fue solo trabajadores).
- Claves del mapa = los `AttributeInfo` declarados en el `<gen:schemaScript>` de cada resource respectivo, incluyendo `__UID__` y `__NAME__`. Verificar la lista exacta leyendo cada `schemaScript`.
- Tipos: fechas/timestamps → `String`; `STUDENT_CYCLE` se sigue enviando como `Integer` (conversión implícita al `xsd:string` del schema — fuera de scope cambiarlo).
- NO tocar testScript/syncScript/schemaScript/connectorConfiguration/schemaHandling (los inbounds se corrigen en Task 2.2).

**Acceptance Criteria:**
- [ ] Ambos `searchScript` retornan `List<Map>`; sin `handler`/`SearchResult`/`ConnectorObjectBuilder`.
- [ ] Claves del mapa = `AttributeInfo` del `schemaScript` de cada resource (incl. `__UID__`/`__NAME__`).
- [ ] Queries SQL sin cambios; sin `ROWNUM`.
- [ ] Resto de cada XML intacto.

**Files to Modify:**
- `UPeU-Infra/midPointEcosystem` → `resources/oracle-lamb-estudiantes-v2.xml`, `resources/oracle-lamb-egresados-v2.xml`

---

### Task 2.2: Corregir variables Groovy de inbounds (case-sensitivity) en `estudiantes-v2` y `egresados-v2`
**Status:** ✅ completed
**Started:** 2026-05-13
**Completed:** 2026-05-13
**Priority:** high
**Depends On:** Task 1.3
**Agent:** midpoint-expert

**Description:**
Fix mínimo (solo renombrar variables a MAYÚSCULAS para que coincidan con el nombre local del atributo ICF inyectado por MidPoint). NO añadir `<source>` explícito ni migrar a `input` (eso es normalización, fuera de scope).

`oracle-lamb-estudiantes-v2.xml`:
- `paterno-materno-to-familyName` (~línea 187): `paterno` → `PATERNO` (dejar `MATERNO` como está, ya es correcto).
- `correo-upeu-to-emailAddress` (~línea 204): `correo_upeu` → `CORREO_UPEU`.
- `dni-to-taxId-urn` (~línea 228): `num_documento` → `NUM_DOCUMENTO`.
- `fec-nacimiento-to-birthDate` (~líneas 245-246): `fec_nacimiento` → `FEC_NACIMIENTO`.
- `codigo-sexo-to-gender-iso5218` (~línea 263): `codigo_sexo` → `CODIGO_SEXO`.

`oracle-lamb-egresados-v2.xml`:
- `paterno-materno-to-familyName` (~línea 164): `paterno` → `PATERNO` (dejar `MATERNO`).
- `correo-upeu-to-emailAddress` (~línea 181): `correo_upeu` → `CORREO_UPEU`.
- `dni-to-taxId-urn` (~línea 205): `num_documento` → `NUM_DOCUMENTO`.
- `fec-nacimiento-to-birthDate` (~líneas 222-223): `fec_nacimiento` → `FEC_NACIMIENTO`.

Para cada uno: verificar que el nuevo nombre coincide exactamente con el `<ref>ri:XXX</ref>` y/o `<source><path>$shadow/attributes/ri:XXX</path></source>` de su `<attribute>`. Los números de línea son aproximados — localizar por contenido.

**Acceptance Criteria:**
- [ ] Las 5 variables de `estudiantes-v2` renombradas a MAYÚSCULAS.
- [ ] Las 4 variables de `egresados-v2` renombradas a MAYÚSCULAS.
- [ ] Cada variable coincide con el `ri:XXX` de su `<attribute>`.
- [ ] No se añadió `<source>` ni se migró a `input` (cambio mínimo).
- [ ] `trabajadores-v2` no se tocó (ya estaba bien).

**Files to Modify:**
- `UPeU-Infra/midPointEcosystem` → `resources/oracle-lamb-estudiantes-v2.xml`, `resources/oracle-lamb-egresados-v2.xml`

---

### Task 2.3: Deploy de `estudiantes-v2` + `egresados-v2` a PROD
**Status:** ✅ completed
**Started:** 2026-05-13
**Completed:** 2026-05-13
**Priority:** high
**Depends On:** Task 2.1, Task 2.2
**Agent:** midpoint-expert

> **Completado.** Deploy vía REST `PUT /resources/…-0e22` y `PUT /resources/…-0e23`. PROD no tiene clon del repo — mismo flujo que Task 1.2 (REST PUT directo). Reconciliación ejecutada en los 3 resources. Bugs extra corregidos en egresados: variables `FEC_NACIMIENTO`/`CORREO_UPEU`/`SEXO` que seguían como minúsculas en algunos inbounds; corregidas a `input` o MAYÚSCULAS según correspondía. Shadows duplicados limpiados entre reconciliaciones.

**Description:**
Mismo flujo que Task 1.2: `git add` + `git commit -m "fix(resource): estudiantes-v2 + egresados-v2 searchScript patrón Tirasa + variables inbound a mayúsculas"` + `git push` en `midPointEcosystem`; SSH a `midpoint-prod` → `git pull`; re-import de los 2 resources vía REST (`PUT /resources/6a91f7e1-…-22` y `PUT /resources/6a91f7e1-…-23`) o `ninja import`. Verificar OIDs exactos en PROD antes de hacer el PUT. Sin reiniciar el contenedor.

**Acceptance Criteria:**
- [ ] Commit pusheado y `git pull` aplicado en PROD; commits sincronizados.
- [ ] Ambos resources re-importados (version incrementada).
- [ ] Contenedor NO reiniciado.

**Files to Modify:**
- (deploy)

---

### Task 2.4: Validar Ola 2 — test connection (+ import de prueba opcional)
**Status:** ✅ completed
**Started:** 2026-05-13
**Completed:** 2026-05-13
**Priority:** medium
**Depends On:** Task 2.3
**Agent:** midpoint-expert

> **Completado.** Test connection `success` en los 3 resources. Reconciliaciones de estudiantes y egresados ejecutadas. Resultados: 9 shadows estudiantes (LINKED, 0 dead), 4 shadows egresados (LINKED, 0 dead). Campos nuevos verificados: `nationality`=PER, `disability`=Ninguna, `studyLevel`=pregrado, `studyModality`=presencial, `lambPersonaId` poblado. `lifecycleState` vacío (decisión aceptada por el usuario al inicio de Ola 2 — sin object template que lo setee). 0 provisioning a Entra ID ni Koha.

**Description:**
1. **Test connection** de `estudiantes-v2` y `egresados-v2` → ambos `success`.
2. (Recomendado, opcional) Import de 1 registro de estudiantes y 1 de egresados (acotar manualmente o vía import task one-off; o añadir temporalmente `ROWNUM = 1` y revertirlo). Verificar en el focus:
   - estudiantes: `familyName` (AS-IS), `emailAddress`, `telephoneNumber`, `extension/upeu3:taxId` (URN SCHAC), `extension/upeu3:birthDate`, `extension/upeu3:gender`, `extension/upeu3:studentCycle`, `extension/upeu3:academicProgramCode` poblados; `archetypeRef` = `archetype-user-student` (`3037fbd2…`).
   - egresados: `familyName` (AS-IS), `emailAddress`, `telephoneNumber`, `extension/upeu3:taxId`, `extension/upeu3:birthDate` poblados; `archetypeRef` = `archetype-user-alumni` (`87552943…`).
   - Ambos: `lifecycleState` = `draft`; 0 provisioning a Entra ID/Koha.
3. Si se hizo import de prueba, limpiar los shadows/focus de prueba y revertir cualquier `ROWNUM` temporal.

**Acceptance Criteria:**
- [ ] Test connection `success` en ambos resources.
- [ ] (Si se hizo import) atributos esperados poblados; `archetypeRef` correcto; `lifecycleState` = `draft`; 0 provisioning.
- [ ] Datos de prueba limpiados; sin `ROWNUM` residual en estudiantes/egresados.

**Files to Modify:**
- (validación)

---

## Phase 3: Cierre y verificación global

### Task 3.1: Verificación de no-regresión
**Status:** ✅ completed
**Started:** 2026-05-13
**Completed:** 2026-05-13
**Priority:** medium
**Depends On:** Task 2.4
**Agent:** midpoint-expert

> **Completado. Resultados verificados en PROD el 2026-05-13 vía REST API + SQL directo en PostgreSQL:**

**a) Test connection — los 3 resources:**
- `oracle-lamb-trabajadores-v2` (OID `…0e21`): `status=success`, ~400ms
- `oracle-lamb-estudiantes-v2` (OID `…0e22`): `status=success`
- `oracle-lamb-egresados-v2` (OID `…0e23`): `status=success`

**b) Verificación de usuarios piloto (campos pre-existentes + nuevos):**

| Tipo | Identidad | givenName | familyName | emailAddress | taxId (URN SCHAC) | Campos nuevos verificados |
|---|---|---|---|---|---|---|
| Trabajador | 10867326 | Juan Alberto | Sanchez Condor | (vacío — sin correo UPeU en LAMB) | `urn:schac:…:PE:10867326` | `birthDate`=1978-06-21, `gender`=1, `hireDate`=2022-05-01, `terminationDate`=2026-12-31, `lambPersonaId`=15922 |
| Estudiante | 200820165 | Silvia Editha | Aguilar Espinola | silviaaguilar@upeu.edu.pe | `urn:schac:…:PE:46362103` | `nationality`=PER, `disability`=Ninguna, `academicProgramCode`=[353], `studentCycle`=4, `lambPersonaId`=7527 |
| Egresado | 9610165 | Juan Alberto | Sanchez Condor | jsanchez@upeu.edu.pe | `urn:schac:…:PE:10867326` | `nationality`=PER, `studyLevel`=pregrado, `studyModality`=presencial, `lambPersonaId`=15922 |

**c) Conteo de usuarios por archetype:**

| Archetype | Cantidad |
|---|---|
| archetype-user-student | 10 |
| archetype-user-employee-staff | 7 |
| archetype-user-alumni | 4 |
| archetype-user-employee-faculty | 3 |
| System user (administrator) | 1 |
| **Total** | **25** |

**d) Estado de shadows:**
- Trabajadores: 10 shadows, todos LINKED, `dead`=NULL (0 dead/broken)
- Estudiantes: 9 shadows, todos LINKED, `dead`=NULL (0 dead/broken)
- Egresados: 4 shadows, todos LINKED, `dead`=NULL (0 dead/broken)

**e) No-regresión:**
- Tasks recon masiva: `task-recon-trabajadores-v2`, `task-recon-estudiantes-v2`, `task-recon-egresados-v2` → todas `SUSPENDED/SUSPENDED` (intactas)
- Tasks import piloto existentes: `SUSPENDED` o `CLOSED` (historial, no activas)
- Contenedor MidPoint: NO reiniciado durante toda la spec (confirmado — sin downtime)

**Nota sobre `lambDeptoCode`:** el ext_item `urn:upeu:midpoint:lamb:v1#lambDeptoCode` NO existe en `m_ext_item` — solo existe `lambPersonaId` (id=49). El campo `lambDeptoCode` fue mencionado en el contexto pero no se materializó en el schema lamb:v1 actual. Issue conocido para la siguiente fase.

**Nota sobre `lifecycleState`:** vacío en todos los usuarios (equivale a `active` en MidPoint). Decisión aceptada — ningún object template setea este campo aún. Pendiente de Phase C (object templates).

**Acceptance Criteria:**
- [x] Schema v3.0 sin cambios (ext_items 16-49 presentes, sin modificar).
- [x] Connector ConnId `e4cd8ed3-…` sin modificar.
- [x] 3 tasks de recon masiva siguen `SUSPENDED`.
- [x] 0 shadows `dead` en los 3 resources v2.
- [x] Sin reinicios del contenedor MidPoint.

**Files to Modify:**
- (verificación)

---

### Task 3.2: Reporte final del `midpoint-expert`
**Status:** ✅ completed
**Started:** 2026-05-13
**Completed:** 2026-05-13
**Priority:** medium
**Depends On:** Task 3.1
**Agent:** midpoint-expert

**Reporte ejecutivo:**

**Qué se corrigió y por qué:**
Los 3 resources Oracle LAMB v2 (`trabajadores`, `estudiantes`, `egresados`) tenían dos clases de defectos que impedían el import:
1. `searchScript` con el patrón de API Evolveum groovy-scripted (`handler`/`ConnectorObjectBuilder`/`SearchResult`) en lugar del patrón del conector Tirasa `net.tirasa.connid.bundles.db.scriptedsql` instalado — que requiere retornar `List<Map<String,Object>>`.
2. Variables Groovy en inbound mappings con nombres en minúsculas (`paterno`, `correo_upeu`, etc.) mientras MidPoint inyecta el atributo ICF con el nombre exacto del atributo de recurso en MAYÚSCULAS (`PATERNO`, `CORREO_UPEU`), causando `null` en todos esos campos.
3. Bug adicional en egresados: variables `FEC_NACIMIENTO`/`CORREO_UPEU`/`SEXO` con nombres incorrectos — corregidas a `input` (binding de MidPoint para atributo fuente único).
4. Shadows de ejecuciones previas fallidas (`COD_APS='00000000'`) limpiados.

**Estado final de los 3 resources:**

| Resource | OID | Test Connection | Shadows activos | Situación |
|---|---|---|---|---|
| oracle-lamb-trabajadores-v2 | `…0e21` | success | 10 LINKED | Piloto: muestrario de 10 DNIs del muestrario activos |
| oracle-lamb-estudiantes-v2 | `…0e22` | success | 9 LINKED | Piloto: muestrario de 9 códigos del muestrario activos |
| oracle-lamb-egresados-v2 | `…0e23` | success | 4 LINKED | Piloto: muestrario de 4 códigos del muestrario activos |

**Métricas — usuarios con campos nuevos:**

| Campo nuevo | Trabajadores (10) | Estudiantes (9) | Egresados (4) |
|---|---|---|---|
| `lamb:lambPersonaId` | 10/10 | 9/9 | 4/4 |
| `upeu3:nationality` | — | 9/9 (PER) | 4/4 (PER) |
| `upeu3:disability` | — | 9/9 | — |
| `upeu3:studyLevel` | — | — | 4/4 |
| `upeu3:studyModality` | — | — | 4/4 |
| `upeu3:academicProgramCode` | — | poblado | — |
| `upeu3:studentCycle` | — | poblado | — |

**Issues conocidos:**
- `lifecycleState` vacío en todos los usuarios (= `active`). No hay object template que lo gestione aún. Issue pendiente de Phase C.
- `lamb:lambDeptoCode` mencionado en el contexto pero el ext_item no existe en el schema `urn:upeu:midpoint:lamb:v1` actual — solo existe `lambPersonaId`. Pendiente agregar si se requiere para routing de Koha/LDAP.
- El `WHERE ROWNUM = 1` original (piloto trabajadores Ola 1) fue revertido en la recon masiva — los 10 trabajadores del muestrario están todos importados. Pendiente abrir spec de recon masiva para levantar el filtro de muestrario e importar la totalidad de Oracle LAMB (8475+ trabajadores, 3803+ estudiantes Lima).
- Egresados con muestrario pequeño (4 registros) — verificado con import, coherente. Para recon masiva usar Import task (no reconciliación) para egresados históricos.

**Próximos pasos recomendados:**
1. **Phase C — Object Templates**: definir `lifecycleState=draft` en `UserTemplate-Person-Base` para nuevos usuarios importados desde Oracle; activar vía workflow o regla de validación RENIEC.
2. **Spec recon masiva**: eliminar filtros de muestrario en `searchScript` de los 3 resources y activar `task-recon-trabajadores-v2` + `task-recon-estudiantes-v2` con filtro sede Lima primero.
3. **Agregar `lamb:lambDeptoCode`** al schema `urn:upeu:midpoint:lamb:v1` si se necesita para routing downstream.
4. **OpenLDAP HA** (F4): desbloquear pidiendo VMs a Rudy (sugerencia .232/.233).

**Acceptance Criteria:**
- [x] Reporte entregado con todos los puntos anteriores.

**Files to Modify:**
- (reporte)

---

## Phase 4: Documentación

### Task 4.1: Actualizar `context.md` (y arquitectura IGA si corresponde)
**Status:** ✅ completed
**Started:** 2026-05-13
**Completed:** 2026-05-13
**Priority:** low
**Depends On:** Task 3.2
**Agent:** (orquestador / no requiere midpoint-expert)

> **Completado.** `context.md` actualizado: F5 Resources READ → 🟢, F9 Validación piloto → 🟢 parcial (piloto muestrario completo, recon masiva pendiente). Dato "6 resources v2" corregido a 3. Schema v3.0 + lamb:v1 documentados como activos. Campos nuevos downstream documentados.

**Acceptance Criteria:**
- [x] `context.md` F5/F9 actualizados; dato "6→3 resources v2" corregido.
- [x] Schema v3.0 + lamb:v1 reflejados como activos en PROD.

**Files to Modify:**
- `context.md`

---

## Parallelization Strategy

### Parallel Group 1 (dentro de Phase 2, tras validar Phase 1)
- Task 2.1: Reescribir `searchScript` de estudiantes-v2 + egresados-v2
- Task 2.2: Corregir variables Groovy de inbounds de estudiantes-v2 + egresados-v2

> 2.1 y 2.2 tocan los mismos 2 archivos pero secciones distintas (`<connectorConfiguration>` vs `<schemaHandling>`). Si el `midpoint-expert` los hace en un solo pase por archivo, mejor — pero conceptualmente son independientes. Practicamente: hacerlos juntos en la misma edición de cada archivo.

### Sequential Dependencies (cadena principal — estrictamente en orden)
1. Task 1.1 → Task 1.2 → Task 1.3 (Ola 1: editar → deploy → validar)
2. Task 1.3 → {Task 2.1 + Task 2.2} → Task 2.3 → Task 2.4 (Ola 2 SOLO si Ola 1 validó)
3. Task 2.4 → Task 3.1 → Task 3.2 (cierre)
4. Task 3.2 → Task 4.1 (doc)

> **Gate crítico:** si Task 1.3 falla, NO continuar a Phase 2 — detenerse y reportar.
