/*
 * Test.groovy — Test Connection del resource DSpace-CRIS UPeU (ScriptedREST).
 * Verifica login JWT y lee el root REST para confirmar versión.
 */
// --- carga dinámica del helper CrisClient (opción 1) ---
// El RESTConnector compila cada *ScriptFileName aislado, sin el dir en el classpath,
// así que 'import CrisClient' no resuelve. Cargamos la clase con GroovyClassLoader,
// cacheándola JVM-wide por (path, lastModified) para parsear una sola vez.
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
def client = __crisClass.newInstance(configuration.baseAddress?.toString(),
                            configuration.username?.toString(),
                            configuration.password instanceof char[] ? new String(configuration.password) : configuration.password?.toString(),
                            log)
client.login()
def r = client.getJson('')
if (r.code != 200) throw new RuntimeException('CRIS root no responde 200: ' + r.code)
log.info('CRIS Test OK — dspaceVersion=' + r.json?.dspaceVersion + ' crisVersion=' + r.json?.crisVersion)
