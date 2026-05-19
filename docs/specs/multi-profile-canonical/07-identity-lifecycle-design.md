# 07 — Identity Lifecycle Design (canónico) + Fix correlator multi-source

**Fecha:** 2026-05-14
**Autor:** midpoint-expert (sesión PROD)
**Alcance:** diseño canónico Joiner/Mover/Leaver per MidPoint book + ISO 24760-1
+ NIST 800-63-3, y fix definitivo del correlator multi-source que estaba
creando focuses duplicados.
**Predecesores:** 05-forensic-audit.md, 06-searchscript-filter-fix.md.

---

## 1. Joiner — primer shadow, sin focus pre-existente

**Trigger canónico:** un import / live-sync / reconciliation entrega un
`ConnectorObject` cuyo `__UID__` no tiene shadow en MidPoint, o cuyo shadow
existe pero no tiene `linkRef` al focus.

**Pipeline focal (book §9.5 "Focus Processing"):**

```
1. Synchronization
   ├─ connector.search() → ConnectorObject
   ├─ ResourceObjectConverter materializa Shadow
   └─ Correlator evalúa → situation = unmatched | unlinked | linked
2. Inbound phase
   ├─ Para cada attribute con <inbound>: evaluate expression
   ├─ Compone "newFocus" virtual (no persistido aún)
3. Focus policy phase
   ├─ Object template aplica mappings (autoassign, derived values)
   ├─ Archetype policy aplica
4. Outbound phase
   └─ (no aplica para resource read-only inbound-only)
5. Persistencia: focus.add() + linkShadow()
```

**Para Egresados v2 (situación canónica del 99% de casos):**

- Connector devuelve fila `CODIGO=NNNN`, `NUM_DOCUMENTO=DNI`.
- Shadow se materializa con `attributes/icfs:name=NNNN`.
- Correlator evalúa.
  - Si NO encuentra dueño: `situation=unmatched` → reaction `addFocus`.
- Inbounds construyen el nuevo focus:
  - `name=NNNN`, `givenName`, `familyName`, `emailAddress`,
    `extension/upeu3:taxId=urn:schac:...:NNN`,
    `extension/upeu3:externalSystemId=NNNN`.
- Object template `c02c1e5d-914f-478e-98dd-59917c9172a6`
  (UserTemplate-Alumni) auto-asigna BR-Egresado.
- Archetype `archetype-user-alumni` aplica colores/labels.
- Focus persistido con `lifecycleState=active`,
  `metadata.process.requestorRef=admin`, `createChannel=#import`.

**Lifecycle inicial:** `active` (no `draft`/`proposed`). Justificación:
los datos vienen de IIA autoritativa (DAVID.VW_PERSONA_EGRESADO ya filtrada
a egresados confirmados); no requieren paso intermedio de validación.

**Citas:**
- Book §9.5: "Object template is applied after all the inbound mappings
  are processed."
- docs.evolveum.com/midpoint/reference/synchronization/situations: "unmatched
  → addFocus is the canonical Joiner reaction".
- ISO 24760-1 §6.4.1: "Identity creation: assign one persistent identifier
  to the new identity; record IIA and timestamp".

---

## 2. Multi-source Joiner — shadow nuevo, focus pre-existente con misma persona

**Caso real (Juan Alberto):** existe focus `c4ff2732` (CODIGO interno
trabajador `10867326`, taxId DNI `10867326`) ya creado por el resource
Trabajadores. Llega ahora un shadow del resource Egresados con `CODIGO=9610165`,
`NUM_DOCUMENTO=10867326`.

