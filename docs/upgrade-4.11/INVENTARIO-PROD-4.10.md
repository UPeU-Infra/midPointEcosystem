# Inventario MidPoint PROD (4.10.2) para la actualización a 4.11.0

- **Fecha de la medición:** 27-oct-2026, 09:20–10:30 (hora de Lima).
- **Alcance:** solo lectura. No se usó REST de escritura ni se tocaron tareas. `docker exec` solo para leer (`ls`, `cat`, `java -version`, `find`). Postgres siempre con `PGOPTIONS=-c default_transaction_read_only=on`; comprobado: `show default_transaction_read_only` → `on`.
- **Host:** `midpoint.upeu` (192.168.15.166), usuario `juansanchez`.
- **Fuentes de 4.11:** release notes `docs/release-notes/4.11.0` y el código del tag `v4.11.0` en `Evolveum/midpoint` (consultado con `gh api`).
- **Convención:** ❓ = no verificado, hay que probarlo en el laboratorio.

Acceso usado en todos los comandos:

```bash
source ~/.secrets/midpoint-upeu.env
sshpass -p "$MIDPOINT_PROD_PASS" ssh -o ProxyJump=none -o NumberOfPasswordPrompts=1 \
  -o StrictHostKeyChecking=no juansanchez@192.168.15.166 "..."
# SQL: archivo local -> stdin
... 'docker exec -i -e PGOPTIONS="-c default_transaction_read_only=on" midpoint-midpoint_data-1 psql -U midpoint -d midpoint' < q.sql
```

Para el análisis de expresiones se exportó el `fullObject` de los 1.351 objetos de configuración. Se excluyeron USER, CASE, REPORT_DATA, SIMULATION_RESULT y NODE:

```sql
\copy (select oid, objecttype, nameorig, convert_from(fullobject,'UTF8') from m_object
       where objecttype not in ('USER','CASE','REPORT_DATA','SIMULATION_RESULT','NODE')) to stdout with (format csv)
```

Luego se recorrió el JSON (en 4.10 el `fullObject` es JSON) con Python, buscando cada `expression`/`condition` y cada `script`.

---

## 1. Plataforma

| Dato | Valor | Cómo se midió |
|---|---|---|
| Versión MidPoint | **4.10.2** (imagen `evolveum/midpoint:4.10.2-ubuntu`, `midpoint.jar` del 16-mar-2026) | `docker ps`; `.env` `MP_VER=4.10.2` |
| Última 4.10.x publicada | **4.10.5** (también existen 4.10.3 y 4.10.4; 4.10.6 está planificada para el 27-ene-2027) | docs.evolveum.com/midpoint/release/; Docker Hub tiene `4.10.5-ubuntu` y `4.10.5-alpine` |
| 4.11.0 en Docker Hub | `4.11.0`, `4.11.0-ubuntu`, `4.11.0-alpine`, `4.11.0-rockylinux` (26-oct-2026) | API de tags de Docker Hub |
| Imagen `data_init` | `evolveum/midpoint:${MP_VER}-alpine` (corre `midpoint.sh init-native` y `ninja`) | compose |
| Usuario del contenedor | **root (uid 0)**; `Config.User` vacío; el PID 1 y Java corren como root | `docker inspect`; `id` y `ps` dentro del contenedor |
| Java | OpenJDK **21.0.10** (Ubuntu 22.04) | `docker exec midpoint_server java -version` |
| JVM | `-Xms5120m -Xmx9216m`, G1GC, truststore `/opt/midpoint/certs/truststore.jceks`. Propiedades por defecto de la imagen: `upgradeableSchemaAction=stop` y `missingSchemaAction=create` | `ps` dentro del contenedor |
| PostgreSQL | imagen `postgres:16-bullseye`, `server_version` **16.9** (Debian). 4.11 admite 14–18 y recomienda 17. Debian 11 «bullseye» está al final de su vida | `show server_version` |
| Tamaño de la BD | **45 GB** en total: auditoría **37 GB** y el resto 8,1 GB (`m_user` 1,8 GB, `m_case` 1,4 GB). 398.056 shadows y 192.441 `m_ref_projection` (linkRef) | `pg_database_size`, `pg_total_relation_size` |
| Número de cambio del esquema | repo `schemaChangeNumber=51`, audit `schemaAuditChangeNumber=10`. 4.11 los lleva a **67** y **16** | `select * from m_global_metadata` |
| Recuento de objetos | 66.121 USER, 2.944 CASE, 751 SERVICE, 191 ORG, 110 ROLE, 88 ARCHETYPE, 57 TASK, 12 RESOURCE, 20 CONNECTOR, 7 OBJECT_TEMPLATE, 4 FUNCTION_LIBRARY, 13 REPORT, 15 LOOKUP_TABLE, 39 MARK | `select objecttype,count(*) from m_object group by 1` |
| Compose | `/opt/midpoint/docker-compose.yml`, proyecto `midpoint`. Servicios: `midpoint_data`, `data_init` y `midpoint_server` | label `com.docker.compose.project.config_files` |
| `.env` | `POSTGRES_USER`, `MP_DB_PASSWORD`, `MP_ADMIN_PASSWORD`, `MP_VER=4.10.2` | `sed` con los valores redactados |
| Volúmenes | `midpoint_midpoint_home` → `/opt/midpoint/var`<br>bind `/opt/midpoint/connectors` → `/opt/midpoint/var/icf-connectors` (ro)<br>bind `/opt/midpoint/certs` (ro)<br>`midpoint_midpoint_data` → PGDATA | `docker inspect … .Mounts` |
| Dueños en el home | 62 entradas `root:root` y 66 `1001:1001`. `keystore.jceks` es **root 0600**; `log/` es root 0750 (332 MB); `lib/ojdbc11-23.6.0.24.10.jar` es 1001. En el host, el uid 1000 es `devops` y el 1001 es `juansanchez` | `find /opt/midpoint/var -xdev -printf "%u:%g\n" \| sort \| uniq -c` |
| `config.xml` | **Existe** (`/opt/midpoint/var/config.xml`, plantilla nativa de abril de 2026). Tiene repository/audit/icf/keystore y **no tiene** `<expressions>` ni `<connectors>`. Los datos JDBC reales entran por `MP_SET_*` | `cat` |
| `logback.xml` en el home | Personalizado: logger `MappingSorter` en DEBUG hacia `mapping-sorter-debug.log`. No referencia clases renombradas en 4.11 | `cat` |
| Overlays o JAR propios | No hay overlay. `lib/` solo tiene `midpoint.jar` y `ninja.jar`. En `var/lib` está el driver Oracle `ojdbc11-23.6.0.24.10.jar` | `ls` |
| Restos en el home | `import/` (~70 XML de pruebas de mayo y junio), `cris-scripts/` (Groovy del CRIS retirado), `GateD.java` y `GateE.java`. `post-initial-objects/` está vacío. Según la documentación, `importFolder` lo usa la GUI y no se importa solo al arrancar ❓ | `ls` |
| Host | **16 vCPU, 21 GiB de RAM** (11 GiB disponibles), swap de 3,5 GiB. Disco `/` LVM de **121 GB, 60 GB usados (52 %), 57 GB libres**. El disco creció desde los 72 GB de septiembre | `nproc`, `free -h`, `df -h /`, `lsblk` |
| Límites de los contenedores | midpoint `mem_limit 10g`; postgres `5g` (`shared_buffers` 1536 MB) | compose |

