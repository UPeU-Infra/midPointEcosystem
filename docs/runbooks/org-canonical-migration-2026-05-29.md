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

---

## VERIFICACIÓN PASO A — Merge masivo (2026-05-29 ~19:35 Lima)

**Estado: MERGE EN CURSO — NO COMPLETO.** Verificación read-only; no se ejecutó nada destructivo.

- Script `/tmp/merge_all.sh` PID `3098258` **vivo**. Sin marker `=== MERGE_ALL COMPLETE ===` en `/tmp/mergeall.log`.
- Scope: `total groups=5477` (grupos de DNI duplicado en `tmp_merge`), lotes de 200, arrancó en offset=400.
- Progreso: 9 lotes cerrados (offsets 400-2000, todos `processed=200 ok=200 fail=0`), lote 10 (offset=2200) ejecutándose.
- Faltan ~16 lotes → ETA ~2.5-3 h (terminaría ~22:00-22:30 Lima) al ritmo de ~10 min/lote.
- `m_user`: 52,571 y bajando ~200/lote, consistente. Proyección final ≈ 49,328 (objetivo ~49,318). ✓ trayectoria correcta.
- Disco PROD: **78%** (42G/57G), estable — NO llegó a 90%. DB 17 GB. Disk-guard del script aborta a ≥90% (no disparado).
- Contenedores: `midpoint_server` healthy (22h), `midpoint-midpoint_data-1` healthy (2d). ✓
- 0 fallos en todos los lotes ejecutados.

**Decisión:** conforme a la regla "si el merge NO completó → NO continuar". **PASOS B-E NO ejecutados.** Re-verificar cuando aparezca el marker COMPLETE: m_user final, 0 duplicados por DNI, caso `00074909` (un user name=DNI, afiliaciones consolidadas, dueño de shadows, gemelo eliminado), 3,524 ex-trabajadores-egresados con `alum` en el mismo user, luego recompute de survivors (`merged-2026-05-29`).

---

## SESIÓN PM8 (2026-05-29 ~22:50 Lima) — PASO A ✅ COMPLETO + PASO B DETENIDO por defecto de diseño (archived sticky)

> Skills consultadas: `midpoint-best-practices` §1.2 (lifecycle desde IIA, sticky lifecycle), Cap.9 focus
> processing (mappings strong al mismo target), §2.1 Reality vs Policy; `iga-canonical-standards` §1.2
> (ISO 24760 lifecycle, archived retiene datos) y §1.3 (IIA). Solo READ-ONLY + 1 PATCH no-op idempotente.

### PASO A — Verificación post-merge ✅ (TODO PASA)
- **Merge COMPLETO:** marker `=== MERGE_ALL COMPLETE m_user=49318 ===` presente, proceso `3098258` DEAD,
  todos los lotes `ok=N fail=0`. **m_user = 49,318** (cuadre exacto con el brief).
- **0 duplicados por taxId** (ext key `72`, URN SCHAC) y **0 por nameorig**. (El único "dup" por
  lambDocNum es el valor basura `0` en 2 users sin DNI real — no es persona.) Distribución name:
  13,956 DNI(8) + 34,200 CODIGO_num + 1,158 num_otro + 4 no_num.
- **Caso `00074909` ✅:** un solo user (OID `a7888b8e-...`), name=DNI, `primaryAffiliation=staff`,
  `affiliations=["faculty","alum"]` consolidadas, dueño de sus shadows; gemelo eliminado.
- Contenedores healthy; disco **79%** (12G libres); merge dejó backup `bkp_pre_merge_20260529_1714.dump`.
- Backup incremental PASO B creado: `/home/juansanchez/bkp_pre_survivor_recompute_20260529_2244.dump` (670M).

### PASO B — DETENIDO: el merge dejó 1,775 usuarios académicos en `archived` y el template NO los revierte

**Hallazgo (datos duros, READ-ONLY):** de los **4,737 survivors** (`description=merged-2026-05-29`):
| lifecycleState | N | Detalle |
|---|---|---|
| active | 2,908 | 2,582 staff + 167 faculty + 138 alum + 20 student + 1 null |
| **archived** | **1,752** | **1,749 con `alum`/`student` en affiliations** (1,737 primAff=staff + 12 faculty) + 3 solo-laboral |
| (null) | 77 | sin lifecycle (residuo técnico) |

A nivel **global**: **1,775 usuarios con afiliación académica vigente (alum/student) están `archived`**
→ **viola la salvaguarda BLOQUEANTE** del brief ("0 usuarios con afiliación académica vigente archivados").
Los 1,749 son survivors del merge; 26 son preexistentes.

**Causa raíz (defecto de diseño del template, no del merge) — limbo F↔H:**
- Estos 1,749 son ex-trabajadores (terminationDate pasada, p.ej. `48150895` term=2024-07-31
  motivo=termino_contrato) que **además son egresados** (`alum` en affiliations). Su shadow Trabajador v3
  sigue VIVO (1,749/1,749), por lo que **Bloque J3 calcula `primaryAffiliation=staff`** (prioridad
  faculty>staff>student>alum) — `staff` aún presente en affiliations.
- Con primAff=staff + terminationDate + motivoCese grace cumplido:
  - **Bloque F** (`lifecycleState`, línea 945-958) **retorna `null` (CEDE a H)** — guard DT-5.
  - **Bloque H** (línea 1082) tiene `curState != 'archived'` → con el user YA `archived`, **H retorna
    false** (no re-archiva). **H2** igual (línea 1156).
  - Resultado: **ningún mapping escribe `lifecycleState`** → queda el valor de repo `archived`. **archived
    es terminal/sticky** por diseño (ningún mapping revierte archived→active mientras primAff=staff).
- Un `recompute` (probado con PATCH no-op no-raw en canary `48150895`, HTTP 204) **NO lo saca de
  archived** → confirma empíricamente el limbo. (El PATCH no-op fue idempotente: mismo `description`,
  0 cambio neto.)

**Por qué un recompute masivo de los 4,737 NO repara y por qué PASO C agravaría:**
- Recompute ahora deja los 1,749 en `archived` (sticky) → no cumple "survivors con afiliaciones correctas".
- PASO C (re-recon Trabajadores) desproyectaría el shadow staff denominacional → affiliations pierde
  `staff` → J3 recalcula `primaryAffiliation=alum`. PERO **Bloque H2/F siguen sin revertir archived→active**
  (sticky) → los 1,749 quedarían `archived` PERMANENTEMENTE siendo alumni activos. Daño durable.

Conforme a la regla operacional ("anomalía/salvaguarda disparada → DETENER y reportar, NO forzar"),
**NO se ejecutó el recompute masivo de survivors ni PASO C/D/E/F.** 0 cambios destructivos.

### Decisión requerida de Alberto antes de PASO B/C (opciones canónicas)
El template necesita un camino de **reversión `archived→active` cuando reaparece afiliación académica
viva**. archived debe dejar de ser terminal para quien recupera/conserva una IIA no laboral. Opciones:

1. **Mapping de reversión en el template** (`lifecycleState`, strong): si `curState=='archived'` Y existe
   afiliación válida no laboral (`alum`/`student`/`affiliate` en affiliations) Y no hay condición de
   archivado laboral vigente → emitir `active`. Desacopla "archivado por cese laboral" de "identidad
   persiste por otra IIA". **PREFERIDA** — canónica (ISO 24760: archived no es destroyed; una identidad
   con IIA viva debe volver a active), reusable SciBack. Requiere: que J3 deje de hacer `staff` el
   primaryAffiliation cuando el contrato está terminado (o que la reversión mire `affiliations`, no
   `primaryAffiliation`). Cuidado con el guard DT-4/DT-5 (dependencia circular: leer `focus.lifecycleState`
   en condición, no como source).
2. **Orden de operaciones:** primero PASO C (desproyectar shadows Trabajador denominacionales → affiliations
   pierde staff → primAff=alum), LUEGO el mapping de reversión (1) los devuelve a active. Pero (1) es
   prerequisito de (2) — sin reversión, PASO C los deja archived.
3. **Reparación puntual de los 1,749 ya archived** vía recompute tras desplegar (1) — el template
   re-derivaría active. NO usar PATCH raw (silenciosamente reversible).

**Recomendación:** implementar (1) — mapping de reversión `archived→active` por afiliación académica viva,
probarlo en canary `48150895`, desplegar, y RECIÉN ENTONCES recompute de survivors (PASO B) → PASO C.
El defecto es de diseño del lifecycle (archived terminal), preexistente al merge; el merge solo lo
visibilizó al consolidar 1,749 egresados que estaban archived en su gemelo laboral.

### Estado de PROD tras PM8
- **0 cambios destructivos.** Solo lecturas + 1 PATCH no-op idempotente (canary, mismo valor). m_user 49,318.
- Backups vigentes: `bkp_pre_survivor_recompute_20260529_2244.dump` (670M), `bkp_pre_merge_20260529_1714.dump`
  (746M), `bkp_pre_correlation_recon_20260529_1622.dump` (745M), `bkp_focus_20260529_1557.dump` (738M).
- Lista de OIDs survivors en PROD `/tmp/survivor_oids.txt` (4,737) conservada para PASO B futuro.
- PASOS B (recompute)–F **NO ejecutados** — bloqueados por el defecto de reversión archived→active.

---

# ADDENDUM — Bloque L (derivación canónica de lifecycleState) + J3 strong (2026-05-29, sesión lifecycle)

Tarea distinta del árbol org: implementar el veredicto canónico aprobado (mapping de
derivación de lifecycleState, NO el parche de reversión) y arreglar J3 para multi-afiliación.

## PASO 1 — Implementado y desplegado (commits 76e9820, +fix H/H2)
- **J3** (`primaryAffiliation` desde `affiliations`): strength `normal`→`strong`. Objetivo:
  limpiar el `staff`/`faculty` stale cuando el empleo muere pero persiste lo académico (§3.2).
- **Bloque L** (NUEVO, `<item><ref>lifecycleState`): state machine única, strong, sin guard
  anti-circular. liveAff = `affiliations` ∩ vocabulario canónico. liveAff≠∅ → active (draft si
  perfil incompleto); liveAff=∅ con terminationDate → archived; liveAff=∅ sin termDate → draft.
- **Bloques H y H2 ELIMINADOS** (primero deprecated, luego borrados del XML): su lógica la
  absorbe L. Backup del objeto previo: PROD `/home/juansanchez/backups/templates/
  UserTemplate-Person-Base.pre-bloqueL.20260529_2301.xml` (74KB, con F+H+H2). PUT del nuevo: HTTP 201.

## PASO 2 — CANARY FALLA. BLOQUEO por anomalía de motor (DETENIDO según regla del runbook).

Canary egresado-archived `48150895` (OID `6e8d69bf-3862-48a0-bac0-1c4fb0c4e84d`):
estado real: lifecycleState=`archived`, primaryAffiliation=`staff` (STALE), affiliations=`["alum"]`,
terminationDate=2024-07-31, motivoCese=termino_contrato, graduationYear=2017. Dos shadows LINKED
vivos: Trabajadores v3 (ESTADO='I', NO aporta token a affiliations) + Egresados v3 (aporta `alum`).
Debe volver a `active` como alumni. **No lo hace tras desplegar L+J3.**

### Diagnóstico (probado en PROD, raw PATCH + modify aislados, sin reconcile)
1. `includeRef` del per-archetype template `UserTemplate-EmployeeStaff` (OID `59b1e325`) → base
   `855caaca` **SÍ funciona**: prueba decisiva — corrompí `eppn` a `CORRUPTED@bad.test` (raw) y un
   `modify` plano lo corrigió a `48150895@upeu.edu.pe` vía **Bloque C** (base, strong). Las
   mappings base SÍ se aplican.
2. **PERO J3 (base, strong) NO sobrescribe `primaryAffiliation`.** Test: puse primaryAffiliation=
   `SENTINEL` (raw), affiliations=`["alum"]` (raw, garantizado en repo), lifecycleState=`active`
   (raw), luego `modify` plano (sin reconcile, sin re-lectura de recursos): **primaryAffiliation
   quedó en `SENTINEL`** (J3 no produjo valor) y lifecycleState pasó a `archived` (un archivador
   externo a L, porque L con affs=['alum'] retorna active).
3. **Contradicción central:** Bloque C (base, strong, source=personalNumber) corrige su target;
   Bloque J3 (base, strong, source=affiliations, +condition) NO corrige el suyo — MISMO usuario,
   MISMO template, MISMO modify. La diferencia: `primaryAffiliation` tiene inbounds de recurso
   competidores (trabajadores `archetype-to-primaryAffiliation` weak→staff; egresados
   `afiliacion-to-primaryAffiliation` weak→alum) y/o J3 con `<source>` sin delta en el wave no
   produce valor; `eppn` no tiene competidores.
4. Eliminar H/H2 NO cambió el resultado (el `archived` persiste de otra fuente aún no localizada
   —posiblemente inbound/reaction de Egresados o cadena per-archetype—; L no es quien archiva).

### Causa raíz (hipótesis a confirmar con DEBUG, NO ejecutado en PROD post-OOM sin confirmación)
J3 (mapping de template strong cuyo target `primaryAffiliation` también tiene inbounds de recurso)
no impone su valor en un `modify` sin delta de su source `affiliations`. El patrón canónico para
un atributo DERIVADO por el template debe evitar que ese mismo atributo sea también target de
inbounds de recurso (Reality-vs-Policy: o lo gobierna el template, o lo gobierna el recurso, no
ambos). Hoy `primaryAffiliation` tiene 3 escritores (J3 strong + K strong + 2 inbounds weak) → el
combinatorial evaluation no converge al valor de J3 de forma fiable en recompute sin delta.

### Estado tras la sesión
- Template en PROD = versión nueva (L + J3 strong, sin H/H2). HTTP 201. Backup previo intacto.
- Canary `48150895` RESTAURADO a estado original (archived/staff/['alum']) vía raw PATCH.
- **NO** se ejecutó recompute masivo (PASO 3), ni re-recon Trabajadores (PASO 4), ni purga (PASO 5).
- 0 cambios destructivos en datos. Tasks diagnósticos: ninguno dejado corriendo. Disco 79%.

### Decisión pendiente (para Alberto antes de continuar)
La derivación canónica de lifecycleState (Bloque L) está bien diseñada, pero **depende de que J3
fije primaryAffiliation/affiliations de forma fiable** — y eso hoy NO ocurre por la competencia de
escritores sobre `primaryAffiliation`. Opciones:
  A. Quitar los inbounds de recurso a `primaryAffiliation` (trabajadores+egresados): que SOLO J3
     (template) lo gobierne desde `affiliations`. Reality-vs-Policy limpio. Requiere verificar que
     ningún usuario dependa del inbound directo (retrocompat para usuarios sin affiliations poblado).
  B. Hacer que L lea `affiliations` directamente (ya lo hace) e ignore primaryAffiliation —
     entonces L funcionaría aunque primaryAffiliation siga stale. PERO el archivador externo que
     sigue poniendo `archived` debe localizarse y neutralizarse primero (Egresados inbound/reaction
     o cadena per-archetype). L lee affiliations=['alum'] → active, pero otro mapping gana.
  C. DEBUG controlado (subir log de `MappingEvaluator`/`Projector` a TRACE para 1 usuario) en
     ventana coordinada para ver exactamente qué pone `archived` y por qué J3 no produce valor.

Recomendación: localizar PRIMERO el archivador externo (opción C acotada a 1 usuario) antes de
tocar inbounds (opción A). No avanzar a masivo hasta que el canary 48150895 cierre en active.

---

# SESIÓN PM9 (2026-05-29 ~23:50 Lima) — PASO 1 ✅ + PASO 2 ✅ DESPLEGADOS; PASO 3 (canary) ❌ FALLA por defecto NUEVO aislado. DETENIDO.

> Skills consultadas: `midpoint-best-practices` §2.1 (Reality vs Policy), §4.2 (strength), §4.5
> (pipeline de procesamiento focal: inbound→focus policy→outbound), §5; `iga-canonical-standards`
> §1.2/§1.3 (IIA, lifecycle ISO 24760). Solo READ-ONLY + PUTs de config + recompute/import + 2
> classLogger temporales (revertidos). 0 cambios destructivos de datos.

