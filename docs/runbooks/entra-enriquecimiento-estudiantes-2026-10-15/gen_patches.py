#!/usr/bin/env python3
"""Genera los PATCH del enriquecimiento Entra (estudiantes) para UPEU-EntraID-Graph (2f11c057).
Uso: python3 gen_patches.py <dir_salida>
Los ids de contenedor (340, 341...) son los de PROD v131 (leidos de m_resource el 15-oct-2026)."""
import sys, os
from xml.sax.saxutils import escape

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
CANARIOS = ['202512190']

GATE = """// GATE enriquecimiento Entra ID (2026-10-15). Escribe SOLO si:
//  (1) la persona es estudiante en esta fase: 'student' en sb:affiliations y su afiliacion
//      principal NO es de trabajador (faculty/staff/employee) -> las dobles afiliaciones
//      estudiante+trabajador quedan FUERA hasta decidir que ficha manda en el directorio; y
//  (2) es un canario de la lista, o el modo de ejecucion NO es persistente (simulacion).
// Para cualquier otro caso (incluida la recon diaria de las 02:00) -> false: cero efecto.
// Ante cualquier error -> false.
def canarios = [%s] as Set
def ok = false
try {
    if (focus != null) {
        def affs = basic.getExtensionPropertyValues(focus, 'urn:sciback:midpoint:person', 'affiliations')?.collect { it?.toString() } ?: []
        def pa = basic.getExtensionPropertyValue(focus, 'urn:sciback:midpoint:person', 'primaryAffiliation')?.toString()
        if (affs.contains('student') && !(pa in ['faculty', 'staff', 'employee'])) {
            def n = focus.getName()?.getOrig()
            if (n != null && canarios.contains(n)) {
                ok = true
            } else {
                def m = midpoint.getCurrentTask()?.getExecutionMode()
                ok = (m != null && !m.isFullyPersistent())
            }
        }
    }
} catch (Exception ex) {
    ok = false
}
return ok""" % ', '.join("'%s'" % c for c in CANARIOS)

TITLE = """// Nombres en formato Titulo (MidPoint los guarda en MAYUSCULAS desde Oracle/RENIEC).
// Particulas (de, del, la...) en minuscula salvo en primera posicion. Guiones respetados.
// Si el valor actual en Entra es el MISMO nombre y solo difiere en que Entra lleva MAS tildes
// (p.ej. Entra 'Gutierrez' con tilde y MidPoint sin ella), se conserva la grafia de Entra:
// el enriquecimiento no degrada un dato mejor que el de la fuente (medido: ~2%% de la poblacion).
def loc = new Locale('es', 'PE')
def low = ['de', 'del', 'la', 'las', 'los', 'y', 'e', 'da', 'das', 'do', 'dos', 'van', 'von'] as Set
def tc = { String t ->
    def out = []
    t.trim().toLowerCase(loc).split(/\\s+/).eachWithIndex { w, i ->
        if (i > 0 && low.contains(w)) { out << w }
        else { out << w.split('-').collect { p -> p ? p.substring(0, 1).toUpperCase(loc) + p.substring(1) : p }.join('-') }
    }
    out.join(' ')
}
def s = (%s ?: '').toString().trim()
if (!s) return null
def res = tc(s)
try {
    def cur = projection != null ? basic.getAttributeValue(projection, '%s')?.toString()?.trim() : null
    if (cur) {
        def nfd = { String t -> java.text.Normalizer.normalize(t, java.text.Normalizer.Form.NFD) }
        def base = { String t -> nfd(t).replaceAll(/\\p{M}/, '').toLowerCase(loc).split(/\\s+/).join(' ') }
        def marks = { String t -> nfd(t).findAll(/\\p{M}/).size() }
        if (base(cur) == base(res) && marks(cur) > marks(res)) { res = tc(cur) }
    }
} catch (Exception ex) { }
return res"""

