# INCIDENTE: escribí el ePPN de otra persona a 1.497 usuarios de Keycloak

**27-ago-2026 · detectado y reparado el mismo día · sin pérdida de datos**

## Qué pasó

Corrigiendo el `eppn` congelado de Keycloak (1.500 personas tenían su **DNI** publicado como
identificador federado), extraje del LDAP el par `uid → eduPersonPrincipalName` con este `awk`:

```bash
awk '/^uid: /{u=$2} /^eduPersonPrincipalName: /{print tolower(u)"|"$2}'
```

**En el LDIF de OpenLDAP, `eduPersonPrincipalName` aparece ANTES que `uid`.** El `awk` emparejó
cada ePPN con el `uid` de la **entrada anterior**, desplazando todo el fichero una posición:

```
8410001|8410002@upeu.edu.pe     ← la clave es 8410001, el valor es de 8410002
```

Escribí ese fichero a producción. **1.497 personas quedaron con el identificador federado de otra
persona.** A `200010013` le puse `200010015@upeu.edu.pe`.

Es más grave que el problema que resolvía: un DNI expuesto es dato personal; un ePPN cruzado es
suplantación potencial en cualquier aplicación que vincule por ese claim (RIMS).

## Por qué ninguna de las tres verificaciones lo detectó

Esto es lo que hay que aprender, más que el bug.

| Verificación | Resultado | Por qué no sirvió |
|---|---|---|
| **Canario** (1 persona) | correcto ✅ | Lo apliqué con la fórmula `username@upeu.edu.pe`, **antes** de construir el cruce. Validó un procedimiento **distinto del que después ejecuté**. |
| **Lote de 20** | «limpio» ✅ | Solo comprobaba *«¿el valor sigue siendo un DNI?»*. El ePPN de otra persona **no es un DNI**, así que pasó. |
| **Log de ejecución** | `ok=1477 err=0` ✅ | Las escrituras se aplicaron sin fallo. Eran **correctas como operación y falsas como dato**. |

Las tres verificaban la **forma** del valor. Ninguna verificaba **que el valor fuera el de esa
persona**. Lo detectó la comparación final contra la fuente —la única que compara identidad con
identidad— y solo porque el número no cuadró y fui a mirar en lugar de dar por bueno el `err=0`.

## Reparación

Parser nuevo que **agrupa por bloque de entrada** (separador: línea en blanco) en vez de fiarse
del orden de los atributos, y que además desdobla las continuaciones LDIF. Con prueba de
integridad incorporada:

| | volcado roto | volcado correcto |
|---|---|---|
| clave ≠ local-part del valor | **45.624 de 50.097** | **3 de 50.097** |

Reparadas las 1.497. Verificación final, entrada por entrada contra el LDAP:

```
LAS 1.497 QUE TOQUE:  coinciden con el LDAP = 1497   DIFIEREN = 0
TODO EL REALM:        coinciden = 46.955             difieren = 1 (preexistente, nunca tocada)
```

Ningún atributo perdido: `affiliation`, `epuid`, `eduperson_entitlement`, `LDAP_ENTRY_DN` y
`LDAP_ID` intactos en sus recuentos originales.

## Reglas que salen de aquí

1. **Un volcado derivado de un LDIF lleva prueba de integridad antes de usarse.** Para un mapa
   `clave → valor` donde ambos deberían corresponderse, contar las discrepancias: si son decenas
   de miles, el parser está roto. Cuesta una línea y habría evitado todo esto.
2. **Nunca parsear LDIF asumiendo el orden de los atributos.** Agrupar por bloque.
3. **El canario debe ejecutar EXACTAMENTE el procedimiento del lote**, con el mismo fichero de
   entrada. Un canario aplicado con otro método no valida nada.
4. **Verificar la forma del valor no es verificar el valor.** La comprobación válida compara
   contra la fuente, registro a registro: *«¿el valor de esta persona es el que la fuente dice
   para ESTA persona?»*.
5. **`err=0` no es una verificación.** Solo dice que las escrituras se aplicaron.

## Estado final y cabos abiertos

- ✅ **1.497 personas** con su ePPN alineado con el directorio; los 1.500 DNI retirados.
- 🟡 **2.065** cuyo ePPN es su propio DNI: **correcto respecto al LDAP** — son las pendientes del
  rename (uid = DNI), fuera del alcance de esta operación.
- 🟡 **7.364 cuentas de Keycloak sin entrada en el LDAP**, 54 de ellas con un ePPN que es un DNI
  ajeno. No se pueden corregir sin fuente; hilo aparte.
- 🔴 Sin tocar: `affiliation`, `epuid`, `eduperson_entitlement` — pendientes de la respuesta de
  RIMS y devsupeu-backend.

Respaldo intacto en todo momento: `user_attribute` completo en el servidor
(`/tmp/kc-user_attribute-20260827.sql.gz`) y las 1.556 filas originales en local.
