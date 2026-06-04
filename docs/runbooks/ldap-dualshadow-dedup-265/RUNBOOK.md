# Saneamiento dual-shadow LDAP — 265 focos (dedup uid=DNI vs uid=código)

Fecha: 2026-06-04
Resource LDAP (Identity Cache): `7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f` (`upeu/resources/ldap-identity-cache.xml`), base `ou=people,dc=upeu,dc=edu,dc=pe`, DN = `uid=<focus/name>,...`.

## Estado: PARADO tras canary 2/2 PASS — BLOQUEO por concurrencia (NO ejecutar masivo todavía)

### Resumen ejecutivo
- Diagnóstico confirmado: **265 focos** con dual-shadow LDAP, patrón **uniforme 0 ambiguos**.
- Backups OBLIGATORIOS hechos y verificados (>0).
- **Re-canary 2/2 PASS** en esta sesión (procedimiento end-to-end validado).
- **Masivo de 265 NO ejecutado**: un `Import from resource Oracle LAMB Estudiantes v3` está **RUNNING** y **regenera dual-shadows 1:1** en tiempo real → el universo nunca converge a ~0 mientras ese import corra. Además el usuario instruyó NO involucrar el recon/import Estudiantes (sub-workstream aparte).

## Diagnóstico (verificado en PROD)
| Verificación | Resultado |
|---|---|
| Focos con >1 shadow LDAP (m_ref_projection) | **265** |
| keeper: `uid == focus/name` (código) | 265/265 |
| loser: `uid` = DNI 8 dígitos, ≠ name | 265/265 |
| ambiguos / otro mismatch | 0 |
| overlap keeper vs loser | 0 |
| name del foco = DNI (que rompería "conservar código") | **0** (257 código `20…` + 8 otros códigos numéricos no-DNI) |
| keepers presentes en LDAP físico | 265/265 |
| losers presentes en LDAP físico | 265/265 |
| loser shadow flags | `lifecycleState=NULL, dead=NULL, exist=t` (MidPoint los cree vivos → causa `already exists in lens context`) |

**OJO — no borrar por patrón ciego:** LDAP tiene **2241 entradas `uid=DNI8`**; solo **265** son losers de dual-shadow (las que tienen keeper-código en el MISMO foco). Las otras ~1976 son focos cuyo único shadow LDAP es legítimamente el DNI (workers). El masivo SOLO debe tocar las 265 del dataset, NUNCA "todos los uid=DNI8".

Dataset completo (foco OID | name/código | keeper shadow OID | loser shadow OID | DNI):
`dualshadow_265_dataset_2026-06-04.csv` (gitignored — contiene DNI/PII; vive solo local + PROD `/tmp`).

## Backups (PROD)
- `pg_dump` m_shadow + m_ref_projection: `/home/juansanchez/backups/dualshadow-265/mp_shadows_20260604_113146.dump` (8.0 MB).
- LDIF de las 265 entradas loser `uid=DNI`: `/home/juansanchez/backups/losers_20260604_113146.ldif` (265/265 entradas, 256 KB).

## Procedimiento por foco (validado, serializado)
1. `DELETE /shadows/<loser_sh>?options=raw` → HTTP 204 (el delete normal da 409; raw lo evita).
2. `ldapdelete uid=<DNI>,ou=people,...` dentro del contenedor `openldap` (host `ldap-upeu` 192.168.15.168; `ldapsearch/ldapdelete` NO están en el host, solo dentro del contenedor `osixia/openldap`). Conserva `uid=<código>`.
3. `PATCH /users/<foid>?options=reconcile` con delta no-op (`replace c:telephoneNumber` sin valor) → reevalúa clockwork, consolida en el shadow keeper.

Resultado esperado por foco: queda **1 solo shadow LDAP = `uid=<código>`**, loser ausente. `partial_error` en el PATCH es **ruido esperado** (Entra ID `CreateCapabilityType is missing`, resource `2f11c057...` inbound-only/proposed); NO hay error LDAP ni Koha.

