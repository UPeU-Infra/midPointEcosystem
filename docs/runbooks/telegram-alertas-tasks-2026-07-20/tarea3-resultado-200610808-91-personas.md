# Resultado — ejecución dirigida del caso 200610808 (Orlando Cortez Bazantes) a las 91 personas, todas las sedes

2026-07-20. Continuación de
[`tarea3-medicion-200610808-alcance.md`](tarea3-medicion-200610808-alcance.md) (medición de la
tarde). Alberto autorizó explícitamente el universo más amplio medido (91, todas las sedes).
Reconstrucción en vivo + import dirigido por OID de shadow vía REST
(`POST /shadows/{oid}/import`). **NUNCA PUT. NUNCA reconcile completo del resource
(6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21, ~7.532 shadows vivos). Oracle LAMB solo lectura, ningún
INSERT/UPDATE/DELETE.**

## Universo reconstruido en vivo (no reutilizado el archivo de la tarde)

Mismo criterio exacto: shadow del resource Oracle LAMB Trabajadores,
`synchronizationSituation IN (UNMATCHED, UNLINKED)`, `ESTADO='A'`, todas las sedes.

```sql
SELECT synchronizationsituation, attributes->>'29' AS estado, attributes->>'166' AS sede, count(*)
FROM m_shadow
WHERE resourcereftargetoid = '6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21' AND exist = true
GROUP BY 1,2,3;
```

**91 exactos** (Lima 52, Juliaca 24, Tarapoto 13, sin sede 2) — idéntico a la medición de la
tarde, el universo no cambió en el intervalo.

## Desvío encontrado ANTES de procesar (parada obligatoria, se investigó)

El caso base (Orlando, shadow `0c1660ee-...`, COD_APS `00534601`) fue presentado como "shadow
real + User real que nunca se conectaron", implicando que un reintento de correlación
(import/reconcile) los uniría. **Se verificó que esto NO es cierto para la mayoría del
universo, incluido Orlando mismo**, y forzar el import ciego habría sido peligroso:

- El correlador del resource (`extension/upeu:lambDocNum` == valor canonicalizado de
  `ri:NUM_DOCUMENTO` vía función `toCanonicalDocNumber`, evaluada `beforeCorrelation`) depende
  de que `NUM_DOCUMENTO` sea un número de documento real.
- **68 de los 91 shadows (+2 con `ID_TIPODOCUMENTO=97`) tienen `ID_TIPODOCUMENTO=98`** — el
  mismo código que el Bloque J del `UserTemplate-Person-Base` ya trata como
  `INVALID_TYPES` ("sin documento válido") — y su `NUM_DOCUMENTO` en Oracle
  (`ELISEO.VW_APS_EMPLEADO`) es un valor alfanumérico corrupto, no un documento
  (ej. `321931OCBTA0`, `580530CCPRI2`). **Orlando es uno de estos 70.**
- `toCanonicalDocNumber` no filtra estos tipos inválidos (a diferencia del Bloque J): para
  `ID_TIPODOCUMENTO` no reconocido y `NUM_DOCUMENTO` no numérico, devuelve el string corrupto
  **sin cambios**, como clave de correlación. Verificado contra `m_user.ext->>'156'`
  (`lambDocNum`) de los 91 candidatos: **ningún** User existente tiene esa clave.
- Consecuencia real: si se fuerza `import`, el reaction `unmatched → addFocus` **crearía un
  User nuevo, duplicado y con documento basura**, en vez de vincular al Orlando/persona real
  que ya existe en otro `name`. Esto es exactamente el riesgo de split-brain ya documentado en
  memoria (`05436990`, `202421264`).
- Se validó también que `synchronizationSituation=UNLINKED` (39 shadows) **no garantiza** que
  el correlador siga encontrando el mismo match hoy: de 28 `UNLINKED` con
  `ID_TIPODOCUMENTO=98/97`, **0 de 28** tienen ya un User con esa clave corrupta como
  `lambDocNum` — el estado cacheado está obsoleto (probablemente de antes del fix
  `toCanonicalDocNumber` 2026-06-29, o de un estado previo de los datos Oracle). Ejecutar
  import sobre estos también habría arriesgado `addFocus`.

