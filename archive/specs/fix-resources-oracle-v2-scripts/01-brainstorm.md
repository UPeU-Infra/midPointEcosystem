# Fix de searchScript / inbounds en los 3 resources Oracle LAMB v2

**Slug:** fix-resources-oracle-v2-scripts
**Author:** Claude Code
**Date:** 2026-05-12
**Branch:** preflight/fix-resources-oracle-v2-scripts
**Related:** `context.md` (Snapshot 2026-05-12, F5/F9), commit `8c53d0d` (fix parcial trabajadores-v2), spec `midpoint-prod-upeu`

---

## 1) Intent & Assumptions

- **Task brief:** Corregir los scripts Groovy de los 3 resources Oracle LAMB v2 en MidPoint PROD para que la reconciliación funcione:
  1. **`oracle-lamb-trabajadores-v2.xml`** — el `searchScript` usa el patrón del connector *Evolveum groovy-scripted* (`handler.handle(cob.build())` + `return new SearchResult()`) cuando el connector desplegado es *Tirasa* `net.tirasa.connid.bundles.db.scriptedsql 2.2.10`, que en `executeQuery()` espera que el `searchScript` **retorne un `List<Map<String,Object>>`** y construye él mismo los `ConnectorObject`. Resultado actual: `MissingPropertyException: No such property: handler` → `ConnectorException: Search script error`.
  2. **`oracle-lamb-estudiantes-v2.xml` y `oracle-lamb-egresados-v2.xml`** — los `searchScript` tienen el **mismo bug `handler.handle()`**, y además los `<inbound>` con `<expression><script>` referencian variables Groovy en minúsculas (`paterno`, `correo_upeu`, `num_documento`, `fec_nacimiento`, `codigo_sexo`) cuando el atributo ICF (y por tanto la variable inyectada) está en MAYÚSCULAS (`PATERNO`, `CORREO_UPEU`, `NUM_DOCUMENTO`, `FEC_NACIMIENTO`, `CODIGO_SEXO`). `trabajadores-v2` NO tiene este segundo bug.
- **Objetivo final:** dejar los 3 resources listos para reconciliación y re-probar el piloto de importación de **1 solo trabajador**.
- **Assumptions:**
  - El único ambiente es PROD (`192.168.15.166`, user `juansanchez`). No hay DEV→PROD para este proyecto.
  - Los XMLs canónicos viven en `UPeU-Infra/midPointEcosystem`; el worktree actual (`resources/oracle-lamb-*-v2.xml`) refleja ese repo y coincide byte-relevante con lo desplegado en PROD (auditoría 2026-05-12 confirmó solo diferencias cosméticas).
  - El connector Tirasa `net.tirasa.connid.bundles.db.scriptedsql 2.2.10` se queda; ya está desplegado, el `schemaScript` ya sigue su convención (mutar `builder`), `ojdbc11` ya está cargado, y la conectividad Oracle real está verificada (test connection `success`, round-trip ~424 ms).
  - Todo el trabajo técnico (escritura/edición de XML, deploy, ninja/REST, troubleshooting) se delega al sub-agente `midpoint-expert`, que consulta `iga-canonical-standards` + `midpoint-best-practices` antes de proponer cambios.
