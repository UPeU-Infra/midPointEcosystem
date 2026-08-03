#!/usr/bin/env python3
"""
Detección de personas con 2+ correos personales @upeu.edu.pe en Entra ID,
segmentada por campus, para revisión manual de DTI.

Mejoras sobre la versión 2026-06-05:
  - Cada cuenta se resuelve a su foco MidPoint (por email exacto, luego por nombre).
  - Si dos cuentas del mismo nombre resuelven a DNIs DISTINTOS -> HOMÓNIMOS, no duplicado.
    (evita que DTI borre el buzón de una persona real; patrón ya confirmado en Koha 26-jul)
  - Campus resuelto por cascada MidPoint -> Entra -> sin dato, con columna de trazabilidad.
"""
import json, csv, re, unicodedata, datetime, sys
from collections import defaultdict

SP = "/private/tmp/claude-501/-Users-alberto-proyectos-productos-iga/4cb5ae8a-606c-44ee-b762-9f9a872a7da2/scratchpad"
TODAY = datetime.datetime.now(datetime.timezone.utc)
USED_DAYS = 90

# ---------- utilidades ----------
def norm(s):
    if not s: return ""
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Za-z0-9 ]', ' ', s).upper()).strip()

def parse_dt(s):
    if not s: return None
    try: return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception: return None

def days_since(s):
    d = parse_dt(s)
    return None if not d else max(0, (TODAY - d).days)

def local(a): return a.split("@")[0] if a and "@" in a else ""

def is_personal_upeu(a):
    """Correo @upeu.edu.pe que no es un placeholder numérico (DNI, código, CE).
    Mismo criterio que el correlator de MidPoint sobre emailAddress: un local-part
    100% numérico no es un correo personal, es un relleno."""
    if not a or not a.lower().endswith("@upeu.edu.pe"): return False
    return not re.match(r'^\d+$', local(a).lower())

def proper_format(a):
    """Formato institucional canónico: nombre.apellido@"""
    return '.' in local(a or "")

FUNC_HINTS = ['noreply','no-reply','biblioteca','gerencia','mesa','soporte','informes','info',
              'admin','sistemas','secretaria','sec','decanato','tesoreria','contabilidad','rrhh',
              'marketing','crai','test','prueba','admision','caja','almacen','logistica',
              'activosfijos','alumno','aula','laboratorio','lab','labuno','labdos','labarqui',
              'clinica','cafeteria','libreria','imprenta','transporte','mantenimiento',
              'seguridad','sst','pastoral','capellania','bienestar','tramite','matricula',
              'facturacion','cobranza','remuneraciones','planillas','presupuesto','auditoria',
              'legal','licencia','recepcion','conmutador','ventas','cobros','egresados',
              'practicas','convenios','calidad','acreditacion','posgrado','postgrado']

SEP = r'[._\-0-9]'
def looks_functional(addr):
    """True si el local-part parece un buzón de área/rol, no una persona.
    Exige que el hint sea una palabra completa dentro del local-part (delimitada por
    separadores o extremos) para no marcar apellidos que contengan la cadena."""
    lp = local(addr or "").lower()
    if not lp: return False
    for h in FUNC_HINTS:
        if re.search(r'(^|%s)%s($|%s)' % (SEP, re.escape(h), SEP), lp):
            return True
    return False

def name_looks_functional(display):
    n = norm(display).lower()
    if not n: return False
    flat = n.replace(" ", "")          # "Activos Fijos Juliaca" -> "activosfijosjuliaca"
    for h in FUNC_HINTS:
        if re.search(r'(^|\s)%s(\s|$)' % re.escape(h), n):
            return True
        # substring solo con hints largos: 'lab'/'sec'/'sst' darían falsos positivos
        # sobre apellidos reales (Labarca, Calabria...)
        if len(h) >= 8 and h in flat:
            return True
    return False

