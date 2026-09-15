# ADR-066 — Los equipos del DTI se unifican sobre `serviceDeskTeam`; manda el modelo del director

**Fecha:** 15-sep-2026 · **Estado:** **aplicado y verificado** (15-sep-2026, 41/41)
**Supersede:** [`ADR-065`](ADR-065-equipos-desarrollo-dti.md) — propuesto y **descartado**
**Continúa:** [`runbooks/gobierno-grupos-dti-canario-2026-09-03.md`](../../runbooks/gobierno-grupos-dti-canario-2026-09-03.md)

## Qué se decidió y por qué

El ADR-065 proponía una segunda dimensión (OrgType + roles + grupos nuevos en paralelo a los 22
del canario). Se descartó al contrastar persona a persona las dos listas: **no son taxonomías
distintas, son la misma con el corte desactualizado.** LAMB Financiero coincidía 7 de 7 con el
modelo del director; LAMB Académico coincidía salvo los dos que él mueve desde Mantenimiento.
Montar una segunda dimensión habría creado justo la doble autoridad que el canario del 03-sep
evitó a propósito.

**Decisión: una sola autoridad, `extension/upeu:serviceDeskTeam`, y la verdad es el modelo
validado por el director David Jefferson Barrantes Delgado.** El dato se corrige para reflejarlo;
las colas de Zammad se reorganizan solas porque beben del mismo dato.

## Lo aplicado

| # | Qué | Cómo |
|---|---|---|
| 1 | `AR-DTI-Team-conservatory` (`…00000027`, identifier `Conservatory`) | POST 201 |
| 2 | `AR-DTI-Team-devops` (`…00000028`, identifier `DevOps`) | POST 201 |
| 3 | `cn=dti-conservatory` y `cn=dti-devops` (`groupOfUniqueNames`, `ou=groups`) | `ldapadd` |
| 4 | 7 personas cambian de `serviceDeskTeam` | PATCH `replace` |
| 5 | `AR-DTI-Team-seguridad-informatica`: `displayName` + archetype (**el `subtype` NO**, ver abajo) | PATCH ×2 |

Los dos roles nuevos **no llevan `inducement` de cola Zammad**: `Conservatory` y `DevOps` no
existen entre las 26 colas de `servicedesk.upeu.edu.pe`. Se añadirá cuando se creen.

### Los 7 movimientos

| Código | Persona | Desde | Hasta |
|---|---|---|---|
| 201611794 | Owen Mejía | Desarrollo · LAMB Admisión | Desarrollo · LAMB Admisión (events) |
| 201011058 | Jack Castillo | Desarrollo · LAMB Admisión (events) | Desarrollo · Aplicaciones |
| 201110708 | Diana García | Desarrollo · LAMB Mantenimiento | Desarrollo · LAMB Académico |
| 200510795 | Willy Medina | Desarrollo · LAMB Mantenimiento | Desarrollo · LAMB Académico |
| 201610466 | Jhon Mendieta | Desarrollo · LAMB Mantenimiento | Conservatory |
| 201811327 | Anderson Lopez | Desarrollo · LAMB Admisión | Conservatory |
| 9610165 | Juan Alberto Sánchez | Infraestructura TI | DevOps |

**El orden no era libre.** `dti-desarrollo-lamb-admision-events` tenía un solo miembro (Jack) y
`uniqueMember` es MUST en `groupOfUniqueNames`: se metió a Owen **antes** de sacar a Jack, para
que no quedara vacío ni transitoriamente. Verificado en LDAP entre paso y paso.

## Las cuatro de fuera del modelo NO se tocan

Mirian Calcina (201322759), Ruth Fuentes (200010139), Carla Esquivel (202116492) y Zulin Vallejos
(202210579) no aparecen en el modelo del director. Se quedan donde estaban hasta preguntarle.
Consecuencia buscada: `lamb-mantenimiento` (1), `lamb-admision` (1) y `ux-ui` (2) **siguen
existiendo** y nadie pierde acceso por un modelo que no lo contemplaba.

## Los jefes: no se escriben, y eso es la decisión

El modelo define jefe para 6 de los 9 equipos. **Con RoleType no hay sitio canónico donde ponerlo,
y no se inventa uno.**

- `relation=org:manager` está definido sobre **unidades organizativas**. El rector lo dice citando
  el libro (D5): *«MidPoint assigns managers to organizational units. That is the right way to do
  it.»* Sobre un RoleType no alimenta organigrama ni aprobación: sería semántica falsa.
- `ownerRef`/`relation=org:owner` tampoco: [`ADR-064`](ADR-064-politica-owner-roles.md) ya
  estableció que estos 22 son *application roles* y **su owner es el responsable de la aplicación,
  no un jefe de personas**.

El sitio natural, cuando exista, es el que el propio ADR-064 anticipa: **un `approver` por equipo
(el coordinador)**, con una `relation` distinta de `org:owner`. Queda para la reunión con Urquizo,
junto con la política de owner. **El dato no se pierde**: vive en
[`upeu/roles/dti-teams/modelo-organizacion-dti-VALIDADO.json`](../../../upeu/roles/dti-teams/modelo-organizacion-dti-VALIDADO.json)
y en el Excel del director.

## Verificación (41/41, releyendo LDAP y MidPoint)

Cruzada, no por totales: para cada una de las 27 se comparó su grupo real en LDAP contra el
`serviceDeskTeam` real en MidPoint, resuelto por el modelo del director.

| Criterio | Resultado |
|---|---|
| 27 personas en su equipo y en ningún otro `dti-desarrollo-*` | **27/27** |
| 9 grupos del modelo con el número exacto del modelo | 9/9 (9·7·2·2·2·2·1·1·1) |
| 4 de fuera del modelo intactas | 4/4 |
| Ningún grupo `dti-*` vacío | 25 grupos, 69 membresías, 0 vacíos |

