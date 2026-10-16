#!/usr/bin/env python3
"""
Corrige las cuentas que crear_cuentas.py creó con el USUARIO LAMB del alumno cuando ese usuario NO sigue la
nomenclatura UPeU (p. ej. «kewincharca», «deivis.c.quispe», «gmba2005»). Regla del 15-oct (Alberto): una
dirección sin el formato nombre.apellido[NN|NNN] no se toma en cuenta → la cuenta va por la regla oficial y
Oracle se actualiza.

  python3 renombrar_formato.py simular                          # SOLO LECTURA
  python3 renombrar_formato.py ejecutar <plan_renombrar_*.json> [--limite N]

simular: toma de ~/backups/entra-snapshots/creacion_resultado_*.json las cuentas «creada» cuyo UPN no cumple el
formato, calcula la dirección por la regla (base, +2, +3 dígitos del código) contra lo ocupado en el tenant
(activos y borrados), los usuarios LAMB y el CORREO_INST de Oracle de OTRAS personas, y lee si la cuenta ya se usó
(signInActivity). Deja el plan en ~/backups/entra-snapshots/ y un Excel en ~/Downloads.

ejecutar: por cada cuenta vuelve a comprobar EN VIVO que la dirección nueva está libre, cambia userPrincipalName
y mailNickname, espera a Exchange y comprueba que la dirección principal (mail) cambió. La dirección vieja queda
como alias (no se reasigna nunca). Genera el SQL de CORREO_INST para Oracle: el candado acepta el valor que
Oracle tenía al crear la cuenta O el usuario LAMB (por si ya se cargó el SQL anterior). Sin COMMIT.
Reversión: PATCH userPrincipalName a la dirección vieja (sigue siendo alias de la misma cuenta).
"""
import json, os, re, sys, glob, time, datetime, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crear_cuentas as cc      # utilidades (token, graph, ocupadas); su main no corre al importar
log, graph, lp, slug, tokens, HOME, OUTD, DOM = cc.log, cc.graph, cc.lp, cc.slug, cc.tokens, cc.HOME, cc.OUTD, cc.DOM
FORMATO = re.compile(r"^[a-z]+\.[a-z]+\d{0,3}$")
import urllib.parse

def afectadas():
    d = {}
    for f in sorted(glob.glob(os.path.join(HOME, "backups/entra-snapshots/creacion_resultado_*.json"))):
        for x in json.load(open(f))["hechos"]:
            if x.get("estado") == "creada" and x.get("id") and not FORMATO.match(lp(x["upn"])):
                d[x["ID_PERSONA"]] = x
    return list(d.values())

