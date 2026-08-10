#!/usr/bin/env python3
"""
Migra MARC 526$a del codigo INEI al P-code oficial (A4/A8 2026-1), en Koha.

Decision (Alberto, 2026-08-10): se migran SOLO los codigos que corresponden a un
programa vigente; los de programas extintos se QUEDAN con su INEI historico.
Resultado esperado: campo 526 mixto A PROPOSITO.

Solo toca <subfield code="a"> DENTRO de un <datafield tag="526">. Un replace global
del numero podria pisar otros campos (ISBN, fechas, codigos de otros esquemas).

Uso: migrar526.py <mapa.csv> [--dry-run]
"""
import csv, re, subprocess, sys, collections

MAPA = sys.argv[1]
DRY = "--dry-run" in sys.argv

mapa = {r["inei"]: r["pcode"] for r in csv.DictReader(open(MAPA))}
print(f"mapa: {len(mapa)} codigos a migrar", flush=True)

def sql(q, fetch=True):
    # SIN --raw: mysql escapa newline/tab/backslash, asi cada fila cabe en una linea.
    # Con --raw el marcxml (que lleva saltos reales) se parte y no se puede parsear.
    # Los UPDATE van por STDIN: un lote con marcxml completo desborda ARG_MAX
    # ("Argument list too long") si se pasa con -e.
    if fetch:
        p = subprocess.run(["koha-mysql", "upeu", "-N", "-e", q],
                           capture_output=True, text=True)
    else:
        p = subprocess.run(["koha-mysql", "upeu", "-N"],
                           input=q, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[:400])
    return p.stdout

def desescapar(s):
    out=[]; i=0
    while i < len(s):
        if s[i] == "\\" and i+1 < len(s):
            c = s[i+1]
            out.append({"n":"\n","t":"\t","r":"\r","0":"\0","\\":"\\"}.get(c, c))
            i += 2
        else:
            out.append(s[i]); i += 1
    return "".join(out)

# datafield 526 completo, con sus subfields
RE_526 = re.compile(r'<datafield[^>]*tag="526"[^>]*>.*?</datafield>', re.S)
RE_SUBA = re.compile(r'(<subfield[^>]*code="a"[^>]*>)([^<]*)(</subfield>)')

def migrar(xml):
    """Devuelve (xml_nuevo, n_valores_cambiados).

    Ademas de traducir, DEDUPLICA: dos INEI distintos pueden mapear al mismo
    P-code (P29 <- 41400200 y 41600207; P80 <- 31302652 y 31302933) porque son
    modalidades del mismo programa. Sin deduplicar, 12.232 registros quedarian
    con el mismo P-code repetido en varios datafield 526.
    """
    cambios = [0]
    dups = [0]
    vistos = set()
    def en_526(m):
        bloque = m.group(0)
        def sub(s):
            val = s.group(2).strip()
            nuevo = mapa.get(val)
            if nuevo and nuevo != val:
                cambios[0] += 1
                return s.group(1) + nuevo + s.group(3)
            return s.group(0)
        nuevo_bloque = RE_SUBA.sub(sub, bloque)
        vals = [v.strip() for _, v, _ in RE_SUBA.findall(nuevo_bloque)]
        clave = tuple(vals)
        if clave and clave in vistos:
            dups[0] += 1
            return ""          # datafield 526 duplicado: se elimina entero
        vistos.add(clave)
        return nuevo_bloque
    return RE_526.sub(en_526, xml), cambios[0] + dups[0]

ids = [l.strip() for l in sql(
    'SELECT id FROM biblio_metadata WHERE metadata LIKE \'%tag="526"%\'').splitlines() if l.strip()]
LIM = [a for a in sys.argv if a.startswith("--limit=")]
if LIM:
    ids = ids[:int(LIM[0].split("=")[1])]
    print(f"LIMITADO a {len(ids)} registros", flush=True)
print(f"registros con 526: {len(ids)}", flush=True)

LOTE = 200
tot_reg = tot_val = 0
sin_cambio = 0
for i in range(0, len(ids), LOTE):
    chunk = ids[i:i+LOTE]
    filas = sql("SELECT id, metadata FROM biblio_metadata WHERE id IN (%s)" % ",".join(chunk))
    updates = []
    for linea in filas.split("\n"):
        if "\t" not in linea:
            continue
        rid, xml = linea.split("\t", 1)
        xml = desescapar(xml)
        nuevo, n = migrar(xml)
        if n == 0:
            sin_cambio += 1
            continue
        tot_reg += 1; tot_val += n
        esc = nuevo.replace("\\", "\\\\").replace("'", "\\'")
        updates.append(f"UPDATE biblio_metadata SET metadata='{esc}' WHERE id={rid};")
    if updates and not DRY:
        sql("\n".join(updates), fetch=False)
    if (i // LOTE) % 10 == 0:
        print(f"  offset {i}  registros_cambiados={tot_reg}  valores={tot_val}", flush=True)

print(f"\n{'(DRY-RUN) ' if DRY else ''}registros modificados: {tot_reg}")
print(f"valores 526 migrados : {tot_val}")
print(f"registros sin cambio : {sin_cambio}  (solo llevan codigos historicos o ya migrados)")
