# Runbook — Reactivación canónica Koha ILS + LDAP (2026-05-30)

**Estado:** DISEÑO (read-only). No ejecuta cambios. Para revisión y aprobación del usuario.
**Autor:** midpoint-expert (Claude Code)
**Skills consultadas:** `midpoint-best-practices` (§1.2 lifecycle, §4.2 conditions/strength, §4.5 pipeline outbound, §7 constructions/inducement conditions), `iga-canonical-standards` (§1.2 ISO 24760 lifecycle, §1.3 IIA, §3.2 eduPerson affiliations, §10.1 archetypes).

---

## 0. Resumen ejecutivo

MidPoint gobierna el **ciclo de vida completo** de cada identidad (active/suspended/archived) y proyecta a cada sistema **solo el subconjunto que ese sistema necesita**:

| Sistema | Población proyectada | Leaver | Identificador del leaver |
|---|---|---|---|
| **Koha ILS** | Activos con afiliación viva (worker/faculty con contrato, student matriculado) + Visitas | **ARCHIVAR** (expirar + bloquear carnet) — **preservar transacciones para métricas** | `__DISABLE__` → `patron_card_lost=true` + `expiry_date=ayer` (NO delete) |
| **LDAP Identity Cache** | Solo activos con afiliación viva | **DEPROVISIONAR** (delete shadow LDAP) | inducement condicional, ya implementado |

**MidPoint NO pierde a nadie:** jubilados, ex-trabajadores y alumnos no matriculados siguen en MidPoint con su `lifecycleState`. Simplemente no se proyectan como *activos*. En Koha además se conserva el patrón archivado (estadística), en LDAP se deprovisiona.

**Hallazgo clave (mecanismo de archivado Koha YA EXISTE en el conector):** `connector-koha` v1.3.x `PatronMapper.applyEnableAttribute(enabled=false)` ejecuta exactamente el archivado-no-borra:
```java
payload.put("patron_card_lost", true);                          // bloqueo inmediato del carnet
payload.put("expiry_date", LocalDate.now().minusDays(1));       // expiración temporal
```
`computeEnabled()` deriva `__ENABLE__ = !(patron_card_lost || expired)`. `anonymized` y `expired` son read-only. **No requiere desarrollo nuevo de conector.** El archivado canónico se obtiene con `administrativeStatus=disabled` en el shadow Koha (NO con delete). Las transacciones (`old_issues`, `statistics`) permanecen intactas porque el patrón nunca se borra.

---

## 1. PASO 1 — Análisis del estado actual y de lo hecho antes

### 1.1 Estado en PROD (2026-05-30)

| Resource | OID | lifecycleState (repo) | Shadows vivos | Shadows dead |
|---|---|---|---|---|
| Koha ILS | `9b5a7c81-47aa-42ac-9a08-4de8b64935af` | `active` (repo) — confirmar en PROD si `proposed` | **13.805** | 0 |
| LDAP-IdentityCache-UPeU | `7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f` | `active` | **5.836** | 1 |

> Nota: el repo trae `koha-ils.xml` con `<lifecycleState>active</lifecycleState>`. Verificar el valor efectivo en PROD antes de reactivar — el encargo asume `proposed`. Si en PROD está `proposed`, el paso de reactivación es `proposed → active` sobre el objectType (no el resource).

### 1.2 Conector Koha — capacidades para archivado (revisión v1.3.x)

`~/proyectos/upeu/connector-koha`:
- `deletePatron(uid)` existe (DELETE) — **NO se usará para leavers** (borraría transacciones).
- `applyEnableAttribute(payload, false)` → `patron_card_lost=true` + `expiry_date=ayer`. **Este es el archivado canónico.**
- `computeEnabled()` → inbound de `__ENABLE__` desde `patron_card_lost OR expired`.
- `expired` (read-only): lo calcula Koha desde `expiry_date < hoy`.
- `anonymized` (read-only): bandera GDPR de Koha; no la gestionamos desde MidPoint.
- `addRemoveAttributeValues=true`: deltas granulares (ya usado en `extended_attributes`).

**Conclusión:** el conector soporta nativamente "archivar no borrar". El archivado = `__DISABLE__`. Koha preserva `borrowers.borrowernotes`, historial de préstamos (`old_issues`) y estadísticas aunque el patrón esté expirado/bloqueado. Mecanismo Koha de "anonimización con preservación estadística" (`AnonymousPatron` + `anonymize`) NO es necesario: expirar conserva más datos para métricas que anonimizar.

### 1.3 Decisiones de diseño Koha previas — qué sigue válido / qué rehacer

| Pieza previa | Estado | Veredicto |
|---|---|---|
| Correlación 3-capas (cardnumber=name, lambDocNum=DNI, taxId=URN SCHAC) | implementada | **VÁLIDA** — robusta contra duplicados legacy. Mantener. |
| `unmatched` sin acción (no inactiva cuentas que MidPoint no reconoce) | implementada | **VÁLIDA** — Koha no es IIA; MidPoint no resta lo que no creó. Mantener. |
| `deleted → unlink` + `deadShadowRetentionPeriod=P3D` | implementada | **VÁLIDA**. Mantener. |
| `library_id` desde locality (BUL/BUJ/BUT/CIA) | implementada | VÁLIDA. Mantener. |
| Foto vía JDPC weak passthrough | implementada | VÁLIDA. Mantener. |
| **Sin `<existence>` / condición de cuenta** | **AUSENTE** | **REHACER** — hoy todo user con AR-Koha-* o mapping activo crea patrón. Con estructura madura hay que condicionar la existencia a afiliación viva. |
| **`category_id` = DOCEN/ADMINIST/PREGRADO/POSGRADO/ALUMNI** (resource líneas 1064-1086) | implementada en resource | **CONFLICTO** con `docs/DECISION-eduperson-koha-categorycodes.md` (APROBADA, no implementada) que manda `category_id = primaryAffiliation` literal eduPerson (faculty/staff/student/alum). **DECIDIR** (ver §2.3). |
| Roles `AR-Koha-Jubilado`, `AR-Koha-Patron-Alumni` con override category | implementadas | **REVISAR** a la luz del nuevo scope (jubilado/alumni → archivar en Koha, no categoría activa). |
| Activation outbound: jubilado→enabled perenne | implementada | **REVISAR/INVERTIR** — bajo el nuevo scope, jubilado/alumni NO matriculado = leaver → archivar (disabled), NO acceso perenne. |

