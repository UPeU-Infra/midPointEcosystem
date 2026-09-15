# ADR-065 — Los 9 equipos de desarrollo de la DTI

**Fecha:** 15-sep-2026
**Estado:** 🟠 **PROPUESTO — no aplicado.** Requiere aprobación escrita de Alberto
**Ámbito:** árbol organizativo — cambio 🟡 (ADR + simulación + canario + baseline) · archetype de org nuevo
**Rector:** [`ARQUITECTURA-ARBOL-ORGANIZATIVO.md`](../../ARQUITECTURA-ARBOL-ORGANIZATIVO.md) (D1, D3, D4, D5)
**Contrasta con:** [`runbooks/gobierno-grupos-dti-canario-2026-09-03.md`](../../runbooks/gobierno-grupos-dti-canario-2026-09-03.md) — que decidió lo contrario para OTRA población
**Artefactos listos:** [`docs/pendientes/dti-dev-teams/`](../../pendientes/dti-dev-teams/)

## Contexto

El director de la DTI, David Jefferson Barrantes Delgado, validó por escrito la estructura del
área de desarrollo: **9 equipos, 27 personas, 6 con jefe y 3 que dependen directamente de él**.
Se pide fijarla en MidPoint y que llegue a LDAP, que es lo que consumen las aplicaciones.

El modelo de negocio no está en discusión. Lo que este ADR decide es **cómo se representa**,
porque la forma obvia (OrgType con `archetype-org-department`) choca con tres cosas medidas.

## Lo medido antes de decidir (15-sep-2026, contra PROD)

### M1 · `archetype-org-department` publica una OU, y el DN es jerárquico

El archetype lleva el `inducement` con `construction` a `7b4e1c2d` (`generic/ou`), y el outbound
de `ri:dn` (objectType id 447, attribute id 448) **apila los ancestros** cuyo archetype está en
`OU_ARCH` — donde `73795c10` (department) está incluido. DTI tiene ya su shadow
`ou=18,ou=org,dc=upeu,dc=edu,dc=pe`. Consecuencia: los 9 equipos crearían
`ou=dti-dev-*,ou=18,ou=org,…`, **9 OUs nuevas**. D4 del rector lo somete a decisión escrita.

### M2 · 🔴 Con OrgType, la pertenencia al equipo NO llega a LDAP. En absoluto

Se leyeron los tres mappings candidatos del `account/default`, no se muestreó un usuario:

| Atributo LDAP | Fuente real | ¿Lo mueve pertenecer a una org? |
|---|---|---|
| `ri:ou` | `$focus/organizationalUnit` — IIA Oracle (`nom-facultad-to-organizationalUnit`) | no |
| `ri:departmentNumber` | `$focus/costCenter` — IIA Oracle | no |
| `ri:eduPersonOrgUnitDN` | `roleMembershipRef` **filtrado a `PROGRAM_ARCH` (`9f3b8e2a`)** | no |

`parentOrgRef` aparece **1 sola vez** en todo el `schemaHandling` del recurso LDAP, y es dentro
del script del DN de las propias OUs (recorre org→org). **Ningún outbound de persona lo lee.**

Es decir: la ruta OrgType, por sí sola, fija la estructura en MidPoint y entrega **cero** a las
aplicaciones. Lo único que aparecería en el directorio son 9 OUs que describen al equipo pero no
enlazan a nadie con él.

### M3 · La ruta que sí funciona ya existe y está verificada

Desde el 03-sep-2026 MidPoint gobierna 22 grupos `cn=dti-*,ou=groups` (`groupOfUniqueNames`,
64 membresías verificadas una a una). El `objectType` `entitlement/group` (id 497) delinea
`baseContext=ou=groups`, `scope=one`, filtro **`cn` empieza por `dti-`**; el `associationType`
`ri:group` (id 501) es `tolerant=false`. El ACL `{5}` sobre `ou=groups` ya concede `write` a
`cn=midpoint`.

**Un grupo llamado `cn=dti-dev-*` cae dentro de esa delineación ya existente.** Por tanto este
diseño **no exige ningún cambio en el recurso LDAP** — ni un PATCH.

### M4 · La reconciliación de Oracle NO borra lo que Oracle no conoce

Era la primera duda del encargo. El recurso `Oracle LAMB Org` (`9e2f4c7a`) tiene exactamente
cuatro reacciones: `linked→synchronize`, `unlinked→link`, `unmatched→addFocus`,
`deleted→inactivateFocus`. **`deleted` solo dispara para un shadow que existía y desapareció del
origen.** Los 9 equipos no tendrán shadow en ese recurso, así que son invisibles para esa
reconciliación. `generic/ou` del recurso LDAP no tiene `synchronization` en absoluto: es
solo-salida. **El riesgo temido no existe.** No hace falta aislarlos con lifecycleState ni con
filtros de tarea.

### M5 · 8 de las 27 personas tienen HOY un equipo distinto publicado en LDAP

Las 27 ya tienen `extension/upeu:serviceDeskTeam`, que las coloca en un grupo `dti-*`:

| Persona | Grupo LDAP actual (cola Zammad) | Equipo validado por el director |
|---|---|---|
| Elvis Paul Arce Chavarria | Desarrollo · Aplicaciones | Aplicaciones Móviles |
| Jack Cosme Castillo Ramos | Desarrollo · LAMB Admisión (events) | Aplicaciones Móviles |
| Jhon Dilmer Mendieta Tantalean | Desarrollo · LAMB Mantenimiento | Conservatory |
| Ronald Anderson Lopez Mamani | Desarrollo · LAMB Admisión | Conservatory |
| Diana Elizabeth Garcia Tello | Desarrollo · LAMB Mantenimiento | Lamb Academico |
| Willy Jhon Medina Bacalla | Desarrollo · LAMB Mantenimiento | Lamb Academico |
| Owen Miguelich Mejia Guerra | Desarrollo · LAMB Admisión | Lamb Events |
| Juan Alberto Sanchez Condor | Infraestructura TI | DevOps |

