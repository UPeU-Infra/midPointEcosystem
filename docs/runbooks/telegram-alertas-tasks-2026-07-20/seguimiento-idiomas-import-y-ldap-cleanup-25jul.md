# Seguimiento (25-jul): import Idiomas destrabado + intento de limpieza LDAP de los "22"

Sesión de seguimiento sobre 2 pendientes abiertos en la memoria del 19/20-jul. Ejecutado
en vivo contra PROD (`midpoint.upeu` .166, Oracle LAMB `.13.9` solo lectura, LDAP `.168`).
Ningún PUT en resources; ninguna escritura en Oracle.

## Tarea 1 — Import masivo Idiomas: CERRADA, sin acción manual necesaria

**Medición en vivo (Oracle, solo lectura):** se replicó el `searchScript` real desplegado en
`upeu/resources/oracle-lamb/estudiantes.xml` (resource `6a91f7e1-...`, "Oracle LAMB
Estudiantes v3") con el filtro OLD (`ID_SEMESTRE IN (267,279,283)`) y el filtro NEW (los 3 IDs
oficiales OR Idiomas con módulo `FECHA_FIN >= SYSDATE`). Resultado hoy (6 días después del fix
del 19-jul): universo OLD=25.117, NEW=25.138, delta=**21** (no 12 — el universo crece con el
tiempo, semestres de Idiomas nuevos como 289 siguen apareciendo; 0 personas removidas por el
fix, confirmando que es estrictamente aditivo). Verificado con muestreo detallado (`NIVEL_ENSENANZA`,
módulos, fechas) que los 21 son genuinamente Idiomas con módulo vigente, no ruido.

**Estado de sincronización de los 21 (verificado en Postgres de MidPoint, no adivinado):**
los 21 YA tienen shadow vivo (`exist=true`, `dead=NULL`) en los 3 resources relevantes —
Oracle LAMB Estudiantes, Koha ILS UPeU consolidado, y LDAP-IdentityCache — con
`fullSynchronizationTimestamp` de **hoy mismo** (25-jul, entre 11:21 y 12:30 UTC). Cero
duplicados (`COUNT(DISTINCT oid) por CODIGO` = 1 en los 21 casos).

**Causa: `recon-oracle-lamb-estudiantes-daily` (activada 20-jul) ya venía absorbiendo el
universo destrabado sin necesidad de import dirigido.** La task está corriendo en vivo ahora
mismo (iniciada 06:20 hora Lima de hoy, progreso 12.086 de ~25.138 al momento de revisar,
sin haber avanzado en los últimos ~4 minutos de observación — posible desaceleración, no
investigada más a fondo por estar fuera del alcance de esta sesión). Los 21 destrabados por
el fix de Idiomas ya fueron alcanzados por esta corrida (o por corridas previas) antes de
cualquier posible degradación posterior — no se requirió ninguna intervención manual.

**Balance final Tarea 1: 21/21 (100%) con shadow Estudiantes+Koha+LDAP vivo, 0 duplicados,
0 import manual ejecutado (innecesario).**

**Nota lateral no accionada (fuera de alcance):** la task diaria de Estudiantes muestra
`executionState=running` desde las 06:20 con progreso estancado en 12.086/~25.138 durante
la ventana de observación de esta sesión; el `diagnosticInformation` embebido en el propio
objeto Task es un thread-dump histórico del 23-jul (no de hoy), por lo que no se usó como
evidencia de un cuelgue actual. No se tocó la task (ni restart ni suspend) — se deja para que
Alberto decida si amerita seguimiento aparte.

## Tarea 2 — Limpieza LDAP de "los 22": DETENIDA por desajuste de alcance (no ejecutada)

**No se encontró la lista exacta de los 22 en memoria/runbooks/scratchpad** (búsqueda
exhaustiva en `~/.claude/projects/.../memory/*.md`, en el runbook del 20-jul, y en los
scratchpads de sesiones de esa fecha — ninguno persiste los 22 UIDs). Se reconstruyó la
población afectada de dos formas independientes:

1. **Heurística LDAP en vivo** (entradas con >1 valor en `mail` o `eduPersonUniqueId`):
   394 entradas en todo `ou=people`. Rechazada como base de trabajo — la inmensa mayoría son
   personas con 2 direcciones institucionales legítimas (alias personal + institucional),
   sin relación con el bug de renombrado de `uid`; usar este conjunto habría arriesgado
   borrar un valor válido.
