# Diseño canónico — Manejo de perfiles múltiples (multi-afiliación)

**Spec:** `multi-profile-canonical`
**Fecha:** 2026-05-13
**Autor:** midpoint-expert (UPeU PROD)
**Caso testigo:** Juan Alberto Sanchez Condor — Trabajador (`COD_APS=10867326`, focus OID `c4ff2732-52e7-463a-89fb-218a43280aee`) y Egresado (`CODIGO=9610165`, mismo DNI `10867326`).

Skills consultadas: `iga-canonical-standards` (eduPerson 202208 §3.2, SCHAC 1.6.0 §4.2, ISO 24760 §1.1-1.3, NIST RBAC INCITS 359 §6.4) · `midpoint-best-practices` (§1.1 schema, §2 RBAC, §3 archetypes, §4 focus processing, §5 generic synchronization).

---

## 1. Tesis

Una persona física es **un solo subject** (ISO 24760-1 §3.1.2 *identity* = "set of attributes related to **an entity**"). En un IGA universitario, esa persona puede coexistir simultáneamente como Trabajador, Estudiante, Egresado, Investigador, etc. **El modelo canónico exige UN focus con MÚLTIPLES projections (linkRefs)** y derivar la afiliación múltiple al estilo eduPerson — NO crear focuses paralelos por cada faceta.

> Cita ISO 24760-1: *"The identity is the representation of an entity in a particular domain"* — la persona física es la entidad; el dominio de identidad es UPeU. Una sola identidad por persona, múltiples projections.

> Cita Evolveum (best-practices §1.1): *"Focus / Focal object: single point con múltiples projections."*

---

## 2. Las 9 decisiones canónicas

