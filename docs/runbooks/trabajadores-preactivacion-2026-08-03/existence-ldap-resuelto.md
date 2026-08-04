# Bloqueante 3 RESUELTO — la baja ya no borra la entrada LDAP (default + alumni)

**Fecha:** 2026-08-04 · **Resource:** `LDAP-IdentityCache-UPeU` (`7b4e1c2d-…`) version **222**
**Patch:** [`upeu/resources/patches/leaver-gap-03-existence-no-borrar.xml`](../../../upeu/resources/patches/leaver-gap-03-existence-no-borrar.xml) (rev2)
**Cierra:** [`RESULTADO-SIMULACION.md`](RESULTADO-SIMULACION.md) §3 y §5 acción 3

---

## 1. El problema

Sin mapping de existencia, al cesar una persona la proyección deja de ser legal y MidPoint
**borra la entrada LDAP** en vez de deshabilitarla. Medido: 180 `SHADOW DELETED`, de los cuales
**114 dejaban a la persona sin ninguna entrada** en el directorio.

Contradecía el arreglo del leaver gap del 03-ago y la petición P1 de Pulso DTI, RIMS e InOut: lo
que se pidió es una **señal** de baja, no la desaparición de la ficha.

Verificado antes de tocar nada:

```
@id=62   account/default   existence=False  administrativeStatus=True
@id=461  account/alumni    existence=False  administrativeStatus=False   <- ver §5
@id=447  generic/ou        existence=False  administrativeStatus=False
```

## 2. Por qué la rev1 (valor fijo) no servía

La primera versión usaba `<value>true</value>` incondicional. **Se aplicó y se midió** — no se
descartó por teoría:

| | rev1 |
|---|---|
| Borrados en `ou=people` (bajas) | 141 → **0** ✅ |
| Personas con **dos** entradas a la vez | 0 → **9** ❌ (en el 36 % de la corrida; ~25 proyectadas) |

**Causa:** las mudanzas `ou=people` ↔ `ou=alumni` (26 + 21 en la corrida completa) el conector las
implementa como **delete + add**, porque no soporta rename. Con existencia incondicional el
borrado del lado viejo no ocurre → la persona queda en las dos OUs. Es el mismo dual-shadow que se
limpió a mano días antes.

MidPoint entrega «baja» y «mudanza» con la misma señal —pérdida de legalidad—, así que el mapping
debe distinguirlas por el **estado del foco**.

## 3. La solución (rev2)

```groovy
condition:  def st = focus?.activation?.effectiveStatus?.toString()?.toLowerCase()
            def lc = focus?.lifecycleState?.toString()?.toLowerCase()
            return (st in ['disabled','archived']) || (lc in ['archived','suspended'])
expression: true
strength:   strong
```

Solo actúa cuando la persona está de baja. En cualquier otro caso el mapping no aporta valor y
decide la legalidad normal — que es lo que mantiene funcionando las mudanzas.

## 4. Validación — canario `9f2e1a55-…` en `preview`, las tres clases a la vez

| Clase | Persona | Esperado | Obtenido |
|---|---|---|---|
| **Baja** | `77354642` Jhony Chuquilin | conservar + deshabilitar | `MODIFIED` → `administrativeStatus=disabled`, `disableReason#deprovision` ✅ |
| **Baja** | `72240030` Jhan Camarena | ídem | ídem ✅ |
| **Mudanza** | `200210286` Claudia De la Cruz | seguir borrando + crear alumni | `default DELETED` + `alumni ADDED` ✅ |
| **Mudanza** | `202118561` Genesis Endara | ídem | ✅ |
| **Mudanza** | `9510077` Gloria Espíritu | ídem | ✅ |
| **Mudanza** | `201110354` Emilyn Verde | ídem | ✅ |
| **Control ⊖** | `202122579`, `201711922` (activos, sin cuenta LDAP) | **0 altas** | no aparecen ✅ |

