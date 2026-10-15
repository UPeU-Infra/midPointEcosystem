# Campus y escuela del estudiante por su matrícula de PREGRADO vigente (2026-10-14)

Resource `Oracle LAMB Estudiantes v3` (`6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22`). **Solo PATCH**
(ver `../NUNCA-PUT-resources-schema-cache.md`).

## Causa medida

`SEDE_NOMBRE`/`SCHOOL_NAME` salían de `MAX(...) KEEP (DENSE_RANK LAST ORDER BY FECHA_FIN)` sobre
**todas** las matrículas del horizonte. Un contrato de Idiomas (p. ej. «Ingles Online», Sede Lima,
sem 285, fin 2026-11-30) termina después que el de Pregrado (fin 2026-11-27) y gana. En los 4.677 de
pregrado 2026-2: 564 con `campusStudent=LIMA` siendo de Juliaca/Tarapoto (562 Inglés 285 + 2 Quechua
283) y 768 sin escuela por esa misma causa.

## Regla

Matrícula que gobierna campus/escuela/facultad/nivel/tipo: **Pregrado** (`TIPO_NIVEL_ENSENANZA =
'Pregrado'` o con P-code) antes que cualquier otro nivel; dentro del nivel, la **en curso**
(`MIN(FECHA_INICIO) <= hoy <= MAX(FECHA_FIN)` de sus módulos); desempate `FECHA_FIN`. Sin default de
sede: valor desconocido → vacío (antes `getOrDefault(v,'LIMA')`).

## Despliegue escalonado

| Paso | Archivo | Estado |
|---|---|---|
| 1 | `patch1-schemaScript.xml` → test connection (regenera el `<schema>` con `PRIMARY_*`) | aplicado |
| 2 | `patch2-search-and-inbounds.xml`: `searchScript` con columnas `PRIMARY_*` (las viejas no cambian), 5 atributos nuevos con inbounds gateados, condición inversa en los 7 inbounds viejos | aplicado |
| 2b | `patch2b-studyLevel.xml`: el inbound nuevo de nivel copiaba el del repo (minúsculas, `normal`); PROD usa `strong` + normalización «Pregrado». Cazado en la simulación del testigo (`Pregrado`→`pregrado`) | aplicado |
| 3 | Corte: `patch3-corte.xml` | **aplicado el 15-oct-2026 ~00:35 Lima por Alberto** (PATCH manual, HTTP 204) → resource **v205** |

El GATE (condición Groovy) activa la lógica nueva solo en **simulaciones** (`TaskExecutionMode`
no persistente) y para la lista de **canarios**; en producción, para el resto, sigue la vieja. Ante
error, comportamiento de producción.

## Resultado medido (2026-10-14)

**Simulación** (`import` preview de todo el feed, 30.066 usuarios, 45 min, 28 fallos = mismas clases
crónicas que la recon real de esa mañana, 36). Cambios atribuibles (columna vieja ≠ `PRIMARY_*`):

| Ítem | Cambios |
|---|---|
| `campusStudent` | 1.451 (LIMA→JULIACA 1.062, LIMA→TARAPOTO 387, otros 2) + 31 `Sede ISTAT` pierden el LIMA inventado |
| Koha `library_id` | 1.451 (BUL→BUJ 1.064 —incluye 2 ISTAT trabajadores de Juliaca—, BUL→BUT 385, 2 otros) |
| LDAP `scibackCampusCode` | 1.443 |
| Assignment a `EP-*` (D6) | +1.762 (0 cambios de EP a EP, 0 pérdidas) · LDAP `eduPersonOrgUnitDN` +1.760 |
| `facultyName` / Koha `statistics_1` / LDAP `scibackFacultyCode` | 84 / 82 / 82 |
| `studyLevel` / `studentEnrollmentType` | 39 / 24 |
| `academicProgramCode` | +2.128 valores nuevos; 16.131 «borrar y re-añadir el MISMO valor» (solo cambia la procedencia del mapping; sin efecto en proyecciones) |

No atribuibles (aparecen en cualquier recon): Koha `extended_attributes` (8.809, la recon real lo
reescribe a diario), `rejectedAt` (7.302, ídem), 212 correos recién cargados en Oracle, matrículas
nuevas del día.