### Backups (memoria `backup-midpoint-s3-2026-09-23`, comprobado hoy)

- **Cron diario:** `/etc/cron.d/midpoint-backup-s3`, a las 22:30, como `juansanchez`. Ejecuta `~/midPointEcosystem/upeu/scripts/backup-midpoint-s3.sh`.
- **Último backup:** `s3://upeu-iga-backups-360416501080/midpoint/db/2026/10/midpoint-db-20261026-223001.dump` (2,70 GB) **con `.sha256`**, y `home/…20261026-223001.tar.gz` (138 MB) **con `.sha256`**. Comando: `aws s3 ls … --recursive` con las credenciales de `~/.secrets/aws-iga-backup.env`.
- **Cron mensual de auditoría:** `/etc/cron.d/midpoint-audit-partition-maintenance`, el día 1 a las 03:00 (export a S3 y luego DROP).
  - En S3 solo está `audit/ma_audit_202606.dump`.
  - **Las particiones de julio (`ma_audit_*_202607`, unos 10 GB) siguen en la BD.** Con la retención de 2 meses más el mes en curso, el 1-oct debían haberse exportado y borrado. Causa ❓ (mirar `/var/log/midpoint-audit-partition-maintenance.log`).

### Hallazgos de seguridad, de paso (no bloquean la 4.11)

- *(Hallazgo de seguridad omitido en este repositorio público; detalle en la nota privada del equipo.)*
- *(Hallazgo de seguridad omitido en este repositorio público; detalle en la nota privada del equipo.)*
- El repositorio `UPeU-Infra/midPointEcosystem` es **PUBLIC** (`gh repo view --json visibility`).

---

## 2. Conectores y recursos

Consulta: `m_resource` con JOIN a `m_connector` por `connectorRefTargetOid`, y `m_connector` con el número de recursos que usa cada uno.

