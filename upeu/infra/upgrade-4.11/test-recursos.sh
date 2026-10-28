#!/usr/bin/env bash
#
# test-recursos.sh
# ------------------------------------------------------------------------------
# Test connection de TODOS los recursos (POST /resources/<oid>/test) y resumen:
# un recurso por linea con su estado global y las operaciones que no son success.
# El test de conexion solo lee (conexion, esquema, capacidades): no escribe en el
# sistema destino. Criterio de exito de la subida: 12/12 success.
#
# USO (en el HOST):  ./test-recursos.sh            -> exit 0 si todos success
# ENTORNO: MP_BASE (http://localhost:8080/midpoint), MP_REST_USER (administrator),
#          MP_REST_PASS (se pide si falta), PG_CONTAINER (midpoint-midpoint_data-1)
# ------------------------------------------------------------------------------
set -euo pipefail
MP_BASE="${MP_BASE:-http://localhost:8080/midpoint}"
MP_REST_USER="${MP_REST_USER:-administrator}"
PG_CONTAINER="${PG_CONTAINER:-midpoint-midpoint_data-1}"
[[ -n "${MP_REST_PASS:-}" ]] || { read -r -s -p "Contrasena REST de $MP_REST_USER: " MP_REST_PASS; echo; }
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

docker exec -e PGOPTIONS='-c default_transaction_read_only=on' "$PG_CONTAINER" \
    psql -U midpoint -d midpoint -tA -F'|' -c "SELECT oid, nameorig FROM m_resource ORDER BY nameorig;" > "$T/res"
total=0; okc=0
while IFS='|' read -r oid name; do
    [[ -z "$oid" ]] && continue
    total=$((total+1)); t0=$(date +%s)
    code=$(curl -sS -m 600 -o "$T/body" -w '%{http_code}' -u "$MP_REST_USER:$MP_REST_PASS" -X POST \
        -H 'Accept: application/xml' "$MP_BASE/ws/rest/resources/$oid/test" < /dev/null || echo 000)
    res=$(python3 - "$T/body" <<'PY'
import re, sys
x = open(sys.argv[1], encoding='utf-8', errors='replace').read()
top = re.search(r'<(?:\w+:)?status>([^<]+)</', x)
bad = sorted({f'{op}={st}' for op, st in re.findall(r'<(?:\w+:)?operation>([^<]+)</(?:\w+:)?operation>\s*<(?:\w+:)?status>([^<]+)</', x) if st != 'success'})
print((top.group(1) if top else 'desconocido') + '|' + '; '.join(bad))
PY
)
    st="${res%%|*}"; [[ "$st" == "success" && "$code" =~ ^2 ]] && okc=$((okc+1))
    printf '%-38s %-14s HTTP %s  %3ss  %s\n' "${name:0:38}" "$st" "$code" "$(( $(date +%s) - t0 ))" "${res#*|}"
done < "$T/res"
echo "RESULTADO: $okc/$total success"
[[ "$okc" -eq "$total" ]]
