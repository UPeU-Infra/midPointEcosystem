# Activación por vínculo vivo — runbook (preparado 22-oct-2026, NO ejecutado)

Rama `fix/activacion-vinculo-vivo` (worktree `.worktrees/activacion-vinculo-vivo`). Todo lo medido aquí es
**solo lectura** sobre PROD (GET `?options=raw`, `SELECT` con `default_transaction_read_only=on`, Oracle `SELECT`,
`ldapsearch`). Antes de ejecutar: `PROTOCOLO-PRE-EJECUCION-PROD.md` y `NUNCA-PUT-resources-schema-cache.md`
(**los 3 resources tocados son PUT-peligrosos: solo PATCH**).

## 1. Qué escribe hoy el estado de la persona (PROD 22-oct)

| Escritor | Objeto / id | Qué hace | Evidencia |
|---|---|---|---|
| Reaction `deleted → inactivateFocus` | Estudiantes `e22` v205, `objectType[3297]/…/reaction[3355]` | `replace administrativeStatus=DISABLED` como **delta primario** (código 4.10 `InactivateFocusAction.prepareContext`) | 85 de los 113 `active+DISABLED` los apagó la recon de Estudiantes |
| Reaction `deleted → inactivateFocus` | Egresados `e23` v211, `objectType[2708]/…/reaction[2758]` | ídem | los 8 egresados `DISABLED` los apagó la recon de Egresados 05→12-ago |
| Inbound `estado-to-administrativeStatus` (strong) | Trabajadores `e21` v330, `attribute[5484]/inbound[5485]` | `ESTADO='A'→enabled`, si no `disabled` | causa de la oscilación (abajo) |
| Template `leaver-disable-on-terminationdate` (strong, condición `terminationDate != null`) | `855caaca` v131, `item[5771]/mapping[5772]` | `DISABLED` si cesó y no le queda vivo; si no `ENABLED` | mantiene ENABLED a 32 ex-estudiantes con 217 rancio |
| Template Bloque L (strong) | `item[5769]/mapping[5770]` | `lifecycleState` desde 216/217/215: vivo→`active`/`draft`; sin vivo→`archived` (con `terminationDate` o evidencia laboral) o `draft` | `draft`/`archived` ⇒ `effectiveStatus=DISABLED` (66.030 users: 0 `draft`/`archived` con effective ENABLED) |
| Trabajadores `deleted → unlink` | `e21 reaction[5536]` | no toca activation (ya es el patrón bueno, gobernanza 2026-05-29) | — |
| Entra inbound `administrativeStatus` (weak) | `2f11c057 inbound[358]` | **inerte**: `lifecycleState=proposed` | ⚠️ si algún día se activa, volvería a ser un escritor automático |
| Outbounds | LDAP `470`/`474` y Zammad `36` sin expresión ⇒ siguen el **effectiveStatus** del foco; Koha `28` calcula su estado **solo desde 216/217/215/guest/bibliotecario**, no del foco | — |

Archetypes, roles, `systemConfiguration`, policies: **ninguno** escribe `activation` ni `lifecycleState` (grep de
`all_roles.xml`, `all_archetypes.xml`, `sysconfig.xml`). Tareas que lo cambiaron (audit, ~3 meses): recon 388.735
eventos, recompute 18.957, REST 825 (todas `administrator`, scripts; 0 desde GUI).

**Cómo se deshabilita hoy un trabajador que cesa:** el searchScript lo mantiene con `ESTADO='I'` 730 días;
`archetype-to-liveAffiliationWorker` devuelve `null` ⇒ 216 vacío ⇒ L lo `archived` (tiene `terminationDate`).
Además el inbound ESTADO escribe `DISABLED`. Si es egresado/estudiante, L lo deja `active` y 5772 lo pone `ENABLED`.
**Un egresado** no se deshabilita nunca por diseño («una vez egresado, siempre egresado», 512 de LDAP).

### La oscilación diaria (medida, `medir-oscilacion.sql`)

