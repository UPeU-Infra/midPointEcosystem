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

**Si se publica en LDAP.** El item entra primero en la ficha de MidPoint; que InOut y otros
consumidores puedan leerlo es un segundo paso, y conviene decidirlo con ellos —incluye elegir
el atributo, que es la pregunta abierta desde el prompt del puente ("qué atributo eduPerson
publica el programa").

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

Queda una **decisión de producto, no técnica**: si el tesauro institucional debe incluir
programas no licenciados (Idiomas, CEPRE, Conservatorio, diplomaturas). Este ADR no la fuerza
— funciona igual con o sin ellos.

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

## Verificación

1. Schema: el item nace `unbounded` — comprobar en PROD tras desplegar.
2. Canario: un estudiante de Inglés (p. ej. `PROGRAM_CODES=356`) debe quedar con
   `academicProgramSourceId=356` y **sin** P-code.
3. Canario 2: uno de los 90 con doble programa → debe traer **los dos valores**.
4. Control negativo: un estudiante con P-code no debe perder ni cambiar nada.
5. Cierre: estudiantes activos sin ningún identificador de programa → **0**.