**Dual-shadows: 0.** Los 4 `alumni ADDED` emparejan exactamente con los 4 `default DELETED`.

Nota: Claudia tenía `disableTimestamp` no nulo y aun así mudó correctamente — su
`effectiveStatus` no es `disabled`. La condición discrimina por estado **efectivo**, no por la
presencia del timestamp, que es lo correcto.

### Verificaciones del resource (no se confió en el 204)

version 220 → **221** · `xsd:element` 2.288 intactos · `<native>` intacto · test connection
**15/15 success**.

## 5. ✅ `account/alumni` — cerrado también (patch 04, version 222)

**`account/alumni` (@id=461) no tenía bloque `activation` en absoluto.** El patch del 03-ago que
cerró el leaver gap **solo cubrió `account/default`** — el canario de aquel día era de `ou=people`,
y por eso no se vio. Consecuencia: **las cuentas de egresados nunca habían podido deshabilitarse**.
No era una regresión: venía de antes.

> ⚠️ La primera lectura por regex sobre el JSON dio `activation=True` para alumni — **falso
> positivo**, porque la delimitación del bloque capturaba texto del `synchronization` global.
> Se confirmó pidiendo el resource **en XML por REST** y recorriendo el DOM. Ante cualquier duda
> estructural, XML por REST, no regex sobre el JSON del repositorio.

Aplicado [`leaver-gap-04-alumni-activation.xml`](../../../upeu/resources/patches/leaver-gap-04-alumni-activation.xml):
mismo `existence` condicional + `administrativeStatus` strong. version 221 → **222**,
`xsd:element` 2.288 intactos, test connection 15/15.

### Validación — canario `9f2e1a55-…`, cuatro clases

| Clase | Personas | Esperado | Obtenido |
|---|---|---|---|
| **Baja real** (`effectiveStatus=DISABLED`) | `202015421`, `323100157`, `202313501`, `201610032` | conservar + deshabilitar | `alumni MODIFIED` → `administrativeStatus=disabled` + `disableReason#deprovision` ✅ |
| **Mudanza** `alumni`→`people` | `200110510`, `200411521`, `200510741` | seguir borrando + crear people | `alumni DELETED` + `default ADDED` en `ou=people` ✅ |
| **Consolidación** (tenían ambas) | `200310882`, `200410438`, `200510677` | borrar alumni, conservar people | ✅ nadie queda sin entrada |
| **Control ⊖** | `202122579`, `201711922` | 0 altas | **0 altas LDAP** ✅ |

Nota: hizo falta buscar la clase «baja real» aparte, porque **no hay ningún `User`
archived/suspended con cuenta alumni** (0 en PROD) — la condición se dispara por
`effectiveStatus`, y esos sí existen.

### ⚠️ Efecto pendiente de dimensionar antes de una corrida real

Hay **26.972 shadows alumni vivos**. Al declarar `administrativeStatus` strong, el próximo
recompute escribirá `midPointAccountStatus` en todos ellos — el mismo backfill masivo que ya
ocurrió con `ou=people`. Correcto y deseado, pero conviene escalonarlo.

### Sigue sin activation: `generic/ou` (@id=447)

Es el árbol organizativo bajo `ou=org`, no cuentas de persona. No aplica la misma semántica, pero
queda constancia de que tampoco la tiene.

## 6. Trampa de medición — documentada para no repetirla

Al contar los shadows que *se crearían* **no se puede hacer `JOIN` con `m_shadow`**: un shadow
`ADDED` todavía no existe en esa tabla y el join lo descarta en silencio. Eso produjo un falso
«0 dual-shadows» en la primera medición de la rev1. Se detectó porque el total de `ADDED` no
cuadraba con los 189 del informe previo.

**Leer siempre el `fullobject` de `m_simulation_result_processed_object` directamente.**

## 7. Reversión

Backup del resource previo en PROD: `~/backup-ldap-resource-preexistence-20260804.json`
(version 219, sin ningún `existence`).
