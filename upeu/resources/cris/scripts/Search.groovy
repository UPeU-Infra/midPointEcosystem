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
 * RESTConnector v1.1.0 (Tirasa): usa el paradigma results = [] (lista de Maps ConnId)
 * en lugar del paradigma handler{} closure. Cada resultado es un ConnectorObject.
 */
import org.identityconnectors.framework.common.objects.ConnectorObjectBuilder
import org.identityconnectors.framework.common.objects.AttributeBuilder
import org.identityconnectors.framework.common.objects.Uid
import org.identityconnectors.framework.common.objects.Name

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

// RESTConnector v1.1.0 puede pasar objectClass como String (sin método objectClassValue).
String oc = (objectClass instanceof String) ? objectClass : objectClass.objectClassValue

// Inicializar results (paradigma Tirasa RESTConnector — handler{} no es el patrón aquí).
results = []

// El RESTConnector v1.1.0 puede pasar el filtro como 'filter' o 'query' según la operación.
// Acceso defensivo para compatibilidad.
def __filter = null
try { __filter = filter } catch (MissingPropertyException e) {}
if (__filter == null) {
    try { __filter = query } catch (MissingPropertyException e) {}
}
if (__filter == null) {
    log.info('CRIS Search sin filtro: no-op (CRIS no es fuente autoritativa, no se reconcilia masivamente).')
    return results
}

// Helper: emitir un ConnectorObject con __UID__ y __NAME__
def emit = { String uuid, String name ->
    def bob = new ConnectorObjectBuilder()
    bob.setObjectClass(objectClass instanceof org.identityconnectors.framework.common.objects.ObjectClass
                        ? objectClass
                        : new org.identityconnectors.framework.common.objects.ObjectClass(oc))
    bob.setUid(uuid)
    bob.setName(name)
    results << bob.build()
}

def attrName = null
def filterValue = null
try {
    // EqualsFilter
    attrName = __filter.attribute?.name ?: __filter.attributeName
    def vals = __filter.attribute?.value ?: __filter.attributeValue
    filterValue = (vals && !vals.isEmpty()) ? vals[0]?.toString() : null
} catch (Exception e) {
    log.warn('CRIS Search: no se pudo extraer atributo del filtro: ' + e.message)
}
if (!filterValue) return results

if (attrName == Uid.NAME || attrName == '__UID__') {
    def r = client.getJson('/core/items/' + filterValue)
    if (r.code == 200 && r.json?.uuid) emit(r.json.uuid, r.json?.name ?: filterValue)
    return results
}

// attrName == '__NAME__' / Name.NAME
if (oc == 'person') {
    String orcid = null, dni = null
    if (filterValue.startsWith('orcid:')) orcid = filterValue.substring(6)
    else if (filterValue.startsWith('dni:')) dni = filterValue.substring(4)
    else orcid = filterValue
    def uuid = client.findPersonUuid(orcid, dni)
    if (uuid) emit(uuid, filterValue)
} else if (oc == 'orgUnit') {
    def uuid = client.findOrgUnitUuid(filterValue)
    if (uuid) emit(uuid, filterValue)
}

return results
