#!/usr/bin/env python3
"""uso: gen_limpieza.py <template-raw.xml> <e22-raw.xml>
Genera los PATCH de borrado por @id de lo que la gracia dejó archived el 30-oct y su reversión (re-añade tal cual,
sin _metadata, todavía archived; tras ella, rollback-20/21 vuelven a servir)."""
import sys, re, json
TPL = [('item[5830]/mapping', 'mapping', [5844, 5852], 'ObjectTemplateMappingType'),
       ('mapping', 'mapping', [5853], 'ObjectTemplateMappingType')]
E22 = [('schemaHandling/objectType[3297]/attribute[3324]/inbound', 'inbound', [3327], 'InboundMappingType')]
C3 = 'http://midpoint.evolveum.com/xml/ns/public/common/common-3'
def build(raw, spec, root_tag, sufijo):
    root = re.search(r'<%s\b[^>]*>' % root_tag, raw).group(0)
    ns = ' '.join(re.findall(r'xmlns(?::\w+)?="[^"]*"', root)).replace('xmlns="%s"' % C3, 'xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3"')
    deltas, adds = [], []
    for path, tag, ids, xtype in spec:
        deltas.append({"modificationType": "delete", "path": path, "value": [{"@id": i} for i in ids]})
        for i in ids:
            b = re.search(r'<%s id="%d">(.*?)</%s>' % (tag, i, tag), raw, re.S)
            if not b: sys.exit('falta %s %d' % (tag, i))
            body = re.sub(r'\s*<_metadata\b.*?</_metadata>', '', b.group(1), flags=re.S)
            if '<lifecycleState>archived</lifecycleState>' not in body: sys.exit('%s %d NO esta archived' % (tag, i))
            adds.append('  <itemDelta>\n    <t:modificationType>add</t:modificationType>\n    <t:path>%s</t:path>\n'
                        '    <t:value xmlns="%s" xsi:type="c:%s" id="%d">%s</t:value>\n  </itemDelta>' % (path, C3, xtype, i, body))
    json.dump({"objectModification": {"itemDelta": deltas}}, open('patch-L%s-limpieza.json' % sufijo, 'w'), indent=2)
    open('rollback-L%s-restaurar.xml' % sufijo, 'w').write('<objectModification %s>\n%s\n</objectModification>\n' % (ns, '\n'.join(adds)))
    print('L%s: %d borrados, version origen %s' % (sufijo, sum(len(s[2]) for s in spec), re.search(r'version="(\d+)"', root).group(1)))
build(open(sys.argv[1]).read(), TPL, 'objectTemplate', '1-template')
build(open(sys.argv[2]).read(), E22, 'resource', '2-e22')