| Recurso | OID | Conector (bundle, versión) | Origen | `connectorRef` OID | lifecycle |
|---|---|---|---|---|---|
| LDAP-IdentityCache-UPeU | `7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f` | `connector-ldap` **3.9.2** LdapConnector | **bundled** | `31072286-…` | active |
| Koha ILS UPeU (consolidado) | `e10a539a-cb7f-4c72-a19f-60f7f62e4b96` | `com.identicum.midpoint.connector-koha` 1.7.0 | custom (`icf-connectors`) | `8c090235-…` | active |
| Zammad UPeU | `7a11d0d0-0000-4000-a000-7a11d0d00001` | `connector-zammad` 0.2.0 | custom | `0ae9cbcd-…` | (null) |
| UPEU-EntraID-Graph | `2f11c057-7b15-4641-a0eb-00c98a6fa4cb` | `connector-msgraph` 1.2.0.0 | Evolveum, no bundled (`icf-connectors`) | `01a9df66-…` | active |
| Oracle LAMB Trabajadores v3 | `6a91f7e1-…0e21` | `scriptedsql` 2.2.10 (Tirasa) | custom | `e4cd8ed3-…` | active |
| Oracle LAMB Estudiantes v3 | `6a91f7e1-…0e22` | idem | custom | idem | active |
| Oracle LAMB Egresados v3 | `6a91f7e1-…0e23` | idem | custom | idem | active |
| Oracle LAMB Ausencias v1 | `6a91f7e1-…0e24` | idem | custom | idem | active |
| Oracle LAMB Grados v1 | `3b2d8c4a-6f17-4e90-a1d5-9c0e7b5a4f62` | idem | custom | idem | active |
| Oracle LAMB Org | `9e2f4c7a-1b5d-4e8c-a3f6-c2d9e4b7a1f3` | idem | custom | idem | active |
| Oracle LAMB RENIEC Cache v1 | `c4d5e6f7-a8b9-0123-cdef-123456789abc` | idem | custom | idem | active |
| LAMB-Oracle-Posiciones | `f2422f42-90da-4ca4-a4db-78fe25a63245` | idem | custom | idem | active |

- **Solo un recurso depende de un conector bundled: LDAP-IdentityCache-UPeU.**
  - 4.11 trae LDAP **3.10** (ConnId 1.5.3.0). El objeto conector 3.9.2 quedará `available=false`, igual que pasó con 3.9.1 al subir a 4.10.x.
  - Hay que **cambiar `connectorRef` al OID del conector 3.10** que 4.11 crea al arrancar.
  - Ese cambio va por **PATCH, nunca por PUT**. Ver la memoria `nunca-put-resources-schema-cache`: un PUT pisa el `<schema>` cacheado.
  - Cambios de 3.10 según su ficha: filtro `exists` corregido (los resultados pueden cambiar), descripciones de clases en el esquema, security descriptor de AD binario. Nada marcado como breaking.
- DatabaseTable (1.5.2.0 no disponible y 1.5.3.0 disponible), CSV (2.8 custom y 2.9 bundled) y REST 1.1.0 **no los usa ningún recurso.**
- Conectores huérfanos que se pueden limpiar: Koha 1.3.11, 1.5.0 y 1.6.0; Zammad 0.1.0; CSV 2.8; REST 1.1.0. Además hay `.jar.bak-*` en `/opt/midpoint/connectors`.
- **ConnId pasa de 1.6.0.0 (4.10.2) a 1.7.0.0-M0 (4.11), que es un *milestone*.** Manifiestos (leídos con `python3 zipfile` en el host):
  - Koha 1.7.0 y Zammad 0.2.0: `FrameworkVersion 1.5.2.0`, Java 17, y **embeben `lib/connector-framework-internal-1.5.2.0.jar`**.
  - ScriptedSQL 2.2.10: FW 1.5.2.0, Java 8.
  - msgraph 1.2.0.0: FW 1.5.1.3.
  - Compatibilidad con 1.7.0.0-M0 ❓; hay que probar los cuatro en el laboratorio. El framework embebido de Koha y Zammad es el punto más frágil.
- **Scripts Groovy internos de ScriptedSQL** (`searchScript`, `schemaScript`, `syncScript`, `testScript`, `scriptingLanguage=GROOVY`; 8 recursos, 1,3–9,3 KB por `searchScript`):
  - Los ejecuta el `ScriptExecutorFactory` de ConnId, **no** el `AbstractScriptExecutor` de midPoint.
  - `safeScriptingLanguagesOnly` y los perfiles de expresión de 4.11 solo se aplican en `AbstractScriptExecutor.checkProfileAndSafetyRestrictions` (comprobado en el código de v4.11.0). **No deberían afectarles.**
  - Usan `groovy.sql.Sql`. 4.11 sigue incluyendo `groovy-all` (Groovy 4.0.24 → 4.0.31) y `connectors/developmentToolsEnabled` solo gobierna el generador de conectores.
  - Que funcione bajo ConnId 1.7.0.0-M0 ❓; se valida en el laboratorio con `test resource` y un import acotado.
