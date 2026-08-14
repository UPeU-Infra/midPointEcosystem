# ADR-062 — El IGA identifica el programa de TODO estudiante, esté licenciado o no

**Fecha:** 14-ago-2026
**Estado:** propuesto — preparado, pendiente de simulación y canario
**Ámbito:** schema canónico + resource Estudiantes
**Relacionado:** [`ADR-005`](../../HALLAZGO-programas-academicos-vocbench-2026-08-05.md) (P-code al lado de la URI)

## Contexto

**6.706 estudiantes activos no tienen ningún identificador de programa** en el IGA: ni
`academicProgramSuneduCode`, ni `academicProgramUri`. Nada.

| | |
|---|---|
| Con P-code | 18.479 |
| **Con URI pero sin P-code** | **0** |
| **Sin ningún identificador** | **6.706** |

La causa está en la tabla `program-pxx-byid`: mapea `ID_PROGRAMA_ESTUDIO → P-code` y tiene
**188 filas, solo programas licenciados**. Un estudiante de Inglés, Conservatorio, CEPRE o
una diplomatura no está ahí, así que no obtiene nada — ni código ni URI, porque ambos
dependen de la misma tabla.

### Por qué esto es un defecto y no un comportamiento correcto

Que esos programas **no necesiten P-code es cierto**: no son licenciados y su cobertura ante
SUNEDU debe ser 0 % (Ley 30220 art. 46). Pero de ahí no se sigue que el sistema de identidad
pueda no saber **en qué programa está** la persona.

El catálogo se construyó con el criterio de **un consumidor** —Calidad, que necesita el
A4/A8— y no con el de identidad. **Es exactamente el patrón que produjo el incidente de
InOut**: `ou=org` se publicaba solo para ciertos archetypes, y 899 personas quedaron sin área
en el aforo del CRAI porque nadie miraba ese hueco: "no era obligatorio".

Un IGA no puede tener 6.706 personas cuyo programa no sabe nombrar, teniendo el dato.

## Decisión

**Publicar siempre el `ID_PROGRAMA_ESTUDIO` de Oracle en la ficha**, resuelva o no a P-code.

1. **Item nuevo en el schema canónico:**
   `academicProgramSourceId`, `xsd:string`, **`maxOccurs="unbounded"`**, indexado.
   **Es un identificador de correlación, hermano de `externalSystemId` — NO un valor de
   publicación.** Se dice aquí explícitamente porque dentro de seis meses alguien lo va a
   querer publicar por ser el único campo poblado al 100 %.
2. **Inbound `strong`** en el resource Estudiantes desde `ri:PROGRAM_CODES` — el atributo
   que ya trae el dato y que hoy solo alimenta al puente.

**Aditivo**: no toca `academicProgramSuneduCode` ni `academicProgramUri`. Los 18.479 que hoy
resuelven no cambian en nada.

## Impacto medido (14-ago-2026, PROD)

| | |
|---|---|
| Estudiantes activos con ficha en la fuente | **25.136** |
| **Con `ID_PROGRAMA_ESTUDIO` en el shadow** | **25.136 — el 100 %** |
| **Ganan identificador de programa** | **6.654** |
| **Se quedarían sin nada** | **0** |
| Programas distintos que pasan a ser identificables | **106** |
| Con P-code, sin cambio | 18.479 |

**El dato ya viaja en todos los shadows.** No hay que tocar el `searchScript` ni traer nada
nuevo de Oracle: solo publicarlo.

## ⚠️ Multivalor desde el principio — no negociable

**90 estudiantes tienen más de un programa** (dobles matrículas). El item nace `unbounded`.

Esto no es precaución teórica: `academicProgramSuneduCode` se creó single-value, hubo que
cambiarlo, y **el cambio de cardinalidad generó un id nuevo en `m_ext_item` que partió los
datos** — 29 personas quedaron ancladas al id viejo, 4 de ellas con el valor basura `'P'`
que LDAP estuvo publicando hasta que se limpió con `PATCH replace` vacío.

Naciendo `unbounded` ese camino no se recorre.

Y por la misma razón: **source multivalor ⇒ nunca `<function>` en el mapping, siempre
`<script>`** (regresión del 5-ago, prohibición permanente nº 4 del rector del árbol).

