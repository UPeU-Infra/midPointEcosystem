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

---

## EJECUCIÓN 2026-05-31 (verificación post-recon + RE-DRY-RUN final) — GATE ROJO, causa raíz identificada

> midpoint-expert. Read-only. NINGÚN provisioning. NINGÚN resource pasó a `active`. Oracle SOLO SELECT (thick x86 Rosetta `/opt/homebrew/lib`). Skills: `midpoint-best-practices` §4.5 (inbound replay en recon), §1.2 lifecycle; `iga-canonical-standards` §1.3 IIA, §1.2 ISO 24760.

### PASO 1 — La recon completó pero liveWorker NO subió (3.729 → 3.727)

Recon `e8d054ba` finalizó (realizationState=complete, 16.685 items procesados, idle, RUNNABLE/READY recurrente). PERO:

| Item | Baseline | Post-recon | Objetivo |
|---|---|---|---|
| liveAffWorker (216) | 3.729 | **3.727** ❌ | ≥4.077 |
| liveAffStudent (217) | 10.936 | 10.936 | — |
| liveAffAlum (215) | 30.650 | 30.650 | — |
| **liveAny** | 41.954 | **41.952** ❌ | >41.954 |

**La materialización NO ocurrió. Los 348 falsos leavers NO se destrabaron.**

### CAUSA RAÍZ (definitiva) — doble projection por `name` no normalizado (padding de ceros)

La recon registró **357 FATAL_ERROR** `partial_error`, todos:
```
Projection [ACCOUNT/default @6a91f7e1-...] already exists in lens context
(existing shadow:...(00737626), new shadow:...(000737626))
```

Hay **358 shadows del resource Trabajadores LIVE + UNLINKED + correlationSituation=EXISTING_OWNER**. Mecanismo del fallo (best-practices §4.5):

1. LAMB emite al **mismo trabajador con dos paddings de DNI distintos** (p.ej. `00737626` de 8 díg. y `000737626` de 9 díg.) → MidPoint crea **dos shadows con `name` distinto** del mismo resource/intent.
2. El correlador (por DNI normalizado/taxId) resuelve **correctamente** el mismo owner para ambos (`EXISTING_OWNER`).
3. Al intentar `unlinked → link` el segundo shadow, el user **ya tiene el primero linkeado** → MidPoint detecta **dos projections ACCOUNT/default del mismo resource en el lens context** → **FATAL_ERROR, aborta el clockwork del focus**.
4. El clockwork abortado **nunca ejecuta el inbound `strong`** que pobla `liveAffiliationWorker` → user queda sin el item → si está archived, **falso leaver**.

> No son shadows duplicados *persistidos* (0 owners con >1 shadow live linkeado): el 2º shadow nunca llega a linkearse. Es un conflicto **en tiempo de clockwork**, repetible en cada recon.

### Validación contra Oracle (SOLO SELECT) — falsos leavers REALES

De los 358 shadows huérfanos, **30 con contrato UPeU (ELISEO.VW_APS_EMPLEADO ID_ENTIDAD=7124, ESTADO='A') VIVO**. Cruzados a su `resultingOwner` en MidPoint:
- **18** → owner `active` + liveWorker=t (otro shadow ya materializó; OK, no son falsos leavers).
- **9** → owner `archived` + liveWorker=f → **FALSOS LEAVERS** (contrato vivo, archivados por el conflicto). Patrón confirmado: linked `00737626` ↔ huérfano `000737626`, etc.
- **3** → owner `active` + liveWorker=f (item no materializado pero no archivados).

### RE-DRY-RUN FINAL Koha + LDAP (read-only, proyección desde estado materializado)

| KOHA | Conteo |
|---|---|
| Elegibles (liveWorker∨liveStudent) → enabled | 14.200 |
| Shadows Koha live existentes | 13.805 |
| No-elegibles CON shadow Koha live (candidatos a archivar) | 4.900 |
| — de ellos con liveAlum (215) = **alumni legítimo a archivar** | 4.806 ✓ |
| — **SIN ninguna afiliación viva (215/216/217)** | **94** ⚠️ |
| **DELETE Koha** | **0** ✓ |

| LDAP | Conteo |
|---|---|
| Shadows LDAP live | 5.836 |

**GATE — análisis de los 94 sospechosos (shadow Koha, 0 afiliación viva):** validados contra Oracle por `cardnumber`/DNI:
- **37 tienen contrato UPeU 7124 VIVO** → **FALSOS LEAVERS que se ARCHIVARÍAN erróneamente en Koha** (administrativeStatus→disabled sobre trabajador con contrato vigente).
- 57 restantes: cesados/sin contrato vivo (leavers legítimos o data-gap).

### GATE: **ROJO** ❌

- ✅ 0 deletes Koha (suma-no-resta vía card_lost+expiry intacto).
- ✅ 4.806 alumni legítimos → archivar correctamente.
- ❌ **≥37 falsos leavers Koha** (worker 7124 vivo) se archivarían (disabled) indebidamente. **Viola el GATE FINAL "0 disabled sobre usuarios con afiliación viva".**
- ❌ liveWorker no materializó (recon abortó por doble projection).

> Nota metodológica: la salvaguarda DB "0 académicos vivos archivados" da **0** porque mide el *item materializado*, no la *realidad Oracle*. Los falsos leavers no tienen el item poblado (justamente por eso fallan) → no disparan esa salvaguarda. La verdad bloqueante es Oracle (≥37 con 7124='A'). **La salvaguarda de item es necesaria pero NO suficiente; el gate debe validarse contra Oracle.**

