# F1 · Ensayo completo en el laboratorio (192.168.15.150)

> **Ejecutado el 3-nov-2026 → [`F1-RESULTADO-2026-11-03.md`](F1-RESULTADO-2026-11-03.md)** (tiempos, hallazgos H1–H12 y
> criterio de salida). Diferencias con este texto: puerto **8096** (el 8085 lo usa el Zammad del lab),
> clon reducido (`LAB_MP_MEM_*`, `LAB_PG_*`) y **Oracle inalcanzable desde el `.150`**.

**Objetivo:**

- Ejecutar sobre una copia de PROD **exactamente** los pasos de [F2](F2-ventana-4.10.5.md) y
  [F3](F3-ventana-4.11.0.md), con el mismo orden y los mismos scripts.
- Cronometrar cada paso y ensayar las dos vueltas atrás.
- Salir con la lista de ❓ resuelta.

**Regla absoluta: el clon no puede escribir nunca en LDAP, Koha, Entra, Zammad ni Telegram
reales**, ni avisar al grupo de Telegram. El clon tiene las credenciales reales (el keystore del
home las descifra), así que el aislamiento va en tres capas independientes. Se aplican **antes**
del primer arranque.

| Capa | Qué | Cómo se comprueba |
|---|---|---|
| 1. Red | `lab-f1/aislamiento-red.sh aplicar`: la subred del clon (172.31.41.0/24) **solo** sale a Oracle LAMB `192.168.13.9:1521` (solo lectura) | `aislamiento-red.sh comprobar` → `AISLAMIENTO OK` (Oracle sí; LDAP .168/.169, Koha .136, Microsoft y Telegram no) |
| 2. midPoint | primer arranque con el **planificador parado**; luego `lab-f1/aislar-midpoint.sh aplicar`: LDAP, Koha, Zammad y Entra en `maintenance`; sin transportes de mensajes; 8 tareas suspendidas | `aislar-midpoint.sh comprobar` |
| 3. Simulación | Toda prueba de procesamiento va en `preview`. Los 8 Oracle tienen `create/update/delete` deshabilitados y ningún script de escritura (medido en PROD el 28-oct) | — |

Si la capa 1 no da `AISLAMIENTO OK`, **no se arranca el clon**.

## 0. Requisitos ❓ (comprobar el día 1, solo lectura en el lab)

```bash
source ~/.secrets/lab-identidad.env
sshpass -p "$LAB_PASS" ssh "$LAB_USER@$LAB_HOST" 'free -h; nproc; df -h / /u01 2>/dev/null; docker version --format "{{.Server.Version}}"; docker compose version; sudo -n true && echo SUDO_OK; docker ps --format "{{.Names}} {{.Ports}}"'
```

- **RAM:** PROD usa 10 GB para midPoint y 5 GB para Postgres. Si el lab no los tiene libres, rebajar
  `LAB_MP_MEM_MAX`/`LAB_MP_MEM_LIMIT` y anotar que los tiempos no son comparables.
- **Disco:** ~8 GB de BD restaurada (sin auditoría), ~8 GB más por cada copia local, ~3 GB de
  imágenes y ~3 GB del dump.
- `sudo` para `iptables`, Docker con la cadena `DOCKER-USER` y el puerto 8085 libre.
- **Datos personales (Ley 29733):** el dump contiene los datos de ~66.000 personas. El clon solo
  vive durante el ensayo; al terminar se borran volúmenes, dump y tar (§6). El acceso al lab ya
  está restringido a DTI ❓ (confirmarlo).

## 1. Montar el clon (día 1)

### 1.1 Datos: el backup de anoche de PROD

Se usa el backup diario: el dump de la BD **sin datos de auditoría** y el tar del home.
En la Mac:

```bash
source ~/.secrets/aws-iga-backup.env
B=upeu-iga-backups-360416501080; D=$(date -v-1d +%Y%m%d)   # o la fecha elegida
aws s3 ls "s3://$B/midpoint/db/$(date +%Y/%m)/" | grep "$D"     # elegir el .dump con su .sha256
# bajar dump + .sha256 + home + .sha256, y comprobar:
shasum -a 256 -c midpoint-db-<ts>.dump.sha256 && shasum -a 256 -c midpoint-home-<ts>.tar.gz.sha256
# copiarlos al lab (no son ficheros del repo); LAB_DIR=/u01/lab/mp411 ❓
```

### 1.2 Directorio, conectores, certs y `.env` del clon

