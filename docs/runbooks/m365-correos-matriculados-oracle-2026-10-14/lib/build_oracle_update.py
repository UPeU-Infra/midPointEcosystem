#!/usr/bin/env python3
"""
Correo institucional que FALTA en Oracle (MOISES.PERSONA_NATURAL.CORREO_INST) para los
matriculados de PREGRADO del ciclo 2026-2, verificado contra Entra ID.

Decisión de Alberto (14-oct-2026): a estas alturas del ciclo no se cambia el UPN de nadie;
las cuentas DNI@upeu.edu.pe se informan TAL CUAL, siempre que sean un buzón real.

Salidas (en OUT):
  Correos_faltantes_Oracle_pregrado_2026-2_<fecha>.xlsx
  UPDATE_CORREO_INST_pregrado_2026-2_<fecha>.sql     (sin COMMIT: lo decide quien ejecuta)
  ROLLBACK_CORREO_INST_pregrado_2026-2_<fecha>.sql
"""
import csv, json, re, unicodedata, datetime, sys
from collections import defaultdict, Counter
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

SP = sys.argv[1]
OUT = sys.argv[2]
FECHA = datetime.date.today().isoformat()
TIPOS = {"1": "DNI", "4": "Carné de extranjería", "7": "Pasaporte", "24": "Doc. identidad extranjero",
         "6": "RUC", "0": "Otros", "31": "Cédula"}
RX_OK = re.compile(r"^[a-z0-9._-]+@upeu\.edu\.pe$")

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z ]", " ", s).upper()).strip()
def lp(a): return (a or "").split("@")[0].lower()
def num(a): return lp(a).isdigit()

# ── Oracle: pregrado 2026-2, una fila por persona ──
ora = {}
for r in csv.DictReader(open(f"{SP}/ora_2026_2_v2.tsv", encoding="utf-8", errors="replace"), delimiter="\t"):
    if r["NIVEL"].strip() != "Pregrado": continue
    k = r["ID_PERSONA"].strip()
    if k in ora:
        if r["PROGRAMA"].strip() not in ora[k]["PROGRAMA"]:
            ora[k]["PROGRAMA"] += " | " + r["PROGRAMA"].strip()
        continue
    ora[k] = {c: (v or "").strip() for c, v in r.items()}
    ora[k]["CUR"] = ora[k]["CORREO_INST_RAW"].lower()

# CORREO_INST de TODO Oracle: para no asignar un correo que ya es de otra persona
dueno = defaultdict(set)
for r in csv.DictReader(open(f"{SP}/ora_correo_inst_all.tsv", encoding="utf-8", errors="replace"), delimiter="\t"):
    if r["CORREO_INST"]: dueno[r["CORREO_INST"].strip()].add(r["ID_PERSONA"].strip())
# fichas con el mismo documento (advertencia de Owen)
docdup = defaultdict(list)
for r in csv.DictReader(open(f"{SP}/ora_doc_dup.tsv", encoding="utf-8", errors="replace"), delimiter="\t"):
    docdup[(r["ID_TIPODOCUMENTO"], r["NUM_DOCUMENTO"])].append(r)

# nombres completos repetidos en TODO Oracle (homonimia): un nombre único es evidencia fuerte
import os
homon = set()
if os.path.exists(f"{SP}/ora_nombres_dup.tsv"):
    for r in csv.DictReader(open(f"{SP}/ora_nombres_dup.tsv", encoding="utf-8", errors="replace"), delimiter="\t"):
        homon.add(norm(f"{r['N']} {r['P']} {r['M']}"))

# ── MidPoint ──
mp_cod, mp_dni = {}, {}
for r in csv.DictReader(open(f"{SP}/mp_hoy.csv", encoding="utf-8")):
    if r["codigo"]: mp_cod[r["codigo"].strip()] = r
    if r["dni"]: mp_dni.setdefault(r["dni"].strip(), r)

