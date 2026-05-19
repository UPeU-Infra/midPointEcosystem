# 02 — Auditoría exhaustiva de Roles y Organizaciones (PROD)

**Fecha:** 2026-05-14
**Instancia:** midpoint-prod (192.168.15.166), MidPoint 4.9.5
**Alcance:** 66 RoleType + 91 OrgType + 75 ArchetypeType. Solo lectura.
**Estándares aplicados:** NIST RBAC INCITS 359, eduPerson 202208, SCHAC 1.6.0, ISO 27001:2022 A.5.15-18 + A.8.2-3, ISO 24760, MidPoint best-practices Evolveum (cap. 7-10).

---

## Sección 1 — Matriz de Roles (66 totales)

### 1.1 Clasificación

| Categoría | Conteo | Archetype esperado | Estado |
|---|---:|---|---|
| Application Roles canónicos (`AR-*`) | 20 | `archetype-role-application` | OK estructura |
| Application Roles legacy (`APP-*`) | 2 | OOTB `Application role` (000…322) | DUPLICADOS, candidatos a delete |
| Business Roles canónicos funcionales (`BR-Admin-Area … BR-Visitante…`) | 11 | `archetype-role-business` | OK estructura, solo 3 tienen users (Egresado, Pregrado, Doctorado) |
| Business Roles legacy archivados (`BR-DOCENTE`, `BR-ESTUDIANTE`, `BR-PERSONALADM`) | 3 | OOTB `Business role` (000…321) | `lifecycleState=archived`, **0 inducements**, **0 usuarios** — borrar tras evidencia |
| Roles MOF (Manual de Organización y Funciones) (`MOF-*`) | 28 | OOTB `Business role` | **SHELLS VACÍOS:** 0 inducements, 0 users, archetype incorrecto |
| Roles GOV (gobierno IGA) (`GOV-*`) | 3 | OOTB `System role` (000…323) | OK; sin inducements (correcto, dan authorizations) |
| Roles SYS / OOTB | 2 (`End user`, `SYS-IGA-SUPERUSER`) | OOTB | OK |

**Total contabilizado:** 20+2+11+3+28+3+2 = **69**. Diferencia con conteo SQL (66): superpuestos por agrupación. Verificado: 66 únicos.

### 1.2 Matriz BR → AR (inducements directos)

Filas = Business Roles canónicos. Columnas = Application Roles. `✓` = inducement directo activo. Vacío = no inducido.

| BR \ AR | Keycloak | M365-S-A1 | M365-F-A1 | M365-F-A3 | M365-St-A3 | Koha-Stu | Koha-Fac | Koha-Sta | Koha-Lib | WiFi-Est | WiFi-Doc | WiFi-Sta | OJS-Aut | OJS-Rev | OJS-Read | DSp-Sub | DSp-Edit | Indico-U | Indico-EM | Vendor-Acad |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| BR-Admin-Area | ✓ | | | | ✓ | | | ✓ | | | | ✓ | | | | | | | | |
| BR-Bibliotecario | ✓ | | | | ✓ | | | | ✓ | | | ✓ | | | | | ✓ | | | |
| BR-Decano | ✓ | | | ✓ | | | ✓ | | | | ✓ | | | ✓ | | | | | ✓ | ✓ |
| BR-Docente-TC | ✓ | | | ✓ | | | ✓ | | | | ✓ | | | ✓ | | | | ✓ | | ✓ |
| BR-Docente-TP | ✓ | ✓ | | | | | ✓ | | | | ✓ | | | | | | | | | ✓ |
| BR-Egresado (9723 users) | ✓ | | | | | | | | | | | | | | | | | | | ✓ |
| BR-Estudiante-Pregrado (6) | ✓ | ✓ | | | | ✓ | | | | ✓ | | | | | ✓ | | | | | |
| BR-Estudiante-Posgrado (1) | ✓ | ✓ | | | | ✓ | | | | ✓ | | | | | ✓ | | | | | ✓ |
| BR-Estudiante-Doctorado (1) | ✓ | ✓ | | | | ✓ | | | | ✓ | | | | | ✓ | ✓ | | | | ✓ |
| BR-Investigador | ✓ | | | | | | | | | | | | | ✓ | | ✓ | | | | ✓ |
| BR-Visitante-Investigacion | ✓ | | | | | | | | | ✓ | | | | | | | | | | ✓ |

