# Curación tesauro VocBench — cierre de códigos INEI (2026-07-16)

**Para:** curador del tesauro `Tesauro_Institucional_UPeU` (VocBench) · **Origen:** reconciliación LT-Pcode-INEI ↔ tesauro ↔ Oracle LAMB, workstream Bsort2→INEI.
**Estado:** insumo de curación. Nada aplicado — solo lectura SPARQL/Oracle.

> **Contexto en una línea:** el reporte "usuarios que usaron la biblioteca por programa (INEI 8 díg)" del Koha nuevo consolidado agrupa por `borrowers.sort2` = INEI. Para que salga completo y correcto, el catálogo de programas del tesauro (que curó la `LT-Pcode-INEI` que alimenta Koha) debe cerrar estos cuatro frentes. Ver contrato: [`docs/specs/koha-consolidado-contrato-configuracion.md`](../../../docs/specs/koha-consolidado-contrato-configuracion.md).

## Hallazgo base
- **Oracle LAMB NO es fuente de INEI.** `DAVID.ACAD_PROGRAMA_ESTUDIO.CODIGO_NACIONAL` está NULL para **todos** los programas. La única autoridad de INEI hoy es **VocBench + la LT** (derivada de VocBench). Cualquier INEI nuevo/conflictivo requiere el **clasificador INEI 2022 oficial** (fuente externa), no Oracle.
- Cobertura tesauro: **96 programas canónicos, 48 con `IneiCode8`, 48 sin** (pregrado 19/33; posgrado 29/63, mayormente esperado).

---

## A. Merges — 8 duplicados de slug (limpieza, SIN dato nuevo)

Cada huérfano es un duplicado por renombre de carrera; su gemelo canónico YA tiene el INEI. Acción: `skos:exactMatch` bidireccional huérfano↔gemelo (o `dct:isReplacedBy` + `skos:editorialNote` de deprecación en el huérfano, convención "nunca borrar" ya usada en los `c_<uuid>`). Todos bajo `http://upeu.edu.pe/sys/programas/programa/`.

| Concepto huérfano (deprecar) | Gemelo canónico (vigente) | INEI8 gemelo |
|---|---|---|
| `administracion-con-mencion-en-gestion-empresarial` | `administracion` | 41300270 |
| `contabilidad-gestion-tributaria` | `contabilidad-gestion-tributaria-y-aduanera` | 41101896 |
| `educacion-educacion-fisica` | `educacion-especialidad-educacion-fisica-recreacion-y-deportes` | 12200708 |
| `educacion-ingles-espanol` | `educacion-especialidad-ingles-y-espanol` | 12104952 |
| `educacion-inicial` | `educacion-inicial-y-puericultura` | 11102086 |
| `educacion-musica-artes` | `educacion-especialidad-musica-y-artes-visuales` | 12302089 |
| `educacion-primaria` | `educacion-primaria-y-pedagogia-terapeutica` | 11200247 |
| `psicologia-fche` | `psicologia` | 31300211 |

## B. Backfill LT → tesauro (la LT tiene el INEI; el tesauro lo perdió)

| Programa | INEI a cargar | Acción |
|---|---|---|
| `medicina-humana` | **91200267** | Backfill directo: agregar `skos:notation "91200267"^^IneiCode8`. Carrera activa con matrícula real; hoy **sí proyecta a Koha** vía la LT, pero el tesauro no la tiene → cargar para consistencia con DSpace/Indico. |

## Fuente oficial (obtenida y parseada 2026-07-16)

**INEI — "Clasificador Nacional de Programas e Instituciones de Educación Superior y Técnico Productiva 2022"**, Res. Jefatural N° 067-2024-INEI. Archivo de programas (hoja `profesional _universidad` / `doctorado_universidad`):
`https://cdn.www.gob.pe/uploads/document/file/6264275/5355494-listado-de-programas-de-educacion-superior-31-12-2022(2).xlsx`

**Estructura del código (confirmada):** 9 dígitos = `CCC`(campo detallado) + `PPPPP`(programa) + `N`(nivel: 6=profesional, 7=maestría, 8=doctorado, 9=2ª esp.). **El "código de 8 dígitos" de UPeU = CCC+PPPPP** (columna "Código de campo_programa"), sin el dígito de nivel. Verificado contra los 7 códigos conocidos.

## C. Conflictos de valor LT ↔ tesauro — RESUELTOS contra el clasificador oficial

