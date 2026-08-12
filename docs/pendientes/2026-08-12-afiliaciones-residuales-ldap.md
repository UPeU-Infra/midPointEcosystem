# Afiliaciones residuales en `ou=people` — limpieza del 12-ago-2026

## El defecto

`eduPersonAffiliation` (resource LDAP, objectType `default`, attribute id 72) tenía
**`tolerant` sin declarar → `true` por defecto** con `strength=strong`. MidPoint **añade**
sus valores calculados pero **nunca retira los ajenos**: cuando alguien dejaba de ser docente
o administrativo, el mapping escribía su nueva afiliación y dejaba la vieja intacta.

Resultado: personas figurando como `faculty` o `staff` en el directorio años después de
terminar su vínculo laboral.

**Corregido:** `tolerant=false` aplicado en PROD (resource v235+).

> ⚠️ `tolerant=false` **solo actúa cuando MidPoint reescribe el atributo**. Si el valor que
> calcula ya está presente no hay delta, no toca el atributo y la intolerancia nunca se
> aplica. Por eso NO basta un recompute ni un import: hace falta un **reconcile** del
> resource. Verificado: recompute → sin efecto; import → sin efecto; `POST
> /shadows/{oid}/reconcile` → 404 (no existe).

## No se puede acotar una reconciliación de este resource

Las tres vías fallan:

| Filtro | Resultado |
|---|---|
| `q:inOid` sobre el shadow | `Cannot combine on-resource and off-resource properties` |
| `attributes/icfs:name` (DN) | `No definition for attribute name` |
| `attributes/ri:uid` | **se ignora en silencio y barre el resource entero** |

El tercero es el peligroso: lancé una recon "de 1 shadow" que empezó a recorrer las 49.222
entradas. Suspendida a los 5.064 objetos, **sin ningún cambio** (la recon lee y solo escribe
donde detecta divergencia). Lección: **verificar el `progress` en los primeros segundos de
cualquier task nueva sobre un resource grande**.

## Limpieza aplicada (directa en LDAP, `ldapmodify`)

Con `tolerant=false` puesto y sin `liveAffiliationWorker`, MidPoint **no recalcula**
`faculty`/`staff` para estas personas: la limpieza directa es estable, no se deshace.

| Grupo | Entradas | Acción | Resultado |
|---|---|---|---|
| Egresados con entrada en `ou=people` | **166** (de 175; 9 ya limpias) | dejar solo `alum` | faculty 0 · staff 0 |
| Estudiantes activos con residuo laboral | **479** | quitar `faculty`/`staff`, conservar `student`+`member`(+`alum`) | faculty 0 · staff 0 · student 479 |

Backups: `/tmp/backup_174.ldif`, `/tmp/backup_479.ldif` (formato LDIF, re-aplicables).
Verificado en **ambos nodos** (.168 y .169).

**Los 479 eran el grupo expuesto**: cuenta viva y habilitada (187 `enabled`) por derecho
propio como estudiantes, con `staff` residual. Ningún control de estado los frena.

### Estado global de `ou=people`

| | Antes | Después |
|---|---|---|
| `faculty` | 1.556 | **1.364** |
| `staff` | 2.744 | **2.263** |
| `alum`+`faculty` | 984 | 813 |

## 🔴 PENDIENTE — 565 archivados, decisión de producto

Ex-trabajadores `lifecycleState=archived`, **513 deshabilitados en LDAP y 0 habilitados**
(52 sin el atributo, anteriores al leaver-gap del 4-ago). No conceden acceso: la cuenta
está cerrada.

**No se limpiaron a propósito.** Al quitar `faculty`/`staff` quedarían:

- 514 con un `member` huérfano (en eduPerson `member` se deriva de una afiliación primaria)
- **51 sin ninguna afiliación**

Sería cambiar un dato obsoleto por uno incoherente. Antes hay que decidir **qué afiliación
corresponde a un ex-trabajador archivado** — `affiliate` es lo canónico en eduPerson — y
aplicarlo en el mapping, no a mano.

## Contraste que queda abierto

`liveAffiliationWorker` en MidPoint: **2.416**. `faculty`+`staff` en LDAP: **3.261**.
La diferencia (~845) son los archivados de arriba más casos por revisar. La reconciliación
completa del resource LDAP, con `tolerant=false` activo, los alinearía de una vez — pero
es una operación sobre 49.222 entradas y merece ventana propia.
