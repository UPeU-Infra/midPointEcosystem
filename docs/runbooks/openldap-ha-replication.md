# OpenLDAP N-Way Multimaster — Runbook UPeU

## Arquitectura

```
MidPoint PROD (192.168.15.166)
    │ escribe (outbound, cn=midpoint)
    ▼
OpenLDAP Nodo 1 (192.168.15.168)  ←──syncrepl──→  OpenLDAP Nodo 2 (192.168.15.169)
    ▲                                                       ▲
    └─── Keycloak (192.168.12.88) lee desde ambos ─────────┘
```

**Imagen:** `osixia/openldap:1.5.0` (OpenLDAP 2.4.57, backend mdb, cn=config OLC dinámico)  
**Base DN:** `dc=upeu,dc=edu,dc=pe`  
**Árbol de usuarios:** `ou=people,dc=upeu,dc=edu,dc=pe`  
**Compose en cada nodo:** `/opt/ldap/docker-compose.yml`  
**Env (passwords):** `/opt/ldap/.env`

---

## INCIDENTE 2026-05-20 — Pérdida de datos por mirrormode mal configurado

### Causa raíz

Al configurar `olcServerID` con URL (`olcServerID: 1 ldap://192.168.15.168:389`), slapd
falla al arrancar con el error `no serverID / URL match found`. Esto ocurre porque osixia
inicia slapd con `-h "ldap:/// ldaps:/// ldapi:///"` (wildcard), no con la URL específica.

Adicionalmente, al activar `olcMirrorMode: TRUE` con un nodo consumer vacío, OpenLDAP
propaga la base vacía del nodo 2 al nodo 1, borrando los datos del nodo maestro.

### Lección aprendida

1. `olcServerID` debe usarse SIN URL cuando slapd escucha en wildcard (`ldap:///`).
   Usar solo el número: `olcServerID: 1`
2. Configurar syncprov en el nodo maestro PRIMERO. No activar mirrormode en el nodo
   maestro hasta que el nodo replica tenga los datos.
3. La secuencia correcta es: proveedor activo → consumer sincroniza datos → luego
   activar mirrormode en ambos.

### Recuperación aplicada

Re-provisión completa desde MidPoint PROD usando recompute task con 4 workers.
Los 34k+ usuarios fueron re-creados en ~2 horas.

---

## Configuración N-Way Multimaster — Procedimiento Correcto

### Pre-requisitos

- Nodo 1 tiene datos (es el nodo maestro con todos los usuarios)
- Nodo 2 está limpio (o se puede limpiar sin riesgo)
- Ambos nodos tienen `osixia/openldap:1.5.0` corriendo y healthy
- Modulo syncprov disponible en `/usr/lib/ldap/syncprov.so`
- `entryCSN` y `entryUUID` ya indexados en nodo 1

### Variables necesarias

```bash
source ~/.secrets/ldap-upeu.env
# LDAP_PROD_PASS = password SSH a juansanchez@192.168.15.168 y 192.168.15.169
# LDAP_ADMIN_PASS = password de cn=admin,dc=upeu,dc=edu,dc=pe
```

### FASE 1 — Preparar nodo 1 (maestro con datos)

Ejecutar dentro del contenedor del nodo 1:

```bash
# 1. Cargar módulo syncprov
docker exec openldap bash -c 'printf "%s\n" \
"dn: cn=module{0},cn=config" \
"changetype: modify" \
"add: olcModuleLoad" \
"olcModuleLoad: syncprov" \
> /tmp/01.ldif && ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/01.ldif'

# 2. Asignar ServerID (SIN URL — solo el número)
docker exec openldap bash -c 'printf "%s\n" \
"dn: cn=config" \
"changetype: modify" \
"add: olcServerID" \
"olcServerID: 1" \
> /tmp/02.ldif && ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/02.ldif'

# 3. Añadir overlay syncprov a la base mdb
docker exec openldap bash -c 'printf "%s\n" \
"dn: olcOverlay=syncprov,olcDatabase={1}mdb,cn=config" \
"changetype: add" \
"objectClass: olcOverlayConfig" \
"objectClass: olcSyncProvConfig" \
"olcOverlay: syncprov" \
"olcSpCheckpoint: 100 10" \
"olcSpSessionLog: 200" \
> /tmp/03.ldif && ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/03.ldif'
```

### FASE 2 — Preparar nodo 2 (consumer inicial)

**IMPORTANTE:** NO activar mirrormode en el nodo 2 hasta que tenga los datos sincronizados.

