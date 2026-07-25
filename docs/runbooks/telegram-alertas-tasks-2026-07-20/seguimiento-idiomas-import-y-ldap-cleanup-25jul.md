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

## Tarea 2 (actualización, misma tarde 25-jul) — Limpieza LDAP ejecutada sobre el alcance real: 248/248 CERRADA

**Autorización:** Alberto autorizó explícitamente ejecutar sobre el alcance real medido (248, no
22) — ver decisión pendiente #1 de la sección original de Tarea 2 más abajo. Este es el 3er
intento del encargo; los 2 anteriores fallaron por problemas de infraestructura (stream
watchdog / conexión API cerrada) justo al confirmar el OID del resource, sin llegar a tocar
nada — no hubo nada que revertir.

**Reconfirmación del universo (UNA sola query dirigida, no full-dump):** se reutilizó la
reconstrucción forense ya hecha (`ma_audit_event`/`ma_audit_delta`, 260 candidatos con firma
`FATAL_ERROR`+`noSuchAttribute`+rename de `uid`) y se validó su estado LDAP actual con un único
`ldapsearch` filtrado por los 260 `uid` exactos (no se repitió el full-dump de `ou=people`).
Resultado: **248 siguen sucios, 12 ya limpios solos, 0 ambiguos, 0 casos borde** — coincide
exactamente con la medición de la sesión anterior de hoy. Verificación adicional de seguridad:
0 colisiones de `old_uid` entre personas, 0 renombramientos encadenados, y **0 casos donde el
`old_uid` siga vivo como `uid=` de otra persona** (confirmado con un segundo `ldapsearch`
dirigido a los 248 `old_uid`) — descarta el riesgo de borrar el valor vigente de alguien más.

**Backup previo:** dump LDIF completo (todos los atributos) de las 260 personas antes de tocar
nada, en `.backups-prod-p0/2026-07-25-ldap-cleanup-248/BACKUP-pre-cleanup-260-full.ldif`
(gitignored, contiene PII — nunca a git).

**Ejecución:** 10 lotes de 25 (9×25 + 1×23 = 248), cada uno con:
1. PRE-check `ldapsearch` (confirma que el valor viejo sigue presente, `uid`/DN intactos).
2. `ldapmodify` **acotado estrictamente** a `delete: eduPersonUniqueId`/`delete: mail` con el
   valor literal exacto `<old_uid>@upeu.edu.pe` (nunca `uid` ni el DN) vía bind con la cuenta de
   servicio `cn=midpoint` (la misma que usa el resource en producción).
3. POST-check `ldapsearch` (confirma valor viejo ausente, valor nuevo correcto intacto,
   `uid`/DN sin cambio).
4. Checkpoint de conteo total `ou=people` (48.139 antes/durante/después, sin variación en
   ningún lote).

**Resultado: 10/10 lotes OK, 248/248 personas correctamente limpiadas, 0 residuales, 0 casos
ambiguos separados.** Verificación final consolidada sobre las 260: 248 limpios (antes sucios)
+ 12 ya-limpios sin tocar = 260/260 coherente, `uid`/DN intactos en el 100% de los casos, total
`ou=people` final = 48.139 (idéntico al baseline).

Progreso incremental de cada lote quedó registrado en
`.backups-prod-p0/2026-07-25-ldap-cleanup-248/progress.log` (gitignored) para permitir retomar
si esta ejecución se hubiera caído a medio camino — no hizo falta, terminó en una sola sesión.

**Nada más se tocó:** ni `uid`, ni el DN, ni ningún otro atributo, ni la configuración del
resource `LDAP-IdentityCache-UPeU` (`7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f`) — solo `ldapmodify`
directo contra el directorio, 0 PUT.

**Sección original (antes de la autorización de esta tarde), preservada para trazabilidad:**

### Tarea 2 (medición original, mañana 25-jul) — Limpieza LDAP de "los 22": DETENIDA por desajuste de alcance (no ejecutada)

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

## Verificación real ejecutada (sesión de la mañana, ambas tareas)

- Oracle LAMB: consultas de solo lectura vía `oracledb` (thick mode, Instant Client ARM64),
  cero DML.
- MidPoint PROD: lecturas directas a Postgres (`docker exec midpoint-midpoint_data-1 psql`)
  y REST GET de tasks — cero PATCH/PUT ejecutado.
- LDAP `.168`: `ldapsearch` de solo lectura con la cuenta admin — cero `ldapmodify` ejecutado.
- No se tocó ningún archivo de configuración del repo (`upeu/resources/*`, `upeu/roles/*`) —
  no aplica commit/push para esta sesión.

## Cierre (sesión de la tarde, 25-jul): Tarea 2 completada 248/248

- LDAP `.168`: 20 `ldapsearch` de verificación (pre/post por lote + reconfirmación de
  universo + chequeo de colisión de `old_uid`) + 10 `ldapmodify` (uno por lote), bind con
  `cn=midpoint`. Cero PUT, cero escritura en Oracle, cero cambio de `uid`/DN.
- Backup pre-cambio y log de progreso incremental en
  `.backups-prod-p0/2026-07-25-ldap-cleanup-248/` (gitignored — contiene PII real, nunca a
  git).
- Este archivo de runbook sí se commiteó/pusheó (no contiene PII, solo narrativa + conteos).