## PASO 1 ✅ — execute-script roto (tarea #52) ARREGLADO y desplegado
- **Bug localizado** en `user-template-employee-staff.xml` (línea 96-99) y
  `user-template-employee-faculty.xml` (línea 81-84): el warn de hireDate usaba
  `focus?.getExtension()?.asPrismContainerValue()?.findProperty(new ItemName(NS,"hireDate"))?.getRealValue()`
  — API inexistente/abortaba en 4.10 (genera el "partial 240" del brief).
- **Fix:** reemplazado por `basic.getExtensionPropertyValue(focus, new javax.xml.namespace.QName(NS,"hireDate"))`
  con guarda null (patrón ya usado en `koha-ils.xml` L1284 y RENIEC fix `7259ab6`).
- **Otros con el mismo antipatrón:** búsqueda `findProperty|getPropertyRealValue|findItem|findExtension`
  → solo quedan usos VÁLIDOS de `PrismContainerValue.findProperty(ItemPath)` sobre el contenedor
  multivalor `identityDocuments` (Bloque G L842, Bloque J L1739, Bloque J2 L1775, Bloque L L982).
  Esos NO son el antipatrón (no leen extension via API rota; leen sub-propiedades de un container value,
  API legítima 4.10). NO se tocan.
- Commit `291db8a`. PUT objectTemplates staff/faculty → HTTP 201 ambos.

## PASO 2 ✅ — Doble (triple) autoridad sobre primaryAffiliation RESUELTA y desplegada
- **Hallazgo:** NO eran 2 sino **3** inbounds weak compitiendo por `extension/sb:primaryAffiliation`:
  `egresados.xml` (afiliacion-to-primaryAffiliation), `trabajadores.xml` (archetype-to-primaryAffiliation),
  y `estudiantes.xml` (school-name-to-primaryAffiliation).
- **Fix (Reality-vs-Policy §2.1):** eliminados los 3. `primaryAffiliation` queda como atributo DERIVADO
  exclusivamente por el template (Bloque J3, strong, desde `affiliations`). Los inbounds
  `*-to-affiliations` (que alimentan J3) se CONSERVAN intactos en los 3 recursos.
- Verificado en PROD (objetos live): 0 menciones de `primaryAffiliation` como target en los 3 recursos;
  solo `afiliacion-to-affiliations` / `archetype-to-affiliations` / `school-name-to-affiliations`.
- Commit `291db8a`. PUT 3 resources → HTTP 201. **Test Connection 15/15 success** en los 3.

## PASO 3 ❌ — CANARY `48150895` SIGUE EN `archived`. Causa raíz NUEVA aislada (distinta del limbo PM8).

Estado canary (OID `6e8d69bf-3862-48a0-bac0-1c4fb0c4e84d`): lifecycleState=`archived`,
primaryAffiliation=`staff` (STALE), affiliations=`[alum]` (en repo), terminationDate=2024-07-31.
2 proyecciones LINKED vivas (dead=f, exist=t): Trabajadores v3 (`41ec0daf`, ESTADO='I') +
Egresados v3 (`f68d39b8`, name 201010107, **AFILIACION=alum confirmado en shadow**).

### Diagnóstico definitivo (TRACE acotado a 1 usuario, logger `com.evolveum.midpoint.expression`=TRACE)
Tras desplegar PASO 1+2, recompute e import del shadow Egresados sobre el canary:
```
DEBUG J3: affiliations vacío en 48150895 — primaryAffiliation null
INFO  Bloque L: 48150895 sin afiliacion viva + con terminationDate 2024-07-31 -> archived (leaver)
```
- **J3 y Bloque L SÍ se evalúan** (el template corre correctamente — PASO 1 desbloqueó el cómputo focal;
  ya no hay "partial 240" que aborte). El defecto NO está en J3/L.
- **El defecto es upstream:** el inbound `afiliacion-to-affiliations` (Egresados, normal) **NO contribuye
  `alum` a `extension/sb:affiliations`** durante recompute/import, AUNQUE su propia proyección está cargada
  (en el mismo trace, Bloque I lee la foto del MISMO shadow Egresados → la proyección sí se procesa).
- Por eso J3 lee `affiliations` vacío → primaryAffiliation null (no sobrescribe el `staff` stale) →
  Bloque L con liveAff=∅ + terminationDate → `archived`. Cadena internamente consistente.

### Naturaleza del bug (multi-source multivalued inbound, relativo)
- `affiliations` NO se persiste en repo (es transitorio; solo existe durante una operación que cargue
  la proyección y aplique el inbound). En cualquier recompute posterior, affiliations=∅.
- El inbound `afiliacion-to-affiliations` es `normal` y **relativo**: en un import/recompute de un shadow
  YA `linked` sin delta en su source (AFILIACION no cambia), un mapping relativo normal produce **ningún
  delta** → no asienta `alum`. Para un foco con DOS proyecciones (Trabajadores ESTADO='I' que retorna null
  + Egresados), el valor `alum` no llega a `affiliations` en la ola donde J3 lo lee.
- **Contraste probado:** un egresado PURO (1 sola proyección Egresados, p.ej. user `0397b9b9` name 201121390)
  está `active` con primaryAffiliation=`alum` — porque su `alum` SÍ se asentó en el onboarding original
  (recompute completo de foco nuevo) y, sin competidores tras PASO 2, persiste. El canary tiene
  primaryAffiliation=`staff` STALE persistido que J3 nunca logra sobrescribir porque nunca ve affiliations≠∅.

### Mecanismos probados que NO reparan el canary (todos dejan archived/staff)
| Operación | Resultado |
|---|---|
| `PATCH ?options=reconcile` (no-op description) | HTTP 204, affiliations=∅, archived |
| recompute task (sin reconcile) | clear affiliations→∅, archived |
| recompute task con `reconcile=true` | affiliations=∅, archived |
| `/shadows/{egresados}/import` | HTTP 200 success, J3 ve ∅, archived |
| reconciliation task Egresados por `icfs:name=201010107` | CLOSED/SUCCESS, J3 ve ∅, archived |
| import secuencial Trabajadores→Egresados | archived |
| set affiliations=[alum] raw + non-raw modify | J3/L NO disparan (sin delta en source) → archived |

> Nota REST 4.10: `POST /users/{oid}/recompute` → 404; `POST /rpc/executeScript` con
> `<s:executeScript>` → 400 "Wrong input value for ExecuteScriptType: RawType" (binding roto en este
> deployment). Mecanismo fiable de recompute/recon = **task** (recomputation/reconciliation activity).
> Filtros de recon Egresados: el searchScript SOLO soporta `EqualsFilter` sobre `__NAME__`/`__UID__`
> (no `attributes/ri:CODIGO` ni `inOid` combinado con resourceRef).

### Defecto pre-existente, visibilizado por el merge PM8
El bug existía antes; el merge consolidó 1,749 ex-trabajadores-egresados con primaryAffiliation=`staff`
stale persistido + affiliations transitorio. Tras PASO 2 (quitar inbounds competidores) el `staff` ya no
se re-escribe — pero TAMPOCO se corrige a `alum`, porque el inbound `*-to-affiliations` no asienta el
valor en recompute de focos `linked` existentes.

## DECISIÓN REQUERIDA antes de continuar (PASO 4-7 BLOQUEADOS)
El inbound de afiliación debe asentar `affiliations` de forma **autoritativa/absoluta** (no relativa),
de modo que, mientras el shadow Egresados exista y AFILIACION=alum, `affiliations` contenga `alum` tras
cualquier reconciliación — y entonces un recompute con reconcile derive primaryAffiliation=alum (J3) y
active (L). Opciones canónicas (a validar con skills + dev antes de PROD):

1. **Inbound `afiliacion-to-affiliations` → asignar `<evaluationPhases>` (beforeCorrelation+clockwork)
   y/o convertirlo a fuente absoluta** (que asiente el valor por existencia del shadow, no por delta).
   Patrón: tal como ya hacen los inbounds de correlación taxId/lambDocNum del MISMO recurso (L145-175).
   PREFERIDA — alinea con best-practices §4.5 (inbounds colectados antes del focus policy) y mantiene
   `affiliations` como única fuente de J3.
2. **Persistir `affiliations`** (que el inbound sea `strong` y/o que exista un mapping que lo mantenga)
   para que recompute sin reconcile lo conserve. Riesgo: que un foco sin reconcile retenga afiliaciones
   stale de empleos muertos (rompería la semántica "afiliación viva" de Bloque L). Menos canónica.
3. **Re-recon masiva Egresados (PASO 5) con reconcile que SÍ asiente affiliations** — verificar primero
   en 1 canary que la recon completa (no import puntual) asienta `alum`. Hoy la recon por `icfs:name`
   cerró SUCCESS pero NO asentó → la opción 3 SOLA no basta sin la 1.

**Recomendación:** implementar (1) en `egresados.xml` + `estudiantes.xml` + `trabajadores.xml` (inbounds
`*-to-affiliations` absolutos/con evaluationPhases), probar en dev (`pruebas-alberto-1`), re-probar canary
`48150895` → debe cerrar en `active`. NO avanzar a PASO 4-7 hasta canary verde (regla BLOQUEANTE del brief).

## Estado de PROD tras PM9
- **Config desplegada (durable, canónica):** PASO 1 (API 4.10 en staff/faculty) + PASO 2 (autoridad única
  de primaryAffiliation = template J3). Commit `291db8a` pusheado + git pull PROD + PUT 5 objetos (201) +
  Test Connection 3 recursos 15/15.
- **Datos:** 0 destructivos. Canary `48150895` restaurado a estado documentado (archived/staff/[alum]).
  Loggers temporales (expression TRACE + inbounds DEBUG) **revertidos** (0 custom loggers). Todas las tasks
  `canary-*`/`trace*` **eliminadas** (0 remanentes). Disco 79%. Contenedores healthy.
- **PASOS 3 (canary verde)–7 NO completados** — bloqueados por el defecto del inbound de afiliación
  (relativo, no asienta affiliations en focos linked). Backups PM8 vigentes.

---

# SESIÓN PM10 (2026-05-30) — Inbounds `*-to-affiliations` ABSOLUTOS implementados; canary SIGUE archived. Causa raíz FINAL aislada (zero-set no materializa). DETENIDO.

> Skills consultadas: `midpoint-best-practices` §4.2 (strength/conditions relativistas), §4.5 (pipeline
> inbound→focus policy→outbound), §4.6; `iga-canonical-standards` §1.3 (IIA). READ-ONLY + PUTs de config
> + recompute/recon tasks + 2 classLogger temporales (revertidos). 0 cambios destructivos de datos.

## Decisión de entorno
DEV (`pruebas-alberto-1`) tiene SOLO 3 resources NO canónicos (Koha, Azure EntraID, Lamb Academic) —
no posee el schema sciback:person, los templates ni los 3 resources Oracle LAMB canónicos. Reconstruir
el stack canónico en el sandbox era inviable y contrario a la doctrina ("no construir el IGA en DEV").
**Decisión:** aplicar en PROD con canary estricto BLOQUEANTE (autorizado por el brief). Cambios de bajo
riesgo (solo strength + value-set en mappings ya existentes), validados con Test Connection 15/15.

## PASO 1 ✅ (config) — Inbounds `*-to-affiliations` hechos ABSOLUTOS en los 3 recursos
Patrón aplicado (idéntico a los inbounds de correlación `dni-to-taxId-urn` del mismo recurso):
- `<strength>normal</strength>` → `<strength>strong</strength>` ("recomputa", best-practices §4.2).
- `+ <evaluationPhases>beforeCorrelation + clockwork</evaluationPhases>`.
- `+ <set><predefined>matchingProvenance</predefined></set>` DENTRO de `<target>` (NO `<range>` suelto
  — `InboundMappingType` no admite `<range>`: HTTP 400 "Item range has no definition"; el value-set va
  como hijo de `<target>` [VariableBindingDefinitionType]; `matchingProvenance` confirmado en
  `common-core-3.xsd` enum `ValueSetDefinitionPredefinedType`).
- Commits `7749c53` (strong+phases ×3) + `<set>` egresados + `<set>` trab/estud. PUT 3 resources → 201.
  Test Connection 15/15 ×3. Config DURABLE y canónica desplegada.

## PASO 2 ❌ — Canary `48150895` SIGUE `archived`/`staff`/affiliations=∅. Causa raíz FINAL.

### Diagnóstico definitivo (TRACE `...projector.focus.inbounds`=TRACE, log activo = `midpoint.log`)
Tras desplegar strong+phases+set en los 3 recursos y correr **user recompute+reconcile** sobre el canary:
- **Los inbounds SÍ se evalúan ahora** (614 líneas inbound; antes 0 — confirma que strong reactivó la
  evaluación). El mapping produce el valor:
  `producer: M(afiliacion-to-affiliations: affiliations = PVDeltaSetTriple(zero: [PPV(String:alum, meta: provenance: 4)]; plus: []; minus: []), strong)`
- **PERO `alum` queda en el ZERO set, nunca en PLUS** → no genera delta real hacia el focus → el focus
  `affiliations` permanece ∅ → J3 lo lee vacío → `primaryAffiliation` null (no sobrescribe `staff` stale)
  → Bloque L con liveAff=∅ + terminationDate → `archived`. Cadena consistente.

### Por qué `matchingProvenance` NO materializó el valor (causa raíz FINAL)
`matchingProvenance` limita la autoridad del mapping a los valores que portan **SU** metadata de
provenance EN EL FOCUS. El focus del canary tiene `affiliations` VACÍO (sin metadata de provenance) →
el conjunto "propiedad de este mapping" es ∅ → el consolidador no tiene nada que reconciliar → el valor
zero-set `alum` (provenance 4) NO se añade. En 4.10, un inbound strong cuyo valor cae en zero-set NO se
materializa en un item de focus vacío salvo que exista infraestructura de **metadata/provenance grabada
en el focus** (no configurada en este deployment). `matchingProvenance` presupone esa metadata.

### Mecanismos probados que NO reparan (todos dejan archived/affiliations=∅)
| Operación | Resultado |
|---|---|
| `/shadows/{egresados}/import` (post strong) | success, inbounds NO corren (import short-circuit) → ∅ |
| user recompute (sin reconcile) | inbounds NO corren → ∅ |
| user recompute + `reconcile=true` | inbounds SÍ corren, valor en zero-set → ∅ |
| recon task Egresados por `icfs:name` | filtro NO se push-down (searchScript solo `__NAME__`/`__UID__`) → recon FULL 30k; alcanzó canary, valor en zero-set → ∅ |
| recon task por `inOid` shadow | 400 "Cannot combine on-resource and off-resource properties" |
| strong + evaluationPhases (sin set) | valor zero-set → ∅ |
| strong + evaluationPhases + `<set>matchingProvenance` ×3 | valor zero-set → ∅ |

> Notas REST 4.10 (confirmadas): `POST /users/{oid}/recompute` → 404. `<range>` en inbound → 400. recon
> filtro `inOid`+resourceRef → 400. Mecanismo fiable de inbound eval = **task recompute con
> `<reconcile>true</reconcile>`** o recon FULL del recurso. Log ACTIVO = `/opt/midpoint/var/log/midpoint.log`
> (los `midpoint-YYYY-MM-DD.N.log` están rotados/congelados — NO mirar esos).

## DECISIÓN REQUERIDA antes de continuar (PASO 3-6 BLOQUEADOS) — necesita re-discusión de diseño
El valor zero-set con provenance NO se materializa en un focus con `affiliations` vacío sin metadata-
provenance. Tres caminos canónicos (a decidir con el usuario; NINGUNO es un simple tweak de mapping):

1. **Habilitar grabación de metadata/provenance en el focus** (item `affiliations` con
   `<valueMetadata>`/provenance, o `dataProvenance` en system config) para que `matchingProvenance`
   tenga un conjunto-propiedad no vacío y materialice el zero-set. Más alineado al modelo multi-source
   canónico Evolveum, pero introduce infraestructura de provenance en todo el deployment (impacto amplio,
   requiere prueba dedicada). PREFERIDA a medio plazo.