def simular():
    A = afectadas()
    log(f"cuentas creadas fuera del formato UPeU: {len(A)} · leyendo direcciones ocupadas (~3 min)…")
    occ = cc.direcciones_ocupadas()
    lamb = cc.usuarios_lamb(); lamb_dueno = {}
    for idp, u in lamb.items(): lamb_dueno.setdefault(u, set()).add(idp)
    ora_dueno = {}
    for rr in csv.DictReader(open(os.path.join(HOME, ".cache/upeu-correos-oracle/ora_correo_inst_hoy.tsv"), encoding="utf-8", errors="replace"), delimiter="\t"):
        c = (rr.get("CORREO_INST") or "").strip().lower()
        if c.endswith("@" + DOM): ora_dueno.setdefault(lp(c), set()).add(rr["ID_PERSONA"].strip())
    plan, ret = [], []
    for x in A:
        n, p = tokens(x["NOMBRES"]), tokens(x["PATERNO"])
        if len(p) > 1: ret.append((x, f"apellido paterno compuesto «{x['PATERNO']}»: regla pendiente del anexo")); continue
        base = f"{slug(n[0])}.{slug(p[0])}"; cod = re.sub(r"\D", "", x["CODIGO"])
        ajeno = lambda c: bool((lamb_dueno.get(c, set()) | ora_dueno.get(c, set())) - {x["ID_PERSONA"]})
        nuevo = regla = None
        for cand, rg in ((base, "regla: base"), (base + cod[-2:], "regla: +2 dígitos"), (base + cod[-3:], "regla: +3 dígitos")):
            if cand not in occ and not ajeno(cand): nuevo, regla = cand, rg; break
        if not nuevo: ret.append((x, f"{base}, +2 y +3 ocupados: decisión manual")); continue
        occ.add(nuevo)
        st, u = graph("GET", f"/users/{x['id']}?$select=id,userPrincipalName,mail,proxyAddresses,signInActivity,createdDateTime")
        uso = "no verificable"
        if st == 200:
            last = (u.get("signInActivity") or {}).get("lastSignInDateTime") or (u.get("signInActivity") or {}).get("lastNonInteractiveSignInDateTime")
            uso = f"YA ENTRÓ ({last})" if last else "sin inicios de sesión"
        plan.append({**{k: x[k] for k in ("ID_PERSONA", "CODIGO", "ID_TIPODOCUMENTO", "NUM_DOCUMENTO", "NOMBRES", "PATERNO", "MATERNO",
                                          "SEDE", "PROGRAMA", "CORREO_INST_ACTUAL_ORACLE", "usuario_lamb", "id")},
                     "upn_viejo": x["upn"].lower(), "upn_nuevo": f"{nuevo}@{DOM}", "regla": regla, "uso": uso})
        time.sleep(0.3)
    fecha = datetime.date.today().isoformat()
    pj = os.path.join(HOME, f"backups/entra-snapshots/plan_renombrar_{fecha}.json")
    json.dump(plan, open(pj, "w"), ensure_ascii=False, indent=1); os.chmod(pj, 0o600)
    import openpyxl as ox
    wb = ox.Workbook(); ws = wb.active; ws.title = "Se renombrarían"
    ws.append(["ID_PERSONA", "CODIGO", "NOMBRES", "PATERNO", "MATERNO", "SEDE", "CUENTA_ACTUAL", "CUENTA_NUEVA", "REGLA", "USO"])
    for q in plan: ws.append([q["ID_PERSONA"], q["CODIGO"], q["NOMBRES"], q["PATERNO"], q["MATERNO"], q["SEDE"], q["upn_viejo"], q["upn_nuevo"], q["regla"], q["uso"]])
    ws2 = wb.create_sheet("Retenidos"); ws2.append(["ID_PERSONA", "CODIGO", "CUENTA_ACTUAL", "MOTIVO"])
    for x, m in ret: ws2.append([x["ID_PERSONA"], x["CODIGO"], x["upn"], m])
    xo = os.path.join(OUTD, f"Simulacion_renombrar_formato_{fecha}.xlsx"); wb.save(xo)
    from collections import Counter
    log(f"\nSE RENOMBRARÍAN: {len(plan)} {dict(Counter(q['regla'] for q in plan))}")
    log(f"uso: {dict(Counter(q['uso'].split(' (')[0] for q in plan))}")
    log(f"RETENIDOS: {len(ret)}")
    for q in plan: log(f"  {q['upn_viejo']:40s} → {q['upn_nuevo']:35s} {q['uso']}")
    log(f"Excel: {xo}\nPlan: {pj}")

