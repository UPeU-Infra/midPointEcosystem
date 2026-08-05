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
| 2 | Verificar qué URIs de las 20 siguen vigentes tras la migración a UUID (ADR-003) | barato; evita construir sobre URIs muertas |
| 3 | Generar el puente `ID_PROGRAMA_ESTUDIO → URI` desde VocBench | desbloquea el 41 % sin cobertura |
| 4 | Contraste modalidad `TIPO_PROGRAMA` ↔ P-code del A4 | detecta matrícula en modalidad no licenciada |

**Nada de esto se ha ejecutado.** Los cambios 1 y 3 tocan decenas de miles de identidades y exigen
simulación previa, como todo lo de esta semana.
