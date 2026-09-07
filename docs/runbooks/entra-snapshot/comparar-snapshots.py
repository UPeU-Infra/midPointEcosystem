#!/usr/bin/env python3
"""
Compara dos snapshots del directorio Entra ID y reporta qué cambió.

    python3 comparar-snapshots.py <antiguo.json> <nuevo.json> [--csv salida.csv]

Es lo que da sentido al backup: detecta altas, bajas y modificaciones de
atributos entre dos fotos, para poder ver si algo cambió sin que se supiera.
"""
import json, sys, csv, os
from collections import Counter, defaultdict

CAMPOS = ["upn","mail","display","enabled","department","office","jobTitle",
          "city","company","employeeId","pwdChange","given","surname"]
ETIQ = {"upn":"UPN","mail":"Correo","display":"Nombre para mostrar","enabled":"Habilitada",
        "department":"Departamento","office":"Oficina","jobTitle":"Cargo","city":"Ciudad",
        "company":"Compañía","employeeId":"ID de empleado","pwdChange":"Cambio de contraseña",
        "given":"Nombre","surname":"Apellido"}

def cargar(p):
    d = json.load(open(p, encoding="utf-8"))
    return {u["id"]: u for u in d if u.get("id")}

def norm(v):
    if isinstance(v, list): return tuple(sorted(x.lower() for x in v if x))
    if isinstance(v, str):  return v.strip().lower()
    return v

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    pa, pn = sys.argv[1], sys.argv[2]
    csv_out = sys.argv[sys.argv.index("--csv")+1] if "--csv" in sys.argv else None
    A, N = cargar(pa), cargar(pn)

    altas = [N[i] for i in N.keys() - A.keys()]
    bajas = [A[i] for i in A.keys() - N.keys()]
    comunes = A.keys() & N.keys()

    cambios = []          # (id, upn, campo, antes, despues)
    for i in comunes:
        for c in CAMPOS:
            va, vn = A[i].get(c), N[i].get(c)
            if norm(va) != norm(vn):
                cambios.append((i, N[i].get("upn",""), c, va, vn))

    print(f"ANTES   {os.path.basename(pa)}   {len(A):,} cuentas".replace(",","."))
    print(f"AHORA   {os.path.basename(pn)}   {len(N):,} cuentas".replace(",","."))
    print(f"\n  altas          {len(altas):6d}")
    print(f"  bajas          {len(bajas):6d}")
    print(f"  modificadas    {len({c[0] for c in cambios}):6d}  ({len(cambios)} atributos en total)")

    if cambios:
        print("\n=== cambios por atributo ===")
        for campo, n in Counter(c[2] for c in cambios).most_common():
            print(f"  {ETIQ.get(campo,campo):24s} {n:6d}")

    # lo que más importa vigilar: cuentas que se habilitaron o deshabilitaron
    act = [c for c in cambios if c[2] == "enabled"]
    if act:
        print(f"\n⚠ CAMBIOS DE ESTADO DE CUENTA ({len(act)}):")
        for i, upn, _, va, vn in act[:20]:
            print(f"   {upn:45s} {'habilitada→DESHABILITADA' if va else 'DESHABILITADA→habilitada'}")
        if len(act) > 20: print(f"   … y {len(act)-20} más")

    if bajas:
        print(f"\n⚠ CUENTAS QUE YA NO EXISTEN ({len(bajas)}):")
        for u in bajas[:15]: print(f"   {u.get('upn','?')}")
        if len(bajas) > 15: print(f"   … y {len(bajas)-15} más")

    if csv_out:
        with open(csv_out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["tipo","id","upn","campo","valor_antes","valor_despues"])
            for u in altas: w.writerow(["ALTA",u.get("id"),u.get("upn"),"","",""])
            for u in bajas: w.writerow(["BAJA",u.get("id"),u.get("upn"),"","",""])
            for i,upn,c,va,vn in cambios:
                w.writerow(["CAMBIO",i,upn,ETIQ.get(c,c),va,vn])
        print(f"\ndetalle completo → {csv_out}")

if __name__ == "__main__":
    main()
