#!/usr/bin/env bash
#
# bd-copia-local.sh
# ------------------------------------------------------------------------------
# Copia local de la BD de midPoint para la VUELTA ATRAS RAPIDA de las ventanas F2/F3.
#
#   CREATE DATABASE midpoint_pre_<etiqueta> TEMPLATE midpoint STRATEGY FILE_COPY
#
# Copia ficheros dentro del mismo Postgres (con midPoint parado): minutos, no horas,
# e incluye la auditoria (que un pg_dump a S3 no puede subir dentro de una ventana:
# ~37 GB a ~5 MB/s). La vuelta atras es renombrar dos bases: segundos.
# La copia FUERA del host la hace backup-midpoint-s3.sh --pre-upgrade.
#
# Detalles que el TEMPLATE no copia y este script si:
#   - ajustes ALTER DATABASE ... SET (en PROD: enable_partitionwise_join=on, medido
#     el 28-oct) y ALTER ROLE ... IN DATABASE ... SET.
#
# ORDENES
#   estado                    solo lectura: bases, tamanos, disco libre, conexiones
#   crear     <etiqueta>      copia midpoint -> midpoint_pre_<etiqueta> (midPoint PARADO)
#   restaurar <etiqueta>      midpoint -> midpoint_fallida_<ts>; midpoint_pre_<etiqueta> -> midpoint
#   borrar    <nombre>        DROP DATABASE <nombre> (nunca 'midpoint'); pide confirmacion
#
# Corre en el HOST (docker exec al contenedor de Postgres, conectando a la base
# `postgres` para no bloquear la plantilla). No contiene secretos.
#
# ENTORNO: PG_CONTAINER (midpoint-midpoint_data-1), PG_USER (midpoint),
#          DB (midpoint), MP_CONTAINER (midpoint_server), MARGIN_GB (8)
# ------------------------------------------------------------------------------
set -euo pipefail

PG_CONTAINER="${PG_CONTAINER:-midpoint-midpoint_data-1}"
PG_USER="${PG_USER:-midpoint}"
DB="${DB:-midpoint}"
MP_CONTAINER="${MP_CONTAINER:-midpoint_server}"
MARGIN_GB="${MARGIN_GB:-8}"

q()  { docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d postgres -tA -F'|' -v ON_ERROR_STOP=1 "$@"; }
qdb() { local d="$1"; shift; docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$d" -tA -F'|' -v ON_ERROR_STOP=1 "$@"; }
die() { echo "ABORTO: $*" >&2; exit 1; }
ts()  { date '+%Y-%m-%d %H:%M:%S'; }

mp_parado() {
    [[ -z "$(docker ps --filter "name=^/${MP_CONTAINER}$" --format '{{.Names}}')" ]] \
        || die "$MP_CONTAINER esta en marcha: pararlo antes (docker compose stop midpoint_server)."
}
conexiones() { q -c "SELECT count(*) FROM pg_stat_activity WHERE datname = '$1' AND pid <> pg_backend_pid();"; }
existe()     { [[ "$(q -c "SELECT count(*) FROM pg_database WHERE datname = '$1';")" == "1" ]]; }
libre_gb()   { docker exec "$PG_CONTAINER" df -BG --output=avail /var/lib/postgresql/data | tail -1 | tr -dc '0-9'; }
huella() {   # numeros de esquema + recuento de usuarios: deben coincidir copia/original
    qdb "$1" -c "SELECT (SELECT string_agg(name||'='||value, ',' ORDER BY name) FROM m_global_metadata), (SELECT count(*) FROM m_user), (SELECT count(*) FROM m_shadow);"
}
check_etiqueta() { [[ "$1" =~ ^[a-z0-9_]+$ ]] || die "etiqueta '$1' invalida (solo a-z, 0-9, _)"; }

case "${1:-}" in
estado)
    echo "[$(ts)] Bases (nombre|tamano|conexiones):"
    q -c "SELECT datname, pg_size_pretty(pg_database_size(datname)), (SELECT count(*) FROM pg_stat_activity a WHERE a.datname = d.datname) FROM pg_database d WHERE datname NOT IN ('template0','template1','postgres') ORDER BY 1;"
    echo "Ajustes por base (base|rol|ajustes):"
    q -c "SELECT d.datname, coalesce(r.rolname,'-'), s.setconfig FROM pg_db_role_setting s JOIN pg_database d ON d.oid = s.setdatabase LEFT JOIN pg_roles r ON r.oid = s.setrole ORDER BY 1;"
    echo "Disco libre para PGDATA: $(libre_gb) GB"
    ;;
