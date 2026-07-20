# Alertas Telegram sobre fallo de tasks — 2026-07-20

## Objetivo

Antes de activar las 4 tasks de reconciliación diaria (`recon-oracle-lamb-trabajadores-daily`,
`recon-oracle-lamb-estudiantes-daily`, `recon-oracle-lamb-egresados-daily`,
`recon-koha-upeu-daily`), cerrar el riesgo identificado: si Oracle LAMB o Koha están caídos
toda la ventana nocturna, hasta hoy no había ninguna alerta.

## Mecanismo elegido

`SystemConfiguration/notificationConfiguration/handler/simpleTaskNotifier` (categoría
`taskEvent`, `status` = `failure` + `onlyFailure`, cubre CUALQUIER task de MidPoint que
termine en fallo, no solo las 4 mencionadas — deliberado, red de seguridad más amplia) →
`transport = custom:telegram-alerts` → `customTransport` con expression Groovy que llama al
API de Telegram (`sendMessage`) vía `java.net.http.HttpClient`.

Bot y chat ya existentes en `~/.secrets/telegram.env` (grupo "SciBack · Pulso").

## Hallazgo empírico crítico (MidPoint 4.10.2)

El prefijo `custom:<name>` en `<transport>` **solo resuelve contra
`notificationConfiguration/customTransport`** (`LegacyCustomTransportConfigurationType`,
marcado `deprecated` desde 4.5 con `plannedRemoval 5.0` en el propio XSD). Definir el
`customTransport` únicamente bajo la forma nueva recomendada por los docs
(`messageTransportConfiguration/customTransport`, `CustomTransportConfigurationType`) **no
funciona**: en runtime tira `WARN LegacyCustomTransport: Custom configuration 'X' not found.
Custom notification to [null] will not be sent.` — el bean que resuelve `custom:` en 4.10.2
sigue siendo el legacy, pese a la deprecación documentada.

Verificado leyendo el schema real desplegado en PROD
(`/opt/midpoint/doc/schema/xml/ns/public/common/common-notifications-3.xsd` dentro del
contenedor `midpoint_server`), no solo la documentación pública — la doc pública describe la
intención de 4.5+, no necesariamente el comportamiento exacto de 4.10.2.

**Consecuencia práctica:** el `customTransport` real y funcional vive en
`notificationConfiguration/customTransport`, con `name` como **atributo XML** (no elemento
hijo) — heredado de `NotificationTransportConfigurationType`. En JSON REST esto se serializa
junto a `expression` en el mismo objeto `value` (no hay wrapper adicional).

Se dejó TAMBIEN configurado el `messageTransportConfiguration/customTransport` nuevo (no
estorba, y es forward-compatible si Evolveum termina de cablear la resolución `custom:` contra
él en una versión futura), pero el que efectivamente dispara el envío hoy es el legacy.

## Verificación realizada (no simulada — prueba dirigida real)

1. Se creó una task desechable (`TEST-alerta-telegram-DESECHABLE-2026-07-20`,
   reconciliation contra un `resourceRef` inexistente) para forzar `fatal_error` de forma
   controlada, sin tocar datos ni resources reales.
2. Primer intento (solo `messageTransportConfiguration/customTransport`): confirmado el bug
   de arriba vía log (`Custom configuration 'telegram-alerts' not found`).
3. Fix aplicado (`notificationConfiguration/customTransport`), task re-ejecutada.
4. Verificación de entrega: canary manual vía `curl` desde **dentro del contenedor
   `midpoint_server`** (mismo runtime exacto que ejecuta el Groovy) antes y después de
   disparar la task real dos veces. El `message_id` de Telegram avanzó exactamente en 2
   (514 → 517, con 2 corridas de la task fallida en medio) — confirma que las 2 alertas
   automáticas SÍ llegaron al canal, no solo el canary manual.
5. Task desechable borrada (`DELETE /tasks/{oid}` → 404 confirmado tras el borrado).
6. Archivos temporales con secretos en `/tmp` del host y del contenedor, eliminados tras la
   prueba.

## Activación de las 4 tasks

Las 4 tasks pasaron de `schedulingState=suspended` a `ready` vía PATCH REST (ver
`upeu/tasks/recon-oracle-lamb-{trabajadores,estudiantes,egresados}.xml` y
`upeu/tasks/reconcile-koha-daily.xml`, actualizados en este commit para reflejar el estado
real en PROD).

Verificado tras la activación:
- `schedulingState=ready`, `executionState=runnable` en las 4.
- Sin `resultStatus` ni entradas de ejecución en el audit log — **ninguna corrió de forma
  descontrolada** (el cron más próximo, 06:00 UTC Trabajadores, cae ~18h después del cambio;
  el momento del cambio fue 2026-07-20 ~11:32 UTC, todos los horarios de las 4 tasks — 06:00,
  06:20, 06:45, 07:15 UTC — ya habían pasado para el día en curso).
- Primera corrida real esperada: madrugada 2026-07-21 (hora Lima).

## Secretos

Token del bot y chat_id NUNCA se comitean — viven solo en `~/.secrets/telegram.env` y en el
objeto `SystemConfiguration` real de PROD (no hay mecanismo de secret-injection sin restart
de contenedor disponible hoy sin tocar `/opt/midpoint/.env` + reiniciar `midpoint_server`, lo
cual requiere confirmación explícita de Alberto por ser un contenedor crítico — se optó por
evitar el restart y aceptar el token embebido en el objeto de configuración de PROD,
consistente con cómo ya se manejan credenciales de resources en este mismo repo).
