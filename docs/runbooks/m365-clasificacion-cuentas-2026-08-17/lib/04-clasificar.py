#!/usr/bin/env python3
"""
Clasificación de cuentas M365 de UPeU por CASCADA DE PROCEDENCIA.

Reescritura del requerimiento de D. Urquizo (ms365.docx) invirtiendo su prioridad:
la inferencia semántica sobre el nombre deja de ser el método principal y pasa a
ser el último recurso, aplicado solo a lo que ninguna fuente autoritativa resuelve.
Cada fila declara de qué nivel salió su clasificación.

  N0  forma de la cuenta        reglas objetivas (invitado externo, placeholder)
  N1  MidPoint                  archetype, afiliación, campus y unidad heredados
  N2a Oracle LAMB por correo    persona real que MidPoint todavía no tiene
  N2b Oracle LAMB por documento el alias numérico ES un documento de identidad
  N3  heurística                el método de Urquizo, marcado como inferencia
"""
import json, csv, re, unicodedata, datetime, sys
from collections import Counter, defaultdict

import os
_SP = os.environ.get("M365_WORK") or os.path.expanduser("~/.cache/upeu-m365")
_OUT = os.environ.get("M365_OUT") or os.path.expanduser("~/Downloads")

SP = _SP
HOY = datetime.datetime.now(datetime.timezone.utc)

def norm(s):
    if not s: return ""
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode()
    return re.sub(r'\s+',' ', re.sub(r'[^A-Za-z0-9 ]',' ', s).upper()).strip()

def parse(s):
    if not s: return None
    try: return datetime.datetime.fromisoformat(s.replace("Z","+00:00"))
    except Exception: return None

def lp(a): return a.split("@")[0].lower() if a and "@" in a else ""
def dm(a): return a.split("@")[-1].lower() if a and "@" in a else "(sin dominio)"

# ───────────────────────────── fuentes autoritativas ─────────────────────────────
mp = {}
for r in csv.DictReader(open(f"{SP}/mp_full.csv", newline='', encoding='utf-8')):
    mp[r["nameorig"]] = r
mp_by_email = {r["email"]: k for k, r in mp.items() if r["email"]}
mp_by_code  = set(mp)
mp_by_name  = defaultdict(set)
for k, r in mp.items():
    n = norm(r["given"] + " " + r["family"])
    if n: mp_by_name[n].add(k)

ora_mail, ora_doc = {}, {}
for line in open(f"{SP}/ora_correo.tsv", encoding='utf-8', errors='replace'):
    p = line.rstrip("\n").split("\t")
    if len(p) < 3 or p[1] == "CORREO_INST": continue
    ora_mail[p[1].strip()] = {"idp": p[0], "doc": p[2],
                              "nombre": " ".join(x for x in p[3:6] if x).strip() if len(p) > 3 else ""}
for line in open(f"{SP}/ora_doc.tsv", encoding='utf-8', errors='replace'):
    p = line.split("\t")
    if p[0] == "NUM_DOCUMENTO": continue
    d = p[0].strip()
    if d: ora_doc[d] = p[1].strip() if len(p) > 1 else ""

# nombres del MDM completo (410.996 personas): permite reconocer a una persona real
# aunque no tenga correo institucional registrado ni foco en MidPoint
ora_nombre = defaultdict(set)
for line in open(f"{SP}/ora_nombres.tsv", encoding='utf-8', errors='replace'):
    p = line.rstrip("\n").split("\t")
    if len(p) < 3 or p[0] == "ID_PERSONA": continue
    nom, pat, mat = p[1], p[2] if len(p) > 2 else "", p[3] if len(p) > 3 else ""
    for k in (norm(f"{nom} {pat} {mat}"), norm(f"{nom} {pat}")):
        if k: ora_nombre[k].add(p[0])

# catálogo institucional de unidades (no un diccionario inventado)
AREAS = []
for r in csv.DictReader(open(f"{SP}/mp_orgs.csv", newline='', encoding='utf-8')):
    disp = (r["display"] or r["nameorig"]).strip()
    if not disp: continue
    toks = [t for t in norm(disp).split() if len(t) >= 5
            and t not in ("UNION","UPEU","NIVEL","GENERAL","CENTRO","OFICINA","DIRECCION")]
    if toks: AREAS.append({"org": r["nameorig"], "nombre": disp, "tokens": toks})