- **Drift entre el repo y PROD:**
  - `upeu/resources/koha-ils.xml` apunta a Koha 1.3.11 (`45b4f0e0`) y `koha-upeu.xml` a 1.6.0 (`16030383`); PROD usa 1.7.0 (`8c090235`).
  - `upeu/infra/docker-compose.yml` conserva el truststore viejo (`/etc/ssl/certs/java/cacerts`) y le falta el bind de `/opt/midpoint/certs`.

---

## 3. Expresiones

### 3.1 Recuento

Se recorrieron todos los `expression`/`condition` y cada `script` con `code`.

- **433 expresiones `script`**, de ellas 309 con código distinto. **Ninguna declara `language`**: las 433 dependen del lenguaje por defecto, Groovy.
- No hay Velocity, JavaScript ni Python.
- Ninguna expresión usa `#parse`, `#include`, `xerces`, `ScriptExpression*`, `ScriptEvaluator` ni `repo.api.Cache`.
  - Las 48 apariciones de `ScriptExpression` que salieron están en las **estadísticas de operación de tareas**, no son código.

| Objeto (tipo) | script | Otros evaluadores | Origen |
|---|---|---|---|
| RESOURCE (12) | **170** | path 16, value 10, **function 11**, assignmentTargetSearch 2 | UPeU |
| OBJECT_TEMPLATE | **121**: Person-Base 105, EmployeeStaff 4, EmployeeFaculty 4, Alumni 2, Student 2, OrgTemplate-Area 1, *380 Person Object Template* 3 | assignmentTargetSearch 21, value 7, asIs 2 | UPeU, salvo el 380 |
| FUNCTION_LIBRARY (4 `sb-*`) | **8** | — | UPeU |
| SYSTEM_CONFIGURATION | **2** (`customTransport` de Telegram) | — | UPeU |
| REPORT (13, todos initial) | **107** | — | Evolveum, sin modificar (v1) |
| DASHBOARD (admin, compliance) | **19** | proportional 16 | Evolveum |
| MARK (710, 711, 730, 731) | **4** | — | Evolveum |
| OBJECT_COLLECTION («All audit records») | **1** | — | Evolveum |
| VALUE_POLICY (Default Password Policy) | **1** | — | Evolveum, sin modificar |
| ROLE, ARCHETYPE, ORG, SERVICE, POLICY, TASK | **0** | **0 expresiones de cualquier tipo** | — |

- **Total UPeU: 298 scripts** (205 únicos).
- **Total de initial objects de Evolveum: 135.** Las versiones 4.11 los traen en MEL con `language#mel` explícito (comprobado en 110, 310, 010, 710 y 380).
- **Tareas:** ninguna de las 57 tiene acciones masivas ni scripting (`execute-script`, `scriptingExpression`, `iterativeScripting`): 0. El repo tampoco las usa por REST (`grep executeScript`): 0, salvo menciones en documentación.

### 3.2 APIs usadas por los 298 scripts de UPeU

Clasificación por dificultad de portar a MEL:

| Clase | Cuántos (únicos) | Qué contienen |
|---|---|---|
| A. `basic.*` y Groovy puro | 192 (126) | `basic.stringify` 140×, `getExtensionPropertyValue(s)`, `getAttributeValue`, `norm`, `trim`, `concatName`; colecciones, regex, `switch` |
| B. API `midpoint.*` / `prismContext` | 60 (36) | `midpoint.hasLinkedAccount` 11×, `getCurrentTask().getExecutionMode().isFullyPersistent()` 18× (los gates de canario y simulación), `getObject(LookupTableType, …, createRetrieve)` 12×, `resolveReferenceIfExists` 4×, `getLinkedShadow`, `log.*` 100× |
| C. Clases Java/Prism, red, E/S | 46 (43) | `java.net.URL`/`HttpURLConnection` (descarga de `jpegPhoto` en Person-Base); `java.net.http.HttpClient` + `groovy.json.JsonOutput` (Telegram, sysconfig); `javax.imageio`/`java.awt` (redimensionado de la foto de Entra); `TriggerType`/`XmlTypeConverter`/`java.time` (triggers de ausencias); `PrismContainerValue`, `ItemPath`, `ItemName`, `QName`, `javax.naming.ldap.Rdn`, `metaClass.respondsTo` (LDAP: DN jerárquico, `schacPersonalUniqueID`); `SelectorOptions`/`GetOperationOptions` |

- Todas las clases y métodos usados siguen existiendo en v4.11.0:
  - Clases: `ReportUtils`, `CertCampaignTypeUtil`, `ObjectTypeUtil`, `DeltaConvertor`, `ProcessedObject`, `SelectorOptions`, `GetOperationOptions`; en prism, `PrismContainerValue`, `ItemPath`, `ItemName`, `XmlTypeConverter`.
  - Métodos: `PrismContext.toUniformPath`, `TaskExecutionMode.isFullyPersistent`.
  - Ningún método de `MidpointFunctions` ni de `BasicExpressionFunctions` usado desaparece. Se compararon los fuentes de v4.10.2 y v4.11.0.
