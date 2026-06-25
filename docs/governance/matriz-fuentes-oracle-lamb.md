# Consultas a validar con los DBAs — Fuentes Oracle LAMB (IGA UPeU / MidPoint)

**Fecha:** 2026-06-25
**Para:** Barrantes y Carlomagno (DBA / dueños de Oracle LAMB)
**De:** DTI Infraestructura — proyecto IGA (MidPoint)

## Cómo se construyó este documento

MidPoint lee Oracle LAMB (**solo lectura** — `create/update/delete=false`, jamás escribe) para construir las identidades de la UPeU. Antes de molestarlos, **investigamos directamente en la base** las dudas que teníamos sobre qué tabla/columna usar. La mayoría se resolvió sola consultando catálogos y relaciones reales (38 dudas → **28 resueltas en la propia BD**, ver Anexo A).

Este documento contiene **solo lo que la base NO puede responder**: decisiones de fuente autoritativa, reglas de negocio no codificadas en datos, y licitud de uso. Son **7 preguntas**. Además, la investigación detectó **4 supuestos nuestros equivocados** que vamos a corregir (Anexo B) — los listamos por transparencia.

---

## Preguntas para validar (lo que la base no responde)

| # | Tema | Lo que ya investigamos (contexto) | Pregunta concreta | Respuesta DBA |
|---|---|---|---|---|
| P1 | Licitud de RENIEC como fuente de nombres | `DAVID.CONSULTA_APIS_LOG` es un log de la API RENIEC con 151.245 respuestas exitosas (`STATUS='S'`, `TIPO='DNI'`). La tabla "limpia" `MOISES.LOG_CONSULTA_RENIEC` solo tiene 51 filas → sin cobertura. Técnicamente el log es la única fuente con volumen. | ¿Es **lícito y autorizado** usar el log de la API RENIEC como fuente de nombres jurídicamente validados para las identidades? ¿O hay restricción de protección de datos que lo impida? | |
| P2 | Fuente autoritativa del nombre legal | El nombre de una misma persona vive en `MOISES.PERSONA`, `ELISEO.VW_APS_EMPLEADO`, `ENOC.VW_TRABAJADOR` y el caché RENIEC, y a veces difieren. | ¿Cuál declaran ustedes como **fuente oficial** del nombre legal de una persona, y qué orden de prioridad seguir cuando difieren entre tablas? | |
| P3 | Régimen docente (TC/TP/DE) completo | `MOISES.PERSONA_ACAD_REGIMEN` solo cubre **245 docentes de ~8.655** (y 286 filas con régimen en blanco). Vimos `ENOC.PLLA_REGIMEN_DEDICACION` como candidata, y `CAT_DOCENTE.ID_TIPO_TIEMPO_TRABAJO` (1=TC,2=MT,3=TP,4=DE) que sí está poblado. | ¿Cuál es la **fuente completa y correcta** del régimen docente? ¿`PLLA_REGIMEN_DEDICACION`, o se deriva de `TIPO_TIEMPO_TRABAJO`? ¿Por qué `PERSONA_ACAD_REGIMEN` está casi vacía? | |
| P4 | Área "principal" de un puesto / trabajador | Confirmamos que `ENOC.PLLA_PERFIL_PUESTO` (ID_AREA + ID_PUESTO + ID_ENTIDAD + VIGENCIA) **es** la relación área↔puesto que faltaba — pero es **N:N** (un mismo puesto aparece en hasta 58 áreas; 739 puestos para entidad 7124). | Dado que un puesto puede pertenecer a muchas áreas, ¿cuál es la **regla de negocio** para determinar el área orgánica **principal** de un puesto (y por tanto del trabajador que lo ocupa)? | |
| P5 | Autoridades / designaciones formales | Encontramos `ELISEO.ORG_AREA_RESPONSABLE` (liga área↔persona con FECHA/ACTIVO/ID_ANHO; 10.132 activos, 2.040 personas), que parece cubrir "responsable de área". No hallamos una tabla explícita de designaciones con resolución. | ¿Es `ORG_AREA_RESPONSABLE` la **fuente oficial** del responsable/autoridad de un área, y su vigencia (ACTIVO + ID_ANHO) es confiable por periodo? ¿Existe una tabla de **designaciones/resoluciones** de autoridades académicas (rector, decanos, directores de confianza) con vigencia formal que debamos consumir? | |
| P6 | Periodo académico vigente | Confirmamos que los IDs 267/279/283 = "Regular 2026-1"/"Verano 2026-0"/"Regular 2026-2" (`DAVID.ACAD_SEMESTRE`). Pero **no existe un flag de "semestre vigente"**: `ESTADO='1'` solo significa "no borrado" (hay 149 semestres con ESTADO=1, incluidos futuros). | ¿Hay una **regla o columna oficial** para identificar "el periodo en curso", o el equipo LAMB confirma que la práctica aceptada es codificar los IDs de semestre cada periodo (hoy lo hacemos a mano en el conector)? | |
| P7 | Tipo de documento en planilla | El catálogo oficial es `MOISES.TIPO_DOCUMENTO` (1=DNI, 4=CE, 7=Pasaporte…). Pero `ELISEO.VW_APS_EMPLEADO.ID_TIPODOCUMENTO` trae como dominantes **98 (CUSPP) y 97 (SNP)** — que son códigos de **pensiones**, no de identidad. | ¿Confirman que `97/98` en `VW_APS_EMPLEADO.ID_TIPODOCUMENTO` son códigos de pensiones (CUSPP/SNP) y NO documentos de identidad, de modo que debemos **ignorarlos** al tomar el documento de identidad del trabajador? | |