Sobre los 4.677 de pregrado 2026-2: **564/564** corregidos (Koha 410 BUL→BUJ + 153 BUL→BUT); los
4.676 con usuario quedan con campus = sede del programa; **755 de 967** sin escuela reciben su EP
(0 equivocadas). Quedan 212: 168 por nombre de escuela sin alias en el lookup `d9b1e0c2`
(152 «Educación, Especialidad Primaria y Pedagogía Terapeútica», 10 Tecnología Médica —sin org EP—,
4 «EP Educación: Educación Física», 1 «EP Educación: Especialidad Musical y Artes», 1 Comunicación
Audiovisual —sin org EP—) y 44 por la condición de D6 (`primaryAffiliation` staff 22 / faculty 1 /
vacía 21).

**Canario real** (`202512090`, `202310412`, `201612129`): correcto en MidPoint, OpenLDAP (.168 y .169)
y Koha (`MODIFY SUCCESS`, `library_id` BUJ/BUT/BUJ). **Control negativo** (`202311335`, no canario,
la simulación le cambiaba campus/EP/Koha): `import` real → ficha intacta. El gate funciona.

## Estado del corte (15-oct-2026)

- Aprobado por Alberto el 14-oct 20:58. El PATCH desde la sesión del agente lo bloqueó el sistema de
  permisos; **Alberto lo aplicó él mismo ~00:35 del 15-oct** (HTTP 204). PROD **v205**: los 7 `primary-*`
  activos sin condición; los 7 viejos en `archived` **conservando su condición** (rollback más simple).
  Esquema con las 5 `PRIMARY_*`.
- **No se lanzó recon manual**: el cambio lo procesa `recon-oracle-lamb-estudiantes-daily` de las 06:20.
- **PENDIENTE: verificar tras la recon de las 06:20** contra la simulación (`campusStudent` ~1.451 cambios +
  31 ISTAT vacíos; +~1.762 EP; 0 EP perdidas/cambiadas; fallos ≈ 36) y el testigo `202512090` + muestra
  en LDAP (.168/.169) y Koha. Foto previa del 14-oct 20:59 (30.051 usuarios) en la sesión del agente.
- Repo alineado a v205 en el mismo día.

## Procedimiento de corte (referencia)

1. `PATCH patch3-corte.xml` (zero-set de la condición de los 7 inbounds nuevos; los 7 viejos a `archived`).
2. Verificar: `<schema>` 28 atributos, test connection 15/15, ids de inbounds, `lifecycleState`.
3. `POST .../tasks/9bcfb273-3d8e-4acb-84b0-e7c8b490975b/run` (recon diaria, 4 hilos) en ventana
   atendida 19:30–21:30 Lima (sin choques: backup 22:30, Entra 02:00), **o** dejar que la de las 06:20
   lo haga. Duración esperada ~60–75 min (la diaria dura ~53; se suman ~18k escrituras en el foco).
4. Verificar con las mismas consultas (564 → 0; Koha/LDAP por muestreo) y actualizar el repo:
   quitar las condiciones de los `primary-*` y marcar `archived` los viejos (mismo commit que el corte).
5. Limpieza posterior (otro cambio): retirar los inbounds viejos y la lista de canarios.

**Rollback:** `lifecycleState=active` en los viejos + re-añadir la condición (bloque de `patch2`) en
los nuevos, y recon. Los valores ya escritos vuelven con esa recon.

## Deriva repo↔PROD corregida en el repo (sin efecto en PROD)

- `program-level-to-studyLevel`: PROD `strong` + normalización canónica (2026-08-10); el repo tenía `normal` + minúsculas.
- `correo-personal-to-personalEmail`: el repo tenía pegado el código de `studyLevel`.
- `sunedu-code-to-academicProgramSuneduCode`: no existe en PROD; retirado del repo.

## Verificación del corte (15-oct-2026)

Recon `recon-oracle-lamb-estudiantes-daily` lanzada a mano por Alberto: **00:39 → 01:34 Lima (55 min)**,
30.038 éxitos y **36 fallos** (los mismos 36 crónicos de la recon del 14-oct). Comparación con la foto previa
(`~/backups/estudiantes-campus-20261014/snap_antes.psv` vs `snap_despues.psv`, Mac):

