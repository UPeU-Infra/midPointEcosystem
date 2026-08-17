# Prompt — MidPoint + LDAP: el P-code como código principal de programa

> Pegar al abrir una sesión nueva sobre `~/proyectos/productos/iga`.
> Estado **verificado en vivo el 17-ago-2026** contra PROD: MidPoint `192.168.15.166` (Postgres del
> contenedor `midpoint-midpoint_data-1`), LDAP `192.168.15.168`, VocBench vía SPARQL, Oracle LAMB.
> Sesiones hermanas: `koha/canonico/docs/PROMPT-pxx-koha.md` e `inout/canonico/docs/PROMPT-pxx-inout.md`.

---

## La regla (ADR-005 del tesauro)

UPeU identifica el programa académico por su **P-code / SEG-code** (`P30`, `SEG61`…) en **todos** sus
sistemas. El **código INEI queda solo para el repositorio de tesis**, donde SUNEDU/RENATI lo exige
como `renati.discipline`.

**Fuente de verdad, innegociable:** `/Users/alberto/Downloads/programas pxx upeu` — Formatos de
Licenciamiento **A4 y A8 2026-1**, **183 códigos** (121 `P*` del A4 + 72 `SEG*`/`P*` del A8, unión
183). Cualquier cosa distinta está mal.

### Tres cosas que hay que tener claras antes de tocar nada

**1 · El P-code no es la llave de unión.** 52 conceptos llevan **dos** códigos oficiales porque UPeU
recodifica por resolución (`SEG20`→`SEG61`, `SEG26`→`SEG44`), y **ambos están en el A8 2026-1**.
Para empalmar sistemas se usa **`sb:academicProgramUri`**, que no cambia. El P-code es lo que se
muestra, se reporta y se declara.

**2 · El P-code depende de la MODALIDAD.** El A4 lista **una fila por modalidad**: Administración es
`P04` presencial, `P05` semipresencial y `P95` a distancia — tres programas distintos ante SUNEDU.

**3 · Multivalor está bien; arrastrar códigos que ya no corresponden, no.** Una persona puede cursar
dos programas y un docente enseñar en varias escuelas. Lo que no puede es llevar `P04` **y** `P95`
por una sola matrícula.

---

## Estado verificado — no rehacer

### VocBench (repo del tesauro)
* **188 IDs de LAMB** declarados como `skos:notation` con datatype `urn:esther:id_programa_estudio`,
  en 76 conceptos vigentes, sobre 440 conceptos totales.
* **100 % de los `ID_PROGRAMA_ESTUDIO` con matrícula resuelven a un concepto vigente**
  (16.927/16.927 del semestre 2026-2, programas en alcance).
* **Los 15 EP-codes atrapados en conceptos deprecados, migrados al vigente.**
* Comprobación permanente en `10-auditar-tesauro.py`: *«IDs de Oracle atrapados en un concepto
  deprecado»*. Hoy da 0.

### Este repo, commiteado
* **`upeu/lookup-tables/program-pxx-byid.xml`** — OID `5d1c8a47-2b93-4f60-8e1a-7c4d9f0e6a25`,
  188 filas, `key` = `ID_PROGRAMA_ESTUDIO` → `value` = **un** P-code, el de la modalidad. Emite 103
  P-codes distintos, **todos** en el A4/A8 2026-1 (contrastado contra los xlsx).
* **`upeu/lookup-tables/program-resolver-lamb-byid.xml`** — 188 filas, 91 con EP-code.
* **`scripts/generar-lookup-programas.py`** — genera ambas desde VocBench. No editarlas a mano.
  `--dry-run` hoy: 188 IDs · 91 EP-code · 188 con P-code · 146 elegidos por modalidad.

### Desplegado en PROD — ya está hecho, no volver a proponerlo
* **Schema canónico `SciBack IGA … v1.4`, `m_object` version 33.** Ya lleva
  `academicProgramSuneduCode` como **PRINCIPAL desde 2026-08-09**, el INEI como *ALCANCE ACOTADO →
  `renati.discipline`*, más `liveProgramSuneduCodeStudent` y `academicProgramSourceId`.
  **No hay pendiente de despliegue de esquema ni, por tanto, de reinicio.**
* **El inbound que resuelve el P-code por ID ya corre:**
  `program-id-to-liveProgramSuneduCodeStudent` (id `3365`, resource **Oracle LAMB Estudiantes v199**)
  lee `PROGRAM_CODES` y resuelve contra `program-pxx-byid` (OID `5d1c8a47-…`), escribiendo en
  `extension/sb:liveProgramSuneduCodeStudent`. **22.227 users poblados, solo 377 multivalor.**
  No hace falta escribir ninguna función nueva: falta cambiar **quién lo consume**.

