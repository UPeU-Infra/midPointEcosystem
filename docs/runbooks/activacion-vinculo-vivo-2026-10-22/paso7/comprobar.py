#!/usr/bin/env python3
"""uso: comprobar.py <tpl.xml> antes|despues <version_esperada>
antes:   los 9 existen y estan archived; los vivos estan active.
despues: los 9 ya no existen; los vivos siguen active; mismo numero de items."""
import sys, re
BORRAR = [5772, 5836, 5843, 5831, 5840, 5833, 5841, 5835, 5842]
VIVOS = [5770, 5847, 5850, 5845, 5846]
raw = open(sys.argv[1]).read(); fase, vesp = sys.argv[2], sys.argv[3]
def lc(i):
    b = re.search(r'<mapping id="%d">(.*?)</mapping>' % i, raw, re.S)
    if not b: return 'absent'
    m = re.search(r'<lifecycleState>(\w+)</lifecycleState>', re.sub(r'<_metadata\b.*?</_metadata>', '', b.group(1), flags=re.S))
    return m.group(1) if m else 'none'
ok = True
def chk(c, msg):
    global ok; print(('OK  ' if c else 'MAL ') + msg); ok &= c
v = re.search(r'<objectTemplate\b[^>]*version="(\d+)"', raw).group(1)
chk(v == vesp, 'version %s (esperada %s)' % (v, vesp))
for i in BORRAR: chk(lc(i) == ('archived' if fase == 'antes' else 'absent'), 'mapping %d: %s' % (i, lc(i)))
for i in VIVOS: chk(lc(i) == 'active', 'mapping %d (vivo): %s' % (i, lc(i)))
print('items=%d mappings=%d' % (len(re.findall(r'<item id=', raw)), len(re.findall(r'<mapping id=', raw))))
sys.exit(0 if ok else 1)