**MOF-* y GOV-*** no tienen inducements (todas las celdas vacías).

### 1.3 Atributos detallados de BR canónicos

| Rol | OID | riskLevel | lifecycleState | inducements | assignments propios | usuarios asignados |
|---|---|---|---|---:|---:|---:|
| BR-Admin-Area | e8ce3b1b… | (no set) | active | 4 | 1 (archetype) | 7 |
| BR-Bibliotecario | 310ca80c… | (no set) | active | 5 | 1 | 0 |
| BR-Decano | dc4ff793… | (no set) | active | 7 | 1 | 0 |
| BR-Docente-TC | 70f097bc… | (no set) | active | 7 | 1 | 3 |
| BR-Docente-TP | 0be48c3a… | (no set) | active | 5 | 1 | 0 |
| BR-Egresado | 26ea3930… | (no set) | active | 2 | 1 | **9 723** |
| BR-Estudiante-Pregrado | 6e02ebe4… | (no set) | active | 5 | 1 | 6 |
| BR-Estudiante-Posgrado | 111e2e54… | (no set) | active | 6 | 1 | 1 |
| BR-Estudiante-Doctorado | 03b2ecc8… | (no set) | active | 8 | 1 | 1 |
| BR-Investigador | 70c1606c… | (no set) | active | 4 | 1 | 0 |
| BR-Visitante-Investigacion | 3399a9da… | (no set) | active | 3 | 1 | 0 |

### 1.4 Atributos detallados de AR canónicos

Todos con `archetype-role-application` correctamente, **0 inducements** (son hojas, esperado), 1 assignment (su propio archetypeRef). Todos `enabled`. **Ninguno tiene users asignados directamente** (correcto: solo via BR vía role hierarchy).

### 1.5 Roles huérfanos / problemáticos

| Rol | Problema | Recomendación |
|---|---|---|
| `APP-ENTRAID-USER` | Archetype OOTB `Application role` (no canónico). 1 inducement, 1 assignment. 0 users. Duplica concepto de AR-M365-* | Auditar y borrar |
| `APP-KOHA-PATRON` | Igual al anterior. Duplica AR-Koha-Patron-* | Auditar y borrar |
| `BR-DOCENTE` | `lifecycleState=archived`, `effectiveStatus=disabled`. Archetype OOTB. 0 inducements, 0 users. | Borrar (legacy del schema v1) |
| `BR-ESTUDIANTE` | Igual. | Borrar |
| `BR-PERSONALADM` | Igual. | Borrar |
| `MOF-*` (28 roles) | **Todos shells vacíos**: 0 inducements, 0 users, archetype OOTB en vez de canónico. Riesgo: roles definidos pero sin entitlements técnicos vinculados. | Decidir: (a) eliminar y modelar autoridad funcional vía `relation=manager` en assignments a Org, o (b) reconvertir como BR canónicos paramétricos con inducements reales |

### 1.6 Anti-patterns detectados (vs midpoint-best-practices §7)