crear)
    TAG="${2:?falta la etiqueta, p. ej. 4102}"; check_etiqueta "$TAG"; NEW="${DB}_pre_${TAG}"
    mp_parado
    existe "$NEW" && die "ya existe $NEW"
    n=$(conexiones "$DB"); [[ "$n" == "0" ]] || die "$DB tiene $n conexion(es) abiertas (q -c \"select * from pg_stat_activity\")."
    size_gb=$(q -c "SELECT ceil(pg_database_size('$DB')/1024.0^3);")
    free_gb=$(libre_gb)
    echo "[$(ts)] $DB ocupa ${size_gb} GB; libres ${free_gb} GB; margen exigido ${MARGIN_GB} GB"
    (( free_gb >= size_gb + MARGIN_GB )) || die "no cabe: hacen falta $((size_gb + MARGIN_GB)) GB y hay ${free_gb} GB."
    t0=$(date +%s)
    q -c "CREATE DATABASE ${NEW} TEMPLATE ${DB} STRATEGY FILE_COPY;"
    # Ajustes ALTER DATABASE/ROLE ... SET de la original -> copia
    q -c "SELECT coalesce(r.rolname,''), cfg FROM pg_db_role_setting s JOIN pg_database d ON d.oid = s.setdatabase LEFT JOIN pg_roles r ON r.oid = s.setrole, unnest(s.setconfig) cfg WHERE d.datname = '$DB';" \
    | while IFS='|' read -r rol cfg; do
        [[ -z "$cfg" ]] && continue
        k="${cfg%%=*}"; v="${cfg#*=}"
        if [[ -z "$rol" ]]; then q -c "ALTER DATABASE ${NEW} SET ${k} = '${v}';" < /dev/null
        else q -c "ALTER ROLE \"${rol}\" IN DATABASE ${NEW} SET ${k} = '${v}';" < /dev/null; fi
        echo "  ajuste copiado: ${rol:-(base)} ${k}=${v}"
    done
    h0=$(huella "$DB"); h1=$(huella "$NEW")
    echo "[$(ts)] Copia creada en $(( $(date +%s) - t0 )) s"
    echo "  original: $h0"; echo "  copia:    $h1"
    [[ "$h0" == "$h1" ]] && echo "OK: la copia coincide (esquema, usuarios, shadows)." || die "la huella NO coincide"
    ;;
restaurar)
    TAG="${2:?falta la etiqueta}"; check_etiqueta "$TAG"; SRC="${DB}_pre_${TAG}"; FAILED="${DB}_fallida_$(date +%Y%m%d%H%M)"
    mp_parado
    existe "$SRC" || die "no existe $SRC"
    echo "Se renombrara: $DB -> $FAILED ; $SRC -> $DB"
    if [[ "${3:-}" != "--yes" ]]; then read -r -p "¿Seguir? escribe SI: " ok; [[ "$ok" == "SI" ]] || die "cancelado"; fi
    t0=$(date +%s)
    q -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname IN ('$DB','$SRC') AND pid <> pg_backend_pid();" >/dev/null
    q -c "ALTER DATABASE ${DB} RENAME TO ${FAILED};"
    q -c "ALTER DATABASE ${SRC} RENAME TO ${DB};"
    echo "[$(ts)] Renombrado en $(( $(date +%s) - t0 )) s. Ahora: $(huella "$DB")"
    echo "La base fallida queda como $FAILED (para analisis). Borrarla cuando no haga falta: $0 borrar $FAILED"
    ;;
borrar)
    NAME="${2:?falta el nombre de la base}"
    [[ "$NAME" == "$DB" || "$NAME" == "postgres" || "$NAME" == template* ]] && die "no se borra '$NAME'"
    [[ "$NAME" =~ ^${DB}_(pre|fallida)_[a-z0-9_]+$ ]] || die "solo se borran ${DB}_pre_* o ${DB}_fallida_*"
    existe "$NAME" || die "no existe $NAME"
    read -r -p "DROP DATABASE $NAME ($(q -c "SELECT pg_size_pretty(pg_database_size('$NAME'));")). Escribe el nombre para confirmar: " ok
    [[ "$ok" == "$NAME" ]] || die "cancelado"
    q -c "DROP DATABASE ${NAME};"; echo "Borrada $NAME. Libres: $(libre_gb) GB"
    ;;
*)
    sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
