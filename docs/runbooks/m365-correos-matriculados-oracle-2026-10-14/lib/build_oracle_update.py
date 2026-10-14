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
    (f"«1 Confirmar» ({len(CONFIRMAR)}): hay una cuenta candidata pero con una duda (columna MOTIVO).", False),
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
      sorted(CONFIRMAR, key=lambda x: (x[4], x[0]["PATERNO"]))], W)
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
up = [f"-- Carga de CORREO_INST · matriculados de pregrado 2026-2 · generado {FECHA}",
      f"-- Filas: {len(CARGAR)} (hoja «Cargar en Oracle» de {xl.split('/')[-1]})",
      "-- Candados por fila: ID_PERSONA + tipo y número de documento, y CORREO_INST igual al valor leído hoy.",
      "-- NO incluye COMMIT. Al terminar revise el total impreso: si coincide, COMMIT; si no, ROLLBACK.",
      "SET SERVEROUTPUT ON SIZE UNLIMITED", "SET DEFINE OFF", ""]
rb = [f"-- ROLLBACK de la carga de CORREO_INST del {FECHA}: devuelve el valor anterior.",
      "-- Solo revierte filas que sigan teniendo el correo cargado por el script de carga. Sin COMMIT.",
      "SET SERVEROUTPUT ON SIZE UNLIMITED", "SET DEFINE OFF", ""]
LOTE = 400
for i in range(0, len(CARGAR), LOTE):
    lote = CARGAR[i:i + LOTE]
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
        dst.append(f"  DBMS_OUTPUT.PUT_LINE('lote {i // LOTE + 1}: ' || n || ' de {len(lote)} filas');")
        dst.append("END;"); dst.append("/"); dst.append("")
# verificación final: cuántas fichas del listado tienen ya el correo esperado
ver = ["-- VERIFICACIÓN: debe devolver " + str(len(CARGAR))]
partes = []
for i in range(0, len(CARGAR), 500):
    tup = ",".join(f"({int(d['ID_PERSONA'])},{q(c)})" for d, u, c, o, _ in CARGAR[i:i + 500])
    partes.append(f"(ID_PERSONA, LOWER(TRIM(CORREO_INST))) IN ({tup})")
ver.append("SELECT COUNT(*) AS FILAS_CON_CORREO_ESPERADO FROM MOISES.PERSONA_NATURAL WHERE\n   " + "\n OR ".join(partes) + ";")
up += ver + ["", "-- Si FILAS_CON_CORREO_ESPERADO = " + str(len(CARGAR)) + " → COMMIT;   si no → ROLLBACK;"]
sq = f"{OUT}/UPDATE_CORREO_INST_pregrado_2026-2_{FECHA}.sql"
rq = f"{OUT}/ROLLBACK_CORREO_INST_pregrado_2026-2_{FECHA}.sql"
open(sq, "w").write("\n".join(up) + "\n")
open(rq, "w").write("\n".join(rb) + "\n")

print(f"pregrado matriculados: {len(ora)} | Oracle ya OK: {YA_OK}")
print(f"1 cargar: {len(CARGAR)} (DNI@ tal cual: {dni_tal}) | por origen: {dict(Counter(x[3] for x in CARGAR))}")
print(f"2 confirmar: {len(CONFIRMAR)} | motivos: {dict(Counter(re.sub(r'«.*»|\(.*\)', '', x[4]).strip() for x in CONFIRMAR))}")
print(f"3 crear: {len(CREAR)} (posible cuenta: {sum(1 for d in CREAR if probable(d))}, Oracle con @upeu inexistente: {sum(1 for d in CREAR if d['CUR'].endswith('@upeu.edu.pe'))}) | 4 sin licencia: {len(SINLIC)} {dict(Counter(x[2].split(':')[0] for x in SINLIC))} | correos dobles: {len(dobles)}")
print(xl); print(xl2); print(sq); print(rq)
