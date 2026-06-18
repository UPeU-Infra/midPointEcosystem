/*
 * CrisClient.groovy — helper común para los scripts ScriptedREST del resource DSpace-CRIS UPeU.
 *
 * Encapsula:
 *   - Autenticación DSpace 7+/9 REST: CSRF (DSPACE-XSRF-TOKEN) + login JWT (Bearer).
 *   - Upsert idempotente de items entidad (OrgUnit / Person) por búsqueda previa.
 *   - Emisión del contrato PerúCRIS v1.1 (entity.type single-value, tiposubunidad,
 *     parentOrganization, person.identifier.orcid, perucris.person.dni).
 *   - Relación CERIF Person↔OrgUnit (relationshipType id 5, isOrgUnitOfPerson /
 *     isPersonOfOrgUnit), repetible, principal en place 0.
 *
 * NO usa librerías externas: solo java.net.http.HttpClient (JDK 11+, soporta PATCH) + groovy.json.
 * El connector ScriptedREST (net.tirasa.connid.bundles.rest) inyecta las
 * configurationProperties (baseUrl/username/password) en cada script como binding.
 *
 * IMPORTANTE — contrato PerúCRIS verificado (Fase 5):
 *   - dspace.entity.type DEBE ser un solo valor por item; duplicarlo rompe la indexación.
 *   - Solo la raíz UPeU lleva perucris.orgunit.tipoinstitucion #06 + naturaleza #privada
 *     + sector #ensenanzaSuperior + RUC. Facultades/carreras: solo parentOrganization.
 *   - tiposubunidad: #unidadDeInvestigacionOInnovacion (DGI + 7 CII),
 *                    #lineaDeInvestigacion (líneas), #grupoDeInvestigacion (grupos RENACYT).
 *   - NO poblar organizationType (vocab 404).
 *   - Person collection destino: "Investigadores" (uuid 6460c5ef-29d4-45b1-b92b-18ccd057f476).
 */

import groovy.json.JsonSlurper
import groovy.json.JsonOutput

class CrisClient {

    String baseUrl          // p.ej. https://cris.upeu.edu.pe/server/api  (sin / final)
    String username
    String password
    def log

    String jwt
    String xsrf
    String cookieHeader

    // Vocabularios PerúCRIS (verificados)
    static final String VOC_TIPOSUBUNIDAD = 'https://catalogos.concytec.gob.pe/vocabulario/concytec_tipoSubunidad.xml'
    static final String TIPOSUB_UNIDAD_INV = VOC_TIPOSUBUNIDAD + '#unidadDeInvestigacionOInnovacion'
    static final String TIPOSUB_LINEA_INV  = VOC_TIPOSUBUNIDAD + '#lineaDeInvestigacion'
    static final String TIPOSUB_GRUPO_INV  = VOC_TIPOSUBUNIDAD + '#grupoDeInvestigacion'
    static final String COLLECTION_INVESTIGADORES = '6460c5ef-29d4-45b1-b92b-18ccd057f476'
    static final int RELTYPE_PERSON_ORGUNIT = 5   // isOrgUnitOfPerson / isPersonOfOrgUnit

    CrisClient(String baseUrl, String username, String password, def log) {
        this.baseUrl = baseUrl?.replaceAll('/+$', '')
        this.username = username
        this.password = password
        this.log = log
    }

    // ---------- bajo nivel HTTP ----------
    // Cliente HTTP. Se usa java.net.http.HttpClient (JDK 11+, módulo java.net.http) en
    // lugar de java.net.HttpURLConnection porque este último NO soporta el método PATCH
    // (setRequestMethod("PATCH") lanza ProtocolException: Invalid HTTP method: PATCH) y
    // el workaround por reflection sobre el campo privado `method` está bloqueado por el
    // module system en Java 21 (InaccessibleObjectException, java.base no abierto).
    // DSpace REST requiere un PATCH HTTP real (X-HTTP-Method-Override NO lo respeta → 415).
    // HttpClient.method("PATCH", ...) emite un PATCH nativo sin restricciones.
    private static final java.net.http.HttpClient HTTP =
        java.net.http.HttpClient.newBuilder()
            .connectTimeout(java.time.Duration.ofSeconds(20))
            .followRedirects(java.net.http.HttpClient.Redirect.NEVER)
            .build()