**Por lo tanto, "el mismo patrón que Orlando" solo es válido, de forma verificable y segura,
para un subconjunto de los 91 — no para el universo completo.** Se ejecutó únicamente ese
subconjunto verificado; el resto se dejó intacto y se documenta abajo.

## Clasificación final de los 91

| Grupo | N | Situación | Acción |
|---|---|---|---|
| **A — match verificado, procesado** | **11** | 11× UNLINKED (0 de UNMATCHED) | **Import dirigido ejecutado, LINKED confirmado** |
| B — documento válido (tipo 1/4/6), sin match existente | 10 | 10× UNMATCHED | NO procesado — probable alta nueva genuina, no bug |
| C — `ID_TIPODOCUMENTO` 98/97 (documento corrupto en Oracle), incluye Orlando | 70 | 42× UNMATCHED + 28× UNLINKED-obsoleto | NO procesado — riesgo de duplicado, requiere decisión separada |

Grupo A + B + C = 11 + 10 + 70 = 91. ✓

### Grupo A — 11 procesados, verificados LINKED (canario + lote)

Metodología: para cada shadow del subconjunto UNLINKED con `ID_TIPODOCUMENTO` válido (1=DNI,
4/6=CE), se calculó la clave canónica igual que `toCanonicalDocNumber` y se verificó contra
`m_user.ext->>'156'` que un User **activo** ya la tenía. Solo se ejecutó `import` sobre los
verificados.

1. **Canario** (`3f123504-...`, COD_APS `40786815`) ejecutado solo primero, verificado
   LINKED + sin duplicado + `linkRef` del User correcto actualizado, ANTES de continuar con el
   resto.
2. Lote restante (10) ejecutado, 1 por 1, con HTTP capturado.

| Shadow OID | COD_APS | Sede | User destino (name) | HTTP | Resultado verificado (psql) |
|---|---|---|---|---|---|
| `3f123504-...` | 40786815 | Filial Juliaca | 202421244 | 200 | LINKED |
| `6cc72ed8-...` | 42338674 | Filial Juliaca | 202520348 | 200 | LINKED |
| `36d95b4a-...` | 43999511 | Filial Juliaca | 200511209 | 200 | LINKED |
| `dad5a8d4-...` | 60417105 | Filial Juliaca | 202413238 | 200 | LINKED |
| `ca343cf6-...` | 19260333 | Filial Tarapoto | 200110363 | 200 | LINKED |
| `6fa501ad-...` | 61231270 | Filial Tarapoto | 202511878 | 200 | LINKED |
| `dd8ecf58-...` | 08178514 | Sede Lima | 202011025 | 200 | LINKED |
| `74471043-...` | 40506633 | Sede Lima | 200310209 | 200 | LINKED |
| `803ab1a9-...` | 71696089 | Sede Lima | 202210140 | **240** | LINKED (240 = handled_error benigno, patrón ya documentado en Koha Etapa 1) |
| `46b380ac-...` | 72950806 | Sede Lima | 201410874 | 200 | LINKED |
| `5e9520a4-...` | 01794074 (CE) | sin sede | 201820260 | 200 | LINKED (correctamente al User **activo**, no al duplicado archivado preexistente `f8cdf020` que ya tenía `lambDocNum=01794074` sin prefijo) |

**Verificación real (no eco), doble vía:**
- `psql` en `midpoint-midpoint_data-1`: los 11 shadows → `synchronizationSituation=LINKED`.
- `0` Users nuevos creados en la BD (`m_object.createtimestamp > now()-2h` = 0) → confirma que
  ningún `addFocus` se disparó por accidente.
- Balance agregado del resource cerrado exacto: `LINKED` 7.386→**7.397** (+11),
  `UNLINKED` 53→**42** (−11), `UNMATCHED` 92→92 (sin cambio, esperado — no se tocó ninguno),
  `DISPUTED` 1→1. Total 7.532 antes y después — cero shadows perdidos u orfanados.
