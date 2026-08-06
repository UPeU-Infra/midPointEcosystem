# Protocolo de pre-ejecución en PROD — reglas destiladas de errores reales

**Vigente desde 2026-08-06.** Cada regla existe porque su ausencia causó un incidente concreto,
citado. No es teoría: es la lista de cheques que, aplicada, habría evitado cada uno.

Complementa [`NUNCA-PUT-resources-schema-cache.md`](NUNCA-PUT-resources-schema-cache.md) y el
blindaje de [`../ARQUITECTURA-ARBOL-ORGANIZATIVO.md`](../ARQUITECTURA-ARBOL-ORGANIZATIVO.md).

---

## R1 — Leer el MECANISMO, no muestrear el resultado

Una muestra prueba la muestra, no la regla. Antes de predecir el comportamiento de un mapping,
outbound o conector, **abrir y leer su código/config**, no inferirlo de ejemplos.

> *Incidente (6-ago):* afirmé «el DN de las OUs es plano» tras ver `ou=430,ou=org,…`. El outbound
> de `ri:dn` era **jerárquico** (apila ancestros de `OU_ARCH`); `ou=430` parecía plano solo porque
> sus ancestros se saltaban. Resultado: 62 OUs movidas en producción.

## R2 — Contrastar el plan contra los documentos rectores ANTES de ejecutar

Los ADR/documentos rectores son **entrada** de la ejecución, no solo salida del análisis. Si un
doc dice «excluir X del outbound», verificar contra la config real que X está excluido.

> *Incidente (6-ago):* D4 del documento rector decía «los nodos de la rama de sedes deben
> excluirse explícitamente del outbound `generic/ou`» — **escrito por mí ese mismo día** — y
> ejecuté el poblado sin contrastarlo contra el script.

## R3 — En lotes: imprimir la lista COMPLETA y leerla antes de ejecutar

El canario valida el **procedimiento**; no valida la **selección**. Son verificaciones distintas
y ambas son obligatorias. Todo lote se materializa en archivo, se inspecciona (extremos, conteos
por familia, elementos inesperados) y solo después se ejecuta.

> *Incidente (6-ago):* canario de 3 OK, y lancé el lote de 41 sin leer la lista — que incluía las
> 3 OUs de campus. `ou=sede-juliaca` y `ou=sede-tarapoto` fueron borradas (recuperadas).

## R4 — Filtros de texto sobre DN/paths: anclar y probar en SELECT antes de tocar

`LIKE '%ou=sede-%'` casa con `ou=sede-lima` **misma**, no solo con sus hijas. Anclar al
componente (`'%,ou=sede-%'`, o comparar profundidad) y ejecutar el filtro primero como consulta
de solo-lectura revisando qué devuelve.

## R5 — Toda predicción de riesgo lleva su medición previa

Prohibido «no pasará X» sin responder: *¿qué medición lo probaría?* — y hacerla ANTES. Si la
predicción no es medible, tratarla como incógnita y simular/canarear.

> *Incidentes (5 y 6-ago):* «cambiar el identifier es un cambio de metadato» (creó OUs duplicadas)
> y «el DN es plano» (movió 62 OUs). Ambas eran medibles en un minuto leyendo la config.

## R6 — Cambias N cosas ⇒ mides N cosas

Cada atributo/objeto tocado tiene su propia medición de impacto. Medir uno y extrapolar al resto
no es verificación.

> *Incidente (5-ago):* cambié `academicProgramUri` Y `academicProgramCode`; medí solo el primero.
> El segundo caía de 40,9 % a 17,0 % y dejaba a 7.268 estudiantes sin su organización (revertido).

## R7 — Un efecto no predicho en la simulación es una PREGUNTA, no una confirmación

Si el diff trae algo que el plan no anticipó, se investiga hasta explicarlo **antes** de aplicar.
«Es consecuencia lógica» sin verificar = el punto ciego clásico.

> *Incidente (5-ago):* la simulación marcó 260 cambios de `parentOrg`; los despaché como «efecto
> lateral del 1 %». Eran la señal de la regresión de `academicProgramCode`.

## R8 — Los códigos HTTP de MidPoint no son la verdad; Postgres sí

`240`/`250` son *handled error*: pueden aplicar el cambio, no aplicarlo, o aplicarlo a medias.
`204` en un PATCH de container puede ser NO-OP silencioso. Tras toda escritura: **verificar el
estado en `m_*` por Postgres** (o GET + parse), nunca fiarse del código.

## R9 — El orden es simular → leer el diff → canario → lote → verificar

Cada salto de etapa sin completar la anterior es donde nacieron los incidentes. La simulación
DESPUÉS del cambio (5-ago, sedes) o el lote sin canario de selección (6-ago) son la misma falla:
etapas fuera de orden.

---

## Por qué fallan estas reglas (la causa de fondo, para reconocerla)

Los errores de esta semana no fueron de conocimiento — cada regla ya se «sabía» — sino de
**sustituir medición por inferencia cuando hay inercia de éxitos y jornada larga**. La disciplina
de verificar se aplicaba a los RESULTADOS (después) y no a las PREMISAS (antes). Señales de
alarma: «es obvio que», «esto no dispara nada», «igual que el caso anterior». Cuando aparezcan,
parar y medir.
