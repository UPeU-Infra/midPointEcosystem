# Estructura organizacional UPeU — Hallazgos de descubrimiento

**Fecha:** 2026-05-26
**Objetivo:** Consolidar todas las fuentes encontradas sobre estructura organizacional, MOF (Manual de Organización y Funciones), áreas, cargos y jerarquías de UPeU. Base para diseñar el resource Oracle ORG y el conector M365.

---

## 1. Fuentes web públicas (transparencia upeu.edu.pe)

### 1.1 Organigrama oficial — PDF

**URL:** https://upeu.edu.pe/pdf/Organigrama.pdf
**Visor:** https://upeu.edu.pe/visor/visor.html (iframe que apunta al PDF)
**Página contenedora:** https://upeu.edu.pe/organigrama/
**Resolución oficial:** **Resolución N° 0001-2026/UPeU-AU** (Asamblea Universitaria)

Estructura completa (extraída del PDF):

```
Asamblea Universitaria  ──  Unión Peruana del Norte
        │
Consejo Universitario
        │
   Rectorado  ────  Defensoría Universitaria
   │              ─  Tribunal de Honor Universitario
   │
   ├── Dirección de Cooperación y Proyectos
   ├── Dirección de Planificación y Gestión de la Calidad  ──  Dirección de Fondo Editorial (funcional)
   ├── Auditoría Interna
   ├── Dirección de Imagen Institucional y Relaciones Públicas
   ├── Secretaría General
   ├── Dirección de Misión                                ──  Asesoría Legal (funcional)
   │
   ├── Vicerrectorado Académico
   │       ├── Dirección de Asuntos Académicos
   │       ├── Dirección de Investigación e Innovación
   │       ├── Dirección de Educación Adventista a Distancia
   │       ├── Decanato Facultad
   │       │       └── Dirección de Escuela Profesional
   │       └── Dirección de Escuela de Posgrado
   │               └── Dirección de Unidad de Posgrado
   │
   ├── Vicerrectorado Administrativo
   │       ├── Centro de Producción Imprenta Unión
   │       ├── Centro de Producción de Bienes Unión
   │       ├── Dirección de Marketing
   │       ├── Dirección de Tecnologías de Información  ←  DTI (área del usuario)
   │       ├── Dirección de Talento Humano
   │       ├── Dirección Financiera
   │       ├── Dirección de Operaciones Campus
   │       └── Dirección de Infraestructura
   │
   ├── Vicerrectorado de Bienestar Universitario
   │       ├── Dirección de Universidad Saludable
   │       ├── Dirección de Bienestar Universitario
   │       ├── Dirección Programa Deportivo de Alta Competencia
   │       └── Dirección Instituto de Desarrollo del Estudiante Colportor
   │
   └── Dirección General de Campus  ──  Lima, Juliaca, Tarapoto
```

Leyenda del PDF:
- Línea sólida = mando jerárquico
- Línea punteada = coordinación funcional
- Casilla amarilla = Campus
- Casilla azul = Institucional / Sede

Notas:
- `Dirección General de Campus` aparece como bloque diferenciado para Lima, Juliaca y Tarapoto.
- `Dirección de Operaciones Campus` y `Dirección de Bienestar Universitario` aparecen marcadas en amarillo (Campus) en el PDF — son las únicas con replicación por sede a nivel ejecutivo.

### 1.2 Página de transparencia

**URL:** https://upeu.edu.pe/transparencia/
Contenido relevante:
- TUPA (Texto Único de Procedimientos Académico-Administrativos)
- Cronogramas y resultados de Concurso a la Docencia Ordinaria
- Convocatoria pública interna
- Plan Estratégico
- Normatividad institucional

No expone MOF en PDF público ni base de datos abierta.

### 1.3 Página de normatividad

**URL:** https://upeu.edu.pe/normatividad-institucional/
Contiene links a sistemas internos (lamb-academic, lamb-talent, etc.) pero no MOF descargable.

### 1.4 Sistemas web internos descubiertos

