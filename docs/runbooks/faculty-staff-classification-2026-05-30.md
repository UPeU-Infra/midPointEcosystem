# Runbook — Clasificación canónica faculty vs staff (UPeU)

Fecha: 2026-05-30 · Autor: midpoint-expert (Claude Opus 4.8) · Recurso: `Oracle LAMB Trabajadores v3` (OID `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21`)

## 1. Problema

La regla previa clasificaba `faculty` cuando el `NUM_DOCUMENTO` aparecía en `DAVID.VW_PERSONA_DOCENTE`:

```sql
CASE WHEN pd.NUM_DOCUMENTO IS NOT NULL THEN 'archetype-user-employee-faculty' ELSE 'archetype-user-employee-staff' END
```

`VW_PERSONA_DOCENTE` es un **padrón histórico contaminado** (7.080 documentos, sin filtro de vigencia ni de tipo de personal). Fallaba en dos direcciones:

- **Falsos faculty:** personal puramente administrativo aparece en el padrón. Confirmado: Zonia Acosta (DNI 01119359, puesto "Auxiliar de circulación", CRAI) y 177 más (Analistas, Secretarias, Community Manager, etc.).
- **Docentes perdidos:** docentes reales que NO están en el padrón quedaban como `staff`. Confirmado: 1.400 personas, incluidos los docentes de colegio (Docente/Profesor de Inicial/Primaria/Secundaria) y muchos Docente Contratado.

Matriz de confusión (regla vieja vs nueva, población ESTADO='A', por persona):

| viejo → nuevo | personas |
|---|---|
| faculty → faculty | 523 |
| faculty → staff (falsos corregidos) | 77 |
| staff → faculty (docentes recuperados) | 1400 |
| staff → staff | 1949 |

## 2. Fuente de verdad canónica (nueva regla)

`faculty` = (A) **carga docente vigente** ∪ (B) **puesto docente en contrato activo 7124**:

- **(A)** `ENOC.VW_CARGA_DOCENTE` con `ID_SEMESTRE IN (267,279,283)` (semestres 2026-1, 2026-0, 2026-2). Captura a quien tiene carga lectiva este ciclo, incluidas autoridades académicas que enseñan (Decano, Director de EP) y personal no-docente que dicta un curso.
- **(B)** `ENOC.PLLA_PUESTO.NOMBRE` del contrato vivo (`ID_ENTIDAD=7124`, ya filtrado por el resource):
  - `Docente*` / `Profesor*` excluyendo `%AUXILIAR%`
  - `Jefe de Práctica(s)` (`LIKE 'JEFE DE PR_CTICA%'`)
  - `Tutor de Internado*`, `Supervisor de Internado*`, `Supervisor de Práctica` (exacto), `Asesor de Tesis` (exacto)

IIA por atributo (ISO 24760 §1.3): la **afiliación docente viva** la gobierna el dominio académico (carga, `ENOC`), no un padrón estático. La clasificación alimenta `UPEU_ARCHETYPE_NAME` → inbound `archetype-to-liveAffiliationWorker` (strong, single-source) → `sb:liveAffiliationWorker` → template (J3b→affiliations, J3→primaryAffiliation, D7→archetype estructural).

## 3. Decisiones de borde (fundamento normativo)

### Borde 1 — Auxiliar Docente / Auxiliar de Educación de colegio → **staff**
**Ley de Reforma Magisterial 29944** distingue el **PROFESOR** (docente responsable de la enseñanza) del **AUXILIAR DE EDUCACIÓN** (apoya al docente, no es el instructor responsable). Son categorías legalmente distintas. eduPerson 202208 §3.2 define `faculty` como "academic/teaching staff with a contractual relationship for instruction"; el auxiliar de educación no cumple ese rol responsable. → `staff`. Implementado con `NOT LIKE '%AUXILIAR%'` sobre los puestos Docente/Profesor (excluye "Auxiliar Docente", "Auxiliar Docente de Inicial/Secundaria", "Auxiliar docente primaria").

### Borde 2 — Docencia clínica / internado / supervisión de prácticas → **faculty**
**Ley Universitaria 30220 Art. 79** incluye la enseñanza y la supervisión académica entre las funciones docentes; **Art. 81** declara a los jefes de práctica y ayudantes de cátedra como "etapa inicial de la carrera docente" (son docentes). La supervisión de internado y de prácticas pre-profesionales es actividad docente directa. → `faculty` para: `Jefe de Prácticas`, `Jefe de Práctica Medicina`, `Tutor de Internado Médico`, `Supervisor de Internado`, `Supervisor de Práctica`, `Docente Supervisor/Tutor de Práctica`, `Asesor de Tesis`.
**Excluidos** (acto puntual de evaluación, no relación docente sostenida; reciben faculty solo si tienen carga): `Dictaminador de tesis`, `Metodólogo de Curso de Tesis`. **Practicante / Practicante Pre Profesional → staff** (son aprendices, no instructores; eduPerson `faculty` exige rol instructor).

### Borde 3 — Ex-docente hoy administrativo, sin carga ni puesto docente vigente → **staff**
Reality-vs-Policy (MidPoint best-practices §2.1): la afiliación primaria refleja el **rol presente** (reality), no la historia. Quien fue docente pero hoy no tiene carga vigente (A) ni puesto docente activo (B) es `staff`. Si en el futuro vuelve a tener carga, (A) lo reclasifica a `faculty` automáticamente. La historia docente no confiere afiliación estructural viva.

