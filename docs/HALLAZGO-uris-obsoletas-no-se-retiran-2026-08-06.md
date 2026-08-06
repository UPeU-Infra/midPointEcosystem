# Las URIs de programa obsoletas no se retiran de LDAP — diagnóstico completo

**Fecha:** 2026-08-06 · **Medido en vivo** · **Nada corregido todavía**
**Contexto:** primera reconciliación tras el cambio de resolver de programa por `ID_PROGRAMA_ESTUDIO`
(resource v183/v184, commits `b978b4a` / `3d5bcc9`).

---

## 1. El cambio funcionó

Recon del 6-ago 11:20 UTC, medido en LDAP:

| Medida | Antes | Después |
|---|---|---|
| URIs de programa distintas publicadas | **20** | **84** |
| Personas con URI de programa | 10.527 | **34.646** |
| URIs que están en el puente | — | 71 de 84 |

El puente por identificador hace lo que debía: aparecieron 64 URIs que el emparejamiento por
nombre nunca alcanzaba.

## 2. 🔴 Pero las URIs viejas siguen ahí — 12.727 personas

| Situación | Personas |
|---|---|
| Publican la deprecada **Y** la canónica a la vez | **7.841** |
| Publican **solo** la deprecada | **4.886** |
| **Total con URI de concepto deprecado** | **12.727** |

Las 6 deprecadas implicadas son las del grupo A del tesauro: `c_b48bff58` (3.593),
`c_c5f87ee9` (2.608), `c_be8b346d` (2.513), `c_bbf436cf` (1.843), `c_e399e0aa` (1.097),
`c_353ae8f7` (1.083).

**Una persona que publica Psicología dos veces, con dos identificadores distintos, está peor
que antes del cambio:** quien agrupe por URI ve duplicados, y quien resuelva `c_b48bff58` obtiene
el concepto que el tesauro declaró sustituido.

## 3. Causa raíz: el zero-set no materializa

`academicProgramUri` es **multivalor**. El mapping `strong` **añade** el valor correcto pero
**no elimina** el que ya estaba de corridas anteriores. En un atributo single-value lo habría
reemplazado; aquí conviven.

**Es el mismo patrón ya documentado en este repo para `affiliations`** (2026-05-30, runbook
PM10: *"el zero-set no materializa"*), que entonces se resolvió con un item per-IIA single-source
más derivación en el template.

Una sola causa explica los tres síntomas: los 7.841 duplicados, los 4.336 egresados congelados y
los 393 activos sin canónica.

## 4. Desglose de los 4.886 «solo deprecada»

| Grupo | Personas | Qué son |
|---|---|---|
| **Sin matrícula vigente** | **4.336** | Egresados/ex-alumnos: no están en la fuente, el inbound nunca corre para ellos. Valor **congelado** |
| **Con matrícula vigente** | **550** | Estudiantes activos |

De los **550 activos**:
- **157** cursan niveles **no licenciados** (TESIS 101, Idiomas 40, Diplomatura 6, Ed. Contínua 5,
  CEPRE 4, Posgrado 1). **No deben tener URI** — el problema es que arrastran una deprecada que
  nunca debieron recibir, publicada por el viejo resolver por nombre.
- **393** tienen su `ID_PROGRAMA_ESTUDIO` **en el puente** y aun así no recibieron la canónica.

## 5. Hipótesis descartadas por medición (las tres)

| Hipótesis | Veredicto |
|---|---|
| El puente es ambiguo: un ID sirve a varios programas | ❌ **0 de 186** ambiguos (y 0 de los 942 IDs de Oracle) |
| Están fuera del universo del `searchScript` (filtro de semestres, como pasó con Idiomas) | ❌ **550 de 550 están DENTRO** |
| No tienen shadow del resource Estudiantes | ❌ **sí lo tienen** (`a463cf20-…` en el caso testigo) |

## 6. El caso testigo: `202612155`

| Dónde | Qué tiene |
|---|---|
| MidPoint | **`academicProgramUri` NO existe** |
| MidPoint | `academicProgramSuneduCode = 'P'` (el valor fabricado, aún) |
| LDAP | `eduPersonEntitlement: …/c_bbf436cf` |
| Shadows | Estudiantes, LDAP, Koha, RENIEC — los 4 presentes |

**MidPoint no tiene la URI pero LDAP la publica** → el valor de LDAP es un **residuo congelado**:
el outbound lo escribió en su día y nunca lo retiró.

### 🔴 Recompute ≠ Reconcile (verificado en vivo)

Se le hizo un **recompute** individual: cerró `success`, versión 181 → 182, y **`academicProgramUri`
siguió sin aparecer**.

- **Recompute**: re-evalúa mappings sobre el **shadow cacheado en el repositorio**. No consulta
  Oracle. Si el shadow no trae `PROGRAM_CODES` actualizado, el inbound no recibe entrada,
  devuelve `null`, no se escribe nada y el valor viejo de LDAP sobrevive.
- **Reconcile**: relee del recurso y **refresca el shadow** antes de evaluar.

