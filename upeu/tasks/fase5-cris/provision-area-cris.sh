#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# provision-area-cris.sh — VÍA RÁPIDA reutilizable: provisionar un ÁREA al DSpace-CRIS
#
# Parametrizado por ÁREA. Materializa afiliaciones persona→OrgUnit y proyecta
# Person + identidad + afiliación CERIF al CRIS, SIN storms a Koha/Entra/LDAP.
#
# DISEÑO (por qué es "vía rápida" y churn-free):
#   - NO usa ?options=reconcile contra recursos pesados (Koha/Entra/LDAP/CRIS). El
#     reconcile fuerza fetch de TODAS las proyecciones por persona → ~1,5 días + churn.
#   - Materializa afiliaciones vía RECOMPUTE (computa deltas del modelo en repo, sin
#     fetch externo). El recompute solo escribe a un target si hay delta real.
#   - Proyecta a CRIS asignando **AR-CRIS-Person** (OID c4e8f1a2-…) DIRECTAMENTE al
#     foco. Esa AR aporta SOLO la construction CRIS (kind=account intent=person),
#     gated por su propia <condition> (afiliación research-center O padrón RENACYT).
#     => proyecta Person SOLO al CRIS. CERO churn a Koha/Entra/LDAP (no induce esos AR).
#   - BR-Investigador (el "puesto" completo: M365 A3 + Koha + LDAP + Entra + Zoom…) es
#     una decisión de POLICY que SÍ cambia entitlements → NO se aplica como efecto
#     colateral de una corrida CRIS. Flag --assign-br opcional para hacerlo deliberado.
#
# MODOS:
#   AFFIL    — Fase 1: recompute multihilo del scope para materializar afiliaciones
#              persona→OrgUnit (assignment desde el inbound ya reconciliado). No CRIS.
#   CRIS     — Fase 2: asigna AR-CRIS-Person (default) y/o BR-Investigador (--assign-br)
#              a cada foco del OIDS file → la construction escribe Person+CERIF al CRIS.
#              Idempotente (upsert por orcid/dni; afiliación reltype 5 place 0 sin dup).
#
# USO:
#   provision-area-cris.sh AFFIL <admin_user> <admin_pass> [--workers N]
#       (recompute del subtree del ÁREA — ver vars AREA_SUBTREE_OID abajo)
#   provision-area-cris.sh CRIS  <admin_user> <admin_pass> <oids_file> [--assign-br] [--workers N]
#       (oids_file = 1 OID de UserType por línea; los gate-eligible del área)
#
# PARÁMETROS POR ÁREA (editar el bloque CONFIG o exportar como env):
#   AREA_LABEL          — etiqueta para checkpoints/logs (ej. "dgi")
#   AREA_SUBTREE_OID    — OID del Org raíz del área (subtree) para el recompute AFFIL
#   CRIS_RESOURCE_OID   — resource CRIS (normalmente 3f8b2d61-…; igual para toda UPeU)
#   AR_CRIS_PERSON_OID  — AR construction-driven CRIS person (c4e8f1a2-…)
#   BR_PUESTO_OID       — puesto completo del área (BR-Investigador 70c1606c-… para DGI)
#
# IDEMPOTENTE + RESUMIBLE: checkpoint en /tmp/cris_<AREA_LABEL>_<MODE>_done.txt.
#
# ─── INCIDENTE OOM 2026-06-18 (por qué este driver está endurecido) ───────────
# Una corrida CRIS con --workers 4 ahogó el heap del JVM (98.6%) tras ~395/3.776
# focos → OOM → MidPoint reiniciado. Causa raíz: el recompute multihilo (4 workers)
# acumula lens contexts en heap sin liberarlos a tiempo, y el JVM corre con
# -XX:+DisableExplicitGC (System.gc() NO baja el heap; solo G1 decide). El gate de
# heap del driver original solo se evaluaba ENTRE lotes, así que un lote de 4
# recomputes concurrentes disparaba el heap de golpe sin chance de frenar.
# ENDURECIMIENTO (este archivo):
#   - WORKERS por defecto 1; TOPE DURO = 2 (se ignora cualquier valor mayor).
#   - Proceso en LOTES PEQUEÑOS (BATCH_SIZE, default 50) con PAUSA entre lotes.
#   - Gate de heap ANTES de cada lote: pausa≥75 (espera GC con backoff), ABORT≥88.
#   - RESTART PROGRAMADO de midpoint_server cada RESTART_EVERY_BATCHES lotes (default 8)
#     SOLO si el heap no bajó de HEAP_SOFT tras la espera de GC (patrón conocido de
#     este PROD: el heap no cede sin restart). Gate de disco previo + espera healthy.
#   - Gate de disco abort≥92.
# CÓDIGOS HTTP CRIS: 204/240/250 = ÉXITO (dato en CRIS; shadow dead = ruido del connector).
#   400 'without any attributes' = dato sucio del foco (sin dni/givenName) → excluido, no fail.
#   Verificar éxito REAL en CRIS (matches por dni=1), NO por HTTP code.
# ─────────────────────────────────────────────────────────────────────────────
set -u

