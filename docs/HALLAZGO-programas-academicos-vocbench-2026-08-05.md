# Programas académicos: 9.367 identidades con código SUNEDU inválido — y el puente a VocBench

**Fecha:** 2026-08-05 · **Medido en vivo en PROD** · **Nada ejecutado**
**Contexto:** [`PROMPT-MIDPOINT-IDENTIDAD.md`](PROMPT-MIDPOINT-IDENTIDAD.md) §"Puntos de contacto" · ADR-004 de VocBench

---

## 1. Resumen

| Hallazgo | Medida |
|---|---|
| 🔴 Identidades con `academicProgramSuneduCode` **que NO existe en el Formato A4** | **9.367** |
| 🔴 De ellas, con el valor literal `'P'` (basura) | **8.305** |
| ✅ Identidades con P-code válido | 16.301 |
| ⚠️ Cobertura de `academicProgramUri` en estudiantes activos | **14.908 / 25.344 = 58,8 %** |
| ⚠️ URIs distintas publicadas por MidPoint | **20** (el tesauro tiene **108 conceptos**) |
| 🔴 El resolver de programas empareja por **NOMBRE**, no por identificador | `program-resolver-lamb`, 75 filas |

**Corrección a la premisa de partida:** el prompt del proyecto dice que el puente Oracle→tesauro
«hoy no existe». **Sí existe, a medias**: hay `program-resolver-lamb` (75 filas) y
`LT-Pcode-INEI` (42 filas), y MidPoint ya publica `academicProgramUri`, `…SuneduCode` y
`…IneiCode`. El problema no es la ausencia del puente: es **cómo está construido**.

## 2. Causa raíz del código SUNEDU inválido

En el `searchScript` de [`estudiantes.xml`](../upeu/resources/oracle-lamb/estudiantes.xml):

```sql
MAX(COALESCE(ape.CODIGO_SUNEDU2, 'P'||ape.CODIGO_SUNEDU)) ... AS SUNEDU_CODE
```

Dos defectos en una línea:

1. **`'P' || CODIGO_SUNEDU` fabrica un P-code falso.** `CODIGO_SUNEDU` es el correlativo interno
   de Oracle que el **ADR-004 declaró NO canónico**. Anteponerle una `P` lo disfraza de código
   oficial. Así aparecen `P178`, `P171`, `P175`, `P176`… (fuera del rango del A4) y —peor—
   `P68`, `P73`, `P63`, `P67`, `P45`, `P61`, que **parecen legítimos pero no están en el A4**:
   colisión semántica, no error visible.
2. **Si ambas columnas son NULL, Oracle concatena sobre NULL y devuelve `'P'`.** De ahí las
   **8.305 identidades con `academicProgramSuneduCode = 'P'`**.

Contraste con la fuente canónica: `sunedu-formato-a4-2025-2.csv` tiene **121 P-codes oficiales**.
Todo valor fuera de ese conjunto es inválido por definición.

## 3. El resolver empareja por nombre — justo lo que no debe hacer

`program-resolver-lamb` (LookupTable, 75 filas) tiene como **clave el nombre del programa**:

```
Administración                              → EP-ADM → …/programa/administracion
Administración y Negocios Internacionales   → EP-ADM → …/programa/administracion
Arq.                                        → EP-ARQ → …/programas/c_e399e0aa
Arquitectura y Urbanismo                    → EP-ARQ → …/programas/c_e399e0aa
```

El prompt del proyecto lo prohíbe explícitamente: *«una tabla de equivalencia explícita
`PE.CODIGO → URI`, **nunca una inferencia por nombre**»*. Los nombres de Oracle arrastran sección
y sede («Administración - Sección Juliaca - Sección Jul»), y el desdoble **938 programas Oracle →
108 conceptos** no se resuelve con cadenas de texto. Es la explicación directa del 58,8 % de
cobertura: lo que no coincide de nombre, no resuelve.

