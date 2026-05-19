# MIGRATION-EXECUTED — Consolidación IGA UPeU

**Fecha:** 2026-05-19
**Ejecutor:** midpoint-expert (turno automatizado siguiendo `AUDIT-CONSOLIDATION-2026-05-19.md` §6 + §7)
**Base:** commit `c3f04a5` (audit) → commit `859514a` (reorganización) → este reporte
**Tag de seguridad:** `pre-consolidation-2026-05-19` (pushado a `origin`)

---

## TL;DR (10 líneas)

- **Nueva ubicación del repo:** `/Users/alberto/proyectos/upeu/midPointEcosystem/` (movido fuera del padre).
- **123 XMLs** reorganizados a estructura `canonical/` (35) + `upeu/` (88), 0 errores xmllint, 280 OIDs únicos.
- **Documentación rica** importada del repo padre: ROADMAP, ARCHITECTURE, IDENTITY-PROFILES, eduperson-reference, sso-academic-vendors, runbooks, specs ClaudeFlow.
- **Material descartado:** drafts sin OID (18 archetypes + 9 templates + 31 roles + 3 partner-orgs) + resources v1/v2 legacy (Oracle LAMB) + connector custom keycloak-http (archivado, no descartado).
- **Repo padre `SciBack/midpoint`:** carpeta local eliminada (`rm -rf`). Repo GitHub **NO** eliminado (pendiente `gh repo archive`).
- **PROD NO TOCADO.** MidPoint PROD en OOM post-upgrade 4.10.2 (hallazgo crítico #3 audit). Re-checkout y validación en PROD se aplaza hasta recuperación.
- **OIDs estables.** Filename cambió; OID nunca. PROD sigue válido tal cual (lee desde DB, no filesystem).
- Branch `consolidation-2026-05-19`. Por mergear a `main` cuando todo verificado.
- Decisiones tomadas por el ejecutor (no en audit) documentadas en `docs/MIGRATION-DECISIONS-PENDING.md` (10 items).
- Memorias del agente actualizadas con nuevo path.

---

## 1. Movimientos ejecutados (Fase 6.2 del audit)

### 1.1 Schemas
| Origen | Destino |
|---|---|
| `midpoint/schema/schema-object-sciback-person-v1.0.xml` | `canonical/schemas/sciback-person-v1.0.xml` |
| `midpoint/schema/schema-object-upeu-local-v1.0.xml` | `upeu/schemas/upeu-local-v1.0.xml` |
| `midpoint/schema/archive/DEPRECATED-schema-object-upeu-person-v3.1.xml` | `archive/previous/DEPRECATED-schema-object-upeu-person-v3.1.xml` |
| `midpoint/schema/archive/DEPRECATED-extension-upeu-person-v3.1.xsd` | `archive/previous/DEPRECATED-extension-upeu-person-v3.1.xsd` |

### 1.2 Archetypes
| Origen | Destino |
|---|---|
| `midpoint/archetypes/archetype-user-student.xml` | `canonical/archetypes/user/user-student.xml` |
| `midpoint/archetypes/archetype-user-employee-faculty.xml` | `canonical/archetypes/user/user-employee-faculty.xml` |
| `midpoint/archetypes/archetype-user-employee-staff.xml` | `canonical/archetypes/user/user-employee-staff.xml` |
| `midpoint/archetypes/archetype-user-alumni.xml` | `canonical/archetypes/user/user-alumni.xml` |
| `midpoint/archetypes/archetype-org-academic-program.xml` | `canonical/archetypes/org/org-academic-program.xml` |
| `midpoint/archetypes/archetype-person.xml` | `upeu/archetypes/custom/archetype-person.xml` |
| `midpoint/archetypes/archetype-position.xml` | `upeu/archetypes/custom/archetype-position.xml` |
| `midpoint/archetypes/archetype-affiliation-role.xml` | `upeu/archetypes/custom/archetype-affiliation-role.xml` |
| `midpoint/archetypes/aux-affiliation-{alum,faculty,staff,student}.xml` | `upeu/archetypes/auxiliary/` (4 archivos) |

### 1.3 Object templates, policies, function libraries, lookup tables
| Origen | Destino |
|---|---|
| `midpoint/object-templates/UserTemplate-Person-Base.xml` | `canonical/object-templates/UserTemplate-Person-Base.xml` |
| `midpoint/policies/policy-owners-required.xml` | `canonical/policies/policy-owners-required.xml` |
| `midpoint/policies/policy-sod-basic.xml` | `canonical/policies/policy-sod-basic.xml` |
| `midpoint/function-libraries/sb-program-resolver.xml` | `canonical/function-libraries/sb-program-resolver.xml` |
| `midpoint/lookup-tables/program-resolver-lamb.xml` | `upeu/lookup-tables/program-resolver-lamb.xml` |

### 1.4 Resources
| Origen | Destino |
|---|---|
| `midpoint/resources/oracle-lamb/resource-oracle-lamb-trabajadores-v3.xml` | `upeu/resources/oracle-lamb/trabajadores.xml` |
| `midpoint/resources/oracle-lamb/resource-oracle-lamb-estudiantes-v3.xml` | `upeu/resources/oracle-lamb/estudiantes.xml` |
| `midpoint/resources/oracle-lamb/resource-oracle-lamb-egresados-v3.xml` | `upeu/resources/oracle-lamb/egresados.xml` |
| `midpoint/resources/oracle-lamb/resource-oracle-lamb-posiciones-v1.xml` | `upeu/resources/oracle-lamb/posiciones.xml` |
| `midpoint/resources/ldap/resource-ldap-identity-cache-upeu.xml` | `upeu/resources/ldap-identity-cache.xml` |
| `midpoint/resources/entra-id/UPEU-EntraID-Graph.xml` | `upeu/resources/entra-id-graph.xml` |
| `midpoint/resources/koha/resource-koha-ils-upeu.xml` | `upeu/resources/koha-ils.xml` |
| `midpoint/resources/ad/UPEU-AD.xml` | `upeu/resources/ad-upeu.xml` |
| `midpoint/resources/db-sis/SIS-CSV.xml` | `upeu/resources/datasets/SIS-CSV.xml` |
| `midpoint/resources/db-crm/CRM-CSV-skeleton.xml` | `upeu/resources/datasets/CRM-CSV-skeleton.xml` |
| `midpoint/resources/db-rrhh/RRHH-CSV-skeleton.xml` | `upeu/resources/datasets/RRHH-CSV-skeleton.xml` |
| `midpoint/resources/db-sis/resource-academico-legacy.xml` | `archive/previous/resource-academico-legacy.xml` |
| `midpoint/resources/entra-id/resource-msgraph-legacy.xml` | `archive/previous/resource-msgraph-legacy.xml` |
| `midpoint/resources/entra-id/legacy-ms_entraid/README.md` | `archive/previous/legacy-ms_entraid-README.md` |

### 1.5 Roles
| Origen | Destino |
|---|---|
| `midpoint/roles/affiliation/R-Affiliation-*.xml` (6) | `upeu/roles/affiliation/` |
| `midpoint/roles/application/AR-*.xml` (20) | `upeu/roles/application/` |
| `midpoint/roles/business/BR-*.xml` (12) | `upeu/roles/business/` |

### 1.6 Orgs
| Origen | Destino |
|---|---|
| `midpoint/org/000-UPeU-root.xml` | `upeu/orgs/000-UPeU-root.xml` |
| `midpoint/org/010-Facultades.xml` | `upeu/orgs/010-Facultades.xml` |
| `midpoint/org/020-Rectorado.xml` | `upeu/orgs/020-Rectorado.xml` |
| `midpoint/org/030-AreaTecnologia.xml` | `upeu/orgs/030-AreaTecnologia.xml` |
| `midpoint/org/040-Posgrado.xml` | `upeu/orgs/040-Posgrado.xml` |
| `midpoint/org/050-GobiernoAdmin.xml` | `upeu/orgs/050-GobiernoAdmin.xml` |
| `midpoint/org/academic-programs/*.xml` | `upeu/orgs/academic-programs/` |
| `midpoint/org/campus/*.xml` (5) | `upeu/orgs/campus/` |
| `midpoint/org/colegio-union/*.xml` (16) | `upeu/orgs/colegio-union/` |

### 1.7 Services (positions)
13 archivos `midpoint/services/positions/position-*.xml` → `upeu/services/positions/`.

### 1.8 Dashboards, object-collections, auth, system
| Origen | Destino |
|---|---|
| `midpoint/dashboards/dashboard-operacion-iga.xml` | `upeu/dashboards/dashboard-operacion-iga.xml` |
| `midpoint/object-collections/collection-personas-upeu.xml` | `upeu/object-collections/collection-personas-upeu.xml` |
| `midpoint/object-collections/sysconfig-patch-personas-upeu-view.xml` | `upeu/object-collections/sysconfig-patch-personas-upeu-view.xml` |
| `midpoint/auth/oidc-entra-id.xml` | `upeu/auth/oidc-entra-id.xml` |
| `midpoint/system/system-configuration.xml` | `upeu/system/system-configuration.xml` |

### 1.9 Tasks
| Origen | Destino |
|---|---|
| `midpoint/tasks/task-reconcile-oracle-lamb-{trabajadores,estudiantes,egresados}.xml` | `upeu/tasks/recon-oracle-lamb-*.xml` |
| `midpoint/tasks/task-{import,reconcile}-{SIS,AD}-simulation.xml` (3) | `upeu/tasks/simulations/` |
| `midpoint/tasks/pilot-*.xml` (3) | `upeu/tasks/pilots/` |
| `midpoint/simulations/README.md` | `upeu/tasks/simulations/README.md` |

### 1.10 Material rescatado del repo padre `SciBack/midpoint/`
| Origen (repo padre) | Destino |
|---|---|
| `docs/roadmap-iga-2026.md` | `docs/ROADMAP.md` |
| `docs/iga-canonical-analysis-2026-05.md` | `docs/ARCHITECTURE.md` |
| `docs/perfiles-identidad.md` | `docs/IDENTITY-PROFILES.md` |
| `docs/eduperson-attributes-reference.md` | `docs/canonical/eduperson-reference.md` |
| `docs/sso-academico-vendors-mapping.md` | `docs/canonical/sso-academic-vendors.md` |
| `docs/david-urquizo-tasks.md` | `docs/runbooks/tickets-david-urquizo.md` |
| `docs/rudy-oracle-tasks.md` | `docs/runbooks/tickets-rudy.md` |
| `docs/arquitectura.html` | `docs/arquitectura-legacy.html` |
| `docs/PROMPT-onboarding-sso-academico.md` | `docs/runbooks/onboarding-sso-academico.md` |
| `doc/specs/iga-canonical-model-upeu/` | `docs/specs/iga-canonical-model-upeu/` |
| `doc/specs/multi-profile-canonical/` | `docs/specs/multi-profile-canonical/` |
| `doc/specs/midpoint-prod-upeu/` | `docs/specs/midpoint-prod-upeu/` |
| `doc/specs/sciback-iga-blueprint/` | `docs/specs/sciback-iga-blueprint/` |
| `doc/specs/fix-resources-oracle-v2-scripts/` | `archive/specs/fix-resources-oracle-v2-scripts/` (superseded) |
| `doc/catalogo-positions-upeu/` | `docs/catalogo-positions-upeu/` |
| `doc/runbooks/upgrade-midpoint-docker.md` | `docs/runbooks/upgrade-midpoint-docker.md` |
| `context.md` | `docs/CONTEXT-legacy.md` |
| `connector-keycloak-http/` (proyecto Maven) | `archive/connector-keycloak-http/` |
| `audit/resource-trabajadores-v2-{pre,post}-schemaScript-fix-prod-*.xml` | `archive/backups-2026-05/` |
| `audit/resource-trabajadores-v2-post-schema-and-sql-fix-prod-*.xml` | `archive/backups-2026-05/` |
| `audit/schema-v3.0-current.xml` | `archive/backups-2026-05/schema-v3.0-current.xml` |
| `audit/legacy-UserTemplate-UPEU-*.xml` | `archive/backups-2026-05/legacy-UserTemplate-UPEU-*.xml` |
| `audit/2026-05-11/` | `archive/backups-2026-05/2026-05-11/` |
| `ldap/{deploy.sh,docker-compose.yml,env.example,keycloak-user-federation.md,ldifs/}` | `upeu/ldap/` (rescate fuera de audit, ver decisión #11 abajo) |
| `ldap/resource-ldap-upeu.xml`, `ldap/role-ar-ldap-person.xml` | `archive/drafts-from-sciback-midpoint/` (drafts sin OID) |

---

## 2. Material descartado (lista negra §7 del audit)

| Artefacto | Razón |
|---|---|
| 18 archetypes draft (`archetypes/user/01-08-*.xml`, `archetypes/org/01-08-*.xml`, `archetypes/role/01-02-*.xml`) | Drafts sin OID; las versiones vivas con OID PROD ya están en `canonical/archetypes/` |
| 9 object templates draft (`objectTemplates/00-08-*.xml`) | Diseño aspiracional, no aplicados. Principio "1 template/archetype" preservado en ROADMAP |
| 31 roles draft (`roles/application/0X-AR-*.xml`, `roles/business/0X-BR-*.xml`) | Drafts duplicados; vivos con OID en `upeu/roles/` |
| 3 partner-orgs draft (`orgs/04-partner-cgh.xml`, `05-partner-istat.xml`, `06-partner-agtu.xml`) | Drafts sin OID; partners reales aún no creados en PROD |
| 6 resources Oracle LAMB v1+v2 (`resources/oracle-lamb-*.xml`, `*-v2.xml`) | Superseded por v3 |
| 2 resources Keycloak (`resources/keycloak-resource.xml`, `resources/resource-keycloak.xml`) | OID `a3f9c1d2-…` nunca aplicado en PROD; decisión doctrinal 2026-05-11 |
| 6 tasks recon v1/v2 (`tasks/task-recon-{*}-{v2}.xml`) | Superseded por v3 + runs ad-hoc |
| `schema/archive/DEPRECATED-*` (xsd/xml `v3.0`, `lamb-v1`, `SPEC-v3`, `test-user-v3`) | Schemas obsoletos; PROD usa `urn:sciback:midpoint:person` + `urn:upeu:midpoint:local` |
| `schema/backups/v2.2-*`, `v2.3-after-put-*` | Snapshots históricos |
| ~25 audit XMLs forensic no-críticos (`*v2-pre-fix*`, `*current*`, `legacy-deletes/`) | Volumen alto, valor decreciente. Solo 5 críticos preservados en `archive/backups-2026-05/` |
| `archetypes/`, `objectTemplates/`, `orgs/`, `resources/`, `roles/`, `schema/`, `tasks/`, `ldap/`, `audit/`, `connector-keycloak-http/`, `docs/`, `doc/`, `scripts/`, `archive/`, `backups/`, `context.md`, `.impeccable.md`, `vercel.json`, `CLAUDE.md`, `.gitignore`, `.git/` | Repo padre completo eliminado (`rm -rf /Users/alberto/proyectos/upeu/midpoint/`) tras rescatar lo valioso |

---

## 3. Pasos del plan §6 SALTADOS (por OOM en PROD)

| Paso audit | Estado | Cuándo retomar |
|---|---|---|
| §6.3 — descargar 8 archetype-org canónicos faltantes desde REST PROD | SALTADO | Post-OOM |
| §6.6 — diff de OIDs repo vs `m_object` SQL | PARCIAL (validación local OK, diff PROD pendiente) | Post-OOM |
| §6.7 — re-checkout en PROD + smoke tests | SALTADO | Post-OOM |
| §6.8 paso 21 — merge `consolidation-2026-05-19` → `main` via PR | SALTADO | Tras validación PROD |
| §6.8 paso 22 — tag `post-consolidation-2026-05-19` | SALTADO | Tras merge |
| §6.8 paso 23 — `gh repo delete SciBack/midpoint` | **NO** (Alberto: archivar, no eliminar) | Cuando Alberto confirme `gh repo archive` |

---

## 4. Próximos pasos cuando OOM esté resuelto

1. Aumentar heap JVM container `midpoint_server` (4-8 GB en `JAVA_OPTS -Xmx`), runbook en `docs/runbooks/upgrade-midpoint-docker.md` o nuevo `recovery-oom-midpoint.md`.
2. Verificar PROD UP: `curl -u admin:pass …/midpoint/ws/rest/users?paging=maxSize=1` → HTTP 200.
3. `pg_dump` PROD a `archive/backups-2026-05/midpoint-postOOM.dump` (snapshot post-recuperación).
4. En PROD `/home/juansanchez/midPointEcosystem/`:
   ```bash
   git fetch origin && git checkout consolidation-2026-05-19
   git diff main..consolidation-2026-05-19 --stat
   ```
   Esperar solo renames + adds de docs + adds en archive/. Cero cambios de OID.
5. **Smoke tests post-checkout** (criterios §8.7 del audit):
   - `SELECT COUNT(*) FROM m_archetype WHERE lifecyclestate='active'` = 18
   - `SELECT COUNT(*) FROM m_resource WHERE lifecyclestate='active'` = 5
   - `SELECT COUNT(*) FROM m_user` ≥ 35.450
   - Recompute usuario `75824658` OK
   - Sin nuevos ERROR/FATAL/OOM en logs.
6. **Descargar via REST y commitear** los 8 archetype-org canónicos + MOF-* + GOV-* faltantes (decisiones pendientes #4, #5 en `MIGRATION-DECISIONS-PENDING.md`).
7. **Uninstall connector openstandia/connector-keycloak v1.1.7** (huérfano en PROD, decisión #7).
8. **Merge a `main`** via PR + tag `post-consolidation-2026-05-19` + push.
9. **`gh repo archive SciBack/midpoint`** (cuando Alberto confirme).

**NO reaplicar XMLs vía REST PUT.** Los OIDs no cambiaron; PROD lee desde DB, no filesystem. Solo `git checkout` y validación.

---

## 5. Estado del repo GitHub `SciBack/midpoint`

| Item | Estado |
|---|---|
| Carpeta local `/Users/alberto/proyectos/upeu/midpoint/` | **Eliminada** (`rm -rf`) |
| Repo GitHub `SciBack/midpoint` | **PENDIENTE archivar** vía `gh repo archive SciBack/midpoint --yes` |
| Branch local del padre que tenía un commit no pusheado (`Your branch is ahead of 'origin/main' by 1 commit`) | **PERDIDO** (el padre fue eliminado). Pero ese commit local ya tenía toda la info que migramos a `midPointEcosystem` antes de borrar. Verificar si era pérdida crítica (no creemos). |

---

## 6. Estructura final

```
~/proyectos/upeu/midPointEcosystem/        # nueva ubicación (no más anidado en /upeu/midpoint/)
├── canonical/                              # 35 XMLs
├── upeu/                                   # 88 XMLs
├── docs/                                   # ROADMAP + ARCHITECTURE + IDENTITY-PROFILES + runbooks + specs + catalogo-positions
│   ├── AUDIT-CONSOLIDATION-2026-05-19.md
│   ├── MIGRATION-EXECUTED-2026-05-19.md   # ← este archivo
│   ├── MIGRATION-DECISIONS-PENDING.md
│   └── …
├── datasets/                               # CSV/PG demo (sin cambios)
├── archive/                                # previous + backups-2026-05 + specs + connector-keycloak-http + drafts-from-sciback-midpoint
├── midpoint-project.yaml                   # descriptor ninja/Studio (sources actualizados)
├── README.md
└── CLAUDE.md
```

---

## 7. Commits

| Commit | Mensaje |
|---|---|
| `pre-consolidation-2026-05-19` (tag) | Tag de seguridad pre-cambios (pushado a origin) |
| `c3f04a5` (existing) | docs(audit): auditoría de consolidación 2026-05-19 — canonical/upeu |
| `859514a` | refactor(repo): consolidar IGA UPeU en canonical/ + upeu/ (audit 2026-05-19) |
| _este reporte + ldap rescue + decisions-pending_ | Próximo commit |