En el lab, con `LAB_DIR=/u01/lab/mp411` y `W=<clon del repo en el lab>/upeu/infra/upgrade-4.11`:

```bash
mkdir -p $LAB_DIR && cd $LAB_DIR && chmod 700 .
tar -xzf midpoint-home-<ts>.tar.gz                       # -> home-var.<ts>.tar y home-host.<ts>.tar
mkdir host && tar -C host -xf home-host.<ts>.tar          # compose, .env, certs/, connectors/ de PROD
cp -a host/connectors host/certs .
# .env del clon: valores NUEVOS para la BD del lab; la contraseña del truststore es la de PROD
cat > .env <<EOF
POSTGRES_USER=midpoint
MP_DB_PASSWORD=$(openssl rand -hex 16)
MP_ADMIN_PASSWORD=$(openssl rand -hex 16)
MP_VER=4.10.2
MP_TRUSTSTORE_PASSWORD=<copiar de host/docker-compose.yml, trustStorePassword>
LAB_DIR=$LAB_DIR
MP_CONNECTORS_DIR=$LAB_DIR/connectors
LAB_PORT=8085
EOF
chmod 600 .env
```

`MP_ADMIN_PASSWORD` solo sirve para la creación inicial: el administrador del clon tiene la
contraseña de PROD (viene en la BD).

### 1.3 Variables de los scripts para el clon

```bash
cd $LAB_DIR
L="docker compose -f $W/lab-f1/docker-compose.yml --env-file $LAB_DIR/.env"
LW="$L -f $W/docker-compose.upgrade-window.yml"
L3="$LW -f $W/docker-compose.4.11.yml"
export PG_CONTAINER=mp411_data MP_CONTAINER=mp411_server MP_HOME_VOLUME=mp411_midpoint_home \
       MP_BASE=http://localhost:8085/midpoint
read -r -s -p "Contraseña REST administrator (la de PROD): " MP_REST_PASS; echo; export MP_REST_PASS
```

> En las tablas de F2/F3, `C`/`CW`/`C3` pasan a ser `LW`/`LW`/`L3`; `docker compose stop
> midpoint_server` pasa a `$L stop midpoint_server`; el contenedor de Postgres es `mp411_data`.
> `--pre-upgrade` (S3) **no** se ejecuta en el lab: ya está probado con
> `upeu/scripts/tests/test-backup-modes.sh`.

### 1.4 Red aislada, Postgres y restauración

```bash
$L up -d midpoint_data                      # crea la red mp411_net (subred fija)
sudo SUBNET=172.31.41.0/24 $W/lab-f1/aislamiento-red.sh aplicar
sudo $W/lab-f1/aislamiento-red.sh comprobar # -> AISLAMIENTO OK. Si no: PARAR.
docker cp midpoint-db-<ts>.dump mp411_data:/tmp/db.dump
time docker exec mp411_data pg_restore -U midpoint -d midpoint --no-owner --no-acl /tmp/db.dump   # en SERIE, nunca -j
docker exec mp411_data psql -U midpoint -d postgres -c "ALTER DATABASE midpoint SET enable_partitionwise_join = on"
docker exec mp411_data psql -U midpoint -d midpoint -tAc "select * from m_global_metadata; select count(*) from m_user"   # 51, 10 y ~66.1k
# home al volumen del clon (como root: en 4.10.x el contenedor es root)
docker volume create mp411_midpoint_home
docker run --rm -i -v mp411_midpoint_home:/v --entrypoint tar postgres:16-bullseye -C /v -xf - < home-var.<ts>.tar
docker run --rm -v mp411_midpoint_home:/v:ro --entrypoint ls postgres:16-bullseye -l /v/keystore.jceks /v/config.xml
```

### 1.5 Primer arranque (4.10.2, planificador parado) y capa 2

```bash
$LW up -d midpoint_server
until [ "$(docker inspect -f '{{.State.Health.Status}}' mp411_server)" = healthy ]; do sleep 10; done
$W/lab-f1/aislar-midpoint.sh aplicar        # 4 recursos en maintenance, sin transportes, 8 tareas suspendidas
$W/lab-f1/aislar-midpoint.sh comprobar
sudo $W/lab-f1/aislamiento-red.sh comprobar
$L up -d                                     # arranque normal: planificador en marcha, tareas ya suspendidas
```

## 2. Línea base en 4.10.2

