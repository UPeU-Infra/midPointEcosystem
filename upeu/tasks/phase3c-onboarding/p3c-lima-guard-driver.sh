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
# -----------------------------------------------------------------------------
# GUARD REFINADO (2026-06-04) — anti FALSO POSITIVO del create-or-adopt v1.3.9
# -----------------------------------------------------------------------------
# El run anterior (02:25:08Z) abortó por un FALSO POSITIVO: durante el adopt,
# por un instante coexisten 2 shadows VIVOS con el mismo cardnumber (el nuevo
# recien creado + el que se va a adoptar, ANTES de que el viejo se marque dead).
# El guard viejo leía dup_card(shadow)>=1 y abortaba -> fail-safe correcto pero
# transitorio. Verificado: Koha tenía 0 cardnumbers duplicados.
#
# El guard ahora distingue TRANSITORIO de REAL con DOS barreras:
#   1) Detector barato (cada ciclo): dup en shadow-cache (dead IS NOT TRUE,
#      exist=true). Si 0 -> todo OK. Si >0 -> NO aborta de inmediato: pasa a (2).
#   2) Verdad dura de KOHA via REST: por cada cardnumber sospechoso consulta
#      /api/v1/patrons?cardnumber=X -> header x-total-count. Koha es la verdad.
#         - algun cardnumber con x-total-count >= 2 en KOHA  -> DUP REAL -> KILL inmediato.
#         - todos <= 1 en Koha                               -> transitorio del adopt -> CONTINUA.
#   3) Anti-transitorio por persistencia (defensa en profundidad, por si Koha
#      REST no respondiera): un MISMO cardnumber dup en shadow-cache durante
#      >= STREAK_MAX ciclos consecutivos -> KILL (algo no converge).
#
# Resultado: 0 cardnumber duplicado REAL en Koha sigue siendo SAGRADO, pero el
# ruido transitorio del adopt ya no detiene el bootstrap.
#
# Uso (lanzar desde la Mac, queda corriendo en PROD):
#   setsid nohup ./p3c-lima-guard-driver.sh >> ~/phase3c-lima-bootstrap.log 2>&1 &
#
# Requiere en el entorno: MP_AU, MP_AP (admin REST MidPoint),
#                         KOHA_URL, KOHA_CID, KOHA_SECRET (Koha REST OAuth).
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
STREAK_MAX=2     # ciclos consecutivos con el MISMO cardnumber dup en shadow -> kill (fallback)

AU="${MP_AU:?MP_AU (admin user) requerido}"
AP="${MP_AP:?MP_AP (admin pass) requerido}"
# Koha REST (verdad dura). Si faltan, el guard cae al modo persistencia (STREAK).
KU="${KOHA_URL:-}"
KC="${KOHA_CID:-}"
KS="${KOHA_SECRET:-}"

log(){ echo "[$(date -u +%H:%M:%SZ)] $*"; }
P(){ docker exec "$DATA" psql -U midpoint -d midpoint -tAc "$1" 2>/dev/null | tr -d ' '; }
mem(){ docker stats --no-stream --format '{{.MemPerc}}' "$SRV" | tr -d '%' | cut -d. -f1; }

# --- shadow-cache (item 128 = cardnumber), solo shadows VIVOS ---
# Lista (una por linea) de cardnumbers con >1 shadow vivo en el cache.
dupcards_list(){
  P "SELECT trim(both '\"' FROM attributes->>'128')
       FROM m_shadow
      WHERE resourcereftargetoid='$KOHA_RES'
        AND attributes ? '128'
        AND dead IS NOT TRUE AND exist=true
      GROUP BY attributes->'128'
     HAVING count(*)>1;"
}
# numero de cardnumbers sospechosos (rapido)
dupcard(){ dupcards_list | grep -c . ; }
kohashadows(){ P "SELECT count(*) FROM m_shadow WHERE resourcereftargetoid='$KOHA_RES' AND dead IS NOT TRUE AND exist=true;"; }
limbo(){ P "SELECT count(*) FROM m_user u WHERE u.ext->>'217'='student' AND NOT EXISTS (SELECT 1 FROM m_ref_archetype ra WHERE ra.owneroid=u.oid) AND (u.lifecyclestate IS NULL OR u.lifecyclestate<>'archived');"; }
tstate(){ P "SELECT executionstate FROM m_task WHERE oid='$1';"; }
suspend(){ curl -s -o /dev/null -X POST -u "$AU:$AP" "$REST/tasks/$1/suspend"; }
resume(){  curl -s -o /dev/null -X POST -u "$AU:$AP" "$REST/tasks/$1/resume"; }

