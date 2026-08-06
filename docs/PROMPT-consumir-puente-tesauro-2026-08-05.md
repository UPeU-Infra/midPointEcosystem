# Prompt para la sesión del IGA — consumir el puente del tesauro

> Escrito desde VocBench el 5-ago-2026, en respuesta al hallazgo
> `HALLAZGO-programas-academicos-vocbench-2026-08-05.md`. Las cuatro rondas que esa sesión
> pidió están **ejecutadas y verificadas**; esto es lo que queda, y ya no tiene bloqueos.

---

## Lo que cambió en VocBench

Las cuatro rondas se ejecutaron con correcciones, todas verificadas contra Oracle y el
Formato A4 antes de escribir nada:

| Ronda | Pedido | Ejecutado |
|---|---|---|
| Cerrar pares sin declarar | 6 pares | **17** — al repetir la consulta sin filtrar por named graph aparecieron 11 más |
| Anclar IDs con `CODIGO_SUNEDU2` | 22 programas | 22 · **73 de 73** del universo evaluable |
| Anclar pregrado sin `CODIGO_SUNEDU2` | 17 programas | 17 · con dos destinos corregidos |
| Cerrar posgrado | — | 6 más |

**Estado hoy, medido:**

```
186 anclajes urn:esther:id_programa_estudio sobre 80 conceptos · 0 colisiones
99,6 % de la matrícula de grado — 18.846 de 18.930 (semestres 267/279/283)
17 pares duplicados con dct:isReplacedBy hacia su canónico · 0 sin declarar
auditoría estructural del tesauro: 0 hallazgos
```

Lo único sin anclar es lo que **debe** quedar fuera: dos diplomaturas y dos cursos taller
(82 matrículas, formación continua — art. 46 de la Ley 30220), más un caso sin destino
defendible (`216`, 2 matrículas).

### Tres correcciones que afectan a lo que ustedes midieron

1. **`1262` iba al programa equivocado** en el prompt 4. Su nombre en Oracle dice
   «Lingüística e Inglés» (P14/P127) y el prompt lo mandaba a «Inglés y Español» (P97), que
   es otro programa. Verificado además que `1208` y `1262` son **el mismo programa
   renombrado**: ambos modalidad 13, misma unidad académica 152, creados abr-2025 y
   oct-2025 con solape en 2026-1 y 2026-2. Los dos quedaron en P127.

2. **No existe el dilema de modalidad** que planteaban los prompts 2 y 4. Por el ADR-004 un
   concepto agrupa todos sus P-codes: P04/P05/P95 resuelven los tres a
   `programa/administracion`. No hay conceptos por modalidad a los que anclar por separado;
   la modalidad se lee en `upeu:codigoSunedu{Presencial,Semipresencial,Distancia}`.

3. **Resolver por etiqueta es lo que causó los duplicados.** El tesauro reparte los
   programas entre `programas-academicos`, `posgrado` y `segunda-especialidad` —los tres
   legítimos— y además existe `programas-en-implementacion`, que duplica denominaciones sin
   código oficial. Buscar «Ingeniería de Software» por nombre puede devolver el gemelo sin
   P-code. **Resolver siempre por P-code o SEG-code.**

---

## Lo que toca ahora, en este orden

### 1. Dejar de fabricar códigos SUNEDU

En el `searchScript` de [`estudiantes.xml`](../upeu/resources/oracle-lamb/estudiantes.xml):

```sql
MAX(COALESCE(ape.CODIGO_SUNEDU2, 'P'||ape.CODIGO_SUNEDU)) AS SUNEDU_CODE
```

`'P' || CODIGO_SUNEDU` fabrica un P-code falso a partir del correlativo interno que el
ADR-004 declaró no canónico, y cuando ambas columnas son NULL Oracle devuelve `'P'` a secas
—de ahí las 8.305 identidades con ese valor—. Sustituir por el valor oficial **o nada**:

```sql
MAX(ape.CODIGO_SUNEDU2) AS SUNEDU_CODE
```

Un atributo vacío es honesto; `P178` y `'P'` son afirmaciones falsas sobre un dato
regulatorio. El código de quien quede sin valor lo resuelve el puente del paso 2.

**Toca ~25.000 identidades: simulación previa obligatoria.**

### 2. Reemplazar `program-resolver-lamb` por una tabla generada

La LookupTable actual tiene 75 filas, clave por nombre, escrita a mano y congelada con las
URIs del día que se escribió. Por eso publica el gemelo sin P-code en 20.879 de 30.674
entradas de `eduPersonEntitlement`.

