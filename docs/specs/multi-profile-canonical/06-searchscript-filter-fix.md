# 06 — Fix `searchScript` para respetar el filter de ConnId

**Fecha:** 2026-05-14
**Autor:** midpoint-expert (sesión PROD)
**Contexto:** auditoría forense `05-forensic-audit.md` (incidentes
`27333f76` 24K + `91e67788` 30K focuses creados por scoped imports que se
convirtieron silenciosamente en imports masivos).

---

## 1. Causa raíz (resumen)

El `searchScript` Groovy de los 3 resources Oracle LAMB v2 ignoraba el
binding `query` (map de filtro ConnId) y ejecutaba SIEMPRE un SELECT sin
WHERE sobre la vista LAMB. Cuando MidPoint lanzaba un Import Task con
`<q:filter>` por `attributes/icfs:name`, el filtro se evaluaba en memoria
post-fetch — pero **el fetch ya había barrido toda la vista** y MidPoint
creaba un focus por cada CODIGO procesado antes de aplicar el filtro
(porque los inbound mappings y la sincronización corren por cada
`ConnectorObject` que llega del connector).

El comentario en los XMLs ("el binding `query` se IGNORA en este piloto")
era la racionalización del bug, no su justificación.

## 2. Convención real del connector Tirasa ScriptedSQL 2.2.10

Verificado en código fuente
(`Tirasa/ConnIdCommons` →
`scripted/src/main/java/net/tirasa/connid/commons/scripted/AbstractScriptedConnector.java`,
método `executeQuery` líneas 585-620; y
`Tirasa/ConnIdDBBundle` →
`scriptedsql/src/main/java/net/tirasa/connid/bundles/db/scriptedsql/ScriptedSQLFilterTranslator.java`).

### Bindings que el script recibe

| Binding | Tipo | Origen |
|---|---|---|
| `configuration` | `ScriptedSQLConfiguration` | `buildArguments()` |
| `connection` | `java.sql.Connection` | `buildArguments()` |
| `objectClass` | `String` (e.g. `"__ACCOUNT__"`) | runtime |
| `action` | `String` (`"SEARCH"`) | runtime |
| `log` | `org.identityconnectors.common.logging.Log` | runtime |
| `options` | `Map<String,Object>` (de `OperationOptions`) | runtime |
| **`query`** | **`Map<String,Object>` o `null`** | **`ScriptedSQLFilterTranslator`** |

> El binding se llama **`query`**, NO `filter`. La auditoría forense lo
> menciona como `filter` informalmente.

### Estructura del Map `query`

Producido por `ScriptedSQLFilterTranslator extends AbstractFilterTranslator<Map<String,Object>>`:

**Filter atómico (Equals, Contains, StartsWith, etc.):**
```groovy
[
  not: false,                  // boolean
  operation: 'EQUALS',         // CONTAINS|STARTSWITH|ENDSWITH|EQUALS|EQUALSIGNORECASE|GREATERTHAN|...
  left: '__NAME__',            // nombre del atributo ConnId
  right: '9610165'             // valor (siempre String — AttributeUtil.getAsStringValue)
]
```

**Filter compuesto (AND/OR):**
```groovy
[
  operation: 'AND',            // o 'OR'; sin 'not'
  left:  [ ... map atómico o compuesto ... ],
  right: [ ... map atómico o compuesto ... ]
]
```

**Sin filtro (reconciliation full):** `query == null`.

**Importante:** ConnId / framework re-aplica TODOS los filtros sobre
los `ConnectorObject` que devuelva el script — el WHERE en SQL es solo
una optimización para reducir el resultset. Pero como el script construye
focuses inbound desde el ResultsHandler, en MidPoint la diferencia
operacional es enorme: o bien fetcheamos 1 fila de Oracle, o fetcheamos
22 K filas y el motor crea 22 K focuses antes de descartar 21 999.

### Atributos especiales

`__NAME__` y `__UID__` son atributos lógicos de ConnId. En estos tres
resources ambos están aliasados a la misma columna SQL:

