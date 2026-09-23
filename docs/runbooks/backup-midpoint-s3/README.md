# Backup de MidPoint PROD en S3

> **Lo que hay que recordar:** los backups de MidPoint están en
> **`s3://upeu-iga-backups-360416501080/midpoint/`**, en la cuenta AWS **`upeu-repo`
> (360416501080), región `us-east-2`**. MidPoint corre on-prem (`midpoint.upeu`,
> 192.168.15.166), pero su backup vive en AWS.

Creado el 2026-09-23. Hasta ese día MidPoint **no tenía ningún backup programado**: el único
dump era uno manual del 16-jul, guardado en el mismo disco que la base de datos.

## Qué se guarda, dónde y cuánto tiempo

| Prefijo en el bucket | Contenido | Frecuencia | Retención |
|---|---|---|---|
| `midpoint/db/AAAA/MM/midpoint-db-<ts>.dump` | `pg_dump -Fc` de la BD **sin datos de auditoría ni de simulaciones** (la estructura de esas tablas sí va) | diario, 22:30 | 35 días |
| `midpoint/home/AAAA/MM/midpoint-home-<ts>.tar.gz` | `/opt/midpoint/var` del contenedor (**`keystore.jceks`**, `config.xml`, conectores, `logback.xml`...) y `/opt/midpoint` del host (`docker-compose.yml`, `.env`, `certs/`) | diario | 35 días |
| `midpoint/audit/ma_audit_AAAAMM.dump` | Las 3 particiones de auditoría de un mes (`event`, `delta`, `ref`) | mensual, **antes** de borrarlas de la BD | **No expira.** Pasa a Deep Archive a los 30 días |

Cada archivo tiene al lado un **`<archivo>.sha256`**. El script solo lo escribe cuando el
archivo pasó todas las verificaciones.

> 🔴 **Un dump sin su `.sha256` al lado no está verificado** (por ejemplo, si `pg_dump`
> murió a medias). No hay que restaurar desde él.

**Por qué el keystore importa tanto:** MidPoint cifra con `keystore.jceks` los valores
protegidos de la base de datos (contraseñas de los conectores, entre otros). Un dump sin su
keystore se restaura, pero los recursos no pueden conectar.

## Cómo funciona

| Pieza | Dónde |
|---|---|
| Script | `upeu/scripts/backup-midpoint-s3.sh` (en PROD: `~/midPointEcosystem/upeu/scripts/`) |
| Cron diario | `/etc/cron.d/midpoint-backup-s3` (copia en `upeu/scripts/cron/`) |
| Retención de auditoría | `upeu/scripts/audit-partition-maintenance.sh`, cron `/etc/cron.d/midpoint-audit-partition-maintenance`, día 1 a las 03:00 |
| Credenciales en el servidor | `/home/juansanchez/.config/midpoint-backup/backup.env` (600) |
| Credenciales en la Mac | `~/.secrets/aws-iga-backup.env` |
| Log | `/home/juansanchez/midpoint-backup.log` |
| Imagen de la CLI de AWS | `amazon/aws-cli:2.36.50` (la CLI no está instalada en el host) |

- **La BD va a S3 en streaming** (`pg_dump | S3`), sin pasar por el disco local. El dump
  pesa ~2,6 GB (los `fullobject` apenas comprimen) y el servidor no tiene espacio para
  prepararlo en local. Tarda unos 9 minutos.
- **Verificación antes de marcar un dump como bueno:**
  - el tamaño en S3 tiene que coincidir con los bytes enviados;
  - se descarga el principio del archivo y `pg_restore -l` tiene que listar datos de
    `m_user`, `m_shadow_*`, `m_resource`, `m_role`, `m_org`, `m_system_configuration` y
    `m_assignment`.
- **Auditoría:** en la BD quedan los **2 últimos meses completos más el mes en curso**. El día 1
  de cada mes, `audit-partition-maintenance.sh` exporta a S3 los meses más viejos y **solo si
  la exportación queda verificada** hace el DROP. Si la exportación falla, no borra nada y
  manda una alerta.

### Avisos (grupo de Telegram «SciBack · Pulso»)

