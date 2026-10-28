#!/usr/bin/env bash
#
# backup-midpoint-s3.sh
# ------------------------------------------------------------------------------
# Backup de MidPoint PROD (midpoint.upeu, 192.168.15.166, on-prem) a S3.
#
# DONDE QUEDAN LOS BACKUPS  (que no se olvide)
#   s3://upeu-iga-backups-360416501080/midpoint/
#   Cuenta AWS upeu-repo 360416501080, region us-east-2.
#     db/YYYY/MM/midpoint-db-<ts>.dump       pg_dump -Fc SIN datos de auditoria (35 dias)
#     home/YYYY/MM/midpoint-home-<ts>.tar.gz keystore.jceks + config.xml + compose/.env (35 dias)
#     audit/ma_audit_YYYYMM.dump             particion mensual de auditoria, exportada
#                                            ANTES de su DROP (Deep Archive a los 30 dias,
#                                            no expira)
#   Runbook (restore incluido): docs/runbooks/backup-midpoint-s3/README.md
#
#   Cada dump va acompanado de <archivo>.sha256, que se escribe SOLO cuando el
#   dump paso todas las verificaciones. UN DUMP SIN SU .sha256 AL LADO NO ESTA
#   VERIFICADO (p. ej. pg_dump murio a medias): no restaurar desde el.
#
#   La BD va a S3 en STREAMING (pg_dump | S3), sin pasar por el disco local: el
#   dump pesa ~4 GB y el servidor no tiene espacio para prepararlo en local.
#
# MODOS
#   ./backup-midpoint-s3.sh                        backup diario (BD sin auditoria + home)
#   ./backup-midpoint-s3.sh --export-audit YYYYMM  exporta las particiones de ese mes
#                                                  (event, delta, ref y, desde 4.11,
#                                                  payload); lo invoca
#                                                  audit-partition-maintenance.sh antes
#                                                  de hacer DROP. Exit != 0 => NO dropear.
#   ./backup-midpoint-s3.sh --pre-upgrade ETIQUETA  backup de ventana de subida, con
#                                                  MidPoint PARADO: BD COMPLETA (con
#                                                  auditoria) + home leido del volumen.
#                                                  Va a midpoint/upgrade/ETIQUETA/.
#                                                  Runbooks: docs/upgrade-4.11/
#
# CREDENCIALES (nunca en el repo)
#   $CONF (por defecto ~/.config/midpoint-backup/backup.env, permisos 600):
#     AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION, IGA_BACKUP_BUCKET,
#     TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
#   El usuario IAM (midpoint-backup-onprem) solo puede escribir/leer en midpoint/*
#   y tiene Deny explicito de borrado: ni un error ni un servidor comprometido
#   pueden borrar backups.
#
# AVISOS
#   - Fallo de cualquier paso => mensaje a Telegram (grupo "SciBack · Pulso").
#   - Los lunes, aunque todo vaya bien, manda un resumen: si un lunes no llega
#     el mensaje, el backup murio en silencio (cron borrado, servidor caido...).
# ------------------------------------------------------------------------------
set -Eeuo pipefail

CONF="${CONF:-$HOME/.config/midpoint-backup/backup.env}"
PG_CONTAINER="${PG_CONTAINER:-midpoint-midpoint_data-1}"
PG_USER="${PG_USER:-midpoint}"
PG_DB="${PG_DB:-midpoint}"
MP_CONTAINER="${MP_CONTAINER:-midpoint_server}"
MP_HOST_DIR="${MP_HOST_DIR:-/opt/midpoint}"
AWS_IMAGE="${AWS_IMAGE:-amazon/aws-cli:2.36.50}"
STAGE="${STAGE:-/var/tmp/midpoint-backup}"
MIN_FREE_GB="${MIN_FREE_GB:-1}"
LOG_FILE="${LOG_FILE:-$HOME/midpoint-backup.log}"
# Solo para --pre-upgrade (MidPoint parado): volumen del home y una imagen
# que ya este en el host para leerlo (no descarga nada nuevo).
MP_HOME_VOLUME="${MP_HOME_VOLUME:-midpoint_midpoint_home}"
MP_IMAGE_FOR_TAR="${MP_IMAGE_FOR_TAR:-postgres:16-bullseye}"