- **Bug latente que ya existe en 4.10.2 y no depende de la 4.11:** 3 condiciones de `UserTemplate-Person-Base` llaman a `midpoint.getObjectByOid(...)`.
  - Ese método **no existe** ni en 4.10.2 ni en 4.11 (ni en la interfaz ni en `MidpointFunctionsImpl`).
  - El `try/catch` se traga la excepción y `perP` siempre vale `null`.

### 3.3 ¿Fallarían con los perfiles por defecto de 4.11?

Lo que se leyó en el código de v4.11.0 (`ExpressionProfileManager`, `ExpressionProfile`, `ScriptFactory`, `ExpressionsConfigurationSectionImpl`, `midpoint.sh`):

1. **El perfil sale de la SystemConfiguration del repositorio, no del binario.**
   - Si el objeto no tiene un perfil por archetype ni por `defaultObjectPolicyConfiguration/expressionProfile`, y no hay `expressions/defaults/authorizedObjects`, se aplica `legacyDefaultForAuthorizedObjects()`, que es **`full()`**.
   - En PROD: 0 archetypes con `expressionProfile`; las 2 entradas de `defaultObjectPolicyConfiguration` (UserType y OrgType) solo tienen `objectTemplateRef`; `expressions` solo tiene `expressionProfile`/`permissionProfile`/`bulkActionsProfile` y **no tiene `defaults`**.
   - **Conclusión: con la SystemConfiguration actual, las 433 expresiones se evalúan con perfil `full`, igual que hoy.**
2. **`safeScriptingLanguagesOnly` vale `false` por defecto** si el `config.xml` no lo declara (`configuration.getBoolean(..., false)`).
   - El `init-native` de 4.11 **solo copia `config.xml` si no existe** (`[ ! -e ${MP_INIT_CFG}/config.xml ]`).
   - PROD lo tiene en el volumen, así que **se conserva y Groovy sigue habilitado.**
   - Para blindarlo, conviene añadir `<expressions><safeScriptingLanguagesOnly>false</safeScriptingLanguagesOnly></expressions>`.
3. **El lenguaje por defecto sigue siendo Groovy** si la SystemConfiguration no fija `expressions/defaultScriptLanguage` (`ScriptFactory.DEFAULT_LANGUAGE = …#Groovy`).
4. **Caso «principal actual» (expresiones ad hoc por GUI/REST que no son acciones masivas):**
   - Sin `expressions/defaults`, en 4.11 devuelve `ExpressionProfile.none()`. **Ya no da `full` al administrador, como hacía en 4.10.2.**
   - Las acciones masivas de un usuario privilegiado siguen en `full`.
   - En PROD no se detectó ningún uso por REST (los scripts del repo solo hacen GET/PATCH/POST de objetos). Impacto ❓ bajo.

**La trampa:** si se aplica la SystemConfiguration de 4.11 (con `ninja initial-objects` sin excluirla, o con un merge desde la GUI), entran a la vez:

- `defaultScriptLanguage=mel`, que convierte en **MEL las 433** (ninguna declara lenguaje) y **rompe todo**;
- `defaultObjectPolicyConfiguration`, que asigna:
  - **configuration** a Resource, ObjectTemplate, FunctionLibrary, Mark y SystemConfiguration. Solo admite MEL y safe-velocity, **deniega `function`** y admite `assignmentTargetSearch`.
  - **reporting** a Report.
  - **safe** a Role, Archetype, Org, Service, Policy, ValuePolicy, Dashboard y ObjectCollection.

Si se adoptaran esos perfiles, fallaría lo siguiente:

| Perfil | Objetos | Fallarían |
|---|---|---|
| configuration | Resources | 170 scripts y **11 `function`** |
| configuration | Templates | 118 de UPeU y 3 del 380 (1 dentro del filtro de un `assignmentTargetSearch`) |
| configuration | Function libraries | 8 |
| configuration | Sysconfig | 2 (HttpClient: **MEL no puede hacer HTTP**, hace falta otro transporte) |
| configuration | Marks | 4 |
| reporting | Reports | 107 |
| safe | Dashboards, collections, value policy | 19 + 1 + 1 |
| safe | Roles, archetypes, orgs, services | **0**: sin expresiones y sin `assignmentTargetSearch` |

Además, el perfil `safe` que hoy tiene PROD es el de 4.10.0, con `permissionProfile` `script-safe` (renombrado a `script-limited` en 4.10.5 y eliminado en 4.11). Nada lo referencia, así que no hace daño, pero hay que reemplazarlo al adoptar los perfiles nuevos.

---

## 4. Otros cambios de 4.11

