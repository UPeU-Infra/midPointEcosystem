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

## Antes de reintentar F3

1. ~~**Reproducir en el lab**~~ ✅ hecho (sección anterior). El kit es también el banco de
   pruebas de cualquier arreglo.
2. Buscar/abrir el caso con Evolveum (Jira / lista `midpoint`): ¿4.11.x lo corrige? ¿qué
   versión de `script-security`/`groovy-sandbox` espera ConnId 1.7.0.0-M0?
3. Solo si Evolveum no lo corrige: probar en el lab añadir esas dependencias en `var/lib`
   (classpath extendido, como `ojdbc11`), con la SIM recon de Oracle como criterio.
4. Añadir al runbook F3, paso 17, que el test de los 8 Oracle es **bloqueante**.
