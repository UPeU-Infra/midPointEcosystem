#!/bin/bash
# EN .166. uso: rest.sh <objectTemplates|resources> <oid> <fichero.xml|.json>
# Hace PATCH (NUNCA PUT) y muestra version antes/despues. Un 204 NO prueba nada: si la version no sube, fue NO-OP.
set -euo pipefail
: "${MIDPOINT_ADMIN_USER:?}" "${MIDPOINT_ADMIN_PASS:?}"
T=$1; O=$2; F=$3; REST=http://localhost:8080/midpoint/ws/rest; A="$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS"
case "$F" in *.json) CT=application/json;; *.xml) CT=application/xml;; *) echo "extension?"; exit 1;; esac
ver() { curl -sf -u "$A" -H 'Accept: application/xml' "$REST/$T/$O?options=raw" | grep -o 'version="[0-9]*"' | head -1; }
echo "antes:   $(ver)"
code=$(curl -s -o /tmp/rest-out.$$ -w '%{http_code}' -u "$A" -X PATCH -H "Content-Type: $CT" --data-binary @"$F" "$REST/$T/$O")
echo "HTTP $code"; head -c 600 /tmp/rest-out.$$; rm -f /tmp/rest-out.$$; echo
echo "despues: $(ver)"