# --- Koha REST: verdad dura ---
KTOK=""
koha_token(){
  [ -z "$KU" ] && { KTOK=""; return 1; }
  KTOK=$(curl -sk -X POST "$KU/api/v1/oauth/token" \
          -d 'grant_type=client_credentials' \
          -d "client_id=$KC" -d "client_secret=$KS" \
          | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))' 2>/dev/null)
  [ -n "$KTOK" ]
}
# x-total-count de borrowers en KOHA para un cardnumber. Devuelve "" si no se pudo consultar.
koha_count(){
  local card="$1" out
  [ -z "$KTOK" ] && return 1
  out=$(curl -sk -H "Authorization: Bearer $KTOK" \
        "$KU/api/v1/patrons?cardnumber=$card&_per_page=2" -D - -o /dev/null 2>/dev/null \
        | tr -d '\r' | awk 'tolower($1)=="x-total-count:"{print $2}')
  echo "$out"
}
# Confirma si ALGUN cardnumber de la lista tiene >=2 borrowers REALES en Koha.
# stdout: "REAL <card>=<n> ..." si hay dup real ; "" si todos <=1 ; "UNKNOWN" si Koha no respondio.
koha_confirm_real(){
  local cards="$1" card n real="" any_ok=0
  koha_token || { echo "UNKNOWN"; return; }
  while IFS= read -r card; do
    [ -z "$card" ] && continue
    n=$(koha_count "$card")
    if [ -n "$n" ]; then
      any_ok=1
      if [ "$n" -ge 2 ] 2>/dev/null; then real="$real $card=$n"; fi
    fi
  done <<< "$cards"
  if [ -n "$real" ]; then echo "REAL$real"
  elif [ "$any_ok" -eq 1 ]; then echo ""        # consultado, todos <=1 -> transitorio
  else echo "UNKNOWN"; fi                        # Koha no respondio
}

# --- arranque ---
DUP0_LIST=$(dupcards_list); DUP0=$(echo "$DUP0_LIST" | grep -c .)
log "==== DRIVER START. dup_card(shadow)=$DUP0  koha_shadows=$(kohashadows)  limboStud=$(limbo)  mem=$(mem)% | KohaREST=$([ -n "$KU" ] && echo on || echo off) STREAK_MAX=$STREAK_MAX ===="
if [ "${DUP0:-1}" != "0" ]; then
  # Hay sospechosos ANTES de arrancar -> confirmar con Koha antes de bloquear.
  log "dup_card=$DUP0 al inicio. Sospechosos: $(echo "$DUP0_LIST" | tr '\n' ' '). Consultando Koha..."
  V=$(koha_confirm_real "$DUP0_LIST")
  case "$V" in
    REAL*) log "FATAL: DUP REAL en Koha al inicio ($V). NO se lanza nada. Investigar."; exit 1;;
    UNKNOWN) log "WARN: Koha REST no respondio. Sospechosos pueden ser transitorios del adopt previo. Continuo con guard de persistencia.";;
    *) log "OK: Koha confirma <=1 borrower por cardnumber (transitorios del adopt). Continuo.";;
  esac
fi

PREV_DUP=""   # set de cardnumbers dup del ciclo anterior (para STREAK)
STREAK=0

# --- guard loop generico: vigila la task $1 hasta CLOSED; suspende ante dup REAL/mem ---
run_guarded(){
  local OID="$1" LABEL="$2"
  log ">>> Lanzando $LABEL ($OID)"
  resume "$OID"   # por si quedo runnable; arranca la ejecucion
  local st mm dc ks lb dlist V
  while :; do
    st=$(tstate "$OID"); mm=$(mem); ks=$(kohashadows); lb=$(limbo)
    dlist=$(dupcards_list); dc=$(echo "$dlist" | grep -c .)
    log "$LABEL state=$st mem=${mm}% dup_card=$dc koha_shadows=$ks limboStud=$lb streak=$STREAK"

    if [ "${dc:-0}" -gt 0 ]; then
      # Sospecha. Barrera 2: verdad dura de Koha.
      V=$(koha_confirm_real "$dlist")
      if [[ "$V" == REAL* ]]; then
        log "!!!! KILL-SWITCH DUP REAL confirmado en KOHA ($V) -> SUSPEND TODO. DAÑO REAL, PARAR."
        suspend "$TASK_A"; suspend "$TASK_B"
        return 9
      fi
      # No confirmado real -> transitorio. Barrera 3: persistencia del mismo set.
      local cur; cur=$(echo "$dlist" | sort | tr '\n' ',')
      if [ "$cur" = "$PREV_DUP" ] && [ -n "$cur" ]; then
        STREAK=$((STREAK+1))
      else
        STREAK=1
      fi
      PREV_DUP="$cur"
      if [ "$STREAK" -ge "$STREAK_MAX" ]; then
        log "!!!! KILL-SWITCH dup persistente $STREAK ciclos (mismo set: $(echo "$dlist" | tr '\n' ' ')) Koha=[$V] -> SUSPEND TODO. No converge, PARAR."
        suspend "$TASK_A"; suspend "$TASK_B"
        return 9
      fi
      log "  dup_card=$dc transitorio del adopt (Koha<=1) streak=$STREAK/$STREAK_MAX -> CONTINUO."
    else
      STREAK=0; PREV_DUP=""
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