### 1.4 LDAP — qué sigue válido

| Pieza | Estado | Veredicto |
|---|---|---|
| `AR-LDAP-Person` con `<condition>` `lifecycleState==active or null` en el **inducement** | implementada | **VÁLIDA y suficiente** para "solo activos". Cuando lifecycle deja de ser active, MidPoint deprovisiona (delete shadow LDAP) en el siguiente recompute. |
| Capability `activation` removida (LDAP read-only de MidPoint, no escribe estado) | implementada | VÁLIDA. LDAP no necesita disable: el leaver se deprovisiona (delete). |
| `unmatched → addFocus`, `unlinked → link`, `linked → synchronize` | implementada | VÁLIDA para liveSync inbound. |

**Brecha LDAP:** la condición actual usa solo `lifecycleState`. Con el modelo maduro debe alinearse a **afiliación viva** (`liveAffiliation*`), porque `lifecycleState=active` y "tiene afiliación viva" deben coincidir tras Bloque L del template — pero conviene endurecer la condición para que no dependa solo de la derivación de lifecycle (defensa en profundidad). Ver §2.5.

---

## 2. PASO 2 — Diseño de la política de provisioning canónica

### 2.1 Fundamento: afiliación viva como predicado de existencia (IIA por atributo)

Tras la migración del 2026-05-30 (Opción 2, schema sciback-person v1.2) existen tres items de **policy por IIA**, poblados por inbound `strong` single-source desde cada resource LAMB:

| Item (extension/sb:) | IIA | Semántica | Poblado por |
|---|---|---|---|
| `liveAffiliationWorker` | HR (LAMB Trabajadores, `ID_ENTIDAD=7124`, `ESTADO≠I`) | contrato UPeU vivo (staff/faculty) | `trabajadores.xml` → `archetype-to-liveAffiliationWorker` |
| `liveAffiliationStudent` | SIS (LAMB Estudiantes, semestre vigente) | matrícula vigente | `estudiantes.xml` → `school-name-to-liveAffiliationStudent` |
| `liveAffiliationAlum` | SIS (LAMB Egresados) | condición de egresado | `egresados.xml` → `afiliacion-to-liveAffiliationAlum` |

> `iga-canonical-standards` §1.3: cada atributo tiene **una IIA**. `liveAffiliation*` materializa la *reality* de cada dominio. `midpoint-best-practices` §2.1: assignments=policy, shadows=reality. Estos items son la base canónica para condicionar projections.

**Definición de elegibilidad por sistema:**

```
ELEGIBLE_KOHA   = liveAffiliationWorker != null   // contrato vivo (staff/faculty)
               OR liveAffiliationStudent != null   // matrícula vigente
               OR esVisita                          // hook Smart WiFi (§2.6)
               OR esBibliotecario                   // AR-Koha-Librarian (operacional)

ELEGIBLE_LDAP   = (liveAffiliationWorker != null OR liveAffiliationStudent != null)
               // alumni NO matriculado NO va a LDAP (no necesita SSO académico activo)
```

> `liveAffiliationAlum` **no** entra en `ELEGIBLE_KOHA` ni `ELEGIBLE_LDAP`: alumni puro (egresado sin contrato ni matrícula) = leaver para ambos. En Koha se archiva (categoría histórica preservada); en LDAP se deprovisiona. Esto materializa la política de scope del usuario.

### 2.2 Construcción condicional Koha — `<existence>` outbound (midpoint-best-practices §4.2, §7)

En lugar de condicionar cada `AR-Koha-*` por separado (frágil), se centraliza la existencia del account en el **objectType del resource** con un mapping `<existence>`. Patrón canónico (Semančík Cap. 7 — *Existence Mappings*):

```xml
<!-- koha-ils.xml → schemaHandling/objectType(account/default) -->
<activation>
  <existence>
    <outbound>
      <name>koha-account-existence-by-live-affiliation</name>
      <strength>strong</strength>
      <source><path>$focus/extension/sb:liveAffiliationWorker</path></source>
      <source><path>$focus/extension/sb:liveAffiliationStudent</path></source>
      <!-- hook visitas: extension/upeu:smartwifiGuest (single string, ver §2.6) -->
      <source><path>$focus/extension/upeu:smartwifiGuest</path></source>
      <expression>
        <script>
          <code>
            def worker  = liveAffiliationWorker
            def student = liveAffiliationStudent
            def guest   = smartwifiGuest
            def hasLib  = focus?.roleMembershipRef?.any { it?.oid == '<OID AR-Koha-Librarian>' }
            // existe el patrón Koha si hay CUALQUIER afiliación viva elegible
            return (worker != null) || (student != null) || (guest != null) || hasLib
          </code>
        </script>
      </expression>
    </outbound>
  </existence>
  <administrativeStatus>
    <outbound>
      <!-- Ver §2.4: NO delete cuando existence pasa a false; en su lugar disabled (=archivado Koha) -->
    </outbound>
  </administrativeStatus>
</activation>
```

