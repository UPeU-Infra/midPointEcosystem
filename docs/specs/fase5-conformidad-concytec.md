# Fase 5 — Análisis de conformidad CONCYTEC + propuesta de revisión del modelo canónico de investigación

> **Estado:** ANÁLISIS Y PROPUESTA. **NO APLICADO a PROD.** Los XML incluidos son
> **borradores de propuesta** — no importar hasta aprobación del usuario.
> **Fecha:** 2026-06-17 · **Autor:** midpoint-expert · **Skills:** `iga-canonical-standards`, `midpoint-best-practices`
>
> ⚠️ Durante la redacción de este documento corría un **barrido masivo de 970 focos dual** en
> PROD. **No se escribió a PROD, no se importó, no se cambió lifecycle, no se recomputó.**
> La inspección de PROD fue read-only (de hecho, ninguna fue necesaria: todo se resolvió
> contra el repo). La sonda a **Oracle LAMB fue 100% de solo lectura** (`SELECT`/metadata
> `ALL_TABLES`/`ALL_TAB_COLUMNS`); cero DML/DDL. El resource CRIS sigue `proposed`.

---

## 0. Resumen ejecutivo (TL;DR para el usuario)

1. **El "Grupo de Investigación" NO existe en Oracle LAMB.** No hay `DGI_GRUPO` ni
   `DGI_GRUPO_INVESTIGADOR` (sonda confirmada). Lo que LAMB modela es **proyecto/tesis**
   (`DGI_INVESTIGACION`, 2.468 filas, 1,83 investigadores/proyecto en promedio) y la cadena
   investigador→proyecto→línea→centro. **El Grupo es exactamente la capa que MidPoint debe
   MATERIALIZAR y GOBERNAR**, alineado a la visión "MidPoint = SSOT que fusiona LAMB +
   gobierna lo que la fuente no tiene". Es el caso de uso canónico de Reality vs Policy.

2. **El modelo Fase 5 actual incumple la norma CONCYTEC en la jerarquía de afiliación:**
   afilia `persona → Centro` directo, saltándose el Grupo. La norma exige
   `persona → Grupo → Centro`. **GAP confirmado (A).**

3. **Falta la capa Área de investigación (GAP B)** y la **categorización de madurez
   Consolidado/Por consolidar/Emergente (GAP C)** — ninguna de las dos está en LAMB.

4. **Propuesta:** 2 archetypes nuevos (`org-research-group`, `org-research-area`),
   gobierno manual del Grupo en MidPoint (curado por la DGI/VRI), reusar el árbol
   Academic-Program existente para el vínculo Área↔programa, y capturar la madurez en
   **schema** (un solo item de extensión nuevo, justificado). Instituto y Red se difieren
   (no existen aún en UPeU) pero se reservan archetype-slots para SciBack.

---

## 1. Sonda READ-ONLY a Oracle LAMB — catálogo real (schema ESTHER)

Método: `arch -x86_64 /usr/bin/python3` + `oracledb` thick (`lib_dir=/opt/homebrew/lib`,
Instant Client 19.8 x86 vía Rosetta — thin falla con Oracle 11g DPY-3010).
Credenciales `~/.secrets/oracle-lamb.env` (`JUANSANCHEZ`, rol read-only).

### 1.1 ¿Existe tabla de GRUPOS de investigación?

**NO.** Búsqueda en `ALL_TABLES` con `LIKE '%GRUPO%'` (todos los schemas): 63 tablas, **ninguna
en ESTHER** y ninguna relacionada a investigación (son grupos focales/contables/planilla/
WhatsApp/eventos). En ESTHER no hay `DGI_GRUPO*`. **El Grupo de Investigación no está en la fuente.**

### 1.2 Tablas DGI_* de investigación relevantes (las 68 DGI_* — extracto pertinente)

