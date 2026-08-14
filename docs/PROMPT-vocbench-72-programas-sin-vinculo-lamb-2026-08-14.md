# Dimensionamiento para VocBench: 72 programas a vincular con LAMB

**Para:** equipo del tesauro (VocBench) / MidPoint
**De:** InOut — medido en vivo el 14-ago-2026 contra Oracle LAMB (`192.168.13.9/UPEU`),
LDAP de producción (`192.168.15.168`) y el tesauro (`vocbench.upeu.edu.pe`,
proyecto `Tesauro_Institucional_UPeU`). Nada aquí es supuesto.

---

## La respuesta corta

**72 programas distintos** — 38 de pregrado y 34 de posgrado.

Cubren **429 estudiantes**. Los otros 159 del total medido no necesitan nada: no están
matriculados en ningún programa licenciado.

## Cómo se llegó a ese número

Partiendo de los estudiantes activos sin `scibackAcademicProgramSuneduCode` en LDAP:

| Paso | Resultado |
|---|---:|
| Estudiantes activos sin P-code (filtro completo, ver abajo) | 6.971 |
| — de ellos, en unidades académicas reales (facultades, posgrado, EP) | **588** |
| — con al menos un programa **licenciado** en LAMB → el P-code SÍ es derivable | **429** |
| — sin ningún programa licenciado (inglés, CEPRE, talleres, tesis, diplomaturas) | 159 |
| **Programas licenciados distintos que suman esos 429** | **72** |

Filtro LDAP:

```
(&(objectClass=inetOrgPerson)(eduPersonAffiliation=member)
  (eduPersonAffiliation=student)(!(scibackAcademicProgramSuneduCode=*)))
```

Cruce en LAMB (plan **activo**, `ACAD_ALUMNO_PLAN.ESTADO = '1'`):

```sql
SELECT a.CODIGO, pe.ID_PROGRAMA_ESTUDIO, pe.NOMBRE, pe.CODIGO_SUNEDU
  FROM MOISES.PERSONA_NATURAL_ALUMNO a
  JOIN DAVID.ACAD_ALUMNO_PLAN      ap ON ap.ID_PERSONA = a.ID_PERSONA
  JOIN DAVID.ACAD_PLAN_PROGRAMA    pp ON pp.ID_PLAN_PROGRAMA = ap.ID_PLAN_PROGRAMA
  JOIN DAVID.ACAD_PROGRAMA_ESTUDIO pe ON pe.ID_PROGRAMA_ESTUDIO = pp.ID_PROGRAMA_ESTUDIO
 WHERE a.CODIGO IN (...)
```

## Un dato del tesauro que conviene mirar antes de empezar

El proyecto `Tesauro_Institucional_UPeU` tiene hoy **440 conceptos**, de los cuales 108
declaran algún `codigoSunedu*`. Al buscar un predicado que guarde el identificador de LAMB
—cualquiera cuyo nombre contenga `lamb`, `erp`, `idPrograma` o `identifier`— **no aparece
ninguno**:

```sparql
SELECT DISTINCT ?p WHERE { ?s ?p ?o
  FILTER(CONTAINS(LCASE(STR(?p)),"lamb") || CONTAINS(LCASE(STR(?p)),"erp")
      || CONTAINS(LCASE(STR(?p)),"idprograma") || CONTAINS(LCASE(STR(?p)),"identifier")) }
```
→ 0 resultados.

`skos:notation` existe (725 usos) pero guarda códigos INEI/CINE (`0612`, `0313`…) y SUNEDU
(`61`, `72`, `91`…), no identificadores de LAMB.

**Esto no contradice que el puente funcione** —19.032 estudiantes sí traen su P-code—, así
que el enlace debe estar viajando por otra vía que desde fuera no se ve: probablemente un
mapeo en la configuración de MidPoint y no en el tesauro. Merece la pena confirmarlo antes de
elegir dónde registrar los 72: si el vínculo va a vivir en el tesauro, hace falta acordar
primero **qué predicado usar** (p. ej. `upeu:idProgramaLamb`), porque hoy no existe.