```bash
# En nodo 2 (192.168.15.169):

# 1. Cargar syncprov
docker exec openldap bash -c 'printf "%s\n" \
"dn: cn=module{0},cn=config" \
"changetype: modify" \
"add: olcModuleLoad" \
"olcModuleLoad: syncprov" \
> /tmp/01.ldif && ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/01.ldif'

# 2. ServerID 2 (SIN URL)
docker exec openldap bash -c 'printf "%s\n" \
"dn: cn=config" \
"changetype: modify" \
"add: olcServerID" \
"olcServerID: 2" \
> /tmp/02.ldif && ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/02.ldif'

# 3. Overlay syncprov
docker exec openldap bash -c 'printf "%s\n" \
"dn: olcOverlay=syncprov,olcDatabase={1}mdb,cn=config" \
"changetype: add" \
"objectClass: olcOverlayConfig" \
"objectClass: olcSyncProvConfig" \
"olcOverlay: syncprov" \
"olcSpCheckpoint: 100 10" \
"olcSpSessionLog: 200" \
> /tmp/03.ldif && ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/03.ldif'

# 4. Configurar syncrepl consumer (jala desde nodo 1)
#    SIN mirrormode por ahora
ADMIN_PASS=$(grep LDAP_ADMIN_PASS /opt/ldap/.env | cut -d= -f2)
docker exec -i openldap bash << INNERSCRIPT
ADMIN_PASS="${ADMIN_PASS}"
cat > /tmp/04.ldif << LDIFEOF
dn: olcDatabase={1}mdb,cn=config
changetype: modify
add: olcSyncRepl
olcSyncRepl: rid=001
  provider=ldap://192.168.15.168:389
  bindmethod=simple
  binddn=cn=admin,dc=upeu,dc=edu,dc=pe
  credentials=${ADMIN_PASS}
  searchbase=dc=upeu,dc=edu,dc=pe
  scope=sub
  schemachecking=on
  type=refreshAndPersist
  retry="30 5 300 3"
  interval=00:00:05:00
LDIFEOF
ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/04.ldif 2>&1
INNERSCRIPT
```

### FASE 3 — Verificar sincronización inicial

Esperar que el nodo 2 sincronice todos los datos del nodo 1. Con 34k entradas, puede tomar 10-30 minutos.

```bash
# Contar entradas en nodo 2 (debe igualar al nodo 1)
for host in 192.168.15.168 192.168.15.169; do
  echo -n "Nodo $host: "
  sshpass -p "$LDAP_PROD_PASS" ssh -o StrictHostKeyChecking=no juansanchez@$host \
    "ADMIN_PASS=\$(grep LDAP_ADMIN_PASS /opt/ldap/.env | cut -d= -f2) && \
    docker exec openldap ldapsearch -x -H ldap://localhost:389 \
    -D 'cn=admin,dc=upeu,dc=edu,dc=pe' -w \"\$ADMIN_PASS\" \
    -b 'ou=people,dc=upeu,dc=edu,dc=pe' '(objectClass=*)' dn 2>/dev/null | \
    grep '^dn:' | wc -l"
done
```

### FASE 4 — Activar mirrormode (solo cuando nodo 2 esté sincronizado)

Solo ejecutar cuando los counts sean iguales en ambos nodos.

```bash
# Activar mirrormode en nodo 2
docker exec openldap bash -c 'printf "%s\n" \
"dn: olcDatabase={1}mdb,cn=config" \
"changetype: modify" \
"add: olcMirrorMode" \
"olcMirrorMode: TRUE" \
> /tmp/05.ldif && ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/05.ldif'

# Configurar syncrepl + mirrormode en nodo 1 (consumer desde nodo 2)
ADMIN_PASS=$(grep LDAP_ADMIN_PASS /opt/ldap/.env | cut -d= -f2)
docker exec -i openldap bash << INNERSCRIPT
ADMIN_PASS="${ADMIN_PASS}"
cat > /tmp/06.ldif << LDIFEOF
dn: olcDatabase={1}mdb,cn=config
changetype: modify
add: olcSyncRepl
olcSyncRepl: rid=002
  provider=ldap://192.168.15.169:389
  bindmethod=simple
  binddn=cn=admin,dc=upeu,dc=edu,dc=pe
  credentials=${ADMIN_PASS}
  searchbase=dc=upeu,dc=edu,dc=pe
  scope=sub
  schemachecking=on
  type=refreshAndPersist
  retry="30 5 300 3"
  interval=00:00:05:00
-
add: olcMirrorMode
olcMirrorMode: TRUE
LDIFEOF
ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/06.ldif 2>&1
INNERSCRIPT
```

---

## Verificación del estado de replicación

