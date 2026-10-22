#!/bin/bash
# Respaldo previo (se ejecuta EN .166, en ~/backups/j3b-20261021/). Solo lecturas.
set -euo pipefail
: "${MIDPOINT_ADMIN_USER:?}" "${MIDPOINT_ADMIN_PASS:?}"   # se pasan por entorno desde el Mac (ver plan)
B=~/backups/j3b-20261021; mkdir -p $B
curl -s -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" -H 'Accept: application/xml' \
  'http://localhost:8080/midpoint/ws/rest/objectTemplates/855caaca-68c4-4f7f-8ff8-b4e35dd7d390?options=raw' > $B/template-pre.xml
grep -o 'version="[0-9]*"' $B/template-pre.xml | head -1
docker exec -e PGOPTIONS='-c default_transaction_read_only=on' midpoint-midpoint_data-1 psql -U midpoint -d midpoint -X -A -t -c \
  "copy (select u.oid, u.nameorig, u.ext->'100', convert_from(u.fullobject,'UTF8')::jsonb->'user'->'extension'->'affiliations' from m_user u where u.ext ? '100') to stdout" \
  | gzip > $B/affiliations-pre.tsv.gz
zcat $B/affiliations-pre.tsv.gz | wc -l
sha256sum $B/* > $B/SHA256SUMS