DEPT = """// Escuela profesional = org con archetype Academic-Program (9f3b8e2a) entre los parentOrgRef
// (relacion default = miembro). Formato del nombre oficial de LAMB: 'EP ' + displayName, sin el
// sufijo desambiguador entre parentesis (p.ej. 'Psicologia (FCS)' -> 'EP Psicologia').
// 0 o 2+ escuelas -> null (no se adivina; tolerant: no borra lo que haya).
def ARCH = '9f3b8e2a-4c7d-4b1e-a8f5-6d2c4e9a1b73'
def names = [] as LinkedHashSet
for (ref in (focus?.getParentOrgRef() ?: [])) {
    def rel = ref.getRelation()
    if (rel != null && rel.getLocalPart() != 'default') continue
    try {
        def org = midpoint.getObject(com.evolveum.midpoint.xml.ns._public.common.common_3.OrgType.class, ref.getOid())
        if (org.getArchetypeRef()?.any { it.getOid() == ARCH }) {
            def dn = org.getDisplayName()?.getOrig() ?: org.getName()?.getOrig()
            if (dn) names << dn.replaceAll(/\\s*\\([^)]*\\)\\s*$/, '').trim()
        }
    } catch (Exception ex) { }
}
if (names.size() != 1) return null
def d = names.iterator().next()
return d.startsWith('EP ') ? d : 'EP ' + d"""

JOB = """def v = (studyLevel ?: '').toString().trim().toLowerCase(new Locale('es', 'PE')).replace('-', ' ')
switch (v) {
    case 'pregrado': return 'Estudiante de pregrado'
    case 'posgrado': return 'Estudiante de posgrado'
    case 'doctorado': return 'Estudiante de doctorado'
    case 'segunda especialidad': return 'Estudiante de segunda especialidad'
    case 'idiomas': return 'Estudiante de idiomas'
    case 'cepre': return 'Estudiante de CEPRE'
    default: return 'Estudiante'
}"""

OFFICE = """def v = (campusStudent ?: '').toString().trim().toUpperCase()
return ['LIMA': 'Sede Lima', 'JULIACA': 'Filial Juliaca', 'TARAPOTO': 'Filial Tarapoto'].get(v)"""
CITY = """def v = (campusStudent ?: '').toString().trim().toUpperCase()
return ['LIMA': 'Lima', 'JULIACA': 'Juliaca', 'TARAPOTO': 'Tarapoto'].get(v)"""
EMPID = """def v = (lambIdPersona ?: '').toString().trim()
return v ? v : null"""


def mapping(name, desc, expr, sources=(), const=None, strength='strong'):
    x = '<c:name>%s</c:name><c:description>%s</c:description><c:strength>%s</c:strength>' % (name, escape(desc), strength)
    for path, var in sources:
        x += '<c:source><c:name>%s</c:name><c:path>%s</c:path></c:source>' % (var, path)
    if const is not None:
        x += '<c:expression><c:value>%s</c:value></c:expression>' % escape(const)
    else:
        x += '<c:expression><c:script><c:code>%s</c:code></c:script></c:expression>' % escape(expr)
    x += '<c:condition><c:script><c:code>%s</c:code></c:script></c:condition>' % escape(GATE)
    return x


D = 'Enriquecimiento Entra ID de estudiantes (2026-10-15, runbook entra-enriquecimiento-estudiantes-2026-10-15). '
EXISTING = {
    344: mapping('entra-enrich-givenName', D + 'givenName <- focus givenName (formato Titulo).', TITLE % ('givenName', 'givenName'), [('$focus/givenName', 'givenName')]),
    346: mapping('entra-enrich-surname', D + 'surname <- focus familyName (formato Titulo).', TITLE % ('familyName', 'surname'), [('$focus/familyName', 'familyName')]),
    352: mapping('entra-enrich-employeeId', D + 'employeeId <- ID_PERSONA de LAMB (upeu:lambIdPersona): ancla de correlacion.', EMPID, [('$focus/extension/upeu:lambIdPersona', 'lambIdPersona')]),
    354: mapping('entra-enrich-jobTitle', D + 'jobTitle <- nivel de estudios (sb:studyLevel).', JOB, [('$focus/extension/sb:studyLevel', 'studyLevel')]),
}
NEW = [
    ('employeeType', mapping('entra-enrich-employeeType', D + 'employeeType = Estudiante.', None, const='Estudiante')),
    ('department', mapping('entra-enrich-department', D + 'department <- escuela profesional (org EP-* archetype Academic-Program).', DEPT)),
    ('officeLocation', mapping('entra-enrich-officeLocation', D + 'officeLocation <- campus (sb:campusStudent).', OFFICE, [('$focus/extension/sb:campusStudent', 'campusStudent')])),
    ('city', mapping('entra-enrich-city', D + 'city <- campus (sb:campusStudent).', CITY, [('$focus/extension/sb:campusStudent', 'campusStudent')])),
    ('country', mapping('entra-enrich-country', D + 'country = Peru.', None, const='Perú')),
    ('companyName', mapping('entra-enrich-companyName', D + 'companyName = Universidad Peruana Union.', None, const='Universidad Peruana Unión')),
    ('usageLocation', mapping('entra-enrich-usageLocation', D + 'usageLocation = PE solo si esta vacio (weak): 50 estudiantes tienen ES/US/... puesto a mano y usageLocation condiciona licencias.', None, const='PE', strength='weak')),
]
INBOUNDS = [(341, 342), (341, 343), (344, 345), (346, 347), (348, 349), (350, 351), (352, 353), (354, 355)]
REACTIONS = [361, 363, 365, 366]
OT = 'c:schemaHandling/c:objectType[340]'

