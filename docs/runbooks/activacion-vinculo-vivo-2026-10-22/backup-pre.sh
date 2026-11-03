#!/bin/bash
# Respaldo previo. Se ejecuta EN .166 desde ~/midPointEcosystem/docs/runbooks/activacion-vinculo-vivo-2026-10-22/
# Solo lecturas (GET raw + SELECT read-only). Credencial por stdin, una línea usuario:clave (ver README): nunca en argv.
set -euo pipefail
IFS= read -r A || true; [ -n "$A" ] || { echo "falta la credencial por stdin"; exit 1; }
A=${A//\\/\\\\}; A=${A//\"/\\\"}
cred() { printf 'user = "%s"\n' "$A"; }
B=~/backups/activacion-vinculo-vivo-$(date -u +%Y%m%dT%H%MZ); mkdir -p "$B"; echo "$B"
REST=http://localhost:8080/midpoint/ws/rest
curl -sf -K <(cred) -H 'Accept: application/xml' "$REST/objectTemplates/855caaca-68c4-4f7f-8ff8-b4e35dd7d390?options=raw" > "$B/template-pre.xml"
for r in 21 22 23; do curl -sf -K <(cred) -H 'Accept: application/xml' "$REST/resources/6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e$r?options=raw" > "$B/resource-e$r-pre.xml"; done
grep -o 'version="[0-9]*"' "$B/template-pre.xml" | head -1
for r in 21 22 23; do echo "e$r $(grep -o '<resource [^>]*version="[0-9]*"' "$B/resource-e$r-pre.xml" | grep -o 'version="[0-9]*"') xsd:element=$(grep -c '<xsd:element' "$B/resource-e$r-pre.xml")"; done
docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' midpoint-midpoint_data-1 psql -U midpoint -d midpoint -X -q < ds.sql | gzip > "$B/estado-pre.tsv.gz"
echo "usuarios: $(zcat "$B/estado-pre.tsv.gz" | grep -cE '^[0-9a-f]{8}-')"
sha256sum "$B"/* > "$B/SHA256SUMS"; cat "$B/SHA256SUMS"