---

## Decisiones DTI (Alberto, 2026-06-25) y qué queda

| # | Decisión / criterio | Estado | Acción derivada |
|---|---|---|---|
| P1 | **Autorizado** usar el flujo del log RENIEC (`DAVID.CONSULTA_APIS_LOG`) como fuente de nombres. | ✅ RESUELTO | Ninguna (ya en uso). |
| P2 | El nombre legal **siempre** se toma con prioridad del **caché RENIEC**; las demás tablas son secundarias. | ✅ RESUELTO | MidPoint: el inbound de nombres desde RENIEC debe ganar (mayor precedencia) sobre PERSONA / VW_APS_EMPLEADO / VW_TRABAJADOR. |
| P3 | La autoridad del régimen docente (y de RRHH) es **LAMB Talent** (módulo RRHH). Se **correlaciona en MidPoint**. | ⏳ PENDIENTE IDENTIFICAR | Ubicar la tabla/schema de **LAMB Talent** en Oracle (¿qué schema/objeto?). Luego correlacionar régimen en MidPoint desde esa fuente, no desde `PERSONA_ACAD_REGIMEN`. |
| P4 | "Creo que ya lo sabemos, confirmar con DBAs." Hipótesis DTI: el área operativa del trabajador = **área del contrato** (`ID_DEPTO`→`ID_AREA`, ya usada en `costCenter`); el catálogo N:N `PLLA_PERFIL_PUESTO` solo dice qué puestos *pueden* existir en qué áreas, no la asignación. | 🔶 CONFIRMAR | Mantener pregunta de confirmación a DBAs. |
| P5 | "Se puede deducir." Deducción DTI: autoridad/responsable de área = fila **activa** en `ELISEO.ORG_AREA_RESPONSABLE` (ACTIVO + ID_ANHO vigente). No requiere tabla de resoluciones. | ✅ DEDUCIBLE | MidPoint: derivar autoridad desde `ORG_AREA_RESPONSABLE` cuando se modele. |
| P6 | "Creo que ya lo sabemos, confirmar." La investigación confirmó que **NO existe** flag de "semestre vigente"; la práctica aceptada es **codificar los IDs de semestre por periodo** en el conector. | 🔶 CONFIRMAR | Mantener práctica actual; confirmar con DBAs que no hay columna oficial. |
| P7 | Aplicar las **normas IGA** (identityDocument = solo documentos de identidad reales, eduPerson/ISO 24760). | ✅ RESUELTO | MidPoint: el mapeo de tipo-doc del trabajador **excluye 97/98** (SNP/CUSPP pensiones). Coincide con corrección B4. |

**Quedan para los DBAs solo 2 confirmaciones (P4, P6) + 1 dato a ubicar (P3: dónde vive "LAMB Talent").** Las demás están resueltas por decisión del responsable.

---

## Anexo A — Lo que la base YA respondió (28 dudas resueltas, no requieren su tiempo)

Catálogos de códigos confirmados (existe tabla de referencia para cada uno):

