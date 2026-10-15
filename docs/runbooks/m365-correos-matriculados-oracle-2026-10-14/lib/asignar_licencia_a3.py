#!/usr/bin/env python3
"""
Asigna la licencia «Microsoft 365 A3 for students use benefit» (M365EDU_A3_STUUSEBNFT) a las cuentas
de un JSON de selección. Idempotente y reanudable: se puede relanzar las veces que haga falta.

  python3 asignar_licencia_a3.py <seleccion.json>

<seleccion.json> = {"sku": "<skuId>", "users": [{"id":..., "userPrincipalName":..., ...}, ...]}

Fases:
  0. Relee el estado ACTUAL de cada cuenta y salta las que ya tienen la licencia.
  1. Fija usageLocation=PE solo en las que lo tienen VACÍO (nunca cambia uno existente) y espera 60 s,
     porque Microsoft tarda en propagarlo y rechaza la licencia mientras tanto.
  2. Asigna la licencia; si Microsoft aún responde «invalid usage location», reintenta hasta 4 veces.
Antes y después quedan en ~/backups/entra-snapshots/ (600). Toda llamada tiene timeout de 30 s.
Reversión: POST assignLicense con removeLicenses=[skuId].
Credenciales de la app MidPoint-UPeU en ~/.secrets/upeu-infra.env (requiere LicenseAssignment.ReadWrite.All).
"""
import json, os, sys, time, datetime, urllib.request, urllib.parse, urllib.error

def log(*a): print(*a, flush=True)

env = {}
for line in open(os.path.expanduser("~/.secrets/upeu-infra.env")):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k.replace("export ", "").strip()] = v.strip().strip('"').strip("'")
T, C, S = env["MIDPOINT_AZ_TENANT_ID"], env["MIDPOINT_AZ_CLIENT_ID"], env["MIDPOINT_AZ_CLIENT_SECRET"]

def token():
    return json.load(urllib.request.urlopen(urllib.request.Request(
        f"https://login.microsoftonline.com/{T}/oauth2/v2.0/token",
        data=urllib.parse.urlencode({"client_id": C, "client_secret": S, "scope": "https://graph.microsoft.com/.default",
                                     "grant_type": "client_credentials"}).encode()), timeout=30))["access_token"]
TOK = token()

def graph(method, url, body=None, intentos=4):
    """Llamada a Graph con timeout y reintentos ante 429/5xx/timeouts. Devuelve (status, json|texto)."""
    for n in range(intentos):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                "https://graph.microsoft.com/v1.0" + url, method=method,
                data=json.dumps(body).encode() if body is not None else None,
                headers={"Authorization": "Bearer " + TOK, "Content-Type": "application/json"}), timeout=30)
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            txt = e.read().decode(errors="replace")
            if e.code in (429, 500, 502, 503, 504) and n < intentos - 1:
                time.sleep(int(e.headers.get("Retry-After") or 5 * (n + 1))); continue
            return e.code, txt
        except Exception as e:  # timeout, conexión
            if n < intentos - 1:
                time.sleep(5 * (n + 1)); continue
            return 0, f"{type(e).__name__}: {e}"

d = json.load(open(sys.argv[1]))
sku, users = d["sku"], d["users"]
stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
bk = os.path.expanduser(f"~/backups/entra-snapshots/licencia-a3-antes-{stamp}.json")
json.dump(d, open(bk, "w"), ensure_ascii=False, indent=1); os.chmod(bk, 0o600)
log(f"selección: {len(users)} cuentas · antes guardado en {bk}")

# ── 0. estado actual ──
SEL = "id,userPrincipalName,mail,accountEnabled,usageLocation,assignedLicenses"
actual, pendientes = {}, []
for i, u in enumerate(users, 1):
    st, x = graph("GET", f"/users/{u['id']}?$select={SEL}")
    if st != 200:
        log(f"  ERR lectura {st} {u['userPrincipalName']}"); continue
    actual[u["id"]] = x
    if any(l["skuId"] == sku for l in x.get("assignedLicenses", [])):
        continue
    pendientes.append(x)
    if i % 100 == 0: log(f"  leídas {i}/{len(users)}")
log(f"fase 0: ya tenían la licencia {len(users) - len(pendientes)} · pendientes {len(pendientes)}")

# ── 1. usageLocation solo si está vacío ──
sin_ul = [x for x in pendientes if not x.get("usageLocation")]
for x in sin_ul:
    st, r = graph("PATCH", f"/users/{x['id']}", {"usageLocation": "PE"})
    log(("  usageLocation=PE " if st in (200, 204) else f"  ERR usageLocation {st} ") + x["userPrincipalName"])
if sin_ul:
    log(f"fase 1: usageLocation fijado en {len(sin_ul)} · esperando 60 s a que Microsoft lo propague…")
    time.sleep(60)

# ── 2. licencia con reintentos ──
ok, err, cola = 0, [], list(pendientes)
for ronda in range(1, 5):
    reintentar = []
    for x in cola:
        st, r = graph("POST", f"/users/{x['id']}/assignLicense",
                      {"addLicenses": [{"skuId": sku, "disabledPlans": []}], "removeLicenses": []})
        if st == 200:
            ok += 1; log(f"  OK  {x['userPrincipalName']}")
        elif st == 400 and "usage location" in str(r).lower():
            reintentar.append(x)
        else:
            err.append((x["userPrincipalName"], st, str(r)[:160])); log(f"  ERR {st} {x['userPrincipalName']} {str(r)[:160]}")
    if not reintentar: break
    log(f"ronda {ronda}: {len(reintentar)} aún sin usageLocation propagado · reintento en 45 s")
    cola = reintentar; time.sleep(45)
else:
    for x in cola: err.append((x["userPrincipalName"], 400, "usageLocation no propagado tras 4 rondas"))
log(f"fase 2: asignadas {ok} · errores {len(err)}")

# ── después ──
time.sleep(20)
despues, con = [], 0
for u in users:
    st, x = graph("GET", f"/users/{u['id']}?$select={SEL}")
    if st == 200:
        despues.append(x); con += any(l["skuId"] == sku for l in x.get("assignedLicenses", []))
dk = os.path.expanduser(f"~/backups/entra-snapshots/licencia-a3-despues-{stamp}.json")
json.dump({"despues": despues, "errores": err}, open(dk, "w"), ensure_ascii=False, indent=1); os.chmod(dk, 0o600)
log(f"RESULTADO: {con}/{len(users)} con licencia A3 · errores {len(err)} · después en {dk}")
log("(el campo mail/buzón puede tardar unos minutos en aparecer tras licenciar)")
