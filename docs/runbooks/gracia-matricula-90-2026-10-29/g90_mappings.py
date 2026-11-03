"""Gracia de matricula (N dias tras el fin real) — UNA sola fuente de texto para mappings y PATCH.

Piezas (ver README):
  G1  template  extension/F   = fin real con memoria (sube con la fuente; no baja si el semestre sale del
                               horizonte del feed; si baja ANTES del fin previsto es un retiro y se acepta)
  G2  template  extension/EFF = F + N   (N vive SOLO aqui; con 215/216 vivo EFF = F: la gracia no aplica)
  R1v3 template rango sobre 217: como R1v2 (retira si no hay cuenta e22 viva) SALVO dentro de la gracia
  T1  template  trigger de recompute en EFF+1 (patron N2-absence, ya probado en PROD) para la cuenta muerta
  IN  e22       inbound 217: 'student' si DATE_EXPIRY >= hoy (igual que hoy) o si hoy <= EFF del foco
Sin PII: la lista CANARIO no vive aqui; se inyecta desde un fichero fuera del repo (g90_build.py --canario).
"""
from xml.sax.saxutils import escape

NS = 'urn:sciback:midpoint:person'
E22 = '6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22'
N_DIAS = 90  # <- valor de despliegue; en PROD vive en el <code> de G2 (id 5849) y se cambia con UN PATCH

# ids (PROD template v137 max=5847; e22 v209 max=3380)
ID = dict(G1=5848, G2=5849, R1v3=5850, T1=5851, R1v3c=5852, T1c=5853, IN=3381, INc=3382)
ITEM_217 = 5830            # item[...] de liveAffiliationStudent (contiene R1v2 5844)
R1V2 = 5844
E22_OT, E22_ATTR, IN_OLD = 3297, 3324, 3327   # objectType / attribute SCHOOL_NAME / inbound actual


class Names:
    """Nombres de los items nuevos. En la simulacion se sustituyen por items YA definidos y sin uso."""
    def __init__(self, last='studentEnrollmentLastEnd', eff='studentEnrollmentEffectiveEnd'):
        self.last, self.eff = last, eff


HOY_REAL = "java.time.LocalDate.now(java.time.ZoneId.of('America/Lima'))"


def _pre(hoy):
    return ("def NS = '%s'\n"
            "def HOY = %s\n"
            "def fecha = { v -> def s = (v == null) ? '' : basic.stringify(v).trim(); "
            "(s ==~ /\\d{4}-\\d{2}-\\d{2}.*/) ? java.time.LocalDate.parse(s.substring(0, 10)) : null }\n") % (NS, hoy)


def _canario(names_list):
    return ("def CANARIO = [%s]  // vacio = todos\n"
            "def enCanario = CANARIO.isEmpty() || (basic.stringify(focus?.name) in CANARIO)\n"
            % ', '.join("'%s'" % n for n in names_list))


def g1_code(nm, hoy=HOY_REAL):
    return (_pre(hoy) +
            "// G1: fin real de la matricula CON MEMORIA. terminationDateStudent (IIA e22) puede BAJAR cuando un\n"
            "// semestre sale del horizonte del feed (medido 29-oct: 21 de los 46). Regla:\n"
            "//   sube o igual -> se acepta; baja con el fin previo YA pasado -> memoria (fin de modulo, no retiro);\n"
            "//   baja ANTES del fin previsto -> retiro/anulacion (cursos ESTADO=3) -> se acepta el valor menor.\n"
            "def t = fecha(terminationDateStudent)\n"
            "def prev = fecha(basic.getExtensionPropertyValue(focus, NS, '%s'))\n"
            "if (t == null) return prev?.toString()\n"
            "if (prev == null || !t.isBefore(prev)) return t.toString()\n"
            "if (HOY.isBefore(prev)) return t.toString()\n"
            "return prev.toString()\n") % nm.last