| Tabla ESTHER | Filas (activas) | Rol real |
|---|---|---|
| `DGI_CENTRO_INVESTIGACION` | 7 | **Centro CII.** Cols: `ID_CENTRO_INVESTIGACION, NOMBRE, CODIGO, ESTADO`. **Sin columna de categoría/madurez.** |
| `DGI_LINEA_INVESTIGACION` | 178 | **Línea.** FK `ID_CENTRO_INVESTIGACION`. Cols extra útiles: `OBJETIVO, AREA_DESARROLLO`. **Sin categoría/madurez.** |
| `DGI_LINEA_PROGRAMA` | 657 | **Vínculo Línea↔Programa de estudio** (`ID_LINEA_INVESTIGACION` ↔ `ID_PROGRAMA_ESTUDIO`). 141 líneas mapean a 167 programas. **Esta es la relación que la norma CONCYTEC exige (área/línea ↔ programa de estudio).** |
| `DGI_INVESTIGACION` | 2.468 | **Proyecto / trabajo de investigación / tesis** (TITULO = títulos individuales de tesis/artículos). FK `ID_PROGRAMA_ESTUDIO, ID_PERSONA, ID_DEPTO, ID_ENTIDAD`. **NO es un grupo.** |
| `DGI_INVESTIGADOR` | 4.097 personas distintas | **Persona ↔ proyecto** (`ID_PERSONA, ID_INVESTIGACION, ID_PROGRAMA_ESTUDIO, CICLO, FINALIZO`). Promedio 1,83 investigadores/proyecto. |
| `DGI_INVESTIGACION_LINEA` | — | Proyecto ↔ línea (vía `ID_LINEA_PROGRAMA`). |
| `DGI_PERFIL` | 290 con ORCID | Perfil del investigador: `ID_PERSONA, ORCID, URL_FOTO`. **IIA del ORCID.** |
| `DGI_TIPO_CATEGORIA` | 4 | **Falso amigo:** NO es madurez de grupo. Son niveles de estudio (Pregrado/Maestría/Doctorado/2da Esp.) con `ID_TIPO_CONTRATO, MAX_CUPO`. Categoriza al *investigador por nivel*, no al grupo. |

### 1.3 ¿Categorización de líneas/grupos (Consolidado/Por consolidar/Emergente)?

**NO existe en LAMB.** Ninguna columna `CATEGORIA`/`MADUREZ`/`CONSOLIDA*` en `DGI_CENTRO_*`
ni `DGI_LINEA_*`. La única tabla `CATEGORIA` (`DGI_TIPO_CATEGORIA`) es de niveles de estudio.
→ **La madurez debe gobernarse en MidPoint** (no hay fuente).

### 1.4 ¿Vínculo Área↔programa de estudio?

**Parcial — vía línea, no vía "área".** LAMB **no tiene entidad "Área de investigación"**: la
jerarquía LAMB es `Centro → Línea`. El vínculo a programas existe en `DGI_LINEA_PROGRAMA`
(`Línea ↔ ID_PROGRAMA_ESTUDIO`) y `DGI_PROGRAMA_SEDEAREA`. El `ID_PROGRAMA_ESTUDIO` **es el
mismo identificador** que alimenta los OrgType `archetype-org-academic-program` ya en PROD.
→ **El Área se gobierna en MidPoint; su vínculo a programas se deriva de `DGI_LINEA_PROGRAMA`.**

### 1.5 Conclusión de la sonda

| Pregunta | Respuesta |
|---|---|
| ¿Grupo en LAMB? | **NO** → materializar+gobernar en MidPoint |
| ¿Madurez en LAMB? | **NO** → gobernar en MidPoint (schema) |
| ¿Área como entidad en LAMB? | **NO** (solo Centro→Línea) → gobernar en MidPoint |
| ¿Línea↔programa en LAMB? | **SÍ** (`DGI_LINEA_PROGRAMA`, 657) → derivable |
| ¿Persona↔proyecto↔línea↔centro? | **SÍ** (cadena ya usada por `investigadores-afiliacion.xml`) |
| ¿ORCID? | **SÍ** (`DGI_PERFIL`, 290) |

Esto **valida la visión del usuario**: MidPoint fusiona lo que LAMB aporta (centros, líneas,
proyectos, investigadores, ORCID, línea↔programa) y **materializa/gobierna las capas que la
norma CONCYTEC exige y la fuente no tiene: Grupo, Área y Madurez.**

---

## 2. Matriz de conformidad — modelo Fase 5 actual ↔ Guía CONCYTEC