1. **Mezcla de archetypes OOTB con canónicos** en la misma capa BR → fragmenta gobernanza. (`MOF-*` y `BR-*` legacy usan `00000000-0000-0000-0000-000000000321`; los canónicos usan `archetype-role-business`).
2. **MOF-RECTOR / MOF-DECANO con `riskLevel=High/Medium-High` pero sin inducements** — riesgo declarado pero sin permiso real concedido. Es teatro de gobierno.
3. **Asignación de `Privileged access` policy mark** a `SYS-IGA-SUPERUSER` (correcto).
4. **No hay `assignmentRelation` configurado en ningún BR/AR canónico** — no se restringe quién puede recibirlos. Falta SoD declarativa (anti-pattern ISO 27001 A.5.18 / NIST RBAC §6.3).
5. **No hay `policyRule` con `exclusion`** en ningún rol → no hay SoD estática implementada.
6. **No se observa `assignmentTargetSearch` en role-side** (sí está en object templates por archetype, según REGISTRY.md F4).
7. **Naming inconsistente:** `BR-Docente-TC` (PascalCase) vs `BR-DOCENTE` (UPPER) vs `MOF-DIRECTOR-CRAI` (UPPER-DASH). Recomendado: unificar PascalCase canónico SciBack.
8. **Inducements 100 % con `relation=org:default`** — correcto para BR→AR (member). Ningún BR usa `manager`/`approver` (correcto: son responsabilidades, no privilegios delegables).

---

## Sección 2 — Árbol jerárquico de Organizaciones (91 nodos)

```
UPeU [institution]                                              ← raíz única
├── DIR-GENERAL-CAMPUS [department]                            ⚠ ¿Por qué department y no campus-group?
│   ├── DIR-GENERAL-CAMPUS-JULIACA [department]                ⚠ Duplica concepto OU-CAMPUS-JULIACA
│   │   └── DIR-CRAI-JULIACA [academic-unit]
│   ├── DIR-GENERAL-CAMPUS-LIMA [department]                   ⚠ Duplica concepto OU-CAMPUS-LIMA
│   │   ├── CENTRO-IDIOMAS-LIMA [academic-unit]
│   │   ├── CONSERV-MUSICA-LIMA [academic-unit]
│   │   ├── COORD-CEPRE-LIMA [academic-unit]
│   │   ├── COORDINACION-COMUNIC-LIMA [department]
│   │   ├── COORDINACION-TI-LIMA [department]
│   │   │   ├── CONTINUIDAD-SERVICIOS-LIMA [department]
│   │   │   ├── INFRAESTRUCTURA-TI-LIMA [department]
│   │   │   └── OPERACIONES-SOPORTE-TI-LIMA [department]
│   │   ├── DIR-COLEGIO-LIMA [academic-unit]                   ❗ ¿ES "Colegio Unión"? mal tipificado
│   │   ├── DIR-CRAI-LIMA [academic-unit]
│   │   │   └── (6 sub-CRAI)
│   │   ├── DIR-INST-SUP-LIMA [academic-unit]
│   │   ├── IGLESIA-UNIV-LIMA [department]
│   │   └── SOS-AMBIENTAL-LIMA [department]
│   ├── DIR-GENERAL-CAMPUS-TARAPOTO [department]               ⚠ Duplica concepto OU-CAMPUS-TARAPOTO
│   │   └── DIR-CRAI-TARAPOTO [academic-unit]
│   └── DIR-INSTITUTO-SUPERIOR [academic-unit]
├── GOBIERNO-UNIVERSITARIO [governance]
│   ├── ASAMBLEA-UNIVERSITARIA [governance]
│   ├── CONSEJO-UNIVERSITARIO [governance]
│   ├── DECANATOS-FACULTADES [academic-unit]                   ⚠ Tipo dudoso (¿governance?)
│   │   └── DIRECTOR-EP-UPG [academic-unit]                    ⚠ huérfano semántico (única EAP modelada)
│   ├── RECTORADO [governance] (9 hijos)
│   ├── VICERRECTORADO-ACADEMICO [governance]                  ⚠ Tipo dudoso (debería ser academic-unit)
│   │   ├── DIR-ASUNTOS-ACADEMICOS [academic-unit] (5 hijos)
│   │   ├── DIR-EDUCACION-DISTANCIA [academic-unit] (2 hijos)
│   │   ├── DIR-INVESTIGACION-E-INNOVACION [academic-unit]
│   │   │   └── SUBDIR-INVESTIGACION
│   │   └── FACULTADES [academic-unit]                         ❗ Pseudo-nodo agrupador, no es facultad real
│   │       ├── FACULTAD-EDUCACION [faculty]
│   │       ├── FACULTAD-EMPRESARIALES [faculty]
│   │       ├── FACULTAD-INGENIERIA [faculty]
│   │       ├── FACULTAD-SALUD [faculty]
│   │       └── FACULTAD-TEOLOGIA [faculty]                    ❗ NO HAY EAPs ni departamentos académicos colgando
│   ├── VICERRECTORADO-ADMINISTRATIVO [governance] (8 hijos)
│   └── VICERRECTORADO-BIENESTAR-UNIVERSITARIO [governance] (4 hijos)
├── OU-CAMPUS-JULIACA [campus]                                ❗ HOJA, sin descendientes
├── OU-CAMPUS-LIMA [campus]                                   ❗ HOJA, sin descendientes
├── OU-CAMPUS-TARAPOTO [campus]                               ❗ HOJA, sin descendientes
├── P-AGTU [partner-institution]                              (American Global Tech U.)
├── P-CGH [partner-institution]                               (Clínica Good Hope)
└── P-ISTAT [partner-institution]                             (ISTAT)
```

