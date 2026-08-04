# Migración del `CANON_KEY` — Oracle LAMB Trabajadores v3

**Fecha:** 2026-08-03 · **Estado:** DISEÑO, nada ejecutado · **Requiere aprobación y ventana**
**Problema:** `docs/runbooks/bajas-trabajadores-sin-procesar-2026-08-03/RUNBOOK.md` §causa raíz
**Antecedentes obligatorios:** `docs/specs/trabajadores-correlation-guardrail-2026-07-20.md` ·
memoria `fix-uid-trabajadores-abortado-2026-07-17`

---

## 1. El problema, en una frase

El `__NAME__`/`__UID__` del resource es el `CANON_KEY`, que se apoya en `COD_APS`; **`COD_APS`
no es único por persona**, así que el desempate `CANON_RN = 1` descarta a todas menos una de
cada grupo que lo comparte.

Medido en Oracle (03-ago), trabajadores con contrato vivo (`ID_ENTIDAD=7124`):

| | |
|---|---|
| Personas (`NUM_DOCUMENTO` distintos) | **5.603** |
| `COD_APS` distintos | **2.489** |
| `COD_APS` compartidos por >1 persona | **2.203** |
| Peor caso | `005567508` → **6 personas distintas** |
| Personas en MidPoint hoy | **2.423** (43 %) |
| **Nunca salen del `searchScript`** | **~3.114** |

```sql
CANON_KEY = CASE WHEN COUNT(*) OVER (PARTITION BY ID_TIPODOCUMENTO, <num canonicalizado>) = 1
                 THEN COD_APS                        -- ← colisiona entre personas
                 ELSE COD_APS || '-' || ID_PERSONA
            END
... WHERE z.CANON_RN = 1
```

La rama `ELSE` solo se activa cuando colisiona el **documento**. Dos personas con documentos
distintos que comparten `COD_APS` caen ambas en la rama `THEN`.

---

## 2. Restricciones que impone la historia (no negociables)

| # | Lección | Origen |
|---|---|---|
| R1 | **Cambiar el `__UID__` renombra shadows en masa.** Un intento previo se abortó al descubrir que habría renombrado a **4.097 personas**; lo detectó una pregunta sobre InOut, no los 8 tests de laboratorio | 17-jul |
| R2 | **Una persona puede tener varios `ID_PERSONA` en Oracle.** `COD_APS 00534601` (Orlando) existe con `ID_PERSONA` 10041 y 202895 — mismo humano, dos filas. `ID_PERSONA` **no** es clave de persona | guardarraíl §1 |
| R3 | **Drift de padding ya materializado**: `personalNumber` en MidPoint = `00614192` vs `CANON_KEY` = `000614192`. El tier 2 del guardarraíl (comparación exacta) **no** atrapa esos casos | guardarraíl §4 |
| R4 | **El guardarraíl 2-tier nunca se validó** con un canario real | runbook 26-jul |
| R5 | `searchScript` solo admite `EqualsFilter` sobre `__NAME__`/`__UID__` — no hay filtros compuestos para acotar pruebas | medido 03-ago |

---

## 3. Opciones de clave

| Opción | Clave | Único por persona | Estable | Veredicto |
|---|---|---|---|---|
| **A** | `ID_PERSONA` | ❌ (R2: una persona, varios ID) | ✅ | **Descartada**: rompe la identidad de los duplicados de origen |
| **B** | `NUM_DOCUMENTO` canonicalizado + tipo | ✅ salvo duplicados de origen | ⚠️ cambia al reanclar CE→DNI | Descartada como clave: es justo lo que provocó los duplicados de julio |
| **C** | **`COD_APS \|\| '-' \|\| ID_PERSONA` SIEMPRE** | ✅ por fila-persona | ✅ mientras Oracle no reescriba `ID_PERSONA` | **Recomendada** |
| D | Sintética en MidPoint (secuencia) | ✅ | ✅ | Descartada: obliga a un mapa externo y rompe la reproducibilidad del conector |

### Por qué C

- Es un **superconjunto** del formato actual: la rama `ELSE` ya produce exactamente ese valor,
  así que no se inventa nada — se generaliza lo que ya existe y está probado.
- Elimina la colisión por construcción: `COD_APS` puede repetirse, pero el par con `ID_PERSONA`
  no.
- **No resuelve R2** (una persona con dos `ID_PERSONA` seguirá generando dos shadows). Eso es un
  **duplicado de origen en Oracle**, ya escalado a los DBAs, y no debe resolverse falseando la
  clave: dos filas distintas en la fuente deben verse como dos objetos, y la correlación decide
  si son el mismo humano.

