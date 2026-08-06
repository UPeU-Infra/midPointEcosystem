# Preparado, NO desplegado — repoblar `academicProgramSuneduCode` por ID

**Fecha:** 2026-08-06 · **Estado: LISTO PARA APLICAR, sin desplegar**

## Qué resuelve

Al retirar `'P'||CODIGO_SUNEDU` del searchScript (resource **v185**, commit `db859ce`),
**10.448 estudiantes quedan sin código SUNEDU**. Este paquete repuebla el código desde el
identificador inmutable, usando el mismo puente que ya alimenta `academicProgramUri`.

## Cobertura medida contra Oracle (25.765 estudiantes con matrícula vigente)

| Momento | Cobertura |
|---|---|
| Antes del fix | 100 % — pero **40,6 % falso** |
| Hoy (v185) | **59,4 %** |
| Con este paquete | **72,9 %** — recupera **3.478** |

Los **6.970** que seguirían sin código son niveles **no licenciados** (Idiomas, CEPRE,
Educación Contínua, TESIS, Conservatorio): **no deben tener P-code**. 72,9 % es la cobertura
correcta, no un objetivo a superar.

## Los dos artefactos

| Archivo | Qué es |
|---|---|
| `upeu/lookup-tables/program-sunedu-byid.xml` | LookupTable generada desde VocBench: **177 filas, 0 colisiones**, `id → P-code` resolviendo `dct:isReplacedBy` |
| `docs/pendientes/PATCH-inbound-suneduCode-byid.xml` | PATCH que añade el inbound en `PROGRAM_CODES` |

## Procedimiento (cuando se decida aplicar)

1. **Leer primero el diff de la recon** del 7-ago 11:20 UTC — hay dos cambios ya en vuelo
   (URI por ID y retirada del código fabricado). No añadir un tercero a ciegas.
2. Desplegar la LookupTable: `POST /ws/rest/lookupTables` (o `PUT` sobre su OID — en
   LookupTables el PUT es seguro; la regla del *nunca PUT* es solo para `ResourceType`).
   Verificar **en Postgres**: `SELECT count(*) FROM m_lookup_table_row WHERE owneroid='9d4e7f21-…'`
   → debe dar **177** (el REST NO serializa las filas: devuelve 0 y parece vacía).
3. **Verificar que los ids del container siguen vigentes**: `objectType[3297]/attribute[3323]`.
4. Aplicar el PATCH del inbound (`PATCH`, nunca `PUT`) y comprobar `version`, `<schema>` con sus
   25 `xsd:element`, `connectorRef` y `capabilities`.
5. Simular en `preview` antes de que corra ninguna reconciliación real.

## Advertencias incorporadas

- 🔴 `PROGRAM_CODES` es **multivalor** → el mapping usa `<script>`, **nunca `<function>`**
  (una `<function>` recibe el conjunto y falla: regresión del 5-ago).
- ⚠️ `academicProgramSuneduCode` es **single-value**. El script devuelve el **menor P-code**
  para ser determinista. **Pendiente de diseño**: pasarlo a multivalor —como ya es
  `academicProgramUri`— o documentar que refleja la matrícula principal.
- Consumidor a vigilar: **Koha**, que lee el código vía `LT-Pcode-INEI`.
