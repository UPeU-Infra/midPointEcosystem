#!/usr/bin/env python3
"""uso: comprobar.py <tpl.xml> <e22.xml> antes|despues <v_tpl> <v_e22>"""
import sys, re
tpl, e22 = open(sys.argv[1]).read(), open(sys.argv[2]).read(); fase = sys.argv[3]
def lc(raw, tag, i):
    b = re.search(r'<%s id="%d">(.*?)</%s>' % (tag, i, tag), raw, re.S)
    if not b: return 'absent'
    m = re.search(r'<lifecycleState>(\w+)</lifecycleState>', re.sub(r'<_metadata\b.*?</_metadata>', '', b.group(1), flags=re.S))
    return m.group(1) if m else 'none'
ok = True
def chk(c, msg):
    global ok; print(('OK  ' if c else 'MAL ') + msg); ok &= c
gone = 'archived' if fase == 'antes' else 'absent'
chk(re.search(r'<objectTemplate\b[^>]*version="(\d+)"', tpl).group(1) == sys.argv[4], 'template version (esperada %s)' % sys.argv[4])
chk(re.search(r'<resource\b[^>]*version="(\d+)"', e22).group(1) == sys.argv[5], 'e22 version (esperada %s)' % sys.argv[5])
for i in (5844, 5852, 5853): chk(lc(tpl, 'mapping', i) == gone, 'template mapping %d: %s' % (i, lc(tpl, 'mapping', i)))
for i in (5848, 5849, 5850, 5851): chk(lc(tpl, 'mapping', i) == 'active', 'template mapping %d (gracia, vivo): %s' % (i, lc(tpl, 'mapping', i)))
chk(lc(e22, 'inbound', 3327) == gone, 'e22 inbound 3327: %s' % lc(e22, 'inbound', 3327))
chk(lc(e22, 'inbound', 3381) == 'active', 'e22 inbound 3381 (gracia, vivo): %s' % lc(e22, 'inbound', 3381))
n = len(re.findall(r'<xsd:element\b', e22)); chk(n == 30, 'e22 <schema> xsd:element = %d (esperado 30)' % n)
sys.exit(0 if ok else 1)