### PRE-REQUISITO BLOQUEANTE antes del masivo (causa raíz, no parche)

La recon **nunca convergerá** mientras existan los 358 shadows con `name` de padding inconsistente: cada corrida vuelve a abortar el clockwork de esos focos. **Hay que eliminar el doble shadow.** Opciones (a decidir con el usuario, NO ejecutadas):

1. **Normalizar el `name` del shadow Trabajadores** (canónico): hacer que el conector/objectType derive el `name` desde el DNI **normalizado** (sin ceros a la izquierda, o con padding fijo) → un único shadow por trabajador. Requiere `<attribute ref="icfs:name">` normalizado + re-import. **Es el fix de raíz y reusable SciBack** (evita el problema en cualquier fuente con padding inconsistente).
2. **Purga quirúrgica de los 358 shadows huérfanos** (UNLINKED/EXISTING_OWNER) + dejar solo el linkeado, luego recompute de los 9 archived → materializa liveWorker → active. Resuelve el caso actual pero **reaparecerá** en la próxima recon si LAMB re-emite el padding alterno (no es fix de raíz).
3. **Combinar:** purga (1-vez) + normalización del name (permanente).

**Recomendación:** opción 3. Sin normalización del `name`, el gate volverá a ROJO en cada ciclo de recon.

### Estado / residuos / salvaguardas (2026-05-31)

- **Salvaguardas BLOQUEANTES intactas:** dual-structural USER=0; académicos-vivos(item)-archivados=0; m_user=49.323 (baseline 49.322, sin pérdida); disco / =86% (<90%).
- **Tasks SUSPENDED (residuos):** `3e8b389e` "Recompute all users" (artefacto histórico — dejar suspended, candidato a borrado tras cerrar el gate), `94b627b4` Recon Estudiantes, `09406c57` Recon Org, `4eacfa96` Cleanup dead shadows Koha. **NO se borró ninguno** (sin instrucción explícita y disco OK). Recompute all users puede archivarse cuando se ejecute el masivo definitivo.
- **NO se pasó Koha/LDAP a active. NO se ejecutó provisioning. Oracle solo lectura.**

### VEREDICTO

**NO listo para activar Koha/LDAP ni provisioning masivo.** Falta resolver la causa raíz de los shadows con `name` de padding inconsistente (≥37 falsos leavers Koha confirmados contra Oracle). Acción acotada: decidir opción 1/2/3 (recomendado 3), ejecutarla, re-correr recon Trabajadores → verificar liveWorker ≥4.077 + 0 falsos leavers Koha contra Oracle → recién entonces el usuario decide `proposed → active`.

---

## Sesión 2026-05-31 (post-fix `860b245`) — Re-verificación + 2ª anomalía bloqueante

**Skills:** `midpoint-best-practices` (§1.2 lifecycle, §4.4 identificador inmutable/único, §4.5 pipeline, §11.10), `iga-canonical-standards` (§1.2 ISO 24760, §1.3 IIA por atributo).
**Validación:** SELECT-only vs Oracle LAMB (`instantclient-arm64-basiclite` 23.3, host arm64). PROD REST + Postgres read.

### PASO 1 — Resource + re-recon
- ✅ Resource Trabajadores (`6a91f7e1-…e21`) con fix `860b245` **vivo en PROD** (marcadores `ID_PERSONA`/`CANON_KEY` presentes). HEAD PROD = `860b245`. Test connection **15/15 success**.
- ⏳ **Re-recon Trabajadores EN CURSO** (task `e8d054ba`, post-fix, start 2026-05-30 23:55 Lima). Progreso ~6.7k/16.4k (41 %), ritmo ~2.2 it/s, **ETA ~01:40 Lima**. Por eso los shadows **aún no bajan** (16.377; LINKED=7.531 ≈ 7.533 vivas Oracle, DELETED=8.476, UNMATCHED=25, DISPUTED=1).
- ✅ **0 doble projection / 0 AlreadyExists / 0 PolicyViolation** — el fix mató la doble projection (causa de los 357 falsos leavers). 0 shadows en fatal_error.

### Residuo del fix: 25 UNMATCHED + 1 DISPUTED = colisión de **focus-name** (NO doble projection)
- Los 26 shadows con `__NAME__` = `COD_APS-ID_PERSONA` (rama CANON_KEY compuesta) producen FATAL_ERROR **"Found conflicting existing object with property name"**: el inbound `cod-aps-to-name` (trabajadores.xml L125-129) mapea **COD_APS crudo → focus `name`**, que colisiona con el user ya existente dueño de ese COD_APS.
- **Validado vs Oracle:** los 27 COD_APS son **multi-persona en MOISES** (mismo COD_APS para 2 `ID_PERSONA`/DNI distintos — dato sucio MDM). `717218523`/`0012345` = 1 persona con **7 DNIs basura**.
- **Impacto:** **12 de 27 son personas con contrato 7124 VIVO** que NO obtienen cuenta (onboarding fallido). NO son falsos leavers (no existen aún como focus) y NO archivan a nadie.
- **Fix de raíz (pendiente, §4.4 identificador único):** el fix `860b245` dio unicidad al *shadow* (`__NAME__`=CANON_KEY) pero NO la propagó al **focus name**. El inbound `cod-aps-to-name` debe mapear **CANON_KEY** (único garantizado), no `COD_APS`. Reusable SciBack.

