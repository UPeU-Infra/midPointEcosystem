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
| 3 | Corte: `patch3-corte.xml` | **pendiente de aprobación** |

El GATE (condición Groovy) activa la lógica nueva solo en **simulaciones** (`TaskExecutionMode`
no persistente) y para la lista de **canarios**; en producción, para el resto, sigue la vieja. Ante
error, comportamiento de producción.

## Corte (cuando se apruebe)

1. `PATCH patch3-corte.xml` (quita la condición de los inbounds nuevos y archiva los viejos).
2. Verificar `<schema>`, test connection, `schemaHandling`.
3. Ejecutar `recon-oracle-lamb-estudiantes-daily` (run now) **o** esperar a la de las 06:20.

## Deriva repo↔PROD corregida en el repo (sin efecto en PROD)

- `program-level-to-studyLevel`: PROD `strong` + normalización canónica (2026-08-10); el repo tenía `normal` + minúsculas.
- `correo-personal-to-personalEmail`: el repo tenía pegado el código de `studyLevel`.
- `sunedu-code-to-academicProgramSuneduCode`: no existe en PROD; retirado del repo.
