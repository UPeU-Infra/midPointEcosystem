# ADR-064 — Política de `owner` en los RoleType: separar por naturaleza, no ensanchar ni maquillar

**Fecha:** 04-sep-2026 · **Estado:** PROPUESTO — para la reunión con Urquizo
**Contexto medido en PROD el 04-sep-2026. Nada aplicado.**

## El problema tal y como aparece

Los 22 roles `AR-DTI-Team-*` desplegados el 03-sep no tienen `ownerRef` y el Compliance
Dashboard los marca **«Unowned»** (ISO 27001 A.5.1/A.5.2/A.5.9/A.5.36). Pero **los 112
RoleType del sistema están sin owner**, no solo esos 22. Poner owner a 22 dejaría el tablero
igual de rojo y crearía una inconsistencia sin resolver nada.

## Lo que dice la regla, literalmente

```xml
<name>global-require-owner-business-roles</name>
<description>Aplica minAssignees owner=1 a TODOS los RoleType. ...</description>
<policyConstraints>
  <minAssignees><multiplicity>1</multiplicity><relation>org:owner</relation></minAssignees>
</policyConstraints>
<policyActions><record/></policyActions>      <!-- modo record: no bloquea -->
<focusSelector><type>RoleType</type></focusSelector>
```

**El nombre miente; la descripción no.** Quien la escribió sabía que alcanzaba a todo
`RoleType` y lo dejó por escrito. No es un `focusSelector` puesto de más: es un **nombre mal
puesto**. Por tanto la pregunta no es «¿fue un descuido?» sino «¿el alcance ancho es la
política que queremos?».

## Los 112 no son una población: son cinco

| Archetype | Roles | Qué significaría `owner` |
|---|---|---|
| `archetype-role-application` (propio, `279ad5be-…`) | **60** | Responsable de la aplicación |
| `Application role` (estándar MidPoint, `…0328`) | 6 | Lo mismo, con otro archetype |
| `archetype-role-business` (propio, `af29bb55-…`) | 35 | Jefe de la función de negocio |
| `Affiliation-Role` (`a1c40fd6-…`) | 6 | **Nadie** |
| `System role` (estándar, `…0320`) | 4 | **Nadie** |
| Sin archetype | 1 | — |

**Ninguno de los 112 tiene `ownerRef`.** Y los 22 del DTI son `archetype-role-application`:
son *application roles*, así que Evolveum tiene razón — su owner es el responsable de la
aplicación, no un jefe de personas.

## 🔴 Obstáculo previo: conviven dos taxonomías de archetypes

Están los propios (`archetype-role-application`, `archetype-role-business`) **y** los estándar
de MidPoint (`Application role` `…0328`, `Business role` `…0321`, `System role` `…0320`,
`Application` `…0329`). **6 roles usan el estándar en lugar del propio.**

Si se acota la regla por archetype hoy, **esos 6 se caen del alcance sin que nadie lo note** —
justo el agujero silencioso que un tablero de cumplimiento no debe tener.

→ **Primero unificar la taxonomía; después acotar la regla.** En ese orden.

## Decisión propuesta

**1. NO acotar la regla para reducir el rojo.** Sería maquillar el tablero: el rojo
desaparecería sin que ningún rol gane responsable.

**2. SÍ dividirla en tres**, por una razón distinta — `owner` significa cosas incompatibles en
cada categoría, y las campañas de certificación se organizan por tipo de rol, no en bloque:

| Regla | Alcance | Owner |
|---|---|---|
| `require-owner-application-roles` | los 66 application roles | Responsable de la aplicación |
| `require-owner-business-roles` | los 35 business roles | Jefe de la función |
| **exención documentada** | `System role` (4) + `Affiliation-Role` (6) | **ninguno, por diseño** |

**3. La exención no es deuda diferida: es una decisión.** Un rol de afiliación **no es un acceso
que alguien apruebe**: es la consecuencia de que la persona sea estudiante, docente o egresada.
Marcarlo «Unowned» convierte un acierto de diseño en una falsa no conformidad. Lo mismo con los
`System role`, que son infraestructura. **10 de los 112 no son deuda y hoy se cuentan como tal.**

## Lo que hay que decir en voz alta

**Hoy esto no reduce ningún riesgo real.** Verificado: la regla está en modo `record` (no
bloquea), no hay campañas de certificación, y `owner` no se usa en ninguna aprobación. Poner
owners sin campañas es **rellenar un campo que nadie lee**.

Es el mismo hallazgo del 04-ago (*«la gobernanza está construida pero DESHABITADA»*: 0
campañas, roles `GOV-*` sin titulares). El `ownerRef` sin campaña es documentación, no control.

Eso **no significa no hacerlo** — significa no presentarlo como cierre de un riesgo ISO cuando
es preparación. El valor aparece con la primera campaña de certificación.

## Orden de ejecución

1. Unificar la taxonomía de archetypes de rol (los 6 que usan el estándar).
2. Sustituir la regla ancha por las dos acotadas + la exención documentada.
3. Poblar `ownerRef` por lotes, por categoría.
4. Solo entonces: primera campaña de certificación, que es lo que da sentido al campo.

## Para la reunión con Urquizo

**Los 22 no necesitan 22 owners.** Son application roles de un mismo sistema —alimentan las
colas de agentes de Zammad—, así que el owner natural es **el responsable del servicio de mesa
de ayuda**: uno solo para los 22.

Si se quiere granularidad, el patrón habitual son **dos figuras**: un *owner técnico* (quien
opera Zammad) y un *approver por equipo* (el coordinador). El approver usa un `relation`
distinto de `org:owner`, así que **no afecta a esta regla** ni al tablero.

## Consecuencias

- El dashboard bajará de 112 a 102 «Unowned» solo con documentar la exención, sin tocar un rol.
- Con la taxonomía unificada, acotar por archetype pasa a ser seguro.
- Cada categoría podrá certificarse por separado cuando existan campañas.
- Queda pendiente de la reunión: quién es el responsable del servicio de mesa de ayuda.