# ── CONFIG POR ÁREA (overridable por env) ────────────────────────────────────
AREA_LABEL="${AREA_LABEL:-dgi}"
AREA_SUBTREE_OID="${AREA_SUBTREE_OID:-00000000-0000-0000-0000-205881674697}"   # subtree DGI
CRIS_RESOURCE_OID="${CRIS_RESOURCE_OID:-3f8b2d61-7c94-4a05-9e3b-6d1f8a2c5e70}"
AR_CRIS_PERSON_OID="${AR_CRIS_PERSON_OID:-c4e8f1a2-9b03-4d57-8e62-1a4f7c0d9e35}"
BR_PUESTO_OID="${BR_PUESTO_OID:-70c1606c-9d56-42ce-989f-a025c98f9c0b}"          # BR-Investigador
BASE="${BASE:-http://localhost:8080/midpoint/ws/rest}"

# ── ARGS ──────────────────────────────────────────────────────────────────────
MODE="${1:?MODE=AFFIL|CRIS}"; shift
A_USER="${1:?admin_user}"; shift
A_PASS="${1:?admin_pass}"; shift

OIDS=""; ASSIGN_BR=0; WORKERS=1
while [ $# -gt 0 ]; do
  case "$1" in
    --assign-br) ASSIGN_BR=1 ;;
    --workers)   shift; WORKERS="${1:-1}" ;;
    --batch)     shift; BATCH_SIZE="${1:-50}" ;;
    *)           OIDS="$1" ;;
  esac
  shift
done

# ── LÍMITES DE SEGURIDAD (endurecimiento post-OOM 2026-06-18) ─────────────────
# Tope duro de concurrencia: NUNCA más de 2 workers (el OOM ocurrió con 4).
if [ "${WORKERS:-1}" -gt 2 ]; then
  echo "AVISO: --workers $WORKERS excede el tope duro post-OOM. Forzando WORKERS=2."
  WORKERS=2
fi
BATCH_SIZE="${BATCH_SIZE:-50}"            # focos por lote
PAUSE_BETWEEN_BATCHES="${PAUSE_BETWEEN_BATCHES:-20}"   # seg de pausa entre lotes (deja respirar a G1)
HEAP_ABORT="${HEAP_ABORT:-88}"            # heap% que ABORTA el driver
HEAP_SOFT="${HEAP_SOFT:-75}"              # heap% que dispara espera de GC
HEAP_OK="${HEAP_OK:-65}"                  # heap% objetivo tras espera/restart
RESTART_EVERY_BATCHES="${RESTART_EVERY_BATCHES:-8}"    # cada N lotes, restart si heap sigue alto
GC_WAIT_MAX="${GC_WAIT_MAX:-6}"           # nº de esperas de 30s antes de considerar restart

DONE="/tmp/cris_${AREA_LABEL}_${MODE}_done.txt"; touch "$DONE"

# ── GATES ───────────────────────────────────────────────────────────────────
# NOTA: el contenedor corre JRE (sin jcmd/jstat) y con -XX:+DisableExplicitGC,
# así que NO podemos forzar GC ni leer el heap del JVM directamente. Usamos el
# MemPerc del contenedor (RSS vs límite 10GiB) como proxy del heap — fue la métrica
# que llegó a 98.6% en el OOM, así que es la señal correcta a vigilar.
heap_pct () { docker stats --no-stream --format '{{.MemPerc}}' midpoint_server 2>/dev/null | tr -d '%' | cut -d. -f1; }
disk_pct () { df -h / | awk 'NR==2{gsub("%","",$5);print $5}'; }

# Espera healthy del contenedor tras un restart (hasta ~3 min).
wait_healthy () {
  local i=0
  while [ $i -lt 36 ]; do
    local S; S=$(docker inspect --format '{{.State.Health.Status}}' midpoint_server 2>/dev/null)
    [ "$S" = "healthy" ] && { echo "  midpoint_server healthy."; return 0; }
    sleep 5; i=$((i+1))
  done
  echo "  ADVERTENCIA: midpoint_server no llegó a healthy en 3min."; return 1
}

