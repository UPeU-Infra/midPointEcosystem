#!/bin/bash
# FASE 3c — monitor + kill-switch del full import Estudiantes.
# Uso (en PROD): monitor-import.sh <ADMIN_USER> <ADMIN_PASS> <TASK_OID> [MAX_ITER]
# Vigila cada 20s: storm (409 en 60s), mem%, progreso de focos. Auto-suspende si:
#   - storm sostenido: 409/60s > 120 en 2 ventanas consecutivas (ACOTADO esperado ~18 focos)
#   - mem% >= 92 (OOM guard)
set -u
AU="$1"; AP="$2"; OID="$3"; MAX="${4:-200}"
REST="http://localhost:8080/midpoint/ws/rest"
PSQL(){ docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tAc "$1" 2>/dev/null | tr -d ' '; }
mem(){ docker stats --no-stream --format '{{.MemPerc}}' midpoint_server | tr -d '%' | cut -d. -f1; }
storm(){ docker logs midpoint_server --since 60s 2>&1 | grep -ciE '409|AlreadyExists|duplicate key'; }
suspend(){ curl -s -o /dev/null -X POST -u "$AU:$AP" "$REST/tasks/$OID/suspend"; echo "SUSPENDED task $OID"; }

prev_storm=0
for i in $(seq 1 "$MAX"); do
  ST=$(PSQL "SELECT executionstate FROM m_task WHERE oid='$OID';")
  USERS=$(PSQL "SELECT count(*) FROM m_user;")
  LIMBO=$(PSQL "SELECT count(*) FROM m_user u WHERE NOT EXISTS (SELECT 1 FROM m_ref_archetype ra WHERE ra.owneroid=u.oid);")
  M=$(mem); S=$(storm)
  echo "[$i] state=$ST users=$USERS limbo=$LIMBO mem=${M}% storm60s=$S"
  if [ "$ST" = "CLOSED" ] || [ -z "$ST" ]; then echo "TASK_DONE state=$ST"; break; fi
  if [ "${M:-0}" -ge 92 ]; then echo "MEM_GUARD mem=${M}% -> suspend"; suspend; break; fi
  if [ "${S:-0}" -gt 120 ] && [ "${prev_storm:-0}" -gt 120 ]; then echo "STORM_GUARD sustained ($prev_storm,$S) -> suspend"; suspend; break; fi
  prev_storm=$S
  sleep 20
done
echo "MONITOR_END"