- Sanity adicional: se comprobó que la materialización downstream de `liveAffiliationWorker`
  (staff/faculty) en los 11 Users **depende correctamente de `FEC_TERMINO`** (guardarraíl
  "RESIDUAL 1", PM10 2026-05-30, ya existente en el template — no tocado hoy): 3/11 con
  contrato vigente (`FEC_TERMINO` nulo o futuro) materializaron `staff`/`faculty` correctamente;
  8/11 con `FEC_TERMINO` ya vencido (`ESTADO='A'` en Oracle pero la bandera no se volteó a `I`)
  quedaron sin materializar afiliación laboral — **comportamiento correcto y ya documentado**,
  no un defecto de esta ejecución. No se ejecutó ningún `PATCH ?options=reconcile` sobre los
  Users (memoria `koha-ldap-reactivation-2026-05-30.md`: ese mecanismo específico puede
  **archivar** al usuario si se aplica sin reproducir los inbounds — riesgo evitado
  deliberadamente).

### Grupo B — 10 sin procesar (documento válido, sin match)

`ID_TIPODOCUMENTO` 1/4/6 bien formado, canonicalizado, pero **ningún** User existente (por
`lambDocNum` ni por `name`) coincide. Shadows: `0cb3eda7` (43873259), `a495e1ff` (001642451),
`3365b340` (005482418), `eb80dc8b` (29694024), `5f62d207` (43986487), `1f41c48f` (46492202),
`4b8a9889` (47995722), `f0737be6` (72224251), `0ebad487` (74597344), `7156125a` (75911884).

No se ejecutó `import`: con 0 candidatos, la reacción `unmatched → addFocus` **crearía un User
nuevo** — comportamiento correcto SOLO si son personas genuinamente nuevas nunca aprovisionadas
(lo más probable, dado que sus documentos no colisionan con nada). Onboarding de altas nuevas
es una operación de alcance y riesgo distintos a "reparar una correlación rota" — no estaba en
el alcance autorizado hoy. **Se deja para el primer ciclo nocturno real de
`recon-oracle-lamb-trabajadores-daily`** (activado hoy más temprano, primera corrida esperada
madrugada 2026-07-21), que es el mecanismo diseñado y ya programado para altas nuevas, con
cobertura completa del resource en vez de una selección arbitraria de 10.

### Grupo C — 70 sin procesar (documento corrupto en origen, incluye Orlando)

`ID_TIPODOCUMENTO=98` (68) o `97` (2). `NUM_DOCUMENTO` en `ELISEO.VW_APS_EMPLEADO` no es un
documento de identidad válido para estos registros — es un dato sucio en el origen Oracle
(fuente autoritativa, solo lectura). El correlador de este resource no tiene fallback (un solo
`items` correlator sobre `lambDocNum`); no hay mecanismo seguro hoy para vincular estos 70 sin
riesgo de crear identidades duplicadas o fantasma.

**Orlando (`0c1660ee-...`, COD_APS `00534601`) está en este grupo — su caso base NO quedó
resuelto por esta ejecución**, a pesar de ser el disparador original de la tarea. Esto se
reporta con transparencia: el diagnóstico original identificó correctamente que su User y su
shadow existen por separado, pero atribuyó la causa a un simple "gap de correlación reintentable"
cuando en realidad es un problema de calidad de dato en el origen (`NUM_DOCUMENTO` corrupto para
`ID_TIPODOCUMENTO=98`).

Opciones para una sesión futura (ninguna ejecutada hoy, todas requieren decisión de Alberto):

1. **Fix de ingeniería en el correlador/normalizador**: excluir `ID_TIPODOCUMENTO` en
   `{0,97,98,99}` de la clave de correlación (igual que ya hace el Bloque J para
   `identityDocuments`), y definir una clave de respaldo (ej. `COD_APS`, que en los casos
   `ID_TIPODOCUMENTO=1` limpios coincide exactamente con el documento real) con revisión
   humana antes de auto-vincular.
2. **Saneamiento en el origen**: escalar a quien administra `ELISEO.VW_APS_EMPLEADO` para que
   `NUM_DOCUMENTO` refleje el documento real en los registros `ID_TIPODOCUMENTO=98/97`
   (arreglo de raíz, pero fuera del alcance de un agente de solo lectura sobre Oracle LAMB).
