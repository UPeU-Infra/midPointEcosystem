# Guardarraíl de correlación — Oracle LAMB Trabajadores v3 (diseño, 2026-07-20)

**Estado (actualizado 2026-07-26): APLICADO A PROD (version 322), verificado.** El canario de
validación en vivo no se pudo completar como estaba diseñado porque, al verificar el estado real
antes de tocar nada, se descubrió un **incidente crítico no documentado**: la tarea
`recon-oracle-lamb-trabajadores-daily` fue reanudada y ejecutada manualmente el 2026-07-25 (sin
decisión explícita registrada), recreando el patrón del incidente del 20-jul para 4 personas más,
3 de ellas ya provisionadas a LDAP/Koha reales sin remediar. La tarea sigue **suspendida** (re-
suspendida hoy como acción de protección). Ver §5b para el detalle completo y §6 para la
recomendación actualizada. Este documento nació como el entregable de una sesión de diseño
explícitamente autorizada por Alberto tras el incidente de duplicados del 20-jul (ver
`docs/runbooks/telegram-alertas-tasks-2026-07-20/tarea3-resultado-200610808-91-personas.md`,
sección "✅ FIX APLICADO" → "🔴 Riesgo colateral").

Resource: `Oracle LAMB Trabajadores v3`, oid `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21`.

---

## 1. Recontextualización del problema (no reabrir la investigación ya hecha, solo el marco)

El fix `CANON_RN` del 20-jul (colapsar 2-3 filas por persona a 1, priorizando DNI) es correcto y
ya está desplegado. El riesgo remanente, ya documentado: cuando el valor de
`extension/upeu:lambDocNum` que un shadow computa CAMBIA (p. ej. de `CE:000534601` a `00534601`
porque antes ganaba la fila CE y ahora gana la fila DNI), el único correlador del resource
(`items` sobre `lambDocNum`) deja de encontrar al `User` existente → `unmatched → addFocus` crea
un `User` duplicado. Esto ya ocurrió 2/2 veces en el canario de hoy (Orlando `00534601`, Luzirene
`000614192`), ambos remediados en la misma sesión.

**Corrección de causa raíz (nuevo hallazgo de esta sesión, verificado contra Oracle en vivo, no
inferido):** para los 2 casos del canario, el problema **no es únicamente** un reanclaje de
documento (CE→DNI) de la MISMA persona-Oracle. Es más profundo:

```
COD_APS 00534601 (Orlando) en ELISEO.VW_APS_EMPLEADO tiene DOS ID_PERSONA distintos:
  ID_PERSONA=10041   → MOISES.PERSONA: "Orlando Gabriel Cortez Bazantes", doc CE 000534601
                        (este es el ID_PERSONA que el User real de MidPoint ya conoce:
                        extension/upeu:lambIdPersona=10041, extension/sb:externalSystemId=10041)
  ID_PERSONA=202895  → MOISES.PERSONA: "ORLANDO GABRIEL CORTEZ BAZANTES" (mayúsculas), doc CE
                        0534601 — MISMO NOMBRE, documento con formato distinto. Y en
                        ELISEO.VW_APS_EMPLEADO este ID_PERSONA tiene la fila DNI
                        (00000000534601, tipo=1) que el fix CANON_RN ahora prefiere y que GANA
                        el dedup por CANON_KEY=00534601.

COD_APS 000614192 (Luzirene) tiene el mismo patrón:
  ID_PERSONA=11173   → MOISES.PERSONA: "Luzirene Gomes De Alcantara", doc CE 00614192
                        (ID_PERSONA que el User real ya conoce: externalSystemId=11173)
  ID_PERSONA=192480  → MOISES.PERSONA: "Luzirene Gomes De Alcantara", doc CE 000614192 —
                        MISMO NOMBRE. En ELISEO.VW_APS_EMPLEADO este ID_PERSONA es el que aporta
                        la fila DNI ganadora tras CANON_RN.
```

Es decir: **MOISES tiene un registro de persona DUPLICADO para Orlando y para Luzirene** (misma
clase de hallazgo que `05436990`/Ariana ya escalados a RRHH — ver Anexo D de
`docs/governance/matriz-fuentes-oracle-lamb.md`), y el fix `CANON_RN`, al preferir el tipo de
documento de mayor prioridad (DNI), en estos 2 casos terminó prefiriendo la fila que pertenece al
`ID_PERSONA` **"nuevo"/duplicado**, no al que MidPoint ya conocía.