# shellcheck disable=SC1090
source "$CONF"
: "${IGA_BACKUP_BUCKET:?falta IGA_BACKUP_BUCKET en $CONF}"
export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION

HOST="$(hostname)"
TS="$(date +%Y%m%d-%H%M%S)"
YM="$(date +%Y/%m)"
STEP="inicio"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S%z')] $*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
}

telegram() {
    [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]] && return 0
    curl -s -m 15 -o /dev/null "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
        --data-urlencode "text=$1" || true
}

on_error() {
    local rc=$?
    log "ERROR en paso '$STEP' (exit $rc)"
    telegram "🔴 Backup MidPoint FALLÓ en ${HOST}
Paso: ${STEP} (exit ${rc})
Log: ${LOG_FILE}
Runbook: midPointEcosystem/docs/runbooks/backup-midpoint-s3"
    rm -f "$STAGE"/*."$TS".* "$STAGE"/*."$TS" 2>/dev/null || true
    exit "$rc"
}
trap on_error ERR

aws_cli() {
    docker run --rm -i \
        -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION \
        -v "$STAGE:/stage" "$AWS_IMAGE" "$@"
}

# Sube /stage/<file> a s3://bucket/<key> y verifica que el tamano en S3 coincide.
upload_verified() {
    local file="$1" key="$2" size sha remote
    size=$(stat -c %s "$STAGE/$file")
    sha=$(sha256sum "$STAGE/$file" | cut -d' ' -f1)
    STEP="subida $key"
    aws_cli s3 cp "/stage/$file" "s3://$IGA_BACKUP_BUCKET/$key" \
        --metadata "sha256=$sha,host=$HOST" --only-show-errors
    STEP="verificacion en S3 de $key"
    remote=$(aws_cli s3api head-object --bucket "$IGA_BACKUP_BUCKET" --key "$key" \
        --query ContentLength --output text | tr -d '\r')
    if [[ "$remote" != "$size" ]]; then
        log "Tamano distinto en S3: local=$size remoto=$remote"
        false
    fi
    printf '%s  %s\n' "$sha" "$(basename "$key")" \
        | aws_cli s3 cp - "s3://$IGA_BACKUP_BUCKET/$key.sha256" --only-show-errors
    log "OK s3://$IGA_BACKUP_BUCKET/$key ($(numfmt --to=iec "$size"), sha256=$sha)"
}

# Cuenta bytes y calcula sha256 de lo que pasa por la tuberia; lo deja en $1.
PYHASH='import sys,hashlib
h=hashlib.sha256(); n=0; i=sys.stdin.buffer; o=sys.stdout.buffer
while True:
    b=i.read(1<<20)
    if not b: break
    h.update(b); n+=len(b); o.write(b)
o.flush()
open(sys.argv[1],"w").write("%d %s\n" % (n, h.hexdigest()))'

# Subida en streaming: stdin -> s3://bucket/<key>, contando bytes y sha256.
# Va como ultimo eslabon de una tuberia (subshell): solo sube y deja el .meta.
#   uso: <productor> | stream_upload <key>
stream_upload() {
    trap - ERR   # el fallo lo recoge el shell padre via pipefail (una sola alerta)
    python3 -c "$PYHASH" "$STAGE/stream.$TS.meta" \
        | aws_cli s3 cp - "s3://$IGA_BACKUP_BUCKET/$1" \
            --expected-size 21474836480 --only-show-errors
}

# Se llama DESPUES de que la tuberia entera termino bien (si pg_dump muere a
# medias, pipefail dispara el ERR antes y nunca se llega aqui). Verifica tamano
# en S3 y que el TOC del dump (al principio del archivo) trae las tablas
# pedidas; solo entonces escribe <key>.sha256 = marca de "dump verificado".
#   uso: verify_and_mark <key> <regex_tabla>...
verify_and_mark() {
    local key="$1"; shift
    local meta="$STAGE/stream.$TS.meta" head="stream-head.$TS.bin" bytes sha remote toc re
    read -r bytes sha < "$meta"
    (( bytes > 0 )) || { log "Stream vacio para $key"; false; }

    STEP="verificacion de tamano en S3 de $key"
    remote=$(aws_cli s3api head-object --bucket "$IGA_BACKUP_BUCKET" --key "$key" \
        --query ContentLength --output text | tr -d '\r')
    if [[ "$remote" != "$bytes" ]]; then
        log "Tamano distinto en S3: enviado=$bytes remoto=$remote"
        false
    fi

    STEP="verificacion del TOC (pg_restore -l) de $key"
    aws_cli s3api get-object --bucket "$IGA_BACKUP_BUCKET" --key "$key" \
        --range bytes=0-67108863 "/stage/$head" > /dev/null
    toc=$(docker exec -i "$PG_CONTAINER" pg_restore -l < "$STAGE/$head")
    rm -f "$STAGE/$head"
    for re in "$@"; do
        if ! grep -Eq "TABLE DATA [[:alnum:]_]+ ${re} " <<< "$toc"; then
            log "El dump $key no contiene TABLE DATA que case con '${re}'"
            false
        fi
    done
    LAST_TOC_TABLES=$(grep -c 'TABLE DATA' <<< "$toc" || true)

    STEP="marca .sha256 de $key"
    printf '%s  %s\n' "$sha" "$(basename "$key")" \
        | aws_cli s3 cp - "s3://$IGA_BACKUP_BUCKET/$key.sha256" --only-show-errors
    rm -f "$meta"
    LAST_BYTES=$bytes
    log "OK s3://$IGA_BACKUP_BUCKET/$key ($(numfmt --to=iec "$bytes"), $LAST_TOC_TABLES tablas con datos, sha256=$sha)"
}

check_free_space() {
    STEP="espacio libre"
    mkdir -p "$STAGE"
    local free_gb
    free_gb=$(df -BG --output=avail "$STAGE" | tail -1 | tr -dc '0-9')
    if (( free_gb < MIN_FREE_GB )); then
        log "Solo ${free_gb} GB libres en $STAGE (minimo ${MIN_FREE_GB} GB)"
        false
    fi
}

# ------------------------------------------------------------------------------
export_audit_month() {
    local m="$1"
    [[ "$m" =~ ^[0-9]{6}$ ]] || { log "Mes invalido: '$m'"; exit 2; }
    log "==== EXPORT auditoria $m ===="
    check_free_space
    # 4.10: event, delta, ref. 4.11+ (cambio de auditoria 15): ademas payload,
    # que tiene FK a event. Se detecta en tiempo de ejecucion.
    local tables=("ma_audit_event_${m}" "ma_audit_delta_${m}" "ma_audit_ref_${m}") t n targs=()
    STEP="deteccion de ma_audit_payload_${m}"
    n=$(docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tA \
        -c "SELECT count(*) FROM pg_class WHERE relname = 'ma_audit_payload_${m}' AND relkind = 'r'" < /dev/null)
    [[ "$n" == "1" ]] && tables+=("ma_audit_payload_${m}")
    for t in "${tables[@]}"; do targs+=(-t "*.${t}"); done
    log "Tablas a exportar: ${tables[*]}"
    STEP="pg_dump auditoria $m"
    docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" -Fc -Z 6 "${targs[@]}" \
        | stream_upload "midpoint/audit/ma_audit_${m}.dump"
    verify_and_mark "midpoint/audit/ma_audit_${m}.dump" "${tables[@]}"
    log "==== FIN EXPORT auditoria $m ===="
}

# ------------------------------------------------------------------------------
daily_backup() {
    local homef="midpoint-home.${TS}.tar.gz" t0
    t0=$(date +%s)
    log "==== INICIO backup diario ===="
    check_free_space

    # Sin datos de auditoria (van aparte, por mes) ni de simulaciones (previews
    # desechables). m_shadow esta particionada por recurso: sus datos viven en
    # m_shadow_<oid>, por eso se comprueba con regex.
    STEP="pg_dump BD (sin auditoria ni simulaciones)"
    docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" -Fc -Z 1 \
        --exclude-table-data='*.ma_audit_*' \
        --exclude-table-data='*.m_simulation_result_processed_object*' \
        | stream_upload "midpoint/db/$YM/midpoint-db-${TS}.dump"
    verify_and_mark "midpoint/db/$YM/midpoint-db-${TS}.dump" \
        m_user 'm_shadow_[[:alnum:]_]+' m_resource m_role m_org \
        m_system_configuration m_assignment
    local dbsize ndata
    dbsize=$(numfmt --to=iec "$LAST_BYTES"); ndata=$LAST_TOC_TABLES

    # keystore.jceks es imprescindible: sin el, los valores cifrados de la BD
    # (credenciales de los recursos) no se pueden descifrar tras un restore.
    STEP="tar del home de MidPoint"
    {
        docker exec "$MP_CONTAINER" tar -C /opt/midpoint/var -cf - \
            --exclude=./log --exclude=./trace --exclude=./tmp --exclude=./work .
    } > "$STAGE/home-var.${TS}.tar"
    tar -C "$MP_HOST_DIR" -cf "$STAGE/home-host.${TS}.tar" \
        --exclude='*.jar.bak*' --exclude='*.bak' .
    tar -C "$STAGE" -czf "$STAGE/$homef" "home-var.${TS}.tar" "home-host.${TS}.tar"
    rm -f "$STAGE/home-var.${TS}.tar" "$STAGE/home-host.${TS}.tar"
    STEP="verificacion del tar del home"
    # Listados a variable: un 'grep -q' en la tuberia cortaria tar con SIGPIPE
    # y pipefail lo daria por fallo aunque el archivo este.
    local lvar lhost
    lvar=$(tar -xzOf "$STAGE/$homef" "home-var.${TS}.tar" | tar -t)
    lhost=$(tar -xzOf "$STAGE/$homef" "home-host.${TS}.tar" | tar -t)
    grep -qx './keystore.jceks' <<< "$lvar"
    grep -qx './config.xml' <<< "$lvar"
    grep -qx './docker-compose.yml' <<< "$lhost"
    grep -qx './.env' <<< "$lhost"

    upload_verified "$homef" "midpoint/home/$YM/midpoint-home-${TS}.tar.gz"
    rm -f "$STAGE/$homef"
    log "==== FIN backup diario OK ($(( $(date +%s) - t0 )) s) ===="

    if [[ "$(date +%u)" == "1" || "${FORCE_SUMMARY:-0}" == "1" ]]; then
        telegram "🟢 Backup MidPoint OK (${HOST})
BD sin auditoría: ${dbsize} · $ndata tablas
s3://${IGA_BACKUP_BUCKET}/midpoint/db/${YM}/
Resumen semanal: si un lunes no llega este mensaje, el backup dejó de correr."
    fi
}

# ------------------------------------------------------------------------------
# Backup de ventana de subida (docs/upgrade-4.11/F2-*.md y F3-*.md).
# Precondicion: midpoint_server PARADO (el home se lee del volumen, no con
# docker exec) y Postgres arriba. Diferencias con el diario:
#   - la BD va COMPLETA, CON los datos de auditoria: el esquema de auditoria
#     tambien cambia en la subida y la vuelta atras debe poder restaurarlo;
#   - el home se lee del volumen con un contenedor auxiliar (--user 0, solo
#     lectura), porque el contenedor de MidPoint esta parado;
#   - destino propio midpoint/upgrade/<etiqueta>/, fuera de la caducidad de 35
#     dias de db/ y home/ (revisar la regla de ciclo de vida del bucket).
pre_upgrade_backup() {
    local tag="$1" key_db key_home homef t0 running
    [[ "$tag" =~ ^[A-Za-z0-9._-]+$ ]] || { log "Etiqueta invalida: '$tag'"; exit 2; }
    t0=$(date +%s)
    log "==== INICIO backup pre-upgrade '$tag' ===="
    STEP="comprobar que MidPoint esta parado"
    running=$(docker ps --filter "name=^/${MP_CONTAINER}$" --format '{{.Names}}')
    if [[ -n "$running" ]]; then
        log "El contenedor $MP_CONTAINER sigue en marcha: pararlo antes (docker compose stop midpoint_server)."
        false
    fi
    check_free_space

    key_db="midpoint/upgrade/${tag}/midpoint-full-${TS}.dump"
    STEP="pg_dump BD COMPLETA (con auditoria)"
    docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" -Fc -Z 1 \
        | stream_upload "$key_db"
    verify_and_mark "$key_db" \
        m_user 'm_shadow_[[:alnum:]_]+' m_resource m_role m_org \
        m_system_configuration m_assignment 'ma_audit_event_[0-9]{6}'
    local dbsize ndata
    dbsize=$(numfmt --to=iec "$LAST_BYTES"); ndata=$LAST_TOC_TABLES

    homef="midpoint-home.${TS}.tar.gz"
    STEP="tar del home desde el volumen ${MP_HOME_VOLUME}"
    docker run --rm --user 0 --entrypoint tar -v "${MP_HOME_VOLUME}:/v:ro" "$MP_IMAGE_FOR_TAR" \
        -C /v -cf - --exclude=./log --exclude=./trace --exclude=./tmp --exclude=./work . \
        > "$STAGE/home-var.${TS}.tar"
    tar -C "$MP_HOST_DIR" -cf "$STAGE/home-host.${TS}.tar" \
        --exclude='*.jar.bak*' --exclude='*.bak' .
    tar -C "$STAGE" -czf "$STAGE/$homef" "home-var.${TS}.tar" "home-host.${TS}.tar"
    rm -f "$STAGE/home-var.${TS}.tar" "$STAGE/home-host.${TS}.tar"
    STEP="verificacion del tar del home"
    local lvar lhost
    lvar=$(tar -xzOf "$STAGE/$homef" "home-var.${TS}.tar" | tar -t)
    lhost=$(tar -xzOf "$STAGE/$homef" "home-host.${TS}.tar" | tar -t)
    grep -qx './keystore.jceks' <<< "$lvar"
    grep -qx './config.xml' <<< "$lvar"
    grep -qx './docker-compose.yml' <<< "$lhost"
    grep -qx './.env' <<< "$lhost"
    key_home="midpoint/upgrade/${tag}/midpoint-home-${TS}.tar.gz"
    upload_verified "$homef" "$key_home"
    rm -f "$STAGE/$homef"
    log "==== FIN backup pre-upgrade '$tag' OK ($(( $(date +%s) - t0 )) s): BD ${dbsize} (${ndata} tablas con datos) ===="
    telegram "🟡 Backup PRE-UPGRADE MidPoint OK (${HOST}) - ${tag}
BD completa: ${dbsize} · ${ndata} tablas
s3://${IGA_BACKUP_BUCKET}/midpoint/upgrade/${tag}/"
}

case "${1:-}" in
    --export-audit) export_audit_month "${2:-}" ;;
    --pre-upgrade)  pre_upgrade_backup "${2:-}" ;;
    "")             daily_backup ;;
    *)              echo "Uso: $0 [--export-audit YYYYMM | --pre-upgrade ETIQUETA]" >&2; exit 2 ;;
esac
