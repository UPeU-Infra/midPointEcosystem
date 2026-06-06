# Role Mining LAMB — Análisis Fase 7.5
**Fecha:** 2026-06-06  
**Fuente:** `ELISEO.LAMB_ROL` + `ELISEO.LAMB_USUARIO_ROL` (Oracle LAMB, solo lectura)  
**Alcance:** UPeU entidad 7124

## Resumen ejecutivo

| Indicador | Valor |
|---|---|
| Roles totales en LAMB | 664 |
| Roles usados en UPeU | 606 |
| Personas con ≥1 rol LAMB | 100,042 |
| Roles auto-asignables por afiliación | ~4 (ya cubiertos en IGA) |
| Roles operacionales candidatos a AR | ~20 prioritarios |

## Taxonomía por prefijo

| Prefijo | Sistema | Roles | Personas | Naturaleza |
|---|---|---|---|---|
| `LU -` | LAMB Universidad (SIS) | 187 | 91,464 | Alumnos, docentes, operaciones académicas |
| `LA -` | LAMB Admisión | 20 | 55,578 | Postulantes (auto-asignado) |
| `DTH-` | RR.HH. (GTH) | 86 | 8,876 | Gestión de personal |
| `*` | Codificados (CODIGO=clave) | 39 | 1,415 | Roles funcionales estratégicos |
| `RESEARCH-` | DGI (investigación) | 14 | 798 | Dictaminadores, asesores, CIEP |
| `LS -` | LAMB Servicios | 17 | 680 | Mapas, planificación, calidad |
| `LE -` | LAMB Eventos | 7 | 1,425 | Control de eventos |
| `LF -` | LAMB Finanzas | 11 | 111 | Tesorería, estados de cuenta |
| Otros | Sin prefijo estructurado | 183 | 11,043 | Compras, logística, almacén |
| `UPN-` | Otro campus o legacy | 42 | 2,538 | No UPeU directos |

## Roles masivos auto-asignables (ya cubiertos en IGA o en roadmap)

| Rol LAMB | Personas | Equivalente IGA | Estado |
|---|---|---|---|
| `LU - ALUMNO` | 88,776 | BR-Alumno → AR-LAMB-SIS | Pendiente (LAMB no es resource write) |
| `LA - POSTULANTE` | 55,574 | — (postulantes fuera de scope IGA) | Out of scope |
| `LU - ALUMNO EGRESADO` | 20,594 | BR-Egresado | Pendiente |
| `TRABAJADOR` | 10,986 | BR-Employee | Pendiente |
| `DTH-TRABAJADOR - CANDIDATO` | 8,429 | — (candidatos no en MidPoint) | Out of scope |
| `LU - DOCENTE` | 5,492 | BR-Docente-TC / BR-Docente-TP | Parcial (auto-asignado en MidPoint, pero LAMB rol no provisionado) |

## Roles operacionales prioritarios — candidatos a AR en MidPoint

### Tier 1: >500 personas (impacto alto)

| Rol LAMB | Personas | Código | Categoría sugerida | Notas |
|---|---|---|---|---|
| `LU - MATRICULADOR` | 599 | 42 | AR-LAMB-Matriculador | Staff académico autorizado para matrícula |
| `LU - ADVISER` | 546 | 98 | AR-LAMB-Adviser | Consejero académico; se superpone con DTH/faculty |
| `RESEARCH-INV-DICTAMINADOR` | 720 | RSHDICT | AR-LAMB-Research-Dictaminador | Evaluador de proyectos DGI |
| `RESEARCH-INV-ASESOR` | 613 | RSHASES | AR-LAMB-Research-Asesor | Asesor de proyectos DGI |
| `LU - TUTORIA DE AULA` | 723 | 519 | AR-LAMB-TutorAula | Docente-tutor; derivable de carga docente |

### Tier 2: 100-500 personas (impacto medio)

| Rol LAMB | Personas | Código | Categoría sugerida | Notas |
|---|---|---|---|---|
| `RENDIR VALES Y DOCUMENTOS` | 457 | 249 | AR-LAMB-RendirVales | Rendición financiera; staff en general |
| `LA - ENTREVISTADOR` | 309 | 426 | AR-LAMB-Entrevistador | Admisión; personal específico |
| `DTH-JEFE DE ÁREA - CORPORATIVO` | 226 | 206 | → MOF-JEFE (ya existe) | Jefe de área; correlaciona con puesto |
| `LU - GESTOR PLANTILLA SILABO` | 266 | 88 | AR-LAMB-GestorSilabo | Coordinación curricular |
| `LU - TUTOR DOCENTE` | 232 | 481 | AR-LAMB-TutorDocente | Tutoría; derivable de carga docente |
| `GESTOR DE COMPRAS` | 202 | 375 | AR-LAMB-GestorCompras | Logística; por puesto |
| `APROBAR PEDIDOS` | 154 | 419 | AR-LAMB-AprobadorPedidos | Jefes de área; correlaciona con MOF-JEFE |
| `*DIRECTOR DE EP` | 148 | DIREP | → MOF-DIRECTOR-EP (ya existe) | Positional; ya en IGA |
| `LU - REPORTES` | 141 | 75 | AR-LAMB-Reportes | Acceso general a reportes |
| `RESEARCH-INV-CIEP` | 74 | RSHCIEP | AR-LAMB-Research-CIEP | Centro de investigación específico |

