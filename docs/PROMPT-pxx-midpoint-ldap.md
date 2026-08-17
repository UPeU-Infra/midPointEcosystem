# Prompt — MidPoint + LDAP: el P-code como código principal (actualizado 17-ago-2026)

> Pegar al abrir una sesión nueva sobre `~/proyectos/productos/iga`.
> **Sustituye la versión del 09-ago**, que quedó desfasada: MidPoint avanzó mucho entre medias
> (ADR-062 aplicado, ADR-063 propuesto) y **dos de sus premisas ya no son ciertas**.
> Sesiones hermanas: `koha/canonico/docs/PROMPT-pxx-koha.md` e `inout/canonico/docs/PROMPT-pxx-inout.md`.

---

## Lo primero: dos correcciones a `ADR-063`

`ADR-063` está **propuesto**, y su sección *«Por qué no era opcional»* afirma:

> «Ninguno de los 440 conceptos del tesauro declara un predicado con el id de LAMB: la
> correspondencia vive **solo** en la LookupTable de MidPoint.»

**Eso dejó de ser cierto el 09-ago**, cinco días antes de escribirse el ADR.
**Verificado en vivo contra VocBench el 17-ago-2026** (SPARQL sobre el grafo, no sobre el export):

```
conceptos totales del tesauro  : 440      ← el ADR cita bien este número
IDs de LAMB en el tesauro      : 188 sobre 76 conceptos   ← el ADR dice que son 0
```


| Punto de ADR-063 | Estado real |
|---|---|
| **2.** «El vínculo `ID_PROGRAMA_ESTUDIO` → concepto se muda al tesauro» | ✅ **HECHO**. **188 IDs** declarados en VocBench como `skos:notation` con datatype `urn:esther:id_programa_estudio`, repartidos en 76 conceptos vigentes. Commits `12a6e19` y `4d9a297` del repo del tesauro. |
| **3.** «La LookupTable pasa a ser artefacto generado por SPARQL» | ✅ **HECHO**. `scripts/generar-lookup-programas.py` la genera desde VocBench. La cabecera de ambas tablas dice *«ARTEFACTO GENERADO — no editar a mano»*. |
| **1.** «El tesauro cubre todo programa de matrícula; la licencia es propiedad, no condición» | ⬜ **PENDIENTE** — y es el único punto real que queda. |

**El diagnóstico del ADR sigue siendo correcto; lo que estaba desfasado era el inventario.**
Conviene corregir esa sección antes de aprobarlo, o quedará justificando un trabajo ya hecho.

---

## La regla (ADR-005 del tesauro)

UPeU identifica el programa por su **P-code / SEG-code** en todos sus sistemas. El **INEI queda
solo para el repositorio de tesis** (SUNEDU/RENATI lo exige como `renati.discipline`).

**Fuente de verdad, innegociable:** `/Users/alberto/Downloads/programas pxx upeu` — Formatos A4/A8
2026-1, **183 programas**. Cualquier cosa distinta está mal, incluido `CODIGO_SUNEDU2` de Oracle.

**El P-code NO es la llave de unión.** 52 conceptos llevan dos códigos oficiales por recodificación
vía resolución (`SEG20`→`SEG61`), **ambos en el A8 2026-1**. Para empalmar se usa
`sb:academicProgramUri`. El P-code es lo que se muestra, se reporta y se declara.

**El P-code depende de la MODALIDAD.** El A4 lista una fila por modalidad: Administración es `P04`
presencial, `P05` semipresencial, `P95` a distancia. La tabla generada ya lo resuelve cruzando con
`DAVID.ACAD_PROGRAMA_ESTUDIO.ID_MODALIDAD_ESTUDIO` (146 de 188 filas eligen por modalidad).

---

## Lo que ya está en el repo, commiteado — no rehacer

* **`upeu/lookup-tables/program-pxx-byid.xml`** — OID `5d1c8a47-2b93-4f60-8e1a-7c4d9f0e6a25`,
  **188 filas**, `key` = `ID_PROGRAMA_ESTUDIO` → `value` = P-code vigente por modalidad. Los 103
  P-codes que emite están **todos** en el A4/A8.
* **`upeu/lookup-tables/program-resolver-lamb-byid.xml`** — regenerada: 186→**188 filas**,
  82→**91 con EP-code**.
* **`scripts/generar-lookup-programas.py`** — el generador.
* **`canonical/schemas/sciback-person-v1.0.xml`** — `academicProgramSuneduCode` pasó de *LEGACY* a
  **PRINCIPAL**; `academicProgramIneiCode` a **metadato de disciplina para tesis**.

En VocBench (repo del tesauro), también hecho y verificado:
* **100 % de los `ID_PROGRAMA_ESTUDIO` con matrícula resuelven a un concepto vigente**
  (16.927/16.927 del semestre 2026-2, programas en alcance).
* **Los 15 EP-codes atrapados en conceptos deprecados, migrados al vigente.** Ese era el bloqueo
  literal del inbound retirado en PROD v184.
* Comprobación permanente en el auditor: *«IDs de Oracle atrapados en un concepto deprecado»*.

---

## Lo que falta

### 1. Desplegar a MidPoint lo que está en el repo
Las 2 LookupTables y el esquema. ⚠️ Un cambio de esquema **suele exigir reinicio** — confirmarlo
con Alberto antes.

