# DECISIÓN — Categorycodes Koha alineados a eduPerson 202208

**Fecha:** 2026-05-23
**Estado:** APROBADA — pendiente implementación
**Autor decisión:** Alberto Sánchez (Infra UPeU / SciBack)
**Análisis técnico:** midpoint-expert (vía Claude Code)

---

## Contexto

UPeU usa MidPoint 4.10 como IGA central y Koha como ILS de biblioteca. Hoy el mapping `MidPoint primaryAffiliation → Koha categorycode` es complejo y desordenado:

- Nombres distintos en cada lado (faculty→DOCEN, staff→ADMINIST, alum→ALUMNI)
- Mezcla de ejes ortogonales en `categorycode`: affiliation (DOCEN), lifecycle (JUBILADO), nivel académico (PREGRADO/POSGRADO), rol funcional (INVESTI)
- 3 correladores acumulados como parches (cardnumber, lambDocNum, taxId)
- Categorías legacy con 22,967 patrones huérfanos (ESTUDI, VISITA, STAFF)
- Categorías nuevas vacías (PREGRADO=0, POSGRADO=0)

## Decisión

**`categorycode` Koha = `primaryAffiliation` MidPoint literal, lowercase, en vocabulario eduPerson 202208.**

El modelo canónico IGA es la fuente de verdad. Koha es una **proyección**, no un eje paralelo de gobernanza. Si MidPoint dice `faculty`, Koha dice `faculty`.

### Mapping canónico

| MidPoint `primaryAffiliation` | Koha `categorycode` | Estándar |
|---|---|---|
| `faculty` | `faculty` | eduPerson 202208 |
| `staff` | `staff` | eduPerson 202208 |
| `student` | `student` | eduPerson 202208 |
| `alum` | `alum` | eduPerson 202208 |
| `affiliate` | `affiliate` | eduPerson 202208 |
| *(cuentas sistema)* | `local` | Convención local explícita |

**Total: 6 categorías Koha** (vs 12 actuales).

### Ejes que NO van en `categorycode`

| Eje | Antes (anti-pattern) | Después (correcto) |
|---|---|---|
| Lifecycle (jubilado) | categorycode=`JUBILADO` | `primaryAffiliation=alum` automático en template cuando `motivoCese=jubilacion` |
| Nivel académico (pregrado/posgrado) | categorycode=`PREGRADO`/`POSGRADO` | `extension/sb:studyLevel` → Koha `extended_attribute STUDY_LEVEL` |
| Rol funcional (investigador) | categorycode=`INVESTI` | Rol/membership `R-Researcher` con inducement Koha `extended_attribute RESEARCHER=Y` |
| Área CRAI (bibliotecario) | (ya correcto) | Rol `AR-Koha-Librarian` con `extended_attribute AREA=CRAI` |

## Racional

### 1. Schema is the law
Doctrina canónica del repo (CLAUDE.md): "modelo canónico primero, datos UPeU se adaptan al modelo, NUNCA al revés." El vocabulario eduPerson 202208 es el estándar internacional de identidad académica. Cualquier sistema downstream se alinea, no se inventa equivalencias locales.

### 2. Trazabilidad inmediata
`WHERE categorycode='faculty'` se entiende sin consultar tabla de conversión. La documentación gratis es el propio estándar eduPerson.

### 3. Reusabilidad SciBack
Modelo aplicable a cualquier universidad que SciBack despliegue. No depende de la historia particular de Koha UPeU.

### 4. Federación SAML futura
Si UPeU se conecta a REFEDS/eduGAIN, los exports/logs de Koha con valores canónicos no rompen políticas de federación.

### 5. Mapping XML trivial
```groovy
return primaryAffiliation
```
vs el bloque de 30 líneas con condicionales actuales en `koha-ils.xml`.

### 6. Separación de ejes ortogonales
Lifecycle, affiliation, nivel académico y rol funcional son **cuatro dimensiones independientes**. Mezclarlas en `categorycode` produce categorías como JUBILADO (lifecycle), INVESTI (rol), PREGRADO (nivel) que no son comparables entre sí.

## Anti-patterns evitados

| Anti-pattern | Por qué se rechaza |
|---|---|
| Inventar `researcher` como eduPerson | NO está en eduPerson 202208 vocabulary. Federación lo rechaza. |
| `RETIRED`/`JUBILADO` como categorycode | Mezcla lifecycle con affiliation. eduPerson 202208: jubilados → `alum`. |
| `PREGRADO`/`POSGRADO` como categorycode | Nivel académico, no affiliation. Va en atributo separado. |
| Uppercase `FACULTY` | Cosmético; rompe alineación literal con estándar. eduPerson usa lowercase. |
| Categorycodes en español (`DOCEN`, `ADMINIST`) | Romántico pero no estándar internacional. |
| Mapping condicional con special cases | Cada excepción es deuda técnica acumulada. Modelo limpio = sin excepciones. |

