#!/usr/bin/env python3
"""Resume un sim_<oid>.json: por persona, delta en Entra (atributo: antes -> despues) y
cualquier otro cambio (usuario sin metadatos, otros recursos). uso: analiza.py sim_x.json"""
import sys, json, collections
ENTRA = '2f11c057-7b15-4641-a0eb-00c98a6fa4cb'
RES = {'7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f': 'LDAP', 'e10a539a-cb7f-4c72-a19f-60f7f62e4b96': 'Koha',
       '6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22': 'Estudiantes', ENTRA: 'Entra'}
d = json.load(open(sys.argv[1]))
users = {}
for r in d:
    po = r['obj'].get('processedObject', {})
    if r['type'] == 'USER':
        users[po.get('@id')] = po.get('name') if isinstance(po.get('name'), str) else r['name']


def val(v):
    if v is None: return None
    out = []
    for x in (v if isinstance(v, list) else [v]):
        out.append(x.get('@value', x) if isinstance(x, dict) else x)
    return out[0] if len(out) == 1 else out


per = collections.OrderedDict()
attr_counter = collections.Counter()
other = collections.Counter()
for r in d:
    po = r['obj'].get('processedObject', {})
    delta = po.get('delta') or {}
    deltas = [i for i in (delta.get('itemDelta') or []) if not str(i.get('path', '')).startswith('@metadata')]
    if r['type'] == 'USER':
        who = r['name']
        for i in deltas:
            p = i['path']
            if p in ('name',) and val(i.get('value')) == val(i.get('estimatedOldValue')):
                continue
            per.setdefault(who, {}).setdefault('USER', []).append('%s %s -> %s' % (i['modificationType'], p, val(i.get('value'))))
            other['USER ' + p] += 1
        continue
    res = (po.get('resourceObjectCoordinates') or {}).get('resourceRef', {}).get('oid')
    who = users.get(po.get('focusRecordId'), '?')
    if not deltas:
        continue
    before = ((po.get('before') or {}).get('attributes') or {})
    for i in deltas:
        p = i['path']
        a = p.split('/')[-1].replace('ri:', '')
        if res == ENTRA and p.startswith('c:attributes/'):
            old = before.get(a)
            new = val(i.get('value'))
            per.setdefault(who, {}).setdefault('Entra', []).append((a, old, new))
            attr_counter[a] += 1
        else:
            per.setdefault(who, {}).setdefault(RES.get(res, res), []).append('%s %s -> %s' % (i['modificationType'], p, str(val(i.get('value')))[:80]))
            other['%s %s' % (RES.get(res, res), p)] += 1
for who, x in per.items():
    print('==', who)
    for k, v in x.items():
        if k == 'Entra':
            for a, o, n in v:
                print('   Entra  %-15s %r -> %r' % (a, o, n))
        else:
            for line in v:
                print('   %-6s %s' % (k, line))
print('\nAtributos Entra con cambio:', dict(attr_counter))
print('Otros cambios:', dict(other))
