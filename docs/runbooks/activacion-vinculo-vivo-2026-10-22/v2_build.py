import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_mappings import *
RB = sys.argv[1]  # uso: python3 v2_build.py <dir_runbook> [dir_fragmentos_template]
FRAG = sys.argv[2] if len(sys.argv) > 2 else None
HDR = ('<objectModification\n    xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3"\n'
       '    xmlns:t="http://prism.evolveum.com/xml/ns/public/types-3"\n'
       '    xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"\n'
       '    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
       '    xmlns:sciback="urn:sciback:midpoint:person">\n')
def add(path, body):
    # body = '<c:mapping id=..>' ... ; convierte a t:value con xsi:type
    body = body.replace('<c:mapping id=', '<t:value xsi:type="c:ObjectTemplateMappingType" id=', 1)
    body = body[:body.rfind('</c:mapping>')] + '</t:value>'
    body = '\n'.join('    ' + l for l in body.split('\n'))
    return '  <itemDelta>\n    <t:modificationType>add</t:modificationType>\n    <t:path>%s</t:path>\n%s\n  </itemDelta>\n' % (path, body)
def rep(path, val):
    return '  <itemDelta>\n    <t:modificationType>replace</t:modificationType>\n    <t:path>%s</t:path>\n    <t:value>%s</t:value>\n  </itemDelta>\n' % (path, val)
ITEMID = {'student': 5830, 'alum': 5832, 'worker': 5834}
NID = {'student': 5840, 'alum': 5841, 'worker': 5842, 'act': 5843}   # acotados al canario
GID = {'student': 5844, 'alum': 5845, 'worker': 5846, 'act': 5847}   # globales
def named(xml, suffix):
    return re.sub(r'(<c:name>[^<]*)(</c:name>)', r'\1%s\2' % suffix, xml, count=1)
s = HDR
for k in ('student', 'alum', 'worker'):
    s += add('item[%d]/mapping' % ITEMID[k], named(r_mapping(k, CANARIO, 'proposed', NID[k]), '-canario'))
s += add('item[5771]/mapping', named(act_mapping(CANARIO, 'proposed', NID['act']), '-canario'))
for k in ('student', 'alum', 'worker'):
    s += add('item[%d]/mapping' % ITEMID[k], r_mapping(k, [], 'proposed', GID[k]))
s += add('item[5771]/mapping', act_mapping([], 'proposed', GID['act']))
# los v1 (no-op por construccion) quedan fuera de toda configuracion
for p in ('item[5830]/mapping[5831]', 'item[5832]/mapping[5833]', 'item[5834]/mapping[5835]', 'item[5771]/mapping[5836]'):
    s += rep(p + '/lifecycleState', 'archived')
# 5772: deprecated = visible en produccion (sin cambio real), invisible en desarrollo => SIM-dev = estado final
s += rep('item[5771]/mapping[5772]/lifecycleState', 'deprecated')
s += '</objectModification>\n'
open(os.path.join(RB, 'patch-31-template-v2-proposed.xml'), 'w').write(s)
def jp(fn, deltas):
    open(os.path.join(RB, fn), 'w').write(json.dumps({'objectModification': {'itemDelta': [
        {'modificationType': 'replace', 'path': p, 'value': v} for p, v in deltas]}}, indent=1) + '\n')
P = lambda i, m: 'item[%d]/mapping[%d]/lifecycleState' % (i, m)
canario = [(P(ITEMID['student'], NID['student'])), P(ITEMID['alum'], NID['alum']), P(ITEMID['worker'], NID['worker']), P(5771, NID['act'])]
glob = [P(ITEMID['student'], GID['student']), P(ITEMID['alum'], GID['alum']), P(ITEMID['worker'], GID['worker']), P(5771, GID['act'])]
jp('patch-32-template-v2-canario-activar.json', [(p, 'active') for p in canario])
jp('patch-72-template-v2-canario-rollback.json', [(p, 'archived') for p in canario])
jp('patch-41-template-v2-global-activar.json', [(p, 'active') for p in glob] + [(p, 'archived') for p in canario] + [(P(5771, 5772), 'archived')])
jp('patch-81v2-template-global-rollback.json', [(P(5771, 5772), 'active')] + [(p, 'proposed') for p in glob])
# template canonico (estado final): bloques globales, active, sin id (solo si se pide)
if FRAG: open(os.path.join(FRAG, 'v2-tpl-R.xml'), 'w').write('\n'.join(
    ['    <item>\n        <ref>extension/sciback:%s</ref>\n%s\n    </item>' % (ITEM[k], '\n'.join('        ' + l for l in r_mapping(k, [], 'active', None, '').split('\n'))) for k in ('student', 'alum', 'worker')]))
if FRAG: open(os.path.join(FRAG, 'v2-tpl-ACT.xml'), 'w').write(
    '    <item>\n        <ref>activation/administrativeStatus</ref>\n%s\n    </item>' % '\n'.join('        ' + l for l in act_mapping([], 'active', None, '').split('\n')))
print('ok')
jp('patch-91v2-template-v2-retirar.json', [(p, 'archived') for p in canario + glob] + [(P(5771, 5772), 'active')])
print('ok91')