# ── Entra ID ──
entra = json.load(open(f"{SP}/entra_hoy.json"))
por_dir, por_lp, por_nom = {}, {}, defaultdict(list)
for u in entra:
    upn = (u.get("upn") or "").lower()
    if "#ext#" in upn: continue
    for d in filter(None, [u.get("mail"), upn] + [p.split(":", 1)[1] for p in (u.get("proxy") or [])]):
        por_dir.setdefault(d.lower().strip(), u)
    por_lp.setdefault(lp(upn), u)
    por_nom[norm(u.get("display"))].append(u)

def buzon(u):
    """Dirección entregable de la cuenta: prioriza una no numérica; si solo hay DNI@, esa (tal cual)."""
    if not u or not u.get("mail"): return ""
    cands = [u.get("mail"), u.get("upn")] + [p.split(":", 1)[1] for p in (u.get("proxy") or []) if p.lower().startswith("smtp:")]
    cands = [c.lower().strip() for c in cands if c and c.lower().strip().endswith("@upeu.edu.pe")]
    real = [c for c in cands if not num(c)]
    return real[0] if real else (u["mail"].lower().strip() if u["mail"].lower().endswith("@upeu.edu.pe") else "")

def nombre_coincide(u, d):
    t = set(norm(u.get("display")).split())
    return bool(set(norm(d["PATERNO"]).split()) & t) and bool(set(norm(d["NOMBRE"]).split()) & t)

def ultimo(u):
    return (max(filter(None, [u.get("lastInteractive"), u.get("lastNonInteractive")]), default="") or "")[:10] if u else ""

# índice por apellidos para detectar cuentas probables (nombre + ambos apellidos en displayName)
por_tok = defaultdict(list)
for u in entra:
    t = set(norm(u.get("display")).split())
    for w in t: por_tok[w].append((u, t))
def probable(d):
    p, m, n = norm(d["PATERNO"]).split(), norm(d["MATERNO"]).split(), norm(d["NOMBRE"]).split()
    if not p or not n: return None
    cs = [u for u, t in por_tok.get(p[-1], []) if set(p) <= t and set(m) <= t and n[0] in t]
    return cs[0] if cs else None

# ── clasificación ──
CARGAR, CONFIRMAR, CREAR, SINBUZON, SINLIC, YA_OK = [], [], [], [], [], 0
uso = Counter()
prop = {}
for k, d in ora.items():
    cur = d["CUR"]
    if cur and cur in por_dir:
        if por_dir[cur].get("mail"):
            YA_OK += 1; continue                               # Oracle ya apunta a un buzón real
        SINLIC.append((d, por_dir[cur], "Oracle ya tiene este correo; la cuenta existe pero sin buzón")); continue
    cod, doc = d["CODIGO"], d["NUM_DOCUMENTO"]
    mp = mp_cod.get(cod) or mp_dni.get(doc) or {}
    mpm = (mp.get("email") or "").lower()
    u, origen, motivo = None, "", ""
    if mpm and not num(mpm) and mpm in por_dir and por_dir[mpm].get("mail"):
        u, origen = por_dir[mpm], "MidPoint, verificado en M365"
    else:
        for key, lab in ((doc, "cuenta hallada por documento"), (cod, "cuenta hallada por código")):
            if key and key in por_lp:
                u, origen = por_lp[key], lab
                break
    if u is None:
        n1, n2 = norm(f'{d["NOMBRE"]} {d["PATERNO"]} {d["MATERNO"]}'), norm(f'{d["NOMBRE"]} {d["PATERNO"]}')
        cs = [x for n in (n1, n2) for x in por_nom.get(n, [])]
        cs = list({x["id"]: x for x in cs}.values())
        if cs and not any(buzon(x) for x in cs):
            SINLIC.append((d, cs[0], f"cuenta hallada por nombre ({len(cs)}), sin buzón: confirmar y licenciar")); continue
        cs = [x for x in cs if buzon(x)]
        if len(cs) == 1:
            u, origen, motivo = cs[0], "nombre exacto en M365", "solo coincide el nombre: confirmar que es su cuenta"
        elif len(cs) > 1:
            CONFIRMAR.append((d, None, "", "—", f"{len(cs)} cuentas con el mismo nombre (homónimos)")); continue
        else:
            CREAR.append(d); continue
    correo = buzon(u)
    if not correo:
        SINLIC.append((d, u, "cuenta hallada por " + ("MidPoint" if origen.startswith("MidPoint") else origen.split(" por ")[-1]) + ", sin buzón")); continue
    if not motivo and origen.startswith("cuenta hallada") and not nombre_coincide(u, d):
        motivo = f"el nombre de la cuenta no coincide: «{u.get('display')}»"
    if not motivo and not u.get("enabled"):
        motivo = "la cuenta está deshabilitada en M365"
    otros = dueno.get(correo, set()) - {k}
    if not motivo and otros:
        motivo = f"ese correo ya es el CORREO_INST de otra ficha en Oracle (ID_PERSONA {', '.join(sorted(otros))})"
    hermanas = [x for x in docdup.get((d["ID_TIPODOCUMENTO"], doc), []) if x["ID_PERSONA"] != k]
    if not motivo and hermanas:
        motivo = "su documento tiene otra ficha en Oracle (ID_PERSONA " + ", ".join(x["ID_PERSONA"] for x in hermanas) + ")"
    if not motivo and d["CUR"] and not num(d["CUR"]) and d["CUR"].endswith("@upeu.edu.pe"):
        motivo = f"Oracle ya tiene «{d['CUR']}», que no existe en M365: decidir si se reemplaza"
    if not motivo and not RX_OK.match(correo):
        motivo = "formato de correo no estándar"
    uso[correo] += 1
    (CONFIRMAR if motivo else CARGAR).append((d, u, correo, origen, motivo))