## 🔴 `AR-DTI-Team-seguridad-informatica`: la ausencia de `subtype` es el mecanismo, no un bug

**Rectificación.** Durante este lote se le puso `subtype=dti-service-desk-team` leyéndolo como un
descuido. **Era deliberado y estaba escrito dentro del propio objeto.** Revertido el mismo día con
un PATCH que retira solo el `subtype`; `displayName` y el archetype se dejaron puestos, porque la
justificación no los ampara y añadirlos es inocuo.

Lo dice su `description` (y, en los mismos términos, la del grupo LDAP):

> «**NO ES UN EQUIPO DE AREA. Es una RESPONSABILIDAD DE TURNO**: sus integrantes pertenecen a
> areas distintas (Infraestructura TI, Redes y Conectividad, Direccion DTI) y su
> `extension/upeu:serviceDeskTeam` nunca dira "Seguridad Informatica". **Por eso este rol NO lleva
> subtype dti-service-desk-team y queda deliberadamente FUERA del autoassign**
> `T-autoassign-ar-dti-team-from-serviceDeskTeam`: se asigna a mano, y el equipo real lo decide
> jefatura. […] Respalda el compromiso de respuesta en 15 minutos ante un P1 de seguridad.
> Verificado antes de crearlo (07-sep-2026, canario sobre Ruth Fuentes): dos roles de equipo
> ACUMULAN sus colas en vez de pisarse, asi que sus titulares conservan la cola de su area.»

**Por qué ponerle el `subtype` era peligroso:** el filtro del mapping es
`subtype=dti-service-desk-team AND identifier=<serviceDeskTeam>`, con `strength: strong` sobre
`assignment`. Con el `subtype` puesto, el rol vuelve a ser alcanzable por el autoassign — justo lo
que ese diseño cerró a propósito para una responsabilidad que no se deduce del área.

**Y explica el «hallazgo» que este ADR registró mal en su primera versión.** Que sus 4 titulares
sobrevivan a los recomputes pese a `tolerant=false` **no es una anomalía: es el diseño
funcionando.** Se asignan a mano; la asociación no los retira porque el rol asignado sí los
induce. **No hay nada que investigar.**

**Por eso no entra en `mapa-equipo-slug-VERIFICADO.json`**: ese mapa es de equipos de área.

### Verificación de la reversión

| Comprobación | Resultado |
|---|---|
| `subtype` retirado, `displayName` y archetype intactos | ✅ relectura de PROD |
| Inducement de la cola Zammad (`group_ids=26`) intacto | ✅ |
| Los 4 titulares siguen en `cn=dti-seguridad-informatica` | ✅ `200110568`, `200720020`, `201121781`, `9610165` |
| El mecanismo real: **assignment directo** (a mano), no autoassign | ✅ los 4 con `assignment` directo al rol **y** `roleMembershipRef` resuelto |

⚠️ **El recompute de los 4 no llegó a completarse y eso queda abierto.** El endpoint
`POST /users/{oid}/recompute` da 404 y `POST /rpc/executeScript` agotó el tiempo sin dejar rastro.
La tarea acotada por `inOid` sí arrancó (`expectedTotal=4`, filtro verificado) pero se quedó en
`progress=0` más de 20 minutos, con toda probabilidad bloqueada en los recursos rotos de arriba;
se **suspendió y eliminó** para no dejarla corriendo en PROD. La pertenencia de los 4 se comprobó
igualmente por la vía que decide: el `assignment` directo existe y `roleMembershipRef` resuelve,
que es lo que induce el grupo — el `subtype` solo gobernaba el autoassign, del que este rol está
fuera por diseño.

### Lección de método

El dato estaba en el campo `description` del objeto que se iba a modificar. Se leyó el *estado*
(«le faltan campos») sin leer su *justificación*. **En este repo la `description` se usa para dejar
constancia de las excepciones a propósito: antes de "arreglar" un objeto que se sale del patrón,
hay que leerla.**

## Otros hallazgos

1. **Ya no es cierto que nadie esté en dos grupos `dti-*`** (lo era el 03-sep): Ruth Fuentes está
   en `lamb-admision` y `mesa-de-servicio`; Juan Alberto en `devops` y `seguridad-informatica`.
   En ambos casos la segunda pertenencia es intencional, no deriva.
2. Los PATCH que cambian de verdad devuelven **HTTP 240**, no 204. El detalle son recursos ya
   rotos de antes (RIMS-SciBack sin `clientSecret`, foto de Entra, Zammad 422 por correo
   duplicado). Un PATCH sin cambio real devuelve 204 limpio — se comprobó. **No lo causa este
   cambio** y no impidió ninguna escritura: todas verificadas en LDAP.
3. El endpoint REST `POST /users/{oid}/recompute` devuelve **404** en esta versión, y
   `POST /rpc/executeScript` agotó el tiempo sin dejar rastro en PROD. Lo que sí funciona es una
   **tarea de recompute acotada por `inOid`** (`resume` y después `run`). Tarda minutos para 4
   personas por los recursos rotos de arriba: comprobar `expectedTotal` antes de alarmarse.

## Backup

`pg_dump` **descartado con medición**: la base son 36 GB y el disco de PROD tiene 8,8 GB libres
(87 % usado) — volcarla habría llenado el disco. En su lugar, backup lógico exacto del alcance:
XML completo de las 12 personas del alcance y del rol tocado, más el LDIF de los 23 grupos
`dti-*` previos. Revertir es reponer 7 valores de `serviceDeskTeam`.
