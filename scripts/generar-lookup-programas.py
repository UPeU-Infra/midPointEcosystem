#!/usr/bin/env python3
"""
Genera las LookupTables de programa de MidPoint desde VocBench.

Sustituye la generación manual de `upeu/lookup-tables/program-resolver-lamb-byid.xml`
y añade la tabla del **P-code**, que por ADR-005 pasa a ser el código principal
de programa en UPeU (el INEI queda para el repositorio de tesis).

Emite dos tablas
----------------
1. `program-resolver-lamb-byid` (OID 7c3f2a91-…) — la que ya existía.
   `key` = ID_PROGRAMA_ESTUDIO · `value` = URI canónica · `label` = EP-XXX.
2. `program-pxx-byid` (OID 5d1c8a47-…) — **nueva**.
   `key` = ID_PROGRAMA_ESTUDIO · `value` = P-code/SEG-code vigente · `label` = ídem.

Por qué el P-code sale de aquí y no de Oracle
---------------------------------------------
Hoy `sb:academicProgramSuneduCode` se alimenta de
`DAVID.ACAD_PROGRAMA_ESTUDIO.CODIGO_SUNEDU2`. Ese campo **no es fiable**: el
ADR-004 del tesauro demostró que es un correlativo interno que diverge del
oficial en todo el posgrado.

Medido sobre la matrícula 2026-2 (19.486 estudiantes, 09-ago-2026):

| Fuente del P-code | Cobertura | Errores |
|---|---|---|
| Oracle `CODIGO_SUNEDU2` | 73,18 % | **139 estudiantes con el código equivocado** (Oracle dice `P14`, el A4 dice `P97`) |
| **Tesauro (esta tabla)** | **88,44 %** | **0** |

Además Oracle deja el campo vacío en 2.972 identidades que el tesauro sí resuelve.

Cuando un concepto lleva varios P-codes
---------------------------------------
El A4 lista **una fila por modalidad**: Administración es `P04` presencial,
`P05` semipresencial y `P95` a distancia — tres programas distintos ante SUNEDU.
El tesauro los agrupa en un concepto y guarda cada código en
`upeu:codigoSunedu{Presencial,Semipresencial,Distancia}`.

Por eso el P-code **no se elige por concepto sino por modalidad**: se cruza con
`DAVID.ACAD_PROGRAMA_ESTUDIO.ID_MODALIDAD_ESTUDIO` (1=Presencial,
2=Semipresencial, 13=A Distancia; el resto —Ecuador, PAE, sedes— se tratan como
presencial salvo que el concepto no lo tenga). Emitir un único código por
concepto declararía a un alumno de la modalidad equivocada.

Si tras eso quedan varios candidatos (recodificación vía resolución,
`SEG20`→`SEG61`), gana el de numeración más alta: el de la resolución reciente.

Uso:
    python3 scripts/generar-lookup-programas.py [--dry-run]
"""
import importlib.util
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
IGA = os.path.abspath(os.path.join(AQUI, ".."))
VOCBENCH = "/Users/alberto/proyectos/productos/vocbench/instituciones/upeu"
DRY = "--dry-run" in sys.argv

OID_URI = "7c3f2a91-4e8d-4b16-9a52-6d0e1f7b3c48"
OID_PXX = "5d1c8a47-2b93-4f60-8e1a-7c4d9f0e6a25"