Esto es simétrico a lo comprobado el mismo día con las OUs: **la reconciliación de `generic/ou`
NO recalcula el DN** (solo sincroniza shadow↔recurso), mientras que el recompute sí evalúa el
foco. Son operaciones complementarias y **cada problema exige la suya**.

## 6.bis CONFIRMADO: una reconciliación completa NO los limpia (6-ago, 22:30 UTC)

Se lanzó por error una **reconciliación completa** del canal Estudiantes (el filtro
`attributes/icfs:name` no acotó; ver R4 del protocolo de pre-ejecución). Procesó **25.794
objetos**, cerró `partial_error` (timeouts de Koha, ajenos a este canal).

**Diff real en LDAP: CERO.**

| | Antes | Después |
|---|---|---|
| Personas con URI | 34.646 | 34.646 |
| Valores totales | 46.179 | 46.179 |
| URIs distintas | 84 | 84 |
| **Valores deprecados** | **12.737** | **12.737** |
| Con deprecada **y** canónica | 7.841 | 7.841 |

Nadie ganó URI, nadie la perdió, ningún valor cambió. El estado ya era **convergente**.

**Confirmación empírica y definitiva:** ninguna reconciliación limpiará los 12.737. No es
cuestión de esperar ni de forzar pasadas — el mapping no puede retirar un valor que ya no
produce. La corrección exige tocar el outbound (materializar el zero-set, patrón PM10) o limpiar
el atributo directamente en LDAP.

**Corolario sobre el testigo `202612155`:** su `ID_PROGRAMA_ESTUDIO` es **893 = «Cepre Regular»**,
que **no está en el puente y no debe estarlo** (preuniversitario, no licenciado). El inbound hace
lo correcto al no asignarle URI. Su `c_bbf436cf` es residuo del viejo resolver por nombre.
⚠️ Estaba **mal clasificado** en el grupo de «393 con id en el puente»: pertenece a los 157 de
niveles no licenciados. La clasificación interna de los 12.727 tiene errores de agregación
propios; **el total y la causa raíz sí están bien medidos**.

## 6.ter CORRECCIÓN — clasificación rehecha: los «393 sin explicar» NO existen

La clasificación de §4 estaba **mal construida**. Rehecha con el criterio correcto:

| Grupo | Personas | Naturaleza |
|---|---|---|
| **URI correcta + deprecada residual** | **8.234** | ya tienen su canónica; solo sobra la vieja |
| Egresados sin matrícula vigente | **4.336** | valor congelado; nadie los recomputa |
| Activos de niveles NO licenciados | **156** | TESIS 101 · Idiomas 41 · Diplomatura 6 · Ed. Contínua 5 · CEPRE 4 |
| Activo licenciado con id fuera del puente | 1 | caso aislado |
| | **12.727** | |

### El error de método

Comprobaba «¿tiene la canónica?» contra una **tabla fija de seis pares de pregrado**
(`c_b48bff58 → programa/psicologia`). Pero los afectados de posgrado publican
`c_b48bff58` **junto a la URI de su maestría**:

```
201521028  →  c_b48bff58  +  programa/maestria-en-educacion-psicologia-educativa   ✅ correcta
202013547  →  c_b48bff58  +  programa/maestria-en-psicologia-clinica-y-de-la-salud ✅ correcta
```

Como su canónica **no era** `programa/psicologia`, el emparejamiento fallaba y los contaba como
«sin canónica». La pregunta correcta era **«¿tiene alguna URI que esté en el puente?»**, no
«¿tiene la pareja que yo espero para esta deprecada?».

🔴 **Consecuencia: la cifra «393 activos sin URI canónica» era FALSA.** Podría haber motivado
trabajo innecesario en VocBench buscando anclajes que no faltan.

### Lo que queda tras la corrección

**No hay ningún grupo sin explicar.** Los 12.727 son una sola cosa con tres orígenes: **residuo
del viejo resolver por nombre que nunca se retiró**. Ni el puente falla, ni el inbound falla, ni
faltan anclajes en el tesauro. Y el remedio es más simple de lo que parecía: a **8.234 solo hay
que quitarles la URI vieja** (ya tienen la buena).

## 7. Qué falta

1. ~~Testigo `202612155`~~ — ✅ **RESUELTO** (§6.bis): es un CEPRE, el sistema actúa
   correctamente. Y una recon completa ya demostró que no limpia nada.
   ~~Rehacer la clasificación~~ — ✅ **HECHA** (§6.ter): 8.234 con URI correcta + residual,
   4.336 egresados, 156 no licenciados, 1 aislado. **Los «393 sin explicar» no existían.**
2. 🔴 **Retirar los valores obsoletos** — lo de fondo, y **ninguna reconciliación lo arregla**:
   afecta a las 12.727 (7.841 duplicados + 4.336 egresados + los que queden). Opciones a evaluar:
   hacer que el outbound de `eduPersonEntitlement` retire lo que ya no corresponde (patrón PM10),
   o una limpieza puntual del atributo en LDAP. **Ambas tocan decenas de miles de entradas y
   exigen simulación propia.**
3. **Los 157 de niveles no licenciados**: decisión de producto ya abierta — no deben publicar URI
   de programa académico en absoluto.
