# Guardarraíl de correlación — Oracle LAMB Trabajadores v3 (diseño, 2026-07-20)

**Estado: DISEÑADO Y VALIDADO OFFLINE. NO APLICADO A PROD.** `recon-oracle-lamb-trabajadores-daily`
sigue **suspendida**. Este documento es el entregable de una sesión de diseño explícitamente
autorizada por Alberto tras el incidente de duplicados del 20-jul (ver
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

## 6. Recomendación y próximo paso

**No se aplicó nada a PROD en esta sesión.** `trabajadores.xml` en PROD queda exactamente como
quedó tras el fix `CANON_RN` de esta tarde (version 320). `recon-oracle-lamb-trabajadores-daily`
sigue **suspendida**.

Razones para no aplicar hoy, explícitas:

1. Ya hubo un incidente real hoy en este mismo resource (2 duplicados provisionados a LDAP/Koha
   real). Encadenar un segundo cambio en vivo sobre el mismo resource, en la misma sesión
   maratónica, no es prudente aunque el diseño tenga buena base.
2. La validación offline reveló una limitación real y no trivial (drift de padding en
   `personalNumber`, §4) que sugiere que el diseño, aunque sólido, **no es la versión final** —
   conviene decidir con margen si vale la pena cerrar esa brecha (backfill) antes o después de
   desplegar el guardarraíl.
3. El hallazgo de duplicado de persona en MOISES para Orlando Y Luzirene (§1) es información nueva
   que Alberto no tenía y que amerita su propia decisión de escalamiento, independiente del
   guardarraíl técnico.

**Próximos pasos recomendados, en orden:**

1. Alberto revisa este diseño con margen (no en una sesión ya larga).
2. Escalar a DBAs el hallazgo de `ID_PERSONA` duplicado en MOISES para Orlando (`10041`/`202895`)
   y Luzirene (`11173`/`192480`) — mismo canal que `05436990`/Ariana. Ver Anexo E de
   `docs/governance/matriz-fuentes-oracle-lamb.md` (agregado en este commit).
3. Si Alberto autoriza aplicar: `PATCH` (nunca `PUT`) de los 3 elementos (`correlation`,
   `synchronization/reaction` nueva, `evaluationPhases` de `cod-aps-to-personalNumber`), con
   backup previo y verificación post-PATCH (`<schema>` intacto, test connection 15/15,
   `schemaHandling`/`capabilities`/`connectorRef` intactos) — mismo protocolo ya usado hoy.
4. Primer test en vivo: **un solo** import dirigido (`POST /shadows/{oid}/import`) sobre el shadow
   ya huérfano y conocido de Orlando (`0c1660ee-b79f-48c3-abc8-5c852ad8226c`) — bajo riesgo
   (shadow ya aislado, sin `linkRef`, resultado esperado conocido: `disputed`, no `addFocus`).
   Verificar con `psql`/REST (no solo el código HTTP) que NO se creó ningún `User` nuevo y que SÍ
   se creó un caso de correlación.
5. Si sale limpio, considerar (no ejecutar automáticamente) un barrido dirigido sobre el resto de
   los 96 casos restantes (11 más del bucket "atrapados" + los 85 "altas nuevas", estos últimos
   ya cubiertos por el ciclo nocturno una vez reactivado).
6. Solo después de (3)-(5) validados, evaluar backfill de `personalNumber` (§4) y, por separado,
   la reactivación de `recon-oracle-lamb-trabajadores-daily` — decisión explícita de Alberto, no
   automática.

---

## 7. Archivos y referencias

- Resource: `upeu/resources/oracle-lamb/trabajadores.xml` (oid `6a91f7e1-...-0e21`, PROD version
  320 al cierre de esta sesión — **sin cambios de este spec aplicados**).
- Precedente del patrón `disputed`+`createCorrelationCase`: `upeu/resources/koha-ils.xml` líneas
  ~1915-1919.
- Incidente de origen: `docs/runbooks/telegram-alertas-tasks-2026-07-20/tarea3-resultado-200610808-91-personas.md`.
- Gobernanza: `docs/governance/matriz-fuentes-oracle-lamb.md` Anexo B punto 5 (fix `CANON_RN`) y
  Anexo E (nuevo, duplicado de persona MOISES Orlando/Luzirene).
- Doctrina de despliegue: `docs/runbooks/NUNCA-PUT-resources-schema-cache.md`.