Leyenda: ✅ CUMPLE · ⚠️ GAP · ⛔ AUSENTE · N-A no aplica todavía.

| # | Entidad / requisito CONCYTEC | Norma (cita) | Modelo Fase 5 actual | Estado |
|---|---|---|---|---|
| 1 | **VRI / "quien haga sus veces"** constituye/categoriza/evalúa grupos | Guía 2020 §GI: "Vicerrectorado de Investigación o quien haga sus veces" | DGI (`identifier=69`) cuelga del VR Académico y **hace las veces del VRI** | ✅ (decisión documentada; ver §6 decisión D1) |
| 2 | **Centro de Investigación** = ≥2 grupos consolidados; depende del VRI | Guía 2020 §CI | 7 Centros CII como OrgType bajo DGI (`archetype-org-research-center` → `#unidadDeInvestigacionOInnovacion`) | ✅ estructura · ⚠️ la regla "≥2 grupos consolidados" no es verificable hasta tener Grupos |
| 3 | **Grupo de Investigación** = UNIDAD BÁSICA; persona pertenece al grupo; coordinador único; ≥1 titular Dr/Mg + ≥1 colaborador | Guía 2020 §GI (núcleo de la norma) | **AUSENTE.** No hay capa Grupo; el 3er valor del vocab `#grupoDeInvestigacion` **no se usa**. Afiliación es `persona→Centro` directa | ⛔ **GAP A (crítico)** |
| 4 | **Afiliación jerárquica** persona → Grupo → Centro | Guía 2020 §GI/§CI | `investigadores-afiliacion.xml` afilia **persona → Centro** (salta el Grupo) | ⚠️ **GAP A** |
| 5 | **Área de investigación**, vinculada a programas de estudio; de ella derivan líneas | Guía 2019 (RP 115-2019) §Área; Guía 2020 §Área | **AUSENTE.** Jerarquía actual = Centro→Línea, sin Área. Vínculo a programa no modelado | ⛔ **GAP B** |
| 6 | **Línea de investigación**, dentro de Área, eje temático | Guía 2019/2020 §Línea | 178 líneas como OrgType (`archetype-org-research-line` → `#lineaDeInvestigacion`), hijas de Centro | ✅ entidad · ⚠️ cuelga de Centro, no de Área (ver §3) |
| 7 | **Categorización de madurez** Grupos y Líneas: Consolidado / Por consolidar / Emergente | Guía 2020 §Categorización; Guía 2019 §Categorización | **AUSENTE** (no capturado en ningún sitio) | ⛔ **GAP C** |
| 8 | **Instituto de Investigación** (evolución/fusión de centros) | Guía 2020 §Instituto | No existe en UPeU ni en LAMB | N-A (reservar archetype, §3.4) |
| 9 | **Red de Investigación** (3+ instituciones) | Guía 2020 §Red | No existe en UPeU ni en LAMB | N-A (reservar archetype, §3.4) |
| 10 | **Evaluación periódica** (grupos 2 años, centros 3, institutos 5) | Guía 2020 §Evaluación | No capturado (fecha de última categorización/evaluación) | ⚠️ menor — se cubre con metadata de la madurez (§3.5) |
| 11 | **Todos los integrantes en CTI-Vitae/RENACYT + ORCID** | Guía 2020 §GI | ORCID se provisiona a CRIS (`person.identifier.orcid` desde `DGI_PERFIL`); RENACYT no modelado como flag de persona | ⚠️ menor (ver §5.4 reconciliación 16 grupos RENACYT) |
| 12 | **Registro ante CONCYTEC** del grupo | Guía 2020 §GI | N-A en MidPoint (trámite externo); pero el código RENACYT del grupo debe persistirse | ⚠️ se cubre con `identifier` del Grupo (§3.5) |

**Resumen:** estructura Centro/Línea ✅, pero **3 GAPs estructurales** (A Grupo, B Área,
C Madurez) y ajustes menores de jerarquía y metadata.

---

## 3. Propuesta de revisión del modelo canónico (MidPoint-as-SSOT)