### Tier 3: Roles posicionales — mapeo a MOF ya existentes

| Rol LAMB | Código | MOF IGA equivalente | Decisión |
|---|---|---|---|
| `*SECRETARIA GENERAL - REGISTRO ACADÉMICO` | REGACAD | MOF-SG | Ya existe |
| `*DIRECTOR DE EP` | DIREP | MOF-DIRECTOR-EP | Ya existe |
| `*COORDINADOR EP` | COORDEP | MOF-COORDINADOR | Ya existe |
| `DTH-JEFE DE ÁREA - CORPORATIVO` | 206 | MOF-JEFE | Ya existe |
| `*DECANO` (implícito) | — | MOF-DECANO | Ya existe |

## Roles a NO incorporar en IGA

| Rol | Razón |
|---|---|
| Prefijo `UPN-` | No UPeU; campus ajeno o legacy contaminado |
| `TRABAJADOR-V2` (84) | Duplicado funcional de TRABAJADOR |
| `TEST`, `PARA PRUEVAS`, `ABC` | Roles de prueba inactivos (`ESTADO='0'`) |
| `DTH-TRABAJADOR - CANDIDATO` | Candidatos no son identidades IGA activas |
| `LA - POSTULANTE` | Postulantes fuera de scope IGA actual |

## Bloqueante arquitectónico: LAMB no es resource write

Actualmente **LAMB es fuente de verdad (lectura)** en MidPoint — no existe un resource de provisioning hacia LAMB. Para que los ARs listados arriba tengan efecto real, se requiere:

1. **Crear resource LAMB-SIS** (ScriptedSQL write) que provea `ELISEO.LAMB_USUARIO_ROL`
2. **Definir ARs** en MidPoint con `outbound` → INSERT/DELETE en LAMB_USUARIO_ROL
3. **Los BRs inducen los ARs** (BR-Docente-TC induce AR-LAMB-TutorAula, etc.)

Esto es **Fase 8** del roadmap. El presente análisis es el prerequisito de diseño.

## Hallazgo TC/TP (relacionado con D.3 Fase 7 Paso 3)

`MOISES.PERSONA_ACAD_REGIMEN.REGIMEN` contiene los valores literales `'TC'`, `'TP'`, `'DE'` (Dedicación Exclusiva):

| REGIMEN | Docentes activos UPeU |
|---|---|
| TP | 247 |
| TC | 175 |
| DE | 87 |
| NULL | 520 |
| (sin entrada) | ~7,600+ |

`ID_CATEGORIAOCUPACIONAL = 3` para el **100% de los activos** — no discrimina TC/TP. El fallback en D.3 (todos los faculty → BR-Docente-TC) es correcto mientras LAMB no exponga REGIMEN en el resource trabajadores.

**Próximo paso para TC/TP real**: añadir JOIN a `MOISES.PERSONA_ACAD_REGIMEN` en el searchScript de `oracle-lamb/trabajadores.xml` y exponer campo `DOCENTE_REGIMEN`. Ticket: DU-010.

## Recomendaciones Fase 7 completa

1. ✅ **Paso 1-2**: ARs versionados, lifecycleState corregido — COMPLETO
2. ✅ **Paso 3**: D.3 split fallback/TC/TP — COMPLETO (fallback activo, TC/TP esperando REGIMEN en resource)
3. ✅ **Paso 4**: SoD GOV-APROBADOR ⊥ GOV-REVISOR — COMPLETO (en PROD)
4. ✅ **Paso 5**: Role mining — COMPLETO (este documento)
5. **Fase 8** (próxima): Resource write LAMB-SIS + ARs operacionales tier 1-2

## Artefactos relacionados

- `canonical/policies/policy-sod-basic.xml` — SoD Paso 4
- `canonical/object-templates/UserTemplate-Person-Base.xml` — D.3 split
- `upeu/roles/application/` — 4 ARs nuevos versionados
- `upeu/roles/mof/*.xml` — 25 MOF roles con lifecycleState
- `upeu/roles/governance/*.xml` — 3 GOV roles con lifecycleState + SoD
