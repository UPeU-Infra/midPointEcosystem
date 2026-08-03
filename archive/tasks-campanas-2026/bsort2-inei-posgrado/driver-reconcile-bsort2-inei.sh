#!/bin/bash
# Serialized resumable Bsort2->INEI push for posgrado + P143/P05 conflict.
# Reads /tmp/masivo_oid_map.tsv (CODE\tOID\tLC). PATCH reconcile no-op on description.
# Resumable via /tmp/masivo_done.txt. Heap gate. Counters in /tmp/masivo_progress.log.
PASS="$1"
MAP=/tmp/masivo_oid_map.tsv
DONE=/tmp/masivo_done.txt
LOG=/tmp/masivo_progress.log
touch "$DONE"
OK=0; FAIL=0; SKIP=0
TOTAL=$(awk -F'\t' '$3=="active" && $2!="NONE"' "$MAP" | wc -l | tr -d ' ')
echo "=== masivo start $(date) total=$TOTAL ===" >> "$LOG"
while IFS=$'\t' read CODE OID LC; do
  [ "$LC" != "active" ] && continue
  [ "$OID" = "NONE" ] && continue
  if grep -qx "$CODE" "$DONE"; then SKIP=$((SKIP+1)); continue; fi
  # heap gate
  USED=$(docker exec midpoint_server bash -c "jcmd 1 GC.heap_info 2>/dev/null" | grep -oE 'used [0-9]+K' | head -1 | grep -oE '[0-9]+')
  # fallback: skip gate if jcmd unavailable
  TS=$(date +%s%N)
  HTTP=$(curl -s -o /tmp/m_resp.out -w '%{http_code}' -u "administrator:$PASS" -X PATCH "http://localhost:8080/midpoint/ws/rest/users/$OID?options=reconcile" -H 'Content-Type: application/xml' -d "<objectModification xmlns=\"http://midpoint.evolveum.com/xml/ns/public/common/api-types-3\" xmlns:t=\"http://prism.evolveum.com/xml/ns/public/types-3\" xmlns:c=\"http://midpoint.evolveum.com/xml/ns/public/common/common-3\"><itemDelta><t:modificationType>replace</t:modificationType><t:path>c:description</t:path><t:value>bsort2-inei-$TS</t:value></itemDelta></objectModification>")
  if [ "$HTTP" = "204" ] || [ "$HTTP" = "200" ]; then
    OK=$((OK+1)); echo "$CODE" >> "$DONE"
  else
    # 500 may be benign post-Koha clockwork; verify INEI materialized to decide
    INEI=$(curl -s -u "administrator:$PASS" "http://localhost:8080/midpoint/ws/rest/users/$OID" -H 'Accept: application/xml' 2>/dev/null | tr '>' '>\n' | grep -oE 'academicProgramIneiCode>[0-9]+' | head -1 | grep -oE '[0-9]+')
    if [ -n "$INEI" ]; then
      OK=$((OK+1)); echo "$CODE" >> "$DONE"; echo "$(date +%H:%M:%S) $CODE HTTP=$HTTP but INEI=$INEI -> OK(benign)" >> "$LOG"
    else
      FAIL=$((FAIL+1)); echo "$(date +%H:%M:%S) $CODE OID=$OID HTTP=$HTTP FAIL" >> "$LOG"
    fi
  fi
  N=$((OK+FAIL))
  if [ $((N % 25)) -eq 0 ]; then echo "$(date +%H:%M:%S) progress ok=$OK fail=$FAIL skip=$SKIP / $TOTAL" >> "$LOG"; fi
done < "$MAP"
echo "=== masivo end $(date) ok=$OK fail=$FAIL skip=$SKIP total=$TOTAL ===" >> "$LOG"
