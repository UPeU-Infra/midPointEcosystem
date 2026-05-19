# Keycloak User Federation — OpenLDAP UPeU
## Fase 6 — Instrucciones de configuración (implementar post-import piloto)

### Prerrequisitos antes de implementar

1. Import piloto completado (al menos 50 usuarios activos en ou=people,dc=upeu,dc=edu,dc=pe)
2. Verificar que Keycloak en 192.168.12.88 tiene conectividad a 192.168.15.168:389
3. El SA `cn=keycloak,dc=upeu,dc=edu,dc=pe` tiene acceso read-only a ou=people

### Datos de conexión

| Parámetro | Valor |
|---|---|
| Connection URL | ldap://192.168.15.168:389 |
| Bind DN | cn=keycloak,dc=upeu,dc=edu,dc=pe |
| Bind Credential | Kc@Ldap2026! |
| User DN | ou=people,dc=upeu,dc=edu,dc=pe |
| User object classes | inetOrgPerson, eduPerson |
| UUID LDAP attribute | uid |
| Username LDAP attribute | uid |
| RDN LDAP attribute | uid |

### Pasos de configuración en Keycloak Admin Console

1. Ir a: **realm upeu → User Federation → Add provider → LDAP**

2. Configurar la sección **Required Settings**:
   ```
   UI display name:    OpenLDAP-Identity-Cache-UPeU
   Vendor:             Other (NOT Active Directory)
   Connection URL:     ldap://192.168.15.168:389
   Enable StartTLS:    OFF
   Use Truststore SPI: Never
   Bind type:          simple
   Bind DN:            cn=keycloak,dc=upeu,dc=edu,dc=pe
   Bind credentials:   [ver ~/.secrets/ldap-upeu.env LDAP_KEYCLOAK_PASS]
   Edit mode:          READ_ONLY
   Users DN:           ou=people,dc=upeu,dc=edu,dc=pe
   Username LDAP attr: uid
   RDN LDAP attr:      uid
   UUID LDAP attr:     uid
   User object classes: inetOrgPerson, eduPerson
   Search scope:       One Level
   Pagination:         ON (VLV/sssvlv está activo en OpenLDAP)
   ```

3. Configurar la sección **Sync Settings**:
   ```
   Import users:         ON
   Sync Registrations:   OFF  (LDAP es read-only para Keycloak)
   Batch size:           100
   Periodic full sync:   ON — Period: 86400 (24h)
   Periodic changed sync: ON — Period: 3600 (1h)
   ```

4. Hacer clic en **Save** y luego **Test connection** → debe decir "Connection successful"

5. Hacer clic en **Test authentication** con las credenciales del SA keycloak → "Authentication successful"

6. Hacer clic en **Synchronize all users** (primera sincronización)

### Attribute Mappers (crear después de guardar la federation)

Ir a la federation creada → pestaña **Mappers** → agregar cada mapper:

#### Mapper 1: username
```
Name:           username
Mapper type:    user-attribute-ldap-mapper
LDAP attribute: uid
User Model Attr: username
```

#### Mapper 2: email
```
Name:           email
Mapper type:    user-attribute-ldap-mapper
LDAP attribute: mail
User Model Attr: email
```

#### Mapper 3: firstName
```
Name:           firstName
Mapper type:    user-attribute-ldap-mapper
LDAP attribute: givenName
User Model Attr: firstName
```

#### Mapper 4: lastName
```
Name:           lastName
Mapper type:    user-attribute-ldap-mapper
LDAP attribute: sn
User Model Attr: lastName
```

#### Mapper 5: eduPersonPrincipalName
```
Name:           eppn
Mapper type:    user-attribute-ldap-mapper
LDAP attribute: eduPersonPrincipalName
User Model Attr: eppn
Token Claim Name: eduPersonPrincipalName
```

#### Mapper 6: eduPersonPrimaryAffiliation
```
Name:           affiliation
Mapper type:    user-attribute-ldap-mapper
LDAP attribute: eduPersonPrimaryAffiliation
User Model Attr: affiliation
```

#### Mapper 7: schacPersonalUniqueCode
```
Name:           personalNumber
Mapper type:    user-attribute-ldap-mapper
LDAP attribute: schacPersonalUniqueCode
User Model Attr: personalNumber
```

#### Mapper 8: accountStatus (midPointAccountStatus)
```
Name:           midpoint-status
Mapper type:    user-attribute-ldap-mapper
LDAP attribute: midPointAccountStatus
User Model Attr: midPointAccountStatus
```

### Configuración de Client Scopes OIDC (para SSO académico)

Agregar al Client Scope `academic-databases-eduperson` (ya existe):
- Mapear `eppn` → `eduPersonPrincipalName` en ID token
- Mapear `affiliation` → `eduPersonPrimaryAffiliation` en ID token
- Mapear `schacPersonalUniqueCode` en token para SPs académicos

### Nota sobre cn=keycloak (ubicación)

El SA keycloak fue creado por osixia en `cn=keycloak,dc=upeu,dc=edu,dc=pe` (nivel raíz),
NO en `ou=services,dc=upeu,dc=edu,dc=pe`. El Bind DN para Keycloak es:
```
cn=keycloak,dc=upeu,dc=edu,dc=pe
```

En futuras reinstalaciones, mover a `ou=services` actualizando el LDAP_READONLY_USER_DN en osixia
o creando el SA manualmente en `ou=services` con ldapadd.

### Validación post-configuración

Después de configurar:
```bash
# Desde Keycloak admin, verificar que los usuarios se importaron:
# realm upeu → Users → Total debe mostrar >= 1 (usuarios del piloto)

# Test SSO completo:
# 1. Ir a https://biblioteca.upeu.edu.pe
# 2. Login con credenciales LDAP (username = personalNumber)
# 3. Verificar que el patron de Koha existe (MidPoint debe haberlo creado antes)
```
