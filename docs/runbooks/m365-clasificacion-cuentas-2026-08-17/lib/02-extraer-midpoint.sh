#!/usr/bin/env bash
# Extrae de MidPoint PROD los focos de identidad y el catálogo de unidades.
# SOLO LECTURA (SELECT). Salida: $M365_WORK/mp_full.csv y mp_orgs.csv
set -euo pipefail
: "${M365_WORK:?define M365_WORK}"
source ~/.secrets/midpoint-upeu.env
export SSHPASS="$MIDPOINT_PROD_PASS"

PSQL='docker exec midpoint-midpoint_data-1 psql -U midpoint midpoint'
ssh_mp() { sshpass -e ssh -o StrictHostKeyChecking=no -o ConnectTimeout=25 midpoint-prod "$@"; }

echo "→ focos de identidad (archetype, afiliación, campus, unidad)…"
ssh_mp "$PSQL -c \"COPY (
SELECT u.nameorig,
 replace(coalesce(u.ext->>'72',''),'urn:schac:personalUniqueID:pe:DNI:PE:','') AS dni,
 coalesce(u.ext->>'74','')  AS codigo,
 coalesce(u.givennameorig,'')  AS given,
 coalesce(u.familynameorig,'') AS family,
 lower(coalesce(u.emailaddress,'')) AS email,
 coalesce(u.ext->>'78','')  AS aff,
 coalesce(u.ext->>'219', u.ext->>'220','') AS campus,
 u.lifecyclestate,
 coalesce((SELECT string_agg(DISTINCT a.nameorig,';')
           FROM m_ref_archetype ra JOIN m_archetype a ON a.oid=ra.targetOid
           WHERE ra.ownerOid=u.oid AND a.nameorig LIKE 'archetype-%'),'') AS archetype,
 coalesce((SELECT string_agg(DISTINCT o.nameorig,';')
           FROM m_ref_object_parent_org po JOIN m_org o ON o.oid=po.targetOid
           WHERE po.ownerOid=u.oid),'') AS orgs,
 coalesce((SELECT string_agg(DISTINCT coalesce(o.displaynameorig,o.nameorig),';')
           FROM m_ref_object_parent_org po JOIN m_org o ON o.oid=po.targetOid
           WHERE po.ownerOid=u.oid),'') AS orgs_nombre
FROM m_user u) TO STDOUT WITH CSV HEADER\"" > "$M365_WORK/mp_full.csv"

echo "→ catálogo de unidades organizativas…"
ssh_mp "$PSQL -c \"COPY (SELECT nameorig, coalesce(displaynameorig,'') AS display,
 coalesce(lifecyclestate,'') AS lc FROM m_org ORDER BY nameorig) TO STDOUT WITH CSV HEADER\"" > "$M365_WORK/mp_orgs.csv"

python3 - "$M365_WORK" <<'EOF'
import csv,sys
w=sys.argv[1]
u=list(csv.DictReader(open(f"{w}/mp_full.csv",newline='',encoding='utf-8')))
o=list(csv.DictReader(open(f"{w}/mp_orgs.csv",newline='',encoding='utf-8')))
print(f"   focos: {len(u)} | con email: {sum(1 for x in u if x['email'])} | con archetype: {sum(1 for x in u if x['archetype'])}")
print(f"   orgs: {len(o)} | AREA-*: {sum(1 for x in o if x['nameorig'].startswith('AREA-'))} | con displayName: {sum(1 for x in o if x['display'])}")
assert len(u)>1000 and len(o)>50, "extracción sospechosamente corta"
EOF
