# Especificación — Fix de searchScript / inbounds en los 3 resources Oracle LAMB v2

**Slug:** fix-resources-oracle-v2-scripts
**Author:** Claude Code
**Date:** 2026-05-12
**Branch:** preflight/fix-resources-oracle-v2-scripts
**Brainstorm:** `doc/specs/fix-resources-oracle-v2-scripts/01-brainstorm.md`
**Ejecución técnica:** delegada al sub-agente `midpoint-expert` (consulta `iga-canonical-standards` + `midpoint-best-practices` antes de cualquier decisión de diseño).

---

## 1. Objetivo

Dejar operativos los 3 resources Oracle LAMB v2 de MidPoint PROD para reconciliación, corrigiendo dos bugs de scripting Groovy, y re-probar el piloto de importación de **1 trabajador arbitrario**. El schema canónico v3.0 NO se toca (auditoría 2026-05-12 confirmó que todos los paths `extension/upeu3:*` referenciados existen).

Se ejecuta en **dos olas secuenciales**: Ola 1 valida el patrón de fix con `trabajadores-v2`; solo tras validar se aplica a `estudiantes-v2` y `egresados-v2` (Ola 2).

## 2. Contexto técnico

- **Ambiente único:** PROD `192.168.15.166`, user `juansanchez`, alias SSH `midpoint-prod`. Secretos en `~/.secrets/midpoint-upeu.env` (`MIDPOINT_PROD_PASS`). REST API en `https://identity.upeu.edu.pe`.
- **Fuente de verdad del XML:** repo `UPeU-Infra/midPointEcosystem`. Flujo de deploy: editar en el repo → commit → push → `git pull` en PROD → re-import del resource vía REST `PUT /resources/{oid}` (o `ninja import`). **Sin reiniciar el contenedor** — solo refrescar el resource. Reflejo local del repo: `resources/oracle-lamb-*-v2.xml` en este worktree.
- **Connector:** `net.tirasa.connid.bundles.db.scriptedsql 2.2.10`, OID `e4cd8ed3-2e91-48d9-abb7-32090a5e8849`. `ojdbc11-23.6.0.24.10.jar` ya cargado en `/opt/midpoint/var/lib/`. Conectividad Oracle real verificada (test connection `success`, ~424 ms). **No se cambia el connector.**
- **Resources afectados (3):**
  | Resource | Archivo | OID | Archetype destino |
  |---|---|---|---|
  | Oracle LAMB Trabajadores v2 | `resources/oracle-lamb-trabajadores-v2.xml` | `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21` | faculty (`c93083ca…`) / staff (`6460facf…`) vía `assignmentTargetSearch` por `name` desde columna `UPEU_ARCHETYPE_NAME` |
  | Oracle LAMB Estudiantes v2 | `resources/oracle-lamb-estudiantes-v2.xml` | `6a91f7e1-…-22` | `archetype-user-student` (`3037fbd2…`) estático |
  | Oracle LAMB Egresados v2 | `resources/oracle-lamb-egresados-v2.xml` | `6a91f7e1-…-23` | `archetype-user-alumni` (`87552943…`) estático |
- **Tasks de recon (todas suspended, NO se activan en esta spec):** `task-recon-trabajadores-v2` (`6a91f7e1-…-0e31`), `task-recon-estudiantes-v2` (`…-0e32`), `task-recon-egresados-v2` (`…-0e33`). Existe `import-piloto-1-trabajador-00238680` (suspended + fatal_error) — puede reutilizarse o reemplazarse para el piloto.
- **Data flow:** Oracle LAMB (vistas, solo lectura) → `searchScript` Groovy → ConnId ConnectorObject → shadow MidPoint → inbound mappings → focus UserType. Capabilities create/update/delete = disabled (resources inbound-only).
- **Blast radius:** acotado. `searchScript` afecta solo búsqueda/reconciliación; variables de inbounds afectan solo el populado del focus. Riesgo a vigilar: que un focus importado con `lifecycleState` "vivo" dispare provisioning a Entra ID / Koha — por eso el piloto se limita a 1 registro y se verifica el lifecycle antes de cualquier escalada.

## 3. Diagnóstico (resumen del brainstorm)