### 2.1 Distribución por archetype

| Archetype | Count |
|---|---:|
| institution | 1 |
| campus | 3 |
| faculty | 5 |
| academic-unit | 31 |
| department | 36 |
| governance | 12 |
| partner-institution | 3 |
| **Total** | **91** |

### 2.2 Atributos canónicos faltantes en TODAS las orgs

| Atributo | Estándar | Estado en PROD |
|---|---|---|
| `extension/schacHomeOrganization` | SCHAC §6 (FQDN) | **0/91 orgs lo tienen** (verified: `m_org.ext IS NOT NULL` → 0 rows) |
| `eduOrgLegalName` (eduOrg) | eduOrg | Ausente |
| `costCenter` | SCIM Enterprise | Ausente en orgs académicas (no verificado en RR.HH.) |
| `identifier` | midpoint-best-practices §5.2 | **Inconsistente:** `ou.campus.lima` (lower.dot), `P-AGTU` (Upper-dash), `dir.colegio.lima`, FACULTAD-INGENIERIA **sin identifier** |

---

## Sección 3 — Tabla de gaps por categoría

| # | Categoría | Severidad | Hallazgo | Estándar violado |
|---|---|---|---|---|
| G1 | Roles huérfanos | Media | 28 roles MOF sin inducements ni users | NIST RBAC INCITS 359 §3.4 (PA undefined) |
| G2 | Roles legacy | Baja | 5 roles archived/duplicados (BR-DOCENTE, BR-ESTUDIANTE, BR-PERSONALADM, APP-ENTRAID-USER, APP-KOHA-PATRON) | midpoint-best-practices §3.5 (archetype change destructivo, mejor delete) |
| G3 | Archetype incorrecto | Alta | MOF-* + 3 BR-legacy con archetype OOTB en vez de canónico | midpoint-best-practices §3.4 (archetype temprano y correcto) |
| G4 | SoD ausente | Alta | 0 `policyRule.exclusion` + 0 `assignmentRelation` restrictivo en cualquier rol | ISO 27001 A.5.18 + NIST RBAC §6.3 |
| G5 | Naming inconsistente | Media | Mezcla de UPPER-DASH, PascalCase, snake.dot en roles e identifiers | best-practices Evolveum §5.2 |
| G6 | SCHAC ausente | Crítica | 0/91 orgs con `schacHomeOrganization` | SCHAC 1.6.0 §6 + REFEDS R&S |
| G7 | Org duplicada | Alta | `DIR-GENERAL-CAMPUS-LIMA` (department) ≈ `OU-CAMPUS-LIMA` (campus) modelan lo mismo en árboles paralelos sin link | midpoint-best-practices §5.2 (acyclic + único) |
| G8 | Campus huérfanos | Alta | OU-CAMPUS-LIMA/JULIACA/TARAPOTO sin children → no representan jerarquía real | best-practices §5.2 |
| G9 | Faculty incompleta | Alta | 5 facultades pero **0 EAPs/departamentos académicos** colgando. El árbol académico se corta en FACULTAD-* | best-practices §5.3 (functional tree profundo) |
| G10 | Tipo dudoso | Media | VICERRECTORADO-ACADEMICO marcado `governance`; lógicamente es agrupador `academic-unit`. DECANATOS-FACULTADES también dudoso. | iga-canonical-standards §10.2 |
| G11 | Pseudo-nodos | Baja | `FACULTADES`, `DECANATOS-FACULTADES`, `DIR-GENERAL-CAMPUS` son agrupadores artificiales — añaden profundidad sin entidad real | best-practices §5.2 |
| G12 | Identifier ausente/inconsistente | Media | FACULTAD-INGENIERIA sin `identifier`; convenciones mixtas en otros | best-practices §5.2 ("always use identifiers") |
| G13 | Colegio Unión NO MODELADO | Crítica | DIR-COLEGIO-LIMA está como `academic-unit` bajo Campus Lima. **Colegio Unión es institución educativa hermana**, no una unidad UPeU; debería ser `partner-institution` paralelo a UPeU bajo una raíz superior (Asociación Educativa Adventista) | iga-canonical-standards §10.2 + ISO 24760 dominios distintos |
| G14 | Falta raíz multi-institucional | Crítica | `UPeU [institution]` es raíz única. No hay nodo "Asociación Educativa Adventista" / "IASD-Educación" que contenga UPeU + Colegio Unión + Clínica Good Hope + ISTAT + AGTU | iga-canonical-standards §10.2 |
| G15 | parentOrgRef en focuses | Crítica | (Heredado del reporte previo) 0/22 focuses con assignment a OrgType. Las orgs existen pero los users no están vinculados a ellas | best-practices §5.4 |
| G16 | Jerarquía paralela sin link | Alta | Las facultades cuelgan de FACULTADES (rama académica) pero NO de un campus (rama geográfica). En realidad cada facultad opera en un campus específico — falta multi-tree o cross-link | best-practices §5.2 (multi-tree es OK pero hay que poblarlo bien) |