```bash
# 1. Contar entradas en ambos nodos
for host in 192.168.15.168 192.168.15.169; do
  echo -n "Nodo $host entradas en ou=people: "
  sshpass -p "$LDAP_PROD_PASS" ssh -o StrictHostKeyChecking=no juansanchez@$host \
    "ADMIN_PASS=\$(grep LDAP_ADMIN_PASS /opt/ldap/.env | cut -d= -f2) && \
    docker exec openldap ldapsearch -x -H ldap://localhost:389 \
    -D 'cn=admin,dc=upeu,dc=edu,dc=pe' -w \"\$ADMIN_PASS\" \
    -b 'ou=people,dc=upeu,dc=edu,dc=pe' '(objectClass=*)' dn 2>/dev/null | \
    grep '^dn:' | wc -l"
done

# 2. Verificar contextCSN en ambos nodos (debe ser igual)
for host in 192.168.15.168 192.168.15.169; do
  echo "=== contextCSN nodo $host ==="
  sshpass -p "$LDAP_PROD_PASS" ssh -o StrictHostKeyChecking=no juansanchez@$host \
    "docker exec openldap ldapsearch -Y EXTERNAL -H ldapi:/// \
    -b 'dc=upeu,dc=edu,dc=pe' -s base contextCSN 2>/dev/null | grep contextCSN"
done

# 3. Verificar conexiones TCP activas de replicación
for host in 192.168.15.168 192.168.15.169; do
  echo "=== Conexiones TCP nodo $host ==="
  sshpass -p "$LDAP_PROD_PASS" ssh -o StrictHostKeyChecking=no juansanchez@$host \
    "docker exec openldap ss -tnp | grep ':389'"
done

# 4. Verificar config syncrepl en cada nodo
for host in 192.168.15.168 192.168.15.169; do
  echo "=== SyncRepl config nodo $host ==="
  sshpass -p "$LDAP_PROD_PASS" ssh -o StrictHostKeyChecking=no juansanchez@$host \
    "docker exec openldap ldapsearch -Y EXTERNAL -H ldapi:/// \
    -b 'olcDatabase={1}mdb,cn=config' -s base olcSyncrepl olcMirrorMode 2>/dev/null | \
    grep -E 'olcSync|olcMirror'"
done
```

---

## Recuperación de datos desde MidPoint

Si los datos LDAP se pierden, re-provisionarlos con un recompute task:

```bash
# Crear y lanzar task de recompute con 4 workers
source ~/.secrets/midpoint-upeu.env
cat > /tmp/recompute-recovery.xml << 'XMLEOF'
<?xml version="1.0" encoding="UTF-8"?>
<task xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
      xmlns:org="http://midpoint.evolveum.com/xml/ns/public/common/org-3">
    <name>LDAP Recompute Recovery</name>
    <ownerRef oid="00000000-0000-0000-0000-000000000002" relation="org:default" type="UserType"/>
    <executionState>runnable</executionState>
    <activity>
        <work>
            <recomputation>
                <objects>
                    <type>UserType</type>
                </objects>
            </recomputation>
        </work>
        <distribution>
            <workerThreads>4</workerThreads>
        </distribution>
    </activity>
    <binding>loose</binding>
    <schedule>
        <misfireAction>executeImmediately</misfireAction>
    </schedule>
</task>
XMLEOF

sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
  "curl -s -u '${MIDPOINT_ADMIN_USER}:${MIDPOINT_ADMIN_PASS}' \
  'http://localhost:8080/midpoint/ws/rest/tasks' \
  -X POST -H 'Content-Type: application/xml' \
  -d @/tmp/recompute-recovery.xml -w '\nHTTP:%{http_code}'"
```

Monitorear progreso:
```bash
# Contar entradas en LDAP (esperar que llegue a ~34k)
sshpass -p "$LDAP_PROD_PASS" ssh -o StrictHostKeyChecking=no juansanchez@192.168.15.168 \
  "ADMIN_PASS=\$(grep LDAP_ADMIN_PASS /opt/ldap/.env | cut -d= -f2) && \
  docker exec openldap ldapsearch -x -H ldap://localhost:389 \
  -D 'cn=admin,dc=upeu,dc=edu,dc=pe' -w \"\$ADMIN_PASS\" \
  -b 'ou=people,dc=upeu,dc=edu,dc=pe' '(objectClass=*)' dn 2>/dev/null | \
  grep '^dn:' | wc -l"
```

---

## Restaurar después de reinicio del nodo 1

Si el nodo 1 reinicia y slapd falla con `no serverID / URL match found`:

```bash
# Corregir olcServerID en el volumen de config (quitar URL, dejar solo número)
docker run --rm -v ldap_ldap_config:/etc/ldap/slapd.d \
  --entrypoint='' osixia/openldap:1.5.0 bash -c \
  'sed -i "s/olcServerID: [0-9] ldap:\/\/.*/olcServerID: 1/" \
  /etc/ldap/slapd.d/cn=config.ldif && grep olcServerID /etc/ldap/slapd.d/cn=config.ldif'

# Mismo para nodo 2 (cambiar 1 por 2)
docker run --rm -v ldap_ldap_config:/etc/ldap/slapd.d \
  --entrypoint='' osixia/openldap:1.5.0 bash -c \
  'sed -i "s/olcServerID: [0-9] ldap:\/\/.*/olcServerID: 2/" \
  /etc/ldap/slapd.d/cn=config.ldif && grep olcServerID /etc/ldap/slapd.d/cn=config.ldif'
```

---

## Integración con MidPoint

El resource LDAP apunta al nodo 1 como primary: `192.168.15.168:389`

Para activar failover en MidPoint, actualizar `upeu/resources/ldap-identity-cache.xml`
con la configuración de failover cuando el conector lo soporte. Ver estado en
`docs/ROADMAP.md`.

## Integración con Keycloak

User Federation `OpenLDAP Identity Cache UPeU` en realm `upeu` apunta a `192.168.15.168`.
Actualizar para agregar nodo 2 cuando ambos estén estables.
Ver runbook `keycloak-ldap-federation.md`.

---

## Estado actual (2026-06-07) ✅ REPLICACIÓN N-WAY OPERATIVA

### Estado tras fix completo (2026-06-07)

**Incidente:** Replicación rota desde 2026-05-26. Causa raíz: `olcServerID` no configurado en ningún nodo → ambos usaban serverID `000` → CSN conflictivo → syncrepl consumer de nodo 2 se colgó.

**Fix aplicado:**
1. `olcServerID: 1` en nodo 1 (168) — via `ldapmodify -Y EXTERNAL`
2. `olcServerID: 2` en nodo 2 (169) — via `ldapmodify -Y EXTERNAL`
3. Schema `cn={12}upeu` faltaba en nodo 2 → importado con `ldapadd -Y EXTERNAL`
4. Limpieza de datos de nodo 2 (`data.mdb` + `lock.mdb` del volumen `ldap_ldap_data`) + restart
5. Full resync automático desde nodo 1 (~10 minutos, ~28K entradas)

**Estado final verificado:**
- Nodo 1 (168): `olcServerID: 1`, 48,348 people, contextCSN `20260607080739Z#000#000000`
- Nodo 2 (169): `olcServerID: 2`, 48,348 people, mismo contextCSN ✅
- Replicación bidireccional activa: rid=001 (169→168) y rid=002 (168→169) ✅
- Sin errores de replicación en logs ✅
- MidPoint (192.168.15.166) → Nodo 1:389 ✅
- Keycloak (192.168.12.88) → Nodo 1:389 ✅
- Schemas en ambos nodos: core, cosine, nis, inetorgperson, ppolicy, kopano, openssh-lpk, postfix-book, samba, eduPerson, schac, midpointperson, **upeu** ✅

### Lecciones adicionales (L9–L11)

**L9: olcServerID sin URL**
Usar `olcServerID: 1` (solo número). Con URL (`olcServerID: 1 ldap://...`) slapd falla
si escucha en wildcard (`ldap:///`). Causa del incidente original 2026-05-20.

**L10: Schema faltante → syncrepl falla silenciosamente**
Si el nodo consumer no tiene un schema que el provider usa, `syncrepl_message_to_entry`
falla con "objectClass value #N invalid per syntax". El error PARECE de sintaxis pero es
de schema desconocido. Fix: importar el schema faltante, luego restart.
En este caso: `cn=upeu` (OID 1.3.6.1.4.1.47378) fue añadido a nodo 1 post-divergencia
y nunca replicado a nodo 2.

**L11: Wipe + resync es más limpio que resolver conflictos LDAP_TYPE_OR_VALUE_EXISTS**
Si el consumer tiene datos conflictivos (writes directos vía failover durante split-brain),
el resync incremental falla con err=20. La solución: borrar `data.mdb` + `lock.mdb`
del volumen de datos (NO el config) y hacer full resync. El volumen config preserva
olcServerID, schemas, syncrepl config y mirrormode — todo lo necesario para el resync.

### Pendiente

- Actualizar Keycloak User Federation para incluir nodo 2 como fallback (actualmente solo nodo 1)
- Verificar MidPoint failover: la conexión desde 192.168.15.166 a nodo 2 ya no está activa
  (correcto — failover solo activa si nodo 1 cae). Confirmar comportamiento en próxima
  ventana de mantenimiento.