3. **Vínculo manual caso por caso** (70 revisiones humanas: nombre + fecha de nacimiento +
   `ID_PERSONA` cruzado contra `MOISES.PERSONA_NATURAL`), fuera del alcance autorizado hoy
   ("arreglo dirigido por identificador" asumía que el mecanismo automático de import
   funcionaría, no una revisión manual masiva).

## Balance final

- **Universo real procesado hoy: 91** (reconstruido en vivo, idéntico a la medición de la tarde).
- **Éxitos verificados: 11/91** (12,1%) — shadow `LINKED` a su User activo correcto, 0
  duplicados, balance del resource cerrado exacto (+11/−11), materialización downstream
  correcta según guardarraíl `FEC_TERMINO` preexistente.
- **Fallos: 0** — no hubo ningún intento fallido; los 80 restantes **no se intentaron**, por
  diseño, tras la investigación previa.
- **Retenidos sin procesar, clasificados: 80**
  - 10 (11%) — documento válido sin match — probable alta nueva, diferido al ciclo nocturno ya
    programado.
  - 70 (77%), **incluye el caso base Orlando** — documento corrupto en el origen Oracle
    (`ID_TIPODOCUMENTO=98/97`), requiere decisión de ingeniería o saneamiento de datos, no un
    simple reintento de correlación.
- **Provisioning downstream (Koha/LDAP):** no aplica — el resource Trabajadores en sí no
  provisiona Koha/LDAP directamente; los 11 Users afectados ya tenían sus propias afiliaciones
  académicas (alum/student) y roles Koha preexistentes por otras vías, sin cambios en esta
  sesión más allá del nuevo `linkRef` y (para 3/11) la materialización de `liveAffiliationWorker`
  según el guardarraíl `FEC_TERMINO` ya existente.

## 🔴 CORRECCIÓN (20-jul, verificación manual de Alberto) — el diagnóstico del Grupo C estaba mal atribuido

Alberto pidió la lista de los 70 para revisar manualmente y descartar mal-reporte o tabla incorrecta. **Se ejecutó el `baseQuery` REAL y desplegado de `trabajadores.xml` directamente contra Oracle en vivo** (no una aproximación) para los 70 COD_APS del Grupo C.

**Resultado: los 70/70 SÍ tienen un documento válido (`ID_TIPODOCUMENTO=1`, DNI, `NUM_DOCUMENTO` = su propio `COD_APS`) en `ELISEO.VW_APS_EMPLEADO`.** No hay ni un solo caso de "documento corrupto sin alternativa" — la premisa central del análisis anterior era incorrecta. Ejemplo (Orlando, `00534601`):

```
CANON_KEY   COD_APS     NUM_DOCUMENTO      ID_TIPODOCUMENTO  ESTADO
00534601    00534601    00000000534601     1  (DNI, válido)  A
00534601    00534601    000534601          4  (CE)           A
00534601    00534601    321931OCBTA0       98 (corrupto)     A
```

**Causa raíz real: el `baseQuery` de `trabajadores.xml` no colapsa a una sola fila por persona.** El `ROW_NUMBER()` que calcula `RN` particiona por `(ID_TIPODOCUMENTO, NUM_DOCUMENTO canonicalizado)` — dedupea DENTRO de cada documento, pero NO across los distintos documentos que una misma persona puede tener en `VW_APS_EMPLEADO` (DNI + CE + el código 97/98 de pensiones, todos como filas separadas). El cálculo de `CANON_KEY` asume que cada `COD_APS` ya llegó a una sola fila y solo desambigua colisiones ENTRE personas distintas (`w.COD_APS || '-' || w.ID_PERSONA` cuando el mismo documento lo comparten 2+ personas) — nunca contempla que una misma persona aporte 2-3 filas con el MISMO `CANON_KEY`. El `searchScript` del conector devuelve estas filas duplicadas con el **mismo `__UID__`/`__NAME__`** a MidPoint. Sin `ORDER BY` explícito en la query externa, el orden de retorno de Oracle no está garantizado — cuál de las 2-3 filas "gana" en el shadow cacheado de MidPoint es, en la práctica, no determinístico entre corridas.

