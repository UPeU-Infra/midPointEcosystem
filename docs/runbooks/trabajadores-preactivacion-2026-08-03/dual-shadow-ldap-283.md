# 283 personas activas con doble entrada LDAP — diagnóstico

**Fecha:** 2026-08-04 · **Medido en vivo** · **Nada ejecutado**
**Origen:** [`INVENTARIO-CONFLICTOS.md`](INVENTARIO-CONFLICTOS.md) §2

---

## 1. El hecho

**283 `User` activos tienen simultáneamente una entrada en `ou=people` y otra en `ou=alumni`.**
Ambos shadows `LINKED`, ambos vivos. Para RIMS, InOut y Pulso DTI son **dos personas distintas**.

Ninguno tiene dos entradas en la misma OU — eso sí sería peor.

## 2. Quiénes son: todos tienen doble afiliación

| `eduPersonAffiliation` | Nº | Afiliación viva además de `alum` |
|---|---|---|
| `["staff","alum"]` | 87 | trabajador |
| `["alum","student"]` | 83 | estudiante |
| `["faculty","alum"]` | 76 | docente |
| `["alum"]` | **15** | **ninguna — solo egresado** |
| `["staff","alum","student"]` | 8 | trabajador + estudiante |
| `["alum","faculty"]` | 6 | docente |
| `["alum","staff"]` | 4 | trabajador |
| `["faculty","alum","student"]` | 2 | docente + estudiante |
| `["staff","alum","faculty"]` | 2 | trabajador + docente |

Archetypes coherentes (1 structural + 1 auxiliar cada uno, sin conflicto):
`alumni` 155 · `student` 93 · `employee-faculty` 23 · `employee-staff` 12.

**El patrón es claro: son personas que egresaron y siguen vinculadas** — el egresado que ahora
trabaja en la universidad, o que hace una maestría. No es un caso raro: es la trayectoria normal.

## 3. Cuándo apareció

| Mes de creación del shadow | `default` | `alumni` |
|---|---|---|
| 2026-05 | 122 | — |
| 2026-06 | 46 | — |
| **2026-07** | 92 | **282** |
| 2026-08 | 23 | 1 |

**Los 282 shadows de `alumni` se crearon en julio**, sobre personas que en su mayoría ya tenían
entrada en `ou=people` desde mayo o junio. Coincide con la activación de las reconciliaciones
diarias (21-jul).

## 4. Lo que NO es

**No viene del RBAC.** Se buscó en **todos** los `ROLE`, `ARCHETYPE`, `ORG` y `SERVICE` del
repositorio: **ningún objeto tiene una `construction` hacia el resource LDAP**. Las proyecciones no
las otorga ningún rol.

Configuración de los objectType:

```
account/default   default=true
account/alumni    default=false
generic/ou        default=false
```

## 5. La regla de negocio que falta

Es evidente y no requiere inventar nada:

> **Quien tiene una afiliación viva además de `alum` va en `ou=people`.
> `ou=alumni` es para quien es *exclusivamente* egresado.**

Aplicada a esta población: **268 deberían estar solo en `ou=people`** y **15 solo en `ou=alumni`**.

Hoy no existe esa exclusión: `account/default` y `account/alumni` no son mutuamente excluyentes, así
que una persona con dos afiliaciones acaba con las dos entradas.

## 6. Lo que falta averiguar antes de proponer el fix

**Cómo se decide hoy el `intent` de cada proyección.** No viene de roles, y `account/default` está
marcado `default=true`, pero eso no explica por qué se crea *además* la de `alumni`. Faltan dos
comprobaciones:

1. La `synchronization` / `focus` de cada `objectType` del resource — no se pudo extraer con el
   parser usado; hay que revisarla a mano sobre el XML.
2. **Si el dual existe en el LDAP real o solo en los shadows de MidPoint.** Si el directorio ya
   tenía ambas entradas y MidPoint las importó, la causa está en el LDAP y no en la configuración.
   No se pudo comprobar: el bind `cn=rims-reader` del `.env` disponible no autenticó.

**Sin esas dos respuestas no se puede escribir el fix**, solo adivinarlo. Y un cambio de exclusión
entre intents afecta a 283 personas activas: exige simulación previa, como los tres arreglos de hoy.

## 7. Riesgo de no hacer nada

Bajo a corto plazo —lleva así desde julio— pero **creciente**: cada reconciliación diaria de
Egresados puede añadir casos nuevos, y los tres consumidores del directorio siguen viendo doble a
283 personas activas.
