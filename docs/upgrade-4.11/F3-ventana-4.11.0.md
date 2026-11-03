# F3 · Ventana PROD: midPoint 4.10.5 → 4.11.0

- **Cuándo (propuesto):** martes 25-nov-2026, **16:30–21:30 UTC** (11:30–16:30 Lima).
- **Requisitos:**
  - F1 completo y sin bloqueos, con los tiempos de este runbook medidos.
  - F2 lleva una semana sin incidencias: recons con el mismo `resultStatus` y LDAP `.168 = .169`.
- **Ficheros:** [`upeu/infra/upgrade-4.11/`](../../upeu/infra/upgrade-4.11/README.md).
- **Qué cambia y por qué cada paso:** [`PLAN-Y-ROADMAP.md`](PLAN-Y-ROADMAP.md) e
  [`INVENTARIO-PROD-4.10.md`](INVENTARIO-PROD-4.10.md) §7 (bloqueantes R1–R5).

## 0. Lo que NO se hace en esta ventana

- **No** se importa la SystemConfiguration de 4.11 (`000`), ni el administrador, ni los roles
  004/008/00a/00b/00c: ver [`initial-objects/nunca.oids`](../../upeu/infra/upgrade-4.11/initial-objects/nunca.oids).
- **No** se activan los perfiles de expresión de 4.11 ni `defaultScriptLanguage=mel`. Groovy
  sigue igual (proyecto F5).
- **No** se cambia la imagen base (se sigue con `-ubuntu`), **no** se sube Postgres y **no** se
  toca la configuración de los recursos, salvo el `connectorRef` de LDAP.

## 1. Días antes (fuera de ventana)

```bash
source ~/.secrets/midpoint-upeu.env
alias prod='sshpass -p "$MIDPOINT_PROD_PASS" ssh -o ProxyJump=none -o NumberOfPasswordPrompts=1 -o StrictHostKeyChecking=no juansanchez@192.168.15.166'
```

1. `git pull` en PROD (ver F2 §1).
2. Imágenes:
   `prod 'docker pull evolveum/midpoint:4.11.0-ubuntu && docker pull evolveum/midpoint:4.11.0-alpine'`.
3. **Comprobación previa (nodos y esquema).** `ninja pre-upgrade-check` de 4.11 **no sirve**:
   su repositorio se niega a abrir una BD en esquema 51 (exige 67), también con
   `upgradeableSchemaAction=warn` (ensayo F1, H5). Se mide lo mismo por SQL:
   ```bash
   prod 'docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tAc "select nameorig, convert_from(fullobject,'"'"'UTF8'"'"')::jsonb->'"'"'node'"'"'->'"'"'build'"'"'->>'"'"'version'"'"' from m_node; select * from m_global_metadata"'
   ```
   Esperado: **un solo** nodo, en `4.10.5`, y `51` / `10`.
4. **`verify` de 4.11** (F1, 3-nov): **0 `CRITICAL`**, 1 `NECESSARY`, 288 `OPTIONAL`. El
   `NECESSARY` es `SystemConfiguration` → `cleanupPolicy/objectResults` (eliminado en 4.11). Se
   quita **con 4.10.5 en marcha**, fuera de ventana (probado en F1 ida y vuelta):
   ```bash
   curl -sS -o /dev/null -w '%{http_code}\n' -u administrator:$MP_REST_PASS -X PATCH -H 'Content-Type: application/xml' \
     --data-binary @$W/sysconfig-cleanup-objectresults-delete.xml $REST/systemConfigurations/00000000-0000-0000-0000-000000000001
   ```
   `204`, `version` +1 y `?options=raw` sin `<objectResults>`. Vuelta atrás:
   `sysconfig-cleanup-objectresults-rollback.xml` (repone `P7D`). Si se olvidara, 4.11 arranca
   igual (medido), pero el `verify` lo exige.
5. **Espacio:** borrar la copia de F2 (`bd-copia-local.sh borrar midpoint_pre_4102`) y comprobar
   con `estado` que hay libre ≥ tamaño de `midpoint` + 8 GB.
6. **Muestra fija** para la simulación, generada una vez y reutilizada en PRE y POST:
   `prod 'mkdir -p ~/upgrade-4.11 && ~/midPointEcosystem/upeu/infra/upgrade-4.11/muestra-sim.sh generar 20 > ~/upgrade-4.11/muestra.oids && wc -l ~/upgrade-4.11/muestra.oids'`
   (≤ 80 usuarios; no commitear).