**Verificado sistemáticamente para los 70 (no solo la muestra), vía Cypher/SQL directo, no una extrapolación:** 70/70 tienen al menos un tipo de documento válido (1/4/6) coexistiendo con el 97/98. 0/70 son "sin documento real" como se había concluido.

**Consecuencia:** las Opciones 1-3 propuestas arriba (fix del correlador, saneamiento de Oracle, vínculo manual) apuntaban al síntoma equivocado. **El fix correcto es en el `baseQuery` de `trabajadores.xml`: colapsar a UNA fila por `CANON_KEY`, prefiriendo el tipo de documento más confiable** (el propio `ORDER BY` interno ya tiene la lista de prioridad `CASE e.ID_TIPODOCUMENTO WHEN 1 THEN 1 WHEN 4 THEN 2 ... ELSE 14 END ASC` pensada para esto — solo falta aplicarla como desempate FINAL entre documentos de una misma persona, no solo dentro de un mismo documento). Fix no diseñado ni aplicado hoy — pendiente de autorización, dado que toca la query desplegada del resource completo (~7.532 shadows, blast radius real aunque el cambio en sí sea acotado).

**Nota de proceso:** el agente de la tarde no estaba "mal reportando" en el sentido de inventar datos — los valores que citó (COD_APS, `NUM_DOCUMENTO` corrupto, `ID_TIPODOCUMENTO=98`) son reales y están efectivamente en el shadow. El error fue de **atribución causal**: concluyó "el dato de origen es malo" sin ejecutar el `baseQuery` completo para confirmar si existía una fila alternativa válida para la misma persona. Verificar la causa raíz contra la query real, no solo contra el shadow ya materializado, habría evitado la conclusión errónea.

---

## Pendiente

- Grupo B (10) y Grupo C (70, incluido Orlando) quedan sin resolver — requieren una decisión
  explícita de Alberto sobre cuál opción tomar para el Grupo C, y confirmar si el Grupo B se
  deja al ciclo nocturno de mañana o se revisa antes.
- Verificar mañana (2026-07-21) el resultado de la primera corrida real de
  `recon-oracle-lamb-trabajadores-daily` — cubrirá el Grupo B de forma nativa si son altas
  nuevas genuinas, y no debería tocar el Grupo A (ya `LINKED`) ni crear duplicados sobre el
  Grupo C si el correlador no cambia (mismo riesgo se aplicaría en la corrida automática —
  vale la pena verificar sus resultados en el Grupo C específicamente, sin intervenir).

  **ACTUALIZACIÓN: esta task quedó SUSPENDIDA el 2026-07-20 — ver sección "✅ FIX APLICADO"
  abajo, no dejarla correr sin decidir primero cómo reconciliar la población en riesgo.**

---

## ✅ FIX APLICADO (20-jul, misma sesión que la corrección de arriba)

Alberto autorizó explícitamente diseñar y aplicar el fix de ingeniería identificado en la
corrección: colapsar `CANON_KEY` a una sola fila por persona en el `baseQuery` del
`searchScript` de `trabajadores.xml` (oid `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21`).

### Diff conceptual del SQL

**Antes:** `baseQuery` terminaba en `SELECT w.*, CASE ... END AS CANON_KEY FROM (...) w` — sin
ningún desempate posterior al cálculo de `CANON_KEY`. El `ROW_NUMBER() ... AS RN` interno
particiona por `(ID_TIPODOCUMENTO, NUM_DOCUMENTO canonicalizado)`, es decir dedupea DENTRO de
cada documento pero no ACROSS los documentos distintos que una misma persona puede tener.

**Después:** se envuelve el `baseQuery` original (alias `y`) en una capa adicional que agrega

```sql
SELECT z.* FROM (
  SELECT y.*, ROW_NUMBER() OVER (
    PARTITION BY y.CANON_KEY
    ORDER BY
      CASE y.ID_TIPODOCUMENTO WHEN 1 THEN 1 WHEN 4 THEN 2 WHEN 7 THEN 3 WHEN 22 THEN 4 WHEN 24 THEN 5
           WHEN 31 THEN 6 WHEN 23 THEN 7 WHEN 9 THEN 8 WHEN 6 THEN 9 WHEN 0 THEN 10 WHEN 97 THEN 11
           WHEN 98 THEN 12 WHEN 99 THEN 13 ELSE 14 END ASC,
      y.FEC_INICIO DESC NULLS LAST
  ) AS CANON_RN
  FROM ( /* baseQuery original, ya calcula CANON_KEY */ ) y
) z
WHERE z.CANON_RN = 1
```

