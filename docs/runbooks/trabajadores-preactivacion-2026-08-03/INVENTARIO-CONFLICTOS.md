# Inventario de conflictos de identidad en PROD — 2026-08-04, tras la reactivación

**Respuesta corta a «¿están aislados todos los conflictos?»: NO.**
Lo de hoy resolvió el canal de Trabajadores. Queda bastante más, y una parte **no se había medido
nunca**.

---

## 1. Lo que SÍ está aislado ✅

| Conflicto | Nº | Estado |
|---|---|---|
| `DISPUTED` en Oracle LAMB Trabajadores | **3** | ✅ con caso de correlación abierto, 0 duplicados creados |

Los tres, con nombre:

| Shadow | Persona | Choca con |
|---|---|---|
| `000614192` | Luzirene Gomes de Alcantara | `00614192` (archived) — duplicado de origen en Oracle |
| `44528386f` | Katty Aracelly Porras Espinoza | `44528386` (archived) — duplicado de origen en Oracle |
| **`002558245`** | **Natalia Raquel Benavides Paredes** | `002558245` (archived, trabajadora) **y** `201810090` (active, estudiante) — **mismo documento `02558245`** |

> **`002558245` no estaba previsto.** No aparecía en el análisis de la simulación: es un acierto
> real del tier 4 desplegado hoy. Una persona con dos `User` y el mismo documento; al volver a
> aparecer su contrato, el guardarraíl abrió caso en vez de crear un tercer objeto. **Es la prueba
> en producción de que el guardarraíl hace lo que debe.**

## 2. Lo que NO está aislado 🔴

| Conflicto | Nº | Observación |
|---|---|---|
| **Dual-shadow LDAP** (`ou=people` + `ou=alumni`) | **283** | **todos con el `User` ACTIVO**. Ninguno tiene dos entradas en la misma OU (eso sí sería peor) |
| Casos de correlación **abiertos** | **105** | **102 abiertos desde mayo**, sin atender en 3 meses. Solo 3 son de hoy |
| `DISPUTED` en Entra ID | **32** | **NO los generó la corrida de hoy** (todos entre 07:31 y 15:42; la corrida fue 21:25). Los produce `recon-entra-id-daily`. Todos son cuentas **sin foco** en MidPoint → mismo gap de cobertura del 18-jul |
| Dual-shadow en **Koha** | 28 | |
| Dual-shadow en Entra ID | 9 | |
| Dual-shadow en Oracle LAMB Egresados | 2 | |
| `User` duplicados por `lambIdPersona` | **14 grupos** (6 con ambos activos) | Identificados: [`duplicados-identidad-midpoint.md`](duplicados-identidad-midpoint.md) |
| **`User` duplicados por documento** | **22 grupos** (3 con ambos activos) | 🔴 **Eje nunca medido antes.** No coincide con los 14: es otra población |
| Homónimos activos (`fullName` normalizado) | 32 grupos | El tier 4 los mandará a `disputed` si vuelven por el canal de Trabajadores |

Contexto: `UNMATCHED` = 182.411 y `UNLINKED` = 580, casi todo del lado de Entra ID — es el gap de
cobertura documentado el 18-jul, no conflictos de identidad propiamente dichos.

## 3. Lectura

**El canal de Trabajadores quedó limpio y con guardarraíl operativo.** Los tres conflictos vivos
están contenidos, con caso abierto y sin haber creado ningún duplicado.

**Fuera de ese canal, no.** Lo más relevante por volumen y por ser gente activa:

1. **283 personas activas con doble entrada en el directorio.** Los consumidores (RIMS, InOut,
   Pulso DTI) las ven dos veces. La reconciliación de Trabajadores consolidó las que pasan por su
   canal; el resto son estudiantes y egresados, que van por otros.
2. **102 casos de correlación abiertos desde mayo.** Un caso abierto es una decisión pendiente que
   nadie ha tomado. Si nadie los mira, el mecanismo de `disputed` que acabamos de desplegar acabará
   siendo un buzón que se llena.
3. **22 grupos de `User` duplicados por documento**, un eje que no se había medido y que no coincide
   con los 14 de `lambIdPersona`.

## 4. Orden sugerido

| # | Qué | Por qué primero |
|---|---|---|
| 1 | **Notificador de tareas** | El canal ya corre solo a las 06:00 y **nadie se entera si falla**. Es la lección del 25-jul |
| 2 | **Los 105 casos abiertos** | Decidir si se atienden o se cierran en bloque; sin eso, `disputed` no sirve de nada |
| 3 | **Los 283 dual-shadow LDAP** | Son personas activas y afecta a tres consumidores del directorio |
| 4 | Los 14 + 22 `User` duplicados | Ya identificados; requieren regla de negocio sobre cuál conservar |
| 5 | Los 32 `DISPUTED` de Entra | Ligado al gap de cobertura, no al canal de Trabajadores |