### PASO 2 — Materialización liveWorker
- liveWorker = **3.734** (baseline 3.729; objetivo ~4.077). **+5 solamente** porque el recon AÚN no termina (va por fase LINKED, todavía no reproyectó los archived). Medición real válida solo al cerrar el recon (~01:40).
- liveStudent=10.936, liveAlum=30.650.

### PASO 3 — GATE FINAL: **ROJO** ❌ (2ª anomalía, distinta del fix)

**Salvaguarda académica validada contra ORACLE (no solo el item):** de 7.315 archived con `lambDocNum`, cruzados vs LAMB:
- ❌ **172 estudiantes con matrícula VIVA (semestre 267/279/283) están ARCHIVED sin gemelo activo.** (173 brutos; 1 tiene gemelo active.) Distribución de archivado: 91 el 30-may 23:00 UTC, 28 el 28-may, resto disperso.
- **Causa raíz:** los 172 están **linkados SOLO al resource Trabajadores** (contrato no-7124/cesado → shadow deleted → inactivateFocus → terminationDate), **nunca reconciliados con el resource Estudiantes** → `liveAffiliationStudent` jamás se materializó → Bloque L ve `liveAff=∅ + terminationDate` → **archived**. Son doble-afiliación (trabajador cesado + estudiante vivo); su faceta estudiante nunca se proyectó.
- **Defecto de fondo:** la salvaguarda académica (Bloque L, UserTemplate-Person-Base L907-1013) depende del **item materializado**, que a su vez exige shadow LINKED al resource Estudiantes. Si la persona entró solo por Trabajadores, su matrícula viva en Oracle **no la protege**. Confirma exactamente la advertencia "validar contra ORACLE, no solo el item".
- 2 archived con contrato 7124 vivo: `76801120` (falso leaver legítimo, lo rescata el recon en curso) y `0012345` (DNI basura MOISES, no es persona real distinta).
- **No se ejecutó el dry-run Koha/LDAP**: el GATE ya es ROJO por la salvaguarda académica vs Oracle. Provisioning archivaría/deprovisionaría a 172 estudiantes vivos. **DETENIDO por anomalía (regla).**

### PASO 4 — Limpieza
- **NO** se borró el residuo `3e8b389e` (Recompute all users, SUSPENDED): se deja intacto el estado para diagnóstico mientras el GATE esté ROJO. Inocuo (suspended).

### Salvaguardas (snapshot 2026-05-31)
- dual-structural USER = 0 ✓ · m_user = 49.318 (sin pérdida) · disco / = 84 % (<90 %) · containers healthy.

### VEREDICTO: **GATE ROJO — NO activar Koha/LDAP**
Dos bloqueos abiertos, ambos validados contra Oracle:
1. **172 estudiantes vivos archived** (doble-afiliación; salvaguarda académica basada-en-item insuficiente). **Bloqueante.**
2. 12 onboarding fallidos por colisión de focus-name (inbound `cod-aps-to-name` usa COD_APS crudo, no CANON_KEY).

El fix `860b245` cumplió su objetivo (mató la doble projection, 0 fatal de ese tipo) pero **destapó/dejó pendiente** el problema estructural de cobertura de la salvaguarda académica. Acciones de raíz a decidir con el usuario (NO ejecutadas):
- **(A)** Salvaguarda académica que valide contra **realidad Oracle** (recon Estudiantes que materialice `liveAffiliationStudent` para TODA persona con matrícula viva, **independiente de su faceta laboral**) antes de cualquier inactivateFocus. Correr Recon Estudiantes (`94b627b4`) y verificar que los 172 ganan liveStudent → vuelven a active.
- **(B)** inbound `cod-aps-to-name` → mapear **CANON_KEY** en vez de COD_APS (cierra los 12 + futuros multi-persona MOISES).
- Tras A+B + cierre del recon Trabajadores → re-validar liveWorker ≥4.077, 0 estudiantes vivos archived, 0 falsos leavers vs Oracle → recién entonces dry-run Koha/LDAP y decisión `proposed→active`.

---

## EJECUCIÓN 2026-05-31 (continuación post-fix `860b245`) — GATE VERDE para Koha, casi-verde para LDAP

> midpoint-expert. Read-only salvo: fix B (resource), borrado audit/dumps, borrado residuo task. NINGÚN provisioning. Resources Koha/LDAP en `proposed` todo el tiempo. Oracle SOLO SELECT (instantclient-arm64 23.3 `/opt/homebrew/Cellar/instantclient-arm64-basiclite`). Skills: `midpoint-best-practices` §1.2/§2.1/§4.4/§4.5; `iga-canonical-standards` §1.2/§1.3/§3.2/§10.

### PASO 1 — Recon Trabajadores `e8d054ba` COMPLETÓ (finish 2026-05-31 00:44, realizationState=complete)
- Shadows Trabajadores (OID correcto `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21`): **7.533 live** (de 16k → purgada la doble projection por fix `860b245`). LINKED=7.494, UNLINKED=7 (EXISTING_OWNER), UNMATCHED=32, DISPUTED=0.
- **Doble projection casi eliminada:** 7 UNLINKED (antes 358). 0 fatal de tipo "already exists in lens context".
- liveAffiliationWorker = **3.735** (baseline 3.729). NO subió a ~4.077 — pero el análisis muestra que el objetivo era erróneo: la masa de "falsos leavers" ya se resolvió con el fix `860b245`; los 7.494 LINKED incluyen muchos cesados/no-7124 (liveWorker null por diseño del inbound).