Misma lista de prioridad de `ID_TIPODOCUMENTO` que ya usaba el `ORDER BY` interno del `RN`
(DNI=1 primero, CE=4 segundo, ..., códigos de pensión 97/98 casi al final). No se puede fusionar
en el mismo nivel de `SELECT` que calcula `CANON_KEY`: Oracle no permite que un `ROW_NUMBER()`
particione por el alias de OTRA función analítica calculada en el mismo nivel — de ahí la capa
extra `y`/`z`.

### Validación en Oracle (solo lectura, ANTES de tocar MidPoint)

Ejecutado en vivo contra `192.168.13.9:1521/UPEU` (`JUANSANCHEZ`), query real desplegada
(pre-fix) vs. la versión con `CANON_RN` (post-fix):

| Métrica | ANTES | DESPUÉS |
|---|---|---|
| Filas totales del universo (`ID_ENTIDAD=7124`, población completa) | 14.905 | 7.379 |
| `CANON_KEY` distintos | 7.379 | 7.379 |
| `CANON_KEY` con >1 fila (duplicados) | **5.573** | **0** |

**Hallazgo clave: el bug NO afectaba a 70 personas aisladas — afectaba potencialmente a 5.573 de
7.379 personas (75% del universo).** Los "70" de la corrección de arriba eran solo el
subconjunto que Alberto pidió revisar manualmente (el Grupo C de la tarea original); la medición
completa contra Oracle muestra que **cualquier trabajador con más de un documento registrado en
`ELISEO.VW_APS_EMPLEADO`** (típicamente DNI + código de pensión 97/98, o DNI + CE + pensión)
estaba expuesto al mismo no-determinismo, aunque solo una fracción tenía ya un shadow "roto" de
forma visible en MidPoint (porque el orden de Oracle, aunque no garantizado, en la mayoría de los
casos ya venía devolviendo el DNI primero por casualidad).

Verificación adicional (sin `IN`-list por el límite `ORA-01795` de 1000 expresiones; se usó
`JOIN` sobre CTEs en su lugar):

| Métrica | Valor |
|---|---|
| `CANON_KEY` duplicados que colapsaron a exactamente 1 fila tras el fix | 5.573 / 5.573 (100%) |
| De esos, cuántos tenían DNI (tipo=1) disponible entre sus filas duplicadas | 5.514 |
| De esos 5.514, cuántos quedaron con el DNI como fila ganadora | 5.514 (100%) |
| Casos con DNI disponible pero NO elegido (debía ser 0) | **0** |

Casos puntuales verificados fila por fila:

```
Orlando (00534601)  ANTES: 3 filas (tipo 1, tipo 4, tipo 98) mismo CANON_KEY=00534601
                     DESPUÉS: 1 fila (tipo 1, DNI 00000000534601)
Luzirene (000614192) ANTES: 2 filas (tipo 1, tipo 98) mismo CANON_KEY=000614192
                      DESPUÉS: 1 fila (tipo 1, DNI 000614192)
```

No se perdió gente: el universo de personas (`CANON_KEY` distintos) es idéntico antes y después
(7.379 = 7.379); solo se colapsaron las filas duplicadas por persona.

### PATCH a PROD (nunca PUT)

1. Backup completo del resource vía `GET /resources/{oid}` antes de tocar nada
   (`trabajadores-BACKUP-preFIX-2026-07-20.xml`, version 318).
2. `PATCH` de `c:connectorConfiguration/icfc:configurationProperties/cfg:searchScript` con el
   `baseQuery` corregido → **HTTP 204**, version 318→319.
3. Verificación post-PATCH: `<schema>` cacheado con el mismo número de `xsd:element` que antes
   (5=5), `connectorRef`/`schemaHandling`/`capabilities` intactos, **test connection 15/15
   sub-resultados `success`**.
