# PLAN — Migración Koha categorycodes a eduPerson 202208

**Fecha:** 2026-05-23
**Decisión origen:** [`DECISION-eduperson-koha-categorycodes.md`](DECISION-eduperson-koha-categorycodes.md)
**Duración estimada:** 5-7 semanas (con observación)
**Riesgo:** MEDIO — 51K patrones tocados en PROD; coexistencia old↔new mitiga
**Rollback:** Tabla `borrowers_migration_log` + git revert + restore mysqldump

---

## Resumen ejecutivo

**Orden actualizado 2026-05-23**: Fase 3 (crear categorías Koha) se mueve ANTES de Fase 1 (template MidPoint). Razón: cuando MidPoint cambie a vocabulario lowercase eduPerson, Koha debe ya tener esas categorías creadas o el provisioning falla masivamente.

| Fase | Descripción | Duración | Dependencias |
|---|---|---|---|
| 0 | Pre-migración (backup, doc, validaciones) | 3 días | — |
| **3** | **Koha — Crear categorías nuevas eduPerson en paralelo** | **1 día** | **Fase 0** |
| 1 | MidPoint — Template jubilados→alum (condicional) + prioridad multi-aff + lowercase rename | 3-4 días | Fase 3 |
| 2 | MidPoint — Crear rol R-Researcher | 1 día | Fase 1 |
| 4 | MidPoint — Simplificar koha-ils.xml mapping | 1 día | Fases 1, 2 |
| 5 | Reconciliación Koha — re-stamp ~38K IGA-managed | 1-2 días | Fase 4 |
| 6 | Migración batch 22K legacy (ESTUDI/VISITA/STAFF) | 2-3 días | Fase 5 |
| 7 | Observación + monitoreo | 14 días | Fase 6 |
| 8 | Cleanup — drop categorías viejas | 1 día | Fase 7 |
| 9 | Documentación post-mortem + gobernanza | 2 días | Fase 8 |

---

## Fase 0 — Pre-migración

### Acciones

- [ ] Backup completo Koha DB:
  ```bash
  mysqldump --single-transaction --routines --triggers koha_bul > koha_bul_pre_eduperson_$(date +%Y%m%d).sql
  ```
- [ ] Tag git estado actual:
  ```bash
  cd ~/proyectos/upeu/midPointEcosystem && git tag pre-eduperson-categorycodes
  ```
- [ ] Inventario integraciones downstream que filtran por categorycode:
  - [ ] Reportes COUNTER (en biblioteca)
  - [ ] Reportes INEI / SUNEDU
  - [ ] OPAC custom theme (revisar plantillas que muestren categoría)
  - [ ] SMS gateway (improbable, pero verificar)
  - [ ] Cualquier API externa consumiendo Koha
- [ ] Validar longitud máxima de `categorycode` en Koha PROD:
  ```sql
  SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA='koha_bul' AND TABLE_NAME='categories' AND COLUMN_NAME='categorycode';
  ```
  Esperado: `varchar(10)`. Si menor, ajustar plan.
- [ ] Confirmar con biblioteca UPeU (asíncrono, no bloqueante para Fases 1-3):
  - ¿Política de préstamo distinta por studyLevel (pregrado vs posgrado)?
  - ¿Política diferenciada jubilados vs alumni regular?
  - ¿Reportes que filtran por categorycode literal?

### Entregables

- `koha_bul_pre_eduperson_YYYYMMDD.sql` en servidor MariaDB
- Tag git `pre-eduperson-categorycodes` en remoto
- `docs/migracion-koha-cat-inventario-downstream.md` con lista de integraciones

---

## Fase 1 — MidPoint Template: jubilados→alum (condicional) + prioridad multi-affiliation + lowercase rename

**Spec detallada del midpoint-expert** (2026-05-23): seis sub-fases con tag git + pg_dump obligatorios.

### Anti-pattern detectado en estado actual

El template tiene vocabulario MIXTO uppercase/lowercase:
- Bloques G, H, F: `STAFF`/`FACULTY`/`STUDENT` (uppercase)
- Bloques D.5-alum, S: `alum`/`student`/`faculty` (lowercase)

Fase 1.1 normaliza TODO a lowercase eduPerson 202208.

### Cambio arquitectónico clave: inbound de resources