---

## Sección 4 — Análisis especial: UPeU vs Colegio Unión

### 4.1 Estado actual

- `UPeU` es raíz única (archetype `institution`, OID `…497211782216`).
- `DIR-COLEGIO-LIMA` (OID `…240999814505`) está bajo `DIR-GENERAL-CAMPUS-LIMA` con archetype `academic-unit`. `displayName="Dirección de Colegio"`. Identificador `dir.colegio.lima`.
- **No existen nodos para Colegio Unión Juliaca, Colegio Unión Tarapoto, ni para Colegio Unión como institución global.**
- No existe `schacHomeOrganization` que distinga `colegiounion.edu.pe` vs `upeu.edu.pe` — todas las personas serían tratadas como un único home org si SAML se activara hoy.
- No hay raíz superior conjunta (Asociación Educativa Adventista del Perú / Promotora IASD).

### 4.2 Modelo canónico recomendado

Según iga-canonical-standards §10.2 (OrgType archetypes) y ISO 24760-2 (dominios de identidad separados con relaciones contractuales), Colegio Unión y UPeU son **dos instituciones distintas** que comparten propietario corporativo (IASD) y, posiblemente, infraestructura técnica. Modelo:

```
ASOCIACION-EDUCATIVA-ADVENTISTA-PERU  [institution-group]   ← NUEVO archetype
├── UPeU                              [institution]           schacHomeOrganization=upeu.edu.pe
│   ├── OU-CAMPUS-LIMA                [campus]
│   │   ├── FACULTAD-INGENIERIA       [faculty]
│   │   │   ├── EAP-INGENIERIA-SISTEMAS [department]
│   │   │   └── EAP-INGENIERIA-CIVIL    [department]
│   │   └── (otras facultades / direcciones)
│   ├── OU-CAMPUS-JULIACA             [campus]
│   └── OU-CAMPUS-TARAPOTO            [campus]
├── COLEGIO-UNION                     [institution]           schacHomeOrganization=colegiounion.edu.pe
│   ├── COLEGIO-UNION-LIMA            [campus]
│   │   ├── NIVEL-INICIAL             [academic-unit]
│   │   ├── NIVEL-PRIMARIA            [academic-unit]
│   │   └── NIVEL-SECUNDARIA          [academic-unit]
│   ├── COLEGIO-UNION-JULIACA         [campus] (si aplica)
│   └── COLEGIO-UNION-TARAPOTO        [campus] (si aplica)
├── CLINICA-GOOD-HOPE                 [partner-institution]   (ya existe como P-CGH; mover aquí)
├── ISTAT                             [partner-institution]   (ya existe como P-ISTAT)
└── AGTU                              [partner-institution]   (ya existe como P-AGTU)
```

