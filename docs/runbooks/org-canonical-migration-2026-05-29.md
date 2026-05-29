# Runbook — Migración a Org tree canónico único

Fecha: 2026-05-29
Autor: midpoint-expert
Estado: **EJECUCIÓN EN CURSO — ver ADDENDUM DE EJECUCIÓN al final (estrategia revisada por hallazgos en PROD).**

> **IMPORTANTE:** El cuerpo del runbook (§0-§8) es el DISEÑO original. Durante la ejecución
> (2026-05-29) la inspección de PROD reveló una realidad distinta de la asumida, que CAMBIA la
> estrategia. La estrategia ejecutada está en el **ADDENDUM DE EJECUCIÓN** (final del documento).
> El cuerpo original se conserva para trazabilidad.
Servidor: PROD `192.168.15.166` (MidPoint 4.10.2)
Resource org: `upeu/resources/oracle-lamb/org.xml` (OID `9e2f4c7a-1b5d-4e8c-a3f6-c2d9e4b7a1f3`)
Template base: `canonical/object-templates/UserTemplate-Person-Base.xml`
Skills consultadas: `midpoint-best-practices` §5 (Org structures, Cap.10 Semančík), `iga-canonical-standards` §10.2 (OrgType archetypes)

---

## 0. Resumen ejecutivo

Hoy coexisten **dos árboles de orgs** en PROD:

| Árbol | Raíz | Orgs | Usuarios | Cómo se pueblan |
|---|---|---|---|---|
| **Canónico** (con `archetype-org-*`) | `UPeU` (`OU-...`, identifiers semánticos) | 120 | **26,162** | D6 (`academicProgramCode`→OrgType EP) + orgs declaradas a mano en `upeu/orgs/` |
| **Legacy** (`AREA-N`, sin archetype) | `AREA-1 Asamblea Universitaría` (`identifier`=ID_AREA puro) | 370 | **4,605** | Resource `org.xml` (sync ELISEO.ORG_AREA) + Bloque E (`costCenter`=ID_AREA → `OrgType.identifier=costCenter`) |

El árbol legacy NO tiene archetype (el resource `org.xml` lo dejó como "TODO Ola 3", línea 163). Los 4,605 usuarios legacy son **trabajadores UPeU reales** (faculty/staff), asignados por su `costCenter`.

**Objetivo:** UN solo árbol canónico, todas las orgs con `archetype-org-*`, todos los usuarios reasignados sin pérdida, residuo denominacional purgado.

### Causa raíz (la decisión que lo explica todo)

El resource `org.xml` crea orgs con `identifier = ID_AREA` puro (ej. `86`), y el **Bloque E** del template asigna usuarios buscando `OrgType.identifier = costCenter (=ID_AREA)`. Las orgs canónicas declaradas a mano usan identifiers **semánticos** (`SEDE-LIMA`, `EP-ARQ`, `ENGLISH-LIMA`) — **nunca** `ID_AREA`. Por eso Bloque E nunca matchea contra el árbol canónico, y los trabajadores caen en el árbol `AREA-N` paralelo.

**Conclusión de diseño:** el árbol canónico debe llevar el `identifier = ID_AREA` (numérico, persistente, IIA = `ELISEO.ORG_AREA.ID_AREA`) en cada org que corresponda a un área real de LAMB. Así el Bloque E reasigna los 4,605 trabajadores **automáticamente** al recompute, sin tocar el template. Esto cumple la regla de oro #10 de `iga-canonical-standards` (identifiers inmutables y persistentes) y la cita de Semančík: *"Always use organizational unit identifiers if you can."*

---

## 1. Causa raíz y mapeo objetivo

### 1.1 Cómo el resource crea hoy los `AREA-N` planos

`upeu/resources/oracle-lamb/org.xml` (kind=generic, intent=default, focus=OrgType):

- `UID = ID_AREA` → `inbound` a `identifier` (puro numérico, ej. `86`).
- `NAME = 'AREA-' || ID_AREA` → `inbound` a `name` (`AREA-86`).
- `NOMBRE` → `displayName`.
- `ID_PARENT` → `assignmentTargetSearch` (`OrgType.identifier = ID_PARENT`) → assignment al padre (jerarquía via `parentOrgRef`).
- **NO** asigna `archetypeRef` (línea 161-164: `<focus><type>OrgType</type></focus>` sin archetype — el comentario dice "Ola 3 lo hará").
- Filtro v1.1: `ESTADO='1' AND (TIENEHIJO='1' OR tiene_trabajadores_activos)` → ~370 nodos, pero **sin filtro por entidad** → incluye áreas de entidades denominacionales (Asoc Educ, IGLESIAS LEGAL, etc.) que tengan trabajadores activos.

### 1.2 Datos de clasificación disponibles en Oracle LAMB

Investigación de `ELISEO.ORG_AREA` (20 columnas). Las que clasifican:

| Columna | Tipo | Uso para archetype/parent |
|---|---|---|
| `ID_AREA` | NUMBER | **identifier canónico** (IIA, inmutable) |
| `ID_PARENT` | NUMBER (nullable) | **jerarquía** (parentOrgRef vía assignmentTargetSearch). NULL = raíz. |
| `ID_ENTIDAD` | NUMBER | **filtro de scope** — `7124` = UPeU. Otras = denominacional. |
| `ID_TIPOAREA` | NUMBER (NOT NULL) | **clasificador de archetype** (catálogo `ELISEO.TIPO_AREA`) |
| `NIVEL` | NUMBER | NO confiable: NULL en 8,010/8,026 filas. **No usar.** |
| `IZQUIERDA`/`DERECHA` | NUMBER | nested-set (no se usa; jerarquía via ID_PARENT) |
| `ESTADO` | VARCHAR2(1) | `1`=activo, `0`=inactivo |

Catálogo `ELISEO.TIPO_AREA` (17 tipos):

| ID_TIPOAREA | NOMBRE | Count en ent=7124 (UPeU) |
|---|---|---|
| 1 | PROMOTORA | 1 |
| 2 | ASAMBLEA | 1 |
| 3 | CONSEJO | 1 |
| 4 | RECTORADO | 1 |
| 5 | VICERRECTORADO | 6 |
| 6 | DIRECCION | 71 |
| 7 | COORDINACION | 29 |
| 8 | JEFATURA | 576 |
| 9 | OFICINA | 118 |
| 10-17 | Liderazgo/Especialistas/etc. (clasificación de cargos, casi sin uso en ent=7124) | 0 |

Tabla puente `ELISEO.ORG_ESCUELA_PROFESIONAL` (`ID_EP` ↔ `ID_AREA`): identifica qué áreas son **Escuelas Profesionales** (academic-program). NO se distingue por `ID_TIPOAREA` (una EAP es una `DIRECCION` o `JEFATURA` en TIPO_AREA).

Tabla `ELISEO.ORG_SEDE` (6 sedes): `ID_SEDE` 1=Lima, 2=Juliaca, 3=Tarapoto, 4=ISTAT, 5=Clínica Good Hope (FUERA), 6=AGTU (FUERA).

### 1.3 Estructura real del árbol UPeU (ent=7124)

Raíz única: `AREA=1 Asamblea Universitaría` (tipo=2). Bajo ella, jerarquía via ID_PARENT:

```
AREA=1   Asamblea Universitaría        (tipo 2 ASAMBLEA)
  AREA=2   Consejo Universitario        (tipo 3 CONSEJO)
    AREA=3   Rectorado                  (tipo 4 RECTORADO)
      AREA=4   Vicerrectorado Bienestar (tipo 5 VICERRECTORADO)
      AREA=5   Vicerrectorado Académico (tipo 5)
      AREA=6   Vicerrectorado Admin.    (tipo 5)
      AREA=430 Dirección General Campus (tipo 5) → bajo aquí cuelgan colegios
      ...
```

**804 áreas activas** en ent=7124. Los 3 colegios están DENTRO de ent=7124:
- `AREA=97 Colegio Unión` (parent=5, tipo 6 DIRECCION)
- `AREA=695 Colegio Adventista del Titicaca - CAT` (parent=430, tipo 6)
- `AREA=8208 Colegio Unión - Tarapoto` (parent=430, tipo 6)

### 1.4 Mapeo objetivo ID_AREA → archetype canónico

El `ID_TIPOAREA` solo NO basta para distinguir faculty/academic-program/department (todas son DIRECCION/JEFATURA). El mapeo canónico combina **TIPO_AREA + tablas puente + posición jerárquica + listas curadas**. Regla de precedencia (primera que matchea gana):

| # | Condición (sobre el área) | Archetype canónico | OID |
|---|---|---|---|
| 0 | `ID_AREA = 1` (Asamblea, raíz UPeU) | **org-institution** | `455d90ab-b54a-4aa7-a402-a6b6ffc0c0d9` |
| 1 | `ID_AREA IN (97, 695, 8208)` (los 3 colegios) | **org-partner-institution** | `79bd8a9e-78f0-430f-8133-e8f3be6859c1` |
| 2 | área está en `ORG_ESCUELA_PROFESIONAL` (es una EP) | **org-academic-program** | `9f3b8e2a-4c7d-4b1e-a8f5-6d2c4e9a1b73` |
| 3 | `ID_TIPOAREA IN (2,3,4,5)` (Asamblea/Consejo/Rectorado/Vicerrectorado) | **org-governance** | `20ee260b-8591-4a5b-8b93-f1607eb501a7` |
| 4 | área cuyo nombre/lista curada = facultad (ver §1.5) | **org-faculty** | `87f84549-d101-4ae4-8036-42fb6abdfeec` |
| 5 | área académica no-EP no-facultad (CRAI, idiomas, CEPRE, conservatorio — lista curada) | **org-academic-unit** | `04c304d1-9205-4097-9c1d-6dce6ba98c7f` |
| 6 | resto (DIRECCION/COORDINACION/JEFATURA/OFICINA administrativa) | **org-department** | `73795c10-2417-4323-b6fa-b88449a8bba4` |

**Parent** de cada org canónica: `assignmentTargetSearch(OrgType.identifier = ID_PARENT)` — idéntico al mecanismo actual del resource, pero ahora todas las orgs llevan identifier=ID_AREA puro, así que la jerarquía LAMB se reconstruye fiel. Raíz `AREA=1` cuelga de la institución (sin ID_PARENT → condición de raíz).

> **Nota sobre §1.4 reglas 4 y 5 (faculty vs academic-unit):** `ID_TIPOAREA` no las distingue. Se resuelven con una **lista curada de ID_AREA** (tabla de mapeo en `upeu/orgs/_mapping/area-archetype-overrides.csv`, propuesta nueva). Las facultades UPeU son ~5 (ya existen 5 orgs `org-faculty` canónicas declaradas en `010-Facultades.xml`). El runbook de ejecución debe **cruzar** los ID_AREA de esas facultades con sus orgs canónicas existentes para no duplicar.

### 1.5 Los 3 colegios — modelado canónico

Cada colegio = `org-partner-institution`, colgando de su **campus** respectivo (no de la Dirección General de Campus genérica):

| Colegio | ID_AREA | Campus padre canónico | identifier campus |
|---|---|---|---|
| Colegio Unión | 97 | Campus Lima (`OU-CAMPUS-LIMA`) | `SEDE-LIMA` |
| Colegio Adventista del Titicaca (CAT) | 695 | Campus Juliaca | `SEDE-JULIACA` |
| Colegio Unión - Tarapoto | 8208 | Campus Tarapoto | `SEDE-TARAPOTO` |

