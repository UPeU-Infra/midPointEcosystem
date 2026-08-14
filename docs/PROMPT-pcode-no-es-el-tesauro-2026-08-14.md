# Los 466 sin P-code NO son un problema del tesauro

**Para:** equipo de MidPoint / IGA
**De:** InOut — medido el 14-ago-2026 contra Oracle LAMB (`192.168.13.9/UPEU`), LDAP de
producción (`192.168.15.168`) y el tesauro (`vocbench.upeu.edu.pe`).

---

## Por qué escribimos esto

Nos dijeron que el puente ya está desplegado y consumiendo por ID —correcto— y que los
estudiantes que siguen sin P-code lo están **porque su programa no tiene el identificador de
LAMB registrado en el tesauro**, y que hacía falta saber cuántos programas son para
dimensionar el trabajo en VocBench.

Fuimos a contarlos. Salieron 72. Antes de enviárselos verificamos la premisa, y **no se
sostiene**: mandar esa lista habría puesto a VocBench a registrar 72 vínculos que en su
mayoría ya funcionan.

## La comprobación

Cruzamos los **19.153 estudiantes que SÍ tienen P-code** contra LAMB, y miramos en qué
programas están:

| | |
|---|---:|
| Programas licenciados de los estudiantes afectados | **72** |
| — donde **sí** hay estudiantes que obtienen su P-code | **69** |
| — donde ninguno lo obtiene | **3** |
| Estudiantes afectados que están en programas que funcionan | **459** de 466 |

En 69 de esos 72 programas hay compañeros de aula con su P-code correctamente publicado. Si
el programa no estuviera vinculado al tesauro, no lo tendría **ninguno** de ellos.

**La causa está en la persona, no en el programa.**

## Dónde sí está el patrón: la antigüedad del estudiante

Agrupando por cohorte de ingreso (los cuatro primeros dígitos del código):

| cohorte | sin P-code | con P-code | % que falla |
|---|---:|---:|---:|
| 2003–2011 | 74 | 312 | ~19 % |
| 2012–2016 | 85 | 498 | ~15 % |
| 2017–2021 | 161 | 2.593 | ~6 % |
| 2022–2023 | 13 | 4.211 | 0,3 % |
| 2024 | 45 | 2.114 | **2,1 %** |
| 2025–2026 | 18 | 5.492 | 0,3 % |

Mediana de cohorte: **2019** entre los que fallan, **2023** entre los que no.

El fallo se concentra casi entero en matrículas antiguas —rezagados, gente que retomó, planes
de versiones recodificadas—. La excepción es **2024**, que rompe la tendencia con 45 casos
(2,1 % frente al 0,3 % de sus vecinas); puede ser otra cosa y vale la pena mirarla aparte.

## Pares para depurar

Dos estudiantes del **mismo programa**, uno con P-code y otro sin él. Comparar sus registros
en MidPoint debería mostrar la diferencia directamente:

| SUNEDU | programa | sin | con | ejemplo SIN | ejemplo CON |
|---|---|---:|---:|---|---|
| 104 | Contabilidad y Gestión Tributaria, Presencial | 60 | 393 | `201121109` | `201220907` |
| 115 | Psicología | 41 | 1399 | `200910554` | `200310122` |
| 19 | Ingeniería de Sistemas, Presencial | 21 | 253 | `200411248` | `200110121` |
| 14 | Educación: Especialidad Primaría, Presencial | 18 | 26 | `200010074` | `200411005` |
| 113 | Ingeniería de Sistemas, Presencial | 16 | 572 | `200310873` | `200210345` |
| 67 | Posgrado de Maestría en Enfermería con Mención en Ad | 15 | 45 | `200610968` | `200110503` |
| 32 | Posgrado de Maestría en Educación: Mención en Psicol | 15 | 2 | `200220124` | `200010249` |
| 31 | Posgrado de Maestría en Educación: Investigación y D | 15 | 7 | `200310365` | `200010085` |
| 74 | Posgrado de Maestría en Educación: Investigación y D | 13 | 157 | `201310387` | `200110014` |
| 23 | Psicología, Presencial | 12 | 531 | `200810628` | `200010187` |
| 30 | Posgrado de Maestría en Educación: Administración Ed | 12 | 1 | `200210227` | `200310430` |
| 110 | Ingeniería Ambiental | 12 | 570 | `201812072` | `201011218` |
| 78 | Posgrado de Maestría en Salud Publica Mención: Gesti | 12 | 88 | `200921173` | `200010289` |
| 17 | Ingeniería Civil, Presencial | 11 | 153 | `201323117` | `200110121` |
| 75 | Posgrado de Maestría en Educación: Mención en Psicol | 11 | 124 | `200311422` | `200010159` |
| 7 | Contabilidad y Gestión Tributaria - Sección Lima | 11 | 87 | `200910067` | `200010159` |
| 126 | Psicología, Presencial | 10 | 647 | `201110235` | `200510264` |
| 15 | Enfermería, Presencial | 9 | 381 | `200110470` | `200010181` |
| 22 | Nutrición Humana | 8 | 193 | `200620130` | `200010114` |
| 111 | Ingeniería Civil, Presencial | 8 | 1255 | `201010455` | `200711043` |

## Lo único que sí podría ser trabajo de tesauro

Tres programas donde ningún estudiante obtiene P-code. Son pocos alumnos, así que tampoco es
concluyente, pero son los únicos candidatos legítimos:

| id_lamb | SUNEDU | programa | afectados |
|---|---|---|---:|
| `214` | 149 | Posgrado de Segunda Especialidad en Estadística Aplicada | 4 |
| `177` | 134 | Posgrado de Segunda Especialidad en Enfermería en Cuidados Intensivos | 2 |
| `536` | 154 | Segunda Especialidad en Psicología Clínica y de la Salud | 1 |

## Un apunte sobre el tesauro, por si ayuda

Buscando en `Tesauro_Institucional_UPeU` (440 conceptos) un predicado que guarde el
identificador de LAMB —cualquiera cuyo nombre contenga `lamb`, `erp`, `idPrograma` o
`identifier`— no aparece **ninguno**. `skos:notation` existe pero guarda códigos INEI/CINE y
SUNEDU.

Como el puente evidentemente funciona para 19.153 personas, el vínculo debe estar viviendo en
la configuración de MidPoint y no en el tesauro. Lo decimos por si el diagnóstico inicial
partía de suponer que estaba allí.

## Qué pedimos

Nada que aprovisionar todavía. Solo que miren un par de los casos de arriba: con dos
estudiantes del mismo programa, uno funcionando y otro no, la diferencia debería salir sola.
Cuando sepan qué es, si hace falta algo de nuestro lado lo hacemos.