| Tema | PROD | Impacto |
|---|---|---|
| Iteración (`useTokenOnlyOnConflict` por defecto true; `start`) | Solo el **380 Person Object Template** (`maxIterations 99` + `tokenExpression`), y **ese template no lo referencia nadie**: UserType usa Person-Base `855caaca`. Templates y recursos de UPeU: 0 `iterationSpecification` | Ninguno |
| PolyString `orig` deja de usarse como clave de traducción | 377 PolyString con `translation` explícita (reports 145, archetypes 138, sysconfig 50, collections 26, dashboards 18); **0** `orig` con forma de clave y sin `translation` | Ninguno |
| OIDC resource server (atributos eliminados) | Security policy `…0120` solo con `loginForm` + `httpBasic`. El repo tiene `upeu/auth/oidc-entra-id.xml` (módulo **cliente** `oidc`, no resource server, **no desplegado**) | Ninguno |
| Velocity `#parse`/`#include` | 0 Velocity | Ninguno |
| Overlays o JAR propios en `lib` | No hay; solo el driver `ojdbc11` en `var/lib` | ❓ comprobar que 4.11 lo sigue cargando y que puede leerlo el uid 1000 (archivo 1001, modo 644: lectura OK) |
| `PasswordType.hint` pasa a ProtectedString (ya en 4.10.5) | 0 usuarios con `hint`; 2 usuarios con contraseña | Ninguno |
| `linkRef` → `ProjectionHolderType` | 192.441 `m_ref_projection`. Cambios de BD 61–64 (`ALTER TABLE m_focus/m_case … INHERIT m_projection_holder`): catálogo, rápidos, con lock exclusivo | Ventana de mantenimiento |
| `displayName`/`preferredName` | Cambio 58: `ALTER TABLE m_user ADD COLUMN` ×4 + 2 índices sobre 66.121 filas | Minutos ❓ |
| Auditoría | Cambio 15: `CREATE EXTENSION pg_trgm`, tabla particionada `ma_audit_payload` con partición por mes existente y FK a `ma_audit_event_*`; se reescribe `audit_create_monthly_partitions` | **Rompe el script propio de purga** (ver riesgo R4) |
| xercesImpl eliminado, clases de script renombradas | 0 usos | Ninguno |
| Puesta al día de 4.10.3–4.10.5 | Sin cambios de BD (sigue en 51); Spring Boot 4.x; validación de ficheros subidos; hints como ProtectedString | Bajo |

---

## 5. Initial objects modificados en local

Consulta: `select objecttype, oid, nameorig, version from m_object where oid::text like '00000000-0000-0000-0000-%' and version>0`. `version=1` significa intacto.

- **SystemConfiguration** `…0001`: **v63**, muy personalizada.
  - `adminGuiConfiguration`, logging, notificación por Telegram, `globalPolicyRule`, `defaultObjectPolicyConfiguration` (UserType → Person-Base `855caaca`, OrgType → OrgTemplate-Area `47252981`), `cleanupPolicy` y perfiles de expresión de 4.10.0.
  - **No importarla.** Lo de 4.11 que interese se aplica a mano, con PATCH.
- **Archetype Person** `…0702`: **v16**, personalizado el 15-may. 4.11 solo le añade claves de traducción, así que **no hace falta tocarlo.**
- **Role** `…0004`: renombrado a **SYS-IGA-SUPERUSER** (v2). Role `…0008` End user: v2.
- **Archetypes** `…0330` Classification, `…0331` Clearance y `…0341` Operation request: v3. Unos 50 archetypes de tareas, casos y marcas en v2.
  - ❓ Son retoques masivos, probablemente la reparación de `archetypeRef` del 3-ago o algo parecido.
  - Antes de un `initial-objects` hay que revisar el diff.
- **Intactos (v1)**, se pueden reemplazar por las versiones MEL de 4.11:
  - los 13 reports;
  - marks 710/711/730/731;
  - Default Password Policy `…0003` (Groovy → MEL en 4.11);
  - Security Policy `…0120` (4.11 añade `otp` y `passwordHintConfigurability=neverConfigure`);
  - 380 Person Object Template (sin uso).
  - Los dashboards admin y compliance no tienen OID `0000…`: confirmar su versión ❓.
- **No hay colisiones de OID:** ninguno de los 32 objetos nuevos o renombrados de 4.11 choca con OIDs de UPeU.
  - Los 12 que ya existen en PROD son los mismos objetos de Evolveum, con el prefijo de archivo renombrado.
  - UPeU usa OIDs propios en el espacio `00000000-0000-0000-0000-xxxxxx`: 26 orgs y los roles GOV `…000a`/`…000b`/`…000c`. **Mantener esa vigilancia en cada versión.**

---

## 6. Tareas programadas

Horas de Lima (`TZ=America/Lima`). Duración = última ejecución.

