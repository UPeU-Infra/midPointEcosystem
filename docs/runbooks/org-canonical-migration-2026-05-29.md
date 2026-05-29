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