## Riesgos

- **Bajo.** El campo es nuevo y aditivo; nada lo consume todavía.
- El recompute de 25.136 estudiantes escribe un valor nuevo por persona → carga de
  provisioning. **Koha está saturado por el scraper del OPAC** (load 43, 1 worker): no
  ejecutar hasta que eso se resuelva.
- Reversible: retirar el inbound y vaciar el item.

## Lo que NO decide este ADR

**Si se publica en LDAP. Y la respuesta provisional es NO** — ver la prohibición de abajo.

Tampoco resuelve que esos 106 programas tengan **URI en el tesauro**: eso es trabajo de
VocBench, y ahora con el criterio correcto —cubrir el catálogo entero, no solo el A4/A8.

### Qué le cambia esto a VocBench

**No lo sustituye.** `academicProgramSourceId` es un número interno de Oracle: no tiene
semántica, ni jerarquía, ni enlace al código SUNEDU. La URI del tesauro sigue siendo lo único
que da significado. Este ADR llena el hueco de **identidad**, no el de **vocabulario**.

Le cambia tres cosas:

1. **Le da su lista de trabajo real, completa, por primera vez.** El tesauro se pobló con el
   criterio de Calidad —los 188 licenciados—. Con el ID publicado se puede medir exactamente
   qué programas de la fuente no tienen concepto: hoy son **106**.
2. **Deja de ser un punto único de fallo.** Hoy, si un programa no está en el tesauro, la
   persona se queda sin **nada**. Después se queda sin URI, pero con identificador.
3. **No le añade trabajo nuevo por este cambio.** El vínculo programa↔concepto vive en la
   LookupTable de MidPoint, no en el tesauro —InOut lo verificó: ninguno de los 440 conceptos
   declara un predicado con el id de LAMB—. Un concepto nuevo se engancha por ID, como quedó
   tras la corrección del 5-ago.

~~Queda una decisión de producto, no técnica: si el tesauro debe incluir programas no
licenciados. Este ADR no la fuerza — funciona igual con o sin ellos.~~

**Corregido el 14-ago-2026 tras revisión doctrinal (libro de MidPoint + estándares canónicos):
doctrinalmente NO funciona igual, y la decisión sí tiene dueño.** Sin cobertura completa se
institucionalizan **dos niveles de normalización del mismo atributo** — una parte de la
población con URI y otra con un entero de Oracle—, y eso rompe por tres sitios: las reglas
PD-RBAC sobre el atributo dejan fuera al 27 % **en silencio**; un revisor de campaña de
certificación que recibe `356` en vez del nombre del programa no puede decidir (ISO 27001
A.5.18), lo que produce evidencia de auditoría falsa; y los agregados por programa **parecen
correctos** porque suman el 100 % de las filas presentes.

La respuesta es **sí, el tesauro cubre el catálogo de matrícula completo** → **[`ADR-063`](ADR-063-tesauro-cubre-catalogo-matricula.md), que este ADR tiene como dependencia, no como opcional.**

## ⚠️ Posible drift repo↔PROD que hay que comprobar antes de aplicar

En el repo, el inbound vecino `program-id-to-liveProgramUriStudent` **sigue usando
`<function>`** sobre el mismo `PROGRAM_CODES` multivalor. El 5-ago eso se corrigió a
`<script>` **en PROD**, así que el repo puede llevar drift.

No afecta a este cambio —se despliega como `PATCH add` de un inbound nuevo, sin tocar el
otro— pero **hay que mirarlo antes**, porque un despliegue del atributo entero desde el repo
reintroduciría la regresión. No se pudo comprobar hoy: sin VPN ni túnel a PROD en el momento
de escribir esto.

## Despliegue

Los dos artefactos se aplican por separado y en este orden:

1. **Schema** (`SchemaType` OID `e800335c-9ca1-4a2d-b4ca-e06f6db42693`) — `PATCH` de
   `c:definition`. Es el objeto que edita la UI: **no requiere reinicio**. Precaución
   registrada: el `replace` sustituye el `c:definition` entero, así que el XML enviado debe
   ser el de PROD con el item añadido, nunca el del repo a secas — así se perdieron
   `campusEgreso` y `suneduLocalCode` el 11-ago.