# afiliación canónica (eduPerson) derivada del archetype real de MidPoint
ARCH2AFF = {
    "archetype-user-student":         ("Personal", "Estudiante",     "student"),
    "archetype-user-alumni":          ("Personal", "Egresado",       "alum"),
    "archetype-user-employee-staff":  ("Personal", "Administrativo", "staff"),
    "archetype-user-employee-faculty":("Personal", "Docente",        "faculty"),
    "archetype-user-service-account": ("Servicio", "Cuenta de servicio", "service"),
}

# términos de función institucional (Urquizo §3.2 y §7), solo para N3
FUNC = ["contabilidad","contab","tesoreria","finanzas","rrhh","recursoshumanos","admision",
        "matricula","secretaria","secretar","registro","bienestar","soporte","sistemas",
        "tecnologia","comunicaciones","marketing","biblioteca","investigacion","calidad",
        "logistica","compras","almacen","caja","mesadepartes","atencion","administracion",
        "direccion","rectorado","decanato","coordinacion","gerencia","planillas","remuneraciones",
        "presupuesto","auditoria","legal","recepcion","tramite","cobranza","facturacion",
        "pastoral","capellania","mantenimiento","seguridad","transporte","imprenta","libreria",
        "cafeteria","clinica","laboratorio","aula","posgrado","egresados","practicas","convenios",
        "acreditacion","noreply","no-reply","informes","servicios","operaciones","tutoria",
        "audiovisual","gestiondocumental","activosfijos","sst","crai","credito","becas"]
SEDES = {"lima":"LIMA","lim":"LIMA","nana":"LIMA","juliaca":"JULIACA","jul":"JULIACA",
         "tarapoto":"TARAPOTO","tpp":"TARAPOTO"}
SEP = r'[._\-0-9]'

def token_en(lpart, t):
    return re.search(r'(^|%s)%s($|%s)' % (SEP, re.escape(t), SEP), lpart) is not None

def alias_coherente(disp, lpart):
    """¿La estructura del alias es compatible con el nombre para mostrar?
    Urquizo §3.1: un UPN con estructura de nombre/apellido es señal de cuenta personal.
    Devuelve cuántos componentes del nombre aparecen dentro del alias."""
    plano = re.sub(r'[^a-z0-9]', '', (lpart or "").lower())
    toks = [t.lower() for t in norm(disp).split() if len(t) >= 4]
    if not plano or not toks: return 0, 0
    return sum(1 for t in toks if t in plano), len(toks)

def area_por_catalogo(blob):
    """Busca en el catálogo REAL de unidades. Devuelve (nombre_area, org, token)."""
    for a in AREAS:
        for t in a["tokens"]:
            if t.lower() in blob:
                return a["nombre"], a["org"], t.lower()
    return None, None, None