---

## 4. Estrategia de migración — el orden es lo que evita el desastre

> **Idea central:** *migrar primero los shadows en el repositorio y después el `searchScript`.*
> Si se cambia el script primero, en el siguiente ciclo MidPoint ve 7.371 objetos "nuevos" y
> 7.371 shadows "desaparecidos" → altas masivas + posible `unmatched → addFocus`. Invirtiendo
> el orden, cuando el script emite la clave nueva los shadows **ya coinciden** y no hay ventana.

### Fase 0 — Normalizar `personalNumber` (prerequisito de R3)

Backfill: recalcular `personalNumber` de todo `User` con afiliación laboral desde el
`CANON_KEY` actual de su shadow linkado. Sin esto el tier 2 del guardarraíl es papel mojado
para los casos con padding desfasado.
**Salida:** 0 discrepancias `personalNumber` ↔ `CANON_KEY` en los linkados.

### Fase 1 — Medición previa (obligatoria, sin tocar nada)

1. Cuántos shadows cambian de `__UID__` con la clave nueva (esperado: **todos** los que hoy usan
   la rama `THEN`).
2. **De las ~3.114 personas que entrarían por primera vez, cuántas YA existen como `User`** por
   otro canal (estudiantes/egresados) — se cruza por `extension/upeu:lambDocNum`, **no** por
   `name` (los `User` se llaman por código, no por documento). *No medido aún: la consulta por
   `ext` jsonb agota el timeout; hay que hacerla por lotes.*
3. Cuántas de esas caerían en tier 1 (`lambDocNum`), cuántas en tier 2, cuántas `unmatched`.

**Criterio de parada:** si el número de `unmatched` previsto es > 0 y no se puede explicar caso
por caso, **no se ejecuta**.

### Fase 2 — Validar el guardarraíl (R4, sigue pendiente desde el 26-jul)

Canario real sobre uno de los casos "atrapables" conocidos, comprobando que produce
`disputed → createCorrelationCase` y **no** un `User` nuevo.

### Fase 3 — Migrar los shadows en el repositorio

Para cada shadow con clave vieja: `PATCH` de `primaryIdentifierValue` y del atributo de
identificación al valor nuevo `COD_APS-ID_PERSONA`, con `?options=raw` (operación de
repositorio, sin invocar al conector).

- Por lotes, con verificación de `version` en Postgres tras cada lote (un 204 no prueba nada).
- Backup previo: `pg_dump` de `m_shadow` + CSV del mapeo `oid, uid_viejo, uid_nuevo` — **ese CSV
  es el plan de reversión**.

### Fase 4 — Desplegar el `searchScript` nuevo

`PATCH` del resource (nunca `PUT`: arranca el `<schema>`). Verificar `<schema>`, `<native>`,
`connectorRef`, `capabilities` y test connection.

### Fase 5 — Reconciliación controlada

Con el guardarraíl activo y validado, reconciliar para incorporar las ~3.114 personas nuevas.
**Por lotes**, revisando los `disputed` que aparezcan antes de continuar.

---

## 5. Riesgos

| Riesgo | Mitigación |
|---|---|
| **Duplicación masiva de `User`** si la correlación falla tras el cambio de clave | Fase 0 + Fase 2 antes de tocar nada; guardarraíl en `disputed`; lotes pequeños con revisión |
| **Consumidores que dependen del identificador**: LDAP (`uid`), Koha (`cardnumber`), InOut, RIMS | El `__UID__` del shadow **no** se proyecta a los consumidores (ellos usan `name`/`employeeNumber` del `User`), pero **hay que verificarlo explícitamente** — fue exactamente lo que abortó el intento del 17-jul |
| Reversión difícil a mitad de camino | El CSV `oid, uid_viejo, uid_nuevo` permite deshacer la Fase 3 con el mismo mecanismo |
| Las ~3.114 altas disparan provisioning masivo (LDAP, Koha, M365) | Ejecutar con los roles de aplicación en `proposed`, o por lotes con verificación de efectos aguas abajo |
| Duplicados de origen en Oracle (R2) generan 2 shadows para 1 humano | Es correcto que existan 2 objetos; la correlación los une al mismo `User`. El saneamiento del dato es de los DBAs |

---

## 6. Lo que este diseño NO resuelve