### LDAP producción — el P-code YA se publica
```
personas en ou=people                                    49.480
  de ellas, con scibackAcademicProgramSuneduCode         19.843
personas en ou=alumni con el mismo atributo               2.924
  → total en todo el DIT                                 22.767
P-codes distintos                                            91
de ellos, fuera del A4/A8 2026-1                              0   ✅
OUs de programa en ou=org (con EP-XXX + URI)                 26
```
⚠️ **Al medir, fijar la rama**: `-b "ou=people,…"` y `-b "ou=alumni,…"` dan cifras distintas; el
22.767 es el DIT entero. Los conteos de duplicados de abajo son **solo `ou=people`**.

---

## Lo que hay que cambiar

### 1 · Publicar la URI del programa en las personas — antes hay que ampliar el schema LDAP
Hoy `ou=people` lleva **solo cuatro** atributos `sciback*`: `scibackAcademicProgramSuneduCode`,
`scibackCampusCode`, `scibackDocumentNumber`, `scibackFacultyCode`. **La URI está únicamente en las
26 OUs de `ou=org`, y no es un olvido de mapping: es el schema.**

```
objectClasses: ( 1.3.6.1.4.1.47378.2.1 NAME 'upeuPerson' … MAY ( upeuDataQualityStatus $
  upeuReniecValidationDate $ isni $ scibackDocumentNumber $ scibackFacultyCode $
  scibackCampusCode $ scibackAcademicProgramSuneduCode ) )      ← NO tiene la URI
objectClasses: ( 1.3.6.1.4.1.47378.2.2 NAME 'scibackOrgUnit' … MAY ( … $
  scibackAcademicProgramUri $ … ) )                             ← la URI vive aquí
```

**Orden obligatorio:** (a) ampliar el `MAY` de `upeuPerson` con `scibackAcademicProgramUri` en
`cn=config` **de .168 y de .169** — el schema **no replica**; (b) recién entonces añadir el outbound
en el resource LDAP. Invertir el orden da error de objectClass violation en masa.

Consecuencias de no tenerlo, medidas:
* **InOut no puede resolver por URI** — tendría que empalmar por P-code, justo lo que la regla 1
  prohíbe. Su prompt asume que la URI estará ahí.
* **Desde fuera es imposible auditar de dónde salió un código**, porque no hay con qué unir una
  persona a su `ID_PROGRAMA_ESTUDIO`.

### 2 · Un P-code por MATRÍCULA — y la causa NO es la que parecía
De las **1.133 personas de `ou=people` con más de un P-code**:

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

**No es que el mapping pegue todas las modalidades.** `SUNEDU_CODE` llega **single-value** desde
Oracle (`MAX(ape.CODIGO_SUNEDU2) KEEP (DENSE_RANK LAST …)`): en cada corrida entra **un** valor. El
multivalor es **residuo acumulado**, porque `sunedu-code-to-academicProgramSuneduCode` es `strong`
sobre un target multivalor (`m_ext_item` id **302 = ARRAY**) y un strong **añade y nunca retira** —
el mismo patrón PM10 de las URIs obsoletas del 6-ago. Contraste en Postgres de PROD:

| | |
|---|---|
| users con `academicProgramSuneduCode` (302) | 22.227 · **1.134 multivalor** |
| users con `liveProgramSuneduCodeStudent` (300, por ID) | 22.227 · **377 multivalor** |
| **users con valores en 302 que 300 no produce (rancios)** | **771** |
| de ellos, multi en 302 con 300 single-value | **757** |

**La corrección tiene por tanto dos mitades, y la segunda es la que limpia:**

1. **Cambiar el consumidor.** `sb:academicProgramSuneduCode` deja de alimentarse de `SUNEDU_CODE`
   (`estudiantes.xml`, atributo `ri:SUNEDU_CODE`) y pasa a derivarse de
   `extension/sb:liveProgramSuneduCodeStudent`, que ya está poblado y ya resuelve por
   `ID_PROGRAMA_ESTUDIO` contra `program-pxx-byid`. Quien curse dos programas seguirá con dos
   códigos. ⚠️ El borrador `docs/pendientes/PATCH-inbound-suneduCode-byid.xml` **está obsoleto en un
   punto**: asume que `academicProgramSuneduCode` es single-value, y en PROD es ARRAY.
2. **Retirar lo rancio explícitamente.** Sin `range`/zero-set en el mapping, o sin un
   `PATCH replace` del item seguido de recompute, los **757** valores viejos se quedan donde están y
   la métrica no baja. Repetir aquí la limpieza sin arreglar el mapping es el error del 6-ago; hacer
   solo el mapping sin limpiar es el error simétrico.

