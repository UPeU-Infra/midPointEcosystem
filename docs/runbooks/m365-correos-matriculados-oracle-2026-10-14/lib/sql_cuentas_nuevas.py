#!/usr/bin/env python3
"""
SQL ÚNICO de CORREO_INST para TODAS las cuentas que el IGA creó en M365 (creacion_resultado_*.json), con la
dirección FINAL que tienen hoy en M365 (tras renombrados). Reemplaza a los SQL parciales de cada ejecución.

  python3 sql_cuentas_nuevas.py [--excluir ID_PERSONA,...]

SOLO LECTURA: lee cada cuenta en Graph por su id (comprueba employeeId = ID_PERSONA y que mail = UPN) y lee en
Oracle el CORREO_INST ACTUAL de cada ficha y quién más tiene esa dirección. El candado de cada UPDATE es el valor
leído ahora. Salen UPDATE y ROLLBACK (sin COMMIT) en ~/Downloads. Requiere VPN.
"""
import json, os, re, sys, glob, subprocess, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crear_cuentas as cc      # utilidades (token, graph); su main no corre al importar
log, graph, HOME, OUTD = cc.log, cc.graph, cc.HOME, cc.OUTD
excluir = set(sys.argv[sys.argv.index("--excluir") + 1].split(",")) if "--excluir" in sys.argv else set()

# 1. cuentas creadas por el IGA
C = {}
for f in sorted(glob.glob(os.path.join(HOME, "backups/entra-snapshots/creacion_resultado_*.json"))):
    for x in json.load(open(f))["hechos"]:
        if x.get("id"): C[x["ID_PERSONA"]] = x
log(f"cuentas creadas por el IGA: {len(C)}")

# 2. estado real en M365
prob = []
for k, x in C.items():
    st, u = graph("GET", f"/users/{x['id']}?$select=userPrincipalName,mail,employeeId,accountEnabled")
    if st != 200: prob.append((k, f"Graph {st}")); continue
    x["final"] = (u.get("mail") or "").lower()
    if str(u.get("employeeId")) != k: prob.append((k, f"employeeId {u.get('employeeId')} ≠ ID_PERSONA"))
    elif x["final"] != u["userPrincipalName"].lower(): prob.append((k, f"mail {x['final']} ≠ UPN {u['userPrincipalName']}"))
    elif not u.get("accountEnabled"): prob.append((k, "cuenta deshabilitada"))

# 3. Oracle: valor actual de cada ficha y dueños de cada dirección final
env = {}
for p in ("midpoint-upeu.env", "oracle-lamb.env"): env.update(cc.envfile(os.path.join(HOME, ".secrets", p)))
JAR = "/opt/midpoint/var/lib/ojdbc11-23.6.0.24.10.jar"; DSN = "jdbc:oracle:thin:@192.168.13.9:1521/UPEU"
def ora(q):
    cmd = f"docker exec midpoint_server java -cp /tmp:{JAR} OraQ '{DSN}' '{env['ORACLE_USER']}' '{env['ORACLE_PASS']}' \"{q}\""
    r = subprocess.run(["sshpass", "-e", "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=60",
                        "-o", "NumberOfPasswordPrompts=1", "midpoint-prod", cmd],
                       env={**os.environ, "SSHPASS": env["MIDPOINT_PROD_PASS"]}, capture_output=True, text=True, timeout=300)
    if r.returncode: sys.exit(f"✗ Oracle: {r.stderr[-300:]}")
    return [l.split("\t") for l in r.stdout.splitlines()[1:] if l.strip()]
ids = ",".join(sorted(C))
actual = {r[0]: r[1] for r in ora(f"SELECT ID_PERSONA, NVL(LOWER(TRIM(CORREO_INST)),'#') FROM MOISES.PERSONA_NATURAL WHERE ID_PERSONA IN ({ids})")}
finales = sorted({x["final"] for x in C.values() if x.get("final")})
dueno = {}
for i in range(0, len(finales), 500):
    lista = ",".join("'" + a + "'" for a in finales[i:i + 500])
    for r in ora(f"SELECT LOWER(TRIM(CORREO_INST)), ID_PERSONA FROM MOISES.PERSONA_NATURAL WHERE LOWER(TRIM(CORREO_INST)) IN ({lista})"):
        dueno.setdefault(r[0], set()).add(r[1])