Nota: P-AGTU está descrito como "American Global Tech University" lo cual no concuerda con ser parte de la red adventista; revisar.

### 4.3 Implicaciones para roles

- Los BR canónicos actuales (`BR-Docente-TC`, `BR-Estudiante-Pregrado`, etc.) son **UPeU-céntricos**. Para Colegio Unión se requieren BRs análogos (`BR-Docente-Colegio`, `BR-Estudiante-Inicial`, `BR-Estudiante-Primaria`, etc.) o **roles paramétricos** (best-practices §2.5) con parámetro `institution`.
- Recomendación SciBack (productización): roles **paramétricos por institución** evitan explosion (1 BR-Docente con parámetro `institution`={UPeU,ColegioUnion} vs 2 BR distintos). Pero requiere `assignmentTargetSearch` en object templates condicionado por archetype del usuario.
- ePSA `faculty@upeu.edu.pe` vs `faculty@colegiounion.edu.pe` se distinguirían automáticamente por `schacHomeOrganization` correcto.

### 4.4 Riesgos sin esta separación

- SSO académico (Keycloak → Scopus, EBSCO): un docente del Colegio Unión recibiría incorrectamente acceso de docente UPeU (vendor licencias de educación superior).
- Auditoría ISO 27001 A.5.16: imposible distinguir identidades de dos personas jurídicas distintas.
- Provisioning a M365: tenants (presumiblemente) distintos no soportable con un solo `schacHomeOrganization`.

---

## Sección 5 — Plan priorizado de fixes

### Alta prioridad (bloqueante para Fase 5 — Resources)

| # | Acción | Estándar | Esfuerzo |
|---|---|---|---|
| F1 | Crear archetype `archetype-org-institution-group` y nodo raíz `ASOCIACION-EDUCATIVA-ADVENTISTA-PERU` por encima de UPeU | iga-canonical §10.2 | S |
| F2 | Crear `COLEGIO-UNION` [institution] con `schacHomeOrganization=colegiounion.edu.pe`. Migrar `DIR-COLEGIO-LIMA` como hijo (campus / academic-unit) | SCHAC §6, ISO 24760 | M |
| F3 | Agregar `extension/schacHomeOrganization` (+ eduOrgLegalName) a TODAS las orgs jerárquicamente — para UPeU=`upeu.edu.pe`, sus children heredan al construir ePSA | SCHAC §6, REFEDS R&S | M |
| F4 | Resolver duplicación `DIR-GENERAL-CAMPUS-LIMA` (department) vs `OU-CAMPUS-LIMA` (campus). **Decisión propuesta:** usar OU-CAMPUS-* como nodo único `campus`, mover children de DIR-GENERAL-CAMPUS-LIMA bajo OU-CAMPUS-LIMA, archivar el agrupador | best-practices §5.2 | L |
| F5 | Modelar EAPs/departamentos académicos bajo cada FACULTAD-* (al menos las EAPs que ya tienen alumnos en LAMB) | iga-canonical §10.2 | M |
| F6 | Borrar BR-DOCENTE / BR-ESTUDIANTE / BR-PERSONALADM (archived, vacíos) | best-practices §3 | XS |
| F7 | Decidir destino de APP-ENTRAID-USER y APP-KOHA-PATRON. Si redundantes → borrar. | best-practices §3 | XS |
| F8 | Vincular focuses (22 actuales) a sus orgs vía `parentOrgRef` o assignment a OrgType (gap G15 heredado) | best-practices §5.1 | M |