**Comportamiento clave del existence mapping (Semančík Cap. 7):**
- `existence=true` → MidPoint crea/mantiene el patrón.
- `existence=false` → MidPoint **normalmente borraría** el shadow.

Para "archivar no borrar" hay que **interceptar** la transición a `existence=false`. Ver §2.4.

### 2.3 Mapeo `category_id` — decidir entre dos diseños (REQUIERE CONFIRMACIÓN)

Hay un conflicto activo entre lo desplegado y lo aprobado:

**Diseño A (desplegado hoy en resource, líneas 1064-1086):** `category_id` ∈ {DOCEN, ADMINIST, PREGRADO, POSGRADO, ALUMNI, INVESTI, JUBILADO, VISITA}. Mezcla ejes (lifecycle/nivel/función).

**Diseño B (`DECISION-eduperson-koha-categorycodes.md`, APROBADO no implementado):** `category_id = primaryAffiliation` literal eduPerson lowercase {faculty, staff, student, alum, affiliate, local}. Ejes ortogonales separados: nivel→`extended_attribute STUDY_LEVEL`, investigador→rol+`RESEARCHER=Y`, bibliotecario→`AREA=CRAI`.

**Recomendación midpoint-expert (alinear con Diseño B):**
- Es coherente con "schema is the law" y eduPerson 202208 (§3.2 `iga-canonical-standards`), y con la reusabilidad SciBack.
- Simplifica el mapping a `return primaryAffiliation` (elimina el bloque de 30 líneas con special-cases).
- Con el nuevo scope, **jubilado/alumni dejan de ser categorías** — pasan a ser *estado archivado* del patrón (disabled), independiente de su `category_id` histórica. Esto **elimina** la necesidad de `AR-Koha-Jubilado` con acceso perenne.
- **Pero** requiere crear las 6 categorías en Koha (`faculty/staff/student/alum/affiliate/local`) y migrar 13.805 patrones. Es un cambio mayor.

**Decisión pendiente del usuario:** ¿reactivamos con Diseño A (menor cambio, mantiene categorías ES) o aprovechamos para implementar Diseño B (canónico, ya aprobado)? El resto del runbook es válido para ambos; solo cambia el contenido del mapping `category_id` y el set de categorías Koha.

> Nota: bajo cualquiera de los dos, el **scope** (quién recibe patrón activo) lo gobierna el `<existence>` mapping de §2.2, NO el `category_id`. Los dos ejes son independientes.

### 2.4 Leaver Koha = ARCHIVAR (disabled), no borrar — diseño exacto

El requisito es: cuando un usuario pierde toda afiliación viva elegible (deja de ser worker/student/visita), el patrón Koha debe **quedar bloqueado y expirado pero presente** (transacciones preservadas para métricas).

**Mecanismo canónico:** NO usar el `<existence>` mapping para borrar. En su lugar:

1. **`<existence>` siempre true para patrones ya creados por MidPoint** (evita delete). Concretamente, el existence mapping retorna `true` si el shadow ya existe (reality) aunque la afiliación viva sea null — patrón "MidPoint suma, no resta":

```xml
<expression>
  <script>
    <code>
      def eligible = (liveAffiliationWorker != null) || (liveAffiliationStudent != null)
                  || (smartwifiGuest != null) || hasLib
      // si ya existe el shadow (reality), NUNCA borrar: archivar vía administrativeStatus
      def alreadyExists = (midpoint.getLinkedShadow(focus, '9b5a7c81-47aa-42ac-9a08-4de8b64935af', 'account', 'default', false) != null)
      return eligible || alreadyExists
    </code>
  </script>
</expression>
```

2. **`administrativeStatus` outbound gobierna el archivado.** Cuando deja de ser elegible → `disabled` → el conector aplica `patron_card_lost=true` + `expiry_date=ayer` (archivado, transacciones intactas):

```xml
<administrativeStatus>
  <outbound>
    <name>koha-admin-status-by-live-affiliation</name>
    <strength>strong</strength>
    <source><path>$focus/extension/sb:liveAffiliationWorker</path></source>
    <source><path>$focus/extension/sb:liveAffiliationStudent</path></source>
    <source><path>$focus/extension/upeu:smartwifiGuest</path></source>
    <expression>
      <script>
        <code>
          import com.evolveum.midpoint.xml.ns._public.common.common_3.ActivationStatusType
          def eligible = (liveAffiliationWorker != null) || (liveAffiliationStudent != null)
                      || (smartwifiGuest != null)
                      || focus?.roleMembershipRef?.any { it?.oid == '<OID AR-Koha-Librarian>' }
          return eligible ? ActivationStatusType.ENABLED : ActivationStatusType.DISABLED
        </code>
      </script>
    </expression>
  </outbound>
</administrativeStatus>
```

**Resultado:**
- Worker/student activo → patrón `enabled`, `expiry_date` futura.
- Leaver (jubilado, ex-trabajador, alumni no matriculado) → patrón **archivado** (`disabled` = `patron_card_lost=true` + `expiry_date=ayer`), **presente con todo su historial**. Métricas de circulación preservadas.
- **`AR-Koha-Jubilado` con acceso perenne queda OBSOLETO** bajo el nuevo scope (jubilado = leaver, se archiva). El override de activation jubilado→enabled del resource (líneas 1271-1294) debe **eliminarse**.