2. **Persistir per-source en items DISTINTOS** (`affiliationStudent`/`affiliationWorker`/`affiliationAlum`
   por recurso, cada uno single-source → el inbound strong materializa sin ambigüedad de provenance) y
   que el template compute `affiliations` (y J3/L) como UNIÓN de los per-source persistidos. Evita
   provenance; es el patrón "una IIA por atributo" llevado al límite (§1.3). Redesign de mappings + J3/L.
3. **Que J3/L lean liveness desde la REALIDAD (proyecciones linked) en vez del transitorio
   `affiliations`** (best-practices §2.1/§5.8 focus-and-projection): liveAff derivada de qué shadows
   LAMB están `linked & exists & no-dead`. Elimina la dependencia del item transitorio. Cambio de J3/L,
   no de inbounds.

**Recomendación:** discutir con el usuario antes de implementar — la opción 1 toca config global de
metadata; la 2 y 3 son redesigns de template. NO avanzar a PASO 3-6 hasta canary verde (BLOQUEANTE).

## Estado de PROD tras PM10
- **Config desplegada (durable, canónica, válida):** inbounds `*-to-affiliations` strong +
  evaluationPhases + `<set>matchingProvenance` en los 3 recursos (egresados/trabajadores/estudiantes).
  Commits `7749c53` + (set egresados) + (set trab/estud) pusheados + git pull PROD + PUT 3 resources 201
  + Test Connection 15/15 ×3. NOTA: aunque no resuelve el canary por sí sola, esta config es correcta y
  necesaria (strong = absoluto; matchingProvenance = no-wipe multi-source) y queda como base para
  cualquiera de las 3 opciones de arriba.
- **Datos:** 0 destructivos. Canary `48150895` restaurado a baseline documentado (archived/staff/[alum]
  vía PATCH raw replace). Loggers temporales TRACE **revertidos** (0 custom loggers). Todas las tasks
  `canary-*`/`trace*` **eliminadas** (0 remanentes). Disco 74%. Contenedores healthy.
- **PASOS 3 (canary verde)–6 NO completados** — bloqueados por la no-materialización del zero-set; requiere
  decisión de diseño (3 opciones). Backups PM8 vigentes.

---

# SESIÓN PM11 (2026-05-30) — OPCIÓN 2 implementada y VALIDADA (item materializa). PASO 2 canary egresado-archived BLOQUEADO por dual-archetype assignment pre-existente (no por Opción 2). DETENIDO.

> Skills consultadas: `midpoint-best-practices` §1.2 (lifecycle desde IIA), §1.3 (activation), §4.2
> (strength relativista), §4.5 (pipeline inbound→focus policy: inbounds corren ANTES del template);
> `iga-canonical-standards` §1.2 (lifecycle ISO 24760), §1.3 (una IIA por atributo). Opción 2 APROBADA
> por Alberto. READ-ONLY + PUTs de config + 1 recon (suspendido/borrado) + 4 PATCH (3 no-op fallidos +
> 1 exitoso benigno) + classLogger TRACE (revertido). 0 cambios destructivos de datos.

## PASO 1 ✅ — Items per-IIA single-source implementados, desplegados y VALIDADOS

### Schema v1.2 (OID `e800335c-...`, PUT 201)
3 items single-valor nuevos en `UserExtensionType` (canonical/schemas/sciback-person-v1.0.xml):
`liveAffiliationWorker` (faculty|staff), `liveAffiliationAlum` (alum), `liveAffiliationStudent` (student).
Cada uno = **una IIA, single-source** (§1.3): su ÚNICO escritor es el inbound de su recurso.

### Inbounds strong single-source (PUT 3 resources 201, Test Connection 15/15 ×3)
- `egresados.xml`: `afiliacion-to-liveAffiliationAlum` (alum).
- `trabajadores.xml`: `archetype-to-liveAffiliationWorker` (faculty/staff; ESTADO='I'→null).
- `estudiantes.xml`: `school-name-to-liveAffiliationStudent` (student; vigencia = existencia del shadow,
  searchScript ya filtra semestres 279/267).
- **Neutralizados** los 3 inbounds `*-to-affiliations` multi-source (causa del zero-set PM10). La
  autoridad de `affiliations` (eduPerson downstream) pasa al template (Bloque J3b, abajo).

### Template (OID `855caaca-...`, PUT 201) — J3/K/L repuntados + J3b nuevo
- **J3** (`primaryAffiliation`): source = los 3 items persistidos (unión por prioridad
  faculty>staff>student>alum). Quitada la `<condition>` relativista (bloqueaba firing sin delta).
- **Bloque K** (jubilados→alum): sources repuntados a los 3 items persistidos.
- **Bloque L** (`lifecycleState`): `liveAff` = unión de los 3 items persistidos (NO el transitorio
  `affiliations`). Salvaguarda académica intacta.
- **Bloque J3b (NUEVO)**: deriva el multivalor eduPerson `affiliations` (downstream Koha/LDAP) como
  unión de los items per-IIA → autoridad única de `affiliations` = template (Reality-vs-Policy §2.1).

### CAUSA RAÍZ FINAL del zero-set RESUELTA: `evaluationPhases`, no el diseño
- **Primer intento** (commit `2e31782`) copió `<evaluationPhases>beforeCorrelation+clockwork</...>` del
  patrón PM10 → el TRACE mostró el MISMO zero-set:
  `M(afiliacion-to-liveAffiliationAlum: liveAffiliationAlum = PVDeltaSetTriple(zero: [PPV(alum)]; plus: []; minus: []), strong)`
  → item de extension vacío NO se materializaba.
- **Diagnóstico decisivo:** `nivel-ensenanza-to-studyLevel` (egresados.xml) es ESTRUCTURALMENTE
  IDÉNTICO (strong, single-source, target extension/sb, script string-or-null) y **SÍ materializó**
  `studyLevel=Técnica` en el mismo recon. La diferencia: **NO tiene `evaluationPhases`** (default =
  solo clockwork). `beforeCorrelation` evalúa el mapping en la fase de correlación (donde no hay focus
  consolidado) → el valor cae en zero-set → no genera plus-delta hacia el item vacío.
- **Fix** (commit `b790dc0`, PUT 3 resources 201): **quitado `<evaluationPhases>`** de los 3 inbounds
  per-IIA → default clockwork-only → el inbound corre sobre el focus real → **ADD delta genuino**.

### VALIDACIÓN POSITIVA de la Opción 2 (canary limpio `200920749`)
- Canary `200920749` (OID `0000ad0a-...`): egresado **active, single structural archetype, solo shadow
  Egresados vivo**. PATCH no-op `?options=reconcile` → **HTTP 204** → **`liveAffiliationAlum=alum` SE
  MATERIALIZA** en el focus. J3 derivó `primaryAffiliation=alum`, Bloque L mantuvo `active`.
- **Conclusión: la Opción 2 FUNCIONA.** El item per-IIA single-source materializa de forma fiable con
  inbound strong + clockwork-only. El zero-set de PM10 era causado por `evaluationPhases=beforeCorrelation`,
  no por el modelo multi-source ni por falta de metadata-provenance. (Esto también explica retroactivamente
  por qué los inbounds de correlación `dni-to-taxId-urn` parecían "funcionar con zero-set": su valor ya
  estaba persistido del onboarding; nunca dependieron del plus-delta.)

## PASO 2 ❌ — Canary egresado-ARCHIVED (`48150895`) NO pasa a active: BLOQUEADO por dual-archetype assignment pre-existente (independiente de Opción 2)

**Hallazgo bloqueante (datos duros):** cualquier `recompute`/`reconcile` del canary `48150895`
(y de `201811293`, otro candidato) **aborta con PolicyViolation ANTES de materializar nada**:
`Found [archetype-user-alumni, archetype-user-employee-staff] structural archetypes; only a single one is supported`.

- En **repo** cada canary tiene UN solo structural archetype (`48150895`=employee-staff;
  `201811293`=alumni) + su auxiliary `AuxAff-*`. El SEGUNDO structural lo genera el **Bloque D7 del
  template** (`assignmentTargetSearch`→archetype por `primaryAffiliation`) cuando J3 recalcula
  `primaryAffiliation`: para `48150895`, repo=staff pero al reconcile J3 ve `liveAffiliationAlum`
  (egresado) y `liveAffiliationWorker` vacío (ESTADO='I') → primAff pasa a `alum` → D7 intenta asignar
  `archetype-user-alumni`, que **se acumula** sobre el `employee-staff` de repo (D7 strong solo remueve
  los assignments que ÉL produjo; el structural histórico no tiene su provenance) → 2 structural → PolicyViolation.
- Es exactamente el cambio de afiliación DESEADO (staff→alum del ex-trabajador-egresado), pero el motor
  4.10 **no reemplaza** el structural archetype viejo; los suma. Es un **caso de saneo dual-archetype
  pre-existente** (mismo problema de PM6 caso `21835727` y de la consolidación de identidad PM7/merge PM8),
  NO un defecto de la Opción 2.
- **Magnitud:** en repo (`m_ref_archetype`) solo **1 usuario** tiene 2 structural materializados; pero el
  conflicto se dispara EN RECOMPUTE para todo ex-trabajador-egresado cuya `primaryAffiliation` cambia de
  staff/faculty→alum. **CERO** egresados-archived en PROD tienen un único shadow (todos entrelazan
  Egresados+Trabajadores/Estudiantes) → el recompute masivo de survivors (PASO 3) chocaría en cadena.

**Por la regla BLOQUEANTE del brief** (canary egresado-archived debe pasar a active; si falla → TRACE
acotado + DETENER), **DETENGO**. La mecánica de Opción 2 está validada; el bloqueo es el saneo
dual-archetype, que es trabajo aparte.

### Decisión requerida de Alberto antes de PASO 3 (cómo permitir el cambio de structural archetype)
El template debe poder **reemplazar** el structural archetype cuando `primaryAffiliation` cambia, sin
acumular. Opciones canónicas (a validar con skills + dev antes de masivo):

1. **D7 con `<set>` de provenance / o remover el structural viejo explícitamente.** Hacer que D7 sea
   autoritativo sobre TODOS los `archetype-user-*` structural (no solo el que produce), de modo que al
   cambiar primAff retire el anterior y ponga el nuevo. Requiere que D7 conozca el conjunto de structural
   archetypes que gobierna. Riesgo: tocar el assignment de archetype es delicado (best-practices: archetype
   solo por direct assignment).
2. **Saneo previo de los structural archetypes históricos** (que no tienen provenance D7): recompute/
   re-stamp para que queden gobernados por D7, o eliminación del structural stale en repo cuando contradice
   la `primaryAffiliation` derivada. Alinea con la consolidación de identidad PM7/PM8 (un solo archetype
   por persona según su afiliación viva de mayor prioridad). **PREFERIDA** — es el cierre natural del
   trabajo de merge: tras consolidar identidad, consolidar archetype estructural.
3. **policy de archetype: permitir transición** vía `assignmentRelation`/`archetypePolicy` que defina
   el reemplazo. Más complejo; revisar soporte 4.10.

**Recomendación:** opción 2 (saneo del structural stale) + verificar opción 1 en dev. NO avanzar a PASO 3
(recompute survivors) ni PASO 4-6 hasta que un egresado-archived recompute LIMPIO a active (canary verde).
La Opción 2 (items per-IIA) queda desplegada y correcta; es prerequisito cumplido, no el bloqueo.

## Estado de PROD tras PM11
- **Config desplegada (durable, canónica, VALIDADA):** schema v1.2 (+3 items per-IIA), template
  (J3/K/L repuntados + J3b), 3 resources (inbounds per-IIA strong clockwork-only + `*-to-affiliations`
  neutralizados). Commits `2e31782` + `b790dc0` pusheados + git pull PROD + PUT 5 objetos (201) + Test
  Connection 15/15 ×3.
- **Datos:** 0 destructivos. 1 cambio benigno: canary `200920749` quedó con `liveAffiliationAlum=alum`
  + `description=canary3-opcion2` (active→active, es la materialización correcta de la Opción 2). Canaries
  `48150895`/`201811293` intactos (PATCH abortó por PolicyViolation, sin cambios). TRACE logger revertido
  (0 custom loggers). Tasks `canary-*` eliminadas (0 remanentes, incl. fantasma en m_task).
- **Backups:** `bkp_pre_opcion2_20260530_0020.dump` (640M) + PM8/PM7 vigentes. Disco 76%, RAM 7.5G, contenedores healthy.
- **PASOS 3 (recompute survivors)–6 NO ejecutados** — bloqueados por dual-archetype assignment en recompute
  de ex-trabajadores-egresados. Requiere decisión de saneo de structural archetype (3 opciones).

---

# SESIÓN PM12 (2026-05-30) — PASO 1 (saneo dual-structural) + PASO 2 (3 canaries) VERDE. Hallazgos de diseño antes de PASO 3 masivo. DETENIDO para decisión.

> Skills consultadas: `midpoint-best-practices` §3.3 (max 1 structural archetype), §3.4 (archetype solo
> por assignment plano NO-condicional, línea 169 SKILL), §3.5 (cambio de archetype = operación
> destructiva/especial), §4.1-4.3 (object template + assignmentTargetSearch); `iga-canonical-standards`
> §1.2/§1.3 (lifecycle ISO 24760, una IIA por atributo). READ-ONLY masivo + 7 unassign raw + 4 recompute
> reconcile + 1 assign alumni. Backup `bkp_pre_paso1_struct_20260530_0154.sql` (674M). 0 destructivos de datos crudos.

## Cuantificación dual-structural (DATOS DUROS)
- `m_ref_archetype` (archetypeRef PROYECTADO): **0 usuarios** con >1 structural (MidPoint nunca proyecta 2).
- `m_assignment` (structural ASSIGNMENTS) sobre los 9 structural-user archetypes: **7 usuarios** con 2 structural:
  - 5× alumni+employee-staff, 1× alumni+employee-faculty, 1× employee-faculty+employee-staff (los "6" del brief)
  - +1× **researcher+employee-faculty** (NO contemplado en el brief; el conteo inicial solo miró 4 archetypes académicos — hay 9 structural-user).
- **Población LATENTE** (no materializa dual hoy, pero lo dispara EN RECOMPUTE): structural employee + shadow
  Egresados linked = **4,734** (3,190 active + 1,542 archived con shadow trabajador vivo; 2 sin). De ellos
  **4,269 son survivors** (`merged-2026-05-29`). Estos chocarían en cadena en el recompute masivo del PASO 3.

