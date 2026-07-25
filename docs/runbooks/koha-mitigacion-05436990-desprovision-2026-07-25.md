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
