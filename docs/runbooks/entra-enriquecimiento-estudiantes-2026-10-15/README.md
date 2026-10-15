# Enriquecimiento de Entra ID (M365) desde MidPoint — estudiantes, prueba con 1 canario (2026-10-15)

Encargo de Alberto (15-oct): «enriquece los datos en M365 con MidPoint, haz 1 prueba primero». Alcance:
dejar el mecanismo listo y probarlo con **un** estudiante. Nada masivo.

Resource `UPEU-EntraID-Graph` (`2f11c057-7b15-4641-a0eb-00c98a6fa4cb`), conector msgraph 1.2.0.0.
**Solo PATCH** (ver [`../NUNCA-PUT-resources-schema-cache.md`](../NUNCA-PUT-resources-schema-cache.md)).

## Qué se escribe (diseño acordado, solo estudiantes)

| Atributo Entra | Valor | Fuente MidPoint | Strength |
|---|---|---|---|
| `employeeId` | ID_PERSONA de LAMB | `extension/upeu:lambIdPersona` | strong |
| `givenName` / `surname` | nombres / apellidos en formato Título | `givenName` / `familyName` | strong (*) |
| `employeeType` | `Estudiante` | constante | strong |
| `jobTitle` | `Estudiante de pregrado` (o el nivel real) | `extension/sb:studyLevel` | strong |
| `department` | `EP ` + nombre de la escuela | org `EP-*` (archetype Academic-Program) en `parentOrgRef` | strong |
| `officeLocation` | `Sede Lima` / `Filial Juliaca` / `Filial Tarapoto` | `extension/sb:campusStudent` | strong |
| `city` | `Lima` / `Juliaca` / `Tarapoto` | `extension/sb:campusStudent` | strong |
| `country` | `Perú` | constante | strong |
| `companyName` | `Universidad Peruana Unión` | constante | strong |
| `usageLocation` | `PE` | constante | **weak** (solo si vacío) |

NO se tocan `userPrincipalName`, `mail`, `proxyAddresses`, contraseña, `accountEnabled`, licencias ni
`displayName`. Nunca DNI, correo personal, teléfono ni fecha de nacimiento (Ley 29733: el directorio lo lee
cualquier usuario del tenant). `tolerant` por defecto (true): si MidPoint no tiene valor, no borra lo que haya.

(*) **Tildes:** si el valor actual en Entra es el mismo nombre y solo difiere en que Entra lleva más tildes
(`Casas Gutiérrez` vs MidPoint `CASAS GUTIERREZ`), se conserva la grafía de Entra. Sin esto, la simulación
quitaba tildes a ~2 % de la población (104 nombres, 189 apellidos).

**`department`:** el `displayName` de la org es «Derecho»; el nombre oficial en LAMB es «EP Derecho» (y así
se enriqueció a mano a 202512090 el 14-oct). Se antepone `EP ` y se quita el sufijo desambiguador entre
paréntesis (`Psicología (FCS)` → `EP Psicología`). 0 o 2+ escuelas → sin valor (no se adivina).

**`usageLocation` weak:** 50 estudiantes enlazados tienen otro país (ES 39, US 7, AR, PL, GB, BO), puesto a
mano, y `usageLocation` condiciona licencias. Strong los habría pasado a PE.

## El GATE (condición de cada outbound)

Escribe **solo** si (1) la persona es estudiante en esta fase (`student` en `sb:affiliations` y afiliación
principal que NO sea `faculty`/`staff`/`employee`) **y** (2) es canario de la lista (`202512190`) o el modo de
ejecución no es persistente (simulación). Cualquier otro caso → `false`. Ante error → `false`.

## Hallazgo que condicionó el diseño: el objectType en `proposed` hace a Entra INVISIBLE en producción

Medido el 15-oct: desde julio (inicio de la retención de auditoría) la recon diaria de Entra **no ha
modificado ni un usuario** (solo eventos `DISCOVER_OBJECT`). Con el objectType en `proposed`, producción no
ejecuta sus inbounds, ni sus reacciones, ni sus outbounds. Consecuencias:

1. El «Entra es IIA strong de `emailAddress`» de la documentación **no está operando desde el 28-may-2026**.
2. Para escribir en Entra hace falta el objectType en `active`. Pero en `active` se activarían también los
   inbounds (entre ellos `icfs:name` **strong** → `$user/name`: renombraría usuarios al prefijo del UPN) y las
   reacciones (link/synchronize/inactivate) en la recon de las 02:00.

Por eso el despliegue va en tres pasos:

| Paso | PATCH | Efecto en producción |
|---|---|---|
| A | `patchA-preparar-outbounds-gate.xml` (v131→v134): 11 outbounds con GATE; los 9 inbounds y las 4 reacciones pasan a `proposed`; `cap:update`=true (create/delete siguen en false) | **ninguno** (objectType sigue en `proposed`) |
| A2 | `patchA2-tildes-usageLocation-weak.xml` (v134→v135): tildes en nombres + `usageLocation` weak | ninguno |
| B | `patchB-ventana-objecttype-active.xml` (v135→v136, 11:32:39): objectType → `active` | solo el GATE escribe (canario) |
| C | `patchC-cierre-objecttype-proposed.xml` (v136→v137, 11:37:32): objectType → `proposed` | vuelta al estado de siempre |

