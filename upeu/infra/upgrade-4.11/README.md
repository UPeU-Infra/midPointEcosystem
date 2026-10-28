# Ficheros de la subida 4.10.2 → 4.10.5 → 4.11.0

Plan y roadmap: [`docs/upgrade-4.11/PLAN-Y-ROADMAP.md`](../../../docs/upgrade-4.11/PLAN-Y-ROADMAP.md).
Runbooks: [`F1-ensayo-lab.md`](../../../docs/upgrade-4.11/F1-ensayo-lab.md) ·
[`F2-ventana-4.10.5.md`](../../../docs/upgrade-4.11/F2-ventana-4.10.5.md) ·
[`F3-ventana-4.11.0.md`](../../../docs/upgrade-4.11/F3-ventana-4.11.0.md).

En el servidor todo se usa **desde el clon del repo** (`~/midPointEcosystem`, tras `git pull`),
sin copiar nada: los overrides se pasan con `-f` detrás del compose de `/opt/midpoint`, y
compose toma el proyecto (`midpoint`) y el `.env` del directorio del primer `-f` (comprobado
con `docker compose config`). En los runbooks: `W=~/midPointEcosystem/upeu/infra/upgrade-4.11`.

| Fichero | Para qué | Ventana |
|---|---|---|
| [`docker-compose.upgrade-window.yml`](docker-compose.upgrade-window.yml) | Override: neutraliza `data_init` (no toca la BD), arranca midPoint **con el planificador parado** y añade el servicio `ninja` (perfil `tools`) con las credenciales del `.env` | F2, F3 (y F1) |
| [`docker-compose.4.11.yml`](docker-compose.4.11.yml) | Override permanente desde 4.11: `user: "1000:1000"` en `midpoint_server` y `data_init` | F3 en adelante |
| [`config-xml-safe-scripting.sh`](config-xml-safe-scripting.sh) | `--check` / `--apply`: escribe `safeScriptingLanguagesOnly=false` en el `config.xml` del volumen, con copia, validación XML e idempotencia | F3 |
| [`ldap-connectorref.sh`](ldap-connectorref.sh) + [`ldap-connectorref-patch.xml.tmpl`](ldap-connectorref-patch.xml.tmpl) | `show` / `find <v>` / `apply <v>` / `test`: PATCH del `connectorRef` de LDAP al conector bundled de la versión arrancada | F2 (3.9.4), F3 (3.10) |
| [`sysconfig-privileged-principal-patch.xml`](sysconfig-privileged-principal-patch.xml) (+ `-rollback.xml`) | `expressions/defaults/privilegedPrincipal = permissive` en la SystemConfiguration | F3, con 4.11 arrancado |
| [`initial-objects/`](initial-objects/README.md) | Listas blanca / revisar / nunca para `ninja initial-objects` | F3 |
| [`bd-copia-local.sh`](bd-copia-local.sh) | `estado` / `crear` / `restaurar` / `borrar`: copia de la BD en el mismo Postgres (`CREATE DATABASE … TEMPLATE … STRATEGY FILE_COPY`) con midPoint parado. **Vuelta atrás en segundos** (renombrar dos bases); replica `enable_partitionwise_join=on` | F2, F3 |
| [`tareas-ventana.sh`](tareas-ventana.sh) | `estado` / `suspender` / `reanudar <oid>` / `ejecutar <oid>` de las 8 tareas de negocio | F2, F3 |
| [`test-recursos.sh`](test-recursos.sh) | Test connection de todos los recursos; exit 0 solo si todos dan `success` | F1, F2, F3 |
| [`muestra-sim.sh`](muestra-sim.sh) | `generar` muestra fija (≤80 usuarios por vínculo vivo) / `tarea` de simulación (recompute+reconcile en preview) / `comparar` PRE vs POST | F1, F3 |

Scripts tocados fuera de esta carpeta:

- `upeu/scripts/audit-partition-maintenance.sh`: ya exporta y borra `ma_audit_payload` (4.11).
  Prueba: `upeu/scripts/tests/test-audit-partition-maintenance.sh`.