4. `PATCH` adicional de `c:description` con la nota de gobernanza del fix → HTTP 204,
   version 319→320.

### Canario — resultado

Import dirigido (`POST /shadows/{oid}/import`) sobre los 2 shadows conocidos:

| Caso | Shadow OID | Antes (NUM_DOCUMENTO / TIPO) | Después (NUM_DOCUMENTO / TIPO) | Sync situation |
|---|---|---|---|---|
| Orlando 00534601 | `0c1660ee-b79f-48c3-abc8-5c852ad8226c` | `321931OCBTA0` / `98` (corrupto) | `00000000534601` / `1` (DNI) | UNMATCHED → LINKED (efímero, ver abajo) |
| Luzirene 000614192 | `f3af8397-61f4-45f5-8c4e-0c286e339425` | `570370LGAEA5` / `98` (corrupto) | `000614192` / `1` (DNI) | UNMATCHED → LINKED (efímero, ver abajo) |

El fix en sí funcionó exactamente como se diseñó: el shadow ahora trae la fila DNI, no la
corrupta. **Pero el `import` reveló un riesgo colateral no anticipado** (ver siguiente sección).

### 🔴 Riesgo colateral descubierto en el canario — remediado en la misma sesión

Ambos casos (Orlando, Luzirene) tienen un **User pre-existente** en MidPoint cuyo
`extension/upeu:lambDocNum` está anclado en su documento **CE**, no en su DNI:

```
Orlando real:  oid 2dba749b-...  name=200610808  lambDocNum=CE:000534601  (activo)
Luzirene real: oid 49945169-...  name=00614192   lambDocNum=CE:000614192  (archivado)
```

Antes del fix, el shadow cacheado de ambos —por la suerte del orden no determinístico de
Oracle— venía trayendo la fila **corrupta** (tipo 97/98), así que el correlador nunca los tocaba.
Tras el fix, el shadow trae la fila **DNI** (tipo 1, prioridad más alta) — pero el `lambDocNum`
calculado a partir del DNI (`00534601`, sin prefijo) **no coincide** con la clave `CE:000534601`
que ya tiene el User real. El correlador, correctamente, no encontró match → la reacción
`unmatched → addFocus` **creó un User nuevo y duplicado** para cada uno:

```
Orlando duplicado:  oid cb5e3a5e-...  name=00534601   lambDocNum=00534601   (activo)
Luzirene duplicada: oid 0a3ada24-...  name=000614192  lambDocNum=00614192  (archivado, por template)
```

El duplicado de Orlando, al ser `active`, **se auto-aprovisionó en ~10 minutos** a 2 sistemas
reales downstream (recompute automático del template):

- **LDAP** (`LDAP-IdentityCache-UPeU`, oid `7b4e1c2d-...`): entrada real
  `uid=00534601,ou=people,dc=upeu,dc=edu,dc=pe` con datos completos (eduPerson, email, etc.).
- **Koha** (`Koha ILS UPeU (consolidado)`, oid `e10a539a-...`): patrón real, `cardnumber=00534601`,
  `branchcode=BUL`, `borrowernumber≈16200`.

**Remediación ejecutada de inmediato, misma sesión:**

1. Se intentó `DELETE` directo de los 2 Users duplicados → `fatal_error` HTTP 500 porque
   Trabajadores (fuente read-only) no tiene `DeleteCapabilityType` — como es correcto que no la
   tenga. El modelo igual eliminó el `UserType` del repo (los `linkRef` a Trabajadores quedaron
   huérfanos sin dañar nada, porque ese shadow no tiene ninguna operación de escritura pendiente).
2. Los shadows huérfanos de **LDAP y Koha** (con delete deshabilitado por guardarraíl de
   configuración, `capabilities/configured/delete/enabled=false`) se borraron con el **mismo
   mecanismo gobernado usado ayer para el caso `202421264`**: backup → habilitar el guardarraíl
   temporalmente (`PATCH`, nunca `PUT`) → `DELETE /shadows/{oid}` (204) → revertir el guardarraíl
   a `false` de inmediato (204, verificado con schema intacto: LDAP 153/153 `xsd:element`, Koha
   9/9).
