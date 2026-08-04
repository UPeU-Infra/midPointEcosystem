# Simulación final tras los tres arreglos — VEREDICTO

**Fecha:** 2026-08-04 · **Task:** `3cb0c47a-…` (`mode=preview`, confirmado en PROD)
**SimulationResult:** `bbb4c5e0-50c0-407b-9895-07e01ef8cef2` · **progress 7.542** · 0 `fatal_error`
**Resources:** Trabajadores v**324** · LDAP v**222**

## ✅ VEREDICTO: los tres bloqueantes están cerrados

Primera corrida con los tres arreglos actuando **a la vez** sobre el universo completo. Todos los
efectos previstos se confirman y no aparece ninguno nuevo.

---

## 1. Comparativa

| | Antes (a241d818) | **Ahora** (bbb4c5e0) |
|---|---|---|
| **`USER ADDED`** | **18** | **15** ✅ los 3 duplicados neutralizados |
| `SHADOW DELETED` | 180 | **67** |
| **→ personas que se quedaban sin ninguna entrada LDAP** | **114** | **0** ✅ |
| `SHADOW ADDED` | 189 | 109 |
| `SHADOW MODIFIED` | 2.033 | 3.122 |
| `USER MODIFIED` | 6.671 | 6.615 |
| **Users realmente creados (control)** | — | **0** ✅ |

### Los 3 casos que iban a duplicarse

| Shadow | Antes | Ahora |
|---|---|---|
| `001642451` Evanilda | `UNMATCHED` → `addFocus` | **`UNLINKED`** → vincula con `201520024` ✅ |
| `000614192` Luzirene | `UNMATCHED` → `addFocus` | **`DISPUTED`** → abre caso ✅ |
| `44528386f` Katty | `UNMATCHED` → `addFocus` | **`DISPUTED`** → abre caso ✅ |

Las 15 altas restantes son personas nuevas legítimas (`40236214`, `45441477`, `70667867`…),
ninguna con homónimo.

## 2. Los 67 borrados, uno a uno

Ninguno deja a nadie sin presencia en el directorio:

| Tipo | Nº | Qué pasa |
|---|---|---|
| **Mudanzas limpias** | **48** | pierden una entrada y ganan otra (`people`↔`alumni`) |
| **Consolidaciones de dual-shadow** | **19** | tenían entrada en `people` **y** en `alumni`; se borra la sobrante y la otra queda `MODIFIED` |
| **Se quedan sin ninguna** | **0** | ✅ |

Los 19 se verificaron **uno por uno** (no por muestra): 19 de 19 conservan entrada. Uno de ellos
(`201323330`) al revés — sobrevive la de `alumni`.

> ⚠️ **Trampa de medición, tercera vez hoy.** El primer conteo dio «19 personas pierden entrada y no
> ganan otra», lo que parecía un fallo. Era la consulta: comparaba borrados contra **altas nuevas**,
> sin mirar si el foco ya tenía **otra entrada preexistente que sobrevive**. El patrón se repite:
> cualquier cruce sobre una simulación debe contemplar los tres estados —borrado, alta y
> preexistente-que-sobrevive—, no solo dos.

## 3. Marcas de evento

| Marca | Nº | Lectura |
|---|---|---|
| Resource object affected | 4.187 | |
| **Projection deactivated** | **2.464** | (antes 1.124) — incluye el **backfill de `alumni`**, que nunca había podido deshabilitarse |
| Focus assignments changed | 441 | |
| Focus role membership changed | 435 | |
| Focus parent organization reference changed | 393 | |
| Focus archetype changed | 387 | |
| Projection activated | 322 | |
| **Focus deactivated** | **153** | las bajas |
| Focus activated | 119 | |
| Projection renamed / identifier changed | 5 / 5 | |

## 4. Errores

**Un solo mensaje en toda la corrida**, el mismo de la corrida anterior y preexistente a todos
estos cambios:

```
Projection [ACCOUNT/default] already exists in lens context
(existing: 76443853@upeu.edu.pe, new: james.raymundo@upeu.edu.pe)
```

Colisión de proyección en Entra ID sobre un mismo foco. Es el `PARTIAL_ERROR`. Ya estaba catalogado
como acción 5 (no bloqueante) en [`RESULTADO-SIMULACION.md`](RESULTADO-SIMULACION.md).
**0 `fatal_error`.**

---

## 5. Qué falta decidir antes de reactivar

Lo técnico está cerrado. Quedan tres decisiones de operación, **todas de Alberto**:

| # | Asunto | Consideración |
|---|---|---|
| 1 | **El backfill masivo** | 2.464 proyecciones se deshabilitarían en la primera corrida, y ~26.972 entradas `alumni` recibirán `midPointAccountStatus`. Es correcto y deseado —es el estado que el directorio nunca reflejó— pero conviene escalonarlo en vez de soltarlo de golpe |
| 2 | **Luzirene y Katty** | abrirán `disputed` en **cada** corrida hasta que los DBAs fusionen sus fichas en Oracle. Es ruido conocido, no un fallo. Ver [`HALLAZGO-DUPLICADOS-ORACLE.md`](HALLAZGO-DUPLICADOS-ORACLE.md) |
| 3 | **Los 14 duplicados ya existentes** | el tier de `lambIdPersona` los habría evitado, pero no los fusiona: ya son Users separados. Sanearlos es trabajo aparte, ahora identificado |

Además, sigue pendiente y **no bloquea**: la colisión de proyección Entra del foco `76443853`.
