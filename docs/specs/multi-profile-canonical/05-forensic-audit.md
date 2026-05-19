# Auditoría Forense PROD — 2026-05-14

**Auditor:** midpoint-expert (sesión read-only)
**Fecha:** 2026-05-14 ~05:32 UTC
**Alcance:** investigar 2 hallazgos del agente previo en PROD `192.168.15.166`
**Restricción:** sin escrituras, sin bulk delete, sin cambios de tasks.

---

## Resumen ejecutivo

| Hallazgo previo | Realidad observada | Veredicto |
|---|---|---|
| 18 697 focuses esperados 22 | **22 560 focuses (creciendo en vivo)** | Hipótesis 1c parcial + nueva causa: import runaway en curso |
| `lambDeptoCode = 0/18 697` | `lambDeptoCode` NUNCA fue inbound; sólo está declarado en el XSD del schema lamb v1 | Hipótesis 2b confirmada (variante: el inbound no existe, no está “mal escrito”) |

---

## Sección 1 — Cronograma de creación de focuses

Snapshot tomado a las 2026-05-14 05:32 UTC.

```
hour_utc            |   n
--------------------+-------
2026-05-14 05:00:00 | 11778
2026-05-14 04:00:00 |  9719
2026-05-13 20:00:00 |     4
2026-05-13 17:00:00 |    16
2026-05-13 15:00:00 |     1
2026-04-15 20:00:00 |     1
```

**Antes del 2026-05-14 04:00 UTC:** 22 focuses (baseline correcto post-cleanup del 13-may).
**Después:** 22 501 focuses creados en ventana `04:35:25 → 05:31:58 UTC`, ritmo ~415/min, **aún en progreso**.

Distribución por archetype (snapshot 05:32 UTC):
- `archetype-user-alumni`: 21 461
- `archetype-user-student`: 8
- `archetype-user-employee-staff`: 7
- `archetype-user-employee-faculty`: 3
- `System user`: 1
- **Total m_user:** 22 560

---

## Sección 2 — Tasks identificadas

| OID | Nombre | Estado | Window | Veredicto |
|---|---|---|---|---|
| `91e67788-dc04-4145-b312-3944524c80b1` | `import-egresado-9610165-juan-alberto-v2` | **RUNNING** desde 2026-05-14 04:35:23 UTC | progress=21 660 (creciendo) | **OFENSORA ACTIVA** |
| `8eee3158-692f-4501-91c7-afdd603a35c9` | `import-egresado-9610165-juan-alberto` | SUSPENDED 04:28:55 | corrió 0,1 s, sin daño material | inocuo |
| `27333f76-643e-487b-aa02-26164fa46b8f` | `Import egresado 9610165 — re-correlate post-fix correlator` | SUSPENDED 04:00:39 | terminó antes del runaway | inocuo |
| `8801323d-…` | `Import egresado 9610165 v3` | SUSPENDED 03:28:10 | 0,1 s | inocuo |
| Resto | Recon/Import-egr-muestrario | CLOSED OK 13-may | dentro del baseline 22 | OK |

**Causa raíz del runaway (task `91e67788`):**

El XML de la task contiene el filtro:

```xml
<q:filter>
  <q:equal>
    <q:path>attributes/icfs:name</q:path>
    <q:value>9610165</q:value>
  </q:equal>
</q:filter>
<queryApplication>append</queryApplication>
```

Pero el `searchScript` desplegado en el resource Egresados v2
(`6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23`) **no respeta ningún filtro de ConnId**.
Es un script Groovy con SQL hardcoded sin WHERE:

```groovy
def query = '''
SELECT * FROM (
  SELECT e.CODIGO, MAX(e.NOMBRE) AS NOMBRE, ...
  FROM DAVID.VW_PERSONA_EGRESADO e
  GROUP BY e.CODIGO
)
'''
sql.eachRow(query) { row -> result << [...] }
return result
```

No hay parámetro `filter` ni `options.query` consumido. El connector ScriptedSQL
de Tirasa entrega el filtro al script, pero este lo descarta. Resultado: la task
ejecuta un import COMPLETO de la vista `DAVID.VW_PERSONA_EGRESADO` (~22 K filas)
y MidPoint crea un focus por cada CODIGO.

**Tasks recurrentes activas:** ninguna. No hay live-sync ni recon programada.
Sólo esta task `SINGLE` está corriendo; cuando termine no se reactivará sola,
pero terminará habiendo creado ~22 K alumni focuses.

---