Principio rector aplicado (`midpoint-best-practices` §1, §5; `iga-canonical-standards` §10):
**org tree = assignments; jerarquía vía `parentOrgRef`; archetype solo tipifica; identifier
inmutable separado del name; Reality(LAMB)+Policy(gobierno MidPoint) fusionados.**

### 3.1 Jerarquía OrgType propuesta (árbol de investigación canónico)

```
UPeU (institution)
└── DGI  (hace las veces del VRI)            [archetype-org-research-center #unidadDeInnovacion]  identifier=69
    └── Centro CII  (×7)                     [archetype-org-research-center #unidadDeInnovacion]  identifier=CII-{id}
        └── Grupo de Investigación (GI) ★    [archetype-org-research-group  #grupoDeInvestigacion] identifier=GI-{codRenacyt|slug}
            └── (la GI ABORDA 1..n Líneas, ver 3.3)

  Áreas de investigación  ★ (eje temático general, vinculado a programas)
  └── Área (×n)                              [archetype-org-research-area]  identifier=AREA-{id}
      └── Línea de investigación (×178)      [archetype-org-research-line  #lineaDeInvestigacion] identifier=LINEA-{id}
```

**Cambios clave frente al modelo actual:**

- **(A) Se inserta el Grupo entre Centro y la afiliación de personas.** La persona ya **NO**
  cuelga del Centro: cuelga del **Grupo**, y el Grupo cuelga del Centro. Así
  `persona → Grupo → Centro` queda materializada vía `parentOrgRef` (cadena de assignments).

- **(B) La Línea pasa a colgar del Área**, no del Centro (la norma dice "de un Área derivan
  líneas"). El Centro agrupa Grupos; el Área agrupa Líneas. Son **dos ejes** (igual que
  functional vs project en `midpoint-best-practices` §5.2): el eje **orgánico**
  (Centro→Grupo→persona) y el eje **temático** (Área→Línea). Un Grupo **aborda** líneas
  mediante assignment cruzado (relation `org:default`), sin que la Línea sea su parent
  estructural. Esto evita un grafo con multiparent forzado y respeta el DAG acíclico.

  > **Decisión abierta D3 (ver §6):** alternativa más conservadora = mantener Línea bajo
  > Centro (como hoy) y modelar el Área como **agrupador temático paralelo** que referencia
  > las líneas. Recomendado el eje temático separado, pero requiere visto bueno.

### 3.2 Archetypes — inventario propuesto

| Archetype | OID candidato (libre en repo, verificado) | tiposubunidad PerúCRIS | Estado |
|---|---|---|---|
| `archetype-org-research-center` | `6b1d9a4e-2f53-4c8a-bf17-9d0c6e2a4b81` | `#unidadDeInvestigacionOInnovacion` | **EXISTE** (sin cambios) |
| `archetype-org-research-line` | `7c2e0b5f-3a64-4d9b-c028-ae1d7f3b5c92` | `#lineaDeInvestigacion` | **EXISTE** (re-parent a Área, sin cambio de archetype) |
| `archetype-org-research-group` ★ | `8a3f2c1d-1b4e-4f6a-9c2d-3e7b5a9f1c80` | `#grupoDeInvestigacion` | **NUEVO** |
| `archetype-org-research-area` ★ | `9b4e3d2c-2c5f-4a7b-8d3e-4f8c6b0a2d91` | *(sin tiposubunidad; o `#unidad...` — decisión D4)* | **NUEVO** |
| `archetype-org-research-institute` | `a0c5f4e3-3d6a-4b8c-9e4f-5a9d7c1b3e02` | `#unidadDeInvestigacionOInnovacion` | **RESERVADO** (no crear hoy; N-A UPeU) |
| `archetype-org-research-network` | `b1d6a5f4-4e7b-4c9d-af50-6bae8d2c4f13` | *(decisión)* | **RESERVADO** (no crear hoy; N-A UPeU) |

> Los OIDs de Instituto/Red se **reservan en este doc** para SciBack pero **NO se crean**
> hasta que exista la entidad (evita orgs vacías sin fuente). Verificado: los 4 OIDs nuevos
> no aparecen en ningún XML del repo.

#### Borrador `archetype-org-research-group` (PROPUESTA — NO APLICAR)