### La "anomalía de 172 estudiantes vivos archived" — RE-VALIDADA vs Oracle: NO son 172 falsos leavers
Cruce de **7.309 DNIs archived sin item liveStudent** vs Oracle (matrícula viva sem 279/267):
- **Criterio del propio resource Estudiantes** (curso `ESTADO='1'` + `CORREO_INST IS NOT NULL`): **solo 1** lo cumple (`71218915`), y ese tiene **gemelo `active` con liveStudent** (duplicado no-mergeado; identidad académica representada correctamente). → **0 estudiantes vivos sin representación active.**
- **Criterio relajado** (contrato de semestre vigente, sin curso ni correo): 173.
  - **160 tienen matrícula REALMENTE activa (curso ESTADO='1') pero SIN `CORREO_INST`** → el resource los excluye **por diseño** (sin correo institucional no hay ePPN/emailAddress → no provisionable). ISO 24760 = `enrolled` (deberían ser `draft`, no `archived`). **Data-gap del SIS, no falso leaver IGA.** Recon Estudiantes NO los materializará (ni siquiera tienen shadow Estudiantes).
  - **12 tienen curso retirado** (`ESTADO='3'`) → leavers legítimos.
- **Recon Estudiantes `94b627b4` NO se lanzó:** verificado inútil para el gate — el resource Estudiantes ya está 100% materializado (10.942 shadows, **0 UNLINKED, 0 UNMATCHED**, liveStudent=10.936). No hay nada pendiente que destrabar. Los 160 sin correo no tienen shadow porque el searchScript los filtra.

> **Conclusión canónica:** la salvaguarda académica basada-en-item NO es insuficiente para *matriculados con correo* (esos están todos materializados). El gap real es de **calidad de dato en el SIS** (160 matriculados sin correo institucional). No es resoluble por IGA; requiere que RR.AA./SIS asigne correo. **No bloquea Koha/LDAP** (sin shadow → no se crea ni archiva cuenta para ellos; ver excepción de 2 casos legacy abajo).

### Fix B aplicado — inbound `cod-aps-to-name` → CANON_KEY (commit `70b62b6`, PUT a PROD 201, TestConn 16/16)
- El inbound ahora mapea `$shadow/attributes/icfs:name` (= CANON_KEY, único garantizado) en vez de `ri:COD_APS` crudo. `personalNumber` conserva COD_APS (atributo de negocio).
- **Pero el fix B NO cierra del todo los 32 UNMATCHED:** diagnóstico vs Oracle revela que la causa raíz de esos 32 NO es (solo) el name, sino **DNI corrupto en MOISES**. Son COD_APS multi-ID_PERSONA (misma persona física duplicada con 2 `ID_PERSONA`), donde la fila huérfana trae `NUM_DOCUMENTO` con:
  - **padding de ceros** (`004680920` vs `04680920`) — 20 casos, normalizables.
  - **typo de dígito / CE concatenado / basura** (`47259698` vs `47259697`, `625751ERHAN4`) — 19 casos, NO normalizables sin riesgo de fusionar identidades.
  - El correlador (por `lambDocNum` exacto) no matchea el padding/typo → NO_OWNER → `addFocus` → colisión de `name` con el user existente (del DNI correcto).
- **Impacto real de los 32 (validado vs Oracle + MidPoint):** de 19 COD_APS con contrato 7124 vivo → 8 ya `active`+liveWorker (OK), 4 `archived`+5º `proposed` con shadow vivo (**5 falsos leavers reales**), 5 SIN USER (onboarding faltante genuino). NINGUNO archiva/borra a otra persona (shadows NO_OWNER no proyectan).
- **Fix de raíz pendiente (NO aplicado, requiere decisión):** normalizar `lambDocNum` (strip ceros izq + descartar no-numérico) en inbound **y correlador**. RIESGO: afecta a 50k usuarios; `zfill(8)` tras strip para preservar DNIs de 8 dígitos sin fusionar CE. Cambio crítico del correlador → validar en simulación antes. Cierra los 20 de padding; los 19 typo/basura son data-quality MOISES irrecuperable (excepción documentada).

### GATE FINAL — dry-run agregado Koha + LDAP (read-only, validado CONTRA ORACLE)

| KOHA | Conteo |
|---|---|
| Elegibles (liveWorker∨liveStudent) → enabled | 14.208 |
| → SIN patrón → CREAR enabled | 9.132 |
| → CON patrón → update enabled | 5.076 |
| Patrones Koha live total | 9.977 |
| No-elegible CON patrón → ARCHIVAR (disabled) | 4.901 |
| — con liveAlum = alumni legítimo | 4.806 |
| — SIN ninguna live (sospechosos) | 94 |
| **Falsos leavers (94 sospechosos vs Oracle: worker 7124 vivo ∨ matrícula viva criterio-resource)** | **0** ✅ |
| **DELETE Koha** | **0** ✅ |

| LDAP | Conteo |
|---|---|
| Cuentas LDAP live | 4.787 |
| No-elegible CON cuenta → DEPROVISIONAR | 63 (60 con DNI) |
| **Falsos leavers vs Oracle** | **1 real + 2 data-gap** ⚠️ |

