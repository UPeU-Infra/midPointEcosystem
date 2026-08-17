#!/usr/bin/env python3
"""Entregable 3: informe técnico y ejecutivo en HTML."""
import json, datetime, html
from collections import Counter, defaultdict

SP="/private/tmp/claude-501/-Users-alberto-proyectos-productos-iga/ca1dd53b-d6bb-4df4-95a3-78d21daf87b8/scratchpad"
HOY=datetime.datetime.now(datetime.timezone.utc); FECHA=HOY.strftime("%Y-%m-%d")
OUT=f"/Users/alberto/Downloads/Informe_Analisis_Cuentas_Institucionales_{FECHA}.html"

act=json.load(open(f"{SP}/actividad.json"))
T=len(act)
def pct(n): return f"{100*n/T:.1f}%"
def m(n): return f"{n:,}".replace(",",".")

tipo=Counter(a["TipoCuenta"] for a in act)
fuente=Counter(a["Fuente"] for a in act)
estado=Counter(a["EstadoActividad"] for a in act)
riesgo=Counter(a["NivelRiesgoInactividad"] for a in act)
conf=Counter(a["NivelConfianza"] for a in act)
dominio=Counter(a["dominio"] for a in act)
aut=sum(1 for a in act if a["Fuente"].startswith(("N1","N2")))
inf=sum(1 for a in act if a["Fuente"].startswith("N3"))
rev=sum(1 for a in act if a["RequiereRevisionManual"]=="Sí")
aband=sum(1 for a in act if a["PotencialmenteAbandonada"]=="Sí")
sinbuzon=sum(1 for a in act if not a["mail"])
deshab=sum(1 for a in act if a["habilitada"]=="No")
byarea=defaultdict(list)
for a in act:
    if a["AreaCargo"]: byarea[a["AreaCargo"]].append(a)

def barras(counter, total, color="#2E5496", top=None, orden=None):
    items = orden if orden else [k for k,_ in counter.most_common(top)]
    out=[]
    for k in items:
        v=counter.get(k,0)
        if not v and orden is None: continue
        w=100*v/total
        out.append(f'<tr><td class="lbl">{html.escape(str(k))}</td><td class="num">{m(v)}</td>'
                   f'<td class="num pc">{100*v/total:.1f}%</td>'
                   f'<td class="bar"><span style="width:{max(w,0.4):.2f}%;background:{color}"></span></td></tr>')
    return "\n".join(out)

areas_top="\n".join(
    f'<tr><td>{html.escape(a)}</td><td class="num">{m(len(rs))}</td>'
    f'<td class="num">{m(sum(1 for r in rs if r["Fuente"].startswith(("N1","N2"))))}</td>'
    f'<td class="num">{m(sum(1 for r in rs if r["EstadoActividad"] in ("Inactiva >2 años","Nunca inició sesión")))}</td></tr>'
    for a,rs in sorted(byarea.items(), key=lambda x:-len(x[1]))[:20])

