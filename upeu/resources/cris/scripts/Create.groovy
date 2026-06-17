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
import CrisClient

def client = new CrisClient(configuration.baseAddress?.toString(),
                            configuration.username?.toString(),
                            configuration.password instanceof char[] ? new String(configuration.password) : configuration.password?.toString(),
                            log)
client.login()

String oc = objectClass.objectClassValue
def a = { String n -> def v = attributes.findResult { it.name == n ? it.value : null }; (v && v.size() > 0) ? v[0]?.toString() : null }
def aMulti = { String n -> def v = attributes.findResult { it.name == n ? it.value : null }; v ?: [] }

if (oc == 'orgUnit') {
    return upsertOrgUnit(client, a)
} else if (oc == 'person') {
    return upsertPerson(client, a, aMulti)
}
throw new RuntimeException('objectClass no soportado en Create: ' + oc)

// ============================ ORGUNIT ============================
String upsertOrgUnit(CrisClient client, Closure a) {
    String legalName = a('legalName')
    if (!legalName) throw new RuntimeException('OrgUnit sin legalName')

    String existing = client.findOrgUnitUuid(legalName)
    def md = [:]
    md['dspace.entity.type'] = [CrisClient.mdVal('OrgUnit', 0)]   // SINGLE value
    md['organization.legalName'] = [CrisClient.mdVal(legalName, 0)]
    md['dc.title'] = [CrisClient.mdVal(legalName, 0)]

    String parentUuid = a('parentOrganizationUuid')
    String parentName = a('parentOrganizationName')
    if (parentName) {
        md['organization.parentOrganization'] = [ CrisClient.mdVal(parentName, 0, parentUuid) ]
    }
    String tiposub = a('tiposubunidad')
    if (tiposub) md['perucris.orgunit.tiposubunidad'] = [CrisClient.mdVal(tiposub, 0)]

    if (a('esRaiz') == 'true') {
        md['perucris.orgunit.tipoinstitucion'] = [CrisClient.mdVal('https://catalogos.concytec.gob.pe/vocabulario/concytec_tipoInstitucion.xml#06', 0)]
        md['perucris.orgunit.naturalezajuridica'] = [CrisClient.mdVal('privada', 0)]
        md['perucris.orgunit.sector'] = [CrisClient.mdVal('ensenanzaSuperior', 0)]
        if (a('ruc')) md['organization.identifier'] = [CrisClient.mdVal(a('ruc'), 0)]
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
String upsertPerson(CrisClient client, Closure a, Closure aMulti) {
    String orcid = a('orcid')
    String dni = a('dni')
    String existing = client.findPersonUuid(orcid, dni)

    def md = [:]
    md['dspace.entity.type'] = [CrisClient.mdVal('Person', 0)]   // SINGLE value
    if (a('dcTitle')) md['dc.title'] = [CrisClient.mdVal(a('dcTitle'), 0)]
    if (a('givenName')) md['person.givenName'] = [CrisClient.mdVal(a('givenName'), 0)]
    if (a('familyName')) md['person.familyName'] = [CrisClient.mdVal(a('familyName'), 0)]
    if (a('email')) md['person.email'] = [CrisClient.mdVal(a('email'), 0)]
    if (orcid) md['person.identifier.orcid'] = [CrisClient.mdVal(orcid, 0)]
    if (dni) md['perucris.person.dni'] = [CrisClient.mdVal(dni, 0)]

    String uuid
    if (existing) {
        client.patchReplaceAll(existing, md)
        uuid = existing
        log.info('CRIS Person upsert (update) ' + a('dcTitle') + ' uuid=' + uuid)
    } else {
        uuid = client.createItem(CrisClient.COLLECTION_INVESTIGADORES, md, 'Person')
        log.info('CRIS Person creado ' + a('dcTitle') + ' uuid=' + uuid)
    }

    // Afiliaciones CERIF (relationshipType 5). place 0 = principal (dependencia laboral).
    def affs = aMulti('affiliationOrgUnitUuid')
    client.syncPersonAffiliations(uuid, affs.collect { it.toString() })
    return uuid
}