| URL | Tipo | Acceso |
|---|---|---|
| https://lamb-academic.upeu.edu.pe/ | Sistema académico (Angular SPA) | Requiere auth |
| **https://lamb-talent.upeu.edu.pe/** | **Sistema de RRHH / Talent** | **Requiere auth — Angular SPA "LambTalentShellFront"** |
| https://lamb-files.upeu.edu.pe/ | Repositorio de archivos (fotos) | Auth + cert TLS |
| https://investigacion.upeu.edu.pe/ | DGI (Dirección General de Investigación) | Web pública parcial |
| https://repositorio.upeu.edu.pe/ | DSpace institucional | Público |

`lamb-talent.upeu.edu.pe` es el frontend del sistema de gestión de talento humano. Backend probablemente Oracle LAMB schema ENOC. No tiene API REST pública expuesta.

---

## 2. Oracle LAMB — tablas y vistas de estructura organizacional

Hallazgo confirmado mediante JDBC desde el contenedor MidPoint (`ojdbc11-23.6.0.24.10.jar`).

### 2.1 Schema ELISEO — módulo principal de organización

| Objeto | Tipo | Filas | Descripción |
|---|---|---|---|
| `ELISEO.ORG_SEDE` | TABLE | 6 | Sedes institucionales (Lima, Juliaca, Tarapoto, ISTAT, CGH, AGTU) |
| `ELISEO.ORG_AREA` | TABLE | 8,026 | **Árbol completo de áreas/unidades** con jerarquía (`ID_PARENT`, `IZQUIERDA`/`DERECHA` = nested set). Incluye facultades, vicerrectorados, direcciones, EAPs |
| `ELISEO.ORG_SEDE_AREA` | TABLE | 5,665 | Mapeo área↔sede, con `ID_DEPTO` (código contable 8 dígitos), `ID_PERSONA` responsable |
| `ELISEO.VW_SEDE_AREA` | VIEW | — | Join completo: área + sede + centro de costo (`CCOSTO`) + jerarquía |
| `ELISEO.VW_AREA` | VIEW | — | Áreas enriquecidas con tipo (`TIPO_AREA`), conteo de dependientes |
| `ELISEO.VW_AREA_DEPTO` | VIEW | — | **Vista más limpia para integración** — área padre + área + código contable + departamento LAMB |
| `ELISEO.APS_CARGO` | TABLE | ~500+ | Cargos APS (nómina): "Director General", "Mecánico", "Asistente de Gerencia"… |
| `ELISEO.ORG_ESCUELA_PROFESIONAL` | TABLE | 10 | Mapeo EP ↔ área (`ID_EP`, `ID_AREA`) |

### 2.2 Schema ENOC — módulo de puestos y RRHH

| Objeto | Tipo | Filas | Descripción |
|---|---|---|---|
| `ENOC.PLLA_PUESTO` | TABLE | 1,010 | **Puestos formales** con nombre, grupo de escala, competencias |
| `ENOC.VW_PERFIL_PUESTO` | VIEW | — | Perfil completo: área, depto, misión, email funcional, jerarquía (`ID_PERFIL_PUESTO_JEFE`), autonomía, requisitos |
| `ENOC.VW_ENT_DEP_AREA_CCOSTO` | VIEW | — | Área + centro de costo + entidad contable |
| `ENOC.VW_TRABAJADOR` | VIEW | — | Persona → `ID_SEDEAREA` + `ID_PUESTO` + correo institucional |
| `ENOC.PLLA_CESE` | TABLE | — | Cese de trabajadores (motivo, fecha) — ya usado en trabajadores v3 |

### 2.3 Schema JOSUE — admisiones/carreras

| Objeto | Tipo | Filas | Descripción |
|---|---|---|---|
| `JOSUE.CONFIG_CARGO` | TABLE | 54 | Cargos académico-administrativos con nombre M/F, si es puesto directivo |
| `JOSUE.CONFIG_CARGOHIERARCHY` | TABLE | ~50+ | Jerarquía de cargos |

### 2.4 Schema MOISES — histórico de asignaciones

| Objeto | Tipo | Descripción |
|---|---|---|
| `MOISES.TRABAJADOR_AREA` | TABLE | Historial área por trabajador (DESDE/HASTA) |
| `MOISES.TRABAJADOR_PUESTO` | TABLE | Historial puesto por trabajador (DESDE/HASTA, `ID_PERFIL_PUESTO`) |