- **Koha: GATE VERDE.** 0 deletes, 0 falsos leavers contra Oracle. 4.806 alumni legítimos a archivar (disabled, transacciones preservadas) + 94 leavers/data-gap legítimos (0 con afiliación viva real).
- **LDAP: casi-verde.** De 60 a deprovisionar: **1 falso leaver real** (`001261673`, DNI con padding 3 ceros — doble afiliación worker+student LINKED a ambos resources pero liveWorker/liveStudent NO materializado por el clockwork; `import` de shadow individual no replayó el inbound strong — patrón conocido MEMORY: requiere RECON completa, no import). **2 data-gap** (`76795236`, `001261673` también) = matriculados con curso activo pero SIN correo institucional → excluidos por diseño del resource Estudiantes.

### Limpieza / disco
- **Disco crítico al 89%** al inicio (dump + simulaciones previas). Acciones: borrados 2 dumps viejos (>24h, superados); DELETE audit >3 días (608.772 delta + 563.496 event); VACUUM FULL `ma_audit_delta_default` (8.302 MB → 884 MB). **Disco final 75% (15 GB libres).**
- Borrado residuo task `3e8b389e` "Recompute all users" (SUSPENDED, artefacto histórico) — HTTP 204.
- Backup de sesión: `/home/juansanchez/bkp_pre_recon_estudiantes_20260531.dump` (2.7 GB lean, `--exclude-table-data=ma_audit*`).

### Salvaguardas finales (snapshot 2026-05-31)
- m_user = **49.327** (sin pérdida) · dual-structural USER = **0** · disco / = **75%** · Koha+LDAP resources = `proposed` (sin provisioning).

### VEREDICTO: **GATE VERDE para Koha. LDAP verde-condicional (3 casos acotados).**

1. **Koha listo para `proposed → active`** desde el punto de vista de seguridad: 0 deletes, 0 falsos leavers contra Oracle, 4.806 alumni + 94 leavers legítimos a archivar (disabled idempotente, sin pérdida transaccional). Decisión de activar = del usuario.
2. **LDAP: 3 casos a resolver antes de activar** (`001261673` doble-afiliación con item no materializado + `76795236` data-gap correo). Acción acotada: **recon completa del resource Estudiantes Y Trabajadores** (replay inbound strong) para materializar `001261673`; o aceptar que esos 1-3 se re-provisionan en el siguiente ciclo de recon tras activar. Los 2 sin correo son data-gap del SIS (no IGA).

**Pendientes de raíz (NO bloquean Koha, decisión usuario):**
- **(C)** Normalización `lambDocNum` (padding) en inbound+correlador → cierra 20 de los 32 UNMATCHED Trabajadores. Cambio crítico (50k users) → validar en simulación.
- **(D)** 160 matriculados activos SIN `CORREO_INST` en MOISES → escalar a RR.AA./SIS (asignación de correo). Mientras tanto quedan `archived`/`draft` sin cuenta; canónicamente deberían ser `draft` (enrolled), no `archived`.
- **(E)** 19 COD_APS multi-ID_PERSONA con DNI typo/basura → data-quality MOISES irrecuperable; excepción documentada (no archivan a nadie).

---

## ROADMAP ORDENADO COMPLETO — Go-live Koha + LDAP (2026-05-31)

> **PARTE A del encargo.** Análisis de dependencias para go-live, ordenado por fases que MINIMIZAN rework. midpoint-expert + koha-expert. Skills: `iga-canonical-standards` §1.2/§1.3/§3.2/§10; `midpoint-best-practices` §1.2/§2.1/§3/§4.4/§4.5. Read-only salvo G1/G3/G4 (ya ejecutados, ver PARTE B abajo).

### Estado de cierre de gaps (snapshot tras esta sesión)

| Gap | Tema | Estado |
|---|---|---|
| **G1** | Birthright CRAI roto (costCenter format + ID_AREA erróneos) | ✅ **HECHO** (esta sesión): `93` numérico puro. 97/522/625 eran basura. |
| **G2** | Permisos librarian (flags CRAI) requieren connector v1.4.0 | ⏳ DIFERIDO (no bardea go de patrones; ver Fase 5) |
| **G3** | circulation_rules de las 6 categorías eduPerson | ✅ **HECHO** (esta sesión): faculty/staff/student/alum/affiliate ya estaban; `local` clonado de ADMIN. |
| **G4** | Descripciones legacy AR-Koha-Patron-* + mapa MEMORY | ✅ **HECHO** (esta sesión). |
| **C** | Normalización `lambDocNum` padding (50k, correlador) | ⏳ data-quality, validar simulación |
| **D** | 160 matriculados sin CORREO_INST → draft (no archived) | ⏳ escalar SIS/RR.AA. |
| **E** | 19 DNIs typo/basura MOISES | ⏳ excepción documentada (irrecuperable) |

### Mapa de dependencias (qué precede a qué)