| Día | recon Trabajadores → LDAP `disabled` | Egresados / Estudiantes / Koha → LDAP `enabled` |
|---|---|---|
| 19-oct | 1.485 | 996 / 438 / 50 |
| 20-oct | 1.484 | 1.000 / 437 / 51 |
| 21-oct | 1.483 | 853 / 635 / — |
| 22-oct | 1.484 | 969 / 444 / 50 |

Son **1.484 personas, no 1.093**: el 100 % con cuenta Trabajadores `ESTADO='I'`, `terminationDate` y un vínculo
académico vivo (1.041 alum, 343 student, 100 ambos); la predicción por datos da 1.485 y casa 1.484/1.484.
Mecanismo (usuario `201811473`, 22-oct 11:24:19): en el **mismo** clockwork el inbound ESTADO pone `disabled`
(`disableTimestamp` .546), el outbound LDAP se calcula sobre ese estado intermedio (`replace disabled`), y el
mapping 5772 devuelve `ENABLED` (`enableTimestamp` .741). El foco acaba ENABLED; LDAP queda disabled hasta que
otra recon (Estudiantes 11:20, Egresados 12:45, Koha 14:15) lo vuelve a calcular. **Ventana de corte diaria:
~1,5–3 h** para 1.484 personas.

## 2. Diseño elegido

**Un único conductor del estado: `lifecycleState` (Bloque L, ya existe) calculado desde los ítems vivos.
La automatización deja de escribir `administrativeStatus`.** Es lo que dicen las dos skills:
`midpoint-best-practices` §1.2 y regla de oro #3 («Lifecycle se sincroniza desde la fuente; `administrativeStatus`
queda solo como override de emergencia») e `iga-canonical-standards` §1.2 (tabla ISO 24760: active↔enabled,
archived↔disabled). El propio comentario de 5772 ya lo anotaba como «PENDIENTE DE REDISEÑO».

| # | Cambio | Por qué |
|---|---|---|
| R1/R2/R3 | Template: 3 mappings strong que **retiran** 217/215/216 cuando no hay cuenta **viva** de su IIA en el contexto (`midpoint.hasLinkedAccount(oid)`) | En 4.10 el inbound **no corre** para una proyección muerta (`FullInboundsProcessing`: «projection is gone» → se salta), así que el ítem queda rancio. `hasLinkedAccount` mira los projection contexts del clockwork (no `linkRef`): una cuenta recién enlazada (`link`/`addFocus`) cuenta como viva; una muerta (`gone`) o en `unlink`/`delete` no (código `MidpointFunctionsImpl.isProjectionConsideredLinked`). Patrón strong + `null` + `condition` = ya en PROD (`B-email-sanitize-numeric`). |
| ACT | Template: sustituye 5772 por un mapping que **solo borra** `DISABLED` si hay ítem vivo; nunca escribe | Cura sola los 113 `active+DISABLED` y cualquier escritor perdido futuro. Excepción documentada a §1.2: un DISABLED manual sobre una persona viva también se limpia (medido: **0** overrides manuales; el bloqueo de emergencia va por la IIA o `activation/validTo`). |
| e22/e23 | `deleted → synchronize` (en lugar de `inactivateFocus`) | Doc 4.10 schema-handling/synchronization: «The synchronization (mappings evaluation) is driven by the presence of the `synchronize` action»; el unlink del shadow muerto ocurre siempre. En 4.10 `unlink` y `synchronize` son el mismo `BaseClockworkAction` sin preparación; se elige `synchronize` por ser el documentado. Mismo criterio que Trabajadores. |
| e21 | Retirar `estado-to-administrativeStatus` | Elimina el doble escritor ⇒ fin de la oscilación. ESTADO sigue usándose en `archetype-to-liveAffiliationWorker`. |

**Leavers (no se reintroduce el leaver gap):** estudiante que sale del feed ⇒ `synchronize` ⇒ R1 retira 217 ⇒ L
`draft`/`archived` ⇒ effective DISABLED ⇒ LDAP `disabled`, Koha `disabled` (hoy Koha seguía habilitado por el 217
rancio: 85 patrones). Trabajador cesado ⇒ 216 `null` por `ESTADO='I'`/`FEC_TERMINO` ⇒ L `archived` (igual que hoy).
Con otro vínculo vivo, sigue habilitado por ese vínculo. **Vuelta:** la cuenta reaparece ⇒ inbound pone el ítem ⇒
L `active` ⇒ habilitado, sin intervención. Cambio de código (3241… → 2026…): la recon enlaza primero el shadow
nuevo y en la fase de remanentes procesa el muerto ⇒ `hasLinkedAccount` ya es `true` ⇒ no se apaga.

