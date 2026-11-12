# F3 · Resultado (11-nov-2026): **VUELTA ATRÁS** — PROD sigue en 4.10.5

**Resumen:** la ventana llegó al paso 17 sin incidencias y se volvió atrás porque **los 8 recursos
Oracle LAMB (ScriptedSQL 2.2.10) dan `fatal_error` en 4.11.0**. La vuelta atrás (R1–R6) tardó
~70 s más el test de recursos. Estado final verificado: 4.10.5, esquema 51/10, LDAP 3.9.4,
12/12 recursos `success`, 8 tareas `RUNNABLE`, foto de estado **idéntica** a la PRE (`diff` = 0
líneas sobre 66.153).

Adelantada al 11-nov (el plan decía 25-nov) por decisión de Alberto; arrancó al terminar
`recon-koha-upeu-daily` (10:41 Lima).

## Cronología (UTC)

| Hora | Paso | Resultado |
|---|---|---|
| 15:42 | 0–2 | nodo 4.10.5, esquema 51/10; fotos PRE; 8 tareas `SUSPENDED` |
| 15:42 | 3 SIM PRE | 73 usuarios, `SUCCESS` en 151 s |
| 15:45 | 4–5 | parado; `midpoint_pre_4105` (28 GB) en **137 s**, huella igual |
| 15:47 | 6 | S3 `f3-4105`: dump 2,6 GB + home 76 MB, 506 s |
| 15:56 | 7–10 | home tgz con keystore; `safeScripting=false`; UID 1000 legible/escribible; `MP_VER=4.11.0` |
| 15:57 | 11–13 | esquema **67/16** (3 s + 3 s); 62/62 particiones; initial objects: **39/39** +1, nada fuera de la lista |
| 15:58 | 14 | 4.11.0 `healthy` en **50 s**, `uid=1000`; log: solo el `ERROR` del archetype Project (H11) |
| 15:59 | 15–16 | LDAP → **3.10** (`7289b0ec-…`), test `success`; Koha 1.7.1, Zammad 0.2.0, ScriptedSQL 2.2.10, msgraph 1.2.0.0 `available=t` |
| 15:59 | 17 | **4/12**: los 8 Oracle `fatal_error` |
| 16:03 | R1–R5 | parado; BD restaurada (renombrado 0 s); `.env`; home; 4.10.5 `healthy` en 40 s |
| 16:04 | R6 | **12/12 success** |
| 16:06 | — | 8 tareas reanudadas; foto POST = PRE |

## Causa (medida)

```
java.lang.NoClassDefFoundError in Oracle LAMB …: org/jenkinsci/plugins/scriptsecurity/sandbox/Whitelist
```

- `connector-framework-internal-1.7.0.0-M0.jar` (el ConnId que trae midPoint 4.11.0) referencia
  esa clase desde `org.identityconnectors.common.script.groovy.GroovyScriptExecutorFactory$GroovyScriptExecutor`
  (búsqueda en los `.class` de los jars de `midpoint.jar`).
- **Ningún** jar de `midpoint.jar` 4.11.0 contiene la clase (ni `script-security` ni `groovy-sandbox`).
- En 4.10.5 (`connector-framework-internal-1.6.0.0`) ningún jar la referencia → por eso funciona.
- El bundle `net.tirasa.connid.bundles.db.scriptedsql-2.2.10` (FrameworkVersion 1.5.2.0, con
  `commons-scripted-1.5.2.0` y `commons-db-1.5.2.0` dentro) **no** la referencia: usa el
  ejecutor Groovy del framework.
- Afecta a **todo conector que ejecute Groovy a través del framework de ConnId**, no solo a
  Oracle. LDAP, Koha, Zammad y msgraph no lo usan.

**Por qué F1 no lo vio:** en el lab Oracle era inalcanzable (*Connection refused*) y el test
moría antes de compilar el primer script Groovy. F1 lo dejó como riesgo abierto («8/8 Oracle
⚠️ no medible en el lab»). **Lección:** el ensayo debió ejercitar el ejecutor Groovy de ConnId
con *cualquier* base alcanzable (p. ej. un ScriptedSQL contra un Postgres del lab), no
depender de Oracle.