- **Bug A — `searchScript` con patrón de connector equivocado (los 3 resources).** Los `searchScript` usan `new ConnectorObjectBuilder()` + `handler.handle(cob.build())` + `return new SearchResult()` (API del connector Evolveum groovy-scripted). El connector desplegado es Tirasa, que en `executeQuery()` espera que el `searchScript` **retorne `List<Map<String,Object>>`** y construye él mismo los `ConnectorObject`; **no expone binding `handler`**. Síntoma: `groovy.lang.MissingPropertyException: No such property: handler` envuelto en `ConnectorException: Search script error`. (Confirmado por decompilación del bundle.) El `schemaScript` de cada XML ya sigue correctamente la convención Tirasa — solo el `searchScript` quedó con el patrón ajeno.
  - Ubicaciones: `trabajadores-v2` líneas ~88–136 (`handler.handle` en 133, `new SearchResult` en 135); `estudiantes-v2` líneas ~75–124 (102/121/123); `egresados-v2` líneas ~66–101 (87/98/100).
- **Bug B — variables Groovy en minúsculas en inbounds de `estudiantes-v2` y `egresados-v2`.** Los `<inbound>` con `<expression><script>` referencian `paterno`, `correo_upeu`, `num_documento`, `fec_nacimiento`, `codigo_sexo` cuando la variable inyectada por MidPoint lleva el nombre local del atributo ICF en MAYÚSCULAS (`PATERNO`, `CORREO_UPEU`, `NUM_DOCUMENTO`, `FEC_NACIMIENTO`, `CODIGO_SEXO`). `MATERNO` ya está bien escrito. `trabajadores-v2` NO tiene este bug.
  - Ubicaciones en `estudiantes-v2`: línea 187 (`paterno`), 204 (`correo_upeu`), 228 (`num_documento`), 245-246 (`fec_nacimiento`), 263 (`codigo_sexo`).
  - Ubicaciones en `egresados-v2`: línea 164 (`paterno`), 181 (`correo_upeu`), 205 (`num_documento`), 222-223 (`fec_nacimiento`).

## 4. Decisiones (clarificaciones resueltas)

| # | Decisión |
|---|---|
| Alcance piloto | 1 registro **arbitrario** vía `WHERE ROWNUM = 1` en la query del `searchScript` de `trabajadores-v2` (o equivalente en la import task). No se fija un `COD_APS` concreto. |
| Orden de deploy | **Trabajadores primero** (Ola 1) → validar → estudiantes + egresados (Ola 2). |
| Fix de inbounds estudiantes/egresados | **Mínimo**: solo renombrar las variables Groovy a MAYÚSCULAS. Sin normalización (no añadir `<source>` explícito, no migrar a `input`). |
| Connector | Se mantiene Tirasa `scriptedsql 2.2.10`. No se cambia. |
| `studentCycle` (tipo `xsd:string` vs `Integer`) | Fuera de scope; se deja con conversión implícita. |
| Resources Oracle v1 | Fuera de scope; tarea de limpieza posterior. |
| `familyName` AS-IS | Se mantiene paterno+materno sin INITCAP. |
| Lifecycle esperado del piloto | Se asume `draft` y SIN provisioning a Entra ID/Koha → criterio de "verificación OK". Si sale `active` o dispara provisioning: detenerse y reportar antes de escalar a Ola 2. |

## 5. Alcance

### En scope
- Reescribir el `searchScript` de los 3 resources Oracle v2 al patrón Tirasa (`return List<Map>`).
- Añadir `WHERE ROWNUM = 1` (o equivalente) a la query de `trabajadores-v2` para acotar el piloto. *(Decisión de implementación del `midpoint-expert`: si conviene más mantener el `searchScript` sin límite y acotar vía la import task, es aceptable mientras el resultado sea ≤ 1 registro importado. Documentar qué se eligió y cómo revertir el límite después del piloto.)*
- Renombrar las variables Groovy en minúsculas a MAYÚSCULAS en los inbounds de `estudiantes-v2` y `egresados-v2`.
- Deploy vía `UPeU-Infra/midPointEcosystem` → `git pull` PROD → re-import REST de los resources modificados.
- Test connection + import de 1 registro (trabajadores) + verificación del focus resultante.

### Fuera de scope
- Cambiar el connector ConnId.
- Resources Oracle v1.
- Tipo de `studentCycle` en el schema v3.0.
- Normalización de inbounds (añadir `<source>`, usar `input`).
- Activar tasks de reconciliación masiva.
- Eliminar el resource Keycloak legacy.
- Asignar IIA (fuente Lamb) a `country`/`province`/`personalWeb`/`languageSkills`/`studyModality`/`institutionalIdCard`.
- OpenLDAP HA (F4), Resources WRITE (F6), gobierno Entra ID (F12).

## 6. Plan de implementación

### Ola 1 — `oracle-lamb-trabajadores-v2`

