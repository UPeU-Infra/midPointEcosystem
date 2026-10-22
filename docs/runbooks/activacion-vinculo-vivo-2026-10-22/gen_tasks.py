#!/usr/bin/env python3
"""Genera las tareas del runbook activacion-vinculo-vivo-2026-10-22.
uso: gen_tasks.py <dir_salida> [--chunk 75] [--threads 2]
  task-sim-0-prod-muestra.xml     preview, config PRODUCCION, recompute reconcile=false (muestra, ANTES del paso 1)
  task-sim-1-prod-muestra.xml     idem DESPUES del paso 1 (debe ser identica a sim-0: el paso 1 es inerte en produccion)
  task-sim-2-dev-muestra.xml      preview, config DESARROLLO (proposed+active): el diseno nuevo
  task-sim-3-dev-recon-trab.xml   preview, config DESARROLLO, reconciliation de Trabajadores (oscilacion LDAP)
  task-real-canario.xml           recompute REAL reconcile=false (8)
  task-real-L1-NN.xml             recompute REAL reconcile=false por trozos (afectados sin canario ni excluidos)
reconcile=false: el diseno no necesita releer Oracle (R/ACT/L leen items del foco y los projection
contexts que el context loader carga desde linkRef); asi el recompute solo materializa outbounds por delta."""
import os, sys
here = os.path.dirname(os.path.abspath(__file__)); L = os.path.join(here, 'lotes')
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
chunk = int(sys.argv[sys.argv.index('--chunk') + 1]) if '--chunk' in sys.argv else 75
threads = int(sys.argv[sys.argv.index('--threads') + 1]) if '--threads' in sys.argv else 2
col = lambda f, i: [l.rstrip('\n').split('\t')[i] for l in open(os.path.join(L, f)) if l.strip()]
canario = col('canario.oids', 2); excl = set(col('excluidos.oids', 1)); muestra = col('muestra-sim.tsv', 1)
L1 = [o for o in col('L1-afectados.oids', 2) if o not in excl and o not in canario]
RUN = 'Runbook activacion-vinculo-vivo-2026-10-22.'
def exe(cfg): return ('<execution><mode>preview</mode><configurationToUse><predefined>%s</predefined></configurationToUse></execution>' % cfg) if cfg else ''
def recompute(name, desc, oids, cfg=None, threads=None):
    vals = ''.join('<q:value>%s</q:value>' % o for o in oids)
    dist = '<distribution><workerThreads>%d</workerThreads></distribution>' % threads if threads else ''
    return ('<task xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3" xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3">\n'
            '  <name>%s</name>\n  <description>%s</description>\n'
            '  <ownerRef oid="00000000-0000-0000-0000-000000000002" type="UserType"/>\n  <executionState>runnable</executionState>\n'
            '  <activity>\n    <work>\n      <recomputation>\n        <objects>\n          <type>UserType</type>\n'
            '          <query><q:filter><q:inOid>%s</q:inOid></q:filter></query>\n        </objects>\n'
            '        <executionOptions><reconcile>false</reconcile></executionOptions>\n      </recomputation>\n    </work>\n'
            '    %s%s\n  </activity>\n</task>\n') % (name, desc, vals, exe(cfg), dist)
def recon_trab():
    return ('<task xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3" xmlns:ri="http://midpoint.evolveum.com/xml/ns/public/resource/instance-3">\n'
            '  <name>SIM-DEV recon Trabajadores (activacion-vinculo-vivo)</name>\n  <description>%s Preview con configuracion de DESARROLLO: ESTADO-&gt;administrativeStatus deprecated (excluido), template R/ACT proposed (incluidos). Esperado: 0 cuentas LDAP disabled para los 1.484 oscilantes.</description>\n'
            '  <ownerRef oid="00000000-0000-0000-0000-000000000002" type="UserType"/>\n  <executionState>runnable</executionState>\n'
            '  <activity>\n    <work>\n      <reconciliation>\n        <resourceObjects>\n'
            '          <resourceRef oid="6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21"/>\n          <kind>account</kind>\n          <intent>default</intent>\n'
            '        </resourceObjects>\n      </reconciliation>\n    </work>\n    %s\n  </activity>\n</task>\n') % (RUN, exe('development'))
def w(fn, s): open(os.path.join(out, fn), 'w').write(s); print(fn)
w('task-sim-0-prod-muestra.xml', recompute('SIM-0-PROD activacion-vinculo-vivo muestra %d (antes paso 1)' % len(muestra), RUN + ' Preview, config produccion.', muestra, 'production'))
w('task-sim-1-prod-muestra.xml', recompute('SIM-1-PROD activacion-vinculo-vivo muestra %d (tras paso 1)' % len(muestra), RUN + ' Preview, config produccion. Debe igualar a SIM-0.', muestra, 'production'))
w('task-sim-2-dev-muestra.xml', recompute('SIM-2-DEV activacion-vinculo-vivo muestra %d' % len(muestra), RUN + ' Preview, config desarrollo (diseno nuevo).', muestra, 'development'))
w('task-sim-3-dev-recon-trab.xml', recon_trab())
w('task-real-canario.xml', recompute('REAL activacion-vinculo-vivo canario (%d)' % len(canario), RUN + ' Recompute real, reconcile=false.', canario))
for i in range(0, len(L1), chunk):
    part = L1[i:i + chunk]
    w('task-real-L1-%02d.xml' % (i // chunk + 1), recompute('REAL activacion-vinculo-vivo L1 %02d (%d)' % (i // chunk + 1, len(part)), RUN + ' Recompute real, reconcile=false.', part, threads=threads))