def g2_code(nm, n=N_DIAS):
    return ("// N = DIAS DE GRACIA tras el fin real de la matricula. UNICO SITIO donde vive N.\n"
            "// Cambiarlo = PATCH replace de este <code> (item mapping[%d]) y recompute de los afectados.\n"
            "def N = %d\n"
            "def s = (%s == null) ? '' : basic.stringify(%s).trim()\n"
            "if (!(s ==~ /\\d{4}-\\d{2}-\\d{2}.*/)) return null\n"
            "def fin = java.time.LocalDate.parse(s.substring(0, 10))\n"
            "// Alumno + personal/egresado: la gracia NO aplica (su estado lo sostiene 216/215; no cambian).\n"
            "def otro = [worker, alum].any { it != null &amp;&amp; basic.stringify(it).trim() != '' }\n"
            "return (otro ? fin : fin.plusDays(N)).toString()\n") % (ID['G2'], n, nm.last, nm.last)


def _gracia_muerta(nm):
    # cuenta e22 muerta: gracia si el fin real ya paso (no es un retiro) y hoy <= fin efectivo
    return ("def fin = fecha(basic.getExtensionPropertyValue(focus, NS, '%s'))\n"
            "def eff = fecha(basic.getExtensionPropertyValue(focus, NS, '%s'))\n"
            "def enGracia = fin != null &amp;&amp; eff != null &amp;&amp; !HOY.isBefore(fin) &amp;&amp; !HOY.isAfter(eff)\n"
            % (nm.last, nm.eff))


def r1v3_range(nm, canario=None, hoy=HOY_REAL):
    c = _pre(hoy)
    c += "if (input == null || basic.stringify(input).trim() == '') return false\n"
    if canario is not None:
        c += _canario(canario)
    c += ("def vivo\n"
          "try { vivo = midpoint.hasLinkedAccount('%s') } catch (Exception e) { log.warn('R1v3: hasLinkedAccount fallo en {}: {} -> no se retira', focus?.name, e.message); return false }\n"
          "if (vivo) return false\n" % E22)
    if canario is not None:
        c += "if (!enCanario) { log.warn('R1v3: retira {} de {} (sin cuenta viva, fuera del canario)', input, focus?.name); return true }\n"
    c += _gracia_muerta(nm)
    c += ("if (enGracia) return false\n"
          "log.warn('R1v3: retira {} de {} (sin cuenta e22 viva y fuera de la gracia: fin={} eff={})', input, focus?.name, fin, eff)\n"
          "return true\n")
    return c


def t1_code(nm, canario=None, hoy=HOY_REAL):
    c = ("import com.evolveum.midpoint.xml.ns._public.common.common_3.TriggerType\n"
         "import com.evolveum.midpoint.prism.xml.XmlTypeConverter\n") + _pre(hoy)
    c += ("def out = []\n"
          "def s217 = basic.getExtensionPropertyValue(focus, NS, 'liveAffiliationStudent')\n"
          "if (s217 == null || basic.stringify(s217).trim() == '') return out\n")
    if canario is not None:
        c += _canario(canario) + "if (!enCanario) return out\n"
    c += ("def vivo\n"
          "try { vivo = midpoint.hasLinkedAccount('%s') } catch (Exception e) { return out }\n"
          "if (vivo) return out\n" % E22)
    c += _gracia_muerta(nm)
    c += ("if (!enGracia) return out\n"
          "// Solo fechas ESTRICTAMENTE futuras (mismo guardarrail que N2: sin bucle al disparar).\n"
          "def d = eff.plusDays(1)\n"
          "if (!d.isAfter(HOY)) return out\n"
          "def ZONE = java.time.ZoneId.of('America/Lima')\n"
          "def t = new TriggerType()\n"
          "t.setHandlerUri('http://midpoint.evolveum.com/xml/ns/public/model/trigger/recompute/handler-3')\n"
          "t.setTimestamp(XmlTypeConverter.createXMLGregorianCalendar(d.atStartOfDay(ZONE).toInstant().toEpochMilli()))\n"
          "out.add(t)\n"
          "return out\n")
    return c