    private Map raw(String method, String path, Map headers, byte[] body) {
        def uri = java.net.URI.create(path.startsWith('http') ? path : (baseUrl + path))
        def bp = (body != null) ? java.net.http.HttpRequest.BodyPublishers.ofByteArray(body)
                                : java.net.http.HttpRequest.BodyPublishers.noBody()
        def rb = java.net.http.HttpRequest.newBuilder(uri)
            .timeout(java.time.Duration.ofSeconds(60))
            .method(method, bp)
        headers?.each { k, v -> if (v != null) rb.header(k.toString(), v.toString()) }
        def resp = HTTP.send(rb.build(), java.net.http.HttpResponse.BodyHandlers.ofString(java.nio.charset.StandardCharsets.UTF_8))
        int code = resp.statusCode()
        String text = resp.body() ?: ''
        // capturar set-cookie (XSRF), DSPACE-XSRF-TOKEN y Authorization de la respuesta.
        def hdrs = resp.headers()
        def setCookies = hdrs.allValues('Set-Cookie')
        def xsrfHeader = hdrs.firstValue('DSPACE-XSRF-TOKEN').orElse(null)
        def authHeader = hdrs.firstValue('Authorization').orElse(null)
        return [code: code, text: text, setCookies: setCookies, xsrfHeader: xsrfHeader, authHeader: authHeader]
    }

    private Map authHeaders(Map extra = [:]) {
        def h = [:]
        if (jwt) h['Authorization'] = 'Bearer ' + jwt
        if (xsrf) h['X-XSRF-TOKEN'] = xsrf
        if (cookieHeader) h['Cookie'] = cookieHeader
        h.putAll(extra)
        return h
    }

    private void captureXsrf(Map resp) {
        if (resp.xsrfHeader) xsrf = resp.xsrfHeader
        if (resp.setCookies) {
            resp.setCookies.each { c ->
                if (c?.startsWith('DSPACE-XSRF-COOKIE')) {
                    def kv = c.split(';')[0]
                    xsrf = kv.split('=', 2)[1]
                    cookieHeader = kv
                }
            }
        }
    }

    // ---------- autenticación ----------
    void login() {
        // 1) GET status para recibir el token CSRF
        def s = raw('GET', '/authn/status', [:], null)
        captureXsrf(s)
        // 2) POST login con CSRF + credenciales (form-encoded)
        def form = 'user=' + URLEncoder.encode(username, 'UTF-8') + '&password=' + URLEncoder.encode(password, 'UTF-8')
        def headers = ['Content-Type': 'application/x-www-form-urlencoded']
        if (xsrf) headers['X-XSRF-TOKEN'] = xsrf
        if (cookieHeader) headers['Cookie'] = cookieHeader
        def r = raw('POST', '/authn/login', headers, form.getBytes('UTF-8'))
        captureXsrf(r)
        if (r.authHeader && r.authHeader.startsWith('Bearer ')) {
            jwt = r.authHeader.substring(7)
        }
        if (!jwt) throw new RuntimeException('CRIS login fallo (sin JWT). code=' + r.code + ' body=' + safeMsg(r.text?.take(300)))
        log?.info('CRIS login OK')
    }

    Map getJson(String path) {
        def r = raw('GET', path, authHeaders(['Accept': 'application/json']), null)
        return [code: r.code, json: (r.text ? new JsonSlurper().parseText(r.text) : null)]
    }

    Map postJson(String path, Object payload) {
        def r = raw('POST', path, authHeaders(['Content-Type': 'application/json', 'Accept': 'application/json']),
                    JsonOutput.toJson(payload).getBytes('UTF-8'))
        captureXsrf(r)
        return [code: r.code, json: (r.text ? safeJson(r.text) : null), text: r.text]
    }

    Map patchJson(String path, Object payload) {
        // PATCH de metadatos DSpace (operaciones add/replace)
        def r = raw('PATCH', path, authHeaders(['Content-Type': 'application/json', 'Accept': 'application/json']),
                    JsonOutput.toJson(payload).getBytes('UTF-8'))
        captureXsrf(r)
        return [code: r.code, json: (r.text ? safeJson(r.text) : null), text: r.text]
    }

    Map postText(String path, String contentType, String payload) {
        def r = raw('POST', path, authHeaders(['Content-Type': contentType, 'Accept': 'application/json']),
                    payload.getBytes('UTF-8'))
        captureXsrf(r)
        return [code: r.code, json: (r.text ? safeJson(r.text) : null), text: r.text]
    }

    private static Object safeJson(String t) {
        try { return new JsonSlurper().parseText(t) } catch (ignored) { return null }
    }

    // DEFECTO 1 (Fase 5): el connector ConnId (net.tirasa RESTConnector) loguea los
    // mensajes de excepción y los strings de log vía org.identityconnectors.common.logging.Log,
    // cuyo .info/.warn/.error/.ok ejecutan java.text.MessageFormat sobre el mensaje como PATRÓN.
    // El cuerpo de error JSON de DSpace ({"timestamp":...,"status":...}) contiene llaves '{'
    // que MessageFormat interpreta como placeholders → IllegalArgumentException:
    //   "can't parse argument number: \"timestamp\"".
    // Eso ENMASCARA el status+body real (el script muere formateando, no reportando).
    // Solución: neutralizar las llaves de TODO texto de error de DSpace antes de incluirlo
    // en cualquier log o mensaje de excepción. Es texto diagnóstico → sustituir '{' '}' por
    // '(' ')' (no se reinterpretan como placeholders). NO afecta los payloads enviados a DSpace
    // (esos van por JsonOutput.toJson, nunca por aquí).
    static String safeMsg(String t) {
        if (t == null) return ''
        return t.replace('{', '(').replace('}', ')')
    }

