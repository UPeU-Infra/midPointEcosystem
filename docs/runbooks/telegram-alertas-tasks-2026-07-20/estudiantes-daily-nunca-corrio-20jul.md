# `recon-oracle-lamb-estudiantes-daily` nunca corrió en su primer cron — causa raíz y ejecución manual (20-jul-2026)

## Síntoma

La task `recon-oracle-lamb-estudiantes-daily` (oid `9bcfb273-3d8e-4acb-84b0-e7c8b490975b`, resource
`Oracle LAMB Estudiantes v3` oid `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22`) tenía cron `0 20 6 * * ?`
(06:20 hora servidor / 11:20 UTC) con `misfireAction=executeImmediately`, pero a las 14:17 UTC
(3 horas después de su disparo esperado) `lastRunStartTimestamp` seguía vacío — nunca había corrido
ni una sola vez. Sus 2 hermanas (`recon-oracle-lamb-egresados-daily`, `recon-koha-upeu-daily`) sí
corrieron hoy en su horario, sin problema.

## Hipótesis inicial (descartada)

Se sospechó colisión entre el disparo de las 06:20 y el PATCH del fix del filtro de Idiomas al
mismo resource esa mañana (`modifyTimestamp` de la task = 06:31:44, 11 min después del cron).

**Esta hipótesis es INCORRECTA.** Confirmado por auditoría (`ma_audit_event`/`ma_audit_delta` en
Postgres, no solo logs) — nunca hubo colisión con el resource.

## Causa raíz real

La task se creó anoche (2026-07-19 22:03:03 local) con `schedulingState=suspended` **por diseño**
— su propia `description` decía literalmente *"SUSPENDED hasta aprobación explícita de Alberto"*
(documentado también en la memoria de cierre del 19-jul, punto 4 de la sección "Ejecución
autorizada"). Las 4 tasks de reconciliación recurrente se crearon así a propósito, pendientes de
aprobación.

A las **06:31:44 local (11:31:44 UTC)** — 11 minutos después de la ventana de cron de las 06:20 —
alguien (`modifierRef=administrator`, canal `#rest`) hizo un PATCH que cambió
`schedulingState: suspended → ready`. Verificado con el delta de auditoría exacto:

```
itemDelta: path=schedulingState, modificationType=replace,
  estimatedOldValue=suspended, value=ready
```

**Como la task estaba `suspended` en el momento exacto del disparo programado, Quartz nunca tuvo
un trigger activo registrado para ella** (MidPoint retira de Quartz las tasks suspendidas). Por
eso no hay ningún log de misfire, error, ni intento fallido — simplemente nunca hubo un trigger que
"perder". Al pasar a `ready` 11 minutos tarde, MidPoint calculó el siguiente disparo para **mañana**
06:20, no "ahora" — `misfireAction=executeImmediately` solo aplica a triggers que YA estaban
registrados en Quartz y se perdieron por caída del sistema, no a una task recién habilitada después
de que pasó su ventana del día.

No hay ninguna corrupción de schema, ni el nodo (`DefaultNode`, `clustered=false`) tuvo caída —
`docker ps` mostraba `midpoint_server Up 2 days`, sin restart.

## Resolución

Se confirmó salud del resource (`Test Connection` → `success`, schema con `definition` intacta) y
se disparó ejecución manual vía `POST /ws/rest/tasks/{oid}/run` a las 14:25:42 UTC del 20-jul.
Terminó a las 15:05:34 UTC (~39 min), `resultStatus=partial_error`, 24.808/24.925 éxito (99,53%).

## Lección para las 3 tasks hermanas restantes

Cualquier task de reconciliación diaria creada `suspended` y luego aprobada/activada **después**
de su ventana de cron del día no correrá hoy — solo mañana. Si se necesita que corra el mismo día
de la activación, hay que dispararla manualmente una vez (`/run`), tal como se hizo aquí. Vale la
pena, a futuro, agregar una alerta o un check post-activación que dispare automáticamente un `run`
inicial cuando una task pasa de `suspended` a `ready` fuera de su ventana de cron.