```
[FASE 0] Materialización IIA completa (liveAffiliation*)  ── PRE-REQUISITO DURO de todo provisioning
   │  recon Trabajadores (✅ e8d054ba) + Estudiantes (✅ 100% materializado) + Egresados (✅)
   │  → liveAffiliationWorker / liveAffiliationStudent / liveAffiliationAlum poblados
   ▼
[FASE 1] Data-quality bloqueante mínima
   │  C (padding lambDocNum)  → opcional para go (cierra 20 falsos leavers; NO bloquea Koha)
   │  D (160 sin correo → draft)  → NO bloquea (sin shadow no se crea/archiva cuenta)
   │  E (19 typo)  → excepción (no archiva a nadie)
   ▼
[FASE 2] Gaps de provisioning Koha/LDAP   ── G1 ✅, G3 ✅, G4 ✅  (ESTA SESIÓN)
   │  G1 birthright CRAI → necesario antes de activar Koha para que bibliotecarios tengan AR-Koha-Librarian
   │  G3 circulation_rules → necesario antes de activar Koha (sin reglas, préstamos sin límites correctos)
   │  G4 descripciones → cosmético, no bloquea
   ▼
[FASE 3] GO PARCIAL Koha = PATRONES  (proposed → active del objectType Koha)
   │  Habilita: creación/archivado de patrones (faculty/staff/student/alum/affiliate/local)
   │  category_id eduPerson (Diseño B), existence+admin-status (leaver=disabled), library_id por locality
   │  NO depende de connector v1.4.0 (los patrones se crean/archivan con v1.3.3)
   ▼
[FASE 4] GO LDAP  (proposed → active del objectType LDAP)
   │  Pre: resolver 3 casos acotados (001261673 doble-afiliación item no materializado vía recon completa; 2 data-gap correo)
   │  Menor riesgo: deprovisión limpia (delete shadow), 5.836 cuentas
   ▼
[FASE 5] DIFERIDO post-go — permisos CRAI (G2)
   │  connector-koha v1.4.0: flags de permisos librarian (CRAI staff vs circulación)
   │  Los bibliotecarios ya tienen patrón + AR-Koha-Librarian (G1); v1.4.0 añade los FLAGS de permiso fino.
   │  NO bloquea el go de patrones: un bibliotecario sin v1.4.0 funciona como patrón staff hasta el upgrade.
   ▼
[FASE 6-8] Migración categorycodes legacy  ── POST-GO, asíncrono
      Reconciliación 13.805 shadows Koha existentes (DISPUTED/UNLINKED/UNMATCHED)
      22K patrones legacy DOCEN/PREGRADO/ADMINIST/... → categorías eduPerson (vía recompute/recon)
      Drop categorías legacy (DOCEN/ADMINIST/PREGRADO/POSGRADO/ALUMNI/ESTUDI/VISITA/JUBILADO)
      SOLO tras confirmar 0 patrones residuales en categorías viejas.
```

### Orden canónico recomendado (fases, qué permite go-parcial, qué difiere)

| # | Fase | Bloqueante para go | Permite go-parcial | Difiere |
|---|---|---|---|---|
| 0 | Materialización IIA (recons completas) | **SÍ** (duro) | — | — |
| 1 | Data-quality C/D/E | No (acotados, validados vs Oracle) | sí (go con 0 falsos leavers Koha) | C/D/E a ciclo siguiente |
| 2 | G1/G3/G4 | **SÍ** (G1 birthright, G3 reglas) | — | G4 cosmético |
| 3 | **GO Koha patrones** (objectType proposed→active) | — | **GO PARCIAL AQUÍ** (patrones ya) | — |
| 4 | GO LDAP (objectType proposed→active) | resolver 3 casos | go tras recon completa | — |
| 5 | G2 connector v1.4.0 (permisos CRAI) | No | — | **DIFERIDO post-go** |
| 6-8 | Migración categorycodes + recon 13.805 + drop legacy | No | — | **POST-GO asíncrono** |

### Reconciliación de los 13.805 shadows Koha existentes — tratamiento canónico
- **No requiere acción pre-go.** Tras `proposed→active`, la primera recon Koha correlaciona los 13.805 por las 3 capas (cardnumber/lambDocNum/taxId).
- DISPUTED/UNMATCHED de Koha = `unmatched` sin acción (Koha NO es IIA; MidPoint no resta lo que no creó — patrón ya implementado y VÁLIDO).
- UNLINKED con owner → `link`. Los legacy en categorías viejas se recategorizan a eduPerson en el siguiente recompute (Fase 6-8), sin pérdida de transacciones (archivado = disabled, nunca delete).

### Veredicto de orden
**Camino crítico al go de patrones:** FASE 0 (✅ materialización) → FASE 2 (✅ G1/G3/G4 esta sesión) → **FASE 3 (GO Koha patrones) = LISTO para decisión del usuario.** LDAP requiere FASE 4 (3 casos). G2/categorycodes/recon legacy son **post-go** y NO bloquean. Esto evita el rework de descubrir gaps uno por uno: todo lo bloqueante para patrones está cerrado.

---

## PARTE B — EJECUCIÓN G1 + G3 + G4 (2026-05-31)

> Autorizado por usuario. Oracle SOLO SELECT (instantclient thick ARM64). Koha DB: backup previo + INSERT idempotente. MidPoint: commit→push→pull→PUT. Resources Koha/LDAP siguen `proposed` (sin provisioning). Skills consultadas: ambas.

### G1 — Birthright CRAI (ID_AREA reales encontrados)
**Validación vs Oracle (`ELISEO.ORG_AREA`, SELECT):**
- `97` = **Colegio Unión** (NO CRAI), `522` = Agente de Seguridad-Turno Día, `625` = APCE SUSCRIPCIONES (ent. 17114). Los tres ERRÓNEOS.
- CRAI real: **ID_AREA 93** = 'Centro de Recursos del Aprendizaje e Investigación' (ESTADO='1', ID_ENTIDAD=7124, parent=69 Dir. Gral. Investigación). Únicos otros matches (454 'CRAI', 582 'CRAI FT') están INACTIVOS (ESTADO='0').
- **52 trabajadores vivos 7124 resuelven a área 93** (vs 0 a 454/582). En MidPoint hoy: 22 users con `costCenter='93'` (confirma formato numérico puro). El split por campus (BUL/BUJ/BUT/CIA) NO son áreas separadas: se gobierna en Koha vía `library_id`/locality.
- **2º bug confirmado:** el fix costCenter del 2026-05-27 (`id-area-to-costCenter`) cambió costCenter a ID_AREA numérico puro; la condición `['area.97',...]` quedó doblemente rota (valor + formato `area.NN`).