# un mismo correo propuesto para dos personas → ninguna se carga
dobles = {c for c, n in uso.items() if n > 1}
if dobles:
    mov = [x for x in CARGAR if x[2] in dobles]
    CARGAR = [x for x in CARGAR if x[2] not in dobles]
    CONFIRMAR += [(d, u, c, o, "el mismo correo resultó para 2 personas") for d, u, c, o, _ in mov]

# ── lote 2: coincidencias SOLO por nombre que pasan 6 controles → se cargan sin revisión manual ──
correos_l1 = {x[2] for x in CARGAR}
def controles(d, u, c):
    full = norm(f'{d["NOMBRE"]} {d["PATERNO"]} {d["MATERNO"]}')
    ing = d["CODIGO"][:4]
    hermanas = [x for x in docdup.get((d["ID_TIPODOCUMENTO"], d["NUM_DOCUMENTO"]), []) if x["ID_PERSONA"] != d["ID_PERSONA"]]
    return {
        "nombre completo único en Oracle": bool(homon) and full not in homon,
        "la cuenta lleva nombre y ambos apellidos": set(full.split()) <= set(norm(u.get("display")).split()),
        "correo no es de otra ficha": not (dueno.get(c, set()) - {d["ID_PERSONA"]}),
        "correo no propuesto para otro alumno": c not in correos_l1 and c not in dobles,
        "cuenta habilitada": bool(u.get("enabled")),
        "creada desde el año de ingreso -1": ing.isdigit() and (u.get("created") or "")[:4] >= str(int(ing) - 1),
        "sin otra ficha con su documento": not hermanas,
        "Oracle no trae otro correo con nombre": not (d["CUR"] and not num(d["CUR"]) and d["CUR"].endswith("@upeu.edu.pe")),
    }
CARGAR2, FLOR, LAMB, DAVID = [], [], [], []
for x in CONFIRMAR:
    d, u, c, o, m = x
    if m.startswith("solo coincide el nombre"):
        ck = controles(d, u, c)
        if all(ck.values()):
            CARGAR2.append((d, u, c, "nombre exacto + 6 controles", "")); continue
        FLOR.append((d, u, c, o, m + " — falla: " + ", ".join(k for k, v in ck.items() if not v))); continue
    if m.startswith("ese correo ya es") or m.startswith("su documento tiene otra ficha"):
        LAMB.append(x); continue
    if m.startswith("Oracle ya tiene"):
        DAVID.append(x); continue
    FLOR.append(x)

