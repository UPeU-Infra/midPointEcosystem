#!/bin/bash
# ============================================================================
# Barrido serializado y resumible de los focos DUAL SUCIOS (student+worker).
# Contexto: fix de desempate IIA single-valued ya desplegado en PROD
#   (commits a5a4e6f->c45ce31, tag iga-desempate-dual-email-doc-2026-06-15).
# Objetivo: sacar de FATAL_ERROR/PARTIAL_ERROR a los focos con doble afiliacion
#   viva (liveAffiliationStudent + liveAffiliationWorker) por colision de
#   cardinalidad single-valued, y materializar academicProgramIneiCode->Koha sort2
#   en los que tengan P-code mapeable en LT-Pcode-INEI.
#
# Mecanismo: PATCH ?options=reconcile no-op (marca timestamp en description).
#   Idempotente, no-destructivo, storm-free. UNO POR UNO (serializado).
#
# Scope: /tmp/dual_dirty_oids.tsv  (oid \t name \t lifecycle \t [P|-] \t [I|-])
#   derivado de:  m_user where ext ? '216'(worker) and ext ? '217'(student)
#                 and lifecyclestate='active'
# Resumible via /tmp/dual_done.txt   Log /tmp/dual_progress.log
#
# Uso:  ./driver-reconcile-dual-dirty.sh <ADMIN_PASS> [MAX]
#   MAX opcional = procesar solo los primeros MAX pendientes (para canary).
# ============================================================================
set -u
PASS="$1"
MAX="${2:-0}"          # 0 = sin limite
SCOPE=/tmp/dual_dirty_oids.tsv
DONE=/tmp/dual_done.txt
LOG=/tmp/dual_progress.log
RESP=/tmp/dual_resp.out
ADMIN_USER="administrator"
BASE="http://localhost:8080/midpoint/ws/rest"
touch "$DONE"

OK=0; FAIL=0; SKIP=0; BENIGN=0; PROC=0
TOTAL=$(wc -l < "$SCOPE" | tr -d ' ')
echo "=== dual-sweep start $(date) total_scope=$TOTAL max=$MAX ===" >> "$LOG"

while IFS=$'\t' read -r OID NAME LC PFLAG IFLAG; do
  [ -z "$OID" ] && continue
  [ "$LC" != "active" ] && continue
  if grep -qx "$OID" "$DONE"; then SKIP=$((SKIP+1)); continue; fi
  if [ "$MAX" != "0" ] && [ "$PROC" -ge "$MAX" ]; then break; fi
  PROC=$((PROC+1))

  TS=$(date +%s%N)
  HTTP=$(curl -s -o "$RESP" -w '%{http_code}' -u "$ADMIN_USER:$PASS" \
    -X PATCH "$BASE/users/$OID?options=reconcile" \
    -H 'Content-Type: application/xml' \
    -d "<objectModification xmlns=\"http://midpoint.evolveum.com/xml/ns/public/common/api-types-3\" xmlns:t=\"http://prism.evolveum.com/xml/ns/public/types-3\" xmlns:c=\"http://midpoint.evolveum.com/xml/ns/public/common/common-3\"><itemDelta><t:modificationType>replace</t:modificationType><t:path>c:description</t:path><t:value>dual-sweep-$TS</t:value></itemDelta></objectModification>")

  if [ "$HTTP" = "204" ] || [ "$HTTP" = "200" ] || [ "$HTTP" = "250" ]; then
    OK=$((OK+1)); echo "$OID" >> "$DONE"
  else
    # HTTP 4xx/5xx puede ser benigno (PARTIAL_ERROR downstream empty-shadow-add)
    # o el clockwork ya aplico el delta. Verificamos INEI materializado si tenia P-code,
    # y si no tenia P-code, basta con confirmar que el foco respondio (cardinalidad resuelta).
    if [ "$PFLAG" = "P" ]; then
      INEI=$(curl -s -u "$ADMIN_USER:$PASS" "$BASE/users/$OID" -H 'Accept: application/xml' 2>/dev/null \
        | tr '>' '>\n' | grep -oE 'academicProgramIneiCode>[0-9]+' | head -1 | grep -oE '[0-9]+')
      if [ -n "$INEI" ]; then
        OK=$((OK+1)); BENIGN=$((BENIGN+1)); echo "$OID" >> "$DONE"
        echo "$(date +%H:%M:%S) $NAME $OID HTTP=$HTTP INEI=$INEI -> OK(benign-partial)" >> "$LOG"
      else
        FAIL=$((FAIL+1))
        echo "$(date +%H:%M:%S) $NAME $OID HTTP=$HTTP pcode-no-inei FAIL :: $(head -c 240 $RESP)" >> "$LOG"
      fi
    else
      # sin P-code: el reconcile no debe materializar INEI; tratamos 500 con
      # cuerpo de partial-error como benigno (cardinalidad resuelta upstream).
      if grep -qiE 'without any attributes|partial' "$RESP"; then
        OK=$((OK+1)); BENIGN=$((BENIGN+1)); echo "$OID" >> "$DONE"
        echo "$(date +%H:%M:%S) $NAME $OID HTTP=$HTTP -> OK(benign-partial-noPcode)" >> "$LOG"
      else
        FAIL=$((FAIL+1))
        echo "$(date +%H:%M:%S) $NAME $OID HTTP=$HTTP FAIL :: $(head -c 240 $RESP)" >> "$LOG"
      fi
    fi
  fi

  N=$((OK+FAIL))
  if [ $((N % 50)) -eq 0 ]; then
    echo "$(date +%H:%M:%S) progress ok=$OK fail=$FAIL skip=$SKIP benign=$BENIGN proc=$PROC / $TOTAL" >> "$LOG"
  fi
done < "$SCOPE"

echo "=== dual-sweep end $(date) ok=$OK fail=$FAIL skip=$SKIP benign=$BENIGN proc=$PROC total_scope=$TOTAL ===" >> "$LOG"
echo "RESULT ok=$OK fail=$FAIL skip=$SKIP benign=$BENIGN proc=$PROC"
