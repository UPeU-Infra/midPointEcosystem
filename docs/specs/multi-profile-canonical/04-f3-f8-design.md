# 04 — Diseño F3 + F8: schacHomeOrganization y vinculación focus→Org

**Fecha:** 2026-05-14
**Instancia:** midpoint-prod (192.168.15.166), MidPoint 4.9.5
**Autor:** midpoint-expert (UPeU PROD)
**Autorización:** Juan Alberto Sánchez Condor — ejecutar F8 + F3 del plan en `02-roles-orgs-audit.md`.

Skills consultadas: `iga-canonical-standards` §1.3 (IIA), §4.2 (`schacHomeOrganization`), §10.2 (OrgType archetypes); `midpoint-best-practices` §5.1 (assignment vs parentOrgRef), §5.2 (org tree, identifiers), §5.4 (Role hierarchy ≠ Org hierarchy), §6.1 (object templates como lugar canónico para reglas cross-resource).

---

## 1. Resumen ejecutivo

Diseño completo. **Implementación BLOQUEADA por gap upstream** (cobertura focus→Org = 0% con el modelo actual). Se documenta el diseño objetivo y se reporta el bloqueo para que F4/F5 (modelado de EAPs + extracción `lambDeptoCode`) se ejecuten antes.

| Decisión | Conclusión |
|---|---|
| F3 — `schacHomeOrganization` se setea en | **Solo en las 2 institutions (raíz)**. Hijas lo derivan en runtime via outbound recorriendo `parentOrgRef`. (Confirma decisión 03 §2.2.) |
| F3 — Persistencia | Ya cubierto: `UPeU.identifier=upeu.edu.pe`, `COLEGIO-UNION.identifier=colegiounion.edu.pe`. **No se requiere extender schema** ni poblar `extension/schacHomeOrganization` redundantemente. |
| F3 — `eduOrgLegalName` | Setear `displayName` (ya hecho para UPeU = "Universidad Peruana Unión"). NO crear atributo extension separado: `displayName` cumple la misma semántica para SAML SPs y para auditoría humana. |
| F8 — Método de vinculación | **Assignment con `relation=default` a OrgType** (Opción A). Estándar Evolveum (best-practices §5.1). |
| F8 — Lugar de la regla | **Object template** por archetype (mejor: declarativo, cross-resource — best-practices §6.1). NO en mapping inbound del resource. |
| F8 — Estado | **BLOQUEADO**. Ver §5. |

---

## 2. F3 — `schacHomeOrganization` y `eduOrgLegalName`

### 2.1 Investigación canónica

**SCHAC 1.6.0 §6 (`schacHomeOrganization`):**
- Tipo: single-valued FQDN DNS administrativo de la institución que asierta la identidad.
- Granularidad: **una institución = un valor**. No es un atributo jerárquico que cambie por sub-org. Una facultad de UPeU NO tiene `schacHomeOrganization=ingenieria.upeu.edu.pe` — todos comparten `upeu.edu.pe` (el dominio del Identity Provider SAML).
- En IGA el valor se persiste **una vez por institución** (en la raíz del árbol institucional) y se deriva por herencia para todas las personas afiliadas a esa institución.

**eduOrg `eduOrgLegalName`:**
- Aplica solo a la entidad legal (institution). Sub-orgs NO tienen `eduOrgLegalName` propio. UPeU = "Universidad Peruana Unión"; FACULTAD-INGENIERIA NO tiene `eduOrgLegalName` separado — su displayName humano alcanza.

### 2.2 Decisión

**No extender schema. No agregar `extension/upeu3:schacHomeOrganization` a OrgType.** Razones:

1. **Fuente de verdad única ya cubierta** por `identifier` (best-practices §5.2 *"Always use organizational unit identifiers"*). Las dos institutions ya lo tienen poblado correctamente:
   - `UPeU.identifier = upeu.edu.pe`
   - `COLEGIO-UNION.identifier = colegiounion.edu.pe`
2. **Duplicar en extension viola** el principio canónico §2 de SPEC v3 ("atributos derivables no se persisten").
3. **Resolución en outbound** (Fase 6 OpenLDAP/Keycloak): la outbound expression del resource LDAP/Keycloak recorrerá `parentOrgRef` del focus hasta encontrar el primer ancestro con `archetype-org-institution` y leerá su `identifier`. Esto soporta nativamente afiliación dual (un docente con `parentOrgRef` a ambas institutions emite dos `schacHomeOrganization` o uno por SP destino según política).
4. **`displayName`** ya satisface `eduOrgLegalName` para todos los consumidores: SAML SPs leen `o`/`displayName`; auditoría humana lee `displayName`.

