#!/usr/bin/env python3
"""
Verificador del árbol organizativo — el blindaje ejecutable.

Compara PROD contra la línea base versionada (docs/baselines/arbol-organizativo-baseline.json)
y contra el repo. Falla (exit 1) ante cualquier desviación estructural no autorizada.

Uso:
    source ~/.secrets/midpoint-upeu.env
    python3 upeu/scripts/verificar-arbol-organizativo.py

Invariantes que protege (con su porqué, ver docs/ARQUITECTURA-ARBOL-ORGANIZATIVO.md):
  I1  Las raíces del bosque son EXACTAMENTE las de la baseline. Una raíz nueva = una OU
      nueva en LDAP sin decisión (incidente sedes 2026-08-05).
  I2  Ningún nodo estructural cambió su `identifier`. El identifier gobierna el DN de la OU;
      el conector LDAP no soporta rename → cambiarlo crea OU duplicada.
  I3  Ningún nodo estructural cambió de padre ni desapareció. La espina del árbol
      (Asamblea→Rectorado→VRs→DG Campus, facultades, campus, 26 EP) es fija.
  I4  Toda org versionada en upeu/orgs/ (fuera de archive/) EXISTE en PROD — anti-drift
      repo→PROD. Excepciones conocidas en KNOWN_PENDING (limpieza quirúrgica pendiente).
  I5  Toda org academic-program de PROD está versionada en el repo — anti-drift PROD→repo
      (así aparecieron EP-DER/EP-III/EP-ISW el 2026-08-06).
  I6  Los restos del CRIS no crecen: LINEA-* ≤ 178 y CII-* ≤ 7. Solo pueden bajar.

Cambiar la estructura NO es editar la baseline a mano: exige ADR + simulación preview +
regenerar la baseline en el mismo commit que el cambio. Ver la sección "Blindaje" del doc.
"""
import json, os, re, sys, glob, base64, urllib.request
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASELINE = os.path.join(REPO, 'docs/baselines/arbol-organizativo-baseline.json')

# Orgs del repo aún no desplegadas/limpiadas — cada entrada debe tener ticket o doc que la ampare.
# Al cerrar la limpieza de los 2 archivos mixtos, esta lista debe quedar VACÍA.
KNOWN_PENDING_FILES = [
    'upeu/orgs/050-GobiernoAdmin.xml',          # 24 orgs sin desplegar (arbol manual, mixto)
    'upeu/orgs/campus/org-campus-lima-units.xml' # 8 orgs sin desplegar (mixto)
]

def loc(t): return t.split('}')[-1]

def fetch_prod_orgs():
    url = os.environ['MIDPOINT_URL'].rstrip('/') + '/midpoint/ws/rest/orgs?limit=2000'
    tok = base64.b64encode(f"{os.environ['MIDPOINT_ADMIN_USER']}:{os.environ['MIDPOINT_ADMIN_PASS']}".encode()).decode()
    req = urllib.request.Request(url, headers={'Authorization': 'Basic ' + tok})
    with urllib.request.urlopen(req, timeout=240) as r:
        root = ET.fromstring(r.read())
    orgs = {}
    for o in root:
        oid = o.get('oid')
        if not oid:
            continue
        g = lambda t: (o.find('{*}' + t).text if o.find('{*}' + t) is not None else None)
        pars = sorted(p.get('oid') for p in o.iter() if loc(p.tag) == 'parentOrgRef')
        orgs[oid] = {'name': g('name'), 'identifier': g('identifier'),
                     'subtype': (g('subtype') or '').strip() or None, 'parents': pars}
    return orgs

def repo_org_oids():
    out = {}
    for f in glob.glob(os.path.join(REPO, 'upeu/orgs/**/*.xml'), recursive=True):
        rel = os.path.relpath(f, REPO)
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        nodes = [root] if loc(root.tag) == 'org' else [c for c in root if loc(c.tag) == 'org']
        for n in nodes:
            if n.get('oid'):
                nm = n.find('{*}name')
                out[n.get('oid')] = (rel, nm.text if nm is not None else '?')
    return out

def main():
    base = json.load(open(BASELINE))
    prod = fetch_prod_orgs()
    fails, warns = [], []

    # I1 — raíces exactas
    roots = sorted(v['name'] for v in prod.values() if not v['parents'])
    if roots != sorted(base['raices_permitidas']):
        fails.append(f"I1 raíces: PROD={roots} vs baseline={sorted(base['raices_permitidas'])}")

    # I2/I3 — nodos estructurales: existen, identifier y padres intactos
    for oid, b in base['nodos'].items():
        p = prod.get(oid)
        if p is None:
            fails.append(f"I3 nodo estructural DESAPARECIDO: {b['name']} ({oid[:8]})")
            continue
        if (p['identifier'] or '') != (b['identifier'] or ''):
            fails.append(f"I2 identifier CAMBIADO en {b['name']}: '{b['identifier']}' -> '{p['identifier']}'")
        if p['parents'] != b['parents']:
            fails.append(f"I3 padres CAMBIADOS en {b['name']}: {b['parents']} -> {p['parents']}")

    # I4 — todo lo versionado existe en PROD (anti-drift repo→PROD)
    repo = repo_org_oids()
    pending_ok = 0
    for oid, (rel, nm) in sorted(repo.items()):
        if oid in prod:
            continue
        if any(rel == kp for kp in KNOWN_PENDING_FILES):
            pending_ok += 1
            continue
        fails.append(f"I4 org versionada SIN desplegar (drift): {nm} en {rel}")
    if pending_ok:
        warns.append(f"I4 {pending_ok} orgs en KNOWN_PENDING (limpieza de archivos mixtos pendiente)")

    # I5 — todo academic-program de PROD está en el repo (anti-drift PROD→repo)
    for oid, v in prod.items():
        if v['subtype'] == 'academic-program' and oid not in repo:
            fails.append(f"I5 academic-program en PROD sin versionar: {v['name']} ({oid[:8]})")

    # I6 — los restos del CRIS no crecen
    n_linea = sum(1 for v in prod.values() if (v['identifier'] or '').startswith('LINEA-'))
    n_cii = sum(1 for v in prod.values() if (v['identifier'] or '').startswith('CII-'))
    if n_linea > 178:
        fails.append(f"I6 LINEA-* creció: {n_linea} > 178")
    if n_cii > 7:
        fails.append(f"I6 CII-* creció: {n_cii} > 7")
    warns.append(f"I6 restos del CRIS presentes: {n_linea} LINEA-* + {n_cii} CII-* (segunda pasada pendiente)")

    print(f"Árbol organizativo — PROD: {len(prod)} orgs · baseline: {len(base['nodos'])} nodos estructurales")
    for w in warns:
        print(f"  🟡 {w}")
    if fails:
        print(f"\n🔴 {len(fails)} VIOLACIONES:")
        for f in fails:
            print(f"  🔴 {f}")
        sys.exit(1)
    print("\n✅ Estructura íntegra: 6/6 invariantes se cumplen.")

if __name__ == '__main__':
    main()