```xml
<archetype xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
           oid="8a3f2c1d-1b4e-4f6a-9c2d-3e7b5a9f1c80">
    <name>archetype-org-research-group</name>
    <description>Grupo de Investigación (GI) — UNIDAD BÁSICA de organización de I+D
      (CONCYTEC Guía 2020). OrgType hijo de un Centro CII. Mapea a PerúCRIS
      perucris.orgunit.tiposubunidad #grupoDeInvestigacion (3er valor del vocab).
      GOBERNADO EN MIDPOINT (no existe en Oracle LAMB): MidPoint es SSOT y materializa
      esta capa. Los investigadores se afilian al Grupo (assignment relation org:default);
      el Grupo cuelga de su Centro (parentOrgRef). El coordinador se modela como
      assignment con relation org:manager. El archetype solo tipifica.
      iga-canonical-standards §10.2.</description>
    <lifecycleState>active</lifecycleState>
    <assignment>
        <assignmentRelation><holderType>OrgType</holderType></assignmentRelation>
    </assignment>
    <archetypePolicy>
        <display>
            <label>Grupo de Investigación</label>
            <pluralLabel>Grupos de Investigación</pluralLabel>
            <icon><cssClass>fa fa-users</cssClass><color>#2980b9</color></icon>
        </display>
    </archetypePolicy>
</archetype>
```

#### Borrador `archetype-org-research-area` (PROPUESTA — NO APLICAR)

```xml
<archetype xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
           oid="9b4e3d2c-2c5f-4a7b-8d3e-4f8c6b0a2d91">
    <name>archetype-org-research-area</name>
    <description>Área de Investigación — unidad temática general del conocimiento
      (CONCYTEC Guía 2019 RP 115-2019). De un Área derivan Líneas; el Área se vincula
      con los programas de estudio (eje temático, paralelo al eje orgánico Centro→Grupo).
      GOBERNADO EN MIDPOINT (no existe como entidad en Oracle LAMB; el vínculo
      línea↔programa se deriva de ESTHER.DGI_LINEA_PROGRAMA). El archetype solo tipifica.
      iga-canonical-standards §10.2.</description>
    <lifecycleState>active</lifecycleState>
    <assignment>
        <assignmentRelation><holderType>OrgType</holderType></assignmentRelation>
    </assignment>
    <archetypePolicy>
        <display>
            <label>Área de Investigación</label>
            <pluralLabel>Áreas de Investigación</pluralLabel>
            <icon><cssClass>fa fa-sitemap</cssClass><color>#8e44ad</color></icon>
        </display>
    </archetypePolicy>
</archetype>
```

### 3.3 Regla de FUSIÓN: cómo MidPoint materializa Grupos (núcleo de la propuesta)

El Grupo no tiene fuente. Tres estrategias, de menor a mayor automatización:

**Opción 1 — Gobierno 100% manual (RECOMENDADA para arranque).**
- Los **16 "grupos" RENACYT** que ya existen en el CRIS (hoy mal colgados de carreras) se
  **curan a mano** como OrgType `archetype-org-research-group` bajo su Centro CII correcto.
  Identifier = `GI-{codRenacyt}` (código RENACYT del grupo = identificador persistente y
  registrable ante CONCYTEC, regla de oro §10).
- La membresía persona→Grupo la asigna la DGI/VRI vía request/asignación en MidPoint.
- Pro: cumple la norma de inmediato, 16 grupos es manejable, el VRI **gobierna** (que es
  exactamente lo que la norma manda: "constituido/categorizado por el VRI").
- Contra: el alta de miembros no es automática.

**Opción 2 — Derivación asistida desde proyecto (`DGI_INVESTIGACION`).**
- Un proyecto NO es un grupo, pero la **co-participación recurrente** de investigadores en
  proyectos de las **mismas líneas** es señal de grupo. Se puede generar un **reporte
  candidato** (role-mining-like) que sugiera composición de grupos; el VRI aprueba.
- Pro: acelera el poblamiento. Contra: heurístico, requiere validación humana (no
  automatizar el alta — `iga-canonical-standards` regla "MidPoint suma, nunca resta").