## Trade-offs aceptados

| Costo | Mitigación |
|---|---|
| 51K patrones a re-stampar | Reconciliación automática MidPoint (≈90% IGA-managed) + batch SQL (≈22K legacy) |
| Bibliotecarios reentrenan vocabulario UI | 2 semanas observación + comunicación interna; cambio en UI Koha cosmético |
| Pierde "español natural" en Koha admin | Documentación clara; nombres autoexplicativos en inglés estándar |
| Reportes históricos requieren mapeo | Tabla `borrowers_migration_log` permite query histórico |
| Pierde distinción pregrado/posgrado en categoría | `extended_attribute STUDY_LEVEL` preserva info; circulation rules ajustables con itemtype/branchcode si biblioteca lo requiere |

## Casos especiales resueltos

### Jubilados (override condicional — Decisión B)
- **Antes:** categorycode=JUBILADO via rol AR-Koha-Jubilado con strong construction override
- **Después:** template MidPoint detecta `motivoCese=jubilacion` y override a `alum` **solo si NO hay affiliation activa de mayor prioridad**:
  - Jubilado puro (sin otras affiliations) → `alum`
  - Jubilado + estudiante posgrado → `student` (prioridad J3 gana)
  - Jubilado + recontratado como docente → `faculty` (el nuevo vínculo activo gana)
  - Jubilado + alumni preexistente → `alum`
- **Racional**: refleja realidad — si después de jubilarte sigues estudiando o vuelven a contratarte, ese vínculo activo manda. eduPerson dice que la affiliation primary refleja el rol institucional vigente más relevante.
- Si biblioteca necesita política diferenciada para jubilados → `extension/upeu:formerRole=staff|faculty` (atributo nuevo) → `extended_attribute FORMER_ROLE` en Koha + circulation rules condicionadas.

### Investigadores (97 DGI)
- **Antes:** planeado como categorycode=INVESTI con resource CSV
- **Después:** rol `R-Researcher` (canonical/roles/) asignado desde CSV DGI. Su categorycode Koha sigue siendo `faculty` o `staff` según contrato. Su rol Researcher proyecta `extended_attribute RESEARCHER=Y` en Koha. Si biblioteca quiere identificar investigadores: filtrar por ese atributo.

### Multi-affiliation (alum + staff simultáneo)
- Egresado que ahora es docente → `primaryAffiliation=faculty`
- Regla de prioridad explícita en template: **`faculty > staff > student > alum > affiliate`**
- Determinístico, no dependiente del orden de inbound de resources
- Sus condiciones secundarias preservadas en `affiliations` (multi-valor) y en cada resource shadow

### Visitas / externos
- **Antes:** categorycode=VISITA, alta manual en Koha
- **Después:** categorycode=`affiliate` (eduPerson 202208 lo cubre exactamente). MidPoint puede gestionar `affiliate` con lifecycle (validFrom/validTo) y birthright limitado. Pendiente: definir proceso de alta MidPoint para affiliates.

### Cuentas sistema (ANON, ADMIN)
- categorycode=`local`. Único valor fuera de eduPerson, documentado como "cuenta técnica no-IGA".

## Referencias estándar

- eduPerson Object Class Specification (202208): https://refeds.org/eduperson
- SCHAC URN registry: https://www.terena.org/activities/tf-emc2/schac.html
- REFEDS R&S: https://refeds.org/category/research-and-scholarship
- ISO 24760 — IT Security and privacy — A framework for identity management
- skill `iga-canonical-standards` (this repo)
- skill `midpoint-best-practices` (this repo)

## Decisiones diferidas

- **Política de préstamo diferenciada por studyLevel** → pendiente discusión con biblioteca UPeU. Si hace falta, se implementa con itemtype rules o circulation rules condicionadas a `extended_attribute STUDY_LEVEL`, NO con categorycode.
- **Proceso de alta de affiliates en MidPoint** → pendiente diseño. Por ahora, los affiliates se siguen creando manualmente en Koha (categorycode=affiliate) hasta que se defina un resource o workflow IGA.
- **Resource CSV Investigadores DGI** → ya planeado (Memoria 2026-05-22). Cuando se implemente, asignará rol `R-Researcher` automáticamente.

## Plan de migración

Ver: [`MIGRATION-koha-categorycodes-plan.md`](MIGRATION-koha-categorycodes-plan.md)

## Aprobación

| Rol | Persona | Estado |
|---|---|---|
| Decisor técnico | Alberto Sánchez | ✅ Aprobado |
| Análisis canónico | midpoint-expert | ✅ Analizado |
| Biblioteca UPeU | — | ⏳ Pendiente socializar antes de Fase 5 |
| DTI | — | ⏳ Informativo |