Por qué no «mapping que calcula ENABLED/DISABLED»: escribiría `administrativeStatus` a ~34k usuarios sin cambio
efectivo y mataría el override manual; L ya da el mismo `effectiveStatus`.

## 3. Efecto medido sobre los 66.030 usuarios (sin MidPoint, `ds.sql` + `predecir.py`, 22-oct ~21:00 UTC)

| Clase hoy (lc, 216/217/215 vivos) | eff hoy → nuevo | n |
|---|---|---|
| active, solo 217, **cuenta e22 viva**, DISABLED | DIS → **ENA** | 35 |
| active, 217+215, DISABLED | DIS → **ENA** (1 con e22 viva; 3 egresados con 217 rancio) | 4 |
| active, solo 215, DISABLED (cuenta e23 viva) | DIS → **ENA** | 8 |
| active, solo 217 **sin cuenta e22**, DISABLED | DIS → DIS (active→draft) | 65 |
| active, solo 217 **sin cuenta e22**, ENABLED | **ENA → DIS** (active→archived) | 32 |
| active, sin vivo (202512729, congelado) | ENA → DIS (latente de L, ajeno; **excluido**) | 1 |
| active, solo 215 sin cuenta e23 (323100157) | DIS → DIS (→draft) | 1 |
| active, staff/alum + 217/216 rancio (4) | ENA → ENA (pierden student/staff) | 4 |
| resto (27.919 alum, 16.771 student, 3.512 con worker, 5.954 archived, 10.688 draft…) | sin cambio | 65.880 |

Totales: **47 DISABLED→ENABLED**, **33 ENABLED→DISABLED** (32 + el excluido), 99 cambios de lifecycle, 105 ítems
retirados (S 103, A 1, W 1), `primaryAffiliation` 104 cambios (student→∅ 97, student→alum 5, staff→alum 1, alum→∅ 1).

**Contraste con Oracle (los 150 afectados, `PERSONA_NATURAL_ALUMNO.CODIGO` × contratos ≥ sem. 267):**
- 33 → DISABLED: **33/33 sin matrícula vigente** (último fin 2026-07-03…08-21; 202520474 y 202613145 con
  contrato futuro pero **ningún curso ESTADO='1'**). Lista con justificación: `lotes/pasan-a-DISABLED.tsv`.
- 47 → ENABLED: **36 con cursos vigentes hoy** (= los 12 de cambio de código + 24 retomados del diagnóstico);
  11 egresados con cuenta e23 viva. Lista: `lotes/pasan-a-ENABLED.tsv`.
- 70 retiros sin cambio de estado: ninguno vigente; 6 «zona gris» con contrato/cursos `M` (4) o contrato `0`
  sin cursos (2) — el feed exige `ESTADO='1'`, el diseño sigue a la IIA ❓ semántica de `M`.

**Sistemas:** LDAP real (.168, `ldap-afectados.sh`): `ou=people` 39 disabled→enabled y 33 enabled→disabled;
`ou=alumni` 11 disabled→enabled; 65 siguen disabled. **Además deja de oscilar** la cuenta LDAP de 1.484 personas.
Koha: **85 patrones enabled→disabled** (todos ex-estudiantes con 217 rancio; incluye a Hulda, ver §6), 0
habilitaciones nuevas por el diseño. Zammad: 0 (ningún afectado tiene cuenta). Entra: inerte (`proposed`).
Quién lo aplicaría solo: recon Koha 85, Estudiantes 37, Egresados 14, Trabajadores 1, **nadie 13** (solo recompute).

## 4. Cambio preparado

