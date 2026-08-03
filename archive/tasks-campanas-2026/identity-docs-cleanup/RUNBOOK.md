# identity-docs-cleanup — Limpieza identityDocuments duplicados y taxId residuales

**Fecha:** 2026-06-06
**Ejecutado por:** midpoint-expert (Claude Code)
**Estado:** COMPLETADO con 1 irreducible

## Problema

Tras el fix CANON_DOC type-aware (commits `b21d6ec`/`b413e82`/`84841a5`), quedaron dos residuos:

### Residuo 1 — identityDocuments con tipo diferente (duplicados)

7 focos activos tenían 2 containers `identityDocuments`:
- Container stale: escrito por mapping `J-build-identityDocuments-from-lambDocType-taxId` (usa taxId legacy como fallback)
- Container correcto: escrito por mapping `J-build-identityDocuments-from-lambDocType-lambDocNum` (CANON_DOC type-aware)

### Residuo 2 — taxId `:DNI:` con doc_type CE/PASSPORT

25 focos activos tenían `taxId=urn:schac:personalUniqueID:pe:DNI:PE:<num>` pero `identityDocuments.type=CE`.

## Hallazgos de diagnóstico

### Distribución de taxId anómalos (activos)
- Total activos con taxId no-estándar: 939
- Ya corregidos como `:CE:`: 86
- Ya corregidos como `:passport:`: 82
- Con letras iniciales en `:DNI:PE:` (CE/Pasaporte mal tipado en LAMB): 199
- Con más de 8 dígitos en `:DNI:PE:` (CE numérico): 465
- Discrepancia tipo/número pero misma fuente: 754

### identityDocuments duplicados (72 total activos)
- 7 con tipo DIFERENTE (el Residuo 1 real de esta tarea)
- 65 con mismo tipo pero número diferente (discrepancia taxId vs lambDocNum — distinto problema)
- 6 con número exactamente igual (duplicado puro por type=mismo)

### Schema: identityDocuments
- Namespace: `urn:sciback:midpoint:person` (PrismContainer de schema canónico SciBack)
- Path REST correcto: `extension/sb:identityDocuments` con `xmlns:sb="urn:sciback:midpoint:person"`
- El campo NO está en `m_ext_item` (es container PrismContainerValue, no scalar indexado)
- Bloque J2 del template base limpia `taxId` a null cuando `identityDocuments` tiene primary=true

## Acciones ejecutadas

### Paso A — Identificación
Query DB para encontrar focos con `identityDocuments` como array JSON con tipos diferentes.

### Paso B — Verificación
GET REST por OID para confirmar tipo y cid de cada container.

### Paso C — Purga containers stale (7 focos)

PATCH REST con `<modificationType>delete</modificationType><path>extension/sb:identityDocuments</path><value id="CID"/>`:

| OID | código | cid_stale | tipo_stale | tipo_correcto | HTTP |
|---|---|---|---|---|---|
| `2d8e61fc-...` | 201311041 | 27 | DNI | PASSPORT | 204 ✓ |
| `14f5c9e1-...` | 201711967 | 35 | DNI | CE | 204 ✓ (con error 500 en proyección LDAP) |
| `12bce20f-...` | 201712009 | 35 | DNI | PASSPORT | 204 ✓ |
| `2ab68477-...` | 202313459 | 27 | DNI | PASSPORT | 204 ✓ |
| `0ff70566-...` | 202414495 | 101 | DNI | PASSPORT | 204 ✓ |
| `272596f6-...` | 202421264 | 114 | DNI | CE | 204 ✓ (con error LDAP AlreadyExists rename) |
| `2c80c106-...` | 202611565 | 114 | PASSPORT | CE | 204 ✓ |

**7/7 containers stale eliminados.**

Nota: los HTTP 500 en 201711967 y 202421264 fueron errores de proyección secundaria (LDAP), no del cambio focal. El cambio focal fue exitoso (verificado por query DB post-operación).

### Paso D — Limpieza taxId residual (25 focos)

El recompute no-op por `telephoneNumber` NO disparó el bloque J2 (MidPoint no re-evalúa mappings cuyo source no cambió).
Solución: PATCH directo `<modificationType>replace</modificationType><path>extension/sb:taxId</path>` sin value = null.

- 24/25 limpiados con HTTP 204
- 1 irreducible: `d76b35bf` (201910528, CE num=075804938) — HTTP 409 por dual-shadow LDAP

## Resultados (gates verificados)

| Gate | ANTES | DESPUÉS | Estado |
|---|---|---|---|
| Duplicados tipo diferente (activos) | 7 | 0 | VERDE |
| taxId DNI con doc_type CE/PASSPORT | 25 | 1 | 1 irreducible |
| m_user activos | 54,499 | 54,499 | INVARIANTE |
| Heap MidPoint | 52.4% | 52.5% | OK |

## Irreducible

**Foco:** `d76b35bf-61cd-40c1-b32c-11eed35c1a9c` (código 201910528)
- `taxId`: `urn:schac:personalUniqueID:pe:DNI:PE:75804938` (stale)
- `identityDocuments.type`: CE, number=075804938 (correcto)
- **Causa:** dual-shadow LDAP (uid=201910528 y uid=75804938 coexisten) → HTTP 409 en cualquier cambio focal que toque proyección LDAP
- **Riesgo:** bajo — taxId es deprecated, identityDocuments es la fuente de verdad
- **Resolución:** sub-workstream dedup LDAP (merge shadows o eliminar shadow huérfano uid=75804938)

## Lecciones aprendidas

1. **Path namespace correcto:** `extension/sb:identityDocuments` con `xmlns:sb="urn:sciback:midpoint:person"`, NO `c:identityDocuments` ni `c:extension/c:identityDocuments`.
2. **recompute no-op (telephoneNumber)** NO dispara J2 si `identityDocuments` no cambió. Para limpiar taxId: PATCH replace directo.
3. **HTTP 500/240 en PATCH** puede indicar error de proyección con cambio focal exitoso. Verificar siempre con query DB.
4. **65 duplicados mismo-tipo-número-distinto** quedan pendientes (discrepancia taxId legacy vs lambDocNum) — diferente problema, requiere análisis separado.
5. **199 focos** con `:DNI:PE:letra` son error de datos en LAMB (lambDocType=1/DNI pero número alfanumérico) — requieren corrección upstream o fix en CANON_DOC para inferir tipo desde formato del número.