- Egresados v2: `CODIGO`
- Estudiantes v2: `CODIGO`
- Trabajadores v2: `COD_APS`

Cuando MidPoint envía `<q:equal><q:path>attributes/icfs:name</q:path>...`
el filter `EqualsFilter` lleva `attribute.name = "__NAME__"`.

## 3. Estrategia de fix

### Principios

1. **Default safe:** si `query == null` → comportamiento actual
   (SELECT completo). Mantiene reconciliation masiva intacta.
2. **Filter soportado:** EqualsFilter sobre `__NAME__` o `__UID__` → WHERE
   por la columna PK del resource (`CODIGO` o `COD_APS`). Esto cubre el
   100% de los scoped imports que MidPoint genera (los Import Tasks con
   filtro siempre referencian `attributes/icfs:name`).
3. **Anti-runaway:** cualquier OTRO filter (Contains, AND, OR, atributos
   distintos a Name/Uid) → `throw new UnsupportedOperationException(...)`.
   La task falla EXPLÍCITAMENTE con error visible en el log de MidPoint
   en lugar de degradar a full-scan silencioso.
4. **PreparedStatement:** parametrizar el valor (`?` + `params`) para
   evitar SQL injection desde valores arbitrarios.
5. **Cero cambios al SELECT base** — solo se inyecta una cláusula WHERE
   adicional al inicio (envolviendo o anteponiendo).

### Pseudo-código

```groovy
def whereClause = ''
def params = []

if (query != null) {
    if (query.operation == 'EQUALS' && !query.not
            && (query.left == '__NAME__' || query.left == '__UID__')) {
        whereClause = ' AND <PK_COLUMN> = ? '
        params << (query.right as String)
    } else {
        throw new UnsupportedOperationException(
            'searchScript only supports EqualsFilter on __NAME__/__UID__; got: ' + query)
    }
}
// inyectar whereClause dentro del SELECT existente
```

### Cómo inyectar el WHERE sin reescribir el query

Para los 3 resources la estrategia más segura es envolver el query
existente en una sub-select y aplicar el filter externamente:

```groovy
def baseQuery = '''SELECT * FROM ( <query original> )'''
def finalQuery = whereClause
    ? "${baseQuery} WHERE ${pkAlias} = ?"
    : baseQuery
```

Esto preserva al 100% la lógica deduplicadora (LISTAGG, ROW_NUMBER,
GROUP BY, JOIN ENOC.CAT_DOCENTE) sin riesgo de romper sub-queries.

PK alias por resource:
- Egresados v2 → `CODIGO`
- Estudiantes v2 → `CODIGO`
- Trabajadores v2 → `COD_APS`

## 4. Análisis por resource

### 4.1 Egresados v2 (`6a91f7e1-...-23`)

- **Bug confirmado:** searchScript ignora `query`. Causa raíz del
  incidente `91e67788` (~30K focuses).
- **Fix:** envoltorio sub-select + WHERE CODIGO = ?
- **Riesgo de regresión:** bajo. El SELECT base ya es una sub-select
  (`SELECT * FROM (... GROUP BY e.CODIGO)`), agregar otro nivel es
  trivial.

### 4.2 Trabajadores v2 (`6a91f7e1-...-21`)

- **Estado actual:** searchScript ignora `query`, PERO tiene
  `WHERE ROWNUM = 1` que limita el daño a 1 fila por task. **No se ha
  manifestado runaway porque el ROWNUM lo bloquea estructuralmente.**
- **Bug latente:** SÍ. Si alguien quita el `ROWNUM = 1` (necesario para
  pasar a recon masiva), el bug del filter ignorado vuelve a estar
  presente.
- **Decisión:** aplicar el fix simétrico AHORA. Es el momento adecuado
  porque (a) ya hay que tocar el archivo para el lifecycle proposed,
  (b) cuando se quite `ROWNUM = 1` para recon masiva el fix ya estará
  desplegado, (c) cohesión simétrica con egresados.
- **Importante:** mantener el `WHERE ROWNUM = 1` en su sitio mientras
  estamos en piloto. El fix solo agrega capacidad, no la activa.