> `midpoint-best-practices` §6.6 ("MidPoint suma, no resta") + §4.2: `disabled` no borra reality. El conector traduce disabled a expiración Koha sin delete. Esto satisface "preservar transacciones para métricas" mejor que cualquier delete o anonimización.

### 2.5 LDAP — condición de activos + leaver = deprovisión (delete)

A diferencia de Koha, LDAP **sí** deprovisiona (delete shadow) al leaver: el Identity Cache solo debe contener identidades con SSO académico activo, y LDAP no tiene historial transaccional que preservar.

`AR-LDAP-Person` ya tiene la condición correcta en el inducement. **Endurecerla** para que dependa de afiliación viva (no solo de la derivación de lifecycle):

```xml
<!-- AR-LDAP-Person.xml → inducement/condition (reemplaza la actual) -->
<condition>
  <expression>
    <script>
      <code>
        // activo Y con afiliación viva worker o student (alumni puro NO va a LDAP)
        def ls = focus?.lifecycleState
        def live = (focus?.extension?.liveAffiliationWorker != null)
                || (focus?.extension?.liveAffiliationStudent != null)
        return (ls == 'active' || ls == null) &amp;&amp; live
      </code>
    </script>
  </expression>
</condition>
```

**Comportamiento:** afiliación viva worker/student → cuenta LDAP. Al perder afiliación viva → condición false → inducement inactivo → MidPoint **deprovisiona** (delete shadow LDAP) en el siguiente recompute. No requiere disable (capability activation ya removida).

### 2.6 Hook para Visitas (Smart WiFi) — dejar preparado

Las visitas se gobernarán desde el proyecto **Smart WiFi** (producto SciBack que regula visitas para universidades). El hook se deja preparado sin fuente activa todavía:

1. **Item de schema (overlay UPeU):** `extension/upeu:smartwifiGuest` (single string) — marca de visita activa con vigencia. Alternativa canónica: archetype `affiliate` + `validTo`. Recomendado: usar `liveAffiliation`-style item `upeu:smartwifiGuest` que Smart WiFi poblará vía resource inbound strong (mismo patrón IIA que worker/student).
2. **Categoría Koha:** `affiliate` (Diseño B) o `VISITA` (Diseño A). La construcción de patrón visita ya está contemplada en los `<source>` de §2.2 y §2.4 (`smartwifiGuest`).
3. **Estado del hook hoy:** el `<source>` de `smartwifiGuest` se incluye en los mappings pero, al no existir aún la fuente, siempre es null → no afecta el comportamiento actual. Cuando Smart WiFi entre (fase futura), poblará el item y los patrones visita se crearán automáticamente sin tocar Koha.
4. **Archivado de visita vencida:** misma mecánica §2.4 — cuando `smartwifiGuest` pase a null (visita expirada), el patrón se archiva (disabled), no se borra.

> Decisión pendiente: confirmar el nombre/forma del item (`upeu:smartwifiGuest` single vs reusar `liveAffiliation`-pattern). Se alineará con el diseño del producto Smart WiFi (skill `smartwifi-canonical-product`).

### 2.7 Confirmación de gobernanza

- **MidPoint conserva el ciclo de vida COMPLETO** de todas las identidades (active/suspended/archived). Ningún leaver se borra de MidPoint.
- **Koha** recibe el subconjunto {worker vivo, student matriculado, visita, bibliotecario} como patrones *activos*; los leavers quedan como patrones *archivados* (disabled, transacciones preservadas). Nada se borra en Koha por política IGA.
- **LDAP** recibe solo {worker vivo, student matriculado}; los leavers se deprovisionan (delete).
- **Reality preservada:** `unmatched` sin acción (Koha y LDAP) — MidPoint no inactiva/borra lo que no gobierna.

---

## 3. PASO 3 — Plan de reactivación por fases (con salvaguardas)

> Orden seguro `proposed → active` evitando provisioning descontrolado sobre 13.805 patrones Koha y 5.836 cuentas LDAP. Cada fase con dry-run (simulación MidPoint) antes de ejecución real.

### Pre-requisitos (gate)

- [ ] Focus MidPoint estable: dual-structural=0, lifecycle derivation cerrada (cola de retoma del runbook `org-canonical-migration-2026-05-29.md` completada — survivors recomputados, egresados→active correctos).
- [ ] Verificar valor efectivo de `lifecycleState` del resource/objectType Koha en PROD.
- [ ] Backup: tag git + `pg_dump` MidPoint + snapshot tabla `borrowers` de Koha (para verificación de no-pérdida de transacciones).
- [ ] Confirmar Diseño A vs B para `category_id` (§2.3).

### FASE 0 — Congelar y medir (read-only)

1. Suspender tasks de reconciliación Koha (`Reconcile-Koha-ILS-Daily`) y LDAP liveSync durante la reactivación.
2. Snapshot de métricas base:
   - Koha: `SELECT categorycode, count(*) FROM borrowers GROUP BY 1;` + `SELECT count(*) FROM old_issues;` (baseline transacciones).
   - MidPoint: shadows vivos Koha (13.805) y LDAP (5.836); usuarios por `liveAffiliation*`.
3. **Salvaguarda:** registrar el conteo de `old_issues`/`statistics` para verificar al final que NO disminuyó (prueba de no-borrado de transacciones).

### FASE 1 — Aplicar el nuevo modelo en MODO SIMULACIÓN (dry-run)

