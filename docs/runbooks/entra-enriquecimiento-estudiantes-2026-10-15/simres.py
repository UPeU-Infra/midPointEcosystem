#!/usr/bin/env python3
"""Lee un simulation result (m_simulation_result_processed_object) y resume los deltas.
uso: simres.py <sim_result_oid> [--raw]  (ejecuta psql en PROD via psql.sh)"""
import sys, json, subprocess, os, collections
here = os.path.dirname(os.path.abspath(__file__))
oid = sys.argv[1]
q = ("SELECT objecttype||'|'||coalesce(nameorig,'')||'|'||coalesce(state::text,'')||'|'||coalesce(oid::text,'')||'|'||"
     "coalesce(focusrecordid::text,'')||'|'||cid||'|'||encode(fullobject,'base64') FROM m_simulation_result_processed_object WHERE owneroid='%s' ORDER BY cid;" % oid)
out = subprocess.run([os.path.join(here, 'psql.sh'), '-t'], input=q, capture_output=True, text=True).stdout
import base64
rows = []
buf = ''
for line in out.splitlines():
    buf += line.strip()
for chunk in out.split('\n'):
    pass
# las filas base64 vienen partidas en varias lineas por psql: reagrupar por prefijo de tipo
recs = []
cur = None
for line in out.splitlines():
    if not line.strip():
        continue
    if line.split('|')[0] in ('USER', 'SHADOW', 'ORG', 'ROLE') and line.count('|') >= 6:
        if cur: recs.append(cur)
        cur = line.strip()
    else:
        cur += line.strip()
if cur: recs.append(cur)
res = []
for r in recs:
    t, name, state, ooid, focus, cid, b64 = r.split('|', 6)
    try:
        fo = json.loads(base64.b64decode(b64).decode('utf-8'))
    except Exception as e:
        fo = {'_err': str(e)}
    res.append(dict(type=t, name=name, state=state, oid=ooid, focus=focus, cid=cid, obj=fo))
json.dump(res, open(os.path.join(here, 'sim_%s.json' % oid), 'w'), ensure_ascii=False, indent=1)
print('procesados:', len(res), collections.Counter((x['type'], x['state']) for x in res))