Commit local en `fix/activacion-vinculo-vivo` (sin push): template (bloques R y ACT, cabecera), `estudiantes.xml`,
`egresados.xml` (`deleted → synchronize`), `trabajadores.xml` (sin inbound ESTADO). El repo refleja el estado
**final**; PROD se lleva ahí en 3 pasos por PATCH con `lifecycleState` (doc 4.10 *Simulation*: «active y
deprecated = configuración de producción; proposed y active = de desarrollo»).

| Objeto (versión medida) | Paso 1 — inerte en producción | Paso 2 — activar | Paso 3 — limpieza (≥7 días) |
|---|---|---|---|
| Template `855caaca` (v131) | `patch-01`: +item 5830/5831 (R1), 5832/5833 (R2), 5834/5835 (R3), +`item[5771]/mapping` 5836 (ACT) `proposed`; 5772 `deprecated` | `patch-11`: nuevos `active`, 5772 `archived` | `patch-21`: borra 5772 |
| Estudiantes `e22` (v205) | `patch-02`: +reaction 3379 (`synchronize`, action 3380) `proposed`; 3355 `deprecated` | `patch-12` | `patch-22` |
| Egresados `e23` (v211) | `patch-03`: +reaction 2765 (action 2766) `proposed`; 2758 `deprecated` | `patch-13` | `patch-23` |
| Trabajadores `e21` (v330) | `patch-04`: inbound 5485 `deprecated` | `patch-14`: `archived` | `patch-24` |

Vuelta atrás: paso 2 → `patch-81..84`; paso 1 → `patch-91..94` (borrado por `@id` ❓ no probado en 4.10: si la
versión no sube, alternativa equivalente = dejar los nuevos en `archived`). Datos → `restore-datos.py`.
IDs nuevos elegidos > máximo actual (template 5829, e22 3378, e23 2764): **tras el paso 1 comprobar con
`verificar.py` que PROD respetó los ids**; si no, corregir `patch-1x/8x/2x` antes de seguir.

## 5. Ejecución (ventana: 16:10–07:00 UTC; recons 07:00 Entra … 14:15–16:03 Koha)

```bash
# Mac. Previo: Alberto revisa/mergea la rama; push; luego en PROD:
source ~/.secrets/midpoint-upeu.env
SSH() { SSHPASS="$MIDPOINT_PROD_PASS" sshpass -e ssh -o ProxyJump=none -o NumberOfPasswordPrompts=1 -o StrictHostKeyChecking=no juansanchez@192.168.15.166 "$@"; }
RB='~/midPointEcosystem/docs/runbooks/activacion-vinculo-vivo-2026-10-22'
cred() { printf '%s:%s\n' "$MIDPOINT_ADMIN_USER" "$MIDPOINT_ADMIN_PASS"; }   # rest.sh la lee por stdin: nunca en argv
SSH "cd ~/midPointEcosystem && git pull --ff-only && git log --oneline -1"
```