# ── Excel ──
HDR = ["ID_PERSONA", "ID_TIPODOCUMENTO", "TIPO_DOCUMENTO", "NUM_DOCUMENTO", "CODIGO", "PATERNO", "MATERNO",
       "NOMBRES", "SEDE", "PROGRAMA", "CORREO_INST_ACTUAL_ORACLE"]
def base(d):
    return [int(d["ID_PERSONA"]), d["ID_TIPODOCUMENTO"], TIPOS.get(d["ID_TIPODOCUMENTO"], d["ID_TIPODOCUMENTO"]),
            d["NUM_DOCUMENTO"], d["CODIGO"], d["PATERNO"], d["MATERNO"], d["NOMBRE"], d["SEDE"], d["PROGRAMA"],
            d["CORREO_INST_RAW"]]

H = Font(bold=True, color="FFFFFF"); F = PatternFill("solid", fgColor="1F4E79")
def hoja(wb, nombre, cab, filas, ancho=None):
    ws = wb.create_sheet(nombre)
    ws.append(cab)
    for c in ws[1]: c.font, c.fill, c.alignment = H, F, Alignment(vertical="center", wrap_text=True)
    for f in filas: ws.append(f)
    ws.freeze_panes = "B2"; ws.auto_filter.ref = ws.dimensions
    for i, c in enumerate(cab, 1):
        ws.column_dimensions[get_column_letter(i)].width = (ancho or {}).get(c, max(12, min(38, len(c) + 4)))
    return ws
def leeme(wb, texto):
    ld = wb.active; ld.title = "LEEME"
    for t, b in texto:
        ld.append([t]); ld.cell(ld.max_row, 1).font = Font(bold=b, size=13 if ld.max_row == 1 else 11)
    ld.column_dimensions["A"].width = 120

W = {"PATERNO": 16, "MATERNO": 16, "NOMBRES": 22, "PROGRAMA": 40, "CORREO_A_CARGAR": 34, "CORREO_PROPUESTO": 34,
     "CORREO_INST_ACTUAL_ORACLE": 30, "MOTIVO": 60, "CUENTA_EN_M365": 34, "NOMBRE_EN_M365": 30}
dni_tal = sum(1 for x in CARGAR if num(x[2]))
PRIV = ("Datos personales (Ley 29733): no reenviar por WhatsApp ni dejar en carpetas compartidas abiertas.", False)

# ── Excel 1: lo que se carga en Oracle (va con el UPDATE) ──
wb1 = openpyxl.Workbook()
leeme(wb1, [
    ("Correos a cargar en Oracle (MOISES.PERSONA_NATURAL.CORREO_INST) — pregrado 2026-2", True),
    (f"Generado el {FECHA} con datos leídos hoy de Oracle LAMB, MidPoint y Entra ID (M365).", False),
    ("", False),
    (f"Filas: {len(CARGAR)}. Cada correo existe hoy como buzón en M365 y es de esa persona.", False),
    (f"   {dni_tal} son cuentas DNI@upeu.edu.pe: se informan tal cual (no se cambia el usuario a mitad de ciclo).", False),
    ("Solo se completa lo que falta: CORREO_INST vacío, numérico o con un correo no institucional.", False),
    ("", False),
    ("CÓMO SE CARGA", True),
    ("UPDATE_CORREO_INST_*.sql: un UPDATE por fila de este Excel, con candados:", False),
    ("  • ID_PERSONA + ID_TIPODOCUMENTO + NUM_DOCUMENTO deben coincidir (no escribe en otra ficha).", False),
    ("  • CORREO_INST debe seguir valiendo lo mismo que hoy (no pisa un cambio hecho mientras tanto).", False),
    (f"  • Sin COMMIT: al final un SELECT debe devolver {len(CARGAR)}. Si cuadra, COMMIT; si no, ROLLBACK.", False),
    ("ROLLBACK_CORREO_INST_*.sql: devuelve cada fila a su valor anterior si hiciera falta.", False),
    ("", False), PRIV])
