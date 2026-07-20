# Contrato de configuración — Koha nuevo consolidado (1 instancia, 4 bibliotecas)

**Fecha:** 2026-07-16 · **Owner:** Alberto Sánchez · **Estado:** el resource del consolidado YA EXISTE en `lifecycleState=proposed` — ver §1

> **⚠️ ACTUALIZACIÓN 2026-07-20.** `koha-upeu.xml` ya está en `lifecycleState=active` en PROD
> (cutover Etapas 1-4, 19-jul: 11 roles Koha repuntados, Koha viejo `koha-ils.xml`/`9b5a7c81`
> archivado, 15.914+ patrons migrados). Branches `BUL/BUJ/BUT/CIA` confirmados activos en vivo
> con patrons reales en los 3 primeros (BUL 15.315, BUJ 655, BUT 262). **Gap encontrado y
> cerrado el mismo 20-jul:** aunque el resource y los 11 roles ya apuntaban al consolidado, 4 de
> los `AR-Koha-Patron-*` (Pregrado/Posgrado/Faculty/Administrativo) conservaban el `<condition>`
> Lima-only heredado del Koha viejo (gate tarea #65) — bloqueaba ~11.148 holders reales en
> Juliaca/Tarapoto. Gate retirado en los 4 roles (ver sus XML). El resto de este contrato (§4-9,
> catálogo Bsort2/discriminador CIA) sigue siendo el pendiente real para el reporte consolidado
> por branch.
> **🔴 SUPERSEDIDO 2026-07-20 — el plan Teología→CIA queda DESCARTADO.** Decisión explícita de
> Alberto: CIA (Centro de Investigación Adventista) es una **biblioteca de solo lectura en sala**
> (3.564 ítems, 100% `notforloan=1` en Koha, medido en vivo), accesible como **extensión abierta**
> a cualquier persona de cualquier campus, y **NUNCA** debe ser home library/branchcode de ningún
> patron. Esto supersede el diseño de §3.5 y §5 de este contrato (discriminador
> `facultyName=='Facultad de Teología'` para estudiantes + `teachingProgram⊇'EP-TEO'` para
> docentes → `library_id='CIA'`), y las tareas derivadas en §8.3, §10.3 y "Puntos abiertos" #1/#3
> — ver notas inline en cada sección. Aplicado en PROD el mismo día: el parche legacy
> `'CIA':'CIA','ICA':'CIA'` se **retiró** de `library-id-outbound` en `upeu/resources/koha-upeu.xml`
> y su espejo en `upeu/resources/koha-ils.xml` (sin migración de patrons: 0 población afectada,
> verificado 0 patrons branchcode=CIA en Koha y 0 Users locality=CIA en MidPoint). El personal y
> alumnado de Teología se registra en su sede real (Lima → `BUL`); CIA sigue existiendo como
> branch/edificio en Koha para circulación en sala, sin patrons propios.

**Fuentes:** validado por `midpoint-expert` (lado proyección + verificación PROD), `koha-expert` (lado receptor + conector v1.3.12), `vocbench-expert` (catálogo tesauro real).

> **⚠️ CORRECCIÓN 2026-07-16.** La primera versión de este contrato se redactó analizando `upeu/resources/koha-ils.xml` (el resource **viejo**, `.135`/`koha_bul`) y afirmaba que "el resource ya es único, solo hay que re-apuntar `serviceAddress`+`dbHost`". **Es falso.** Existe un resource **dedicado** para el consolidado — `upeu/resources/koha-upeu.xml` — creado y re-apuntado al `.136` en otra sesión (commit `300f6aa`, 15-jul). El re-apuntado **ya se hizo**. Las §1 y §10 quedan corregidas abajo; el resto del contrato (5 ejes, checklist receptor, reporte SQL, circulación, dedup INEI, discriminador CIA) **sigue siendo válido y es justo lo que falta** para promover `koha-upeu` de `proposed` a `active`.

> **Principio rector.** MidPoint es la **única fuente de verdad**. Koha es una **proyección** del gobierno IGA, no un eje paralelo de gobernanza. El "Koha nuevo" (1 instancia, 4 branches `BUL/CIA/BUJ/BUT`) debe estar **preparado para recibir** exactamente los valores/formatos de abajo. Ningún operador de Koha edita manualmente estos campos: MidPoint los reescribe en cada recompute/reconcile.

---

## 1. Contexto

UPeU migra de **4 instancias Koha (una por biblioteca)** a **1 instancia con las 4 bibliotecas como branches**. Del lado MidPoint hay **DOS resources Koha** (estado verificado 2026-07-16):

| Resource | OID | Endpoint / BD | `lifecycleState` | Rol |
|---|---|---|---|---|
| `upeu/resources/koha-ils.xml` | `9b5a7c81…` | `192.168.12.135:8001` / `koha_bul` | active | **Viejo** (instancia por-biblioteca). Hoy en *maintenance* por la caída del FortiGate del 08-jul. |
| **`upeu/resources/koha-upeu.xml`** — "Koha ILS UPeU (consolidado)" | `e10a539a-cb7f-4c72-a19f-60f7f62e4b96` | **`192.168.12.136:8001` / `koha_upeu`** (koha-plus-prod) | **`proposed`** | **El consolidado.** Re-apuntado del `.167` (modelado) al `.136` en el commit `300f6aa` (15-jul). `dbEnabled=false` temporal: el FortiGate bloquea `.166→.136:3306` (canal de fotos, commit `acb9538`). |

**`koha-upeu.xml` ya porta los 5 ejes** (`category_id`, `statistics_1`/Bsort1, `statistics_2`/Bsort2, `extended_attributes`, `library_id`). Su `library-id-outbound` ya usa `.get(effective)` sin default (null si no mapea) — mejor que el viejo, que forzaba `BUL`.

**Lo que este contrato aporta y AÚN falta en `koha-upeu.xml`:** su `library-id-outbound` sigue resolviendo CIA por el **parche legacy `locality=='CIA'/'ICA'`**, sin el discriminador gobernado de Teología (§3.5/§5). Más el checklist receptor del lado Koha (§4), el reporte SQL (§7) y la circulación cross-sede (§6). Eso es lo que hay que cerrar para promover el resource de `proposed` → `active`.

### Topología campus / biblioteca

| Campus | Biblioteca(s) — branchcode |
|---|---|
| Lima | `BUL` (Biblioteca Lima) + `CIA` (Centro de Investigación Adventista — especializada; habituales = Teología) |
| Juliaca | `BUJ` |
| Tarapoto | `BUT` |

Relación **no 1:1**: Lima tiene 2 bibliotecas. Que "todas atiendan a cualquiera de cualquier campus" **NO** se modela en el branchcode — es config de **circulation rules dentro de Koha** (§6).

### Reporte estrella (motiva todo el diseño)

Cada biblioteca reporta *"usuarios que USARON esta biblioteca, agrupados por programa académico (INEI 8 díg), sin importar campus"*. Dos dimensiones, dos dueños:
- **"dónde se usó"** → `statistics.branch` (transacción) — lo pone **Koha**, no MidPoint.
- **"por programa"** → `borrowers.sort2` = Bsort2 = INEI 8 díg — lo pone **MidPoint**.

Al consolidar, los 4 reportes salen de la **misma tabla** agrupando por el **mismo `Bsort2`** → las 4 bibliotecas deben compartir **un único catálogo Bsort2**, cargado **desde VocBench** (fuente única de la codificación INEI).

---

## 2. Los 5 ejes — resumen

| # | Eje IGA | Campo Koha (`ri:`) | Fuente focus MidPoint | Valor/formato emitido | Strength |
|---|---|---|---|---|---|
| 1 | Perfil | `category_id` | `sb:primaryAffiliation` | `faculty`\|`staff`\|`student`\|`alum`\|`affiliate`\|`local` (eduPerson 202208; `employee`→`staff`; resto→`local`) | strong |
| 2 | Facultad | `statistics_1` (Bsort1) | `sciback:facultyName` | `FCS`\|`FIA`\|`FACIHED`\|`FCE`\|`FACTEO`\|`EPG` (no mapeada → null) | normal |
| 3 | Programa | `statistics_2` (Bsort2) | `sciback:academicProgramIneiCode` | INEI 2022 **8 dígitos** (ej. `31300211`); sin INEI → null | normal |
| 4 | Ortogonales | `extended_attributes` | varios | Lista JSON `{"type":"CODE","value":"..."}` | strong (parcial) |
| 5 | Biblioteca home | `library_id` | `campusStudent`?:`campusWorker`?:`locality` + facultad/teaching | `BUL`\|`CIA`\|`BUJ`\|`BUT` | strong |

Namespaces: `sb:`/`sciback:` = `urn:sciback:midpoint:person`; `upeu:` = `urn:upeu:midpoint:local`.

---

## 3. Lado MidPoint — qué proyecta

### 3.1 Perfil → `category_id`
Outbound `category-id-from-primary-affiliation`, strong, sin overrides por-rol. `primaryAffiliation`→lowercase; `employee`→`staff`; valores eduPerson literales; otro→`local`. **6 categorías** requeridas en Koha.

### 3.2 Facultad → `statistics_1` (Bsort1)
Outbound `statistics1-outbound`, normal. Match exacto `facultyName` (Oracle) → código corto:

| `facultyName` exacto | Bsort1 |
|---|---|
| Facultad de Ciencias de la Salud | `FCS` |
| Facultad de Ingeniería y Arquitectura | `FIA` |
| Facultad de Ciencias Humanas y Educación | `FACIHED` |
| Facultad de Ciencias Empresariales | `FCE` |
| Facultad de Teología | `FACTEO` |
| Escuela General de Posgrado | `EPG` |

No listada → null.

### 3.3 Programa → `statistics_2` (Bsort2) — EL CRÍTICO
Outbound `statistics2-outbound`, normal, **sin transformación** (emite el valor tal cual). La derivación ocurre aguas arriba: bloque **D.1c** del template base resuelve `academicProgramSuneduCode` (P-code, de Oracle `COALESCE(CODIGO_SUNEDU2,'P'||CODIGO_SUNEDU)`) → `academicProgramIneiCode` (INEI) vía **LookupTable `LT-Pcode-INEI`** (OID `e129d9e4-c2fd-4a02-9369-0ae5b8f59c06`, **42 rows pobladas**). Cadena: **VocBench (fuente de curación) → LT-Pcode-INEI → (D.1c) focus → (outbound) Bsort2**.

> **IMPORTANTE — la proyección NO lee VocBench en vivo.** El P-code del estudiante viene de **Oracle**; la traducción a INEI la hace la **LookupTable ya poblada**. VocBench fue la fuente para *curar* esa tabla, pero la operación diaria no lo toca. Por tanto la **salud del tesauro VocBench en vivo NO es un bloqueante del reporte Koha** — lo que gobierna Bsort2 es la LT + los P-codes de Oracle. Estado real del workstream Bsort2→INEI (jun-2026, ver `upeu/tasks/bsort2-inei-posgrado/README.md`): **pregrado casi cerrado** (INEI en la LT, salvo ~3 carreras sin P-code en Oracle); **posgrado con GAP conocido y documentado** (~1.449 estudiantes Lima en 31 P-codes sin INEI validado — "no es bug, ronda futura").
>
> **⚠️ La LT y el tesauro NO están perfectamente sincronizados (reconciliación 2026-07-16).** Oracle LAMB **no** tiene INEI poblado (`DAVID.ACAD_PROGRAMA_ESTUDIO.CODIGO_NACIONAL` = NULL para todos) → la única autoridad de INEI es VocBench + la LT, y **divergen en algunos códigos**. Conflictos de valor detectados (mismo programa, INEI distinto en cada capa): **P35 Teología** (LT `22103063` vs tesauro `22101180` — relevante porque Teología es el programa de CIA), **P05 Administración Negocios Int.** (LT `41600562` vs tesauro `41300011`), **P99 Doctorado Ing. Sistemas** (LT `61200058` vs tesauro `61203409` sin tipar). Requieren el clasificador INEI 2022 oficial para dirimir. Detalle y plan de curación: [`upeu/tasks/bsort2-inei-posgrado/curacion-tesauro-inei-2026-07-16.md`](../../upeu/tasks/bsort2-inei-posgrado/curacion-tesauro-inei-2026-07-16.md).

### 3.4 Ortogonales → `extended_attributes`
Multivaluado, JSON `{"type":"CODE","value":"..."}` (conector v1.3.x). Gobierno parcial: `tolerant=false` + whitelist `tolerantValuePattern`.
- **Gobernados (MidPoint dueño):** `STUDY_LEVEL` (pregrado/posgrado), `STUDYCYCLE` (multivalor), `AREA` (vía AR-Koha-Librarian), `RESEARCHER=Y` (vía AR-Koha-Investigador), `CRAI_TIER`.
- **Preservados (emite pero no borra):** `DNI` (adopt-by-DNI del conector), `SEDE`, `TIPO_VINC`, `ORCID`, `COD_UPEU`, `SHOW_BCODE`.

### 3.5 Biblioteca home → `library_id` (branchcode)

> **🔴 SUPERSEDIDO 2026-07-20.** Esta sección documentaba (a) el estado del parche legacy
> `locality=='CIA'/'ICA'` y (b) una **propuesta** de discriminador gobernado Teología→CIA que
> nunca llegó a implementarse. Ambos quedan descartados por decisión de Alberto: **CIA es
> biblioteca de solo lectura en sala, extensión abierta a cualquier campus, y NUNCA home
> library de ningún patron.** El parche legacy `'CIA':'CIA','ICA':'CIA'` fue **retirado** (no
> reemplazado por el discriminador de abajo) de `library-id-outbound` en `koha-upeu.xml` y su
> espejo `koha-ils.xml`, aplicado en PROD el 2026-07-20. Contenido histórico preservado abajo
> por contexto; **no representa el diseño vigente.**

**Estado actual (verificado 2026-07-16, histórico):**
- `koha-ils.xml` (viejo): `[...].getOrDefault(effective,'BUL')` — forzaba `BUL` por defecto.
- **`koha-upeu.xml` (consolidado):** `['LIMA':'BUL','JULIACA':'BUJ','TARAPOTO':'BUT','CIA':'CIA','ICA':'CIA'].get(effective)` — ya **sin default** (null si no mapea; mejor). Pero **CIA sigue alcanzándose solo por el parche legacy** `locality=='CIA'/'ICA'` (frágil, no gobernado). **Este es el cambio que falta aplicar en `koha-upeu.xml`.**

**Propuesta (histórica, descartada):** `library_id = f(campus, unidad-Teología)`. **Requiere DOS señales** (ver §5, verificado en PROD):
- **Estudiantes:** `facultyName == 'Facultad de Teología'` → `CIA`. ✅ ya materializado.
- **Docentes:** `teachingProgram ⊇ 'EP-TEO'` → `CIA`. ✅ dato ya en el focus (los docentes **no** tienen `facultyName`).
- Resto Lima → `BUL`; Juliaca → `BUJ`; Tarapoto → `BUT`.
- **Mantener** el fallback `locality=='CIA'/'ICA'` como puente hasta cubrir el 100%.

---

## 4. Lado Koha — checklist receptor (pre-requisito antes de re-apuntar)

Conector `connector-koha` **v1.3.12: apto** — mapea los 5 ejes correctamente vía REST (`category_id`/`library_id`/`statistics_1`/`statistics_2` como campos directos del POST/PUT `/patrons`; `extended_attributes` por endpoint dedicado `PUT /patrons/{id}/extended_attributes` con merge-preserve de los no-gobernados). **El conector NO crea catálogo** (solo GET de categories/branches/attribute types) → todo esto debe existir **antes**, o Koha responde **400/rechaza**.

En single-instance, categories / authorised values / attribute types son **globales** (compartidos por los 4 branches) — satisface por diseño el "catálogo Bsort2 único".

| Objeto | Qué crear | Mecanismo |
|---|---|---|
| **Patron categories (6)** | `faculty`, `staff`, `student`, `alum`, `affiliate`, `local` | UI Administration → Patron categories (fija defaults) |
| **AV `Bsort1`** | `FCS, FIA, FACIHED, FCE, FACTEO, EPG` (+ `COLEGIO, UNKNOWN` legacy) | UI Authorised values — **"All libraries" (sin límite por branch)** |
| **AV `Bsort2`** | Códigos INEI 8 díg del tesauro (ver §7 — **catálogo pendiente de curación**) | SQL bulk a `authorised_values` — **sin límite por branch** |
| **Patron attribute types (11)** | Gobernados: `STUDY_LEVEL`, `RESEARCHER`, `AREA`, `CRAI_TIER`, `STUDYCYCLE`(repeatable). Preservados: `DNI`(unique), `SEDE`, `TIPO_VINC`, `ORCID`(unique), `COD_UPEU`, `SHOW_BCODE` | UI Patron attribute types |
| **Branches (4)** | `BUL`, `CIA`, `BUJ`, `BUT` | UI Libraries |

> **Crítico:** las AV `Bsort1`/`Bsort2` NO deben limitarse por branch (`authorised_values_branches`) → así los 4 branches comparten idéntico catálogo (requisito del reporte consolidado).

Bug conocido **DT-11** (`Uid cannot be null` en search) presente en el conector — no afecta CREATE/UPDATE de los 5 ejes, pero vigilar en imports masivos.

---

## 5. Discriminador CIA — verificado en PROD (12-jul-2026)

> **🔴 SUPERSEDIDO 2026-07-20.** Esta sección documentaba la investigación de cobertura de datos
> (`facultyName`/`teachingProgram`) para un discriminador Teología→CIA que **nunca se
> implementó** y que queda **descartado** por decisión de Alberto: CIA es biblioteca de solo
> lectura en sala, extensión abierta a cualquier campus, NUNCA home library de ningún patron. La
> conclusión técnica de abajo (`facultyName` insuficiente para docentes) sigue siendo correcta
> como dato histórico, pero ya no motiva ningún cambio de diseño — no hay discriminador CIA que
> construir. Ver nota superseded al inicio del documento y en §3.5.

**Conclusión (histórica): `facultyName == 'Facultad de Teología'` NO alcanza para docentes.** Cobertura real de `facultyName` por afiliación:

| afiliación | total | con `facultyName` | % |
|---|---|---|---|
| student | 24 227 | 24 145 | 99.7% |
| faculty | 1 159 | 162 | 14% (ninguno de Teología; son doble-rol de otras facultades) |
| staff | 8 669 | 306 | 3.5% |
| alum | 27 534 | 0 | 0% |

- Los 174 con `facultyName='Facultad de Teología'` = 171 students + 3 staff + **0 faculty**.
- Docentes de Teología identificables por **`teachingProgram ⊇ 'EP-TEO'`** (29 detectados; `teachingProgram` poblado en 52% de faculty). Todos con `campusWorker='LIMA'` y `facultyName` vacío.
- Campos de org laboral (`orgDepto`, `areaId`, `sedeId`) = 0 poblados en faculty/staff → NO sirven de discriminador.

**Caminos:**
- **Mínimo viable (sin tocar Oracle):** discriminar docentes CIA por `teachingProgram ⊇ 'EP-TEO'` (dato ya en focus). Requiere **confirmar con Calidad** que los semestres de corte (267/279/283 de `VW_CARGA_DOCENTE`) capturan a todos los docentes vivos de Teología.
- **Canónico completo (recomendado para Bsort1 coherente en docentes):** extender el `searchScript` de `trabajadores.xml` (Opción A) para materializar `sb:facultyName` en docentes desde `VW_CARGA_DOCENTE.NOMBRE_ESCUELA → ORG_AREA` padre — misma mecánica que estudiantes. *Solo diagnosticado, no implementado.*

---

## 6. Circulation cross-sede — config Koha (NO MidPoint)

Para que "todas atiendan a cualquiera de cualquier campus":
1. **`IndependentBranches = OFF`** (interruptor maestro).
2. **Circulation & fine rules** con `library = "All libraries" (*)` (al menos una fila default All/All/All).
3. **`CircControl`** = *logged-in library* (reglas del mostrador donde se hace la transacción).
4. **Holds cross-branch:** `canreservefromotherbranches=Allow`, pickup any.
5. **Transfers:** sin `BranchTransferLimits` bloqueantes entre `BUL/CIA/BUJ/BUT`; `AutomaticItemReturn` según política.

Valores concretos de préstamo/multa por `category×itemtype` los define el área de biblioteca — **PENDIENTE** (requiere Koha real).

---

## 7. Reporte estrella — de qué sale el número

- **"usó esta biblioteca"** → `statistics.branch` (branch de la transacción, NO home library).
- **"programa"** → `borrowers.sort2` (INEI que puso MidPoint).
- **Cruce:** `statistics.branch` × `borrowers.sort2`.

El **wizard estándar de Koha cuenta transacciones, no personas distintas** → para el entregable ("usuarios distintos por programa") hace falta un **SQL report custom** (Reports → Guided reports → New SQL):

```sql
SELECT
  b.sort2                             AS codigo_inei,
  COALESCE(av.lib,'(sin programa)')   AS programa,
  COUNT(DISTINCT st.borrowernumber)   AS usuarios_distintos,
  COUNT(*)                            AS transacciones
FROM statistics st
JOIN borrowers b ON b.borrowernumber = st.borrowernumber
LEFT JOIN authorised_values av
       ON av.category='Bsort2' AND av.authorised_value = b.sort2
WHERE st.branch = <<Biblioteca|branches>>
  AND st.type IN ('issue','renew','localuse')   -- quitar 'localuse' si "uso" = solo préstamos
  AND st.datetime BETWEEN <<Desde|date>> AND <<Hasta|date>>
GROUP BY b.sort2, av.lib
ORDER BY usuarios_distintos DESC;
```

El dropdown `<<Biblioteca|branches>>` hace que el mismo reporte sirva a las 4. Un patrón con `sort2` nulo cae en "(sin programa)".

---

## 8. Pre-requisitos BLOQUEANTES (antes de re-apuntar al Koha nuevo)

Ordenados por criticidad:

1. **🟠 Poblar AV Bsort2 en Koha desde la `LT-Pcode-INEI` (42 rows), NO desde el tesauro en vivo.** El catálogo operativo de INEI ya existe en la LookupTable (pregrado cerrado). Generar los authorised_values Bsort2 del Koha nuevo **desde las filas de la LT, deduplicando por INEI** (`SELECT DISTINCT value` → ~37 INEI únicos). La LT tiene 4 INEI con múltiples P-codes (`11102086`=P19/P58; `12104952`=P14/P106/P57; `41101896`=P08/P120 Tarapoto; `91910681`=P69/P82 menciones Salud Pública) — **NO son bug**, son aliases N:1 intencionales (P-code=key única→INEI; varios códigos SUNEDU por mención/sede caen en el mismo programa, documentado en cada label). En Koha el código es el INEI y debe ser único → un AV por INEI. El reporte agrupa por INEI, consolidando menciones/sedes bajo el programa (deseable).
2. **🟡 Cerrar el gap de posgrado** (documentado, "no es bug"): ~1.449 estudiantes Lima en 31 P-codes sin INEI validado (P178, P171, P75, P164, P159, P73, P78…). Sin esto esos patrons de posgrado salen con `Bsort2` vacío ("(sin programa)"). Requiere nueva ronda de validación INEI 2022 y agregar rows a la LT. **NO bloquea pregrado.**
3. ~~🟠 Decidir discriminador CIA docentes~~ — **SUPERSEDIDO 2026-07-20**: decidido que NO hay discriminador CIA que construir (ver nota al inicio del documento y §3.5/§5). Ítem cerrado, no bloqueante.
4. **🟠 Pre-crear el catálogo receptor** completo en el Koha nuevo (§4).
5. **🟡 Confirmar** listas de valores AV para `AREA`/`CRAI_TIER`/`TIPO_VINC`/`SEDE`.
6. **🟢 (Higiene VocBench, NO bloqueante Koha)** — el snapshot del tesauro en vivo tiene deuda de curación que afecta a *otros* consumidores (DSpace/Indico) y a futuras regeneraciones de la LT, pero NO a la proyección Koha actual: ~14 conceptos duplicados/legacy de pregrado sin `IneiCode8` (son gemelos de conceptos que sí lo tienen — p.ej. Medicina Humana proyecta bien vía `P30→91200267` en la LT), 82% de programas sin vínculo formal a facultad (solo `scopeNote`), 6 conceptos RIMS sin SKOS-XL, `ciencias-de-la-salud` con doble notation `FCS`/`FACISAL`. Deseable curar, sin urgencia para Koha.

---

## 9. Sincronización continua VocBench ↔ (MidPoint + Koha)

`Bsort2` exige coherencia de **dos proyecciones** que MidPoint NO sincroniza solo: `LT-Pcode-INEI` (define qué INEI se materializa) y `authorised_values Bsort2` en Koha (define qué INEI es válido). Desincronización → MidPoint emite un INEI que Koha rechaza, o el focus nunca lo materializa.

**Procedimiento cuando VocBench cambia un programa:**
1. Actualizar VocBench (fuente de verdad) → regenerar CSV bridge.
2. Editar row en `LT-Pcode-INEI` (UI MidPoint; key=P-code, value=INEI).
3. Agregar el INEI como AV Bsort2 en Koha **antes** de recomputar (no eliminar el viejo hasta migrar patrons).
4. Recompute masivo de focos afectados (materializa vía D.1c).
5. Reconcile del resource Koha (proyecta Bsort2). Verificar contra muestra.
6. Recién entonces retirar el AV/INEI antiguo si aplica.

**Estructural:** VocBench único origen; `LT-Pcode-INEI` y AV Bsort2 son dos proyecciones a regenerar juntas desde el mismo bridge CSV. Recomendado un script que valide que toda `key` del LookupTable tiene su INEI como AV en Koha, y reporte discrepancias antes de cualquier reconcile masivo. **Nunca** editar Bsort2 en Koha ni el INEI en el focus directamente.

---

## 10. Promover `koha-upeu` de `proposed` → `active` (el re-apuntado YA se hizo)

> El paso "cambiar `serviceAddress`/`dbHost`" **ya está hecho** (commit `300f6aa`): `koha-upeu.xml` apunta al `.136`/`koha_upeu`. Lo que queda:

1. **Cumplir el checklist receptor §4** en la instancia `.136` (6 categories, AV Bsort1/Bsort2 **sin límite por branch**, 11 patron attribute types, 4 branches `BUL/CIA/BUJ/BUT`). El conector no crea nada de esto.
2. **Poblar AV Bsort2 desde la LT** deduplicando por INEI (§8.1, ~37 únicos).
3. ~~Actualizar `library-id-outbound` de `koha-upeu.xml` al discriminador gobernado de Teología~~ — **SUPERSEDIDO Y EJECUTADO 2026-07-20 en sentido contrario**: no se implementó el discriminador; se **retiró** el parche `locality=='CIA'/'ICA'` sin reemplazo (CIA nunca es home library — ver nota al inicio del documento). Aplicado en PROD mediante PATCH a `koha-upeu.xml` y `koha-ils.xml`, 0 población afectada.
4. **Desbloquear `dbEnabled`**: hoy `false` porque el FortiGate bloquea `.166→.136:3306` (canal de fotos). Depende de Redes — misma causa raíz que tumbó los LAMB el 08-jul.
5. Commit → push → `git pull` en PROD → aplicar vía REST → Test Connection (`success`).
6. **Promover `lifecycleState`: `proposed` → `active`.**
7. Reconcile + verificar un patrón muestra **por branch** (BUL/CIA/BUJ/BUT): category/Bsort1/Bsort2/extended_attributes/library_id correctos.
8. Retirar el resource viejo `koha-ils.xml` (`.135`) cuando el consolidado esté validado.

---

## Puntos abiertos

1. ~~[CIA docentes]~~ — **CERRADO 2026-07-20**: no aplica, no hay discriminador CIA (ver nota superseded al inicio del documento).
2. **[Tesauro]** Curar INEI8 faltantes (14 pregrados) + duplicado (Maestría Salud Pública) + vínculos a facultad. Bloquea reporte consolidado confiable.
3. ~~[Home Teología-Lima]~~ — **CERRADO 2026-07-20**: decidido B (`BUL`, sede real) para toda persona de Teología en Lima. CIA nunca es home library, por decisión explícita de Alberto (extensión de solo lectura abierta a cualquier campus).
4. **[AV valores]** Confirmar listas exactas AREA/CRAI_TIER/TIPO_VINC/SEDE.
5. **[Circulation]** Valores de préstamo/multa por category×itemtype (área biblioteca).

**Artefactos de datos (scratchpad, no versionados):** tabla completa de 96 programas y `final_catalog.json` con inconsistencias — regenerables vía las SPARQL documentadas por `vocbench-expert` contra `Tesauro_Institucional_UPeU`.