| P-code | Programa (denominación UPeU) | INEI LT | INEI tesauro | Veredicto clasificador | Acción |
|---|---|---|---|---|---|
| P05 | Administración **de** Negocios Internacionales | `41600562` ✅ | `41300011` | `41600562`="Administración de Negocios Internacionales" (exacto); `41300011`="Administración **y** Negocios Int." (otra denominación) | **LT correcta → corregir TESAURO** a 41600562 |
| P99 | Doctorado en Ingeniería de Sistemas | `61200058` ✅ | `61203409` | `61200058`="Doctorado en Ingeniería de Sistemas" (exacto); `61203409`="Ingeniería de Sistemas" (denom. corta) | **LT correcta → corregir TESAURO** a 61200058 |
| **P35** | **Teología** (⚠️ programa de CIA) | `22103063` ❌ | `22101180` ✅ | **RESUELTO por Oracle:** el programa vigente de UPeU es **"Teología"** (P35, matrícula activa continua; la variante "con Mención en Liderazgo Eclesiástico" está discontinuada desde 2021 y sin CODIGO_SUNEDU). → `22101180` correcto. | **TESAURO correcto → corregir LA LT** (hecho en repo: `22103063→22101180`). Falta aplicar a PROD (§G). |

En P05 y P99 la LT tenía razón; en **P35 la LT estaba mal** y el tesauro bien — ninguna capa es infalible, por eso se verificó cada caso contra el clasificador oficial + Oracle. **Al fijar cada valor, ponerlo en AMBAS capas** (tesauro `IneiCode8` + row LT) para no re-divergir.

## D. Huecos reales — 1 resuelto, 2 requieren denominación exacta UPeU

| Programa | Denominación Oracle vigente | INEI clasificador | Estado |
|---|---|---|---|
| `ingenieria-informatica-y-estadistica` | — | **`61202313`** = "Ingeniería Informática y Estadística" (exacto) | ✅ **RESUELTO** — cargar al tesauro |
| `educacion-ciencias-naturales` | "Educación, Especialidad Ciencias Naturales y Tecnología" (ID 1157) | — | ⏸ **PILOTO sin licenciar** — sin CODIGO_SUNEDU, matrícula mínima (2 en 2025-1, **0 en semestres actuales**). No forzar código hasta licenciamiento SUNEDU (Calidad/DTI). |
| `educacion-matematica` | "Educación, Especialidad Matemática, Análisis de Datos y Computación" (ID 1158) | — | ⏸ **PILOTO sin licenciar** — ídem (2 en 2025-1, 0 actuales). |

> Los huecos SIN P-code no proyectan a Koha aunque se cargue el INEI al tesauro (la vía actual es P-code→LT→INEI). Requieren además una vía de materialización alterna (por `academicProgramCode` EP-XXX o por nombre) — decisión de diseño MidPoint aparte. Dado que los 2 pilotos tienen **0 matriculados en los semestres actuales**, su impacto en el reporte de biblioteca es **nulo hoy** → baja prioridad hasta que se licencien y tengan matrícula.

## F. Estado final — todo dirimido salvo 2 pilotos sin licenciar

| Caso | Resolución | Fuente |
|---|---|---|
| P35 Teología | **22101180** (corregir LT ✅ hecho) | Oracle: "Teología" vigente + clasificador |
| P05 Adm. Neg. Int. | **41600562** (corregir tesauro) | clasificador (match exacto) |
| P99 Doct. Ing. Sistemas | **61200058** (corregir tesauro) | clasificador (match exacto) |
| Ing. Informática y Estadística | **61202313** (cargar tesauro; sin P-code → no proyecta a Koha aún) | clasificador (match exacto) |
| Medicina Humana | **91200267** (backfill tesauro; ya proyecta vía LT) | LT + Oracle confirma P30 |
| 8 duplicados de slug | mergear (§A) | tesauro |
| Educ. Ciencias Naturales / Matemática | ⏸ pilotos sin licenciar, 0 matrícula actual | Oracle |

## G. Aplicar a PROD (pendiente de confirmación)
La corrección P35 en la LT ya está en el repo. Falta: `git pull` en PROD + PATCH REST de la fila P35 de `LT-Pcode-INEI` + recompute de los ~5 estudiantes de Teología activos para que su `Bsort2` pase a `22101180`. Bajo riesgo (5 usuarios, dato corregido, reversible). El Koha viejo está en maintenance (caído) → sin urgencia; conviene hacerlo junto con el re-apuntado al Koha nuevo.

## E. Flags menores (verificar con Calidad, no bloqueantes)
- `P152` Ingeniería Industrial (INEI `72200109`): programa nuevo (2026-07), solo existe como legacy `c_iii00716` sin tipar; su `editorialNote` dice sin licencia SUNEDU vigente. No tipar hasta confirmar.
- `P143` Derecho (`42100042`): correcto y tipado, pero vive en `scheme/programas-en-implementacion`, no en `programas-academicos` (por eso no cuenta en los 96). Sin acción.

---

## Resumen de acciones
1. **8 merges** (A) — limpieza inmediata, sin dato externo.
2. **1 backfill** (B) — Medicina 91200267, dato ya disponible en la LT.
3. **3 conflictos** (C) — necesitan clasificador INEI 2022 para dirimir; **P35 Teología es prioritario** (afecta el reporte de CIA).
4. **3 huecos reales** (D) — necesitan clasificador INEI 2022 + vía de materialización (sin P-code).

**Dependencia común de C y D:** conseguir el **clasificador INEI 2022 oficial** de carreras de educación superior. Es el insumo que cierra tanto los conflictos como los huecos.