**5.1 Respaldo** (Permission denied ⇒ esperar 90 s, 1 reintento):
```bash
cred | SSH "cd $RB && ./backup-pre.sh"          # template/resources raw + estado-pre.tsv.gz + SHA256SUMS
./ldap-afectados.sh 168 > /tmp/ldap-168-pre.tsv; ./ldap-afectados.sh 169 > /tmp/ldap-169-pre.tsv; diff /tmp/ldap-16{8,9}-pre.tsv
```
**5.2 SIM-0** (config producción, antes del paso 1) — separa los cambios latentes (lección j3b):
```bash
python3 gen_tasks.py /tmp/avv-tasks && SSH "mkdir -p /tmp/avv" && for f in /tmp/avv-tasks/*.xml; do SSH "cat > /tmp/avv/$(basename $f)" < $f; done
SSH "curl -s -u '$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS' -X POST -H 'Content-Type: application/xml' --data-binary @/tmp/avv/task-sim-0-prod-muestra.xml http://localhost:8080/midpoint/ws/rest/tasks -D - -o /dev/null | grep -i location"
# al terminar: oid del SimulationResult y lectura
SSH "docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' midpoint-midpoint_data-1 psql -U midpoint -d midpoint -X -A -c \"select oid,nameorig from m_simulation_result where nameorig like '%activacion-vinculo-vivo%' order by createtimestamp desc limit 3\""
SSH "docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' midpoint-midpoint_data-1 psql -U midpoint -d midpoint -X -v sim=\"'<OID>'\"" < medir-sim.sql > /tmp/sim0.txt
```
**5.3 Paso 1** (inerte) y verificación por objeto — un 204 no prueba nada (R8):
```bash
cred | SSH "cd $RB && ./rest.sh objectTemplates 855caaca-68c4-4f7f-8ff8-b4e35dd7d390 patch-01-template-proposed.xml"   # 131 -> 132
cred | SSH "cd $RB && ./rest.sh resources 6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22 patch-02-e22-reaction-proposed.xml"       # 205 -> 206
cred | SSH "cd $RB && ./rest.sh resources 6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23 patch-03-e23-reaction-proposed.xml"       # 211 -> 212
cred | SSH "cd $RB && ./rest.sh resources 6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21 patch-04-e21-estado-deprecated.json"      # 330 -> 331
G() { SSH "curl -sf -u '$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS' -H 'Accept: application/xml' 'http://localhost:8080/midpoint/ws/rest/$1?options=raw'" > /tmp/$2.xml; }
G objectTemplates/855caaca-68c4-4f7f-8ff8-b4e35dd7d390 tpl && ./verificar.py /tmp/tpl.xml 5831=proposed 5833=proposed 5835=proposed 5836=proposed 5772=deprecated 5770=active
G resources/6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22 e22 && ./verificar.py /tmp/e22.xml 3379=proposed 3355=deprecated
G resources/6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23 e23 && ./verificar.py /tmp/e23.xml 2765=proposed 2758=deprecated
G resources/6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21 e21 && ./verificar.py /tmp/e21.xml 5485=deprecated
# xsd:element debe ser igual al respaldo; test connection de los 3:
for r in 21 22 23; do SSH "curl -s -u '$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS' -X POST http://localhost:8080/midpoint/ws/rest/resources/6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e$r/test" | grep -o 'status>[a-z_]*' | sort | uniq -c; done
```
**5.4 SIM-1** (producción, tras paso 1) = mismo resultado que SIM-0 (prueba de inercia). **SIM-2** (desarrollo):
GO solo si por clase coincide con §3: 104-C/104-D → `administrativeStatus` borrado y LDAP people `enabled`; 104-E y
`ENA2DIS` → `liveAffiliationStudent` borrado, `lifecycleState` draft/archived **en la misma operación**, LDAP
`disabled`, Koha `disabled`; `DIS2ENA-alum` y los 3 egresados → LDAP alumni `enabled`; **controles: 0 cambios**
de activation en `CTRL-*` (oscilantes, cesados, egresados, estudiantes y trabajadores activos, draft, svc).
Efecto no previsto = pregunta (R7). ❓ a confirmar aquí: que el template honra `proposed` en desarrollo (si SIM-2
no cambia nada, no lo honra ⇒ NO-GO y replantear) y que L ve la retirada de R1 en la misma pasada.
**SIM-3** (`task-sim-3-dev-recon-trab.xml`, ~35 min): 0 cuentas LDAP a `disabled` entre los 1.484
(`lotes/oscilantes-1484.oids`); bajas reales del día sí. ⚠️ una recon en preview gestiona shadows (precedente 4-ago).

**5.5 Datos previos**: Hulda (§6) antes del paso 2.
**5.6 Paso 2** (`patch-11..14` con `rest.sh`; `verificar.py` con `active`/`archived`; test connection).
**5.7 Canario real** (`task-real-canario.xml`, 8): por cada uno, foco (`m_user`), LDAP .168 = .169 y Koha.
**5.8 Lote** `task-real-L1-01/02.xml` (142, 2 hilos). Excluidos: `lotes/excluidos.oids`.
**5.9 Medición**: `medir-estado.sql` (esperado R1≤1, R2 0, R3 0, ACT 0), `ds.sql`+`predecir.py` (0 cambios
pendientes), `ldap-afectados.sh` post; `medir-deltas-ventana.sql` de j3b para ver que no hubo deltas a Entra/Zammad.
**Día siguiente** (tras 11:00–16:03): `medir-oscilacion.sql` ⇒ Trabajadores→LDAP DIS de ~1.484 a solo las bajas
del día. Solo con las recons, tras el paso 2, se aplican: 37 (Estudiantes), 14 (Egresados), 85 (Koha), 1
(Trabajadores) y la oscilación; **13 solo con el recompute** (por eso el lote).
**5.10 Paso 3** a los ≥7 días sin incidencias: `patch-21..24`, así PROD == repo.