### 2.5 Schema JAIRO — data mart (BI)

| Objeto | Tipo | Descripción |
|---|---|---|
| `JAIRO.DM_AREA` | TABLE | Réplica BI de áreas |
| `JAIRO.DM_SEDE_AREA` | TABLE | Réplica BI de áreas por sede |
| `JAIRO.DM_AREA_RESPONSABLE` | TABLE | Responsables por área |

### 2.6 Schema JONAS — académico

| Objeto | Tipo | Descripción |
|---|---|---|
| `JONAS.VW_UNIDAD_ACADEMICA` | VIEW | **Sin acceso SELECT** desde el usuario actual |
| `JONAS.EVENTO_CARGO`, `EVENTO_TIPO_PUESTO` | — | Eventos académicos |

### 2.7 Schema PABLO — eclesiástico (no aplica)

`PABLO.CARGO` — 2 registros (Anciano, Mayordomo). Módulo eclesiástico, irrelevante para IGA universitaria.

---

## 3. Jerarquía confirmada (muestreo Oracle)

Estructura visible en muestras de `ELISEO.ORG_AREA`:

| ID_AREA | Nombre | Tipo |
|---|---|---|
| 4 | Vicerrectorado de Bienestar Universitario | VR |
| 5 | Vicerrectorado Académico | VR |
| 6 | Vicerrectorado Administrativo | VR |
| 12 | Facultad de Ciencias Empresariales | Facultad |
| 13 | Dirección Financiera (Dir. Financiero Contable) | Dirección |
| 18 | **Dirección de Tecnologías de Información (DTI)** | Dirección (área del usuario) |
| 97 | Colegio Unión (sede Lima) | Externo |
| 103 | EP Ciencias de la Comunicación | EAP |
| 522 | (CRAI) | — |
| 625 | (CRAI) | — |

### Áreas CRAI identificadas (Personal Biblioteca → AR-Koha-Librarian)

Las áreas con `costCenter = area.97`, `area.522`, `area.625` corresponden al personal del **CRAI** (Centro de Recursos para el Aprendizaje y la Investigación). Birthright Q4 en `user-template-employee-staff.xml` les asigna `AR-Koha-Librarian` (AREA=CRAI).

---

## 4. Caminos de resolución para IGA

### Camino canónico: trabajador → área → sede → centro de costo

```
ENOC.VW_TRABAJADOR.ID_PERSONA
  → ID_SEDEAREA → ELISEO.VW_SEDE_AREA  (nombre área + sede + CCOSTO)
  → ID_PUESTO   → ENOC.PLLA_PUESTO     (nombre del puesto)
  → ID_PERFIL_PUESTO → ENOC.VW_PERFIL_PUESTO  (email funcional, jefe, misión)
```

### Estado actual en MidPoint

- El campo `costCenter` ya se popula desde el resource `oracle-lamb/trabajadores.xml` con el formato `area.<ID_SEDEAREA>`.
- No hay sincronización del **árbol de áreas** hacia `OrgType` — los users tienen el `costCenter` como string suelto, sin objeto `OrgType` correspondiente en el repo MidPoint.
- No hay sincronización de `jobTitle` desde `ENOC.PLLA_PUESTO` (los users tienen el campo vacío o con valor manual).

---

## 5. Propuesta de uso para el resource ORG nuevo

### 5.1 Resource canónico (M365, decisión midpoint-expert)

- **Nombre:** `oracle-lamb-org.xml`
- **Ubicación:** `upeu/resources/oracle-lamb/org.xml`
- **`kind`:** `generic`
- **`intent`:** `orgunit`
- **`focus`:** `OrgType`
- **Archetype:** `archetype-org-unit` (canonical)
- **SQL principal:** `SELECT * FROM ELISEO.VW_AREA_DEPTO` con `ELISEO.ORG_SEDE_AREA` para resolver sede.
- **Parentesco:** mapping inbound de `ID_PARENT` resuelve `parentOrgRef` vía `assignmentTargetSearch` (libro cap. 10.6 "Synchronization of org structure").