**Opción 3 — Híbrida (RECOMENDADA a régimen).**
- El **catálogo de Grupos** (qué grupos hay, su Centro, su madurez, su coordinador) se
  **gobierna manual** en MidPoint (Opción 1) — es policy puro, no hay fuente.
- La **afiliación persona→Grupo** se **fusiona**: si LAMB declara a la persona como
  investigador (`DGI_INVESTIGADOR`) **de una línea que el grupo aborda**, MidPoint
  **propone** la membresía; el VRI confirma. La afiliación persona→**Centro** (lo que hoy
  hace `investigadores-afiliacion.xml`) se **degrada a derivada del Grupo**: ya no se asigna
  el Centro directo; el Centro se obtiene por `parentOrgRef` del Grupo.

> **Refactor del inbound `investigadores-afiliacion.xml`:** en vez de
> `persona → assignment(Centro CII)`, pasa a `persona → assignment(Grupo)` **solo cuando la
> persona ya está asignada a un grupo gobernado**; mientras no haya grupo, queda como
> afiliación de investigación "sin grupo" (estado transitorio) o se mantiene la afiliación
> a línea. La pertenencia al Centro deja de ser un assignment directo. **Decisión D2.**

### 3.4 Instituto y Red

No existen en UPeU ni en LAMB. **No se crean archetypes hoy.** Se reservan OIDs (§3.2) y se
documenta el patrón para SciBack: Instituto = `parentOrgRef` DGI, agrupa Centros; Red =
org transversal (como `project`) con `assignmentRelation` a OrgType de 3+ instituciones.

### 3.5 Categorización de madurez + metadata de evaluación (GAP C)

No hay fuente → **gobierno en MidPoint**. **Schema is the law**: antes de extender se buscó
en core. No hay item core para "nivel de madurez de unidad de investigación". Se propone
**un único item nuevo** en `OrgExtensionType` (justificación fuerte: concepto regulatorio
CONCYTEC sin equivalente core ni eduPerson/SCHAC), con **vocabulario controlado**:

```xml
<!-- PROPUESTA — agregar a OrgExtensionType en upeu-local-v1.0.xml. NO APLICAR. -->
<xsd:element name="researchMaturity" type="xsd:string" minOccurs="0" maxOccurs="1">
    <xsd:annotation><xsd:appinfo>
        <a:displayName>Categoría de madurez (CONCYTEC)</a:displayName>
        <a:help>Madurez de Grupo o Línea (CONCYTEC Guía 2020): consolidado |
          por-consolidar | emergente. Gobernado en MidPoint (no existe en LAMB).</a:help>
        <a:indexed>true</a:indexed>
    </xsd:appinfo></xsd:annotation>
</xsd:element>
```

- **¿Por qué schema y no solo metadata?** Es un atributo de negocio consultable/filtrable
  (informes CONCYTEC, "centros con ≥2 grupos consolidados"), no un dato de auditoría →
  va en `extension`, indexed, no en `metadata`.
- **Fechas de evaluación** (req. 10: grupos/2a, centros/3a): se cubren con la
  `metadata` nativa (`modifyTimestamp`) **o**, si se requiere fecha explícita de
  categorización, un 2º item `researchMaturityDate` (`xsd:dateTime`). **Decisión D5** —
  recomendado empezar solo con `researchMaturity` y añadir la fecha si Auditoría lo pide.
- **Reusabilidad SciBack:** `researchMaturity` es canónico CONCYTEC → aunque vive en el
  overlay `urn:upeu:midpoint:local` hoy, debe **promoverse al schema canónico**
  `urn:sciback:midpoint:research` en el blueprint (es norma nacional, no dato UPeU).
  **Decisión D6.**

### 3.6 Vínculo Área ↔ Academic-Program (GAP B, reuso de schema existente)

**Cero extensiones nuevas.** El `ID_PROGRAMA_ESTUDIO` de `DGI_LINEA_PROGRAMA` es el mismo
que identifica los OrgType `archetype-org-academic-program` ya en PROD. Se modela como
**assignment cruzado**: la Línea (o el Área) → assignment al OrgType Academic-Program con
**relation dedicada** (p.ej. `org:related` o un relation custom `relatedProgram`) para no
confundirlo con la jerarquía estructural. **Decisión D7** sobre el relation. El inbound que
lo deriva lee `DGI_LINEA_PROGRAMA` (nuevo objectType en el resource de investigación, o un
resource hermano), correlacionando Línea por `identifier=LINEA-{id}` y Programa por su
identifier de programa.