Esto cumple `iga-canonical-standards` §10.2 (partner-institution transversal) y el doctrina activa #anexo (Colegio Unión / Clínica Good Hope como `affiliate.partner-institution`). Los colegios YA tienen orgs canónicas declaradas en `upeu/orgs/colegio-union/` — el mapeo debe **reusarlas** (asignarles identifier=ID_AREA 97/695/8208) en vez de crear nuevas.

---

## 2. Estrategia de migración de usuarios (sin pérdida)

### 2.1 Pieza clave: el Bloque E ya hace el trabajo

`UserTemplate-Person-Base.xml` Bloque E (líneas 749-784):
```
costCenter (=ID_AREA puro) → assignmentTargetSearch(OrgType.identifier = costCenter) → assignment
condición: costCenter.matches('\d+')
```

**Implicación:** si las orgs canónicas tienen `identifier = ID_AREA`, un `recompute` reasigna los 4,605 trabajadores a la org canónica correcta **automáticamente**, sin cambiar el template ni los datos de usuario. El `costCenter` de los usuarios YA es el ID_AREA puro (verificado: valores `85`, `86`, `83`, `53`...).

### 2.2 Decisión de identifiers (la única decisión de fondo)

**Opción elegida: las orgs canónicas adoptan `identifier = ID_AREA` (numérico).**

- Orgs canónicas que corresponden a un área LAMB → `identifier = {ID_AREA}` (ej. campus Lima podría no tener ID_AREA directo; ver matiz abajo).
- Esto NO rompe D6 (Escuelas Profesionales): D6 busca `OrgType.name = academicProgramCode` (ej. `EP-ARQ`), usa `name`, NO `identifier`. Cambiar el `identifier` de la EP a su ID_AREA deja `name=EP-ARQ` intacto → D6 sigue funcionando, y además Bloque E ahora puede asignar trabajadores de esa EP por costCenter. **Doble cobertura sin conflicto.**
- `name` se mantiene estable y legible (`OU-CAMPUS-LIMA`, `EP-ARQ`, etc.) — regla §5.2 Semančík (name técnico + displayName legible + identifier persistente separado).

**Matiz campus/institución:** Campus Lima/Juliaca/Tarapoto NO son áreas LAMB con ID_AREA propio (son `ID_SEDE`, no `ID_AREA`). Se mantienen con identifier semántico (`SEDE-LIMA`). No reciben usuarios por Bloque E directamente — los usuarios cuelgan de las áreas hijas (departamentos), y la jerarquía sube al campus vía parentOrgRef. Correcto.

### 2.3 Orden de migración (sin downtime)