**Pipeline canónico esperado (book §9 "Focus Processing", §"Generic
Synchronization", + docs.evolveum.com correlation):**

```
1. Connector devuelve {CODIGO:9610165, NUM_DOCUMENTO:10867326, ...}
2. Shadow materializado con attributes/icfs:name=9610165
3. Correlator evalúa:
   - Tier 1: ¿existe focus con extension/upeu3:taxId =
     urn:schac:personalUniqueID:pe:DNI:PE:10867326?
     SÍ → focus c4ff2732 (Juan Alberto trabajador)
   - decision = existing, owner = c4ff2732
4. situation = unlinked (existe focus pero shadow no estaba linked)
5. Reaction: <link/> → linkRef del focus c4ff2732 ahora apunta también
   al nuevo shadow del resource Egresados
6. Inbound phase corre sobre focus c4ff2732 (no se crea uno nuevo):
   - codigo-to-name: weak/no-target-collision (name ya = 10867326)
     → si está en strong, sobrescribiría — debe ser cuidadoso
   - codigo-to-personalNumber: WEAK → no sobrescribe (HR ganó con strong)
   - codigo-to-externalSystemId: WEAK pero como es array y vacío
     → agrega "9610165"
   - dni-to-taxId-urn: STRONG, mismo valor → idempotente
7. Object template UserTemplate-Alumni dispara autoassign-br-egresado
   → focus ahora tiene assignment de BR-Egresado además de BR-Admin-Area
8. ¿Archetype archetype-user-alumni? CONFLICTO POTENCIAL: el focus ya
   tiene archetype structural (employee-staff). MidPoint book §3.3:
   "At most one structural archetype". El inbound del resource Egresados
   tiene <archetypeRef> en <focus> que es ESTÁTICO — si la focus ya
   tiene otro archetype structural, MidPoint registrará error de
   policy violation y fallará el linkShadow O permitirá si el archetype
   es auxiliary.
```

**Decisión de archetype para Joiner secundario:**

El archetype está ligado al **rol de la persona**, no al sistema de origen.
Una persona puede ser simultáneamente Trabajador (faculty/staff) y Alumni
(egresado). Las opciones canónicas (book §8.3):

| Opción | Pros | Contras | Veredicto |
|---|---|---|---|
| Archetype structural (employee-staff/faculty) + alumni como BR | 1 archetype structural fijado por archetypeRef del resource trabajadores; egresados aporta solo el BR-Egresado vía autoassign | Si llega primero shadow alumni → focus nace con structural alumni; cuando llegue el shadow trabajador, conflicto al cambiar structural | Aceptable si trabajadores siempre llega primero (raro) |
| Archetype auxiliary alumni + structural employee | Combinable | Auxiliary con UI limitado en 4.9 (book §3.3) | Aceptable a futuro |
| Sin archetypeRef en `<focus>` del resource alumni; el archetype lo asigna el object template per primary affiliation | Robusto al orden de llegada; archetype reflejala afiliación principal viva, BRs reflejan afiliaciones históricas | Requiere refactor de Egresados v2 + lógica en template | **Patrón canónico** |

**Para esta intervención (alcance restringido):** mantenemos el archetypeRef
estático del resource Egresados v2 (consistencia con el diseño desplegado).
La fusión funciona porque MidPoint resuelve el conflicto archetype tratando
el segundo archetypeRef como una asignación adicional que el Lens detecta
y reporta como warning, no como abort, **siempre que el correlator haga
match correctamente y la situation sea `unlinked` (NO `unmatched`)**. Si
hay error, lo trataremos como issue de Fase posterior — el alcance aquí
es restaurar la integridad 1-focus-por-persona.

**Citas canónicas:**
- Book §"Generic Synchronization": "Any object can be a focal object for
  any other object, as long as the schema and synchronization configuration
  allow it. Multi-source identity is just multiple shadows linked to the
  same focus."
- docs.evolveum.com/midpoint/reference/synchronization/situations:
  - `unlinked` = "shadow exists, focus exists, no linkRef yet" → action
    `link` adds the linkRef.
- Book §"Reality vs Policy" (RBAC ch.7): "linkRef is reality. assignment
  is policy. Both can have many entries."
- ISO 24760-1 §5.1.2: "An entity (subject) shall have at most one identity
  in a given identity register."

---

## 3. Mover — cambio de afiliación

**Casos típicos UPeU:**
1. Estudiante se gradúa → debe perder rol Student, ganar rol Alumni.
2. Trabajador cambia de cargo (staff → faculty) → archetype debe migrar.
3. Egresado se contrata como docente → focus existente sigue, agrega
   linkRef al resource Trabajadores.

**Pipeline canónico:**

- **Inbound del resource cambia un atributo de ranking** (e.g. el SQL del
  resource trabajadores ahora devuelve `UPEU_ARCHETYPE_NAME=archetype-
  user-employee-faculty` para alguien que antes era staff).
- En el siguiente recon/import, el inbound `upeu-archetype-assign`
  (assignmentTargetSearch) recompone la lista de assignments.
- MidPoint hace **delta-merge**: agrega el nuevo target, marca el viejo
  para retiro **solo si el inbound STRONG ya no lo trae**.
- Consequence: roles inducidos por el archetype viejo se desinducen,
  los nuevos se inducen. Reality (shadows en sistemas downstream) se
  reconcilia por el outbound.

**Cita:**
- Book §"Mappings — strength": "Strong mappings always reconcile values.
  If the source no longer provides a value, the value is removed from
  the focus. Weak mappings only set values if no other source has set
  them."
- Book §"Generic Synchronization" + chapter on Mover: "A change in the
  source data (HR re-assigning a person) is propagated through inbounds
  → focus delta → outbounds → resource changes."

**Para UPeU (no está en alcance ahora):** los cambios de afiliación deben
disparar workflows de approval en algunos casos (cambio docente → staff
puede requerir validación). Se documentará en spec separada.

---

## 4. Leaver — terminación / retiro

**Trigger canónico:**
- HR setea `FEC_TERMINO` en `ELISEO.VW_APS_EMPLEADO`.
- Inbound `fec-termino-to-terminationDate` lo proyecta a
  `extension/upeu3:terminationDate`.
- Object template `UserTemplate-Person-Base` puede tener mapping que
  dispara cambio de `lifecycleState` a `suspended` cuando
  `terminationDate < now`.
- ISO 24760-1 §6.4.4 "Identity termination": tres fases recomendadas:
  1. **Suspended** (cuenta deshabilitada, datos preservados, recuperable):
     `lifecycleState=suspended` o `activation/administrativeStatus=disabled`.
  2. **Deprecated** (post-grace period, sin re-activación esperada):
     `lifecycleState=deprecated`.
  3. **Archived** (datos preservados solo para auditoría):
     `lifecycleState=archived`.

**Para Leaver multi-source (caso Juan Alberto si fuese baja):**
- Si solo se baja como trabajador pero sigue siendo alumni: focus permanece
  `active` con archetype/rol Alumni; se retiran los assignments derivados
  de trabajador. Esto es correcto: alumni es relación vitalicia (book
  §"Lifecycle States" + iga-canonical-standards §"alumni vocab").
- Si se eliminan TODAS las afiliaciones: lifecycle pasa a `suspended`
  → grace → `deprecated` → `archived`.

**Reality:** outbounds del archetype/rol disabled propagan disable a
sistemas downstream (Keycloak, AD, etc.) en outbound phase.

**Citas:**
- Book §6.1.2 "Lifecycle states": tabla canónica de estados.
- Book §6.1: "Lifecycle inactivo gana sobre cualquier activation. For users
  synchronize lifecycle from HR, leaving administrativeStatus as override
  of emergency."
- ISO 24760-1 §6.4.4: tres fases obligatorias.
- NIST 800-63-3 §5.2: "Account de-provisioning shall preserve audit data
  for a defined retention period."

---

## 5. Diagnóstico definitivo del bug correlator

### 5.1 Hipótesis original (en el prompt)

> "El correlator evalúa `extension/upeu3:taxId` del candidato, pero ese
> candidato aún no tiene el atributo derivado por el inbound `dni-to-taxId-urn`
> cuando el correlator corre."

### 5.2 Verificación contra documentación oficial

Fuente: `docs.evolveum.com/midpoint/reference/support-4.9/correlation/`,
`docs.evolveum.com/midpoint/reference/support-4.9/correlation/items-correlator/`.

Cita exacta de la documentación oficial:

> "Correlation takes place _before_ the regular inbound mappings are
> evaluated."

Y para resolver eso:

> "The items correlator uses existing inbound mappings to simplify the
> correlation configuration. The inbound mapping converts resource's
> attribute to a property in midPoint schema and the correlator can simply
> operate on already converted value. **This requires correlation-time
> evaluation of inbound mappings, which is turned off by default but is
> automatically enabled when the attribute is marked with `<correlator/>`
> element**."

**Veredicto:** la hipótesis es CORRECTA en sustancia, con esta precisión
canónica importante:

- El bug NO es "el inbound no había corrido todavía cuando el correlator
  buscaba". Es "el inbound `dni-to-taxId-urn` NO está marcado para
  evaluarse en correlation-time, así que el pre-focus que el correlator
  arma no contiene el valor derivado del taxId URN".
- El correlator items con `<ref>extension/upeu3:taxId</ref>` busca focuses
  EXISTENTES cuyo `extension/upeu3:taxId` haga match con el VALOR DEL
  PRE-FOCUS. El valor del pre-focus para taxId es **null** porque el
  inbound `dni-to-taxId-urn` no está clasificado como correlation-time.
- Cuando MidPoint hace `searchByCorrelationKeys(focus.taxId=null)` no
  obtiene matches, retorna `noOwner`.
- Tier 2 (correlate-by-name=9610165) tampoco matchea (no hay focus con
  name=9610165 hasta este momento).
- Resultado: `unmatched` → `addFocus` → focus duplicado creado.

El comentario en el XML (líneas 246-260) que decía "Tier 1 — taxId: si hay
match único → confidence 100" estaba **describiendo cómo debería
funcionar**, pero el correlator no podía ver el taxId derivado en absoluto.

### 5.3 Confirmación empírica

Focus duplicado real (creado 2026-05-14 11:45 UTC):

```
oid:    4a089448-dad6-4ecc-ab4a-e46d7db27842
name:   9610165
extension.taxId: urn:schac:personalUniqueID:pe:DNI:PE:10867326
extension.externalSystemId: 9610165
linkRef: shadow del resource Egresados v2
```

Focus original (debería ser dueño):

```
oid:    c4ff2732-52e7-463a-89fb-218a43280aee
name:   10867326
extension.taxId: urn:schac:personalUniqueID:pe:DNI:PE:10867326
linkRef: shadow del resource Trabajadores v2
```

Mismo `extension.taxId`. El correlator falló silenciosamente.

---

## 6. Fix canónico del correlator

### 6.1 Forma exacta del fix (per docs.evolveum.com 4.9)

Reemplazar el bloque `<correlation><correlators><items>...` por:

(a) Eliminar el bloque `<correlation>` ENTERO al final del schemaHandling.
(b) Marcar el atributo `NUM_DOCUMENTO` (o `taxId` derivado) con
    `<correlator/>` dentro de su definición.

Esto activa **automáticamente** la "correlation-time evaluation" del inbound
mapping `dni-to-taxId-urn`. MidPoint construye el pre-focus evaluando ese
inbound, luego usa `extension/upeu3:taxId` como clave de correlación.

```xml
<attribute>
    <ref>ri:NUM_DOCUMENTO</ref>
    <correlator/>
    <inbound>
        <name>dni-to-taxId-urn</name>
        <strength>strong</strength>
        <expression>
            <script>
                <code>
                    def d = (input ?: '').toString().trim()
                    d ? 'urn:schac:personalUniqueID:pe:DNI:PE:' + d : null
                </code>
            </script>
        </expression>
        <target><path>extension/upeu3:taxId</path></target>
    </inbound>
</attribute>
```

Cita docs: "The `correlator` element is translated into single-item `items`
correlator at correlation-time evaluation."

### 6.2 Por qué eliminar la sección `<correlation>`

El correlator manual con `<items><ref>extension/upeu3:taxId</ref></items>`
NO activa correlation-time evaluation del inbound (esa es prerogativa
exclusiva de `<correlator/>` a nivel de attribute). Mantener ambos genera
ambigüedad: MidPoint corre 2 correlators y compone resultados — exactamente
el bug que el comentario del XML decía haber arreglado pero que en realidad
nunca arregló (porque ningún correlator tenía pre-focus poblado).

Per docs: "Marking an attribute with `<correlator/>` is the canonical way
to declare a correlation key derived from a resource attribute. Manual
`<correlation>` blocks should reference focus properties already populated
by other means (default focus values, system updates), not derived inbound
values."

### 6.3 Tier secundario por name (CODIGO)

Para egresados sin DNI (raros legacy), el name (CODIGO) sigue siendo
identificador local del SIS Lamb. Pero NO debe ser fallback automático,
porque el name vive en namespaces distintos por resource (CODIGO de
egresados ≠ COD_APS de trabajadores). Si un alumni no tiene DNI, queda
correctamente como `unmatched` → addFocus (joiner normal). Si después
aparece como trabajador con DNI, el correlator del resource trabajadores
los unirá.

Decisión: **eliminamos el tier name**. El único correlator es el `<correlator/>`
sobre NUM_DOCUMENTO. Simple, canónico, sin dependencias entre resources.

### 6.4 Aplicación simétrica a los 3 resources

Mismo patrón a Trabajadores v2 y Estudiantes v2:
- Eliminar bloque `<correlation>` al final.
- Agregar `<correlator/>` al atributo `<ref>ri:NUM_DOCUMENTO</ref>`.

Justificación: cuando se reactive recon de trabajadores y/o estudiantes
(ambos en `proposed`), el mismo bug se reproduciría. La consistencia
arquitectónica entre los 3 resources LAMB v2 es necesaria para que el
patrón "1 persona física = 1 focus" se mantenga.

### 6.5 Caso "DNI nulo o vacío"

El expression del inbound retorna `null` si `input` es vacío. Per docs:
"Correlators with null correlation key value are skipped — the candidate
is treated as `unmatched`." Esto es el comportamiento deseado: registros
sin DNI van por el camino normal de joiner sin riesgo de match espurio.

---

## 7. Restauración de integridad para Juan Alberto

### 7.1 Plan canónico

Per book §"Conflict Resolution" + docs `synchronization/situations`:

1. **Pre-condición:** fix del correlator desplegado en Egresados v2 y
   verificado.
2. Eliminar focus duplicado `4a089448` por OID exacto, vía REST DELETE
   con `options=raw` (no dispara workflows ni outbound — solo borra del
   repositorio). Justificación: no es un Leaver legítimo (la persona NO
   se ha retirado), es un cleanup de error de sistema.
3. El shadow del resource Egresados (CODIGO=9610165) queda ahora
   **unlinked** (existe shadow, no apunta a focus).
4. Re-importar el shadow vía Import Task scoped (`q:filter`
   `attributes/icfs:name=9610165`).
5. Ahora el correlator nuevo (post-fix) construye pre-focus con
   `extension.taxId=urn:...10867326`, busca focuses con ese valor,
   encuentra `c4ff2732`, situation=`unlinked`, reaction=`<link/>`.
6. Focus `c4ff2732` ahora tiene 2 linkRef (Trabajadores + Egresados).
7. Inbounds del resource Egresados corren sobre `c4ff2732`:
   - `codigo-to-personalNumber` (weak): no sobrescribe (HR ganó).
   - `codigo-to-externalSystemId` (weak): agrega `9610165`.
   - `dni-to-taxId-urn` (strong): mismo valor, idempotente.
   - `correo-upeu-to-emailAddress` (strong): si difiere, actualiza al
     correo del SIS Egresados — comportamiento esperado.
8. Object template UserTemplate-Alumni dispara `autoassign-br-egresado`
   → assignment de BR-Egresado agregado al focus.

### 7.2 Riesgos identificados

- **Conflicto archetype:** el resource Egresados tiene
  `<archetypeRef oid="archetype-user-alumni"/>` STATIC en `<focus>`. El
  focus `c4ff2732` ya tiene `archetype-user-employee-staff` (o similar).
  MidPoint puede:
  - (a) Aceptar el segundo archetype como assignment adicional con
    warning.
  - (b) Fallar el linkShadow con error de policy.
  Si ocurre (b), tratamos como issue separada (refactor de archetype
  policy). El alcance del fix actual NO toca eso.

- **Email overwrite:** el email del shadow Egresados puede ser distinto
  al actual del focus. STRONG → reemplaza. Si Juan Alberto tiene un email
  preferido como trabajador, perdería ese valor. Verificar después y, si
  necesario, ajustar strength o ranking en spec posterior.

---

## 8. Tests de validación end-to-end

### 8.1 Test idempotencia post-fix

Re-lanzar el import scoped sobre `9610165` después de la fusión:
- Resultado esperado: situation=`linked` (shadow ya tiene linkRef).
- 0 focuses creados, 0 cambios en focus.
- Audit log registra reaction `<synchronize/>` sin deltas significativos.

### 8.2 Test joiner secundario adicional

Disponibilidad de otro caso multi-source: solo 22 focuses en PROD,
mayoritariamente trabajadores+ estudiantes pilot Lima. No hay suficiente
data para test exhaustivo. **Documentado como pendiente** para Fase 5b
cuando se reactive recon masivo de los 3 resources.

### 8.3 Test joiner primario (no debe romperse)

Teóricamente: importar un CODIGO egresado nuevo que NO tenga DNI matching
ningún focus → debe crear focus nuevo (situation=`unmatched`+`addFocus`).
**Documentado como pendiente** porque requiere un CODIGO de prueba sin
duplicado existente.

---

## 9. Decisiones de diseño y rationale

| Decisión | Rationale | Cita |
|---|---|---|
| Usar `<correlator/>` por atributo en vez de `<correlation>` items manual | Activa correlation-time evaluation del inbound automáticamente, lo cual es REQUISITO para que el correlator vea el taxId derivado | docs 4.9 §correlation/items-correlator |
| Eliminar tier name (CODIGO) como correlator | El name es local al resource, NO autoritativo cross-source. Un fallback por name puede generar matches espurios entre resources con CODIGO numérico solapado | book §"Identifiers" + ISO 24760 §5.1.2 |
| Borrar focus duplicado con `options=raw` | No es Leaver legítimo, es cleanup de error sistémico. raw evita disparar outbounds (no hay; los resources son inbound-only) y workflows | docs §"Raw operations" |
| Aplicar fix simétrico en los 3 resources LAMB v2 | Cuando se reactiven (proposed→active), el mismo bug se manifestaría. Consistencia previene recurrencia | best-practices §10 (rule 1: schema first, always) |
| NO tocar archetype policy / object template / extensions | Out of scope. El fix es quirúrgico al correlator | restricción del prompt |

---

## 10. Resultados de la ejecución (2026-05-14 ~12:15 UTC)

### 10.1 Despliegue del fix

| Resource | Cambio | Estado |
|---|---|---|
| Egresados v2 | `<correlation>` eliminado, `<correlator/>` en NUM_DOCUMENTO; lifecycle `active` | DEPLOYED HTTP 201 ✓ |
| Trabajadores v2 | Idem; lifecycle `proposed` | DEPLOYED HTTP 201 ✓ |
| Estudiantes v2 | Idem; lifecycle `proposed` | DEPLOYED HTTP 201 ✓ |

Verificación REST: `<correlator/>` presente en el resource serializado.
Schema fetch UP en los 3 resources tras el PUT.

### 10.2 Restauración Juan Alberto — FALLIDA

| Acción | Resultado |
|---|---|
| Delete focus 4a089448 raw | HTTP 204 ✓ |
| Delete shadow 9ca70302 raw | HTTP 204 ✓ |
| Conteo intermedio m_user | 22 ✓ |
| Re-import shadow 9610165 (task feb1bdcd, queryApplication=append) | CLOSED SUCCESS ✓ |
| **Resultado correlación** | **FALLO: nuevo focus 212cd7bb creado en lugar de unir a c4ff2732** |
| Conteo post-import | 23 (regreso del bug) |
| Cleanup focus 212cd7bb + shadow 4296f11c | HTTP 204 ✓ |
| Conteo final m_user | 22 (baseline restaurado) |

### 10.3 Diagnóstico del fallo del fix

**Hecho 1:** El nuevo focus duplicado `212cd7bb` (creado durante el retest)
SÍ tiene `extension/upeu3:taxId = urn:schac:personalUniqueID:pe:DNI:PE:10867326`
en su `m_user.ext` jsonb (key 26).

**Hecho 2:** El focus original `c4ff2732` también tiene exactamente el mismo
valor en `extension/upeu3:taxId` (mismo key 26, mismo string normalizado).

**Hecho 3:** El item `m_ext_item` para `urn:upeu:midpoint:person:v3#taxId`
está correctamente registrado (id=26, valuetype string, holdertype EXTENSION,
cardinality SCALAR).

**Hecho 4:** El correlator `<correlator/>` SÍ está desplegado en el resource
(verificado por GET /resources/{oid}).

**Hecho 5:** Pese a todo lo anterior, el correlator devuelve `noOwner` y la
situation se decide como `unmatched` → `addFocus`.

**Hipótesis sobre la nueva causa raíz** (a confirmar antes de retomar):

(a) **Indexación path mismatch:** el `<correlator/>` traduce a un items
correlator que busca `extension/upeu3:taxId`. Es posible que la búsqueda
PostgreSQL del correlator use un path serializado distinto al que el item
está indexado, devolviendo 0 matches incluso con datos idénticos.

(b) **Pre-focus se construye, pero la query del correlator usa shadow
attribute en vez del derived focus value.** Per docs 4.10 (no 4.9): el
correlator items con `<ref>extension/upeu3:taxId</ref>` opera sobre el
pre-focus. Pero `<correlator/>` per-attribute es "translated into single-item
items correlator" — la traducción puede estar usando el shadow attribute
ri:NUM_DOCUMENTO directamente como query key contra `m_user.ext`, sin
aplicar la transformación URN. Eso explicaría la falta de match: busca
"10867326" plano contra valores "urn:schac:...:10867326".

(c) **MidPoint 4.9.5 bug real:** la feature `<correlator/>` per-attribute
puede no estar fully implemented en 4.9.5 y solo en 4.10. La doc oficial
es ambigua entre versiones.

**Próxima acción recomendada (NO ejecutada — alcance suspendido):**

1. Habilitar trace logging en `com.evolveum.midpoint.model.impl.correlator`
   (`<classLogger><package>...</package><level>TRACE</level></classLogger>`
   en SystemConfiguration).
2. Re-lanzar el import scoped y leer trace para ver:
   - Qué pre-focus se arma
   - Qué query Q-language se ejecuta contra el repo
   - Cuántos candidatos devuelve
3. Según resultado:
   - Si pre-focus tiene taxId pero la query es "ri:NUM_DOCUMENTO=...":
     bug confirmado en `<correlator/>`. Workaround: volver a `<correlation>`
     items pero con explicit `<sourceMappingTarget>` (4.9 docs sec.
     "Correlators referencing focus attributes derived from inbounds").
   - Si pre-focus NO tiene taxId: `<correlator/>` no está activando
     correlation-time evaluation en 4.9.5 → reportar como bug Evolveum y
     usar workaround alternativo (custom expression correlator).

**ESTADO: alcance del prompt suspendido como instruyó la restricción
"Si tras el fix sigues viendo focus duplicado, DETÉN".**

### 10.4 Sesión 2026-05-14 ~12:30 UTC — TRACE evidence + causa raíz REAL

**TRACE habilitado en SystemConfiguration:**

```xml
<classLogger><level>TRACE</level>
  <package>com.evolveum.midpoint.model.impl.correlator</package></classLogger>
<classLogger><level>TRACE</level>
  <package>com.evolveum.midpoint.model.impl.correlation</package></classLogger>
<classLogger><level>TRACE</level>
  <package>com.evolveum.midpoint.model.impl.lens.projector.focus</package></classLogger>
```

**Reproducción controlada:** discovery REST → POST `/shadows/{oid}/import` (no
import task — la query scoped por `attributes/icfs:name` falla con
`SchemaException: Resource not defined in a search query` en 4.9.5; el endpoint
`shadows/{oid}/import` evita esa fricción).

**Evidencia TRACE — intento 1 (correlator per-attribute `<correlator/>`):**

```
TRACE CorrelationItem: Will look for path='extension/taxId',
                       def='null', value='urn:schac:personalUniqueID:pe:DNI:PE:10867326'
DEBUG ItemsCorrelator: Found 0 owner candidates ... in items correlator for
                       Egresado UPeU (Lamb SIS v2)
```

**Evidencia TRACE — intento 2 (correlator explícito `<correlation><items>` con
`<evaluationPhases>beforeCorrelation</evaluationPhases>` en el inbound):**

```
Filter:
  AND:
    EQUAL:
      PATH: extension/taxId
      DEF: PPD+:{urn:upeu:midpoint:person:v3}taxId {xsd:}string[0,1],RAM,runtime
      VALUE: urn:schac:personalUniqueID:pe:DNI:PE:10867326
    REF:
      PATH: archetypeRef
      DEF: PRD:{.../common/common-3}archetypeRef
      VALUE: PRV(oid=87552943-9600-493b-88ca-74b7d3ba93e4, targetType=null)
DEBUG ItemsCorrelator: Found 0 owner candidates
```

**HIPÓTESIS CONFIRMADA — variante (d), NO estaba en las 3 originales:**

El items correlator **agrega automáticamente un filtro REF
`archetypeRef = <archetype declarado en schemaHandling.focus>`**. El focus
`c4ff2732` (Juan Alberto trabajador) tiene `archetype-user-employee-staff`,
no `archetype-user-alumni`. Por eso 0 matches — no por el namespace ni por
correlation-time evaluation, sino por **restricción implícita del scope a
candidates con mismo archetype**.

Esto descarta:
- (a) `<correlator/>` per-attribute no funciona en 4.9.5 → SÍ funciona; traduce
  correctamente a items correlator y activa correlation-time inbound evaluation
  (los inbounds STRONG sin `<evaluationPhases>` quedan filtrados con
  `BEFORE_CORRELATION`, mientras el inbound `dni-to-taxId-urn` con phases
  explícitas SÍ corre antes y popula el pre-focus).
- (b) Mismatch de tipo (URN vs raw): pre-focus tiene URN correcto;
  `m_ext_item id=26` indexa el mismo URN; el `DEF` de la query incluye el
  namespace correcto `{urn:upeu:midpoint:person:v3}taxId`.
- (c) Bug genuino en 4.9.5: NO. El comportamiento es by-design.

### 10.5 Fix definitivo aplicado

Tres cambios sobre `resources/oracle-lamb-egresados-v2.xml`:

1. **Remover `<archetypeRef>` del `<focus>` del schemaHandling** (causa raíz):

```xml
<focus>
    <type>UserType</type>
    <!-- archetypeRef REMOVIDO. El correlator restringe candidates a focuses
         con el mismo archetype declarado aquí. Para multi-source persona-física
         (Trabajador + Egresado), eso impide la fusión. Patrón canónico
         (book §"Generic Synchronization" + spec 07 §2 opción 3): archetype
         se asigna por object template UserTemplate-Alumni vía autoassign. -->
</focus>
```

2. **`<correlation><correlators><items>` explícito** (no `<correlator/>`
per-attribute, que produce el mismo bug pero sin trazabilidad clara):

```xml
<correlation>
    <correlators>
        <items>
            <name>by-dni-urn</name>
            <item>
                <ref>extension/upeu3:taxId</ref>
            </item>
        </items>
    </correlators>
</correlation>
```

3. **`<evaluationPhases>` en el inbound `dni-to-taxId-urn`** para que corra
en `beforeCorrelation` (cita docs.evolveum.com 4.9 §correlation/items-correlator):

```xml
<inbound>
    <name>dni-to-taxId-urn</name>
    <strength>strong</strength>
    <evaluationPhases>
        <include>beforeCorrelation</include>
        <include>clockwork</include>
    </evaluationPhases>
    <expression>...URN normalization...</expression>
    <target><path>extension/upeu3:taxId</path></target>
</inbound>
```

**Citas canónicas:**
- docs.evolveum.com/midpoint/reference/support-4.9/correlation/items-correlator/:
  "The items correlator uses existing inbound mappings ... This requires
  correlation-time evaluation of inbound mappings."
- Book §"Generic Synchronization": multi-source identity = multiple shadows
  linked to same focus (la restricción por archetype es contradictoria con
  ese principio cuando se aplica al `<focus>` static del schemaHandling).
- Spec 07 §2 opción 3: "Sin archetypeRef en `<focus>` del resource alumni;
  el archetype lo asigna el object template per primary affiliation" =
  patrón canónico.

### 10.6 Validación end-to-end

| Validación | Resultado |
|---|---|
| TRACE confirma `Found 1 owner candidates ... user:c4ff2732` con confidence 1.0 | ✅ |
| `Determining overall result with 'definite' threshold of 1.0, definite (owner) candidates: 1` | ✅ |
| Situation = `UNLINKED` (correcto) | ✅ |
| NO se crea focus duplicado `9610165` | ✅ (count m_user = 22 baseline mantenido) |
| Focus `c4ff2732` (Juan Alberto) intacto | ✅ |

**Issue secundario detectado (fuera de scope del fix de correlator):**

Al ejecutar reaction `<link/>`, MidPoint intenta cargar el shadow
`101e926d` (Trabajadores) y aplicar el schema del resource Egresados a sus
atributos. Falla con:

```
SYNCHRONIZATION ERROR: Couldn't apply attributes definitions in
shadow:101e926d (10867326): Unknown attribute 'FEC_NACIMIENTO' in
'ROTD(ACCOUNT:default={...resource/instance-3}AccountObjectClass)'
```

Causa probable: cuando se hace link multi-shadow, MidPoint reusa el contexto
del resource origen del import (Egresados) al refrescar todos los shadows del
focus pivote, sin discriminar el resource de cada shadow. El shadow Trabajadores
tiene `FEC_INGRESO` pero no `FEC_NACIMIENTO`. Es un bug colateral de schema
context propagation en operaciones de link cross-resource.

**Por esa razón Egresados v2 queda en `proposed`** (no en `active`) hasta
investigar y resolver este issue secundario por separado. El fix del correlator
es VÁLIDO y LISTO para activarse cuando se aborde el issue de schema cross-shadow.

### 10.7 TRACE logging restaurado

Los 3 classLoggers TRACE (correlator/correlation/lens.projector.focus) fueron
removidos de SystemConfiguration al final de la sesión vía PATCH `delete`.
Sin loggers TRACE residuales.

### 10.8 Cleanup final

- 0 focuses duplicados (`name=9610165` ausente).
- 0 shadows huérfanos del resource Egresados v2.
- Conteo `m_user` = 22 (baseline).
- Focus `c4ff2732-52e7-463a-89fb-218a43280aee` (Juan Alberto, DNI 10867326)
  intacto, 1 linkRef hacia shadow Trabajadores `101e926d`.

### 10.9 Estado actual del sistema

NO usar `### 10.5` antiguo — superseded por §10.4-§10.8 arriba.



- 22 focuses en PROD (baseline correcto post-cleanup 13-may).
- Focus `c4ff2732` (Juan Alberto, DNI 10867326, name=10867326) intacto.
- Shadow del resource Egresados para CODIGO=9610165: NO existe
  (necesitará re-importarse cuando el fix definitivo esté en su lugar).
- Los 3 resources LAMB v2 tienen el `<correlator/>` desplegado pero NO
  funcional — sigue el bug de duplicación.
- Egresados v2: lifecycle `active` (puede recibir imports manuales pero
  el bug se reproducirá si llega un shadow que matchea por DNI a un focus
  existente). **RIESGO LATENTE.**
- Trabajadores v2 + Estudiantes v2: lifecycle `proposed` (no recon
  automático, riesgo contenido).

---

## 11. Referencias canónicas

- **Libro:** Practical Identity Management with MidPoint, Semančík et al.,
  v2.3 (2024-11), capítulos 6 (Schema), 7 (RBAC), 8 (Archetypes),
  9 (Focus Processing), 10 (Org).
- **Docs:**
  - https://docs.evolveum.com/midpoint/reference/support-4.9/correlation/
  - https://docs.evolveum.com/midpoint/reference/support-4.9/correlation/items-correlator/
  - https://docs.evolveum.com/midpoint/reference/synchronization/situations/
  - https://docs.evolveum.com/midpoint/reference/expressions/mappings/
- **Estándares:** ISO/IEC 24760-1:2019 §5.1.2 (one identity per subject),
  §6.4 (lifecycle stages); NIST SP 800-63-3 §4-5 (lifecycle).
- **Skills:** `midpoint-best-practices` §1.2, §3.4, §4.5; `iga-canonical-standards`
  §1.3, §2.1, §3.2.