## 6. Datos (aparte del mecanismo)

| Grupo | n | ¿Lo resuelve el mecanismo? |
|---|---|---|
| Vigentes (12 cambio de código + 24 retomados) | 36 | **Sí**: ACT borra el DISABLED (recon Estudiantes o lote). Sin PATCH puntual. |
| 217 rancio no matriculados | 67 | **Sí**: R1 retira 217 ⇒ draft. Los 6 «M/0» se tratan igual (siguen a la IIA); si Académico confirma que `M` es matrícula válida, el arreglo es el `searchScript` y volverán solos. |
| Egresados apagados con 217 rancio (201122601, 201711925, 202622832) | 3 | **Sí**: R1 retira 217, ACT borra DISABLED ⇒ ou=alumni `enabled`. |
| Egresados apagados por Egresados 05→12-ago | 8 | **Sí** (no estaban en los 104). |
| Hulda (d838c216 `202321001` / c7a03760 `200310031`) | 1 | **No**: requiere fusión **antes** del paso 2 (si no, R1 le retira 217 y Koha 28930 —vigente, posgrado 283— se deshabilita). |
| 201811693 (ficha duplicada de ID_PERSONA 77791; el contrato vivo está en `75609890`) | 1 | R3 le retira el `staff` rancio (lo hará la recon de Egresados); la persona conserva `staff` en 75609890. Fusión aparte. |

**Hulda, medido:** Oracle `ID_PERSONA 8070` = Hulda Gisella Arévalo Castro, DNI **42542948**, código PNA
**200310031**; `34379` es fantasma (sin nombre). `c7a03760` (name 200310031, cuenta e23 200310031 con idp 8070,
LDAP alumni, Entra) lleva idp/doc **rancios** 34379/42542946. `d838c216` (name 202321001, código viejo) lleva
idp 8070 y DNI correctos, LDAP `uid=202321001,ou=people` y Koha 28930 (`cardnumber=8070`). El shadow e22
`200310031` (vigente hasta 2026-12-29) está **UNLINKED** por el conflicto de nombre. Superviviente:
**c7a03760** (su `name` es el código vigente). Secuencia (cada paso con preview `explicitChangeExecution` antes,
lección 201810596: **nunca** vaciar y reconciliar en la misma operación):
1. Respaldo GET raw de ambos.
2. En d838c216: `delete linkRef` de Koha 28930 y LDAP `b685bfd2` con `?options=raw` (sin clockwork).
3. En c7a03760 (no raw, preview→real): `replace` directo de `lambIdPersona`=8070, `lambDocNum`=42542948,
   `externalSystemId`=8070 (no vaciar); `add linkRef` Koha 28930. Esperado: Koha userid 202321001→200310031.
4. Import del shadow e22 `200310031` (o esperar la recon): enlaza a c7a03760 ⇒ 217 ⇒ entrada `ou=people` nueva.
5. d838c216 sin cuentas: preview de borrado del foco; si no, `archived` + quitar idp/doc en raw (evita disputa
   por `lambIdPersona`). `uid=202321001,ou=people` queda huérfana y `disabled` (no hay `delete` en LDAP).

## 7. Abierto ❓
- Template + `proposed`/`deprecated` en simulación de desarrollo: documentado para «mappings»; no comprobado
  para mappings de object template (lo decide SIM-2).
- Orden R → L → ACT en la misma pasada (el sorter de dependencias; R es fuente=destino como B-email-sanitize).
  Si L no ve la retirada, la persona queda `active` hasta el siguiente procesamiento (SIM-2 lo mide).