---

## 4. Impacto en el outbound PerúCRIS (`cris-dspace.xml`)

| Aspecto | Hoy | Con la propuesta |
|---|---|---|
| `dspace.entity.type` (single-value) | OrgUnit / Person | sin cambio |
| `perucris.orgunit.tiposubunidad` | emite `#unidadDeInvestigacionOInnovacion` (DGI+Centros) y `#lineaDeInvestigacion` (líneas) | **+ `#grupoDeInvestigacion`** para los OrgType con `archetype-org-research-group`. El 3er valor del vocab por fin se usa. El mapping outbound debe ramificar por archetype (igual patrón que ya tiene). Área → sin tiposubunidad (o `#unidad...`, D4). |
| `organization.parentOrganization` (jerarquía CERIF) | Centro→DGI, Línea→Centro | Centro→DGI, **Grupo→Centro**, Línea→**Área**, Área→DGI (o raíz). La jerarquía CRIS se deriva de `parentOrgRef`, así que sigue automática. |
| Afiliación CERIF Person↔OrgUnit `relationshipType=5` place 0 | persona↔Centro (place 0 = dependencia laboral) | **place 0 sigue siendo la dependencia laboral** (área de RR.HH., NO investigación). La afiliación de investigación persona↔**Grupo** se emite como relación CERIF adicional (place ≥1), no como place 0. Esto **ya es correcto** en el contrato actual; solo cambia el OrgUnit destino (Grupo en vez de Centro). |
| 16 grupos RENACYT en CRIS (mal colgados de carreras) | provisioning no los toca | **se reconcilian** (§5.4): re-parent al Centro CII, archetype Grupo, upsert idempotente por `organization.legalName`/uuid en shadow. |

**No se requiere romper el contrato PerúCRIS** — el outbound ya soporta tiposubunidad por
valor; solo se añade la rama del 3er valor y se cambia el destino de la afiliación de
investigación a Grupo.

---

## 5. Reconciliación de los 16 grupos RENACYT del CRIS

1. **Inventariar** (read-only en CRIS, post-barrido): los 16 OrgUnit "grupo" + su carrera padre actual + código RENACYT.
2. **Mapear** cada grupo → su **Centro CII** correcto (por línea/facultad). Curación DGI/VRI.
3. **Materializar en MidPoint** 16 OrgType `archetype-org-research-group`, `identifier=GI-{codRenacyt}`, `parentOrgRef=Centro CII`.
4. **Upsert idempotente al CRIS**: el outbound busca por `organization.legalName`; al re-provisionar con `parentOrganization=Centro`, el grupo queda colgado del Centro (no de la carrera). El shadow guarda el uuid DSpace → idempotente.
5. **Re-afiliar** las 97 Person del CRIS: las que sean miembros de un grupo → relación CERIF a su Grupo.

> Esto es **post-barrido** y requiere lectura del CRIS (no hecha aquí; el resource sigue `proposed`).

---

## 6. Decisiones que requieren al usuario

