#!/bin/bash
# FASE 3b — driver de onboarding create-only por recon scoped __UID__.
# Uso (en PROD): driver-recon-batch.sh <ADMIN_USER> <ADMIN_PASS> <CODES_FILE> <CONCURRENCY>
# - CODES_FILE: un CODIGO por linea (subconjunto create-only, SIN borrower Koha).
# - Cada codigo => task con OID UNICO (NO overwrite => sin bloat de activity-state).
# - Lanza hasta CONCURRENCY recons en paralelo; espera a que bajen; limpia tasks CLOSED/SUSPENDED.
# - Anti-storm: si detecta rafaga de 409 en logs Koha, aborta (exit 9).
# - Memoria: si mem% > 90, pausa hasta que baje.
set -u
AU="$1"; AP="$2"; CODES_FILE="$3"; CONC="${4:-5}"
RESOID="6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22"
REST="http://localhost:8080/midpoint/ws/rest"
PG="docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tA -c"
DC="docker exec midpoint_server"

mem_pct(){ docker stats --no-stream --format '{{.MemPerc}}' midpoint_server | tr -d '%' | cut -d. -f1; }
running_count(){ docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -tA -c \
  "SELECT count(*) FROM m_task WHERE nameorig LIKE 'p3b-onb-%' AND executionstate IN ('runnable','running');"; }
storm_check(){ docker logs midpoint_server --since 30s 2>&1 | grep -c '409 Conflict' ; }

launch(){
  local CODE="$1"
  # OID determinista derivado del CODIGO (12 ultimos hex de su md5) => sin colision, idempotente
  local H=$(echo -n "p3b-$CODE" | md5sum | cut -c1-12)
  local OID="d1a2b3c4-3b00-4abc-9def-${H}"
  cat > /tmp/p3b_$CODE.xml <<XML
<task xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3" xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3" xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3" xmlns:icfs="http://midpoint.evolveum.com/xml/ns/public/connector/icf-1/resource-schema-3" oid="$OID">
<name>p3b-onb-$CODE</name><executionState>runnable</executionState>
<ownerRef oid="00000000-0000-0000-0000-000000000002" type="c:UserType"/>
<cleanupAfterCompletion>PT5M</cleanupAfterCompletion>
<activity><work><reconciliation><resourceObjects>
<resourceRef oid="$RESOID" type="c:ResourceType"/><kind>account</kind><intent>default</intent>
<query><q:filter><q:equal><q:path>attributes/icfs:uid</q:path><q:value>$CODE</q:value></q:equal></q:filter></query>
</resourceObjects></reconciliation></work></activity></task>
XML
  curl -s -o /dev/null -X POST -u "$AU:$AP" -H 'Content-Type: application/xml' --data-binary @/tmp/p3b_$CODE.xml "$REST/tasks"
  rm -f /tmp/p3b_$CODE.xml
}

TOTAL=$(wc -l < "$CODES_FILE"); n=0
while IFS= read -r CODE; do
  [ -z "$CODE" ] && continue
  n=$((n+1))
  # backpressure: wait while running >= CONC
  while [ "$(running_count)" -ge "$CONC" ]; do sleep 3; done
  # memory guard
  while [ "$(mem_pct)" -ge 90 ]; do echo "MEM_HIGH pause"; sleep 15; done
  # storm guard
  S=$(storm_check); if [ "$S" -gt 20 ]; then echo "STORM_DETECTED ($S 409 in 30s) ABORT at $CODE"; exit 9; fi
  launch "$CODE"
  [ $((n % 50)) -eq 0 ] && echo "launched $n/$TOTAL (running=$(running_count) mem=$(mem_pct)%)"
done < "$CODES_FILE"

# drain
while [ "$(running_count)" -gt 0 ]; do sleep 5; done
echo "BATCH_DONE launched=$n"