def inbound_code(nm, canario=None, hoy=HOY_REAL):
    c = _pre(hoy)
    c += ("// Matricula vigente segun la fuente (identico a 3327): sin fecha o fin >= hoy -> 'student'.\n"
          "def raw = basic.getAttributeValue(shadow, 'DATE_EXPIRY')\n"
          "if (raw == null) return 'student'\n"
          "def s = raw.toString().trim()\n"
          "if (s.length() < 10) return 'student'\n"
          "def f\n"
          "try { f = java.time.LocalDate.parse(s.substring(0, 10)) } catch (Exception ex) { return 'student' }\n"
          "if (!f.isBefore(HOY)) return 'student'\n")
    if canario is not None:
        c += _canario(canario) + "if (!enCanario) return null\n"
    c += ("// Fin vencido: gracia hasta el fin efectivo que publica el template (G2; ahi vive N).\n"
          "def eff = fecha(basic.getExtensionPropertyValue(focus, NS, '%s'))\n"
          "return (eff != null &amp;&amp; !HOY.isAfter(eff)) ? 'student' : null\n") % nm.eff
    return c


def _esc_code(code):
    # el codigo ya trae &amp;&amp; donde hace falta; escapamos < y > sueltos
    return code.replace('<', '&lt;').replace('>', '&gt;').replace('&lt;-', '&lt;-')


def _code(code):
    return '<c:code>\n%s</c:code>' % _esc_code(code).replace('-&gt;', '-&gt;')


def m_g1(nm, lc, hoy=HOY_REAL):
    return ('<c:mapping id="%d">\n'
            '  <c:name>G1-studentEnrollmentLastEnd-fin-real-con-memoria</c:name>\n'
            '  <c:description>Fin real de la matricula con memoria (gracia-matricula-90). Ver runbook gracia-matricula-90-2026-10-29.</c:description>\n'
            '  <c:lifecycleState>%s</c:lifecycleState>\n'
            '  <c:strength>strong</c:strength>\n'
            '  <c:source><c:path>extension/sciback:terminationDateStudent</c:path></c:source>\n'
            '  <c:expression><c:script>%s</c:script></c:expression>\n'
            '  <c:target><c:path>extension/sciback:%s</c:path></c:target>\n'
            '</c:mapping>') % (ID['G1'], lc, _code(g1_code(nm, hoy)), nm.last)


def m_g2(nm, lc, n=N_DIAS):
    return ('<c:mapping id="%d">\n'
            '  <c:name>G2-studentEnrollmentEffectiveEnd-fin-efectivo-con-gracia</c:name>\n'
            '  <c:description>Fin efectivo = fin real + N dias de gracia. UNICO sitio de N. Alumno con 215/216 vivo: sin gracia.</c:description>\n'
            '  <c:lifecycleState>%s</c:lifecycleState>\n'
            '  <c:strength>strong</c:strength>\n'
            '  <c:source><c:path>extension/sciback:%s</c:path></c:source>\n'
            '  <c:source><c:name>worker</c:name><c:path>extension/sciback:liveAffiliationWorker</c:path></c:source>\n'
            '  <c:source><c:name>alum</c:name><c:path>extension/sciback:liveAffiliationAlum</c:path></c:source>\n'
            '  <c:expression><c:script>%s</c:script></c:expression>\n'
            '  <c:target><c:path>extension/sciback:%s</c:path></c:target>\n'
            '</c:mapping>') % (ID['G2'], lc, nm.last, _code(g2_code(nm, n)), nm.eff)


