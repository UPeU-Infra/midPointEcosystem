# midPointEcosystem — IGA UPeU (canónico + UPeU overlay)

## Descripción

Repositorio único de la configuración MidPoint 4.10.x de la Universidad Peruana Unión (UPeU). Resultado de la consolidación 2026-05-19 que fusionó el repo paralelo `SciBack/midpoint` en esta estructura `canonical/ + upeu/`.

## Agente — POLÍTICA OBLIGATORIA

**Para CUALQUIER tarea con MidPoint en este proyecto (XMLs, archetypes, roles, resources, tasks, ninja, REST API, troubleshooting, diagnóstico, operaciones PROD) SIEMPRE usar el sub-agente `midpoint-expert`.** No descubrir empíricamente ni operar MidPoint directamente desde el hilo principal.

El `midpoint-expert` DEBE consultar la skill `midpoint-best-practices` (y `iga-canonical-standards`) antes de cualquier diseño o decisión, para garantizar conformidad con estándares Evolveum y canónicos.

```
/agent midpoint-expert <tarea>
```

Regla: modelo canónico primero, datos UPeU se adaptan al modelo, NUNCA al revés.

## Servidores

| Alias SSH | Host | Usuario | Rol |
|-----------|------|---------|-----|
| `midpoint-prod` | 192.168.15.166 | juansanchez | **Producción** |
| — | 192.168.15.150 | devops | Laboratorio UPeU (`~/.secrets/lab-identidad.env`); su MidPoint (:8081) solo tiene LDAP |
| ~~`pruebas-alberto-1`~~ | ~~192.168.15.230~~ | — | **Ya no existe**: la máquina se liberó el 25-ago-2026 |

Secretos:
- Prod: `~/.secrets/midpoint-upeu.env` (`MIDPOINT_PROD_PASS`)
- Backups de PROD: en S3, ver [`docs/runbooks/backup-midpoint-s3/README.md`](docs/runbooks/backup-midpoint-s3/README.md)

SSH con password:
```bash
source ~/.secrets/midpoint-upeu.env
sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod "<comando>"
```

**Conectividad a la LAN UPeU:** SOLO por la VPN corporativa (WireGuard.app, túnel «JSanchez»). Si `.166` y el resto de `192.168.x` no responden, es la red o la VPN, no el servidor: comprobar con `route -n get 192.168.15.168 | grep interface`. ⚠️ **El túnel WireGuard vía OCI está muerto y retirado desde el 17-ago-2026: NO levantarlo.** Aunque esté muerto, secuestra las rutas `192.168.12/13/15` y rompe la VPN. Detalles en el CLAUDE.md global («Acceso a la LAN interna de UPeU»).

**SSH a `.166`:** a veces da «Permission denied» de forma intermitente. Un solo reintento; tres fallos seguidos bloquean la cuenta 15 minutos.

## Repos relacionados

- `UPeU-Infra/midPointEcosystem` — **este** repo (config GitOps UPeU, fuente única de verdad)
- `UPeU-Infra/connector-koha` — conector Java ConnId para Koha
- En PROD: `/home/juansanchez/midPointEcosystem/`

## Estructura

Ver `README.md`. Resumen:

```
midPointEcosystem/
├── canonical/       # Capa 1: agnóstica (eduPerson/SCHAC/RBAC/SCIM/ISO 24760)
├── upeu/            # Capa 2: overlay tenant UPeU
├── docs/            # ROADMAP, ARCHITECTURE, profiles, runbooks, specs
├── datasets/        # CSV/PG demo
├── archive/         # Material histórico (NO importar a PROD)
└── midpoint-project.yaml
```

## Flujo de trabajo

Local → commit → push → en PROD `git pull` en `/home/juansanchez/midPointEcosystem/` → reaplicar selectivo vía REST API. **Nunca** `scp`. **Nunca** `git push --force` a `main`.

### 🔴 Resources: NUNCA con `PUT`. Siempre `PATCH` del elemento concreto

Un `PUT` sobre un `ResourceType` desplegado le **arranca a PROD el `<schema>` cacheado** (el repo no lo lleva, y es correcto que no lo lleve: el `<schema>` es *estado en runtime del conector*, no configuración) → `ConfigurationException` → resource **`broken` / 502**.

**Medido 2026-07-17: afecta a 8 de los 11 resources desplegados** (los 7 Oracle LAMB ScriptedSQL + `UPEU-EntraID-Graph`). **No es un caso especial: es la forma normal del repo.**