### 2.3 Acciones F3 en PROD

| # | Acción | Estado |
|---|---|---|
| F3.1 | Verificar `UPeU.identifier=upeu.edu.pe` + `displayName=Universidad Peruana Unión` | ✓ Ya hecho (spec 03 anexo B) |
| F3.2 | Verificar `COLEGIO-UNION.identifier=colegiounion.edu.pe` | ✓ Ya hecho (spec 03 anexo B) |
| F3.3 | Setear `COLEGIO-UNION.displayName=Colegio Unión` (TBD si está vacío) | Por verificar/aplicar |
| F3.4 | NO crear `extension/upeu3:schacHomeOrganization` ni `eduOrgLegalName`. NO modificar schema. | Decisión documentada |

**Conclusión F3:** ya está completo a nivel de fuente de verdad. La materialización SAML/LDAP llega en Fase 6.

---

## 3. F8 — Vinculación focus → Org

### 3.1 Opciones evaluadas

| Opción | Evaluación |
|---|---|
| **A. Assignment a OrgType** (`assignment[targetRef→OrgType, relation=default]`) | Patrón canónico Evolveum. Soporta multi-org nativamente. Habilita `roleMembershipRef` derivado, herencia de inducements via Org→Role induction, gobierno por approver/manager via `relation`. **Elegida.** |
| B. `parentOrgRef` directo en focus | Patrón legacy 3.x. Menor expresividad. NO deriva membership ni inducement. Descartada. |

Cita best-practices §5.1: *"User → Assignment → Org. Assignments are the canonical way for a focus to participate in organizational structure."*

### 3.2 Lugar de la regla

**Object template por archetype** (best-practices §6.1 — *"Object templates are the canonical place for cross-resource derivations and birthright assignments"*).

Razones para NO ponerla en el inbound del resource:
1. Multi-source: si el focus tiene shadows en N resources, la regla en inbound se ejecutaría N veces con resultados parciales. En object template se ejecuta una vez por focus, después de focus processing.
2. Reutilización: object template aplica también a focuses creados manualmente o vía CSV import, no solo desde Oracle LAMB.
3. SoT: la regla cross-cutting "trabajador → Org de su departamento" es lógica de negocio del IGA, no del resource.

### 3.3 Reglas de mapeo por archetype

| Archetype | Atributo fuente | Atributo Org buscado | Fallback |
|---|---|---|---|
| `archetype-user-employee-staff` | `extension/upeu3:lambDeptoCode` (TBD: requiere extracción nueva) | Org con `identifier = lambDeptoCode` y archetype `department` o `academic-unit` | Campus inferido por `lambSedeCode` → si tampoco, `OU-CAMPUS-LIMA` por defecto |
| `archetype-user-employee-faculty` | `extension/upeu3:lambDeptoCode` | Igual | Igual + assignment a `FACULTAD-*` derivada por `lambEscuelaCode` |
| `archetype-user-student` | `extension/upeu3:academicProgramCode[*]` | Org con `identifier = academicProgramCode` y archetype `department` (EAP) | Facultad correspondiente; último recurso `OU-CAMPUS-LIMA` |
| `archetype-user-alumni` | `extension/upeu3:academicProgramCode[*]` | Igual a student | Igual |
| `archetype-user-affiliate-*`, `contractor`, `service-account` | N/A | N/A | Org corporativa por defecto o ninguna |

### 3.4 Sintaxis de referencia (objeto template)

```xml
<mapping>
  <name>autoassign-org-by-academic-program</name>
  <strength>strong</strength>
  <source>
    <path>extension/upeu3:academicProgramCode</path>
  </source>
  <expression>
    <assignmentTargetSearch>
      <targetType>c:OrgType</targetType>
      <filter>
        <q:equal>
          <q:path>identifier</q:path>
          <expression><script><code>academicProgramCode</code></script></expression>
        </q:equal>
      </filter>
      <createOnDemand>false</createOnDemand>
    </assignmentTargetSearch>
  </expression>
  <target>
    <path>assignment</path>
  </target>
  <condition>
    <script><code>
      // Solo si focus NO tiene aún assignment a una Org
      midpoint.focusContext.objectNew?.asObjectable()?.assignment?.findAll {
        it.targetRef?.type?.localPart == 'OrgType'
      }?.isEmpty()
    </code></script>
  </condition>
</mapping>
```