def m_r1v3(nm, lc, canario=None, hoy=HOY_REAL):
    mid = ID['R1v3c'] if canario is not None else ID['R1v3']
    suf = '-canario' if canario is not None else ''
    return ('<c:mapping id="%d">\n'
            '  <c:name>R1v3-rango-retirar-liveAffiliationStudent-sin-cuenta-viva-salvo-gracia%s</c:name>\n'
            '  <c:lifecycleState>%s</c:lifecycleState>\n'
            '  <c:strength>strong</c:strength>\n'
            '  <c:source><c:path>extension/sciback:%s</c:path></c:source>\n'
            '  <c:source><c:path>extension/sciback:%s</c:path></c:source>\n'
            '  <c:expression><c:script><c:code>null</c:code></c:script></c:expression>\n'
            '  <c:target>\n'
            '    <c:path>extension/sciback:liveAffiliationStudent</c:path>\n'
            '    <c:set><c:condition><c:script>%s</c:script></c:condition></c:set>\n'
            '  </c:target>\n'
            '</c:mapping>') % (mid, suf, lc, nm.last, nm.eff, _code(r1v3_range(nm, canario, hoy)))


def m_t1(nm, lc, canario=None, hoy=HOY_REAL):
    mid = ID['T1c'] if canario is not None else ID['T1']
    suf = '-canario' if canario is not None else ''
    return ('<c:mapping id="%d">\n'
            '  <c:name>T1-gracia-matricula-recompute-trigger%s</c:name>\n'
            '  <c:description>Planta un trigger de recompute en fin efectivo + 1 dia para quien conserva 217 por gracia con la cuenta e22 muerta (nadie mas lo recompondria). Patron N2-absence.</c:description>\n'
            '  <c:lifecycleState>%s</c:lifecycleState>\n'
            '  <c:strength>strong</c:strength>\n'
            '  <c:source><c:path>extension/sciback:%s</c:path></c:source>\n'
            '  <c:source><c:path>extension/sciback:%s</c:path></c:source>\n'
            '  <c:expression><c:script>%s</c:script></c:expression>\n'
            '  <c:target><c:path>trigger</c:path></c:target>\n'
            '</c:mapping>') % (mid, suf, lc, nm.last, nm.eff, _code(t1_code(nm, canario, hoy)))


def i_inbound(nm, lc, canario=None, hoy=HOY_REAL):
    mid = ID['INc'] if canario is not None else ID['IN']
    suf = '-canario' if canario is not None else ''
    return ('<c:inbound id="%d">\n'
            '  <c:name>school-name-to-liveAffiliationStudent-con-gracia%s</c:name>\n'
            '  <c:lifecycleState>%s</c:lifecycleState>\n'
            '  <c:strength>strong</c:strength>\n'
            '  <c:expression><c:script>%s</c:script></c:expression>\n'
            '  <c:target><c:path>extension/sciback:liveAffiliationStudent</c:path></c:target>\n'
            '</c:inbound>') % (mid, suf, lc, _code(inbound_code(nm, canario, hoy)))


def schema_elements(nm):
    return ('                    <xsd:element maxOccurs="1" minOccurs="0" name="%s" type="xsd:string">\n'
            '                        <xsd:annotation><xsd:appinfo><a:displayName>Fin de matricula — real, con memoria (derivado)</a:displayName><a:help>YYYY-MM-DD. Lo calcula el template (G1) desde terminationDateStudent: sube con la fuente y NO baja cuando un semestre sale del horizonte del feed; si baja antes del fin previsto (retiro/anulacion) acepta el valor menor. Base del fin efectivo.</a:help><a:displayOrder>476</a:displayOrder></xsd:appinfo></xsd:annotation>\n'
            '                    </xsd:element>\n'
            '                    <xsd:element maxOccurs="1" minOccurs="0" name="%s" type="xsd:string">\n'
            '                        <xsd:annotation><xsd:appinfo><a:displayName>Fin de matricula — efectivo (con gracia)</a:displayName><a:help>YYYY-MM-DD. Fin real + N dias de gracia (template G2, unico sitio de N). Mientras hoy &lt;= este valor se conserva liveAffiliationStudent. Sin gracia si la persona tiene otro vinculo vivo (215/216). Base de la vigencia academica publicada a LDAP.</a:help><a:indexed>true</a:indexed><a:displayOrder>477</a:displayOrder></xsd:appinfo></xsd:annotation>\n'
            '                    </xsd:element>\n') % (nm.last, nm.eff)