**Corrección aplicada** en `canonical/object-templates/UserTemplate-Person-Base.xml`:
- Condiciones Q4 y Q5: `['area.97','area.522','area.625']` → `['93']` (numérico puro). Comentarios L30-31 y bloque Q4 (L1385+) corregidos con la validación Oracle.

### G3 — circulation_rules (Koha DB, koha_bul, branch BUL único)
**Verificación (SELECT):** faculty(34)/staff(34)/student(33)/alum(33)/affiliate(3) YA tenían reglas equivalentes a sus predecesores DOCEN(34)/ADMINIST(34)/ESTUDI(33)/ALUMNI(33)/VISITA(3). **Gap único: `local` con 0 reglas.**
**Acción:** backup `circulation_rules` (`/tmp/circulation_rules_bkp_20260531_0802.sql`) + `INSERT...SELECT` idempotente clonando `local` de `ADMIN` (35 reglas, branchcode global NULL — apropiado para cuentas de sistema/kioscos). Resultado: **6/6 categorías eduPerson con reglas equivalentes a su predecesora.**

### G4 — Descripciones legacy
Actualizadas `<description>` de AR-Koha-Patron-{Faculty,Administrativo,Alumni,Pregrado,Posgrado}: señalan que **Diseño B (eduPerson) reemplazó al Diseño A**, category_id = primaryAffiliation literal (faculty/staff/student/alum), nivel→STUDY_LEVEL ortogonal, CRAI/researcher fuera de category_id. Mapa "categorías Koha↔IGA" en MEMORY.md reescrito a Diseño B con counts de circulation_rules.

### Estado tras G1/G3/G4 — qué falta para go (según roadmap)
- **GO Koha patrones (FASE 3): LISTO** salvo decisión del usuario de `proposed→active` del objectType Koha. Camino crítico cerrado.
- **GO LDAP (FASE 4):** resolver 3 casos acotados (recon completa para materializar `001261673`; 2 data-gap correo del SIS).
- **Diferido (no bloquea):** G2 (connector v1.4.0 permisos CRAI), C/D/E data-quality, migración categorycodes + recon 13.805 + drop legacy (post-go asíncrono).

### G1 — Canary y verificación post-PUT (2026-05-31)
- PUT a PROD: template `855caaca...` + 5 roles AR-Koha-Patron-* → todos **HTTP 201**.
- **Canary 1 (`07683776`, costCenter=93):** assignment vía mapping `Q4-birthright-koha-librarian-crai` → **AR-Koha-Librarian** + tier **AR-Koha-Librarian-Circulacion** (fallback). ✅
- **Canary 2 (`29605891`, costCenter=93):** **AR-Koha-Librarian** + tier **AR-Koha-Librarian-ProcesosTecnicos** (resuelto por ID_PUESTO vía LookupTable). ✅ Confirma que la condición `['93']` matchea y Q5 resuelve tier correcto.
- **Residuo benigno detectado (NO bloquea):** 10 users costCenter=93 con AR-Koha-Librarian (correcto) **+ 11 users costCenter=69** ('Dirección General de Investigación', parent del CRAI) con la asignación Q4/Q5 STALE (metadata createTimestamp 2026-05-18, pre-fix). El mapping strong la REMOVERÁ en el próximo recompute (condición `['93']` falsa para cc=69). Sin impacto: resource Koha en `proposed` (0 provisioning). Se auto-sanea en el ciclo de recompute/recon masivo previo al go. `POST /users/{oid}/recompute` devuelve 404 en este build 4.10 (quirk REST conocido); el saneo se hará vía task de recompute masivo, no per-user REST.

---

## GO/NO-GO FORMAL — Activación provisioning patrones Koha (2026-05-31, sesión de decisión)

> Encargo: activar provisioning real de patrones Koha en PROD **SOLO SI** los expertos Koha y MidPoint dan GO. midpoint-expert. Read-only (SOLO validación). NINGÚN resource pasó a `active`. NINGÚN provisioning. Oracle SOLO SELECT (instantclient ARM64 23.3). Skills consultadas: `midpoint-best-practices` §1.2/§2.1/§4.2/§4.5; `iga-canonical-standards` §1.2/§1.3/§3.2.

### Invariantes pre-go (frescas, PROD 2026-05-31)
| Invariante | Valor | OK |
|---|---|---|
| m_user total | 49.327 | ✅ (sin pérdida) |
| dual-structural USER (9 archetypes structural) | 0 | ✅ |
| Disco / | 75% | ✅ (<90%) |
| Koha resource lifecycleState | `proposed` (a nivel RESOURCE, no objectType) | ✅ (0 provisioning) |
| liveWorker(216)/liveStudent(217)/liveAlum(215) materializados | 3.735 / 10.936 / 30.650 | — |
| Salvaguarda académica POR ITEM (217/215 archived) | 0 | ✅ pero **insuficiente** (ver abajo) |