**Hoy**: cada resource escribe directo a `extension/sciback:primaryAffiliation` (weak) → el último inbound corre gana.

**Nuevo**: resources escriben a `extension/sciback:affiliations` (multi-valor, add, weak). El template calcula `primaryAffiliation` por prioridad.

Resources a modificar:
- `upeu/resources/oracle-lamb/trabajadores.xml`
- `upeu/resources/oracle-lamb/egresados-v3.xml`
- `upeu/resources/oracle-lamb/matriculados.xml`
- `upeu/resources/oracle-lamb/grados.xml`
- `upeu/resources/oracle-lamb/secretaria-general.xml`

### Sub-fases

#### 1.0 — Schema extension `upeu:formerRole` (riesgo nulo)

Añadir a `upeu/schemas/upeu-local-v1.0.xml`:
```xml
<xsd:element name="formerRole" type="xsd:string" minOccurs="0" maxOccurs="1">
  <xsd:annotation><xsd:appinfo>
    <a:displayName>Rol anterior (post-jubilación)</a:displayName>
    <a:help>Vocabulario controlado: staff|faculty|student. Setado por Bloque K cuando motivoCese=jubilacion y la persona venía de staff o faculty. Permite que Koha exponga extended_attribute FORMER_ROLE.</a:help>
    <a:indexed>true</a:indexed>
  </xsd:appinfo></xsd:annotation>
</xsd:element>
```

#### 1.1 — Prioridad multi-affiliation + lowercase rename (mayor superficie)

**Bloque J3 nuevo** — calcula `primaryAffiliation` desde `affiliations` multi-valor:

```groovy
def CANONICAL = ['faculty','staff','student','alum','affiliate']
def affs = (affiliations ?: []).collect { basic.stringify(it).trim().toLowerCase() }
    .findAll { it in CANONICAL } as Set
if (affs.isEmpty()) return null
for (canon in CANONICAL) {  // orden de prioridad
    if (canon in affs) return canon
}
return null
```

**Strength**: `normal` (Bloque K strong puede override).

**Limpieza vocabulario** simultánea:
- Bloques D.1, D.3, D.4, F, G, H, R, S: comparaciones a lowercase
- `VALID_AFFILIATIONS` de Bloque G: `['faculty','staff','student','alum','affiliate']`
- `roleMap` Bloque D.1: keys lowercase
- Eliminar `EMPLOYEE` y `AFFILIATE-CU` del set (no son eduPerson canónicos)
- Auditar sub-templates: `user-template-employee-staff.xml`, `user-template-employee-faculty.xml`, `user-template-alumni.xml`

**Modificar inbounds de 5 resources Oracle**:
- Cambiar destino de `extension/sciback:primaryAffiliation` → `extension/sciback:affiliations` (add, weak)
- Resource Trabajadores: mapear `employee` → `staff` en el inbound (adapter responsibility, no template)

#### 1.2 — Eliminar Bloque R (asignación AR-Koha-Jubilado)

- Comentar el Bloque R en `UserTemplate-Person-Base.xml`
- Documentar: jubilados nuevos ya no recibirán el rol
- Los 6 jubilados existentes lo conservan transitoriamente (red de seguridad)

#### 1.3 — Bloque K nuevo: override condicional jubilados (Decisión B)

**Decisión B**: jubilado → `alum` SOLO si no hay affiliation activa de mayor prioridad.

```groovy
def mc = motivoCese != null ? basic.stringify(motivoCese).trim().toLowerCase() : ''
if (mc != 'jubilacion') return null  // no aplica

// Decisión B: si hay affiliation activa de mayor prioridad que alum, dejar que J3 calcule
def affs = (affiliations ?: []).collect { basic.stringify(it).trim().toLowerCase() }
    .findAll { it in ['faculty','staff','student','alum','affiliate'] } as Set
def HIGHER_THAN_ALUM = ['faculty','staff','student'] as Set
if (affs.any { it in HIGHER_THAN_ALUM }) return null  // J3 ganará (faculty/staff/student)

// Jubilado puro o jubilado + affiliate → forzar alum
return 'alum'
```

**Strength**: `strong`.

**Mapping side `formerRole`** (mismo bloque): si se dispara `alum`, escribe `extension/upeu:formerRole = staff|faculty` (lo que tenía antes en `affiliations`).

