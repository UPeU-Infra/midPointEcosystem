#!/usr/bin/env python3
"""Estima, contra el snapshot Entra del 7-sep, que escribiria el enriquecimiento en la poblacion
de estudiantes con shadow de Entra enlazado (replica en Python las expresiones de los outbounds).
uso: impacto.py pop.psv snapshot.json p4677.psv"""
import sys, csv, json, unicodedata, re, collections

pop = [r for r in csv.DictReader(open(sys.argv[1]), delimiter='|') if r.get('nameorig') and r['nameorig'][0].isdigit()]
snap = {x['upn'].lower(): x for x in json.load(open(sys.argv[2]))}
p4677 = {l.split('|')[0] for l in open(sys.argv[3]).read().split()}
LOW = {'de', 'del', 'la', 'las', 'los', 'y', 'e', 'da', 'das', 'do', 'dos', 'van', 'von'}


def title(s):
    s = (s or '').strip()
    if not s: return None
    out = []
    for i, w in enumerate(re.split(r'\s+', s.lower())):
        if i > 0 and w in LOW: out.append(w)
        else: out.append('-'.join(p[:1].upper() + p[1:] if p else p for p in w.split('-')))
    return ' '.join(out)


def noacc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn').lower()


def job(l):
    v = (l or '').strip().lower().replace('-', ' ')
    return {'pregrado': 'Estudiante de pregrado', 'posgrado': 'Estudiante de posgrado', 'doctorado': 'Estudiante de doctorado',
            'segunda especialidad': 'Estudiante de segunda especialidad', 'idiomas': 'Estudiante de idiomas', 'cepre': 'Estudiante de CEPRE'}.get(v, 'Estudiante')


def dept(eps):
    names = {re.sub(r'\s*\([^)]*\)\s*$', '', e).strip() for e in (eps or '').split('#') if e}
    if len(names) != 1: return None
    d = names.pop()
    return d if d.startswith('EP ') else 'EP ' + d


OFF = {'LIMA': ('Sede Lima', 'Lima'), 'JULIACA': ('Filial Juliaca', 'Juliaca'), 'TARAPOTO': ('Filial Tarapoto', 'Tarapoto')}
gated = [r for r in pop if r['pa'] not in ('faculty', 'staff', 'employee')]
print('estudiantes con shadow Entra:', len(pop), '| pasan el GATE de poblacion:', len(gated), '| fuera (doble afiliacion trabajador):', len(pop) - len(gated))
for label, rows in (('TODOS (gate)', gated), ('de los 4.677', [r for r in gated if r['idp'] in p4677])):
    stats = collections.defaultdict(collections.Counter)
    nosnap = 0
    for r in rows:
        x = snap.get(r['upn'].lower())
        if x is None:
            nosnap += 1
            continue
        camp = OFF.get((r['campus'] or '').upper(), (None, None))
        want = {'given': title(r['givennameorig']), 'surname': title(r['familynameorig']), 'employeeId': r['idp'] or None,
                'jobTitle': job(r['lvl']), 'department': dept(r['eps']), 'office': camp[0], 'city': camp[1],
                'company': 'Universidad Peruana Unión', 'usageLocation': 'PE'}
        for a, w in want.items():
            cur = x.get(a)
            if w is None:
                k = 'sin valor MidPoint (no se toca)'
            elif cur in (None, ''):
                k = 'rellena vacio'
            elif cur == w:
                k = 'igual'
            elif a in ('given', 'surname') and noacc(cur) == noacc(w):
                if cur.lower() == w.lower():
                    k = 'solo mayusculas'
                elif sum(1 for c in unicodedata.normalize('NFD', cur) if unicodedata.category(c) == 'Mn') > sum(1 for c in unicodedata.normalize('NFD', w) if unicodedata.category(c) == 'Mn'):
                    k = 'PIERDE TILDE'
                else:
                    k = 'gana tilde'
            else:
                k = 'SOBRESCRIBE distinto'
            stats[a][k] += 1
    print('\n==', label, len(rows), '(sin cuenta en el snapshot 7-sep:', nosnap, ')')
    for a, c in stats.items():
        print('  %-14s %s' % (a, dict(c.most_common())))

# --- detalle de 'SOBRESCRIBE distinto' en nombres: ¿forma corta, basura o OTRA persona? ---
def toks(s): return set(noacc(s).replace('.', ' ').replace('_', ' ').split())
cls = collections.Counter(); ejemplos = collections.defaultdict(list); usage = collections.Counter(); dep = collections.Counter()
for r in gated:
    x = snap.get(r['upn'].lower())
    mp = toks(r['givennameorig']) | toks(r['familynameorig'])
    en = toks(x.get('given')) | toks(x.get('surname'))
    g, s = title(r['givennameorig']), title(r['familynameorig'])
    if (x.get('given') and noacc(x['given']) != noacc(g or '')) or (x.get('surname') and noacc(x['surname']) != noacc(s or '')):
        if not en: k = 'vacio'
        elif en <= mp: k = 'subconjunto (forma corta)'
        elif any('@' in t for t in en) or noacc(x.get('given') or '') == noacc(r['upn'].split('@')[0]): k = 'UPN como nombre'
        elif en & mp: k = 'solapa parcial'
        else: k = 'SIN SOLAPE (¿otra persona?)'
        cls[k] += 1
        if len(ejemplos[k]) < 8: ejemplos[k].append((r['nameorig'], r['upn'], x.get('given'), x.get('surname'), x.get('display'), g, s))
    if x.get('usageLocation') not in (None, '', 'PE'): usage[x.get('usageLocation')] += 1
    d = dept(r['eps'])
    if d and x.get('department') and x['department'] != d: dep[x['department']] += 1
print('\nNombres distintos:', dict(cls))
for k, v in ejemplos.items():
    print(' --', k)
    for e in v: print('    ', e)
print('usageLocation distinto de PE:', dict(usage))
print('department actual que se sobrescribiria (top):', dep.most_common(15))