# ---------- carga MidPoint ----------
mp_by_email = {}
mp_by_name  = defaultdict(list)
mp_rows = []
with open(f"{SP}/mp_users.csv", newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        campus = (r['campus_est'] or r['campus_trab'] or '').strip().upper()
        p = {
            "name": r['nameorig'], "dni": r['dni'], "codigo": r['codigo'],
            "given": r['given'], "family": r['family'], "email": (r['email'] or '').lower().strip(),
            "aff": r['aff'], "campus": campus,
            "campus_src": "MidPoint/campusStudent" if r['campus_est'] else ("MidPoint/campusWorker" if r['campus_trab'] else ""),
            "lifecycle": r['lifecyclestate'],
        }
        mp_rows.append(p)
        if p["email"]:
            # preferir foco activo si hay colisión de email
            prev = mp_by_email.get(p["email"])
            if prev is None or (prev["lifecycle"] != "active" and p["lifecycle"] == "active"):
                mp_by_email[p["email"]] = p
        for k in (norm(p["given"] + " " + p["family"]), norm(p["family"] + " " + p["given"])):
            if k: mp_by_name[k].append(p)

print(f"MidPoint: {len(mp_rows)} focos, {len(mp_by_email)} con email, {len(mp_by_name)} claves de nombre", file=sys.stderr)

# ---------- sede de egresados (Oracle LAMB, DAVID.VW_PERSONA_EGRESADO.SEDE) ----------
# MidPoint solo puebla campusStudent/campusWorker para afiliaciones vivas; los egresados
# quedan sin campus. La vista de Oracle sí lo tiene, aunque el resource no lo mapea.
SEDE_MAP = {"SEDE LIMA": "LIMA", "FILIAL JULIACA": "JULIACA", "FILIAL TARAPOTO": "TARAPOTO"}
sede_por_codigo = {}
try:
    with open(f"{SP}/sede_egresados.tsv", encoding='utf-8') as f:
        next(f, None)
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2: continue
            camp = SEDE_MAP.get(norm(parts[1]))
            if camp: sede_por_codigo[parts[0].strip()] = camp
    print(f"Oracle: sede recuperada para {len(sede_por_codigo)} egresados", file=sys.stderr)
except FileNotFoundError:
    print("AVISO: sin sede_egresados.tsv, los egresados quedan sin campus", file=sys.stderr)

# ---------- carga Entra ----------
users = json.load(open(f"{SP}/entra_users.json"))
print(f"Entra: {len(users)} cuentas", file=sys.stderr)

CAMPUS_PATTERNS = [
    ("JULIACA",  [r'\bJULIACA\b', r'\bPUNO\b', r'\bFILIAL JULIACA\b']),
    ("TARAPOTO", [r'\bTARAPOTO\b', r'\bMORALES\b', r'\bSAN MARTIN\b']),
    ("LIMA",     [r'\bLIMA\b', r'\bNANA\b', r'\bCHOSICA\b', r'\bLURIGANCHO\b', r'\bATE\b']),
]

def campus_from_entra(a):
    blob = norm(" ".join(filter(None, [a.get("office"), a.get("city"), a.get("department"),
                                       a.get("street"), a.get("state"), a.get("company"),
                                       a.get("jobTitle")])))
    if not blob: return "", ""
    for camp, pats in CAMPUS_PATTERNS:
        for p in pats:
            if re.search(p, blob):
                return camp, "Entra/atributos"
    return "", ""

def resolve_focus(acc):
    """Devuelve (foco_midpoint|None, como_se_resolvio)."""
    cands = set()
    for addr in filter(None, [acc.get("mail"), acc.get("upn")]):
        cands.add(addr.lower().strip())
    for px in acc.get("proxy") or []:
        px = px.lower().replace("smtp:", "").strip()
        if px: cands.add(px)
    for c in cands:
        if c in mp_by_email:
            return mp_by_email[c], "email exacto"
    hits = mp_by_name.get(norm(acc.get("display")), [])
    uniq = {h["dni"] or h["name"]: h for h in hits}
    if len(uniq) == 1:
        return list(uniq.values())[0], "nombre (único)"
    if len(uniq) > 1:
        return None, "nombre ambiguo (%d focos)" % len(uniq)
    return None, "sin foco"

# ---------- agrupar duales ----------
by_name = defaultdict(list)
for u in users:
    if u.get("enabled"):
        by_name[norm(u.get("display"))].append(u)

grupos = []
for nm, accs in by_name.items():
    if not nm: continue
    pers, seen = [], set()
    for a in accs:
        addr = a.get("mail") or a.get("upn")
        if not is_personal_upeu(addr): continue
        up = (a.get("upn") or "").lower()
        if up in seen: continue
        seen.add(up); pers.append(a)
    if len(pers) < 2: continue

    for a in pers:
        a["_d"] = days_since(a.get("lastInteractive"))
        a["_dn"] = days_since(a.get("lastNonInteractive"))
        foco, how = resolve_focus(a)
        a["_foco"] = foco; a["_how"] = how

    ranked = sorted(pers, key=lambda a: (a["_d"] if a["_d"] is not None else 99999))
    used = [a for a in ranked if a["_d"] is not None and a["_d"] <= USED_DAYS]

    focos = {a["_foco"]["dni"] or a["_foco"]["name"]: a["_foco"] for a in ranked if a["_foco"]}
    con_foco = [a for a in ranked if a["_foco"]]

    # ----- cuentas de área mezcladas dentro del grupo -----
    # Un buzón de rol suele llevar como displayName el nombre de quien lo administra,
    # así que cae en el mismo grupo que su correo personal. Nunca debe proponerse para
    # borrado: borrarlo deja sin buzón a un área entera.
    func_accs = [a for a in ranked if looks_functional(a.get("upn") or a.get("mail"))]
    n_func = len(func_accs)

    # ----- clasificación de la NATURALEZA del grupo -----
    if len(ranked) >= 5 and not focos:
        naturaleza = "POOL"          # pools de licencias/laboratorio (labuno.NN@, lab1.N@)
    elif len(focos) >= 2:
        naturaleza = "HOMONIMOS"
    elif len(focos) == 1:
        naturaleza = "MIXTO_FUNCIONAL" if (n_func or name_looks_functional(nm)) else "PERSONA"
    else:
        naturaleza = "FUNCIONAL" if (n_func or name_looks_functional(nm)) else "SIN_IDENTIDAD"

    # ----- campus -----
    campus, csrc = "", ""
    for a in ranked:
        if a["_foco"] and a["_foco"]["campus"]:
            campus, csrc = a["_foco"]["campus"], a["_foco"]["campus_src"]; break
    if not campus:
        for a in ranked:
            cod = a["_foco"]["codigo"] if a["_foco"] else None
            if cod and cod in sede_por_codigo:
                campus, csrc = sede_por_codigo[cod], "Oracle LAMB/SEDE egresado"; break
    if not campus:
        for a in ranked:
            c, s = campus_from_entra(a)
            if c: campus, csrc = c, s; break

    # ----- veredicto -----
    if naturaleza == "POOL":
        veredicto = "REVISAR (pool de cuentas)"
        keeper = None
        accion = ("%d cuentas con el mismo nombre para mostrar y patrón secuencial: es un POOL "
                  "(licencias de software / puestos de laboratorio), no una persona con correos "
                  "duplicados. No aplica consolidar. Verificar con el área dueña si el pool sigue "
                  "vigente." % len(ranked))
    elif naturaleza == "MIXTO_FUNCIONAL":
        veredicto = "REVISAR — buzón de área mezclado"
        keeper = None
        if n_func:
            accion = ("⚠ NO BORRAR SIN VERIFICAR. El grupo mezcla el correo personal con %d buzón(es) "
                      "de área/rol (%s) que llevan el nombre de la persona como displayName. Borrar la "
                      "cuenta «sin uso» puede dejar sin buzón a un área. Acción: cambiar el displayName "
                      "del buzón funcional por el nombre del área, y tratar el correo personal aparte."
                      % (n_func, ", ".join(a.get("upn") for a in func_accs)))
        else:
            accion = ("⚠ NO BORRAR SIN VERIFICAR. El nombre para mostrar del grupo («%s») es el de un "
                      "área, no el de una persona, aunque una de las cuentas esté vinculada a un foco "
                      "de MidPoint. Verificar si son cuentas de área con nombre de persona asignado o "
                      "al revés, antes de tocar nada." % nm.title())
    elif naturaleza == "HOMONIMOS":
        veredicto = "NO FUSIONAR — personas distintas"
        accion = ("Mismo nombre, %d identidades DISTINTAS en MidPoint (%s). NO borrar ninguna cuenta: "
                  "cada correo pertenece a una persona diferente. Verificar que el nombre para mostrar "
                  "permita distinguirlas." % (len(focos), ", ".join("DNI " + (d or "s/d") for d in focos)))
        if n_func:
            accion += (" Además, %s tiene forma de buzón de área/rol: es posible que no sean dos "
                       "homónimos sino una persona más un buzón funcional que lleva su nombre como "
                       "displayName. En ambos casos la acción es la misma: no borrar."
                       % ", ".join(a.get("upn") for a in func_accs))
        keeper = None
    elif len(used) >= 2:
        veredicto = "CONSOLIDAR (ambas en uso)"
        keeper = next((a for a in used if proper_format(a.get("upn"))), used[0])
        accion = ("Migrar buzón a %s (formato nombre.apellido). Las demás quedan como ALIAS de esa "
                  "cuenta. Conservar 1 sola." % keeper.get("upn"))
    elif len(used) == 1:
        veredicto = "BORRAR no usada"
        keeper = used[0]
        losers = [a for a in ranked if a is not keeper]
        fmt = "" if proper_format(keeper.get("upn")) else " OJO: la cuenta en uso NO tiene formato nombre.apellido → renombrar."
        accion = ("Conservar %s (única con login interactivo <%dd). Borrar: %s." %
                  (keeper.get("upn"), USED_DAYS, ", ".join(a.get("upn") for a in losers)) + fmt)
        # tokens vivos: sin login interactivo, pero una app/dispositivo sigue autenticándose
        vivos = [a for a in losers if a["_dn"] is not None and a["_dn"] <= 30]
        if vivos:
            veredicto = "BORRAR — con tokens vivos"
            accion += (" ⚠ ANTES DE BORRAR: %s tiene actividad NO-interactiva de hace %d día(s) — "
                       "hay un dispositivo o aplicación todavía conectado con esa cuenta (correo en "
                       "el móvil, Outlook, un servicio). Borrarla lo rompe sin aviso. Avisar a la "
                       "persona y revisar qué app la usa antes de eliminar."
                       % (", ".join(a.get("upn") for a in vivos), min(a["_dn"] for a in vivos)))
    else:
        veredicto = "REVISAR (ninguna en uso reciente)"
        keeper = next((a for a in ranked if proper_format(a.get("upn"))), ranked[0])
        accion = ("Ninguna cuenta con login interactivo en %dd. Contactar a la persona antes de borrar; "
                  "tentativamente conservar %s (formato correcto)." % (USED_DAYS, keeper.get("upn")))

    foco0 = con_foco[0]["_foco"] if con_foco else None
    grupos.append({
        "nombre": nm.title(),
        "dni": foco0["dni"] if foco0 else "",
        "codigo": foco0["codigo"] if foco0 else "",
        "aff": foco0["aff"] if foco0 else "",
        "lifecycle": foco0["lifecycle"] if foco0 else "",
        "campus": campus, "campus_src": csrc,
        "naturaleza": naturaleza, "veredicto": veredicto, "accion": accion,
        "keeper": keeper.get("upn") if keeper else "",
        "cuentas": ranked,
        "n_focos": len(focos),
    })

json.dump([{k: v for k, v in g.items() if k != "cuentas"} | {
    "cuentas": [{"upn": a.get("upn"), "mail": a.get("mail"), "d": a["_d"], "dn": a["_dn"],
                 "li": a.get("lastInteractive"), "lni": a.get("lastNonInteractive"),
                 "how": a["_how"], "created": a.get("created"),
                 "office": a.get("office"), "dept": a.get("department"), "city": a.get("city"),
                 "job": a.get("jobTitle")} for a in g["cuentas"]]
} for g in grupos], open(f"{SP}/grupos.json", "w"), ensure_ascii=False)

# ---------- diagnóstico ----------
from collections import Counter
print("\n=== TOTAL GRUPOS:", len(grupos), "===")
print("\nPor naturaleza:", dict(Counter(g["naturaleza"] for g in grupos)))
print("\nPor campus:", dict(Counter(g["campus"] or "(sin campus)" for g in grupos)))
print("\nPor veredicto:", dict(Counter(g["veredicto"] for g in grupos)))
print("\nCampus x naturaleza:")
for k, v in sorted(Counter((g["campus"] or "SIN", g["naturaleza"]) for g in grupos).items()):
    print("  ", k, v)
print("\nFuente del campus:", dict(Counter(g["campus_src"] or "(ninguna)" for g in grupos)))