## Canary 2/2 PASS (esta sesión)
| Caso | foco | código (keeper) | DNI (loser) | DELETE shadow | ldapdelete | reconcile | shadows LDAP después |
|---|---|---|---|---|---|---|---|
| 1 | a04a5483… | 200010013 | 42653118 | 204 | OK | partial_error (solo Entra) | 1 (uid=código) ✓ |
| 2 | 7fd2cbd3… | 200010092 | 41767058 | 204 | OK | partial_error (solo Entra) | 1 (uid=código) ✓ |

- Keeper LDAP (uid=código) intacto en ambos; loser LDAP confirmado `No such object`.
- **Koha intacto:** ambos borrowers conservan `cardnumber=DNI` (94206/94218, BUL) — el mapping `cardnumber-outbound` es **weak** (source `$focus/name`=código), así que NO sobreescribe cardnumber existente y NO crea duplicado (los códigos 200010013/200010092 no existen como cardnumber). dup_cardnumbers = 0.

## BLOQUEO — por qué NO se corrió el masivo
`Import from resource Oracle LAMB Estudiantes v3` quedó **RUNNING desde 2026-06-04 16:20** (no lanzado en esta sesión). Evidencia de que regenera el dual:
- Tras sanear 2 canary, el conteo dual global se mantuvo en **265** (no bajó a 263).
- Comparación de conjuntos: 2 focos de mi CSV salieron del universo dual (los saneados) y **2 focos NUEVOS** entraron (no estaban en el CSV). Neto 1:1.
- Mis 2 canary siguen sanos (no revirtieron); son focos distintos los que aparecen.

Conclusión: con el import Estudiantes activo el universo dual-shadow es **móvil**; el masivo de 265 no converge a ~0 y mezcla atribución con un sub-workstream que el usuario pidió no tocar.

## Invariante Koha (siempre verde durante la sesión)
- Baseline: 14267 borrowers, **0 cardnumbers duplicados**.
- Cierre sesión: 14292 borrowers (+25 por el import Estudiantes activo, cardnumber=código, student — NO de este dedup), **0 cardnumbers duplicados**.
- Todos los toques de este dedup fueron updates in-place / no-op; 0 borrowers creados por el dedup.

## Relación con Change 3 (home library)
Change 3 dejó **30 focos LIMA bloqueados** por `Projection ACCOUNT already exists in lens context` (dual-shadow LDAP). Esos 30 son subconjunto de estos 265. Al sanear el dual-shadow flipean solos a BUL en el reconcile (ya tienen campusStudent/Worker LIMA materializado). **Aún NO desbloqueados** porque el masivo está parado.

## Recomendación / próximos pasos (decisión usuario)
1. **Coordinar ventana sin import/recon Estudiantes activo** (suspenderlo es decisión del usuario — instrucción explícita de no tocar ese sub-workstream). Con el import detenido el universo dual queda estable.
2. Recién entonces correr el masivo serializado (scripts del procedimiento por foco) sobre el dataset de 265 → esperado dual-shadow 265→~0.
3. Limpieza Keycloak de ~181 cuentas federadas stale por DNI (READ_ONLY, 0 sesiones): **NO tocada** esta sesión (depende del masivo LDAP previo; se hace después de que LDAP quede con un solo uid=código por foco, porque Keycloak federa desde LDAP).
4. Sub-workstream recon Estudiantes (Tito y similares: pendientes de materialización de `campusStudent` LIMA) — NO forzar aquí; es decisión aparte del usuario (los ~13k addFocus).

## Pendientes de materialización de campus (sub-workstream, NO forzar)
Los focos cuyo `campusStudent`/`campusWorker` LIMA aún no está materializado dependen del recon Estudiantes (Change 1 vigencia DENSE_RANK LAST). No se fuerzan en este dedup. Tito (43508613) es ejemplo de este grupo.
