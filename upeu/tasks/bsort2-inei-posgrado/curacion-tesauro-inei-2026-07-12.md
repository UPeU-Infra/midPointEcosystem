# Curación tesauro VocBench — cierre de códigos INEI (2026-07-12)

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

## C. Conflictos de valor LT ↔ tesauro (mismo programa, INEI distinto — DECISIÓN HUMANA)

Requieren el clasificador INEI 2022 oficial para dirimir cuál es el correcto. **Hasta resolverlos, la LT (lo que proyecta a Koha) puede estar emitiendo el INEI equivocado.**

| P-code | Programa | INEI en la LT (→ Koha hoy) | INEI en el tesauro | Nota |
|---|---|---|---|---|
| **P35** | **Teología** | `22103063` | `22101180` (tipado) | ⚠️ **Prioritario: Teología es el programa de CIA.** El reporte de CIA por programa depende de este código. |
| P05 | Administración de Negocios Internacionales | `41600562` | `41300011` (tipado, RIMS 2026-06-28) | Dos INEI distintos para el mismo programa. |
| P99 | Doctorado en Ingeniería de Sistemas | `61200058` | `61203409` (sin tipar, `xsd:string`) | La LT (nota "RONDA 3") dice que `61203409→61200058` fue corrección validada; el tesauro quedó con el valor viejo. |

**Al resolver cada conflicto:** fijar el INEI correcto en AMBAS capas (tesauro `IneiCode8` + row de la LT) para no re-divergir.

## D. Huecos reales — sin INEI en NINGUNA capa (requieren clasificador INEI 2022 externo)

Oracle no los tiene (CODIGO_NACIONAL NULL), no están en el crosswalk RIMS, no tienen P-code. Sin INEI, estos alumnos salen "(sin programa)" en el reporte de biblioteca.

| Programa (y variante slug) | ¿P-code? | Fuente para el INEI |
|---|---|---|
| `educacion-ciencias-naturales` / `…-especialidad-ciencias-naturales-y-tecnologia` | No | Clasificador INEI 2022 oficial |
| `educacion-matematica` / `…-especialidad-matematica-analisis-datos-y-computacion` | No | Clasificador INEI 2022 oficial |
| `ingenieria-informatica-y-estadistica` | No | Clasificador INEI 2022 oficial |

> Como no tienen P-code en Oracle, aunque se cargue el INEI en el tesauro **no bastará** para que proyecten a Koha por la vía actual (P-code → LT → INEI). Requieren además una vía de materialización alterna (mapear por `academicProgramCode` EP-XXX o por nombre) — decisión de diseño MidPoint aparte, fuera de la curación del tesauro.

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
