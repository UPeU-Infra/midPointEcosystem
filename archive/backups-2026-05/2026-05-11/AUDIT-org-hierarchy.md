# AUDIT — Jerarquía de Orgs MidPoint PROD
**Fecha:** 2026-05-11  **Servidor:** 192.168.15.166  **Fuente:** `orgs-dump.json` (91 orgs vía REST)

## Resumen estadístico

- **Total orgs:** 91
- **Raíces (sin parentOrgRef):** 1 → esperado 1 (UPeU) ✅
- **Huérfanas (parent inexistente):** 0 ✅
- **Multi-parent:** 0 ✅ (esperado 0 — Cf. midpoint-best-practices §5.2 acyclic directed graph)
- **Ciclos detectados:** 0 ✅
- **No alcanzables desde root:** 0 ✅

### Distribución por profundidad

| Profundidad | Orgs |
|---|---|
| 0 | 1 |
| 1 | 8 |
| 2 | 11 |
| 3 | 37 |
| 4 | 34 |

### Distribución por archetype

| Archetype OID | Orgs |
|---|---|
| `73795c10` | 36 |
| `04c304d1` | 31 |
| `20ee260b` | 12 |
| `87f84549` | 5 |
| `79bd8a9e` | 3 |
| `a0c2e4e3` | 3 |
| `455d90ab` | 1 |

## Veredicto

✅ **Tree sano. Se puede proceder a Fase 3 (Object Templates canónicos) sin intervención manual.**

- 1 root (UPeU), 0 huérfanas, 0 ciclos, 0 multi-parent, 91/91 alcanzables.
- `parentOrgRef` consistente — permite queries de subtree según midpoint-best-practices §5.7.
- Estructura conforme a §5.2 (acyclic directed graph).
- Profundidad máxima 4 — razonable para una universidad.

