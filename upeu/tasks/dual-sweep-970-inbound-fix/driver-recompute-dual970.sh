#!/bin/bash
# ============================================================================
# Barrido serializado y resumible de los 970 focos DUAL (shadow en ambos
# resources Oracle: Trabajadores v3 + Estudiantes v3), tras el fix del
# inbound num-documento-to-lambDocNum del resource Trabajadores
#   (tag fix-trabajadores-inbound-newline-2026-06-17).
#
# Contexto: el inbound colapsaba newlines y abortaba el recompute (compile
#   error en el script de mapping) de los focos que pasaban por el resource
#   Trabajadores. Reimport del XML limpio -> inbound sano. Este barrido saca
#   de FATAL_ERROR/PARTIAL_ERROR a los 970 focos dual.
#
# Mecanismo: PATCH ?options=reconcile no-op (timestamp en description).
#   Fuerza el clockwork completo (PROJECTOR pasa por el inbound ya sano).
#   Idempotente, no-destructivo, storm-free. UNO POR UNO (serializado).
#
# Scope: /tmp/dual970_oids.tsv  (oid \t name \t lifecycle \t [V|-]livedual)
# Resumible via /tmp/dual970_done.txt   Log /tmp/dual970_progress.log
#
# Gates anti-storm:
#   - Heap JVM: si used/max > HEAP_MAX_PCT -> pausa hasta que baje (o aborta).
#   - Monitoreo cada 50 focos.
#
# Clasificacion de respuesta:
#   200/204/250        -> OK (clockwork aplico delta)
#   5xx con cuerpo 'without any attributes'/'partial' -> OK benigno
#                         (residual empty-shadow-add, no crea cuentas)
#   timeout/Koha read-timeout/connect (cuerpo con 'koha'/'timed out'/'Read timed') ->
#                         RUIDO transitorio Koha (bot-flood .135), reintentable
#   resto 4xx/5xx      -> FAIL genuino
#
# Uso:  ./driver-recompute-dual970.sh <ADMIN_PASS> [MAX]
#   MAX opcional = procesar solo los primeros MAX pendientes (canary).
# ============================================================================
set -u
PASS="$1"
MAX="${2:-0}"
SCOPE=/tmp/dual970_oids.tsv
DONE=/tmp/dual970_done.txt
LOG=/tmp/dual970_progress.log
RESP=/tmp/dual970_resp.out
ADMIN_USER="administrator"
BASE="http://localhost:8080/midpoint/ws/rest"
HEAP_MAX_PCT=85         # pausa si heap usado supera este %
touch "$DONE"

heap_pct() {
  # % de memoria del contenedor (cgroup limit 10GiB) via docker stats.
  # Es el indicador real de proximidad a OOM (no hay jcmd: es JRE).
  local p
  p=$(docker stats midpoint_server --no-stream --format '{{.MemPerc}}' 2>/dev/null | tr -d ' %' | cut -d. -f1)
  [ -z "$p" ] && p=0
  echo "$p"
}

OK=0; FAIL=0; SKIP=0; BENIGN=0; KNOISE=0; PROC=0
TOTAL=$(wc -l < "$SCOPE" | tr -d ' ')
echo "=== dual970-sweep start $(date) total_scope=$TOTAL max=$MAX ===" >> "$LOG"

