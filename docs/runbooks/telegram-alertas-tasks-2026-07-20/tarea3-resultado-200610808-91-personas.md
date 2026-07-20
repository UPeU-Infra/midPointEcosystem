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

## Pendiente

- Grupo B (10) y Grupo C (70, incluido Orlando) quedan sin resolver — requieren una decisión
  explícita de Alberto sobre cuál opción tomar para el Grupo C, y confirmar si el Grupo B se
  deja al ciclo nocturno de mañana o se revisa antes.
- Verificar mañana (2026-07-21) el resultado de la primera corrida real de
  `recon-oracle-lamb-trabajadores-daily` — cubrirá el Grupo B de forma nativa si son altas
  nuevas genuinas, y no debería tocar el Grupo A (ya `LINKED`) ni crear duplicados sobre el
  Grupo C si el correlador no cambia (mismo riesgo se aplicaría en la corrida automática —
  vale la pena verificar sus resultados en el Grupo C específicamente, sin intervenir).