## Tree completo
```
UPeU — UPeU
  ├─ DIR-GENERAL-CAMPUS — Dirección General de Campus
  │  ├─ DIR-GENERAL-CAMPUS-JULIACA — Dirección General de Campus – Juliaca
  │  │  └─ DIR-CRAI-JULIACA — Dirección del CRAI
  │  ├─ DIR-GENERAL-CAMPUS-LIMA — Dirección General de Campus – Lima
  │  │  ├─ CENTRO-IDIOMAS-LIMA — Centro de Idiomas
  │  │  ├─ CONSERV-MUSICA-LIMA — Conservatorio de Música
  │  │  ├─ COORD-CEPRE-LIMA — Coordinación CEPRE
  │  │  ├─ COORDINACION-COMUNIC-LIMA — Coordinación de Comunicaciones
  │  │  ├─ COORDINACION-TI-LIMA — Coordinación Tecnologías de Información - Lima
  │  │  │  ├─ CONTINUIDAD-SERVICIOS-LIMA — Continuidad de los Servicios TI - Lima
  │  │  │  ├─ INFRAESTRUCTURA-TI-LIMA — Infraestructura TI - Lima
  │  │  │  └─ OPERACIONES-SOPORTE-TI-LIMA — Operaciones y Soporte Tecnológico - Lima
  │  │  ├─ DIR-COLEGIO-LIMA — Dirección de Colegio
  │  │  ├─ DIR-CRAI-LIMA — Dirección del CRAI
  │  │  │  ├─ CRAI-ADQUISICIONES-LIMA — Adquisiciones
  │  │  │  ├─ CRAI-PROC-TECNICOS-LIMA — Procesos Técnicos
  │  │  │  ├─ CRAI-REPOSITORIO-LIMA — Repositorio Institucional
  │  │  │  ├─ CRAI-SECRETARIA-LIMA — Secretaría del CRAI
  │  │  │  ├─ CRAI-SERV-TEC-LIMA — Servicios Tecnológicos del CRAI
  │  │  │  └─ CRAI-SERV-USUARIO-LIMA — Servicios al Usuario
  │  │  ├─ DIR-INST-SUP-LIMA — Dirección de Instituto Superior
  │  │  ├─ IGLESIA-UNIV-LIMA — Iglesia Universitaria
  │  │  └─ SOS-AMBIENTAL-LIMA — Sostenibilidad Ambiental
  │  ├─ DIR-GENERAL-CAMPUS-TARAPOTO — Dirección General de Campus – Tarapoto
  │  │  └─ DIR-CRAI-TARAPOTO — Dirección del CRAI
  │  └─ DIR-INSTITUTO-SUPERIOR — Dirección de Instituto Superior
  ├─ GOBIERNO-UNIVERSITARIO — Gobierno Universitario
  │  ├─ ASAMBLEA-UNIVERSITARIA — Asamblea Universitaria
  │  ├─ CONSEJO-UNIVERSITARIO — Consejo Universitario
  │  ├─ DECANATOS-FACULTADES — Decanato Facultad Director de EPG
  │  │  └─ DIRECTOR-EP-UPG — Director de EP Director de UPG
  │  ├─ RECTORADO — Rectorado
  │  │  ├─ ASESORIA-LEGAL — Asesoria Legal
  │  │  ├─ AUDITORIA-INTERNA — Auditoria Interna
  │  │  ├─ DEFENSORIA-UNIVERSITARIA — Defensoría Universitaria
  │  │  ├─ DIR-COOPERACION-Y-PROYECTOS — Dirección de Cooperación y Proyectos
  │  │  ├─ DIR-FONDO-EDITORIAL — Dirección de Fondo Editorial
  │  │  ├─ DIR-IMAGEN-INSTITUCIONAL-RRPP — Dirección de Imagen Institucional y Relaciones Públicas
  │  │  ├─ DIR-MISION — Dirección de Misión
  │  │  ├─ DIR-PLANIFICACION-CALIDAD — Dirección de Planificación y Gestión de la Calidad
  │  │  └─ SECRETARIA-GENERAL — Secretaria General
  │  ├─ VICERRECTORADO-ACADEMICO — Vicerrectorado Académico
  │  │  ├─ DIR-ASUNTOS-ACADEMICOS — Dirección de Asuntos Académicos
  │  │  │  ├─ COORDINACION-ACADEMICA — Coordinación Académica
  │  │  │  ├─ GABINETE-PEDAGOGICO — Gabinete Pedagógico
  │  │  │  ├─ GESTION-CURRICULAR — Gestión Curricular
  │  │  │  ├─ SEGUIMIENTO-EGRESADOS — Seguimiento a Egresados
  │  │  │  └─ TUTORIA-UNIVERSITARIA — Tutoría Universitaria
  │  │  ├─ DIR-EDUCACION-DISTANCIA — Dirección de Educación a Distancia
  │  │  │  ├─ COORDINACION-APRENDIZAJE-DIGITAL — Coordinación de Aprendizaje Digital
  │  │  │  └─ COORDINACION-EDUCACION-CONTINUA — Coordinación de Educación Continua
  │  │  ├─ DIR-INVESTIGACION-E-INNOVACION — Dirección de Investigación e Innovación
  │  │  │  └─ SUBDIR-INVESTIGACION — Sub Dirección de Investigación e Innovación
  │  │  └─ FACULTADES — Facultades
  │  │     ├─ FACULTAD-EDUCACION — Facultad de Ciencias Humanas y Educación
  │  │     ├─ FACULTAD-EMPRESARIALES — Facultad de Ciencias Empresariales
  │  │     ├─ FACULTAD-INGENIERIA — Facultad de Ingeniería y Arquitectura
  │  │     ├─ FACULTAD-SALUD — Facultad de Ciencias de la Salud
  │  │     └─ FACULTAD-TEOLOGIA — Facultad de Teología
  │  ├─ VICERRECTORADO-ADMINISTRATIVO — Vicerrectorado Administrativo
  │  │  ├─ DIR-COMERCIAL — Dirección Comercial
  │  │  ├─ DIR-FINANCIERA — Dirección Financiera
  │  │  │  ├─ CONTABILIDAD-GENERAL — Contabilidad General
  │  │  │  ├─ FINANZAS-ALUMNOS — Finanzas Alumnos
  │  │  │  └─ TESORERIA-GENERAL — Tesorería General
  │  │  ├─ DIR-INFRAESTRUCTURA — Dirección de Infraestructura
  │  │  │  └─ DESARROLLO-PROYECTOS — Desarrollo de Proyectos
  │  │  ├─ DIR-MARKETING-COMUNICACIONES — Dirección de Marketing y Comunicaciones
  │  │  ├─ DIR-OPERACIONES-CAMPUS — Dirección de Operaciones Campus
  │  │  │  ├─ LOGISTICA-ACTIVOS — Logística y Activos
  │  │  │  └─ SERVICIOS-GENERALES — Servicios Generales
  │  │  ├─ DIR-TALENTO-HUMANO — Dirección del Talento Humano
  │  │  └─ DTI — Dirección de Tecnologías de Información
  │  │     ├─ ANALITICA-AVANZADA — Analítica Avanzada
  │  │     ├─ DESARROLLO-PROYECTOS-TI — Desarrollo de Proyecto TI
  │  │     └─ SEGURIDAD-INFORMACION — Seguridad de la Información
  │  └─ VICERRECTORADO-BIENESTAR-UNIVERSITARIO — Vicerrectorado de Bienestar Universitario
  │     ├─ DIR-IDEC — IDEC
  │     ├─ DIR-PRODAC — PRODAC
  │     ├─ DIR-UNIV-SALUDABLE — Dirección de Universidad Saludable
  │     └─ DIRECCION-BIENESTAR-UNIVERSITARIO — Dirección de Bienestar Universitario
  │        ├─ ASISTENCIA-SOCIAL — Asistencia Social
  │        ├─ COORD-MISION — Coordinación de Misión
  │        └─ COORD-RESIDENCIAS — Coordinación de Resid. Universitarias
  ├─ OU-CAMPUS-JULIACA — Campus Juliaca
  ├─ OU-CAMPUS-LIMA — Campus Lima
  ├─ OU-CAMPUS-TARAPOTO — Campus Tarapoto
  ├─ P-AGTU — American Global Tech University
  ├─ P-CGH — Clínica Good Hope
  └─ P-ISTAT — ISTAT
```

## Referencias
- midpoint-best-practices §5.2 — Org tree design (acyclic directed graph)
- midpoint-best-practices §5.7 — Provisioning con `resolveReference`
- midpoint-best-practices §5.1 — `parentOrgRef` operacional indexado
