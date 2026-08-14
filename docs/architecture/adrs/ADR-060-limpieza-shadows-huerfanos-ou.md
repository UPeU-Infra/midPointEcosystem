# ADR-060 — Limpieza de 9 shadows huérfanos `generic/ou` que bloquean el alta de unidades

**Fecha:** 14-ago-2026
**Estado:** aceptado
**Ámbito:** árbol organizativo — cambio 🟡 (ADR + simulación + canario + baseline)
**Rector:** [`ARQUITECTURA-ARBOL-ORGANIZATIVO.md`](../ARQUITECTURA-ARBOL-ORGANIZATIVO.md)

## Contexto

InOut (aforo del CRAI) reportó que **56 códigos de `departmentNumber` no tenían entrada en
`ou=org`**, dejando 899 personas sin área en sus reportes. Consume dos ramas del directorio
y las une: el código va en la persona, el nombre en el catálogo.

El diagnóstico descartó lo que se suponía. **No era un hueco de catálogo**: las unidades
existían en Oracle y en buena parte en MidPoint. Eran dos fallos encadenados:

1. **El resource `Oracle LAMB Org` no tiene ninguna tarea de reconciliación.** Hay diarias
   para Estudiantes, Egresados, Trabajadores y Koha, pero no para organizaciones: el árbol
   se pobló una vez y no volvió a sincronizarse. 18 áreas llevaban tiempo en el feed sin
   que MidPoint las hubiera leído (0 shadows), entre ellas **Rectorado (`3`), los tres
   vicerrectorados (`4`, `5`, `6`), Dirección General de Investigación (`69`) y Colegio
   Unión (`97`)**.
2. **9 shadows huérfanos ocupan el DN** que necesitan las unidades nuevas, y hacen fallar
   su creación con `Found conflicting existing object with dn = …`.

Con el import ya ejecutado (🟢 libre: altas de `AREA-NNN` desde Oracle), el catálogo pasó de
104 a 155 unidades y las personas sin área de 1.033 a 274. Los 9 huérfanos son lo que impide
cerrar el resto.

## Decisión

**Borrar los 9 shadows huérfanos de `intent=ou` del resource LDAP-IdentityCache**, y solo
esos:

```
ou=11,ou=org            ou=51,ou=16,ou=org      ou=53,ou=16,ou=org
ou=54,ou=16,ou=org      ou=67,ou=58,ou=org      ou=692,ou=16,ou=org
ou=710,ou=113,ou=org    ou=713,ou=113,ou=org    ou=ep-teo,ou=11,ou=org
```

Son residuo del incidente del 6-ago (DN jerárquico de sedes), sin `owner` desde entonces.

### 🔴 Lo que NO se toca

Los otros **6 shadows huérfanos son las ramas raíz del directorio** y quedan explícitamente
fuera:

```
ou=people    ou=alumni    ou=groups    ou=services    ou=org    ou=upeu,ou=org
```

Son huérfanos por naturaleza —no cuelgan de ninguna org— y sus entradas **son la estructura
del árbol LDAP**. `ou=people` contiene 49.222 personas. Tocarlos no está contemplado por
ningún procedimiento.

### Lo que tampoco entra en este ADR

Los **243 shadows huérfanos del resource `Oracle LAMB Org`**. No ocupan DN en LDAP ni
bloquean nada; su limpieza es higiene y va por separado.

## Por qué esta opción

**El DN jerárquico no es el problema.** 66 de las 155 OUs son anidadas, y eso es el diseño
(D1 del rector). El incidente de agosto fue moverlas **bajo las sedes**, que es distinto y
ya está resuelto (42/14/6 → 1/0/0).

Lo que sobra es la **referencia** en MidPoint, no la entrada en LDAP: las entradas reales
existen y se conservan. Borrar el shadow libera el DN para que la unidad correcta lo adopte
en el siguiente recompute.

### Alternativas descartadas

| Opción | Por qué no |
|---|---|
| Borrar también las entradas LDAP | El conector **no tiene `DeleteCapability`**; además destruiría OUs vivas. |
| Renombrar las entradas a DN plano | El conector **no sabe renombrar** — así nacieron estos huérfanos el 6-ago. |
| Limpiar los 258 huérfanos de golpe | Mezcla tres problemas distintos; 6 de ellos son las ramas raíz. |
| No hacer nada | 274 personas siguen sin área, incluidas las de Rectorado y los vicerrectorados. |

## Riesgos y mitigación

- **Riesgo:** borrar un shadow que sí tenía dueño. → Filtro por `NOT EXISTS` en
  `m_ref_projection` y exclusión nominal de las 6 ramas raíz.
- **Riesgo:** que MidPoint interprete la ausencia como "borrar la OU". → `DeleteCapability`
  no está habilitada en el resource LDAP: no puede borrar entradas aunque quisiera.
- **Reversible:** un import del resource los recrea. No se pierde información.

## Verificación

1. Verificador de invariantes **antes** — hecho: **6/6 ✅**, 191 orgs.
2. Canario: un shadow, comprobar que su entrada LDAP sigue viva.
3. Los 8 restantes.
4. Recompute de las orgs bloqueadas.
5. Verificador **después**: debe seguir 6/6.
6. Métrica de cierre: personas sin unidad resoluble por debajo de 274.

## Resultado de la ejecución (14-ago)

Los 9 shadows se borraron sin error y **la entrada LDAP de cada uno quedó intacta**
(verificado en el canario `ou=713,ou=113,ou=org`). Quedan exactamente los **6 de las ramas
raíz**, como prescribe este ADR. Verificador después: **6/6 ✅**, 191 orgs.

### 🔴 Pero el DN NO se libera: los huérfanos se REGENERAN

El recompute posterior volvió a fallar con el mismo error, y esta vez apuntando a un shadow
**nuevo** (`a9dcb685`, `ou=692,ou=16,ou=org`) que también nace huérfano.

El ciclo es: el recompute **crea** el shadow → **no consigue vincularlo** a su org → queda
huérfano → el siguiente intento **choca contra él**. Borrarlos no resuelve nada mientras la
vinculación siga fallando.

**La causa raíz no es la basura acumulada, es que la adopción falla.** Este ADR eliminó un
síntoma real (los 9 del 6-ago) pero el bloqueo persiste, así que las 21 unidades siguen sin
publicarse y las 274 personas sin área.

**Lo que hay que investigar en sesión propia**, con MidPoint respondiendo con holgura:
por qué el shadow recién creado no se vincula a su `OrgType`. Sospechas a descartar en
orden: que la entrada LDAP existente no correlacione (matching por DN vs por `identifier`),
que el DN calculado no coincida con el del padre real de la org, o que falte el
`correlation` en el objectType `generic/ou`.

## Estado del pedido de InOut

| | Inicio | Tras el import | Objetivo |
|---|---|---|---|
| Unidades en `ou=org` | 104 | 155 | ~176 |
| Personas sin área | 1.033 | 274 | decenas |