HDR = '''<objectModification xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3"
    xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
    xmlns:t="http://prism.evolveum.com/xml/ns/public/types-3"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:ri="http://midpoint.evolveum.com/xml/ns/public/resource/instance-3"
    xmlns:cap="http://midpoint.evolveum.com/xml/ns/public/resource/capabilities-3"
    xmlns:sb="urn:sciback:midpoint:person"
    xmlns:upeu="urn:upeu:midpoint:local">
'''


def delta(kind, path, value, typ=None):
    t = ' xsi:type="%s"' % typ if typ else ''
    return '  <itemDelta><t:modificationType>%s</t:modificationType><t:path>%s</t:path><t:value%s>%s</t:value></itemDelta>\n' % (kind, path, t, value)


# PATCH A: preparar (objectType sigue en proposed -> cero efecto en produccion)
a = HDR
a += delta('replace', 'c:description', escape('Microsoft Graph API · tenant upeu.edu.pe · LECTURA + enriquecimiento de estudiantes (outbound con GATE: solo simulacion y canarios; ver docs/runbooks/entra-enriquecimiento-estudiantes-2026-10-15). Nunca create/delete.'))
for at, ib in INBOUNDS:
    a += delta('replace', '%s/c:attribute[%d]/c:inbound[%d]/c:lifecycleState' % (OT, at, ib), 'proposed')
a += delta('replace', '%s/c:activation/c:administrativeStatus/c:inbound[358]/c:lifecycleState' % OT, 'proposed')
for r in REACTIONS:
    a += delta('replace', '%s/c:synchronization/c:reaction[%d]/c:lifecycleState' % (OT, r), 'proposed')
for at, m in EXISTING.items():
    a += delta('replace', '%s/c:attribute[%d]/c:outbound' % (OT, at), m)
for ref, m in NEW:
    a += delta('add', '%s/c:attribute' % OT, '<c:ref>ri:%s</c:ref><c:outbound>%s</c:outbound>' % (ref, m), 'c:ResourceAttributeDefinitionType')
a += delta('replace', 'c:capabilities/c:configured/cap:update/cap:enabled', 'true')
a += '</objectModification>\n'
open(os.path.join(OUT, 'patchA-preparar-outbounds-gate.xml'), 'w').write(a)

# PATCH A2 (2026-10-15, tras la simulacion): tildes en nombres + usageLocation weak
a2 = HDR
a2 += delta('replace', '%s/c:attribute[344]/c:outbound' % OT, EXISTING[344])
a2 += delta('replace', '%s/c:attribute[346]/c:outbound' % OT, EXISTING[346])
a2 += delta('replace', '%s/c:attribute[438]/c:outbound' % OT, dict(NEW)['usageLocation'])
a2 += '</objectModification>\n'
open(os.path.join(OUT, 'patchA2-tildes-usageLocation-weak.xml'), 'w').write(a2)

# PATCH B: ventana de prueba -> objectType visible en produccion
b = HDR + delta('replace', '%s/c:lifecycleState' % OT, 'active') + '</objectModification>\n'
open(os.path.join(OUT, 'patchB-ventana-objecttype-active.xml'), 'w').write(b)
# PATCH C: cierre de la ventana -> objectType de vuelta a proposed (estado de produccion de siempre)
c = HDR + delta('replace', '%s/c:lifecycleState' % OT, 'proposed') + '</objectModification>\n'
open(os.path.join(OUT, 'patchC-cierre-objecttype-proposed.xml'), 'w').write(c)
print('ok')
