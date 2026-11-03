# F2 · Ventana PROD: midPoint 4.10.2 → 4.10.5

- **Cuándo (propuesto):** martes 18-nov-2026, **16:30–20:30 UTC** (11:30–15:30 Lima). Es después
  de la recon de Koha (09:15, ~2 h) y lejos del backup de las 22:30.
- **Requisito:** F1 cerrado sin bloqueos ([`F1-ensayo-lab.md`](F1-ensayo-lab.md)), con los tiempos
  de este runbook medidos allí.
- **Ficheros:** [`upeu/infra/upgrade-4.11/`](../../upeu/infra/upgrade-4.11/README.md).
- **Protocolo:** [`PROTOCOLO-PRE-EJECUCION-PROD.md`](../runbooks/PROTOCOLO-PRE-EJECUCION-PROD.md).
  En una subida de plataforma, el «canario» son una tarea corta y la muestra de simulación. El
  lote es la primera noche de recons.

## 0. Qué cambia de 4.10.2 a 4.10.5 (y qué no)

Fuentes: release notes de [4.10.3](https://docs.evolveum.com/midpoint/release/4.10.3/),
[4.10.4](https://docs.evolveum.com/midpoint/release/4.10.4/) y
[4.10.5](https://docs.evolveum.com/midpoint/release/4.10.5/), más el `pom.xml` y
`config/sql/native/` de cada tag en GitHub (leídos el 28-oct-2026).

| Tema | 4.10.2 | 4.10.5 | Efecto en UPeU |
|---|---|---|---|
| **Esquema de BD** | repo 51 / audit 10 | **51 / 10** (ningún `apply_change` nuevo) | Ninguno. `postgres-audit-upgrade.sql` solo añade un `ALTER TYPE ObjectType ADD VALUE IF NOT EXISTS 'ROLE_ANALYSIS_OUTLIER'` para BD de auditoría **separadas**; en PROD ese valor **ya existe** (medido) |
| **Conector LDAP bundled** | **3.9.2** | **3.9.4** (3.9.3 en 4.10.3) | **El recurso LDAP deja de funcionar hasta el PATCH del `connectorRef`** (paso 9). Las release notes siguen diciendo 3.9.2: manda el `pom.xml` |
| ConnId | 1.6.0.0 | 1.6.0.0 | Ninguno (Koha, Zammad, ScriptedSQL y msgraph, igual que hoy) |
| Spring Boot | 3.5.11 | **4.1.1** (salto de versión mayor, en 4.10.4) | Interno. Se prueba con las llamadas REST que usan los scripts del repo (GET/PATCH `?options=raw`, `/test`, `/suspend`) en F1 |
| Tomcat | 10.1.x | **11.0.25** | Interno. Mismo `server.servlet.context-path` ❓ (F1) |
| Groovy | 4.0.24 | 4.0.24 | Ninguno |
| Pistas de contraseña | texto | `ProtectedStringType` (MID-12111) | 0 usuarios con `hint` en PROD |
| Subida de ficheros | — | validación configurable (MID-11849, 4.10.3); límite multipart = el de Tomcat | Ninguno conocido |
| Correcciones con relación con UPeU | | MID-11979 (bucle de descubrimiento que acababa en OOM con «Already exists»), MID-12154 (marcas efectivas rancias), MID-11807 (atributos de referencia simulados pedidos al conector), MID-11186 (progreso de tareas con buckets), recepción de `notifyChange` sin OID | Mejoras; ninguna exige acción |
| Initial objects | | solo claves de localización | No se aplican en F2 (todo se hace en F3) |

**No hay scripts SQL que ejecutar entre 4.10.2 y 4.10.5.** El paso 7 lanza `run-sql --upgrade` de
todas formas, como comprobación: debe terminar sin aplicar ningún cambio numerado.

## 1. Días antes (fuera de ventana)

```bash
# En la Mac
source ~/.secrets/midpoint-upeu.env
alias prod='sshpass -p "$MIDPOINT_PROD_PASS" ssh -o ProxyJump=none -o NumberOfPasswordPrompts=1 -o StrictHostKeyChecking=no juansanchez@192.168.15.166'
```

1. La rama `prep/upgrade-4.11` está en `main` y en PROD: `prod 'cd ~/midPointEcosystem && git pull && git log --oneline -1'`.
2. Imágenes descargadas (no tocan nada en marcha):
   `prod 'docker pull evolveum/midpoint:4.10.5-ubuntu && docker pull evolveum/midpoint:4.10.5-alpine && docker images evolveum/midpoint'`.
3. Espacio para la copia local de la BD:
   `prod '~/midPointEcosystem/upeu/infra/upgrade-4.11/bd-copia-local.sh estado'`.
   Hace falta **libre ≥ tamaño de `midpoint` + 8 GB**. Referencia del 28-oct: 45 GB de BD y 57 libres.
   Tras la purga del 1-nov con el script corregido (julio y agosto, 20,5 GB) quedarían ~30 GB de
   BD y ~70 libres. **Si no cabe, no hay ventana.**
4. Backup de anoche con su `.sha256` (runbook [backup-midpoint-s3](../runbooks/backup-midpoint-s3/README.md)).
5. Aviso a los usuarios de la consola (DTI): sin cambios de configuración en midPoint desde el
   viernes anterior (congelación de F0).

## 2. Ventana — paso a paso

En el servidor (`prod` y luego trabajar dentro), con estas variables:

```bash
cd /opt/midpoint
W=~/midPointEcosystem/upeu/infra/upgrade-4.11
C="docker compose -f docker-compose.yml -f $W/docker-compose.upgrade-window.yml"
mkdir -p ~/upgrade-4.11 && chmod 700 ~/upgrade-4.11
read -r -s -p "Contraseña REST administrator: " MP_REST_PASS; echo; export MP_REST_PASS
```

Cada paso lleva su tiempo de referencia (de F1 ❓ o de la subida de mayo). Apuntar la hora real.

| # | Paso | Comando | Verificación | Tiempo ref. |
|---|---|---|---|---|
| 0 | **Hora** | `date -u` | Entre 16:30 y 17:00 UTC. Si no, no se empieza | — |
| 1 | Foto PRE | `docker exec -i midpoint-midpoint_data-1 psql -U midpoint -d midpoint < ~/midPointEcosystem/docs/runbooks/activacion-vinculo-vivo-2026-10-22/snapshot-estado.sql > ~/upgrade-4.11/snap-pre-F2.tsv` y `$W/ldap-connectorref.sh show > ~/upgrade-4.11/conectores-pre-F2.txt` | `wc -l` ≈ número de usuarios (66.1xx) | 1 min |
| 2 | Suspender tareas | `$W/tareas-ventana.sh suspender` | `estado`: las 8 `SUSPENDED`, **ninguna `RUNNING`** (si Koha sigue corriendo, esperar) | 1 min |
| 3 | Parar midPoint (Postgres sigue) | `docker compose stop midpoint_server` | `docker ps` sin `midpoint_server`; `bd-copia-local.sh estado` con 0 conexiones a `midpoint` | 15 s |
| 4 | **Copia local de la BD** (vuelta atrás) | `$W/bd-copia-local.sh crear 4102` | «OK: la copia coincide» y el ajuste `enable_partitionwise_join` copiado | ~5 min (F1: 5 GB en 56 s ≈ 90 MB/s; PROD 26 GB el 3-nov) |
| 5 | Copia fuera del host | `~/midPointEcosystem/upeu/scripts/backup-midpoint-s3.sh --pre-upgrade f2-4102` | «FIN backup pre-upgrade … OK»; `.sha256` del dump y del home en `s3://…/midpoint/upgrade/f2-4102/` | ~10 min |
| 6 | Copia local del home | `docker run --rm -v midpoint_midpoint_home:/v:ro --entrypoint tar postgres:16-bullseye -C /v -czf - --exclude=./log --exclude=./trace . > ~/upgrade-4.11/home-pre-F2.tgz && chmod 600 ~/upgrade-4.11/home-pre-F2.tgz && tar -tzf ~/upgrade-4.11/home-pre-F2.tgz \| grep -x './keystore.jceks'` | imprime `./keystore.jceks` | 30 s |
| 7 | Versión nueva en `.env` | `cp -p .env .env.bak-pre-4105 && sed -i 's/^MP_VER=4.10.2$/MP_VER=4.10.5/' .env && grep '^MP_VER' .env` | `MP_VER=4.10.5` (una sola línea) | — |
| 8 | Comprobación de esquema | `$C run --rm -T --no-deps ninja run-sql --upgrade --mode repository` y luego `--mode audit`; después `docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tAc "select * from m_global_metadata"` | «Scripts executed successfully»; **51 y 10** (sin cambios) | <1 min |
| 9 | Arrancar 4.10.5 (planificador parado, `data_init` neutralizado) | `$C up -d midpoint_server` y `until [ "$(docker inspect -f '{{.State.Health.Status}}' midpoint_server)" = healthy ]; do sleep 10; done; date -u` | `healthy`; `docker logs midpoint_server 2>&1 \| grep -c ' ERROR '` sin errores nuevos de arranque; versión: `docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tAc "select convert_from(fullobject,'UTF8')::jsonb->'node'->'build'->>'version' from m_node"` → `4.10.5` | ~4 min (mayo) |
| 10 | **Conector LDAP 3.9.4** | `$W/ldap-connectorref.sh show`, luego `$W/ldap-connectorref.sh apply 3.9.4` y `$W/ldap-connectorref.sh test` | `show`: 3.9.4 `available=t` y 3.9.2 `available=f`. `apply`: «OK: connectorRef -> 3.9.4 verificado» (versión +1, GET raw, `<schema>` presente). `test`: ESTADO GLOBAL `success` | 2 min |
| 11 | Test de los 12 recursos | `$W/test-recursos.sh` | `RESULTADO: 12/12 success` | ~2 min |
| 12 | Volver al arranque normal (planificador en marcha) | `docker compose up -d` (solo el compose base) y esperar `healthy` como en 9 | `healthy`; el log **no** trae una línea de «scheduler» (F1): comprobar que el planificador corre con `tareas-ventana.sh estado`; `data_init` ejecutó su lógica normal y dijo «Repository init is not needed» | ~4 min |
| 13 | Canarios | `$W/tareas-ventana.sh reanudar d71a0003-0000-4000-a000-d71a00000003` y `ejecutar` la misma (LDAP grupos DTI, ~1 s). Después, `reanudar` + `ejecutar a1c0de00-0000-4000-8000-00000000a05e` (ausencias, ~2 min) | Ambas terminan `SUCCESS`; 0 errores de expresión en el log | 5 min |
| 14 | Reanudar el resto | `reanudar` las otras 6 (Entra, DTI teams, trabajadores, estudiantes, egresados, Koha), **sin `ejecutar`**: corren mañana a su hora | `estado`: 8 `RUNNABLE` | 1 min |
| 15 | Foto POST y cierre | `snapshot-estado.sql > snap-post-F2.tsv; diff snap-pre-F2.tsv snap-post-F2.tsv \| head` | Diferencias **solo** explicables por los dos canarios (ausencias) | 2 min |

**Si cualquier verificación falla y no se resuelve en 30 minutos → vuelta atrás (§4).** Hora
límite para decidir: **19:30 UTC**.

## 3. Después de la ventana

- **Mañana siguiente:** seguir las recons en su hora y comparar `resultStatus` y duración con
  los del día anterior (inventario §6). Comprobar `pendingOperationCount = 0` y LDAP `.168 = .169`.
- **Repo:** PATCH espejo en `upeu/resources/ldap-identity-cache.xml` (`connectorRef` → OID del
  3.9.4 de PROD, con comentario) y `MP_VER=4.10.5` en `upeu/infra/env.example`. Un commit.
- **A los 7 días sin incidencias:** borrar la copia local de la BD
  (`bd-copia-local.sh borrar midpoint_pre_4102`) y `~/upgrade-4.11/home-pre-F2.tgz`. Hasta F3, la
  copia ocupa disco: comprobar con `estado` que F3 tendrá sitio.

## 4. Vuelta atrás (objetivo: < 15 min)

El esquema no cambió (51/10), pero el `connectorRef` y lo que haya hecho 4.10.5 sí. Se vuelve a
la BD de antes, renombrando, que es inmediato.

| # | Paso | Comando | Verificación |
|---|---|---|---|
| R1 | Parar | `docker compose stop midpoint_server` | sin `midpoint_server` |
| R2 | BD de antes | `$W/bd-copia-local.sh restaurar 4102` (pide escribir `SI`; si sale «ABORTO», **no** se ha restaurado nada) | huella = la del paso 4; la fallida queda como `midpoint_fallida_<ts>` |
| R3 | Versión | `cp -p .env.bak-pre-4105 .env && grep '^MP_VER' .env` | `MP_VER=4.10.2` |
| R4 | Home | Solo si 4.10.5 cambió algo en el volumen (no se espera): `docker run --rm -i -v midpoint_midpoint_home:/v --user 0 --entrypoint tar postgres:16-bullseye -C /v -xzf - < ~/upgrade-4.11/home-pre-F2.tgz` | `keystore.jceks` presente |
| R5 | Arrancar 4.10.2 | `docker compose up -d`, esperar `healthy` | versión `4.10.2` en `m_node`; `ldap-connectorref.sh show` → 3.9.2 en uso y `available=t` |
| R6 | Recursos y tareas | `$W/test-recursos.sh` → 12/12; `tareas-ventana.sh reanudar …` las 8 | igual que antes de la ventana |

**Si la copia local tampoco sirve:** restaurar desde `s3://…/midpoint/upgrade/f2-4102/`
(runbook de backup, §Restaurar, **sin `-j`**). Ese dump **no lleva datos de auditoría**: la
auditoría posterior al último export mensual se perdería. Es el último recurso.

Tiempos de la vuelta atrás medidos en F1 (3-nov, lab): **245 s** de R1 a R6, de ellos 178 s del
test de recursos. Detalle en [`F1-RESULTADO-2026-11-03.md`](F1-RESULTADO-2026-11-03.md).