| # | Decisión | Estándar / Cita | Estado actual UPeU PROD | Gap |
|---|----------|------|---|---|
| 1 | **Single focus por persona física.** Identidad de persona = 1 `UserType`. Las facetas son projections, NO focuses paralelos. | ISO 24760-1 §3.1.2; Evolveum §4 "single point with multiple projections" | OK por diseño (correlator tier-1 = `taxId`/DNI URN en los 3 resources v2). | Ninguno estructural; falta ejecución (4382 focuses, ninguno multi-shadow porque ningún import multi-source ocurrió todavía). |
| 2 | **Multi-source linking.** Cada resource crea un shadow distinto; el focus acumula N `linkRef`. | Evolveum §4.5 pipeline (sync→shadow→correlation→link); §1.1 jerarquía Focus/Projection | OK: los 3 resources v2 tienen `<situation>unlinked → <link/></actions>` en su `<synchronization>`. Correlator por DNI los une. | Ninguno estructural. Falta evidencia operativa: 0 focuses con shadows>1. |
| 3 | **`eduPersonAffiliation` multi-valued derivado.** Calcular en object template a partir de los `linkRef` del focus. Vocabulario canónico (eduPerson 202208 §3.2): `student`, `faculty`, `staff`, `employee`, `member`, `affiliate`, `alum`, `library-walk-in`. `member` se aserta independientemente. | eduPerson 202208 §3.2 (8 valores); REFEDS R&S §8.1 (ePSA recomendado) | **GAP**: NO existe mapping derivativo en `00-common-base.xml` ni en templates por archetype. El atributo no se persiste ni se publica. | Crear item `extension/upeu3:eduPersonAffiliation` (multi) o derivar al vuelo en outbound a Keycloak/LDAP. |
| 4 | **Single structural archetype + auxiliary o "primary affiliation rule".** Best-practices §3.3: *"At most one structural archetype can be applied to object."* Auxiliary archetypes están desaconsejados en 4.9 (UI limitada) → recomendado **birthright roles** en su lugar. | Evolveum §3.3 + §3.5; eduPerson 202208 §3.1 (`eduPersonPrimaryAffiliation`, single) | OK a nivel diseño (1 archetype estructural). Pero falta **regla de precedencia** documentada para decidir cuál archetype gana cuando hay multi-source. | Documentar regla: **HR-trabajadores > SIS-estudiantes > SIS-egresados** (laboral activo gana, luego matrícula activa, luego histórico). Mapping `assignmentTargetSearch` en trabajadores ya tiene `strong`; egresados/estudiantes deben condicionarse a "no hay archetype de orden mayor". |
| 5 | **Multi-assignment de Business Roles simultáneos.** Si Juan es staff + alum, recibe BR-Admin-Area + BR-Egresado simultáneamente. Sus inducements se acumulan (MidPoint suma, no resta — best-practices §2.6 cita literal). | NIST RBAC INCITS 359 §6.4 (Business Role); Evolveum §2.4 inducement | OK: el mapping `autoassign-by-archetype` en cada object template asigna un BR por archetype. Si el focus tiene múltiples archetypes (vía multi-source), recibirá múltiples BRs. **Pero el modelo actual fuerza 1 archetype** → no llega a este escenario en práctica. | Una vez resuelto #4, validar que múltiples BRs convivan (assignments separados con `provenance` distinto). |
| 6 | **`externalSystemId` multi-valued (lista de IDs LAMB).** Cada resource pobla el suyo; deben acumularse, no sobrescribirse. | SCIM 2.0 RFC 7643 §4.1.1 (`externalId` per-resource); ISO 24760 §1.3 IIA por sistema | OK: schema v3 declara `<xsd:element maxOccurs="unbounded" name="externalSystemId">`. Inbounds en estudiantes-v2 y egresados-v2 mapean a `extension/upeu3:externalSystemId` con `strength=weak`. **Trabajadores-v2 NO mapea `COD_APS` a `externalSystemId`** (solo a `personalNumber`+`name`). | Agregar inbound en trabajadores-v2 que pobla `externalSystemId` con `COD_APS` (también weak, también acumulativo). Así, focus fusionado contiene `[COD_APS, CODIGO_egresado, CODIGO_estudiante]`. |
| 7 | **`personalNumber` strength: HR gana.** Cuando colisionan COD_APS (HR) y CODIGO (SIS), prevalece el laboral. | ISO 24760 §1.3 IIA: HR es IIA del identificador laboral primario; Evolveum §4.2 strength | OK: trabajadores-v2 = `strong`, estudiantes-v2 = `weak`, egresados-v2 = `weak`. Implementación correcta. | Ninguno. |
| 8 | **Object templates derivan ePPN, ePSA, eduPersonAffiliation desde linkRef + archetypeRef.** Los atributos eduPerson NO se persisten en extension; se computan en outbound (LDAP/Keycloak). Best-practices §6 regla 2 ("no duplicar lo que ya está en core") y SPEC v3 principio §2 ("atributos derivables no se persisten"). | eduPerson 202208 §3 (atributos LDAP, no de schema interno); Evolveum §4.1 object template | **GAP**: `00-common-base.xml` NO contiene mapping para `eduPersonAffiliation` ni `ePSA`. La derivación sigue pendiente para Fase 6 (resources outbound LDAP/Keycloak). | Documentar que la derivación canónica vivirá en el outbound del resource OpenLDAP cache (Fase 6) o, si se necesita ya, en un mapping del object template base que itere `linkRef` y deduzca afiliación por `resourceRef.oid`. |
| 9 | **Correlación cross-resource consistente.** Los 3 resources deben usar **misma estrategia tier-based** anclada en taxId. | Evolveum §4.5 sync pipeline; ISO 24760 §1.3 IIA correlation | **GAP de consistencia**: egresados-v2 usa **tier-based correlator** (tier 1=taxId, tier 2=name) — correcto. Trabajadores-v2 y estudiantes-v2 usan **multi-correlator plano** (`name` y `taxId` sin tier ni weight) — riesgoso. El mismo bug que fue corregido en egresados (foco duplicado por `uncertain`) puede ocurrir en trabajadores/estudiantes. | Migrar trabajadores-v2 y estudiantes-v2 al patrón tier-based: tier 1 = `taxId` (autoritativo persona física), tier 2 = `name` (fallback para registros legacy sin DNI). |

---

## 3. Cómo debería verse Juan Alberto en el modelo final