- **No arregla los duplicados de persona en Oracle** (R2). Solo deja de esconderlos.
- **No corta accesos** — eso es el leaver gap (`docs/specs/ldap-leaver-gap/01-analisis.md`).
- **No reactiva** `recon-oracle-lamb-trabajadores-daily`: esa decisión sigue dependiendo de la
  validación del guardarraíl y de la remediación de los 3 duplicados activos.

## 7. Recomendación

Ejecutar **Fase 0 y Fase 1 primero, como trabajo independiente**. Ambas son de solo lectura o
reversibles, y su resultado decide si la migración es viable o si hay que resolver antes la
calidad del dato en Oracle. **No comprometerse con las Fases 3-5 hasta ver los números de la
Fase 1.**

---

## 8. RESULTADOS — Fase 0 y Fase 1 ejecutadas (2026-08-03)

### Fase 0 — `personalNumber`: **no requiere acción** ✅

| Situación | Users |
|---|---|
| `personalNumber` = `CANON_KEY` **exacto** | **7.364** |
| Nulo | 0 |
| Difiere solo en padding de ceros | 0 |
| Difiere de verdad | 0 |

El drift de padding que documentó el spec del 20-jul (caso Luzirene, `00614192` vs
`000614192`) **ya no existe en la población linkada**. R3 queda cerrado: el tier 2 del
guardarraíl sí protegería. **No hay backfill que hacer.**

### Fase 1.1 — Impacto del cambio de clave: **total**

| Formato actual del `__NAME__` | Vivos | Muertos |
|---|---|---|
| Solo `COD_APS` → **CAMBIA** | **7.371** | 145 |
| Ya `COD_APS-ID_PERSONA` → no cambia | 0 | 0 |

**De los que cambian, 7.364 están LINKADOS a un `User`.**

Dato relevante: hoy la rama `ELSE` del `CASE` **nunca se activa** — ningún shadow lleva el
formato compuesto. Es decir, el `CANON_RN` ya colapsa las colisiones de documento antes de que
la rama pueda dispararse. La generalización de la opción C es, en la práctica, un cambio de
formato del 100 % de los identificadores.

### Fase 1.2 — Las personas que entrarían: **son altas nuevas, no vinculaciones**

Muestra de **30** trabajadores vivos (no aleatoria: 30 consecutivos del listado — sesgo
reconocido, conviene repetir con muestreo aleatorio antes de ejecutar):

| Situación | Personas |
|---|---|
| Ya tienen shadow de Trabajadores | 9 |
| **Existen como `User` solo en la extensión** (`lambDocNum`) | **0** |
| No aparecen de ninguna forma | 21 |

**Ninguna de las personas ausentes existe en MidPoint por otro canal.** No entraron como
estudiante ni como egresado. Por tanto la migración **no vincularía identidades existentes:
daría de alta ~3.114 personas nuevas.**

### Qué cambia esto en el análisis de riesgo

| Riesgo previsto | Veredicto tras medir |
|---|---|
| Duplicación de `User` por correlación fallida | **Menor de lo temido**: las personas nuevas no tienen `User` previo con el que duplicarse. El guardarraíl sigue siendo necesario para los 7.364 renombrados, no para las altas |
| Drift de `personalNumber` rompe el tier 2 | **Descartado** (Fase 0: 0 casos) |
| **Renombrado de 7.364 shadows linkados** | **Confirmado, es el riesgo principal.** Es el mismo escenario que abortó el intento del 17-jul, ahora cuantificado |
| **Provisioning masivo por 3.114 altas** | **Nuevo riesgo, ahora dimensionado**: cada alta dispara LDAP + Koha + M365 + WiFi. Es el efecto más visible y el que hay que escalonar |

### Criterio de parada de la Fase 1: **superado, con condiciones**

No aparecen `unmatched` problemáticos: los que no correlacionan son personas nuevas, y crear su
`User` es el comportamiento correcto. La migración es **viable**.

**Condiciones antes de la Fase 3:**

1. Repetir la Fase 1.2 con **muestreo aleatorio** de ≥300 (la muestra actual es consecutiva).
2. **Verificar que ningún consumidor depende del `__UID__` del shadow** — LDAP, Koha, InOut,
   RIMS. Es lo que abortó el intento del 17-jul y sigue sin comprobarse.
3. Validar el guardarraíl (R4, Fase 2), que sigue pendiente desde el 26-jul.
4. Decidir cómo escalonar 3.114 altas para no disparar provisioning masivo en un solo ciclo
   (p. ej. roles de aplicación en `proposed` durante la carga).