def vocbench():
    spec = importlib.util.spec_from_file_location(
        "cargador", os.path.join(VOCBENCH, "scripts", "sprint4", "07-cargar-delta.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    vb = mod.VocBench(mod.env())
    vb.login()
    return vb


def consultar(vb, sparql):
    r = vb.post("SPARQL/evaluateQuery",
                {"ctx_project": vb.cfg["VOCBENCH_PROJECT"], "query": sparql})
    return json.loads(r)["result"]["sparql"]["results"]["bindings"]


def orden_pcode(c):
    return (0 if c.startswith("P") else 1, int(re.sub(r"\D", "", c)))


def escapar(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def tabla(oid, nombre, descripcion, cabecera, filas):
    L = ['<?xml version="1.0" encoding="UTF-8"?>', "<!--", cabecera, "-->",
         f'<lookupTable xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3" oid="{oid}">',
         f"    <name>{nombre}</name>",
         f"    <description>{escapar(descripcion)}</description>"]
    for key, value, label in filas:
        L.append("    <row>")
        L.append(f"        <key>{escapar(key)}</key>")
        L.append(f"        <value>{escapar(value)}</value>")
        if label:
            L.append(f"        <label>{escapar(label)}</label>")
        L.append("    </row>")
    L.append("</lookupTable>")
    return "\n".join(L) + "\n"


def main():
    vb = vocbench()

    # ID de Oracle → concepto vigente, con sus EP-code y P-codes.
    # No se filtra por named graph: el tesauro vive repartido entre el grafo
    # <.../programas/> y el default, y filtrar dejaba fuera ~2.900 triples.
    filas = consultar(vb, """PREFIX skos:<http://www.w3.org/2004/02/skos/core#>
        PREFIX owl:<http://www.w3.org/2002/07/owl#>
        SELECT ?id ?c ?ep ?px ?mp ?ms ?md WHERE {
          ?c skos:notation ?v .
          FILTER(DATATYPE(?v)=<urn:esther:id_programa_estudio>) BIND(STR(?v) AS ?id)
          FILTER NOT EXISTS { ?c owl:deprecated true }
          OPTIONAL { ?c skos:notation ?e . FILTER(REGEX(STR(?e),"^EP-")) BIND(STR(?e) AS ?ep) }
          OPTIONAL { ?c skos:altLabel ?p . FILTER(REGEX(STR(?p),"^(P|SEG)[0-9]+$"))
                     BIND(STR(?p) AS ?px) }
          OPTIONAL { ?c <http://upeu.edu.pe/sys/ontologia#codigoSuneduPresencial> ?mp }
          OPTIONAL { ?c <http://upeu.edu.pe/sys/ontologia#codigoSuneduSemipresencial> ?ms }
          OPTIONAL { ?c <http://upeu.edu.pe/sys/ontologia#codigoSuneduDistancia> ?md } }""")

    # Oracle: ID_PROGRAMA_ESTUDIO -> ID_MODALIDAD_ESTUDIO (1=Presencial, 2=Semi, 13=Distancia)
    modalidad = json.load(open(os.path.join(AQUI, "..", "datasets", "id-modalidad-lamb.json")))

    datos = {}
    for b in filas:
        d = datos.setdefault(b["id"]["value"],
                             {"uri": b["c"]["value"], "ep": set(), "px": set()})
        if "ep" in b:
            d["ep"].add(b["ep"]["value"])
        if "px" in b:
            d["px"].add(b["px"]["value"])
        for clave, var in (("presencial", "mp"), ("semipresencial", "ms"), ("distancia", "md")):
            if var in b:
                d.setdefault("mod", {})[clave] = b[var]["value"]

    orden = sorted(datos, key=lambda k: int(k))
    f_uri = [(k, datos[k]["uri"], sorted(datos[k]["ep"])[0] if datos[k]["ep"] else None)
             for k in orden]
    f_pxx, por_modalidad = [], 0
    for k in orden:
        mod = datos[k].get("mod", {})
        clave = {"2": "semipresencial", "13": "distancia"}.get(str(modalidad.get(k, "")), "presencial")
        elegido = mod.get(clave)
        if elegido:
            por_modalidad += 1
        else:
            px = sorted(datos[k]["px"], key=orden_pcode)
            elegido = px[-1] if px else None
        if elegido:
            f_pxx.append((k, elegido, elegido))

    con_ep = sum(1 for _, _, l in f_uri if l)
    print(f"IDs resueltos a concepto vigente : {len(f_uri)}")
    print(f"  con EP-code                    : {con_ep}")
    print(f"  con P-code                     : {len(f_pxx)}")
    print(f"    de ellos, elegido por modalidad: {por_modalidad}")

    salidas = [
        (os.path.join(IGA, "upeu", "lookup-tables", "program-resolver-lamb-byid.xml"),
         tabla(OID_URI, "program-resolver-lamb-byid",
               "ID_PROGRAMA_ESTUDIO -> URI canonica del tesauro UPeU. Generado desde "
               "VocBench, resuelve dct:isReplacedBy. NO editar a mano.",
               f"""  LookupTable: program-resolver-lamb-byid
  OID: {OID_URI}

  ARTEFACTO GENERADO por scripts/generar-lookup-programas.py — no editar a mano.
  Fuente: VocBench, notation urn:esther:id_programa_estudio.
  {len(f_uri)} filas · {con_ep} con EP-code.

  key   = ID_PROGRAMA_ESTUDIO (Oracle, inmutable)
  value = URI canonica del concepto VIGENTE
  label = notation EP-XXX cuando existe""", f_uri)),
        (os.path.join(IGA, "upeu", "lookup-tables", "program-pxx-byid.xml"),
         tabla(OID_PXX, "program-pxx-byid",
               "ID_PROGRAMA_ESTUDIO -> P-code/SEG-code oficial de los Formatos A4/A8. "
               "Codigo principal de programa en UPeU (ADR-005). NO editar a mano.",
               f"""  LookupTable: program-pxx-byid
  OID: {OID_PXX}

  ARTEFACTO GENERADO por scripts/generar-lookup-programas.py — no editar a mano.
  Fuente: VocBench (skos:altLabel P-code), que a su vez toma los Formatos A4/A8 2026-1.
  {len(f_pxx)} filas.

  El P-code es el codigo PRINCIPAL de programa en UPeU (ADR-005 del tesauro).
  NO se toma de DAVID.ACAD_PROGRAMA_ESTUDIO.CODIGO_SUNEDU2: ese campo es un
  correlativo interno que diverge del oficial en el posgrado (ADR-004). Medido
  sobre la matricula 2026-2: Oracle da 73,18 % con 139 codigos equivocados; esta
  tabla da 88,44 % sin errores.

  key   = ID_PROGRAMA_ESTUDIO (Oracle, inmutable)
  value = P-code / SEG-code vigente del A4/A8
  label = idem""", f_pxx)),
    ]

    for ruta, contenido in salidas:
        if DRY:
            print(f"  (dry-run) {os.path.relpath(ruta, IGA)} — {contenido.count('<row>')} filas")
            continue
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as fh:
            fh.write(contenido)
        print(f"  → {os.path.relpath(ruta, IGA)} ({contenido.count('<row>')} filas)")


if __name__ == "__main__":
    main()
