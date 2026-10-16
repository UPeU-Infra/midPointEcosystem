#!/usr/bin/env python3
"""
Enriquece en M365 las cuentas de estudiantes cuya pareja persona↔cuenta quedó COMPROBADA en el trabajo de correos
del 14-16 oct (lotes 1-3 de Oracle, cuentas creadas, existentes confirmadas y duplicados resueltos). Mismo diseño de
atributos que el canario de MidPoint del 15-oct (docs/runbooks/entra-enriquecimiento-estudiantes-2026-10-15), con los
datos de MidPoint (campus y escuela ya corregidos, v205 + lookup v9), escrito directo por Graph porque MidPoint aún no
correlaciona estas cuentas (UPN = DNI, shadows sin enlazar).

  python3 enriquecer_m365.py simular                       # SOLO LECTURA (MidPoint + Graph)
  python3 enriquecer_m365.py ejecutar <plan_enriq_*.json> [--limite N]

Escribe: employeeId (= ID_PERSONA), givenName, surname (formato Título; si Entra ya tiene el mismo nombre con más
tildes, se conserva), employeeType «Estudiante», jobTitle según nivel, department «EP <escuela>» (solo con una única
EP), officeLocation/city según campus, country «Perú», companyName, usageLocation PE solo si está vacío.
NO toca UPN, mail, alias, displayName, contraseña, accountEnabled ni licencias. Nunca DNI ni datos de contacto.
Se SALTA a la persona si: no está en MidPoint o tiene 2+ usuarios con su ID; no es estudiante o su afiliación principal
es de trabajador (faculty/staff/employee); la cuenta tiene un employeeId de OTRA persona; la cuenta está deshabilitada.
Antes y después quedan en ~/backups/entra-snapshots/ (600). Reversión: los valores «antes» del plan.
"""
import json, os, re, sys, glob, time, datetime, subprocess, unicodedata, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crear_cuentas as cc
log, graph, HOME, OUTD, DOM = cc.log, cc.graph, cc.HOME, cc.OUTD, cc.DOM
SEL = "id,userPrincipalName,accountEnabled,givenName,surname,employeeId,employeeType,jobTitle,department,officeLocation,city,country,companyName,usageLocation"
ATR = ["employeeId", "givenName", "surname", "employeeType", "jobTitle", "department", "officeLocation", "city", "country", "companyName", "usageLocation"]
AP = "9f3b8e2a-4c7d-4b1e-a8f5-6d2c4e9a1b73"   # archetype Academic-Program (EP-*)
LOW = {"de", "del", "la", "las", "los", "y", "e", "da", "das", "do", "dos", "van", "von"}
OFF = {"LIMA": ("Sede Lima", "Lima"), "JULIACA": ("Filial Juliaca", "Juliaca"), "TARAPOTO": ("Filial Tarapoto", "Tarapoto")}
NIV = {"pregrado": "Estudiante de pregrado", "posgrado": "Estudiante de posgrado", "doctorado": "Estudiante de doctorado",
       "segunda especialidad": "Estudiante de segunda especialidad", "idiomas": "Estudiante de idiomas", "cepre": "Estudiante de CEPRE"}

def title(s):
    s = re.sub(r"[\s,;.]+$", "", re.sub(r"^[\s,;.]+", "", s or ""))   # MidPoint trae a veces «Bances Zamora,»
    if not s: return None
    return " ".join(w if i and w in LOW else "-".join(p[:1].upper() + p[1:] for p in w.split("-")) for i, w in enumerate(re.split(r"\s+", s.lower())))
def noacc(s): return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower()
def ntildes(s): return sum(1 for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) == "Mn")

def pares():
    """ID_PERSONA → dirección de la cuenta, de todos los entregables comprobados (SQL de Oracle y cuentas creadas vivas)."""
    P, origen = {}, {}
    for f, tag in [("UPDATE_CORREO_INST_pregrado_2026-2_2026-10-14.sql", "lote 1"), ("UPDATE_CORREO_INST_pregrado_2026-2_lote2_2026-10-14.sql", "lote 2"),
                   ("UPDATE_CORREO_INST_pregrado_2026-2_lote3_2026-10-15.sql", "lote 3"),
                   ("UPDATE_CORREO_INST_cuentas_existentes_confirmadas_2026-10-15_2147.sql", "existente confirmada"),
                   ("UPDATE_CORREO_INST_cuentas_duplicadas_resueltas_2026-10-15_2310.sql", "duplicado resuelto")]:
        p = os.path.join(OUTD, f)
        if not os.path.exists(p): sys.exit(f"✗ falta {p}")
        for c, k in re.findall(r"SET CORREO_INST = '([^']+)' WHERE ID_PERSONA = (\d+)", open(p).read()):
            P[k] = c.lower(); origen[k] = tag
    for f in sorted(glob.glob(os.path.join(HOME, "backups/entra-snapshots/creacion_resultado_*.json"))):
        for x in json.load(open(f))["hechos"]:
            if x.get("id"): P.setdefault(x["ID_PERSONA"], "id:" + x["id"]); origen.setdefault(x["ID_PERSONA"], "creada 15-oct")
    return P, origen

