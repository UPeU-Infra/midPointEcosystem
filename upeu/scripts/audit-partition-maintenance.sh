#!/usr/bin/env bash
#
# audit-partition-maintenance.sh
# ------------------------------------------------------------------------------
# Mantenimiento del ciclo de retencion de las particiones de auditoria nativa de
# MidPoint (repositorio PostgreSQL nativo, esquema sqale).
#
# CONTEXTO
#   MidPoint solo CREA particiones mensuales (procedure
#   midpoint.audit_create_monthly_partitions(futurecount)); NUNCA las borra.
#   Para cerrar el ciclo de retencion (canonico Evolveum: retencion de audit =
#   DROP de particion, no DELETE) este script:
#     1. EXPORTA a S3 y luego hace DROP de las particiones de cada mes mas antiguo
#        que (mes-actual - RETENTION_MONTHS).
#     2. CALL audit_create_monthly_partitions(FUTURE_MONTHS) para reponer el
#        colchon de particiones futuras (idempotente: solo crea las que faltan).
#
# RETENCION EN LA BD: 2 meses completos + el mes en curso (2026-09-23).
#   La auditoria crece ~11 GB/mes. El audit trail NO se pierde: cada mes se
#   EXPORTA a S3 antes de su DROP (backup-midpoint-s3.sh --export-audit) y alli
#   no expira (s3://upeu-iga-backups-360416501080/midpoint/audit/, Deep Archive).
#   Si la exportacion falla, ese mes NO se dropea (fail-closed) y llega alerta.
#   Runbook: docs/runbooks/backup-midpoint-s3/README.md
#
# TABLAS POR MES (y orden de DROP, CRITICO)
#   MidPoint 4.10:  ma_audit_event_M, ma_audit_delta_M, ma_audit_ref_M
#   MidPoint 4.11+: ademas ma_audit_payload_M (cambio de esquema de auditoria 15)
#   delta, ref y payload tienen FK -> ma_audit_event_M (ON DELETE CASCADE no
#   aplica a DROP TABLE). Se dropean SIEMPRE las hijas antes que event, y las
#   cuatro en UNA transaccion: o se va el mes entero o no se va nada.
#   payload se detecta en tiempo de ejecucion: el mismo script vale para 4.10
#   (sin payload) y 4.11 (con payload).
#
# GUARDAS
#   - Solo toca tablas ma_audit_(event|delta|ref|payload)_YYYYMM (regex estricta).
#   - NUNCA toca _default ni tablas m_* ni ningun otro objeto.
#   - Guarda FK generica: antes del DROP se listan TODAS las FK que apuntan a
#     ma_audit_event_M. Si alguna viene de una tabla que no es delta/ref/payload
#     del mismo mes (p. ej. una tabla nueva de una version futura), ese mes NO
#     se toca y se corta el bucle (fail-closed), igual que si fallara el export.
#   - --dry-run no ejecuta nada destructivo, no llama al export, y sus consultas
#     corren con default_transaction_read_only=on (la BD rechazaria cualquier
#     escritura). Por eso se puede lanzar contra PROD sin riesgo.
#   - Verifica que ma_audit_event_default este VACIA antes del CALL de reposicion.
#
# CORREGIDO 2026-10-28 (rama prep/upgrade-4.11)
#   El 1-oct la corrida listo 2 meses (202606 202607) y solo proceso 202606: el
#   export (backup-midpoint-s3.sh) lanza `docker run -i` sin redirigir stdin y se
#   comia el resto del here-string que alimentaba el `while read`. Ahora los
#   meses van en un array y el export recibe stdin=/dev/null.
#
# USO
#   ./audit-partition-maintenance.sh --dry-run     # lista, no borra, BD en solo lectura
#   ./audit-partition-maintenance.sh               # modo real (EXPORT + DROP + reposicion)
#
# Se ejecuta en el HOST de PROD (midpoint-prod). El SQL corre via:
#   docker exec -i <PG_CONTAINER> psql -U <PG_USER> -d <PG_DB>
# NO contiene secretos.
#
# Prueba reproducible (Postgres desechable, esquema 4.10 y 4.11):
#   upeu/scripts/tests/test-audit-partition-maintenance.sh
# ------------------------------------------------------------------------------
set -euo pipefail