1. **Reescribir el `searchScript`** (en `UPeU-Infra/midPointEcosystem`, archivo equivalente a `resources/oracle-lamb-trabajadores-v2.xml`):
   - Mantener la query SQL actual (dedup por `COD_APS` con `ROW_NUMBER()`, JOIN `ENOC.CAT_DOCENTE`, `CASE WHEN` para `UPEU_ARCHETYPE_NAME`, `WHERE e.ESTADO='A'`) **+ `WHERE ROWNUM = 1`** envolviendo el resultado final (para el piloto).
   - Reemplazar el cuerpo del `eachRow` para acumular un `List<Map>` cuyas claves coincidan con los `AttributeInfo` declarados en el `schemaScript`, incluyendo `__UID__` y `__NAME__` (= `COD_APS`). Tipos: fechas/timestamps → `String`.
   - `return result`. Eliminar `import org.identityconnectors.framework.common.objects.*` si ya no se usa, y `new ConnectorObjectBuilder()` / `handler.handle()` / `return new SearchResult()`.
   - No tocar `testScript`, `syncScript`, `schemaScript`, `connectorConfiguration` ni `schemaHandling`.
2. **Deploy:** `git add` + `git commit` + `git push` en `midPointEcosystem`; SSH a PROD → `git pull` en el directorio del repo; re-import del resource vía REST (`PUT /resources/6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21`) o `ninja import`. Sin reiniciar contenedor.
3. **Validación Ola 1:**
   - Test connection del resource → `success` (instanciación + `testScript` + `fetchCapabilities` + `fetchResourceSchema` OK).
   - Lanzar la importación de 1 registro (reutilizar `import-piloto-1-trabajador-00238680` ajustada, o una import task one-off acotada; o simplemente confiar en el `WHERE ROWNUM = 1`). La task debe terminar en `success` (no `fatal_error`).
   - Verificar en MidPoint el shadow creado (1) y el focus UserType resultante:
     - `name` = `COD_APS`, `employeeNumber` poblado, `givenName` poblado, `familyName` = paterno+materno AS-IS sin INITCAP.
     - `extension/upeu3:taxId` en formato `urn:schac:personalUniqueID:pe:DNI:PE:<dni>`, `extension/upeu3:hireDate`, `extension/upeu3:terminationDate` (si aplica), `activation/administrativeStatus`.
     - `assignment` al archetype correcto (faculty o staff según `UPEU_ARCHETYPE_NAME`).
     - `lifecycleState` = `draft` (o lo que dicte el object template) y **ningún provisioning a Entra ID ni Koha** (revisar logs / shadows de esos resources).
   - Si todo OK → revertir el `WHERE ROWNUM = 1` solo si se decide, o dejarlo documentado como pendiente para cuando se pase a recon masiva (esa es otra spec). **No** activar la recon masiva aquí.
   - Si falla → detenerse, diagnosticar, reportar. No pasar a Ola 2.

### Ola 2 — `oracle-lamb-estudiantes-v2` + `oracle-lamb-egresados-v2` (solo si Ola 1 validó)

4. **Reescribir el `searchScript`** de ambos al mismo patrón Tirasa (`return List<Map>`, claves = `AttributeInfo` del `schemaScript` respectivo incl. `__UID__`/`__NAME__`). Mantener sus queries SQL tal cual (no se añade `ROWNUM` aquí; el piloto fue solo trabajadores).
5. **Corregir variables Groovy de inbounds** (renombrar a MAYÚSCULAS, cambio mínimo):
   - `estudiantes-v2`: línea ~187 `paterno`→`PATERNO`; ~204 `correo_upeu`→`CORREO_UPEU`; ~228 `num_documento`→`NUM_DOCUMENTO`; ~245-246 `fec_nacimiento`→`FEC_NACIMIENTO`; ~263 `codigo_sexo`→`CODIGO_SEXO`.
   - `egresados-v2`: línea ~164 `paterno`→`PATERNO`; ~181 `correo_upeu`→`CORREO_UPEU`; ~205 `num_documento`→`NUM_DOCUMENTO`; ~222-223 `fec_nacimiento`→`FEC_NACIMIENTO`.
   - Verificar que cada nombre coincide exactamente con el `<ref>ri:XXX</ref>` / `<source><path>$shadow/attributes/ri:XXX</path></source>` de su `<attribute>`.