**Casos resueltos**:
- Jubilado puro (sin más affiliations) → `alum`, formerRole=staff/faculty
- Jubilado + estudiante posgrado → `student` (J3 gana, no toca formerRole)
- Jubilado + recontratado docente → `faculty` (J3 gana)
- Jubilado + alumni preexistente → `alum`, formerRole=staff/faculty

#### 1.4 — Recompute masivo (ventana de mantenimiento)

**Pre-requisitos críticos**:
- ✅ Tag git: `git tag pre-fase1-recompute-masivo`
- ✅ pg_dump de `m_user` y `m_assignment`
- ✅ Categorías Koha nuevas YA EXISTEN (Fase 3 completada)

Task: `iterative-recompute` sobre `UserType`, filter `lifecycleState=active`. Estimado 30-45 min sobre 35,450 users.

Validación inmediata post-recompute (queries psql):
```sql
SELECT ext->>'78' AS aff, COUNT(*) FROM m_user
WHERE lifecyclestate='active'
GROUP BY 1 ORDER BY 2 DESC;
```
Esperado: 5 valores canónicos lowercase + null. Si aparece `STAFF`/`FACULTY` uppercase: bug en el rename.

#### 1.5 — Vaciar inducements AR-Koha-Jubilado (~7 días post-1.4)

- Solo ejecutar si Fase 1 estable en PROD
- Vaciar `<inducement>` del rol (convierte en no-op)
- NO eliminar el rol todavía — preserva auditoría hasta Fase 8

### Tests de validación (casos PROD reales)

| Caso | OID | Esperado |
|---|---|---|
| Jubilado puro (faculty) | `1609b661-04e1-4246-b9ab-6b8d084724b0` (COD_APS 21835727) | `primaryAffiliation=alum`, `formerRole=faculty`, lifecycle activo |
| Staff activo | cualquiera costCenter=area.97 | `primaryAffiliation=staff` (lowercase) |
| Docente activo | cualquiera DOCEN | `primaryAffiliation=faculty` |
| Egresado puro | usuario solo en Egresados v3 | `primaryAffiliation=alum` |
| Multi-rol staff+alum | egresado contratado | `staff` (prioridad J3) |
| Estudiante puro | matriculado activo | `student` |
| Jubilado + estudiante posgrado | (buscar uno) | `student` (J3 gana — Decisión B) |
| `employee` huérfano | usuarios con `EMPLOYEE` antiguo | filtrado → mapeado a `staff` en inbound |

### Riesgos no obvios (del análisis midpoint-expert)

1. **Sub-templates** con vocabulario uppercase — auditar simultáneamente
2. **`R-Affiliation-Employee`** y `R-Affiliation-Affiliate-CU` deprecated — migración previa: unassign + reassign
3. **`assignmentTargetSearch` cache** — reset cache MidPoint post-rename
4. **Logging volume** — Bloque J3 usar `log.debug` para filtrados, `log.warn` solo si vacío
5. **Egresados v3 weak**: tras cambio, escribirá en `affiliations`. Verificar que no deje `primaryAffiliation` huérfano en usuarios solo-alum.

### Rollback granular

| Sub-fase | Rollback |
|---|---|
| 1.0 schema | Sin rollback (atributo opcional sin uso) |
| 1.1 prioridad + rename | `git revert` + re-import template + recompute masivo |
| 1.2 Bloque R eliminado | Restaurar Bloque R desde tag git |
| 1.3 Bloque K | Eliminar Bloque K + recompute jubilado |
| 1.4 recompute masivo | `pg_restore` de `m_user`+`m_assignment` |
| 1.5 inducements vacíos | Restaurar inducements desde tag git |

**Tag obligatorio antes de Fase 1**: `git tag pre-fase1-koha-categorycodes`

---

## Fase 2 — Crear rol R-Researcher

### Archivo nuevo: `canonical/roles/business/R-Researcher.xml`

