#!/bin/bash
# EN .166. uso: printf '%s:%s\n' "$USUARIO" "$CLAVE" | rest.sh <objectTemplates|resources> <oid> <fichero.xml|.json>
# La credencial entra por stdin (una línea usuario:clave) y curl la lee con -K: nunca aparece en argv (`ps`).
# Hace PATCH (NUNCA PUT) y muestra version antes/despues. Un 204 NO prueba nada: si la version no sube, fue NO-OP.
set -euo pipefail
T=$1; O=$2; F=$3; REST=http://localhost:8080/midpoint/ws/rest
IFS= read -r A || true; [ -n "$A" ] || { echo "falta la credencial por stdin"; exit 1; }
A=${A//\\/\\\\}; A=${A//\"/\\\"}
cred() { printf 'user = "%s"\n' "$A"; }
case "$F" in *.json) CT=application/json;; *.xml) CT=application/xml;; *) echo "extension?"; exit 1;; esac
ver() { curl -sf -K <(cred) -H 'Accept: application/xml' "$REST/$T/$O?options=raw" | grep -o 'version="[0-9]*"' | head -1; }
echo "antes:   $(ver)"
code=$(curl -s -o /tmp/rest-out.$$ -w '%{http_code}' -K <(cred) -X PATCH -H "Content-Type: $CT" --data-binary @"$F" "$REST/$T/$O")
echo "HTTP $code"; head -c 600 /tmp/rest-out.$$; rm -f /tmp/rest-out.$$; echo
echo "despues: $(ver)"