**Además, las URIs son de dos generaciones**: slug (`…/programa/administracion`) y UUID
(`…/programas/c_e399e0aa`). El ADR-003 de VocBench documenta una migración a UUID; MidPoint
conserva ambas. Hay que verificar cuáles siguen resolviendo en el tesauro.

## 4. Lo que VocBench ya ofrece y aquí no se usa

| Archivo | Contenido | Uso hoy en MidPoint |
|---|---|---|
| `sunedu-formato-a4-2025-2.csv` | **121 P-codes oficiales** + denominación, grado, modalidad | ninguno |
| `inei-2022-programas.csv` | catálogo INEI (RJ 067-2024-INEI) | ninguno (LT-Pcode-INEI cubre 42) |
| `oracle-to-vocbench-mapping.csv` | 31 filas con `match_method` y `confidence` | ninguno |
| Tesauro (108 conceptos) | P-codes y SEG-codes como `altLabel`, INEI, ISCED-F, modalidad explícita | parcial, vía nombres |

El tesauro distingue **modalidad por P-code** (Administración = P04 presencial / P05
semipresencial / P95 a distancia). MidPoint clasifica lo mismo por `TIPO_PROGRAMA` (`EP`/`SP`/`AD`).
**Son la misma información por duplicado** → se pueden contrastar, y una discordancia es un
hallazgo de cumplimiento (matrícula en modalidad no licenciada), no un bug de datos.

## 4.bis VocBench está alineado al 100 % con las fuentes oficiales (verificado)

Contrastado contra los originales de SUNEDU e INEI (`~/Downloads/programas pxx upeu` y
`~/Downloads/clasificador_de_carreras_inei`):

| Fuente oficial | Contenido | vocbench | Veredicto |
|---|---|---|---|
| **A4 2026-1** | 121 P-codes | 121 | ✅ conjuntos **idénticos** |
| **A4 2025-2** | 121 P-codes | 121 | ✅ **sin altas ni bajas** entre periodos |
| **A8 2026-1** | 62 SEG-codes | 62 | ✅ |
| **A8 2025-2** | 57 SEG-codes | 57 (CSV propio) | ✅ conserva ambos periodos |
| **INEI programas** | 7.812 (todos los niveles) | 5.794 | ✅ ver desglose |

Desglose INEI por nivel: `profesional_universidad` 1.477 → 1.477 · `maestría_universidad`
2.426 → 2.426 · `segunda especialidad_universidad` 1.601 → 1.601 · `doctorado_universidad`
290 → 290. **Suma exacta = 5.794.** Lo no importado son niveles no universitarios (IEST, IESP,
CETPRO, EEST, ESFA), correctamente descartados. **Códigos en vocbench que no existan en el
oficial: 0.**

**Conclusión: el problema no está en vocbench.** La fuente canónica está construida, verificada y
al día con 2026-1. El defecto está en que MidPoint no la usa.

Cambio detectado a registrar: el A8 pasó de **57 a 62 SEG-codes** en 2026-1 (5 segundas
especialidades nuevas). El A4 no movió ningún código.

## 4.ter Qué llega realmente a LDAP (medido en el directorio)

`academicProgramSuneduCode` —el atributo con los 9.367 valores inválidos— **NO se publica a LDAP**.
Eso acota el daño: la basura de P-codes vive en el repositorio de MidPoint y en Koha
(vía `LT-Pcode-INEI`), no en el directorio.

Lo que sí viaja al directorio es la **URI del programa**, por `eduPersonEntitlement`:

| Medida en LDAP | Valor |
|---|---|
| Personas (`inetOrgPerson`) | 75.690 |
| Entradas con `eduPersonEntitlement` | 30.535 |
| Valores de programa publicados | **30.674** |
| **URIs de programa distintas** | **20** |
| `scibackAcademicProgramUri` / `…Code` | **0 entradas** — el mapping existe en el resource pero no está poblando |

