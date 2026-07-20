# Medición de alcance real — patrón de 200610808 (Orlando Cortez Bazantes)

2026-07-20. Solo lectura (Oracle LAMB + repo Postgres de MidPoint vía `psql` dentro del
contenedor `midpoint-midpoint_data-1`). Ningún reconcile/import ejecutado.

## Caso base confirmado

- User MidPoint `2dba749b-eb5b-4d1e-82bc-77b7a8b0de0a`, `name=200610808`,
  `fullName=Orlando Gabriel Cortez Bazantes` — **ya existe**.
- Shadow en el resource Oracle LAMB Trabajadores (oid `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21`):
  oid `0c1660ee-b79f-48c3-abc8-5c852ad8226c`, `nameorig=00534601` (su COD_APS),
  `synchronizationSituation=UNMATCHED`, atributos `ESTADO=A`, `SEDE_NOMBRE=Sede Lima`.
- Confirma el diagnóstico previo: contrato activo + sede Lima correctos en Oracle, el shadow
  existe y fue importado, pero la correlación nunca encontró/vinculó al User existente
  (`UNMATCHED`, no `LINKED`). User y shadow, cada uno correcto por separado, nunca se
  conectaron.

## Medición del universo completo (m_shadow del repo MidPoint, resource Trabajadores)

```sql
SELECT synchronizationsituation, attributes->>'29' AS estado, attributes->>'166' AS sede, count(*)
FROM m_shadow
WHERE resourcereftargetoid = '6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21'
  AND exist = true
GROUP BY 1,2,3;
```

Total shadows vivos (no `dead`) en el resource: **7.532**
(`LINKED`=7.386, `UNMATCHED`=92, `UNLINKED`=53, `DISPUTED`=1).

### Mismo patrón exacto que Orlando (UNMATCHED + contrato activo ESTADO='A' + Sede Lima)

**35 personas** (lista completa de shadow OIDs y `COD_APS` en el log de esta sesión,
disponible bajo pedido — no se incluye aquí por longitud).

### Si se incluye también UNLINKED (mismo síntoma práctico: shadow vivo, activo, sin vínculo)

+17 más (`UNLINKED`, `ESTADO=A`, `Sede Lima`) → **52 personas** en total, Lima únicamente.

### Todas las sedes, ESTADO activo, sin vínculo (UNMATCHED + UNLINKED)

**91 personas** (Lima 52, Juliaca 24 [12+12], Tarapoto 13 [4+9], sin sede 2).

## Decisión (per instrucción explícita: <10 = arreglo dirigido autorizado; más = reportar y esperar autorización)

35 (o 52 con UNLINKED) **no es un puñado** — no se ejecutó ningún reconcile ni import, ni
siquiera dirigido a estos 35/52 shadows puntuales. Esto queda pendiente de decisión explícita
de Alberto:

- **Opción A (mínima):** import/reconcile dirigido SOLO a los 35 shadows con patrón exacto
  (UNMATCHED + activo + Lima) — bajo riesgo, no toca los 7.386 ya `LINKED` ni las ~2.800
  activaciones nocturnas normales.
- **Opción B (moderada):** extender a los 52 (incluye UNLINKED Lima).
- **Opción C (amplia):** extender a los 91 (todas las sedes).
- **Opción D:** reconciliation completa del resource (~2.800+ activos) — la que el
  diagnóstico original decía que requería alcance mayor no autorizado. Sigue sin
  autorizarse hoy.

No se ejecutó ninguna opción — queda para que Alberto decida el alcance.