## Sección 3 — Estado real de schema lamb v1 + trabajadores-v2

### Schema lamb v1 (`11111111-1111-1111-1111-000000000001`)

XSD desplegado declara los 3 atributos:

```xml
<xsd:element minOccurs="0" name="lambPersonaId"  type="xsd:string"/>
<xsd:element minOccurs="0" name="lambDeptoCode"  type="xsd:string"/>
<xsd:element minOccurs="0" name="lambSemestreId" type="xsd:string"/>
```

PERO en `m_ext_item` sólo está materializado uno:

```
id |                itemname                 | valuetype | holdertype | cardinality
49 | urn:upeu:midpoint:lamb:v1#lambPersonaId | xsd#string| EXTENSION  | SCALAR
```

Sin fila en `m_ext_item`, MidPoint no indexa ni persiste el atributo en
`m_user.ext`. Eso ocurre la primera vez que un mapping escribe en él —
y aquí nunca pasó porque no existe inbound.

### Trabajadores v2 (`6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21`) deployed

- **searchScript SQL** (líneas 92-126): NO selecciona `ID_DEPTO`. Sólo
  `COD_APS, NOMBRE, PATERNO, MATERNO, NUM_DOCUMENTO, FEC_INICIO, FEC_TERMINO,
  ESTADO, ID_CATEGORIAOCUPACIONAL, UPEU_ARCHETYPE_NAME`. **Aún tiene el
  limitador piloto `WHERE ROWNUM = 1`** (línea 125).
- **schemaScript:** NO declara `ID_DEPTO` ni `DEPTO_CODE`.
- **schemaHandling:** atributos definidos = `COD_APS, NOMBRE, PATERNO, MATERNO,
  NUM_DOCUMENTO, FEC_INICIO, FEC_TERMINO, ESTADO, UPEU_ARCHETYPE_NAME`.
  No hay `ri:DEPTO_CODE` ni `ri:ID_DEPTO`. **No hay ningún `<inbound>` con
  `<target><path>extension/lamb:lambDeptoCode</path>`.**
- Caching metadata del schema del resource: `2026-05-13T22:09:22Z` —
  el último refresh fue antes del cambio que se cree haber hecho.

### Worktree local vs PROD

```
worktree:  schema/v3.0/schemaType-lamb-v1.xml      → declara lambDeptoCode (XSD only)
worktree:  resources/oracle-lamb-trabajadores-v2.xml → grep "ID_DEPTO" → 0 matches
PROD:      schema lamb v1 deployed                  → declara lambDeptoCode (XSD only)
PROD:      trabajadores-v2 deployed                 → grep "ID_DEPTO" → 0 matches
```

**El cambio del inbound `lambDeptoCode` nunca fue escrito en el XML**, ni en
local ni en PROD. La memoria del usuario es parcial: añadió el atributo al
schema, pero no llegó a añadir SQL+schemaScript+schemaHandling+inbound al
resource trabajadores-v2.

---

## Sección 4 — Diagnóstico raíz

### Hallazgo 1 — 22 560 focuses (no 18 697)

1. La cifra previa de 18 697 está obsoleta (snapshot anterior).
2. El cleanup del 2026-05-13 22:46 dejó la base en 22 focuses (baseline OK).
3. A las 04:35 UTC del 14-may se lanzó la task `91e67788` con la **intención**
   de re-correlacionar UN egresado (CODIGO=9610165), pero el filtro fue
   silenciosamente ignorado por el `searchScript` Groovy del Resource.
4. Resultado: import masivo en curso de toda la vista `VW_PERSONA_EGRESADO`,
   creando un focus por CODIGO con archetype `archetype-user-alumni`.
5. La task sigue corriendo. Cada minuto suma ~415 focuses más.

**No fueron las tasks viejas (`27333f76`, `8801323d`).** Esas se cerraron antes.
**No hubo trigger automático ni live-sync.** Es la task `91e67788` única
y exclusivamente.

### Hallazgo 2 — `lambDeptoCode` = 0

`lambDeptoCode` no se puebla porque **el inbound nunca fue escrito**. El atributo
existe únicamente en el XSD del schema lamb v1; el resource trabajadores-v2 no
lo lee de Oracle, no lo expone como `ri:`, no lo mapea. Por eso ni siquiera se
materializó la fila en `m_ext_item`.

Verificación en focuses staff/faculty (10 totales) — ninguno tiene clave para
`lambDeptoCode` en `ext` jsonb. Sólo `lambPersonaId` (key `49`).

