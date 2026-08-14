# ADR-060 — Limpieza de 9 shadows huérfanos `generic/ou`

**Fecha:** 14-ago-2026
**Estado:** aceptado (alcance reducido tras el diagnóstico — ver §Corrección)
**Ámbito:** árbol organizativo — cambio 🟡 (ADR + simulación + canario + baseline)
**Rector:** [`ARQUITECTURA-ARBOL-ORGANIZATIVO.md`](../ARQUITECTURA-ARBOL-ORGANIZATIVO.md)

## Contexto

InOut (aforo del CRAI) reportó **56 códigos de `departmentNumber` sin entrada en `ou=org`**,
dejando 899 personas sin área. Consume dos ramas del directorio y las une: el código va en
la persona, el nombre en el catálogo.

## Decisión

**Borrar los 9 shadows huérfanos de `intent=ou`** del resource LDAP-IdentityCache, residuo
del incidente del 6-ago (DN jerárquico de sedes), sin `owner` desde entonces:

```
ou=11,ou=org            ou=51,ou=16,ou=org      ou=53,ou=16,ou=org
ou=54,ou=16,ou=org      ou=67,ou=58,ou=org      ou=692,ou=16,ou=org
ou=710,ou=113,ou=org    ou=713,ou=113,ou=org    ou=ep-teo,ou=11,ou=org
```

### 🔴 Lo que NO se toca

Los otros **6 huérfanos son las ramas raíz del directorio**:

```
ou=people    ou=alumni    ou=groups    ou=services    ou=org    ou=upeu,ou=org
```

Son huérfanos por naturaleza y sus entradas **son la estructura del árbol**. `ou=people`
contiene 49.222 personas. Tocarlos no está contemplado por ningún procedimiento.

## Resultado

Los 9 borrados sin error; **la entrada LDAP de cada uno quedó intacta** (canario
`ou=713,ou=113,ou=org`). Quedan exactamente los 6 de las ramas raíz.
Verificador de invariantes **6/6 ✅ antes y después**, 191 orgs.

Junto con el import del resource Org (cambio 🟢 libre, ejecutado antes):

| | Inicio | Ahora |
|---|---|---|
| Orgs en MidPoint | 175 | 191 |
| Unidades en `ou=org` | 104 | **155** |
| Personas sin área | 1.033 | **274** |

---

## 🔴 Corrección — la causa real NO era la que este ADR suponía

**La primera versión de este ADR partía de una premisa falsa** y conviene dejarlo escrito.

Se afirmó que *"18 áreas están en el feed y MidPoint nunca las leyó, entre ellas Rectorado
(3) y los tres vicerrectorados (4, 5, 6)"*. **Es incorrecto.** Esas unidades existen en
MidPoint desde siempre y forman la espina del árbol — con nombre **semántico**:

```
RECTORADO      VICERRECTORADO-ACADEMICO      VICERRECTORADO-ADMINISTRATIVO
VICERRECTORADO-BIENESTAR-UNIVERSITARIO       DIR-INVESTIGACION-E-INNOVACION
```

El error de método: se comprobó su existencia buscando `AREA-3`, `AREA-4`… porque las
primeras orgs inspeccionadas seguían ese patrón. **Conviven dos convenciones de nombre**
y no se verificó antes de concluir:

| Convención | Orgs |
|---|---|
| `AREA-<ID_AREA>` | **103** |
| Nombre semántico | **88** (51 con proyección LDAP) |

### La causa real: dos claves para la misma unidad

| Eje | Qué publica | Ejemplo |
|---|---|---|
| Persona → `departmentNumber` | el **`ID_AREA`** de Oracle | `3` |
| Org → DN en `ou=org` | el **identificador** de la org | `ou=RECTORADO` |

InOut busca `ou=3,ou=org` y encuentra `ou=RECTORADO`. **No falta la unidad: falta la clave
con la que se la busca.** Por eso resuelven bien las `AREA-N` —cuyo nombre contiene el
número— y no las de nombre semántico.

Esto **no lo arregla ningún import ni recompute**: no es un hueco de datos.

### Lo que sí quedó resuelto por este ADR y el import

Los 9 huérfanos eran basura real del 6-ago y había que quitarlos. Y el import creó 16 orgs
que efectivamente faltaban. De ahí la mejora de 1.033 → 274 personas. Pero **el resto no se
cierra por esta vía**.

### Lo que falta decidir (ADR propio)

Qué clave manda para el catálogo que consume InOut:

- **Opción A** — que las orgs de nombre semántico publiquen también su `ID_AREA` como
  entrada en `ou=org` (o como atributo adicional buscable).
- **Opción B** — que `departmentNumber` de la persona publique el identificador semántico
  en lugar del `ID_AREA`.

**A** no toca a las personas y es aditiva; **B** cambia el dato en 24.824 personas y rompería
a cualquier otro consumidor que hoy espere el número.

⚠️ Cualquiera de las dos toca el `identifier` de orgs, y el rector advierte que **eso
gobierna el DN de su OU**: cambiarlo dispara provisioning y el conector **no sabe renombrar**
— así nacieron los 9 huérfanos que este ADR acaba de limpiar.

### Nota sobre el conflicto de DN

`ou=692,ou=16,ou=org` y `ou=713,ou=113,ou=org` siguen dando `Found conflicting existing
object`. Es un problema **independiente**, de OUs anidadas cuyo shadow se regenera huérfano
en cada recompute. No bloquea a las unidades de InOut y va por separado.