Las 20 URIs son de **dos generaciones**: 14 en formato slug (`…/programa/administracion`) y 6 en
UUID (`…/c_e399e0aa`). Rastreadas en el repo de vocbench, aparecen en archivos **seed**
(`seed/programas-academicos-v2.ttl`, `seed/upeu-programas-pregrado.ttl`) — es decir, generaciones
**anteriores** del tesauro. Una no aparece en ninguna parte:
`…/programa/ingenieria-informatica-y-estadistica` (3 identidades).

✅ **Verificado por SPARQL — ver §4.quater.** Las 20 URIs **sí resuelven**; el problema es otro y
peor de lo previsto: 13 de ellas apuntan al concepto **equivocado** del par.

## 4.quater Verificación SPARQL contra el tesauro vivo (5-ago, cerrada)

Ejecutada contra Semantic Turkey (`Tesauro_Institucional_UPeU`, endpoint
`SPARQL/evaluateQuery`, **POST** — el GET devuelve `HttpRequestMethodNotSupportedException`).
El almacén es el nativo de Semantic Turkey; GraphDB sigue vacío y no interviene.

**Las 20 URIs resuelven: las 20 son `skos:Concept` vivos, en
`scheme/programas-academicos`, con tripletas y etiquetas.** La hipótesis «LDAP publica
identificadores muertos» queda **REFUTADA**.

Pero la comprobación destapó un defecto distinto y mayor: **LDAP publica sistemáticamente el
concepto equivocado del par.** El tesauro contiene pares de conceptos para el mismo programa, y
en cada par uno lleva el P-code oficial y el otro no. **La URI publicada es siempre la que NO lo
lleva.**

| Grupo | URIs | Publicaciones | Estado |
|---|---|---|---|
| **A — sustituidas, con enlace declarado** | 6 (todas UUID) | **12.734** | 🔴 el tesauro declara `dct:isReplacedBy` + `skos:exactMatch` al gemelo con P-code |
| **B — gemelo con P-code, sin enlace declarado** | 6 | **8.142** | 🔴 duplicado no resuelto en el tesauro |
| **C — correctas** | 7 | 9.795 | ✅ concepto con P-code oficial |
| **D — concepto incompleto** | 1 | 3 | ⚠️ sin P-code, sin gemelo, sin `xl:prefLabel` |
| | **20** | **30.674** | **68,1 % apunta a un concepto sin P-code** |

**Grupo A** (corrección mecánica — el propio tesauro dice a dónde ir):

| Publicada en LDAP | `isReplacedBy` | P-code del sustituto | Identidades |
|---|---|---|---|
| `c_b48bff58` | `programa/psicologia` | P33, P131, P101 | 3.590 |
| `c_c5f87ee9` | `programa/enfermeria` | P22 | 2.608 |
| `c_be8b346d` | `programa/ingenieria-civil` | P25 | 2.513 |
| `c_bbf436cf` | `programa/ingenieria-de-sistemas` | P27 | 1.843 |
| `c_e399e0aa` | `programa/arquitectura-y-urbanismo` | P06 | 1.097 |
| `c_353ae8f7` | `programa/medicina-humana` | P30 | 1.083 |

**Grupo B** (requiere decisión: no hay enlace, hay que declarar cuál es canónico):

| Publicada en LDAP | Gemelo con P-code | P-code | Identidades |
|---|---|---|---|
| `programa/contabilidad-gestion-tributaria` | `…-y-aduanera` | P08, P96, P09 | 5.236 |
| `programa/educacion-inicial` | `…-y-puericultura` | P19, P128, P98 | 2.245 |
| `programa/educacion-ingles-espanol` | `educacion-especialidad-ingles-y-espanol` | P97 | 293 |
| `programa/educacion-educacion-fisica` | `…-recreacion-y-deportes` | P12 | 217 |
| `programa/educacion-primaria` | `…-y-pedagogia-terapeutica` | P20, P129, P99 | 123 |
| `programa/educacion-musica-artes` | `…-musica-y-artes-visuales` | P17 | 28 |

**Grupo D:** `programa/ingenieria-informatica-y-estadistica` (3 identidades) — 9 tripletas, un
`skos:broader` a la facultad, `skos:prefLabel` plano en vez de SKOS-XL. Concepto a medio crear.

