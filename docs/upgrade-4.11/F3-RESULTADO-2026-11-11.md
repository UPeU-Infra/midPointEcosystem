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

- `midpoint_fallida_202611111103` (BD en esquema 67/16, ~28 GB) para análisis. Borrar con
  `bd-copia-local.sh borrar midpoint_fallida_202611111103` cuando no haga falta.
- `midpoint_pre_4105` **ya no existe** (pasó a ser `midpoint`). La copia S3 `f3-4105` sigue válida.
- `~/upgrade-4.11/`: `log-411-F3-fallido.txt` (600), `home-pre-F3.tgz`, `sysconfig-pre-F3.xml`
  (600, lleva el token de Telegram), `snap-*-F3.tsv`, `muestra.oids` (PII). Borrar los
  `tgz`/`xml`/`tsv` cuando se cierre el análisis.
- Volumen del home con dueño 1000 (no molesta a 4.10.5, que corre como root).

## Antes de reintentar F3

1. **Reproducir en el lab** con un recurso ScriptedSQL contra una base alcanzable (Postgres) en
   4.11.0: confirmar el `NoClassDefFoundError` sin Oracle.
2. Buscar/abrir el caso con Evolveum (Jira / lista `midpoint`): ¿4.11.x lo corrige? ¿qué
   versión de `script-security`/`groovy-sandbox` espera ConnId 1.7.0.0-M0?
3. Solo si Evolveum no lo corrige: probar en el lab añadir esas dependencias en `var/lib`
   (classpath extendido, como `ojdbc11`), con la SIM recon de Oracle como criterio.
4. Añadir al runbook F3, paso 17, que el test de los 8 Oracle es **bloqueante**.