    // ---------- creación / actualización de items ----------
    // Crea un item-entidad en una colección owning. entityType refuerza dspace.entity.type.
    String createItem(String owningCollectionUuid, Map metadata, String entityType) {
        if (!owningCollectionUuid) throw new RuntimeException('createItem: owningCollectionUuid nulo (entityType=' + entityType + ')')
        def payload = [ name: (metadata['dc.title']?.getAt(0)?.value ?: entityType),
                        inArchive: true, discoverable: true, withdrawn: false,
                        type: 'item', metadata: metadata ]
        def r = postJson('/core/items?owningCollection=' + owningCollectionUuid, payload)
        if (r.code != 201 && r.code != 200) {
            throw new RuntimeException('createItem ' + entityType + ' fallo code=' + r.code + ' body=' + safeMsg(r.text?.take(800)))
        }
        return r.json?.uuid
    }

    // Reemplaza (replace/add) cada metadato del mapa en un item existente vía PATCH JSON.
    void patchReplaceAll(String itemUuid, Map metadata) {
        // DSpace PATCH: [{op:'replace', path:'/metadata/<field>/0', value:{...}}] o add si no existe.
        def ops = []
        metadata.each { field, vals ->
            // estrategia simple y robusta: replace del array completo del campo (op 'replace' sobre /metadata/<field>)
            // DSpace acepta replace del array si el campo ya existe; usamos add que crea o reemplaza.
            ops << [ op: 'add', path: '/metadata/' + field, value: vals ]
        }
        if (ops.isEmpty()) return
        def r = patchJson('/core/items/' + itemUuid, ops)
        if (r.code != 200) {
            log?.warn('patchReplaceAll code=' + r.code + ' body=' + safeMsg(r.text?.take(400)))
        }
    }

    // ---------- afiliaciones CERIF (relationshipType 5) ----------
    // DEFECTO 2 (Fase 5): la afiliación CERIF Person↔OrgUnit no se escribía. Tres causas:
    //   (1) syncPersonAffiliations recibía los NOMBRES (legalName) de las orgs que emite el
    //       outbound del Person, pero los trataba como uuids → POST uri-list con un nombre →
    //       relación inválida / no creada. FIX: resolver cada nombre a uuid vía findOrgUnitUuid.
    //   (2) Si el OrgUnit del Centro CII aún no existe en CRIS (su provisión por la object class
    //       orgUnit no corrió), findOrgUnitUuid devuelve null → sin relación. FIX: auto-crear un
    //       OrgUnit mínimo (entity.type=OrgUnit + legalName) on-demand para que la afiliación sea
    //       autocontenida e idempotente; la metadata rica (tiposubunidad/parent) la completa el
    //       recompute del OrgType en su object class.
    //   (3) El orden de la afiliación principal lo gobierna rightPlace (posición del OrgUnit dentro
    //       de la Person), NO leftPlace. Verificado en vivo: las 85 relaciones reltype-5 del CRIS
    //       tienen leftPlace=0 fijo y rightPlace variable. Principal = índice 0 → rightPlace 0.
    //
    // orgUnitNames en orden de prioridad; índice 0 = afiliación principal (dependencia laboral).
    void syncPersonAffiliations(String personUuid, List<String> orgUnitNames) {
        if (!orgUnitNames) return
        // relaciones reltype-5 existentes de la persona (key = uuid del OrgUnit) para no duplicar
        def existing = listPersonOrgUnitRelations(personUuid)
        orgUnitNames.eachWithIndex { name, idx ->
            if (!name) return
            String ouUuid = findOrgUnitUuid(name)
            if (!ouUuid) {
                // OrgUnit aún no provisionado en CRIS → crear mínimo (idempotente por legalName).
                ouUuid = ensureMinimalOrgUnit(name)
            }
            if (!ouUuid) {
                log?.warn('syncPersonAffiliations: no se pudo resolver/crear OrgUnit legalName=' + name + ' (afiliación omitida)')
                return
            }
            if (existing.containsKey(ouUuid)) return    // ya afiliado → idempotente
            createPersonOrgUnitRelation(personUuid, ouUuid, idx)
        }
    }

