/*
 * Update.groovy — actualización idempotente de OrgUnit / Person ya existente en CRIS.
 *
 * MidPoint llama Update cuando el shadow ya está vinculado (uid conocido). Aplica
 * el mismo upsert que Create (metadatos PerúCRIS + afiliaciones CERIF), pero sobre
 * el uuid existente (no re-crea). Reutiliza CrisClient.
 *
 * uid = uuid DSpace del item. attributes = metadatos PerúCRIS emitidos por MidPoint.
 */
// --- carga dinámica del helper CrisClient (opción 1) ---
def CRIS = {
    def f = new File('/opt/midpoint/var/cris-scripts/CrisClient.groovy')
    def key = 'CRIS_CLIENT_CLASS@' + f.lastModified()
    def cache = System.getProperties()
    def cached = cache.get(key)
    if (cached != null) return cached
    def cl = new GroovyClassLoader(this.class.classLoader)
    def c = cl.parseClass(f)
    cache.put(key, c)
    return c
}()
// El RESTConnector (Tirasa) entrega configuration.password como GuardedString;
// hay que desencriptarlo vía Accessor — .toString() devuelve el handle del objeto, no la clave.
def __pwd = {
    def p = configuration.password
    if (p == null) return null
    if (p instanceof org.identityconnectors.common.security.GuardedString) {
        def sb = new StringBuilder()
        p.access({ chars -> sb.append(chars) } as org.identityconnectors.common.security.GuardedString.Accessor)
        return sb.toString()
    }
    if (p instanceof char[]) return new String(p)
    return p.toString()
}()
def client = CRIS.newInstance(configuration.baseAddress?.toString(),
                            configuration.username?.toString(),
                            __pwd,
                            log)
client.login()
def mdVal = { String value, Integer place = null, String authority = null -> CRIS.mdVal(value, place, authority) }

// RESTConnector v1.1.0 pasa objectClass como String en Create/Update pero como ObjectClass
// en Search. Manejo defensivo para ambos casos.
// RESTConnector v1.1.0 pasa objectClass como String en Create/Update pero como ObjectClass
// en Search. Manejo defensivo para ambos casos.
String oc = (objectClass instanceof String) ? objectClass : objectClass.objectClassValue
String itemUuid = uid.uidValue
// RESTConnector v1.1.0 pasa attributes como Map<String,List> en Create/Update.
def a = { String n ->
    if (attributes instanceof Map) {
        def v = attributes.get(n)
        return (v instanceof List && v.size() > 0) ? v[0]?.toString() : v?.toString()
    }
    def v = attributes.findResult { it.name == n ? it.value : null }
    return (v && v.size() > 0) ? v[0]?.toString() : null
}
def aMulti = { String n ->
    if (attributes instanceof Map) {
        def v = attributes.get(n)
        return (v instanceof List) ? v : (v == null ? [] : [v])
    }
    def v = attributes.findResult { it.name == n ? it.value : null }
    return v ?: []
}

def md = [:]
if (oc == 'orgUnit') {
    md['dspace.entity.type'] = [mdVal('OrgUnit', 0)]
    if (a('legalName')) { md['organization.legalName'] = [mdVal(a('legalName'), 0)]; md['dc.title'] = [mdVal(a('legalName'), 0)] }
    if (a('parentOrganizationName')) md['organization.parentOrganization'] = [mdVal(a('parentOrganizationName'), 0, a('parentOrganizationUuid'))]
    if (a('tiposubunidad')) md['perucris.orgunit.tiposubunidad'] = [mdVal(a('tiposubunidad'), 0)]
    if (a('esRaiz') == 'true') {
        md['perucris.orgunit.tipoinstitucion'] = [mdVal('https://catalogos.concytec.gob.pe/vocabulario/concytec_tipoInstitucion.xml#06', 0)]
        md['perucris.orgunit.naturalezajuridica'] = [mdVal('privada', 0)]
        md['perucris.orgunit.sector'] = [mdVal('ensenanzaSuperior', 0)]
        if (a('ruc')) md['organization.identifier'] = [mdVal(a('ruc'), 0)]
    }
    client.patchReplaceAll(itemUuid, md)
} else if (oc == 'person') {
    md['dspace.entity.type'] = [mdVal('Person', 0)]
    if (a('dcTitle')) md['dc.title'] = [mdVal(a('dcTitle'), 0)]
    if (a('givenName')) md['person.givenName'] = [mdVal(a('givenName'), 0)]
    if (a('familyName')) md['person.familyName'] = [mdVal(a('familyName'), 0)]
    if (a('email')) md['person.email'] = [mdVal(a('email'), 0)]
    if (a('orcid')) md['person.identifier.orcid'] = [mdVal(a('orcid'), 0)]
    if (a('dni')) md['perucris.person.dni'] = [mdVal(a('dni'), 0)]
    client.patchReplaceAll(itemUuid, md)
    client.syncPersonAffiliations(itemUuid, aMulti('affiliationOrgUnitUuid').collect { it.toString() })
} else {
    throw new RuntimeException('objectClass no soportado en Update: ' + oc)
}
return uid.uidValue
