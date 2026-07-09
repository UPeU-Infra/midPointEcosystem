# Keycloak — Motor SSO de la suite Identidad & Seguridad

Sub-componente **canónico** de IGA. Keycloak es el servidor IAM/SSO (OIDC/SAML) que
da inicio de sesión federado a los productos de la línea *Identidad & Seguridad*
(IGA, Smart WiFi, Unified Access) y a servicios institucionales (GUIA, Indico, Koha, Moodle).

> **Clasificación (ADR-054):** Keycloak **no es un producto vendible suelto** — es un
> ladrillo transversal de identidad. Vive aquí, dentro de IGA (donde se comercializa como
> parte de la suite), y el resto de productos lo **referencian**, no lo copian.
> El paquete cliente Python vive aparte en
> [`sciback/sciback-core/packages/sciback-identity-keycloak`](../../../../sciback/sciback-core/packages/sciback-identity-keycloak).

## Alcance de este componente

- **`deploy/`** — capa canónica de despliegue (Compose + realm base + config) reutilizable
  para instanciar Keycloak en cualquier cliente. **Pendiente de extracción desde PROD** — ver [deploy/README.md](deploy/README.md).
- **`docs/`** — KB especializada que alimenta al agente `keycloak-expert`.

## Estado del despliegue de referencia (UPeU PROD)

| Ítem | Valor |
|---|---|
| URL pública | https://keyid.upeu.edu.pe |
| URL directa | https://192.168.12.88 (cert auto-firmado) |
| Versión | Keycloak 26.6.1 (`quay.io/keycloak/keycloak:26.6.1`) |
| Host | `192.168.12.88` (Rocky Linux), SSH `juansanchez` |
| Compose dir (en el host) | `/u01/container_hosts/keycloak/` |
| Base de datos | contenedor `keycloak_db` (`postgres:16`) |
| Realm de producción | `upeu` (IdP MicrosoftUPeU + todos los clientes) |
| Secretos | `~/.secrets/keycloak-prod.env` |

> ⚠️ El Compose real **solo existe en el host**, sin versionar. El primer entregable de
> `deploy/` es traerlo al repo y parametrizarlo como capa canónica (ver plan en `deploy/`).

## Material existente (consolidado, no duplicado)

| Doc | Ubicación | Qué cubre |
|---|---|---|
| User Federation → OpenLDAP | [`docs/runbooks/keycloak-ldap-federation.md`](../docs/runbooks/keycloak-ldap-federation.md) | Federación Keycloak → OpenLDAP identity-cache (PROD, verificado 2026-05-19) |
| Config Fase 6 federation | [`upeu/ldap/keycloak-user-federation.md`](../upeu/ldap/keycloak-user-federation.md) | Parámetros de conexión y pasos en Admin Console |
| Conector ConnId Keycloak (Java) | [`archive/connector-keycloak-http/`](../archive/connector-keycloak-http/) | Conector MidPoint→Keycloak HTTP (archivado) |

## Agente especialista

[`keycloak-expert`](~/.claude/agents/keycloak-expert.md) — invócalo para cualquier tarea de
Keycloak. Su contexto de despliegue UPeU vive embebido; esta carpeta es la KB canónica del
componente que debe mantenerse en sincronía con él.