- `add` con `id` explícito en el PATCH y `delete` por `@id` en JSON: verificar con `verificar.py`.
- Semántica de `ACAD_CURSO_ALUMNO.ESTADO='M'` (6 casos).
- Riesgo heredado, no introducido: si la vista de Egresados volviera vacía sin error, todos pasarían a `deleted`
  (hoy: apagado masivo; con el diseño: retirada masiva de 215). Proponer umbral en la tarea de recon.
- Riesgo heredado: el template por defecto de UserType (`855caaca`) aplica a `administrator` (lifecycle null,
  nunca recomputado): un recompute lo llevaría a `draft` por L. Ninguna tarea del runbook lo incluye.
- Drift repo↔PROD previo: `trabajadores.xml` (faltan `correlate-by-lamb-id-persona`,
  `guardarrail-homonimo-abre-caso`) y `egresados.xml` (`escuela-to-*`, `sede-to-campusEgreso`). No afecta: se
  despliega por PATCH de elementos concretos.

## 8. v2 (23-oct) — por qué el paso 2 no hizo nada y la corrección

**Hecho medido.** Paso 2 activo 13:16:50–13:52:59 UTC. Canario `7b605ba4` (recompute, reconcile=false, 8): SUCCESS,
1 solo delta (202514113: `expiry_date` de Koha 2027-10-22→23, rodante, ajeno). Recon de Egresados en la ventana: 0
cambios de 217/215/216/estado. Log 13:16–13:21: ningún WARN de R*/ACT (las condiciones se evaluaron sin excepción).

**Causa (código v4.10.2, no hipótesis).** R1/R2/R3/ACT eran *no-op por construcción*:
- `AbstractMappingImpl.evaluate` (l. ~839-854): condición cierta ⇒ la expresión `null` deja el triple vacío; con la
  condición constante el resultado va al *zero set* — no hay *minus*.
- Lo único que convierte un valor existente en *minus* es el **rango**: `checkExistingTargetValues` (l. 956-1016) →
  `addToMinusIfNecessary` (l. 1145-1177). Sin `<target><set>` el rango implícito es `matchingProvenance` **solo si el
  ítem es multivalor** (`shouldUseMatchingProvenance`, l. 1714). `liveAffiliation*` y `administrativeStatus` son
  single-valued ⇒ «No range set definition, skipping range check».
- `IvwoConsolidator` (l. 255-279 y ~570): un valor existente sin origen plus/minus/zero «se conserva tal cual».
  El borrado de existentes sin origen (`deleteExistingValues`) solo lo usan los inbounds (`AbstractInboundsProcessing` l. 189).
- Descartado: `lifecycleState` del mapping **sí** se respeta (`FocalMappingSetEvaluation` l. 229 `task.canSee`);
  `hasLinkedAccount` funcionaba (202514113/202622704 no tienen linkRef a e22 ⇒ condición true) — no era el problema.
  ⇒ **SIM-2 sí aplicó los `proposed`; no cambió nada porque los mappings no hacían nada.** La simulación de desarrollo
  vuelve a ser válida para validar el template.
- El patrón correcto ya estaba en este template: `E2-retract-orphan-*` y `J3b` (rango, probado en PROD).

**Corrección (rama `fix/activacion-vinculo-vivo-v2`).** R1v2/R2v2/R3v2/ACTv2: sin `source` ni `condition`, expresión
`null`, y la guarda **dentro de `<target><set><condition>`** (el rango se evalúa aunque el mapping no aplique, MID-5953).
- R: `input` presente y `!midpoint.hasLinkedAccount(<IIA>)`.
- ACT: `input == DISABLED` y algún vínculo vivo = ítem presente **y** cuenta de su IIA enlazada (no depende del
  orden respecto a R). Rango evaluado solo en estado *new* (`skipEvaluationMinus`, `SingleShotEvaluation`).
- `CANARIO = [...]` en el rango: con nombres, el mapping **no puede tocar a nadie más** (ni recon ni recompute).
- Cada retirada/limpieza deja `WARN (com.evolveum.midpoint.expression): R1v2: retira …` / `ACTv2: limpia …`.
- Generador único: `v2_mappings.py` + `v2_build.py <dir>` (regenera los patch v2).