**Consecuencia para el diseño:** ningún mecanismo de correlación, por bien diseñado que esté,
puede decidir con certeza "estos dos `ID_PERSONA` de Oracle son la misma persona física" — eso es
una decisión de calidad de dato/gobernanza, no de IGA. Lo único que un guardarraíl de MidPoint
puede hacer honestamente es: **detectar la ambigüedad y pausarla para revisión humana**, en vez de
(a) crear un `User` nuevo a ciegas (el bug de hoy) o (b) vincular a ciegas al `User` existente
(podría estar vinculando a un `ID_PERSONA` equivocado si algún día los registros MOISES se separan
de verdad en 2 personas reales). Esto descarta cualquier diseño que intente "auto-resolver" el
link, y confirma que el mecanismo correcto es el de **correlación con confianza intermedia →
`disputed` → caso de correlación para un humano**, no un `<condition>` binario que fuerce sí/no.

---

## 2. Mecanismo elegido: correlator compuesto (tiers + pesos) con reacción `disputed`

### 2.1 Por qué este mecanismo y no otros

Se evaluaron 3 opciones (paso 1 del encargo):

| Opción | Veredicto |
|---|---|
| **A. `<condition>` en la reacción `unmatched→addFocus`** (Groovy que busque un `User` con el mismo `personalNumber` antes de permitir `addFocus`) | **Descartada.** No hay precedente en este repo de `<condition>` sobre una `SynchronizationReactionType` (solo sobre `<inbound>`/mappings, que es un elemento de schema totalmente distinto). El repo SÍ tiene un precedente **negativo** relevante: `koha-ils.xml` documenta que `FilterSubCorrelatorType` de MidPoint 4.10 **no admite `<condition>`** — no es evidencia directa de que la reacción tampoco lo admita, pero sí es una señal de que este XSD tiene restricciones no obvias en esta versión, y no hay forma de verificarlo sin un cambio en PROD (que es exactamente lo que se quiere evitar hoy: ensayar sintaxis no probada en el resource que ya tuvo un incidente). |
| **B. Correlator compuesto (tiers/weights) + reacción `disputed` con `createCorrelationCase`** | **Elegida.** Es el mecanismo **documentado oficialmente** por Evolveum para exactamente este escenario ("match can be resolved automatically if it meets a defined confidence threshold, or manually by a human operator" — Correlators / Rule Composition, docs.evolveum.com). Y — más importante — **ya está en producción en este mismo repo**: `koha-ils.xml` usa `reaction situation=disputed → createCorrelationCase` con éxito (líneas 1915-1919). No es una sintaxis nueva sin probar; es un patrón que YA vive en PROD para otro resource. |
| **C. Cambiar la reacción `unmatched` a "sin acción"** (como hace `koha-ils.xml` para Koha, dejando shadows unmatched sin tocar) | Descartada como solución única: aunque es segura (cero riesgo de duplicado), **no resuelve nada** — deja a los 97 casos en riesgo (ver §3) sin ningún camino de resolución, ni automático ni de revisión, indefinidamente. `disputed`+`createCorrelationCase` da lo mismo de seguro PERO además abre un caso de trabajo visible en la UI de MidPoint para que alguien lo revise. Si se quisiera lo más conservador posible como paso intermedio, esta opción C podría usarse como "modo pánico" (ver §6), pero no es el diseño recomendado. |

### 2.2 Diseño exacto