| # | Qué | Comando | Anotar |
|---|---|---|---|
| B1 | Recursos | `$W/test-recursos.sh` | Los 8 Oracle deben dar `success`. Anotar lo que den los 4 en mantenimiento ❓ (¿`success` sin contactar o «maintenance»?) |
| B2 | Muestra fija | `$W/muestra-sim.sh generar 20 > muestra.oids` | nº de OIDs |
| B3 | SIM PRE-4102 | `muestra-sim.sh tarea pre-4102 muestra.oids --sin-reconcile`, POST a `$MP_BASE/ws/rest/tasks` y esperar | OID y duración |
| B4 | SIM recon Oracle PRE | `sed -e 's/ oid="3cb0c47a[^"]*"//' -e 's#<executionState>suspended#<executionState>runnable#' -e 's#<name>SIM pre-activacion#<name>F1 PRE-4102 SIM#' ~/…/upeu/tasks/trabajadores-preactivacion-2026-08-03/sim-recon-trabajadores-preview.xml` → POST | OID, duración y estadísticas. Lee **Oracle real** con ScriptedSQL bajo ConnId 1.6.0.0 |
| B5 | Foto | `snapshot-estado.sql` → `snap-base.tsv` | — |

## 3. Ensayo F2 (4.10.2 → 4.10.5), cronometrado

Ejecutar F2 §2 pasos 1–15 con las equivalencias de §1.3. Lo que se mide aquí sirve también para
F3:

- **Paso 4 `bd-copia-local.sh crear 4102`:** apuntar el tamaño y los segundos. Con el ritmo en
  MB/s se extrapola a los ~30–40 GB de PROD (sin auditoría en el lab, ❓ velocidad de disco
  distinta).
- **Paso 9:** el tiempo de arranque.
- **Paso 10 `ldap-connectorref.sh`:** que existe el 3.9.4 `available=t`, que el 3.9.2 queda
  `available=f` (comportamiento visto en mayo) y que el PATCH se verifica. Con LDAP en
  mantenimiento, el `test` puede no contactar: anotar qué devuelve.
- **Paso 12:** el texto exacto del log que indica que el planificador arrancó.
- **Paso 13:** con LDAP en mantenimiento, el canario de grupos DTI dejará operaciones pendientes:
  **no** ejecutarlo en el clon. El de ausencias (solo Oracle) sí.
- Después: **SIM POST-4105** (misma muestra, `--sin-reconcile`) y `muestra-sim.sh comparar
  <PRE-4102> <POST-4105>`. Recon de Oracle en preview: comparar con B4.

### 3.1 Ensayo de la vuelta atrás de F2

F2 §4 completo (R1–R6), cronometrado de punta a punta (objetivo < 15 min). Después, repetir el
avance a 4.10.5 (pasos 3–12) para seguir con F3. Así se ensaya también un segundo intento.

## 4. Ensayo F3 (4.10.5 → 4.11.0), cronometrado

Antes, con 4.10.5 en marcha: `MP_VER=4.11.0 $LW run --rm --no-deps --user 0 ninja pre-upgrade-check`
(F3 §1.3). Anotar la salida.

Ejecutar F3 §2 pasos 1–23 con las equivalencias. Lo que hay que mirar especialmente:

| ❓ a resolver | Dónde | Criterio |
|---|---|---|
| Duración de `run-sql --upgrade` de repositorio (cambios 52–67: columnas nuevas en `m_user`, tablas `m_projection_holder`…) y de auditoría | paso 11 | anotar; 67/16 al final |
| `ninja verify` de 4.11 sobre la BD migrada | tras el paso 11: `$L3 run --rm --no-deps ninja verify --report-style csv -o /opt/midpoint/var/export/verify-411.csv` | **0 críticos**; revisar `NECESSARY` |
| `initial-objects`: `--oid` con 39 valores, informes y tiempos | paso 13 | ningún OID de `nunca`/`revisar` en el informe de aplicación |
| midPoint 4.11 arranca como UID 1000 con el home `chown`, lee keystore y `ojdbc11` | pasos 9 y 14 | sin «not writable», sin errores de descifrado; Oracle `success` |
| **ConnId 1.7.0.0-M0** con ScriptedSQL 2.2.10 (×8), Koha 1.7.0, Zammad 0.2.0 (framework 1.5.2.0 embebido) y msgraph 1.2.0.0 | pasos 16–17 | los 4 conectores con `available=t`. Los 8 Oracle `success`. **SIM recon Oracle POST-411 = B4**. Koha, Zammad y Entra: al menos cargan (en mantenimiento no se contactan) |
| LDAP 3.10 | paso 15 | PATCH verificado; esquema del recurso no `broken` |
| Expresiones Groovy con 4.11 | paso 20 (`--sin-reconcile`) y recon Oracle | `comparar PRE-4102 POST-411` → `IGUALES` o diferencias explicadas. **0** «TrustDescriptor is required» y **0** errores de perfil de expresión en el log |
| `privilegedPrincipal = permissive` | paso 18 | PATCH 204 y verificado. Con un usuario administrador, en la GUI, una búsqueda avanzada con expresión ❓ funciona |
| Verificación de conectores firmados | log tras el paso 19 | **0** `SubscriptionComplianceException` / «not present in the current public list». ❓ Ver en la GUI si midPoint se cree «producción» (pie de página / About) |
| `data_init` normal con 4.11-alpine y UID 1000 | paso 19 | «Repository init is not needed» |
| Bloque `expressions` en `config.xml` | paso 14 | midPoint arranca; Groovy funciona (la SIM lo demuestra) |
| (opcional) ¿4.10.5 ignora el bloque `expressions` en `config.xml`? | aplicar `config-xml-safe-scripting.sh --apply` en el ensayo de F2 y arrancar 4.10.5 | si arranca sin error, el bloque puede ir ya en F2 |

