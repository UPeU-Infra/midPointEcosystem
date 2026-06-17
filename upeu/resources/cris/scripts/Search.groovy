/*
 * Search.groovy — resolución de UID/existencia para upsert idempotente.
 *
 * MidPoint llama Search para:
 *   (a) reconciliar (listar) — NO soportado masivamente aquí (CRIS no es IIA); devolvemos
 *       solo el objeto pedido por filtro EqualsFilter en __NAME__ o __UID__.
 *   (b) resolver existencia antes de Create/Update.
 *
 * Person:  __NAME__ = 'orcid:<ORCID>' | 'dni:<DNI>'  → busca por metadato.
 * OrgUnit: __NAME__ = legalName                      → busca por organization.legalName.
 * __UID__ = uuid DSpace → GET directo /core/items/{uuid}.
 *
 * Devuelve handler(uid, name, attrs) por cada match. Si no hay match, no emite nada
 * (MidPoint lo interpreta como inexistente → Create).
 */
// --- carga dinámica del helper CrisClient (opción 1) ---
def __crisClass = {
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
def client = __crisClass.newInstance(configuration.baseAddress?.toString(),
                            configuration.username?.toString(),
                            __pwd,
                            log)
client.login()

String oc = objectClass.objectClassValue
def emit = { String uid, String name ->
    handler {
        uid uid
        id name
        attribute '__NAME__', name
    }
}

// filter puede ser null (full scan — devolvemos vacío para no inundar) o un EqualsFilter
if (filter == null) {
    log.info('CRIS Search sin filtro: no-op (CRIS no es fuente autoritativa, no se reconcilia masivamente).')
    return
}

def attrName = filter.attributeName    // '__NAME__' o '__UID__'
def value = filter.attributeValue ? filter.attributeValue[0]?.toString() : null
if (!value) return

if (attrName == '__UID__') {
    def r = client.getJson('/core/items/' + value)
    if (r.code == 200 && r.json?.uuid) emit(r.json.uuid, r.json?.name ?: value)
    return
}

// attrName == '__NAME__'
if (oc == 'person') {
    String orcid = null, dni = null
    if (value.startsWith('orcid:')) orcid = value.substring(6)
    else if (value.startsWith('dni:')) dni = value.substring(4)
    else orcid = value
    def uuid = client.findPersonUuid(orcid, dni)
    if (uuid) emit(uuid, value)
} else if (oc == 'orgUnit') {
    def uuid = client.findOrgUnitUuid(value)
    if (uuid) emit(uuid, value)
}
