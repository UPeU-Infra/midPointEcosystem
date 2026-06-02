#!/usr/bin/env python3
"""
Cruce Koha x Oracle para el SET SEGURO de archivado + clasificacion de pares por email.
SOLO LECTURA. No modifica nada. Reproduce el analisis del runbook (2026-06-02).

Entradas esperadas (generadas con los .sql de este directorio):
  - koha_safe_base.tsv      : embudo cero-uso de Koha (01_safe_base.sql)
  - koha_canon.tsv          : cuentas canonicas student/alum/faculty/staff (cardnumber + attr DNI)
  - koha_email_pairs.tsv    : cuentas que comparten email @upeu.edu.pe (>1 borrower)
  - ora_stu_vivos.tsv       : (CODIGO, NUM_DOCUMENTO) estudiantes 279/267 (02_oracle_live.sql A)
  - ora_work_vivos.tsv      : (COD_APS, NUM_DOCUMENTO) trabajadores 7124 vivos (02_oracle_live.sql B)
  - koha_merge_pares_REVISABLE.csv : los 100 pares ya hallados por DNI (runbook merge)

Salidas:
  - koha_safe_no_twin.tsv   : SET SEGURO FINAL (6,673)
  - koha_excluidos_activos.tsv : excluidos por seguir activos en Oracle (11,428)
  - email_nuevos.tsv        : 46 pares nuevos por email, clasificados
"""
import csv

def norms(s):
    s = (s or '').strip()
    return {s, s.lstrip('0')} - {''}

LEGACY = {'ESTUDI','ALUMNI','VISITA','DOCEN','ADMINIST','INVESTI','POSGRADO','JUBILADO','ADMIN'}

# --- sets vivos Oracle (codigos y DNIs, con y sin ceros a la izquierda) ---
live_cod, live_dni = set(), set()
for fn in ['ora_stu_vivos.tsv', 'ora_work_vivos.tsv']:
    for line in open(fn):
        p = line.rstrip('\n').split('\t')
        if len(p) > 0 and p[0]: live_cod |= norms(p[0])
        if len(p) > 1 and p[1]: live_dni |= norms(p[1])
live_all = live_cod | live_dni  # un identificador vivo cuenta como vivo sea codigo o DNI

# --- cruce: set base Koha -> activo (excluir) vs no activo (candidato) ---
active, safe = [], []
with open('koha_safe_base.tsv') as f:
    rd = csv.reader(f, delimiter='\t'); header = next(rd)
    for r in rd:
        if len(r) < 10: continue
        cn, adni = r[1], r[9]
        ids = (norms(cn) if cn else set()) | (norms(adni) if adni and adni != 'NULL' else set())
        (active if (ids & live_all) else safe).append(r)

# --- gemela canonica: excluir las que tienen cuenta student/alum/faculty/staff con mismo id ---
canon_ids = set()
with open('koha_canon.tsv') as f:
    rd = csv.reader(f, delimiter='\t'); next(rd)
    for r in rd:
        if len(r) < 4: continue
        if r[1]: canon_ids |= norms(r[1])
        if r[3] and r[3] != 'NULL': canon_ids |= norms(r[3])

no_twin, with_twin = [], []
for r in safe:
    ids = (norms(r[1]) if r[1] else set()) | (norms(r[9]) if r[9] and r[9] != 'NULL' else set())
    (with_twin if (ids & canon_ids) else no_twin).append(r)

def dump(path, rows):
    with open(path, 'w') as f:
        f.write('\t'.join(header) + '\n')
        for r in rows: f.write('\t'.join(r) + '\n')

dump('koha_safe_no_twin.tsv', no_twin)
dump('koha_excluidos_activos.tsv', active)

print(f"base cero-uso        : {len(active)+len(safe)}")
print(f"EXCLUIR activos      : {len(active)}")
print(f"con gemela canonica  : {len(with_twin)}")
print(f"SET SEGURO FINAL     : {len(no_twin)}")

# --- TAREA 1: pares por email no cubiertos por DNI ---
prev_bn = set()
with open('koha_merge_pares_REVISABLE.csv') as f:
    for r in csv.DictReader(f):
        prev_bn.add(r['keeper_borrowernumber']); prev_bn.add(r['loser_borrowernumber'])

from collections import defaultdict
groups = defaultdict(list)
with open('koha_email_pairs.tsv') as f:
    rd = csv.reader(f, delimiter='\t'); next(rd)
    for r in rd:
        if len(r) < 8: continue
        em, bn, cn, cat, sur, fn_, adni, uso = r[:8]
        groups[em].append(dict(bn=bn, cn=cn, cat=cat, sur=sur, fn=fn_, adni=adni, uso=int(uso or 0)))

new_same, new_diff, new_dnidiff = [], [], []
for em, accts in groups.items():
    if not any(a['cat'] in LEGACY for a in accts): continue
    if {a['bn'] for a in accts} & prev_bn: continue  # ya cubierto por DNI
    dnis = {a['adni'].lstrip('0') for a in accts if a['adni'] and a['adni'] != 'NULL'}
    names = {(a['sur'].strip().lower(), a['fn'].strip().lower()) for a in accts}
    if len(dnis) > 1: new_dnidiff.append((em, accts))
    elif len(names) == 1: new_same.append((em, accts))
    else: new_diff.append((em, accts))

with open('email_nuevos.tsv', 'w') as f:
    f.write("clasificacion\temail\tborrowernumber\tcardnumber\tcategoria\tapellido\tnombre\tattr_dni\tuso\n")
    for cls, grp in [("EMAIL_MATCH_SAME_NAME_FUSION_CAND", new_same),
                     ("EMAIL_MATCH_DIFF_NAME_REVIEW", new_diff),
                     ("EMAIL_MATCH_DNI_DISTINTO_REVIEW", new_dnidiff)]:
        for em, accts in grp:
            for a in accts:
                f.write(f"{cls}\t{em}\t{a['bn']}\t{a['cn']}\t{a['cat']}\t{a['sur']}\t{a['fn']}\t{a['adni']}\t{a['uso']}\n")

print(f"\nTAREA 1 pares nuevos por email : {len(new_same)+len(new_diff)+len(new_dnidiff)}")
print(f"  same-name (fusion cand)      : {len(new_same)}")
print(f"  diff-name (revisar)          : {len(new_diff)}")
print(f"  dni-distinto (revisar)       : {len(new_dnidiff)}")
</content>
