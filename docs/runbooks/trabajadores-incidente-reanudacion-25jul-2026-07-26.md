# Incidente — reanudación no documentada de `recon-oracle-lamb-trabajadores-daily` (25-jul), descubierto durante la validación del guardarraíl (26-jul)

## Contexto

Tarea encargada: aplicar el guardarraíl de correlación diseñado en
[`docs/specs/trabajadores-correlation-guardrail-2026-07-20.md`](../specs/trabajadores-correlation-guardrail-2026-07-20.md)
al resource `Oracle LAMB Trabajadores v3` (oid `6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21`) y validarlo
con un canario dirigido sobre el shadow huérfano conocido de Orlando Cortez Bazantes
(`0c1660ee-b79f-48c3-abc8-5c852ad8226c`, COD_APS `00534601`), **antes** de decidir si se reactiva
`recon-oracle-lamb-trabajadores-daily` (oid `23b9fde4-6a5f-4c84-9370-0971fb27be73`), que había
quedado **suspendida** el 2026-07-20 tras el incidente original de duplicados.

## Parte 1 — el guardarraíl SÍ se aplicó y verificó limpio

Ver detalle completo en el spec §5b.1. Resumen: `PATCH` (XML, `objectModification`, nunca `PUT`)
de 3 elementos exactos (`correlation` reemplazado por el correlator compuesto 2-tier +
`thresholds`, nueva `reaction situation=disputed`, `evaluationPhases` en el inbound
`cod-aps-to-personalNumber`). Backup previo:
`/home/juansanchez/backups-e21/e21_pre-correlation-guardrail_20260726_033546.xml` (version 321).
`version` 321→322. Post-PATCH verificado: `<schema>` idéntico (comparación JSON completa, no solo
conteo de elementos), `connectorRef`/`capabilities`/`connectorConfiguration` idénticos, **test
connection 15/15 `success`**.

## Parte 2 — el canario reveló un incidente distinto, no relacionado con el PATCH de hoy

Antes de ejecutar el `import` dirigido sobre el shadow de Orlando, se verificó su estado real
(protocolo de esta sesión: nunca asumir, siempre consultar PROD primero). Resultado inesperado:

```
oid                                   | nameorig  | synchronizationsituation | correlationsituation
0c1660ee-b79f-48c3-abc8-5c852ad8226c  | 00534601  | LINKED                   | NO_OWNER
```

El shadow **ya no está huérfano**. Está vinculado a un `User` (`3e756b31-1455-41a2-94b3-315963af0937`,
`name=00534601`, `personalNumber=00534601`, `lambIdPersona=202895`) que es un **duplicado nuevo** de
Orlando, distinto del real (`2dba749b-eb5b-4d1e-82bc-77b7a8b0de0a`, `name=200610808`,
`lambDocNum=CE:000534601`, `lambIdPersona=10041`, verificado intacto y sin cambios).

**Es el mismo patrón exacto del incidente del 20-jul, ocurrido de nuevo, fuera de esta sesión.**

### Causa raíz — evidencia de auditoría

```sql
select timestamp, eventtype, eventstage, outcome, initiatorname, channel
from ma_audit_event
where targetoid = '23b9fde4-6a5f-4c84-9370-0971fb27be73'
order by timestamp desc limit 10;
```

```
2026-07-25 14:18:40 UTC  RUN_TASK_IMMEDIATELY  EXECUTION  UNKNOWN  administrator  rest
2026-07-25 14:18:40 UTC  RUN_TASK_IMMEDIATELY  REQUEST             administrator  rest
2026-07-25 14:18:38 UTC  RESUME_TASK           EXECUTION  UNKNOWN  administrator  rest
2026-07-25 14:18:37 UTC  RESUME_TASK           REQUEST             administrator  rest
2026-07-20 14:33:59 UTC  SUSPEND_TASK          EXECUTION  UNKNOWN  administrator  rest  ← cierre documentado del 20-jul
```

La tarea fue **reanudada y ejecutada manualmente el 25-jul**, sin que exista una decisión
explícita registrada en memoria/runbooks para hacerlo — contradice directamente la instrucción
escrita en el cierre del 20-jul ("**No reactivar sin decisión explícita de Alberto**").