1. Aplicar (en repo→PROD) los mappings nuevos: `<existence>` + `administrativeStatus` Koha (§2.2, §2.4), condición LDAP endurecida (§2.5), eliminación del override jubilado→enabled, hook `smartwifiGuest`.
2. Mantener el objectType Koha en `proposed` (outbound NO se ejecuta — mismo patrón que Entra ID, MEMORY.md).
3. Ejecutar **recompute en modo simulación** (`executionMode=preview` / simulation task de MidPoint 4.10) sobre un scope canario (p.ej. 200 usuarios mezclando worker vivo, ex-trabajador, student matriculado, alumni puro, jubilado).
4. **Revisar el delta simulado:**
   - worker/student vivo → patrón enabled, category correcta.
   - ex-trabajador/jubilado/alumni puro → patrón **disabled** (NO delete).
   - 0 deltas de `deletePatron`.
   - LDAP: leavers → delete shadow; activos → sin cambio.

**Gate:** no avanzar si la simulación muestra cualquier `DELETE` de patrón Koha o un disabled sobre un worker/student vivo.

### FASE 2 — Reactivar LDAP (menor riesgo: 5.836 cuentas, deprovisión limpia)

1. Pasar LDAP objectType a `active` (si estaba proposed).
2. Recompute por lotes (worker threads 4) sobre activos primero.
3. Verificar: cuentas LDAP = usuarios con afiliación viva worker/student. Leavers deprovisionados.
4. Reactivar LDAP liveSync.

### FASE 3 — Reactivar Koha en oleadas (13.805 patrones)

1. Pasar Koha objectType `proposed → active`.
2. **Oleada 3a (activos):** recompute scope `liveAffiliationWorker != null OR liveAffiliationStudent != null`. Verifica creación/actualización de patrones enabled + category. Vigilar 409 (ya cubierto por correlación 3-capas + fallback JDBC del conector).
3. **Oleada 3b (leavers/archivado):** recompute scope leavers (alumni puro, jubilados, ex-trabajadores) → patrones a **disabled** (expiración + card_lost). **Verificar:** `old_issues` count sin cambios; patrones presentes con `expired=1`.
4. **Oleada 3c (reconciliación de los 13.805 shadows existentes — DISPUTED/UNLINKED/UNMATCHED legacy):**
   - `disputed` → `createCorrelationCase` (revisión manual; no auto-merge).
   - `unmatched` → sin acción (preserva patrones Koha sin user MidPoint; no borrar).
   - `unlinked` → `link` (vincula sin recrear).
   - Reconciliación completa por lotes; comparar contra baseline FASE 0.

### FASE 4 — Verificación y cierre

1. Métricas Koha post: `categorycode` distribution; `old_issues` ≥ baseline (prueba no-pérdida transaccional).
2. LDAP: cuentas = afiliación viva; sin huérfanos de leaver.
3. Reactivar `Reconcile-Koha-ILS-Daily`.
4. Spot-check: 1 jubilado (patrón presente disabled), 1 worker vivo (enabled), 1 student matriculado (enabled), 1 alumni puro (disabled, historial visible).
5. Documentar resultado y actualizar MEMORY.md.

### Salvaguardas transversales

| Riesgo | Salvaguarda |
|---|---|
| Borrado masivo de patrones con historial | `<existence>` retorna true si shadow ya existe (§2.4) + `unmatched` sin acción + **0 deletes esperados** verificado en simulación. |
| Disabled erróneo de un activo | Simulación FASE 1 con canario mixto; gate explícito. |
| Duplicados (409) | Correlación 3-capas + fallback JDBC por DNI del conector (ya probado). |
| Pérdida de transacciones para métricas | Baseline `old_issues` en FASE 0; verificación en FASE 4. Nunca `deletePatron` para leavers. |
| Provisioning descontrolado al reactivar | `proposed` mantiene outbound apagado; oleadas por scope; threads limitados. |
| Lifecycle derivation inestable | Gate de pre-requisitos (cola de retoma org-migration cerrada). |

---

## 4. Decisiones que requieren confirmación del usuario

1. **`category_id`: Diseño A (DOCEN/ADMINIST/...) o Diseño B (faculty/staff/... eduPerson, ya aprobado).** Recomendación: B (canónico, alineado a la decisión APROBADA), aceptando la migración de 13.805 patrones y creación de 6 categorías Koha.
2. **Eliminar `AR-Koha-Jubilado` (acceso perenne) y el override activation jubilado→enabled del resource.** Bajo el nuevo scope, jubilado = leaver → archivado. Confirmar.
3. **Hook visitas:** nombre/forma del item (`upeu:smartwifiGuest` single string vs patrón `liveAffiliation`). Se cerrará con el diseño Smart WiFi.
4. **Valor efectivo de lifecycleState del resource Koha en PROD** (repo dice `active`; el encargo asume `proposed`). Confirmar antes de FASE 1.
5. **¿Alumni puro fuera de LDAP confirmado?** El diseño excluye `liveAffiliationAlum` de `ELEGIBLE_LDAP`. Si en el futuro se quiere SSO para egresados (email alumni), se añade un item/condición específica.

---

## 5. Referencias