```xml
<role>
  <name>R-Researcher</name>
  <description>Rol funcional: investigador (DGI / RENACYT).
    Ortogonal a primaryAffiliation. Una persona puede ser faculty/staff/student/alum
    Y simultáneamente researcher. Proyecta extended_attribute RESEARCHER=Y en Koha.</description>
  <archetypeRef oid="..." type="ArchetypeType"/> <!-- archetype-role-business -->
  <inducement>
    <!-- Koha: extended_attribute RESEARCHER=Y -->
    <construction>
      <resourceRef oid="9b5a7c81-47aa-42ac-9a08-4de8b64935af"/>
      <kind>account</kind>
      <attribute>
        <ref>ri:RESEARCHER</ref>
        <outbound>
          <strength>strong</strength>
          <expression><value>Y</value></expression>
        </outbound>
      </attribute>
    </construction>
  </inducement>
  <!-- Asignación: manual O desde resource CSV DGI cuando se cree -->
</role>
```

### Validación

- Asignar manualmente a 1 usuario de prueba (un docente RENACYT conocido) → verificar que aparece `extended_attribute RESEARCHER=Y` en su patron Koha
- Verificar que NO cambia su categorycode (sigue `faculty`)

### Despliegue

```bash
git add canonical/roles/business/R-Researcher.xml
git commit -m "feat(roles): R-Researcher (rol funcional investigador)"
git push
# En PROD: git pull + POST al endpoint /model/roles
```

---

## Fase 3 — Koha: crear categorías nuevas en paralelo

### Categorías a crear

Para cada una, clonar configuración (`enrolment_period`, `category_type`, `default_privacy`, `reset_password`, `change_password`, `min_password_length`, `BlockExpiredPatronOpacActions`) de su equivalente actual:

| Nueva | Clonar de | Notas |
|---|---|---|
| `faculty` | DOCEN | category_type=P |
| `staff` | ADMINIST | category_type=S |
| `student` | ESTUDI (no PREGRADO/POSGRADO porque están vacías) | category_type=A |
| `alum` | ALUMNI | category_type=A |
| `affiliate` | VISITA | category_type=A |
| `local` | ANON | category_type=A — para sistema |

### Implementación

```sql
-- Ejecutar en MariaDB koha_bul (con backup previo de tabla categories)
INSERT INTO categories (categorycode, description, enrolmentperiod, ..., category_type)
SELECT 'faculty' AS categorycode,
       'Docente UPeU (eduPerson:faculty)' AS description,
       enrolmentperiod, ..., category_type
  FROM categories WHERE categorycode='DOCEN';
-- Repetir para staff, student, alum, affiliate, local
```

### Validación

- Crear 1 patron de prueba en cada nueva categoría desde Koha staff UI
- Hacer un préstamo de prueba con cada uno → verificar que circulation rules funcionan idénticas a las viejas

### Circulation rules

- Verificar tabla `circulation_rules`: si las viejas categorías tienen reglas específicas, clonarlas para las nuevas con `INSERT ... SELECT` similar
- Las nuevas categorías deben tener el MISMO comportamiento que las viejas antes de migrar patrones

---

## Fase 4 — Simplificar `koha-ils.xml` mapping

### Cambio principal en `upeu/resources/koha-ils.xml`

**ANTES** (líneas ~1030-1075):
```groovy
if (aff == 'faculty') return 'DOCEN';
if (aff == 'staff' || aff == 'employee') return 'ADMINIST';
if (aff == 'alum') return 'ALUMNI';
// Lógica student → PREGRADO/POSGRADO según studyLevel
def level = ...
if (level == 'maestria' || ...) return 'POSGRADO';
if (level == 'pregrado') return 'PREGRADO';
// + lógica jubilados (early-return null si motivoCese=jubilacion)
// + lógica investigador
```

**DESPUÉS**:
```groovy
// Mapping canónico eduPerson 202208.
// primaryAffiliation YA es el valor correcto (faculty|staff|student|alum|affiliate).
// Jubilados ya vienen como 'alum' desde el template (Bloque J3).
// Investigadores son rol R-Researcher (ortogonal), categorycode no cambia.
def aff = primaryAffiliation != null ? basic.stringify(primaryAffiliation).trim().toLowerCase() : null
if (!aff) return null
def VALID = ['faculty','staff','student','alum','affiliate'] as Set
if (!(aff in VALID)) {
    log.warn('koha-ils mapping: primaryAffiliation no canónico {} en {}', aff, focus?.name)
    return null
}
return aff
```

### Eliminar del archivo