---

## Sección 5 — Recomendación de remediación

**Opción única recomendada (en orden estricto):**

### Paso 1 — Detener el runaway YA (requiere autorización del usuario)

```bash
# REST API: suspend
curl -sk -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" -X POST \
  "$MIDPOINT_URL/midpoint/ws/rest/tasks/91e67788-dc04-4145-b312-3944524c80b1/suspend"
```

Sin esto, en ~30 min más la task agregará ~12 K focuses adicionales.

### Paso 2 — Cleanup quirúrgico de los 22 538 focuses creados por el runaway

Borrar `m_user WHERE createtimestamp >= '2026-05-14 04:35:00 UTC'`. Eso restaura
exactamente el baseline de 22 (mismo criterio que el cleanup del 13-may, sólo
ampliando la ventana). Importante: hacerlo vía MidPoint REST/UI o `ninja`,
no SQL directo, para que se borren shadows + assignments + role memberships
asociados.

### Paso 3 — Reparar el `searchScript` de Egresados v2 antes de cualquier import

Hacer que el script consuma el filtro ConnId. Patrón:

```groovy
// 'filter' es el binding de Tirasa scripted-sql cuando query!=null
def whereClause = ''
def params = []
if (filter != null && filter instanceof Map) {
    // construir WHERE dinámico desde filter (EqualsFilter, etc.)
    if (filter['Name'] || filter['__NAME__']) {
        whereClause = ' WHERE e.CODIGO = ?'
        params << (filter['Name'] ?: filter['__NAME__']) as String
    }
}
def query = """SELECT ... FROM DAVID.VW_PERSONA_EGRESADO e ${whereClause} GROUP BY e.CODIGO"""
sql.eachRow(query, params) { row -> ... }
```

Alternativa más simple: aceptar que Egresados v2 NO admite imports de un solo
ítem y siempre reconcilia masivo (apropiado para cohortes históricas), pero
documentarlo y nunca lanzar `import` con filtro esperando granularidad.

### Paso 4 — Decidir sobre `lambDeptoCode`

Si se quiere realmente, requiere 4 cambios coordinados en
`resources/oracle-lamb-trabajadores-v2.xml`:

1. SQL: agregar `e.ID_DEPTO` al SELECT.
2. Map de salida: `'DEPTO_CODE': row.ID_DEPTO?.toString()`.
3. schemaScript: `ocib.addAttributeInfo(ro("DEPTO_CODE", false))`.
4. schemaHandling: nuevo `<attribute><ref>ri:DEPTO_CODE</ref><inbound>` con
   `<target><path>extension/lamb:lambDeptoCode</path></target>`.

Y **declarar el namespace `lamb`** en el XML del resource. Después: refresh
schema + reimport los 10 trabajadores. Eso materializa la fila en
`m_ext_item` la primera vez que se ejecute el mapping.

### Riesgos

- Borrar 22 538 focuses por API masivo va a generar carga al motor: hacerlo
  fuera de horario y con `raw=true` para evitar disparar workflows/recompute
  por cada delete.
- Suspender la task con progress=21 660 deja shadows huérfanos en el resource
  (uno por CODIGO). El cleanup masivo debe incluir también `ShadowType` del
  resource Egresados v2 con `createTimestamp` en la misma ventana.

---

## Sección 6 — Estado real vs estado deseado

| Dimensión | Deseado post-cleanup 13-may | Real ahora 14-may 05:32 UTC | Delta |
|---|---|---|---|
| Total m_user | 22 | 22 560 | **+22 538 espurios + 1 system** |
| Alumni | 0 (no se ha hecho recon masiva válida) | 21 461 | **+21 461 espurios** |
| Student | 8 | 8 | OK |
| Staff | 7 | 7 | OK |
| Faculty | 3 | 3 | OK |
| Tasks running | 0 | 1 (`91e67788` runaway) | **−1 (suspender)** |
| `lambDeptoCode` materializado | (declarado en spec) | 0/0 (atributo no existe en `m_ext_item`) | falta resource change |
| `lambPersonaId` materializado | sí | 21/22 559 (creciendo) | OK estructuralmente |

**Conclusión:** el modelo canónico (10 trabajadores correctos, 8 estudiantes
pilot Lima SEM 279) está intacto y consistente. Lo que está roto es:
(a) una task runaway en curso, (b) un searchScript que no respeta filtros,
(c) un atributo (`lambDeptoCode`) declarado en schema pero sin pipeline
de poblamiento.
