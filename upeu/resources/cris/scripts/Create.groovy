/*
 * Create.groovy — provisiona OrgUnit o Person en DSpace-CRIS (PerúCRIS) y devuelve su uuid.
 *
 * UPSERT: si el objeto ya existe (Search lo resolvió), MidPoint llama Update, no Create.
 * Aun así, Create re-verifica existencia (defensa anti-duplicado) y, si existe, delega en
 * applyMetadata + relaciones (upsert real).
 *
 * Contrato PerúCRIS v1.1 (verificado):
 *   OrgUnit:
 *     dspace.entity.type = OrgUnit  (UN SOLO valor — duplicarlo rompe la indexación)
 *     organization.legalName
 *     organization.parentOrganization (authority = uuid del padre, valor = nombre)
 *     perucris.orgunit.tiposubunidad (URI del vocab) — solo DGI/CII/líneas/grupos
 *     [solo raíz UPeU] perucris.orgunit.tipoinstitucion #06 + naturaleza #privada
 *                      + sector #ensenanzaSuperior + organization.identifier (RUC)
 *     NO organizationType (vocab 404)
 *   Person:
 *     dspace.entity.type = Person (un solo valor)
 *     dc.title "Apellidos, Nombres"
 *     person.givenName / person.familyName / person.email
 *     person.identifier.orcid / perucris.person.dni
 *     Colección destino: Investigadores (6460c5ef-29d4-45b1-b92b-18ccd057f476)
 *   Afiliación: relación CERIF Person↔OrgUnit relationshipType 5
 *     (isOrgUnitOfPerson / isPersonOfOrgUnit), repetible, principal en place 0.
 *
 * Creación del item entidad en DSpace 7+/9:
 *   POST /core/items?owningCollection={collectionUuid}  con metadata + "inArchive":true.
 *   La colección owning fija el entityType vía su plantilla; además seteamos
 *   dspace.entity.type explícito (un solo valor) por robustez.
 */
// --- carga dinámica del helper CrisClient (opción 1) ---
// El RESTConnector compila cada *ScriptFileName aislado: 'import CrisClient' no resuelve
// ni los static (mdVal/constantes). Cargamos la clase con GroovyClassLoader (cache JVM-wide
// por path+lastModified), instanciamos vía newInstance y accedemos a los static por reflexión
// sobre el objeto Class (CRIS = clase cargada).
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
def client = CRIS.newInstance(configuration.baseAddress?.toString(),
                            configuration.username?.toString(),
                            configuration.password instanceof char[] ? new String(configuration.password) : configuration.password?.toString(),
                            log)
client.login()

// Acceso a static helpers/constantes de CrisClient vía el objeto Class.
def mdVal = { String value, Integer place = null, String authority = null -> CRIS.mdVal(value, place, authority) }
def COLLECTION_INVESTIGADORES = CRIS.COLLECTION_INVESTIGADORES

String oc = objectClass.objectClassValue
def a = { String n -> def v = attributes.findResult { it.name == n ? it.value : null }; (v && v.size() > 0) ? v[0]?.toString() : null }
def aMulti = { String n -> def v = attributes.findResult { it.name == n ? it.value : null }; v ?: [] }

if (oc == 'orgUnit') {
    return upsertOrgUnit(client, a, mdVal)
} else if (oc == 'person') {
    return upsertPerson(client, a, aMulti, mdVal, COLLECTION_INVESTIGADORES)
}
throw new RuntimeException('objectClass no soportado en Create: ' + oc)

// ============================ ORGUNIT ============================
def upsertOrgUnit(def client, Closure a, Closure mdVal) {
    String legalName = a('legalName')
    if (!legalName) throw new RuntimeException('OrgUnit sin legalName')

    String existing = client.findOrgUnitUuid(legalName)
    def md = [:]
    md['dspace.entity.type'] = [mdVal('OrgUnit', 0)]   // SINGLE value
    md['organization.legalName'] = [mdVal(legalName, 0)]
    md['dc.title'] = [mdVal(legalName, 0)]

    String parentUuid = a('parentOrganizationUuid')
    String parentName = a('parentOrganizationName')
    if (parentName) {
        md['organization.parentOrganization'] = [ mdVal(parentName, 0, parentUuid) ]
    }
    String tiposub = a('tiposubunidad')
    if (tiposub) md['perucris.orgunit.tiposubunidad'] = [mdVal(tiposub, 0)]

    if (a('esRaiz') == 'true') {
        md['perucris.orgunit.tipoinstitucion'] = [mdVal('https://catalogos.concytec.gob.pe/vocabulario/concytec_tipoInstitucion.xml#06', 0)]
        md['perucris.orgunit.naturalezajuridica'] = [mdVal('privada', 0)]
        md['perucris.orgunit.sector'] = [mdVal('ensenanzaSuperior', 0)]
        if (a('ruc')) md['organization.identifier'] = [mdVal(a('ruc'), 0)]
    }

    if (existing) {
        client.patchReplaceAll(existing, md)
        log.info('CRIS OrgUnit upsert (update) ' + legalName + ' uuid=' + existing)
        return existing
    }
    // OrgUnit collection no la indicó el contrato → se crea en la colección OrgUnit del CRIS.
    // El connector net.tirasa.connid.bundles.rest.RESTConnector v1.1.0 NO expone una
    // propiedad de configuración personalizada para esto (su esquema es fijo:
    // baseAddress/username/password/*ScriptFileName/clientId/...). Por eso el uuid de la
    // colección OrgUnit se mantiene como constante (verificado en CRIS:
    // dcca9716-6620-4fc8-b7bb-68a4fd0494ff), con override opcional si algún día el
    // connector lo soporta vía binding.
    String coll = (configuration.hasProperty('orgUnitCollectionUuid') ? configuration.orgUnitCollectionUuid?.toString() : null) ?: 'dcca9716-6620-4fc8-b7bb-68a4fd0494ff'
    String uuid = client.createItem(coll, md, 'OrgUnit')
    log.info('CRIS OrgUnit creado ' + legalName + ' uuid=' + uuid)
    return uuid
}

// ============================ PERSON ============================
def upsertPerson(def client, Closure a, Closure aMulti, Closure mdVal, String COLLECTION_INVESTIGADORES) {
    String orcid = a('orcid')
    String dni = a('dni')
    String existing = client.findPersonUuid(orcid, dni)

    def md = [:]
    md['dspace.entity.type'] = [mdVal('Person', 0)]   // SINGLE value
    if (a('dcTitle')) md['dc.title'] = [mdVal(a('dcTitle'), 0)]
    if (a('givenName')) md['person.givenName'] = [mdVal(a('givenName'), 0)]
    if (a('familyName')) md['person.familyName'] = [mdVal(a('familyName'), 0)]
    if (a('email')) md['person.email'] = [mdVal(a('email'), 0)]
    if (orcid) md['person.identifier.orcid'] = [mdVal(orcid, 0)]
    if (dni) md['perucris.person.dni'] = [mdVal(dni, 0)]

    String uuid
    if (existing) {
        client.patchReplaceAll(existing, md)
        uuid = existing
        log.info('CRIS Person upsert (update) ' + a('dcTitle') + ' uuid=' + uuid)
    } else {
        uuid = client.createItem(COLLECTION_INVESTIGADORES, md, 'Person')
        log.info('CRIS Person creado ' + a('dcTitle') + ' uuid=' + uuid)
    }

    // Afiliaciones CERIF (relationshipType 5). place 0 = principal (dependencia laboral).
    def affs = aMulti('affiliationOrgUnitUuid')
    client.syncPersonAffiliations(uuid, affs.collect { it.toString() })
    return uuid
}
