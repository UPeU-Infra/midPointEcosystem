#!/bin/bash
# =============================================================================
# FASE 3c — DRIVER + KILL-SWITCH SERVER-SIDE del bootstrap Lima (relanzamiento).
#
# Corre EN PROD bajo `nohup setsid` -> sobrevive a cualquier desconexion del
# cliente. Secuencia Task A (bootstrap assign) -> Task B (recompute straggler),
# con guard de dup_card (sagrado) + mem en cada ciclo.
#
# Las tasks A/B son NATIVAS de MidPoint (iterativeScripting/recomputation): ya
# corren server-side en el task manager. Este driver solo las secuencia y vigila.
# Si el driver muriera, las tasks SIGUEN corriendo en MidPoint (solo se perderia
# el guard -> por eso el guard es lo critico que mantenemos vivo via nohup setsid).
#
# Uso (lanzar desde la Mac, queda corriendo en PROD):
#   setsid nohup ./p3c-lima-guard-driver.sh >> ~/phase3c-lima-bootstrap.log 2>&1 &
#
# Requiere en el entorno: MP_AU, MP_AP (admin REST MidPoint).
# =============================================================================
set -u

LOG="$HOME/phase3c-lima-bootstrap.log"
REST="http://localhost:8080/midpoint/ws/rest"
DATA="midpoint-midpoint_data-1"
SRV="midpoint_server"
KOHA_RES="9b5a7c81-47aa-42ac-9a08-4de8b64935af"
STUDENT_ARCH="3037fbd2-db02-4ffd-8b1a-83fab5e686aa"
TASK_A="d1a2b3c4-3c00-4abc-9def-0000003c1a3a"   # bootstrap assign
TASK_B="d1a2b3c4-3c00-4abc-9def-0000003c1b3b"   # recompute straggler
MEM_MAX=88
POLL=30

AU="${MP_AU:?MP_AU (admin user) requerido}"
AP="${MP_AP:?MP_AP (admin pass) requerido}"

log(){ echo "[$(date -u +%H:%M:%SZ)] $*"; }
P(){ docker exec "$DATA" psql -U midpoint -d midpoint -tAc "$1" 2>/dev/null | tr -d ' '; }
mem(){ docker stats --no-stream --format '{{.MemPerc}}' "$SRV" | tr -d '%' | cut -d. -f1; }
# dup_card desde el SHADOW CACHE (item 128 = cardnumber). Server-side, sin mysql.
dupcard(){ P "SELECT count(*) FROM (SELECT attributes->'128' c FROM m_shadow WHERE resourcereftargetoid='$KOHA_RES' AND attributes ? '128' AND (dead IS NULL OR dead='false') GROUP BY attributes->'128' HAVING count(*)>1) x;"; }
kohashadows(){ P "SELECT count(*) FROM m_shadow WHERE resourcereftargetoid='$KOHA_RES' AND (dead IS NULL OR dead='false');"; }
limbo(){ P "SELECT count(*) FROM m_user u WHERE u.ext->>'217'='student' AND NOT EXISTS (SELECT 1 FROM m_ref_archetype ra WHERE ra.owneroid=u.oid) AND (u.lifecyclestate IS NULL OR u.lifecyclestate<>'archived');"; }
tstate(){ P "SELECT executionstate FROM m_task WHERE oid='$1';"; }
suspend(){ curl -s -o /dev/null -X POST -u "$AU:$AP" "$REST/tasks/$1/suspend"; }
resume(){  curl -s -o /dev/null -X POST -u "$AU:$AP" "$REST/tasks/$1/resume"; }

DUP0=$(dupcard)
log "==== DRIVER START. dup_card(shadow)=$DUP0  koha_shadows=$(kohashadows)  limboStud=$(limbo)  mem=$(mem)% ===="
if [ "${DUP0:-1}" != "0" ]; then
  log "FATAL: dup_card != 0 ANTES de arrancar ($DUP0). NO se lanza nada. Revisar manualmente."
  exit 1
fi

# --- guard loop generico: vigila la task $1 hasta CLOSED; suspende ante dup/mem ---
run_guarded(){
  local OID="$1" LABEL="$2"
  log ">>> Lanzando $LABEL ($OID)"
  resume "$OID"   # por si quedo runnable; arranca la ejecucion
  local st mm dc ks lb
  while :; do
    st=$(tstate "$OID"); mm=$(mem); dc=$(dupcard); ks=$(kohashadows); lb=$(limbo)
    log "$LABEL state=$st mem=${mm}% dup_card=$dc koha_shadows=$ks limboStud=$lb"
    if [ "${dc:-1}" != "0" ]; then
      log "!!!! KILL-SWITCH dup_card=$dc -> SUSPEND $LABEL (y todas). DAÑO POTENCIAL, PARAR."
      suspend "$TASK_A"; suspend "$TASK_B"
      return 9
    fi
    if [ "${mm:-0}" -ge "$MEM_MAX" ]; then
      log "!!!! MEM_GUARD mem=${mm}% >= $MEM_MAX -> SUSPEND $LABEL (pausa por OOM)."
      suspend "$OID"
      return 8
    fi
    if [ "$st" = "closed" ] || [ -z "$st" ]; then
      log "<<< $LABEL CLOSED."
      return 0
    fi
    sleep "$POLL"
  done
}

run_guarded "$TASK_A" "TASK_A(bootstrap-assign)"; RA=$?
if [ "$RA" -ne 0 ]; then
  log "TASK_A no completo limpio (rc=$RA). NO se lanza Task B. Driver END."
  log "==== DRIVER END (abort). dup_card=$(dupcard) koha_shadows=$(kohashadows) limboStud=$(limbo) ===="
  exit "$RA"
fi

run_guarded "$TASK_B" "TASK_B(recompute-straggler)"; RB=$?

log "==== DRIVER END. rc_A=$RA rc_B=$RB | dup_card=$(dupcard) koha_shadows=$(kohashadows) limboStud=$(limbo) mem=$(mem)% ===="