**Idea:** dos correladores `items` combinados implícitamente en un correlator compuesto (en
MidPoint 4.9+, declarar 2+ correladores dentro de `<correlators>` con `<composition>` en cada uno
YA forma un compuesto — no hace falta un wrapper `<composite>` explícito para el caso "correladores
a nivel raíz").

- **Tier 1** (sin cambio de comportamiento): `lambDocNum`, peso `1.0`. Si matchea exactamente 1
  candidato, confianza = 1.0 = umbral `definite` → vinculación automática, igual que hoy. Los
  procesamiento de tiers se detiene aquí si hay un match `definite` — **tier 2 nunca se evalúa
  para los shadows que ya matchean por tier 1** (los ~5.474/5.573 ya `LINKED` de la población
  afectada, más cualquier alta futura cuyo documento no haya cambiado de prioridad).
- **Tier 2** (nuevo): `personalNumber` (= `CANON_KEY` = `COD_APS`, escrito **strong** por el
  propio inbound `cod-aps-to-personalNumber` de este resource, **estable** independientemente de
  qué fila de documento gane el dedup `CANON_RN` — a diferencia de `lambDocNum`). Peso `0.6`.
  Si tier 1 no encontró nada pero tier 2 sí, la confianza agregada es `0.6` — cae en la banda
  `candidate` (`>= 0.5`, `< 1.0` definite) → situación `disputed`, NO `unmatched`.
- **Umbrales:** `definite=1.0`, `candidate=0.5`.

```xml
<correlation>
    <correlators>
        <items>
            <name>correlate-by-num-documento</name>
            <item>
                <ref xmlns:upeu="urn:upeu:midpoint:local">extension/upeu:lambDocNum</ref>
            </item>
            <composition>
                <tier>1</tier>
                <weight>1.0</weight>
            </composition>
        </items>
        <items>
            <name>correlate-by-personalnumber-fallback</name>
            <documentation>
                GUARDARRAIL 2026-07-20 (post-incidente CANON_RN, ver
                docs/specs/trabajadores-correlation-guardrail-2026-07-20.md). Tier 2, peso 0.6:
                si el tier 1 (lambDocNum) no encuentra match pero SÍ existe un User cuyo
                personalNumber ya coincide con el CANON_KEY de este shadow (mismo COD_APS,
                anclado antes por este mismo resource o heredado de Estudiantes/Egresados),
                la confianza agregada (0.6) cae en banda "candidate" (menor al "definite"=1.0
                de tier 1) -> situation=disputed -> createCorrelationCase (revisión humana) EN
                VEZ de unmatched->addFocus (que crea un User duplicado real, patrón Orlando/
                Luzirene 20-jul). Si tier 1 ya encontró match definite, este tier 2 NUNCA se
                evalúa (los tiers se procesan en orden y se detienen en el primer match
                definite) -> cero cambio de comportamiento para los shadows ya LINKED.
                LIMITACIÓN CONOCIDA: personalNumber puede tener drift de formato (ceros a la
                izquierda) respecto al CANON_KEY actual si fue anclado hace tiempo bajo una
                convención de padding distinta (caso real: Luzirene, personalNumber="00614192"
                vs CANON_KEY actual "000614192" -- NO coincide, este tier2 NO la habría
                atrapado). Ver §4 del spec para el detalle y la mitigación propuesta a futuro.
            </documentation>
            <item>
                <ref>personalNumber</ref>
            </item>
            <composition>
                <tier>2</tier>
                <weight>0.6</weight>
            </composition>
        </items>
    </correlators>
    <thresholds>
        <definite>1.0</definite>
        <candidate>0.5</candidate>
    </thresholds>
</correlation>
```

**Reacción nueva** (agregar en `<synchronization>`, después de `unmatched`, antes de `deleted`,
mismo patrón ya probado en `koha-ils.xml`):

```xml
<reaction>
    <!-- GUARDARRAIL 2026-07-20: disputed = tier2 (personalNumber) encontró candidato pero tier1
         (lambDocNum) no -> confianza "candidate", no "definite". No se auto-vincula (podría NO
         ser la misma persona: ver hallazgo Orlando/Luzirene, MOISES tiene ID_PERSONA duplicado
         para el mismo COD_APS) ni se crea un User nuevo (riesgo de duplicado real, incidente de
         hoy) -- se abre un caso de correlación para revisión humana. Mismo patrón ya en
         producción: koha-ils.xml reaction disputed -> createCorrelationCase. -->
    <situation>disputed</situation>
    <actions>
        <createCorrelationCase/>
    </actions>
</reaction>
```

**Cambio adicional necesario** — el mapping `cod-aps-to-personalNumber` (atributo `ri:COD_APS`,
hoy sin `evaluationPhases`) necesita evaluarse también en fase `beforeCorrelation` para que el
correlator de tier 2 pueda leer el valor en el momento de correlar (mismo patrón ya usado y
probado para `num-documento-to-lambDocNum` en este mismo resource, y en `estudiantes.xml`/
`egresados.xml`):

```xml
<inbound>
    <name>cod-aps-to-personalNumber</name>
    <strength>strong</strength>
    <source><path>$shadow/attributes/icfs:name</path></source>
    <target><path>personalNumber</path></target>
    <evaluationPhases>
        <include>beforeCorrelation</include>
        <include>clockwork</include>
    </evaluationPhases>
</inbound>
```

(Ver nota en el propio `trabajadores.xml`, líneas 980-985: "El shorthand en 4.10 no resuelve el
focus item cuando los únicos inbounds con `beforeCorrelation` están en `lifecycleState archived`"
— la razón por la que el correlator de `lambDocNum` ya tuvo que hacerse explícito. Aplica el
mismo razonamiento a `personalNumber`.)

### 2.3 Por qué esto NO cambia nada para los ya-`LINKED`

`linked` es una propiedad del **shadow** (tiene `linkRef` a un `User`), no algo que se
recalcule en cada sync. La correlación (y por tanto el correlator compuesto nuevo) **solo se
evalúa quÉ shadow no tiene ya un link** (situaciones `unmatched`/`unlinked`/`disputed`). Para los
5.474/5.573 shadows ya `LINKED` de la población afectada por el fix de hoy, la reacción
`linked → synchronize` corre el inbound normal (que corrige `lambDocNum` al valor correcto
silenciosamente) **sin pasar nunca por el correlator**. Cero riesgo de regresión ahí.

---

## 3. Medición de impacto (ANTES de aplicar nada, 100% contra datos reales)

Metodología: se ejecutó el `baseQuery` REAL y desplegado del `searchScript` de `trabajadores.xml`
contra Oracle (solo lectura) para reconstruir los 5.573 `CANON_KEY` que el fix de hoy colapsó, y
se cruzó contra `m_shadow`/`m_user` de MidPoint (Postgres, solo lectura) en PROD.

| Población | N | Riesgo |
|---|---:|---|
| **Total `CANON_KEY` afectados por el fix `CANON_RN` de hoy** | **5.573** | — |
| Ya `LINKED` (shadow con `linkRef` existente) | 5.474 | **Ninguno** — no pasan por el correlator; `lambDocNum` se autocorrige vía `synchronize` |
| Sin shadow materializado aún (nunca importado) | 2 | **Ninguno** — alta genuinamente nueva, sin nada con qué confundirse |
| **No `LINKED` (expuestos HOY al riesgo `unmatched→addFocus`)** | **97** | Ver desglose |
| ... de los cuales: existe un `User` con `personalNumber` **exactamente** igual al `CANON_KEY` del shadow | **12** | **Este es el universo que el guardarraíl atrapa** — pasarían de "duplicado silencioso" a "caso de correlación para revisión humana" |
| ... de los cuales: ningún `User` existente tiene ese `personalNumber` | **85** | Altas nuevas genuinas probables — el guardarraíl **no las toca**, `addFocus` sigue funcionando igual que hoy |

Desglose de situación actual de los 97 no-linkados: `UNMATCHED`=59, `UNLINKED`=35, sin situación
(huérfanos post-incidente, incl. Orlando/Luzirene)=2, `DISPUTED` preexistente (no relacionado a
este cambio, ya estaba así antes de hoy)=1.

Los 12 casos que el guardarraíl atraparía (verificado 1:1 contra `m_user.personalnumber`):

```
CANON_KEY  | situación shadow | User existente (name)     | lifecycle | lambDocNum existente
-----------+------------------+---------------------------+-----------+---------------------
001261673  | UNMATCHED        | 201521241                 | active    | 01261673
001283770  | UNMATCHED        | 001283770                 | archived  | 01283770
002558245  | DISPUTED (previo)| 002558245                 | archived  | 02558245
00534601   | (huérfano canario)| 200610808 (Orlando)      | active    | CE:000534601
40652594   | UNLINKED         | 40652594                  | archived  | 40652594
42734449   | UNLINKED         | 200210031                 | active    | 42734449
43781634   | UNMATCHED        | 43781634                  | active    | 43781634
44789848   | UNLINKED         | 200510086                 | active    | 44789848
60531448   | UNMATCHED        | 60531448                  | active    | 60531448
71459568   | UNLINKED         | 201420147                 | active    | 71459568
740296882  | UNLINKED         | 740296882                 | active    | 73250330
756061634  | UNLINKED         | 756061634                 | active    | 46559590
```

Nota: en varios de estos casos el `lambDocNum` existente y el `CANON_KEY` actual **no coinciden en
absoluto** en valor (p. ej. `740296882` vs `73250330`) — confirma que no es un simple problema de
formato, sino exactamente el patrón "documento distinto ganó tras el fix", y que **sin** tier 2
estos 12 habrían sido 12 duplicados adicionales en la próxima corrida, no solo los 2 del canario.

---

## 4. Limitación conocida, NO resuelta hoy: drift de padding en `personalNumber`

**Luzirene (`000614192`) es el contraejemplo que prueba que el guardarraíl NO es perfecto.** Su
`User` real (archivado, oid `49945169-9f04-422c-888c-13072a89b62a`) tiene
`personalNumber = "00614192"` (8 dígitos) — el `CANON_KEY` actual del shadow es `"000614192"` (9
dígitos, un cero más). **No coinciden como string.** El correlator de tier 2 (`items`, comparación
exacta) **no la habría atrapado** — para Luzirene específicamente, el resultado seguiría siendo
`unmatched → addFocus`, es decir: **un tercer duplicado si algún día se reintenta su import sin
más cambios.**

Causa probable: `personalNumber` de Luzirene fue anclado en una época en que `COD_APS` no llevaba
el cero adicional (o mediante otra convención de padding), y nunca se recalculó tras un cambio de
formato en Oracle. Este es un problema de **normalización histórica de datos ya materializados en
MidPoint**, no del correlator en sí — ningún correlator `items` (comparación exacta) puede
cerrarlo sin antes normalizar los valores ya guardados.

**No se diseñó ni se aplicó una mitigación para esto hoy** (fuera de alcance dado el tiempo y la
cautela pedida). Recomendación para una sesión futura, en orden de preferencia:

1. **Auditoría + backfill de `personalNumber`** para todos los `User` con afiliación laboral
   histórica: recalcular `personalNumber` desde el `CANON_KEY` actual de su shadow Trabajadores
   linkado (si existe) y sobreescribir el valor con padding desactualizado. Una vez normalizado,
   el tier 2 tal como está diseñado cubriría también estos casos.
2. Alternativa más compleja (no recomendada como primera opción): correlator `filter` con
   expresión que normalice (`LTRIM` de ceros) el valor a comparar — pero esto solo normaliza el
   lado del shadow, no el valor YA guardado en `m_user.personalnumber`, así que no cierra la
   brecha sin (1).

---

## 5. Validación realizada hoy (offline, sin tocar PROD)

Instrucción original permitía simular sin tocar producción como primera opción ("si es posible
simular sin tocar producción"). Se optó por esa vía, a escala completa en vez de 2-3 casos
sintéticos:

- **Mecanismo de correlación compuesta + umbrales + reacción `disputed`+`createCorrelationCase`**:
  confirmado como patrón oficial de Evolveum (Correlators / Rule Composition) y como patrón
  **ya en producción** en este mismo repo (`koha-ils.xml`).
- **Simulación completa contra datos reales de producción** (no sintéticos): se recalculó qué
  habría decidido el correlator compuesto propuesto para los **97 shadows realmente expuestos**
  hoy al riesgo (no solo 2-3): 12 habrían caído en `disputed` (correctamente retenidos), 85
  habrían seguido su curso normal como altas nuevas. **Cero escritura** en Oracle o MidPoint
  durante esta validación — 100% lectura (`GET`/`SELECT`).
- **Caso Orlando validado individualmente end-to-end**: `personalNumber` de su `User` real
  (`00534601`) coincide EXACTO con el `CANON_KEY` actual de su shadow huérfano (`0c1660ee-...`).
  Con el guardarraíl aplicado, un import dirigido de ese shadow produciría `disputed` +
  `createCorrelationCase`, NO un `User` nuevo.
- **Caso Luzirene validado como contraejemplo**: confirmado que el guardarraíl, tal como está
  diseñado, **no la protege** (drift de padding, §4). Se documenta honestamente en vez de omitirlo.

**No se ejecutó ningún canario EN VIVO contra PROD en esta sesión** (ni el PATCH del resource, ni
un import dirigido sobre el shadow de Orlando). Se decidió así deliberadamente — ver §6.

---

## 5b. Aplicación real en PROD y validación en vivo (2026-07-26)

Alberto autorizó aplicar el diseño. Ejecutado con el protocolo de siempre: backup completo
(`GET /resources/{oid}` → `/home/juansanchez/backups-e21/e21_pre-correlation-guardrail_20260726_033546.xml`,
version 321), `PATCH` (nunca `PUT`) de los 3 elementos exactos del diseño (§2.2), verificación
post-PATCH, y un intento de canario en vivo sobre el shadow de Orlando que **reveló un incidente
crítico no documentado, independiente del guardarraíl mismo**.

### 5b.1 PATCH aplicado y verificado — ✅ limpio

`version` 321→322. Los 3 `itemDelta` (XML, `objectModification`) aplicados en una sola llamada:

1. `replace` de `schemaHandling/objectType[5464]/correlation` → correlator compuesto 2-tier
   (`correlate-by-num-documento` tier=1/weight=1.0, `correlate-by-personalnumber-fallback`
   tier=2/weight=0.6) + `thresholds` (`definite=1.0`, `candidate=0.5`), exactamente como en §2.2.
2. `add` de una nueva `reaction` (`situation=disputed`, `actions/createCorrelationCase`) en
   `schemaHandling/objectType[5464]/synchronization`, sin tocar las 4 reacciones existentes
   (`linked`/`unlinked`/`unmatched`/`deleted`, mismos `@id` 5530/5532/5534/5536 preservados).
3. `replace` de `schemaHandling/objectType[5464]/attribute[5465]/inbound[5467]/evaluationPhases`
   (mapping `cod-aps-to-personalNumber`) → `include: [beforeCorrelation, clockwork]`.

Verificación post-PATCH (todo confirmado vía REST GET + comparación JSON, no asumido):

- `<schema>` cacheado **byte-idéntico** al pre-PATCH (comparación JSON completa, no solo conteo de
  `xsd:element`).
- `connectorRef`, `capabilities`, `connectorConfiguration` **idénticos** al pre-PATCH.
- `correlation`, `synchronization/reaction` (ahora 5, con `disputed`/`createCorrelationCase`) e
  `inbound[5467]/evaluationPhases` reflejan exactamente el diseño.
- **Test connection: 15/15 sub-resultados `success`.**

### 5b.2 Canario de Orlando — NO se pudo ejecutar como estaba diseñado (premisa invalidada)

Antes de lanzar el `import` dirigido sobre el shadow `0c1660ee-b79f-48c3-abc8-5c852ad8226c`, se
verificó su estado real en PROD (protocolo de esta sesión: nunca asumir, siempre consultar el
sistema real primero). **El shadow YA NO está huérfano**: `synchronizationSituation=LINKED`,
vinculado a un `User` (`3e756b31-...`, `name=00534601`, `personalNumber=00534601`,
`lambIdPersona=202895`) que es un **`User` duplicado nuevo**, distinto del Orlando real
(`2dba749b-...`, `name=200610808`, `lambDocNum=CE:000534601`, `lambIdPersona=10041`, verificado
intacto). Es decir: **exactamente el mismo patrón de incidente del 20-jul volvió a ocurrir para
Orlando**, esta vez fuera de esta sesión.

Con la premisa del canario rota (el shadow ya no está en el estado `UNMATCHED`/huérfano que el
guardarraíl debía interceptar), **se decidió NO ejecutar el `import` dirigido** — habría sido, en
el mejor caso, un no-op (`linked → synchronize`, sin pasar por el correlator) y no habría validado
nada; en el peor caso, una operación sobre un objeto cuyo estado real no coincidía con lo esperado,
justo el escenario que exige detenerse según las reglas invariantes de esta tarea.

### 5b.3 Causa raíz de la desviación — incidente crítico no documentado (2026-07-25)

Investigación (100% lectura, `psql` + REST) de por qué el shadow de Orlando cambió de estado desde
el 20-jul:

**`recon-oracle-lamb-trabajadores-daily` (oid `23b9fde4-...`) fue reanudada y ejecutada
manualmente el 2026-07-25, sin que quede registro de autorización explícita para hacerlo.**
Evidencia de auditoría (`ma_audit_event`, `targetoid` del task):

```
2026-07-20 14:33:59 UTC  SUSPEND_TASK        administrator  (el cierre documentado del 20-jul)
2026-07-25 14:18:37 UTC  RESUME_TASK         administrator  ← sin documentar en memoria/runbooks
2026-07-25 14:18:40 UTC  RUN_TASK_IMMEDIATELY administrator
```

La ejecución corrió de **09:18:40 a 09:40:12 (hora servidor, -05:00)**. Coincide, al segundo, con
la creación de shadows Koha/LDAP reales para los casos abajo (`createtimestamp` 09:19:02–09:19:08
-05:00). El diff sin commitear encontrado al inicio de esta sesión en
`upeu/resources/oracle-lamb/trabajadores.xml` (fix `CIA` fechado 2026-07-25, sobre el mapping
`sede-nombre-to-campusWorker`, ver `git diff` de esa fecha) sitúa una sesión de trabajo sobre este
mismo resource ese mismo día — es la hipótesis más probable del origen de la reanudación
(reanudar la tarea para validar el fix CIA, sin registrar ni prever que correría la reconciliación
completa del resource, no solo el alcance acotado de 2 personas que ese fix documentaba).

**Impacto medido de esa corrida (100% lectura, sin escrituras adicionales de esta sesión):**

| Métrica | Valor |
|---|---|
| `User` nuevos creados en la ventana 09:15–09:50 -05:00 | **97** |
| ...de los cuales, duplicados exactos por `personalNumber` (mismo valor que un `User` más antiguo) | **2** (`001261673`/Juan Elías Mejía Coello, `00534601`/Orlando) |
| ...de los cuales, duplicados por `fullName` exacto no capturados por el join anterior | **2 más**: `000614192`/Luzirene (recurrencia del caso ya conocido, §4 — `archived`, sin downstream) y **`001642451`/Evanilda Ruth Valeriano Tiñini (caso NUEVO, no identificado antes: en el Grupo B del 20-jul se había clasificado como "alta nueva genuina" — en realidad ya tenía un `User` con el mismo nombre bajo otro identificador, `201520024`)** |
| Duplicados **activos y aprovisionados a sistemas reales** | **3 de 4**: Orlando → LDAP + Koha; Evanilda → LDAP + Koha; Juan Elías → LDAP (no Koha) |
| Duplicado sin impacto downstream | Luzirene (`archived`, el guardarraíl `FEC_TERMINO` preexistente correctamente no la materializó hacia ningún resource) |
| Balance agregado del resource (comparado con el cierre del 20-jul) | `UNMATCHED` 90→**2**, `UNLINKED` ~42→**0**, `LINKED` 7.399→**7.368**, total 7.532→**7.371** — consistente con que la corrida procesó legítimamente la gran mayoría del backlog (altas/bajas reales de 5 días), y solo estos 3-4 casos degeneraron en duplicado |

Esta auditoría (`personalNumber` exacto + `fullName` exacto) **no es exhaustiva** — es la misma
metodología de bajo costo usada para medir el impacto original del 20-jul, no un barrido
case-by-case de los 97. Puede haber más colisiones no capturadas por estos dos criterios (nombres
con variantes, apellidos de casada, etc.).

**Acción de protección tomada de inmediato, dentro del alcance de "detente y no dañes más":**
`recon-oracle-lamb-trabajadores-daily` tenía su próximo disparo programado (`cron 0 0 6 * * ?`,
hora servidor) a menos de 2h15min del hallazgo. Se **re-suspendió la tarea** (`POST
/tasks/{oid}/suspend` → 204, verificado `executionState=suspended` / `schedulingState=suspended`)
para evitar que corriera de nuevo antes de que Alberto pueda decidir. Es la restauración del
**último estado explícitamente autorizado** (suspendida, decisión del 20-jul), no una escalación de
alcance — mismo principio que motivó la suspensión original.

**No se tocó ningún dato de los 4 duplicados** (Orlando/Juan Elías/Evanilda/Luzirene) ni sus
shadows downstream en esta sesión — la remediación (borrar duplicados, verificar contra LDAP/Koha
reales, restaurar el guardarraíl de `delete` temporalmente como en el 20-jul) requiere el mismo
protocolo cuidadoso caso-por-caso de esa sesión y una decisión explícita de Alberto, no una
extensión unilateral del alcance de hoy.

Nota importante para la lectura de este spec: el guardarraíl ya aplicado **sí habría evitado 2 de
los 4 duplicados** de esta corrida — Orlando y Juan Elías, ambos con `personalNumber` **exacto**
coincidente entre el `User` nuevo y el viejo (tier 2 los habría atrapado) — **si hubiera estado
desplegado ANTES del 25-jul**. Verificado que **NO** habría atrapado a Evanilda: su `User` nuevo
(`personalNumber=001642451`, el `COD_APS` de trabajador) y su `User` viejo
(`personalNumber=201520024`, un código con pinta de matrícula estudiantil/alumni antiguo) tienen
`personalNumber` **distinto** — es la misma persona física bajo dos identificadores UPeU distintos
de dos afiliaciones distintas (worker vs. student/alumni), un problema de identidad más profundo
(fuera del alcance de un correlator de un solo resource) que ya está señalado como tema abierto en
`docs/specs/multi-profile-canonical/07-identity-lifecycle-design.md`. Luzirene tampoco habría sido
atrapada (drift de padding, §4, limitación ya conocida). Como el guardarraíl se aplicó hoy (26-jul),
después del hecho, no puede deshacer los duplicados ya creados — solo previene que el mismo patrón
(tier 1 sin match + tier 2 con match exacto) se repita en la próxima corrida, una vez que Alberto
decida reactivar la tarea.

---

## 6. Recomendación y próximo paso — actualizado 2026-07-26 tras la aplicación real

**Estado real al cierre de esta sesión (2026-07-26):**

- El guardarraíl (correlator compuesto 2-tier + reacción `disputed` + `evaluationPhases`) está
  **aplicado y verificado en PROD**, `trabajadores.xml` version **322**. Ver §5b.1.
- El canario de Orlando **no se pudo ejecutar como estaba diseñado**: al verificar el estado real
  del shadow antes de tocar nada, se encontró que ya no está huérfano — fue absorbido por un
  incidente distinto y no documentado (§5b.3).
- Se descubrió y confirmó, con evidencia de auditoría, que **`recon-oracle-lamb-trabajadores-daily`
  fue reanudada y ejecutada manualmente el 2026-07-25** (sin decisión explícita registrada),
  recreando el patrón exacto del incidente del 20-jul para **4 personas** (Orlando, Juan Elías
  Mejía Coello, Evanilda Ruth Valeriano Tiñini, Luzirene), **3 de ellas ya provisionadas a LDAP
  y/o Koha reales**, sin remediar.
- Acción de protección ya ejecutada: la tarea fue **re-suspendida** antes de su próximo disparo
  programado (~2h15min de margen). `executionState=suspended` verificado.
- **No se tocaron los 4 duplicados ni sus shadows downstream** — la remediación queda pendiente,
  requiere el mismo protocolo caso-por-caso del 20-jul y decisión explícita de Alberto.
- El hallazgo original de `ID_PERSONA` duplicado en MOISES (Orlando/Luzirene, §1) sigue sin
  escalar a DBAs — pendiente, ver punto 2 de la lista de abajo.

**Por qué NO se ejecutó ningún canario de reemplazo hoy (ni un segundo canario sobre los otros 10
casos del bucket "atrapables"):** las reglas invariantes de esta tarea exigen detenerse y reportar
ante cualquier desviación de lo esperado, **antes de escalar a cualquier otra acción**. El cambio
de estado del shadow de Orlando (de huérfano a vinculado-a-duplicado) es exactamente esa
desviación. Confirmado por lectura (no se ejecutó ningún `import`/`reconcile` adicional en esta
sesión) que los **otros 10 de los 12 casos "atrapables" originales siguen intactos** (1 `User` cada
uno, sin duplicar) — son candidatos viables para una validación futura, una vez que Alberto decida
cómo proceder con los 4 duplicados ya existentes y con la reactivación de la tarea.

**Próximos pasos recomendados, en orden:**

1. **Remediar los 3 duplicados activos aprovisionados** (Orlando, Juan Elías, Evanilda) con el
   mismo protocolo gobernado del 20-jul: backup → habilitar temporalmente el guardarraíl de
   `delete` en LDAP/Koha → `DELETE` de los shadows downstream huérfanos → `DELETE` de los `User`
   duplicados → revertir el guardarraíl de `delete` a `false` → verificar con `ldapsearch`/`mysql`
   reales (no solo MidPoint) que los usuarios reales (Orlando `200610808`, etc.) quedaron intactos.
   Luzirene (`archived`, sin downstream) puede esperar o resolverse en la misma pasada.
2. **Investigar y cerrar el proceso**, no solo el dato: entender por qué se reanudó la tarea el
   25-jul sin dejar registro en memoria/runbooks (hipótesis más probable: sesión del fix `CIA` ese
   mismo día sobre este mismo resource, ver §5b.3) y decidir si hace falta un guardarraíl de
   proceso (p. ej. una nota más visible en el propio task, o una alerta Telegram al reanudar tareas
   suspendidas por incidente) para que esto no vuelva a pasar silenciosamente.
3. Escalar a DBAs el hallazgo de `ID_PERSONA` duplicado en MOISES para Orlando (`10041`/`202895`)
   y Luzirene (`11173`/`192480`) — mismo canal que `05436990`/Ariana. Ver Anexo E de
   `docs/governance/matriz-fuentes-oracle-lamb.md`. Con el hallazgo de Evanilda (§5b.3), este
   patrón (mismo nombre, distintos `ID_PERSONA`/identificador UPeU) parece más frecuente de lo que
   se pensaba — vale la pena ampliar el barrido más allá de los 2 casos originales.
4. **Una vez remediados los duplicados**, ejecutar el canario que esta sesión no pudo completar,
   sobre uno de los **10 casos aún intactos** (p. ej. `40652594` o `71459568`, ver tabla en §3) o
   sobre Orlando/Juan Elías si se opta por re-orfanar sus shadows en vez de fusionar los `User`:
   `import` dirigido, verificar `disputed`+`createCorrelationCase` (no `addFocus`), 0 `User`
   nuevos.
5. Solo después de (1)-(4), evaluar el backfill de `personalNumber` (§4, drift de padding — no
   habría atrapado a Luzirene ni a Evanilda) y, por separado, la reactivación explícita y
   **documentada** (con decisión de Alberto registrada, a diferencia de la reanudación del 25-jul)
   de `recon-oracle-lamb-trabajadores-daily`.

---

## 7. Archivos y referencias

- Resource: `upeu/resources/oracle-lamb/trabajadores.xml` (oid `6a91f7e1-...-0e21`, PROD **version
  322** al cierre de esta sesión — guardarraíl de correlación §2.2 **aplicado**).
- Backup pre-PATCH: `/home/juansanchez/backups-e21/e21_pre-correlation-guardrail_20260726_033546.xml`
  (PROD, version 321).
- Precedente del patrón `disputed`+`createCorrelationCase`: `upeu/resources/koha-ils.xml` líneas
  ~1915-1919.
- Incidente de origen (20-jul): `docs/runbooks/telegram-alertas-tasks-2026-07-20/tarea3-resultado-200610808-91-personas.md`.
- Incidente nuevo (25-jul, descubierto 26-jul): ver runbook
  `docs/runbooks/trabajadores-incidente-reanudacion-25jul-2026-07-26.md`.
- Gobernanza: `docs/governance/matriz-fuentes-oracle-lamb.md` Anexo B punto 5 (fix `CANON_RN`) y
  Anexo E (duplicado de persona MOISES Orlando/Luzirene).
- Doctrina de despliegue: `docs/runbooks/NUNCA-PUT-resources-schema-cache.md`.
- Identidad multi-perfil (persona con más de un identificador UPeU por afiliación distinta, caso
  Evanilda): `docs/specs/multi-profile-canonical/07-identity-lifecycle-design.md`.
