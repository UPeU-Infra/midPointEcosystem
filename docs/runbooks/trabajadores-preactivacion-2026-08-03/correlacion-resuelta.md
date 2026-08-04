# Bloqueantes 1 y 2 RESUELTOS — la correlación ya no crea duplicados en silencio

**Fecha:** 2026-08-04 · **Resource:** `Oracle LAMB Trabajadores v3` (`6a91f7e1-…`) version **324**
**Patch:** [`upeu/resources/patches/correlacion-05-tier-lambidpersona.xml`](../../../upeu/resources/patches/correlacion-05-tier-lambidpersona.xml) (rev2)
**Cierra:** [`RESULTADO-SIMULACION.md`](RESULTADO-SIMULACION.md) §5 acciones 1 y 2

---

## 1. El problema

La simulación del 04-ago demostró que la reconciliación crearía **3 duplicados de persona sin
emitir una sola señal**: 0 marcas `Shadow correlation state changed` frente a 3 duplicados reales.
El guardarraíl 2-tier del 26-jul quedó refutado empíricamente.

Configuración anterior:

```
tier 1  extension/upeu:lambDocNum   weight 1.0
tier 2  personalNumber              weight 0.6
thresholds: definite 1.0 / candidate 0.5
reacción `unmatched` -> addFocus
```

Fallaba porque **la persona había cambiado de documento** (CE→DNI, con-`f`→sin-`f`,
pasaporte→CE): el tier 1 compara documentos que ya no son el mismo, y el tier 2
(`personalNumber` = CANON_KEY) tampoco coincide porque el CANON_KEY se deriva del documento.
Resultado: 0 candidatos → `unmatched` → `addFocus`.

## 2. La solución — dos tiers nuevos

```
tier 1  extension/upeu:lambDocNum      w 1.0   (sin cambios)
tier 2  extension/upeu:lambIdPersona   w 1.0   ← NUEVO, vincula
tier 3  personalNumber                 w 0.6   (baja desde tier 2)
tier 4  givenName + familyName         w 0.55  ← NUEVO, abre caso
```

### Tier 2 — `lambIdPersona`, verificado antes de aplicar

Es el `ID_PERSONA` de Oracle: no cambia cuando cambia el documento, que es el modo de fallo
observado. **Un tier definitivo sobre un identificador ambiguo fusionaría personas distintas**, así
que se midió antes:

| | |
|---|---|
| Users con `lambIdPersona` | 58.178 |
| valores distintos | 58.164 |
| valores compartidos por 2 Users | **14** |
| de esos 14, ¿misma persona? | **14 de 14** (`fullName` normalizado) |
| **colisiones entre personas distintas** | **0** |

Los 14 son el mismo patrón que Evanilda: una persona con `User` de estudiante/egresado
(`202412677`) y otro de trabajador (`007736542`), mismo nombre y mismo `lambIdPersona`. **Son 14
duplicados que ya existen en MidPoint**, no colisiones — este tier los habría evitado.

### Tier 4 — guardarraíl de homónimo

Peso 0.55: por encima de `candidate` (0.5) y por debajo de `definite` (1.0), de modo que un
homónimo exacto cae en la banda intermedia → situación **`disputed`** → `createCorrelationCase`,
reacción que ya estaba declarada y **nunca llegaba a dispararse**. Los dos items forman un AND:
deben coincidir nombre **y** apellido. Volumen dimensionado: **33** pares repetidos entre activos.

> ### 🔴 La rev1 usaba `fullName` y NO disparaba nunca
>
> Se aplicó y se probó: Luzirene y Katty seguían dando `USER ADDED`, sin `disputed`.
> **Causa:** `fullName` se computa en el *object template*, que corre **después** de la
> correlación — no existe en el pre-focus. Solo sirven items poblados por **inbound**:
>
> ```
> ri:NOMBRE   -> givenName
> ri:PATERNO  -> familyName
> ```
>
> Regla general: **un ítem correlator debe venir de un inbound mapping.** Si se computa en el
> template, el correlator no lo ve.

## 3. Validación — los 3 casos reales, en `preview`

| Caso | Antes | Ahora |
|---|---|---|
| `001642451` **Evanilda** | `UNMATCHED` → `addFocus` (duplicado) | **`UNLINKED`** → `USER MODIFIED -> 201520024` ✅ vincula con la egresada existente |
| `000614192` **Luzirene** | `UNMATCHED` → `addFocus` (duplicado) | **`DISPUTED`** ✅ abre caso |
| `44528386f` **Katty** | `UNMATCHED` → `addFocus` (duplicado) | **`DISPUTED`** ✅ abre caso |

**Control: 0 Users creados** (`users creados en la última hora: 0`), y `mode=preview` confirmado en
la task. Los tres duplicados quedan neutralizados.

En el caso de Evanilda la corrida muestra además el comportamiento completo y correcto:
`Focus archetype changed`, `Focus assignments changed`, `Focus role membership changed` — pasa de
egresada a trabajadora **en la misma identidad** — y su entrada LDAP muda de `ou=alumni` a
`ou=people` (`SHADOW DELETED` + `ADDED`), que es el `existence` condicional del patch 03 operando.

### Verificaciones del resource (no se confió en el 204)

version 322 → **324** (dos aplicaciones) · `xsd:element` **64 antes y después** · `<native>`
intacto · test connection **15/15 success**.

## 4. Observación de método

La situación `synchronizationSituation` **sí se persiste en el shadow aunque la task esté en
`preview`**. Es contabilidad de shadow, no cambio de foco ni de recurso: el control de Users
creados (0) confirma que nada más se escribió. Conviene saberlo para no interpretarlo como que el
preview escribió de más.

## 5. Lo que NO hace

- **No fusiona los 14 duplicados ya existentes.** El correlator actúa sobre shadows por vincular,
  no sobre Users ya creados. Sanearlos es trabajo aparte — y ahora están identificados.
- **No arregla los duplicados de origen en Oracle** (544 fichas, 16 vivas): ver
  [`HALLAZGO-DUPLICADOS-ORACLE.md`](HALLAZGO-DUPLICADOS-ORACLE.md). Luzirene y Katty seguirán
  abriendo caso en cada corrida hasta que los DBAs fusionen sus fichas.
- **No cambia `unmatched` → `addFocus`**: crear `User` para una persona realmente nueva sigue
  siendo lo correcto. Lo que cambia es que un homónimo ya no llega a `unmatched`.

## 6. Reversión

`~/backup-trabajadores-precorrelacion-20260804.json` (version 322).
