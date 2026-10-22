#!/usr/bin/env python3
"""VUELTA ATRAS de DATOS (solo si hace falta, DESPUES de revertir la configuracion con patch-8x/9x).
Lee estado-pre.tsv.gz (salida de ds.sql en backup-pre.sh) y, para los OIDs dados, genera un PATCH XML
NO raw por usuario (pasa por el clockwork, para que LDAP/Koha reciban el delta) que repone
liveAffiliationWorker/Student/Alum y administrativeStatus tal como estaban ANTES.
uso: restore-datos.py estado-pre.tsv.gz oids.txt <dir_salida>
OJO: reponer un 217 rancio vuelve a habilitar Koha a un ex-estudiante; usar solo con lista revisada."""
import gzip, os, re, sys
COLS = ['oid','name','lc','adm','eff','w','s','a','term','termS','mot','idp']
pre = {}
for l in gzip.open(sys.argv[1], 'rt'):
    f = l.rstrip('\n').split('\t')
    if re.match(r'^[0-9a-f]{8}-', f[0]): pre[f[0]] = dict(zip(COLS, f))
only = set(open(sys.argv[2]).read().split()); out = sys.argv[3]; os.makedirs(out, exist_ok=True); n = 0
H = ('<objectModification xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3" '
     'xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3" '
     'xmlns:t="http://prism.evolveum.com/xml/ns/public/types-3" xmlns:sciback="urn:sciback:midpoint:person">')
for oid in only:
    u = pre.get(oid)
    if not u: continue
    d = ''
    for k, item in (('w','liveAffiliationWorker'),('s','liveAffiliationStudent'),('a','liveAffiliationAlum')):
        v = u[k]
        d += ('<itemDelta><t:modificationType>replace</t:modificationType><t:path>c:extension/sciback:%s</t:path>%s</itemDelta>'
              % (item, '<t:value>%s</t:value>' % v if v else ''))
    adm = u['adm'].lower()
    d += ('<itemDelta><t:modificationType>replace</t:modificationType><t:path>c:activation/c:administrativeStatus</t:path>%s</itemDelta>'
          % ('<t:value>%s</t:value>' % adm if adm else ''))
    open(os.path.join(out, oid + '.xml'), 'w').write(H + d + '</objectModification>'); n += 1
print('patches:', n)
