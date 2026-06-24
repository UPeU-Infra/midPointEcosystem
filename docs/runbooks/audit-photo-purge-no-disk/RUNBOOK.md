# RUNBOOK — Recuperar ~35G de auditoría MidPoint SIN ampliar disco

> Estado: **DISEÑO — NO EJECUTADO.** No tocar PROD hasta confirmación explícita del usuario,
> con backup verificado y MidPoint quiescente. Este documento es para revisión.
>
> Host: PROD `192.168.15.166` (`midpoint-prod`, user `juansanchez`). MidPoint 4.10.2 nativo (Sqale),
> Postgres en contenedor `midpoint-midpoint_data-1`. Disco raíz LVM `ubuntu-vg/ubuntu-lv` ~67G al 97%.
> Causa: `ma_audit_delta_default` ≈ 35G (3.1G heap + 32G TOAST), ~50% de deltas con foto JPEG base64.

---

## 0. Resumen ejecutivo y recomendación

| | OPCIÓN 1 — Redactar foto, preservar traza | OPCIÓN 2 — TRUNCATE total del subsistema audit |
|---|---|---|
| Espacio recuperado | ~32G (el TOAST de fotos); conserva ~3-6G de traza textual | ~38G (todo el subsistema) |
| Riesgo WAL/PANIC | Bajo (export por stream externo + TRUNCATE, no UPDATE in-place) | Mínimo (TRUNCATE casi no genera WAL) |
| Traza de auditoría | **Preservada** (sin el binario JPEG) | **Se pierden los ~14 días** en disco |
| Complejidad / tiempo | Alta (export ninja + redacción + reimport) | Muy baja (segundos) |
| ISO 27001 A.8.15 | Óptimo: conserva "qué cambió y quién" | Aceptable con justificación + respaldo externo |

**RECOMENDACIÓN: OPCIÓN 1 vía ninja export-audit → redactar la foto en el archivo exportado (FUERA del disco lleno) → DROP de las particiones `_default` (no UPDATE in-place) → recrear particiones limpias → import-audit del archivo redactado.**

Motivos:
1. La auditoría de un IGA tiene valor probatorio en el **delta textual** (quién cambió qué atributo), no en el JPEG. Redactar la foto preserva el valor de cumplimiento y recupera el 90%+ del espacio.
2. La redacción se hace **sobre el archivo exportado**, nunca con `UPDATE`/`regexp_replace` sobre el `bytea` en la tabla (eso generaría ~32G de WAL + dead tuples → PANIC con disco lleno). Es la objeción correcta del análisis previo.
3. El export se streamea a un destino EXTERNO (la Mac o un host con disco), nunca al disco lleno de PROD.
4. La recuperación física se hace con **DROP/recreate de partición**, que es el mecanismo **canónico y soportado por Evolveum** para purga rápida de auditoría — NO con `VACUUM FULL`/`pg_repack` (que exigen ~tamaño-de-tabla libre, inviable sin disco).

Si el usuario decide que NO necesita los 14 días de traza histórica, **OPCIÓN 2 es legítima, instantánea y de riesgo casi nulo**; basta documentar la justificación de gobernanza (§7) y conservar el respaldo R1Soft + un export ninja previo como evidencia archivada.

---

## 1. Verificación del esquema real (Sqale audit 4.10) — con fuentes

