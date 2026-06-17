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
def client = new CrisClient(configuration.baseAddress?.toString(),
                            configuration.username?.toString(),
                            configuration.password instanceof char[] ? new String(configuration.password) : configuration.password?.toString(),
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