No se encontró el fallo reportado aguas arriba (búsqueda del 11-nov).

## Qué queda en PROD

- ~~`midpoint_fallida_202611111103` (BD en esquema 67/16, ~28 GB)~~ **borrada el 11-nov
  (20:45 UTC)** con `bd-copia-local.sh borrar`, tras comprobar 0 conexiones. PGDATA pasó de
  45 GB a 73 GB libres. En PROD solo queda la base `midpoint`.
- `midpoint_pre_4105` **ya no existe** (pasó a ser `midpoint`). La copia S3 `f3-4105` sigue válida.
- ~~`~/upgrade-4.11/`~~ **borrado el 11-nov**: 18 ficheros de trabajo de F2/F3 (44 MB). Los que
  llevaban secretos o datos personales (`home-pre-F3.tgz` con el keystore, los 2 `sysconfig-*.xml`
  con el token de Telegram, `muestra.oids`, el log) se borraron con `shred -u`. La copia S3
  `f3-4105` sigue siendo el respaldo de esa ventana.
- Volumen del home con dueño 1000 (no molesta a 4.10.5, que corre como root).

## Reproducción en el lab (11-nov, 16:28 Lima) ✅

Kit: [`upeu/infra/upgrade-4.11/lab-repro-groovy/`](../../upeu/infra/upgrade-4.11/lab-repro-groovy/).
Se usó un midPoint vacío por versión con el **mismo** bundle ScriptedSQL 2.2.10 (sha256 igual
al de PROD) y un recurso con la forma de los Oracle LAMB contra el Postgres del propio proyecto.

| Versión | Test de conexión |
|---|---|
| 4.10.5 (control) | `success` en todas las fases |
| 4.11.0 | `fatal_error` en **`initialize`** (y `schema`): `NoClassDefFoundError: org/jenkinsci/plugins/scriptsecurity/sandbox/Whitelist`, el mismo `WARN` de `ConnIdUtil` que en PROD |

- Falla en `initialize`, **antes de abrir la conexión**: es la compilación de los scripts Groovy.
  No depende de Oracle ni de la red.
- ⚠️ Esto contradice F1, que anotó `initialize` en `success` con 4.11 (§3.1 de
  `F1-RESULTADO`). Es probable que ese test se midiera en otra fase. No se puede comprobar
  porque los logs de F1 ya no existen.

## Prueba del parche en el lab (11-nov, 17:20–17:35 Lima)

**Causa exacta (bytecode de `connector-framework-internal-1.7.0.0-M0`):** ConnId 1.7 añade un
sandbox Groovy. Para ello declara como **opcional** `net.tirasa:groovy-security-sandbox`, que
depende de `org.craftercms:groovy-sandbox`. El constructor del ejecutor intenta desactivarlo si
falta la librería (`catch NoClassDefFoundError` → `"Groovy Sandbox runtime not found, disabling"`).
Pero el verificador de la JVM carga `Whitelist` al enlazar la clase, fuera de ese `try`, y la
clase entera no se puede usar. **Es un bug de ConnId 1.7.0.0-M0.** midPoint 4.11.0 no trae
ninguna de las dos librerías.

| Variante (4.11.0, librerías en `var/lib`) | Test | Búsqueda con `eachRow` |
|---|---|---|
| Sin nada (lo de F3) | ❌ `NoClassDefFoundError: …/Whitelist` | ❌ |
| Solo `groovy-security-sandbox-1.1.0` | ❌ `NoClassDefFoundError: org/kohsuke/groovy/sandbox/GroovyInterceptor` (el mismo problema de verificación) | ❌ |
| `groovy-security-sandbox-1.1.0` + `groovy-sandbox-4.3.2` | ✅ `success` | ❌ `MissingPropertyException: No such property: NOMBRE for class: jdk.proxy2.$Proxy…` |
| Lo mismo + script con `sql.rows(q, params).each { row -> … }` | ✅ `success` | ✅ datos correctos (todos y `EQUALS`) |
| 4.10.5 (control), script original | ✅ | ✅ |