# 4. filas
malos = dict(prob)
filas, ya, fuera = [], [], []
for k, x in sorted(C.items(), key=lambda kv: kv[1].get("final", "")):
    if k in excluir: fuera.append((k, x.get("final"), "excluido a mano")); continue
    if k in malos: fuera.append((k, x.get("final"), malos[k])); continue
    if k not in actual: fuera.append((k, x["final"], "ficha no encontrada en Oracle")); continue
    otros = dueno.get(x["final"], set()) - {k}
    if otros: fuera.append((k, x["final"], f"Oracle ya da esa dirección a ID_PERSONA {','.join(sorted(otros))}")); continue
    if actual[k] == x["final"]: ya.append(k); continue
    filas.append((x, actual[k]))

q = lambda s: "'" + str(s).replace("'", "''") + "'"
stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
up = [f"-- CORREO_INST de las cuentas creadas en M365 por el IGA (pregrado 2026-2) · {stamp}",
      f"-- Filas: {len(filas)}. Reemplaza a TODOS los SQL anteriores de «cuentas nuevas» y «renombradas».",
      "-- Candados: ID_PERSONA + tipo y nº de documento + CORREO_INST igual al leído hoy. Sin COMMIT.",
      "SET SERVEROUTPUT ON SIZE UNLIMITED", "SET DEFINE OFF", "", "DECLARE n NUMBER := 0; BEGIN"]
rb = [f"-- ROLLBACK del SQL de cuentas nuevas ({stamp}). Sin COMMIT.", "SET SERVEROUTPUT ON SIZE UNLIMITED", "SET DEFINE OFF", "",
      "DECLARE n NUMBER := 0; BEGIN"]
for x, cur in filas:
    up.append(f"  UPDATE MOISES.PERSONA_NATURAL SET CORREO_INST = {q(x['final'])} WHERE ID_PERSONA = {int(x['ID_PERSONA'])}"
              f" AND ID_TIPODOCUMENTO = {int(x['ID_TIPODOCUMENTO'])} AND TRIM(NUM_DOCUMENTO) = {q(x['NUM_DOCUMENTO'])}"
              f" AND NVL(LOWER(TRIM(CORREO_INST)),'#') = {q(cur)}; n := n + SQL%ROWCOUNT;")
    rb.append(f"  UPDATE MOISES.PERSONA_NATURAL SET CORREO_INST = {'NULL' if cur == '#' else q(cur)} WHERE ID_PERSONA = {int(x['ID_PERSONA'])}"
              f" AND LOWER(TRIM(CORREO_INST)) = {q(x['final'])}; n := n + SQL%ROWCOUNT;")
for d in (up, rb): d += [f"  DBMS_OUTPUT.PUT_LINE('actualizadas: ' || n || ' de {len(filas)}');", "END;", "/", ""]
up += [f"-- VERIFICACIÓN: debe devolver {len(filas)}",
       "SELECT COUNT(*) AS FILAS_CON_CORREO_ESPERADO FROM MOISES.PERSONA_NATURAL WHERE (ID_PERSONA, LOWER(TRIM(CORREO_INST))) IN (" +
       ",".join(f"({int(x['ID_PERSONA'])},{q(x['final'])})" for x, _ in filas) + ");", "",
       f"-- Si 'actualizadas' = {len(filas)} y FILAS_CON_CORREO_ESPERADO = {len(filas)} → COMMIT;   si no → ROLLBACK;"]
so = os.path.join(OUTD, f"UPDATE_CORREO_INST_cuentas_nuevas_CONSOLIDADO_{stamp}.sql"); open(so, "w").write("\n".join(up) + "\n")
ro = os.path.join(OUTD, f"ROLLBACK_CORREO_INST_cuentas_nuevas_CONSOLIDADO_{stamp}.sql"); open(ro, "w").write("\n".join(rb) + "\n")
from collections import Counter
log(f"a cargar: {len(filas)} · Oracle ya correcto: {len(ya)} · fuera: {len(fuera)}")
log(f"valor actual en Oracle de las que se cargan: {dict(Counter('vacío' if c == '#' else 'otro' for _, c in filas))}")
for f in fuera: log("  fuera:", *f)
log(so); log(ro)
