# Mitigación operativa — desprovisión parcial de `05436990` (User `f849578e`) para detener ruido de Koha (2026-07-25)

## Contexto

Caso ya diagnosticado y CERRADO conceptualmente el 20-jul (ver
`koha-escalamiento-produccion-diagnostico-2026-07-19.md`, entradas "RESUELTO conceptualmente" y
"Faculty/Administrativo Juliaca/Tarapoto CERRADO"): existen dos `ID_PERSONA` distintos en
`ELISEO.VW_APS_EMPLEADO` para la misma persona física ("Ruthy Mamani Jacinto Tafur"), ambos con
contrato marcado `ACTIVO` simultáneamente bajo el mismo `ID_ENTIDAD=7124`:

- `ID_PERSONA=4031567`, `COD_APS='05436990'`, DNI `05436990` → User MidPoint `f849578e-a629-4ec7-8549-993f3e1adbf0`.
  **DNI verificado INVÁLIDO en RENIEC hoy vía apiperu.dev** ("No se encontraron resultados").
- `ID_PERSONA=254553`, `COD_APS='005436990'`, DNI `49096530` → User MidPoint `eda0f988-052e-4c69-9605-37431417169e`.
  **DNI verificado VÁLIDO en RENIEC** ("MAMANI JACINTO DE TAFUR, RUTHY"), 14 assignments, 4 shadows
  reales incluido el patron Koha legítimo (`cardnumber=254553`).

Es un **error de dato en RRHH/Oracle** (duplicado de persona en el origen, posible pago duplicado —
escalado a RRHH por separado), **fuera de alcance de MidPoint**. Alberto autorizó explícitamente
(25-jul) mitigar en MidPoint el ruido operativo que esto genera (intentos fallidos repetidos de
crear cuenta Koha para `f849578e`, 5+ intentos documentados desde 28-may), **sin tocar** el User
válido `eda0f988` y **sin esperar** a que RRHH corrija Oracle.

## Qué se hizo

### 1. Removido permanentemente: `AR-Koha-Patron-Trabajadores` (bridge role Etapa 1)