| Dominio | Tabla catálogo | Valores confirmados (resumen) |
|---|---|---|
| Sexo (ISO 5218) | `MOISES.TIPO_SEXO` | 1=Varón, 2=Mujer (faltante = NULL, 39.471) |
| Tipo de documento | `MOISES.TIPO_DOCUMENTO` (27 filas) | 1=DNI, 4=CE, 6=RUC, 7=Pasaporte, 24=Doc.Id.Extranjero, 31=Cédula, 22=Carné RR.EE, 23=PTP |
| Tipo de alumno | (sin catálogo; dominio real) | RE=regular (289k); B18/BP/INT marginales |
| Categoría ocupacional | `ELISEO.APS_CATEGORIA_OCUPACIONAL` | 1=Ejecutivo, 2=Obrero, 3=Empleado |
| Estado civil | `MOISES.TIPO_ESTADO_CIVIL` | 1=Casado, 2=Soltero, 3=Divorciado, 4=Separado, 5=Conviviente, 6=Viudo, 9=No precisa |
| Tiempo de trabajo docente | `MOISES.TIPO_TIEMPO_TRABAJO` | 1=TC, 2=Medio Tiempo, 3=Tiempo Parcial, 4=Dedicación Exclusiva |
| Estado docente | `ENOC.CAT_ESTADO_DOCENTE` | 02=Aprobado (el que usamos); 00=Anulado…05=No se presentó |
| Condición laboral docente | `MOISES.CONDICION_LABORAL` | E=Empleado, M=Misionero, C=Contratado |
| Categoría docente | `DAVID.CATEGORIA_DOCENTE` | 3=Auxiliar, 4=Asociado, 5=Principal (vigentes); mapea a CODSUNEDU |
| Motivo de cese | `ENOC.PLLA_MOTIVO_CESE` (19 filas) | 05=Jubilación, 09=Fallecimiento, 01/02=Renuncia, 03=Despido, 07=Término, 08=Mutuo disenso, 18=Límite edad 70 |
| Tipo de área | `ELISEO.TIPO_AREA` (17 tipos) | Rectorado/Vicerrectorado/Dirección/Coordinación/Jefatura/Oficina… (facultad/escuela NO se distinguen por este campo) |

Estructuras y relaciones confirmadas:

- **Entidades:** `ELISEO.CONTA_ENTIDAD` → **7124 = UPeU** (RUC vía empresa 201). Sub-entidades comparten empresa 201: 17120=UPeU-FJ, 17122=UPeU-FT, 17125=POSGRADO, 7128=Colegio Unión (PUNION). Clínica Good Hope=7323, Ana Stahl=7723.
- **Sedes:** `ELISEO.ORG_SEDE` (6) → 1=Lima, 2=Juliaca, 3=Tarapoto, 4=ISTAT, 5=Clínica Good Hope, 6=AGTU.
- **Organigrama:** `ELISEO.VW_AREA` es la única vista; `ID_PARENT` resuelve 100% (0 huérfanos), con nested-set (NIVEL/IZQUIERDA/DERECHA). Facultad = `ID_PARENT` de la escuela. ✓
- **Trabajador↔puesto vigente:** `ENOC.VW_TRABAJADOR.ID_PUESTO` está 100% poblado (11.949/11.949) → es la fuente viva. `MOISES.TRABAJADOR_PUESTO` solo tiene 5 filas con VIGENCIA=1 → **no usar**.
- **Área↔puesto:** existe en `ENOC.PLLA_PERFIL_PUESTO` (resuelve el hueco; regla de "principal" pendiente → P4).
- **Egresados:** `DAVID.VW_PERSONA_EGRESADO` trae ANIO/SEMESTRE/SEDE/FACULTAD/ESCUELA/NIVEL/MODALIDAD + `ID_PERSONA` (JOIN a foto). ✓
- **Grados/títulos:** `DAVID.VW_PERSONA_GRADO` → CONDICION T=Titulado (3.836), G=Grado (3.218); NOMBRE: Bachiller/Maestría/Doctor/Posdoctorado. ✓
- **ID_PERSONA** es la FK universal de persona entre MOISES/DAVID/ELISEO/ENOC. ✓
- **Ciclo del alumno:** confirmado que NO existe "ciclo único del alumno"; `ACAD_PLAN_CURSO.CICLO` es ciclo del curso (limitación estructural conocida).

## Anexo B — Supuestos nuestros que la base desmiente (a corregir en los resources)

> Hallazgos de la investigación que indican posible error en el mapeo actual. **Acción interna DTI**, no requieren respuesta de los DBAs.

1. **`ID_EMPRESA=201` NO es "Lima"** — es la persona jurídica UPeU (RUC 20138122256). Lima es `ID_SEDE=1`. El dedup de trabajadores "por empresa 201=Lima" (`trabajadores.xml`) en realidad selecciona *contratos UPeU*, no Lima → **revisar la lógica de desempate**.
2. **`ID_TIPO_TIEMPO_TRABAJO=3` es "Tiempo Parcial", no "hourly"**, y existe `4=Dedicación Exclusiva` → revisar el mapeo de jornada docente (`employeeType`) en `trabajadores.xml`.
3. **`ID_MOTIVO_CESE=18` es "Límite de edad 70 años"**, distinto de jubilación (05) → ajustar el catálogo de `motivoCese`.
4. **`VW_APS_EMPLEADO.ID_TIPODOCUMENTO` mete 97/98 (SNP/CUSPP de pensiones)** mezclados con identidad → el mapeo de documento del trabajador debe excluirlos (relacionado con P7).

---

*La columna "Respuesta DBA" se deja vacía para que Barrantes y Carlomagno la completen. Gracias.*