### 5.2 Atributos a sincronizar

| Oracle | MidPoint `OrgType` | Nota |
|---|---|---|
| `ID_AREA` | `extension/upeu:areaId` (interno) | Identificador inmutable |
| `ID_DEPTO` (8 dígitos) | `identifier` | Código contable estable |
| `NOMBRE_AREA` | `name` + `displayName` | PolyString |
| `ID_PARENT` | resuelve a `parentOrgRef` | Vía `assignmentTargetSearch` |
| `ID_SEDE` | `extension/upeu:sedeId` | Lima/Juliaca/Tarapoto |
| `CCOSTO` | `extension/upeu:ccosto` | Centro de costo |
| `TIPO_AREA` | `extension/upeu:tipoArea` | Para filtros |

### 5.3 Lo que NO va en este resource (doctrina Patrón B)

Este resource **NO declara inbounds de datos personales**. Su `focus` es `OrgType`, no `UserType`. La relación user↔org la mantiene `trabajadores.xml` con el atributo `costCenter`.

### 5.4 Para `jobTitle` del trabajador (futuro, fuera del scope ORG)

Cuando se sincronice `extension/sb:jobTitle`, será desde `ENOC.PLLA_PUESTO` via `trabajadores.xml` (NO un resource separado), porque es atributo del UserType y `trabajadores` ya es IIA de empleo.

---

## 6. Limitaciones encontradas

1. **`JONAS.VW_UNIDAD_ACADEMICA` no es accesible** desde el usuario JDBC actual. Probablemente contiene info adicional de unidades académicas; pedir acceso a DBA si se necesita.
2. **MOF formal no expuesto** ni en web pública ni en Oracle LAMB con esa nomenclatura. Las funciones por puesto viven en `ENOC.VW_PERFIL_PUESTO` (campo `MISION` y `COMPETENCIAS`).
3. **No hay tabla de "directorio institucional"** con autoridades nominales actualizadas. El responsable de cada área se almacena en `ELISEO.ORG_SEDE_AREA.ID_PERSONA` (FK a persona), pero no hay UI pública que lo exponga.

---

## 7. Próximos pasos sugeridos

1. **Construir `oracle-lamb-org.xml`** (Ola 2, antes/durante M365) siguiendo Patrón B y libro cap. 10.6.
2. **Definir archetype `archetype-org-unit`** si no existe en `canonical/archetypes/` (verificar primero).
3. **Crear `archetype-vicerrectorado`**, `archetype-direccion`, `archetype-facultad`, `archetype-eap` como sub-archetypes si se necesita diferenciación visual.
4. **Sincronizar 1 sede primero** (Lima) como piloto antes de extender a Juliaca y Tarapoto.
5. **Solicitar acceso a DBA** para `JONAS.VW_UNIDAD_ACADEMICA` si la información de unidades académicas resulta necesaria para el provisioning M365.

---

## 8. Material físico guardado

| Archivo | Ubicación | Descripción |
|---|---|---|
| `Organigrama.pdf` | `/tmp/Organigrama.pdf` (temporal) | PDF oficial Res. 0001-2026/UPeU-AU |
| `Directorio UPeU 2026.xlsx` | `datasets/fuentes-externas/` | Directorio institucional Infra |
| `Horas de investigacion 2026.xlsx` | `datasets/fuentes-externas/` | Excel DGI (Charmín) |
| `Investigadores-DGI-2026-con-DNI.xlsx` | `datasets/fuentes-externas/` | DGI enriquecido con DNI |

Se recomienda mover `Organigrama.pdf` a `datasets/fuentes-externas/` para preservar la versión oficial 2026.

---

## Referencias

- Semančík et al., "Practical Identity Management with MidPoint" v2.3, cap. 10 (Organizational Structures), §10.6 (Generic Synchronization).
- Resolución N° 0001-2026/UPeU-AU (Asamblea Universitaria UPeU).
- Skill `iga-canonical-standards` (eduPerson 202208, SCHAC, ISO 24760, RBAC).
- Skill `midpoint-best-practices` (FunctionLibrary, archetype patterns, IIA).
