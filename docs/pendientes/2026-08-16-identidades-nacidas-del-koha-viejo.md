# 26 identidades que nacieron del Koha viejo — sin ID_PERSONA, sin carné y fuera de toda reconciliación

## Cómo se llegó aquí

Tirando del hilo de los `linkRef` que quedaban hacia el resource `Koha ILS` viejo
(`9b5a7c81`, archivado el 19-jul). De las **495 personas** que aún lo enlazan, **172 están
activas**; y de esas:

| | |
|---|---|
| Tienen carné en el Koha consolidado (solo les sobra el vínculo viejo) | **38** |
| Sin carné, pero son `alum` — **correcto**, los egresados no reciben Koha | **128** |
| **Sin carné debiendo tenerlo** | **6** (1 staff + 5 estudiantes) |

Al mirar esos 6 apareció algo más grande: **26 patrons del Koha consolidado no tienen
`cardnumber`** (de 33.717 en total), y los 6 estaban dentro.

## La cadena causal, medida entera

`cardnumber` se alimenta de un único sitio (`koha-upeu.xml`, `cardnumber-outbound`, strong):

```xml
<source><path>$focus/extension/sciback:externalSystemId</path></source>
```

`externalSystemId` es el **ID_PERSONA del MDM**, y llega por inbound desde Oracle. Entonces:

1. **Los 26 no tienen shadow de NINGUNA fuente Oracle** — ni Estudiantes, ni Trabajadores, ni
   Egresados. Verificado en `m_ref_projection` contra los tres resources.
2. Sin origen en Oracle → **`externalSystemId` nulo** en los 26.
3. Sin `externalSystemId` → **`cardnumber` nulo** → patron incapaz de prestar.
4. Y sin fila en ninguna fuente, **ninguna reconciliación los procesa**: no fallan, son
   invisibles. Se quedan `active` con lo que traían.

## De dónde salieron

| Creadas | Canal | n |
|---|---|---|
| 2026-05-27 | `reconciliation` | 20 |
| 2026-06-05 | `import` | 6 |

Las creó MidPoint **desde el Koha viejo**: aquel resource daba de alta users a partir de
patrons del ILS. Son identidades **nacidas del sistema equivocado** — al revés del principio
del IGA, donde Oracle es la fuente autoritativa y Koha un destino.

Encaja con la deuda que quedó anotada el 20-jul como *"22 bloqueados por shadows huérfanos del
Koha viejo archivado (patrón nuevo, pendiente limpieza)"*: es la misma familia, ahora medida y
explicada.

## Lo que NO hay que hacer

**Recomputarlos para "arreglarles" el carné.** Se probó con uno (`202613206`): el recompute le
creó el patron el 16-ago —`student`, `BUL`, vence 2027-08-16— pero **sin `cardnumber`**, igual
que los otros 25, porque la persona no tiene ancla. Un alta así no resuelve nada real.

## Lo que hace falta

Determinar, para cada uno de los 26, cuál de estos tres casos es:

1. **Está en Oracle con otro código** → correlacionarlo; recupera `ID_PERSONA` y carné.
2. **Estuvo y ya no** → darlo de baja; hoy sigue `active` por inercia.
3. **Nunca estuvo** → identidad que solo existió en la biblioteca. Decisión de producto: darle
   un origen legítimo o retirarla. Un IGA no debería sostener identidades que su fuente
   autoritativa desconoce.

La consulta está redactada como **encargo B** en
[`docs/prompts/2026-08-15-sede-trabajador-oracle.md`](../prompts/2026-08-15-sede-trabajador-oracle.md),
con los 26 códigos listos.

## Nota sobre los `linkRef` al Koha viejo

Las 495 referencias al resource archivado son deuda aparte y **hoy no cuestan nada**: sus
operaciones pendientes ya se limpiaron (ver
[`2026-08-16-operaciones-pendientes-huerfanas.md`](2026-08-16-operaciones-pendientes-huerfanas.md))
y el recurso no se procesa. Lo natural es retirarlas con la purga de esa instancia, no con una
limpieza aparte.