La corrida real fue de **09:18:40 a 09:40:12** (hora servidor, -05:00). Coincide al segundo con la
creación de shadows Koha/LDAP reales (`createtimestamp` 09:19:02–09:19:08 -05:00) para los
duplicados listados abajo.

**Hipótesis más probable del origen** (no confirmada, pero la más consistente con la evidencia
disponible): hubo trabajo sobre este mismo resource ese mismo día — un diff sin commitear
encontrado en el repo local al iniciar esta sesión (`upeu/resources/oracle-lamb/trabajadores.xml`,
fix "CIA" fechado 2026-07-25, sobre el mapping `sede-nombre-to-campusWorker`, alcance documentado
de solo 2 personas) sitúa una sesión de trabajo ese día sobre el mismo `trabajadores.xml`. Es
plausible que esa sesión reanudara la tarea para validar su fix puntual, sin prever que
`RUN_TASK_IMMEDIATELY` dispara la reconciliación **completa** del resource (~7.500 shadows), no
solo el alcance acotado de 2 personas de su propio fix. **No se puede confirmar con certeza cuál
sesión/agente ejecutó la reanudación** — el audit log identifica al usuario `administrator` (la
cuenta de servicio de todas las sesiones de agente contra REST), no a una sesión específica.

### Impacto medido (100% lectura — `psql`/REST, ninguna escritura adicional en esta investigación)

```sql
-- Users nuevos en la ventana de la corrida
select count(*) from m_user
where createtimestamp between '2026-07-25 14:15:00+00' and '2026-07-25 14:50:00+00';
-- 97

-- duplicados exactos por personalNumber (User nuevo vs User más antiguo con el mismo valor)
select new.oid, new.nameorig, new.personalnumber, old.oid, old.nameorig
from m_user new
join m_user old on old.personalnumber = new.personalnumber and old.oid <> new.oid
                and old.createtimestamp < new.createtimestamp
where new.createtimestamp between '2026-07-25 14:15:00+00' and '2026-07-25 14:50:00+00';
```

| Nuevo (`User` duplicado) | `personalNumber` | Viejo (`User` real) | Downstream provisionado |
|---|---|---|---|
| `3e756b31-...` `00534601` | `00534601` | `2dba749b-...` `200610808` (Orlando) | **Koha + LDAP** (real, 09:19:07–08) |
| `bcc29e66-...` `001261673` | `001261673` | `7844b5da-...` `201521241` (Juan Elías Mejía Coello) | **LDAP** (real, 09:19:02); Koha no |

Búsqueda adicional por `fullName` exacto (no capturada por el join de `personalNumber`, porque el
valor de `personalNumber` difiere entre el `User` nuevo y el viejo):

| Nuevo | `fullName` | Viejo | `personalNumber` nuevo vs viejo | Downstream | Nota |
|---|---|---|---|---|---|
| `b9969b58-...` `001642451` | Evanilda Ruth Valeriano Tiñini | `4799ae35-...` `201520024` | `001642451` vs `201520024` (**distintos** — códigos de afiliación distinta) | **Koha + LDAP** (real, 09:19:03–04) | Caso **nuevo**, no identificado en el 20-jul: se había clasificado como "alta nueva genuina" (Grupo B). En realidad es la misma persona bajo dos identificadores UPeU de afiliaciones distintas (worker vs. student/alumni) — problema de identidad multi-perfil, no de correlación de un solo resource. Ver `docs/specs/multi-profile-canonical/07-identity-lifecycle-design.md`. |
| `eeed7254-...` `000614192` | Luzirene Gomes de Alcantara | `49945169-...` `00614192` | drift de padding (ya documentado, spec §4) | ninguno (`archived`) | Recurrencia del caso ya conocido; sin impacto downstream porque el guardarraíl `FEC_TERMINO` preexistente correctamente no la materializó. |