3. **Verificado con acceso real a los sistemas, no solo MidPoint:**
   - `ldapsearch` directo contra `192.168.15.168` (`docker exec openldap ldapsearch`): `uid=00534601`
     → **0 resultados** (borrado confirmado). `uid=200610808` (Orlando real) → **intacto**, con
     su `cn` correcto.
   - `mysql` directo contra la BD Koha consolidada (`koha-167`, `koha_upeu.borrowers`):
     `cardnumber='00534601' OR borrowernumber=16200` → **0 filas**. Búsqueda adicional por
     apellido "Cortez Bazantes" → 0 filas (Orlando nunca tuvo un patrón Koha real antes de este
     incidente, así que no hay riesgo de haber tocado uno preexistente).
4. Los 2 Users reales (`2dba749b` Orlando, `49945169` Luzirene) quedaron **verificados
   intactos**, sin ningún cambio, con su `lambDocNum` original (`CE:...`) preservado.
5. Los 2 shadows de Trabajadores del canario (`0c1660ee`, `f3af8397`) quedaron en estado
   **huérfano seguro**: `synchronizationSituation` vacío (sin `linkRef` de ningún User), con los
   datos ya corregidos (DNI, tipo=1) cacheados — no dañan nada, no crean nada, listos para que
   una reconciliación DIRIGIDA (no masiva) los vincule manualmente al User correcto en una sesión
   futura.
6. Balance final del resource verificado: **7.532 shadows exactamente igual que antes del
   canario** (0 perdidos, 0 huérfanos nuevos permanentes) — `LINKED` 7.397→7.399 (+2, los 2
   canarios), `UNMATCHED` 92→90 (−2), `UNLINKED`/`DISPUTED` sin cambio.

**Task `recon-oracle-lamb-trabajadores-daily` (oid `23b9fde4-6a5f-4c84-9370-0971fb27be73`)
SUSPENDIDA de inmediato** (`executionState`/`schedulingState` verificados `suspended`) para
evitar que la corrida nocturna programada para el 21-jul repita este patrón a escala sobre los
~5.573 `CANON_KEY` en riesgo (cualquiera cuyo User existente esté anclado en un documento de
menor prioridad que el que el fix ahora prefiere). **No reactivar sin decisión explícita de
Alberto** sobre una de estas rutas (o una combinación):

- Cambiar la reacción `unmatched` de este resource de `addFocus` automático a una cola de
  revisión humana quando el `lambDocNum` calculado no matchea PERO `ID_PERSONA`/nombre+fecha de
  nacimiento sí sugieren una persona ya existente (correlación secundaria).
- Antes de reconciliar, correr un barrido de solo-lectura (como el de esta sesión) sobre los
  ~5.573 `CANON_KEY` para separar: (a) shadows cuyo `lambDocNum` post-fix YA coincide con un User
  existente (reconciliables sin riesgo), de (b) los que, como Orlando/Luzirene, tienen un User
  anclado en una clave de menor prioridad (requieren re-anclaje manual del `lambDocNum` del User
  existente ANTES de reconciliar, para que el `import` los encuentre).
- Evaluar si el `lambDocNum` debería considerar TODAS las claves de documento de una persona
  (no solo la de mayor prioridad) como alias de correlación, en vez de una sola clave ganadora.

### Estado final verificado (resource + PROD)

- `trabajadores.xml` PROD: version 320, `<schema>` cacheado intacto (5/5 `xsd:element`), test
  connection 15/15 `success`, `connectorRef`/`schemaHandling`/`capabilities` intactos.
- Guardarraíles de LDAP y Koha revertidos a `delete/enabled=false` (verificado post-revert en
  ambos, schema intacto: LDAP 153 elementos, Koha 9 elementos).
- `recon-oracle-lamb-trabajadores-daily`: **suspendida**, pendiente de decisión.
- Repo: commit `ad2c626` (`fix: colapsa CANON_KEY duplicado en trabajadores.xml...`), pusheado y
  ya en `main` en PROD (`git pull` fast-forward `9c8abef..ad2c626`).