# Restart programado: solo si el disco lo permite (PG necesita espacio).
restart_midpoint () {
  local D; D=$(disk_pct)
  if [ "${D:-0}" -ge 92 ]; then echo "  RESTART omitido: disco ${D}% >=92 -> ABORT"; exit 3; fi
  echo "  RESTART PROGRAMADO de midpoint_server (heap alto, GC no cede)..."
  docker restart midpoint_server >/dev/null 2>&1
  sleep 10
  wait_healthy
}

# Gate de disco + heap ANTES de cada lote. Devuelve por variable HEAP_STILL_HIGH=1
# si tras esperar GC el heap no bajó de HEAP_SOFT (señal para restart programado).
HEAP_STILL_HIGH=0
gate () {
  HEAP_STILL_HIGH=0
  local D; D=$(disk_pct)
  if [ "${D:-0}" -ge 92 ]; then echo "DISCO ${D}% >=92 -> ABORT"; exit 3; fi
  local H; H=$(heap_pct)
  if [ "${H:-0}" -ge "$HEAP_ABORT" ]; then echo "HEAP ${H}% >=${HEAP_ABORT} -> ABORT (protección OOM)"; exit 2; fi
  local waited=0
  while [ "${H:-0}" -ge "$HEAP_SOFT" ]; do
    echo "  heap ${H}% >=${HEAP_SOFT}, esperando GC 30s ($((waited+1))/${GC_WAIT_MAX})..."
    sleep 30; H=$(heap_pct); waited=$((waited+1))
    if [ "${H:-0}" -ge "$HEAP_ABORT" ]; then echo "HEAP ${H}% >=${HEAP_ABORT} -> ABORT"; exit 2; fi
    if [ "$waited" -ge "$GC_WAIT_MAX" ]; then HEAP_STILL_HIGH=1; break; fi
  done
}

# ─────────────────────────────────────────────────────────────────────────────
# MODO AFFIL — Fase 1: materializar afiliaciones vía recompute multihilo del subtree.
# Lanza una TaskType recomputation con workerThreads. El recompute re-evalúa los
# inbounds ya reconciliados y materializa el assignment persona→OrgUnit SIN tocar
# recursos externos (no reconcile). NO escribe a CRIS si el resource sigue proposed.
# ─────────────────────────────────────────────────────────────────────────────
if [ "$MODE" = "AFFIL" ]; then
  gate
  TASK_OID="f5a1c3b2-9d08-4e57-ae62-2b4f7c0d9e36"   # OID fijo de recompute-dgi-investigadores
  # POST-OOM: el recompute multihilo de un subtree grande es lo que ahogó el heap.
  # WORKERS ya viene topado a ≤2 arriba. Para subtrees grandes preferir 1 worker.
  echo "AFFIL: lanzando recompute subtree $AREA_SUBTREE_OID con $WORKERS worker(s) (task $TASK_OID)..."
  echo "       (tope post-OOM: WORKERS≤2; monitorear heap durante la task y suspender si >=${HEAP_ABORT}%)"
  # Importa/actualiza la task (overwrite) con executionState=runnable + workerThreads.
  cat > /tmp/recompute_${AREA_LABEL}.xml <<XML
<task xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
      xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3" oid="$TASK_OID">
  <name>recompute-affil-${AREA_LABEL}-cris</name>
  <ownerRef oid="00000000-0000-0000-0000-000000000002" type="UserType"/>
  <executionState>runnable</executionState>
  <activity>
    <work><recomputation><objects><type>UserType</type><query><q:filter>
      <q:org><q:orgRef oid="$AREA_SUBTREE_OID"/><q:scope>SUBTREE</q:scope></q:org>
    </q:filter></query></objects></recomputation></work>
    <distribution><workerThreads>$WORKERS</workerThreads></distribution>
  </activity>
</task>
XML
  curl -s -u "$A_USER:$A_PASS" -X PUT "$BASE/tasks/$TASK_OID?options=overwrite" \
    -H 'Content-Type: application/xml' --data-binary @/tmp/recompute_${AREA_LABEL}.xml -o /tmp/affil_resp.txt -w 'import HTTP=%{http_code}\n'
  echo "Task lanzada. Monitorear: GET /tasks/$TASK_OID  (executionState/progress)."
  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# MODO CRIS — Fase 2: asignar AR-CRIS-Person (+ opcional BR-Investigador) por foco.
# Recompute implícito: la asignación dispara el clockwork → construction CRIS escribe.
# NO usa ?options=reconcile → no fetch de Koha/Entra/LDAP. Multihilo opcional vía xargs.
# ─────────────────────────────────────────────────────────────────────────────
[ -z "$OIDS" ] && { echo "CRIS: falta oids_file"; exit 1; }
total=$(grep -c . "$OIDS")
echo "CRIS: $total foci | AR-CRIS-Person=$AR_CRIS_PERSON_OID | assign-br=$ASSIGN_BR | workers=$WORKERS"

