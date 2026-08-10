# MARC 526 de Koha → P-code: medido y detenido — decision de BIBLIOTECA, no de tesauro

**Fecha:** 2026-08-10 · **Estado:** ✅ EJECUTADO — decision de Alberto: dejar los INEI historicos y migrar los vigentes

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


---

## ✅ EJECUTADO (2026-08-10)

**Decision de Alberto:** dejar los INEI historicos y migrar solo los vigentes. El campo 526
queda **mixto a proposito**: P-code donde hay programa vigente, INEI donde el programa ya no
se oferta.

### Resultado

| | |
|---|---|
| Registros modificados | **34.531** de 34.537 |
| Valores 526 migrados | **748.806** |
| Codigos distintos ahora | 103 — 92 P-code + 11 INEI historicos |
| INEI que aun eran migrables | **0** |
| P-codes fuera del A4/A8 | 1 (`P203`, **preexistente**: pendiente de licencia SUNEDU) |
| Registros con valores repetidos | **0** |

Los 11 INEI que se quedan, con su denominacion oficial del Clasificador Nacional 2022:
`12102051` `12102128` `31302383` `41101897` `41310737` `41600562` `41709097` `41910511`
`61110044` `91605478` `91605517`.

### Que desbloqueo la migracion

El **Clasificador Nacional de Programas 2022 del INEI**
(`~/Downloads/clasificador_de_carreras_inei`) confirmo que **los 16 codigos sin mapeo son
validos**: el codigo de 8 digitos es *campo detallado (3) + programa (5)*. No eran basura de
catalogacion. De ellos, 5 se resolvieron cruzando por denominacion contra el tesauro
(`73210077` → **P25** Ingenieria Civil, validado contra estudiantes reales) y 11 corresponden a
programas que ya no figuran en el A4/A8 2026-1.

### Deduplicacion

Dos INEI distintos podian mapear al mismo P-code (`P29` ← 41400200 y 41600207; `P80` ←
31302652 y 31302933): son modalidades del mismo programa. Sin deduplicar, **12.232 registros**
habrian quedado con el mismo P-code repetido. El script elimina el `datafield` 526 duplicado.

### authorised_values

`526$a` **usa la lista `Bsort2`** (verificado en `marc_subfield_structure`). Se repoblo con los
183 P-codes del A4/A8 **y** se anadieron los 11 INEI historicos y `P203`, etiquetados
`[histórico INEI]` / `[pendiente licencia SUNEDU]`. Total: **195**.

### Trampas del script (`upeu/scripts/migrar-marc526-a-pcode.py`)

- **Nunca hacer un REPLACE global del numero**: solo dentro de `<datafield tag="526">`, o se
  pisan ISBN, fechas y codigos de otros esquemas.
- **`koha-mysql --raw` parte el marcxml**: lleva saltos de linea reales y el parseo por lineas
  falla en silencio (dry-run daba 0 cambios). Sin `--raw`, mysql escapa `\n`/`\t`/`\\` y hay
  que desescapar al leer.
- **Los UPDATE van por STDIN**: un lote con marcxml completo desborda `ARG_MAX`
  (*Argument list too long*).

### Backup

`biblio_metadata` completa en el servidor: `/tmp/biblio_metadata-antes-526.sql.gz` (28 MB).


---

## Segunda pasada: PURGA de los INEI historicos (2026-08-10)

**Decision de Alberto:** *«no quiero ni tener rastro de codigos INEI, pues para mis reportes me
va a estar molestando»*. Se elimina el rastro **sin inventar equivalencias**.

### Por que no se les asigno un P-code

Se probo el mapeo automatico de los 11 historicos contra el A4/A8 y **no es viable**:

| Historico | Propuesta automatica | |
|---|---|---|
| `41310737` **Maestria** en Administracion de Negocios | `P01` **Bachiller** en Administracion | cambia el nivel |
| `61110044` **Maestria** en Ingenieria de Sistemas | `P27` **Bachiller** en Ingenieria de Sistemas | cambia el nivel |
| `31302383` Ciencias de la **Familia** | `P07` Ciencias de la **Comunicacion** | sin relacion |
| `41910511` Emprendimiento e Innovacion | `SEG71` 2da Esp. **Enfermeria** | sin relacion |

Solo 3 de 11 eran defendibles. Y varios programas **no tienen sucesor**: *Maestria en
Gobernabilidad y Gestion Publica* y *Maestria en Ciencias de la Familia* no existen en el A4/A8
bajo ninguna forma. Asignarles un P-code habria metido afirmaciones falsas en entre 1.400 y
13.800 registros cada una.

### Lo ejecutado

Se elimina el **datafield 526 completo** cuando todos sus `$a` son codigos historicos.
Medido antes: **ningun registro se queda sin 526** (los afectados conservan entre 8 y 61
P-codes vigentes).

| | |
|---|---|
| Registros modificados | **19.137** |
| Datafields 526 eliminados | **94.870** |
| Codigos INEI restantes en el catalogo | **0** |
| Registros sin ningun 526 | **0** |
| Codigos distintos ahora | 92, todos P-code |
| Fuera del A4/A8 | 1 (`P203`, preexistente: pendiente de licencia) |

`authorised_values` de Bsort2 queda en **184** entradas (183 del A4/A8 + `P203`), sin ningun
codigo INEI.

**Backup previo a esta pasada:** `/tmp/biblio_metadata-antes-purga-inei.sql.gz` en el servidor.
Script: `upeu/scripts/purgar-marc526-inei-historicos.py`.

### Lo que se pierde, dicho explicitamente

Los registros ya no declaran haber servido a esos 11 programas retirados. Es informacion
historica de catalogacion que **no se puede reconstruir** desde el 526 (si desde el backup).
Se acepto a cambio de tener reportes limpios.