### 4.1 Ensayo de la vuelta atrás de F3

F3 §4 completo, cronometrado (objetivo < 20 min). Con eso termina el clon en 4.10.5. Opcional:
repetir el avance a 4.11 y dejarlo arrancado un día para probar a mano la GUI y el MFA.

## 5. (Opcional) Etapa B: escritura real contra destinos DEL LAB

Solo si hay destinos de laboratorio equivalentes, y nunca contra los de PROD:

- OpenLDAP del lab (`LAB_LDAP_URL`) con el esquema de `upeu/ldap-schema`;
- Zammad del lab (`LAB_ZAMMAD_URL`);
- Koha de desarrollo (`koha-dev.env`).

Pasos para cada recurso:

1. PATCH de su `connectorConfiguration` (host, puerto, credenciales del lab) **en el clon**.
2. `EXTRA_ALLOW="ip:puerto"` en `aislamiento-red.sh aplicar` y `comprobar`.
3. Sacar **solo ese** recurso de mantenimiento.
4. Canario real de 1–2 usuarios.

Demuestra que 3.10, Koha 1.7.0 y Zammad 0.2.0 **escriben** bien bajo ConnId 1.7.0.0-M0. Si no
se hace, esa prueba queda para el canario de F3 (paso 21).

## 6. Cierre y limpieza

1. Rellenar la tabla de tiempos (abajo) y copiar los valores a las columnas «Tiempo ref.» de F2
   y F3.
2. Lista de ❓ resueltos o pendientes en `PLAN-Y-ROADMAP.md`.
3. **Borrar el clon:**
   ```bash
   $L down -v
   docker volume rm mp411_midpoint_home
   sudo $W/lab-f1/aislamiento-red.sh quitar
   shred -u $LAB_DIR/*.dump $LAB_DIR/*.tar* 2>/dev/null; rm -rf $LAB_DIR
   ```
   En la Mac, borrar también el dump y el tar descargados.
4. **Criterio de salida a F2:**
   - 0 bloqueos sin resolver;
   - las dos vueltas atrás dentro de su objetivo;
   - SIM POST igual a la PRE (o diferencias explicadas);
   - 8/8 Oracle `success` en 4.11;
   - los 4 conectores propios `available=t`.

## Tiempos medidos (rellenar)

| Paso | Tiempo | Notas |
|---|---|---|
| `pg_restore` del dump diario (en serie) | | |
| `bd-copia-local.sh crear` (tamaño / s / MB/s) | | |
| Arranque 4.10.2 → `healthy` | | |
| Arranque 4.10.5 → `healthy` | | |
| PATCH LDAP 3.9.4 + test | | |
| Vuelta atrás F2 (R1–R6) | | |
| `chown -R` del home | | |
| `run-sql --upgrade` repositorio | | |
| `run-sql --upgrade` auditoría | | |
| `initial-objects` (informe + aplicar) | | |
| Arranque 4.11.0 → `healthy` | | |
| PATCH LDAP 3.10 + test | | |
| SIM muestra (PRE / POST) | | |
| SIM recon Oracle Trabajadores (4.10.2 / 4.11) | | |
| Vuelta atrás F3 (R1–R6) | | |