- 🔴 **Si falla cualquier paso**, llega un mensaje con el paso que falló.
- 🟢 **Todos los lunes llega un resumen aunque todo vaya bien.**
  **Si un lunes no llega, el backup dejó de correr** (se borró el cron, cayó el servidor,
  se venció la clave...). Es el único aviso posible cuando el backup muere en silencio.

### Permisos del usuario IAM `midpoint-backup-onprem`

Solo puede `PutObject`, `GetObject` y `ListBucket` dentro de `midpoint/*`. Tiene un **Deny
explícito para borrar**, tanto objetos como versiones, y para cambiar el ciclo de vida, el
versionado o la política del bucket.

Además, el bucket tiene el versionado activo. Así, ni un error ni un servidor comprometido
pueden destruir los backups: como mucho suben una versión nueva, y la anterior sigue ahí
30 días.

El bucket también tiene el acceso público bloqueado, cifrado SSE-S3, una política que rechaza
cualquier acceso sin TLS y etiquetas (`Proyecto=IGA-MidPoint`, `Runbook=...`) para que
cualquiera que lo vea en la consola sepa qué es.

## Comprobar que está vivo

Desde la Mac:

```bash
source ~/.secrets/aws-iga-backup.env
aws s3 ls "s3://$IGA_BACKUP_BUCKET/midpoint/db/$(date +%Y/%m)/" | tail -4
```

Debe haber un `.dump` y su `.sha256` de anoche.

En el servidor:

```bash
tail -5 ~/midpoint-backup.log
```

## Restaurar

> ⚠️ **Restaurar sobre PROD reemplaza la BD viva.** Antes de hacerlo, probar el mismo dump
> en un Postgres desechable (sección siguiente) y leer
> [`PROTOCOLO-PRE-EJECUCION-PROD.md`](../PROTOCOLO-PRE-EJECUCION-PROD.md).

### 1. Bajar el dump y comprobar su marca

```bash
source ~/.secrets/aws-iga-backup.env       # puede leer midpoint/*; para restore-object de Deep Archive usar aws-upeu-repo.env
B=upeu-iga-backups-360416501080
K=midpoint/db/2026/09/midpoint-db-<ts>.dump
aws s3 cp "s3://$B/$K" . && aws s3 cp "s3://$B/$K.sha256" .
shasum -a 256 -c "$(basename "$K").sha256"   # debe decir OK
```

### 2. Prueba en un Postgres desechable (sin tocar PROD)

```bash
docker run -d --name mp-restore -e POSTGRES_PASSWORD=x -e POSTGRES_USER=midpoint -e POSTGRES_DB=midpoint postgres:16
docker exec mp-restore sh -c 'until pg_isready -U midpoint; do sleep 1; done'
docker cp midpoint-db-<ts>.dump mp-restore:/tmp/db.dump
docker exec mp-restore pg_restore -U midpoint -d midpoint --no-owner --no-acl /tmp/db.dump   # SIN -j: ver nota

docker exec mp-restore psql -U midpoint -d midpoint -c "select count(*) from midpoint.m_user"
docker rm -f mp-restore && rm -f midpoint-db-*.dump*   # son datos personales (Ley 29733): no dejarlos en la Mac
```

> 🔴 **Restaurar en serie, nunca con `pg_restore -j`.** En paralelo, `pg_restore` puede
> cargar los datos de una partición (`m_shadow_<oid>_*`) **después** de crear el trigger
> `insert_object_oid` del padre, y esas filas fallan. Medido el 23-sep: con `-j 4` dio 34
> errores y en serie 0. El restore en serie tarda unos 2 minutos, así que `-j` no aporta
> nada.

### 3. Restaurar en el servidor

Es la misma idea, contra el contenedor `midpoint-midpoint_data-1`, **con MidPoint detenido**
(`docker compose stop midpoint_server` en `/opt/midpoint`):

1. `dropdb` + `createdb` (o una BD nueva).
2. `pg_restore`.
3. Reponer `keystore.jceks` desde el `midpoint-home-<ts>.tar.gz` **del mismo día**.
4. Arrancar MidPoint.
5. Comprobar el test connection de todos los recursos.

El tar del home contiene dos tar internos:
- `home-var.<ts>.tar` es `/opt/midpoint/var`;
- `home-host.<ts>.tar` es `/opt/midpoint`.