# ───────────────────────────── clasificación ─────────────────────────────
users = json.load(open(f"{SP}/entra_users2.json"))
out = []
for x in users:
    upn = x.get("upn") or ""; mail = x.get("mail") or ""
    l = lp(upn) or lp(mail)
    disp = x.get("display") or ""
    cands = {a.lower().strip() for a in (mail, upn) if a}
    for p in (x.get("proxy") or []):
        p = p.lower().replace("smtp:","").strip()
        if p: cands.add(p)

    row = {
        "upn": upn, "mail": mail, "displayName": disp,
        "givenName": x.get("given") or "", "surname": x.get("surname") or "",
        "dominio": dm(upn), "habilitada": "Sí" if x.get("enabled") else "No",
        "creada": (x.get("created") or "")[:10],
        "ultimoAccesoInteractivo": (x.get("lastInteractive") or "")[:10],
        "ultimoAccesoAutomatico": (x.get("lastNonInteractive") or "")[:10],
        "ultimoCambioPassword": (x.get("pwdChange") or "")[:10],
        "departamentoEntra": x.get("department") or "", "oficinaEntra": x.get("office") or "",
        "cargoEntra": x.get("jobTitle") or "",
        "TipoCuenta":"", "SubtipoCuenta":"", "Afiliacion":"", "AreaCargo":"", "UnidadOrg":"",
        "Campus":"", "CodigoInstitucional":"", "DocumentoIdentidad":"", "ArchetypeMidPoint":"",
        "Fuente":"", "NivelConfianza":"", "IndicadoresDetectados":"", "MotivoClasificacion":"",
        "RequiereRevisionManual":"No", "FueraDelGobiernoIGA":"",
    }

    # ── N0: forma de la cuenta ────────────────────────────────────────────
    if "#EXT#" in upn:
        origen = upn.split("#EXT#")[0].split("_")[-1]
        row.update(TipoCuenta="Invitado externo", SubtipoCuenta="Colaboración B2B",
                   Fuente="N0 · forma de la cuenta", NivelConfianza="Alta",
                   IndicadoresDetectados="UPN contiene #EXT#",
                   MotivoClasificacion=f"Identidad externa invitada al tenant; su organización de origen es {origen}. No es una cuenta de UPeU.")
        out.append(row); continue

    # ── N1: MidPoint ──────────────────────────────────────────────────────
    hit = next((mp[mp_by_email[c]] for c in cands if c in mp_by_email), None)
    via = "correo coincide con el foco"
    if not hit and l and (l in mp_by_code or l.lstrip("0") in mp_by_code):
        hit = mp.get(l) or mp.get(l.lstrip("0")); via = "el alias es el código institucional"
    if hit:
        arch = (hit["archetype"] or "").split(";")[0]
        tipo, sub, aff = ARCH2AFF.get(arch, ("Personal","No determinado",hit["aff"] or ""))
        areas = [a for a in (hit["orgs_nombre"] or "").split(";") if a]
        row.update(TipoCuenta=tipo, SubtipoCuenta=sub, Afiliacion=aff,
                   AreaCargo=areas[0] if areas else "", UnidadOrg=hit["orgs"] or "",
                   Campus=hit["campus"], CodigoInstitucional=hit["codigo"],
                   DocumentoIdentidad=hit["dni"], ArchetypeMidPoint=arch,
                   Fuente="N1 · MidPoint (foco de identidad)", NivelConfianza="Alta",
                   IndicadoresDetectados=f"vínculo por {via}",
                   MotivoClasificacion=f"La cuenta corresponde a una identidad gobernada por el IGA "
                                       f"(archetype {arch or 'sin archetype'}, estado {hit['lifecyclestate']}). "
                                       f"Clasificación heredada del modelo canónico, no inferida del nombre.")
        if not arch:
            row["RequiereRevisionManual"]="Sí"; row["NivelConfianza"]="Media"
            row["MotivoClasificacion"]+=" El foco no tiene archetype asignado: revisar en MidPoint."
        out.append(row); continue

    # ── N2a: Oracle por correo institucional ──────────────────────────────
    o = next((ora_mail[c] for c in cands if c in ora_mail), None)
    if o:
        row.update(TipoCuenta="Personal", SubtipoCuenta="Persona registrada en Oracle LAMB",
                   DocumentoIdentidad=o["doc"], Fuente="N2a · Oracle LAMB (correo institucional)",
                   NivelConfianza="Alta", RequiereRevisionManual="Sí",
                   IndicadoresDetectados=f"CORREO_INST coincide (ID_PERSONA {o['idp']})",
                   MotivoClasificacion="Persona real del MDM institucional, pero SIN foco en MidPoint: "
                                       "la cuenta existe en M365 y en Oracle y el IGA no la gobierna. "
                                       "Revisar por qué no fue importada.")
        out.append(row); continue

    # ── N2b: Oracle por documento en el alias ─────────────────────────────
    if l.isdigit():
        d = l if l in ora_doc else (l.lstrip("0") if l.lstrip("0") in ora_doc else None)
        if d:
            row.update(TipoCuenta="Personal", SubtipoCuenta="Persona identificada por documento",
                       DocumentoIdentidad=d, Fuente="N2b · Oracle LAMB (documento en el alias)",
                       NivelConfianza="Alta", RequiereRevisionManual="Sí",
                       IndicadoresDetectados="el alias numérico es un documento de identidad real",
                       MotivoClasificacion="El alias es un documento registrado en Oracle: la cuenta es de "
                                           "una persona, pero conserva nomenclatura provisional en lugar de "
                                           "nombre.apellido. Candidata a renombrado.")
            out.append(row); continue
        row.update(TipoCuenta="Otros", SubtipoCuenta="Alias numérico sin identidad",
                   Fuente="N0 · forma de la cuenta", NivelConfianza="Media",
                   RequiereRevisionManual="Sí", IndicadoresDetectados="alias 100% numérico sin correspondencia",
                   MotivoClasificacion="El alias es numérico pero no corresponde a ningún documento de Oracle. "
                                       "No se puede determinar a quién pertenece.")
        out.append(row); continue

    # ── N3: heurística (método Urquizo), siempre marcada ──────────────────
    blob = (l + " " + norm(disp).lower())
    ind, motivo = [], []
    area_nom, area_org, tok = area_por_catalogo(blob)
    func_hit = [t for t in FUNC if token_en(l, t) or t in norm(disp).lower().replace(" ","")]
    sede = next((v for k, v in SEDES.items() if token_en(l, k)), "")
    nom_match = mp_by_name.get(norm(disp), set())

    if area_nom:  ind.append(f"coincide con la unidad «{area_nom}» ({area_org})")
    if func_hit:  ind.append("término de función institucional: " + ", ".join(func_hit[:3]))
    if sede:      ind.append(f"posible sede {sede}")
    if nom_match: ind.append(f"displayName coincide con {len(nom_match)} persona(s) de MidPoint")

    if nom_match and not func_hit and not area_nom:
        k = list(nom_match)[0]; h = mp[k]
        arch = (h["archetype"] or "").split(";")[0]
        tipo, sub, aff = ARCH2AFF.get(arch, ("Personal","No determinado", h["aff"] or ""))
        unico = len(nom_match) == 1
        row.update(TipoCuenta="Personal",
                   SubtipoCuenta=(sub if unico else "Posible cuenta personal"),
                   Afiliacion=(aff if unico else ""), Campus=(h["campus"] if unico else ""),
                   CodigoInstitucional=(h["codigo"] if unico else ""),
                   Fuente="N3 · inferencia por nombre",
                   NivelConfianza=("Media" if unico else "Baja"),
                   RequiereRevisionManual="Sí",
                   MotivoClasificacion=("El nombre para mostrar coincide exactamente con una persona de MidPoint, "
                                        "pero el correo no está vinculado a ese foco. Vínculo probable, no probado."
                                        if unico else
                                        "El nombre coincide con VARIAS personas distintas: no se puede atribuir sin revisión."))
    elif (area_nom or func_hit) and not nom_match:
        row.update(TipoCuenta="Administrativa", SubtipoCuenta="Cuenta de cargo o área",
                   AreaCargo=area_nom or "Área no determinada", UnidadOrg=area_org or "",
                   Campus=sede, Fuente="N3 · inferencia semántica",
                   NivelConfianza=("Media" if area_nom else "Baja"),
                   RequiereRevisionManual="Sí",
                   MotivoClasificacion=("Coincide con una unidad del catálogo institucional y no con ninguna persona."
                                        if area_nom else
                                        "Contiene términos de función institucional, pero sin correspondencia en el catálogo de unidades."))
    elif area_nom or func_hit or nom_match:
        row.update(TipoCuenta="Observado", SubtipoCuenta="Información contradictoria",
                   AreaCargo=area_nom or "", Campus=sede, Fuente="N3 · inferencia semántica",
                   NivelConfianza="Baja", RequiereRevisionManual="Sí",
                   MotivoClasificacion="Hay indicios simultáneos de persona y de función institucional. "
                                       "No se fuerza la clasificación (regla anti-falsos-positivos).")
    else:
        # ── N3 · persona reconocida en el MDM por nombre, o alias coherente con el nombre ──
        ora_n = ora_nombre.get(norm(disp), set())
        coh, ntok = alias_coherente(disp, l)
        tiene_nombres = bool((x.get("given") or "").strip() and (x.get("surname") or "").strip())
        if ora_n:
            unico = len(ora_n) == 1
            ind.append(f"nombre registrado en Oracle LAMB ({len(ora_n)} persona(s))")
            row.update(TipoCuenta="Personal",
                       SubtipoCuenta="Persona registrada en Oracle (por nombre)" if unico else "Posible cuenta personal",
                       Fuente="N3 · inferencia por nombre (MDM)",
                       NivelConfianza="Media" if unico else "Baja", RequiereRevisionManual="Sí",
                       MotivoClasificacion=("El nombre para mostrar corresponde a una persona registrada en el "
                                            "sistema académico, pero la cuenta no está vinculada a ella por correo "
                                            "ni gobernada por el IGA. Vínculo probable, no probado."
                                            if unico else
                                            f"El nombre coincide con {len(ora_n)} personas distintas en Oracle: "
                                            "no se puede atribuir sin revisión."))
        elif coh >= 2 or (coh == 1 and tiene_nombres):
            ind.append(f"el alias reproduce {coh} de {ntok} componentes del nombre")
            row.update(TipoCuenta="Personal", SubtipoCuenta="Personal individual no determinado",
                       Fuente="N3 · estructura del alias", NivelConfianza="Media",
                       RequiereRevisionManual="Sí",
                       MotivoClasificacion="La estructura del alias es compatible con un nombre y apellido y no "
                                           "se detectó ningún término de función institucional. No fue posible "
                                           "localizar a la persona en las fuentes institucionales.")
        elif tiene_nombres:
            row.update(TipoCuenta="Observado", SubtipoCuenta="Observado - posible cuenta personal",
                       Campus=sede, Fuente="N3 · sin evidencia", NivelConfianza="Baja",
                       RequiereRevisionManual="Sí",
                       MotivoClasificacion="Tiene nombre y apellido poblados, lo que sugiere una persona, pero el "
                                           "alias no es coherente con ese nombre y no aparece en ninguna fuente "
                                           "institucional.")
        else:
            row.update(TipoCuenta="Observado", SubtipoCuenta="Información insuficiente",
                       Campus=sede, Fuente="N3 · sin evidencia",
                       NivelConfianza="Revisión manual", RequiereRevisionManual="Sí",
                       MotivoClasificacion="No hay vínculo con ninguna fuente autoritativa ni indicios suficientes "
                                           "en el nombre. Requiere revisión humana.")
    if sede and not (area_nom or func_hit):
        row["MotivoClasificacion"] += (f" Se detectó «{sede}» en el alias, pero podría formar parte de un "
                                       f"apellido; no se usa como prueba de cuenta de sede.")
    row["IndicadoresDetectados"] = " · ".join(ind)
    out.append(row)