- `upeu/scripts/backup-midpoint-s3.sh --pre-upgrade <etiqueta>`: copia **fuera del host** de la
  ventana (BD sin datos de auditoría, como el diario, ~9 min; y el home leído del volumen), con
  midPoint parado. Con auditoría serían ~37 GB a ~5 MB/s: no cabe en una ventana; por eso la
  vuelta atrás rápida es `bd-copia-local.sh`. Va a `s3://…/midpoint/upgrade/<etiqueta>/`, prefijo
  **sin regla de caducidad** en el bucket (comprobado el 28-oct): se borra a mano cuando ya no
  haga falta (la IAM del servidor no puede borrar). Prueba: `upeu/scripts/tests/test-backup-modes.sh`.

## Hallazgos que cambian el plan del 27-oct

### 1. El salto a 4.10.5 también cambia el conector LDAP (3.9.2 → 3.9.4)

`pom.xml` por tag: 4.10.2 → `connector-ldap` **3.9.2**; 4.10.3 → 3.9.3; 4.10.4 y 4.10.5 →
**3.9.4**; 4.11.0 → **3.10**. Las release notes de 4.10.5 siguen diciendo 3.9.2 en su tabla de
componentes: el `pom.xml` del tag manda.

En PROD, los `LdapConnector`/`AdLdapConnector` **3.9.1** siguen registrados con
`available=false` desde la subida de mayo: midPoint no borra el conector viejo, lo deja sin
uso. Por eso, al arrancar 4.10.5, el 3.9.2 (`31072286-…`) quedará igual y **el recurso LDAP no
funcionará hasta el PATCH a 3.9.4**. El PATCH entra en F2, no solo en F3.

### 2. 4.11 verifica los conectores ConnId contra una lista firmada… en «producción sin suscripción»

`ConnectorSignatureVerifier` (v4.11.0), llamado al cargar cualquier conector ConnId:

- Solo actúa si midPoint estima que corre **en producción** y **sin suscripción activa**.
- Si actúa, el conector tiene que estar en un `AllowedConnectorsList` firmado (el 070 trae 64)
  **o** estar en su periodo de gracia de **90 días** desde el descubrimiento.
- En el primer arranque de 4.11, los conectores ya registrados reciben
  `discoveryTimestamp = ahora` (`ProvisioningServiceImpl.addDiscoveryTimestampToConnectors`).
  La cuenta de 90 días empieza el día de la ventana F3.

De nuestros conectores, la lista firmada incluye `LdapConnector` y `MSGraphConnector`. **No
incluye** `net.tirasa…ScriptedSQLConnector` (los 8 recursos de Oracle LAMB; la lista trae otro
ScriptedSQL, el de `com.evolveum.polygon`), ni Koha ni Zammad.

«Producción» se estima con 6 indicadores de la SystemConfiguration (`SubscriptionPolicies`), y
hacen falta 2: identificador de suscripción, transporte de correo o SMS activo, patrón de URL
pública `https:`, cabecera de IP remota, un appender de log que no sea de fichero, y colores o
logo propios. **La SystemConfiguration de PROD da 0 de 6** (medido el 28-oct). Así que hoy no
aplica.

**Implicación:** activar dos de esos seis (por ejemplo, la URL pública `https://identity.upeu.edu.pe`
y un transporte de correo para notificaciones) **convertiría la instalación en «producción»**.
A partir de los 90 días de la ventana, Oracle LAMB, Koha y Zammad dejarían de cargar. Cualquier
cambio en esos ajustes pasa a ser una decisión con dos salidas posibles:

- contratar la suscripción;
- o migrar a conectores de la lista.

El ensayo F1 debe confirmar en los logs que no se dispara la verificación.

### 3. `privilegedPrincipal` va en la SystemConfiguration, no en `config.xml`

`config.xml` solo lleva `expressions/safeScriptingLanguagesOnly`. `expressions/defaults/privilegedPrincipal`
es un elemento de la SystemConfiguration que **solo existe en el XSD de 4.11** y cuyo valor es el
identificador de un perfil de la propia SystemConfiguration (`permissive` existe en PROD).

### 4. El script de particiones de auditoría ya fallaba con 4.10: solo procesaba un mes por corrida

El 1-oct-2026 listó `202606 202607` y solo exportó y borró junio. Causa: el export
(`docker run -i`) se comía el stdin del bucle. Corregido y probado. El dry-run en PROD del 28-oct
da un candidato (`202607`). El 1-nov, con el script corregido, saldrían julio y agosto.