## 4. Multi-afiliación
El archetype estructural refleja la afiliación primaria (D7, prioridad faculty>staff>student>alum). Las demás afiliaciones van como `eduPersonAffiliation` multivalor. Casos validados: un "Auxiliar de Limpieza" con 1 carga docente vigente → faculty (correcto, multi-rol); autoridad académica con carga → faculty; faculty + alum coexisten vía affiliations.

## 5. Validación (Oracle SOLO SELECT)
Universo ESTADO='A': **faculty 1899 COD_APS / staff 2016** (resource baseQuery ejecutada tal cual). Por persona ~1923/2026.

Tabla de ejemplos (todos verificados contra la baseQuery del resource):

| Tipo | DNI | Puesto | Carga | Resultado |
|---|---|---|---|---|
| Auxiliar circulación (Zonia) | 01119359 | Auxiliar de circulación | no | staff ✓ |
| Docente titular | 00238680 | Docente Ordinario Principal | sí | faculty ✓ |
| Jefe de prácticas | 09765199 | Jefe de Prácticas | sí | faculty ✓ |
| Profesor colegio | 004076884 | Docente de Secundaria | no | faculty ✓ (recuperado) |
| Auxiliar educación colegio | 001841250 | Auxiliar Docente | no | staff ✓ |
| Supervisor internado | 02447628 | Supervisor de Internado | no | faculty ✓ |
| Tutor internado médico | 002476207 | Tutor de Internado Médico | no | faculty ✓ |
| Practicante | 001502765 | Practicante | no | staff ✓ |
| Secretaria | 46206125 | Secretaria | no | staff ✓ |
| Decano que enseña | 02424096 | Decano de Facultad | sí | faculty ✓ (borde 3) |
| Falso faculty corregido | 72738765 | Community Manager (en padrón) | no | staff ✓ |
| Staff con carga | 75238645 | Auxiliar de Limpieza + 1 carga | sí | faculty ✓ (multi-rol) |

## 6. Implementación
`upeu/resources/oracle-lamb/trabajadores.xml` searchScript:
- CASE de `UPEU_ARCHETYPE_NAME` reescrito (carga viva ∪ puesto docente).
- LEFT JOIN `DAVID.VW_PERSONA_DOCENTE pd` reemplazado por LEFT JOIN `(SELECT DISTINCT ID_PERSONA FROM ENOC.VW_CARGA_DOCENTE WHERE ID_SEMESTRE IN (267,279,283)) cvf`.
- El inbound `archetype-to-liveAffiliationWorker` (línea ~545) NO cambia: sigue mapeando `archetype-user-employee-faculty → faculty`, else `staff`.

Despliegue: commit `a283fa3` → push → `git pull` en PROD `/home/juansanchez/midPointEcosystem` → PUT raw (HTTP 201) → **Test Connection 15/15 success**. Backup previo del recurso en PROD `/tmp/trab_backup_20260530_180726.xml`.

## 7. Canary (BLOQUEANTE) — resultado: VERDE
Live-fetch de shadows trabajadores a través de MidPoint+Oracle (la inbound corre sobre datos frescos):
- Shadow `45961967` (Docente de Secundaria, colegio): `UPEU_ARCHETYPE_NAME=archetype-user-employee-faculty` ✓ (recuperado).
- Shadow `72738765` (Community Manager, antes falso-faculty del padrón): `UPEU_ARCHETYPE_NAME=archetype-user-employee-staff` ✓ (corregido).
Ningún caso conocido salió mal → canary aprobado.

## 8. Recompute — DIFERIDO (decisión operativa)
El cambio de archetype estructural es **seguro** respecto a dual-structural: el Bloque D7 es range-authoritative (fix PM16, OIDs `c93083ca`/`6460facf`/`3037fbd2`/`87552943` en `<set>`), REEMPLAZA el structural en vez de acumular.

NO se lanzó recompute masivo de los ~1477 changers en esta sesión porque:
1. PROD está en migración delicada (COLA DE RETOMA PM16 con dual-structural y merge en curso, disco 86%).
2. Los endpoints REST `/recompute` y `/reconcile` por objeto devuelven 404 en este 4.10 (deben ir por Task — ver MEMORY "MidPoint Tasks via REST").

La nueva clasificación se materializa al re-fetchear shadows: en el **sync nocturno** del resource o en las **olas de recompute** ya planificadas en la COLA DE RETOMA. Recomendación: incluir la reconciliación del resource Trabajadores en la próxima ola, verificando post-recompute: `dual-structural=0`, salvaguarda académica intacta, faculty legítimos no rotos.

## 9. Reporte RR.HH.
`docs/reportes-rrhh/padron-docente-contaminado-2026-05-30.csv` (178 trabajadores activos marcados en `DAVID.VW_PERSONA_DOCENTE` sin carga ni puesto docente vigente — contiene DNIs, NO se versiona en git por PII). Inconsistencia a corregir en origen por RR.HH./registros académicos, aunque el fix del IGA ya nos protege.
