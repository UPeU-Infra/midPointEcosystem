# Runbook — Saneamiento del Org tree (Fix 1 + Fix 2)

Fecha: 2026-05-29
Ejecutor: midpoint-expert
Servidor: PROD `192.168.15.166` (MidPoint 4.10.2)
Resource: `oracle-lamb/org.xml` (OID `9e2f4c7a-1b5d-4e8c-a3f6-c2d9e4b7a1f3`)

## Contexto

El sync histórico de `oracle-lamb/org` (filtro v1.0) trajo las 8,026 áreas
de `ELISEO.VW_AREA` como `OrgType` `AREA-{ID_AREA}`. El filtro v1.1
(`ESTADO='1' AND (TIENEHIJO='1' OR tiene_trabajadores_activos)`) reduce el
scope a 370 áreas reales (sedes 1/2/3/4). Las ~7,656 restantes eran residuo
denominacional (sedes 5/6, misiones, iglesias) y áreas vacías.

## Fix 1 — Presentación (displayName legible)

Decisión canónica (skill midpoint-best-practices §5.2): **mantener `name`
estable e identifier-based; mostrar `displayName` en la vista.** El org tree
de MidPoint 4.10 ya renderiza el nodo con `displayName` cuando está presente
(`getDisplayNameOrName()`).

- Cobertura `displayName`: **100%** en las 370 orgs in-scope y en las 122
  canónicas (CU/EP/DIR/...). 0 nulls (excepto raíces de sistema
  World/Projects/Teams).
- Mapping inbound `nombre-to-displayName` (`ri:NOMBRE → displayName`) ya
  funciona — **sin cambios**.
- El ruido de la UI (`AREA-NN` ilegible + displayNames denominacionales tipo
  "119968 - Ilo Ilo") se resolvió al purgar el residuo (Fix 2). No se tocó
  `systemConfiguration` para evitar romper las 50+ vistas default en PROD en
  recuperación.

## Fix 2 — Purga de orgs residuales (DESTRUCTIVO)

### Determinación de scope (autoritativa)
Una reconciliación previa (2026-05-28) ya dejó la huella en `m_shadow`:
- 370 shadows `dead=NULL, exist=true` → **in-scope** (filtro v1.1 los devuelve).
- 7,656 shadows `dead=true, exist=false` → **out-of-scope** (residuo).

Cruce scope × membresía (vía `m_ref_projection` + `m_ref_object_parent_org`):

| Scope | Membresía | Orgs | Acción |
|---|---|---|---|
| in-scope (live shadow) | vacía (nodo estructural) | 19 | KEEP |
| in-scope (live shadow) | con miembros | 351 | KEEP |
| out-of-scope (dead) | vacía | 6,985 | PURGE |
| out-of-scope (dead) | "con miembros" (solo orgs hijas muertas) | 671 | PURGE |

Seguridad confirmada antes de borrar:
- Los "miembros" de las out-of-scope eran **6,969 refs de otras orgs**
  (jerarquía muerta), NO usuarios.
- Solo **7 assignments de usuarios** apuntaban a out-of-scope, todos de
  usuarios `lifecycleState=archived` (AREA-8118, AREA-4546).
- **0 usuarios activos** afectados.

### Backup
- Git tag: `backup-pre-org-purge-2026-05-29`
- `pg_dump` en PROD: `/tmp/backup_orgs_20260529_0650.sql` (885 MB; m_org,
  m_ref_object_parent_org, m_assignment, m_shadow, m_ref_projection).

### Ejecución
1. Delete de 7,656 OrgType vía REST `DELETE /orgs/{oid}?options=raw`
   (mantiene integridad de repositorio; closure se refresca aparte).
   Resultado: **7,655 ok, 1 fail (404 — OID del test single-delete previo).**
2. Cleanup de 7,656 shadows huérfanos vía REST `DELETE /shadows/{oid}?options=raw`
   (el raw org-delete no cascada shadows). Resultado: **7,656 ok, 0 fail.**
3. `CALL m_refresh_org_closure(true)` (materialized view).

### Estado final
- Orgs totales: **492** (370 AREA in-scope + 122 canónicas + raíces).
- AREA-* supervivientes: **370** (rango esperado ~293-400 ✓).
- Org shadows: **370** (1:1 con orgs supervivientes).
- displayName null (no-sistema): **0**.
- Assignments user→AREA: **8,701** intactos (workers Bloque E preservados).

### Pendiente (NO ejecutado aquí — paso separado)
- **69 orgs supervivientes con parentOrgRef colgante** (su padre era
  out-of-scope y fue borrado). Esperado: el filtro v1.1 conserva áreas hoja
  con trabajadores aunque su padre no califique.
- Cierra solo con **recompute de OrgType**: el inbound `id-parent-to-parentOrg`
  con `createOnDemand=false` descarta el assignment colgante; luego
  `m_refresh_org_closure(true)` limpia los 148 ancestros fantasma de la closure.
- Benigno mientras tanto: el árbol renderiza; los ancestros fantasma no
  resuelven a nodo.