| Ítem | Simulado | Real |
|---|---|---|
| `campusStudent` LIMA→JULIACA / LIMA→TARAPOTO | 1.062 / 387 | **1.060 / 386** |
| ISTAT pierden el LIMA inventado | 31 | **31** |
| Koha `library_id` BUL→BUJ / BUL→BUT | 1.064 / 385 | **1.062 / 384** |
| Asignaciones nuevas a EP | 1.762 | **1.759** |
| EP perdidas / cambiadas | 0 / 0 | **0 / 0** |
| Facultad / nivel | 84 / 39 | 86 / 40 |

Usuarios desaparecidos: 0. 14 cambios de ciclo de vida (12 draft→active, 2 archived→active; 11 de ellos con
matrícula 2026-2): flujo diario de ~18 h de datos nuevos de Oracle, no atribuible al corte. Testigos 202512090,
202310412, 201612129 sin cambios (ya estaban corregidos como canarios). Muestra de 8 en la BD de Koha
(`koha-mysql upeu`): 6 BUJ + 2 BUT, actualizados 00:46–01:09 = lo esperado por MidPoint.

## Alias de escuela en el lookup `d9b1e0c2` (15-oct-2026)

Pedido de Alberto: «arregla los 168 que faltan escuela». En el feed completo eran **628 estudiantes**
(no 157): el texto de `PRIMARY_SCHOOL` no estaba en el lookup.

**`patch4-lookup-alias-escuela.xml`** (PATCH `add` de 5 filas, aplicado a las 07:22 después de la recon de
las 06:20; lookup v8→**v9**, 80 filas; backup `~/backups/lookup-escuela-20261015/lookup-d9b1e0c2-v8.xml`).
La clave es el texto **tras quitar `EP `**. La equivalencia se probó por P-code, no por parecido del nombre:

| Clave nueva | EP | Evidencia | Estudiantes |
|---|---|---|---|
| `Educación, Especialidad Primaria y Pedagogía Terapeútica` | EP-EDU-PRI | P20 (= EP-EDU-PRI) | 580 |
| `Educación: Educación Física` | EP-EDU-EFI | P12 | 33 |
| `Educación: Especialidad Musical y Artes` | EP-EDU-MUA | P17 | 13 |
| `Educación: Especialidad de Lingüística y Literatura` | EP-EDU-IES | P97 (VocBench, = un programa de EP-EDU-IES) | 1 |
| `de Educación: Especialidad Biología y Quimica` | EP-EDU-CIN | alias VocBench existente con «de» | 1 |

El repo del lookup se regeneró desde PROD: tenía 70 filas frente a 75, y una «Psicología»→EP-PSI-FCHE que
PROD no tiene.

**Consumidores medidos:** Egresados 0 afectados; Trabajadores `TEACHING_PROGRAMS` 146 docentes (solo
cambia `teachingProgram`, que no consume nada más).

**Simulación** (recompute `preview` de los 774): +628 `academicProgramCode`, +554 asignaciones a EP,
+547 `eduPersonOrgUnitDN`, +110 `teachingProgram`, **0** EP perdidas o cambiadas. **21 personas
excluidas** porque arrastraban efectos ajenos al alias. En 9 de ellas la cuenta LDAP pasaba a `disabled`
siendo activas: es el «estado intermedio» de ex-trabajadores tocados por la recon de Trabajadores de las
06:00, como en el caso 201810596. **Pendiente de investigar; no recomputar a esas personas a mano.**
Lista: 16763865 200511714 200610300 200711023 201110259 201121347 201511082 201910802 202220315
202310594 202311642 202312372 202313398 202413952 202511878 40246911 44947277 71921385 76283402
8710001 9110268.

**Real:** canario de 3 (07:35) + lote de 750 (07:37–07:42), recompute acotado por `inOid` (lista en
`alias-escuela-lote-753.txt`). Auditoría: LDAP `eduPersonOrgUnitDN` 540/540, `academicProgramCode`
621/621, `teachingProgram` 97/97 (= simulación), **0** cambios de activación, **0** asignaciones
borradas. Postgres: 547/547 con la EP esperada (PRI 514, EFI 21, MUA 11, IES 1). Hubo 2 fallos de
la clase crónica de Koha `secondary_email`. LDAP verificado en .168 y .169 (muestra de 5).

**Sin EP todavía:** 143 estudiantes de carreras sin org EP → borrador
[`../../architecture/adrs/ADR-067-escuelas-profesionales-nuevas-sin-org.md`](../../architecture/adrs/ADR-067-escuelas-profesionales-nuevas-sin-org.md).