La consulta que la genera está **probada y devuelve 186 filas**. Sigue `dct:isReplacedBy`,
así que los conceptos sustituidos se resuelven solos:

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX xl:   <http://www.w3.org/2008/05/skos-xl#>
PREFIX dct:  <http://purl.org/dc/terms/>
SELECT ?idLamb ?uri ?pcode ?label WHERE {
  ?c skos:notation ?n . FILTER(DATATYPE(?n) = <urn:esther:id_programa_estudio>)
  BIND(STR(?n) AS ?idLamb)
  OPTIONAL { ?c dct:isReplacedBy ?sust }
  BIND(COALESCE(?sust, ?c) AS ?destino)      # ← nunca publicar la URI sustituida
  BIND(STR(?destino) AS ?uri)
  OPTIONAL { ?destino xl:prefLabel/xl:literalForm ?label }
  OPTIONAL { ?destino skos:altLabel ?pcode FILTER(REGEX(STR(?pcode),"^(P|SEG)[0-9]+$")) }
} ORDER BY xsd:integer(?idLamb)
```

La clave es **`DAVID.ACAD_PROGRAMA_ESTUDIO.ID_PROGRAMA_ESTUDIO`**: interna, inmutable, ya
presente en `PROGRAM_CODES`. De la URI se derivan P-code, INEI e ISCED-F, que viven en el
tesauro y no hay que replicar en MidPoint.

Alternativa sin SPARQL: el mismo contenido servido en
`productos/vocbench/instituciones/upeu/data/thesaurus-export.json`, campos
`programs[].id_programa_estudio_lamb` y `programs[].replaced_by`.

**La tabla es un artefacto derivado**: se regenera, se versiona y se audita contra el A4.
Nunca se edita a mano — eso es lo que la dejó congelada.

Nueve IDs apuntan a un concepto sin P-code: son programas posteriores al corte del
Clasificador, correctamente clasificados en su campo. Que `academicProgramCode` quede vacío
ahí es lo correcto; `academicProgramUri` sí resuelve.

### 3. Decidir qué atributo eduPerson publica el programa

Pendiente y sin decidir. Consultar `iga-canonical-standards` antes de proponer: la semántica
de eduPerson es estrecha. Lo único firme es que el valor debe ser **la URI del tesauro**, no
un nombre ni un código de LAMB.

### 4. Contraste de modalidad — un control de cumplimiento, no de datos

MidPoint clasifica por `TIPO_PROGRAMA` (`EP`/`SP`/`AD`); el tesauro tiene la misma dimensión
en `upeu:codigoSunedu{Presencial,Semipresencial,Distancia}`. Si un estudiante figura como
`AD` y su programa no tiene código a distancia en el A4, hay una **matrícula en modalidad no
licenciada**. Vale la pena construir esa comprobación.

---

## Verificación de cierre

Tras el paso 1, ningún `academicProgramSuneduCode` debe tener un valor fuera de los 121
P-codes del A4 —cero `'P'`, cero `P178`—. Tras el paso 2, la cobertura de
`academicProgramUri` debe subir del 58,8 % al entorno del 99 %, y las URIs distintas
publicadas pasar de 20 a las que correspondan a los programas con matrícula viva, **ninguna
de ellas con `dct:isReplacedBy`**.

---

## Trampas verificadas del lado de VocBench

- `evaluateQuery` **solo acepta POST**; con GET devuelve `HttpRequestMethodNotSupportedException`.
- El tesauro vive repartido entre el named graph `<…/programas/>` y el **default graph**:
  enumerar con `GRAPH ?g` deja fuera ~2.900 triples y 20 conceptos. Consultar sin filtrar
  por grafo.
- Las notaciones llevan **datatypes propios** (`urn:esther:id_programa_estudio`,
  `ns/IneiCode8`, `ns/KohaCode`), no `xsd:string`. Un `DELETE` con el datatype equivocado no
  borra nada y no da error.
- SKOS-XL: `skos:prefLabel` viene vacío en casi todos los conceptos; pedir
  `xl:prefLabel/xl:literalForm`.
- GraphDB está vacío y no interviene; el almacén es el nativo de Semantic Turkey.

## Lo que NO es tarea de esta sesión

Completar el tesauro. Está al 99,6 % de la matrícula de grado y con auditoría en cero. Si
aparece un programa sin anclar, **no crear el concepto desde MidPoint**: reportarlo a la
sesión de VocBench con su `ID_PROGRAMA_ESTUDIO` y su denominación. Crear conceptos desde
fuera es lo que generó los 17 pares duplicados que hubo que cerrar.
