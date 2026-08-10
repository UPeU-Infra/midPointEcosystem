# Prompt — MidPoint + LDAP: el P-code pasa a ser el código principal de programa

> Pegar al abrir una sesión nueva sobre `~/proyectos/productos/iga`.
> Sesiones hermanas: `koha/canonico/docs/PROMPT-pxx-koha.md` e
> `inout/canonico/docs/PROMPT-pxx-inout.md`. **Esta va primero**: las otras dos
> consumen lo que aquí se publique.

---

## La regla

UPeU identifica el programa académico por su **P-code / SEG-code** (`P30`, `SEG61`…) en
**todos** sus sistemas. El **código INEI queda solo para el repositorio de tesis**, donde
SUNEDU/RENATI lo exige como `renati.discipline`.

Decisión: [`ADR-005`](../../../vocbench/instituciones/upeu/docs/decisiones/ADR-005-pxx-identificador-institucional.md)
del tesauro (09-ago-2026). Invierte la designación vigente desde el 13-jun-2026, que hacía
canónico al INEI.

### Fuente de verdad — innegociable

**`/Users/alberto/Downloads/programas pxx upeu`** — Formatos de Licenciamiento **A4 y A8
2026-1**, los que UPeU presentó y tiene validados ante SUNEDU. **183 programas.**
*Cualquier cosa distinta de eso está mal*, incluido `DAVID.ACAD_PROGRAMA_ESTUDIO.CODIGO_SUNEDU2`.

### Dos trampas que ya costaron caro

1. **El P-code NO es la llave de unión entre sistemas.** 52 conceptos llevan **dos** códigos
   oficiales porque UPeU recodifica por resolución (`SEG20`→`SEG61`, `SEG26`→`SEG44`) y **ambos
   están en el A8 2026-1**. Para empalmar sistemas se usa `sb:academicProgramUri` (la URI de
   VocBench, estable). El P-code es lo que se muestra, se reporta y se declara.
2. **El A4 lista una fila por MODALIDAD.** Administración es `P04` presencial, `P05`
   semipresencial y `P95` a distancia — tres programas ante SUNEDU. El código correcto depende de
   `DAVID.ACAD_PROGRAMA_ESTUDIO.ID_MODALIDAD_ESTUDIO` (1=Presencial, 2=Semipresencial,
   13=A Distancia). Emitir uno solo por concepto le pone a un alumno presencial el código de a
   distancia.

---

## Lo que ya está hecho (09-ago-2026) — no rehacer

### En VocBench
* Los **183 P-codes** del A4/A8 están en el tesauro, y **ninguno inventado** (0 códigos que no
  estén en los formatos).
* **Todos los `ID_PROGRAMA_ESTUDIO` con matrícula resuelven a un concepto vigente: 100 %**
  (16.927/16.927 identidades del semestre 2026-2, programas en alcance). Antes era 94,56 %.
  Se liberaron 17 IDs que colgaban solo de conceptos deprecados —incluido Medicina Humana, 757
  alumnos— con `21-anclar-medicina-humana.py` y `22-cerrar-ids-oracle-pendientes.py`.
* **Los 15 EP-codes atrapados se migraron al concepto vigente** con `23-migrar-ep-codes.py`.
  Ese era el bloqueo declarado en `estudiantes.xml` (*«Rehacer por ID solo cuando VocBench migre
  los 15 EP-codes»*). Queda fuera `EP-IIE`: programa extinto, no está en el A4 y tiene 0 alumnos.
* El auditor `10-auditar-tesauro.py` gana la comprobación **«IDs de Oracle atrapados en un
  concepto deprecado»**. Hoy da 0. **Correrla antes de dar por bueno cualquier cambio.**

### En este repo (`iga/canonico`), commiteado y pusheado
* **`scripts/generar-lookup-programas.py`** — genera las LookupTables desde VocBench. Las tablas
  dejan de mantenerse a mano.
* **`upeu/lookup-tables/program-pxx-byid.xml`** — **NUEVA**, OID `5d1c8a47-2b93-4f60-8e1a-7c4d9f0e6a25`.
  188 filas · `key` = `ID_PROGRAMA_ESTUDIO` · `value` = P-code vigente **elegido por modalidad**.
  Los 103 P-codes que emite están todos en el A4/A8.
* **`upeu/lookup-tables/program-resolver-lamb-byid.xml`** — regenerada:
  186→**188 filas** y 82→**91 con EP-code**, gracias a la migración de EP-codes.