def midpoint(ids):
    env = cc.envfile(os.path.join(HOME, ".secrets/midpoint-upeu.env"))
    lista = ",".join("'" + i + "'" for i in ids)
    sql = (f"SELECT u.ext->>'179', u.nameorig, u.givennameorig, u.familynameorig, u.ext->>'110', u.ext->>'219', u.ext->>'78', u.ext->>'100', "
           f"(SELECT string_agg(o.displaynameorig,'#') FROM m_ref_object_parent_org r JOIN m_org o ON o.oid=r.targetoid WHERE r.owneroid=u.oid "
           f"AND EXISTS (SELECT 1 FROM m_ref_archetype a WHERE a.owneroid=o.oid AND a.targetoid='{AP}')) "
           f"FROM m_user u WHERE u.ext->>'179' IN ({lista});")
    r = subprocess.run(["sshpass", "-e", "ssh", "-o", "StrictHostKeyChecking=no", "-o", "NumberOfPasswordPrompts=1", "midpoint-prod",
                        "docker exec -i midpoint-midpoint_data-1 psql -U midpoint midpoint -At -F'|'"],
                       input=sql, env={**os.environ, "SSHPASS": env["MIDPOINT_PROD_PASS"]}, capture_output=True, text=True, timeout=600)
    if r.returncode: sys.exit(f"✗ MidPoint: {r.stderr[-300:]}")
    M = {}
    for l in r.stdout.splitlines():
        a = l.split("|")
        if len(a) == 9: M.setdefault(a[0], []).append(a)
    return M

def leer(refs):
    """GET por lotes de 20 ($batch). refs = UPN o id."""
    out = {}
    for i in range(0, len(refs), 20):
        req = [{"id": str(n), "method": "GET", "url": f"/users/{r}?$select={SEL}"} for n, r in enumerate(refs[i:i + 20])]
        for intento in range(5):
            st, j = graph("POST", "https://graph.microsoft.com/v1.0/$batch", {"requests": req})
            if st == 200: break
            time.sleep(5)
        pend = []
        for x in (j or {}).get("responses", []):
            r = refs[i + int(x["id"])]
            if x["status"] == 200: out[r] = x["body"]
            elif x["status"] == 429: pend.append(r)
            else: out[r] = {"_error": x["status"]}
        for r in pend:   # reintento uno a uno
            st, b = graph("GET", f"/users/{r}?$select={SEL}"); out[r] = b if st == 200 else {"_error": st}
        for r in [r for r in refs[i:i + 20] if out.get(r, {}).get("_error") == 404 and "@" in r]:   # dirección que es alias, no UPN
            st, b = graph("GET", f"/users?$count=true&$select={SEL}&$filter=" + urllib.parse.quote(
                f"mail eq '{r}' or proxyAddresses/any(x:x eq 'smtp:{r}')"), eventual=True)
            if st == 200 and len(b["value"]) == 1: out[r] = b["value"][0]
        if i % 1000 == 0: log(f"  leídas {min(i + 20, len(refs))}/{len(refs)}")
    return out

def deseado(m, cur):
    _, cod, gn, fn, lvl, camp, pa, affs, eps = m
    off = OFF.get((camp or "").upper(), (None, None))
    names = {re.sub(r"\s*\([^)]*\)\s*$", "", e).strip() for e in (eps or "").split("#") if e}
    dep = None
    if len(names) == 1:
        d = names.pop(); dep = d if d.startswith("EP ") else "EP " + d
    w = {"employeeId": m[0], "givenName": title(gn), "surname": title(fn), "employeeType": "Estudiante",
         "jobTitle": NIV.get((lvl or "").strip().lower().replace("-", " "), "Estudiante"), "department": dep,
         "officeLocation": off[0], "city": off[1], "country": "Perú", "companyName": "Universidad Peruana Unión",
         "usageLocation": None if cur.get("usageLocation") else "PE"}
    for a in ("givenName", "surname"):   # conservar la grafía de Entra si solo difiere en tildes a su favor / mayúsculas iguales
        c = cur.get(a)
        if w[a] and c and noacc(c) == noacc(w[a]) and (ntildes(c) > ntildes(w[a]) or c == w[a]): w[a] = c
    return {a: v for a, v in w.items() if v is not None and v != cur.get(a)}