2. **Reconstrucción forense vía audit log de MidPoint** (`ma_audit_delta`/`ma_audit_event`,
   filtrado por `resourceoid` del recurso LDAP y `status=FATAL_ERROR` con patrón
   `noSuchAttribute` + `remove:uid=<viejo>`): esto SÍ reproduce la causa raíz documentada
   ("el modify atómico fallaba al intentar remover un `uid` ya removido, dejando
   `mail`/`eduPersonUniqueId` sin actualizar"). Resultado: **260 personas distintas**, no 22,
   con esta firma exacta el 19-jul (ventana horaria 13:30–13:53 UTC y 01:02–01:06 UTC del
   20-jul, ambas dentro de la misma sesión de trabajo en hora Lima).

**Cruce contra el estado LDAP actual (25-jul) de esas 260:** 248 siguen sucias hoy (una
todavía tiene el valor viejo `<old_uid>@upeu.edu.pe` conviviendo con un valor nuevo correcto
en `mail` y/o `eduPersonUniqueId`); solo 12 ya quedaron limpias solas (probablemente por una
reconciliación posterior que sí completó el ciclo completo). De las 248:
- 247 tienen `eduPersonUniqueId` sucio (valor viejo `<old_uid>@upeu.edu.pe` + un identificador
  persistente distinto, probablemente ligado a `ID_PERSONA` de Oracle — este SÍ es el valor
  correcto por semántica eduPerson: identificador persistente, no reasignable, distinto del
  `uid`/código que sí puede renombrarse).
- 55 tienen además `mail` sucio (valor viejo `<old_uid>@upeu.edu.pe` + el correo real
  `nombre.apellido@upeu.edu.pe`).

**Decisión: NO se ejecutó ningún `ldapmodify`.** El bug real y su firma están bien
identificados (y el criterio "cuál valor es el correcto" quedó claro en el proceso: el que
coincide literalmente con `<old_uid>@upeu.edu.pe` es el residuo a remover), pero el
**alcance verificado (248) es ~11× mayor que el autorizado hoy ("22 casos, pendiente
pequeño y de bajo riesgo")**. Ejecutar una limpieza de 248 personas — tocando el atributo
ancla de RIMS (`eduPersonUniqueId`) — excede el mandato de esta sesión y el criterio de
"bajo riesgo" bajo el que se autorizó. Esto es exactamente el caso previsto por la regla
"si hay ambigüedad, detente y repórtalo en vez de adivinar" — aquí la ambigüedad es de
**alcance**, no de cuál valor borrar.

**Nada fue modificado en LDAP.** Solo se ejecutaron `ldapsearch` de lectura.

**Pendiente para que Alberto decida:**
1. ¿El alcance real de la limpieza es 248, no 22? (Aparenta ser la misma clase de bug que
   afectó al lote masivo de renombrado de códigos Juliaca/Tarapoto `324xxxxxx→2026xxxxx` del
   19-jul, mucho más grande que el subconjunto puntual reportado como "22" en su momento.)
2. Si se autoriza, el patrón de fix es mecánico y seguro de automatizar con verificación
   por persona: para cada una de las 248, `ldapmodify` con `delete: mail`/`eduPersonUniqueId`
   sobre el valor literal `<old_uid>@upeu.edu.pe` únicamente (nunca tocar `uid` ni el DN),
   verificando con `ldapsearch` antes/después — mismo patrón ya usado en la sesión del 20-jul
   para casos individuales, escalado con un guardarraíl de conteo exacto por lote.
3. Vale la pena revisar si la reconciliación diaria (que ya cerró 12 de las 260 por sí sola)
   terminará cerrando más por su cuenta sin intervención manual, igual que ocurrió con
   Tarea 1.

## Verificación real ejecutada (ambas tareas)

- Oracle LAMB: consultas de solo lectura vía `oracledb` (thick mode, Instant Client ARM64),
  cero DML.
- MidPoint PROD: lecturas directas a Postgres (`docker exec midpoint-midpoint_data-1 psql`)
  y REST GET de tasks — cero PATCH/PUT ejecutado.
- LDAP `.168`: `ldapsearch` de solo lectura con la cuenta admin — cero `ldapmodify` ejecutado.
- No se tocó ningún archivo de configuración del repo (`upeu/resources/*`, `upeu/roles/*`) —
  no aplica commit/push para esta sesión.
