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
| `pruebas-alberto-1` | 192.168.15.230 | ticrai | Desarrollo |
| `pruebas-alberto-2` | 192.168.15.231 | ticrai | Sandbox |
| `midpoint-prod` | 192.168.15.166 | juansanchez | **Producción** |

Secretos:
- Dev: `~/.secrets/upeu-infra.env` (`TICRAI_PASS`)
- Prod: `~/.secrets/midpoint-upeu.env` (`MIDPOINT_PROD_PASS`)

SSH con password:
```bash
source ~/.secrets/midpoint-upeu.env
sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod "<comando>"
```

**Conectividad a la LAN UPeU:** vía VPN corporativa, O vía túnel WireGuard OCI (nuevo, reemplaza la VPN). Si `.166` y el resto de `192.168.x` no responden = red/VPN caída, no el servidor. Levantar túnel en la Mac: `~/.secrets/wg-upeu-oci/wg-mac.sh up`. PROD .166 es el **ancla** del túnel. Detalles en el CLAUDE.md global ("Acceso a la LAN interna de UPeU") y memoria `project_wg-tunnel-oci-upeu-2026-07-03`.

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

ClaudeFlow specs en `docs/specs/`.

## Convenciones

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
