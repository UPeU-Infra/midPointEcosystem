# MARC 526 de Koha → P-code: medido y detenido — decision de BIBLIOTECA, no de tesauro

**Fecha:** 2026-08-10 · **Estado:** no ejecutado, a la espera de una decision sobre el catalogo historico

> **Correccion (misma fecha):** una version previa de este documento atribuia el bloqueo a un
> "gap del tesauro". **Es incorrecto.** VocBench esta completo respecto de su alcance —los 183
> programas vigentes del A4/A8 2026-1— y no hay trabajo pendiente ahi. Lo que ocurre es que la
> catalogacion usa codigos INEI de programas que YA NO EXISTEN en el A4/A8 vigente.

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

## La causa: 11 códigos de programas que ya no existen

De los 101 códigos INEI usados en la catalogación, **85 mapean** y **16 no**:

De los 16 sin mapeo directo, **5 se resuelven cruzando por el nombre** que Koha guarda en
`authorised_values` contra las etiquetas del tesauro — entre ellos `73210077` → **P25**
(Ingeniería Civil), que se valida contra estudiantes reales que ya publican P25.

Los **11 restantes son denominaciones que no estan en el A4/A8 2026-1**: por ejemplo
*Maestría en Gobernabilidad y Gestión Pública*, *Educación Especialidad Ambiental, Biología y
Química* o *Tecnología Médica en Terapia Física y Rehabilitación* (con dos codigos INEI
distintos para lo mismo). Son programas extintos o denominaciones antiguas: **no tienen —ni
deben tener— un P-code vigente**.

**Añadir los 5 resueltos por nombre no mejora nada**: 44,6 % antes y 44,6 % despues. Los 11
irresolubles estan repartidos por practicamente todos los registros mixtos.

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

**La decision es de biblioteca, no de tesauro:** que hacer con los titulos catalogados bajo
programas que ya no se ofertan. Tres opciones:

- **(a) Dejarlos con su INEI historico.** El 526 quedaria mixto a proposito: P-code para los
  programas vigentes, INEI para los extintos. Requiere asumir un campo con dos vocabularios.
- **(b) Mapearlos al programa sucesor** (p. ej. las dos Tecnologia Medica → P154/P155). Exige
  que alguien de biblioteca declare cada equivalencia; no es deducible del A4/A8.
- **(c) Retirarles el 526** a los registros de programas extintos.

Y, en paralelo, una mejora que si corresponde al tesauro y es opcional: extender `KohaCode` a
los 46 conceptos multi-modalidad (hoy solo 7 lo tienen), para que la eleccion del representante
la haga el tesauro y no una heuristica del script.

Solo con (a), (b) o (c) decidido se migra el 526 **de una sola vez**, con backup de
`biblio_metadata` y reindexado posterior.

## Verificación previa a cualquier migración

Todo valor emitido debe existir en el A4/A8 2026-1 (183 P-codes). Si aparece uno que no esté,
el mapeo está mal: **no inventarle equivalencia**.
