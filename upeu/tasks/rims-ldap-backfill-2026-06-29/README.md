# RIMS←IGA — Backfill LDAP identity cache (2026-06-29)

Materializa masivamente a LDAP (`ldapidentitycacheupeu`, HA .168/.169) los outbounds
strong del contrato RIMS que ya viven en `ldap-identity-cache.xml` pero no se
empujaron tras editar el resource el 29-jun:

- `schacPersonalUniqueID` (DNI ← identityDocuments)
- `eduPersonOrgUnitDN` (afiliación → programa)
- `eduPersonScopedAffiliation`
- `schacGender`
- (`eduPersonOrcid` / `isni` quedan ~0: la fuente Oracle aún no los provee — fuera de alcance)

## Mecanismo
Recompute **focus-side** (no reconcile on-resource), idempotente, blueprint GAP-1.
Koha degradado a `criticality=partial` (resource `koha-ils.xml`) para que
`AlreadyExistsException` por shadows huérfanos NO aborte el clockwork → LDAP sí materializa.

## Escalonamiento (suspended; resume manual por lote, monitoreando heap/disco)
| Orden | Task | Archetype | OID task | ~Activos |
|---|---|---|---|---|
| 1 (canary) | staff | `6460facf-…aa1a6c46` | `c804fbbf-f44a-8fff-a596-da00ee7f2ffb` | 1,682 |
| 2 | faculty | `c93083ca-…d53b97c9556e` | `1dd379e3-6285-039a-7870-22a3e62d5b0f` | 1,781 |
| 3 | student | `3037fbd2-…83fab5e686aa` | `a1fbccbc-310f-3944-f507-b850f68261b0` | 24,165 |
| 4 | alumni | `87552943-…74b7d3ba93e4` | `aef3f635-41e1-0915-6d42-dd2a3342a7f2` | 26,578 |

`workerThreads=1`. PROD post-OOM: DETENER si heap >80% sostenido / disco crítico / GC thrashing.