### 4. Consultar auditoría de un mes que ya salió de la BD

Pasa a **Deep Archive a los 30 días**. Antes de poder bajarla hay que pedir su recuperación,
**y tarda hasta 12 horas**:

```bash
aws s3api restore-object --bucket "$B" --key midpoint/audit/ma_audit_202606.dump \
  --restore-request '{"Days":7,"GlacierJobParameters":{"Tier":"Standard"}}'
aws s3api head-object --bucket "$B" --key midpoint/audit/ma_audit_202606.dump --query Restore   # esperar ongoing-request="false"
```

Después se restaura **encima de una BD ya restaurada** (paso 2), que es la que aporta las
tablas padre `ma_audit_*`.

Si ese dump diario es de cuando el mes todavía estaba en la BD, trae sus particiones
**vacías** y hay que borrarlas primero. Si no están, el `DROP ... IF EXISTS` no hace nada:

```bash
M=202606
docker exec mp-restore psql -U midpoint -d midpoint -c \
  "DROP TABLE IF EXISTS midpoint.ma_audit_delta_$M, midpoint.ma_audit_ref_$M, midpoint.ma_audit_event_$M;"
docker cp ma_audit_$M.dump mp-restore:/tmp/a.dump
docker exec mp-restore pg_restore -U midpoint -d midpoint --no-owner --no-acl /tmp/a.dump
docker exec mp-restore psql -U midpoint -d midpoint -c "select count(*) from midpoint.ma_audit_event_$M"
```

Salen unos 13 errores **esperables**:
- `... already exists`, en los índices;
- `multiple primary keys ...`.

Aparecen porque, al enganchar la partición a su tabla padre, Postgres crea él mismo esos
índices y luego el dump intenta crearlos otra vez. **Lo que cuenta son los conteos.**

## Pruebas hechas al montarlo (2026-09-23)

| Prueba | Resultado |
|---|---|
| Permisos IAM | `PutObject` y `HeadObject` en `midpoint/` ✅. **Borrar ❌** (Deny explícito). Escribir fuera de `midpoint/` ❌. Listar la raíz ❌ |
| Primer backup diario | 2,6 GB de BD (153 tablas con datos) + 132 MB de home, **8 min 44 s**, verificados, con sus `.sha256` |
| Descarga + `shasum -c` en la Mac | OK en los dos archivos |
| **Restore real** (Postgres 16 desechable, en serie) | **0 errores.** Idéntico a PROD: 65.858 usuarios, 109 roles, 191 orgs, 12 recursos, 291.844 assignments, 35 tasks. Shadows: 395.472 frente a 395.471 (uno se borró después del dump) |
| Keystore en el home | `keystore.jceks`, `config.xml`, `docker-compose.yml` y `.env` presentes |
| Export de auditoría (junio) | 144 MB, 56 s. Restaurado encima: 30.636 eventos, 39.075 deltas, 0 refs, **igual que PROD** |
| Alerta de fallo | Se disparó de verdad en el primer intento: la verificación rechazó un dump porque `m_shadow` está particionada. Era un error del script, corregido |
| `audit-partition-maintenance.sh --dry-run` | Con retención 2: exportaría y luego borraría `202606`. El 1-oct le tocarán `202606` y `202607` |

Los datos de prueba se borraron de la Mac al terminar.

## Costes

Son unos pocos dólares al mes:
- ~35 dumps de ~2,6 GB en S3 Standard: ~90 GB, unos 2 USD al mes;
- la auditoría en Deep Archive: ~0,001 USD por GB al mes.

La subida desde on-prem no se paga.

## Si hay que cambiar algo

- **Rotar la clave:**
  1. `aws iam create-access-key --user-name midpoint-backup-onprem` con el perfil `upeu-repo`.
  2. Actualizar `backup.env` en el servidor y `~/.secrets/aws-iga-backup.env` en la Mac.
  3. Borrar la clave vieja.
- **Cambiar los meses de auditoría que quedan en la BD:** variable `RETENTION_MONTHS` en
  `audit-partition-maintenance.sh` (hoy 2). **Hay que medir el disco antes de subirla:** la
  auditoría crece unos 11 GB al mes.
