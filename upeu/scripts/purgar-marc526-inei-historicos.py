#!/usr/bin/env python3
"""
Elimina del MARC 526 los datafield cuyo $a es un codigo INEI historico.

Decision (Alberto, 2026-08-10): el catalogo no debe conservar rastro de codigos
INEI, porque ensucian los reportes. Los 11 codigos afectados corresponden a
programas que YA NO figuran en el A4/A8 2026-1 y por tanto no tienen P-code:
asignarles uno seria inventar (el matching automatico proponia P01 "Bachiller en
Administracion" para una MAESTRIA en Administracion de Negocios).

Se elimina el datafield 526 completo, no solo el subcampo. Medido antes de
ejecutar: NINGUN registro se queda sin 526 — los 19.138 afectados conservan
entre 8 y 61 P-codes vigentes.

Uso: purgar526.py [--dry-run] [--limit=N]
"""
import re, subprocess, sys

HIST = {'12102051','12102128','31302383','41101897','41310737','41600562',
        '41709097','41910511','61110044','91605478','91605517'}
DRY = "--dry-run" in sys.argv

def sql(q, fetch=True):
    if fetch:
        p = subprocess.run(["koha-mysql","upeu","-N","-e",q], capture_output=True, text=True)
    else:
        p = subprocess.run(["koha-mysql","upeu","-N"], input=q, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[:400])
    return p.stdout

def desescapar(s):
    out=[]; i=0
    while i < len(s):
        if s[i] == "\\" and i+1 < len(s):
            out.append({"n":"\n","t":"\t","r":"\r","0":"\0","\\":"\\"}.get(s[i+1], s[i+1])); i+=2
        else:
            out.append(s[i]); i+=1
    return "".join(out)

RE_526 = re.compile(r'<datafield[^>]*tag="526"[^>]*>.*?</datafield>\s*', re.S)
RE_SUBA = re.compile(r'<subfield[^>]*code="a"[^>]*>([^<]*)</subfield>')

def purgar(xml):
    n = [0]
    def f(m):
        vals = [v.strip() for v in RE_SUBA.findall(m.group(0))]
        if vals and all(v in HIST for v in vals):
            n[0] += 1
            return ""
        return m.group(0)
    return RE_526.sub(f, xml), n[0]

ids = [l.strip() for l in sql(
    'SELECT id FROM biblio_metadata WHERE metadata LIKE \'%tag="526"%\'').splitlines() if l.strip()]
LIM = [a for a in sys.argv if a.startswith("--limit=")]
if LIM:
    ids = ids[:int(LIM[0].split("=")[1])]
print(f"registros con 526: {len(ids)}", flush=True)

LOTE = 200
tot_reg = tot_df = 0
for i in range(0, len(ids), LOTE):
    filas = sql("SELECT id, metadata FROM biblio_metadata WHERE id IN (%s)" % ",".join(ids[i:i+LOTE]))
    ups = []
    for linea in filas.split("\n"):
        if "\t" not in linea: continue
        rid, xml = linea.split("\t", 1)
        nuevo, n = purgar(desescapar(xml))
        if n == 0: continue
        tot_reg += 1; tot_df += n
        esc = nuevo.replace("\\","\\\\").replace("'","\\'")
        ups.append(f"UPDATE biblio_metadata SET metadata='{esc}' WHERE id={rid};")
    if ups and not DRY:
        sql("\n".join(ups), fetch=False)
    if (i//LOTE) % 10 == 0:
        print(f"  offset {i}  registros={tot_reg}  datafields_eliminados={tot_df}", flush=True)

print(f"\n{'(DRY-RUN) ' if DRY else ''}registros modificados: {tot_reg}")
print(f"datafields 526 eliminados: {tot_df}")
