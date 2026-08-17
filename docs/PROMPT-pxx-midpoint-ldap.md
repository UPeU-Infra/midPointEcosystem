# Prompt — MidPoint + LDAP: el P-code como código principal de programa

> Pegar al abrir una sesión nueva sobre `~/proyectos/productos/iga`.
> Estado medido **en producción el 17-ago-2026**: MidPoint `192.168.15.166`, LDAP `192.168.15.168`,
> VocBench vía SPARQL, Oracle LAMB.
> Sesiones hermanas: `koha/canonico/docs/PROMPT-pxx-koha.md` e `inout/canonico/docs/PROMPT-pxx-inout.md`.

---

## La regla (ADR-005 del tesauro)

UPeU identifica el programa académico por su **P-code / SEG-code** (`P30`, `SEG61`…) en **todos** sus
sistemas. El **código INEI queda solo para el repositorio de tesis**, donde SUNEDU/RENATI lo exige
como `renati.discipline`.

**Fuente de verdad, innegociable:** `/Users/alberto/Downloads/programas pxx upeu` — Formatos de
Licenciamiento **A4 y A8 2026-1**, **183 programas**. Cualquier cosa distinta está mal.

### Tres cosas que hay que tener claras antes de tocar nada

**1 · El P-code no es la llave de unión.** 52 conceptos llevan **dos** códigos oficiales porque UPeU
recodifica por resolución (`SEG20`→`SEG61`, `SEG26`→`SEG44`), y **ambos están en el A8 2026-1**.
Para empalmar sistemas se usa **`sb:academicProgramUri`**, que no cambia. El P-code es lo que se
muestra, se reporta y se declara.

**2 · El P-code depende de la MODALIDAD.** El A4 lista **una fila por modalidad**: Administración es
`P04` presencial, `P05` semipresencial y `P95` a distancia — tres programas distintos ante SUNEDU.

**3 · Multivalor está bien; duplicar el mismo programa, no.** Una persona puede cursar dos programas
y un docente enseñar en varias escuelas. Lo que no puede es llevar `P04` **y** `P95` por una sola
matrícula.

---

## Estado verificado — no rehacer

### VocBench (repo del tesauro)
* **188 IDs de LAMB** declarados como `skos:notation` con datatype `urn:esther:id_programa_estudio`,
  en 76 conceptos vigentes, sobre 440 conceptos totales.
* **100 % de los `ID_PROGRAMA_ESTUDIO` con matrícula resuelven a un concepto vigente**
  (16.927/16.927 del semestre 2026-2, programas en alcance).
* **Los 15 EP-codes atrapados en conceptos deprecados, migrados al vigente** — era el bloqueo
  literal del inbound retirado en PROD v184.
* Comprobación permanente en `10-auditar-tesauro.py`: *«IDs de Oracle atrapados en un concepto
  deprecado»*. Hoy da 0.

### Este repo, commiteado
* **`upeu/lookup-tables/program-pxx-byid.xml`** — OID `5d1c8a47-2b93-4f60-8e1a-7c4d9f0e6a25`,
  188 filas, `key` = `ID_PROGRAMA_ESTUDIO` → `value` = **un** P-code, el de la modalidad. Los 103
  que emite están todos en el A4/A8.
* **`upeu/lookup-tables/program-resolver-lamb-byid.xml`** — regenerada: 188 filas, 91 con EP-code.
* **`scripts/generar-lookup-programas.py`** — genera ambas desde VocBench. No editarlas a mano.
* **`canonical/schemas/sciback-person-v1.0.xml`** — `academicProgramSuneduCode` pasó de *LEGACY* a
  **PRINCIPAL**; `academicProgramIneiCode` a **metadato de disciplina para tesis**.

### LDAP producción — el P-code YA se publica
```
personas en ou=people                            49.480
con scibackAcademicProgramSuneduCode             22.767
P-codes distintos                                    91
de ellos, fuera del A4/A8 2026-1                      0   ✅
OUs de programa en ou=org                            26   (con EP-XXX + URI)
```

---

## Lo que hay que cambiar

### 1 · Publicar la URI del programa en las personas
Hoy `ou=people` lleva **solo cuatro** atributos `sciback*`: `scibackAcademicProgramSuneduCode`,
`scibackCampusCode`, `scibackDocumentNumber`, `scibackFacultyCode`. **La URI está únicamente en las
26 OUs de `ou=org`.**

Consecuencias medidas:
* **InOut no puede resolver por URI** — tendría que empalmar por P-code, justo lo que la regla 1
  prohíbe. Su prompt asume que la URI estará ahí.
* **Desde fuera es imposible auditar de dónde salió un código**, porque no hay con qué unir una
  persona a su `ID_PROGRAMA_ESTUDIO`.

### 2 · Un P-code por MATRÍCULA, no todos los del concepto
De las **1.133 personas con más de un P-code** en LDAP:

| | | |
|---|---|---|
| Programas **realmente distintos** | **496** | 43,8 % — correcto, **no tocar** |
| **Mismo concepto, varios códigos** | **637** | 56,2 % — **defecto** |