1. **Sumar, no restar** (regla de oro #6). Primero crear/etiquetar el árbol canónico completo con identifiers=ID_AREA, ANTES de tocar el legacy.
2. El resource `org.xml` se modifica para: (a) filtrar `ID_ENTIDAD=7124` (+ overrides de los 3 colegios, que ya son ent=7124), (b) asignar `archetypeRef` dinámico por las reglas §1.4 vía object template de OrgType.
3. Reconciliación del resource org → las orgs `AREA-N` existentes **se actualizan in-place** (mismo UID=ID_AREA → mismo shadow → mismo OrgType): adquieren archetype. NO se crean orgs nuevas para áreas ya sincronizadas (situación `linked`).
4. Las orgs canónicas declaradas a mano (campus, EP, colegios) reciben su `identifier=ID_AREA` vía patch dirigido (las que corresponden a un área LAMB).
5. `recompute` de los 54,804 usuarios → Bloque E reasigna trabajadores a orgs (ahora con archetype). D6 sigue asignando EP. Sin pérdida: el assignment se recalcula sobre el mismo `identifier`.
6. Recién entonces purgar: orgs legacy duplicadas (si las hubiera) + residuo denominacional fuera de ent=7124.

> **Por qué no hay pérdida:** los assignments de usuario a org son `strong` y derivados del costCenter (Bloque E). MidPoint recalcula el assignment en cada recompute. Mientras el `OrgType.identifier` siga siendo el ID_AREA del costCenter del usuario, el assignment apunta al mismo target (aunque el OID del OrgType cambie, el matcher es por `identifier`, no por OID). **No se debe borrar la org antes del recompute** — eso sí causaría pérdida temporal.

---

## 3. Verificación de los ~303 usuarios denominacionales (PRE-purga, NO destructivo)

Antes de purgar las 7 raíces fuera de scope, confirmar que ningún usuario sea trabajador UPeU real mal clasificado.

### 3.1 Identificar usuarios bajo raíces denominacionales (MidPoint)

Raíces fuera de scope confirmadas en Oracle (ID_PARENT NULL, ID_ENTIDAD ≠ 7124):
`Asoc Educ` (AREA 160/535/536/537/538/4598-4604), `Administración` denominacional (AREA 750/808/811/813/814/815/4306/4605-4611/4726-4732/4800-4806), `Gerencia General ACES Perú` (AREA 116, ent=9415), `SEHS` (AREA 115/4717), `IGLESIAS LEGAL` (AREA 1204/1215/1224/2666), `Mision Centro Oeste` (AREA 4326), `Oficina principal - APCE` (AREA 821).

Query MidPoint (subtree de cada raíz denominacional → usuarios):
```sql
-- En PROD: docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint
SELECT DISTINCT u.oid, u.nameorig, u.costcenter, u.lifecyclestate
FROM m_user u
JOIN m_ref_object_parent_org por ON por.owneroid=u.oid
JOIN m_org o ON o.oid=por.targetoid
WHERE o.identifier IN (<lista ID_AREA denominacionales>)
   OR o.oid IN (<subtree OIDs de las raíces denominacionales>);
```

### 3.2 Cruce contra empleo activo UPeU (Oracle)

Para cada DNI (`taxId`/`num_documento`) de esos usuarios, verificar si tiene vínculo laboral ACTIVO en sede UPeU (1/2/3/4):
```sql
-- Oracle LAMB (solo lectura)
SELECT e.NUM_DOCUMENTO, e.ID_ENTIDAD, osa.ID_SEDE, e.ESTADO
FROM ELISEO.VW_APS_EMPLEADO e
JOIN ENOC.VW_TRABAJADOR t ON t.ID_PERSONA = e.ID_PERSONA
JOIN ELISEO.ORG_SEDE_AREA osa ON osa.ID_SEDEAREA = t.ID_SEDEAREA
WHERE e.NUM_DOCUMENTO IN (<DNIs de los 303>)
  AND e.ESTADO='A'
  AND osa.ID_SEDE IN (1,2,3,4);
```

**Regla de decisión:**
- DNI con empleo activo sede UPeU → **NO purgar** el usuario. Su costCenter debe apuntar a un ID_AREA de ent=7124. Si apunta a denominacional, es dato sucio en LAMB → escalar a RR.HH., mantener usuario en cuarentena (`lifecycleState=suspended`, no archived).
- DNI sin empleo activo UPeU → candidato legítimo a purga/archivado (no es comunidad UPeU).

> Esta verificación se ejecuta en **Fase 3** (read-only) y su resultado **condiciona** la lista de purga de Fase 4. Es bloqueante: no se purga ningún usuario hasta tener el cruce.

---

## 4. Fases de ejecución con backup y rollback

> Todas las fases destructivas requieren confirmación explícita del usuario.

### Fase 0 — Backup (no destructivo)
- Git: `git tag backup-pre-org-canonical-2026-05-29 && git push --tags`
- PROD `pg_dump` selectivo (orgs + assignments + refs + shadows):
  ```
  pg_dump -U midpoint -d midpoint -t m_org -t m_ref_object_parent_org \
    -t m_assignment -t m_ref_archetype -t m_shadow -t m_ref_projection \
    > /tmp/backup_org_canonical_$(date +%Y%m%d_%H%M).sql
  ```
- Export de objetos via REST: `orgs` + `archetypes` + `objectTemplates` a `archive/snapshots/`.
- **Rollback:** restaurar tag git + `psql < backup.sql` (tras `docker compose down` de midpoint_server; data container intacto).

### Fase 1 — Resource mapping + OrgType template (no destructivo si se prueba en dev)
1. **Crear `canonical/object-templates/OrgTemplate-Area.xml`** (NUEVO): object template para OrgType que asigna `archetypeRef` dinámico según reglas §1.4. Source: `extension/upeu:tipoArea`, `identifier`, lookup contra lista curada EP/faculty. Vincular vía `<archetypePolicy>` o `objectTemplateRef` global para OrgType, o referenciarlo desde el resource `org.xml`.
2. **Modificar `upeu/resources/oracle-lamb/org.xml`:**
   - searchScript: añadir `AND a.ID_ENTIDAD = 7124` al `baseQuery` (filtro de scope por entidad UPeU). Los 3 colegios ya son ent=7124 → entran solos.
   - Añadir columna `ID_TIPOAREA` al SELECT + schemaScript + inbound a `extension/upeu:tipoArea` (hoy mapea `TIPO_AREA` texto; usar `ID_TIPOAREA` numérico del catálogo).
   - Añadir `ID_EP` (subquery a `ORG_ESCUELA_PROFESIONAL`) → inbound a una flag `extension/upeu:isEP` para la regla §1.4 #2.
   - En `<focus>`: añadir `<archetypeRef>` NO es válido dinámicamente; el archetype dinámico se asigna vía el **object template de OrgType** (paso 1) usando `assignmentTargetSearch` o mapping condicional a `assignment` con targetRef de archetype. (Alternativa: mappings inbound condicionales que asignen el archetype por `ID_TIPOAREA`.)
3. **Probar primero en dev** (`pruebas-alberto-1`, 192.168.15.230) con un subconjunto, validar `ninja`/REST validate.
- **Rollback:** revertir commit del resource + template; reimport versión anterior via REST.

### Fase 2 — Recon org + patch identifiers canónicos (semi-destructivo: muta orgs)
1. Reconciliación del resource `org.xml` → las 370 orgs `AREA-N` adquieren archetype in-place (situación `linked`, mismo UID). Las áreas denominacionales dejan de re-sincronizarse (filtro ent=7124) → quedan como shadows `dead` (igual que en el saneamiento previo).
2. Patch dirigido a las orgs canónicas declaradas a mano que corresponden a un área LAMB: setear `identifier = {ID_AREA}` (colegios 97/695/8208; EPs con su ID_AREA; facultades con su ID_AREA). Campus/institución mantienen identifier semántico.
   - **Riesgo de colisión:** si una org `AREA-N` (legacy) y una org canónica (declarada a mano) representan la MISMA área → habría dos OrgType con el mismo identifier. **Detección previa obligatoria:** listar ID_AREA duplicados antes del patch; consolidar (mover users + parentOrgRef al canónico, borrar el AREA-N duplicado). Ver §5.
- **Rollback:** restaurar dump de m_org + m_ref_archetype de Fase 0.

### Fase 3 — Verificación pre-purga usuarios (read-only, BLOQUEANTE)
1. Ejecutar queries §3.1 (MidPoint) + §3.2 (Oracle) → clasificar los ~303.
2. Producir lista: `keep_upeu_real[]`, `quarantine_dirty_costcenter[]`, `purge_candidates[]`.
3. **Recompute** de los 54,804 usuarios (o subconjunto trabajadores) → Bloque E reasigna a orgs canónicas (ahora con archetype). Verificar que `LEGACY_NO_ARCH` baje a 0 y `CANONICAL` suba a ~30,767.
4. Confirmar conteo: usuarios bajo orgs sin archetype debe ser 0 (excepto residuo en cuarentena).
- **Rollback:** ninguno necesario (read-only + recompute es idempotente; un nuevo recompute restaura).

### Fase 4 — Purga (DESTRUCTIVO, requiere confirmación)
1. Purgar orgs denominacionales (shadows dead, fuera ent=7124) — mismo procedimiento que `org-tree-sanitation-2026-05-29.md` Fix 2, ya validado.
2. Purgar orgs `AREA-N` duplicadas consolidadas en Fase 2 (si las hubo).
3. Archivar/purgar usuarios `purge_candidates[]` de Fase 3 (solo los SIN empleo UPeU): `lifecycleState=archived`, no delete.
4. Purgar plantillas demo MidPoint (`Projects`/`Teams`/`World`) si aún existen.
- **Rollback:** restaurar dump Fase 0. (Por eso el dump incluye m_org, m_assignment, m_shadow, m_ref_*.)

### Fase 5 — Verificación final
- 1 solo árbol: raíz `org-institution` (AREA-1) → governance → campus → faculty/academic-program/academic-unit/department; + 3 partner-institution colgando de su campus.
- 100% orgs in-scope con archetype `org-*`.
- 0 usuarios activos bajo orgs sin archetype.
- 0 orgs de ent≠7124 activas.
- Conteos esperados: ~30,767 usuarios en orgs canónicas (26,162 + 4,605), ~370 orgs canónicas, 0 legacy `AREA-N` sin archetype.
- Smoke test: 5 usuarios faculty + 5 student → org membership correcta + provisioning Koha/LDAP intacto.

---

## 5. Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | **Colisión de identifier**: org `AREA-N` legacy y org canónica declarada representan la misma área → dos OrgType, identifier duplicado, `assignmentTargetSearch` ambiguo. | Fase 2 detecta ID_AREA duplicados ANTES del patch. Consolidar: mantener el canónico (con archetype + jerarquía correcta), mover usuarios y borrar el duplicado. **Único punto de pérdida potencial — tratar con cuidado.** |
| R2 | **costCenter apunta a ID_AREA que será org canónica con OTRO identifier** (ej. EP cuyo identifier se cambia de `EP-ARQ` a su ID_AREA). | El cambio propuesto es lo contrario: la EP ADQUIERE identifier=ID_AREA (manteniendo name=EP-ARQ). Bloque E (busca por identifier=costCenter) entonces SÍ matchea. D6 (busca por name) sigue intacto. Sin pérdida; doble cobertura. **Verificar que ningún costCenter use un identifier semántico** (todos son numéricos por diseño — condición `matches('\d+')`). |
| R3 | **Provisioning Koha/LDAP** depende de orgs en assignments. Si un assignment de org desaparece durante la ventana recon→recompute. | Las construcciones Koha/LDAP NO dependen del OrgType membership directamente — dependen de business/application roles asignados por afiliación (D, D6) y costCenter (Q4/Q5). El cambio de archetype de la org no altera roleMembershipRef de los usuarios. Mantener Koha/LDAP en `proposed` durante la migración (ya lo están parcialmente) hasta verificar Fase 5. |
| R4 | **Interacción con recompute pendiente** (task `3e8b389e` recompute-all-v2). | Coordinar: dejar terminar el recompute de bootstrap-archetype ANTES de Fase 2. La migración org introduce SU PROPIO recompute (Fase 3.3). No correr ambos en paralelo (OOM riesgo — PROD en recuperación post-OOM). |
| R5 | **Áreas raíz UPeU sin ID_PARENT** (AREA-1) quedan huérfanas del árbol canónico. | Object template OrgType: regla §1.4 #0 → AREA-1 = org-institution, parent = ninguno (es la raíz). Las demás cuelgan vía ID_PARENT. Verificar que AREA-1 NO cuelgue de la institución canónica preexistente `UPeU` (consolidar: AREA-1 ES la institución, o subordinar UPeU↔AREA-1). **Decisión pendiente — ver confirmaciones.** |
| R6 | **Faculty vs academic-unit no distinguibles por TIPO_AREA.** | Lista curada `area-archetype-overrides.csv`. Reusar las 5 orgs `org-faculty` canónicas existentes (cruzar sus ID_AREA). |
| R7 | **OOM durante recompute de 54,804 usuarios.** | Scope el recompute a trabajadores (archetype faculty/staff, ~13K) — son los únicos que cambian de org por Bloque E. Estudiantes (D6) no se ven afectados por el cambio de archetype de orgs administrativas. |

---

## 6. Artefactos a crear/modificar (resumen)

| Archivo | Acción | Fase |
|---|---|---|
| `canonical/object-templates/OrgTemplate-Area.xml` | **NUEVO** — archetype dinámico OrgType por reglas §1.4 | 1 |
| `upeu/resources/oracle-lamb/org.xml` | Modificar — filtro ent=7124, +ID_TIPOAREA, +ID_EP, link a OrgTemplate | 1 |
| `upeu/orgs/_mapping/area-archetype-overrides.csv` | **NUEVO** — faculty/academic-unit curado + ID_AREA de colegios/EP | 1 |
| `upeu/orgs/colegio-union/*` | Patch identifier=97/695/8208 + parent=campus | 2 |
| Orgs canónicas EP/faculty (`010-Facultades.xml`, `academic-programs/`) | Patch identifier=ID_AREA | 2 |
| (sin cambios) `UserTemplate-Person-Base.xml` Bloque E | **NO tocar** — ya hace el matching correcto | — |

---

## 7. Decisión clave de diseño (bloque SciBack)

> **Patrón canónico reutilizable:** En IGA universitario, el árbol de orgs se sincroniza desde el HR/ERP usando el **identificador de área nativo** (`ID_AREA`) como `OrgType.identifier`, y el assignment usuario→org se deriva del `costCenter` (= mismo identificador) vía `assignmentTargetSearch(identifier = costCenter)`. El archetype de cada org se asigna por un **object template de OrgType** que clasifica según el tipo de área del ERP + tablas puente (escuelas profesionales) + listas curadas (facultades). Esto evita el árbol "plano sin archetype" y el árbol "semántico paralelo" — un solo árbol, identifiers persistentes, jerarquía fiel al ERP.

Overlay UPeU: tabla `TIPO_AREA` de ELISEO, entidad 7124, colegios como partner-institution.
Bloque canónico SciBack: el patrón identifier=ERP-area-id + object-template-driven archetype.

---

## 8. Recomendación de arranque y confirmaciones requeridas

**Por dónde empezar:** Fase 0 (backup) + Fase 1 paso 1-2 en **dev** (`pruebas-alberto-1`), nunca en PROD primero. Validar el OrgTemplate-Area + filtro ent=7124 contra un subconjunto antes de tocar PROD.

**Confirmaciones que necesito de ti (Alberto):**

1. **R5 / institución raíz:** ¿`AREA-1 Asamblea Universitaría` ES la org-institution (la raíz canónica), o la institución canónica es la org `UPeU` ya existente y AREA-1 cuelga de ella como governance? (Recomiendo: la org `UPeU` existente es la institución; AREA-1 = governance bajo ella, porque "Asamblea Universitaria" es un órgano de gobierno, no la universidad entera.)

2. **Lista de facultades (R6):** ¿me confirmas los 5 ID_AREA de las facultades UPeU para la lista curada? (O los identifico cruzando los nombres de las 5 orgs `org-faculty` canónicas existentes contra ELISEO.ORG_AREA.)

3. **Cuarentena vs purga (Fase 3):** para usuarios denominacionales SIN empleo UPeU activo, ¿`lifecycleState=archived` (preservar datos) o están fuera de scope total y se borran? (Recomiendo archived — reversible, evidencia ISO 27001.)

4. **Ventana de ejecución:** ¿coordinamos para después de que termine el recompute bootstrap pendiente (`3e8b389e`) y con PROD estable post-OOM? (R4/R7.)

5. **Scope recompute (R7):** ¿OK limitar el recompute de migración a trabajadores (faculty/staff ~13K) en lugar de los 54,804, para evitar OOM? Los estudiantes no cambian de org por este rediseño.

---

# ADDENDUM DE EJECUCIÓN (2026-05-29) — Estrategia revisada por hallazgos en PROD

## A.0 Hallazgos que cambian la estrategia

La inspección de PROD reveló que existen **TRES** formatos de `OrgType.identifier`, no dos:

| Formato | Ejemplo | Quién lo usa | Usuarios que llegan |
|---|---|---|---|
| `area.N` (prefijo `area.`) | `area.5` | **Árbol canónico ADMIN** ya modelado (32 orgs: governance/department/academic-unit) colgando de `UPeU → GOBIERNO-UNIVERSITARIO → ...` | **0** |
| `N` puro numérico | `5` | Árbol **legacy** `AREA-N` (370 orgs, sin archetype) creado por el resource org.xml | **4,605** (trabajadores, vía Bloque E) |
| Semántico | `EP-SIS`, `FE`, `SEDE-LIMA` | EPs (23), facultades (5), campus (3) canónicas | **26,162** (estudiantes, vía D6) |

**Causa raíz real:** El árbol canónico administrativo (`area.N`) YA EXISTE, está bien modelado
(archetypes correctos, displayNames limpios, jerarquía conectada a `UPeU`), PERO el **Bloque E**
del template busca `OrgType.identifier = costCenter` con `costCenter` puro numérico (`5`, `85`).
El prefijo `area.` impide el match. Por eso 0 trabajadores llegan al árbol canónico admin y caen
en las legacy `AREA-N` (identifier numérico puro), un árbol paralelo SIN archetype.

Esto difiere del diseño original (que asumía que las legacy debían recibir archetype vía resource).
La realidad: **el destino canónico ya está construido**; solo falta conectar los trabajadores
quitando el prefijo `area.` de los identifiers.

### Decisión #1 del usuario — ya satisfecha por el modelo existente
`UPeU` (archetype-org-institution, identifier `upeu.edu.pe`) ES la raíz. `Asamblea Universitaria`
(canónica `ASAMBLEA-UNIVERSITARIA`, identifier `area.1`) cuelga bajo `GOBIERNO-UNIVERSITARIO` bajo
`UPeU`. NO se usa AREA-1 legacy como raíz. **Ya implementado correctamente.**

## A.1 Filtro de scope corregido (resource org.xml)

El filtro actual (`ESTADO=1 AND (TIENEHIJO=1 OR trabajadores activos)`) **sin filtro de entidad**
sincroniza **370 áreas, de las cuales solo 129 son ent=7124** (241 son denominacionales que entran
por tener trabajadores). Además **excluye padres estructurales** (ej. AREA-22, padre de Secretaría
General) → árbol inconexo.

**Filtro nuevo (verificado en Oracle):** subárbol conexo desde AREA-1, vía `CONNECT BY PRIOR
ID_PARENT = ID_AREA` a partir de las áreas ent=7124 con trabajadores/hijos, MINUS subárbol AGTU (8196):

```sql
SELECT ID_AREA FROM (
  SELECT DISTINCT ID_AREA FROM ELISEO.VW_AREA
  START WITH ID_AREA IN (
    SELECT a.ID_AREA FROM ELISEO.VW_AREA a
    WHERE a.ID_ENTIDAD=7124 AND a.ESTADO='1'
      AND (a.TIENEHIJO='1' OR EXISTS (SELECT 1 FROM ELISEO.VW_APS_EMPLEADO e
        JOIN ENOC.VW_TRABAJADOR t ON t.ID_PERSONA=e.ID_PERSONA
        JOIN ELISEO.ORG_SEDE_AREA osa ON osa.ID_SEDEAREA=t.ID_SEDEAREA
        WHERE osa.ID_AREA=a.ID_AREA AND e.ESTADO='A')))
  CONNECT BY PRIOR ID_PARENT = ID_AREA)
MINUS
SELECT ID_AREA FROM ELISEO.VW_AREA START WITH ID_AREA=8196 CONNECT BY PRIOR ID_AREA=ID_PARENT
```

**Resultado: 133 áreas, todas ent=7124, raíz única AREA-1, sin AGTU, sin denominacionales.**
Incluye las 5 facultades (8,9,10,11,12), 3 colegios (97,695,8208) e ISTAT (760).

## A.2 Facultades — ID_AREA deducidos y VERIFICADOS (decisión #5)

Cruce `ELISEO.VW_AREA.NOMBRE` (UPPER LIKE '%FACULTAD%', ent=7124, activas) vs displayName de las
5 orgs `org-faculty` canónicas. **Match exacto 5/5, sin ambigüedad:**

| Facultad canónica (OID) | identifier actual | **ID_AREA Oracle** | NOMBRE Oracle | ID_PARENT |
|---|---|---|---|---|
| Facultad de Ciencias Humanas y Educación (`141cd2b3`) | FE | **8** | Facultad de Ciencias Humanas y Educación | 5 |
| Facultad de Ingeniería y Arquitectura (`86968a5a`) | FIA | **9** | Facultad de Ingeniería y Arquitectura | 5 |
| Facultad de Ciencias de la Salud (`a72bbde6`) | FCS | **10** | Facultad de Ciencias de la Salud | 5 |
| Facultad de Teología (`23e944c6`) | FT | **11** | Facultad de Teología | 5 |
| Facultad de Ciencias Empresariales (`2899369e`) | FCCA | **12** | Facultad de Ciencias Empresariales | 5 |

**Ruido descartado:** AREA-673 "Facultad de prueba" (tipo 6 bajo VR Académico) — excluida; por eso
faculty se asigna por **lista curada** {8,9,10,11,12}, NO por TIPO_AREA.

## A.3 Tabla puente ORG_ESCUELA_PROFESIONAL — descartada
Solo 10 filas / 2 EPs (Admin, Contabilidad), con áreas espurias (Ecuador, Tesis). NO sirve como
flag `isEP`. Las EPs reales se modelan a mano en el árbol canónico de estudiantes. **Regla §1.4 #2
del diseño original descartada.** Las 133 áreas in-scope son administrativas/governance; no hay EPs
académicas con trabajadores entre ellas.

## A.4 Estrategia ejecutada (mínimo riesgo)

1. **Patch identifier de las 32 orgs canónicas `area.N` → `N` puro** (mantener name/displayName/OID/
   parent/archetype). Hace que Bloque E las matchee. Colisiona con la legacy `N` → purgar legacy ANTES.
2. **Patch facultades canónicas** FE→8, FIA→9, FCS→10, FT→11, FCCA→12 (mantener name; D6 usa name, no
   se afecta). **Patch colegios** canónicos → 97/695/8208.
3. **Purga de las 370 legacy `AREA-N`** (paralelas, sin archetype) tras vaciarlas.
4. **Resource org.xml corregido** (filtro 133 + archetype dinámico in-place) para las áreas que SÍ
   tienen trabajadores pero NO contraparte canónica `area.N` (departamentos puros) → archetype
   `department` + parent vía ID_PARENT (ahora numérico).
5. **Recompute trabajadores (~13K, decisión #4)** → Bloque E reasigna los 4,605 al árbol canónico.

**Colisión de identifier (R1):** las 25 áreas con par (canónica `area.N` + legacy `N` poblada).
Orden seguro por par: purgar legacy `N` → patch canónica `area.N`→`N`. Ventana breve sin org;
aceptable (Koha/LDAP en `proposed`).


---

# REGISTRO DE EJECUCIÓN (2026-05-29, midpoint-expert)

## Fase 0 — Backup ✅ (previa)
Tag `backup-pre-org-canonical-migration-2026-05-29` + pg_dump 2.8GB en
`/home/juansanchez/backup_org_canonical_20260529_0811.sql`.

## Fase 1 — Patch identifiers del árbol canónico ✅

Estado inicial PROD: 492 orgs (32 `area.N` con archetype y 0 users, 370 `N` puro legacy sin
archetype con 4,898 users, 87 semánticas, 372 sin archetype). 25 colisiones canónica/legacy,
7 canónicas free (19,21,59,126,127,128,130).

**Mecánica:** PATCH/DELETE REST vía localhost en una sola sesión SSH (sshpass falla en reconexiones
rápidas; el patrón `ssh bash -s <<REMOTE` con loop interno es el único fiable). El body XML se
escribe a `/tmp/patch.xml` en PROD y se envía con `--data-binary @file` (las comillas simples se
corrompen a través de las capas shell→ssh→curl, causando "Open quote is expected").

Acciones:
- **7 free canónicas** `area.N`→`N` puro (identifier replace). HTTP 204. (Un primer intento puso
  19→130 por bug de word-split en zsh; corregido a 19.)
- **25 colisiones**: las legacy `N` ya estaban borradas de un intento previo (DELETE devuelve 500
  "not found", pero NO hay duplicados → el borrado fue efectivo). PATCH canónica `area.N`→`N`: 204.
  Nota: DELETE de OrgType con `?options=force` devuelve 500 con OperationResultType aunque el objeto
  SÍ se borra; verificar siempre por ausencia de duplicados, no por el código HTTP.
- **5 facultades** FE→8, FIA→9, FCS→10, FT→11, FCCA→12 (legacy 8-12 borradas, canónica patcheada).
- **4 colegios+ISTAT** (legacy 97/695/8208/760, CON 82/19/7/1 trabajadores): se les asignó
  `archetype-org-partner-institution` + displayName legible + parent=campus respectivo
  (97→SEDE-LIMA, 695/760→SEDE-JULIACA, 8208→SEDE-TARAPOTO), y se eliminó el parent legacy AREA-430/
  area5. Se reusaron las orgs legacy (tienen los trabajadores) en vez de la canónica vacía
  `COLEGIO-UNION`, que se **archivó** (`lifecycleState=archived`, reversible).

Estado tras Fase 1: 467 orgs. 41 orgs con identifier numérico puro + archetype (32 area + 5 faculty
+ 4 partner-institution), todas con displayName legible. 0 `area.N`. 0 identifiers duplicados.
345 legacy `N` puro sin archetype pendientes (departamentos puros → Fase 2/3).

## Fase 2 — Resource org.xml: filtro 133 conexo + archetype dinámico ✅ (config) / ⏳ (recon)

Cambios en `upeu/resources/oracle-lamb/org.xml` (commits `<fase2>`):
- **baseQuery**: reemplazado el WHERE plano por subárbol CONNECT BY conexo desde AREA-1
  (ent=7124, ESTADO=1, con hijos o trabajadores activos), MINUS subárbol AGTU (8196). Verificado
  133 áreas in-scope (incluye facultades 8-12, colegios 97/695/8208, ISTAT 760).
- **testScript**: mismo filtro → reporta count in-scope.
- **name-to-name** y **nombre-to-displayName** → `strong`→`weak`: protege los 41 OrgType canónicos
  (identifier=ID_AREA matchea UID del shadow; sin weak, el recon sobrescribiría sus nombres con
  'AREA-N'). Best-practices §5.2 (name técnico estable separado de displayName).
- **default-department-archetype** (nuevo inbound dentro del attribute ID_AREA existente, NO un
  segundo `<attribute>` — eso causó "Duplicate definition of attribute ID_AREA"): asigna
  `archetype-org-department` solo si `focus.archetypeRef` está vacío. Excluye los 41 canónicos.

PUT resource HTTP 201. **Test connection 15/15 success.**

Recon stage-2 reconcilia TODOS los shadows existentes (no solo los 133 del searchScript). Los ~336
shadows denominacionales fuera del nuevo filtro → situación `deleted` → reaction `inactivateFocus`
→ archived (alimenta Fase 4). Errores ObjectNotFoundException por parentOrgRef stale en orgs
denominacionales: NO fatales (esas orgs se purgan en Fase 4). Task recon `a3ab390f`.

## Fase 2bis — Re-ejecución con resource arreglado (2026-05-29, sesión PM) ⚠️ BLOQUEADO

### PASO 1 (verificación resource en PROD) ✅
- **Hallazgo:** el objeto resource en la DB de MidPoint tenía la versión BUGUEADA (sin el fix
  `f66633f` — `grep getArchetypeRef` = 0 en DB), aunque el archivo en disco SÍ tenía el fix.
  El recon de las 09:00 (PARTIAL_ERROR) corrió con esa versión vieja.
- **Fix aplicado:** `git pull` (already up to date) + `PUT` del resource desde disco → HTTP 201 →
  `getArchetypeRef` = 1 en DB. **Test connection 15/15 success.**
- **Backup incremental:** `/home/juansanchez/backup_org_prerecon_20260529_0952.sql` (755M, m_org +
  refs + assignments).
- **Cruce 334 N-puro-sin-archetype vs 133 in-scope (Oracle, filtro CONNECT BY del addendum A.1):**
  - 133 in-scope confirmadas: `1..18,20,22..27,44,47..55,58,63,65..70,72,73,77..80,82..86,91..94,97,99..107,112,113,131..133,135..137,139,142,143,145,147,150,161,239,251,292,297,430,433,441,511,676,681,692,695,704,709,710,712,713,717,718,719,760,763,765,766,789,803,7763,7871,7902,7920,7948,7987,8019,8027,8080,8081,8085,8088,8102,8110,8112,8138,8153,8154,8177,8208,8223,8232,8242,8266`.
  - De los 334 sin archetype: **92 in-scope** (→ debían recibir department), **242 fuera de scope**
    (→ archived). +5 in-scope sin org en MidPoint (22,433,441,676,763 → recon las crea).
  - Conteo esperado: **97 departments in-scope** tras re-recon (92 patch + 5 nuevas).
  - 36 in-scope ya con archetype (canónicas Fase 1) + 7 free canónicas fuera-de-133
    (19,21,59,126,127,128,130 — academic-unit/department sin trabajadores hoy, legítimas).

### PASO 2 (re-recon) ⚠️ recon SUCCESS pero ARCHETYPE NO SE ASIGNA — BLOQUEADO
- Re-ejecutado task recon `a3ab390f` → **CLOSED/SUCCESS** (375 items, ya NO PARTIAL_ERROR).
- Shadows del resource: **133 LINKED + 242 DELETED** (cuadre exacto con scope — el filtro funciona).
- **PERO `archetype-org-department` NO se asignó a los 97 in-scope.** Solo 2 orgs (99,100) lo tienen,
  y se verificó que fueron creadas el 2026-05-26 (lo traían de antes), NO por este mapping.
- **Las 5 orgs creadas HOY por el recon (22,433,441,676,763) NACIERON SIN archetype.** → refuta la
  hipótesis "solo nuevas reciben el inbound".
- Probado además un **import task** del recurso (`19e43a44`, fuerza inbounds en shadows linked
  unchanged) → CLOSED/SUCCESS → **tampoco asignó**. 97 siguen sin archetype.

### Causa raíz (diagnóstico)
El inbound `default-department-archetype` (assignmentTargetSearch → target=assignment) está
**anidado dentro del `<attribute><ref>ri:ID_AREA</ref>`** y NO produce el assignment ni en orgs
nuevas ni en linked. El mapping en DB es correcto sintácticamente (verificado tras PUT). El defecto
es de **diseño del mapping**: un inbound de assignment cuyo input es un atributo estable (ID_AREA,
sin delta) y cuya expresión `assignmentTargetSearch` ignora el input no genera el assignment
esperado durante import/recon de OrgType. Best-practices: la clasificación de archetype de OrgType
debería vivir en un **object template de OrgType** (se evalúa en cada recompute/create/change —
SKILL §257) en lugar de como inbound del resource — HOY NO existe object template para OrgType en
PROD (solo 5 para UserType).

### DECISIÓN PENDIENTE (no se fuerza más; runbook ordena DETENER ante anomalía repetida)
Opción recomendada: crear `canonical/object-templates/OrgTemplate-Area.xml` con un mapping
(o `assignmentTargetSearch`) que asigne `archetype-org-department` cuando `archetypeRef` esté vacío,
y vincularlo vía `<archetypePolicy><objectTemplateRef>` global para OrgType (o como objectTemplateRef
del resource para kind=generic). Esto desacopla la clasificación del inbound del recurso y la hace
idempotente en recompute. Tras crearlo, un recompute de las 97 orgs in-scope (scope acotado,
sin OOM) las clasificaría. **Pendiente de confirmar con Alberto antes de implementar** (cambio de
object template global de OrgType = artefacto core, requiere confirmación por reglas operacionales).

### Estado de orgs tras PASO 2 (sin avanzar a Fase 3/4)
- 467 orgs total. 43 N-puro con archetype (sin cambio neto). 339 N-puro sin archetype.
- 133 shadows LINKED (in-scope) + 242 DELETED (fuera scope, listos para archivar en Fase 4).
- **NO se ejecutaron Fase 3 (denominacionales) ni Fase 4 (purga)** — bloqueado a la espera de
  resolver la asignación de archetype, para no purgar/archivar con el árbol a medio clasificar.

---

## Fase 2ter — OrgTemplate-Area creado y vinculado (2026-05-29, sesión PM2) ⚠️ NUEVA CAUSA RAÍZ HALLADA

### PASO A — Object template canónico ✅ (implementado y vinculado)
- **Creado** `canonical/object-templates/OrgTemplate-Area.xml` (OID `47252981-08ed-4309-8349-f652a1fb9cef`):
  mapping `default-department-archetype` (strong, `assignmentTargetSearch`→ArchetypeType
  `archetype-org-department`, target=`assignment`) con condición Groovy `getArchetypeRef().isEmpty()`
  → solo clasifica orgs SIN archetype estructural. Las 36 in-scope ya curadas en Fase 1 se excluyen.
- **Neutralizado** el inbound `default-department-archetype` defectuoso de `org.xml` (reemplazado por
  comentario; la clasificación vive ahora en el template). Commit `<fase2ter>`.
- **Vinculado** vía `defaultObjectPolicyConfiguration` para `OrgType` en systemConfiguration
  (PATCH REST add, HTTP 204; verificado en DB: `objectTemplateRef → 47252981...`, `type=c:OrgType`).
  Mecanismo canónico correcto: NO se usa `archetypePolicy/objectTemplateRef` del archetype (sería
  circular — la org aún no tiene archetype), sino el template global por tipo (best-practices §4.1).
- `system-configuration.xml` del repo sincronizado con el bloque (GitOps).

### PASO B — Recompute de las 97 in-scope ❌ 0 clasificadas — BLOQUEADO POR CAUSA RAÍZ DISTINTA
- Recompute acotado a las 97 OIDs (task `iterativeScripting` + `<s:recompute/>`, inOid filter) →
  **CLOSED/SUCCESS** pero **0/97 recibieron `archetype-org-department`**.
- Canary AREA-7 con template aislado (incluso añadiendo `<source>identifier</source>`) → tampoco.

### Causa raíz REAL (distinta del inbound — es integridad de datos)
El template SÍ se evalúa, pero el recompute **aborta la fase de evaluación de assignments** por un
**parent-org assignment colgante**: AREA-7 (y 68 de las 97) tienen un assignment a un OrgType padre
**inexistente** (ej. AREA-7 → `d9e76344-31be-4e02-9d8a-2f00cb5b597e`, org legacy purgada en Fase 1).
Log: `TargetsEvaluation ... Referenced object not found in assignment target reference in
org:...(AREA-7), reason: Object of type 'OrgType' with OID 'd9e76344...' was not found
(ObjectNotFoundException)`. La excepción descarta TODO el cómputo focal del recompute (incluido el
assignment de archetype nuevo del template) → el archetype nunca se persiste, aunque el MODIFY de
repo cierre en SUCCESS.

**Alcance del problema:** 69/97 in-scope con parent colgante; **912/467 orgs en total** tienen al
menos un assignment a OrgType inexistente (residuo de la purga Fase 1 que dejó refs stale en los
hijos). Es un problema de **integridad referencial pre-existente**, NO un defecto del object template
ni del diseño canónico. El template es correcto y queda desplegado.

### DECISIÓN PENDIENTE (DETENIDO por regla del runbook — anomalía bloqueante; no se fuerza)
Antes de re-recomputar las 97 hay que **sanear los parent-org assignments colgantes**. Opciones:
1. **Recon org primero** (re-ejecutar el resource org.xml): reconstruye el assignment de parent vía
   `assignmentTargetSearch(identifier=ID_PARENT)` apuntando al padre canónico vigente → reemplaza el
   ref colgante. Luego recompute → el template clasifica. (Preferida: usa el mecanismo del resource,
   no toca DB.) **Verificar que el recon NO recree los assignments colgantes** (depende de que el
   padre exista en el árbol in-scope; algunos padres pueden ser orgs purgadas legítimamente).
2. **Purga quirúrgica de assignments colgantes** (DELETE de `m_assignment` donde
   `targetreftargettype='ORG'` y target inexistente) — destructivo en DB, requiere backup + confirmación.
3. **Saneamiento masivo previo** de los 912 antes de continuar (más amplio, alineado con Fase 4 purga).

**Recomendación:** opción 1 (recon org) acotada a las 133 in-scope, verificando que cada padre
exista; los huérfanos cuyo padre fue purgado se re-cuelgan de la institución o su campus. Requiere
confirmar con Alberto. NO se ejecutaron Fase 3 ni Fase 4. PROD limpio: tasks diagnósticos borrados,
template canónico (sin `<source>` de prueba) re-PUT desde repo.

### Estado de PROD tras Fase 2ter
- 467 orgs. 97 in-scope siguen sin archetype (bloqueadas por parent colgante). 36 in-scope curadas OK.
- OrgTemplate-Area desplegado + vinculado (systemConfiguration OrgType). Inbound del resource neutralizado.
- 0 cambios destructivos. Backups Fase 0 + incremental intactos.

---

## Fase 2quater — DESBLOQUEO REAL: clasificación por direct assignment + saneo de stales (2026-05-29, sesión PM3) ✅

### Hallazgo que invalida la hipótesis de Fase 2ter
La causa raíz de Fase 2ter ("el parent colgante aborta el recompute") era **parcialmente correcta**, pero
el verdadero bloqueo era OTRO: **el OrgTemplate-Area NO asigna el archetype**, ni siquiera en orgs SIN
parent colgante. Diagnóstico decisivo (canary controlado):

| Org canary | parent colgante | acción | archetype materializado |
|---|---|---|---|
| AREA-22 | NO (parent RECTORADO válido) | PATCH no-op (dispara object template) | **NO** ❌ |
| AREA-22 | NO | PATCH add assignment(archetype) **directo** | **SÍ** ✅ |
| AREA-7 | SÍ (`d9e76344` purgada) | PATCH add assignment **directo** | **SÍ** ✅ (HTTP 240 warning del stale, pero persiste) |

**Conclusión:** asignar archetype vía object template mapping (`assignmentTargetSearch` → `target=assignment`)
es un **anti-patrón en 4.10**: el motor no materializa el archetype assignment desde un template mapping
ordinario sin source delta. El camino fiable es **direct assignment** (PATCH add `assignment/targetRef`
type=ArchetypeType), consistente con la lección de bootstrap de usuarios (MEMORY: "task iterativeScripting
con acción assign directo"). El OrgTemplate-Area queda desplegado pero **inerte** (no daña; su condición
solo actuaría sobre orgs sin archetype y aun así no materializa). Documentado como anti-patrón.

**Segundo hallazgo (favorable):** el parent colgante NO impide el direct assignment (solo genera HTTP 240
warning). Las **69 in-scope con colgante TAMBIÉN tienen un parent VÁLIDO** (dual-parent residuo de Fase 1):
el árbol YA era conexo vía el parent válido; el colgante era un assignment STALE de policy que solo
abortaba `recompute` (no el assign puntual).

### PASO 2 (clasificación) — ✅ 97/97
- Direct assignment `archetype-org-department` (`73795c10`) a las 97 in-scope sin archetype, vía PATCH
  add assignment en bucle (1 sesión SSH; sshpass es flaky en reconexiones). Resultado: **0 errores**
  (4×HTTP 204 limpio + 93×HTTP 240 parcial-pero-persiste por warning de stale).
- **Verificación: 133/133 in-scope con archetype, 0 sin archetype.** Distribución global orgs:
  department 135, academic-unit 37, academic-program 23, governance 13, faculty 5, partner-institution 5,
  campus 3, institution 1.

### PASO 1 (saneo de parents colgantes stale) — ✅ acotado a in-scope
- Backup incremental: `/home/juansanchez/backup_org_stale_clean_20260529_1029.sql` (792 MB; m_assignment +
  m_ref_object_parent_org + m_ref_archetype + m_org).
- **Verificación pre-borrado:** las 69 in-scope con colgante conservan TODAS un parent válido tras quitar
  el stale (0 quedarían huérfanas). A nivel GLOBAL hay 57 orgs solo-colgantes, pero **ninguna es in-scope**
  (todas AREA-N legacy/AGTU/denominacionales → se purgan enteras en Fase 4; no se tocan ahora).
- **DELETE acotado a in-scope:** 69 assignments stale de `m_assignment` borrados (1 por org). 0 refs
  colgantes en `m_ref_object_parent_org` (el ref operacional ya apuntaba al parent válido — confirma
  Reality vs Policy: el stale era solo el assignment de policy).
- **Verificación post:** 0 in-scope con parent colgante, 0 in-scope huérfanas. Canary AREA-7 ahora
  recomputa **limpio (HTTP 204, ya no 240)**, conserva archetype, 1 parent assignment válido.

### Estado de PROD tras Fase 2quater
- **133/133 in-scope con archetype canónico. 0 sin archetype. 0 parents colgantes in-scope. 0 huérfanas.**
- Árbol in-scope conexo y limpio; recomputa sin ObjectNotFoundException.
- Pendiente: Fase 3 (denominacionales READ-ONLY) + Fase 4 (purga legacy/denominacional + recompute
  trabajadores). Los 57 solo-colgantes fuera-de-scope + legacy AREA-N se resuelven en Fase 4.

> **Anti-patrón documentado (bloque SciBack):** NO asignar archetype a OrgType vía object template
> `assignmentTargetSearch`/`target=assignment` — no se materializa en 4.10. Para clasificación masiva de
> orgs sincronizadas desde ERP, usar **direct assignment** (task `iterativeScripting` acción `assign`, o
> PATCH add assignment). El object template de OrgType sirve para mappings de atributos (displayName,
> costCenter, etc.), NO para asignar el archetype estructural.

---

## Fase 3 — Verificación denominacionales (READ-ONLY) ✅ ⚠️ HALLAZGO BLOQUEANTE: premisa falsa

### La premisa "~303 denominacionales sin empleo" resultó FALSA
La Fase 3 partía del supuesto (runbook §3) de que bajo las raíces denominacionales había ~303 usuarios,
algunos sin empleo UPeU real, candidatos a archivar. La verificación READ-ONLY lo refuta:

**Descomposición de usuarios bajo orgs NO in-scope (26,904 total inicialmente alarmante):**
| Conjunto | Usuarios | Naturaleza | Acción |
|---|---|---|---|
| Estudiantes en orgs `EP-*` (academic-program canónicas) | 26,162 | árbol canónico de estudiantes (D6) — legítimo | ninguna (falso positivo de mi filtro inicial, que solo listaba las 133 admin) |
| Trabajadores en orgs legacy `AREA-N` con costCenter in-scope | 0 | — | (no hay; todos los in-scope ya migrados) |
| **Trabajadores en orgs legacy `AREA-N` con costCenter FUERA-scope** | **742** | **empleados UPeU activos reales** | **NO archivar — ver hallazgo** |

### Cruce de empleo (READ-ONLY) — sin Oracle directo
Oracle 11g R2 NO soporta python-oracledb thin mode (`DPY-3010`); PROD no tiene Instant Client. Cruce
alternativo equivalente: shadow vivo en el resource **Oracle LAMB Trabajadores v3**
(`6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21`, 16,326 shadows) = empleo reconocido por RR.HH.

**Resultado: 742/742 tienen shadow VIVO en Trabajadores v3 → TODOS son trabajadores UPeU activos
reales. CERO denominacionales puros a archivar.** (DNI = `name` del user, 8 dígitos.)

### HALLAZGO BLOQUEANTE — el scope de 133 áreas es INCOMPLETO
Los 742 trabajadores activos están en **178 áreas legacy** (su `costCenter`=ID_AREA) que NO están entre
las 133 in-scope del filtro CONNECT BY (addendum A.1), y cuyo shadow en el resource Org quedó `dead`
(0/178 con shadow Org vivo) tras el cambio de filtro de Fase 2. Es decir:

- El **recompute de Bloque E NO los reubicará** al árbol canónico (su costCenter no matchea ninguna de
  las 133 orgs in-scope con archetype).
- **NO son denominacionales** (tienen empleo activo) → NO se pueden archivar (regla del runbook:
  "Si una purga/saneo va a tocar usuarios activos, DETENTE").
- Las 178 áreas NO se pueden purgar (Fase 4) sin dejar 742 trabajadores activos huérfanos.

**Top costCenters afectados:** 7790(44), 7823(35), 7804(32), 7795(26), 4438(21), 7997(17), 4542(14),
4583(14), 787(10), 8007(9), 4520(9), 7799(9)... (178 áreas, todas `AREA-N` legacy sin archetype).

### DETENCIÓN — decisión requerida de Alberto (Fases 3/4 NO proceden con la premisa actual)
El filtro de scope (133 áreas, addendum A.1) excluye 178 áreas con 742 empleados activos. Antes de
archivar/purgar nada se requiere decidir:

1. **¿Son ent=7124 (UPeU) las 178 áreas?** Si SÍ → el filtro CONNECT BY debe AMPLIARSE para incluir
   áreas ent=7124 con trabajadores activos aunque no tengan `TIENEHIJO=1` (la condición EXISTS de
   trabajadores del filtro A.1 no las capturó — probable causa: el JOIN `ORG_SEDE_AREA` por
   `ID_SEDEAREA` no resuelve para estas áreas, o son áreas hoja sin la condición de hijo). Requiere
   re-consulta a Oracle LAMB (CONNECT BY + EXISTS revisado) — **solo ejecutable desde la LAN con un
   cliente Oracle thick (Instant Client) o sqlcl**, que PROD hoy NO tiene.
2. **Si son denominacionales pero con empleados UPeU "prestados"** → definir política (cuarentena
   `suspended` vs mantener bajo área especial "afines/denominacional con empleo UPeU").
3. **Ampliar las 133 → ~311 áreas** (133 + 178) y re-clasificar las nuevas con direct assignment
   (mismo mecanismo de Fase 2quater, ya validado).

**Recomendación:** ampliar el scope para incluir las 178 áreas (probable ent=7124 con trabajadores),
re-clasificarlas por direct assignment, y SOLO ENTONCES evaluar purga de lo que quede sin empleo. NO
archivar ningún trabajador activo. La parte de modelado (clasificación + saneo de stales de las 133)
está COMPLETA y es correcta; lo pendiente es una **decisión de scope de datos**.

### Estado de PROD tras Fase 3 (READ-ONLY, sin cambios)
- 0 cambios destructivos en Fase 3. 133/133 in-scope con archetype + árbol conexo (de Fase 2quater).
- Fase 4 (purga + recompute trabajadores) **NO ejecutada** — bloqueada por scope incompleto.
- Backups Fase 0 + 2 incrementales intactos.

---

# SECUENCIA FINAL (2026-05-29, sesión PM4) — criterio de gobernanza del usuario

Criterio: **contrato RR.HH. de UPeU (VW_APS_EMPLEADO.ID_ENTIDAD=7124 ACTIVO) = incluir; sin contrato UPeU = fuera.**

## PASO 1 — Dedup trabajadores.xml: contrato UPeU gana ✅
- `ROW_NUMBER() OVER (PARTITION BY e.COD_APS ORDER BY ...)`: añadido como **primer** criterio
  `CASE WHEN e.ID_ENTIDAD = 7124 THEN 0 ELSE 1 END ASC`. Commit `9434e1e`, push, git pull PROD,
  PUT resource HTTP 201, **test connection 15/15 success**.
- Verificación Oracle (sqlplus thick vía `gvenzl/oracle-free:slim --network host`) sobre los 742 DNIs:
  - 170 con *alguna* fila de contrato ID_ENTIDAD=7124 (mayoría histórica/inactiva).
  - **5 con contrato ID_ENTIDAD=7124 ACTIVO (ESTADO='A')** → recuperar. DNIs:
    **76575561, 41970870, 75240132, 72783226, 48636923.** Áreas 7124 de su contrato activo:
    58, 4342, 7997, 8232/7997, 102. (Dedup arreglada hace que su fila ganadora sea la 7124.)
  - 0 con contratos SOLO en 7124 (todos tienen además contratos denominacionales — por eso hoy caen
    en áreas denominacionales).
  - **737 = 742 − 5** sin contrato UPeU activo. Cuadre exacto con el brief.

## PASO 2 — Archivar los 737 ❌ BLOQUEADO: lifecycleState=archived NO es durable
- Mapeo 737 DNIs → 737 USER en MidPoint (`m_user.nameorig`=DNI), 1:1, 0 faltantes, los 737 `active`.
  5-keep confirmados active y 0 overlap con los 737.
- **PATCH `lifecycleState=archived` (no-raw, vía clockwork): HTTP 204 limpio en los 737, PERO la DB
  NO cambia — sigue `active`.** Diagnóstico canary:
  - PATCH no-raw → HTTP 204 → DB `active` (revertido por el template).
  - PATCH `?options=raw` → HTTP 204 → DB `archived` (persiste, salta el clockwork).
  - PATCH no-raw posterior sobre el ya-archived → HTTP 204 → **DB vuelve a `active`** (el clockwork
    re-deriva el estado).
- **Causa raíz:** `lifecycleState` es una propiedad **derivada por el object template**
  (UserTemplate-Person-Base, Bloque H `auto-archive-after-termination-grace-period`, strong). Bloque H
  solo archiva si `primaryAffiliation ∈ {staff,faculty}` **Y** hay `terminationDate` **Y** pasó el
  grace period. Los 737 **no tienen terminationDate** (tienen contrato denominacional vigente) → el
  template re-deriva `active` en cada recompute/recon. Además **los 737/737 tienen un shadow VIVO en
  el resource "Oracle LAMB Trabajadores v3"** (`6a91f7e1...`): MidPoint los reconoce como empleados
  activos y SIEMPRE los recomputará active mientras ese shadow exista.
- **Por qué NO se forzó con `raw`:** un `raw` archived sería un cambio **silenciosamente reversible**
  — el próximo recon/recompute de trabajadores (Fase 3 del orden canónico, o cualquier recompute-all)
  lo revertiría a active sin aviso. Anti-patrón. Regla del runbook: anomalía bloqueante → DETENER.

### DECISIÓN REQUERIDA DE ALBERTO antes de continuar (Pasos 3-6 NO proceden)
El "archivado" de los 737 no se logra con `lifecycleState` mientras tengan shadow vivo en Trabajadores
v3. El problema es de **fuente autoritativa**: el contrato denominacional vigente los mantiene en el
resultset del searchScript de Trabajadores v3 (que hoy NO filtra por ID_ENTIDAD). Opciones canónicas:

1. **Filtrar el searchScript de Trabajadores v3 por contrato UPeU** (`AND e.ID_ENTIDAD = 7124` en el
   baseQuery, o exigir que la fila ganadora del dedup sea 7124). Efecto: los 737 dejan de tener fila
   en LAMB-Trabajadores → su shadow pasa a `deleted` → reaction `inactivateFocus` → el usuario se
   desactiva/archiva **de forma durable y por el mecanismo IGA correcto** (no por PATCH manual).
   Los 5 con contrato UPeU activo permanecen (tienen fila 7124). **PREFERIDA** — alinea fuente
   autoritativa con el criterio de gobernanza; es reusable SciBack (el IGA solo gobierna empleo de la
   entidad tenant). Requiere: ¿deben además existir en MidPoint si tienen *otros* roles (alumni,
   investigador)? Si un DNI de los 737 es también alumni/estudiante activo, NO debe archivarse —
   su archetype/affiliation vendría de otra fuente. **Verificar antes.**
2. **Bloque H ampliado**: archivar también cuando el usuario pierde toda afiliación de empleo UPeU
   (no solo por terminationDate). Más invasivo en el template core; afecta a todos los leavers.
3. **Sacar del scope del IGA** vía exclusión por entidad en TODOS los resources de empleo (no solo
   org). Equivalente a (1) generalizado.

**Recomendación:** opción 1. Es coherente con Reality-vs-Policy (el shadow es la realidad; al quitar
la fila autoritativa, la realidad y la policy convergen en archived) y con el criterio del usuario
(sin contrato UPeU = fuera del IGA). Antes de aplicarla, verificar que ninguno de los 737 tenga una
afiliación activa NO laboral (alumni/estudiante/investigador) que justifique mantenerlo.

### Estado de PROD tras SECUENCIA FINAL Paso 2 (sin cambios durables)
- Dedup trabajadores.xml corregida + desplegada (commit `9434e1e`, PUT 201, test 15/15).
- 5-keep `active` (intactos). 737 `active` (NO archivados — PATCH no persiste). 467 orgs.
- 0 cambios destructivos. Backup final `/home/juansanchez/backup_org_final_20260529_1126.sql` intacto.
- Pasos 3 (recompute trabajadores), 4 (purga), 5 (verif), 6 (template) **NO ejecutados** — bloqueados
  por la decisión de fuente autoritativa anterior.

---

# SESIÓN PM5 (2026-05-29) — PASO A diagnóstico + PASO B salvaguarda → DETENCIÓN en PASO C

> Esta sesión NO ejecutó ningún cambio destructivo. Todo fue READ-ONLY (Oracle thick vía contenedor
> `gvenzl/oracle-free:slim` con `--entrypoint .../sqlplus`, y consultas psql en MidPoint).

## PASO A — Diagnóstico del gap del recon ✅

- **Resource Trabajadores v3 en DB (v230) SÍ tiene el filtro** `RN = 1 AND ID_ENTIDAD = 7124`
  (verificado en `m_resource.fullobject`). El reaction `deleted → inactivateFocus` está presente.
- **Universo real (Oracle, filtro exacto del searchScript):**
  - 16,329 COD_APS totales con contrato vigente.
  - **7,850 SOBREVIVEN** (`RN=1 AND ID_ENTIDAD=7124` — contrato UPeU es la fila ganadora del dedup).
  - **8,479 quedan FUERA** (fila ganadora de otra entidad denominacional).
- **Estado shadows Trabajadores v3 en MidPoint:** 14,625 LINKED + 1,348 DELETED(dead) + 353 UNLINKED + 1 DISPUTED.
- **Cruce LINKED vs supervivientes:** 7,496 LINKED matchean supervivientes; **7,129 LINKED quedarían FUERA**
  en un re-recon (pasarían a `deleted` → `inactivateFocus`).
- **Conclusión A:** el recon previo (17:00-18:00) NO completó el barrido — solo marcó 1,348 DELETED,
  dejando **7,129 LINKED de más** que el filtro debería expulsar. El gap (esperado ~4,329) era una
  subestimación; el universo real fuera es mayor.

## PASO B — Salvaguarda (BLOQUEANTE) ✅

Cruce de los 7,129 LINKED-fuera contra **afiliación académica vigente en Oracle** (fuente autoritativa:
`DAVID.VW_PERSONA_EGRESADO` ∪ `DAVID.VW_PERSONA_ALUMNO` = 97,085 DNIs):

| Conjunto | Usuarios | Acción |
|---|---|---|
| **Fuera CON afiliación académica vigente** (egresado/alumno en Oracle) | **3,524** | **NO ARCHIVAR — su IIA es académica** |
| Fuera SOLO laboral (sin afiliación académica) | **3,605** | candidatos legítimos a archivado |

- La salvaguarda por **archetype structural** de MidPoint solo veía 6 alumni (desactualizado);
  la salvaguarda por **fuente autoritativa Oracle** captura **3,524**. Crítico hacerlo por Oracle.
- Cruce contra shadows académicos vivos en MidPoint dio 0 (los resources Estudiantes/Egresados/Grados/
  Investigadores tienen shadows pero su link `m_ref_projection` a estos users está incompleto/roto) —
  **otra razón para usar Oracle como fuente de verdad de la salvaguarda, no los shadows MidPoint.**

## PASO C — DETENIDO (anomalía bloqueante confirmada empíricamente)

**Evidencia del daño ya causado por el recon previo:** de los 1,348 shadows DELETED, los users con owner
vivo quedaron **48 active/DISABLED + 2 archived/DISABLED**. De esos, **38 tienen afiliación académica
vigente** y archetype `archetype-user-alumni` — quedaron `administrativeStatus=DISABLED` **a pesar de
ser egresados activos**. Ejemplos: DNI 06288037, 42046651, 10268184, 44360114 (todos alumni en Oracle).

**Causa raíz de diseño:** el reaction `deleted → inactivateFocus` del resource Trabajadores v3 es
**INCONDICIONAL**. No distingue entre:
- un leaver puro (solo laboral) → desactivar es correcto, y
- un trabajador que ADEMÁS es alumni/student → su identidad persiste por otra IIA → NO debe desactivarse.

Re-correr el PASO C tal como está diseñado **desactivaría/archivaría a los 3,524 con afiliación
académica vigente** (mismo daño que sufrieron los 38, escalado ×90). Esto viola la salvaguarda
BLOQUEANTE del runbook ("nadie con afiliación académica activa se archiva") → **DETENGO y reporto, no
fuerzo** (regla operacional).

### Decisiones requeridas de Alberto antes de PASO C (opciones canónicas)

1. **Hacer condicional el `inactivateFocus`** del resource Trabajadores v3: el reaction `deleted` debe
   ejecutar `inactivateFocus` SOLO cuando el focus NO tiene otra afiliación activa (alum/student/
   researcher). Opciones de implementación:
   - (a) Reaction con `<condition>` que evalúe `affiliations`/`roleMembershipRef` del focus y se
     abstenga si hay afiliación no laboral. (Reality-vs-Policy: la fila Trabajadores desaparece, pero
     la policy del focus se mantiene por su otra afiliación.)
   - (b) En vez de `inactivateFocus`, usar reaction que solo **desproyecte la cuenta Trabajadores**
     (unlink/delete shadow) y deje que el object template (J3 + Bloque H) decida el `lifecycleState`
     final por `primaryAffiliation` recalculada. Bloque H solo archiva staff/faculty; alum/student
     quedarían `active`. **PREFERIDA** — delega la decisión de lifecycle al template canónico (mecanismo
     IGA correcto), en línea con best-practices §1.2 ("lifecycle se sincroniza desde la IIA").
2. **Reparar los 38 ya dañados:** recompute (no-raw) de esos 38 users tras aplicar el fix (1) — el
   template re-derivaría `primaryAffiliation=alum` → administrativeStatus correcto. NO usar PATCH raw.
3. **Confirmar el set de archivado real:** tras el fix, solo los **3,605 solo-laborales** deben
   desactivarse/archivarse vía el mecanismo IGA (shadow deleted → template decide). Verificar que ninguno
   de los 3,605 adquiera afiliación académica entre ahora y la ejecución (re-cruce inmediato pre-recon).

**Recomendación:** opción 1(b) — desacoplar la baja de la cuenta Trabajadores de la baja de la identidad,
dejando que el object template (J3/Bloque H) gobierne el `lifecycleState` por afiliación. Es el patrón
canónico SciBack (un leaver de empleo NO es un leaver de identidad si tiene otra afiliación activa) y
evita re-cablear lógica de afiliación en cada resource.

### Estado de PROD tras sesión PM5
- **0 cambios destructivos.** Solo lecturas (Oracle + psql). Tablas temporales `tmp_survive`, `tmp_fuera`,
  `tmp_fuera_dni`, `tmp_acad` creadas en DB para el análisis (no afectan datos de negocio; se pueden
  dropear). Backups Fase 0 + incrementales intactos.
- 14,625 LINKED / 1,348 DELETED sin cambio. 38 users con afiliación académica siguen `DISABLED`
  (daño pre-existente del recon previo, pendiente de reparar en PASO C corregido).
- PASOS C/D/E/F **NO ejecutados** — bloqueados por la decisión de diseño del reaction `inactivateFocus`.

---

# SESIÓN PM6 (2026-05-29) — Opción 1b IMPLEMENTADA (PASO 1 ✅ + PASO 2 ✅) → DETENCIÓN en PASO 3

> Skills consultadas: `midpoint-best-practices` §1.2 (lifecycle desde IIA), §4.2 (mappings relativos
> por provenance), Cap.9 focus processing; `iga-canonical-standards` (ISO 24760 lifecycle). Opción 1b
> aprobada por Alberto.

## PASO 1 — Reaction condicional + template gobierna lifecycle ✅ (desplegado en PROD)

Tres ediciones canónicas (commits `[ver git log]`):

1. **`upeu/resources/oracle-lamb/trabajadores.xml`** — reaction `deleted`: `inactivateFocus` →
   **`unlink`**. Solo desproyecta la cuenta Trabajador; NO desactiva el focus. El object template
   gobierna el `lifecycleState` final por afiliación recalculada (Reality-vs-Policy).
   PUT REST 201 + Test connection 10/10 success.

2. **`UserTemplate-Person-Base.xml` `leaver-disable-on-terminationdate`** — ahora **condicional a
   `primaryAffiliation ∈ {staff,faculty}`** y retorna **ENABLED explícito** (no null) cuando NO
   corresponde desactivar, para sobrescribir el `administrativeStatus=DISABLED` huérfano dejado por
   `inactivateFocus` previo. Ex-trabajador que es alumni/student → ENABLED.

3. **`UserTemplate-Person-Base.xml` Bloque H2 (nuevo)** — `H2-archive-on-total-affiliation-loss`:
   archiva durablemente al ex-trabajador que perdió TODA afiliación (terminationDate presente, sin
   alum/student/affiliate). **Salvaguarda BLOQUEANTE codificada en la condición**: con cualquier
   afiliación válida → `return false` (NO archiva). Bloque F: guard cede a H2 (en vez de draft)
   cuando hay terminationDate y sin afiliación.

**Cómo gobierna el template el lifecycle (validado):** Caso `06288037` (jubilado, alum, term=2025-07-31)
recompute no-raw → **active / ENABLED / ENABLED** ✓. El template repara correctamente al ex-trabajador
que es alumni.

## PASO 2 — Reparación de los alumni dañados ✅

- El daño real eran **104** alumni `active/DISABLED` (no 38) — causados por `inactivateFocus` previo +
  `leaver-disable-on-terminationdate` incondicional.
- 103/104 reparados → `active` + `ENABLED` (51 vía recompute por el template, 52 vía PATCH
  `administrativeStatus=enabled` para los egresados PUROS sin terminationDate que el mapping condicional
  no cubre).
- **1 caso NO reparable por PATCH** (`21835727`, OID `1609b661-...`): tiene **dual structural archetype**
  (alumni + employee-faculty) preexistente → cualquier modify lanza PolicyViolation "only a single
  structural archetype supported". Jubilado (motivo=jubilacion, term=2024-12-31, primAff=alum). Es un
  caso de saneo dual-archetype histórico (ver MEMORY), NO causado por esta sesión. Pendiente de
  reparación específica (remover assignment/archetypeRef faculty residual).
- Estado alumni final: 26,403 active(null) + 3,455 active/ENABLED + 692 draft + 2 archived + 1 DISABLED.
  Los 692 draft son egresados sin personalNumber/documento válido (Bloque F gate), no daño de sesión.

## PASO 3 — DETENIDO: salvaguarda académica BLOQUEANTE inviable con el estado actual de proyecciones

**Hallazgo bloqueante (datos duros, READ-ONLY):**

- Premisa de opción 1b: al desproyectar Trabajador, el template ve `affiliations` SIN `staff/faculty`
  pero CON `alum/student` para los egresados → los protege (H2 no archiva). Esto requiere que el
  egresado tenga su afiliación académica poblada en el FOCUS.
- **Realidad en PROD:** los **3,524 trabajadores-fuera que son egresados en Oracle** (set a PROTEGER,
  cruce `tmp_fuera_dni ∩ tmp_acad`):
  - 3,524/3,524 existen en MidPoint.
  - **0/3,524 tienen shadow Egresado** (resource `6a91f7e1-...e23`).
  - Su archetype actual: 3,465 employee-staff + 4 faculty + 2 alumni → su `affiliations` contiene
    SOLO `staff/faculty`, **NO `alum`**.
- **Las poblaciones shadow Trabajador-vivo (14,625) y Egresado-vivo (30,651) son DISJUNTAS: 0 overlap.**
  El recon Egresados nunca proyectó/correlacionó a estos trabajadores-egresados.

**Consecuencia:** si se re-corre PASO 3 ahora, los ~7,129 trabajadores-fuera pasan a deleted→unlink;
los 3,524 egresados pierden su única afiliación (`staff/faculty`) → `affiliations` vacío → Bloque H2
los ARCHIVA. **Se archivarían 3,469 egresados que deben permanecer active como alumni → violación de
la salvaguarda BLOQUEANTE.** Regla operacional: anomalía bloqueante → DETENGO y reporto, NO fuerzo.

### Decisión requerida de Alberto antes de PASO 3 (orden canónico de poblamiento)

La salvaguarda del template (Bloque H2) es correcta, pero solo protege a quien tiene `alum/student` en
su focus. ANTES del re-recon Trabajadores hay que POBLAR la afiliación académica de los 3,524. Opciones:

1. **Investigar por qué el recon Egresados no correlacionó a los 3,524 y corregirlo**, luego re-correr
   Egresados (y/o Estudiantes) para que adquieran shadow Egresado + `affiliations=alum`. Recién entonces
   re-correr Trabajadores. **PREFERIDA** — alinea con el orden canónico (MEMORY: "inputs → recompute →
   recons adicionales → RECIÉN baja"). Reusable SciBack.
   - Hipótesis a verificar: ¿la `VW_PERSONA_EGRESADO` los devuelve? ¿el correlator por DNI choca con
     el shadow Trabajador? ¿el reaction `unlinked→link` no añadió la 2ª proyección?
2. **Poblar `affiliations=alum` directamente desde Oracle** (cruce DNI) sin esperar shadow Egresado,
   como dato puente, y luego re-correr Trabajadores. Más rápido pero deja la realidad (shadow) desfasada
   de la policy (affiliation) — anti Reality-vs-Policy. NO preferida.
3. **Salvaguarda dura adicional en H2 por lista Oracle** (no archivar si DNI ∈ tmp_acad). Tactical
   patch, no canónico (acopla el template a una tabla temporal). NO preferida.

**Recomendación:** opción 1. El re-recon Trabajadores NO procede hasta que los egresados-trabajadores
tengan su afiliación `alum` poblada en MidPoint (vía su mecanismo IIA correcto = recon Egresados).

## Estado de PROD tras PM6
- **Cambios desplegados (durables, canónicos):** trabajadores.xml reaction `unlink` (PUT 201) +
  UserTemplate-Person-Base con leaver condicional + Bloque H2 (PUT 201). Test connection 10/10.
- **Cambios de datos:** 103 alumni reparados a active/ENABLED. 0 archivados de más. 0 destructivo.
- Backups: `bkp_focus_20260529_1557.dump` (738M, m_user/m_shadow/m_assignment/refs) +
  `backup_org_final_20260529_1126.sql` (completo) en `/home/juansanchez/`.
- **Disco PROD estaba al 100%** — liberado a ~83% (borrados backups intermedios prerecon/stale + copias
  en container `/tmp`). Vigilar: 57G total es ajustado para esta DB (17G) + backups.
- PASOS 3-6 **NO ejecutados** — bloqueados por la salvaguarda académica (3,524 egresados sin afiliación
  `alum` poblada). Tablas tmp_* de PM5 conservadas (necesarias para el análisis/poblamiento).

---

# SESIÓN PM7 (2026-05-29) — Causa raíz del bloqueo PM6 hallada: IDENTIDAD DUPLICADA, no solo correlación → DETENCIÓN

> Skills consultadas: `midpoint-best-practices` §2.1 (Reality vs Policy), §4.4-4.5 (correlación/focus
> processing), §8 (correlator); `iga-canonical-standards` §1.3 (IIA — un identificador de correlación
> por persona). Orden canónico del brief: recon Egresados ANTES de Trabajadores. **Solo PASO 0 + PASO 1
> ejecutados; PASO 1 reveló una anomalía bloqueante estructural → DETENGO antes de PASO 2.**

## PASO 0 — Disco ✅
84% (9.0G libres), bajo el umbral del runbook. Liberado a **76% (14G libres)**: `docker image prune`
(0B, capas compartidas) + backup fresco `bkp_pre_correlation_recon_20260529_1622.dump` (745M, custom
format: m_user/m_shadow/m_assignment/m_ref_projection/archetype/role_membership/parent_org/m_org) +
retiro de 2 SQL planos superados (`backup_org_canonical_0811` + `backup_org_final_1126`, 5.4G). Backups
de seguridad vigentes: `bkp_pre_correlation_recon_20260529_1622.dump` + `bkp_focus_20260529_1557.dump`.

## PASO 1 — Diagnóstico de por qué los 3,524 no tienen `alum` + fix de correlación

### Hallazgo 1 — descomposición fina del set a proteger (READ-ONLY Oracle thick + psql)
Los **3,524** ex-trabajadores con afiliación académica (PM5 `tmp_fuera_dni ∩ tmp_acad`) se descomponen
por afiliación **vigente**:
| Subconjunto | N | Afiliación vigente | Resource que lo cubre |
|---|---|---|---|
| Egresados (`VW_PERSONA_EGRESADO`) | **1,996** | `alum` (permanente) | Egresados v3 |
| Alumnos matriculados vigentes (resultset estricto Estudiantes, sem 279/267) | **121** | `student` | Estudiantes v3 |
| Ex-alumnos sin matrícula vigente ni egreso (solo en `VW_PERSONA_ALUMNO`) | **1,407** | **ninguna vigente** | **NINGUNO** |

`VW_PERSONA_ALUMNO` es catálogo demográfico de personas-alumno, NO prueba de matrícula vigente.

### Hallazgo 2 — desajuste de correlador entre resources (causa parcial)
- **Trabajadores v3** correlaciona/identifica por `extension/upeu:lambDocNum` (NUM_DOCUMENTO crudo). Su
  `dni-to-taxId-urn` está **deprecado/archived** → NO puebla `sb:taxId`.
- **Egresados v3 / Estudiantes v3** correlacionan SOLO por `extension/sb:taxId` (URN).
- Los 1,996/3,524 tienen `taxId` VACÍO pero `lambDocNum` poblado → el correlador académico por taxId
  NO los enlaza al user-trabajador.

**Fix desplegado (commit `[ver git log]`, durable, canónico, reusable SciBack):** en `egresados.xml` y
`estudiantes.xml` se añadió (a) inbound `num-documento-to-lambDocNum` (beforeCorrelation, strong,
idéntico a trabajadores.xml) y (b) correlador adicional `correlate-by-lambDocNum`. PUT 201 ambos,
**test connection 15/15** ambos. `lambDocNum` único en los 1,996 (0 duplicados → sin DISPUTED).

### Hallazgo 3 (BLOQUEANTE) — la causa raíz real es IDENTIDAD DUPLICADA, no el correlador
Al correr el recon Egresados (PASO 1), el shadow CODIGO `8510323` (DNI `00074909`) quedó **LINKED**,
pero a un user **`8510323`** (name=CODIGO, archetype `archetype-user-alumni`, `affiliations=["alum"]`,
`taxId=urn:...:00074909`) — **NO** al user-trabajador `00074909` (name=DNI, archetype
`employee-staff`, sin alum). **Existen DOS users para la misma persona.**

Causa: el recon Egresados histórico, al no encontrar al trabajador por taxId, ejecutó
`unmatched → addFocus` y **creó un user nuevo** con name=CODIGO. Mi fix por lambDocNum no lo resuelve
porque el user-duplicado-egresado **no tiene lambDocNum poblado** (solo taxId), de modo que el recon
re-enlaza el shadow a su gemelo duplicado preexistente, no al trabajador.

**Magnitud (psql):**
- Total m_user: 54,805 → **40,821 con name=CODIGO** (numérico largo) + 13,979 name=DNI(8).
- 30,651 shadows Egresado tienen owner; **4,847 de esos owners son DUPLICADOS confirmados** (existe
  otro user con name=DNI para el mismo DNI del taxId).
- **Los 1,996 del set a proteger: 1,996/1,996 tienen un user-duplicado egresado** (name=CODIGO, alum).

### Consecuencia y DETENCIÓN
Re-correr Trabajadores (PASO 2) ahora archivaría a los 1,996 trabajadores (siguen sin `alum`; su gemelo
alumni queda aparte) → **fragmenta la identidad y viola la salvaguarda académica**. El recon Egresados
fue **SUSPENDIDO** sin daño (0 trabajadores archivados/desactivados por él; 0 users nuevos creados;
m_user 54,805 estable; shadows-con-owner 30,651 estable). DETENGO en PASO 1 y reporto (regla del runbook).

### Decisión requerida de Alberto antes de PASO 2 — consolidación de identidad duplicada
El fix de correlación (lambDocNum) es necesario y queda desplegado, pero **insuficiente**: el bloqueo
real es ~4,847 (potencialmente más entre los 40,821 name=CODIGO) identidades duplicadas
trabajador↔egresado. Opciones canónicas:

1. **Consolidar (merge) las identidades duplicadas:** para cada par (user-DNI trabajador, user-CODIGO
   egresado del mismo DNI), fusionar en UNA identidad. MidPoint tiene `mergeObjects` (REST/UI). El user
   superviviente debería ser el de name=DNI (identificador canónico de persona; el CODIGO es
   identificador de matrícula, no de persona). Tras merge: el shadow Egresado queda linkeado al user
   único, los inbounds pueblan `alum`, y el archetype lo resuelve el template (J3: faculty>staff>alum).
   **PREFERIDA** — alinea con identidad única por persona (iga-canonical §1.3) y resuelve la raíz.
   Requiere: definir reglas de merge (qué atributo gana), probar en piloto, ejecutar por lotes con
   backup. Es trabajo de saneo de datos considerable (~5K+ pares).
2. **Poblar `lambDocNum` en los user-CODIGO-egresado** desde su taxId (extraer DNI del URN) para que el
   correlador por lambDocNum unifique en futuros recons — NO resuelve la duplicación ya existente (dos
   users seguirían), solo evita crear más. Insuficiente solo.
3. **Cambiar la reaction `unmatched` de Egresados/Estudiantes de `addFocus` a sin-acción** (o
   `createOnDemand` controlado) para NO crear users desde estos resources — Egresados/Estudiantes solo
   deberían ENRIQUECER identidades existentes, no crearlas (¿es Trabajadores/MOISES la IIA de creación
   de persona?). Decisión de gobernanza: ¿qué resource es autoritativo para la CREACIÓN del focus
   persona? Si es uno solo, los demás no deben `addFocus`. Esto previene duplicación futura pero requiere
   merge (1) para la existente.

**Recomendación:** combinar (1) consolidación de los duplicados existentes + (3) revisar qué resources
pueden crear focus (definir IIA de creación de persona única) para que no reaparezcan. NO se puede
proceder al PASO 2 (re-recon Trabajadores) ni a PASO 4 (purga) hasta consolidar — de lo contrario se
archivarían trabajadores cuya afiliación alum vive en un user gemelo separado.

## Estado de PROD tras PM7
- **Cambios desplegados (durables, canónicos):** `egresados.xml` + `estudiantes.xml` con correlador
  adicional por `lambDocNum` + inbound `num-documento-to-lambDocNum` (PUT 201, test 15/15). Commit pusheado.
- **Cambios de datos:** 0 destructivos. Recon Egresados corrió ~5,365/30,653 items y fue SUSPENDIDO; no
  creó users ni archivó/desactivó a nadie (re-correlacionó shadows a sus owners ya existentes).
- Recon Egresados (`86c3766a`) queda SUSPENDED. Tablas tmp_* (PM5/PM6) + `tmp_egr1996` conservadas.
- Disco 76% (14G libre). RAM 7.5G disp. Backups: `bkp_pre_correlation_recon_20260529_1622.dump` +
  `bkp_focus_20260529_1557.dump`.
- PASOS 2-5 **NO ejecutados** — bloqueados por identidad duplicada trabajador↔egresado (~4,847+ pares).

> **Anti-patrón / lección SciBack (PM7):** múltiples resources de persona con reaction `unmatched →
> addFocus` y correladores por identificadores DISTINTOS (taxId vs lambDocNum) generan identidades
> duplicadas cuando una persona aparece en >1 fuente y no comparten el identificador de correlación.
> Canónico: (a) UN identificador de correlación de persona unificado entre todos los resources (el
> documento crudo), (b) definir explícitamente qué resource(s) pueden CREAR el focus persona (IIA de
> creación) — los enriquecedores no hacen `addFocus`.