Estado en reposo tras la prueba: objectType `proposed` (Entra invisible en producción, como antes), outbounds
y `update` listos. Para escribir hace falta, además, abrir el objectType: **dos llaves**.

## Respaldo (antes de escribir)

- Resource v131 completo: `~/backups/entra-enriquecimiento-20261015/resource-2f11c057-v131.xml` en el Mac y
  en PROD (sha256 `24e34e59…1f54`, 274 `xsd:element`). Estado final v137 en el mismo directorio.
- Graph (solo lectura, `graph-leer.py`), en `~/backups/entra-snapshots/` (600, **fuera del repo**: datos
  personales): canario antes/después, las 26 cuentas de la muestra y la foto canario+control+Marcos justo
  antes de abrir la ventana.
- `pendingOperation` en shadows de Entra: **0** antes, durante y después (no había cola que reabrir).

## Canario y muestra

- **Canario `202512190`** (pregrado 2026-2): Oracle (solo lectura) confirma Sede Lima, EP Derecho, Pregrado sem.
  283 con 8 cursos. MidPoint: campus LIMA y EP-DER, solo `student`. Shadow de Entra LINKED a su usuario (uid =
  id de Graph). Cuenta habilitada y los 10 atributos objetivo vacíos (`usageLocation` ya era PE).
- **Control negativo `202510303`** (no canario, Sede Lima, EP-MKT, todo vacío en Entra: la simulación le
  escribía 10 atributos).
- **Idempotencia `202512090`** (enriquecido a mano por Graph el 14-oct): MidPoint debe calcular lo mismo.
- Muestra de 26: los 3 anteriores + 3 campus × escuelas distintas, con casos raros: `givenName` igual al UPN
  (`yampier.rodriguez`), `department='San Martin'`, UPN = DNI, apellido con tilde, doble EP (2), afiliación
  principal vacía, `alum`+`student`, y dobles afiliaciones `staff`/`faculty` (deben quedar fuera).

## Simulaciones

1. **Desarrollo** (`task-sim-dev-muestra.xml`, preview + `configurationToUse=development`, v134 y v135):
   26/26 `success`. Se compara Entra atributo a atributo (`simres.py` + `analiza.py`).
2. **Línea base de producción** con el objectType en `proposed` (`task-sim-prod-muestra.xml`): **0** cambios
   en Entra. Fuera de Entra solo 2 Koha `extended_attributes` (`202610900`, `201911756`), que es la reescritura
   diaria ya conocida y no tiene que ver con esto. Canario y control no tenían ningún otro cambio pendiente.
3. **Producción con la ventana abierta** (`task-sim-prod-ventana-muestra.xml`): mismos deltas que en
   desarrollo, y **ningún efecto de inbounds** sobre el foco (ni `name` ni `employeeNumber`).

| Resultado de la simulación (26) | |
|---|---|
| Con cambios en Entra | 23 |
| `202512090` (Marcos) | **0 cambios**: idempotente |
| `202212088` (staff+student), `202015187` (faculty+student) | **0**: fuera por el GATE |
| Doble EP (`200110574`, `200510640`) | sin `department` (no se adivina) |
| `202210308` `surname` «Casas Gutiérrez» | en v134 lo dejaba en «Casas Gutierrez» → **corregido en v135** (se conserva) |
| `department` «San Martin» (2 de Tarapoto) | → su EP |
| Valores «-» (`201911756`) | → valores reales |
| `country` «PE» (`200510640`) | → «Perú» |
| Cambios por atributo | employeeId 23, jobTitle 23, companyName 23, officeLocation 23, city 23, employeeType 23, country 21, department 20, givenName 17, surname 16 |

## Ventana de prueba (15-oct, 11:32:39 → 11:37:32 Lima, sin otras tareas en curso)

| Paso | Resultado |
|---|---|
| PATCH B → v136 | objectType `active`, schema 274, test 15/15 |
| Simulación de producción (26) | como arriba |
| **Control negativo REAL** `202510303` (`task-real-control-negativo.xml`, recompute+reconcile) | `SUCCESS`; Graph **sin cambios**; **0** deltas de auditoría contra Entra; 0 pendientes; 0 eventos de auditoría (no cambió nada en ningún recurso). Hizo un GET a Graph (`retrievalTimestamp` 11:34), que es lo esperado con `reconcile` |
| **Canario REAL** `202512190` (`task-real-canario.xml`) | `SUCCESS`; 1 `MODIFY` a Entra con **exactamente** 10 atributos; ningún delta a LDAP/Koha; 0 pendientes |
| Idempotencia (`task-sim-idempotencia.xml`, canario + Marcos) | **0** cambios |
| Auditoría de toda la ventana | **1** delta contra Entra (el canario) y ninguno más |
| PATCH C → v137 | objectType `proposed`, schema 274, test 15/15, repo == PROD |

Canario en Graph (leído a los ~20 s):

