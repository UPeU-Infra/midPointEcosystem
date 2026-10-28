#!/usr/bin/env bash
#
# tareas-ventana.sh
# ------------------------------------------------------------------------------
# Tareas programadas de midPoint durante las ventanas F2/F3 (y el ensayo F1).
# Lista de tareas: inventario §6 (docs/upgrade-4.11/INVENTARIO-PROD-4.10.md).
#
# ORDENES
#   estado              solo lectura (SQL): las 8 de negocio + las 3 de sistema,
#                       y cualquier otra tarea RUNNING
#   suspender           POST /tasks/<oid>/suspend de las 8 de negocio (las 3 de
#                       sistema se paran con el nodo); luego `estado`
#   reanudar <oid>      POST /tasks/<oid>/resume de UNA tarea (de una en una,
#                       midiendo entre una y otra)
#   ejecutar <oid>      POST /tasks/<oid>/run (lanzarla ya; debe estar RUNNABLE)
#
# OJO al reanudar: las recons tienen misfireAction=executeImmediately. Si se
# reanuda una tarea cuya hora ya paso MIENTRAS estaba suspendida, arranca al
# instante. Con la ventana de 11:30 a 15:30 (Lima) no se salta ninguna (todas son
# de 02:00 a 09:15), asi que al reanudar esperan a la manana siguiente.
#
# Corre en el HOST (REST en localhost; SQL de solo lectura por docker exec).
# ENTORNO: MP_BASE (http://localhost:8080/midpoint), MP_REST_USER (administrator),
#          MP_REST_PASS (se pide si falta), PG_CONTAINER (midpoint-midpoint_data-1)
# ------------------------------------------------------------------------------
set -euo pipefail
MP_BASE="${MP_BASE:-http://localhost:8080/midpoint}"
MP_REST_USER="${MP_REST_USER:-administrator}"
PG_CONTAINER="${PG_CONTAINER:-midpoint-midpoint_data-1}"

# Orden diario (hora de Lima). Se suspenden en orden inverso.
NEGOCIO=(
  a1e5b2c3-0001-4def-9abc-202406060001   # 02:00 recon-entra-id-daily (~7 h)
  d71a0003-0000-4000-a000-d71a00000003   # 03:30 recon-ldap-dti-groups-daily
  d71a0004-0000-4000-a000-d71a00000004   # 04:15 recompute-dti-teams-daily
  a1c0de00-0000-4000-8000-00000000a05e   # 05:00 import-oracle-lamb-ausencias-daily
  23b9fde4-6a5f-4c84-9370-0971fb27be73   # 06:00 recon-oracle-lamb-trabajadores-daily
  9bcfb273-3d8e-4acb-84b0-e7c8b490975b   # 06:20 recon-oracle-lamb-estudiantes-daily
  86c3766a-77a6-4635-853c-998b26cad45c   # 07:45 recon-oracle-lamb-egresados-daily
  58ef8e82-867e-432a-923e-98adcd7c57fa   # 09:15 recon-koha-upeu-daily (~2 h)
)
SISTEMA=(00000000-0000-0000-0000-000000000005 00000000-0000-0000-0000-000000000006 00000000-0000-0000-0000-000000000007)

sql() { docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' "$PG_CONTAINER" psql -U midpoint -d midpoint -v ON_ERROR_STOP=1; }
need_pass() { [[ -n "${MP_REST_PASS:-}" ]] || { read -r -s -p "Contrasena REST de $MP_REST_USER: " MP_REST_PASS; echo; }; }
post() {  # post <oid> <accion>
    local code
    code=$(curl -sS -o /dev/null -w '%{http_code}' -u "$MP_REST_USER:$MP_REST_PASS" -X POST "$MP_BASE/ws/rest/tasks/$1/$2")
    echo "  $2 $1 -> HTTP $code"
    [[ "$code" =~ ^2 ]]
}
lista_sql() { local IFS=,; local a=("$@"); printf "'%s'" "${a[0]}"; for o in "${a[@]:1}"; do printf ",'%s'" "$o"; done; }

estado() {
    sql <<SQL
SELECT nameorig AS tarea, executionstate AS ejecucion, schedulingstate AS planificacion, oid
FROM m_task WHERE oid IN ($(lista_sql "${NEGOCIO[@]}" "${SISTEMA[@]}")) ORDER BY nameorig;
SELECT 'OTRAS EN MARCHA' AS aviso, nameorig, oid FROM m_task
WHERE executionstate = 'RUNNING' AND oid NOT IN ($(lista_sql "${NEGOCIO[@]}" "${SISTEMA[@]}"));
SQL
}

case "${1:-}" in
estado) estado ;;
suspender)
    need_pass
    for (( i=${#NEGOCIO[@]}-1; i>=0; i-- )); do post "${NEGOCIO[$i]}" suspend || echo "  ^ revisar a mano"; done
    estado
    ;;
reanudar) need_pass; post "${2:?falta el OID}" resume; estado ;;
ejecutar) need_pass; post "${2:?falta el OID}" run; estado ;;
*) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
