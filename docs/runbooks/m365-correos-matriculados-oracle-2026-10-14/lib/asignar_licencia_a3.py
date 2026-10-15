#!/usr/bin/env python3
"""
Asigna la licencia «Microsoft 365 A3 for students use benefit» (M365EDU_A3_STUUSEBNFT) a las cuentas
de un JSON de selección, guardando antes y después en ~/backups/entra-snapshots/ (600).

  python3 asignar_licencia_a3.py <seleccion.json>

<seleccion.json> = {"sku": "<skuId>", "users": [{"id":..., "userPrincipalName":..., ...}, ...]}
Solo añade la licencia (removeLicenses vacío). Reversión: POST assignLicense con removeLicenses=[skuId].
Credenciales de la app MidPoint-UPeU en ~/.secrets/upeu-infra.env (requiere LicenseAssignment.ReadWrite.All).
"""
import json, os, sys, time, datetime, urllib.request, urllib.parse

env = {}
for line in open(os.path.expanduser("~/.secrets/upeu-infra.env")):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k.replace("export ", "").strip()] = v.strip().strip('"').strip("'")
T, C, S = env["MIDPOINT_AZ_TENANT_ID"], env["MIDPOINT_AZ_CLIENT_ID"], env["MIDPOINT_AZ_CLIENT_SECRET"]
tok = json.load(urllib.request.urlopen(urllib.request.Request(
    f"https://login.microsoftonline.com/{T}/oauth2/v2.0/token",
    data=urllib.parse.urlencode({"client_id": C, "client_secret": S, "scope": "https://graph.microsoft.com/.default",
                                 "grant_type": "client_credentials"}).encode())))["access_token"]
H = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}
SEL = "id,userPrincipalName,mail,displayName,accountEnabled,usageLocation,assignedLicenses"

d = json.load(open(sys.argv[1]))
sku, users = d["sku"], d["users"]
stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
bk = os.path.expanduser(f"~/backups/entra-snapshots/licencia-a3-antes-{stamp}.json")
json.dump(d, open(bk, "w"), ensure_ascii=False, indent=1); os.chmod(bk, 0o600)
print(f"antes guardado en {bk}")

ok = err = 0
for u in users:
    if not u.get("usageLocation"):
        # Microsoft exige usageLocation para licenciar; solo se fija si está VACÍO (nunca se cambia uno existente)
        try:
            urllib.request.urlopen(urllib.request.Request(
                f"https://graph.microsoft.com/v1.0/users/{u['id']}", data=json.dumps({"usageLocation": "PE"}).encode(),
                headers=H, method="PATCH"))
            print("usageLocation=PE", u["userPrincipalName"])
        except urllib.error.HTTPError as e:
            err += 1; print("ERR usageLocation", e.code, u["userPrincipalName"], e.read()[:200]); continue
    body = json.dumps({"addLicenses": [{"skuId": sku, "disabledPlans": []}], "removeLicenses": []}).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            f"https://graph.microsoft.com/v1.0/users/{u['id']}/assignLicense", data=body, headers=H, method="POST"))
        ok += 1; print("OK ", r.status, u["userPrincipalName"])
    except urllib.error.HTTPError as e:
        err += 1; print("ERR", e.code, u["userPrincipalName"], e.read()[:200])
print(f"asignadas {ok} · errores {err}")

time.sleep(20)
despues = []
for u in users:
    x = json.load(urllib.request.urlopen(urllib.request.Request(
        f"https://graph.microsoft.com/v1.0/users/{u['id']}?$select={SEL}", headers=H)))
    x.pop("@odata.context", None); despues.append(x)
    tiene = any(l["skuId"] == sku for l in x.get("assignedLicenses", []))
    print(("A3 ✓ " if tiene else "A3 ✗ "), x["userPrincipalName"], "| mail:", x.get("mail"))
dk = os.path.expanduser(f"~/backups/entra-snapshots/licencia-a3-despues-{stamp}.json")
json.dump(despues, open(dk, "w"), ensure_ascii=False, indent=1); os.chmod(dk, 0o600)
print(f"después guardado en {dk}  (el buzón y el campo mail pueden tardar unos minutos en aparecer)")