| Atributo | Antes | Después |
|---|---|---|
| givenName | null | Eliezer Faimes |
| surname | null | Palacios Bojorquez |
| employeeId | null | 88442 |
| employeeType | null | Estudiante |
| jobTitle | null | Estudiante de pregrado |
| department | null | EP Derecho |
| officeLocation | null | Sede Lima |
| city | null | Lima |
| country | null | Perú |
| companyName | null | Universidad Peruana Unión |
| usageLocation | PE | PE |
| userPrincipalName / mail / displayName / accountEnabled | — | **sin cambio** |

Rollback del canario si hiciera falta: PATCH a `null` de esos 10 atributos por Graph (estaban vacíos).

## Impacto medido para extenderlo (contra el snapshot de Entra del 7-sep, `impacto.py`)

Hay **12.760** estudiantes con shadow de Entra enlazado; **12.312** pasan el GATE y **448** quedan fuera por
doble afiliación con trabajador.

| Atributo | Rellena vacío | Igual | Sobrescribe | Nota |
|---|---|---|---|---|
| givenName | 6.715 | 1.494 | 2.560 solo mayúsculas + 1.433 distinto | distinto = forma corta (907), el UPN como nombre (513), solape parcial (77); **0 sin solape** |
| surname | 7.820 | 1.499 | 2.554 mayúsculas + 235 distinto | 189 tildes que se habrían perdido, ahora conservadas |
| employeeId | 12.298 | — | — | 14 sin `lambIdPersona` |
| jobTitle | 12.239 | — | 73 | 35 «-», **34 DNI** (+3 códigos o documentos) escritos en `jobTitle` (PII visible para todo el tenant; 195 `jobTitle` numéricos en todo el tenant): se sustituyen |
| department | 9.827 | — | 247 (215 «San Martin», 32 «-») | 2.238 sin EP única: no se tocan |
| officeLocation / city | 12.276 / 12.215 | — / 60 | 36 / 37 («-») | |
| usageLocation | 26 | 12.236 | 0 | weak: los 50 ES/US/… se respetan |

«Sin solape» = 0 significa que, en las 12.312 cuentas enlazadas, ningún nombre de Entra es totalmente distinto
del de MidPoint: no hay indicios de cuentas enlazadas a la persona equivocada.

**Los 4.677** (correos cargados en Oracle el 14-oct, lotes 1+2), cruzados con MidPoint y los shadows:

| Situación | Personas | ¿Se enriquece? |
|---|---|---|
| Correo en MidPoint y shadow LINKED a la misma persona | 2.778 (2.769 pasan el GATE) | sí |
| UPN = DNI (`DNI@`): MidPoint descarta los correos numéricos, así que no correlaciona | 1.689 UNMATCHED + 13 LINKED + 3 | no, hace falta un correlador nuevo |
| Correo OK pero shadow UNMATCHED | 162 | no hasta que se enlacen (las reacciones están en `proposed`) |
| Sin shadow | 31 | no |
| Shadow enlazado a OTRO usuario con el mismo `lambIdPersona` (254473: `001914761` y `202511206`) | 1 | duplicado en MidPoint, revisar |
| Sin usuario | 1 | no |

## Para extender (no hecho; decisión de Alberto)

1. Extender el GATE de «canarios» a la población. Mantener `primaryAffiliation` fuera de trabajador hasta
   decidir qué ficha manda en las dobles afiliaciones.
2. Dejar el objectType en `active` **de forma permanente** cambia la recon de las 02:00: correlaría los ~54.600
   shadows no enlazados y actualizaría situaciones; no escribiría nada porque las reacciones siguen en
   `proposed`. Hay que simularlo primero (recon en preview sobre una muestra de shadows).
3. Aplicar el enriquecimiento con una tarea de recompute+reconcile **por lotes** (cada persona = 1 GET + 1 PATCH a
   Graph; 2 hilos como la recon), no con la recon.
4. Las dos salvaguardas siguen: los outbounds solo actúan sobre cuentas LINKED (UNMATCHED/DISPUTED no tienen
   foco) y no hay outbound de `activation`, así que los ~98 ex-trabajadores con cuenta activa no se tocan
   (ni se deshabilitan ni se enriquecen como estudiantes salvo que lo sean).
5. Correlador por `employeeId` (= `lambIdPersona`) una vez escrito: más robusto que el correo, y la vía para los
   `DNI@`.

## Herramientas

`gen_patches.py` (genera A/A2/B/C; `patchA-…` está tal como se aplicó, antes de A2), `simres.py` +
`analiza.py` (resumen por persona de un `SimulationResult`), `impacto.py` (impacto contra snapshot),
`compara.py` (repo vs PROD sin ids ni comentarios), `verif_ventana.sh` (auditoría/pendientes desde una
hora), `graph-leer.py` (Graph solo lectura con la app MidPoint-UPeU de `~/.secrets/upeu-infra.env`).
Los scripts usan unos *helpers* locales (`ssh.sh`/`rest.sh`/`psql.sh`: SSH a `midpoint-prod` con
`sshpass -e`, credenciales REST por stdin con `curl -K -`, psql en `midpoint-midpoint_data-1`).
Tareas y resultados de simulación **borrados de PROD** al terminar.