Fuente primaria: `config/sql/native/postgres-audit.sql` del repo oficial Evolveum (rama master, válido para 4.10.x; la última `apply_audit_change` es la #12).
- https://github.com/Evolveum/midpoint/blob/master/config/sql/native/postgres-audit.sql
- Doc: https://docs.evolveum.com/midpoint/reference/repository/native-audit/

### 1.1 Tablas del subsistema de auditoría
Tres tablas, **todas particionadas `PARTITION BY RANGE (timestamp)`**:

| Tabla | Rol | PK | Partición por defecto |
|---|---|---|---|
| `ma_audit_event` | evento top-level (quién, qué, cuándo, outcome) | `(id, timestamp)` | `ma_audit_event_default` |
| `ma_audit_delta` | deltas serializados + fullResult | `(recordId, timestamp, checksum)` | `ma_audit_delta_default` |
| `ma_audit_ref` | referencias del evento | `(id, timestamp)` | `ma_audit_ref_default` |

Tabla auxiliar: `m_global_metadata` (lleva `schemaAuditChangeNumber`). **No se toca.**

### 1.2 ¿Dónde vive la foto?
- En `ma_audit_delta`, columna **`delta BYTEA`** (y `fullResult BYTEA`). Cita textual del DDL:
  `-- @description: Serialized delta data.  delta BYTEA,`
- Es un **ObjectDelta serializado**. Por defecto en native repo se serializa en **JSON** (NO comprimido):
  > "New audit stores serialized objects in `ma_audit_delta` table, in the columns `delta` and `fullResult`. … it defaults to JSON for the new audit. … **New audit does not compress these columns.**" — doc native-audit, sección de migración.
- El JPEG aparece como texto base64 dentro de ese JSON serializado:
  - en deltas de MODIFY del **foco** → propiedad nativa `jpegPhoto` (`c:UserType/jpegPhoto`);
  - en deltas de MODIFY del **shadow** (el origen real del bloat, recon Entra diario) → atributo de recurso `ri:photo` / `attributes/photo`.
- Como no está comprimido y supera el umbral TOAST (~2KB), Postgres lo empuja al **TOAST** de la partición → de ahí los 32G de TOAST en `ma_audit_delta_default`.

### 1.3 Particionamiento real en PROD (hipótesis a confirmar en §2)
El script base SOLO crea las particiones `*_default`. Si en PROD **nunca** se ejecutó `audit_create_monthly_partitions(...)`, **todo** el audit está en `ma_audit_event_default` / `ma_audit_delta_default` / `ma_audit_ref_default`. Esto es consistente con que el bloat esté en `ma_audit_delta_default`. **Confirmar en §2** antes de cualquier acción.

### 1.4 FKs (clave para el orden de borrado)
FK por-partición con `ON DELETE CASCADE`:
```
ma_audit_delta_default_fk: (recordId,timestamp) REFERENCES ma_audit_event_default (id,timestamp) ON DELETE CASCADE
ma_audit_ref_default_fk:   (recordId,timestamp) REFERENCES ma_audit_event_default (id,timestamp) ON DELETE CASCADE
```
→ Orden de borrado: primero dependientes (`delta`, `ref`), luego `event`. (El CASCADE actuaría en DELETE; para DROP/TRUNCATE respetamos el orden explícitamente.)

### 1.5 ¿Es seguro truncar `ma_audit_*` para MidPoint?
**Sí.** La auditoría es **append-only y está desacoplada del repositorio de identidad** (`m_*`). MidPoint no lee `ma_audit_*` para operar IGA (provisioning, recompute, clockwork, RBAC); solo escribe eventos y los lee la GUI/reportes de auditoría. Vaciar `ma_audit_*` borra la traza histórica pero **no afecta** focos, shadows, assignments, tasks ni resources. (Por eso el propio diseño Evolveum soporta tener el audit en **base de datos separada** — postgres-audit.sql empieza con `CREATE SCHEMA … AUTHORIZATION CURRENT_USER` y "For separate audit use this in a separate database".)

### 1.6 Método CANÓNICO de purga/recreación soportado por Evolveum
La doc oficial reconoce DOS mecanismos:
1. **Cleanup task + cleanupPolicy** (`auditRecords/maxAge` o `maxRecords`): hace **DELETE**. Problema admitido por la propia doc: "PostgreSQL needs to reclaim the empty space … you may need to run `VACUUM FULL` eventually, which requires a table lock." → **NO recupera disco al SO sin VACUUM FULL/repack** → inviable aquí.
2. **Particiones (recomendado para cleanup rápido):**
   > "The main benefit of audit partitioning is **fast audit cleanup**. … With partitions you can **virtually instantly drop or detach partitions** … which makes the audit data cleanup and/or archival much easier."

   Drop soportado y documentado (orden dependientes-primero):
   ```sql
   drop table ma_audit_ref_YYYYMM;
   drop table ma_audit_delta_YYYYMM;
   drop table ma_audit_event_YYYYMM;
   ```
3. **Migración / export-import** vía **Ninja** (`export-audit` / `import-audit`, desde 4.4.1): serializa el audit a archivo (JSON por defecto) y lo reimporta preservando IDs. Es la herramienta soportada para mover/transformar audit.

> Conclusión: la combinación soportada para "recuperar disco YA, sin disco extra, preservando traza redactada" es **ninja export-audit (a destino externo) + DROP de la partición default + recrear default + ninja import-audit del archivo redactado**. El DROP de la default es la pieza que devuelve los archivos de datos al SO al instante (igual que TRUNCATE, casi sin WAL).

---

## 2. Diagnóstico previo (READ-ONLY, seguro en PROD)

> Estos comandos NO modifican nada. Ejecutarlos para confirmar las hipótesis antes de planear la ventana.

```bash
source ~/.secrets/midpoint-upeu.env
PSQL='docker exec -i midpoint-midpoint_data-1 psql -U midpoint -d midpoint'

# 2.1 Espacio en disco y mountpoint del LV
sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
  "df -h / ; echo '---' ; sudo lvs ubuntu-vg/ubuntu-lv 2>/dev/null"

# 2.2 ¿Existen particiones mensuales o todo está en _default?
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "$PSQL -c \"
  select i.inhrelid::regclass::text as partition, t.reltuples::bigint rows_estimate
  from pg_inherits i join pg_class t on t.oid=i.inhrelid
  where inhparent='ma_audit_event'::regclass order by partition;\""

# 2.3 Tamaño real de cada tabla/partición de audit (heap + toast + índices)
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "$PSQL -c \"
  select relname, pg_size_pretty(pg_total_relation_size(relid)) total,
         pg_size_pretty(pg_relation_size(relid)) heap
  from pg_catalog.pg_statio_user_tables
  where relname like 'ma_audit_%' order by pg_total_relation_size(relid) desc;\""

# 2.4 Rango temporal y nº de eventos (para dimensionar el export)
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "$PSQL -c \"
  select count(*) events, min(timestamp) oldest, max(timestamp) newest from ma_audit_event;\""

# 2.5 cleanupPolicy vigente (P7D actual según memoria)
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "$PSQL -c \"
  select count(*) deltas, count(delta) with_delta from ma_audit_delta;\""
```

**Criterio de decisión tras §2:**
- Si TODO está en `_default` (caso esperado) → procede el DROP de las 3 particiones default (OPCIÓN 1 §5 ó OPCIÓN 2 §6).
- Si ya hay particiones mensuales → adapta: dropea solo las particiones viejas problemáticas; las recientes se exportan/redactan/reimportan o se dejan.

---

## 3. Precondiciones comunes (AMBAS opciones)

1. **Aplicar primero la Parte A** (commit `c71734e`, `cached=false` en `ri:photo`) — corta la FUENTE del rebloat. Si no, el recon Entra diario volverá a llenar. Aplicar Parte A a PROD ANTES de recuperar espacio.
2. **Quiescer MidPoint (cero escritura de audit):**
   - Suspender todas las tasks/schedulers que generan audit (recompute, recon Entra/Koha/LDAP, import). Vía REST o GUI: poner el nodo en modo no-scheduling, o suspender tareas activas.
   - **Detener el contenedor `midpoint_server`** durante el DROP/TRUNCATE de particiones para garantizar que ningún INSERT de audit choque con el DDL. (El Postgres `midpoint-midpoint_data-1` permanece arriba.)
3. **Backup verificado (doble):**
   - Confirmar último punto **R1Soft (CDP)** del host < 24h y restaurable.
   - Export ninja del audit a destino externo (sirve de respaldo Y de insumo de OPCIÓN 1). Ver §4.
   - **NO** `pg_dump` de las tablas de audit al disco local de PROD (no hay espacio). El stream va FUERA.
4. **Ventana:** baja actividad. Comunicar a DTI (workstream ISO 27001) la operación sobre logs de auditoría (§7).
5. **Espacio del destino externo:** el export ninja `-z` (zip) de ~3-6G de traza textual + ~16G de fotos base64 comprimidas. Reservar ≥30G libres en el destino (Mac o host con disco). Verificar `df -h` del destino ANTES.

---

## 4. Export del audit a destino EXTERNO (insumo de OPCIÓN 1 y respaldo de ambas)

> El export NUNCA escribe al disco lleno de PROD. Se streamea a la Mac vía SSH, o ninja escribe a un volumen/disco externo montado. Aquí: ninja escribe a stdout/archivo en un FS con espacio.

**Variante A — ninja dentro del contenedor, archivo a un bind-mount con espacio externo (preferida):**
```bash
# (En PROD) ninja vive en la imagen midpoint. Ejecutarlo apuntando MIDPOINT_HOME real.
# IMPORTANTE: -o debe apuntar a un FS con espacio (NO al disco raíz lleno).
# Si no hay disco local libre, montar temporalmente un NFS/USB, o usar Variante B.
docker exec -e MIDPOINT_HOME=/opt/midpoint/var midpoint_server \
  /opt/midpoint/bin/ninja.sh -v export-audit -z -o /tmp-ext/audit-export-full.zip
```

**Variante B — stream a la Mac sin tocar disco de PROD (si no hay FS externo en el host):**
```bash
# ninja no streamea a stdout directamente; export a una FIFO y pipe por SSH.
# Alternativa robusta: export filtrado en CHUNKS por timestamp para que cada zip quepa en /tmp
# y se vaya copiando a la Mac y borrando. Ej. por día:
for d in 2026-06-10 2026-06-11 2026-06-12 ; do
  docker exec -e MIDPOINT_HOME=/opt/midpoint/var midpoint_server \
    /opt/midpoint/bin/ninja.sh -v export-audit -z -o /tmp/audit-$d.zip \
    -f "% timestamp >= \"$d\" and timestamp < \"$(date -I -d "$d +1 day")\""
  docker cp midpoint_server:/tmp/audit-$d.zip - | ssh atisbo@mac-destino "cat > ~/audit-backup/audit-$d.zip"
  docker exec midpoint_server rm -f /tmp/audit-$d.zip   # liberar /tmp tras copiar
done
```
> NOTA: confirmar ruta real de ninja y MIDPOINT_HOME en la imagen 4.10.2 (`docker exec midpoint_server ls /opt/midpoint/bin`). El path puede variar.

**Verificación del export:** descomprimir un chunk en la Mac y confirmar que es JSON con eventos+deltas legibles.

---

## 5. OPCIÓN 1 — Redactar foto, preservar traza (RECOMENDADA)

### 5.1 Redacción de la foto EN EL ARCHIVO exportado (en la Mac, no en PROD)
El export es JSON. La foto está como propiedad base64 en cada delta serializado. Redactar = sustituir el contenido base64 por un marcador, conservando el resto del delta (qué atributo cambió, quién, cuándo).

> Por qué NO en SQL: redactar in-place exigiría `UPDATE ma_audit_delta SET delta=...` decodificando bytea→text, parseando JSON, borrando el nodo, re-codificando. Eso genera ~32G de WAL + dead tuples → **PANIC con disco lleno**. La redacción a nivel de archivo evita todo eso.

```bash
# En la Mac. Descomprimir, redactar el nodo de foto, recomprimir.
# El nodo objetivo en el JSON del delta es la propiedad jpegPhoto (foco) y/o el attribute photo (shadow ri:photo).
# La foto es un string base64 largo (>10KB). Estrategia: reemplazar el valor base64 del nodo por "REDACTED".

cd ~/audit-backup
for z in audit-*.zip ; do
  tmp=$(mktemp -d) ; unzip -q "$z" -d "$tmp"
  # Ajustar el/los nombres de archivo JSON segun lo que produzca ninja (inspeccionar primero).
  for jf in "$tmp"/*.json ; do
    # Redacción robusta por jq: poner a null/marcador cualquier valor de jpegPhoto y de attribute photo.
    # (El JSON exacto de ninja debe inspeccionarse; este es el patrón. Si la estructura no es jq-friendly,
    #  usar el fallback regex de abajo.)
    python3 redact_photo.py "$jf"
  done
  ( cd "$tmp" && zip -q -r "$OLDPWD/redacted-$z" . )
  rm -rf "$tmp"
done
```

`redact_photo.py` (patrón de redacción — ajustar a la estructura real del export tras inspección):
```python
import sys, re
# Redacta valores base64 largos asociados a foto, sin romper el resto del JSON.
# Patrón: cualquier cadena base64 > 8KB la sustituimos por marcador. Conservador: limitar a contexto de "jpegPhoto"/"photo".
path = sys.argv[1]
data = open(path, encoding="utf-8").read()
# 1) jpegPhoto (foco nativo) y 2) attribute photo (ri:photo en shadow). Cadena base64 larga entre comillas.
#    Reemplaza solo strings >8000 chars (las fotos), preservando metadatos cortos.
def repl(m):
    return '"__PHOTO_REDACTED__"'
data = re.sub(r'"[A-Za-z0-9+/=\s]{8000,}"', repl, data)
open(path, "w", encoding="utf-8").write(data)
print(f"redacted {path}")
```
> El regex >8000 chars apunta SOLO al binario base64 (las fotos ~68KB → ~90K chars base64). Los valores textuales normales del delta (nombres, OIDs, fechas) quedan intactos. **Validar** en un chunk pequeño antes del lote: confirmar que el delta sigue siendo JSON válido y que el cambio de atributo (p.ej. "photo modified") sigue legible, solo sin el binario.

### 5.2 Recuperación física del espacio (DROP de la partición default)
> Esto es lo que devuelve los 35G al SO. Casi sin WAL (DROP no escribe fila por fila). Soportado por Evolveum (§1.6).

```bash
# MidPoint server DETENIDO (§3.2). Postgres ARRIBA.
PSQL='docker exec -i midpoint-midpoint_data-1 psql -U midpoint -d midpoint'

# 5.2.1 (Opcional, recomendado) tag git + nota del estado.
# 5.2.2 DROP en orden de dependencia (dependientes primero). Cada DROP libera sus archivos al instante.
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "$PSQL -c '
  BEGIN;
  DROP TABLE ma_audit_ref_default;
  DROP TABLE ma_audit_delta_default;
  DROP TABLE ma_audit_event_default;
  COMMIT;'"

# 5.2.3 Recrear las particiones default vacías (idénticas al script oficial postgres-audit.sql).
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "$PSQL -c '
  CREATE TABLE ma_audit_event_default PARTITION OF ma_audit_event DEFAULT;
  CREATE TABLE ma_audit_delta_default PARTITION OF ma_audit_delta DEFAULT;
  CREATE TABLE ma_audit_ref_default   PARTITION OF ma_audit_ref   DEFAULT;
  ALTER TABLE ma_audit_delta_default ADD CONSTRAINT ma_audit_delta_default_fk
    FOREIGN KEY (recordId, timestamp) REFERENCES ma_audit_event_default (id, timestamp) ON DELETE CASCADE;
  ALTER TABLE ma_audit_ref_default ADD CONSTRAINT ma_audit_ref_default_fk
    FOREIGN KEY (recordId, timestamp) REFERENCES ma_audit_event_default (id, timestamp) ON DELETE CASCADE;'"
```
> Alternativa a DROP: `TRUNCATE ma_audit_event, ma_audit_delta, ma_audit_ref;` (CASCADE implícito por FK). TRUNCATE también libera archivos al instante y casi sin WAL, y conserva la definición de partición (no hay que recrearla). **TRUNCATE de las 3 tablas padre es más simple que DROP+recreate y igualmente recupera el disco.** Preferir TRUNCATE salvo que se quiera dropear particiones mensuales específicas.

```bash
# VARIANTE TRUNCATE (preferida por simplicidad — recupera disco igual):
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "$PSQL -c \
  'TRUNCATE TABLE ma_audit_event, ma_audit_delta, ma_audit_ref;'"
```

### 5.3 Reimport de la traza redactada
```bash
# Reactivar disco confirmado libre (df). Copiar los redacted-*.zip de la Mac a un FS con espacio del host
# (ahora ya hay disco). Reimportar con ninja (preserva IDs originales).
docker exec -e MIDPOINT_HOME=/opt/midpoint/var midpoint_server \
  /opt/midpoint/bin/ninja.sh -v import-audit -z -i /tmp-ext/redacted-audit-export-full.zip
# (o por chunks, mismo for que en §4 con import-audit)
```
> Si tras el reimport el `id` sequence quedara desfasado, alinear con:
> `select setval(pg_get_serial_sequence('ma_audit_event','id'), (select max(id) from ma_audit_event));`

### 5.4 Compactar metadatos (NO la tabla grande)
```bash
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "$PSQL -c \
  'VACUUM ANALYZE ma_audit_event; VACUUM ANALYZE ma_audit_delta; VACUUM ANALYZE ma_audit_ref;'"
```
> Tras TRUNCATE/DROP no hay dead tuples masivos que recuperar; el VACUUM ANALYZE solo refresca estadísticas. No requiere espacio temporal grande.

---

## 6. OPCIÓN 2 — TRUNCATE limpio de todo el subsistema audit

> Recupera ~38G al instante. Cero riesgo de WAL/PANIC. Pierde los ~14 días de traza en disco
> (que quedan respaldados en el export ninja externo del §4 si se ejecutó). Audit arranca de cero.

```bash
# Precondiciones §3 cumplidas (Parte A aplicada, MidPoint server detenido, R1Soft OK,
# export ninja externo §4 hecho como evidencia archivada).
PSQL='docker exec -i midpoint-midpoint_data-1 psql -U midpoint -d midpoint'

# 6.1 TRUNCATE de las 3 tablas padre. El FK ON DELETE CASCADE no aplica a TRUNCATE,
#     por eso se truncan juntas (o usar CASCADE). Casi cero WAL, libera archivos al SO al instante.
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "$PSQL -c \
  'TRUNCATE TABLE ma_audit_event, ma_audit_delta, ma_audit_ref;'"

# 6.2 Estadísticas
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "$PSQL -c \
  'VACUUM ANALYZE ma_audit_event; VACUUM ANALYZE ma_audit_delta; VACUUM ANALYZE ma_audit_ref;'"
```
> NO tocar `m_global_metadata` (mantiene `schemaAuditChangeNumber`). El sequence de `id` puede dejarse;
> los nuevos eventos seguirán incrementando sin conflicto.

---

## 7. Verificación post (AMBAS opciones)

```bash
# 7.1 Disco: debe bajar de 97% a ~50-60%.
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "df -h /"

# 7.2 Tamaño de las tablas audit (debe colapsar).
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "$PSQL -c \"
  select relname, pg_size_pretty(pg_total_relation_size(relid))
  from pg_statio_user_tables where relname like 'ma_audit_%' order by 1;\""

# 7.3 Arrancar MidPoint server y verificar operación de IDENTIDAD (no audit).
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "docker start midpoint_server"
#   - Healthcheck contenedor healthy.
#   - REST /users (admin) responde, focos intactos (m_user count = 62,465 según invariante reciente).
#   - Un recompute de canary (1 user) corre y ESCRIBE un evento nuevo de audit -> confirma audit operativo.
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "$PSQL -c \
  'select count(*) from m_user; select count(*) from ma_audit_event;'"
#   m_user invariante; ma_audit_event = (traza redactada reimportada [Op.1]) ó (0 + nuevos eventos [Op.2]).

# 7.4 GUI: abrir un objeto y ver su historial de audit -> en Op.1 muestra el cambio sin el JPEG; en Op.2 vacío salvo nuevos.

# 7.5 Reactivar schedulers/tasks suspendidos (recon, recompute). CON la Parte A ya aplicada
#     para que el rebloat no vuelva.
```

**Invariantes de identidad que NO deben cambiar** (sanity, deben ser idénticos a antes):
- `m_user`, `m_shadow`, `m_assignment`, `m_ref_archetype`, counts de orgs/roles.
- Koha borrowers / dup-card 0 (no debería verse afectado: audit es ortogonal).

---

## 8. Rollback

| Escenario | Acción |
|---|---|
| TRUNCATE/DROP salió mal o se perdió traza necesaria | Restaurar **R1Soft (CDP)** del host al punto pre-operación (restaura el LV completo, incluido el volumen Postgres). Es el rollback de último recurso y completo. |
| Necesito recuperar la traza redactada tras TRUNCATE (Op.1) | `ninja import-audit` del/los `redacted-*.zip`. Idempotente (preserva IDs). |
| Necesito recuperar traza COMPLETA con fotos | `ninja import-audit` del export ORIGINAL **sin redactar** del §4 (si se conservó). Vuelve el bloat → solo en emergencia probatoria. |
| MidPoint server no arranca tras la operación | El DDL solo tocó `ma_audit_*` (no `m_*`); revisar logs del contenedor. Si Postgres sano y `m_*` intacto, el arranque no depende de audit. Si aún falla → R1Soft. |
| Postgres PANIC por disco durante la operación | NO debería ocurrir: TRUNCATE/DROP casi no generan WAL. Si el export §4 hubiera llenado /tmp → ese es el único punto de riesgo de disco; por eso el export va a destino EXTERNO o por chunks con borrado. |

---

## 9. Implicación ISO 27001 (A.8.15 Logging) — justificación de gobernanza

**Control afectado:** ISO/IEC 27001:2022 Anexo A **A.8.15 (Logging)** y, tangencialmente, **A.8.16 (Monitoring)** y **A.5.33 (Protection of records)**.

**Argumento para la REDACCIÓN (Opción 1):**
- El valor probatorio del log de auditoría IGA reside en el registro de **qué atributo de identidad cambió, sobre qué objeto, por quién, cuándo y con qué resultado** (event + delta textual). Eso se **conserva íntegro**.
- El **binario JPEG de la foto NO tiene valor probatorio**: la evidencia relevante es "se modificó el atributo `photo`/`jpegPhoto`" (que se preserva), no el contenido del píxel. Conservar el binario en el log de auditoría es, de hecho, una **mala práctica de minimización de datos** (PII innecesaria en logs; la foto ya está en su sistema autoritativo MinIO/Entra).
- La redacción está **documentada, justificada, autorizada y respaldada** (export externo + R1Soft) → mantiene la **integridad y trazabilidad del proceso de purga**, que es lo que A.8.15 exige (no que se guarde todo para siempre, sino que la gestión del log sea controlada y auditable).
- Refuerza **minimización (Ley 29733 / DS 016-2024-JUS)**: se elimina PII (imagen facial) redundante de un repositorio secundario.

**Argumento para el TRUNCATE total (Opción 2):**
- La **política de retención** de auditoría vigente ya es **P7D** (memoria 2026-06-20) → los datos a truncar están dentro/al borde del periodo que la propia política autoriza a eliminar. Truncar es ejecutar la política de retención por un medio técnico distinto (físico vs DELETE lógico).
- Se conserva un **export ninja completo como evidencia archivada** (§4) antes de truncar → la traza no se "destruye", se **archiva fuera de línea**, cumpliendo A.5.33 (protección de registros) sin mantener PII caliente.

**Registro requerido (ambas opciones) para el expediente ISO 27001:**
1. Acta de cambio (change record) con autorización del responsable (Alberto / DTI).
2. Motivo: saturación de disco al 97% → riesgo de **disponibilidad** del servicio IGA (un riesgo A.8.15/continuidad mayor que la pérdida del binario de foto).
3. Evidencia de backup previo verificado (R1Soft point + export ninja).
4. Alcance exacto (solo `ma_audit_*`, sin tocar `m_*`).
5. Verificación post (§7) firmada.

---

## 10. Notas operativas y prevención del re-bloat

1. **Aplicar Parte A `cached=false` en `ri:photo` ANTES** de esta operación (commit `c71734e`) — sin esto, el recon Entra diario re-emite el JPEG y el bloat vuelve.
2. **Arquitectura de fotos canónica** (memoria `project_photo-architecture-2026-06-22`): MidPoint mueve SOLO la URL; binario en MinIO; servicio externo `photo-sync` empuja a LDAP/Koha; Entra = autoridad de su foto. Implementar para erradicar el binario del pipeline MidPoint.
3. **Crear particiones mensuales** tras esta operación, para que el futuro cleanup sea drop-de-partición (instantáneo, sin VACUUM FULL):
   ```sql
   call audit_create_monthly_partitions(60);   -- 5 años a futuro
   ```
   > Requiere que la `_default` esté VACÍA en ese momento (lo estará tras §5/§6). Programar la llamada (cron/checklist) — la doc lo exige explícitamente.
4. **Dejar `auditRecords` del cleanupPolicy vacío** si se gestiona por particiones (recomendación de la doc), o mantener P7D si se sigue por DELETE.
5. **Disco:** queda igual de pequeño (67G). Con Parte A + fotos-fuera-de-MidPoint + particiones mensuales, el crecimiento de audit será textual (~KB/delta) y gestionable por drop mensual.

---

## Fuentes citadas
- Schema audit Sqale (DDL canónico): `config/sql/native/postgres-audit.sql` — https://github.com/Evolveum/midpoint/blob/master/config/sql/native/postgres-audit.sql
- Doc Native audit (partitioning, cleanup, drop/detach, migración, formato JSON de `delta`/`fullResult` sin compresión): https://docs.evolveum.com/midpoint/reference/repository/native-audit/
- Cleanup policy / removing obsolete information: https://docs.evolveum.com/midpoint/reference/deployment/removing-obsolete-information/
- Ninja export-audit / import-audit: https://docs.evolveum.com/midpoint/reference/deployment/ninja/
- PostgreSQL partitioning + vacuuming (VACUUM FULL requiere lock + espacio): https://www.postgresql.org/docs/current/ddl-partitioning.html , https://www.postgresql.org/docs/current/routine-vacuuming.html
- Attribute caching (`cached=false` para jpegPhoto, Parte A): https://docs.evolveum.com/midpoint/reference/resources/attribute-caching/
