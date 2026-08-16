# Operaciones pendientes que se reintentaban desde mayo — Entra limpiado, Koha viejo abierto

## Qué se vio

La reconciliación de Egresados del 16-ago dejó **201 líneas `ERROR`** de este tipo:

```
java.lang.UnsupportedOperationException: Operation not supported for
ROTD(ACCOUNT:default=…AccountObjectClass) in resource:2f11c057-…(UPEU-EntraID-Graph)
as UpdateCapabilityType is missing
```

No era ruido: cada línea es un **item que falla** en la fase `operation completion` de la
reconciliación, la que reintenta operaciones encoladas.

## Qué eran

**201 shadows de Entra con `pendingOperationCount > 0`** — uno por error. Muestreadas 25:

| | |
|---|---|
| Solicitadas | **25, 26 y 28 de mayo de 2026** — ninguna posterior |
| Intentos acumulados | **70 a 134** por operación |
| Delta | `modify` de `givenName`, `surname`, `displayName` |

Es decir: deltas de nombre encolados a finales de mayo contra un recurso que **no acepta
escritura**, reintentados en cada reconciliación de cada canal durante casi tres meses.

## Por qué no podían funcionar — ni volver a aparecer

El resource `UPEU-EntraID-Graph` (v108) es **de solo lectura por diseño**:

- `create`, `update` y `delete` con `<cap:enabled>false</cap:enabled>`;
- **0 mappings outbound**, 10 inbound.

Son residuo de un episodio anterior al cierre de esas capabilities. Con la configuración
actual **no pueden regenerarse**, así que la limpieza es definitiva y no tapa un origen vivo.

## Limpieza aplicada (16-ago)

`PATCH` con `replace` de `pendingOperation` sin valor, sobre `?options=raw`:

```xml
<itemDelta>
  <t:modificationType>replace</t:modificationType>
  <t:path>c:pendingOperation</t:path>
</itemDelta>
```

Canario de 1 primero (201 → 200, shadow íntegro: `name`, `dead`, vínculo con su owner), luego
el resto: **201/201 aplicados, 0 errores**. Verificado: **0 shadows de Entra con pendientes**,
y los shadows siguen intactos.

Efecto: desaparecen 201 errores por reconciliación y el trabajo inútil que arrastraban.

## Lo que queda abierto

**3.748 shadows del resource `Koha ILS` (el viejo, `9b5a7c81`) con operaciones pendientes.**

No aparecen en los logs porque ese resource está archivado desde el 19-jul y ya no se procesa,
así que hoy no cuestan nada. Son basura de la migración al Koha consolidado, y lo natural es
que se vayan con la purga del propio resource, no con una limpieza aparte. Conviene decidirlo
junto con el retiro definitivo de esa instancia.

## Lección

Una operación pendiente contra un recurso que no puede ejecutarla **no caduca sola**: se
reintenta indefinidamente, suma un `ERROR` por corrida y se cuenta como item fallido. Al
cerrar las capabilities de escritura de un recurso conviene **vaciar lo que quedó en cola**;
si no, el recurso queda "callado" pero su cola sigue gritando en cada reconciliación.