def ejecutar(pj, limite):
    plan = json.load(open(pj))[: limite or None]
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    hechos, err = [], []
    for i, q in enumerate(plan, 1):
        st, u = graph("GET", f"/users/{q['id']}?$select=id,userPrincipalName,mail")
        if st != 200: err.append((q["CODIGO"], q["upn_viejo"], f"lectura {st}")); continue
        if u["userPrincipalName"].lower() == q["upn_nuevo"]:
            log(f"  ya renombrada {q['upn_nuevo']}"); hechos.append({**q, "estado": "ya estaba"}); continue
        a = q["upn_nuevo"]
        st, j = graph("GET", "/users?$count=true&$select=id&$filter=" + urllib.parse.quote(
            f"userPrincipalName eq '{a}' or mail eq '{a}' or proxyAddresses/any(x:x eq 'smtp:{a}')"), eventual=True)
        if st != 200 or j["value"]:
            err.append((q["CODIGO"], a, "dirección nueva ocupada o no verificable")); log(f"  ✗ {a} ocupada → no se toca"); continue
        st, r = graph("PATCH", f"/users/{q['id']}", {"userPrincipalName": a, "mailNickname": lp(a)})
        if st not in (200, 204):
            err.append((q["CODIGO"], a, f"PATCH {st} {str(r)[:160]}")); log(f"  ✗ {q['upn_viejo']}: {st} {str(r)[:160]}"); continue
        log(f"  ✓ {q['upn_viejo']} → {a}  ({i}/{len(plan)})")
        hechos.append({**q, "estado": "renombrada"})
    # Exchange tarda en mover la dirección principal: comprobar mail y alias
    if any(h["estado"] == "renombrada" for h in hechos): log("esperando 90 s a Exchange…"); time.sleep(90)
    for h in hechos:
        st, u = graph("GET", f"/users/{h['id']}?$select=userPrincipalName,mail,proxyAddresses")
        h["mail_despues"] = (u.get("mail") or "").lower() if st == 200 else f"ERR {st}"
        h["alias_viejo"] = st == 200 and any(lp(p.split(":", 1)[1]) == lp(h["upn_viejo"]) for p in u.get("proxyAddresses") or [])
        if h["mail_despues"] != h["upn_nuevo"]: log(f"  ⚠ {h['upn_nuevo']}: mail aún = {h['mail_despues']}")
    out = os.path.join(HOME, f"backups/entra-snapshots/renombrar_resultado_{stamp}.json")
    json.dump({"hechos": hechos, "errores": err}, open(out, "w"), ensure_ascii=False, indent=1); os.chmod(out, 0o600)
    qq = lambda s: "'" + str(s).replace("'", "''") + "'"
    ok = [h for h in hechos if h["estado"] in ("renombrada", "ya estaba")]
    sql = [f"-- CORREO_INST de cuentas renombradas al formato UPeU · {stamp} · {len(ok)} filas · sin COMMIT",
           "-- Candado: acepta el valor que Oracle tenía al crear la cuenta O el usuario LAMB (si ya se cargó el SQL anterior).",
           "SET SERVEROUTPUT ON SIZE UNLIMITED", "SET DEFINE OFF", "DECLARE n NUMBER := 0; BEGIN"]
    for h in ok:
        previos = sorted({(h.get("CORREO_INST_ACTUAL_ORACLE") or "").strip().lower() or "#", h["upn_viejo"]})
        sql.append(f"  UPDATE MOISES.PERSONA_NATURAL SET CORREO_INST = {qq(h['upn_nuevo'])} WHERE ID_PERSONA = {int(h['ID_PERSONA'])}"
                   f" AND ID_TIPODOCUMENTO = {int(h['ID_TIPODOCUMENTO'])} AND TRIM(NUM_DOCUMENTO) = {qq(h['NUM_DOCUMENTO'])}"
                   f" AND NVL(LOWER(TRIM(CORREO_INST)),'#') IN ({', '.join(qq(v) for v in previos)}); n := n + SQL%ROWCOUNT;")
    sql += [f"  DBMS_OUTPUT.PUT_LINE('actualizadas: ' || n || ' de {len(ok)}');", "END;", "/",
            f"-- Si 'actualizadas' = {len(ok)} → COMMIT; si no → ROLLBACK;"]
    so = os.path.join(OUTD, f"UPDATE_CORREO_INST_renombradas_formato_{stamp}.sql"); open(so, "w").write("\n".join(sql) + "\n")
    log(f"\nRENOMBRADAS: {sum(h['estado']=='renombrada' for h in hechos)} · mail ya movido: "
        f"{sum(h['mail_despues']==h['upn_nuevo'] for h in hechos)} · alias viejo conservado: {sum(bool(h['alias_viejo']) for h in hechos)} · errores: {len(err)}")
    log(f"resultado: {out}\nSQL para Oracle (Uziel): {so}")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("simular", "ejecutar"): sys.exit(__doc__)
    if sys.argv[1] == "simular": simular()
    else:
        lim = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 0
        ejecutar(sys.argv[2], lim)
