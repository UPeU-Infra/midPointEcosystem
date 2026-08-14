# Los 429 sin P-code: tres causas distintas, ninguna es "falta el ID de LAMB"

**Para:** equipo de MidPoint / IGA y equipo del tesauro
**De:** InOut — medido el 14-ago-2026 contra Oracle LAMB (`192.168.13.9/UPEU`), LDAP de
producción (`192.168.15.168`) y el tesauro (`vocbench.upeu.edu.pe`, proyecto
`Tesauro_Institucional_UPeU`). Nada aquí es supuesto.

---

## Resumen

Nos dijeron que los estudiantes sin P-code lo están porque **su programa no tiene el
identificador de LAMB registrado en el tesauro**, y pidieron cuántos programas son para
dimensionar VocBench.

Fuimos a contarlos: salían 72. Antes de enviárselos verificamos la premisa y **no se
sostiene**. Al partir los casos por su causa real aparecen tres grupos, y el trabajo de
VocBench resulta ser **8 conceptos**, no 72 programas.

| causa | estudiantes | de quién es |
|---|---:|---|
| No se les asignó ningún programa (no traen URI de concepto) | **149** | MidPoint |
| Su concepto existe pero **no declara código SUNEDU** en el tesauro | **229** | **VocBench — 8 conceptos** |
| Su concepto declara código, pero no se publica igual | 51 | a investigar |
| **total** | **429** | |

## Por qué la premisa no se sostiene

Cruzamos los **19.153 estudiantes que SÍ tienen P-code** contra LAMB para ver en qué
programas están:

- De los 72 programas señalados, **69 tienen estudiantes que obtienen su P-code sin
  problema**. Si el programa no estuviera vinculado, no lo tendría ninguno.
- **459 de los 466** afectados están en programas que demostradamente funcionan.

Solo 3 programas no tienen ningún estudiante con P-code, y suman 7 alumnos:

| id_lamb | SUNEDU | programa | afectados |
|---|---|---|---:|
| `214` | 149 | Posgrado de Segunda Especialidad en Estadística Aplicada | 4 |
| `177` | 134 | Posgrado de Segunda Especialidad en Enfermería en Cuidados Intensivos | 2 |
| `536` | 154 | Segunda Especialidad en Psicología Clínica y de la Salud | 1 |

## Grupo 1 — 149 estudiantes sin programa asignado (MidPoint)

No traen `eduPersonOrgUnitDN` ni `eduPersonEntitlement` con URI de concepto: en `ou` llevan
el nombre de la **facultad o de la escuela**, no de un programa.

El contraste más limpio está en la cohorte de posgrado 2024, donde se ve sin ruido:

| | sin P-code | con P-code |
|---|---:|---:|
| estudiantes | 45 | 53 |
| **traen URI de concepto** | **1** | **53** |
| `ou` | "Escuela General de Posgrado" (44 de 45) | el nombre del programa concreto |

En LAMB los dos grupos son indistinguibles: mismo `CONTRATO` (vacío en el 100 % de ambos),
mismas sedes, modalidades solapadas. La diferencia aparece solo en LDAP. **A estas personas
no se les vinculó programa**, y sin programa no hay P-code que derivar.

## Grupo 2 — 229 estudiantes: 8 conceptos sin código SUNEDU (VocBench)

Estos **sí** traen su URI de concepto. El concepto existe en el tesauro. Lo que le falta es
declarar su código SUNEDU: consultando cada uno por `*codigoSunedu*`, ocho no devuelven nada.

**Esta es la lista de trabajo real para VocBench:**

| afectados | concepto | códigos SUNEDU declarados |
|---:|---|---|
| 78 | `programa/contabilidad-gestion-tributaria` | ‹ninguno› |
| 48 | `c_b48bff58` | ‹ninguno› |
| 37 | `c_bbf436cf` | ‹ninguno› |
| 28 | `programa/educacion-inicial` | ‹ninguno› |
| 20 | `c_be8b346d` | ‹ninguno› |
| 11 | `c_c5f87ee9` | ‹ninguno› |
| 4 | `c_353ae8f7` | ‹ninguno› |
| 3 | `c_e399e0aa` | ‹ninguno› |

(Prefijo `http://upeu.edu.pe/sys/programas/`.)

Para comparar, los conceptos que **sí** lo declaran funcionan: `ingenieria-ambiental`
(`P100,P130,P24`), `nutricion-humana` (`P31`), `ingenieria-de-industrias-alimentarias`
(`P26`), `marketing-y-negocios-internacionales` (`P29`), `teologia` (`P35`),
`ciencias-de-la-comunicacion` (`P07`), `administracion` (`P04,P05,P95`).

## Grupo 3 — 51 estudiantes cuyo concepto sí declara código

Aquí la causa es otra y no la tenemos cerrada. En parte es el problema ya conocido de que un
concepto agrupa varias modalidades (`administracion` → `P04,P05,P95`; `ingenieria-ambiental`
→ `P100,P130,P24`) y la URI no dice cuál es. Pero hay casos con código único —
`nutricion-humana` con `P31`, 8 afectados — que deberían resolverse y no lo hacen.

## Sobre el identificador de LAMB

Buscando en los 440 conceptos del tesauro un predicado cuyo nombre contenga `lamb`, `erp`,
`idPrograma` o `identifier`, no aparece **ninguno**. Como el puente funciona para 19.153
personas, el vínculo debe vivir en la configuración de MidPoint y no en el tesauro. Lo
mencionamos porque el diagnóstico inicial parecía partir de suponer que estaba allí.

## Qué pedimos

1. **VocBench:** declarar el código SUNEDU en los 8 conceptos de arriba → resuelve 229.
2. **MidPoint:** revisar por qué a 149 personas no se les asigna programa. La cohorte de
   posgrado 2024 es el caso más limpio para depurarlo: 45 sin URI contra 53 con URI, con
   datos idénticos en LAMB.
3. Nada que aprovisionar en LAMB: los programas ya tienen su `CODIGO_SUNEDU` allí.

## Cómo verificar

```
(&(objectClass=inetOrgPerson)(eduPersonAffiliation=member)
  (eduPersonAffiliation=student)(!(scibackAcademicProgramSuneduCode=*)))
```

Contando solo los de unidades académicas reales, debe bajar de **588** hacia **159** (los que
no están en ningún programa licenciado y por tanto es correcto que no tengan P-code).
