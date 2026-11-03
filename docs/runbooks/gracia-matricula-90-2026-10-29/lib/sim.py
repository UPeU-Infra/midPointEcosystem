#!/usr/bin/env python3
"""Lanza sim-inyectada.groovy en PROD via POST rpc/executeScript (SIN persistencia).
uso: sim.py --rows <tsv oid,F,EFF,add217> --out <fichero> [--tpl p.xml ...] [--res p.xml ...] [--schema p.xml]
            [--dev] [--no-reconcile] [--names lastReviewedAt,schacExpiryDate] [--chunk 12]
La credencial va por stdin del ssh (mpcurl.sh de fusion-hulda: nunca en argv)."""
import argparse, base64, html, os, re, subprocess, sys, time
ap = argparse.ArgumentParser()
ap.add_argument('--rows', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--tpl', nargs='*', default=[]); ap.add_argument('--res', nargs='*', default=[])
ap.add_argument('--schema'); ap.add_argument('--dev', action='store_true'); ap.add_argument('--no-reconcile', action='store_true')
ap.add_argument('--names', default='lastReviewedAt,schacExpiryDate'); ap.add_argument('--chunk', type=int, default=12)
ap.add_argument('--mpcurl', default=os.environ.get('MPCURL', '/Users/alberto/proyectos/productos/iga/canonico/.worktrees/fusion-hulda/docs/runbooks/fusion-hulda-2026-10-28/lib/mpcurl.sh'))
a = ap.parse_args()
here = os.path.dirname(os.path.abspath(__file__))
g = open(os.path.join(here, 'sim-inyectada.groovy')).read()
def b64(s):
    e = base64.b64encode(s.encode()).decode()
    parts = ', '.join("'%s'" % e[i:i + 60000] for i in range(0, len(e), 60000))  # literal Groovy <= 64K
    return "new String(java.util.Base64.decoder.decode([%s].join('')), 'UTF-8')" % parts
lst = lambda files: '[' + ', '.join(b64(open(f).read()) for f in files) + ']'
rows = [l.rstrip('\n').split('\t') for l in open(a.rows) if l.strip() and not l.startswith('#')]
rows = [(r + ['', '', '', ''])[:4] for r in rows]
out = open(a.out, 'w')
for i in range(0, len(rows), a.chunk):
    part = rows[i:i + a.chunk]
    hdr = ('def TPL_XML = %s\ndef RES_XML = %s\ndef SCHEMA_XML = %s\ndef DEV = %s\ndef RECONCILE = %s\ndef NAMES = %s\ndef ROWS = %s\n'
           % (lst(a.tpl), lst(a.res), b64(open(a.schema).read()) if (a.schema and i == 0) else 'null',
              'true' if a.dev else 'false', 'false' if a.no_reconcile else 'true',
              '[' + ', '.join("'%s'" % n for n in a.names.split(',')) + ']',
              '[' + ', '.join('[' + ', '.join("'%s'" % c for c in r) + ']' for r in part) + ']'))
    code = hdr + g
    body = ('<s:executeScript xmlns:s="http://midpoint.evolveum.com/xml/ns/public/model/scripting-3" '
            'xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
            ' <s:action><s:type>execute-script</s:type>\n'
            '  <s:parameter><s:name>script</s:name><c:value xsi:type="c:ScriptExpressionEvaluatorType"><c:code><![CDATA[%s]]></c:code></c:value></s:parameter>\n'
            '  <s:parameter><s:name>forWholeInput</s:name><c:value>true</c:value></s:parameter>\n'
            ' </s:action>\n</s:executeScript>') % code
    t0 = time.time()
    r = subprocess.run(['bash', '-c', '%s POST rpc/executeScript application/xml application/xml 900' % a.mpcurl], input=body.encode(), capture_output=True)
    s = (r.stdout + r.stderr).decode('utf-8', 'replace')
    m = re.search(r'<(?:\w+:)?value[^>]*>(.*?)</(?:\w+:)?value>', s, re.S)
    txt = html.unescape(m.group(1)) if m else s
    out.write('### lote %d (%d) %.0fs\n%s\n' % (i // a.chunk + 1, len(part), time.time() - t0, txt)); out.flush()
    print('lote %d: %.0fs, %d lineas U' % (i // a.chunk + 1, time.time() - t0, txt.count('\nU ') + txt.startswith('U ')), file=sys.stderr)
    if 'Permission denied' in s:
        print('SSH Permission denied: PARO (no reintentar en bucle)', file=sys.stderr); break
