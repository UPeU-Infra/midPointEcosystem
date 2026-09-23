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
# MODOS
#   ./backup-midpoint-s3.sh                        backup diario (BD sin auditoria + home)
#   ./backup-midpoint-s3.sh --export-audit YYYYMM  exporta las 3 particiones de ese mes
#                                                  (event, delta, ref); lo invoca
#                                                  audit-partition-maintenance.sh antes
#                                                  de hacer DROP. Exit != 0 => NO dropear.
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
MIN_FREE_GB="${MIN_FREE_GB:-4}"
LOG_FILE="${LOG_FILE:-$HOME/midpoint-backup.log}"

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
    rm -f "$STAGE"/*."$TS".* 2>/dev/null || true
    exit "$rc"
}
trap on_error ERR

aws_cli() {
    docker run --rm -i \
        -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION \
        -v "$STAGE:/stage:ro" "$AWS_IMAGE" "$@"
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
    log "OK s3://$IGA_BACKUP_BUCKET/$key ($(numfmt --to=iec "$size"), sha256=$sha)"
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
    local file="ma_audit_${m}.${TS}.dump" key="midpoint/audit/ma_audit_${m}.dump" toc
    log "==== EXPORT auditoria $m ===="
    check_free_space
    STEP="pg_dump auditoria $m"
    docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" -Fc -Z 6 \
        -t "*.ma_audit_event_${m}" -t "*.ma_audit_delta_${m}" -t "*.ma_audit_ref_${m}" \
        > "$STAGE/$file"
    STEP="verificacion pg_restore -l auditoria $m"
    toc=$(docker exec -i "$PG_CONTAINER" pg_restore -l < "$STAGE/$file")
    for t in event delta ref; do
        if ! grep -Eq "TABLE DATA [[:alnum:]_]+ ma_audit_${t}_${m} " <<< "$toc"; then
            log "El dump no contiene TABLE DATA de ma_audit_${t}_${m}"
            false
        fi
    done
    upload_verified "$file" "$key"
    rm -f "$STAGE/$file"
    log "==== FIN EXPORT auditoria $m ===="
}

# ------------------------------------------------------------------------------
daily_backup() {
    local dbf="midpoint-db.${TS}.dump" homef="midpoint-home.${TS}.tar.gz" toc ndata t0
    t0=$(date +%s)
    log "==== INICIO backup diario ===="
    check_free_space

    STEP="pg_dump BD (sin datos de auditoria)"
    docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" -Fc -Z 6 \
        --exclude-table-data='*.ma_audit_*' > "$STAGE/$dbf"

    STEP="verificacion pg_restore -l BD"
    toc=$(docker exec -i "$PG_CONTAINER" pg_restore -l < "$STAGE/$dbf")
    ndata=$(grep -c 'TABLE DATA' <<< "$toc" || true)
    for t in m_user m_shadow m_resource m_role m_org m_system_configuration; do
        if ! grep -Eq "TABLE DATA [[:alnum:]_]+ $t " <<< "$toc"; then
            log "El dump no contiene TABLE DATA de $t"
            false
        fi
    done
    log "Dump BD: $(numfmt --to=iec "$(stat -c %s "$STAGE/$dbf")"), $ndata tablas con datos"

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

    upload_verified "$dbf" "midpoint/db/$YM/midpoint-db-${TS}.dump"
    upload_verified "$homef" "midpoint/home/$YM/midpoint-home-${TS}.tar.gz"

    local dbsize
    dbsize=$(numfmt --to=iec "$(stat -c %s "$STAGE/$dbf")")
    rm -f "$STAGE/$dbf" "$STAGE/$homef"
    log "==== FIN backup diario OK ($(( $(date +%s) - t0 )) s) ===="

    if [[ "$(date +%u)" == "1" || "${FORCE_SUMMARY:-0}" == "1" ]]; then
        telegram "🟢 Backup MidPoint OK (${HOST})
BD sin auditoría: ${dbsize} · $ndata tablas
s3://${IGA_BACKUP_BUCKET}/midpoint/db/${YM}/
Resumen semanal: si un lunes no llega este mensaje, el backup dejó de correr."
    fi
}

case "${1:-}" in
    --export-audit) export_audit_month "${2:-}" ;;
    "")             daily_backup ;;
    *)              echo "Uso: $0 [--export-audit YYYYMM]" >&2; exit 2 ;;
esac
