# Vínculo consolidado — solución integral

**Fecha:** 12-ago-2026 · **Estado:** propuesta, medida contra PROD y Oracle

## El objetivo

MidPoint debe ser el **hub** que captura las fechas de expiración de todos los vínculos,
determina si hay alguno activo, y **solo retira accesos cuando no queda ninguno**.

Principio rector, fijado por Alberto: **sin contrato no hay vínculo.** No se da acceso a
quien no tiene contrato vigente — y la normativa de seguridad respalda no darlo.

Corolario que no se puede perder de vista: **un contrato permanente NO tiene fecha de fin
por diseño.** Ausencia de fecha ≠ vínculo terminado.

## El modelo: tres canales, una decisión

Cada canal responde por separado *"¿esta persona tiene contrato vigente conmigo?"*. La
decisión de acceso es la **unión**: basta un sí.

| Canal | Fuente | Vigente cuando | Hoy |
|---|---|---|---|
| **Laboral** | `ELISEO.VW_APS_EMPLEADO` | `ESTADO='A'` **y** sin cese **y** (`ID_TIPOCONTRATO=01` **o** `FEC_TERMINO >= hoy`) | ✅ correcto |
| **Académico** | `DAVID.ACAD_MODULO_DETALLE` vía `DATE_EXPIRY` | `DATE_EXPIRY >= hoy` | ❌ **no comprueba vigencia** |
| **Egresado** | `DAVID.VW_PERSONA_EGRESADO` | rol con `validTo = 31-dic(egreso+2)` | ✅ correcto |

> El canal de egresado **no otorga accesos generales**: solo biblioteca, y su rol ya caduca
> solo (4.602 vigentes / 22.883 caducados). No hay nada que arreglar ahí.

## Lo que ya funciona (no tocar)

- **`liveAffiliationWorker`** implementa el canal laboral entero, incluidos los permanentes:
  `ESTADO='I'` → null; fecha vencida → null; **fecha nula → vínculo vivo**.
- **`ESTADO` → `activation/administrativeStatus`**: cuando RR.HH. cierra el contrato, la
  persona se desactiva sola. Por eso el canal laboral está sano: **2.376 de 2.415** con
  contrato vigente.
- **El rol de biblioteca de egresados** caduca por `validTo` sin intervención.

## El único defecto real

**`liveAffiliationStudent` se materializa por PRESENCIA EN EL FEED, no por vigencia.**

El `searchScript` no filtra `>= SYSDATE` a propósito (evita huérfanos): el estudiante sigue
en el feed mientras tenga *cualquier* matrícula en el horizonte de semestres. Así que el
vínculo académico **nunca se apaga solo**, al contrario que el laboral.

Medido en PROD (12-ago): de 25.843 estudiantes activos, **15.311 con matrícula vigente** y
**10.519 vencidos** — que conservan `liveAffiliationStudent=true` y `lifecycleState=active`.

**Verificado con una muestra de 10**: importados ya con el filtro de semestres corregido,
ninguno recuperó matrícula (siguen en dic-2025 / ene-2026) y los diez mantienen
`vinculoEst=true`. No son víctimas del filtro: son bajas reales que el mecanismo no ve.

## La solución

**Añadir la condición de vigencia a `liveAffiliationStudent`**, exactamente como el canal
laboral ya la tiene:

```groovy
def fin = basic.getAttributeValue(shadow, 'DATE_EXPIRY')
if (fin != null && LocalDate.parse(fin.toString().substring(0,10)).isBefore(LocalDate.now()))
    return null          // matricula vencida -> sin vinculo academico
// ... resto del mapping actual
```

**Por qué esta vía y no mapear `validTo` en el usuario:**

1. **Simetría**: el canal laboral ya funciona así. Un solo patrón para los dos.
2. **Actúa sobre el vínculo, no sobre la persona.** La consolidación queda intacta: quien
   tenga contrato laboral o biblioteca vigente conserva lo suyo automáticamente. Con
   `validTo` en el usuario habría que reimplementar esa lógica a mano.
3. **No hay que inventar la regla de "sin ningún vínculo"**: emerge sola cuando los tres
   items están vacíos.
4. `DATE_EXPIRY` se renueva al rematricularse (inbound `strong` + recon diaria) → **la
   persona se reactiva sola**, sin intervención.

### Impacto medido

| | |
|---|---|
| Pierden el vínculo académico | **10.519** |
| ...de ellos, con contrato laboral vigente (conservan acceso) | **0** |
| ...de ellos, egresados con biblioteca vigente (conservan Koha) | **1.473** |
| **Quedan sin ningún vínculo → se retiran los accesos** | **9.046** |

## Orden de aplicación

1. ✅ **Ampliar el filtro de semestres** — *hecho hoy* (resource v197). Sin esto, 66 personas
   con matrícula en regla se habrían desactivado por no ser vistas. **Primero ver a todos los
   que tienen contrato; después retirar a quien no lo tiene.**
2. ⏳ **Esperar la recon de Estudiantes** (11:20) para que entren las **3.186** personas
   nuevas del feed ampliado.
3. ⏳ **Re-medir** los 9.046 sobre el feed corregido — parte de ellos puede estar entre las
   3.186.
4. ⏳ **Simular** el cambio en `liveAffiliationStudent` (preview, sin escribir).
5. ⏳ **Aplicar** y verificar sobre una muestra antes del lote.

## Lo que queda fuera y por qué

- **Los 565 ex-trabajadores archivados** con `faculty`/`staff` residual en LDAP: están
  deshabilitados (513 de 565, 0 habilitados). Limpiarlos dejaría 51 sin ninguna afiliación
  y 514 con `member` huérfano. Requiere decidir antes qué afiliación corresponde a un
  ex-trabajador (`affiliate` en eduPerson).
- **`validTo` en el usuario**: descartado como mecanismo principal por lo dicho arriba. Sigue
  teniendo sentido para el canal laboral con fecha conocida (**1.319** contratos a plazo con
  fin futuro), donde *anticipa* la baja en vez de esperar a que la fuente la refleje.
- **374 personas con solo `Confirmado`**: `Confirmado` no es el paso final obligatorio
  (53.516 `Matriculados` vs 2.856 `Confirmado` en 2026, mismo rango de fechas). Revisar aparte.