Precedentes: **`a776e5a`** (e21 `trabajadores`: schema stale → el reconcile de docentes abortaba con 502) · **`670b312`/`8ab4dc9`** (`ldap-identity-cache` quedó `broken` tras un PUT).

Después de cualquier PATCH, **verifica** (no lo asumas): `<schema>` sigue con sus `xsd:element` · test connection todo `success` · `schemaHandling`/`capabilities`/`connectorRef` intactos.

→ **Runbook: [`docs/runbooks/NUNCA-PUT-resources-schema-cache.md`](docs/runbooks/NUNCA-PUT-resources-schema-cache.md)**

ClaudeFlow specs en `docs/specs/`.

## Nombre oficial de persona — MidPoint es la fuente (decisión 2026-11-09)

**MidPoint es la fuente de consulta del nombre oficial de cada persona de UPeU, y la más actualizada.** Todos los sistemas lo toman de aquí (LDAP, M365/Entra ID, Koha, certificados y diplomas digitales, DSpace, DSpace-CRIS, OJS…). **Ningún sistema resuelve el nombre por su cuenta** ni consulta RENIEC directamente: si lo hiciera, cada uno tendría su propia versión.

- **Regla (CRAI + DTI/Infra, por observación de CONCYTEC):** con DNI, el nombre es el del DNI tal como lo registra RENIEC (con sus tildes o sin ellas, con apellido de casada), solo pasado de MAYÚSCULAS a altas y bajas (`sb-name-normalizer`). Sin DNI (CE, PTP, pasaporte…) → el de Lamb.
- **Orden de fuentes para mejorarlo:**
  1. Lo que ya tiene MidPoint (y lo que se le cargue verificado contra RENIEC).
  2. `DAVID.CONSULTA_APIS_LOG` (caché RENIEC que alimenta admisión; costo cero).
  3. **API de pago de consultas DNI de UPeU (`~/.secrets/dni-ruc-upeu.env`): solo en casos extremos y urgentes, y siempre con aprobación expresa de Alberto, lote por lote.** Cada consulta es un gasto y el saldo es compartido con admisión. **Nunca** desde un conector o tarea de MidPoint.
- **Solo personas activas por ahora** (trabajadores y estudiantes vigentes). Egresados, ex trabajadores y jubilados: otra etapa.
- Diseño y etapas: [`docs/specs/nombre-oficial-reniec/01-diseno.md`](docs/specs/nombre-oficial-reniec/01-diseno.md).
- Hoy (2026-11-09) **el nombre visible aún viene de Lamb** (`trabajadores.xml` strong; `reniec-cache.xml` weak). `dataQualityStatus=reniec_validated` NO significa que el nombre sea el de RENIEC.

## Convenciones

- 🔴 **Antes de CUALQUIER ejecución en PROD: [`docs/runbooks/PROTOCOLO-PRE-EJECUCION-PROD.md`](docs/runbooks/PROTOCOLO-PRE-EJECUCION-PROD.md)** — 9 reglas destiladas de incidentes reales (leer el mecanismo, no muestrear; contrastar contra los docs rectores; leer la lista del lote; anclar filtros de DN; toda predicción de riesgo lleva medición previa).
- Passwords de PROD NUNCA en el repo — van en `~/.secrets/`.
- Cambios destructivos requieren backup previo (tag git + `pg_dump` si toca datos).
- Oracle LAMB solo lectura. Política absoluta.
- Schema is the law: antes de extender, buscar en core MidPoint.
- OIDs estables. Filename puede cambiar; OID nunca.

## Estado actual (2026-05-19)

- **Schemas activos en PROD:** `urn:sciback:midpoint:person` (canónico) + `urn:upeu:midpoint:local` (overlay).
- **18 archetypes activos** (8 user + 8 org + 2 role) — ver `canonical/archetypes/`.
- **7 resources** (Oracle LAMB ×4 + LDAP + Entra ID + Koha; AD en draft).
- **35.450 USER + 122 ORG + 72 ROLE** en PROD.
- **MidPoint PROD en recuperación post-OOM** (upgrade 4.10.2 hoy). Re-checkout y re-validación de PROD se hace tras recuperar.

Ver `docs/MIGRATION-EXECUTED-2026-05-19.md` y `docs/MIGRATION-DECISIONS-PENDING.md`.