# ---- Config (sin secretos: el psql dentro del contenedor usa trust local) ----
PG_CONTAINER="${PG_CONTAINER:-midpoint-midpoint_data-1}"
PG_USER="${PG_USER:-midpoint}"
PG_DB="${PG_DB:-midpoint}"
RETENTION_MONTHS="${RETENTION_MONTHS:-2}"
EXPORT_SCRIPT="${EXPORT_SCRIPT:-$(dirname "$(readlink -f "$0")")/backup-midpoint-s3.sh}"
FUTURE_MONTHS="${FUTURE_MONTHS:-60}"
LOG_FILE="${LOG_FILE:-/var/log/midpoint-audit-partition-maintenance.log}"

DRY_RUN=0
case "${1:-}" in
    --dry-run) DRY_RUN=1 ;;
    "")        ;;
    *)         echo "Uso: $0 [--dry-run]" >&2; exit 2 ;;
esac

# ---- Logging ----
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S%z')] $*"
    echo "$msg"
    # best-effort al log file (no fallar si no hay permisos de escritura)
    echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
}

# Ejecuta SQL (stdin) y devuelve filas sin adornos (-tA).
# En --dry-run la sesion es de solo lectura: cualquier DROP/CALL fallaria.
psql_q() {
    if [[ "$DRY_RUN" -eq 1 ]]; then
        docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' "$PG_CONTAINER" \
            psql -U "$PG_USER" -d "$PG_DB" -tA -v ON_ERROR_STOP=1
    else
        docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tA -v ON_ERROR_STOP=1
    fi
}

# ¿Existe la tabla? (relkind r = tabla/particion hoja)
table_exists() {
    local n
    n=$(printf "SELECT count(*) FROM pg_class WHERE relname = '%s' AND relkind = 'r';" "$1" | psql_q)
    [[ "$n" == "1" ]]
}

log "==== INICIO audit-partition-maintenance (dry_run=$DRY_RUN retention=${RETENTION_MONTHS}m future=${FUTURE_MONTHS}) ===="

# ---- 0. ¿Esquema 4.11 (con payload)? Solo informativo ----
if [[ "$(printf "SELECT count(*) FROM pg_class WHERE relname = 'ma_audit_payload';" | psql_q)" == "1" ]]; then
    log "Esquema de auditoria con ma_audit_payload (4.11+): se exporta y dropea tambien payload."
else
    log "Esquema de auditoria sin ma_audit_payload (4.10): event, delta y ref."
fi

# ---- 1. Sufijo de corte: YYYYMM del mes (now - RETENTION_MONTHS) ----
# Las particiones con sufijo ESTRICTAMENTE MENOR a este corte se dropean.
CUTOFF=$(printf "SELECT to_char(date_trunc('month', current_timestamp) - interval '%d months', 'YYYYMM');" "$RETENTION_MONTHS" | psql_q)
log "Sufijo de corte (drop si suffix < ): $CUTOFF"

# ---- 2. Meses candidatos (solo particiones EVENT, regex estricta) ----
CANDIDATE_SQL=$(cat <<SQL
SELECT substring(relname from 'ma_audit_event_([0-9]{6})\$') AS yyyymm
FROM pg_class
WHERE relname ~ '^ma_audit_event_[0-9]{6}\$'
  AND relkind = 'r'
  AND substring(relname from 'ma_audit_event_([0-9]{6})\$') < '${CUTOFF}'
ORDER BY 1;
SQL
)
# Array, NO here-string: un hijo que lea stdin no puede comerse los meses.
mapfile -t CANDIDATES < <(printf '%s' "$CANDIDATE_SQL" | psql_q | grep -E '^[0-9]{6}$' || true)