| Tarea | OID | Horario | Estado | Recurso | Duración |
|---|---|---|---|---|---|
| recon-entra-id-daily | `a1e5b2c3-0001-4def-9abc-202406060001` | 02:00 | **running** (hoy aún en curso) | Entra | ~7 h 38 min (ayer terminó a las 09:38) |
| recon-ldap-dti-groups-daily | `d71a0003-0000-4000-a000-d71a00000003` | 03:30 | runnable | LDAP | 1 s |
| recompute-dti-teams-daily | `d71a0004-0000-4000-a000-d71a00000004` | 04:15 | runnable | — | 50 min |
| import-oracle-lamb-ausencias-daily | `a1c0de00-0000-4000-8000-00000000a05e` | 05:00 | runnable | Ausencias | 2 min |
| recon-oracle-lamb-trabajadores-daily | `23b9fde4-6a5f-4c84-9370-0971fb27be73` | 06:00 | runnable | Trabajadores | 12 min |
| recon-oracle-lamb-estudiantes-daily | `9bcfb273-3d8e-4acb-84b0-e7c8b490975b` | 06:20 | runnable | Estudiantes | 54 min |
| recon-oracle-lamb-egresados-daily | `86c3766a-77a6-4635-853c-998b26cad45c` | 07:45 | runnable | Egresados | 1 h 16 min |
| recon-koha-upeu-daily | `58ef8e82-867e-432a-923e-98adcd7c57fa` | 09:15 | **running** | Koha | ~1 h 55 min |
| Trigger Scanner | `…0007` | cada 300 s | runnable | — | 4 s |
| Validity Scanner | `…0006` | cada 900 s | runnable | — | <1 s |
| Cleanup | `…0005` | cada 86.400 s | runnable | — | <1 s |

- **Crons del host:**
  - backup a S3 a las **22:30** todos los días;
  - purga de auditoría el **día 1 a las 03:00**.
- **Suspendidas o cerradas:** el resto de las 57 son canarios, simulaciones y lotes puntuales. Ninguna está programada; entre ellas `import-entra-id-hourly` (suspendida) y «Recompute all users» (suspendida).
- **Ventana natural:** de **~11:30 a 22:00**, después de la recon de Koha y antes del backup, y con la recon de Entra ya terminada.
- **Durante la ventana:** suspender las 8 tareas de negocio. Las 3 de sistema se paran con el nodo.

---

## 7. Riesgos y bloqueantes, por gravedad

### Bloqueantes: si no se atienden, 4.11 no arranca o no funciona

- **R1. Contenedor no-root (UID 1000).**
  - Hoy todo corre como root. `keystore.jceks` es **root 0600**: el uid 1000 no podría leerlo y **no se descifra nada** (ni credenciales de recursos ni contraseñas).
  - `log/` (root 0750), `import/`, `export/` y `work/` también quedan sin escritura.
  - Remedio: con el contenedor parado, `chown -R 1000:1000` del volumen `midpoint_midpoint_home`, como en la nota de la versión: `docker run --rm -v midpoint_midpoint_home:/var --user 0 busybox chown -R 1000:1000 /var`.
  - Los bind `connectors` y `certs` son 1001 y root con modo 644: legibles.
  - En el host, el uid 1000 es `devops`. Es solo cosmético.
- **R2. Ruta obligada 4.10.2 → 4.10.5 → 4.11.0.** La actualización directa solo es desde la última 4.10.x, y 4.10.5 es la que avisa de los cambios de esquema. 4.10.5 no cambia la BD.
- **R3. Migración de esquema de BD (51 → 67 y audit 10 → 16) con `upgradeableSchemaAction=stop`.**
  - midPoint **se negará a arrancar** hasta que se ejecute `ninja run-sql --upgrade` (repository y audit).
  - El servicio `data_init` del compose ejecuta `ninja -B info` y, si ve `ERROR`, lanza `run-sql --create` **sobre una BD existente**. No está verificado qué imprime `info` con el esquema desactualizado ❓.
  - Durante la actualización hay que **neutralizar `data_init`** o ejecutar la migración a mano antes (`docker compose run`/`up --no-deps`).
- **R4. Script propio `audit-partition-maintenance.sh`.**
  - Tras el cambio de audit 15 existe `ma_audit_payload_YYYYMM` con FK a `ma_audit_event_YYYYMM`.
  - El script hace DROP de delta, ref y event: **el DROP de event fallará**, porque el payload depende de él.
  - El export a S3 (`pg_dump` por mes) tampoco incluirá el payload.
  - Hay que adaptar el orden (payload, delta, ref, event) antes del 1-dic.
- **R5. `connectorRef` de LDAP-IdentityCache-UPeU** (3.9.2 → 3.10). Hasta que se cambie, **LDAP queda inoperativo** (58.883 cuentas). El cambio va por **PATCH**.

### Altos: errores silenciosos o roturas a escala