# Construye el itemDelta: siempre AR-CRIS-Person; opcionalmente también BR-Investigador.
build_delta () {
  local d="{\"modificationType\":\"add\",\"path\":\"assignment\",\"value\":{\"targetRef\":{\"oid\":\"$AR_CRIS_PERSON_OID\",\"type\":\"RoleType\"}}}"
  if [ "$ASSIGN_BR" = "1" ]; then
    d="$d,{\"modificationType\":\"add\",\"path\":\"assignment\",\"value\":{\"targetRef\":{\"oid\":\"$BR_PUESTO_OID\",\"type\":\"RoleType\"}}}"
  fi
  echo "{\"objectModification\":{\"itemDelta\":[$d]}}"
}
DELTA=$(build_delta)

process_one () {
  local OID="$1"
  grep -qx "$OID" "$DONE" && { echo "SKIP $OID"; return; }
  # Idempotencia de POLICY: assignmentPolicyEnforcement=relative + delta 'add' ya
  # presente => MidPoint no duplica el assignment (no-op). El upsert CRIS es por dni.
  local CODE
  CODE=$(curl -s -u "$A_USER:$A_PASS" -X PATCH "$BASE/users/$OID" \
    -H 'Content-Type: application/json' -d "$DELTA" -o "/tmp/cris_resp_$OID.txt" -w '%{http_code}')
  case "$CODE" in
    200|202|204|240) echo "$OID" >> "$DONE"; echo "OK $OID ($CODE)" ;;
    250)             echo "$OID" >> "$DONE"; echo "PARTIAL $OID (250, dato en CRIS)" ;;
    400)
      if grep -q "without any attributes" "/tmp/cris_resp_$OID.txt" 2>/dev/null; then
        echo "DIRTY $OID (foco sin dni/givenName, dato sucio Oracle)"
      else echo "FAIL $OID (400)"; fi ;;
    *) echo "FAIL $OID ($CODE)" ;;
  esac
  rm -f "/tmp/cris_resp_$OID.txt"
}
export -f process_one heap_pct disk_pct
export A_USER A_PASS BASE DELTA DONE

# ── Procesamiento en LOTES PEQUEÑOS (endurecido post-OOM) ─────────────────────
# Estructura: lote de BATCH_SIZE focos; dentro del lote, hasta WORKERS (≤2) en
# paralelo vía xargs -P. ENTRE lotes: gate (disco+heap), pausa, y restart
# programado cada RESTART_EVERY_BATCHES si el heap no cede.
mapfile -t ALL < <(grep . "$OIDS")
echo "Endurecido: WORKERS=$WORKERS BATCH_SIZE=$BATCH_SIZE pausa=${PAUSE_BETWEEN_BATCHES}s heap[soft=$HEAP_SOFT abort=$HEAP_ABORT] restart_cada=$RESTART_EVERY_BATCHES lotes"
i=0; n=0; batch_no=0
while [ $i -lt ${#ALL[@]} ]; do
  batch_no=$((batch_no+1))
  gate
  # Si el heap no bajó tras esperar GC, y toca ventana de restart programado → restart.
  if [ "$HEAP_STILL_HIGH" = "1" ]; then
    echo "  heap no cedió con GC; ejecutando restart programado preventivo (lote $batch_no)."
    restart_midpoint
  elif [ $((batch_no % RESTART_EVERY_BATCHES)) -eq 0 ]; then
    H=$(heap_pct)
    if [ "${H:-0}" -ge "$HEAP_OK" ]; then
      echo "  ventana restart (cada $RESTART_EVERY_BATCHES lotes) y heap=${H}% >=${HEAP_OK} -> restart programado."
      restart_midpoint
    fi
  fi
  LOT=("${ALL[@]:$i:$BATCH_SIZE}")
  if [ "$WORKERS" -le 1 ]; then
    for OID in "${LOT[@]}"; do process_one "$OID"; done
  else
    printf '%s\n' "${LOT[@]}" | xargs -P "$WORKERS" -I{} bash -c 'process_one "$@"' _ {}
  fi
  i=$((i+BATCH_SIZE)); n=$i
  echo "  --- lote $batch_no  ~$n/$total  heap=$(heap_pct)% disk=$(disk_pct)% ---"
  [ $i -lt ${#ALL[@]} ] && sleep "$PAUSE_BETWEEN_BATCHES"
done

ok=$(grep -c . "$DONE")
echo "DONE [CRIS $AREA_LABEL]: procesados-marcados-done=$ok / $total"
echo "VERIFICAR éxito REAL en CRIS (matches por dni=1, entity.type single, CERIF reltype 5 place 0)."