hoja(wb1, "Cargar en Oracle", HDR + ["CORREO_A_CARGAR", "ORIGEN", "CUENTA_HABILITADA", "ULTIMO_ACCESO_M365"],
     [base(d) + [c, o, "Sí" if u.get("enabled") else "No", ultimo(u)] for d, u, c, o, _ in
      sorted(CARGAR, key=lambda x: (x[0]["SEDE"], x[0]["PATERNO"]))], W)
xl = f"{OUT}/Correos_para_cargar_Oracle_pregrado_2026-2_{FECHA}.xlsx"
wb1.save(xl)

# ── Excel 2: casos con conflicto, para revisión de Mesa de Servicios (Flor) ──
def nota_crear(d):
    pc = probable(d); notas = []
    if d["CUR"].endswith("@upeu.edu.pe"): notas.append("Oracle tiene una dirección @upeu que NO existe en M365 (creación fallida o borrada)")
    elif d["CUR"]: notas.append("Oracle tiene un correo no institucional en CORREO_INST")
    if pc: notas.append("POSIBLE CUENTA EXISTENTE: revisar antes de crear")
    return [(pc or {}).get("upn", ""), (pc or {}).get("display", ""), "; ".join(notas)]
wb2 = openpyxl.Workbook()
leeme(wb2, [
    ("Casos por revisar — correo institucional de matriculados de pregrado 2026-2", True),
    (f"Generado el {FECHA}. Ninguno de estos casos se carga en Oracle hasta que se resuelva.", False),
    ("", False),
    ("QUÉ HACER EN CADA HOJA", True),
    (f"«1 Confirmar» ({len(FLOR)}): hay una cuenta candidata pero con una duda (columna MOTIVO).", False),
    ("     Confirmar si la cuenta es de esa persona. Si lo es, se carga en el siguiente envío.", False),
    (f"«2 Sin cuenta» ({len(CREAR)}): no se encontró cuenta en M365 → hay que crearla.", False),
    (f"     ANTES revisar la columna POSIBLE_CUENTA_EN_M365 ({sum(1 for d in CREAR if probable(d))} casos): puede que ya tenga cuenta.", False),
    (f"«3 Sin licencia» ({len(SINLIC)}): la cuenta EXISTE pero no tiene buzón porque no tiene licencia.", False),
    ("     NO crear otra cuenta: basta asignarle la licencia de estudiante.", False),
    ("", False),
    ("Devolver este Excel con una columna de resultado por fila (correo confirmado / crear / licenciar / otro).", False),
    ("", False), PRIV])
hoja(wb2, "1 Confirmar", HDR + ["CORREO_PROPUESTO", "ORIGEN", "NOMBRE_EN_M365", "MOTIVO"],
     [base(d) + [c, o, (u or {}).get("display", ""), m] for d, u, c, o, m in
      sorted(FLOR, key=lambda x: (x[4], x[0]["PATERNO"]))], W)
hoja(wb2, "2 Sin cuenta", HDR + ["POSIBLE_CUENTA_EN_M365", "NOMBRE_EN_M365", "NOTA"],
     [base(d) + nota_crear(d) for d in sorted(CREAR, key=lambda d: (d["SEDE"], d["PATERNO"]))], {**W, "POSIBLE_CUENTA_EN_M365": 32, "NOTA": 60})
hoja(wb2, "3 Sin licencia", HDR + ["CUENTA_EN_M365", "NOMBRE_EN_M365", "CUENTA_HABILITADA", "CREADA", "SITUACION"],
     [base(d) + [u.get("upn"), u.get("display"), "Sí" if u.get("enabled") else "No", (u.get("created") or "")[:10], m]
      for d, u, m in sorted(SINLIC, key=lambda x: (x[2], x[0]["PATERNO"]))], {**W, "SITUACION": 55})
xl2 = f"{OUT}/Correos_por_revisar_pregrado_2026-2_{FECHA}.xlsx"
wb2.save(xl2)

