# MARC 526 de Koha → P-code: medido y BLOQUEADO por un gap del tesauro

**Fecha:** 2026-08-10 · **Estado:** no ejecutado, a la espera de VocBench

## Qué es el campo 526

`526$a` (*Study Program Information Note*) marca **a qué programas sirve cada título** del
catálogo. **34.537 registros** lo llevan, y no son tesis: **29.866 son libros** y solo 990 son
`TESIS`. Por eso la excepción del ADR-005 —«el INEI queda para el repositorio de tesis»— **no
los cubre**: por la regla general les tocaría el P-code.

## Por qué no se migró

| | registros | % |
|---|---|---|
| Todos sus códigos mapean a P-code | 15.397 | 44,6 % |
| **Mixtos** (unos sí, otros no) | **19.138** | **55,4 %** |
| Ninguno mapea | 2 | 0,0 % |

Migrar ahora dejaría al **55 %** de los registros con **P-codes e INEI mezclados en el mismo
campo**. El estado actual es homogéneo (todo INEI); el resultado sería peor que no tocar nada.

## La causa: 16 códigos que el tesauro no puede resolver

De los 101 códigos INEI usados en la catalogación, **85 mapean** y **16 no**:

- **14 NO EXISTEN en el tesauro** — entre ellos `73210077` (Ingeniería Civil, 8.087 registros)
  y `12102051` (13.868). No es que falte el P-code: **el concepto no está**.
- **2 están deprecados con `dct:isReplacedBy`** (`41600562`, `91301068`): resolubles siguiendo
  el enlace, como ya hace `generar-lookup-programas.py`.

Lista completa con volumen y denominación: [`gap-tesauro-marc526-2026-08-10.csv`](gap-tesauro-marc526-2026-08-10.csv).

**El vocabulario INEI de la biblioteca y el del tesauro no están alineados.** Hay además
conceptos vigentes en el tesauro (Enfermería, Psicología) sin ningún INEI de 8 dígitos.

## La segunda cuestión: la ambigüedad por modalidad

46 de los 85 códigos mapeables llevan **varios** P-codes (`11102086` → P19 / P98 / P128): son
las modalidades, que ante SUNEDU son programas distintos. Un libro no tiene modalidad.

El tesauro define un **`KohaCode`** justo para esto —el P-code representante del concepto— pero
**solo 7 de esos 46 lo tienen**. Para el resto habría que elegir por heurística (el de numeración
menor, que coincide con `KohaCode` en 17/17 de los casos donde ambos existen). **Es una regla
razonable, pero no una decisión del tesauro**, y por eso no se aplicó sola.

## Qué desbloquea esto

1. **En VocBench**: anclar los 14 INEI ausentes a su concepto, o declarar que son programas
   extintos y decidir qué código llevan en el catálogo histórico.
2. **En VocBench**: extender `KohaCode` a los 46 conceptos multi-modalidad, para que la elección
   la haga el tesauro y no un script.
3. Solo entonces migrar el 526, **de una sola vez**, con backup de `biblio_metadata` y
   reindexado posterior.

## Verificación previa a cualquier migración

Todo valor emitido debe existir en el A4/A8 2026-1 (183 P-codes). Si aparece uno que no esté,
el mapeo está mal: **no inventarle equivalencia**.