- **Out of scope:**
  - Resources Oracle "v1" (`oracle-lamb-trabajadores.xml` / `-estudiantes.xml` / `-egresados.xml`) — son la generación previa (DatabaseTable→ScriptedSQL); no se tocan en esta spec (ver Clarificación #6).
  - OpenLDAP HA (F4), Resources WRITE (F6), gobierno Entra ID (F12).
  - Eliminar el resource Keycloak legacy (`a3f9c1d2-...`) — tarea aparte ya priorizada en `context.md`.
  - Decidir la fuente Lamb (IIA) de los atributos de extensión sin alimentar todavía (`country`, `province`, `personalWeb`, `languageSkills`, `studyModality`, `institutionalIdCard`).
  - Reconciliación masiva / activar `task-recon-trabajadores-v2` — esta spec solo re-prueba con 1 registro.

## 2) Pre-reading Log

- `context.md` (Snapshot 2026-05-12): F5 "Resources READ" en 🟡 — 6 resources Oracle ScriptedSQL v2 declarados, tasks suspended, "listo para activar" tras abrir firewall. F9 piloto sin usuarios reales. Bloqueante B-NET resuelto. → el piloto está bloqueado por código, no por infra.
- `resources/oracle-lamb-trabajadores-v2.xml`: connector `e4cd8ed3-...` (Tirasa scriptedsql). `searchScript` líneas 88–136 usa `ConnectorObjectBuilder` + `handler.handle()` + `return new SearchResult()`. `schemaScript` líneas 141–177 SÍ sigue convención Tirasa (muta `builder`, retorno ignorado) — comentario inline lo documenta. `reloadScriptOnExecution=false` (workaround de otro bug Tirasa ya aplicado). Inbounds (líneas ~200–379): usan variables en MAYÚSCULAS correctamente (`PATERNO`, `MATERNO`...). `assignmentTargetSearch` de archetype por `name` desde columna `UPEU_ARCHETYPE_NAME` (CASE WHEN en la query).
- `resources/oracle-lamb-estudiantes-v2.xml`: `searchScript` líneas 75–124 con el mismo bug `handler.handle()` (líneas 102/121/123). Inbounds con bug de case: línea 187 `paterno` (debería `PATERNO`; `MATERNO` en línea 188 sí está bien), línea 204 `correo_upeu`, línea 228 `num_documento`, línea 245-246 `fec_nacimiento`, línea 263 `codigo_sexo`. Source paths declarados como `$shadow/attributes/ri:PATERNO` etc.; el mapping `correo-upeu-to-emailAddress` (líneas 199–208) NO declara `<source>` explícito (usa el `<ref>ri:CORREO_UPEU</ref>` como fuente implícita). `archetypeRef` estático `3037fbd2-...` (archetype-user-student). `studentCycle` se envía como `Integer` aunque el schema v3.0 lo declara `xsd:string`.
- `resources/oracle-lamb-egresados-v2.xml`: `searchScript` líneas 66–101 con bug `handler.handle()` (líneas 87/98/100). Inbounds con bug de case: línea 164 `paterno`, línea 181 `correo_upeu`, línea 205 `num_documento`, línea 222-223 `fec_nacimiento`. `archetypeRef` estático `87552943-...` (archetype-user-alumni).
- Schema v3.0 (`b7d55017-...`, namespace `urn:upeu:midpoint:person:v3`, prefijo `upeu3:`): 12 items de extensión, todos `xsd:string`, 5 ComplexTypes (Demographics, EmploymentData, AcademicStatus, ContactExt, PeruvianIdentifiers). Auditoría confirmó: **todos los paths `extension/upeu3:*` referenciados por los resources existen en el schema** → no hay desalineamiento de schema; el problema es exclusivamente de scripts.
- Hallazgo de inventario: en PROD hay **3 resources Oracle v2, no 6** (REST `/resources`: Trabajadores v2, Estudiantes v2, Egresados v2 + Koha + EntraID). `context.md` dice "6" — desfasado (cuenta los 3 v1 + 3 v2).

## 3) Codebase Map

- **Componentes primarios a modificar:**
  - `resources/oracle-lamb-trabajadores-v2.xml` — solo `searchScript` (líneas ~88–136).
  - `resources/oracle-lamb-estudiantes-v2.xml` — `searchScript` (~75–124) + 5 inbounds con bug de case.
  - `resources/oracle-lamb-egresados-v2.xml` — `searchScript` (~66–101) + 4 inbounds con bug de case.
- **Fuente de verdad del XML:** repo `UPeU-Infra/midPointEcosystem` (no este worktree). Flujo: editar en el repo → commit → push → `git pull` en PROD → re-importar resource vía REST `PUT /resources/{oid}` o `ninja import`.
- **Dependencias compartidas:**
  - Connector ConnId `net.tirasa.connid.bundles.db.scriptedsql 2.2.10` (OID `e4cd8ed3-2e91-48d9-abb7-32090a5e8849`) + `ojdbc11-23.6.0.24.10.jar` en `/opt/midpoint/var/lib/`.
  - Schema extension v3.0 (`b7d55017-...`) — no se toca.
  - Object templates por archetype (`00-common-base.xml` + `01-student.xml` + `02-employee-faculty.xml` + `03-employee-staff.xml` + `06-alumni.xml`) — consumen los atributos que pueblan estos inbounds; no se tocan pero hay que verificar end-to-end que reciben valor tras el fix.
  - Archetypes: `archetype-user-employee-faculty` (`c93083ca...`), `archetype-user-employee-staff` (`6460facf...`), `archetype-user-student` (`3037fbd2...`), `archetype-user-alumni` (`87552943...`).
  - Vistas Oracle (solo lectura): `ELISEO.VW_APS_EMPLEADO`, `ENOC.CAT_DOCENTE` (trabajadores); las de estudiantes/egresados según sus queries.
- **Data flow:** Oracle LAMB (vistas) → `searchScript` Groovy → ConnId ConnectorObject → MidPoint shadow → inbound mappings → focus UserType (draft/active según template) → [futuro: outbound a Entra ID / Koha].
- **Feature flags / config:** `reloadScriptOnExecution=false`, `rethrowAllSQLExceptions=true`, `nativeTimestamps=true`, capabilities create/update/delete=disabled (resource inbound-only). `lifecycleState=active`.
- **Tasks relacionadas (todas suspended):** `task-recon-trabajadores-v2` (`6a91f7e1-...-0e31`), `task-recon-estudiantes-v2` (`...-0e32`), `task-recon-egresados-v2` (`...-0e33`), más una `import-piloto-1-trabajador-00238680` (suspended + fatal_error) y `import-piloto-full-trabajadores-v2`. Esta spec NO activa ninguna masiva.
- **Blast radius:** acotado. Cambiar `searchScript` solo afecta búsqueda/reconciliación del resource; cambiar variables de inbounds solo afecta el populado de focus en esa reconciliación. Riesgo principal: una vez que la reconciliación funcione y traiga registros con `lifecycleState` que dispare provisioning, podría propagar a Entra ID / Koha — por eso el piloto se limita a 1 registro y hay que verificar el lifecycle resultante antes de escalar.

## 4) Root Cause Analysis

### Bug A — `searchScript` con patrón de connector equivocado (los 3 resources)

- **Repro:**
  1. Activar/ejecutar una import task acotada contra `oracle-lamb-trabajadores-v2` (p.ej. `import-piloto-1-trabajador-00238680`, o una one-off por REST).
  2. La task pasa a `fatal_error`.
  3. Log: `groovy.lang.MissingPropertyException: No such property: handler for class: Script1` envuelto en `org.identityconnectors.framework.common.exceptions.ConnectorException: Search script error`.
- **Observado vs esperado:** Observado → el `searchScript` aborta porque referencia un binding `handler` inexistente. Esperado → el script devuelve filas y MidPoint crea/actualiza shadows.
- **Evidencia:** decompilación del bundle `net.tirasa.connid.bundles.db.scriptedsql-2.2.10-bundle.jar` (en `/opt/midpoint/var/icf-connectors/`) por el sub-agente: en `executeQuery()` el connector ejecuta el `searchScript` y luego llama `processResults(...)` esperando que el script **retorne** un `List<Map<String,Object>>`; el binding disponible para construir el SQL es `query` (un `Map` con `query`/`filter`/`options`), **no** un `handler` ni un `ConnectorObjectBuilder`. El `schemaScript` del mismo XML ya documenta y respeta la convención Tirasa (mutar `builder`), lo que confirma que el resource fue escrito para Tirasa y el `searchScript` quedó con un patrón ajeno (copiado del connector Evolveum groovy-scripted, que SÍ expone `handler` y `SearchResult`).
- **Root-cause hypotheses:**
  - **(H1, alta)** El `searchScript` fue escrito con la API del connector `com.evolveum.polygon.connector.scripted.sql` (o el genérico groovy-scripted), pero el resource referencia el connector Tirasa. → confirmado por decompilación.
  - (H2, baja) Versión del connector incorrecta. → descartado: el bundle desplegado es el referenciado en el `connectorRef`.
- **Decisión:** adoptar H1. El fix correcto es reescribir el `searchScript` para que **arme el SQL a partir del binding `query` y retorne `List<Map>`** siguiendo la convención Tirasa, sin tocar el connector (alternativa de cambiar de connector evaluada en §5, descartada).

### Bug B — variables Groovy en minúsculas en inbounds de estudiantes/egresados

- **Repro:** (solo observable una vez resuelto el Bug A) ejecutar reconciliación de estudiantes/egresados → los inbounds con `<script>` que usan `paterno`/`correo_upeu`/`num_documento`/`fec_nacimiento`/`codigo_sexo` fallan o producen `null`.
- **Observado vs esperado:** Observado → `familyName` quedaría solo con el materno (o vacío); `emailAddress`, `extension/upeu3:taxId`, `extension/upeu3:birthDate`, `extension/upeu3:gender` quedarían sin valor. Esperado → todos poblados.
- **Evidencia:** los `<source>` declaran `$shadow/attributes/ri:PATERNO`, etc. → MidPoint inyecta la variable con el **nombre local del atributo ICF en mayúsculas** (`PATERNO`). El script usa `paterno` (minúscula) → variable indefinida. En `trabajadores-v2` los scripts usan correctamente las mayúsculas, lo que evidencia que el bug se introdujo solo al clonar el patrón a estudiantes/egresados. Caso especial: `correo-upeu-to-emailAddress` no declara `<source>` explícito (usa `<ref>ri:CORREO_UPEU</ref>` como fuente implícita) → el nombre de variable disponible podría ser `CORREO_UPEU` o `input`; conviene normalizar (ver Clarificación #3).
- **Decisión:** renombrar las variables a MAYÚSCULAS para que coincidan con el nombre del atributo ICF; opcionalmente añadir `<source>` explícito donde falta y/o usar `input` cuando el mapping tenga una sola fuente. Decisión fina del estilo → Clarificación #3.

### Observación C (no-bug) — `studentCycle` declarado `xsd:string` pero tratado como `Integer`

- El `searchScript` de estudiantes envía `STUDENT_CYCLE` como `Integer` y `01-student.xml` lo trata como Integer (`.max() as Integer`); el schema v3.0 lo declara `xsd:string`. MidPoint hace conversión implícita → funciona. No bloquea. Solo se documenta (ver Clarificación #5).

## 5) Research

Investigación interna (decompilación del bundle + docs Evolveum + skills `iga-canonical-standards`/`midpoint-best-practices`); no se requiere librería externa.

- **Solución 1 — Reescribir el `searchScript` para la convención Tirasa (retornar `List<Map>`):**
  - *Cómo:* abrir conexión `groovy.sql.Sql`, armar el SQL (incorporando el filtro del binding `query` si MidPoint lo pasa, o ignorándolo y filtrando todo para reconciliación full), iterar `eachRow` y acumular `result << [__UID__: ..., __NAME__: ..., COD_APS: ..., NOMBRE: ..., ...]`, `return result`. Las claves del mapa deben coincidir con los `AttributeInfo` declarados en el `schemaScript` (incluye `__UID__`/`__NAME__`).
  - *Pros:* cambio mínimo, no toca connector ni infra; consistente con el `schemaScript` ya escrito para Tirasa; patrón de referencia ya redactado por el sub-agente.
  - *Contras:* hay que manejar correctamente el binding `query` (filtros de import por `attributes/ri:COD_APS` deben resolverse en el script o en la query de la task); requiere cuidado con tipos (`Date`/`Timestamp` → `String`).
- **Solución 2 — Cambiar el `connectorRef` al connector Evolveum `com.evolveum.polygon.connector.scripted.sql` (que sí expone `handler`/`SearchResult`):**
  - *Pros:* el `searchScript` actual quedaría casi como está.
  - *Contras:* hay que desplegar otro bundle en `/opt/midpoint/var/icf-connectors/`, reescribir el `schemaScript` (cambia de convención), reescribir el `connectorConfiguration` (otro namespace de `configurationProperties`), revalidar `ojdbc11`, y re-testear los 3 resources desde cero. Mucho mayor blast radius para "ahorrar" la reescritura de un script. Descartado.
- **Solución 3 — `DatabaseTable` connector (sin scripting):**
  - *Contras:* es la generación v1 que ya se abandonó precisamente porque no resolvía el dedup/discriminador faculty-staff ni los JOINs (`ENOC.CAT_DOCENTE`). Retroceso. Descartado.
- **Recomendación:** **Solución 1.** Reescribir los 3 `searchScript` al patrón Tirasa (`return List<Map>`), corregir las variables en mayúsculas de los inbounds de estudiantes/egresados, mantener todo lo demás. El sub-agente `midpoint-expert` implementa, despliega vía repo `midPointEcosystem` → `git pull` en PROD → re-import, hace test connection + import de **1 registro** y verifica el focus resultante (atributos poblados + `lifecycleState` + ausencia de provisioning inesperado).

## 6) Clarification

### Decisiones tomadas (2026-05-12)

- **#2 Alcance del piloto:** un registro **arbitrario** vía `WHERE ROWNUM = 1` en la query del `searchScript` (o equivalente en la import task). No se fija un `COD_APS` concreto.
- **#7 Orden de deploy:** **trabajadores primero** — corregir y desplegar solo `oracle-lamb-trabajadores-v2`, probar el piloto de 1 registro, validar el focus resultante, y RECIÉN ENTONCES aplicar el mismo patrón a `estudiantes-v2` y `egresados-v2`. Esto parte la spec en dos olas.
- **#3 Fix de inbounds estudiantes/egresados:** **mínimo** — solo renombrar las variables Groovy a MAYÚSCULAS para que coincidan con el atributo ICF. La normalización (añadir `<source>` explícito, usar `input`) queda fuera de scope.
- **#1 Connector:** se mantiene Tirasa `scriptedsql 2.2.10` (Solución 1, asumida por defecto — no hubo objeción).
- **#5 `studentCycle` tipo:** fuera de scope; se deja con conversión implícita.
- **#6 Resources v1:** fuera de scope; tarea de limpieza posterior.
- **#8 Lifecycle esperado del piloto:** se asume `draft` y SIN provisioning a Entra ID/Koha; ése es el criterio de "verificación OK". (Confirmar al ejecutar; si sale `active` o dispara provisioning, detenerse y reportar antes de escalar.)
- **#4 `familyName` AS-IS:** se mantiene paterno+materno sin INITCAP (decisión doctrinal vigente).

### Preguntas originales (referencia)

1. **Connector — ¿confirmamos quedarnos con el Tirasa scriptedsql 2.2.10?** El plan asume que sí (Solución 1: reescribir scripts, no cambiar connector). ¿De acuerdo, o quieres evaluar migrar al connector Evolveum scripted-sql? *(Recomendación: quedarnos con Tirasa.)*

2. **Alcance del piloto post-fix — ¿cómo acotamos "1 trabajador"?** Opciones: (a) filtrar por un `COD_APS` específico en la query del `searchScript`/task (¿cuál? ¿el `00238680` que ya tenía la task piloto, o uno tuyo?); (b) `WHERE ROWNUM = 1` (registro arbitrario); (c) filtro de import task por `attributes/ri:COD_APS = <valor>` dejando el `searchScript` sin filtro. ¿Cuál prefieres y con qué `COD_APS`?

3. **Estilo del fix de los inbounds de estudiantes/egresados:** ¿solo renombrar las variables a MAYÚSCULAS (cambio mínimo), o además normalizar — añadir `<source>` explícito donde falta (p.ej. en `correo-upeu-to-emailAddress`) y usar `input` cuando el mapping tiene una sola fuente? *(Recomendación: cambio mínimo ahora — renombrar a mayúsculas — y dejar la normalización como mejora aparte.)*

4. **`familyName` AS-IS:** la auditoría confirmó que se conserva paterno+materno sin INITCAP (decisión doctrinal vigente, commit `4de9597`). Solo confirmar que esto sigue en pie y no hay que cambiar el formato (p.ej. solo paterno como apellido principal).

5. **`studentCycle` — ¿se corrige el tipo en el schema (`xsd:string` → `xsd:int`) o se deja con conversión implícita?** Fuera del alcance estricto de esta spec, pero ¿quieres que lo incluya como cambio menor o lo dejo para una revisión de schema aparte? *(Recomendación: dejarlo fuera; funciona.)*

6. **Resources Oracle v1 (`oracle-lamb-trabajadores.xml` / `-estudiantes.xml` / `-egresados.xml`):** siguen presentes en el repo (y posiblemente en PROD). ¿Se mantienen como están (fuera de scope), o aprovechamos para borrarlos/marcarlos `lifecycleState=archived` ya que los v2 los reemplazan? *(Recomendación: fuera de scope ahora; abrir tarea de limpieza después de validar el piloto v2.)*

7. **Deploy:** ¿confirmas el flujo estándar — editar en `UPeU-Infra/midPointEcosystem`, commit + push, `git pull` en `192.168.15.166`, re-import de los 3 resources vía REST, sin reiniciar el contenedor (solo refrescar el resource)? ¿O prefieres que primero se pruebe el `searchScript` corregido contra uno solo de los 3 (trabajadores) antes de tocar los otros dos?

8. **Object templates / lifecycle:** tras el fix, ¿qué `lifecycleState` esperas en el UserType importado del piloto — `draft` (sin provisioning, solo cache) o `active`? Esto define el criterio de "verificación OK" y si hay que vigilar provisioning hacia Entra ID/Koha. *(Por el pipeline documentado: el piloto debería quedar en `draft` y NO provisionar.)*
