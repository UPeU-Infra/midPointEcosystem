# Alumnos de Juliaca asignados a la Biblioteca de Lima

**26-ago-2026 · para la sesión de MidPoint · solo diagnóstico, no aplicar cambios**

## Contexto

En Koha (recurso **«Koha ILS UPeU consolidado»**, OID `e10a539a-cb7f-4c72-a19f-60f7f62e4b96`)
tres alumnos aparecen asignados a la Biblioteca de Lima (`BUL`) cuando estudian en Juliaca.
El personal de circulación de Juliaca no puede atenderlos, porque cada sede solo alcanza a sus
propios usuarios.

Lo reportó **Walter (CRAI Juliaca)** el 26-ago-2026 y confirmó que **son alumnos de Juliaca**.

## Los tres casos

El `name` en MidPoint es el **código de alumno**, no el DNI.

| OID | `name` | Nombre | `campusStudent` | `locality` |
|---|---|---|---|---|
| `29a3ad68-c3b7-4096-917d-7201c49f1f09` | 202212553 | Fray Ronaldo Adco Quispe | LIMA | JULIACA |
| `af8e697c-d170-4f3a-80a0-22a2b99d63dc` | 202312727 | Brayan Anthonny Calla Huamán | LIMA | JULIACA |
| `f393acd5-a512-4d88-8f7f-002211939c59` | 202411784 | Evelin Yolanda Condori Hancco | LIMA | JULIACA |

En Koha son `borrowernumber` 18500, 24042 y 26862, los tres con `branchcode = BUL`.

## Qué hace hoy el sistema

El mapping **`library-id-outbound`** del atributo `ri:library_id` (strength **strong**) resuelve
la sede en este orden:

```groovy
def cs = campusStudent      // 1º
def cw = campusWorker       // 2º
def ce = extensión 'campus' // 3º
def loc = locality          // 4º
// …y traduce: LIMA→BUL, JULIACA→BUJ, TARAPOTO→BUT, CIA→CIA
```

Como `campusStudent` dice **LIMA**, gana Lima y `locality` **nunca se llega a mirar**.

## Lo que necesito

1. **Confirma el diagnóstico** leyendo el mapping **desplegado**, no el del repo — pueden diferir.

2. **De dónde viene `campusStudent`.** Qué mapping *inbound* lo alimenta y desde qué columna de
   Oracle LAMB. Necesito saber si corregirlo en MidPoint aguanta o lo revierte el siguiente
   recálculo desde el origen.

   > Ya nos pasó con `emailAddress`: se puso a mano, un `reconcile` lo borró de MidPoint **y**
   > de Koha, porque el origen mandaba. No quiero repetirlo.

3. **Mide el alcance.** Cuántos usuarios tienen `campusStudent` distinto de `locality`.
   - Si son tres → se corrige en Registros Académicos y punto.
   - Si son cientos (programas semipresenciales o a distancia) → es una decisión de política,
     no un error de datos.

4. **Evalúa si el mapping debería cambiar.** Opción a discutir: usar `locality` como desempate
   cuando difiera de `campusStudent`. **No lo apliques.** Dime qué se rompería y a cuántas
   personas afectaría — cambiar un mapping `strong` reasigna sedes en masa.

## Restricciones

- **No modifiques nada sin decírmelo antes.** Solo diagnóstico y propuesta.
- Si propones parchear el recurso, reemplaza el **`<outbound>` completo**; apuntar a
  `expression/script/code` devuelve HTTP 500
  (`The PrismProperty cannot be created because PrismPropertyImpl with the same name exists (expression)`).
- La API REST cuelga de **`/midpoint/ws/rest`**, no de `/ws/rest`.
- Credenciales en `~/.secrets/midpoint-upeu.env`; la contraseña es **`MIDPOINT_ADMIN_PASS`**
  (no `..._PASSWORD`).
- El IGA está **en producción** y hay más sistemas colgando de él. Nada de cambios de modelo
  sin analizar el impacto.

## Mi hipótesis — verifícala o túmbala

El dato está mal en LAMB y la corrección es de **Registros Académicos**, no de MidPoint.

Pero si resulta que hay muchos alumnos de programas de Lima estudiando en filiales, entonces el
modelo necesita distinguir **campus del programa** de **sede de atención**, que no son lo mismo.
Eso ya no es un bug: es una pieza que falta.