# ── SQL ──
def q(s): return "'" + s.replace("'", "''") + "'"
def guard(cur): return f"NVL(LOWER(TRIM(CORREO_INST)),'#') = {q(cur or '#')}"
def gen_sql(rows, tag, xlname):
    up = [f"-- Carga de CORREO_INST · matriculados de pregrado 2026-2 · {tag} · generado {FECHA}",
          f"-- Filas: {len(rows)} (hoja «Cargar en Oracle» de {xlname})",
          "-- Candados por fila: ID_PERSONA + tipo y número de documento, y CORREO_INST igual al valor leído hoy.",
          "-- NO incluye COMMIT. Al terminar revise el total impreso: si coincide, COMMIT; si no, ROLLBACK.",
          "SET SERVEROUTPUT ON SIZE UNLIMITED", "SET DEFINE OFF", ""]
    rb = [f"-- ROLLBACK de la carga de CORREO_INST ({tag}, {FECHA}): devuelve el valor anterior.",
          "-- Solo revierte filas que sigan teniendo el correo cargado por el script de carga. Sin COMMIT.",
          "SET SERVEROUTPUT ON SIZE UNLIMITED", "SET DEFINE OFF", ""]
    LOTE = 400
    for i in range(0, len(rows), LOTE):
        lote = rows[i:i + LOTE]
        for dst, inv in ((up, False), (rb, True)):
            dst.append("DECLARE n NUMBER := 0; BEGIN")
            for d, u, c, o, _ in lote:
                if not inv:
                    dst.append(f"  UPDATE MOISES.PERSONA_NATURAL SET CORREO_INST = {q(c)} WHERE ID_PERSONA = {int(d['ID_PERSONA'])}"
                               f" AND ID_TIPODOCUMENTO = {int(d['ID_TIPODOCUMENTO'])} AND NUM_DOCUMENTO = {q(d['NUM_DOCUMENTO'])}"
                               f" AND {guard(d['CUR'])}; n := n + SQL%ROWCOUNT;")
                else:
                    prev = "NULL" if not d["CORREO_INST_RAW"] else q(d["CORREO_INST_RAW"])
                    dst.append(f"  UPDATE MOISES.PERSONA_NATURAL SET CORREO_INST = {prev} WHERE ID_PERSONA = {int(d['ID_PERSONA'])}"
                               f" AND LOWER(TRIM(CORREO_INST)) = {q(c)}; n := n + SQL%ROWCOUNT;")
            dst.append(f"  DBMS_OUTPUT.PUT_LINE('bloque {i // LOTE + 1}: ' || n || ' de {len(lote)} filas');")
            dst.append("END;"); dst.append("/"); dst.append("")
    partes = []
    for i in range(0, len(rows), 500):
        tup = ",".join(f"({int(d['ID_PERSONA'])},{q(c)})" for d, u, c, o, _ in rows[i:i + 500])
        partes.append(f"(ID_PERSONA, LOWER(TRIM(CORREO_INST))) IN ({tup})")
    up += ["-- VERIFICACIÓN: debe devolver " + str(len(rows)),
           "SELECT COUNT(*) AS FILAS_CON_CORREO_ESPERADO FROM MOISES.PERSONA_NATURAL WHERE\n   " + "\n OR ".join(partes) + ";",
           "", "-- Si FILAS_CON_CORREO_ESPERADO = " + str(len(rows)) + " → COMMIT;   si no → ROLLBACK;"]
    suf = "" if tag == "lote 1" else "_" + tag.replace(" ", "")
    sq = f"{OUT}/UPDATE_CORREO_INST_pregrado_2026-2{suf}_{FECHA}.sql"
    rq = f"{OUT}/ROLLBACK_CORREO_INST_pregrado_2026-2{suf}_{FECHA}.sql"
    open(sq, "w").write("\n".join(up) + "\n"); open(rq, "w").write("\n".join(rb) + "\n")
    return sq, rq
sq, rq = gen_sql(CARGAR, "lote 1", xl.split("/")[-1])