```
P08 + P96   223 personas  → Contabilidad, Gestión Tributaria y Aduanera
P04 + P95   208           → Administración
P08 + P09    79           → Contabilidad…
P04 + P05    75           → Administración
P19 + P98    24           → Educación Inicial y Puericultura
P127 + P14   14           → Educación, Especialidad Lingüística e Inglés
```

Es una sola matrícula con los códigos de **todas las modalidades** del programa pegados.

**Por qué importa:** cuando Calidad cuente alumnos de `P04` para el A4, esas 208 personas
aparecerán **también** en `P95` — el mismo estudiante contado dos veces en dos programas que ante
SUNEDU son distintos.

**La corrección:** `sb:academicProgramSuneduCode` se alimenta hoy de la columna `SUNEDU_CODE`
(→ `CODIGO_SUNEDU2`). Pasarlo a **`program-pxx-byid`**, que ya cruza con
`DAVID.ACAD_PROGRAMA_ESTUDIO.ID_MODALIDAD_ESTUDIO` (1=Presencial, 2=Semipresencial, 13=A Distancia)
y devuelve **uno solo por `ID_PROGRAMA_ESTUDIO`**. Quien curse dos programas seguirá con dos códigos.

Hace falta una función nueva en `canonical/function-libraries/sb-program-resolver-byid.xml`
(OID `3f8b6c04-…`), copiando `resolveProgramCodeById` pero apuntando al OID `5d1c8a47-…`.

De paso sube la cobertura: `CODIGO_SUNEDU2` resuelve el **73,18 %** de los 19.486 matriculados de
2026-2; la tabla del tesauro, el **88,44 %**.

### 3 · Desplegar el esquema que ya está en el repo
Solo cambian anotaciones, pero mientras no se despliegue **el `.xsd` sigue diciendo que el
identificador canónico es el INEI**, que es lo contrario de la decisión. ⚠️ Un cambio de esquema en
MidPoint suele exigir reinicio — confirmarlo con Alberto antes.

### 4 · Restaurar `program-id-to-academicProgramCode` (opcional, medir antes)
Es el inbound retirado en PROD v184, que entonces hundió la cobertura del 40,9 % al 17,0 % — **7.268
estudiantes sin organización**. Con los EP-codes ya migrados, resolver por ID daría **74,99 %**. El
techo es 75 % porque los EP-code solo existen para pregrado.

---

## Reglas de ejecución

**Publicar en paralelo antes de retirar nada.** El `EP-XXX` sostiene hoy la asignación de
organización del bloque D6 de `user-template-student`; quitarlo en caliente reproduce la regresión
de los 7.268.

**No renombrar DNs.** El DN codifica el EP-code (`ou=ep-com,ou=8,ou=org,…`); moverlos rompe
`memberOf`, ACLs y toda referencia por DN sin ganar nada — el DN es un handle opaco.

**LDAP:** el schema va en `cn=config`, que **NO replica** → aplicar en **.168 y .169**. Los datos sí
replican → aplicarlos en **un solo nodo**. Ver `upeu/ldap/rims-iga-contract/README.md`.

---

## Sobre los dos ADR recientes

**`ADR-062`** (aplicado en PROD, schema v32 / resource v199) publica `academicProgramSourceId`
siempre, resuelva o no a P-code, porque 6.706 estudiantes —Inglés, CEPRE, Conservatorio,
diplomaturas— no están en una tabla de solo licenciados. **Es correcto y no contradice ADR-005:**
son dos preguntas distintas — *¿en qué programa está esta persona?* (identidad, siempre) frente a
*¿qué declara UPeU ante SUNEDU?* (Calidad, solo licenciados). El DW mide lo mismo desde su lado:
2.253 de los 19.486 matriculados **no tienen P-code ni deben tenerlo** (Ley 30220 art. 46 y 54).

**`ADR-063`** (propuesto) afirma en *«Por qué no era opcional»* que *«ninguno de los 440 conceptos
del tesauro declara un predicado con el id de LAMB»*. **Verificado en vivo el 17-ago: son 188 IDs en
76 conceptos.** Sus puntos 2 (mudar el vínculo al tesauro) y 3 (LookupTable generada por SPARQL) ya
están hechos desde el 09-ago. Queda vivo el **punto 1** —el tesauro cubre todo el catálogo y la
licencia es propiedad del concepto—, que es justamente lo que da identidad a los 6.706 de ADR-062
**sin** meterlos en el denominador de Calidad. Conviene corregir esa sección antes de aprobarlo.

---

## Verificación

```bash
cd ~/proyectos/productos/iga/canonico && python3 scripts/generar-lookup-programas.py --dry-run
cd ~/proyectos/productos/vocbench/instituciones/upeu && python3 scripts/sprint4/10-auditar-tesauro.py
```

Tras desplegar, medir sobre los usuarios vivos y contrastar:

| Medida | Antes (17-ago) | Esperado después |
|---|---|---|
| Personas con P-code en LDAP | 22.767 | ≥ 22.767 |
| Personas con **varios códigos del mismo concepto** | **637** | **0** |
| Personas con códigos de programas distintos | 496 | 496 (no debe cambiar) |
| P-codes fuera del A4/A8 | 0 | 0 |

**Si la cobertura baja o aparecen códigos fuera del A4/A8, revertir.** Es la señal exacta que se
pasó por alto el 5-ago.