7. Congelación de cambios desde el viernes anterior.

## 2. Ventana — paso a paso

```bash
cd /opt/midpoint
W=~/midPointEcosystem/upeu/infra/upgrade-4.11
CW="docker compose -f docker-compose.yml -f $W/docker-compose.upgrade-window.yml"                                   # 4.10.5
C3="docker compose -f docker-compose.yml -f $W/docker-compose.upgrade-window.yml -f $W/docker-compose.4.11.yml"     # 4.11, ventana
read -r -s -p "Contraseña REST administrator: " MP_REST_PASS; echo; export MP_REST_PASS
REST=http://localhost:8080/midpoint/ws/rest
```

| # | Paso | Comando | Verificación | Tiempo ref. |
|---|---|---|---|---|
| 0 | **Hora** | `date -u` | 16:30–17:00 UTC | — |
| 1 | Fotos PRE | `snapshot-estado.sql > ~/upgrade-4.11/snap-pre-F3.tsv` (como en F2), `$W/ldap-connectorref.sh show > ~/upgrade-4.11/conectores-pre-F3.txt`, `curl -s -u administrator:$MP_REST_PASS "$REST/systemConfigurations/00000000-0000-0000-0000-000000000001?options=raw" > ~/upgrade-4.11/sysconfig-pre-F3.xml && chmod 600 ~/upgrade-4.11/sysconfig-pre-F3.xml` | ficheros no vacíos | 2 min |
| 2 | Suspender tareas | `$W/tareas-ventana.sh suspender` | 8 `SUSPENDED`, ninguna `RUNNING` | 1 min |
| 3 | **SIM PRE** (4.10.5) | `$W/muestra-sim.sh tarea pre-F3 ~/upgrade-4.11/muestra.oids > ~/upgrade-4.11/sim-pre.xml` y `curl -sS -u administrator:$MP_REST_PASS -X POST -H 'Content-Type: application/xml' --data-binary @$HOME/upgrade-4.11/sim-pre.xml -D - -o /dev/null $REST/tasks \| grep -i '^location'` → apuntar el OID (`SIM_PRE`) | La tarea termina (`tareas-ventana.sh estado` no la muestra `RUNNING`; GUI: resultado `SUCCESS`) | F1: 73 s (73 usuarios) |
| 4 | Parar midPoint | `docker compose stop midpoint_server` | sin `midpoint_server` | 15 s |
| 5 | **Copia local de la BD** | `$W/bd-copia-local.sh crear 4105` | «OK: la copia coincide» | ~5 min (F1: 5 GB en 59 s) |
| 6 | Copia fuera del host | `~/midPointEcosystem/upeu/scripts/backup-midpoint-s3.sh --pre-upgrade f3-4105` | `.sha256` del dump y del home en S3 | ~10 min |
| 7 | Copia local del home | como F2 paso 6, a `~/upgrade-4.11/home-pre-F3.tgz` | `./keystore.jceks` listado | 30 s |
| 8 | **`config.xml`** (R8) | `$W/config-xml-safe-scripting.sh --apply` y luego `--check` | `safeScriptingLanguagesOnly … : false` | 10 s |
| 9 | **Propietario UID 1000** (R1) | `docker run --rm -v midpoint_midpoint_home:/v --user 0 --entrypoint chown postgres:16-bullseye -R 1000:1000 /v` (en `/v`, **no** en `/var`: la imagen `postgres` declara `VOLUME /var/lib/postgresql/data` y crearía esa ruta dentro del home, F1 H6) | `docker run --rm -v midpoint_midpoint_home:/v --user 1000:1000 --entrypoint sh postgres:16-bullseye -c 'cat /v/keystore.jceks >/dev/null && test -w /v/log && test -w /v && echo LEGIBLE-Y-ESCRIBIBLE; find /v -xdev ! -user 1000 \| head -3'` → `LEGIBLE-Y-ESCRIBIBLE` y ninguna ruta | <1 min |
| 10 | Versión en `.env` | `cp -p .env .env.bak-pre-4110 && sed -i 's/^MP_VER=4.10.5$/MP_VER=4.11.0/' .env && grep '^MP_VER' .env` | `MP_VER=4.11.0` | — |
| 11 | **Esquema** (R3) | `$C3 run --rm -T --no-deps ninja run-sql --upgrade --mode repository` y después `--mode audit` | «Scripts executed successfully»; `select * from m_global_metadata` → **67 y 16** | F1: 8 s + 7 s (sin datos de auditoría ❓ en PROD) |
| 12 | Auditoría con payload (R4) | `docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tAc "select count(*) filter (where relname ~ '^ma_audit_event_[0-9]{6}\$'), count(*) filter (where relname ~ '^ma_audit_payload_[0-9]{6}\$') from pg_class where relkind='r'"` | mismo número de particiones `event` que `payload` | — |
| 13 | **Initial objects** | los 3 comandos de [`initial-objects/README.md`](../../upeu/infra/upgrade-4.11/initial-objects/README.md) con `C="$C3"` | el informe del paso 2 no contiene OIDs de `nunca`/`revisar` **como `objectToAdd`** (ver README); tras aplicar, los 39 suben `version` en 1 y los 10 de `nunca.oids` no cambian (consulta abajo) | F1: 26 + 22 + 25 s; 39/39 +1, 10/10 y 35/35 intactos |
| 14 | **Arrancar 4.11** (planificador parado) | `$C3 up -d midpoint_server`; esperar `healthy` como en F2 | versión `4.11.0` en `m_node`; `docker logs midpoint_server 2>&1 \| grep -E ' ERROR \|not writable\|TrustDescriptor\|SubscriptionCompliance\|safeScripting'` sin nada nuevo respecto a F1 (F1: solo el `ERROR` preexistente del archetype «Project», H11) | F1: 75 s |
| 15 | **LDAP 3.10** (R5) | `$W/ldap-connectorref.sh show`, `apply 3.10`, `test` | 3.10 `available=t`, PATCH verificado, test `success` | 2 min |
| 16 | Resto de conectores | `docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tAc "select connectorversion, available, (convert_from(fullobject,'UTF8')::jsonb->'connector') ? 'discoveryTimestamp' from m_connector where oid in ('51e26e79-862c-4f66-9b76-0a29e3f25b6e','0ae9cbcd-0b39-4b5e-82a5-e0b8ea8a6c95','e4cd8ed3-2e91-48d9-abb7-32090a5e8849','01a9df66-90e9-4fd6-b296-bbe28f2b6b0b')"` | Koha **1.7.1** (el que usa el recurso; F1 H9), Zammad 0.2.0, ScriptedSQL 2.2.10 y msgraph 1.2.0.0 con `available=t` y `discoveryTimestamp` presente (desde hoy cuentan los 90 días, ver README §2) | — |
| 17 | Test de los 12 recursos | `$W/test-recursos.sh` | `12/12 success` | ~2 min |
| 18 | **`privilegedPrincipal`** (R10) | `curl -sS -o /dev/null -w '%{http_code}\n' -u administrator:$MP_REST_PASS -X PATCH -H 'Content-Type: application/xml' --data-binary @$W/sysconfig-privileged-principal-patch.xml $REST/systemConfigurations/00000000-0000-0000-0000-000000000001` | `204`; `version` +1; `?options=raw` contiene `<privilegedPrincipal>permissive</privilegedPrincipal>` y **no** contiene `defaultScriptLanguage` | 1 min |
| 19 | Arranque normal (planificador en marcha, UID 1000) | `docker compose -f docker-compose.yml -f $W/docker-compose.4.11.yml up -d`; esperar `healthy` | `healthy`; `data_init` (4.11-alpine, UID 1000) dice «Repository init is not needed» | ~4 min ❓ |
| 20 | **SIM POST** y comparación | como el paso 3 con etiqueta `post-F3` → `SIM_POST`; `$W/muestra-sim.sh comparar $SIM_PRE $SIM_POST` | `IGUALES`, o cada diferencia explicada (no por la versión) | F1: 83 s; IGUALES (17 MODIFIED preexistentes) |
| 21 | Canarios reales | como F2 paso 13 (grupos DTI de LDAP y ausencias); si quedan más de 45 min, también `recon-oracle-lamb-trabajadores-daily` (~12 min: ScriptedSQL + outbounds a LDAP y Koha con 4.11) | `SUCCESS`; 0 errores de expresión; `pendingOperationCount=0` | 5–20 min |
| 22 | Reanudar el resto | `tareas-ventana.sh reanudar` de las demás (sin `ejecutar`) | 8 `RUNNABLE` | 1 min |
| 23 | Foto POST | `snapshot-estado.sql > snap-post-F3.tsv`; `diff` con la PRE | solo cambios explicados por los canarios | 2 min |