* **`canonical/schemas/sciback-person-v1.0.xml`** — `academicProgramSuneduCode` deja de ser
  *LEGACY* y pasa a **PRINCIPAL**; `academicProgramIneiCode` pasa a **metadato de disciplina para
  tesis**. Solo cambian las anotaciones, no la estructura.

**Nada de esto se ha cargado a MidPoint todavía.**

---

## La tarea

### 1. Desplegar los objetos aditivos
Cargar a MidPoint las 2 LookupTables y el esquema. No cambian comportamiento por sí solos.
⚠️ Un cambio de esquema en MidPoint **suele exigir reinicio** — confirmarlo con Alberto antes.

### 2. Cambiar la fuente del P-code
Hoy `sb:academicProgramSuneduCode` se alimenta de la columna `SUNEDU_CODE` del resource
Estudiantes, que viene de `CODIGO_SUNEDU2`. **Debe pasar a derivarse de `program-pxx-byid`.**

Medido sobre los 19.486 matriculados de 2026-2:

| Fuente | Cobertura | Errores |
|---|---|---|
| Oracle `CODIGO_SUNEDU2` | 73,18 % | **139 alumnos con el código equivocado** (Oracle dice `P14`, el A4 dice `P97`) |
| **LookupTable del tesauro** | **88,44 %** | **0** |

Oracle además lo deja vacío en 2.972 identidades que el tesauro sí resuelve.

Hace falta una función nueva en
`canonical/function-libraries/sb-program-resolver-byid.xml` (OID `3f8b6c04-91a7-4d52-b8e3-2c50f9a1d7b6`),
p. ej. `resolveProgramSuneduCodeById`, copiando el patrón de `resolveProgramCodeById` pero
apuntando al OID `5d1c8a47-…`.

### 3. Restaurar `program-id-to-academicProgramCode`
Es el inbound retirado en **PROD v184** el 5-ago. Entonces hundía la cobertura del 40,9 % al
17,0 % y dejaba **7.268 estudiantes sin organización** (el bloque D6 de `user-template-student`
asigna la Org del programa desde `academicProgramCode`). **Ya no**: con los EP-codes migrados,
resolver por ID da **74,99 %**. El techo es 75 % porque los EP-code solo existen para pregrado.

### 4. LDAP — publicar el P-code
Estado verificado en PROD (`192.168.15.168`): `ou=org` tiene **26 OUs de programa**, con
`scibackAcademicProgramCode` = `EP-XXX` y `scibackAcademicProgramUri` con la URI de VocBench —
**25 de 26 resuelven a un P-code** (la que no, es el programa extinto `EP-IIE`).

* **NO renombrar DNs.** El DN codifica el EP-code (`ou=ep-com,ou=8,ou=org,dc=upeu,dc=edu,dc=pe`).
  Mover entradas rompe `memberOf`, ACLs y toda referencia por DN sin ganar nada: el DN es un
  handle opaco.
* **Atributo nuevo y MULTI-VALUE** para el P-code — `scibackAcademicProgramCode` es `SINGLE-VALUE`
  y semánticamente es el EP. Multi-valor por los 52 recodificados.
* El schema va en `cn=config`, que **NO replica**: aplicar en **.168 y .169**. Los datos sí
  replican: aplicarlos en **un solo nodo**. Ver
  `upeu/ldap/rims-iga-contract/README.md`.

### 5. Regla de transición
**Publicar en paralelo antes de retirar nada.** El `EP-XXX` sostiene hoy la asignación de
organización; quitarlo en caliente reproduce la regresión de los 7.268.

---

## Verificación

```bash
# 1. Las tablas siguen coincidiendo con la fuente de verdad
cd ~/proyectos/productos/iga/canonico && python3 scripts/generar-lookup-programas.py --dry-run

# 2. El tesauro sigue sano (0 IDs atrapados)
cd ~/proyectos/productos/vocbench/instituciones/upeu && python3 scripts/sprint4/10-auditar-tesauro.py
```

Tras desplegar, medir la cobertura real de `sb:academicProgramSuneduCode` y
`sb:academicProgramCode` sobre los usuarios vivos y contrastarla con 88,44 % y 74,99 %.
**Si sale por debajo, revertir**: es la señal exacta que se pasó por alto el 5-ago.

## Cuando termine
Avisar a las sesiones de **Koha** e **InOut**: ambas esperan que el P-code viaje por LDAP.