    // Crea un OrgUnit mínimo (entity.type=OrgUnit + legalName) si no existe, y devuelve su uuid.
    private String ensureMinimalOrgUnit(String legalName) {
        String existing = findOrgUnitUuid(legalName)
        if (existing) return existing
        def md = [:]
        md['dspace.entity.type'] = [mdVal('OrgUnit', 0)]
        md['organization.legalName'] = [mdVal(legalName, 0)]
        md['dc.title'] = [mdVal(legalName, 0)]
        String coll = 'dcca9716-6620-4fc8-b7bb-68a4fd0494ff'
        String uuid = createItem(coll, md, 'OrgUnit')
        log?.info('CRIS OrgUnit mínimo creado on-demand para afiliación: ' + legalName + ' uuid=' + uuid)
        return uuid
    }

    // Lista las relaciones reltype-5 (Person↔OrgUnit) de la persona. key = uuid OrgUnit, val = relId.
    // El JSON de cada relación NO incluye el id del relationshipType inline: hay que seguir el link
    // _links.relationshipType.href → GET → comparar id == 5 (verificado en vivo). Una persona tiene
    // pocas afiliaciones → coste despreciable.
    private Map listPersonOrgUnitRelations(String personUuid) {
        def map = [:]
        def r = getJson('/core/items/' + personUuid + '/relationships')
        def rels = r.json?._embedded?.relationships
        rels?.each { rel ->
            def rtHref = rel?._links?.relationshipType?.href?.toString()
            if (!rtHref) return
            def rt = getJson(rtHref.replace(baseUrl, ''))
            if (rt.json?.id == RELTYPE_PERSON_ORGUNIT) {
                def ouUuid = rel?._links?.rightItem?.href?.toString()?.tokenize('/')?.last()
                if (ouUuid) map[ouUuid] = rel.id
            }
        }
        return map
    }

    private void createPersonOrgUnitRelation(String personUuid, String orgUnitUuid, int rightPlace) {
        // POST /core/relationships?relationshipType=5
        // body text/uri-list: primera URI = leftItem (Person), segunda = rightItem (OrgUnit).
        def uriList = baseUrl + '/core/items/' + personUuid + '\n' + baseUrl + '/core/items/' + orgUnitUuid
        def r = postText('/core/relationships?relationshipType=' + RELTYPE_PERSON_ORGUNIT, 'text/uri-list', uriList)
        if (r.code != 201 && r.code != 200) {
            log?.warn('createPersonOrgUnitRelation code=' + r.code + ' body=' + safeMsg(r.text?.take(400)))
            return
        }
        def relId = r.json?.id
        // rightPlace ordena el OrgUnit dentro de la Person: índice 0 = afiliación principal.
        if (relId != null && rightPlace > 0) {
            patchJson('/core/relationships/' + relId, [[op: 'replace', path: '/rightPlace', value: rightPlace]])
        }
        log?.info('CRIS afiliación CERIF creada person=' + personUuid + ' orgUnit=' + orgUnitUuid + ' rightPlace=' + rightPlace + ' relId=' + relId)
    }

    // ---------- helpers de metadatos DSpace ----------
    static Map mdVal(String value, Integer place = null, String authority = null) {
        // DSpace 9 REST: language y confidence son requeridos en la deserialización
        // aunque sean null/-1. Su ausencia puede causar error 500 en el servidor.
        def m = [value: value, language: null, confidence: -1]
        if (place != null) m.place = place
        if (authority != null) { m.authority = authority; m.confidence = 600 }
        return m
    }

    // ---------- búsqueda idempotente ----------
    // Person: buscar por person.identifier.orcid, luego perucris.person.dni.
    String findPersonUuid(String orcid, String dni) {
        if (orcid) {
            def u = searchByMetadata('Person', 'person.identifier.orcid', orcid)
            if (u) return u
        }
        if (dni) {
            def u = searchByMetadata('Person', 'perucris.person.dni', dni)
            if (u) return u
        }
        return null
    }

    // OrgUnit: buscar por organization.legalName exacto (+ tipo entidad OrgUnit).
    String findOrgUnitUuid(String legalName) {
        if (!legalName) return null
        return searchByMetadata('OrgUnit', 'organization.legalName', legalName)
    }

    // Discovery search por par metadato=valor restringido a un entityType.
    private String searchByMetadata(String entityType, String field, String value) {
        def q = URLEncoder.encode(field + ':"' + value + '"', 'UTF-8')
        def path = "/discover/search/objects?query=${q}&dsoType=item&f.entityType=${URLEncoder.encode(entityType,'UTF-8')},equals"
        def r = getJson(path)
        if (r.code != 200 || r.json == null) return null
        def objs = r.json?._embedded?.searchResult?._embedded?.objects
        if (objs && objs.size() > 0) {
            return objs[0]?._embedded?.indexableObject?.uuid
        }
        return null
    }
}