```
┌────────────────────────────────────────────────────────────────┐
│  UserType focus  oid=c4ff2732…                                 │
│  name           = 10867326                                      │
│  fullName       = Juan Alberto Sanchez Condor                   │
│  personalNumber = 10867326                  (HR strong gana)    │
│  emailAddress   = …@upeu.edu.pe                                 │
│  archetypeRef   → archetype-user-employee-staff (PRIMARY)       │
│                   archetype-user-alumni         (¿auxiliary?)*  │
│                                                                 │
│  extension/upeu3:                                               │
│    taxId            = urn:schac:personalUniqueID:pe:DNI:PE:10867326 │
│    externalSystemId = ["10867326", "9610165"]   ← multi         │
│    hireDate         = 2022-05-01                                │
│    terminationDate  = 2026-12-31                                │
│    birthDate        = 1978-06-21                                │
│                                                                 │
│  linkRef  →  shadow-trabajadores  (resource v2 trabajadores)   │
│              shadow-egresados     (resource v2 egresados)       │
│                                                                 │
│  assignment[1] → BR-Admin-Area  (auto, provenance=template-staff)│
│  assignment[2] → BR-Egresado    (auto, provenance=template-alumni)│
│  assignment[3] → archetype staff                                │
│  assignment[4] → archetype alumni** o equivalente               │
│                                                                 │
│  Derivado en outbound LDAP/Keycloak (Fase 6):                  │
│    eduPersonPrincipalName       = 10867326@upeu.edu.pe          │
│    eduPersonAffiliation         = [staff, employee, alum, member]│
│    eduPersonScopedAffiliation   = [staff@upeu.edu.pe,           │
│                                    alum@upeu.edu.pe,            │
│                                    member@upeu.edu.pe]          │
│    eduPersonPrimaryAffiliation  = staff                         │
│    schacPersonalUniqueCode      = urn:schac:…:9610165 (egresado)│
└────────────────────────────────────────────────────────────────┘
```

\* **Decisión #4** define si `alumni` se modela como (a) **auxiliary archetype** (limitado en 4.9), (b) **birthright role** que se asigna además del archetype principal, o (c) sólo un valor en `eduPersonAffiliation` derivado. **Recomendación:** opción (c) + (b) — un solo archetype estructural (staff por regla de precedencia HR>SIS>egresados), `BR-Egresado` se asigna como assignment normal cuando existe shadow del resource egresados, y `eduPersonAffiliation` derivado lleva ambos `staff` y `alum`.

\*\* **Si optamos por (b):** no habrá segundo `archetypeRef`, sólo un segundo `assignment` a BR-Egresado.

---

## 4. Cambios requeridos (orden de implementación)

| # | Cambio | Archivo | Fase | Bloqueante de |
|---|---|---|---|---|
| 1 | **Migrar correlators a tier-based** en trabajadores-v2 y estudiantes-v2 (igual que egresados-v2). Tier 1 taxId, Tier 2 name. | `resources/oracle-lamb-trabajadores-v2.xml`, `resources/oracle-lamb-estudiantes-v2.xml` | F1 | Todo lo demás. Sin esto, el merge cross-resource es indeterminista. |
| 2 | **Agregar inbound `COD_APS → externalSystemId` (weak, acumulativo)** en trabajadores-v2. | `resources/oracle-lamb-trabajadores-v2.xml` | F1 | #5. |
| 3 | **Documentar regla de precedencia de archetype**: trabajadores-v2 con `strong` (ya está); estudiantes-v2 y egresados-v2 deben **NO sobrescribir** archetypeRef si focus ya lo tiene de mayor prioridad. Implementación: condición en el inbound `assignmentTargetSearch` que verifique `focus?.archetypeRef`. | resources v2 estudiantes/egresados | F2 | #5. |
| 4 | **Agregar inbound de archetype en estudiantes-v2 y egresados-v2** condicionado: si focus tiene archetype de mayor prioridad, NO asignar el de este resource (gana HR). En su lugar, asignar un **BR de afiliación secundaria** (BR-Estudiante, BR-Egresado). | mismas | F2 | #5. |
| 5 | **Mapping derivativo `eduPersonAffiliation` en object template base** que itere `linkRef` y deduzca:<br>- shadow trabajadores → `staff` o `faculty` (según UPEU_ARCHETYPE_NAME)<br>- shadow estudiantes → `student`<br>- shadow egresados → `alum`<br>- siempre → `member` | `objectTemplates/00-common-base.xml` | F3 | Outbound LDAP/Keycloak Fase 6. |
| 6 | **Ejecutar reconciliación scope=1 sobre el shadow del egresado** del DNI 10867326 (CODIGO=9610165) para fusionarlo al focus existente. | task ad-hoc | F4 | Validación end-to-end del modelo. |

---