# lote 2
wb3 = openpyxl.Workbook()
leeme(wb3, [
    ("Correos a cargar en Oracle — LOTE 2 — pregrado 2026-2", True),
    (f"Generado el {FECHA}. Filas: {len(CARGAR2)}.", False),
    ("Casos que solo coincidían por nombre y pasan TODOS estos controles, por lo que no requieren revisión manual:", False),
    ("  • el nombre completo (nombre + 2 apellidos) es único entre todas las personas de Oracle;", False),
    ("  • la cuenta de M365 lleva el nombre y ambos apellidos;  • está habilitada y se creó desde el año de ingreso;", False),
    ("  • el correo no es el CORREO_INST de otra ficha ni se propone para otro alumno;", False),
    ("  • el documento no tiene otra ficha en Oracle y Oracle no trae otro correo con nombre.", False),
    ("Se carga igual que el lote 1: UPDATE_*_lote2.sql (sin COMMIT, con candados) y ROLLBACK_*_lote2.sql.", False),
    ("", False), PRIV])
hoja(wb3, "Cargar en Oracle", HDR + ["CORREO_A_CARGAR", "ORIGEN", "NOMBRE_EN_M365", "CUENTA_HABILITADA", "ULTIMO_ACCESO_M365"],
     [base(d) + [c, o, u.get("display"), "Sí" if u.get("enabled") else "No", ultimo(u)] for d, u, c, o, _ in
      sorted(CARGAR2, key=lambda x: (x[0]["SEDE"], x[0]["PATERNO"]))], W)
xl3 = f"{OUT}/Correos_para_cargar_Oracle_pregrado_2026-2_lote2_{FECHA}.xlsx"
wb3.save(xl3)
sq2, rq2 = gen_sql(CARGAR2, "lote 2", xl3.split("/")[-1])

# pendientes que no son de Mesa de Servicios
wb4 = openpyxl.Workbook()
leeme(wb4, [
    ("Pendientes fuera de Mesa de Servicios — correo institucional pregrado 2026-2", True),
    (f"Generado el {FECHA}.", False),
    (f"«Fichas duplicadas (LAMB)» ({len(LAMB)}): el correo o el documento ya pertenece a OTRA ficha de Oracle.", False),
    ("     Casi seguro es la misma persona con dos ID_PERSONA. Unir las fichas es tarea del equipo LAMB.", False),
    (f"«Decisión reemplazo» ({len(DAVID)}): Oracle tiene un correo con nombre que NO existe en M365.", False),
    ("     Si se aprueba la regla «reemplazar por el buzón verificado», pasan a un lote de carga.", False),
    ("", False), PRIV])
hoja(wb4, "Fichas duplicadas (LAMB)", HDR + ["CORREO_PROPUESTO", "NOMBRE_EN_M365", "MOTIVO"],
     [base(d) + [c, (u or {}).get("display", ""), m] for d, u, c, o, m in LAMB], W)
hoja(wb4, "Decisión reemplazo", HDR + ["CORREO_PROPUESTO", "NOMBRE_EN_M365", "MOTIVO"],
     [base(d) + [c, (u or {}).get("display", ""), m] for d, u, c, o, m in DAVID], W)
xl4 = f"{OUT}/Correos_pendientes_LAMB_y_decision_pregrado_2026-2_{FECHA}.xlsx"
wb4.save(xl4)

print(f"pregrado matriculados: {len(ora)} | Oracle ya OK: {YA_OK}")
print(f"1 cargar: {len(CARGAR)} (DNI@ tal cual: {dni_tal}) | por origen: {dict(Counter(x[3] for x in CARGAR))}")
print(f"2 confirmar: {len(CONFIRMAR)} | motivos: {dict(Counter(re.sub(r'«.*»|\(.*\)', '', x[4]).strip() for x in CONFIRMAR))}")
print(f"3 crear: {len(CREAR)} (posible cuenta: {sum(1 for d in CREAR if probable(d))}, Oracle con @upeu inexistente: {sum(1 for d in CREAR if d['CUR'].endswith('@upeu.edu.pe'))}) | 4 sin licencia: {len(SINLIC)} {dict(Counter(x[2].split(':')[0] for x in SINLIC))} | correos dobles: {len(dobles)}")
print(f"lote 2: {len(CARGAR2)} | Flor confirmar: {len(FLOR)} | LAMB: {len(LAMB)} | decisión: {len(DAVID)}")
print(xl); print(sq); print(rq); print(xl3); print(sq2); print(rq2); print(xl2); print(xl4)