- `midpoint-best-practices` §1.2 (lifecycle states), §4.2 (conditions/strength), §4.5 (pipeline outbound), §6.6 (suma no resta), §7 (constructions, existence mappings, conditions on inducements).
- `iga-canonical-standards` §1.2 (ISO 24760 lifecycle), §1.3 (IIA por atributo), §3.2 (eduPerson affiliations), §10 (archetypes).
- `docs/DECISION-eduperson-koha-categorycodes.md` (Diseño B aprobado).
- `docs/runbooks/org-canonical-migration-2026-05-29.md` (estado focus / cola de retoma).
- `connector-koha` v1.3.x — `PatronMapper.applyEnableAttribute` (mecanismo archivado).
- Estado PROD verificado 2026-05-30: Koha 13.805 shadows, LDAP 5.836 shadows.

---

## 6. EJECUCIÓN — PASO 0/1/2 (dry-run) 2026-05-30 noche

> Ejecutado por `midpoint-expert`. Resources Koha+LDAP en `proposed` todo el tiempo.
> NINGÚN provisioning masivo real. NINGÚN resource pasó a `active`. Oracle solo lectura.

### PASO 0 — Consistencia config (OK)

- `koha-ils.xml`: único cambio sin commitear era `lifecycleState active→proposed` (válido, gate dry-run). Ya estaba aplicado en PROD. Commit `chore(koha+entraid)`.
- `entra-id-graph.xml`: la eliminación de outbounds (UPN/givenName/familyName + existence-outbound) NO es accidental — es **defensa en profundidad** inbound-only. Hallazgo previo (2026-05-28): en 4.10 `lifecycleState=proposed` NO suprime el `<existence><outbound>`, que forzaba ADD a Entra ID (ObjectAlreadyExistsException sobre ~29K shadows huérfanos). Se conserva (commiteado), NO se revierte. Entra ID en PROD: resource `active` + objectType `proposed` (inbound-only confirmado).
- Resource Koha en PROD: `proposed`, schema STUDY_LEVEL merged (sin Duplicate definition), **Test Connection 16/16 success**.
- LDAP en PROD: `proposed`. `AR-LDAP-Person` con condición endurecida.

### Dos bugs 4.10 detectados y corregidos vía simulación (preview)

1. **`AR-LDAP-Person` condición**: usaba `focus.extension.liveAffiliationWorker` → `MissingPropertyException` (ExtensionType no expone items como propiedades Groovy). Fix: `basic.getExtensionPropertyValue(focus, 'liveAffiliationWorker')`. Commit `fix(AR-LDAP-Person)`.
2. **`koha-ils.xml` existence mapping**: `getLinkedShadow(focus, oid, 'account','default', false)` → overload inexistente en 4.10. Fix: `getLinkedShadow(focus, resourceOid)`. Commit `fix(koha)`.

> Sin estos fixes, el existence/condición lanzaban excepción en cada recompute → habrían roto el provisioning masivo. La simulación los cazó ANTES de cualquier escritura.

### Mecanismo de dry-run

Simulation task `recomputation` con `<execution><mode>preview</mode><configurationToUse><predefined>development</predefined></configurationToUse>`. `preview` = NO escribe a MidPoint ni a resources; `development` = evalúa los objectTypes `proposed` (Koha+LDAP) como activos para predecir deltas. Deltas leídos de `m_simulation_result_processed_object` (Postgres, read-only). XMLs: `upeu/tasks/koha-ldap-reactivation/sim-canary-preview.xml`, `sim-leaver-preview.xml`.

### PASO 1 — Canary (todos PASAN, resultStatus=success, 0 errores)

| Caso | Usuario | liveAffiliation | Koha (preview) | LDAP (preview) |
|---|---|---|---|---|
| Staff activo (Zonia) | 01119359 | Worker=staff | MODIFY → enabled, category_id ADMINIST→**staff** | MODIFY (mantener) |
| Docente activo | 70477801 (julieta.rafael) | Worker=faculty | MODIFY → enabled, DOCEN→**faculty** | MODIFY (mantener) |
| Estudiante matriculado | 202110788 | Student | MODIFY → enabled, VISITA→**student** | **ADD** (crear cuenta LDAP eduPerson/SCHAC) |
| Jubilado (sin shadow Koha) | 00186917 (Chanducas) | — (archived) | sin acción (no patrón previo, no elegible) | sin acción |
| Alumni puro (sin shadow Koha) | 201220658 | Alum | sin acción (no patrón previo) | sin acción (alum NO va a LDAP) |
| **Leaver CON patrón Koha** | 60855245 (wilfredo.ramos) | — (archived) | **MODIFY → DISABLED** (disableReason=mapped, category→staff, **NO delete**) | UNMODIFIED* |
| Leaver YA archivado Koha | 43435688 | — (archived) | UNMODIFIED (ya `disabled` → idempotente) | — |

\* El shadow LDAP del leaver 60855245 quedó UNMODIFIED porque el user archived **no tiene assignments/roleMembership** (perdió AR-LDAP-Person). MidPoint no resta lo que no gobierna por recompute. **La limpieza de cuentas LDAP huérfanas de leavers requiere RECONCILIACIÓN del resource LDAP (no recompute del user).** Documentado para la fase LDAP.

**Validado:** Diseño B (category eduPerson) se aplica; archivar-no-borra es idempotente y NO genera deletes; estudiante crea cuenta LDAP completa; alumni puro fuera de LDAP.

### PASO 2 — DRY-RUN agregado (conteos proyectados, 49.322 usuarios)

Calculado por elegibilidad en MidPoint DB (read-only), sin escritura:

| KOHA | Conteo |
|---|---|
| Elegibles (worker/student vivo) → enabled | 14.202 |
| → SIN patrón → **CREAR** enabled | 9.124 |
| → CON patrón → update enabled | 5.078 |
| Leavers CON patrón → **ARCHIVAR (disabled)** | 4.899 |
| No-elegibles SIN patrón → sin acción | 30.220 |
| **DELETE** | **0** ✓ |

