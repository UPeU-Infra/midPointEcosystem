#!/usr/bin/env python3
"""
Verificador del árbol organizativo — el blindaje ejecutable.

Compara PROD contra la línea base versionada (docs/baselines/arbol-organizativo-baseline.json)
y contra el repo. Falla (exit 1) ante cualquier desviación estructural no autorizada.

Cubre el árbol de organizaciones (I1-I6) y la correspondencia repo↔PROD de los roles
versionados (I7-I8).

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
      repo→PROD. KNOWN_PENDING está VACÍA desde 2026-08-06: el repo ya no describe
      ninguna org inexistente.
  I5  Toda org academic-program de PROD está versionada en el repo — anti-drift PROD→repo
      (así aparecieron EP-DER/EP-III/EP-ISW el 2026-08-06).
  I6  Los restos del CRIS no reaparecen: LINEA-* == 0 (limpiadas 2026-08-06) y CII-* ≤ 7.
  I7  Todo rol versionado en upeu/roles/ EXISTE en PROD y con el MISMO OID — anti-drift
      repo→PROD, el análogo de I4 para roles. Un XML versionado describe algo aplicable:
      quien lo encuentre lo va a aplicar. Añadida el 2026-09-17 tras el DevOps huérfano —
      el equipo se deshizo el 16-sep, el rol y el grupo se borraron de PROD, y
      role-dti-devops.xml siguió en el repo sin que nada lo cantara: este script daba 6/6.
  I8  Todo AR-DTI-Team-* de PROD está versionado — anti-drift PROD→repo, el análogo de I5.
      Acotado a esa familia a propósito: es la que se toca a mano con más frecuencia, y
      exigirlo sobre los 72 roles de PROD sería ruido, no blindaje.

Cambiar la estructura NO es editar la baseline a mano: exige ADR + simulación preview +
regenerar la baseline en el mismo commit que el cambio. Ver la sección "Blindaje" del doc.
"""
import json, os, re, sys, glob, base64, urllib.request
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASELINE = os.path.join(REPO, 'docs/baselines/arbol-organizativo-baseline.json')

# Orgs del repo aún no desplegadas — cada entrada debe tener ticket o doc que la ampare.
# VACÍA desde 2026-08-06: las 32 orgs de los 2 archivos mixtos se retiraron a
# archive/orgs-arbol-manual-2026-08-06/*-RETIRADAS.xml. El repo ya no describe
# ninguna org que no exista en PROD. Volver a llenar esta lista exige justificación escrita.
KNOWN_PENDING_FILES = []

# Roles versionados que hoy NO están en PROD — cada entrada con su motivo y su salida.
# No es una vía para silenciar I7: lo declarado aquí sigue saliendo en amarillo cada pasada.
#
# Los 5 del RIMS los destapó I7 el 2026-09-17, su primer día. Se versionaron el 2026-08-03
# (commit 8326f30, "los 6 roles que solo vivian en PROD") y después desaparecieron de PROD sin
# que nada lo registrara: hoy dan 404 por OID y no hay ningún rol con "RIMS" en el nombre.
# No se sabe si se perdieron en la recuperación post-OOM o si se retiraron a propósito.
# SALIDA: o se redespliegan desde estos XML, o se retiran del repo como se retiró
# role-dti-devops.xml (b1f9de0). Mientras no se decida, quedan aquí a la vista.
KNOWN_PENDING_ROLES = [
    'upeu/roles/application/AR-RIMS-Admin.xml',
    'upeu/roles/application/AR-RIMS-Cataloger.xml',
    'upeu/roles/application/AR-RIMS-Cataloger-Campus-LIMA.xml',
    'upeu/roles/application/AR-RIMS-Cataloger-Campus-JULIACA.xml',
    'upeu/roles/application/AR-RIMS-Cataloger-Campus-TARAPOTO.xml',
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

def fetch_prod_roles():
    """Los roles de PROD, por OID. Mismo transporte que las orgs."""
    url = os.environ['MIDPOINT_URL'].rstrip('/') + '/midpoint/ws/rest/roles?limit=2000'
    tok = base64.b64encode(f"{os.environ['MIDPOINT_ADMIN_USER']}:{os.environ['MIDPOINT_ADMIN_PASS']}".encode()).decode()
    req = urllib.request.Request(url, headers={'Authorization': 'Basic ' + tok})
    with urllib.request.urlopen(req, timeout=240) as r:
        root = ET.fromstring(r.read())
    roles = {}
    for o in root:
        oid = o.get('oid')
        if not oid:
            continue
        nm = o.find('{*}name')
        roles[oid] = {'name': nm.text if nm is not None else None}
    return roles


def repo_role_oids():
    """Los roles versionados, por OID. `archive/` queda fuera, como en las orgs."""
    out = {}
    for f in glob.glob(os.path.join(REPO, 'upeu/roles/**/*.xml'), recursive=True):
        rel = os.path.relpath(f, REPO)
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        nodes = [root] if loc(root.tag) == 'role' else [c for c in root if loc(c.tag) == 'role']
        for n in nodes:
            if n.get('oid'):
                nm = n.find('{*}name')
                out[n.get('oid')] = (rel, nm.text if nm is not None else '?')
    return out


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
    if n_linea > 0:
        fails.append(f"I6 LINEA-* REAPARECIÓ: {n_linea} (deben ser 0 desde la limpieza 2026-08-06)")
    if n_cii > 7:
        fails.append(f"I6 CII-* creció: {n_cii} > 7")
    if n_cii:
        warns.append(f"I6 quedan {n_cii} CII-* del CRIS (310 personas — decisión de reubicación pendiente)")

    # I7 — todo rol versionado existe en PROD, con su OID (anti-drift repo→PROD)
    prod_roles = fetch_prod_roles()
    repo_roles = repo_role_oids()
    roles_pending = 0
    for oid, (rel, nm) in sorted(repo_roles.items()):
        if oid not in prod_roles:
            if rel in KNOWN_PENDING_ROLES:
                roles_pending += 1
                continue
            fails.append(f"I7 rol versionado SIN desplegar (drift): {nm} en {rel}")
        elif prod_roles[oid]['name'] != nm:
            fails.append(f"I7 OID {oid[:8]} nombra '{nm}' en {rel} y '{prod_roles[oid]['name']}' en PROD")

    if roles_pending:
        warns.append(f"I7 {roles_pending} roles del RIMS versionados y ausentes de PROD "
                     f"desde antes del 2026-09-17 — redesplegar o retirar, sin decidir")

    # I8 — todo AR-DTI-Team-* de PROD está versionado (anti-drift PROD→repo)
    for oid, v in prod_roles.items():
        if (v['name'] or '').startswith('AR-DTI-Team-') and oid not in repo_roles:
            fails.append(f"I8 rol de equipo del DTI en PROD sin versionar: {v['name']} ({oid[:8]})")

    print(f"Árbol organizativo — PROD: {len(prod)} orgs · baseline: {len(base['nodos'])} nodos estructurales")
    print(f"Roles — PROD: {len(prod_roles)} · versionados: {len(repo_roles)}")
    for w in warns:
        print(f"  🟡 {w}")
    if fails:
        print(f"\n🔴 {len(fails)} VIOLACIONES:")
        for f in fails:
            print(f"  🔴 {f}")
        sys.exit(1)
    print("\n✅ Estructura íntegra: 8/8 invariantes se cumplen.")

if __name__ == '__main__':
    main()