## Los 72 programas

`id_lamb` es `ACAD_PROGRAMA_ESTUDIO.ID_PROGRAMA_ESTUDIO`; `sunedu` es su `CODIGO_SUNEDU`,
que LAMB **ya tiene** — el hueco no está ahí.

| id_lamb | sunedu | nombre en LAMB | estudiantes |
|---|---|---|---:|
| `315` | 104 | Contabilidad y Gestión Tributaria, Presencial | 60 |
| `277` | 115 | Psicología | 41 |
| `17` | 19 | Ingeniería de Sistemas, Presencial | 21 |
| `143` | 14 | Educación: Especialidad Primaría, Presencial | 18 |
| `280` | 113 | Ingeniería de Sistemas, Presencial | 16 |
| `202` | 32 | Posgrado de Maestría en Educación: Mención en Psicología Educativa | 15 |
| `207` | 31 | Posgrado de Maestría en Educación: Investigación y Docencia Universitaría | 15 |
| `626` | 67 | Posgrado de Maestría en Enfermería con Mención en Administración y Gestión, Semipresencial | 15 |
| `774` | 74 | Posgrado de Maestría en Educación: Investigación y Docencia Universitaria, A Distancia | 13 |
| `4` | 23 | Psicología, Presencial | 12 |
| `212` | 30 | Posgrado de Maestría en Educación: Administración Educativa | 12 |
| `282` | 110 | Ingeniería Ambiental | 12 |
| `766` | 78 | Posgrado de Maestría en Salud Publica Mención: Gestión de los Servicios de Salud | 12 |
| `18` | 17 | Ingeniería Civil, Presencial | 11 |
| `92` | 7 | Contabilidad y Gestión Tributaria - Sección Lima | 11 |
| `775` | 75 | Posgrado de Maestría en Educación: Mención en Psicología Educativa, A Distancia | 11 |
| `325` | 126 | Psicología, Presencial | 10 |
| `3` | 15 | Enfermería, Presencial | 9 |
| `2` | 22 | Nutrición Humana | 8 |
| `281` | 111 | Ingeniería Civil, Presencial | 8 |
| `165` | 34 | Posgrado de Maestría en Enfermería con Mención en Administración y Gestión | 7 |
| `662` | 68 | Posgrado de Maestría en Psicología Clinica y de la Salud | 7 |
| `308` | 112 | Ingeniería de Industrías Alimentarías | 6 |
| `769` | 90 | Posgrado de Maestría en Auditoría Mención: Auditoría Integral | 6 |
| `1` | 21 | Medicina Humana, Presencial | 5 |
| `19` | 16 | Ingeniería Ambiental, Presencial | 5 |
| `746` | 71 | Posgrado de Maestría en Administración de Negocios con mención en Liderazgo y Gestión Organizacional | 5 |
| `778` | 79 | Posgrado de Maestría en Salud Publica Mención: Salud Colectiva y Promoción de la Salud | 5 |
| `146` | 10 | Educación: Especialidad Lingüistica e Inglés, Presencial | 4 |
| `151` | 13 | Educación Inicial y Puericultura, Presencial | 4 |
| `214` | 149 | Posgrado de Segunda Especialidad en Estadística Aplicada para Investigación | 4 |
| `314` | 105 | Contabilidad y Gestión Tributaria - Sección Juliaca - Sección Juliaca, Semipresencial | 4 |
| `16` | 5 | Ciencias de la Comunicación, Presencial | 3 |
| `21` | 24 | Teología | 3 |
| `149` | 12 | Educación: Especialidad Musical y Artes, Presencial | 3 |
| `229` | 43 | Posgrado de Maestría en Salud Publica Mención: Gestión de los Servicios de Salud | 3 |
| `276` | 109 | Enfermería, Presencial | 3 |
| `319` | 108 | Educación: Especialidad Primaría | 3 |
| `329` | 118 | Arquitectura | 3 |
| `338` | 125 | Marketing y Negocios Internacionales | 3 |
| `570` | 20 | Marketing y Negocios Internacionales | 3 |
| `688` | 178 | Segunda Especialidad en Psicología Clínica y de la Salud | 3 |
| `776` | 73 | Posgrado de Maestría en Educación: Administración Educativa | 3 |
| `41` | 18 | Ingeniería de Industrias Alimentarias, Presencial | 2 |
| `174` | 45 | Posgrado de Maestría en Teología, Presencial | 2 |
| `177` | 134 | Posgrado de Segunda Especialidad en Enfermería en Cuidados Intensivos Neonatales | 2 |
| `179` | 44 | Posgrado de Maestría en Salud Publica Mención: Salud Colectiva y Promoción de la Salud | 2 |
| `250` | 50 | Posgrado de Doctorado en Educación mención: Gestión Educativa | 2 |
| `336` | 119 | Contabilidad y Gestión Tributaria | 2 |
| `529` | 101 | Administración, Presencial | 2 |
| `621` | 114 | Nutrición Humana | 2 |
| `763` | 98 | Maestría en Ingeniería Ambiental y Desarrollo Sostenible | 2 |
| `768` | 88 | Posgrado de Maestría en Administración de Negocios Mención: Finanzas | 2 |
| `784` | 80 | Posgrado de Maestría en Ingeniería de Sistemas con mención en Dirección y Gestión de Tecnologías de Información | 2 |
| `206` | 46 | Posgrado de Maestría en Teología Bíblica | 1 |
| `215` | 140 | Posgrado de Segunda Especialidad en Enfermería en Cuidados Intensivos | 1 |
| `245` | 49 | Posgrado de Doctorado en Educación mención: Curriculo y Docencia | 1 |
| `320` | 106 | Educación: Especialidad Lingüistica e Inglés | 1 |
| `322` | 107 | Educación Inicial y Puericultura, Presencial | 1 |
| `327` | 124 | Ingeniería de Sistemas, Presencial | 1 |
| `328` | 122 | Ingeniería Ambiental, Presencial | 1 |
| `333` | 116 | Administración - Mención : Gestión Empresaríal | 1 |
| `530` | 102 | Administración - Sección Juliaca - Sección Juliaca, Semipresencial | 1 |
| `536` | 154 | Segunda Especialidad en Psicología Clínica y de la Salud | 1 |
| `574` | 29 | Posgrado de Maestría en Terapia Familiar y de Pareja, Presencial | 1 |
| `618` | 123 | Ingeniería Civil | 1 |
| `628` | 171 | Posgrado de Segunda Especialidad en Enfermería en Centro Quirúrgico | 1 |
| `634` | 169 | Posgrado de Segunda Especialidad en Enfermería en Cuidados Intensivos | 1 |
| `635` | 159 | Posgrado de Segunda Especialidad de Enfermería en Emergencias y Desastres | 1 |
| `664` | 64 | Posgrado de Maestría en Educación: Mención en Psicología Educativa | 1 |
| `669` | 155 | Posgrado de Segunda Especialidad en Estadística Aplicada para Investigación | 1 |
| `729` | 157 | Posgrado de Segunda Especialidad en Enfermería en Cardiología | 1 |

---

## Lo que NO se pide

- Nada en LAMB: los 72 ya tienen su `CODIGO_SUNEDU` registrado.
- Nada en las personas de LDAP.
- Los 159 estudiantes sin programa licenciado **deben** seguir sin P-code: inglés, CEPRE,
  cursos taller, cursos de tesis y diplomaturas no son programas licenciados y su cobertura
  correcta es 0 % (Ley 30220 art. 46).

## Cómo verificar que quedó resuelto

El mismo filtro LDAP de arriba, contando solo unidades académicas reales, debe bajar de
**588** hacia **159**.