### 2. Cambiar la fuente del P-code — el punto con más valor
`sb:academicProgramSuneduCode` se alimenta hoy de la columna `SUNEDU_CODE` (→ `CODIGO_SUNEDU2`).
**Debe pasar a `program-pxx-byid`.** Medido sobre los 19.486 matriculados de 2026-2:

| Fuente | Cobertura | Errores |
|---|---|---|
| Oracle `CODIGO_SUNEDU2` | 73,18 % | **139 alumnos con el código equivocado** (Oracle dice `P14`, el A4 dice `P97`) |
| **LookupTable del tesauro** | **88,44 %** | **0** |

Hace falta una función nueva en `canonical/function-libraries/sb-program-resolver-byid.xml`
(OID `3f8b6c04-…`), copiando `resolveProgramCodeById` pero apuntando al OID `5d1c8a47-…`.

### 3. Restaurar `program-id-to-academicProgramCode`
El inbound retirado en PROD v184. Entonces hundía la cobertura del 40,9 % al 17,0 % — **7.268
estudiantes sin organización**. **Ya no**: con los EP-codes migrados, resolver por ID da **74,99 %**.
El techo es 75 % porque los EP-code solo existen para pregrado.

### 4. LDAP — ~~publicar el P-code~~ **YA ESTÁ PUBLICADO**

⚠️ **Corrección: esto ya se hizo.** Medido en PROD el 17-ago-2026 (`192.168.15.168`):

```
personas en ou=people                            49.480
personas con scibackAcademicProgramSuneduCode    22.767   ← el P-code YA viaja por LDAP
P-codes distintos                                    91
de ellos, fuera del A4/A8 2026-1                      0   ✅ todos válidos
OUs de programa en ou=org                            26   (siguen con EP-XXX + URI)
```

Lo que queda en LDAP no es publicar el código, sino dos huecos:

* **Las personas NO llevan `academicProgramSourceId` ni la URI del programa.** Los únicos atributos
  `sciback*` en `ou=people` son `scibackAcademicProgramSuneduCode`, `scibackCampusCode`,
  `scibackDocumentNumber` y `scibackFacultyCode`. Consecuencias: **InOut no puede resolver por URI**
  —tendría que empalmar por P-code, justo lo que la regla prohíbe— y **desde fuera es imposible
  auditar de dónde salió el código**, porque no hay con qué unir a Oracle.
* **NO renombrar DNs.** El DN codifica el EP-code (`ou=ep-com,ou=8,ou=org,…`); moverlos rompe
  `memberOf`, ACLs y toda referencia por DN sin ganar nada.
* Schema en `cn=config` **no replica**: aplicar en **.168 y .169**. Datos sí replican: **un nodo**.

### 4b. La pregunta que hay que responder primero: ¿de dónde sale ese P-code?

**Es lo que decide si el paso 2 sigue haciendo falta.** Desde fuera no se puede concluir, pero el
test es exacto — la discrepancia conocida entre las dos fuentes:

| | Oracle `CODIGO_SUNEDU2` | Tabla del tesauro |
|---|---|---|
| `id_programa_estudio` **320** y **146** | `P14` (Lingüística e Inglés) | **`P97`** (Inglés y Español) |

En LDAP hoy conviven **249 personas con `P14`** y **186 con `P97`** — mezclado, y ambos códigos son
programas reales del A4, así que el recuento por sí solo no distingue. **Hay que mirar a qué
personas** les tocó cada uno: si los alumnos de los ids 320/146 llevan `P14`, la fuente es Oracle y
el paso 2 sigue pendiente con 139 fichas equivocadas. Si llevan `P97`, ya se hizo.

### 5. Regla de transición
**Publicar en paralelo antes de retirar nada.** El `EP-XXX` sostiene hoy la asignación de
organización; quitarlo en caliente reproduce la regresión de los 7.268.

---

## Sobre ADR-062 — no hay conflicto, y conviene decirlo

`ADR-062` (aplicado en PROD, schema v32 / resource v199) publica `academicProgramSourceId` siempre,
resuelva o no a P-code, porque **6.706 estudiantes** —Inglés, CEPRE, Conservatorio, diplomaturas—
no tienen entrada en una tabla de solo licenciados.

**Es correcto y complementa, no contradice.** Son dos preguntas distintas:

* *¿en qué programa está esta persona?* → identidad → **siempre**, `academicProgramSourceId`;
* *¿qué declara UPeU ante SUNEDU?* → Calidad → **solo licenciados**, el P-code.

El DW mide lo mismo desde su lado y llega al mismo sitio: sobre los 19.486 matriculados de 2026-2,
**2.253 no tienen ni P-code ni deben tenerlo** — idiomas, CEPRE y Conservatorio no son programas
licenciados (Ley 30220 art. 46 y 54) y **su cobertura correcta ante SUNEDU es 0 %**.

Por eso el punto 1 de ADR-063 —el tesauro cubre todo el catálogo, la licencia es una propiedad— es
la solución limpia: da identidad a los 6.706 **sin** meterlos en el denominador de Calidad.

---

## Verificación

```bash
cd ~/proyectos/productos/iga/canonico && python3 scripts/generar-lookup-programas.py --dry-run
cd ~/proyectos/productos/vocbench/instituciones/upeu && python3 scripts/sprint4/10-auditar-tesauro.py
```

Tras desplegar, medir la cobertura real de `sb:academicProgramSuneduCode` y
`sb:academicProgramCode` sobre los usuarios vivos y contrastarla con **88,44 %** y **74,99 %**.
**Si sale por debajo, revertir** — es la señal exacta que se pasó por alto el 5-ago.