H=f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe de análisis de cuentas institucionales — UPeU</title>
<style>
:root{{--tinta:#12181f;--suave:#5b6672;--linea:#dde3ea;--fondo:#fff;--panel:#f6f8fa;
--azul:#2E5496;--navy:#1F3864;--verde:#2e7d52;--ambar:#b8860b;--rojo:#b3391c;}}
@media (prefers-color-scheme:dark){{:root{{--tinta:#e7ecf2;--suave:#9aa7b4;--linea:#2b333d;
--fondo:#11161c;--panel:#171e26;}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--fondo);color:var(--tinta);
font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 28px 80px}}
header{{background:var(--navy);color:#fff;padding:44px 28px;margin-bottom:36px}}
header .in{{max-width:1080px;margin:0 auto}}
header h1{{margin:0 0 8px;font-size:29px;line-height:1.25;font-weight:650}}
header p{{margin:0;opacity:.85;font-size:15px}}
h2{{font-size:21px;margin:44px 0 4px;padding-top:22px;border-top:2px solid var(--linea);font-weight:650}}
h2 .n{{color:var(--azul);font-variant-numeric:tabular-nums;margin-right:10px}}
h3{{font-size:16.5px;margin:26px 0 8px;font-weight:650}}
p{{margin:11px 0}}
table{{width:100%;border-collapse:collapse;margin:16px 0;font-size:14.5px}}
th{{background:var(--panel);text-align:left;padding:9px 11px;border-bottom:2px solid var(--linea);font-weight:650}}
td{{padding:8px 11px;border-bottom:1px solid var(--linea);vertical-align:middle}}
td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
td.pc{{color:var(--suave)}}
td.lbl{{width:33%}}
td.bar{{width:40%;padding-right:0}}
td.bar span{{display:block;height:11px;border-radius:2px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:13px;margin:22px 0}}
.kpi{{background:var(--panel);border:1px solid var(--linea);border-radius:9px;padding:15px 17px}}
.kpi b{{display:block;font-size:27px;font-variant-numeric:tabular-nums;line-height:1.15}}
.kpi span{{font-size:12.5px;color:var(--suave);display:block;margin-top:4px;line-height:1.4}}
.nota{{background:var(--panel);border-left:3px solid var(--azul);padding:13px 17px;margin:18px 0;
border-radius:0 7px 7px 0;font-size:14.5px}}
.alerta{{border-left-color:var(--rojo)}}
.ok{{border-left-color:var(--verde)}}
ul,ol{{padding-left:22px}} li{{margin:6px 0}}
.meta{{color:var(--suave);font-size:13.5px}}
code{{background:var(--panel);padding:1px 5px;border-radius:4px;font-size:13px}}
@media print{{header{{background:#1F3864!important;-webkit-print-color-adjust:exact}}h2{{page-break-after:avoid}}}}
</style></head><body>
<header><div class="in">
<h1>Análisis, clasificación y depuración de cuentas institucionales</h1>
<p>Microsoft 365 / Entra ID · Universidad Peruana Unión · {FECHA}</p>
</div></header>
<div class="wrap">

<h2><span class="n">1</span>Resumen ejecutivo</h2>
<p>Se analizaron <b>{m(T)}</b> cuentas del tenant institucional, repartidas en {len(dominio)} dominios.
El objetivo fue determinar qué es cada cuenta, a quién pertenece y si sigue en uso, para poder ordenar
y depurar el entorno con criterio.</p>

<div class="kpis">
<div class="kpi"><b>{m(T)}</b><span>cuentas analizadas</span></div>
<div class="kpi"><b>{m(aut)}</b><span>clasificadas con fuente autoritativa ({pct(aut)})</span></div>
<div class="kpi"><b>{m(tipo.get('Personal',0))}</b><span>cuentas personales</span></div>
<div class="kpi"><b>{m(tipo.get('Administrativa',0))}</b><span>administrativas o de cargo</span></div>
<div class="kpi"><b>{m(estado.get('Activa 2026',0))}</b><span>con actividad en 2026 ({pct(estado.get('Activa 2026',0))})</span></div>
<div class="kpi"><b>{m(aband)}</b><span>potencialmente abandonadas</span></div>
</div>

<p><b>El hallazgo principal no es de clasificación, sino de gobierno.</b> Los datos muestran que
<b>{pct(estado.get('Nunca inició sesión',0))} del tenant ({m(estado.get('Nunca inició sesión',0))} cuentas)
no registra ningún inicio de sesión</b>, y que otro {pct(estado.get('Inactiva >2 años',0))} lleva más de dos
años sin uso. Frente a ese volumen, solo <b>{m(deshab)}</b> cuentas figuran deshabilitadas en todo el
directorio. Los datos sugieren que el entorno crea cuentas de forma sistemática pero carece de un
proceso equivalente de cierre.</p>

<div class="nota"><b>Sobre la certeza de las cifras.</b> Este informe distingue explícitamente entre lo
verificado y lo inferido. <b>{m(aut)} cuentas ({pct(aut)})</b> se clasificaron heredando el dato de los
sistemas que ya gobiernan la identidad en la universidad; <b>{m(inf)} ({pct(inf)})</b> se clasificaron
por inferencia sobre el nombre y deben tratarse como hipótesis. <b>{m(rev)}</b> cuentas quedan marcadas
para revisión manual.</p>

<h2><span class="n">2</span>Objetivo</h2>
<p>Identificar el tipo de cada cuenta (personal, administrativa o de cargo, servicio, invitado externo),
determinar el área o unidad responsable de las cuentas funcionales, establecer su estado de actividad y
señalar las que presentan indicios de abandono, separando con claridad lo que se sabe con certeza de lo
que requiere validación humana.</p>

<h2><span class="n">3</span>Metodología</h2>
<p>El requerimiento original planteaba deducir la naturaleza de cada cuenta analizando semánticamente su
nombre, correo y atributos de texto. Ese método se conserva, pero <b>deja de ser el punto de partida</b>:
la universidad ya dispone de sistemas que gobiernan la identidad, y su dato es preferible a cualquier
inferencia. La clasificación se resuelve por una cascada de procedencia, y cada registro declara en qué
nivel se resolvió.</p>
<table>
<tr><th>Nivel</th><th>Fuente</th><th class="num">Cuentas</th><th class="num">%</th><th>Naturaleza</th></tr>
<tr><td><b>N0</b></td><td>Forma de la cuenta</td><td class="num">{m(sum(v for k,v in fuente.items() if k.startswith('N0')))}</td><td class="num">{pct(sum(v for k,v in fuente.items() if k.startswith('N0')))}</td><td>Regla objetiva</td></tr>
<tr><td><b>N1</b></td><td>MidPoint (foco de identidad)</td><td class="num">{m(fuente.get('N1 · MidPoint (foco de identidad)',0))}</td><td class="num">{pct(fuente.get('N1 · MidPoint (foco de identidad)',0))}</td><td>Heredado, verificado</td></tr>
<tr><td><b>N2a</b></td><td>Oracle LAMB · correo institucional</td><td class="num">{m(fuente.get('N2a · Oracle LAMB (correo institucional)',0))}</td><td class="num">{pct(fuente.get('N2a · Oracle LAMB (correo institucional)',0))}</td><td>Heredado, verificado</td></tr>
<tr><td><b>N2b</b></td><td>Oracle LAMB · documento en el alias</td><td class="num">{m(fuente.get('N2b · Oracle LAMB (documento en el alias)',0))}</td><td class="num">{pct(fuente.get('N2b · Oracle LAMB (documento en el alias)',0))}</td><td>Heredado, verificado</td></tr>
<tr><td><b>N3</b></td><td>Inferencia semántica sobre el nombre</td><td class="num">{m(inf)}</td><td class="num">{pct(inf)}</td><td>Hipótesis</td></tr>
</table>
<p>Las etiquetas de salida tampoco se inventaron. La afiliación usa <code>eduPersonAffiliation</code>
(<i>student</i>, <i>alum</i>, <i>staff</i>, <i>faculty</i>), el estándar internacional que el modelo de
identidad de la universidad ya adopta. El área procede del <b>catálogo real de 103 unidades</b> del árbol
organizativo, con su denominación oficial, en lugar de un diccionario de palabras clave construido para
la ocasión.</p>
<p class="meta">Se verificó el repositorio de vocabularios controlados de la institución: contiene nueve
esquemas, todos del dominio académico (programas, facultades, líneas de investigación). <b>No existe
todavía un vocabulario de unidades administrativas</b>, por lo que se utilizó el árbol organizativo como
catálogo de referencia. Publicar esas unidades como esquema SKOS es una de las recomendaciones de este
informe.</p>

<h3>Regla contra falsos positivos</h3>
<p>Se mantuvo íntegra: una coincidencia de palabra no basta para clasificar. Cuando aparecen indicios
simultáneos de persona y de función institucional, o cuando un nombre coincide con varias personas
distintas, la cuenta se marca como observada en lugar de forzar una categoría. Un término como
«lima» o «juliaca» en el alias se registra como indicio, nunca como prueba, porque puede formar parte
de un apellido.</p>

<h2><span class="n">4</span>Resultados de clasificación</h2>
<table><tr><th>Tipo de cuenta</th><th class="num">Cuentas</th><th class="num">%</th><th></th></tr>
{barras(tipo,T)}</table>
<h3>Nivel de confianza</h3>
<table><tr><th>Confianza</th><th class="num">Cuentas</th><th class="num">%</th><th></th></tr>
{barras(conf,T,"#1F6F6F")}</table>

<h2><span class="n">5</span>Resultados por área administrativa</h2>
<p>Se identificaron cuentas atribuibles a <b>{len(byarea)}</b> unidades institucionales. La columna
«con fuente autoritativa» indica cuántas de ellas se heredaron de un sistema de gobierno de identidad
y no de una inferencia.</p>
<table><tr><th>Área o unidad</th><th class="num">Cuentas</th><th class="num">Autoritativas</th><th class="num">Sin uso &gt;2 años o nunca</th></tr>
{areas_top}</table>

<h2><span class="n">6</span>Resultados de actividad</h2>
<p class="meta">Fecha de referencia: {FECHA}. «Activa» significa inicio de sesión interactivo, es decir,
una persona autenticándose. El acceso automático (refresco de tokens) no se cuenta como uso humano.</p>
<table><tr><th>Estado de actividad</th><th class="num">Cuentas</th><th class="num">%</th><th></th></tr>
{barras(estado,T,"#2e7d52",orden=["Activa 2026","Cuenta creada recientemente","Inactiva 1-2 años","Inactiva >2 años","Nunca inició sesión","Información insuficiente"])}</table>

<h2><span class="n">7</span>Análisis de riesgo</h2>
<table><tr><th>Nivel de riesgo por inactividad</th><th class="num">Cuentas</th><th class="num">%</th><th></th></tr>
{barras(riesgo,T,"#b3391c",orden=["Bajo","Medio","Alto","Crítico / revisión prioritaria"])}</table>
<div class="nota alerta"><b>Este indicador prioriza revisión; no autoriza eliminación.</b> Una cuenta sin
actividad puede corresponder a una persona vinculada que no usa el correo institucional, a un buzón de
área con uso esporádico o a un registro que nunca llegó a entregarse a su titular. Ninguna cuenta
debería deshabilitarse por figurar en esta tabla sin validación previa del área responsable.</div>

<h2><span class="n">8</span>Hallazgos técnicos</h2>
<ol>
<li><b>Ausencia de un proceso de cierre de cuentas.</b> Con {m(estado.get('Nunca inició sesión',0))}
cuentas sin ningún acceso registrado y {m(estado.get('Inactiva >2 años',0))} sin uso en más de dos años,
solo {m(deshab)} figuran deshabilitadas. Los datos sugieren que el alta está automatizada y la baja no.</li>
<li><b>Buzones creados y nunca abiertos.</b> Existen cuentas con buzón aprovisionado que jamás
registraron un inicio de sesión. Conviene verificar si consumen licencia.</li>
<li><b>{m(sinbuzon)} cuentas sin buzón de correo.</b> Son objetos de identidad sin servicio de correo
asociado; requieren determinar su propósito.</li>
<li><b>Cobertura parcial del gobierno de identidad.</b> Solo {pct(fuente.get('N1 · MidPoint (foco de identidad)',0))}
de las cuentas corresponde a una identidad gobernada por el IGA. Un grupo relevante existe en el sistema
académico y en M365, pero no en el gobierno de identidad: son cuentas reales de personas reales que
ningún proceso de bajas alcanzará.</li>
<li><b>Nomenclatura heterogénea.</b> Conviven el formato <code>nombre.apellido</code>, el formato sin
separador y alias numéricos derivados del documento de identidad. Esa mezcla es la causa de que existan
personas con más de una cuenta y de que la clasificación automática sea ambigua.</li>
<li><b>Invitados externos.</b> Se detectaron invitaciones dirigidas a dominios inexistentes por error
tipográfico, que nunca podrán aceptarse y permanecen en el directorio.</li>
</ol>

<h2><span class="n">9</span>Interpretación ejecutiva</h2>
<p><b>¿Cuántas cuentas parecen realmente necesarias?</b> Con actividad demostrable en 2026 hay
{m(estado.get('Activa 2026',0))} ({pct(estado.get('Activa 2026',0))}). El resto no es necesariamente
prescindible, pero sí es el universo sobre el que hay que decidir.</p>
<p><b>¿Cuántas corresponden a personas y cuántas a funciones?</b> {m(tipo.get('Personal',0))} se
identificaron como personales y {m(tipo.get('Administrativa',0))} como administrativas o de cargo. La
cifra de administrativas debe leerse como un mínimo: solo se contabilizan las que pudieron atribuirse
a una unidad del catálogo institucional.</p>
<p><b>¿Qué volumen exige revisión humana?</b> {m(rev)} cuentas ({pct(rev)}). Es un volumen alto y es
deliberado: se prefirió marcar para revisión antes que arriesgar una clasificación incorrecta.</p>
<p><b>¿Qué información adicional haría falta?</b> Tres cosas concretas: el permiso de lectura de
informes de Microsoft, que daría la serie histórica real de uso; la asignación de un responsable a cada
cuenta funcional, hoy inexistente; y cerrar la brecha entre las personas que el sistema académico conoce
y las que el gobierno de identidad administra.</p>

<h2><span class="n">10</span>Recomendaciones</h2>
<ol>
<li><b>Asignar un responsable a cada cuenta funcional.</b> Es la medida de mayor efecto. Una cuenta de
área sin dueño seguirá sin dueño por bien clasificada que esté en una hoja de cálculo; el responsable
debe registrarse en el sistema de gobierno de identidad, no en un documento paralelo.</li>
<li><b>Definir una política de ciclo de vida</b> que incluya el cierre, con criterios explícitos de
deshabilitación previa a cualquier eliminación y un periodo de gracia.</li>
<li><b>Empezar la depuración por el riesgo crítico</b> ({m(riesgo.get('Crítico / revisión prioritaria',0))}
cuentas antiguas sin ningún acceso registrado), validando con cada área antes de actuar.</li>
<li><b>Estandarizar la nomenclatura</b> en <code>nombre.apellido</code> para personas y un prefijo
reconocible para cuentas de área, y renombrar los alias numéricos heredados.</li>
<li><b>Separar cuentas personales de funcionales</b>, incluido el nombre para mostrar: hoy varios buzones
de área llevan el nombre de quien los administra, lo que los hace indistinguibles de una cuenta personal.</li>
<li><b>Publicar el catálogo de unidades como vocabulario controlado</b> en el repositorio institucional,
para que exista una sola denominación de área compartida por todos los sistemas.</li>
<li><b>Cerrar la brecha de cobertura del gobierno de identidad</b>, incorporando a las personas que hoy
solo existen en el sistema académico y en M365.</li>
<li><b>Repetir esta medición periódicamente</b> con el mismo método, para poder comparar.</li>
</ol>

<h2><span class="n">11</span>Conclusiones</h2>
<p>El inventario está <b>ordenado en cuanto a datos y desordenado en cuanto a gobierno</b>. La
información existe y es de calidad suficiente para clasificar casi la mitad del tenant sin recurrir a
suposiciones; lo que falta no es dato, sino proceso: nadie cierra lo que se abre y nadie responde por
las cuentas que no son de una persona concreta.</p>
<p>La calidad de la clasificación es alta donde hay fuente autoritativa y explícitamente incierta donde
no la hay. Esa separación es el principal valor de este informe: permite actuar con confianza sobre
{m(aut)} cuentas y saber exactamente sobre cuáles no se debe actuar sin verificar antes.</p>
<p>El riesgo mayor no es tener cuentas de más, sino <b>no saber de quién es cada una</b>. Mientras cada
cuenta funcional no tenga un responsable identificado, cualquier depuración se hará a ciegas y volverá a
degradarse en unos meses.</p>

<p class="meta" style="margin-top:40px;padding-top:18px;border-top:1px solid var(--linea)">
Medición de solo lectura sobre Microsoft Graph, el sistema de gobierno de identidad y el sistema
académico. No se modificó ninguna cuenta ni ningún registro. Las cifras de este informe coinciden con
los dos archivos de análisis que lo acompañan.</p>
</div></body></html>"""

open(OUT,"w",encoding="utf-8").write(H)
print("ENTREGABLE 3:",OUT)
print("total:",T,"| autoritativas:",aut,"| inferidas:",inf,"| revisión:",rev)