while IFS=$'\t' read -r OID NAME LC LD; do
  [ -z "$OID" ] && continue
  [ "$LC" != "active" ] && continue
  if grep -qx "$OID" "$DONE"; then SKIP=$((SKIP+1)); continue; fi
  if [ "$MAX" != "0" ] && [ "$PROC" -ge "$MAX" ]; then break; fi

  # Gate heap antes de cada PATCH
  HP=$(heap_pct)
  if [ "$HP" -ge "$HEAP_MAX_PCT" ]; then
    echo "$(date +%H:%M:%S) HEAP GATE heap=${HP}% >= ${HEAP_MAX_PCT}% pausa 30s" >> "$LOG"
    sleep 30
    HP=$(heap_pct)
    if [ "$HP" -ge 95 ]; then
      echo "$(date +%H:%M:%S) HEAP CRITICO ${HP}% ABORT proc=$PROC ok=$OK fail=$FAIL" >> "$LOG"
      echo "ABORT heap=${HP}%"; exit 2
    fi
  fi

  PROC=$((PROC+1))
  TS=$(date +%s%N)
  HTTP=$(curl -s -o "$RESP" -w '%{http_code}' --max-time 120 -u "$ADMIN_USER:$PASS" \
    -X PATCH "$BASE/users/$OID?options=reconcile" \
    -H 'Content-Type: application/xml' \
    -d "<objectModification xmlns=\"http://midpoint.evolveum.com/xml/ns/public/common/api-types-3\" xmlns:t=\"http://prism.evolveum.com/xml/ns/public/types-3\" xmlns:c=\"http://midpoint.evolveum.com/xml/ns/public/common/common-3\"><itemDelta><t:modificationType>replace</t:modificationType><t:path>c:description</t:path><t:value>dual970-sweep-$TS</t:value></itemDelta></objectModification>")

  MARKER="dual970-sweep-$TS"
  if [ "$HTTP" = "204" ] || [ "$HTTP" = "200" ] || [ "$HTTP" = "250" ]; then
    OK=$((OK+1)); echo "$OID" >> "$DONE"
  elif grep -qiE 'koha|read timed|connect timed|connection reset|sockettimeout' "$RESP"; then
    # Ruido transitorio Koha (bot-flood .135) en la PROYECCION downstream.
    # Verificar si el delta de la fase principal se commiteo igual (description).
    APPLIED=$(docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tAc \
      "select 1 from m_user where oid='$OID' and convert_from(fullobject,'UTF8') like '%$MARKER%'" 2>/dev/null | tr -d ' ')
    if [ "$APPLIED" = "1" ]; then
      OK=$((OK+1)); BENIGN=$((BENIGN+1)); echo "$OID" >> "$DONE"
      echo "$(date +%H:%M:%S) $NAME $OID HTTP=$HTTP -> OK(koha-noise,delta-commited)" >> "$LOG"
    else
      KNOISE=$((KNOISE+1))
      echo "$(date +%H:%M:%S) $NAME $OID HTTP=$HTTP -> KOHA-NOISE(retry,no-commit) :: $(head -c 160 $RESP | tr '\n' ' ')" >> "$LOG"
    fi
  else
    # 5xx (StackOverflowError de serializacion Wicket, partial-error, etc.):
    # el clockwork puede haber commiteado igual. Verificar marker en description.
    APPLIED=$(docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tAc \
      "select 1 from m_user where oid='$OID' and convert_from(fullobject,'UTF8') like '%$MARKER%'" 2>/dev/null | tr -d ' ')
    if [ "$APPLIED" = "1" ]; then
      OK=$((OK+1)); BENIGN=$((BENIGN+1)); echo "$OID" >> "$DONE"
      echo "$(date +%H:%M:%S) $NAME $OID HTTP=$HTTP -> OK(benign,delta-commited; serialization/partial noise)" >> "$LOG"
    else
      FAIL=$((FAIL+1))
      echo "$(date +%H:%M:%S) $NAME $OID HTTP=$HTTP FAIL(no-commit) :: $(grep -oE '<message>[^<]*' $RESP | head -1) :: $(head -c 160 $RESP | tr '\n' ' ')" >> "$LOG"
    fi
  fi

  N=$((OK+FAIL+KNOISE))
  if [ $((N % 50)) -eq 0 ]; then
    HP=$(heap_pct)
    echo "$(date +%H:%M:%S) progress ok=$OK fail=$FAIL knoise=$KNOISE skip=$SKIP benign=$BENIGN proc=$PROC/$TOTAL heap=${HP}%" >> "$LOG"
  fi
done < "$SCOPE"

echo "=== dual970-sweep end $(date) ok=$OK fail=$FAIL knoise=$KNOISE skip=$SKIP benign=$BENIGN proc=$PROC total_scope=$TOTAL ===" >> "$LOG"
echo "RESULT ok=$OK fail=$FAIL knoise=$KNOISE skip=$SKIP benign=$BENIGN proc=$PROC"