Consulta del paso 13 (antes y después, comparar):

```bash
docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tA -F' ' -c \
 "select oid, version from m_object where oid in ($(grep -o '^[0-9a-f-]\{36\}' $W/initial-objects/*.oids | cut -d: -f2 | sed "s/.*/'&'/" | paste -sd,)) order by oid" > ~/upgrade-4.11/io-versiones-<pre|post>.txt
```

**Límite para decidir la vuelta atrás: 20:30 UTC.** Con cualquiera de estos síntomas y sin
solución en 30 minutos, se vuelve atrás (§4):

- midPoint no queda `healthy`;
- falla el `run-sql`;
- un recurso no da `success`;
- la simulación POST trae diferencias no explicadas;
- aparecen errores de expresión.

## 3. Después

- **Integrar en el compose base** el `user: "1000:1000"` de `docker-compose.4.11.yml`
  (`upeu/infra/docker-compose.yml`) y desplegarlo en `/opt/midpoint` (con `cp` desde el clon y
  `diff` antes). Después borrar el override del repo. `MP_VER=4.11.0` en `env.example`.
- **Repo:** `connectorRef` de `upeu/resources/ldap-identity-cache.xml` → OID del 3.10 de PROD
  (espejo del PATCH). La SystemConfiguration del repo, si se versiona, lleva el `defaults`.