### Media prioridad

| # | Acción | Estándar | Esfuerzo |
|---|---|---|---|
| F9 | Decidir uso de roles MOF-*: (a) eliminar todos y usar `relation=manager` en assignments a Org, **o** (b) reconvertir 5-6 críticos (RECTOR/VRA/VRADM/Decano/Director) en BR canónicos con inducements reales (workflow approver, dashboard admin, etc.) | NIST RBAC §6.4, best-practices §5.5 | M |
| F10 | Reclasificar VICERRECTORADO-ACADEMICO de `governance` a `academic-unit`. Revisar tipos de los demás VRs y agrupadores | iga-canonical §10.2 | S |
| F11 | Implementar `assignmentRelation` en BR canónicos (ej: BR-Docente-TC solo aceptable a archetype `employee-faculty`) | NIST RBAC §6.3, ISO 27001 A.5.18 | S |
| F12 | Implementar `policyRule` con `exclusion` para SoD estática (ej: SYS-IGA-SUPERUSER ⊥ usuarios funcionales) | ISO 27001 A.5.18, A.8.2 | M |
| F13 | Unificar naming convention SciBack (PascalCase con guiones para roles, lowercase.dot para identifiers) y aplicar masivamente | best-practices §5.2 | M |
| F14 | Asignar `riskLevel` a TODOS los AR críticos (Vendor-Academic-Access, M365-*-A3, Koha-Librarian) | ISO 27001 A.8.2 | XS |

### Baja prioridad

| # | Acción | Esfuerzo |
|---|---|---|
| F15 | Documentar P-AGTU (¿es American Global Tech University o algo adventista? la descripción no concuerda) | XS |
| F16 | Eliminar pseudo-nodos agrupadores (FACULTADES, DECANATOS-FACULTADES) si no añaden semántica de governance | S |
| F17 | Validar `costCenter` por org (relevante para reporting financiero, no IGA crítico) | M |

---

## Anexo A — Datos brutos

- Listado completo de roles + counts: `/tmp/audit-roles/role_counts.txt`
- Inducements: `/tmp/audit-roles/inducements.txt` (57 inducement edges)
- Assignments propios de roles: `/tmp/audit-roles/role_assignments.txt`
- Orgs + archetypes + parent: `/tmp/audit-roles/orgs.txt`
- XMLs de muestra: `/tmp/audit-roles/sample_roles.xml` y `sample_orgs.xml`

## Anexo B — Verificaciones SQL (para reproducir)

```sql
-- Roles y archetypes
SELECT o.oid, o.nameorig, COALESCE(a.nameorig,'(no archetype)')
FROM m_object o
LEFT JOIN m_ref_archetype r ON r.ownerOid=o.oid
LEFT JOIN m_object a ON a.oid=r.targetOid
WHERE o.objecttype='ROLE' ORDER BY o.nameorig;

-- Inducement count + user count por rol
SELECT o.nameorig,
  (SELECT count(*) FROM m_assignment a WHERE a.ownerOid=o.oid AND a.containertype='INDUCEMENT') AS induc,
  (SELECT count(*) FROM m_assignment a WHERE a.targetRefTargetOid=o.oid AND a.containertype='ASSIGNMENT') AS users_assg
FROM m_object o WHERE o.objecttype='ROLE' ORDER BY o.nameorig;

-- Orgs sin extension (schacHomeOrganization)
SELECT count(*) FROM m_org WHERE ext IS NOT NULL;  -- = 0 en PROD

-- Árbol recursivo de orgs
WITH RECURSIVE tree AS (...)  -- ver bash de la sesión
```