- **R6. No aplicar la SystemConfiguration de 4.11 ni sus `defaultObjectPolicyConfiguration`/`defaultScriptLanguage`.**
  - Si se aplican, rompen las 433 expresiones a la vez (ver 3.3).
  - `ninja initial-objects` debe ejecutarse **excluyendo** `000-system-configuration`, el archetype 702 y el role 004.
- **R7. ConnId 1.7.0.0-M0, un milestone, con conectores construidos para FW 1.5.x.**
  - Afecta a Koha y Zammad (con `connector-framework-internal-1.5.2.0` embebido), ScriptedSQL 2.2.10 (8 recursos, toda la entrada de Oracle) y msgraph 1.2.0.0.
  - ❓ Hay que probarlos todos en el laboratorio (test connection, import acotado, recon de canario).
- **R8. `config.xml` reescrito.** Hoy se conserva: el `init-native` no lo pisa. Pero si alguien recrea el volumen, el `config.xml` nuevo trae `safeScriptingLanguagesOnly=true` y apaga Groovy. Fijar explícitamente `false` en el `config.xml` del volumen.
- **R9. Cambio de imagen base.** 4.11 pasa a Alpine por defecto; la etiqueta `-ubuntu` sigue existiendo. El script de redimensionado de la foto de Entra (`javax.imageio`/`java.awt`) depende de las librerías gráficas del JRE headless ❓; hay que probarlo con la imagen elegida.

### Medios

- **R10. Expresiones ad hoc del administrador por GUI/REST** pasan a `none()` sin `expressions/defaults/privilegedPrincipal`. Por ejemplo, filtros con expresión en búsquedas y vistas previas de mapeos.
- **R11. Reports:** la ordenación de los valores devueltos por scripts deja de estar garantizada. Afecta a «IGA: Who has access…» y a los de simulación, que se usan en los canarios. Se resuelve importando sus versiones MEL de 4.11.
- **R12. Filtro `exists` del LDAP 3.10 corregido.** Revisar los filtros de recon con presencia, como el de la tarea `b2c3d4e5` (filtro por `ri:uid`, suspendida).
- **R13. Drift del repo** (`connectorRef` de Koha y el compose). Corregirlo antes, o el GitOps volverá a desplegar valores viejos.

### Bajos / informativos

- PolyString, iteración, OIDC, Velocity, `xerces`, clases renombradas y `hint`: **sin impacto medido**.
- PostgreSQL 16.9 está soportado. Subir a 17 es opcional y conviene hacerlo en otra ventana; la imagen bullseye está al final de su vida.
- `getObjectByOid` inexistente: bug previo, no de la 4.11.
- La auditoría de julio no se purgó.
- *(Hallazgo de seguridad omitido en este repositorio público; detalle en la nota privada del equipo.)*

## 8. Estimación del trabajo

| Bloque | Esfuerzo |
|---|---|
| Ensayo completo en el laboratorio (192.168.15.150) con el dump de anoche (2,7 GB) y el tar del home: 4.10.5 → 4.11.0, chown, `run-sql --upgrade`, PATCH de LDAP, prueba de los 4 conectores custom y de los 8 ScriptedSQL, recon de canario por recurso | 2–3 días |
| Adaptar `audit-partition-maintenance.sh` (payload) y el export | 0,5 día |
| `config.xml`: `safeScriptingLanguagesOnly=false` explícito; compose: `MP_VER`, `data_init` | 0,5 día |
| Initial objects: importar las versiones MEL de 13 reports, 2 dashboards, 4 marks, 1 collection y la value policy (**135 scripts de Evolveum**), excluyendo sysconfig, 702 y 004 | 0,5 día |
| Ventana en PROD: dos pasos, 4.10.2 → 4.10.5 y luego → 4.11.0. Cada salto: backup verificado con `.sha256`, parar tareas, upgrade, test, reanudar | 2 ventanas de ~3 h |
| **Fuera del camino crítico, cuando se quiera adoptar los perfiles de 4.11:** migrar a MEL **298 scripts de UPeU (205 únicos)**: 192 triviales (`basic.*`/Groovy), 60 con API de midPoint (gates `isFullyPersistent`, `hasLinkedAccount`, LookupTable), **46 con Java/red** (descarga de la foto por URL, redimensionado de imagen, HttpClient a Telegram, `TriggerType`, DN jerárquico). Además, 11 llamadas `function` que el perfil `configuration` deniega. El HTTP a Telegram necesita otro transporte | 3–5 semanas |

**Conclusión:** la actualización a 4.11.0 es **viable sin reescribir expresiones**, siempre que no se toque la SystemConfiguration y el `config.xml` mantenga Groovy. Los bloqueantes reales son de plataforma: UID 1000, migración de BD y `data_init`, `connectorRef` de LDAP y el script de auditoría. Lo único con riesgo técnico desconocido es ConnId 1.7.0.0-M0 con los conectores custom y ScriptedSQL; eso se resuelve solo con el ensayo en el laboratorio.
