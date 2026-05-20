# Runbook — Keycloak User Federation → OpenLDAP Identity Cache

**Fecha de verificación:** 2026-05-19
**Owner:** Alberto Sánchez (DTI/Infra)
**Estado:** Funcional en producción

---

## Arquitectura actual

```
Keycloak (192.168.12.88)
  keyid.upeu.edu.pe
        │
        │  TCP 389 (LDAP) — directo, sin proxy
        │  abierto por Rudy 2026-05-19
        ▼
OpenLDAP (192.168.15.168)
  ldap-identity-trust
  dc=upeu,dc=edu,dc=pe
        ▲
        │  provisioning continuo (outbound)
        │
MidPoint PROD (192.168.15.166)
  Resource: LDAP-IdentityCache-UPeU
```

**Flujo de identidades:**

1. Oracle LAMB → MidPoint (inbound) → OpenLDAP (outbound / provisioning)
2. Keycloak lee OpenLDAP para autenticar usuarios en SSO (realm `upeu`)
3. Keycloak NO escribe en OpenLDAP — solo lectura

---

## Servidores involucrados

| Servidor | IP | Rol |
|---|---|---|
| `keycloak-prod` | 192.168.12.88 | SSO (Keycloak 26.6.1) |
| `ldap-identity-trust` | 192.168.15.168 | Directorio centralizado (OpenLDAP, Docker) |
| `midpoint-prod` | 192.168.15.166 | Orquestador IGA (MidPoint 4.10.x) |

---

## OpenLDAP en 15.168

**Contenedor:** `openldap` (Docker, imagen bitnami/openldap)
**Compose:** `/opt/ldap/docker-compose.yml`
**Variables:** `/opt/ldap/.env`

| Parámetro | Valor |
|---|---|
| Base DN | `dc=upeu,dc=edu,dc=pe` |
| Puerto | 389 (LDAP) y 636 (LDAPS) |
| Bind IP | `192.168.15.168` (no 0.0.0.0) |
| Admin DN | `cn=admin,dc=upeu,dc=edu,dc=pe` |
| Admin pass | `LDAP_ADMIN_PASS` en `/opt/ldap/.env` |
| Árbol de usuarios | `ou=people,dc=upeu,dc=edu,dc=pe` |

**Service accounts:**

| DN | Usado por | Password (env) |
|---|---|---|
| `cn=keycloak,dc=upeu,dc=edu,dc=pe` | Keycloak User Federation | `LDAP_KEYCLOAK_PASS` |
| `cn=midpoint,dc=upeu,dc=edu,dc=pe` | MidPoint Resource | `LDAP_MIDPOINT_PASS` |

---

## Keycloak — User Federation configurada

**Realm:** `upeu`
**Provider activo:** `OpenLDAP Identity Cache UPeU`
**Component ID:** `lUyeYTgrSeuojbkJKqOk1A`

| Parámetro | Valor |
|---|---|
| `connectionUrl` | `ldap://192.168.15.168:389` |
| `bindDn` | `cn=keycloak,dc=upeu,dc=edu,dc=pe` |
| `bindCredential` | `LDAP_KEYCLOAK_PASS` (ver `/opt/ldap/.env` en 15.168) |
| `usersDn` | `ou=people,dc=upeu,dc=edu,dc=pe` |
| `enabled` | `true` |

**Otros providers en realm upeu (todos disabled):**

| Nombre | URL | Estado |
|---|---|---|
| `LDAP UPeU Midpoint DTI Pruebas Alberto` | `ldap://192.168.15.230` | disabled — dev, no usar |
| `LDAP UPeU Midpoint Mac Alberto` | `ldap://192.168.25.6` | disabled — dev local, no usar |
| `UPeU AD ACADEMIC` | `ldap://lim.upeu.edu.pe` | disabled — AD antiguo |
| `UPeU AD CRAI` | `ldap://lim.upeu.edu.pe` | disabled — AD antiguo |
| `UPeU AD upeu-id` | `ldap://192.168.15.240` | disabled — AD antiguo |

---

## Historial — qué estaba mal y cómo se corrigió (2026-05-19)

| Problema | Valor incorrecto | Valor correcto |
|---|---|---|
| `connectionUrl` en Keycloak | `ldap://192.168.15.166:8080` (MidPoint HTTP) | `ldap://192.168.15.168:389` |
| `bindCredential` en Keycloak | `keycloak2024` (inválida) | `Kc@Ldap2026!` |
| Firewall TCP 389 (12.88→15.168) | Cerrado | Abierto por Rudy |

No existía proxy de red. La conexión directa estaba bloqueada y la configuración apuntaba a una dirección incorrecta.

---

## Verificación rápida

Desde el servidor Keycloak (`ssh keycloak-prod`):

```bash
# 1. Conectividad TCP
nc -zv 192.168.15.168 389

# 2. Bind y búsqueda de usuarios
ldapsearch -x -H ldap://192.168.15.168:389 \
  -D 'cn=keycloak,dc=upeu,dc=edu,dc=pe' \
  -w '<LDAP_KEYCLOAK_PASS>' \
  -b 'ou=people,dc=upeu,dc=edu,dc=pe' \
  '(objectClass=inetOrgPerson)' uid cn -z 3
```

Resultado esperado: listado de usuarios con `uid` y `cn`. `result: 4` es normal (límite de `-z`).

---

## Si deja de funcionar

1. **Verificar OpenLDAP:** `ssh juansanchez@192.168.15.168` → `docker ps` → `openldap` debe estar `healthy`.
2. **Verificar firewall:** `nc -zv 192.168.15.168 389` desde Keycloak. Si falla → ticket a Rudy (regla TCP 389 de 12.88 a 15.168).
3. **Verificar credenciales:** El password de `cn=keycloak` está en `/opt/ldap/.env` como `LDAP_KEYCLOAK_PASS`. Si fue rotado, actualizar en Keycloak Admin UI: `realm upeu → User Federation → OpenLDAP Identity Cache UPeU → Credentials`.
4. **Verificar que MidPoint sigue provisionando:** Si el LDAP tiene pocas entradas, verificar el Resource `LDAP-IdentityCache-UPeU` en MidPoint PROD y lanzar reconcile manual.