- Construction `AR-Koha-Jubilado` strong override (marcar el rol como deprecated en Fase 1)
- Construction `AR-Koha-Investigador` planeada (NO crear; se reemplaza por R-Researcher rol)
- Mapping `category-id-from-primary-affiliation` lógica especial early-return jubilados

### Validación

- Recompute de 1 jubilado → categorycode debe ser `alum`
- Recompute de 1 docente → `faculty`
- Recompute de 1 estudiante → `student`
- Recompute de 1 docente con R-Researcher asignado → `faculty` Y extended_attribute `RESEARCHER=Y`

---

## Fase 5 — Reconciliación Koha: re-stamp 32K patrones IGA-managed

### Acción

Ejecutar reconciliación completa del resource Koha. MidPoint:
- Lee todos los users con linkRef a shadow Koha
- Aplica el nuevo mapping (`primaryAffiliation` literal)
- UPDATE `categorycode` en cada patron Koha

### Esperado

| Categoría nueva | Esperado aprox | Origen |
|---|---|---|
| `faculty` | ~290 | docentes activos + no-lifecycle MidPoint |
| `staff` | ~7,000 | trabajadores administrativos |
| `student` | ~1,700 | estudiantes activos |
| `alum` | ~30,000 | egresados + jubilados |
| `affiliate` | 0 (sin proceso aún) | pendiente futuro |

Total: ~38,990 patrones IGA-managed (más de 32K estimado porque incluye jubilados que migran de antes).

### Verificación

```sql
SELECT categorycode, COUNT(*) FROM borrowers GROUP BY 1 ORDER BY 2 DESC;
-- Esperado: nuevas categorías con counts ↑↑, viejas igual o ↓
```

---

## Fase 6 — Migración batch 22K patrones legacy

### Plan por categoría legacy

#### ESTUDI (20,392) → mayormente `alum`

Hipótesis: son estudiantes pre-IGA que ya son egresados pero no se han correlacionado con el resource Egresados v3.

1. Crear tabla log:
   ```sql
   CREATE TABLE borrowers_migration_log (
     borrowernumber INT, old_categorycode VARCHAR(10), new_categorycode VARCHAR(10),
     migration_phase VARCHAR(50), migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. Cross-check con Oracle Egresados:
   - Export DNIs de los 20,392 ESTUDI Koha (campo cardnumber)
   - Cruzar con `DAVID.VW_PERSONA_EGRESADO.NUM_DOCUMENTO`
   - Lista A: matchean → migrar a `alum` automáticamente
   - Lista B: NO matchean → expurgo manual o `local` temporal

3. Migrar Lista A:
   ```sql
   INSERT INTO borrowers_migration_log (...)
     SELECT borrowernumber, 'ESTUDI', 'alum', 'fase6-estudi-to-alum' FROM borrowers WHERE ...;
   UPDATE borrowers SET categorycode='alum' WHERE borrowernumber IN (lista_a);
   ```

#### VISITA (2,575) → `affiliate`

```sql
INSERT INTO borrowers_migration_log SELECT borrowernumber, 'VISITA', 'affiliate', 'fase6-visita' FROM borrowers WHERE categorycode='VISITA';
UPDATE borrowers SET categorycode='affiliate' WHERE categorycode='VISITA';
```

#### STAFF (4) → `staff`

```sql
UPDATE borrowers SET categorycode='staff' WHERE categorycode='STAFF';
```

#### ANON (1), ADMIN (1) → `local`

```sql
UPDATE borrowers SET categorycode='local' WHERE categorycode IN ('ANON','ADMIN');
```

### Validación

- Counts post-migración: cada categoría vieja debe tener `COUNT=0`
- Cada nueva debe haber incrementado por los valores migrados
- `borrowers_migration_log` debe tener N filas = total migrado

---

## Fase 7 — Observación 2 semanas

### Monitoreo diario

- **Préstamos/devoluciones**: queries sobre `issues` y `old_issues` para detectar comportamientos anómalos por categoría
- **OPAC login**: revisar logs de error para usuarios que no logran ingresar
- **Multas**: verificar que cálculos de multas siguen correctos por categoría
- **Reportes COUNTER**: ejecutar y comparar contra ejecuciones pre-migración
- **MidPoint reconciliaciones**: que no aparezcan AlreadyExists ni PolicyViolations nuevos

### Comunicación

- Email a bibliotecarios explicando cambio de nombres en UI (DOCEN→faculty, etc.)
- Cheat-sheet con tabla de equivalencias antiguo↔nuevo para los próximos meses
- Disponibilidad guardia de Alberto para incidentes durante semana 1

---

## Fase 8 — Cleanup: drop categorías viejas

### Pre-condición

- `SELECT COUNT(*) FROM borrowers WHERE categorycode IN ('DOCEN','ADMINIST','ESTUDI','ALUMNI','PREGRADO','POSGRADO','JUBILADO','INVESTI','VISITA','STAFF') = 0`
- 2 semanas observación sin incidentes críticos
- Confirmación biblioteca + DTI

### Acciones

```sql
-- Backup tabla categories antes del DROP
CREATE TABLE categories_pre_eduperson_backup AS SELECT * FROM categories;