## 5. Sintaxis canónica `<query>` en `ResourceObjectSetType` (MidPoint 4.9.5)

Verificado en `/opt/midpoint/doc/schema/xml/ns/public/common/common-tasks-3.xsd` línea 7164:

```xml
<element minOccurs="0" name="query" type="q:QueryType"/>
```

**Forma correcta** (el ELEMENTO va SIN prefijo `q:`; el contenido sí lleva `q:filter`/`q:and`/`q:equal`):

```xml
<task xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
      xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3"
      xmlns:t="http://prism.evolveum.com/xml/ns/public/types-3">
  <name>import-egresado-9610165</name>
  <executionState>runnable</executionState>
  <activity>
    <work>
      <import>
        <resourceObjects>
          <resourceRef oid="6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23" type="ResourceType"/>
          <kind>account</kind>
          <intent>default</intent>
          <query>
            <q:filter>
              <q:equal>
                <q:path>attributes/CODIGO</q:path>
                <q:value>9610165</q:value>
              </q:equal>
            </q:filter>
          </query>
        </resourceObjects>
      </import>
    </work>
  </activity>
</task>
```

(Los intentos previos fallaron probablemente por usar `<q:query>` con prefijo, o por path no calificado con namespace `ri:` — el path canónico bajo `ResourceObjectSet` usa el atributo del objeto class, no el `extension/upeu3:` del focus.)

**Alternativa más segura:** primero ejecutar un task de **discovery puro** (`<reconciliation>` con misma query) que sólo CREA el shadow + correla, sin disparar provisioning hacia abajo. La reacción `unlinked → link` del resource se encarga de fusionarlo al focus correcto vía correlator tier-1 (taxId).

---

## 6. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Import sobre resource Egresados v2 (4427 shadows) sin scope dispara recompute masivo y borra cuentas sincronizadas hacia downstream. | Usar query scope-1 con filtro por `CODIGO`. Correr en task aislado, no full reconciliation. |
| Cambiar correlator de trabajadores/estudiantes mientras hay 4382 focuses puede recorrelacionar y duplicar. | Cambiar correlators **en archivo** primero, NO ejecutar reconciliation; aplicar sólo a futuros imports. Para corregir focuses ya creados, usar `recompute` puntual. |
| Asignar segundo archetype estructural a focus existente es operación destructiva (best-practices §3.4). | Usar la opción (c)+(b): **un solo archetype**, segundo perfil expresado como **BR adicional** + valor en `eduPersonAffiliation`. |
| Derivar `eduPersonAffiliation` desde `linkRef` requiere `midpoint.resolveReferenceIfExists()` en el script — coste por user. | Persistir el atributo derivado en `extension/upeu3:eduPersonAffiliation` (multi) y recomputar sólo cuando cambian linkRefs (condition `archetypeRef` o `linkRef` en sources). |

---

## 7. Próximos pasos sugeridos (en orden)

1. **No ejecutar nada destructivo en PROD ahora.** Cerrar primero el plan B→A→C original (limpieza ✅ → fix BR→AR → mapeo OUs).
2. Aplicar cambios #1 y #2 (tier-based correlators + COD_APS→externalSystemId) en archivo, validar XML, importar a PROD sin disparar reconciliation.
3. Diseñar #5 (mapping eduPersonAffiliation) junto con la spec de OpenLDAP cache (Fase 6).
4. Para el caso testigo Juan Alberto: ejecutar #6 con un task scope-1 en una ventana de mantenimiento. Es la única operación cross-focus que necesita autorización explícita del usuario porque toca el resource de 4427 shadows.

---

## 8. Referencias citadas

- ISO 24760-1 (Identity Information Authority §1.3, identity §3.1.2)
- eduPerson 202208 v4.4.0 §3.2 vocabulario (8 valores) y §3.4 best practices
- SCHAC 1.6.0 §4.2 (`schacPersonalUniqueID`, `schacPersonalUniqueCode`)
- SCIM 2.0 RFC 7643 §4.1.1 (`externalId` per-resource semantics)
- NIST RBAC INCITS 359 §6.4 (Business Role / Application Role / Entitlement)
- Practical Identity Management with MidPoint v2.3 (Semančík): cap 6-10
- MidPoint docs: https://docs.evolveum.com/midpoint/reference/correlation/ (tiered correlators)
