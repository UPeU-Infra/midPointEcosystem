#!/usr/bin/env python3
"""Genera los PATCH de gracia-matricula-90 desde g90_mappings.py (una sola fuente de texto).

uso:
  g90_build.py repo   <dir_runbook> <schema_prod.xml> <version_schema>   -> patches SIN PII (van al repo)
  g90_build.py canario <dir_salida_FUERA_del_repo> <fichero_codigos>      -> patch-11c/12c con la lista CANARIO
  g90_build.py sim    <dir_salida> [YYYY-MM-DD]                           -> variantes de SIMULACION: los items
        nuevos se sustituyen por items ya definidos y sin uso en PROD (lastReviewedAt / schacExpiryDate) porque
        el schema nuevo aun no existe; opcionalmente HOY fijo para simular el dia N+1.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from g90_mappings import *

HDR = ('<objectModification\n    xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3"\n'
       '    xmlns:t="http://prism.evolveum.com/xml/ns/public/types-3"\n'
       '    xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"\n'
       '    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
       '    xmlns:sciback="urn:sciback:midpoint:person">\n')
END = '</objectModification>\n'


def add(path, body, xsitype):
    body = re.sub(r'^<c:(mapping|inbound) id=', '<t:value xsi:type="%s" id=' % xsitype, body, count=1)
    body = re.sub(r'</c:(mapping|inbound)>$', '</t:value>', body)
    body = '\n'.join('    ' + l for l in body.split('\n'))
    return '  <itemDelta>\n    <t:modificationType>add</t:modificationType>\n    <t:path>%s</t:path>\n%s\n  </itemDelta>\n' % (path, body)


def rep(path, val):
    return '  <itemDelta>\n    <t:modificationType>replace</t:modificationType>\n    <t:path>%s</t:path>\n    <t:value>%s</t:value>\n  </itemDelta>\n' % (path, val)


TPL_MAP = 'c:ObjectTemplateMappingType'
P_T = lambda mid: 'mapping[%d]/lifecycleState' % mid                        # mapping de nivel superior
P_I = lambda mid: 'item[%d]/mapping[%d]/lifecycleState' % (ITEM_217, mid)    # dentro del item de 217
IN_PATH = 'schemaHandling/objectType[%d]/attribute[%d]/inbound' % (E22_OT, E22_ATTR)
P_IN = lambda iid: '%s[%d]/lifecycleState' % (IN_PATH, iid)


def tpl_proposed(nm, hoy=HOY_REAL, lc='proposed', r1v2='deprecated', n=N_DIAS):
    s = HDR
    s += add('mapping', m_g1(nm, lc, hoy), TPL_MAP)
    s += add('mapping', m_g2(nm, lc, n), TPL_MAP)
    s += add('item[%d]/mapping' % ITEM_217, m_r1v3(nm, lc, None, hoy), TPL_MAP)
    s += add('mapping', m_t1(nm, lc, None, hoy), TPL_MAP)
    # R1v2 deprecated: visible en produccion (sin cambio), invisible en desarrollo => SIM-dev = diseno final
    s += rep(P_I(R1V2), r1v2)
    return s + END


def e22_proposed(nm, hoy=HOY_REAL, lc='proposed', old='deprecated'):
    s = HDR + add(IN_PATH, i_inbound(nm, lc, None, hoy), 'c:InboundMappingType')
    s += rep(P_IN(IN_OLD), old)
    return s + END


def jp(fn, deltas):
    open(fn, 'w').write(json.dumps({'objectModification': {'itemDelta': [
        {'modificationType': 'replace', 'path': p, 'value': v} for p, v in deltas]}}, indent=1) + '\n')


def schema_patch(schema_xml, nm):
    t = open(schema_xml).read()
    i = t.find('<xsd:schema'); j = t.find('</xsd:schema>') + len('</xsd:schema>')
    xs = t[i:j]
    if 'name="%s"' % nm.eff in xs:
        raise SystemExit('el schema YA tiene %s: no hace falta el PATCH' % nm.eff)
    anchor = re.search(r'(<xsd:element [^>]*name="terminationDateStudent"[^>]*>.*?</xsd:element>\n)', xs, re.S)
    if not anchor:
        raise SystemExit('no encuentro terminationDateStudent en el schema de PROD')
    new = xs[:anchor.end()] + schema_elements(nm) + xs[anchor.end():]
    body = (HDR + '  <itemDelta>\n    <t:modificationType>replace</t:modificationType>\n    <t:path>c:definition</t:path>\n'
            '    <t:value>\n        %s\n    </t:value>\n  </itemDelta>\n' % new + END)
    old = (HDR + '  <itemDelta>\n    <t:modificationType>replace</t:modificationType>\n    <t:path>c:definition</t:path>\n'
           '    <t:value>\n        %s\n    </t:value>\n  </itemDelta>\n' % xs + END)
    return body, old


def main():
    mode = sys.argv[1]
    if mode == 'repo':
        rb, schema_xml, ver = sys.argv[2], sys.argv[3], sys.argv[4]
        nm = Names()
        new, old = schema_patch(schema_xml, nm)
        open(os.path.join(rb, 'patch-00-schema-v%s-mas-2-items.xml' % ver), 'w').write(new)
        open(os.path.join(rb, 'rollback-00-schema-v%s.xml' % ver), 'w').write(old)
        open(os.path.join(rb, 'patch-01-template-proposed.xml'), 'w').write(tpl_proposed(nm))
        open(os.path.join(rb, 'patch-02-e22-inbound-proposed.xml'), 'w').write(e22_proposed(nm))
        J = lambda f: os.path.join(rb, f)
        # Fase A: publicar F/EFF (inerte: nada los consume todavia)
        jp(J('patch-10-template-G1G2-activar.json'), [(P_T(ID['G1']), 'active'), (P_T(ID['G2']), 'active')])
        jp(J('rollback-10-template-G1G2.json'), [(P_T(ID['G1']), 'proposed'), (P_T(ID['G2']), 'proposed')])
        # Canario (los patch-11c/12c se generan FUERA del repo con la lista): su vuelta atras solo usa ids
        jp(J('rollback-11c-template-canario.json'), [(P_I(R1V2), 'active'), (P_I(ID['R1v3c']), 'archived'), (P_T(ID['T1c']), 'archived')])
        jp(J('rollback-12c-e22-canario.json'), [(P_IN(IN_OLD), 'active'), (P_IN(ID['INc']), 'archived')])
        # Global
        jp(J('patch-20-template-global-activar.json'), [(P_I(ID['R1v3']), 'active'), (P_T(ID['T1']), 'active'),
                                                        (P_I(R1V2), 'archived'), (P_I(ID['R1v3c']), 'archived'), (P_T(ID['T1c']), 'archived')])
        jp(J('patch-21-e22-global-activar.json'), [(P_IN(ID['IN']), 'active'), (P_IN(IN_OLD), 'archived'), (P_IN(ID['INc']), 'archived')])
        jp(J('rollback-20-template-global.json'), [(P_I(R1V2), 'active'), (P_I(ID['R1v3']), 'proposed'), (P_T(ID['T1']), 'proposed')])
        jp(J('rollback-21-e22-global.json'), [(P_IN(IN_OLD), 'active'), (P_IN(ID['IN']), 'proposed')])
        # Retirar todo lo propuesto (deja PROD como hoy, v137/v209)
        jp(J('rollback-01-template-retirar.json'), [(P_I(R1V2), 'active')] + [(P_T(ID[k]), 'archived') for k in ('G1', 'G2', 'T1')]
           + [(P_I(ID['R1v3']), 'archived')])
        jp(J('rollback-02-e22-retirar.json'), [(P_IN(IN_OLD), 'active'), (P_IN(ID['IN']), 'archived')])
        # Cambiar N: un solo PATCH (replace del <code> de G2)
        open(J('patch-N-template-cambiar-N.xml.ejemplo'), 'w').write(
            HDR + rep('mapping[%d]/expression' % ID['G2'],
                      '<c:script>' + re.search(r'<c:script>(.*)</c:script>', m_g2(nm, 'active', 120), re.S).group(1) + '</c:script>')
            .replace('<t:value><c:script>', '<t:value xsi:type="c:ExpressionType"><c:script>') + END)
        print('repo ok')
    elif mode == 'canario':
        out, f = sys.argv[2], sys.argv[3]
        codes = [l.split()[0] for l in open(f) if l.strip() and not l.startswith('#')]
        nm = Names(); os.makedirs(out, exist_ok=True)
        s = HDR + add('item[%d]/mapping' % ITEM_217, m_r1v3(nm, 'active', codes), TPL_MAP) + add('mapping', m_t1(nm, 'active', codes), TPL_MAP)
        s += rep(P_I(R1V2), 'archived') + END
        open(os.path.join(out, 'patch-11c-template-canario.xml'), 'w').write(s)
        s = HDR + add(IN_PATH, i_inbound(nm, 'active', codes), 'c:InboundMappingType') + rep(P_IN(IN_OLD), 'archived') + END
        open(os.path.join(out, 'patch-12c-e22-canario.xml'), 'w').write(s)
        print('canario ok (%d)' % len(codes))
    elif mode == 'sim':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True)
        hoy = HOY_REAL if len(sys.argv) < 4 else "java.time.LocalDate.parse('%s')" % sys.argv[3]
        nm = Names(last='lastReviewedAt', eff='schacExpiryDate')
        open(os.path.join(out, 'sim-tpl.xml'), 'w').write(tpl_proposed(nm, hoy))
        open(os.path.join(out, 'sim-e22.xml'), 'w').write(e22_proposed(nm, hoy))
        print('sim ok', hoy)


if __name__ == '__main__':
    main()