2. **Resource Estudiantes** — `PATCH add` del `<inbound>` dentro del `<attribute>` de
   `ri:PROGRAM_CODES`. **Nunca `PUT`**: arranca el `<schema>` cacheado y deja el resource
   `broken`.

## 🔴 Prohibición: no se publica a ningún consumidor sin URI

`academicProgramSourceId` **no sale de MidPoint** mientras el programa no tenga URI. No es un
aplazamiento ("ya lo veremos"): un campo poblado al 100 % junto a otro poblado al 73 % tiene
un final previsible, y este ADR existe precisamente para que ese final no ocurra por inercia.

La razón es doctrinal, no estética. Publicar el entero de Oracle obliga a cualquier consumidor
que quiera **interpretarlo** a ir a consultar Oracle LAMB — es decir, **comunicación
spoke-a-spoke**, el patrón que MidPoint desalienta activamente (libro, *Data Unification*,
p. 204). El identificador crudo no viaja solo: arrastra una dependencia al sistema origen.

Y lo confirma la forma de los estándares: **ni un solo atributo semántico de eduPerson o SCHAC
transporta una clave cruda de un sistema origen** — `eduPersonEntitlement`, `eduPersonAssurance`,
`eduPersonOrcid` son URI; `schacHomeOrganizationType`, `schacPersonalUniqueCode`,
`schacUserStatus` son URN scopeadas. Cuando el valor es intrínsecamente local, el estándar no
lo publica desnudo: lo **scopea**.

Si algún día hubiera que publicarlo, iría como `urn:upeu:programId:lamb:{id}` y con decisión
explícita. Que haga falta envolverlo así es, en sí mismo, la señal de que no debería publicarse.

**Corolario sobre lo que SÍ se publica hoy:** `scibackAcademicProgramSuneduCode` es
estructuralmente un mal portador primario del programa — por definición legal solo existe para
los licenciados, y un atributo cuyo dominio no cubre a la población no puede sostener
autorización, certificación ni reporting. Se conserva (Calidad lo necesita), pero el portador
primario debe pasar a ser el **URI**.

## ⚠️ El zero-set, antes de que crezca la cobertura — no después

Cuando los 106 programas empiecen a resolver a URI, `academicProgramUri` **añadirá valores sin
retirar los previos**: es el patrón PM10 que ya costó **7.841 personas publicando a la vez la
URI deprecada y la canónica**, y una limpieza revertida el 6-ago porque el origen estaba en el
mapping, no en LDAP.

Es el mismo mecanismo, en el mismo atributo, y esta vez se ve venir. **El zero-set del mapping
se materializa ANTES de ampliar el tesauro.**

## Verificación

1. Schema: el item nace `unbounded` — comprobar en PROD tras desplegar.
2. Canario: un estudiante de Inglés (p. ej. `PROGRAM_CODES=356`) debe quedar con
   `academicProgramSourceId=356` y **sin** P-code.
3. Canario 2: uno de los 90 con doble programa → debe traer **los dos valores**.
4. Control negativo: un estudiante con P-code no debe perder ni cambiar nada.
5. Cierre: estudiantes activos sin ningún identificador de programa → **0**.

## Invariante permanente (sin esto, el ADR estabiliza el hueco en vez de cerrarlo)

> **Todo valor de `academicProgramSourceId` debe resolver a un `academicProgramUri`.**

Métrica expuesta: **programas de la fuente sin concepto en el tesauro**. Hoy **106**, objetivo
**0**. Se mide como un `diff` entre los `ID_PROGRAMA_ESTUDIO` distintos de la fuente y los
declarados en el tesauro — no como un hallazgo accidental de un consumidor, que es como
apareció el hueco de `ou=org`.

Sin este invariante, dar identificador a los 6.706 **quita la presión de arreglar el
vocabulario**: es la forma más común en que un workaround se vuelve permanente. El propio libro
llama *workaround* —no solución— a arreglar en MidPoint lo que falta en la fuente
(*HR Feed Recommendations*, p. 175).