def simular():
    P, origen = pares()
    log(f"parejas persona↔cuenta comprobadas: {len(P)} · leyendo MidPoint…")
    M = midpoint(list(P))
    log(f"  MidPoint: {len(M)} con usuario · leyendo {len(P)} cuentas en Graph…")
    refs = {k: (v[3:] if v.startswith("id:") else v) for k, v in P.items()}
    G = leer(list(refs.values()))
    plan, salt = [], []
    from collections import Counter
    for k, r in refs.items():
        cur = G.get(r) or {"_error": "?"}
        if "_error" in cur: salt.append((k, r, f"Graph {cur['_error']}")); continue
        ms = M.get(k, [])
        if len(ms) != 1: salt.append((k, r, f"{len(ms)} usuarios en MidPoint con ese ID")); continue
        m = ms[0]
        affs = json.loads(m[7]) if m[7] else []
        if "student" not in affs: salt.append((k, r, f"no es estudiante en MidPoint {affs}")); continue
        if m[6] in ("faculty", "staff", "employee"): salt.append((k, r, f"afiliación principal {m[6]} (doble con trabajador)")); continue
        if cur.get("employeeId") and str(cur["employeeId"]) != k: salt.append((k, r, f"employeeId de otra persona ({cur['employeeId']})")); continue
        if not cur.get("accountEnabled"): salt.append((k, r, "cuenta deshabilitada")); continue
        d = deseado(m, cur)
        if d: plan.append({"ID_PERSONA": k, "codigo": m[1], "origen": origen[k], "id": cur["id"], "upn": cur["userPrincipalName"],
                           "antes": {a: cur.get(a) for a in d}, "cambios": d})
    fecha = datetime.date.today().isoformat()
    pj = os.path.join(HOME, f"backups/entra-snapshots/plan_enriq_{fecha}.json")
    json.dump(plan, open(pj, "w"), ensure_ascii=False, indent=1); os.chmod(pj, 0o600)
    sj = os.path.join(HOME, f"backups/entra-snapshots/enriq_saltados_{fecha}.json")
    json.dump(salt, open(sj, "w"), ensure_ascii=False, indent=1); os.chmod(sj, 0o600)
    por = Counter(a for q in plan for a in q["cambios"])
    sobre = Counter(a for q in plan for a, v in q["antes"].items() if v not in (None, ""))
    log(f"\nCON CAMBIOS: {len(plan)} de {len(P)} · sin nada que cambiar: {len(P) - len(plan) - len(salt)} · SALTADOS: {len(salt)}")
    log(f"por origen: {dict(Counter(q['origen'] for q in plan))}")
    log("por atributo (cambia / de ellos SOBRESCRIBE un valor existente):")
    for a in ATR: log(f"  {a:15s} {por.get(a, 0):5d} / {sobre.get(a, 0)}")
    log(f"saltados: {dict(Counter(re.sub(r' [\\[(].*', '', s[2]) for s in salt))}")
    log(f"Plan: {pj}\nSaltados: {sj}")

def ejecutar(pj, limite):
    plan = json.load(open(pj))[: limite or None]
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    hechos, err = [], []
    for i in range(0, len(plan), 20):
        lote = plan[i:i + 20]
        req = [{"id": str(n), "method": "PATCH", "url": f"/users/{q['id']}", "headers": {"Content-Type": "application/json"}, "body": q["cambios"]}
               for n, q in enumerate(lote)]
        st, j = graph("POST", "https://graph.microsoft.com/v1.0/$batch", {"requests": req})
        res = {int(x["id"]): x for x in (j or {}).get("responses", [])} if st == 200 else {}
        for n, q in enumerate(lote):
            x = res.get(n)
            if x and x["status"] in (200, 204): hechos.append(q); continue
            if x and x["status"] == 429 or not x:   # reintento individual
                s2, r2 = graph("PATCH", f"/users/{q['id']}", q["cambios"])
                if s2 in (200, 204): hechos.append(q); continue
                err.append((q["ID_PERSONA"], q["upn"], f"{s2} {str(r2)[:150]}")); continue
            err.append((q["ID_PERSONA"], q["upn"], f"{x['status']} {str(x.get('body'))[:150]}"))
        log(f"  {min(i + 20, len(plan))}/{len(plan)} · ok {len(hechos)} · errores {len(err)}")
    time.sleep(20)
    # verificación: releer y comparar
    G = leer([q["id"] for q in hechos]); mal = []
    for q in hechos:
        cur = G.get(q["id"], {})
        dif = {a: (cur.get(a), v) for a, v in q["cambios"].items() if cur.get(a) != v}
        if dif: mal.append((q["upn"], dif))
    out = os.path.join(HOME, f"backups/entra-snapshots/enriq_resultado_{stamp}.json")
    json.dump({"hechos": hechos, "errores": err, "no_reflejado": mal}, open(out, "w"), ensure_ascii=False, indent=1); os.chmod(out, 0o600)
    log(f"\nENRIQUECIDAS: {len(hechos)} · errores: {len(err)} · no reflejado al releer: {len(mal)}")
    for e in err[:10]: log("  ERR", *e)
    for m in mal[:10]: log("  ≠", *m)
    log(f"resultado: {out}")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("simular", "ejecutar"): sys.exit(__doc__)
    if sys.argv[1] == "simular": simular()
    else:
        lim = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 0
        ejecutar(sys.argv[2], lim)