6. **Deploy:** mismo flujo (`midPointEcosystem` → push → `git pull` PROD → re-import de los 2 resources).
7. **Validación Ola 2:**
   - Test connection de ambos resources → `success`.
   - (Opcional pero recomendado) import de 1 registro de estudiantes y 1 de egresados; verificar que `familyName`, `emailAddress`, `extension/upeu3:taxId`, `extension/upeu3:birthDate`, `extension/upeu3:gender` (estudiantes), `extension/upeu3:studentCycle`, `extension/upeu3:academicProgramCode` quedan poblados y el `archetypeRef` correcto se asigna. `lifecycleState` = `draft`, sin provisioning.

### Cierre
8. Actualizar `context.md` (F5/F9) y, si corresponde, el archivo de arquitectura IGA, reflejando que los 3 resources v2 quedaron operativos y el piloto de 1 trabajador se validó. *(Tarea de doc, fuera del trabajo de `midpoint-expert` puro.)*

## 7. Criterios de aceptación

**Ola 1 (bloqueante para Ola 2):**
- [ ] `oracle-lamb-trabajadores-v2`: test connection `success` end-to-end.
- [ ] Import de 1 registro: task termina en `success`, **0** `fatal_error`, exactamente **1** shadow creado.
- [ ] Focus UserType resultante: `name`/`employeeNumber`/`givenName`/`familyName` (AS-IS) poblados; `extension/upeu3:taxId` en formato URN SCHAC; `assignment` al archetype faculty/staff correcto.
- [ ] `lifecycleState` del focus = `draft` (o el esperado por el template) y **0** operaciones de provisioning hacia los resources Entra ID y Koha.
- [ ] Ningún reinicio del contenedor MidPoint; cambios aplicados solo por re-import del resource.
- [ ] `git log` de `midPointEcosystem` y de PROD muestran el cambio sincronizado.

**Ola 2:**
- [ ] `oracle-lamb-estudiantes-v2` y `oracle-lamb-egresados-v2`: test connection `success`.
- [ ] Sus `searchScript` retornan `List<Map>` (sin `handler`/`SearchResult`).
- [ ] Las 9 variables Groovy de inbounds corregidas a MAYÚSCULAS y coincidentes con el atributo ICF.
- [ ] (Si se hace import de prueba) atributos esperados poblados, `archetypeRef` correcto, `lifecycleState` = `draft`, sin provisioning.

**Global / no-regresión:**
- [ ] El schema v3.0 (`b7d55017-…`) no se modifica.
- [ ] El connector ConnId no se modifica.
- [ ] Las tasks de reconciliación masiva siguen `suspended`.
- [ ] Resources v1 y resource Keycloak legacy intactos (no son objeto de esta spec).

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| El `searchScript` reescrito devuelve tipos incompatibles con el `schemaScript` (p.ej. `Date` en vez de `String`) → error de schema | Convertir explícitamente fechas a `String`; las claves del mapa deben ser exactamente los `AttributeInfo` declarados. Test connection + import de 1 registro lo detecta. |
| El binding `query` (filtro de import task) no se maneja en el `searchScript` → la task de import por filtro falla con "Resource not defined in a search query" | Para el piloto, acotar con `WHERE ROWNUM = 1` en el SQL en vez de depender del filtro de la task; o usar una recon/import full sin filtro. Si se quiere filtro por `COD_APS`, manejar el binding `query` en el script (fuera de scope del piloto). |
| El focus importado sale `active` y dispara provisioning a Entra ID/Koha | El piloto es 1 solo registro; verificar `lifecycleState` y logs de los resources target ANTES de pasar a Ola 2. Si provisiona, detenerse y reportar. |
| Olvidar revertir `WHERE ROWNUM = 1` antes de la recon masiva | Documentar explícitamente en el commit y en `context.md` que el límite es temporal del piloto; la recon masiva es otra spec que debe quitarlo. |
| Diferencias cosméticas worktree ↔ `midPointEcosystem` ↔ PROD causan confusión | Trabajar siempre sobre `midPointEcosystem` (fuente de verdad) y re-import desde ahí; las líneas citadas son aproximadas — `midpoint-expert` localiza por contenido, no por número de línea. |

## 9. Definición de "hecho"

- Ola 1 con todos sus criterios de aceptación ✅.
- Ola 2 con todos sus criterios de aceptación ✅.
- Cambios en `midPointEcosystem` commiteados, pusheados y aplicados en PROD vía `git pull` + re-import.
- `context.md` actualizado (F5 a 🟢 o lo que corresponda; F9 con el piloto validado).
- Reporte final del `midpoint-expert`: qué registro se importó, atributos resultantes, lifecycle, ausencia de provisioning, y estado de límite `ROWNUM` (revertido o pendiente).
