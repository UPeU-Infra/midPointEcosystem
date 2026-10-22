#!/usr/bin/env python3
"""Genera las tareas de la corrección J3b (runbook j3b-affiliations-range-2026-10-21).
uso: gen_tasks.py <dir_salida> [--chunk 500] [--threads 2]
Produce:
  task-sim-prod-muestra-{pre,post}.xml  preview, configuracion de PRODUCCION, reconcile=false (50 de la muestra)
  task-real-canario.xml                 recompute REAL, reconcile=false (4 canarios)
  task-real-<lote>-NN.xml               recompute REAL por trozos, reconcile=false, sin canarios ni excluidos
reconcile=false a proposito: J3b sale de items del foco (no hace falta releer Oracle) y asi el recompute
solo materializa outbounds por delta del foco (precedente InOut 16-jul: 0,22 s/foco y sin borrados)."""
import os, sys
here = os.path.dirname(os.path.abspath(__file__)); L = os.path.join(here, 'lotes')
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
chunk = int(sys.argv[sys.argv.index('--chunk') + 1]) if '--chunk' in sys.argv else 500
threads = int(sys.argv[sys.argv.index('--threads') + 1]) if '--threads' in sys.argv else 2
rd = lambda f: [l.split('\t')[-1].strip() if '\t' in l else l.strip() for l in open(os.path.join(L, f)) if l.strip()]
canario = rd('canario.oids'); excl = set(rd('excluidos-foco-congelado.oids')) | set(rd('excluir-revisar-dup-entra.oids'))
muestra = [l.split('\t')[1].strip() for l in open(os.path.join(L, 'muestra-sim.tsv')) if l.strip()]
def task(name, desc, oids, preview=False, threads=None):
    vals = ''.join('<q:value>%s</q:value>' % o for o in oids)
    exe = '<execution><mode>preview</mode><configurationToUse><predefined>production</predefined></configurationToUse></execution>' if preview else ''
    dist = '<distribution><workerThreads>%d</workerThreads></distribution>' % threads if threads else ''
    return ('<task xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3" xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3">\n'
            '  <name>%s</name>\n  <description>%s</description>\n'
            '  <ownerRef oid="00000000-0000-0000-0000-000000000002" type="UserType"/>\n  <executionState>runnable</executionState>\n'
            '  <activity>\n    <work>\n      <recomputation>\n        <objects>\n          <type>UserType</type>\n'
            '          <query><q:filter><q:inOid>%s</q:inOid></q:filter></query>\n        </objects>\n'
            '        <executionOptions><reconcile>false</reconcile></executionOptions>\n      </recomputation>\n    </work>\n'
            '    %s%s\n  </activity>\n</task>\n') % (name, desc, vals, exe, dist)
def w(fn, s): open(os.path.join(out, fn), 'w').write(s); print(fn)
for ph in ('pre', 'post'):
    w('task-sim-prod-muestra-%s.xml' % ph, task('SIM-PROD j3b-range muestra %d (%s-PATCH)' % (len(muestra), ph),
      'Runbook j3b-affiliations-range-2026-10-21. Preview con configuracion de produccion; reconcile=false.', muestra, preview=True))
w('task-real-canario.xml', task('REAL canario j3b-range (%d)' % len(canario), 'Runbook j3b-affiliations-range-2026-10-21. Recompute real, reconcile=false.', canario))
skip = set(canario) | excl
for lote in ('L1-solo-foco', 'L2-baja-con-proyecciones', 'L3-activos'):
    oids = [o for o in rd(lote + '.oids') if o not in skip]
    for i in range(0, len(oids), chunk):
        part = oids[i:i + chunk]
        w('task-real-%s-%02d.xml' % (lote, i // chunk + 1), task('REAL j3b-range %s %02d (%d)' % (lote, i // chunk + 1, len(part)),
          'Runbook j3b-affiliations-range-2026-10-21. Recompute real, reconcile=false.', part, threads=threads))
