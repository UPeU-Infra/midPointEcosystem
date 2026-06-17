/*
 * Test.groovy — Test Connection del resource DSpace-CRIS UPeU (ScriptedREST).
 * Verifica login JWT y lee el root REST para confirmar versión.
 */
def client = new CrisClient(configuration.baseAddress?.toString(),
                            configuration.username?.toString(),
                            configuration.password instanceof char[] ? new String(configuration.password) : configuration.password?.toString(),
                            log)
client.login()
def r = client.getJson('')
if (r.code != 200) throw new RuntimeException('CRIS root no responde 200: ' + r.code)
log.info('CRIS Test OK — dspaceVersion=' + r.json?.dspaceVersion + ' crisVersion=' + r.json?.crisVersion)