- **Ningún parche de librerías basta por sí solo.** Con las dos librerías el sandbox se activa,
  y su lista negra (`META-INF/groovy.blacklist`, línea 85:
  `method groovy.lang.GroovyObject getProperty java.lang.String`) bloquea `row.COLUMNA` sobre la
  fila de `eachRow`, que es un proxy `GroovyObject`. Con `rows()` la fila es un `GroovyRowResult`
  (un `Map`) y funciona. `firstRow` (los `testScript`) también funciona.
- **Cambio de script necesario:** 1 `eachRow` por recurso (7 ficheros en
  `upeu/resources/oracle-lamb/`). `rows()` también funciona en 4.10.5, así que el cambio se puede
  desplegar **antes** de subir. Coste: `rows()` carga todo el resultado en memoria en lugar de
  recorrerlo en streaming ❓ medir en estudiantes y trabajadores.
- **No probado:** el resto de construcciones de los scripts reales contra el sandbox. La lista
  negra tiene 210 entradas, y la prueba solo ejercitó `Sql`, `eachRow`/`rows`, closures, mapas y
  `query.*`. Probarlo de verdad exige Oracle; el lab `.150` sigue sin acceso.

## ⚠️ Corrección (11-nov, noche): el fallo de `eachRow` NO es de la lista negra

La explicación de la sección anterior (línea 85 de la lista negra) era **incorrecta**. Medido en el
lab: con una `META-INF/groovy.blacklist` **vacía** en `var/lib`, que es la que se carga primero
(lo confirmó un `testScript` de diagnóstico que listó los recursos del classpath), `eachRow` sigue
fallando con la misma `MissingPropertyException`. El fallo está en cómo el interceptor del sandbox
resuelve `row.COLUMNA` sobre la fila de `eachRow`, que es un `java.lang.reflect.Proxy`. Una lista
negra prohibitiva daría `RejectedAccessException`, no `MissingPropertyException`.

**Arreglo probado en el lab** (`lab-repro-groovy`, plantilla `…-torowresult.xml.tmpl`, `PARCHE=c`):

| Variante | Test | Búsqueda |
|---|---|---|
| 4.11.0 + 2 librerías + lista negra vacía, `eachRow` original | ✅ | ❌ `MissingPropertyException` |
| 4.11.0 + 2 librerías, `eachRow { rs -> def row = rs.toRowResult(); … }` | ✅ | ✅ (todos, `EQUALS`, `row[0]`) |
| 4.11.0 + 2 librerías + lista negra vacía, `toRowResult()` | ✅ | ✅ |
| 4.10.5 sin librerías, `toRowResult()` | ✅ | ✅ |

`toRowResult()` mantiene el streaming (no carga el resultado entero como `rows()`). Y como también
funciona en 4.10.5, **se puede desplegar antes de subir** y validarlo con Oracle real en las recons
diarias.

**Los 8 recursos en PROD** (leídos por REST el 11-nov): los 8 tienen exactamente un
`{ row -> ` en el `searchScript` y no usan la variable `rs`. 6 coinciden con el repo. **Egresados**
difiere del repo (manda PROD), y **Ausencias v1** (`6a91f7e1-…0e24`) **no está en el repo**.

## Antes de reintentar F3 (plan del 11-nov, noche)

Alberto decidió no esperar a Evolveum y no reportar el fallo; se sube con el arreglo probado.