| LDAP | Conteo |
|---|---|
| Elegibles → crear/mantener | 14.199 |
| → SIN cuenta → **CREAR** | 9.475 |
| Leavers CON cuenta → **DEPROVISIONAR** (delete) | 64 |

**Baseline Koha (read-only, a preservar):** `old_issues=21.562`, `issues=199`, `borrowers=30.434`, `statistics=68.995`. Categorías actuales: ESTUDI 17.672, ALUMNI 6.008, ADMINIST 2.641, VISITA 1.753, PREGRADO 1.538, DOCEN 590, INVESTI 127, POSGRADO 91, JUBILADO 7. Categorías eduPerson Diseño B (faculty/staff/student/alum/affiliate/local) YA creadas en Koha.

### GATE — veredicto: NO listo para provisioning masivo todavía

- ✅ **0 deletes Koha**, ✅ 0 disabled sobre vivos (los 14.202 elegibles → enabled).
- ✅ Archivado idempotente (leavers ya disabled = UNMODIFIED).
- ⚠️ **BLOQUEANTE: liveAffiliation aún no propagado a toda la población.** Solo 14.202 usuarios tienen `liveAffiliationWorker/Student` poblado (vs 30.434 borrowers Koha). De los 4.899 leavers-a-archivar: **4.794 son alumni puros legítimos**, pero **~66 son staff/faculty/student con afiliación viva real cuyo inbound `strong` de liveAffiliation aún NO corrió** (recompute Opción 2 pendiente). Archivarlos ahora sería un **falso leaver**.
- ⚠️ Bug preexistente (NO de este trabajo): mapping `D-assign-affiliation-role-from-primaryAffiliation` del object-template lanza Groovy error (`ExtensionType.findProperty/getPropertyRealValue` no existe en 4.10) en cada recompute. No bloquea Koha/LDAP pero el assignment de roles de afiliación puede estar fallando. **Requiere fix del template (mismo patrón: usar `basic.getExtensionPropertyValue`).**

**Pre-requisito obligatorio antes del masivo:** completar el recompute masivo de `liveAffiliation*` (cola de retoma `org-canonical-migration-2026-05-29.md`) para que worker/student vivos tengan el item poblado → los ~66 falsos leavers desaparecen. Recomendado además: corregir el bug del template `D-assign-affiliation-role`.


---

## SESIÓN DIAGNÓSTICA 2026-05-30 PM (materialización liveAffiliation — PRE-REQUISITO)

