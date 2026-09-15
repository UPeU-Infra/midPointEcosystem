#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADR-065 — despliegue de los 9 equipos de desarrollo de la DTI.

NO APLICADO. Requiere la aprobacion escrita de Alberto (ver README.md y el ADR).

Uso:
    source ~/.secrets/midpoint-upeu.env
    python3 aplicar.py            # dry-run: imprime lo que haria, no escribe nada
    python3 aplicar.py --aplicar  # escribe en PROD

Orden (importa):
  1. archetype-org-team      POST  (si no existe)
  2. 9 roles AR-DTI-Dev-*    POST  (antes que las orgs: las orgs los inducen)
  3. 9 orgs DTI-DEV-*        POST
  4. 27 assignments persona->equipo        PATCH add /assignment
  5.  6 assignments jefe->equipo manager   PATCH add /assignment (relation=org:manager)

Idempotente: todo objeto que ya existe se salta; todo assignment que ya esta no se repite.
Los codigos HTTP de MidPoint no son la verdad (R8 del protocolo): al final se RELEE PROD
y se verifica objeto a objeto y persona a persona.
"""
import os, sys, json, base64, urllib.request, urllib.error, time
import xml.etree.ElementTree as ET

C = 'http://midpoint.evolveum.com/xml/ns/public/common/common-3'
T = 'http://prism.evolveum.com/xml/ns/public/types-3'
HERE = os.path.dirname(os.path.abspath(__file__))
APPLY = '--aplicar' in sys.argv
DTI = '00000000-0000-0000-0000-953119566392'

BASE = os.environ['MIDPOINT_URL'].rstrip('/') + '/midpoint/ws/rest'
AUTH = 'Basic ' + base64.b64encode(
    f"{os.environ['MIDPOINT_ADMIN_USER']}:{os.environ['MIDPOINT_ADMIN_PASS']}".encode()).decode()


def call(method, path, body=None, tries=3):
    last = None
    for a in range(tries):
        req = urllib.request.Request(BASE + path,
                                     data=body.encode('utf-8') if body else None, method=method)
        req.add_header('Authorization', AUTH)
        req.add_header('Accept', 'application/xml')
        if body:
            req.add_header('Content-Type', 'application/xml')
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, r.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', 'replace')
        except Exception as ex:                      # red intermitente: reintenta
            last = ex
            time.sleep(2 + 2 * a)
    raise last


def existe(coll, oid):
    return call('GET', f'/{coll}/{oid}')[0] == 200


def post(coll, xml, oid, etiqueta):
    if existe(coll, oid):
        print(f'   = ya existe  {etiqueta}')
        return
    if not APPLY:
        print(f'   + POST       {etiqueta}')
        return
    st, b = call('POST', f'/{coll}', xml)
    print(f'   + POST {st}   {etiqueta}' + ('' if st in (201, 202, 240, 250) else f'  !! {b[:300]}'))


def split_objects(path):
    """Devuelve [(xml_serializado, oid)] de un <objects> contenedor."""
    root = ET.parse(path).getroot()
    out = []
    for ch in root:
        ET.register_namespace('', C)
        out.append((ET.tostring(ch, encoding='unicode'), ch.get('oid')))
    return out


def assignment_patch(target_oid, tipo, relation=None):
    rel = f' relation="org:{relation}"' if relation else ''
    return (f'<objectModification xmlns="{C}" xmlns:t="{T}">'
            f'<t:itemDelta><t:modificationType>add</t:modificationType>'
            f'<t:path>assignment</t:path><t:value>'
            f'<targetRef oid="{target_oid}" type="{tipo}"{rel}/>'
            f'</t:value></t:itemDelta></objectModification>')


def assignments_de(coll, oid):
    st, b = call('GET', f'/{coll}/{oid}')
    if st != 200:
        return None
    o = ET.fromstring(b)
    out = set()
    for a in o.findall(f'{{{C}}}assignment'):
        tr = a.find(f'{{{C}}}targetRef')
        if tr is not None:
            out.add((tr.get('oid'), (tr.get('relation') or 'org:default').split(':')[-1]))
    return out


def main():
    teams = json.load(open(os.path.join(HERE, 'teams.json')))
    per = json.load(open(os.path.join(HERE, 'oids-personas.json')))
    oid_de = {c: v['oid'] for c, v in per.items()}
    modo = 'APLICANDO EN PROD' if APPLY else 'DRY-RUN (no escribe nada)'
    print(f'== ADR-065 · {modo} ==\n')

    print('1. archetype-org-team')
    ET.register_namespace('', C)
    root = ET.parse(os.path.join(HERE, '01-archetype-org-team.xml')).getroot()
    post('archetypes', ET.tostring(root, encoding='unicode'), root.get('oid'), 'archetype-org-team')

    print('\n2. 9 Application Roles AR-DTI-Dev-*')
    for xml, oid in split_objects(os.path.join(HERE, '03-roles-ar-dti-dev.xml')):
        post('roles', xml, oid, oid)

    print('\n3. 9 OrgType DTI-DEV-*')
    for xml, oid in split_objects(os.path.join(HERE, '02-orgs-dti-dev.xml')):
        post('orgs', xml, oid, oid)

    print('\n4. 27 assignments persona -> equipo')
    for eq, t in teams.items():
        for p in t['miembros']:
            u = oid_de[p['codigo']]
            act = assignments_de('users', u) or set()
            if (t['org'], 'default') in act:
                print(f"   = {p['codigo']} ya en {t['code']}")
                continue
            if not APPLY:
                print(f"   + {p['codigo']} -> {t['code']}  ({p['nombre']})")
                continue
            st, b = call('PATCH', f'/users/{u}', assignment_patch(t['org'], 'c:OrgType'))
            print(f"   + {st} {p['codigo']} -> {t['code']}" + ('' if st in (200, 204, 240, 250) else f'  !! {b[:200]}'))

    print('\n5. 6 assignments jefe -> equipo (relation=org:manager)')
    codigo_de = {p['nombre']: p['codigo'] for eq in teams for p in teams[eq]['miembros']}
    for eq, t in teams.items():
        if not t['jefe']:
            print(f"   . {t['code']}: sin jefe — reporta al director de la DTI")
            continue
        u = oid_de[codigo_de[t['jefe']]]
        act = assignments_de('users', u) or set()
        if (t['org'], 'manager') in act:
            print(f"   = {t['jefe']} ya es manager de {t['code']}")
            continue
        if not APPLY:
            print(f"   + {t['jefe']} -> manager de {t['code']}")
            continue
        st, b = call('PATCH', f'/users/{u}', assignment_patch(t['org'], 'c:OrgType', 'manager'))
        print(f"   + {st} {t['jefe']} -> manager de {t['code']}" + ('' if st in (200, 204, 240, 250) else f'  !! {b[:200]}'))

    if not APPLY:
        print('\n(dry-run: nada se escribio. Repetir con --aplicar tras la aprobacion)')
        return

    print('\n== VERIFICACION (relectura de PROD, no se asume nada) ==')
    ok = fail = 0
    for eq, t in teams.items():
        e = assignments_de('orgs', t['org'])
        if e is None:
            print(f'   FALLO org {t["code"]} no existe'); fail += 1; continue
        if (DTI, 'default') not in e:
            print(f'   FALLO {t["code"]} no cuelga de DTI'); fail += 1
        else:
            ok += 1
        for p in t['miembros']:
            a = assignments_de('users', oid_de[p['codigo']]) or set()
            if (t['org'], 'default') in a:
                ok += 1
            else:
                print(f'   FALLO {p["codigo"]} NO esta en {t["code"]}'); fail += 1
        if t['jefe']:
            a = assignments_de('users', oid_de[codigo_de[t['jefe']]]) or set()
            if (t['org'], 'manager') in a:
                ok += 1
            else:
                print(f'   FALLO {t["jefe"]} NO es manager de {t["code"]}'); fail += 1
    print(f'\n   comprobaciones OK={ok}  FALLO={fail}')
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