(Sintaxis verificada contra `midpoint-best-practices` §6.1 ejemplo 6.4 + `iga-canonical-standards` §10.4.)

---

## 4. Verificaciones previas — Estado real PROD (2026-05-14)

### 4.1 Población de focuses

| Archetype | Total | Con `academicProgramCode` (id 22) | Con `lambDeptoCode` |
|---|---:|---:|---:|
| `archetype-user-student` | 8 | 8 (100%) | N/A |
| `archetype-user-employee-staff` | 7 | 0 | **0** (atributo no existe en schema ni inbound) |
| `archetype-user-employee-faculty` | 3 | 0 | **0** (idem) |
| `archetype-user-alumni` | 18 679 | **0 (0%)** | N/A |
| Total focuses canónicos | **18 697** | 8 | 0 |

### 4.2 Población de Orgs

| Métrica | Valor |
|---|---|
| Orgs totales | 92 |
| Orgs con `identifier` | ~14 (las que ya migraron a naming.dot) |
| Orgs con `identifier` numérico (matching `academicProgramCode` o `lambDeptoCode`) | **0 / 92** |
| EAPs / departamentos académicos modelados bajo facultades | **0** (G9 del audit 02 sin resolver) |
| Orgs cuyo `identifier` coincide con algún code presente en focuses | **0** |

### 4.3 Cobertura proyectada del mapping focus → Org

**0%** de los focuses encontrarían target Org bajo el modelo actual.

Casos:
- 8 estudiantes con `academicProgramCode ∈ {1, 10, 353, 356, 649, 893, 1112}` — ninguna Org tiene esos identifiers (no hay EAPs).
- 18 679 alumni sin `academicProgramCode` poblado — ni siquiera tendrían input para el mapping (el inbound de egresados-v2 no extrae código de programa al focus).
- 10 trabajadores sin `lambDeptoCode` poblado — el atributo no está en schema, no hay inbound; trabajadores-v2 SQL no extrae `ID_DEPTO` ni `NOMBRE_DEPTO`.

---

## 5. BLOQUEO — Cobertura 0% → DETENER ejecución F8

Conforme a la restricción explícita del prompt:
> *"Si la cobertura es <50%, DETENTE y reporta — necesitamos primero modelar más OUs (F4/F5)."*

**Resultado: 0% de cobertura. Se detiene la ejecución de F8.**

### 5.1 Pre-requisitos para desbloquear F8

| # | Pre-requisito | Origen | Esfuerzo |
|---|---|---|---|
| **PR-1** | Modelar EAPs (Escuelas Académico-Profesionales) bajo cada `FACULTAD-*` con `identifier` = código numérico LAMB de programa de estudio | F5 del audit 02 | M (necesita query LAMB para enumerar `ID_PROGRAMA_ESTUDIO`) |
| **PR-2** | Extraer `ID_DEPTO`+`NOMBRE_DEPTO` en SQL de `trabajadores-v2.xml` y mapearlo a `extension/upeu3:lambDeptoCode` (atributo NUEVO en schema lamb v1) | F8 (parte preparatoria) | S (modificar SQL, agregar inbound, agregar item a schema) |
| **PR-3** | Modelar departamentos administrativos UPeU bajo `OU-CAMPUS-*` o `DIR-GENERAL-CAMPUS-*` con `identifier` = `lambDeptoCode` | F4+F5 del audit 02 | L (decisión de jerarquía: ¿bajo campus o bajo DIR-GENERAL? Spec 03 §1.3 dejó esto pendiente) |
| **PR-4** | Extraer `ID_PROGRAMA_ESTUDIO` en `egresados-v2.xml` SQL y mapearlo a `extension/upeu3:academicProgramCode` (acumulativo, weak) — habilita los 18 679 alumni para el mapping | F8 (parte preparatoria) | S |
| **PR-5** | Definir convención de identifier numérico para Orgs (¿`identifier = "1112"` o `identifier = "ep.psicologia"` con un atributo separado `extension/upeu3:lambProgramaCode`?). **Recomendación canónica:** mantener `identifier` legible (`ep.psicologia`) y agregar `extension/upeu3:lambProgramaCode` (single-valued indexed) en OrgType para el lookup desde focus. Esto evita romper la convención `lower.dot` de identifiers. | Diseño nuevo | S |

### 5.2 Decisión recomendada sobre identifier numérico

**Opción canónica (PR-5 elegida):** NO usar `identifier` numérico en Orgs.