De paso sube la cobertura: `CODIGO_SUNEDU2` resuelve el **73,18 %** de los 19.486 matriculados de
2026-2; la tabla del tesauro, el **88,44 %**.

### 3 · Restaurar `program-id-to-academicProgramCode` (opcional, medir antes)
Es el inbound retirado en PROD v184, que entonces hundió la cobertura del 40,9 % al 17,0 % — **7.268
estudiantes sin organización**. Con los EP-codes ya migrados, resolver por ID daría **74,99 %**. El
techo es 75 % porque los EP-code solo existen para pregrado.

---

## Reglas de ejecución

**Publicar en paralelo antes de retirar nada.** El `EP-XXX` sostiene hoy la asignación de
organización del bloque D6 de `user-template-student`; quitarlo en caliente reproduce la regresión
de los 7.268.

**Un mapping `strong` multivalor no retira valores.** Todo cambio de fuente sobre un item ARRAY
necesita su plan de retirada explícito (zero-set, `range`, o `PATCH replace` + recompute). Es el
patrón que ya costó dos sesiones en agosto.

**No renombrar DNs.** El DN codifica el EP-code (`ou=ep-com,ou=8,ou=org,…`); moverlos rompe
`memberOf`, ACLs y toda referencia por DN sin ganar nada — el DN es un handle opaco.

**LDAP:** el schema va en `cn=config`, que **NO replica** → aplicar en **.168 y .169**. Los datos sí
replican → aplicarlos en **un solo nodo**. Ver `upeu/ldap/rims-iga-contract/README.md`.

**Resources: nunca `PUT`, siempre `PATCH`** del elemento concreto — ver
`docs/runbooks/NUNCA-PUT-resources-schema-cache.md`. Y antes de ejecutar en PROD,
`docs/runbooks/PROTOCOLO-PRE-EJECUCION-PROD.md`.

---

## Sobre los dos ADR recientes

**`ADR-062`** (aplicado en PROD, schema v32 → hoy v33, resource v199) publica
`academicProgramSourceId` siempre, resuelva o no a P-code, porque 6.706 estudiantes —Inglés, CEPRE,
Conservatorio, diplomaturas— no están en una tabla de solo licenciados. **Es correcto y no
contradice ADR-005:** son dos preguntas distintas — *¿en qué programa está esta persona?* (identidad,
siempre) frente a *¿qué declara UPeU ante SUNEDU?* (Calidad, solo licenciados). El DW mide lo mismo
desde su lado: 2.253 de los 19.486 matriculados **no tienen P-code ni deben tenerlo** (Ley 30220
art. 46 y 54).

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

Duplicados en LDAP (fijar la rama; clasificar cruzando `program-pxx-byid` con
`program-resolver-lamb-byid` por `ID_PROGRAMA_ESTUDIO`):

```bash
source ~/.secrets/ldap-upeu.env
ldapsearch -x -LLL -o ldif-wrap=no -H "ldap://$LDAP_PROD_HOST:$LDAP_PORT" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASS" -b "ou=people,$LDAP_BASE_DN" "(scibackAcademicProgramSuneduCode=*)" dn scibackAcademicProgramSuneduCode
```

Rancios en MidPoint (302 = `academicProgramSuneduCode`, 300 = `liveProgramSuneduCodeStudent`;
confirmar los ids en `m_ext_item` antes de usarlos):

```sql
with u as (select oid, ext->'302' p, ext->'300' l from m_user where ext ? '302' and ext ? '300')
select count(*) from u where exists (select 1 from jsonb_array_elements_text(p) x
  where not exists (select 1 from jsonb_array_elements_text(l) y where y = x));
```

| Medida | Antes (17-ago) | Esperado después |
|---|---|---|
| Personas con P-code en `ou=people` | 19.843 | ≥ 19.843 |
| Personas con P-code en todo el DIT | 22.767 | ≥ 22.767 |
| **Users con valores rancios (302 ∉ 300)** | **771** | **0** |
| Personas de `ou=people` con **varios códigos del mismo concepto** | **637** | **0** |
| Personas con códigos de programas distintos (`ou=people`) | 496 | ≈ 377–496 — **medir, no asumir** |
| P-codes fuera del A4/A8 | 0 | 0 |

⚠️ El 496 **no es invariante**: el resolver por ID solo ve **377** dobles matrículas, así que parte de
esos 496 puede ser residuo también. Medir la diferencia antes de declararla defecto o correcta. Y los
**57 multivalor de `ou=alumni`** (19 del mismo concepto) llegan por el canal Egresados: este cambio
no los toca.

**Si la cobertura baja o aparecen códigos fuera del A4/A8, revertir.** Es la señal exacta que se
pasó por alto el 5-ago.