### Dry-run agregado Koha (read-only, join m_ref_projection)
| Métrica | Valor |
|---|---|
| Elegibles (liveWorker∨liveStudent) → enabled | 14.208 |
| Patrones Koha live | 13.805 (9.977 con owner, 3.828 huérfanos/unmatched) |
| No-elegible CON patrón → ARCHIVAR (disabled) | 4.901 |
| — alumni legítimo (liveAlum) | 4.806 |
| — SIN ninguna afiliación viva (sospechosos) | **95** |
| DELETE Koha | **0** ✅ |
| stale librarian (AR-Koha-Librarian cc≠93) | 10 de 20 |

### VALIDACIÓN DE LOS 95 SOSPECHOSOS CONTRA ORACLE (regla metodológica del propio runbook)
La salvaguarda por item da 0 **precisamente porque** un falso leaver no tiene `liveAffiliationWorker` poblado (por eso aparece como sospechoso). El gate DEBE validarse contra Oracle, no contra el item. Cruce de los 95 vs `ELISEO.VW_APS_EMPLEADO ID_ENTIDAD=7124 ESTADO='A'` **con vigencia `FEC_TERMINO IS NULL OR >= SYSDATE`** (endurecimiento exigido en MEMORY):

- **5 FALSOS LEAVERS ESTRICTOS** (contrato UPeU vigente hasta 2026/2027): `02530108`(→2027-05-31), `04082096`(→2027-12-31), `04680920`(→2026-06-30), `06158248`(→2026-12-31), `71590328`(→2027-05-31). Los 5 tienen **shadow Koha live=1** y están `archived`/`proposed` con `liveWorker=false`. **Activar Koha ahora los marcaría DISABLED (archivados Koha) siendo trabajadores con contrato vigente.**
- 36 vencidos (`ESTADO='A'` con `FEC_TERMINO` pasado, mayoría 2026-04-30) = leavers legítimos hoy → archivar correcto.
- 0 sin match (resto = leavers/data-gap legítimos).

**Causa raíz de los 5** (confirmada): cada uno tiene shadow Trabajadores vivo `__NAME__`=CANON_KEY (`02530108-412759`, etc.) + shadow viejo `02530108` ya `dead=true`. 4 de 5 con **padding de ceros** en NUM_DOCUMENTO (`002530108` vs `02530108`). El correlador no normaliza `lambDocNum` → el inbound `strong` que materializa `liveAffiliationWorker` no se replayó sobre el shadow vivo → `liveWorker=false` pese a contrato vigente. Es exactamente el **pendiente C (normalización lambDocNum)** dejado abierto en sesiones previas.

### VEREDICTO MidPoint: **NO-GO** ❌
- ✅ 0 deletes Koha (suma-no-resta intacto), 4.806 alumni legítimos a archivar.
- ✅ dual-structural=0, m_user sin pérdida, disco 75%.
- ❌ **5 falsos leavers reales** (contrato 7124 vigente 2026-2027) se archivarían (disabled) en Koha. **Viola el GATE FINAL "0 disabled sobre usuarios con afiliación viva real" validado contra Oracle.** La conclusión previa de "0 falsos leavers" no aplicó la vigencia `FEC_TERMINO` ni capturó el +1 sospechoso (94→95).

### Veredicto koha-expert (lado Koha — registrado)
El lado Koha está LISTO (G3 6/6 circulation_rules eduPerson, connector v1.3.3 operativo, archive-not-delete vía `patron_card_lost`+`expiry` sin tocar transacciones, 0 deletes proyectados, categorías eduPerson creadas). **PERO** el riesgo no es del conector ni de Koha: es de **datos de entrada MidPoint** (5 focos sin `liveWorker` materializado). El conector ejecutaría fielmente el `administrativeStatus=DISABLED` que MidPoint le ordene → archivaría a los 5 trabajadores vigentes. Por tanto el lado Koha **no puede dar GO mientras MidPoint envíe estado disabled sobre afiliados vivos**: GO del conector condicionado a GO de MidPoint. Resultado conjunto: **NO-GO**.

### Regla aplicada
"AMBOS expertos deben dar GO. Si uno duda → NO-GO, detener." MidPoint = NO-GO → **DETENIDO. No se ejecutó activación, backup, recompute ni PATCH.** Resource Koha permanece `proposed`.

### ACCIÓN CORRECTIVA ACOTADA (pre-requisito para re-evaluar GO)
1. **Materializar `liveAffiliationWorker` en los 5** (y barrer residuo de padding): recon completa del resource Trabajadores (`6a91f7e1-…e21`) que replaye el inbound `strong` sobre los shadows vivos `CANON_KEY`. Verificar liveWorker en los 5 → desaparecen como sospechosos.
2. **Fix de raíz C (recomendado, no aplicado):** normalizar `lambDocNum` (strip ceros izq + `zfill(8)` para no fusionar CE) en inbound **y correlador** → cierra el padding de forma permanente. Cambio crítico (50k users) → validar en simulación antes de PROD.
3. Re-correr el dry-run + re-validar los sospechosos vs Oracle CON vigencia `FEC_TERMINO` → gate debe dar **0 falsos leavers estrictos**. Recién entonces re-evaluar GO/NO-GO conjunto.

### Salvaguardas finales (snapshot 2026-05-31)
m_user=49.327 · dual-structural=0 · disco 75% · Koha+LDAP=`proposed` (sin provisioning) · Oracle 0 escrituras.

**Pendiente:** LDAP (Fase 4) sigue bloqueado por el mismo origen (item no materializado). G2/categorycodes/recon legacy = post-go. La activación de patrones Koha queda **pendiente** hasta materializar los 5.
