# Reactivación de `recon-oracle-lamb-trabajadores-daily` — EJECUTADA

**Fecha:** 2026-08-04 · **Corrida real (escribe):** 21:25:28 → 21:42 UTC
**Task:** `23b9fde4-6a5f-4c84-9370-0971fb27be73` · estado final **`RUNNABLE`** (diaria, `0 0 6 * * ?`)
**Autorizada por Alberto** tras la simulación final ([`SIMULACION-FINAL.md`](SIMULACION-FINAL.md))

## ✅ La corrida hizo exactamente lo previsto

| | Snapshot previo | Después | Predicción |
|---|---|---|---|
| `users_total` | 63.319 | **63.334** | **+15 exacto** ✅ |
| `ldap_default` | 28.813 | 28.825 | +12 |
| `ldap_alumni` | 26.972 | 26.972 | 0 |
| casos de correlación | 2.936 | **2.939** | +3 ✅ |
| shadows LDAP tocados | — | **4.979** | backfill operando |

Las 15 altas son **nominalmente las mismas** que listó la simulación. Ninguna sorpresa.

### Los 3 duplicados, neutralizados en producción

| Shadow | Situación real |
|---|---|
| `001642451` Evanilda | **`LINKED`** → vinculada al `User` existente `201520024` ✅ |
| `000614192` Luzirene | **`DISPUTED`** → caso abierto ✅ |
| `44528386f` Katty | **`DISPUTED`** → caso abierto ✅ |

**`User` creado para alguno de los tres: NINGUNO.** El objetivo de toda la jornada.

### Guardarraíl de la operación

Se vigiló con **corte de emergencia automático**: si las altas superaban 40 (la simulación predijo
15), la task se suspendía sola. Progresión observada: +4 → +5 → +6 → +8 → +11 → +12 → **+15** y
estable. No hizo falta.

---

## Las 15 altas — 11 completas, 3 correctas sin accesos, 1 con error

| Situación | Nº | Lectura |
|---|---|---|
| LDAP + Koha | **11** | correcto |
| **Sin ningún acceso** | **3** | ✅ **correcto, no es fallo** — ver abajo |
| LDAP sí, Koha no | **1** | 🔴 error real |

### Las 3 sin accesos son el comportamiento correcto

`08138038` Liliana Álvarez · `41860719` Lourdes Tapia · `45441477` Marisset Ramírez

Las tres entran `lifecycleState=archived`, `effectiveStatus=DISABLED` y **sin archetype**. El `ext`
lo explica: su contrato ya venció.

```
Liliana  08138038 : inicio 2026-05-13 · fin 2026-06-30 · sin affiliation
Adriele  009879845: inicio 2026-07-01 · fin 2026-12-31 · affiliation ["staff"] · campus LIMA
```

Entran al IGA como **registro histórico**, se archivan solas y no reciben accesos. Es exactamente
lo que debe ocurrir con una persona cuyo vínculo ya terminó.

---

## 🔴 Lo que sí hay que arreglar

### 1. Koha rechaza la creación de patrons — 5 casos

```
POST /api/v1/patrons → 400
{"errors":[{"message":"Missing property.","path":"/body/library_id"}]}
```

El mapeo no envía `library_id` (la biblioteca del patron). Afecta a **Ana Cristina Llancari
(`73127501`)** entre las altas nuevas —está activa, con archetype `AuxAff-Staff` y cuenta LDAP,
pero **sin carné de biblioteca**— y a 4 personas más.

Relacionado con el trabajo del 20-jul sobre el gate multi-campus de Koha (`BUJ`/`BUT`): conviene
revisar si estas personas pertenecen a un campus sin mapeo de biblioteca.

### 2. `Unknown attribute __ENABLE__ in objectClass inetOrgPerson` — 3 casos

MidPoint intenta usar el atributo ICF nativo `__ENABLE__` en lugar del simulado. La capability
**está bien declarada** y se verificó tras el error:

```
capabilities/configured/activation/status
    attribute   = ri:midPointAccountStatus
    enableValue = enabled | (vacío)
    disableValue= disabled
```

Y el backfill **sí funciona**: 4.979 shadows LDAP tocados en la corrida. Son 3 casos aislados por
un camino que no ve la capability configurada — **no es un fallo sistémico**, pero queda sin
explicar y conviene identificar qué tienen de particular esos 3.

---

## Estado actual

`recon-oracle-lamb-trabajadores-daily` está **`RUNNABLE`**: volverá a correr **cada día a las
06:00**, ya de forma desatendida.

⚠️ **Sigue sin haber notificador activo.** Hay `notificationConfiguration` pero ningún
`simpleTaskNotifier` ni transporte de correo: si una corrida falla, nadie se entera — que es
exactamente lo que ocurrió el 25-jul. **Es lo primero que conviene resolver ahora que el canal
corre solo.**

Y Luzirene y Katty abrirán `disputed` en cada corrida hasta que los DBAs fusionen sus fichas en
Oracle ([`HALLAZGO-DUPLICADOS-ORACLE.md`](HALLAZGO-DUPLICADOS-ORACLE.md)).
