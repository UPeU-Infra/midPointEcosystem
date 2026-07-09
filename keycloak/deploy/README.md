# Keycloak — Capa canónica de despliegue

Objetivo: un despliegue de Keycloak **parametrizable e instalable en cualquier cliente**
(mismo patrón que el resto de productos SciBack: canónico agnóstico + `.env` por institución).

## Estado: 🔴 pendiente de extracción

Hoy el despliegue **solo existe en el host PROD** `192.168.12.88:/u01/container_hosts/keycloak/`,
sin versionar. Esta carpeta es el destino donde debe vivir la versión canónica.

## Plan de extracción

1. **Traer el Compose real** desde PROD:
   `ssh <host> 'cat /u01/container_hosts/keycloak/docker-compose.yml'` → guardar aquí.
2. **Parametrizar** todo lo específico de UPeU a variables → `.env.example`
   (hostname, realm, credenciales admin, DB, cert, IdP Entra/Microsoft).
3. **Realm base agnóstico** en `realms/` — export del realm mínimo sin datos UPeU
   (clientes/mappers genéricos), importable con `--import-realm`.
4. **README de instalación** — pasos para instanciar en un cliente nuevo desde cero.

## Estructura objetivo

```
deploy/
├── docker-compose.yml     # Keycloak 26.x + PostgreSQL 16, todo por variables
├── .env.example           # plantilla de parámetros por institución
├── realms/
│   └── base-realm.json     # realm mínimo agnóstico (--import-realm)
└── README.md              # (este archivo → pasos de instalación cuando esté extraído)
```

## Overlay por institución

Lo específico de cada cliente (dominio, IdP, branding, clientes OIDC/SAML reales) **no va aquí**:
va en la capa institución del cliente y su `.env` (backup en `~/.secrets/<cliente>.env`).
La referencia UPeU está en [`../../upeu/`](../../upeu/) y en el agente `keycloak-expert`.