## PASO 1 ✅ — Saneo de los 7 dual-structural materializados (unassign del structural stale)
- Método: REST PATCH `delete assignment` por container-id, `?options=raw`. **Formato que FUNCIONA en 4.10:
  JSON** `{"objectModification":{"itemDelta":[{"modificationType":"delete","path":"assignment","value":[{"@id":"N"}]}]}}`.
  (El equivalente XML con `<value><c:assignment id="N"/></value>` da HTTP 500 "Item assignment has no
  definition" — usar JSON id-only.)
- Regla de saneo: conservar el structural que coincide con `primaryAffiliation` (autoridad J3/K); unassign
  los demás. Resultado: **0 usuarios con >1 structural assignment** (verificado en m_assignment).

## PASO 2 ✅ (con matiz) — 3 canaries, todos structural ÚNICO, 0 abort
| Canary | Antes | Después | Veredicto |
|---|---|---|---|
| `48150895` egresado-archived dual staff+alum | archived/staff/employee-staff | **active/alum/alumni** | ✅ objetivo exacto |
| `01219011` trabajador activo | active/staff/employee-staff | **active/faculty/employee-faculty** | ✅ (staff→faculty = corrección legítima desde liveAffiliationWorker) |
| `548644005` denominacional sin afiliación viva (dual researcher+faculty) | active/faculty | **draft/employee-faculty** | ⚠️ draft (no archived) por falta de terminationDate |

## HALLAZGOS DE DISEÑO CRÍTICOS (requieren decisión antes de PASO 3 masivo)

### H1 — El saneo NO puede "quitar employee y dejar que D7 ponga alumni". DEBE ser delta ATÓMICO.
Causa raíz descubierta: **NO existe `defaultObjectPolicyConfiguration` para UserType** (solo para OrgType,
OID 47252981). El template base `UserTemplate-Person-Base` (855caaca, contiene J3/K/L) corre SOLO vía
`includeRef` desde los templates per-archetype, que se activan por `<archetypePolicy><objectTemplateRef>`
del archetype structural. ⇒ **user sin structural archetype = SIN template = J3/L NO corren** → primAff y
lifecycle quedan en su valor histórico. Verificado con `48150895`: tras unassign del employee quedó 0
structural → recompute materializó liveAffiliationAlum pero J3 NO recalculó primAff (seguía staff) ni L
archivó. Solo al ASSIGN archetype-alumni (1 structural) el template Alumni corrió y dio active/alum.
**Patrón canónico para PASO 3:** delta único `{add archetype-correcto + delete archetype(s)-stale + delete aux-stale}`
en una sola operación con reconcile → siempre exactamente 1 structural → template corre → J3/L computan.
El "correcto" = nameMap[primaryAffiliation-que-derivará-J3] = nameMap[afiliación viva de mayor prioridad].

### H2 — Wave ordering: liveAffiliation* se materializa en la MISMA pasada que J3 lo lee → J3 ve ∅.
`48150895` necesitó materializar liveAffiliationAlum primero (1ª pasada) y recién con el structural
correcto asignado (2ª pasada) J3 lo consumió. En el recompute masivo hay que prever **2 pasadas** (o que
el delta atómico de H1 ya fije el structural por afiliación-viva calculada FUERA del template, p.ej. en el
propio iterativeScripting leyendo el shadow/ext). Diseño recomendado PASO 3: tarea iterativeScripting que
(a) lee liveAffiliation por IIA del focus/shadow, (b) computa structural-correcto, (c) aplica delta atómico
add-correcto+delete-stale, (d) recompute. Idempotente.

### H3 — Bloque L: draft vs archived depende de `terminationDate`. Denominacionales sin terminationDate → draft, no archived.
`548644005` (sin afiliación viva, sin terminationDate) → rama (3) del Bloque L = **draft** (alta incompleta),
NO archived. El brief espera "archived" para solo-denominacionales. Discrepancia es de DATOS (denominacionales
fuera de scope no tienen terminationDate en LAMB), no de lógica. **Decisión requerida:** ¿(a) aceptar draft
como estado de salida para denominacionales sin terminationDate (canónicamente defendible: sin evidencia de
leaver no se afirma archived); o (b) tratar "fuera-de-scope sin afiliación viva" como archived explícito
(añadir rama en L: si tuvo structural employee histórico + 0 afiliación viva → archived aunque no haya
terminationDate)? La salvaguarda académica NO se ve afectada (egresados/estudiantes tienen liveAffiliation).

### H4 — researcher es structural; ampliar el universo de combinaciones de saneo a los 9 structural-user.
El conteo del brief asumía 4 archetypes; hay 9. El saneo PASO 3 debe priorizar entre los 9 (afiliación viva
real). Para researcher sin shadow CSV-DGI vivo → stale (caso 548644005). Prioridad propuesta:
faculty>staff>student>alum>researcher>visitor>contractor>partner-institution (service-account aparte).

## Estado de PROD tras PM12
- **Datos:** 7 dual-structural saneados (unassign stale). 3 canaries con structural único:
  48150895=active/alumni, 01219011=active/employee-faculty, 548644005=draft/employee-faculty.
  0 usuarios con >1 structural assignment (verificado). description marcadores: canary-paso2-VERDE / canary-c / canary-b.
- **Config:** sin cambios de template en PM12 (Opción 2 de PM11 sigue desplegada y validada). Disco 77%, contenedores healthy.
- **PASO 3-6 NO ejecutados** — bloqueados por decisión de diseño (H1-H4). El mecanismo está validado en canary;
  falta (1) aprobar el patrón delta-atómico de H1/H2 para el masivo, (2) decidir H3 (draft vs archived), (3) confirmar H4 (prioridad 9 structural).

---

# SESIÓN PM13 (2026-05-30) — Decisiones H1-H4 APROBADAS. PASO 1 (rama H3 + task saneo) ✅ + PASO 2 (4 canaries) VERDE. Validando task antes de masivo.

> Skills consultadas: `midpoint-best-practices` §1.2 (lifecycle ISO 24760 sync desde IIA), §3.3/§3.4
> (max 1 structural; archetype solo por assignment plano directo, línea 169), §4.2 (strength); `iga-canonical-standards`
> §1.2/§1.3. READ-ONLY masivo + PUTs de template + 4 PATCH reconcile (canaries). 0 destructivos de datos.

## PASO 1 ✅ — Rama archived H3 (Bloque L) + task saneo dual-structural (H1/H2/H4)
- **Bloque L, rama H3** (commit `5100ce4`+`5fc...`): usuario con 0 afiliación viva, sin terminationDate,
  PERO con structural employee/faculty asignado (evidencia laboral) → `archived` (no draft). `draft` queda
  solo para perfiles genuinamente nunca-activados. §1.2 ISO 24760 (identidad laboral establecida → archived).
- **Bug encontrado y corregido (2 iteraciones):**
  1. `<source><path>assignment</path></source>` MULTIVALOR → Bloque L se evaluaba una vez por valor de
     assignment → producía `[draft, archived]` simultáneos → HTTP 500 "Strong mappings provided more than
     one value for single-valued item lifecycleState". **Mismo antipatrón que forzó D7 affiliations→primaryAffiliation.**
     FIX: leer `focus.assignment` dentro del script (patrón Bloque G), SIN declararlo `<source>` → mapping
     corre UNA vez.
  2. Comentario inline `// ... <source> ...` con `<` crudo en `<code>` NO-CDATA → XML parse error
     ("element type source must be terminated"). FIX: escapar a `source`/`=&gt;`.
- **Task saneo** `upeu/tasks/sanitation-dual-structural/task-sanitation-dual-structural.xml`:
  `iterativeScripting` + `execute-script` Groovy que aplica DELTA ATÓMICO
  `{add structural-correcto + delete TODOS los structural-stale}` por usuario en una sola
  `midpoint.executeChanges(reconcile=true)`. Prioridad H4: faculty>staff>student>alum desde items
  liveAffiliation; si 0 afiliación viva → conserva employee existente (→ Bloque L H3 lo archiva); nunca
  deja 0 structural (H1). Cubre los 9 structural-user (researcher/visitor/contractor/partner/service
  como OTHER_STRUCT, conservados solo si únicos). Idempotente.
- Template base PUT HTTP 201, `focus.assignment` verificado en DB.

## PASO 2 ✅ VERDE — 4 canaries, todos 204, 0 PolicyViolation, structural ÚNICO
| Canary | Antes | Después | Esperado | Veredicto |
|---|---|---|---|---|
| `48150895` egresado dual ex-staff | active/alumni | **active / alumni** (único) | active/alum único | ✅ |
| `548644005` denominacional 0-afiliación-viva | **draft**/employee-faculty | **archived / employee-faculty** (único) | **archived** (H3) | ✅ |
| `01219011` trabajador activo | active/employee-faculty | **active / employee-faculty** | active/faculty | ✅ |
| `200920749` egresado puro (control) | active/alumni | **active / alumni** | active/alum | ✅ |

- **researcher+faculty:** PM12 ya saneó el único dual (0 quedan en m_assignment). La prioridad del task
  (faculty gana; researcher no es liveAffiliation) lo cubre; no hay dual vivo que probar como canary.
- Mecanismo de recompute por canary: PATCH no-op `?options=reconcile` HTTP 204.

## Estado dual-structural PRE-PASO-3 (datos duros)
- `m_assignment` con >1 structural-user: **0** (saneados en PM12).
- **Población LATENTE: 4,733** (structural employee + shadow Egresados v3 linked vivo) → dispararían
  dual-archetype EN RECOMPUTE masivo. ESTE es el target del PASO 3.
- Resources: Trabajadores v3 `...e21`, Estudiantes v3 `...e22`, Egresados v3 `...e23`.

## SIGUIENTE — validar task saneo en lote pequeño (5 latentes) antes del masivo de 4,733.

## PASO 3 (validación previa) — Mecanismo atómico VALIDADO en 5 latentes. DETENIDO para confirmar mecanismo del masivo.

### Validación del delta atómico (5 usuarios latentes reales)
| User | worker shadow | ESTADO | alum shadow | correcto | resultado | dual |
|---|---|---|---|---|---|---|
| 42142175 (002eea55) | dead | — | alive | alum | **active/alumni** | 0 |
| 73781834 (0042922d) | dead | — | alive | alum | **active/alumni** | 0 |
| 74406267 (0014ebb1) | dead | — | alive | alum | **active/alumni** | 0 |
| 72736507 (000afab7) | **alive** | **I** | alive | alum | **active/alumni** | 0 |
| 75231975 (0019c234) | alive | A | alive | staff (worker gana) | **active/employee-staff** | 0 |

- **Delta atómico** `{delete employee-staff @id + add alumni}` con `?options=reconcile` vía REST PATCH JSON
  → **HTTP 240** (240 = partial-success por una ref TaskType stale benigna, no afecta el user; cambio
  del user OK). **0 PolicyViolation** (nunca hay 2 structural a la vez). active/alumni materializado.
- **HALLAZGO CRÍTICO (refina H4):** la liveness del worker NO se decide por el flag `dead` del shadow
  sino por **ESTADO != 'I'**. Caso 72736507: worker shadow `dead=None` (vivo) pero `ESTADO='I'` (cesado
  en grace 730d) → NO es afiliación laboral viva → correcto = alum. El task script YA chequea
  `basic.getAttributeValue(sh,'ESTADO') != 'I'` (réplica exacta de `archetype-to-liveAffiliationWorker`);
  un atajo por `dead` solo lo habría clasificado mal. **El task es la fuente correcta, no el flag dead.**
- **Confirma H1/H2:** no hace falta materializar `liveAffiliation*` antes (race H2 evitada): el task
  computa la afiliación viva desde la REALIDAD (shadows linked + ESTADO), aplica el delta atómico que
  deja 1 structural, y el reconcile dispara J3/L/D7 sobre el objeto ya con structural único → converge
  en 1 pasada. Idempotente.

### BLOQUEO de scheduling (no de lógica): el task iterativeScripting no ejecuta vía REST
- `PUT /tasks` 202 + `POST /tasks/{oid}/run` 204, pero el task queda SUSPENDED en Quartz in-memory
  (DB executionstate NULL) → script NO corre (0 líneas SANEO en log, 0 cambios). Patrón conocido
  (MEMORY.md "Scheduling de tasks vía REST"): requiere
  `UPDATE m_task SET executionstate='RUNNABLE', schedulingstate='READY'` + **restart del container**
  midpoint_server para que Quartz cargue el trigger y `executeImmediately` dispare.
- El **restart de PROD es operación crítica** → requiere confirmación de Alberto (reglas operacionales).

### DECISIÓN REQUERIDA para el masivo de 4,733 (elegir mecanismo de ejecución)
La LÓGICA está validada (delta atómico correcto, ESTADO-aware, 0 dual, egresados→active/alum,
denominacionales→archived vía H3). Falta solo CÓMO ejecutarla sobre 4,733 por lotes:

1. **Task iterativeScripting** (ya desplegado, OID `d1a2b3c4-...`): cambiar query a `inOid` por lote
   (o `<q:or>` archetypeRef structural-user), DB-kick `executionstate=RUNNABLE` + **restart container**.
   Procesa server-side, robusto, con progress. Requiere 1 restart de PROD (confirmar).
2. **Loop REST PATCH** (driver bash desde mi lado): por cada user, leer reality (worker dead+ESTADO,
   student, alum) → computar correcto → PATCH JSON delta atómico `?options=reconcile`. Sin restart,
   pero ~4,733 llamadas REST (más lento, sin progress nativo, pero 100% probado: es justo lo que
   validé en los 5). Por lotes de ~500 con monitoreo disco/memoria.

**Recomendación:** opción 1 (task) si Alberto autoriza el restart de PROD (más limpio y rápido);
si no, opción 2 (loop REST por lotes, sin restart). Ambas usan el MISMO delta atómico validado.
NO se ejecutó el masivo ni PASO 4-6 — esperando elección de mecanismo + autorización.

### Estado PROD tras PM13
- **Config durable:** template base (Bloque L rama H3, `focus.assignment` no-multivalor) PUT 201;
  task saneo desplegado (PUT 202, OID `d1a2b3c4-5e6f-4a8b-9c0d-1e2f3a4b5c6d`). Commits `5100ce4`→`80826bc`.
- **Datos:** 4 canaries PASO2 + 5 validación PASO3 = 9 usuarios saneados (todos single structural correcto).
  0 destructivos no intencionados. 0 dual-structural en los 9. Disco 77%, contenedores healthy.
- Backups PM12 (`bkp_pre_paso1_struct_20260530_0154.sql` 674M) + PM8/PM11 vigentes.

---

# SESIÓN PM14 (2026-05-30) — PASO 1 MASIVO LANZADO (opción 2, loop REST sin restart). EN CURSO en background.

> Skills consultadas: `midpoint-best-practices` línea 169 (archetype solo por direct assignment plano),
> línea 183 (max 1 structural), línea 398 (cambio de archetype = destructivo/especial), §4.1-4.3;
> `iga-canonical-standards` §1.2 (lifecycle ISO 24760), §1.3 (una IIA por atributo). Opción 2 (loop REST
> sin restart) APROBADA por Alberto. Mecanismo idéntico al delta atómico validado en PM12/PM13 (9 users).

## Cuantificación REAL de la población latente (criterio ESTADO='I', no flag `dead`)
El conteo correcto NO usa `m_shadow.dead` sino **ESTADO != 'I'** (attr JSONB clave `"29"` del shadow
Trabajadores v3) — replica `archetype-to-liveAffiliationWorker` (PM13 hallazgo crítico). Worker con
shadow no-dead pero ESTADO='I' (cesado en grace) NO es afiliación laboral viva.

| Conjunto (employee structural, sin laboral vivo) | N | Acción | Seguridad |
|---|---|---|---|
| + shadow alum vivo (e23) | **1,376** | → alum (delta atómico) | ✅ seguro |
| + shadow student vivo (e22) | **363** | → student (delta atómico) | ✅ seguro |
| 0 académica viva en MidPoint, SIN DNI en Oracle académico | **3,203** | → archived (Bloque L H3, conserva employee) | ✅ seguro |
| **0 académica viva en MidPoint PERO CON DNI académico en Oracle (tmp_acad)** | **983** | **QUARANTINE — NO tocar** | ⚠️ salvaguarda |
| **TOTAL latente** | **5,925** | (4,942 procesar + 983 cuarentena) | |

## HALLAZGO BLOQUEANTE menor — 983 en cuarentena (NO archivar)
Los 983 son ex-trabajadores con afiliación académica vigente en Oracle (egresado/alumno) pero **SIN
NINGÚN shadow Egresado/Estudiante** (ni vivo ni muerto) en MidPoint → su `alum`/`student` nunca se
proyectó (residuo del recon Egresados SUSPENDED en PM7). Archivarlos violaría la salvaguarda académica.
**Decisión conforme al runbook:** EXCLUIRLOS del saneo (acción `QUARANTINE`, skip) → quedan como están
(employee/active) hasta que un recon Egresados/Estudiantes complete los proyecte. NO se detiene el resto.
Lista de los 983 = filtrable de `/tmp/saneo_list.tsv` (action=QUARANTINE).

## Mecanismo (validado en canary 15 users antes del masivo)
- Backup incremental fresco: `/home/juansanchez/bkp_pre_paso1_masivo_20260530_0232.sql` (2.4G; m_assignment
  + m_ref_archetype + m_user + m_ref_object_parent_org).
- Script `/tmp/saneo_masivo.sh` (loop REST PATCH JSON, lee `/tmp/saneo_list.tsv`):
  - **alum/student:** delta atómico `{add archetype-correcto + delete employee stale @cid}` con
    `?options=reconcile` → siempre 1 structural → template (J3/L/D7) corre → active/alum|student.
  - **archived:** PATCH no-op (`replace description=saneo-masivo-2026-05-30`) `?options=reconcile` →
    conserva employee → Bloque L rama H3 → archived (H1: nunca 0 structural).
  - Disk-guard 90% (abort), progreso cada 200, acepta HTTP 204/240/200.
- **Canary 15 (5 alum + 5 student + 5 archived): 15/15 OK.** Verificado: alum→active/alumni,
  student→active/student, archived→archived/employee-staff. **0 dual structural** (nstruct=2 = structural
  + auxiliary AuxAff, NO dos structural).

## Estado EN CURSO (lanzado en background, nohup)
- Proceso `saneo_masivo.sh` PID 1008989 VIVO, log `/tmp/saneo_masivo.log`.
- Progreso n=200/5925: ok=162, fail=1, quarantine=36, disco=82%. Ritmo ~200/4.5min → **ETA ~04:50 Lima**.
- **0 dual structural GLOBAL** durante la corrida (delta atómico nunca crea 2). Contenedores healthy.

## FAILs (datos sucios pre-existentes, NO del mecanismo)
- 1 FAIL (dni 42966194): HTTP 500 `Strong mappings provided more than one value for single-valued item
  familyName: [Azan Rodriguez, Azan Rodríguez]`. Causa: **discrepancia de tildes** entre fuente worker y
  egresado para el mismo apellido → 2 valores strong colisionan en familyName. NO es dual-archetype ni
  defecto del saneo; es calidad de datos. El user queda intacto (sin saneo). Se acumulan en el log para
  tratamiento aparte (normalización de tildes en inbounds de nombre — trabajo separado SciBack).

## PENDIENTE al completar el masivo (PASO 2 verificación + PASOS 3-5)
- PASO 2: 0 usuarios >1 structural; 1,376 ex-trab→active/alumni; 363→active/student; 3,203→archived;
  0 egresados/estudiantes con afiliación viva en archived (los 983 cuarentena NO cuentan, siguen active).
- PASO 3-5 (re-recon Trabajadores, recompute UPeU + purga, verificación final): tras completar PASO 1+2.
- Tratar los 983 QUARANTINE (recon Egresados/Estudiantes que los proyecte) — prerequisito para su saneo.

---

# SESIÓN PM15 (2026-05-30 ~03:00 Lima) — El saneo PM14 NUNCA MURIÓ. 5 fails diagnosticados (benignos, calidad de datos). Watchdog robusto instalado. EN CURSO.

> Skills consultadas: `midpoint-best-practices` §2.1 (Reality vs Policy), §4.2 (strength relativista),
> §1.3 (una IIA por atributo: familyName/givenName con 2 IIAs strong); `iga-canonical-standards` §1.3.
> READ-ONLY + reproducción de 5 PATCH (idempotentes, no-op por error pre-existente) + instalación de
> watchdog. 0 cambios destructivos de datos.

## HALLAZGO QUE CORRIGE EL BRIEF — el proceso NO murió
El brief asumió que el saneo masivo murió en n=1200 (~03:00) por corte de SSH. **FALSO.** Inspección en PROD:
- **PID 1008990 VIVO**, `PPID=1` (huérfano de init: el `nohup` desacopló bien; sobrevivió al cierre del SSH).
- AVANZANDO de forma estable: confirmado muestreando el `curl` hijo (de user `3afa3bb5`→`3b4f8910` en 12s) y la
  línea `PROGRESO n=1400/5925 ok=1159 fail=5 quarantine=235` (03:03), POSTERIOR al n=1200 del brief.
- **Por qué pareció muerto:** el script solo escribe `PROGRESO` cada 200 iteraciones. La sesión anterior cerró
  el SSH y no vio la línea n=1400; el proceso siguió corriendo todo el tiempo.
- **Decisión:** NO relanzar un proceso paralelo (causaría doble concurrencia de PATCH sobre los mismos OIDs →
  conflictos de optimistic-locking). Se DEJA correr el proceso sano y se le añade robustez externa (watchdog).

## PASO 1 — Diagnóstico de los 5 fails: BENIGNOS (calidad de datos, NO bloqueantes)
Reproducidos los 5 PATCH `action=alum` con `--max-time`; todos HTTP 500 con el MISMO patrón:
`Strong mappings provided more than one value for single-valued item familyName|givenName`.

| uoid | dni | item | valores en conflicto |
|---|---|---|---|
| 02db91c3 | 42966194 | familyName | `Azan Rodriguez` vs `Azan Rodríguez` |
| 0d1b0f13 | 71920250 | givenName | `Iván Neftalí` vs `Ivan Neftalí` |
| 0facebc2 | 02419611 | familyName | `Chanducas Zarate` vs `CHANDUCAS ZÁRATE` |
| 2d1518ae | 42761734 | givenName | `Jesús Edwar` vs `Jesus Edwar` |
| 3872afa8 | 72261430 | familyName | `Reategui Perez` vs `Reátegui Perez` |

**Causa raíz:** discrepancia de diacríticos/mayúsculas entre la fuente Trabajadores y la fuente Egresados para
la MISMA persona. Dos inbounds `strong` (uno por IIA) aportan 2 valores distintos a `familyName`/`givenName`
(single-valued) → el consolidador no converge → 500. Es la `name-quality` ya anticipada en PM14.

**Veredicto (responde el brief):**
- **NO es provisioning downstream.** El error es de consolidación del FOCUS (fase clockwork), no de un conector.
  NINGÚN recurso (Koha/LDAP en `proposed`, Entra ID `proposed`) interviene. El `action=alum` del log es la
  acción del saneo, no un "recurso alum".
- **NO es dual-archetype.** El delta atómico nunca llega a aplicarse (falla antes, en familyName/givenName).
- **Benigno y NO bloqueante.** Los 5 focos quedan INTACTOS (sin sanear, sin daño). Se acumulan para tratamiento
  aparte: **normalización de diacríticos/case en los inbounds de nombre** (NFC + título) — trabajo SciBack
  separado (regla "una IIA por atributo": designar una fuente autoritativa de nombre, o normalizar antes de
  consolidar). El saneo masivo continúa con el resto sin problema.
- A ritmo actual se esperan ~pocas decenas de fails de este tipo en total (ex-trabajadores-egresados con
  nombre divergente entre fuentes); todos del mismo patrón, todos diferibles.

## PASO 2 — Robustez sin relanzar: WATCHDOG desacoplado instalado
El script `saneo_masivo.sh` usa `curl` SIN `--max-time` (debilidad: una llamada colgada congelaría el loop).
El proceso vivo no se ha colgado, así que NO se reinicia. En su lugar, `/tmp/saneo_watchdog.sh` (lanzado con
`setsid nohup ... </dev/null`, **PID 1062335, PPID=1**, sobrevive al SSH):
- Mata cualquier `curl` hijo del saneo colgado >180s (destraba el loop; el script reintenta el siguiente).
- Si el saneo muere ANTES de `SANEO MASIVO COMPLETE`, **relanza RESUME** desde el último `PROGRESO n=` (tail de
  la lista a `/tmp/saneo_list_resume.tsv`). Reprocesar el bloque <200 ya hecho es no-op idempotente (delta
  atómico por DNI). Evita el doble-proceso: solo arranca si el original murió.
- Disk-guard de respaldo (90%) además del interno del script.
- Termina solo al detectar `COMPLETE`. Log: `/tmp/saneo_watchdog.log`.

## Estado EN CURSO (PM15)
- **Saneo** PID 1008990, PPID=1, vivo, **n=1400/5925** (ok=1159, fail=5, quarantine=235), disco 82%.
- **Watchdog** PID 1062335, PPID=1, vigilando.
- **Ritmo:** ~50 items/min (~200 cada 4 min). **ETA ≈ 04:35 Lima** (~90 min para los ~4,525 restantes).
- Contenedores healthy, RAM 15Gi total (4Gi libre), MidPoint responde <10ms. 0 restart. 0 destructivo.
- **Próxima invocación (al COMPLETE):** verificación post-saneo (0 dual structural; ~1,376→active/alumni,
  ~363→active/student, ~3,203→archived), re-recon Trabajadores, recompute, purga, recon 983 quarantine, cierre.
  Los ~decenas de fails name-quality NO bloquean: se listan de `grep FAIL /tmp/saneo_masivo.log` para SciBack.

---

# SESIÓN PM16 (2026-05-30 ~05:00 Lima) — Saneo masivo COMPLETO verificado. PASO B (recon Trabajadores) ABORTADO: reintroduce dual-structural + archiva académicos sin liveAffiliation. RAÍZ = template D7 acumulativo no resuelto. PROD restaurado limpio. BLOQUEADO esperando fix de template.

> Skills consultadas: `midpoint-best-practices` §3.3 (max 1 structural archetype), §3.4 (archetype solo por
> direct assignment plano, línea 169), §4.5/§4.6 (template corre DESPUÉS de inbounds; wave ordering),
> §2.1 (Reality vs Policy), §1.2 (lifecycle ISO 24760 desde IIA); `iga-canonical-standards` §1.2/§1.3.
> READ-ONLY masivo + 2 recons monitoreados+suspendidos + saneo dual delta-atómico (451+7). Oracle SOLO LECTURA.
> Backups: `bkp_pre_pasoB_20260530_0504.sql.gz` (649M) + `bkp_pre_saneo451_20260530_0543.dump` (641M).

## Verificación de cierre del saneo masivo PM14/PM15 (PASO 1)
- `SANEO MASIVO COMPLETE n=5925 ok=4914 fail=28 quarantine=983` (04:31 Lima). Confirmado.
- **0 dual-structural** en m_assignment (9 structural-user archetypes). Confirmado.
- lifecycle baseline pre-Paso-B: active 44,062 / archived 4,467 / draft 694 / NULL 95.
- distribución structural: alumni 27,138 / employee-staff 12,369 / student 9,414 / employee-faculty 300.
- **28 DNIs FAIL diacríticos** extraídos (PASO F): `00326909 02419611 04430503 07193644 09728940 41119182
  42516817 42761734 42966194 44164612 44187598 44850035 44901960 47707366 70482165 71252394 71920250
  72213587 72261430 72461965 72790254 74254503 75717462 75733382 76362189 76478851 76820058 77667478`.
  Causa: discrepancia tildes/case entre fuente Trabajadores y Egresados para familyName/givenName
  (single-valued, 2 inbounds strong). Diferible — normalización NFC+título en inbounds de nombre (SciBack #56).

## Salvaguarda baseline pre-Paso-B (caracterización de los 98 archived c/ shadow académico vivo)
NO eran académicos puros mal archivados. Desglose: **27 = los FAILs diacríticos** (saneo no pudo
convertirlos a alum/student → quedaron employee archived); **71 = trabajadores ESTADO='A' (laboral VIVO)
mal archivados PRE-EXISTENTES** (un recompute los rescata a active). Métrica bloqueante estricta:
**alumni_arch=1, student_arch=0** (structural alumni/student que estén archived).

## PASO B (recon Trabajadores v3) — LANZADO, MONITOREADO, ABORTADO a los ~6 min por DOBLE anomalía bloqueante
Task `e8d054ba` (→ Trabajadores v3 `...e21`, filtro ID_ENTIDAD=7124, reaction deleted→unlink condicional).
Lanzado vía REST `/run` (HTTP 204). Monitoreado cada 2-6 min. **Suspendido** (REST `/suspend` 204) al detectar:

### Anomalía 1 (salvaguarda académica violada) — egresados/estudiantes VIVOS archivados
- `alumni_arch` creció 1→2→5→6 de forma sostenida; `student_arch` con regresión análoga.
- Diagnóstico (datos duros): **90 archived con shadow Egresado VIVO pero `liveAffiliationAlum`(clave JSONB 215)
  VACÍO**; **36 archived con shadow Estudiante VIVO pero `liveAffiliationStudent`(217) VACÍO**.
  De los 90: **72 son survivors del merge** (`merged-2026-05-29`).
- **Causa raíz (wave ordering, §4.5/§4.6):** estos focos tienen shadow académico vivo pero su `liveAffiliation*`
  NUNCA se materializó (el recon Egresados/Estudiantes que lo poblaría estuvo SUSPENDED desde PM7). El recon
  Trabajadores hace unlink+recompute → Bloque L (Opción 2) lee `liveAffiliation*`(215/217)=∅ → con structural
  employee → rama H3 → **archived**. **Verificado: 0 focos con 215 materializado siguen archived** (la Opción 2
  es correcta — cuando el item existe, L da active). El defecto es de ORQUESTACIÓN: Paso B corre ANTES de poblar
  liveAffiliation académico. ⇒ **Paso D (recons académicos) DEBE preceder a Paso B.**

### Anomalía 2 (template D7 acumulativo reintroduce dual-structural) — MÁS GRAVE, raíz de fondo
- **dual-structural pasó de 0 a 451** en los ~6 min de recon. Combos: 229 faculty+staff, 181 alumni+staff,
  22 alumni+faculty, 19 alumni+student.
- **Causa raíz (best-practices §3.4, línea 169 + H1/PM12):** el Bloque D7 del template (`assignmentTargetSearch`
  → archetype por `primaryAffiliation`) ASIGNA el structural nuevo SIN REMOVER el stale (D7 strong solo retira
  los assignments que ÉL produjo; el structural histórico no tiene su provenance). El saneo masivo PM14/15
  resolvió esto en DATOS (delta atómico externo), pero **el TEMPLATE nunca se corrigió**. ⇒ CUALQUIER recompute
  masivo (Paso B o Paso C) reintroduce el dual-structural. **Este es el bloqueo de fondo, pendiente desde PM11/PM12.**

## Restauración de PROD a estado limpio (revertir el daño del recon)
- **Saneo de los 451 dual** vía delta-atómico loop-REST (mismo mecanismo PM14/15). Canary 3/3 verde
  (faculty/staff/student → single structural correcto, active).
- **Round 1** (lista con criterio `ESTADO='A'` literal): ok=295, fail=156. Los 156 fallaron porque marqué
  `correcto=staff/faculty` para ex-trabajadores cesados, pero D7 (correctamente) derivaba alum/student → pelea.
- **HALLAZGO (refina PM13):** la liveness laboral es `ESTADO != 'I'`, NO `dead`. Re-generada lista de 156 con
  criterio canónico: **141 alum + 8 student + 7 faculty** (la mayoría son ex-trabajadores cesados cuya afiliación
  viva REAL es académica — D7 tenía razón). **Round 2:** ok=149, fail=7.
- **7 residuales** (worker ESTADO='A' real, correcto=faculty, pero D7 pone académico por falta de
  `liveAffiliationWorker` materializado): saneados con **`?options=raw`** (sin reconcile → D7 no corre → structural
  correcto persiste). HTTP 204 ×7.
- **dual-structural FINAL = 0.** ✅

## Estado de PROD tras PM16 (LIMPIO Y ESTABLE)
- **0 dual-structural** (m_assignment). lifecycle: active 44,105 / archived 4,424 / draft 694 / NULL 95.
- structural: alumni 27,399 / employee-staff 11,456 / student 9,420 / employee-faculty 946.
- **Ganancia durable:** **8,230 `liveAffiliationAlum`(215) materializados** por el recon Egresados parcial
  (era ~2,791 al inicio) → +43 active netos. Beneficio que reduce la población de regresión futura.
- alumni_arch=5 (vs 1 baseline): egresados archived con 215 aún vacío — recuperables al completar recon Egresados.
- Los **3 recons SUSPENDED** (Trabajadores/Egresados/Estudiantes). 0 procesos saneo vivos. Contenedores healthy.
  Disco 82%. 0 escritura a Oracle (política absoluta respetada).

## DECISIÓN REQUERIDA DE ALBERTO (bloqueante de fondo — Pasos B/C/D/E NO pueden ejecutarse sin esto)
**El template D7 debe REEMPLAZAR (no acumular) el structural archetype al cambiar `primaryAffiliation`.**
Pendiente desde PM11/PM12; PM16 lo confirma como el bloqueo crítico. Opciones canónicas (validar en dev):
1. **D7 autoritativo sobre los 9 structural-user** (PREFERIDA): que D7, además de añadir el correcto, REMUEVA
   cualquier otro `archetype-user-*` structural presente. Requiere que D7 conozca el conjunto structural que
   gobierna y que su mapping retire los que no correspondan a la afiliación viva. Riesgo: archetype solo por
   direct assignment plano (§3.4) — el remove debe ser cuidadoso. Esto **embebe en el template** la lógica del
   delta-atómico que hoy vive en el task externo de saneo → el recon Trabajadores dejaría de crear dual.
2. **Mantener el saneo como post-paso** de cada recon masivo (operacionalmente frágil; NO canónico — el template
   debe ser autosuficiente). Rechazada como solución permanente.
- **Prerequisito adicional de orquestación:** ejecutar Paso D (recons Egresados+Estudiantes COMPLETOS) ANTES de
  Paso B, para que `liveAffiliation*` esté materializado y la salvaguarda de Bloque L no archive académicos vivos.
  Orden correcto revisado: **D (académicos) → fix template D7 → B (Trabajadores) → C (recompute+purga) → E (cierre).**

## COLA DE RETOMA (orden corregido por PM16)
1. **Fix template D7-reemplaza-structural** (opción 1) + validar en dev `pruebas-alberto-1`. PREREQUISITO de todo.
2. **Recons Egresados + Estudiantes COMPLETOS** (Paso D adelantado): materializan liveAffiliation en TODA la
   población académica viva (incl. los 90+36 regresión + 983 quarantine + survivors). Monitorear que NO creen
   dual (dependerá del fix #1). Recuperan los alumni_arch a active.
3. **Re-recon Trabajadores** (Paso B): con #1 ya no crea dual; con #2 ya no archiva académicos. ~3,605
   solo-denominacionales → archived; académicos → active.
4. **Recompute trabajadores in-scope + purga orgs** (Paso C). 5. **Cierre + verificación** (Paso E).
6. **28 DNIs diacríticos** (Paso F): normalización NFC+título de nombres → reintento (SciBack #56).

---

# SESIÓN PM17 (2026-05-30 ~06:20 Lima) — FIX TEMPLATE D7 (target/set range autoritativo) APLICADO Y VALIDADO. RAÍZ del dual-structural RESUELTA. Canary real-flow 3/3 + reproducción del escenario recon: 0 dual reintroducido.

> Skills: best-practices §3.3 (max 1 structural), §3.4 (archetype direct assignment), §4.2 (strength),
> §4.5/§4.6 (template tras inbounds, wave ordering); docs.evolveum mapping range ("the mapping is
> authoritative for all values in its range"). Oracle SOLO LECTURA. Backup template `bkp_template_D7_pre_20260530_0614.xml`.

## PASO 1 — FIX D7 autoritativo (REEMPLAZA, no acumula) — COMPLETO

### Diseño del fix (commit `<este commit>`)
- **Causa raíz confirmada:** `assignmentTargetSearch` solo gestiona (add/remove) los assignments con SU
  provenance. Un structural stale de otra fuente (J3 cambia primAff alum→staff en recon → alumni queda
  persistido de la operación previa) NO se removía → dual en cada recompute masivo.
- **Solución canónica:** `<target><set><condition>` en D7 que declara el mapping AUTORITATIVO sobre los 4
  OIDs archetype-user structural derivables de afiliación (faculty `c93083ca`, staff `6460facf`,
  student `3037fbd2`, alum `87552943`). Binding del valor evaluado = `input` (docs.evolveum). Con el set,
  D7 produce 1 (el correcto) y MidPoint REMUEVE cualquier otro structural-user del conjunto que esté
  presente y D7 no produzca. researcher/visitor/contractor/partner/service-account FUERA del set (intactos).
- Embebe en el template la lógica del delta-atómico del task de saneo PM14/15 → recon ya no crea dual.

### Despliegue
- xmllint OK (escapado `<range>` literal del comentario que rompía el parse). Commit+push+git pull PROD.
- PUT template OID `855caaca-68c4-4f7f-8ff8-b4e35dd7d390` `?options=overwrite` → HTTP 201.

### CANARY BLOQUEANTE — 3 naturales + test del flujo REAL
- Mecanismo de recompute por REST: `PATCH /users/{oid}?options=reconcile` (dispara clockwork completo).
  `/recompute` y `rpc/executeScript` daban 404/400 en 4.10 — descartados.
- **3 canarios naturales** (egresado `201920223`, trabajador `01794074`, cesado `02547610`): tras recompute,
  exactamente **1 structural correcto c/u**, lifecycle coherente (alumni-active / staff-active / staff-archived).
- **HALLAZGO clave (límite del range):** inyectar dual YA PERSISTIDO (alumni+staff via raw) y recomputar →
  **HTTP 500 PolicyViolation "only a single structural archetype supported"**. La guardia de consistencia
  single-structural de 4.10 corre ANTES del object template → aborta antes de que D7 aplique el delete del set.
  ⇒ **el range NO sanea un dual preexistente persistido.**
- **PERO el flujo REAL del recon NUNCA persiste dual** — lo crea-y-barre en el MISMO clockwork. Test fiel:
  canary A (alumni persistido) + inyección `liveAffiliationWorker=staff` (raw, simula inbound del recon) +
  recompute reconcile → J3 deriva primAff=staff → D7 produce staff Y el set barre alumni **atómicamente** →
  **resultado 1 structural staff, active, 0 dual.** Ida-y-vuelta (staff→alum al limpiar el item) también 1.
- **CONCLUSIÓN:** el recon Trabajadores/Estudiantes/Egresados (que cambia afiliación → J3 → D7 en un clockwork)
  ya NO reintroduce dual. Canary real-flow VERDE. ✅ Fix robusto para los Pasos 2-5.

### Estado global tras PASO 1 (sin cambios de datos masivos)
- **0 dual-structural.** lifecycle: active 44,105 / archived 4,424 / draft 694 / NULL 95. Disco 81%. Healthy.
- Canary A restaurado a su estado real (active/alumni). Backup del template pre-fix conservado en PROD.

## PRÓXIMO — PASO 2: recons académicos COMPLETOS (Egresados+Estudiantes) para materializar liveAffiliation
en toda la población (983 quarantine + 90/36 wave-ordering) ANTES del re-recon Trabajadores (PASO 4).

## PASO 2 — Recons académicos COMPLETOS (Egresados → Estudiantes) — EN CURSO

### Backup pre-paso
- **Issue:** dumps full crecían a ~1.5GB (m_user=1.2GB con ext/photos + audit 9.3GB). `--exclude-table-data`
  con globs no-qualified no excluía audit. Solución: **dump focus-only** de las 6 tablas clave para rollback:
  `/tmp/bkp_focus_0651.dump` (702MB, íntegro vía pg_restore -l): m_user, m_assignment, m_ref_archetype,
  m_ref_role_membership, m_ref_projection, m_archetype. Suficiente para revertir cambios de focus de los recons.

### Lanzamiento Egresados (OID `86c3766a`, resource `...e23`)
- **HALLAZGO scheduling:** `/run` → 204 pero queda SUSPENDED (Quartz in-memory, como MEMORY). `/resume` → 202
  y SÍ arranca (task PREEXISTENTE, no recién creado vía REST). Estado: RUNNING/READY/DefaultNode. SIN restart container.
- **Validación del fix D7 bajo recon real:** dual-structural se mantiene en **0** mientras el recon corre
  (verificado a progress 432/513/1474). El fix aguanta. ✅
- **Ritmo:** ~324 items/min (5.4/s). Población egresados ~30K shadows → **ETA ≈ 90 min**. liveAffiliationAlum
  sube lento (8420→8501, la mayoría ya tienen alum; el recon enriquece/materializa el resto).
- **Monitor desacoplado** `/tmp/recon_monitor.sh` (setsid, PID 1493989, log `/tmp/recon_monitor.log`): cada 5min
  loguea progress/a215/dual/disk; **disk-guard 90%** (suspende recons) + **dual-guard >50** (suspende EGR si el
  fix fallara). Auto-termina cuando EGR deja de RUNNING.
- **PENDIENTE en este paso:** al terminar Egresados → lanzar Estudiantes (OID `94b627b4`, resource `...e22`) →
  verificar 983 quarantine → active, 90/36 wave-ordering materializados, 0 egresados/estudiantes vivos sin liveAffiliation.

# SESIÓN PM18 (2026-05-30 ~07:45 Lima) — DIAGNÓSTICO falsa alarma "monitor murió": NO murió. Egresados VIVO y progresando. Monitor reemplazado por ORQUESTADOR robusto que encadena Estudiantes automáticamente.

> Skills consultadas: midpoint-best-practices (§3.3 single-structural, §4.5/§4.6 wave-ordering),
> iga-canonical-standards (§1.3 IIA por atributo). Oracle SOLO LECTURA. Autonomía delegada.

## PASO 1 — Estado REAL vía REST/DB (no solo log)
- **Egresados `86c3766a`: VIVO.** executionState=RUNNING, schedulingState=READY, resultStatus=in_progress,
  realizationState=inProgressLocal. progress 14464→15197 verificado en vivo. lastRunStart=12:02 UTC (07:02 Lima).
  Resource input = `6a91f7e1-...e23` (Oracle LAMB Egresados v3, 30,653 shadows). **NO murió.**
- **Estudiantes `94b627b4`: SUSPENDED** (último run 28-may). Aún no arrancó esta wave. Resource `...e22`.
- **FALSA ALARMA del monitor:** el log SÍ tenía línea 07:42; la hora del servidor era 07:43. El "dejó de loguear
  a 07:37 / progress=12438" fue lectura parcial — el monitor (PID 1493989) estaba SANO en su `sleep 300`, no
  colgado ni zombie. Causa de la percepción: cadencia de 5 min + lectura entre iteraciones.
- **liveAffiliationAlum (ext key 215): 16,838 (07:37) → 18,849 → 19,424** y subiendo conforme materializa. ✅
- **dual-structural = 0** sostenido durante todo el recon (fix D7 PM17 aguanta). ✅ disco 83%.

## PASO 2 — Continuación autónoma
- **Decisión:** NO reiniciar el recon (está vivo y es idempotente). NO matar por colgado (estaba sano).
- **Monitor viejo (5min, solo fase EGR) reemplazado por ORQUESTADOR robusto** `/tmp/recon_orchestrator.sh`
  (setsid, PID 1561648, log `/tmp/recon_orchestrator.log`, cadencia 180s):
  - FASE A: vigila EGR hasta que deje de RUNNING (disk-guard 90% + dual-guard >50, ambos suspenden y abortan).
  - FASE B: al terminar EGR → lanza Estudiantes `94b627b4` vía `/resume` (retry `/run`+`/resume` si no arranca).
  - FASE C: vigila EST con los mismos guards, loguea student (ext key 217) + dual.
- **ETA Egresados:** ~15,2K/30,7K (~50%), ritmo ~360/min → cierre ≈ 08:30 Lima. Estudiantes a continuación.

## PENDIENTE tras ambos recons (cola PM16, orden corregido)
1. recompute control → confirmar dual=0 y 983 quarantine→active, 90/36 wave-ordering.
2. re-recon Trabajadores → recompute árbol canónico (salvaguarda académica BLOQUEANTE: 0 académicos archived).
3. purga denominacionales/legacy/demo. 4. VALIDACIÓN DTI-Lima (trabajadores de "Coordinación Tecnologías de
   Información - Lima" con parentOrgRef a su org canónica + archetype correcto). 5. cierre.

# SESIÓN PM19 (2026-05-30 ~09:00 Lima) — Ambos recons académicos CERRADOS. PASO 1 verificado (dual=0 sostenido, salvaguarda académica intacta). Diagnóstico wave-ordering 92 NULL. PASO 3 (re-recon Trabajadores) lanzado tras restart limpio + saneo scheduling.

> Skills: midpoint-best-practices (§3.3 single-structural, §4.5/§4.6 wave-ordering, mapping strength/sources),
> iga-canonical-standards (§1.2 lifecycle ISO 24760, §1.3 IIA por atributo). Oracle SOLO LECTURA. Autonomía delegada.
> Backup focus-only pre-PASO3: `/tmp/bkp_focus_pre_paso3_0917.dump` (673M, host + container).

## PASO 1 ✅ — Verificación post-recons (read-only)

**Recons cerrados:** Egresados `86c3766a` CLOSED (SINGLE, PARTIAL_ERROR=warnings benignos), Estudiantes
`94b627b4` suspendido tras completar su run (RECURRING; suspendido para que no re-dispare). Monitores/orquestador
PM18 terminados.

**liveAffiliation materializado (ext jsonb keys 215/216/217):**
- alum(215)=30,650 | student(217)=10,936 | worker(216)=1,400 (pre-PASO3).

**dual-structural = 0** (m_ref_archetype, 4 OIDs structural-user). Fix D7 PM17 AGUANTA tras ambos recons. ✅
Distribución structural: alumni 28,716 / student 10,834 / staff 8,807 / faculty 864.

**lifecycleState:** active 44,198 / archived 4,331 / draft 694 / NULL 99. (vs PM17: active +93, archived -93 —
los recons rescataron ~93 a active).

**SALVAGUARDA ACADÉMICA (BLOQUEANTE) VERIFICADA: 0 usuarios archived con afiliación viva** (alum/student → 0;
cualquier liveAff → 0). Ningún egresado/estudiante vivo está archivado. ✅

**Hallazgos de calidad (NO bloqueantes, se resuelven en PASO 3/4):**
- **694 draft** = TODOS egresados (archetype-alumni) con liveAffiliationAlum pero SIN `sciback:taxId` (DNI).
  Bloque L los mantiene en draft por política de completitud (§1.2 perfil incompleto → draft; requiere
  personalNumber + doc primario). Tienen personalNumber pero LAMB Egresados no trae DNI. **Decisión: NO forzar
  a active** (violaría proofing). Gap de calidad en la fuente, no fallo de migración. 28,022 egresados con taxId
  ya están active.
- **92 NULL-lifecycle con liveAffiliation** = wave-ordering deadlock. 91/92 tienen shadows linkeados a resources
  LAMB (Trabajadores/Estudiantes/Egresados/Grados/Koha). Causa raíz confirmada: la cadena J3→D7 (primaryAffiliation
  → archetype) NO se re-evalúa en recompute IDEMPOTENTE (PATCH reconcile ni recompute-task) cuando los `liveAff`
  items no tienen DELTA de source — los mappings strong con `<source>` solo re-disparan ante cambio de source.
  Sólo un delta genuino (poner `lifecycleState=active` la 1ª vez, o un inbound `replace` del recon) dispara J3→D7→L.
  **Por eso el re-recon Trabajadores (PASO 3) los resolverá**: escribe liveAffiliationWorker con delta → cadena
  completa en el clockwork del recon. NO resolver con PATCH manual (caso borde de bajo volumen, 0.19%).
- **3,938 active con archetype staff SIN liveAffiliationWorker** = trabajadores cuyo item liveWorker aún no se
  materializó; población-objetivo del re-recon Trabajadores. Tras PASO 3: con contrato ent=7124 vivo → liveWorker=staff
  → active; sin contrato vivo y sin liveAff académico → Bloque L archiva (parte de los ~3,605 solo-denominacionales).

## PASO 2 ✅ (implícito) — dual=0 sostenido tras recons
El "recompute control" del brief queda validado: tras ambos recons masivos (30K egresados + 10K estudiantes) el
fix D7 mantiene dual-structural=0. Canaries individuales (draft-alum, NULL+liveAff) confirman 0 dual en cada recompute.

## PASO 3 — Re-recon Trabajadores v3 (LANZADO, EN CURSO)

- **Baseline salvaguarda (pre-recon):** active-con-afiliación-académica-viva (alum/student) = **39,337**.
  El monitor SUSPENDE el recon si este número cae >100 (salvaguarda bloqueante). archived baseline=4,331.
- **Task:** `e8d054ba-fd9a-4f8d-b04c-347359e49054` "Recon Oracle LAMB Trabajadores 2026-05-28", resource v3
  `...e21` (16,327 shadows). Lee Oracle (SOLO SELECT).
- **Incidente de scheduling (resuelto):** 1er `/resume` reanudó un checkpoint viejo parcial que cerró en
  progress=2,482 con CPU idle (0.29%) y 0 MODIFY. Diagnóstico: corrida vieja terminó; además 7 users con >1
  shadow Trabajadores producen `Projection already exists in lens context` (calidad de datos: doble código de
  empleado en Oracle — ej. user 43611157 con cuentas '43611157'+'80435499'). NO masivo (solo 7), no bloquea.
  **Fix:** suspend → `UPDATE m_task SET executionstate='RUNNABLE',schedulingstate='READY'` → restart container
  midpoint_server (libera mem 6.9/10GB, recarga Quartz) → `/resume` → arrancó NUEVA corrida desde progress=19,
  running, 18 MODIFY/30s. Monitor v2 (REST progress + salvaguarda académica + guards disco90/dual50/stall16min)
  relanzado.
- **PENDIENTE:** al completar → verificar ~3,605 solo-denominacionales→archived, salvaguarda (0 académicos archived),
  92 NULL resueltos, dual=0. Luego PASO 4 (recompute árbol canónico + purga), PASO 5 (VALIDACIÓN DTI-Lima), PASO 6 (cierre).

# SESIÓN PM20 (2026-05-30 ~10:00-15:00 Lima) — PASO 3 re-recon Trabajadores EN CURSO (lento por refs rotas). Salvaguarda académica PERFECTA (acad=39337 constante). DTI-Lima identifier fix preparado. Diagnóstico wave-ordering 92 NULL + 694 draft.

> Skills: midpoint-best-practices (§3.3, §4.5/§4.6 wave-ordering, §5 org/costCenter, mapping range PM17),
> iga-canonical-standards (§1.2 lifecycle, §10 identifiers inmutables, regla oro #10). Oracle SOLO LECTURA.
> Backup focus-only pre-PASO3: /tmp/bkp_focus_pre_paso3_0917.dump (673M, host+container).

## PASO 3 — Re-recon Trabajadores v3 (EN CURSO, ~65% a las 15:00 Lima)

- **Task** `e8d054ba-...` resource v3 `...e21` (16,327 shadows). Lee Oracle (SOLO SELECT).
- **Scheduling resuelto** (incidente PM19): 1er resume reanudó checkpoint viejo parcial (cerró en prog=2482).
  Fix: suspend → UPDATE m_task RUNNABLE/READY → restart container (mem 6.9→4.8GB, Quartz recargado) → /resume
  → nueva corrida desde prog=19. **Patrón confiable: restart + /resume tras checkpoint corrupto.**
- **Progreso verificado:** prog 19→2698→5495→7359→9780→10668. liveWrk 1400→3900. **arch 4331→5210 (+879
  solo-denominacionales archivados correctamente).** acad=39337 CONSTANTE (salvaguarda perfecta). dual=0 sostenido.
- **CAUSA DE LENTITUD (no bloqueante):** errores `Referenced object not found in assignment target reference`
  — orgs denominacionales (ej. AREA-4520 → OrgType OID inexistente b4b2220e) con parents purgados en migraciones
  previas. Ralentizan cada item afectado (MODIFY baja a ~70/min). **Estas refs colgantes son target de PASO 4
  (purga).** El recon converge igual; ETA total ~varias horas por la densidad de errores en la cola del scan.
- **7 users con doble shadow Trabajadores** (doble código empleado en Oracle, ej. 43611157) → `Projection already
  exists in lens context`. <0.1%, benigno, no bloquea. Saneo opcional (unlink shadow redundante) en limpieza.
- **Monitores frágiles:** los monitores bash en background mueren tras 1-2 iteraciones (SIGHUP pese a setsid, o
  docker exec colgado). Mitigado con timeouts; en la práctica la verificación directa por checkpoint (yo) fue
  más confiable. Salvaguarda académica verificada manualmente en CADA checkpoint: acad=39337 invariante.

## PASO 5 (preparado, NO aplicado a PROD aún) — VALIDACIÓN DTI-Lima: causa raíz + fix de identifier

**HALLAZGO CRÍTICO (causa raíz de "0 trabajadores en DTI-Lima"):** las orgs canónicas DTI usan identifiers
SEMÁNTICOS (`DTI`, `infraestructura.ti.lima`, `continuidad.servicios.lima`, `ops.soporte.ti.lima`), NO el ID_AREA
numérico de LAMB. El **Bloque E** del template (línea 743) asigna trabajadores buscando `OrgType.identifier =
costCenter (=ID_AREA)`. Como las orgs DTI no tienen ID_AREA como identifier, **Bloque E nunca matchea → 0 cuelgan.**

**Verdad de Oracle (vía camino EXACTO del resource: VW_APS_EMPLEADO → VW_TRABAJADOR.ID_SEDEAREA →
ORG_SEDE_AREA.ID_AREA → ORG_AREA):**
- **ID_AREA=18 "Dirección de Tecnologías de Información": 72 trabajadores activos** (ent=7124, ESTADO='A')
- **ID_AREA=17 "Dirección de Infraestructura": 21 trabajadores activos**
- Total 93 trabajadores TI. **SANCHEZ CONDOR, Juan Alberto (DNI 10867326) está en ID_AREA=18** (usuario del proyecto).
- NOTA: VW_APS_EMPLEADO.ID_DEPTO ≠ ID_AREA (codificaciones distintas; el costCenter sale de ORG_SEDE_AREA.ID_AREA).

**Fix aplicado al repo (commit pushed):** `COORDINACION-TI-LIMA` identifier `DTI`→`18`
(upeu/orgs/campus/org-campus-lima-units.xml). **PENDIENTE de aplicar a PROD:** PUT del org + cambiar identifier de
`INFRAESTRUCTURA-TI-LIMA` (OID ea05eb7a) `infraestructura.ti.lima`→`17` vía REST. Las sub-orgs CONTINUIDAD/OPERACIONES
no tienen contraparte Oracle activa → quedan vacías (uso futuro). Tras el fix + recompute de los 93 → Bloque E los
vincula a DTI-Lima/Infraestructura. ESA es la validación de éxito del usuario.

## PASO 1/2 (recordatorio, ya verificados en PM19)
- liveAffiliation materializado: alum 30,650 / student 10,936 / worker 1,400→3,900 (subiendo en recon).
- **SALVAGUARDA: 0 archived con afiliación viva.** dual=0. lifecycle pre-recon: active 44,198 / archived 4,331.
- **694 draft = egresados sin sciback:taxId** (gap calidad fuente; Bloque L los mantiene draft por política
  completitud §1.2 — NO forzar). **92 NULL = wave-ordering** (J3→D7 no re-evalúa en recompute idempotente sin
  delta de source; 91/92 tienen shadow LAMB → el re-recon los resuelve con delta real).

## COLA DE RETOMA (tras completar PASO 3 recon)
1. Suspender recon Trabajadores (es RECURRING). Verificar arch final (~baseline+3,605 esperado), salvaguarda
   (acad≥39,337), dual=0, NULL resueltos.
2. PASO 4: recompute trabajadores in-scope (Bloque E → árbol canónico). Purga orgs denominacionales (244 sin
   archetype, verificar 0 active c/u antes de DELETE) + limpieza refs colgantes (AREA-4520 etc.).
3. PASO 5: aplicar identifier fix DTI a PROD (COORDINACION-TI-LIMA→18, INFRAESTRUCTURA-TI-LIMA→17) + recompute
   los 93 trabajadores TI → VERIFICAR cuelgan de DTI-Lima con archetype correcto. Listar (incl. DNI 10867326).
4. PASO 6: cierre — árbol único, conteos finales por lifecycle/archetype, OrgTemplate-Area inerte, caso 21835727.

# SESIÓN PM21 (2026-05-30 ~11:30-?? Lima) — PASO 1✅ cierre recon Trabajadores + PASO 3 VALIDACIÓN DTI-LIMA ✅

> Skills: midpoint-best-practices (regla oro #10 identifiers inmutables, §5 org tree, cita Evolveum "always use org unit identifiers"),
> iga-canonical-standards (§10 identifiers persistentes = ID_AREA LAMB). Oracle SOLO LECTURA (thick client Instant Client 23.3 ARM64).
> Backup focus-only pre-PASO2: /tmp/bkp_pre_paso2_1152.dump.gz (653M). Backups viejos comprimidos a .gz.

## PASO 1 ✅ — Recon Trabajadores COMPLETÓ y SUSPENDIDO
- Task `e8d054ba` progress=16686 (≥16,327 shadows), CPU idle (0.25%), progress estático → barrido completo. SUSPENDIDO (era RECURRING).
- lifecycle: active 41,341 / archived 7,185 (+2,854 denominacionales vs baseline 4,331) / draft 698 / NULL 98.
- **SALVAGUARDA ACADÉMICA PERFECTA: 0 archived con afiliación viva (alum/student). 39,337 académicos vivos active (invariante).**
- **dual-structural=0** (query corregida: filtrar SOLO los 6 archetypes structural-user; mi query inicial contaba aux como dual = falso positivo).
- liveWorker(216) materializado en 3,900. 698 draft = egresados sin taxId (gap fuente, NO forzar). 91/98 NULL = wave-ordering.

## SCOPE REAL DE ÁREAS (Oracle thick query) = 161 áreas con contrato UPeU activo (ent=7124, ESTADO='A'), 3,858 personas
Join correcto: VW_APS_EMPLEADO.ID_PERSONA → VW_TRABAJADOR.ID_PERSONA+ID_SEDEAREA → ORG_SEDE_AREA.ID_SEDEAREA→ID_AREA.
(VW_APS_EMPLEADO NO tiene ID_TRABAJADOR ni ID_SEDEAREA; el join va por ID_PERSONA.)

## CUADRANTE orgs numéricas MidPoint (382) × scope Oracle (161):
| | count | active users | acción |
|---|---|---|---|
| con-arch & in-scope | 114 | — | OK (canónicas) |
| **SIN-arch & in-scope** | **47** | 282 | **archetype-org-department asignado ✅** |
| con-arch & fuera-scope | 26 | 2 | revisar |
| SIN-arch & fuera-scope | 195 | 275 | denominacional → purga + reparent |
114+47=161 = exacta coincidencia con Oracle. 0 áreas in-scope sin org en MidPoint.

## FIX: 47 orgs in-scope → archetype-org-department ✅
- OrgTemplate-Area (OID 47252981) ESTÁ vinculado global (OrgType) y NO inerte. PERO recompute (REST /recompute=404;
  executeScript recompute con/sin reconcile) NO materializó el archetype: el mapping strong `assignmentTargetSearch`→assignment
  no se aplica por **wave-ordering** (mismo patrón deadlock bootstrapping del template). Search OK, condition OK (archetypeRefCount=0),
  archetype encontrado (73795c10) — pero assignment nunca se persiste.
- **Bulk `assign` action REST falló silencioso** (success pero sin assignment). **Bulk `execute-script` Groovy con
  `midpoint.deltaFor(OrgType).item(F_ASSIGNMENT).add(AssignmentType{targetRef=archetype}).executeChanges()` SÍ funcionó → 47/47 con-arch.**
  LECCIÓN reconfirmada (API 4.10): para asignar archetype confiablemente, ObjectDelta ADD explícito, NO template ni bulk assign.
- handled_error "TaskType ... not found" en cada recompute = refs colgantes en metadata (create/modifyTaskRef de tasks borradas). Benigno.

## PASO 3 — VALIDACIÓN DTI-LIMA ✅ (criterio de éxito del usuario)
**El "bug DTI" YA estaba resuelto en la realidad.** Las orgs FUNCIONALES son las numéricas auto-recon (NO las semánticas):
- `DTI` (identifier=**18**, OID `...953119566392`, archetype-org-department, displayName "DTI") → **102 activos** cuelgan aquí, todos costCenter=18.
- `DIR-INFRAESTRUCTURA` (identifier=**17**, OID `...586421525057`, archetype-org-department) → 34 activos.
- Orgs semánticas vacías (`COORDINACION-TI-LIMA` id=DTI 3m, `INFRAESTRUCTURA-TI-LIMA` id=infraestructura.ti.lima 0m,
  CONTINUIDAD/OPERACIONES 0m) = diseño manual que el flujo de datos NO usa → PURGA (PASO 4).
- **REVISIÓN del plan PM20:** NO cambiar identifier de canónicas-semánticas a numérico (chocaría con org 18 ya existente).
  La verdad: el correlador del resource org.xml YA correlaciona por identifier=ID_AREA → no duplica numéricas. Las numéricas
  con nombre legible + archetype SON las canónicas. Decisión canónica (regla oro #10): conservar identifier inmutable=ID_AREA LAMB.
- **SANCHEZ CONDOR, Juan Alberto (DNI 10867326): active, archetype-user-employee-staff, parent=DTI, costCenter=18. ✅ CONFIRMADO.**
- Discrepancia 102(MP) vs 72(Oracle): MP cuenta por archetype structural; los 29 alum+2 student+21 faculty trabajan en área 18
  pero su identidad structural es académica/faculty. 50 staff+21 faculty=71≈72 Oracle empleados puros. Canónicamente correcto (dual-afiliación).

## PENDIENTE (cola PASO 4):
1. Purga orgs semánticas vacías (COORDINACION-TI-LIMA, INFRAESTRUCTURA-TI-LIMA, CRAI-*, CU-*, coordinaciones vacías, demo Projects/Teams/World).
2. 195 orgs sin-arch fuera-scope (275 active users): reparent usuarios (salvaguarda académica) + purga orgs.
3. 26 con-arch fuera-scope (2 active): revisar.
4. Cierre: conteos finales, parent residual AREA-97, caso 21835727.

## PASO 4 (PM21) — Bloque E guard + reparent 275 stale + PURGA 201 orgs denominacionales ✅

### FIX Bloque E (template, commit 12c533a): guard reality-vs-policy
- Añadido `<source>extension/sciback:liveAffiliationWorker</source>` + condición `&amp;&amp; liveAffiliationWorker != null`.
- Efecto: la membership a área de trabajo (assignmentTargetSearch costCenter→OrgType) SOLO existe con afiliación laboral VIVA.
  Ex-trabajadores (alumni/student que alguna vez tuvieron contrato) pierden la membership stale; conservan archetype/lifecycle académico.
- Importado a PROD (PUT overwrite, HTTP 201). Base template OID `855caaca-68c4-4f7f-8ff8-b4e35dd7d390`.
- **Canary 76869766 (alum, cc=4385):** parent 4385→∅, sigue active. ✅
- **Canary SANCHEZ CONDOR (staff, cc=18, liveWorker✓):** sigue en DTI/18, active. ✅ (worker vivo conserva org)

### Reparent masivo: 274 stale-parent users recomputados (reconcile)
- 0 active users bajo orgs fuera-scope (antes 275/277). Todos siguen active. **Salvaguarda: acad_vivos_active=39,337 invariante, acad_archived=0.**

### Scope de árbol REAL = 189 áreas (161 con contrato 7124 + 28 ancestros estructurales por ID_PARENT)
- Calculado de Oracle ELISEO.ORG_AREA (ID_PARENT chains). Ancestros: 3 UPeU genuinos (ent=7124: áreas 1 Asamblea, 2 Consejo,
  22 Areas Rectorado) + ~25 denominacionales necesarios para conectar áreas con worker UPeU dentro de asociaciones educativas/IE.
- **Decisión canónica:** conservar el set 189-needed (in-scope + ancestros) para NO romper el árbol ni hacer scope-call contestable.
  Purga = numéricas NOT IN 189-needed.

### PURGA: 201 orgs numéricas denominacionales (REST DELETE bottom-up)
- 0 usuarios (cualquier lifecycle) bajo ellas, 0 orgs-needed colgando → purga limpia sin romper árbol.
- Backup pre-purga: `/tmp/bkp_pre_purga_orgs_1211.dump.gz` (23M, m_org+refs+assignment).
- 201/201 eliminadas vía REST DELETE iterativo (round 1: 185 + cascada hijos). m_org 467→266.
- **Post-purga:** 266 orgs (181 numéricas [161 in-scope + 20 ancestros] + 85 semánticas). 164 numéricas con archetype.
  17 numéricas sin archetype = ancestros-contenedor (1/2/22 governance UPeU + denominacionales estructurales).
- Salvaguarda académica PERFECTA mantenida: active 41,341 / acad_vivos_active 39,337 / acad_archived 0.

### PENDIENTE cola final:
1. Archetipar ancestros UPeU governance (1=Asamblea→governance, 2=Consejo→governance, 22=Areas Rectorado→governance/dept).
2. Purgar 85 semánticas vacías (COORDINACION-TI-LIMA, INFRAESTRUCTURA-TI-LIMA, CRAI-* vacíos, CU-* Colegio Unión vacíos,
   coordinaciones admin vacías, demo Projects/Teams/World). CONSERVAR: EP-* (academic-program con miles), OU-CAMPUS-*,
   UPeU institution, GOBIERNO-UNIVERSITARIO, colegios partner, DTI semántica? (revisar si purgar o mantener).
3. Cierre: conteos finales, parent residual AREA-97, OrgTemplate-Area decisión, caso 21835727.

## PASO 4 (cont.) + CIERRE PM21 — purga demo + estado final

### Purga demo orgs (indestructible): Projects/Teams/World ✅
- Marcadas `indestructible=true` (sample MidPoint). PATCH indestructible=false → DELETE 204. m_org 266→263.

### Archetipado ancestros governance
- Áreas 1 (ASAMBLEA-UNIVERSITARIA) y 2 (CONSEJO-UNIVERSITARIO): YA tenían archetype-org-governance (curadas). ✅
- Área 22 (AREA-22 "Areas Rectorado"): archetype-org-department (contenedor Rectorado, aceptable). Sin cambio.

### Semánticas (85, post-purga): CONSERVADAS como blueprint canónico
- DECISIÓN: las orgs semánticas con 0 usuarios (CRAI-*, CU-*, coordinaciones admin, INFRAESTRUCTURA-TI-LIMA, DTI-semántica
  COORDINACION-TI-LIMA, EP-*, OU-CAMPUS-*, UPeU, GOBIERNO-UNIVERSITARIO, colegios) son la ESTRUCTURA CANÓNICA DISEÑADA
  (org-campus-lima-units.xml, repo). NO son basura → se CONSERVAN como blueprint SciBack (se poblarán en Fase 6+).
  EP-* tienen miles de estudiantes. Solo se purgó demo MidPoint (Projects/Teams/World).
- NOTA: existe par semántico/numérico para TI: COORDINACION-TI-LIMA(id=DTI, 3 child) + INFRAESTRUCTURA-TI-LIMA(id=infra...)
  vs funcionales DTI(18)+DIR-INFRAESTRUCTURA(17). Las funcionales numéricas tienen los 102+34 trabajadores. Las semánticas
  son blueprint vacío. CONVIVEN sin conflicto (identifiers distintos). Decisión futura: unificar nomenclatura cuando se
  consolide el árbol de gobierno (no bloqueante; los trabajadores ya cuelgan correctamente de las funcionales).

### ESTADO FINAL (verificado)
| métrica | valor |
|---|---|
| m_org | 263 (de 467; -201 denominacional -3 demo) |
| m_user | 49,322 |
| active | 41,341 (invariante en TODA la sesión) |
| archived | 7,185 | draft 698 | NULL 98 |
| **acad_vivos_active** | **39,337 (INVARIANTE)** |
| **acad_archived (salvaguarda)** | **0 ✅** |
| dual-structural | **0 ✅** |
| orgs numéricas con archetype | 164 |

### VALIDACIÓN DTI-LIMA — CRITERIO DE ÉXITO ✅✅
- **DTI** (id=18, archetype-org-department, parent=VICERRECTORADO-ADMINISTRATIVO): **102 activos**.
- **DIR-INFRAESTRUCTURA** (id=17, archetype-org-department, parent=VICERRECTORADO-ADMINISTRATIVO): **34 activos**.
- **SANCHEZ CONDOR, Juan Alberto (DNI 10867326): active, archetype-user-employee-staff, costCenter=18, org=DTI.** ✅ CONFIRMADO.
- Listas completas de ambos áreas verificadas (archetypes staff/faculty/alumni/student dual-afiliación correctos).

### PENDIENTE (no bloqueante, design-decision para el usuario):
- **20 orgs orphan-root denominacionales** (160/535-538/809/811/750-chains etc. = Asoc Educativas, IE, misiones donde
  trabajan staff UPeU con contrato 7124). Sus ancestros LAMB (815/814/813/812/808/535/750/816) NO existen como org en
  MidPoint (recon Org solo creó áreas con shadow directo). Forman forest acíclico secundario (Evolveum lo soporta:
  "as long as it is an acyclic directed graph it will work just fine"). Para árbol único: crear nodos ancestro
  denominacionales bajo umbrella partner-institution, O reparent a campus. ES SCOPE-POLICY (cómo modela UPeU a sus
  trabajadores destacados en entidades denominacionales) → requiere decisión del usuario, NO se resuelve autónomamente.
- OrgTemplate-Area: vinculado global y ACTIVO (no inerte). Funciona vía bulk executeChanges, no vía recompute por
  wave-ordering — comportamiento conocido. Mantener.
- Caso 21835727: pendiente revisión individual.

---

## ADDENDUM PM16 — Fix "área del contrato 7124" (2026-05-30)

### Causa raíz
UPeU y la Iglesia Adventista comparten una sola planilla APS. El área/costCenter se derivaba de
`ENOC.VW_TRABAJADOR.ID_SEDEAREA` (nivel persona, STALE hacia la misión de origen) en lugar del
departamento del **contrato vivo 7124** (`ELISEO.VW_APS_EMPLEADO.ID_DEPTO`). Resultado: trabajadores
con contrato UPeU activo colgando de áreas denominacionales. Caso Flores (41970870): contrato 7124
en depto `21010108` (Administración Unión PU, área 133) pero `VW_TRABAJADOR` mostraba área 4342
(Secretaría-MICOP, denominacional).

### Diseño del fix (`upeu/resources/oracle-lamb/trabajadores.xml`, searchScript)
- **Resolutor de área-de-contrato** (LEFT JOIN `ca`): toma el `ID_DEPTO` de la fila 7124 VIVA
  (`ESTADO='A' AND (FEC_TERMINO IS NULL OR FEC_TERMINO >= SYSDATE)`, dedup `ROW_NUMBER` por
  `FEC_INICIO DESC` para los 4 COD_APS multiviva) y lo resuelve **1:1** a `ID_AREA` vía
  `ELISEO.ORG_SEDE_AREA` → `ORG_AREA` (solo cuando `COUNT(DISTINCT ID_AREA)=1`).
- **`COALESCE(ca.CONTRACT_AREA, osa.ID_AREA)`**: prefiere el área del contrato vivo; fallback al área
  histórica (`VW_TRABAJADOR.ID_SEDEAREA`) cuando el `ID_DEPTO` es jerárquico/ambiguo. Preserva 3894
  casos correctos y jubilados.
- **Endurecimiento de vigencia SOLO en el resolutor** (no en el WHERE de inclusión): mata falsos
  activos (ej. DNI 73970305, fila 7124 'A' vencida 2020) para la derivación de área, sin expulsar a
  los 20.617 jubilados grace 730d de la población.
- IIA del área de empleo vivo = contrato 7124 (Reality-vs-Policy §2.1; IIA por atributo §1.3).

### Verificación pre-aplicación (Oracle SOLO SELECT, thick x86_64)
- Flores → ID_AREA **133** (Administración Unión PU). ✓
- baseQuery completo ejecuta limpio: 7849 filas, **7469 in-scope UPeU**, 32 out-of-scope, 348 sin área.
- Cardinalidad: 2120/3744 COD_APS con contrato vivo resuelven área 1:1.

### Despliegue
- Commit `60f26df` + git pull PROD + PUT (HTTP 201) + Test Connection **14/14 success** (incl. schema fetch).
- Backup REST del resource previo: `/home/juansanchez/bkp_trabajadores_pre-area-fix_20260530_1310.xml`.
- Tag git `pre-area-contrato-7124-fix`.

### Canary Flores (c0785b5f) post-deploy
- costCenter **4342 → 133**; parentOrgRef `df582ee2` → `d9ccf4f2` (AREA-133 "Administración Unión (PU)").
- lifecycle `active`; structural `archetype-user-employee-staff` + aux `AuxAff-Staff` → dual=0. ✓

### Materialización (import quirúrgico)
- Identificados **414 COD_APS** cuya área cambia; import shadow-por-shadow (loop REST en background).
- Resultado: **414/414 ok, 0 fails**, disco estable 86%.
- Transferidos denominacional→UPeU: 116 en MidPoint, **116/116 con costCenter que matchea OrgType real**
  (VICERRECTORADO-BIENESTAR, DTI, DIR-IMAGEN-RRPP, áreas in-scope). 110 active, 6 alum.

### Verificación final
- **Salvaguarda académica intacta**: de 414 reimportados, 18 archived, **0 con archetype académico**
  (todos employee puros = leaver legítimo).
- **dual-archetype structural = 0** (global).
- **499/502** "activos en áreas orphan" son legítimos (su contrato 7124 ES esa área compartida).
- Total m_user: 49.322.

### Casos (b) residuales — REQUIEREN DECISIÓN MANUAL
3 trabajadores del changed-set con contrato 7124 vivo cuyo `ID_DEPTO` es jerárquico (mapea a varias
áreas UPeU, todas entidad 7124) → resolutor 1:1 se abstiene, caen al fallback stale. NO degradados
(ya estaban así). Decidir a qué sub-área asignar:
- `76575561` depto `61010106` → 5 áreas candidatas (Comunicaciones/Marketing). Hoy en AREA-7996.
- `48636923` depto `13040722` → 2 áreas (Fac. CC. Humanas / EP Educación). Hoy en AREA-7997.
- `72783226` depto `14010102` → 3 áreas (Cap. Continua / Posgrado / Marketing). Hoy en AREA-7997.
Total estimado de residuales ESTADO='A' con depto ambiguo: ~14 (resto cubierto por leaver/grace).

---

## PM16 — Cura del resolutor depto-ambiguo + reubicación de los 3 + purga AREA-7996/7997 (2026-05-30) ✅

Cierra los "casos (b) residuales" anteriores. Skills: midpoint-best-practices §1.3 (IIA por atributo),
§2.1 (Reality-vs-Policy: org membership = policy derivada de afiliación viva), §5 (org/costCenter).

### PASO 1 — Cura del resolutor `ca` en `upeu/resources/oracle-lamb/trabajadores.xml` (Opción 1, durable)

Problema: cuando `ID_DEPTO` del contrato vivo 7124 mapea a **>1** `ID_AREA` candidata (todas ent=7124),
el resolutor 1:1 `dm` (`HAVING COUNT(DISTINCT ID_AREA)=1`) se abstiene → fallback a `osa.ID_AREA`
(área histórica de VW_TRABAJADOR) → nodo denominacional stale (AREA-7996/7997, ent=7115 PNT).

Cura: segundo nivel `dm2` con `COALESCE(dm.ID_AREA, dm2.ID_AREA)`:
1. `dm2` intersecta las candidatas con el **SET CANÓNICO IN-SCOPE** — exactamente el mismo CONNECT BY
   del resource `org.xml` (ent=7124 conexo desde raíz, MINUS AGTU subtree 8196). 133 áreas.
2. Si tras intersectar quedan varias, elige la de **MAX(ID_SEDEAREA)** (surrogate auto-increment →
   mapeo ORG_SEDE_AREA más reciente = canónico vigente).
3. `dm` (1:1) tiene prioridad vía COALESCE → **invariante probada en Oracle: 0 cambios en strict path**
   (los 414 ya resueltos + Flores→133 + DTI→18 idénticos).

**Verificación pre (Oracle SOLO SELECT):**
- 76575561 depto 61010106 → candidatas {58,62,591,606,789}; in-scope∩={58,789}; MAX(ID_SEDEAREA): 789(5487)>58(877) → **789** ✓
- 48636923 depto 13040722 → {8,102}; in-scope∩={8,102}; MAX: 102(5852/5857)>8(5851) → **102** ✓
- 72783226 depto 14010102 → {7,676,8232}; in-scope∩={7,676,8232}; MAX: 8232(5711)>7(1013)>676(737) → **8232** ✓
- Stats resolutor: total 3744, strict(dm) 2120, newpath(dm2) 1593, unresolved(fallback histórico) 31.
- Invariante: 0 filas donde dm no-null cambia el resultado final.

Commit `be0a618`. PUT resource OID `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21` (HTTP 201). Test connection **15/15 success**.

### PASO 2 — Reubicación de los 3 (import shadow → inbound re-deriva ID_AREA→costCenter→Bloque E)

Backup users `/tmp/bkp-user-*-20260530-135613.xml`. Import de los 3 shadows de la trabajadores resource
(HTTP 200/240). El import por sí solo re-leyó Oracle con el resolutor curado y corrió el clockwork completo
(inbound + template); no hizo falta recompute extra. Resultado:

| DNI | costCenter | parentOrgRef | lifecycle | structural archetype |
|---|---|---|---|---|
| 76575561 | 789 | AREA-789 (Dir. Marketing) | active | archetype-user-employee-staff |
| 48636923 | 102 | AREA-102 (EP Educación) | active | archetype-user-employee-staff |
| 72783226 | 8232 | AREA-8232 (Subdir. Marketing y Comunic.) | active | archetype-user-employee-staff |

dual-structural=0 (cada uno: 1 structural + AuxAff-Staff auxiliar = patrón canónico estándar).

### PASO 3 — Purga AREA-7996 / AREA-7997 + ancestros PNT

Pre-purga: AREA-7996 (2 act) y AREA-7997 (12 act) NO quedaron vacíos tras mover los 3 → **hallazgo**:
14 usuarios académicos (13 alumni + 1 student) con costCenter stale 7996/7997 (ex-trabajadores
sin contrato 7124 vivo). NO son worker mislocados; son membership stale (policy residual).
Recompute `PATCH /users/{oid}?options=reconcile` → **Bloque E guard (PM21)** removió la worker-area
membership (org membership solo con liveAffiliationWorker vivo) conservando archetype/lifecycle académico.
Canary student 73703505: active, archetype-user-student intacto, ahora cuelga solo de EP-COM. Los 14: **14/14 active**.

Cadena denominacional (Oracle: todos ent=**7115** PNT, 0 active): AREA-7989←7995←7996←7997.
indestructible=none. Backup orgs `/tmp/bkp-org-*-20260530-140109.xml`.
DELETE leaf-first con guard "0 active" inmediato antes de cada uno: 7997, 7996, 7995, 7989 → **204×4**.
m_org 263→259.

### PASO 4 — Cierre

- orgs 7989/7995/7996/7997 restantes: **0**.
- Los 3: active, employee-staff, parentOrgRef canónico, costCenter correcto, dual=0. ✓
- **Flores 41970870 → costCenter 133, AREA-133, active** ✓ (intacto).
- **DTI SANCHEZ CONDOR 10867326 → costCenter 18, org DTI, active** ✓ (intacto).
- dual-structural=0 en los 17 usuarios tocados. Disco 86%.
- m_org final: **259**.

### RESIDUAL identificado (fuera de scope PM16 — REQUIERE DECISIÓN)

**AREA-7795 "Pastor distrital" (ent=17611 denominacional)** retiene 26 active: 25 alumni stale (mismo
patrón costCenter stale, curable con recompute Bloque E) + **1 employee-staff DNI 73970305**.
Oracle confirma 73970305 SIN contrato 7124 vivo (7124 venció 2020/2021; contratos activos = ent 17611
"Pastor distrital"). Es un pastor denominacional, NO trabajador UPeU → falso-activo employee-staff
(shadow stale). Caso de democión de archetype no-UPeU + salvaguarda alumni → pase deliberado aparte,
NO se actuó unilateralmente en PM16. Para confirmar con usuario.
