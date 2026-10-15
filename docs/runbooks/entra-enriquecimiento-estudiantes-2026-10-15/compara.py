#!/usr/bin/env python3
# Compara schemaHandling/capabilities configuradas de dos XML de resource (PROD vs repo), ignorando ids y comentarios.
import sys, re, xml.etree.ElementTree as ET
C='{http://midpoint.evolveum.com/xml/ns/public/common/common-3}'
def load(p):
    t=open(p).read(); t=t[:t.rindex('</resource>')+11]
    return ET.fromstring(t)
def norm(s): return re.sub(r'\s+',' ',(s or '')).strip()
def summ(root):
    ot=root.find(f'{C}schemaHandling/{C}objectType')
    out={'objectType.lifecycle': norm(ot.findtext(f'{C}lifecycleState'))}
    for at in ot.findall(f'{C}attribute'):
        ref=norm(at.findtext(f'{C}ref'))
        for kind in ('inbound','outbound'):
            for i,m in enumerate(at.findall(f'{C}{kind}')):
                key=f'{ref}/{kind}[{i}]'
                out[key]=(norm(m.findtext(f'{C}name')), norm(m.findtext(f'{C}lifecycleState')), norm(m.findtext(f'{C}strength')),
                          tuple(norm(s.findtext(f'{C}path')) for s in m.findall(f'{C}source')),
                          tuple(norm(c.text) for c in m.iter(f'{C}code')), tuple(norm(v.text) for v in m.iter(f'{C}value')),
                          norm(m.findtext(f'{C}target/{C}path')))
    for i,r in enumerate(ot.findall(f'{C}synchronization/{C}reaction')):
        out[f'reaction[{i}]']=(norm(r.findtext(f'{C}situation')), norm(r.findtext(f'{C}lifecycleState')), tuple(ch.tag.split('}')[1] for ch in r.find(f'{C}actions') or []))
    act=ot.find(f'{C}activation/{C}administrativeStatus/{C}inbound')
    out['activation.inbound']=(norm(act.findtext(f'{C}lifecycleState')), norm(act.findtext(f'{C}strength')))
    out['correlation']=tuple(norm(x.text) for x in ot.iter(f'{C}ref') if x in list(ot.find(f'{C}correlation').iter()))
    cap=root.find(f'{C}capabilities/{C}configured')
    out['capabilities']=tuple((ch.tag.split('}')[1], norm(ch.findtext('{http://midpoint.evolveum.com/xml/ns/public/resource/capabilities-3}enabled'))) for ch in cap)
    out['connectorRef']=root.find(f'{C}connectorRef').get('oid')
    return out
a,b=summ(load(sys.argv[1])),summ(load(sys.argv[2]))
ok=True
for k in sorted(set(a)|set(b)):
    if a.get(k)!=b.get(k):
        ok=False; print('DIFF',k,'\n  A:',str(a.get(k))[:300],'\n  B:',str(b.get(k))[:300])
print('IGUALES' if ok else 'HAY DIFERENCIAS', len(a), len(b))
