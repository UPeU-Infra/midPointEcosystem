# Barrido 970 focos DUAL (Trabajadores+Estudiantes) — post fix inbound newline — 2026-06-17

Cierre operativo del fix del inbound `num-documento-to-lambDocNum` del resource
Oracle LAMB Trabajadores v3 (OID `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21`,
tag `fix-trabajadores-inbound-newline-2026-06-17`).

## Problema
El inbound colapsaba newlines en el script de mapping → compile error →
abortaba el recompute (PROJECTOR) de los focos que pasan por el resource
Trabajadores. Reimport del XML limpio del repo → inbound sano. Prueba unitaria:
Wendy Pinedo `005def6b-3f46-4f28-94da-99df8247c565` → EXECUTION SUCCESS.

## Scope (reproducible)
Focos **activos** con shadow/projection en AMBOS resources Oracle
(Trabajadores v3 + Estudiantes v3):
```sql
select r.owneroid from m_ref_projection r join m_shadow s on s.oid=r.targetoid
  where s.resourcereftargetoid='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21'  -- Trabajadores
intersect
select r.owneroid from m_ref_projection r join m_shadow s on s.oid=r.targetoid
  where s.resourcereftargetoid='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22'  -- Estudiantes
-- join m_user where lifecyclestate='active'
```
→ **970 focos** (`scope-dual970-active.tsv`: oid · name(código) · lifecycle · [V|-]livedual).
De ellos **518** con doble afiliación VIVA (`liveAffiliationWorker` ext#216 +
`liveAffiliationStudent` ext#217) — el subconjunto que ya barrió el
`dual-dirty-sweep` del 2026-06-15. Los ~452 restantes tienen shadow dual pero
sólo una afiliación viva (egresado que trabaja, etc.); igual pasan por el
inbound Trabajadores al recomputar.

## Driver
`driver-recompute-dual970.sh <ADMIN_PASS> [MAX]`
- PATCH `?options=reconcile` no-op en `description` (`dual970-sweep-<ts>`).
  Idempotente, storm-free; fuerza clockwork completo (PROJECTOR pasa por el
  inbound ya sano).
- Serializado, resumible vía `/tmp/dual970_done.txt`, log `/tmp/dual970_progress.log`.
- Gate heap: `docker stats midpoint_server` MemPerc ≥85% → pausa 30s; ≥95% → ABORT.
- `MAX` opcional limita a los primeros N pendientes (canary).
- 200/204/250 = OK. 5xx `without any attributes`/`partial` = OK benigno.
  Cuerpo con `koha`/`timed out`/`read timed` = ruido transitorio Koha
  (bot-flood .135) → NO marca done, reintentable. Resto 4xx/5xx = FAIL real.

## CRITICO anti-proyección CRIS
Resource CRIS (`3f8b2d61-7c94-4a05-9e3b-6d1f8a2c5e70`) DEBE permanecer
`lifecycleState=proposed` durante TODO el barrido. Verificado antes y después.

## Baseline invariantes (pre, 2026-06-17)
- m_user_total = 62,465 · m_user_active = 54,237
- focos dual (projection,active) = 970 · live-dual = 518
- koha_bul borrowers = 19,876 · dup_cardnumber = 0 (SAGRADO) · sort2 = 9,661
- resource CRIS = proposed · resource Trabajadores = active (inbound sano)
