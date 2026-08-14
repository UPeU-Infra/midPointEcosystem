# ADR-063 — El tesauro cubre el catálogo de matrícula; la licencia es una propiedad del concepto

**Fecha:** 14-ago-2026
**Estado:** propuesto
**Ámbito:** vocabulario controlado (VocBench) + LookupTable de MidPoint
**Dependencia de:** [`ADR-062`](ADR-062-publicar-id-programa-siempre.md) — que lo referencia como
dependencia, **no como opcional**
**Fundamento:** libro de MidPoint (Evolveum) — *Hub and Spoke* p. 120, *HR Feed Recommendations*
p. 174-175, *Data Unification* p. 203-204, `LookupTableType` p. 230 — más eduPerson 202208,
SCHAC 1.6.0, ISO 24760-1, ISO 27001 A.5.18, RBAC INCITS 359

## La pregunta

¿Debe el tesauro institucional cubrir el catálogo **completo** de programas —incluidos los no
licenciados— o basta con los 188 licenciados, dejando que el resto viva solo con el
identificador crudo de Oracle?

Se planteó como decisión de producto. **No lo es**: tiene dueño doctrinal.

## Decisión

**El tesauro cubre todo programa en el que una persona puede estar matriculada.** La condición
"licenciado por SUNEDU" se modela como **propiedad del concepto**, nunca como **condición de
existencia del concepto**.

1. **Todos los programas de la fuente son `skos:Concept`** del esquema de programas. El P-code
   se declara como `skos:notation` con datatype propio, **presente solo en los licenciados**.
   La vista A4/A8 de Calidad pasa a ser una **consulta** (`FILTER(EXISTS notation-sunedu)`), no
   un **filtro de membresía**. Calidad no pierde nada: gana un denominador. Si se quiere
   materializar la vista, `skos:Collection` es el constructo SKOS para facetas.
2. **El vínculo `ID_PROGRAMA_ESTUDIO` → concepto se muda al tesauro**, como `skos:notation` (o
   `dct:identifier`) con datatype propio en cada concepto.
3. **La LookupTable `program-pxx-byid` pasa a ser artefacto generado** por SPARQL desde el
   tesauro, no un objeto mantenido a mano.

## Por qué no era opcional

**Hoy MidPoint es la autoridad de facto de un vocabulario que no le pertenece.** Ninguno de los
440 conceptos del tesauro declara un predicado con el id de LAMB: la correspondencia vive
**solo** en la LookupTable de MidPoint. Hay por tanto dos vocabularios en paralelo —los
conceptos en VocBench, la correspondencia en MidPoint— y **ninguno completo**. Es la misma clase
de defecto que duplicar el IIA, repartido entre dos sistemas (ISO 24760: un atributo, una
autoridad). El punto 2 lo corrige devolviendo la autoridad a VocBench.

**Una tabla de 188 filas no cumple ninguna de sus dos funciones.** El libro define
`LookupTableType` para *value enumerations* y *value mapping* (p. 230):

- como **enumeración de validación**, una enumeración que no enumera el dominio no valida nada
  — MidPoint no puede distinguir "programa inexistente" de "programa no licenciado";
- como **tabla de traducción**, faltarle 106 entradas no significa que esas palabras no
  existan; significa que el traductor no las sabe decir.

**El criterio de cobertura lo puso un consumidor.** El catálogo se pobló con el criterio de
Calidad —el A4/A8—, no con el de identidad. Es exactamente la estructura del incidente de
`ou=org`: un criterio de un consumidor decidió la cobertura de un atributo compartido, el hueco
fue invisible desde dentro, y lo destapó quien lo consumía —**899 personas sin área en el aforo
del CRAI, descubiertas por InOut, no por el IGA**. Aquí el criterio es "no requiere
licenciamiento" en vez de "no es obligatorio para todos", y la población es **6.706** en vez de
899.

El argumento «el IGA no es un catálogo académico, no le toca al tesauro cubrirlo» es la misma
frase de InOut con otro sujeto. Ya sabemos cómo termina.

## Lo que gana la gobernanza

**El hueco se vuelve auto-medible.** Con el punto 3, los programas sin concepto son un `diff`
entre la fuente y una consulta SPARQL — no un descubrimiento accidental. Es la lección de InOut
convertida en mecanismo, que es la única forma en que una lección sobrevive a quien la aprendió.

## Consecuencia sobre lo que se publica

**El portador primario del programa hacia LDAP debe ser el URI**, con el P-code conservado como
valor derivado para Calidad.

`scibackAcademicProgramSuneduCode` —lo que se publica hoy— es estructuralmente un mal portador
primario: por definición legal (Ley 30220 art. 46) solo existe para los licenciados, y un
atributo cuyo dominio no cubre a la población no puede sostener autorización, certificación ni
reporting.

Nota verificada: **ni eduPerson 202208 ni SCHAC 1.6.0 definen un atributo de programa
académico**. `eduPersonOrgUnitDN` es un DN interno que no debe salir del IdP,
`schacPersonalUniqueCode` identifica a la **persona** y `eduPersonEntitlement` expresa un
**derecho**, no una descripción curricular. Por eso el espacio de nombres propio
(`scibackAcademicProgram*`) es correcto — lo que el estándar sí dicta es la **forma del valor**:
URI o URN scopeada, nunca una clave cruda del sistema origen.

## Riesgo y orden de ejecución

⚠️ **Materializar el zero-set del mapping ANTES de ampliar el tesauro.** Al empezar a resolver
los 106, `academicProgramUri` añadirá valores sin retirar los previos — el patrón PM10 que ya
costó 7.841 personas publicando a la vez la URI deprecada y la canónica, con una limpieza
revertida el 6-ago porque el origen estaba en el mapping y no en LDAP. Mismo mecanismo, mismo
atributo, y esta vez se ve venir.

## Verificación

1. Zero-set materializado en el mapping de `academicProgramUri` **antes** de tocar el tesauro.
2. Canario: un programa no licenciado (p. ej. Inglés) con concepto, **sin** `skos:notation`
   SUNEDU → debe resolver a URI y **no** a P-code.
3. Control negativo: un licenciado no cambia ni de URI ni de P-code.
4. La LookupTable regenerada por SPARQL reproduce las 188 filas actuales **más** las nuevas, sin
   alterar ninguna existente.
5. Métrica de cierre: programas de la fuente sin concepto → **106 → 0**.
6. Que la vista A4/A8 de Calidad siga dando exactamente los mismos programas que hoy.

## Lo que este ADR NO decide

Qué atributo LDAP transporta el URI hacia InOut y los demás consumidores. Eso se decide con
ellos, y sigue abierto desde el prompt del puente.