**No es un error de datos: son dos dimensiones distintas.** `serviceDeskTeam` es *qué cola de
tickets atiendes*; el equipo de desarrollo es *a quién reportas y qué producto construyes*. Owen
atiende Admisión y lidera Conservatory; Juan Alberto atiende Infraestructura y está en DevOps.
Pueden y deben convivir — pero con nombres que no se confundan, porque 10 de las 22 colas se
llaman «Desarrollo · …» y un consumidor las leerá como el squad.

## Decisión propuesta

### D1 — Los equipos son `OrgType` colgando de DTI, por `assignment` del hijo al padre

Es estructura de gobierno y línea de reporte: pertenece al árbol (D1/D5 del rector), no a un
atributo. `identifier` = `DTI-DEV-*`, `name` = el mismo código (único y estable), `displayName`
legible. OIDs congelados `d71ade00-0000-4000-a000-d71ade0000NN`, NN 01–09 alfabético por
identifier.

### D2 — Archetype nuevo `archetype-org-team`, **sin proyección `generic/ou`**

No se reutiliza `archetype-org-department`: publicaría 9 OUs (M1) que no sirven a nadie (M2) e
invadiría con `DTI-DEV-*` un espacio de `identifier` que en esa rama pertenece a Oracle (`areaId`).
Tampoco `archetype-org-project`, que está `archived` y describe ciclo de vida corto — estos
equipos son permanentes.

El rector dice que **el carácter lo da el archetype** (D3): un equipo interno de trabajo no es un
departamento académico. OID `d71ade02-0000-4000-a000-d71ade020001`. Generalizable a SciBack.

### D3 — Los jefes, `assignment` con `relation=org:manager` sobre el equipo

Nunca como atributo del usuario (D5 del rector). Los 3 equipos sin jefe no llevan manager: su
dependencia del director es la que ya da el árbol.

### D4 — A LDAP se llega por grupo, y el grupo lo **induce el propio equipo**

Un `AR-DTI-Dev-*` por equipo (`d71ade01-…-d71ade0100NN`), cuyo único efecto es la asociación
`ri:group` contra `cn=dti-dev-<slug>,ou=groups`. **Lo induce el OrgType**, no se autoasigna desde
ningún atributo: así la **única autoridad es el árbol** y no nace un segundo `serviceDeskTeam` que
mantener. Asignar a alguien al equipo le da el grupo; quitarlo se lo quita.

`groupOfUniqueNames`, nunca `groupOfNames`: el overlay memberof de este OpenLDAP está configurado
con `olcMemberOfGroupOC=groupOfUniqueNames` — un `groupOfNames` se acepta sin error y no puebla
`memberOf` (fallo mudo).

### D5 — Prefijo `dti-dev-`, deliberadamente dentro de la delineación existente

Que los grupos nuevos caigan bajo el filtro `cn=dti-*` es intencional: los hace gobernados por la
misma asociación `tolerant=false` sin tocar el recurso (M3). El prefijo `-dev-` los distingue de
las colas de Zammad, que es justo lo que M5 exige.

## Lo único que necesita aprobación para tocar el directorio

**Crear 9 entradas `groupOfUniqueNames` bajo `ou=groups`** (`04-grupos-ldap.ldif`). No es un
cambio de configuración del recurso: es alta de datos en el directorio. `uniqueMember` es MUST en
esa objectClass, así que cada grupo nace con **un miembro real** de su equipo — nunca un
placeholder, porque `tolerant=false` borraría un DN inexistente y dejaría el grupo vacío, que es
violación de schema (la trampa que ya apareció el 03-sep).

`createOnDemand=true` se descartó: el `objectType` 497 no tiene outbound para `ri:cn` ni `ri:dn`,
así que exigiría un PATCH del recurso. El LDIF evita tocarlo.

## Consecuencias

- El verificador del árbol sigue en 6/6: los 9 nodos no son raíz, ni baseline, ni `academic-program`.
  **Estado previo medido: 191 orgs, 6/6 ✅.** Hay que regenerar la baseline en el mismo commit
  que el despliegue.
- `recompute-dti-teams-daily` (04:15, `RUNNABLE`) ya recomputa el subárbol de DTI: mantiene la
  convergencia sin tarea nueva. `recon-ldap-dti-groups-daily` (03:30) repondrá lo que se borre a
  mano en los grupos.
- **Los artefactos NO se versionan en `upeu/orgs/`** mientras no se desplieguen: la invariante I4
  exige que toda org de `upeu/orgs/` exista en PROD y `KNOWN_PENDING_FILES` está vacía a propósito.
  Al aplicar, se mueven de `docs/pendientes/` a `upeu/orgs/dti/` en el commit del despliegue.

## Alternativa descartada

**Equipos como RoleType puro**, replicando el patrón del 03-sep. Llega a LDAP igual de bien, pero
no soporta `relation=org:manager` sobre una jefatura, ni jerarquía, ni certificaciones por jefe,
y el encargo del director es precisamente la línea de reporte. La objeción del runbook de
septiembre («no OrgType») era contra un OrgType **que publica OU e invade el identifier de
Oracle**: con `archetype-org-team` ninguna de las dos cosas ocurre, y la tercera (tocar a las
personas con `parentOrgRef`) quedó medida en M2 como inocua.