-- Drop categorías viejas
DELETE FROM categories WHERE categorycode IN
  ('DOCEN','ADMINIST','ESTUDI','ALUMNI','PREGRADO','POSGRADO',
   'JUBILADO','INVESTI','VISITA','STAFF');

-- Drop circulation rules huérfanas
DELETE FROM circulation_rules WHERE categorycode IN (lista_viejas);
```

### Cleanup MidPoint

- DELETE rol `AR-Koha-Jubilado` (no más necesario)
- Cleanup `koha-ils.xml`: eliminar comentarios de coexistencia
- Tag git: `git tag post-eduperson-categorycodes`

---

## Fase 9 — Post-mortem + gobernanza

### Documentar

- `docs/POST-MORTEM-koha-categorycodes-2026.md`: lecciones aprendidas, métricas reales vs estimadas, incidentes
- `docs/governance/koha-categorycodes.md`: matriz de categorycodes oficial. Cualquier nuevo valor requiere PR + revisión. Justificar por qué no encaja en eduPerson antes de crear local.

### Diseñar gobernanza permanente

Para evitar volver a la entropía actual en 2-3 años:
- Cualquier nueva categoría Koha requiere PR documentado
- Cualquier modificación de mapping `koha-ils.xml` requiere actualización de la matriz docs
- Review trimestral del modelo de categorycodes

---

## Riesgos identificados

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Reportes COUNTER/INEI rompen | Media | Alto | Inventario Fase 0; actualizar SQL antes de Fase 8 |
| Circulation rules no clonadas correctamente | Baja | Alto | Pruebas con patron de cada categoría Fase 3 |
| 20K ESTUDI no correlacionan con Egresados | Media | Medio | Lista B va a `local` temporal, análisis manual |
| Bibliotecarios confundidos por cambio UI | Alta | Bajo | Email + cheat-sheet + soporte 1 semana |
| Multi-affiliation prioridad mal implementada | Baja | Medio | Tests Fase 1 + observación Fase 7 |
| Multas calculadas distinto post-migración | Baja | Alto | Validar circulation_rules clonadas + monitoreo Fase 7 |

## Rollback strategy

### Si falla Fase 1-4 (MidPoint)
- `git revert` del commit
- `git push`
- `git pull` en PROD
- Re-aplicar XML viejo vía REST API

### Si falla Fase 5 (reconciliación)
- Detener task de reconciliación
- Revert mapping a versión anterior
- Re-reconciliar para volver categorycodes viejos

### Si falla Fase 6 (batch SQL)
- `UPDATE borrowers SET categorycode=old_categorycode FROM borrowers_migration_log WHERE migration_phase='fase6-*'`
- Verificar counts post-rollback

### Catastrófico (cualquier fase)
- Restaurar `koha_bul_pre_eduperson_YYYYMMDD.sql`
- `git checkout pre-eduperson-categorycodes` y push
- Comunicación inmediata a usuarios

---

## Métricas de éxito

- ✅ Mapping `koha-ils.xml` reducido de 30 líneas condicionales a 3-5 líneas declarativas
- ✅ 6 categorías Koha activas (vs 12 actuales)
- ✅ 0 patrones en categorías legacy post-Fase 7
- ✅ 0 incidentes críticos durante observación
- ✅ Counts esperados por nueva categoría coinciden con MidPoint (±5%)
- ✅ Reportes COUNTER funcionando con SQL actualizados
- ✅ Bibliotecarios reportan UI funcional tras 2 semanas