**Total: 4 duplicados nuevos confirmados, 3 activos y provisionados a sistemas reales (Koha y/o
LDAP), 1 archivado sin impacto.** Esta auditoría (por `personalNumber` exacto + `fullName` exacto)
**no es exhaustiva** de los 97 `User` creados — es la misma metodología de bajo costo usada el
20-jul, no un barrido caso-por-caso completo.

Balance agregado del resource, comparado con el cierre documentado del 20-jul:

| Situación | 20-jul (cierre) | 26-jul (ahora) |
|---|---:|---:|
| `LINKED` | 7.399 | 7.368 |
| `UNMATCHED` | 90 | 2 |
| `UNLINKED` | ~42 | 0 |
| `DISPUTED` | 1 | 1 |
| **Total** | **7.532** | **7.371** |

La caída neta de shadows totales (161) y del backlog `UNMATCHED`/`UNLINKED` (132→2) es consistente
con que la corrida procesó legítimamente la gran mayoría del backlog acumulado desde el 20-jul
(altas y bajas reales de 5 días) — **solo 3-4 casos degeneraron en duplicado**, no todo el universo
expuesto.

### Acción de protección tomada de inmediato

La tarea tenía su próximo disparo programado (`cron 0 0 6 * * ?`, hora servidor) a menos de
2h15min del hallazgo. Se **re-suspendió**:

```bash
POST /midpoint/ws/rest/tasks/23b9fde4-6a5f-4c84-9370-0971fb27be73/suspend   # -> 204
```

Verificado: `executionState=suspended`, `schedulingState=suspended`.

**Justificación de por qué esto NO es "escalar el alcance" de la tarea encargada:** es la
restauración del último estado explícitamente autorizado (suspendida, decisión del 20-jul). Dejar
la tarea corriendo, sabiendo que ya recreó el incidente una vez y que dispararía de nuevo en <2.5h,
habría sido la opción imprudente. No se tocó ningún otro objeto del sistema más allá de este
`suspend`.

### Qué NO se hizo (fuera de alcance de hoy, requiere decisión de Alberto)

- **No se remediaron** los 3 duplicados activos (Orlando, Juan Elías, Evanilda) ni sus shadows
  downstream en Koha/LDAP. La remediación requiere el mismo protocolo cuidadoso caso-por-caso del
  20-jul (backup, habilitar temporalmente el guardarraíl de `delete`, verificar contra los sistemas
  reales vía `ldapsearch`/`mysql`, no solo MidPoint).
- **No se ejecutó ningún canario de reemplazo** (ni sobre Orlando en su estado actual, ni sobre
  otro de los 10 casos del bucket "atrapables" que siguen intactos) — las reglas de esta tarea
  exigen detenerse y reportar antes de escalar a cualquier otra acción en vivo.
- **No se investigó a fondo** qué sesión/agente específico reanudó la tarea (el audit log no lo
  distingue más allá de "administrator" vía REST).

## Recomendación

Ver `docs/specs/trabajadores-correlation-guardrail-2026-07-20.md` §6 (actualizado hoy) para la
lista completa y ordenada de próximos pasos. Resumen: (1) remediar los 3 duplicados activos, (2)
entender/cerrar el proceso que permitió la reanudación silenciosa, (3) ampliar el escalamiento a
DBAs del patrón "mismo nombre, distinto `ID_PERSONA`/identificador" más allá de los 2 casos
originales, (4) recién entonces completar la validación del guardarraíl sobre uno de los 10 casos
aún intactos, (5) evaluar backfill de `personalNumber` y reactivación **documentada** de la tarea.

## Archivos relacionados

- `docs/specs/trabajadores-correlation-guardrail-2026-07-20.md` (diseño + aplicación + este
  hallazgo, §5b/§6).
- `docs/runbooks/telegram-alertas-tasks-2026-07-20/tarea3-resultado-200610808-91-personas.md`
  (incidente original, 20-jul).
- `upeu/resources/oracle-lamb/trabajadores.xml` — diff local sin commitear al inicio de esta
  sesión (fix "CIA" 2026-07-25, ya aplicado a PROD como version 321 antes del guardarraíl de hoy;
  pendiente de commit, fuera de alcance de esta tarea).
