#!/usr/bin/env python3
"""uso: verificar.py <objeto.xml> id=estadoEsperado ...   (estadoEsperado: proposed|active|deprecated|archived|none|absent)
Lee el GET raw (XML) y comprueba el lifecycleState de cada container por id. En resources ademas
cuenta xsd:element del <schema> (tras cualquier PATCH debe seguir igual que en el respaldo)."""
import sys, xml.etree.ElementTree as ET
NS = '{http://midpoint.evolveum.com/xml/ns/public/common/common-3}'
r = ET.parse(sys.argv[1]).getroot(); ok = True
byid = {e.get('id'): e for e in r.iter() if e.get('id')}
for spec in sys.argv[2:]:
    cid, want = spec.split('=')
    e = byid.get(cid)
    got = 'absent' if e is None else (e.findtext(NS + 'lifecycleState') or 'none')
    flag = 'OK ' if got == want else 'MAL'; ok &= got == want
    print('%s id=%s %s lifecycleState=%s (esperado %s)' % (flag, cid, '' if e is None else e.tag.split('}')[1], got, want))
n = sum(1 for e in r.iter() if e.tag.endswith('}element') and 'XMLSchema' in e.tag)
print('version=%s  xsd:element=%d' % (r.get('version'), n))
sys.exit(0 if ok else 1)
