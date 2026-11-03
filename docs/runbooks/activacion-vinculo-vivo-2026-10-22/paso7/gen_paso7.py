#!/usr/bin/env python3
"""uso: gen_paso7.py <template-raw.xml>
Genera patch-71-template-limpieza.json (delete por @id de los 9 mappings archivados) y
rollback-71-template-restaurar.xml (los re-añade tal cual estaban, sin _metadata), copiados del GET raw."""
import sys, re, json
OBJ = {  # item -> mappings a borrar
    5771: [5772, 5836, 5843],
    5830: [5831, 5840],
    5832: [5833, 5841],
    5834: [5835, 5842],
}
raw = open(sys.argv[1]).read()
root = re.search(r'<objectTemplate\b[^>]*>', raw).group(0)
ns = ' '.join(re.findall(r'xmlns(?::\w+)?="[^"]*"', root))
deltas, adds = [], []
for item, ms in OBJ.items():
    deltas.append({"modificationType": "delete", "path": "item[%d]/mapping" % item, "value": [{"@id": m} for m in ms]})
    for m in ms:
        b = re.search(r'<mapping id="%d">(.*?)</mapping>' % m, raw, re.S)
        if not b: sys.exit('falta mapping %d' % m)
        body = re.sub(r'\s*<_metadata\b.*?</_metadata>', '', b.group(1), flags=re.S)
        if '<lifecycleState>archived</lifecycleState>' not in body: sys.exit('mapping %d NO esta archived' % m)
        adds.append('  <itemDelta>\n    <t:modificationType>add</t:modificationType>\n    <t:path>item[%d]/mapping</t:path>\n'
                    '    <t:value xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3" xsi:type="c:ObjectTemplateMappingType" id="%d">%s</t:value>\n  </itemDelta>' % (item, m, body))
json.dump({"objectModification": {"itemDelta": deltas}}, open('patch-71-template-limpieza.json', 'w'), indent=2)
ns_rb = ns.replace('xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"', 'xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3"')
open('rollback-71-template-restaurar.xml', 'w').write('<objectModification %s>\n%s\n</objectModification>\n' % (ns_rb, '\n'.join(adds)))
print('OK: 9 mappings; version origen', re.search(r'version="(\d+)"', root).group(1))