1. ~~Reproducir en el lab~~ ✅ · ~~probar el arreglo en el lab~~ ✅ (sección anterior).
2. **Scripts en PROD sobre 4.10.5** (PATCH, nunca PUT): `{ row -> ` → `{ rs -> def row = rs.toRowResult(); `
   en los 8 `searchScript`. Primero un canario (Grados), después el resto. Verificar en cada uno: la
   `version` sube, el `<schema>` sigue intacto, el test da `success` y una búsqueda real por nombre
   devuelve 1. Validación: las recons diarias del día siguiente, con el mismo número de cambios y
   errores que la base. Pasar al repo Egresados (la versión de PROD) y Ausencias v1.

   ✅ **Aplicado el 12-nov, 07:10–07:15 (Lima)**, con autorización de Alberto, en los 8 recursos y
   uno por uno. En los 8: PATCH HTTP 204, la `version` sube en 1, el `<schema>` conserva sus
   elementos, el test da `success` en todo el árbol y una búsqueda real contra Oracle por el nombre
   de una cuenta existente devuelve 1. En marcha durante el cambio solo estaba `recon-entra-id-daily`,
   que no toca Oracle.

   | Recurso | version |
   |---|---|
   | Grados v1 (canario) | 6 → 7 |
   | Posiciones | 11 → 12 |
   | Org | 46 → 47 |
   | RENIEC Cache v1 | 26 → 27 |
   | Ausencias v1 | 1 → 2 |
   | Egresados v3 | 215 → 216 |
   | Estudiantes v3 | 212 → 213 |
   | Trabajadores v3 | 334 → 335 |

   En el repo los 7 `searchScript` quedan idénticos a los de PROD (comparado carácter a carácter).
   **Quedan dos desfases pendientes, ajenos a este cambio:**
   - ~~Egresados en PROD lleva la columna `SEDE` en el script **y en `schemaHandling`**, y el repo no.~~
     ✅ 12-nov: el repo recibe de PROD el atributo `ri:SEDE` → `extension/sb:campusEgreso` (inbound
     `sede-to-campusEgreso`, desplegado por PATCH el 11-ago) y su línea en el `schemaScript`, que
     tampoco estaba. Comparado después el recurso completo, sin recortar textos. Diferencias que
     **quedan a propósito**:
     - `givenName`/`familyName` → `extension/upeu:lambGivenName`/`lambFamilyName`: el repo va por
       delante (`1594a3c`, nombre oficial RENIEC E1, sin desplegar).
     - Nombre del inbound de `ESCUELA_PROFESIONAL` (`escuela-to-liveProgramUriAlum` en el repo,
       `escuela-to-academicProgramUri` en PROD), de `f3669e5`; solo cambia el nombre.
     - PROD conserva **archivada** (inerte) la reacción antigua `deleted → inactivateFocus`; el repo
       la eliminó en `2692407`. El efecto es el mismo.
     - `xsi:type` en `libraryRef`/`parameter`: serialización de midPoint, no es configuración.
   - ~~Ausencias v1 (`6a91f7e1-…0e24`) sigue sin estar en el repo.~~ ✅ 12-nov: subido como
     `upeu/resources/oracle-lamb/ausencias.xml`, exportado de PROD sin el estado de runtime
     (`_metadata`, `iteration*`, `operationalState*`, `<schema>`, `capabilities/native` y
     `cachingMetadata`, atributo `version`). Única diferencia con PROD: en la `documentation` del
     correlador se quitó un `ID_PERSONA` concreto (el repo es público).

   Falta la validación con las recons diarias del 13-nov.
3. **Ventana F3** con los mismos pasos que el 11-nov, más uno: antes de arrancar 4.11.0, copiar a
   `/opt/midpoint/var/lib` (volumen `midpoint_midpoint_home`, junto a `ojdbc11`) los 3 jars de
   `lib-parche-c` (sha1 de Maven Central fijados en `repro.sh`). En 4.10.5 no hacen nada: ConnId 1.6
   no los referencia.
4. Paso 17, **bloqueante**: test de los 8 Oracle en `success` **y** una búsqueda real por nombre en
   cada uno. Si alguno falla, se vuelve atrás (R1–R6, ~70 s, probado) y se quitan los 3 jars.
5. Tras la ventana: vigilar las recons de la primera noche (duración y errores frente a la base).