### 4.3 Estudiantes v2 (`6a91f7e1-...-22`)

- **Estado actual:** searchScript ignora `query`, PERO tiene
  `AND ROWNUM <= 1` que limita el daño a 1 fila por task. Mismo patrón
  que trabajadores.
- **Bug latente:** SÍ. Mismo razonamiento que trabajadores.
- **Decisión:** aplicar fix simétrico. Mantener `ROWNUM <= 1`.

## 5. Plan de despliegue

### Defensa en profundidad (PRIMERO, antes de cualquier PUT)

PATCH a los 3 resources: `lifecycleState=proposed`. Esto evita que tareas
recurrentes accidentales los activen mientras estamos editando.

### Despliegue del fix

PUT en orden:
1. Trabajadores v2 (más complejo, sustituir primero)
2. Estudiantes v2
3. Egresados v2 (era el ofensor activo, último para mantener simetría)

Validación post-PUT (sin import task):
```bash
# REST: search scoped — debe devolver SOLO 1 objeto
curl -sk -u "$ADMIN_USER:$ADMIN_PASS" \
  "$URL/midpoint/ws/rest/resources/<oid>/objects?attribute=icfs:name&value=9610165"
```

Si devuelve más de 1 objeto, el fix no funcionó: revertir lifecycle a
`active` queda EXPLÍCITAMENTE prohibido hasta arreglar.

### Reactivación a `active`

Decisión del usuario. El estado `proposed` no impide búsquedas REST ni
test de funcionamiento; solo impide que MidPoint considere el resource
para sincronización automática.

## 6. Implementación — código Groovy single-line

Por directiva del proyecto el `searchScript` debe quedar en una sola
línea con `;` separadores. El bloque que se inserta al inicio:

```groovy
def whereClause = ''; def params = []; if (query != null) { if (query.operation == 'EQUALS' && !query.not && (query.left == '__NAME__' || query.left == '__UID__')) { whereClause = ' WHERE <PK_COL> = ? '; params << (query.right as String); } else { throw new UnsupportedOperationException('searchScript only supports EqualsFilter on __NAME__/__UID__; got: ' + query); } };
```

Y `sql.eachRow(query)` se cambia a `sql.eachRow(finalQuery, params)`
donde `finalQuery = "SELECT * FROM (${baseQuery})${whereClause}"`.

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| MidPoint envía query con AND (rare pero posible) → throws | Acepta riesgo: es preferible un error explícito a un runaway. Si la práctica muestra otros tipos válidos, ampliar el handler. |
| Quoting de comillas dentro del valor `right` | Se usa PreparedStatement parametrizado (`?` + params), no concat. |
| Cambio de schema de SELECT por envoltorio | El envoltorio `SELECT * FROM (...)` propaga columnas tal cual. Sin pérdida. |
| Multi-valor en PROGRAM_CODES (estudiantes) | Sin afectación: solo se filtra por CODIGO/COD_APS, las demás columnas siguen iguales. |
| Connector caches the script | `reloadScriptOnExecution=false` es el modo PROD. PUT del resource fuerza re-init del connector pool en MidPoint, recargando el script. |

## 8. Decisión sobre handlers no-Equals

Se evaluó implementar también StartsWith/Contains. **Descartado** porque:
- MidPoint no genera tales filtros para Import/Reconciliation tasks.
- Cualquier filter complejo legítimo cabe mejor como SQL en el view o
  como reconciliation con `objectQuery` aplicado en MidPoint server-side.
- KISS: cada handler adicional es superficie de ataque para nuevos
  runaways.

## 9. Referencias

- `doc/specs/multi-profile-canonical/05-forensic-audit.md` — auditoría
- Tirasa `ConnIdCommons/scripted/AbstractScriptedConnector.java` L585-620
- Tirasa `ConnIdDBBundle/scriptedsql/ScriptedSQLFilterTranslator.java`
- midpoint-best-practices §5.2 (resource hardening)
- iga-canonical-standards §1.3 (IIA read-only safety)