if [[ ${#CANDIDATES[@]} -eq 0 ]]; then
    log "Candidatos a drop: 0 (no hay particiones mas antiguas que ${RETENTION_MONTHS} meses)."
else
    log "Candidatos a drop: ${#CANDIDATES[@]} mes(es) -> ${CANDIDATES[*]}"
fi

# ---- 3. EXPORT + DROP por mes ----
for M in "${CANDIDATES[@]}"; do
    if ! [[ "$M" =~ ^[0-9]{6}$ ]]; then
        log "GUARD: sufijo inesperado '$M' -> SE OMITE."
        continue
    fi
    EVENT="ma_audit_event_${M}"
    CHILDREN=()
    for c in payload delta ref; do
        table_exists "ma_audit_${c}_${M}" && CHILDREN+=("ma_audit_${c}_${M}")
    done

    # Guarda FK generica: toda FK que apunte a EVENT debe venir de una hija conocida.
    FK_SRC=$(printf "SELECT conrelid::regclass::text FROM pg_constraint WHERE contype = 'f' AND confrelid = '%s'::regclass ORDER BY 1;" "$EVENT" | psql_q)
    UNKNOWN=""
    while IFS= read -r src; do
        [[ -z "$src" ]] && continue
        src="${src##*.}"   # sin esquema
        [[ " ${CHILDREN[*]} " == *" $src "* ]] || UNKNOWN+="$src "
    done <<< "$FK_SRC"
    if [[ -n "$UNKNOWN" ]]; then
        log "GUARD FK: $EVENT es referenciada por tablas no previstas: ${UNKNOWN}-> NO se toca este mes ni los siguientes. Revisar el esquema (¿version nueva de MidPoint?)."
        break
    fi

    DROP_ORDER=("${CHILDREN[@]}" "$EVENT")
    if [[ "$DRY_RUN" -eq 1 ]]; then
        log "[DRY-RUN] mes $M: exportaria a S3 y luego dropearia en una transaccion (orden FK): ${DROP_ORDER[*]}"
        continue
    fi

    # Fail-closed: sin export verificado en S3 no hay DROP. Se corta el bucle
    # entero: los meses siguientes tampoco se tocan.
    log "EXPORT a S3 del mes $M antes del DROP..."
    if ! "$EXPORT_SCRIPT" --export-audit "$M" < /dev/null; then
        log "EXPORT FALLO para $M -> NO se dropea nada mas. Revisar $EXPORT_SCRIPT."
        break
    fi
    log "DROP particiones del mes $M (una transaccion, orden FK): ${DROP_ORDER[*]}"
    {
        echo "BEGIN;"
        for t in "${DROP_ORDER[@]}"; do echo "DROP TABLE IF EXISTS ${t};"; done
        echo "COMMIT;"
    } | psql_q
    log "DROP OK: ${DROP_ORDER[*]}"
done

# ---- 4. Reponer colchon de particiones futuras ----
# Pre-check: ma_audit_event_default debe estar VACIA (datos ahi = mal particionado).
DEFAULT_ROWS=$(printf 'SELECT count(*) FROM ma_audit_event_default;' | psql_q)
log "ma_audit_event_default filas: $DEFAULT_ROWS"
if [[ "$DEFAULT_ROWS" != "0" ]]; then
    log "ADVERTENCIA: ma_audit_event_default NO esta vacia ($DEFAULT_ROWS filas). Se OMITE el CALL de reposicion para no enmascarar un problema de particionado. Revisar manualmente."
else
    if [[ "$DRY_RUN" -eq 1 ]]; then
        log "[DRY-RUN] ejecutaria: CALL audit_create_monthly_partitions(${FUTURE_MONTHS}) -> no-op si el colchon ya esta completo."
    else
        log "Reponiendo colchon: CALL audit_create_monthly_partitions(${FUTURE_MONTHS})..."
        printf 'CALL audit_create_monthly_partitions(%d);' "$FUTURE_MONTHS" | psql_q
        log "Reposicion OK."
    fi
fi

log "==== FIN audit-partition-maintenance ===="