| Patch | Qué | Efecto en producción |
|---|---|---|
| `patch-31-template-v2-proposed.xml` | +5840..5843 (acotados, CANARIO) y +5844..5847 (globales), todos `proposed`; v1 5831/5833/5835/5836 → `archived`; 5772 → `deprecated` | Ninguno (proposed invisible; deprecated sigue visible) |
| `patch-32-template-v2-canario-activar.json` | 5840..5843 → `active` | Solo los 8 nombres de CANARIO |
| `patch-72-template-v2-canario-rollback.json` | 5840..5843 → `archived` | Vuelta atrás del canario |
| `patch-41-template-v2-global-activar.json` | 5844..5847 → `active`; 5840..5843 y 5772 → `archived` | Global (+ `patch-12/13/14` para reactions y e21) |
| `patch-81v2-template-global-rollback.json` | 5772 → `active`; 5844..5847 → `proposed` | Vuelta atrás global (+ `patch-82/83/84`) |
| `patch-91v2-template-v2-retirar.json` | 5840..5847 → `archived`; 5772 → `active` | Deja PROD como hoy |

**Procedimiento v2** (`date -u` antes de CADA paso; ventana 16:10–07:00 UTC; `rest.sh` = PATCH y versión antes/después):
1. *(fuera de ventana vale, solo lectura)* `snapshot-estado.sql` → `snap-pre.tsv`; GET raw del template (respaldo).
2. **[ventana]** `rest.sh objectTemplates 855caaca-… patch-31-template-v2-proposed.xml` (v134→135);
   `verificar.py tpl.xml 5840=proposed 5841=proposed 5842=proposed 5843=proposed 5844=proposed 5845=proposed 5846=proposed 5847=proposed 5831=archived 5833=archived 5835=archived 5836=archived 5772=deprecated 5770=active`.
3. **[ventana]** `task-sim-4-dev-canario.xml` y `task-sim-2-dev-muestra.xml` (preview, desarrollo). GO solo si:
   202014210/202622500/201610032 → `administrativeStatus` borrado; 201122601 → sin 217 y sin DISABLED;
   202514113 → sin 217, `archived`; 202622704 → sin 217, `draft`; controles 0 cambios; muestra ≈ §3 por clase.
   (Ruido conocido: Entra `proposed` genera altas ficticias en desarrollo.)
4. **[ventana]** `patch-32` (v→+1, `verificar.py 5840..5843=active`), luego `task-real-canario.xml`. Verificar en
   `m_user`, LDAP .168=.169 y Koha los 8; `docker logs --since 10m | grep -E 'R[123]v2|ACTv2'` = solo nombres del
   CANARIO. Si algo no cuadra: `patch-72` + `restore-datos.py` en el acto.
5. *(recons diarias, fuera de ventana: es seguro, el rango no puede salir del CANARIO)* ≥1 ciclo completo
   (Estudiantes 11:20, Egresados 12:45, Koha 14:15–16:03). Luego `snapshot-estado.sql` → `snap-post.tsv`, `diff`
   (fuera del CANARIO solo cambios de las IIA del día) y `grep R[123]v2|ACTv2` del log del ciclo = solo CANARIO.
6. **[ventana]** Global: `patch-41` + `patch-12/13/14`; `task-real-L1-*`; §5.9. Vuelta atrás: `patch-81v2` + `patch-82/83/84`.
7. Limpieza ≥7 días: borrar 5831/5833/5835/5836/5840..5843/5772 (PATCH `delete` por id; antes comprobar en un
   objeto de prueba que `delete` por `@id` sube la versión).

**No cubierto por el canario acotado (❓):** el cambio de reactions `deleted → synchronize` y la retirada del inbound
ESTADO de e21 se activan solo en el paso global. Las reactions sin canal se eligen por «la última que casa»
(`SynchronizationActionExecutor.getReaction`): acotar 3379/2765 con `condition` sería seguro para terceros, pero su
efecto en el canario depende del orden de la lista (no verificado), por eso no se incluye.
