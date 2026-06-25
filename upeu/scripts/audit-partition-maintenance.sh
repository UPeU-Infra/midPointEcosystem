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
#     1. DROP de las particiones ma_audit_{event,delta,ref}_YYYYMM mas antiguas
#        que (mes-actual - RETENTION_MONTHS).
#     2. CALL audit_create_monthly_partitions(FUTURE_MONTHS) para reponer el
#        colchon de particiones futuras (idempotente: solo crea las que faltan).
#
# RETENCION: 12 meses (ISO 27001 A.5.16 / A.8.2 exigen conservar el audit trail
#   pero NO imponen una ventana mayor; 12 meses cabe holgado en el disco actual).
#
# ORDEN DE DROP (CRITICO):
#   ma_audit_delta_YYYYMM y ma_audit_ref_YYYYMM tienen FK -> ma_audit_event_YYYYMM
#   (ON DELETE CASCADE NO aplica a DROP TABLE). Por tanto se dropea SIEMPRE
#   delta + ref ANTES que event del mismo mes. Verificado contra el DDL real de
#   PROD (pg_constraint) y la doc Evolveum:
#   https://docs.evolveum.com/midpoint/reference/repository/native-audit/
#
# GUARDS
#   - Solo toca tablas ma_audit_(event|delta|ref)_YYYYMM (regex estricta).
#   - NUNCA toca _default ni tablas m_* ni ningun otro objeto.
#   - --dry-run lista candidatos sin ejecutar nada destructivo.
#   - Verifica que ma_audit_event_default este VACIA antes del CALL de reposicion
#     (si no, el procedure podria fallar / habria datos sin particion).
#
# USO
#   ./audit-partition-maintenance.sh --dry-run     # lista, no borra
#   ./audit-partition-maintenance.sh               # modo real (DROP + reposicion)
#
# Se ejecuta en el HOST de PROD (midpoint-prod). El SQL corre via:
#   docker exec -i <PG_CONTAINER> psql -U <PG_USER> -d <PG_DB>
# NO contiene secretos; usa el patron docker exec ya existente en el proyecto.
#
# Runbook: docs/runbooks/audit-partition-maintenance (retencion audit por DROP)
# ------------------------------------------------------------------------------
set -euo pipefail

# ---- Config (sin secretos: el psql dentro del contenedor usa trust local) ----
PG_CONTAINER="${PG_CONTAINER:-midpoint-midpoint_data-1}"
PG_USER="${PG_USER:-midpoint}"
PG_DB="${PG_DB:-midpoint}"
RETENTION_MONTHS="${RETENTION_MONTHS:-12}"
FUTURE_MONTHS="${FUTURE_MONTHS:-60}"
LOG_FILE="${LOG_FILE:-/var/log/midpoint-audit-partition-maintenance.log}"

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

# ---- Logging ----
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S%z')] $*"
    echo "$msg"
    # best-effort al log file (no fallar si no hay permisos de escritura)
    echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
}

psql_q() {
    # Ejecuta SQL y devuelve filas sin adornos (-tA). stdin = el SQL.
    docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tA -v ON_ERROR_STOP=1
}

log "==== INICIO audit-partition-maintenance (dry_run=$DRY_RUN retention=${RETENTION_MONTHS}m future=${FUTURE_MONTHS}) ===="

# ---- 1. Calcular sufijo de corte: YYYYMM del mes (now - RETENTION_MONTHS) ----
# Las particiones con sufijo ESTRICTAMENTE MENOR a este corte se dropean.
CUTOFF=$(printf "SELECT to_char(date_trunc('month', current_timestamp) - interval '%d months', 'YYYYMM');" "$RETENTION_MONTHS" | psql_q)
log "Sufijo de corte (drop si suffix < ): $CUTOFF"

# ---- 2. Listar meses candidatos a drop (solo particiones EVENT, regex estricta) ----
# Fuente de verdad: pg_class. Filtra ma_audit_event_YYYYMM con suffix < CUTOFF.
CANDIDATE_SQL=$(cat <<SQL
SELECT substring(relname from 'ma_audit_event_([0-9]{6})\$') AS yyyymm
FROM pg_class
WHERE relname ~ '^ma_audit_event_[0-9]{6}\$'
  AND substring(relname from 'ma_audit_event_([0-9]{6})\$') < '${CUTOFF}'
ORDER BY 1;
SQL
)
CANDIDATES=$(printf '%s' "$CANDIDATE_SQL" | psql_q)

if [[ -z "$CANDIDATES" ]]; then
    log "Candidatos a drop: 0 (no hay particiones mas antiguas que ${RETENTION_MONTHS} meses)."
else
    COUNT=$(printf '%s\n' "$CANDIDATES" | grep -c .)
    log "Candidatos a drop: $COUNT mes(es) -> $(printf '%s' "$CANDIDATES" | tr '\n' ' ')"
fi

# ---- 3. DROP (modo real) ----
if [[ -n "$CANDIDATES" ]]; then
    while IFS= read -r M; do
        [[ -z "$M" ]] && continue
        # Guard de seguridad: M debe ser exactamente 6 digitos.
        if ! [[ "$M" =~ ^[0-9]{6}$ ]]; then
            log "GUARD: sufijo inesperado '$M' -> SE OMITE."
            continue
        fi
        EVENT="ma_audit_event_${M}"
        DELTA="ma_audit_delta_${M}"
        REF="ma_audit_ref_${M}"
        if [[ "$DRY_RUN" -eq 1 ]]; then
            log "[DRY-RUN] dropearia (orden FK): $DELTA, $REF, luego $EVENT"
        else
            log "DROP particiones del mes $M (orden FK: delta, ref, event)..."
            # delta y ref ANTES que event (FK delta/ref -> event).
            printf 'DROP TABLE IF EXISTS %s; DROP TABLE IF EXISTS %s; DROP TABLE IF EXISTS %s;' \
                "$DELTA" "$REF" "$EVENT" | psql_q
            log "DROP OK: $DELTA, $REF, $EVENT"
        fi
    done <<< "$CANDIDATES"
fi

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