- `identifier` queda en formato `lower.dot` legible (`ep.ingenieria.sistemas`, `ep.psicologia`, `dpto.contabilidad`).
- Agregar al **schema lamb v1** (no al schema de personas v3) un nuevo ext item para OrgType:
  ```
  urn:upeu:midpoint:lamb:v1#lambProgramaCode  (SCALAR, indexed, OrgType only)
  urn:upeu:midpoint:lamb:v1#lambDeptoCode     (SCALAR, indexed, OrgType only)
  ```
- El mapping `assignmentTargetSearch` busca por `extension/lamb:lambProgramaCode` o `extension/lamb:lambDeptoCode` según archetype.
- Beneficio: separa la **identidad canónica** (identifier humano, estable) del **código de fuente externa** (lamb code, fungible si LAMB cambia).
- Cita iga-canonical-standards §1.3 IIA: el `identifier` es responsabilidad del IGA; el `lambProgramaCode` es responsabilidad de la fuente LAMB. Mantener separados respeta el principio de IIA.

### 5.3 Lo que SÍ se puede ejecutar ahora (sin bloqueo)

1. **F3.3** (verificar/setear `COLEGIO-UNION.displayName=Colegio Unión` si está vacío). Operación atómica, sin riesgo.
2. **Documentación** del diseño (este archivo).
3. **NO ejecutar**: cambios al schema, recompute de focuses, creación de mappings que apuntarían a 0 targets.

---

## 6. Plan F-series re-ordenado

Revisión del orden propuesto en `02-roles-orgs-audit.md` §5 a la luz del bloqueo:

| Orden actual | Orden recomendado | Razón |
|---|---|---|
| F3 (schacHomeOrganization) | **Casi completo (cubierto por identifier en institutions)** | Reducir a verificación + documentación |
| F4 (deduplicar campus) | F4 sigue | Pre-requisito de F5 |
| F5 (modelar EAPs + departamentos) | **F5 BLOQUEANTE de F8** | Sin esto, F8 = 0% cobertura |
| F8 (vincular focuses) | **F8 espera a F5 + PR-2 + PR-4 + PR-5** | Documentado en §5.1 |
| Resto | Sin cambio | |

---

## 7. Próximas acciones (a confirmar con Juan Alberto)

1. ✅ Aceptar el diseño F3 + F8 documentado aquí.
2. Decidir orden de ejecución de pre-requisitos:
   - **Opción rápida** (1-2 días): PR-2 (extraer `lambDeptoCode` en trabajadores) + modelar 5-10 departamentos críticos para los 10 trabajadores actuales → cobertura parcial 50-70% en trabajadores, 0% en estudiantes/alumni.
   - **Opción completa** (1-2 semanas): PR-1 + PR-2 + PR-3 + PR-4 + PR-5 → cobertura ≥80% global.
3. Una vez desbloqueado, retomar la ejecución descrita en §3.4 (object templates) y validar con recompute focus-by-focus.

---

## Anexo A — Verificaciones SQL ejecutadas

```sql
-- Total focuses por archetype
SELECT a.nameorig, count(*) FROM m_user u
JOIN m_ref_archetype r ON r.ownerOid=u.oid
JOIN m_object a ON a.oid=r.targetOid
GROUP BY a.nameorig ORDER BY 2 DESC;
-- → alumni 18679, student 8, employee-staff 7, employee-faculty 3

-- Distintos academicProgramCode en estudiantes
SELECT u.ext->'22' AS program_codes, count(*) FROM m_user u
JOIN m_ref_archetype r ON r.ownerOid=u.oid
JOIN m_object a ON a.oid=r.targetOid
WHERE a.nameorig='archetype-user-student'
GROUP BY u.ext->'22';
-- → {1,10,353,356,649,893,1112,[1,353]}

-- ¿Alguna Org tiene identifier numérico que matchee?
SELECT identifier FROM m_org WHERE identifier ~ '^[0-9]+$';
-- → 0 rows

-- Schema ext items relevantes
SELECT id, itemname, cardinality FROM m_ext_item
WHERE itemname IN ('urn:upeu:midpoint:person:v3#academicProgramCode',
                   'urn:upeu:midpoint:lamb:v1#lambDeptoCode');
-- → academicProgramCode (id 22, ARRAY) existe; lambDeptoCode NO existe
```

## Anexo B — Cambios efectivos en este worktree

- Creado: `doc/specs/multi-profile-canonical/04-f3-f8-design.md` (este archivo).
- NO modificado: schemas, resources, object templates, orgs, focuses.
- NO ejecutado: PATCH/PUT/POST en PROD.