`f849578e` tenía asignado DIRECTAMENTE (vía REST, 19-jul, batch de Etapa 1 del escalamiento Koha)
el rol puente `AR-Koha-Patron-Trabajadores` (oid `c5a63f02-6b30-4c1b-b3eb-94d526e23dd6`,
assignment `@id=333`). Por diseño explícito de ese rol ("NO existe en ningún
`assignmentTargetSearch`... no debe autoasignarse ni sobrevivir por su cuenta"), su remoción es
**durable** — confirmado sin reaparecer en 3 verificaciones posteriores (versiones 142/145/148/151).

```
PATCH JSON: modificationType=delete, path=assignment, value={id:333}
```

### 2. Intento de remover `BR-Admin-Area` — NO durable, autosana

`f849578e` también recibe `AR-Koha-Patron-Administrativo` (rol de PRODUCCIÓN, oid
`a1b2c3d4-e5f6-7890-abcd-ef1234567803`) de forma **indirecta**, vía inducement de `BR-Admin-Area`
(oid `e8ce3b1b-a53b-4090-b416-ab8d78399e17`), que SÍ está asignado directamente (assignment `@id=1`,
desde el bootstrap del 18-may).

Se intentó remover el assignment `@id=1` (`BR-Admin-Area`) — **se auto-reasignó en el mismo
recompute** (verificado: version 145→148, assignment `@id=1` reaparece idéntico). Causa raíz: el
mapping `D-autoassign-br-admin-area` en `UserTemplate-Person-Base` (oid `855caaca-...`) tiene una
condición que **solo evalúa `extension/primaryAffiliation=='staff'`** — no considera
`lifecycleState` ni ningún flag de exclusión — y Oracle LAMB Trabajadores sigue alimentando
`primaryAffiliation=staff` para este `ID_PERSONA` porque su contrato (erróneo) sigue "activo" hasta
2026-12-31 en el origen.

### 3. Intento de `lifecycleState=archived` — también NO durable, revertido por el propio template

Se probó (experimento controlado, reversible) poner `lifecycleState=archived` directamente sobre
`f849578e`. **El propio `UserTemplate-Person-Base` lo revirtió a `active` en el mismo request**
(confirmado: version 148→151, `lifecycleState` vuelve a `active`) — `lifecycleState` es un campo
**derivado** (de `hireDate`/`terminationDate`, "Trigger Leaver policy ISO 24760"), no editable a
mano mientras Oracle siga mostrando el contrato vigente. Este experimento generó, honestamente, 1
intento fallido adicional de Koha (mismo `AlreadyExistsException` de siempre) — sin otro efecto
colateral (LDAP intacto, sin nuevo shadow).

### Resultado: mitigación PARCIAL pero real

- ✅ **Un vector de Koha eliminado de forma permanente** (el bridge role de Etapa 1).
- 🔴 **El segundo vector (`BR-Admin-Area` → `AR-Koha-Patron-Administrativo`) sigue activo y se
  autosana** — es un rol de PRODUCCIÓN compartido por todo el personal administrativo, correcto
  para el 99,9%+ de sus portadores; no se debe tocar el rol/mapping compartido para excluir a una
  sola persona sin una revisión explícita (blast radius: potencialmente miles de trabajadores).
- La tarea `recon-oracle-lamb-trabajadores-daily` (oid `23b9fde4-...`) está **activa**
  (`schedulingState=ready`), corre diario 06:00 UTC, y es la que re-toca a `f849578e` cada noche
  re-derivando `primaryAffiliation=staff` desde el contrato erróneo de Oracle — por eso el intento
  fallido de Koha seguirá repitiéndose ~1 vez/día (log `partial_error`, sin retry en loop, sin
  impacto en otros sistemas) hasta que se aplique una de las opciones de la sección siguiente, o
  RRHH cierre el `ID_PERSONA=4031567` duplicado en el origen.

## Verificación

- `f849578e` (versión final 151): `linkRef` = 2 shadows sin cambio en TODO el proceso (LDAP
  `04d6ca81-...` + Oracle LAMB Trabajadores `43f0101a-...`, el segundo es de solo lectura/fuente,
  no un target de provisioning) — **nunca se creó ni quedó huérfano ningún shadow Koha** para este
  User, en ningún momento (confirmado también contra `m_shadow` en Postgres).
- `eda0f988` (Ruthy válida): **verificado byte-a-byte idéntico** antes/después — versión 52,
  14 assignments, 4 linkRef, sin ningún cambio.
- Koha real: sin cuenta nueva ni duplicada para `05436990`/`4031567` en ningún momento.

## Pendiente — decisión de Alberto (ninguna de las 2 aplicada hoy)

Para un cierre 100% (cero ruido futuro) sin tocar el rol de producción compartido, las opciones
reales identificadas son:

1. **Excluir esta única fila de Oracle (`ID_PERSONA=4031567`) del alcance de la task
   `recon-oracle-lamb-trabajadores-daily`** (filtro a nivel de la propia task/query, no del
   resource compartido) — más quirúrgico, pero requiere diseño y prueba antes de tocar producción.
2. **Regla de exclusión SoD (`policyConstraints/exclusion`)** asignada solo a este User, contra
   `AR-Koha-Patron-Administrativo` — hay precedente de patrón en el repo
   (`canonical/policies/policy-sod-basic.xml`), pero nunca se ha probado este patrón contra un rol
   de birthright ya asignado estructuralmente (riesgo real: podría convertir el `partial_error`
   tolerado de hoy en un bloqueo duro de todo el recompute del usuario — no probado en vivo, no
   aplicado).

**Ninguna aplicada** — ambas tocan configuración compartida/de producción y ameritan confirmación
explícita antes de desplegar, por la política del repo ("Cambios críticos... pedir confirmación al
usuario antes de aplicar en producción").

**La corrección definitiva sigue pendiente en Oracle/RRHH:** cerrar o fusionar
`ID_PERSONA=4031567` (DNI inválido) contra `254553` (DNI válido, `49096530`, confirmado RENIEC).
Una vez corregido en el origen, el siguiente reconcile debería resolver esto solo, sin intervención
manual adicional en MidPoint.

## Backups

`.backups-prod-p0/2026-07-25-ruthy-05436990-desprovision/`:
- `user-f849578e-PRE-20260725.json` (estado completo antes de cualquier cambio, version 139)
- `user-eda0f988-CONTROL-PRE-20260725.json` (control, version 52 — usado para confirmar cero
  cambios en el User válido)

---

## SESIÓN 2026-07-26 — Opción B probada empíricamente en PROD: NO FUNCIONA. Revertido limpio. Sin cierre definitivo (queda pendiente Opción A, con confirmación explícita antes de aplicar).

Alberto autorizó explícitamente aplicar la opción B (SoD exclusion `policyConstraints/exclusion`,
acotada a un único User, sin tocar `BR-Admin-Area` ni `AR-Koha-Patron-Administrativo`). Se probó
en PROD con evidencia real. **Resultado: NO suprime la construction Koha.** Se revirtió todo de
forma limpia. El sistema queda exactamente como al cierre del 25-jul (mismo estado descrito arriba).

### Qué se probó (3 variantes, las 3 fallaron o resultaron inseguras)

**Backup previo:** `/tmp/koha-mitigacion-check/f849578e-current.json` (version 151, snapshot
inicio de sesión) + snapshot de 3 holders reales de `BR-Admin-Area` (`1b1023e1…`, `fbae2830…`,
`0b15298d…`, versiones 117/105/152) usados como control adicional al `eda0f988` de siempre.

**1. `PolicyType` con `inducement/policyRule/exclusion + enforcement`, asignado DIRECTAMENTE al
User (nuevo objeto standalone `SoD-Excluye-Koha-Administrativo-05436990`, oid
`7d76eee5-3715-43b3-934e-44a3d2d1268f`, en
`upeu/policies/policy-sod-exclude-koha-administrativo-05436990.xml`, commits `994e0e5`/`b3761aa`):**
- Import del objeto: limpio (201, cero referencias de nadie más).
- PATCH assignment (`add`, sin `targetRef` propio, solo el PolicyType) en `f849578e`: **SÍ se
  persistió** (version 151→152, assignment nuevo `@id=418`), sin rechazo por policy violation
  (contrario a lo que se temía en la sesión anterior: la operación NO abortó por completo).
  **Pero tampoco bloqueó nada** — un segundo trigger independiente (touch trivial de
  `description`, forzando un recompute completo nuevo) reprodujo el **mismo
  `AlreadyExistsException` de Koha de siempre**, verificado con evidencia de servidor
  (`org.identityconnectors.framework.common.exceptions.AlreadyExistsException`, mismo endpoint
  `POST http://192.168.12.136:8001/api/v1/patrons`).
  **Conclusión empírica:** el exclusion+enforcement de midPoint 4.10 está diseñado para **prevenir
  la incorporación de un NUEVO conflicto** (SoD dinámico contra un request nuevo), no para
  **bloquear retroactivamente una construction ya inducida de forma estructural** por un rol
  birthright que se re-evalúa igual en cada recompute. Coincide con la sospecha de la sesión
  anterior ("no probado en vivo") — ahora queda refutada en la práctica, no solo como riesgo
  teórico.
- Limpieza: assignment `@id=418` removido de `f849578e` (DELETE `raw`, verificado en Postgres:
  version 156, 6 assignments = exactamente el set original). El objeto `PolicyType` se dejó
  **archivado** (`lifecycleState=archived`, no borrado, para dejar registro histórico del intento;
  cero referencias activas, cero riesgo).

**2. `assignment[1]/activation/administrativeStatus=disabled` vía path anidado
(`"path":"assignment[1]/activation/administrativeStatus"` y variante `"assignment/1/..."`):**
ambas sintaxis fallan con `HTTP 500` — bug/edge-case interno de midPoint 4.10
(`NullPointerException: assignmentValueAfter is null` / "doesn't contain definition for path").
No es un patrón soportado de forma fiable en este deployment. Descartado.

**3. Reemplazo del valor COMPLETO de `assignment[id=1]` con `activation.administrativeStatus:
disabled` (mismo patrón JSON que sí funciona para add/delete por `@id`):** el PATCH se aplicó
(version→159), **pero con un efecto colateral serio**: el mapping `D-autoassign-br-admin-area` (y,
al parecer, TODOS los demás autoassign de `UserTemplate-Person-Base`) no reconoció el assignment
`@id=1` deshabilitado como "ya satisfecho" y **regeneró TODO el bloque de assignments con IDs
nuevos** (462/464/466/468/470/472), incluyendo un **segundo assignment DUPLICADO y habilitado**
hacia `BR-Admin-Area` (`@id=466`) — es decir, el intento de deshabilitar creó una ruta paralela
viva hacia Koha en vez de cerrarla. Confirmado también con un segundo `AlreadyExistsException`.
**Incidente menor autocontenido:** se detectó y remedió en la misma sesión (delete de los 6
duplicados + restauración del `@id=1` original sin el override, ambos vía `raw`); verificado en
Postgres que el estado final es **bit a bit igual al de antes de este experimento** (6 assignments,
mismos oids/ids/tipos, mismos 2 `linkRef`). Cero impacto fuera de `f849578e` en todo momento
(confirmado con los 3 controles + conteo total de holders `BR-Admin-Area`, que solo varió por
crecimiento orgánico ajeno: 8.533→8.543).

### Por qué las 3 variantes fallan (causa raíz común)

El condicionamiento que dispara `BR-Admin-Area` (`primaryAffiliation=='staff'`) vive en
`UserTemplate-Person-Base` (objeto **compartido globalmente**, no solo por este rol) y se
re-evalúa completo en cada recompute a partir del dato de Oracle (que sigue diciendo `staff` para
este `ID_PERSONA`). Cualquier contramedida a nivel de `assignment`/`policyRule` puesta SOLO en el
User se pisa o se rodea en el mismo recompute, porque el template no razona en términos de
"¿hay una exclusión declarada?" — solo en términos de "¿la condición de Oracle sigue siendo
verdadera?". No existe, dentro de lo estrictamente acotado a este User, un mecanismo de
midPoint 4.10 que sobreviva a esa re-evaluación sin tocar el template global (fuera de alcance,
blast radius de TODOS los usuarios) o el rol compartido (prohibido explícitamente).

### Estado final verificado (idéntico al cierre del 25-jul)

- `f849578e`: version 163 (el número sube por el propio historial de cambios/reversiones de hoy,
  pero el **contenido** es idéntico al pre-sesión) — `lifecycleState=active`, 6 assignments
  (`1,2,3,4,111,295`, mismos targets), 2 `linkRef` (LDAP `04d6ca81…` + Oracle LAMB Trabajadores
  `43f0101a…`), **cero shadow Koha** en cualquier momento (verificado exhaustivamente contra
  `m_shadow`/`m_ref_projection` en Postgres, incluyendo búsqueda de huérfanos por cualquier
  variante de DNI/`ID_PERSONA`).
- `eda0f988` (Ruthy válida): **version 52, sin cambios**, byte-a-byte igual que el control
  pre-sesión (4 `linkRef`, incluido el patron Koha real `50e86c3d…`).
- 3 holders reales de `BR-Admin-Area` muestreados como control (`1b1023e1…` v117, `fbae2830…`
  v105, `0b15298d…` v152): **sin cambios**, versiones idénticas antes/después.
- Objeto `PolicyType` `7d76eee5-3715-43b3-934e-44a3d2d1268f`: queda **archivado** en PROD,
  documentado en el repo (`upeu/policies/policy-sod-exclude-koha-administrativo-05436990.xml`),
  sin ninguna asignación activa — inerte, no interfiere con nada.

### Hallazgo operativo lateral (no atribuible a este trabajo)

Uno de los PATCH de prueba tardó **~16 minutos** en responder (REQUEST 03:46:11, EXECUTION
efectiva ~04:02 hora Lima) mientras el servidor mostraba, en paralelo, una tormenta de errores
`HTTP 503 ErrorStoreServerUnavailable` del conector `UPEU-EntraID-Graph` (reconciliación de fondo
contra Microsoft Graph) y al menos un `PolicyViolationException` de un User no relacionado
(`ad239d55…`, conflicto de shadow LDAP duplicado, problema preexistente y distinto). No parece
causado por este trabajo, pero es una anomalía de salud del servidor que Alberto debería revisar
por separado (posible contención de hilos/recursos con RAM 7.5GB).

### Pendiente real (sin cambios respecto al 25-jul, ahora con evidencia adicional)

Con la opción B **descartada por evidencia** (no solo por riesgo teórico), la única ruta que
detendría el ruido de forma duradera sin tocar `BR-Admin-Area`/`AR-Koha-Patron-Administrativo` es
la **opción A**: excluir la fila `ID_PERSONA=4031567` en el propio query/task de origen
(`recon-oracle-lamb-trabajadores-daily` / `upeu/resources/oracle-lamb/trabajadores.xml`), idealmente
como un filtro `protected object` acotado por valor único (no editando el SQL embebido masivo del
`searchScript`, que tiene historial de romperse — ver `docs/runbooks/NUNCA-PUT-resources-schema-cache.md`).
**No se aplicó hoy**, por dos motivos: (1) toca un objeto compartido (el resource), lo cual
requiere confirmación explícita de Alberto antes de tocar producción, igual que se dijo el 25-jul;
(2) **la task `recon-oracle-lamb-trabajadores-daily` sigue `suspended`** (confirmado hoy) —
es decir, **hoy no hay ruido activo real** (el intento fallido de Koha no se está repitiendo a
diario mientras la task esté suspendida), por lo que no hay urgencia operativa que justifique un
cambio apresurado sobre un recurso frágil.

**La corrección definitiva sigue siendo la de Oracle/RRHH** (cerrar/fusionar `ID_PERSONA=4031567`
contra `254553`) — sin cambios respecto al 25-jul.

### Backups de esta sesión

`/tmp/koha-mitigacion-check/` en `midpoint-prod` (no persistido en el repo, solo diagnóstico):
`f849578e-current.json` (v151, inicio), `f849578e-FINAL.json` (v163, cierre),
`br-admin-area-holders-BEFORE.json` (8.533 holders), snapshots de los 3 controles.
