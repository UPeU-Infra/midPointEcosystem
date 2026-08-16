# El `existence` de LDAP congelaba a las personas vivas — corregido el 15-ago-2026

## El defecto

El mapping de existencia del objectType `account/default` del resource LDAP
(`7b4e1c2d-…`, `outbound id=472`) nació el 4-ago para cerrar el leaver gap. Era `strong`,
con `<expression><value>true</value></expression>` y una **`<condition>` que solo era cierta
para las bajas**:

```groovy
def st = focus?.activation?.effectiveStatus?.toString()?.toLowerCase()
def lc = focus?.lifecycleState?.toString()?.toLowerCase()
return (st in ['disabled', 'archived']) || (lc in ['archived', 'suspended'])
```

Para una persona **viva** esa condición da `false` y el mapping **no devuelve ningún valor**.
Ahí se parte en dos casos:

| Situación | Qué pasa |
|---|---|
| Persona viva **con** assignment | La cuenta ya está legalizada por el assignment; MidPoint no necesita la respuesta del mapping → funciona. Es el 99 % del padrón, y por eso el defecto pasó desapercibido. |
| Persona viva **sin** assignment | Nadie legaliza la cuenta y el mapping calla → `Activation existence expression resulted in no values` → **se aborta el procesamiento entero de esa persona**. |

Y el fallo se realimenta: la persona se queda en `draft`/`archived`, con **0 assignments** y
sin `primaryAffiliation`… que es exactamente la condición que provoca el fallo. Sin
assignments porque falla, y fallando porque no tiene assignments.

## Cómo se probó

Dos sondas temporales en PROD, ambas revertidas:

1. **`log.info` dentro de la condición** → **no imprimió nada**, ni en el caso que falla ni en
   un control que funciona. *`log` no sirve para diagnosticar mappings de resource; no
   concluir de su silencio que el mapping no se evalúa.*
2. **Retorno forzado para un único usuario** (`if (focus?.name?.orig == '200110414') return
   true`) → esa persona pasó de `archived`/`disabled`/0 assignments a **`active`, `enabled`,
   4 assignments**, con su entrada `uid=200110414,ou=people` habilitada y
   `eduPersonPrimaryAffiliation: student` verificado por `ldapsearch`. **Era un estudiante
   vivo con matrícula, no una baja.**

## Alcance medido (15-ago, antes de corregir)

| | |
|---|---|
| Fichas congeladas: `draft`/`archived`, 0 assignments, con entrada en `ou=people` | **8.412** |
| …con `primaryAffiliation` sin calcular | 8.412 (todas) |
| Users `active` sin ningún assignment | **0** |
| Fallos de la recon de Estudiantes atribuibles a esto | **375 de 399** |

## La corrección (PROD v240)

Se retira la `<condition>`. El `existence` responde **`true` siempre**: la entrada de
`ou=people` no desaparece nunca y las bajas se materializan por
`administrativeStatus=DISABLED` — coherente con el `<cap:delete>` que este resource tiene
**deshabilitado a nivel de recurso**.

> Ese `delete` cerrado importa para entender el diseño: aunque un mapping calcule "no debe
> existir", **MidPoint no puede borrar una entrada de este LDAP**. La barrera dura sigue en
> pie; la corrección no la toca.

## Resultado de los lotes controlados (madrugada del 16-ago)

Se desplegó por canal, no por grupos de personas: un recompute **no re-lee Oracle** (evalúa
sobre los shadows cacheados), así que quien debe recuperar afiliación viva solo la recupera
cuando la reconciliación de su canal lo procesa.

| Canal | Éxitos | Fallos | Antes | Desbloqueadas | Koha pico |
|---|---|---|---|---|---|
| Lote canario (20 personas) | 20 | **0** | — | 2 | — |
| Estudiantes | 29.526 | **26** | 399 | **358** | 2,94 |
| Trabajadores | 7.393 | **18** | — | **69** | 1,14 |
| Egresados | 31.253 | **63** | — | **0** | 0,74 |

Sobre `account/default`, `Activation existence expression resulted in no values` **desaparece
del log** en las tres corridas. Fichas congeladas en `ou=people`: **8.412 → 7.985**.

Que Egresados desbloquee **0** es lo correcto: ese canal no devuelve afiliación viva a nadie.

Los fallos que quedan son cola conocida y ajena a esto: duplicados de persona/patron,
`secondary_email` con más de un valor sobre un campo single-value, los `library_id` sin
campus (ver [`2026-08-12-sin-sede-origen.md`](2026-08-12-sin-sede-origen.md)), y Entra, que
es de solo lectura.

En la corrida de Trabajadores, **1.830 ex-trabajadores archivados perdieron sus assignments**:
es el leaver materializándose, y gracias a este cambio sus entradas se conservan
deshabilitadas en vez de quedar en el limbo.

## Lo que NO se ha hecho — fase 2

**La mudanza `ou=people` → `ou=alumni` al graduarse.** Hoy **1.598 egresados**
(`primaryAffiliation=alum`) figuran en las **dos ramas** a la vez. La regla que lo resolvería
es `if (baja) return true; return prim != 'alum'`, pero implica retirarlos de `ou=people`, y
eso exige:

1. decisión explícita, porque es un borrado en el directorio;
2. **re-habilitar `<cap:delete>`**, hoy cerrado — sin eso la regla ni siquiera podría
   ejecutarse;
3. simulación previa y lote canario verificado contra `ldapsearch`.

### La rama `alumni` tiene el mismo defecto, pero pequeño

El `existence` de `account/alumni` (`outbound id=473`) **conserva la condición vieja**, y la
corrida de Egresados confirma que falla por lo mismo: **80 apariciones del mensaje sobre
`account (alumni)`, 16 personas distintas**, 0 sobre `account/default`.

No ha llegado a formar el bucle circular que sí se dio en `people`: **congelados con shadow en
`ou=alumni` = 0**. Por eso no urge, pero la corrección es la misma y toca hacerla con la fase 2.

### Los dual-rama no crecieron

Tras las tres corridas siguen siendo **1.598** con `primaryAffiliation=alum` en ambas ramas —
el mismo número de antes del cambio. (El total de personas en las dos ramas es 1.871; los 273
restantes tienen otra afiliación y no se midieron antes del cambio, así que de esos no puede
afirmarse nada.)

## Trampas encontradas por el camino

- El valor de `primaryAffiliation` es **`alum`**, no `alumni`. Una primera medición del riesgo
  usó `'alumni'`, dio 0 en todo y era **inválida**: con el valor correcto salieron los 1.598.
- `m_shadow` no tiene `owneroid`; el vínculo user→shadow va por `m_ref_projection`.
- El contenedor de Postgres se llama `midpoint-midpoint_data-1`, no `midpoint_data`.
- Un shadow que apunta a `ou=people` **no garantiza** que la entrada exista en el LDAP real:
  de los 20 del canario, 18 no tenían entrada. Verificar siempre con `ldapsearch`, no con el
  shadow.
