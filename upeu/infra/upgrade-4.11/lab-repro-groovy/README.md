# Reproducción en el lab del fallo de F3 (ScriptedSQL / Groovy en 4.11.0)

En F3 (11-nov-2026) los 8 recursos Oracle LAMB dieron `fatal_error` con midPoint 4.11.0:

```
java.lang.NoClassDefFoundError: org/jenkinsci/plugins/scriptsecurity/sandbox/Whitelist
```

Detalle y vuelta atrás en [`docs/upgrade-4.11/F3-RESULTADO-2026-11-11.md`](../../../../docs/upgrade-4.11/F3-RESULTADO-2026-11-11.md).

Este kit reproduce el fallo **sin Oracle y sin datos de PROD**. Levanta un midPoint vacío por
versión con el **mismo** bundle `net.tirasa.connid.bundles.db.scriptedsql-2.2.10`. El sha256 se
comprueba contra el de PROD. Crea un recurso con la misma forma que los Oracle LAMB
(`scriptingLanguage=GROOVY`, scripts en línea) contra el Postgres del propio proyecto, que solo
hace `SELECT 1`, y lanza el test de conexión.

Sirve también de banco de pruebas para cualquier arreglo, antes de tocar PROD: una 4.11.x nueva o
dependencias en `var/lib`. **El criterio es que en 4.11 el test dé `success`.**

## Uso (en el lab, `192.168.15.150`, carpeta `/u01/lab/pruebas/mp411-repro`)

```bash
./repro.sh preparar                 # jar de Maven Central + sha256 de PROD + .env (600)
./repro.sh probar 4.10.5 8098       # control: debe dar success
./repro.sh probar 4.11.0 8099       # debe reproducir el NoClassDefFoundError
./repro.sh bajar 4.10.5; ./repro.sh bajar 4.11.0   # borra contenedores y volúmenes
```

Cada versión es su propio proyecto Compose (`mprepro4105`, `mprepro4110`). Ocupa unos 3 GB de RAM
por versión.

## Variantes del parche (11-nov)

```bash
./repro.sh preparar-parche                     # lib-parche/ (2 jars, sha1 de Maven Central) y lib-parche-b/ (1 jar)
PARCHE=1 ./repro.sh probar 4.11.0 8099         # con las 2 librerías: test ok, eachRow falla en el sandbox
PARCHE=b ./repro.sh probar 4.11.0 8099         # solo groovy-security-sandbox: falla al enlazar
TMPL=recurso-scriptedsql-postgres-rows.xml.tmpl PARCHE=1 ./repro.sh probar 4.11.0 8099   # rows(): funciona
```

Los resultados están en `docs/upgrade-4.11/F3-RESULTADO-2026-11-11.md` («Prueba del parche»).

## Arreglo elegido para reintentar F3 (11-nov, noche)

```bash
./repro.sh preparar-parche     # crea también lib-parche-c/: 2 librerías + zz-groovy-blacklist-vacia.jar
TMPL=recurso-scriptedsql-postgres-torowresult.xml.tmpl PARCHE=c ./repro.sh probar 4.11.0 8099   # ✅ test y búsqueda
TMPL=recurso-scriptedsql-postgres-torowresult.xml.tmpl ./repro.sh probar 4.10.5 8098            # ✅ el script nuevo también vale en 4.10.5
```

- **Librerías (`var/lib`):** `groovy-security-sandbox-1.1.0` + `groovy-sandbox-4.3.2` (sin ellas la clase
  ni siquiera enlaza) + una `META-INF/groovy.blacklist` **vacía**, que se carga antes que la de ConnId
  (verificado con un `testScript` de diagnóstico). El sandbox queda activo pero no prohíbe nada,
  como en 4.10.5. Así, las construcciones de los scripts reales que no se pueden probar sin Oracle no
  dependen de la lista de 210 prohibiciones.
- **Scripts:** en cada `searchScript`, `sql.eachRow(finalQuery, params) { row -> …` pasa a
  `{ rs -> def row = rs.toRowResult(); …`. Sigue en streaming, y `row.COLUMNA` y `row[0]` se comportan igual.