| ID | Decisión | Recomendación midpoint-expert |
|---|---|---|
| **D1** | ¿DGI hace las veces del VRI de forma permanente, o se creará un OrgType VRI propio cuando exista en LAMB? | Mantener DGI como VRI funcional; documentar; crear VRI solo si LAMB lo modela. |
| **D2** | Afiliación de investigación: ¿persona→**Grupo** (y Centro derivado) reemplaza el actual persona→Centro directo? | **Sí.** Refactor `investigadores-afiliacion.xml` a persona→Grupo; Centro por `parentOrgRef`. |
| **D3** | Línea: ¿re-parent a **Área** (eje temático) o se queda bajo Centro? | Eje temático Área→Línea (cumple norma); Centro→Grupo separado. Conservador: dejar Línea bajo Centro y Área como agrupador paralelo. |
| **D4** | `archetype-org-research-area`: ¿emite `tiposubunidad` a PerúCRIS o queda sin emitir? | Sin tiposubunidad (el vocab solo tiene 3 valores: unidad/línea/grupo; "área" no es uno). |
| **D5** | Madurez: ¿solo `researchMaturity`, o también `researchMaturityDate` para evaluación periódica? | Empezar solo con `researchMaturity`; añadir fecha si Auditoría/VRI lo pide. |
| **D6** | ¿`researchMaturity` se promueve al schema **canónico SciBack** (norma nacional) o queda en overlay UPeU? | Promover a canónico (`urn:sciback:midpoint:research`); es CONCYTEC, no UPeU. |
| **D7** | Relation para el vínculo Línea/Área↔Academic-Program | `org:related` (o relation custom `relatedProgram`), NO `org:default` (no es jerarquía). |
| **D8** | Poblamiento de Grupos: ¿Opción 1 (manual), 2 (derivado), o 3 (híbrida)? | **Opción 3** a régimen; arrancar con **Opción 1** (16 RENACYT curados). |
| **D9** | Instituto/Red: ¿crear archetypes ahora (vacíos) o reservar OIDs hasta que existan? | **Reservar OIDs** (en este doc); no crear orgs vacías sin fuente. |

---

## 7. Plan de implementación post-barrido (orden, SIN ejecutar)

> Nada de esto se ejecuta hasta: (a) terminar el barrido de 970 focos dual, y
> (b) aprobación de las decisiones §6.

1. **Schema** (`upeu-local-v1.0.xml` o canónico SciBack según D6): añadir `researchMaturity`.
   Import vía REST/UI (objeto en repo, no XSD físico). Recompute no requerido (item nuevo).
2. **Archetypes nuevos** (2): `org-research-group`, `org-research-area`. Import. Verificar `GET` por OID.
3. **Re-parent de Líneas** (si D3 = eje temático): generar Áreas (gobierno manual + derivación de `DGI_LINEA_PROGRAMA`), re-asignar `parentOrgRef` de las 178 líneas. Backup git tag + verificación de DAG acíclico.
4. **Materializar 16 Grupos RENACYT** (Opción 1): OrgType manual `GI-{codRenacyt}` bajo su Centro.
5. **Refactor `investigadores-afiliacion.xml`** (D2): destino del assignment = Grupo en vez de Centro. Re-validar recon en `proposed` antes de activar.
6. **Vínculo Área↔Programa** (D7): nuevo objectType/resource inbound desde `DGI_LINEA_PROGRAMA`, relation `org:related`.
7. **Outbound CRIS**: añadir rama `#grupoDeInvestigacion`; cambiar destino de afiliación de investigación a Grupo. Reconciliar los 16 grupos del CRIS (§5).
8. **Madurez**: cargar `researchMaturity` de los grupos/líneas conocidos (curación DGI/VRI).
9. **Smoke test**: piloto Charming (29266) + 1 grupo RENACYT + 1 línea con programa; verificar jerarquía CRIS, tiposubunidad y afiliación CERIF.

Cada paso: backup (tag git), validate antes de import, lifecycle `proposed`→`active` solo
tras verificación. **GitOps**: todo al repo → push → `git pull` en PROD → reaplicar selectivo
vía REST. Nunca `scp`.

---

## 8. Confirmaciones de seguridad

- ✅ **NO se escribió a PROD** (sin import, sin recompute, sin cambio de lifecycle, sin restart). El resource CRIS sigue `proposed`.
- ✅ **Oracle LAMB: solo lectura** (únicamente `SELECT` y consultas a `ALL_TABLES`/`ALL_TAB_COLUMNS`). Cero INSERT/UPDATE/DELETE/DDL.
- ✅ **No se implementaron XMLs definitivos.** Los XML de §3 son **borradores de propuesta** embebidos en este doc; no se crearon archivos en `canonical/`/`upeu/`.
- ✅ Skills consultadas antes de proponer: `iga-canonical-standards` (§10 OrgType archetypes, reglas de oro), `midpoint-best-practices` (§5 org structures, assignment vs inducement, identifier inmutable).
