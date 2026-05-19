# midPointEcosystem — Fuente única de verdad IGA UPeU

Repositorio canónico de la configuración MidPoint 4.10.x de la Universidad Peruana Unión (UPeU). Operado por GitOps; clonado en PROD en `/home/juansanchez/midPointEcosystem/` (`192.168.15.166`).

## Estructura (post-consolidación 2026-05-19)

```
midPointEcosystem/
├── canonical/                  # CAPA 1: agnóstica (eduPerson / SCHAC / RBAC / SCIM / ISO 24760)
│   ├── schemas/                # sciback-person-v1.0.xml (urn:sciback:midpoint:person)
│   ├── archetypes/{user,org}/
│   ├── object-templates/       # UserTemplate-Person-Base
│   ├── policies/               # owners-required, sod-basic
│   ├── function-libraries/
│   └── roles/                  # (futuro) roles canónicos
│
├── upeu/                       # CAPA 2: overlay tenant UPeU
│   ├── schemas/                # upeu-local-v1.0.xml (urn:upeu:midpoint:local)
│   ├── archetypes/{auxiliary,custom}/
│   ├── orgs/                   # Jerarquía UPeU (root, facultades, campus, colegio-union, partners)
│   ├── resources/              # oracle-lamb/, ldap-identity-cache, entra-id-graph, koha-ils, ad-upeu
│   ├── roles/                  # affiliation/, application/, business/, governance/, mof/, system/
│   ├── services/positions/     # Catálogo Positions Ley 30220 / Resol. 0001-2026
│   ├── lookup-tables/
│   ├── object-collections/
│   ├── dashboards/
│   ├── auth/
│   ├── object-templates/       # (futuro) overrides per-archetype UPeU
│   ├── tasks/{simulations,pilots}/
│   └── system/
│
├── docs/                       # Documentación viva (ROADMAP, ARCHITECTURE, profiles, eduperson, runbooks, specs)
│   ├── canonical/              # Referencia eduPerson + SSO vendors
│   ├── runbooks/               # upgrade-midpoint-docker, tickets-david, tickets-rudy, onboarding-sso
│   ├── specs/                  # ClaudeFlow specs históricas (iga-canonical-model, multi-profile, …)
│   └── catalogo-positions-upeu/
│
├── datasets/                   # CSV/PostgreSQL demo (testing)
├── archive/                    # Material histórico (NO importar a PROD)
│   ├── previous/               # Schemas/resources legacy
│   ├── backups-2026-05/        # Snapshots forensic críticos
│   ├── specs/                  # Specs superseded
│   └── connector-keycloak-http/ # Conector custom archivado (decisión 2026-05-11)
│
└── midpoint-project.yaml       # Descriptor ninja/Studio
```

## Quick-start

1. **Leer** `docs/ARCHITECTURE.md` y `docs/ROADMAP.md` para el modelo IGA canónico actual.
2. **Acceso PROD:** `sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod` (alias en `~/.ssh/config`, secreto en `~/.secrets/midpoint-upeu.env`).
3. **GitOps:** editar local → commit → push → en PROD `cd /home/juansanchez/midPointEcosystem && git pull` → reaplicar selectivo vía REST API.
4. **NUNCA** `scp`. **NUNCA** `git push --force` a `main`.

## Principios

1. **Canónico primero.** El modelo se diseña contra estándares (eduPerson 202208, SCHAC, NIST RBAC, ISO 24760). Los datos UPeU se mapean al modelo canónico, no al revés.
2. **Schema is the law.** Antes de extender, buscar en core MidPoint.
3. **OIDs estables.** Filename puede cambiar; OID nunca.
4. **Reality vs Policy.** Assignments = policy. Shadows/links = reality.
5. **Oracle LAMB solo lectura.** Política absoluta.

## Histórico

Esta consolidación (2026-05-19) fusionó el material del repo paralelo `SciBack/midpoint` en una única estructura `canonical/ + upeu/`. Ver `docs/AUDIT-CONSOLIDATION-2026-05-19.md` (auditoría) y `docs/MIGRATION-EXECUTED-2026-05-19.md` (ejecución). Decisiones pendientes en `docs/MIGRATION-DECISIONS-PENDING.md`.