- **Mañana siguiente:** recons a su hora. Comparar `resultStatus` y duración con F2. Comprobar
  LDAP `.168 = .169` y 0 errores de expresión en el log.
- **1-dic, 03:00 Lima:** primera purga de auditoría con `ma_audit_payload`. Revisar
  `/var/log/midpoint-audit-partition-maintenance.log`: debe listar `payload` en el orden de DROP.
- **Revisar a mano** los 35 de `revisar-a-mano.oids` con el informe del paso 13 (F4).
- **Recordatorio a los 90 días (≈ 23-feb-2027):** no cambia nada mientras PROD siga sin
  indicadores de «producción» (README §2). Volver a medirlo si alguien configura URL pública,
  correo, cabecera de IP remota, appender no-fichero o colores/logo.
- **A los 7 días:** `bd-copia-local.sh borrar midpoint_pre_4105`, y borrar los `tgz`/`xml` de
  `~/upgrade-4.11`.

## 4. Vuelta atrás (objetivo: < 20 min)

El esquema 67/16 **no se revierte**: se vuelve a la base copiada en el paso 5.

| # | Paso | Comando | Verificación |
|---|---|---|---|
| R1 | Parar | `docker compose stop midpoint_server` | — |
| R2 | BD | `$W/bd-copia-local.sh restaurar 4105` | huella = paso 5 (51/10) |
| R3 | Versión | `cp -p .env.bak-pre-4110 .env` | `MP_VER=4.10.5` |
| R4 | Home | `docker run --rm -i -v midpoint_midpoint_home:/v --user 0 --entrypoint tar postgres:16-bullseye -C /v -xzf - < ~/upgrade-4.11/home-pre-F3.tgz` (devuelve el `config.xml` sin el bloque `expressions`). El dueño 1000 no molesta a 4.10.5, que corre como root | `config-xml-safe-scripting.sh --check` → `ausente` |
| R5 | Arrancar 4.10.5 | `docker compose up -d` (**sin** el override de 4.11) | versión `4.10.5`; `ldap-connectorref.sh show` → 3.9.4 en uso, `available=t` |
| R6 | Recursos, tareas | `test-recursos.sh` 12/12; reanudar las 8 | como antes de la ventana |

Último recurso: el dump `s3://…/midpoint/upgrade/f3-4105/` (sin datos de auditoría; ver F2 §4).
Tiempos medidos en F1 (3-nov, lab): R1–R5 **86 s**, más ~3 min del test de recursos. Detalle en
[`F1-RESULTADO-2026-11-03.md`](F1-RESULTADO-2026-11-03.md).