Objetivo: ejecutar el pre-requisito (fix #52 + materializar `liveAffiliation*` + re-dry-run). Resultado: **diagnóstico que corrige varias premisas + gate sigue ROJO (348 falsos leavers reales)**.

### PASO 1 — Fix template #52: NO ERA EL BUG REAL
- El mapping `D-assign-affiliation-role-from-primaryAffiliation` **NO usa** `getPropertyRealValue`/`findProperty` roto. Usa `assignmentTargetSearch` + `basic.stringify` (correcto 4.10). Repo y PROD idénticos. Sin cambios necesarios.
- **El bug Groovy real** estaba en `koha-ils.xml` → `getLinkedShadow(focus, oid, String, String, boolean)` (firma 5-arg inexistente en 4.10). YA corregido a 2-arg en commit `0567a25` (repo + objeto PROD).
- Los 65–90 `getLinkedShadow` MissingMethodException de las 20:40 venían de **caché Groovy stale** durante el dry-run anterior. **Restart de `midpoint_server` (2026-05-30 ~22:00) flusheó la caché → 0 errores getLinkedShadow desde entonces.** Verificado.
- Auditoría repo completa: 0 `getPropertyRealValue`; los `findProperty` restantes son sobre `PrismContainerValue` (válido 4.10), no la API rota.

### PASO 2 — Mecanismo de materialización: RECONCILIACIÓN, no recompute
**Hallazgo canónico (best-practices §4.5):** `liveAffiliationWorker/Student/Alum` los pobla el **inbound `strong`** de los resources LAMB (trabajadores/estudiantes/egresados), que **solo se replay en reconciliación/import del shadow**, NO en recompute de focus.
- `PATCH /users/{oid}?options=reconcile` **NO replica inbounds**: re-deriva lifecycle desde los items ya presentes (vacíos) → **archiva al usuario** (demostrado con student 202612279). Mecanismo EQUIVOCADO para materializar.
- `/users/{oid}/recompute` → HTTP 404 en 4.10 (endpoint inexistente).
- Mecanismo correcto = **reconciliación del resource** (replay inbound). Validado con canary scoped por `attributes/icfs:name` sobre Trabajadores (shadow `fullSyncTimestamp` actualizado, 0 error).

### Estado real de materialización (baseline, m_user.ext JSONB)
| Item | Materializado |
|---|---|
| liveAffiliationWorker (216) | 3.729 |
| liveAffiliationStudent (217) | 10.936 |
| liveAffiliationAlum (215) | 30.650 |
| **liveAny** | **41.954 / 49.322** |

- active=41.202, archived=7.323, draft=698, null=99.
- **active sin liveAny = 37** (no 66): 25 alum SIN shadow egresado vivo (0/25 en Oracle egresados → leavers/data-gap, no falsos), 1 staff + 9 student con IIA viva (gap real).

### Salvaguarda académica — VERIFICADA (BLOQUEANTE, intacta)
- **3 archived con liveAffiliationWorker=staff** (`75758850`,`04680920`,`41070902`): Oracle `VW_APS_EMPLEADO ID_ENTIDAD=7124` confirma **contrato UPeU vivo** → eran **falsos leavers** (archivados por error en saneo previo). Corregidos: lifecycleState `archived→proposed` (un-freeze). Quedan `proposed` (no `active`) porque **Bloque L exige `personalNumber && primaryDoc` para `active`**; sin DNI doc materializado → `draft/proposed`. Esto es **correcto canónicamente** (perfil incompleto), NO falso leaver para Koha/LDAP (proposed = sin provisioning).
- Estudiantes archivados probados (`202612279`,`202220532`): Oracle confirma **NO matriculados en sem 279/267** → **true leavers**, `archived` correcto. 0 académicos vivos archivados.
- **dual-structural archetype = 0** (verificado por OIDs structural de los 9 user-archetypes).

### PASO 3 — Re-dry-run (proyección desde estado materializado actual)
| Métrica | Valor |
|---|---|
| Koha eligible (liveWorker∨liveStudent) | 14.202 |
| Alum puro a archivar Koha (archived-not-deleted) | 27.752 |
| Shadows Koha existentes no-elegibles (a deshabilitar) | 4.899 |
| **FALSOS leavers reales (no-elegible PERO con shadow IIA VIVO)** | **348** |
| — de ellos con trabajador vivo | 348 |
| — con estudiante vivo | 0 |
| Koha DELETE | 0 (suma-no-resta: disabled vía card_lost+expiry) |

**GATE: ROJO.** 348 falsos leavers (todos worker vivo) — más que el "~66" estimado antes (aquel era pre-recon). Provisionar Koha ahora deshabilitaría 348 trabajadores con contrato UPeU vigente.

**PRE-REQUISITO restante (acotado y resoluble):** una **reconciliación completa del resource Trabajadores** (`6a91f7e1-...e21`, 16.327 shadows, 7.492 LINKED) replica el inbound `strong` → materializa `liveAffiliationWorker` en los 348 → desaparecen como falsos leavers. (Estudiantes/Egresados ya suficientemente materializados para el gate Koha; recon completo recomendable para consistencia pero no bloquea los 348.)

**Mecánica de scheduling (memoria):** tasks REST quedan SUSPENDED en Quartz in-memory. Para ejecutar recon masiva: `UPDATE m_task SET executionstate='RUNNABLE',schedulingstate='READY'` + `docker restart midpoint_server` (Quartz recarga RUNNABLE → dispara). Guardas durante el masivo: dual-structural=0, 0 académicos-vivos archivados, disco<90%.

### Backup
`/home/juansanchez/bkp_pre_materializa_lean_20260530_2152.dump` (2.7G, pre-materialización). Dump completo previo abortado por bloat de `ma_audit_delta_default` (8.3 GB) que amenazaba el disco; lean dump validado con `pg_restore -l`.

### Recomendación
**NO listo para provisioning masivo.** Falta UNA acción acotada: recon completa de Trabajadores para materializar los 348. Tras ella, re-correr esta proyección → gate debe dar **0 falsos leavers**, solo ~4.551 alumni/leavers legítimos a archivar (disabled, 0 delete). Recién entonces decidir (usuario) pasar Koha/LDAP a `active`.

---

## EJECUCIÓN 2026-05-30 PM (materialización liveWorker — destrabe falsos leavers)

**Objetivo:** materializar `sb:liveAffiliationWorker` en los 348 trabajadores con contrato 7124 vivo que aparecían como falsos leavers en el re-dry-run Koha+LDAP. Mecanismo: inbound `strong` single-source `archetype-to-liveAffiliationWorker` solo se replay en RECON.

**Backup previo:** `/home/juansanchez/bkp_pre_materializa_lean_20260530_2152.dump` (provisto).

### Baseline pre-recon (verificado en DB PROD)
- users_total: 49.322
- liveAffWorker materializado: **3.729**
- liveAffStudent: 10.936 · liveAffAlum: 30.650
- dual-structural canónico (USER, archetype-user-*): **0**
- académicos vivos (217/215) archivados: **0**
- disco /: 86%

### PASO 1 — Recon Trabajadores v3 (LANZADA)
- Tarea conservada `e8d054ba-fd9a-4f8d-b04c-347359e49054` ("Recon Oracle LAMB Trabajadores 2026-05-28").
- Verificado: `<activity><work><reconciliation>` acotada SOLO a resource Trabajadores `6a91f7e1-...` (account/default). NO toca Koha/LDAP. Los resourceRef Koha/LDAP vistos en raw eran de operationStats, no del work.
- Otras recons (Estudiantes, Org) permanecen SUSPENDED.
- Scheduling: UPDATE m_task RUNNABLE/READY → restart midpoint_server → trigger no se creó (qrtz=0) → `POST /tasks/{oid}/resume` (HTTP 202) → **RUNNING/READY**, lastrunstart nuevo.
- Monitor background con guardas BLOQUEANTES: dual>0, académico-vivo-archivado>0, disco>=90% → suspende tarea y aborta. Log: `/tmp/recon_trabajadores_monitor.log`.

### Salvaguardas (BLOQUEANTES, en monitoreo continuo)
1. dual-structural = 0
2. 0 académicos con afiliación viva archivados
3. disco < 90%
4. m_user sin pérdida (49.322 baseline)

EN CURSO — esperando fin de recon para verificar liveAffWorker (objetivo >= 4.077, cubrir los 348).