# ── separar dos conceptos que no son lo mismo ────────────────────────────────
# RequiereRevisionManual  = la CLASIFICACIÓN es dudosa (¿qué es esta cuenta?)
# FueraDelGobiernoIGA     = la clasificación es firme, pero el IGA no gobierna la cuenta
DUDOSO = ("Posible", "Observado", "no determinado", "contradictoria", "insuficiente", "sin identidad")
for r in out:
    r["FueraDelGobiernoIGA"] = "No" if (r["Fuente"].startswith("N1") or r["TipoCuenta"]=="Invitado externo") else "Sí"
    r["RequiereRevisionManual"] = "Sí" if (
        r["NivelConfianza"] in ("Baja","Revisión manual")
        or any(d.lower() in r["SubtipoCuenta"].lower() for d in DUDOSO)
        or (r["Fuente"].startswith("N1") and not r["ArchetypeMidPoint"])
    ) else "No"

json.dump(out, open(f"{SP}/clasificado.json","w"), ensure_ascii=False)

print("TOTAL:", len(out), "| entrada:", len(users), "| CUADRA" if len(out)==len(users) else "| ⚠ NO CUADRA")
print()
for k,v in Counter(r["Fuente"] for r in out).most_common(): print(f"  {v:7d}  {k}")
print()
for k,v in Counter(r["TipoCuenta"] for r in out).most_common(): print(f"  {v:7d}  {k}")
print()
print("confianza:", dict(Counter(r["NivelConfianza"] for r in out)))
print("clasificación dudosa (revisión manual):", sum(1 for r in out if r["RequiereRevisionManual"]=="Sí"))
print("fuera del gobierno del IGA:", sum(1 for r in out if r["FueraDelGobiernoIGA"]=="Sí"))
print("con área asignada:", sum(1 for r in out if r["AreaCargo"]))