**Corrección de cifra:** el scheme `programas-academicos` tiene **179 conceptos**, no 108. LDAP
publica 20 → **11,2 % del catálogo**. Del A4 (121 P-codes oficiales), **70 conceptos** del tesauro
llevan P-code como `altLabel`.

**Consecuencia para el diseño del puente (§5.2):** la tabla `ID_PROGRAMA_ESTUDIO → URI` **no puede
generarse contra el estado actual del tesauro** sin arrastrar el mismo error. El orden correcto es
**primero resolver los pares en VocBench** (aplicar los 6 `isReplacedBy` del grupo A y decidir los
6 del grupo B), y **después** generar la tabla. Generarla antes fijaría en el IGA una elección que
el tesauro ya declaró obsoleta.

**Método:** consultas y salidas reproducibles con
`source ~/.secrets/vocbench-upeu.env` + login `Auth/login` + POST a `SPARQL/evaluateQuery` con
`ctx_project=$VOCBENCH_PROJECT`.

## 5. Propuesta

### 5.1 Dejar de fabricar códigos (corrección inmediata, alto impacto)

En el `searchScript` de estudiantes, sustituir la concatenación por el valor oficial **o nada**:

```sql
MAX(ape.CODIGO_SUNEDU2)   -- solo el oficial; si no hay, NULL
```

Un atributo vacío es honesto; `'P'` y `P178` son afirmaciones falsas sobre el regulador.
El P-code de quienes queden sin valor se resuelve por la tabla de equivalencia (§5.2).
**Requiere simulación previa:** toca ~25.000 identidades.

### 5.2 Puente por identificador, no por nombre

Clave: **`DAVID.ACAD_PROGRAMA_ESTUDIO.ID_PROGRAMA_ESTUDIO`** (interno, inmutable, ya presente en
`PROGRAM_CODES`) → URI del concepto del tesauro. De la URI se derivan P-code, INEI e ISCED-F,
que ya viven en el tesauro y no hay que replicar.

Se materializa como **LookupTable** (patrón ya usado aquí) generada desde VocBench, no escrita a
mano. La tabla es un **artefacto derivado**: se regenera, se versiona y se audita contra el A4.

### 5.3 Dónde vive la fuente

VocBench es la fuente canónica del catálogo (P-codes, INEI, ISCED-F, modalidad); MidPoint es
consumidor. La regla del ADR-054 aplica: **el mapeo se genera en VocBench y se publica al IGA**,
nunca al revés. Decisión pendiente de ADR: LookupTable regenerada vs. resource de solo lectura
sobre una vista del CDC.

### 5.4 Qué atributo eduPerson publica el programa

Pendiente, y hay que consultar `iga-canonical-standards` antes de proponer. Lo que sí es firme:
si se publica, el valor debe ser **la URI del tesauro**, no un nombre ni un código de LAMB.

## 6. Orden sugerido

| # | Qué | Por qué primero |
|---|---|---|
| 1 | Quitar `'P'||CODIGO_SUNEDU` del searchScript | 9.367 identidades afirmando un código falso ante un dato regulatorio |
| ~~2~~ | ~~Verificar qué URIs siguen vigentes~~ | ✅ **HECHO** (§4.quater): resuelven las 20, pero 13 apuntan al concepto equivocado |
| 2.bis | **Resolver los pares en VocBench** (6 del grupo A por `isReplacedBy`, 6 del grupo B por decisión) | sin esto, el puente hereda el error en 20.879 publicaciones |
| 3 | Generar el puente `ID_PROGRAMA_ESTUDIO → URI` desde VocBench, **después de 2.bis** | desbloquea el 41 % sin cobertura |
| 4 | Contraste modalidad `TIPO_PROGRAMA` ↔ P-code del A4 | detecta matrícula en modalidad no licenciada |

**Nada de esto se ha ejecutado.** Los cambios 1 y 3 tocan decenas de miles de identidades y exigen
simulación previa, como todo lo de esta semana.
