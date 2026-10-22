#!/usr/bin/env python3
"""VUELTA ATRAS de datos (solo si hace falta, DESPUES de revertir el template con patch-99).
Lee affiliations-pre.tsv.gz y genera un PATCH XML por usuario (NO raw: pasa por el clockwork para que el
outbound LDAP reciba el delta) que AÑADE los valores que el usuario tenia y ya no tiene.
uso: gen_restore.py affiliations-pre.tsv.gz estado-actual.tsv <dir_salida> [oids.txt]
estado-actual.tsv = copy (select oid, ext->'100' from m_user where ext ? '100') to stdout"""
import gzip, json, os, sys
pre = {}
for l in gzip.open(sys.argv[1], 'rt'):
    f = l.rstrip('\n').split('\t'); pre[f[0]] = set(json.loads(f[2]))
now = {}
for l in open(sys.argv[2]):
    f = l.rstrip('\n').split('\t'); now[f[0]] = set(json.loads(f[1])) if f[1] else set()
only = set(open(sys.argv[4]).read().split()) if len(sys.argv) > 4 else None
os.makedirs(sys.argv[3], exist_ok=True); n = 0
for oid, vals in pre.items():
    if only and oid not in only: continue
    miss = sorted(vals - now.get(oid, set()))
    if not miss: continue
    vals = ''.join('<t:value>%s</t:value>' % v for v in miss)
    xml = ('<objectModification xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3" '
           'xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3" '
           'xmlns:t="http://prism.evolveum.com/xml/ns/public/types-3" xmlns:sciback="urn:sciback:midpoint:person">'
           '<itemDelta><t:modificationType>add</t:modificationType>'
           '<t:path>c:extension/sciback:affiliations</t:path>%s</itemDelta></objectModification>') % vals
    open(os.path.join(sys.argv[3], oid + '.xml'), 'w').write(xml); n += 1
print('patches:', n)
