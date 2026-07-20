# Koha para estudiantes nuevos: el "gap de recompute" NO existe — canario refutado (20-jul-2026)

> **⚠️ CORRECCIÓN 2026-07-20 (misma tarde, sesión posterior).** La afirmación de este
> documento *"Koha hoy es Lima-only por diseño, no por bug"* (línea 26-27) es **incorrecta**
> y quedó **retirada del código**. Esa frase describe el Koha **VIEJO** (`koha-ils.xml`, OID
> `9b5a7c81`, 4 instancias físicas separadas, MidPoint solo gobernaba Lima) — contexto que
> ya no aplica desde el repunte del 19-jul al Koha **NUEVO** consolidado (`koha-upeu.xml`,
> OID `e10a539a`, 1 instancia con 4 branches reales `BUL/BUJ/BUT/CIA`, multi-campus por
> diseño desde P1 4->1). El gate Lima-only en el `<condition>` de `AR-Koha-Patron-Pregrado`
> (y los otros 3 AR-Koha-Patron activos) era **deuda de la migración, no una decisión
> vigente** — el propio comentario del rol ya decía *"FUSIÓN 4 KOHA: eliminar este bloque"*.
> Se retiró el gate en los 4 roles (Pregrado/Posgrado/Faculty/Administrativo) el mismo
> 2026-07-20. El caso Jahaziel analizado abajo **sí era un gap real**, solo que su causa
> (gate obsoleto) no se cuestionó en el momento. Universo medido: ~11.148 holders en
> Juliaca/Tarapoto quedaban bloqueados por este mismo gate. Detalle completo en el mismo
> directorio de memoria del proyecto y en los propios XML de los 4 roles.

## Encargo original

Se pidió diseñar una task recurrente de `recomputation` (acotada por filtro) que corriera poco
después de `recon-oracle-lamb-estudiantes-daily` cada día, bajo la premisa de que la
reconciliación de Oracle LAMB Estudiantes **no** dispara la re-evaluación de la `<condition>`
de campus Lima en el inducement Koha del rol `AR-Koha-Patron-Pregrado` (vía `BR-Estudiante-Pregrado`),
y que por eso los estudiantes recién matriculados no llegaban a Koha sin un
`POST /users/{oid}?options=recompute` manual y separado.

Como canario se propuso `Jahaziel Ashly Pacompia Sanchez` (User oid
`6bf6aba0-1efb-4b63-8dda-833988c7d62f`, name `202612392`), supuestamente matriculado hoy en
Pregrado 2026-2, con Oracle Estudiantes y LDAP `LINKED` pero cero shadow en `koha-upeu`.

## Verificación en vivo — el canario es un falso positivo

`GET /users/6bf6aba0-...` muestra `extension/campusStudent = JULIACA`, **no LIMA**. El gate de
campus del inducement Koha (`AR-Koha-Patron-Pregrado`, ver `condition` en su XML) es explícito:

```groovy
return (cs == 'LIMA') || (cw == 'LIMA') || (guest != null) || hasLib
```

Juliaca queda fuera **a propósito** — el comentario del rol lo documenta: *"FUSIÓN 4 KOHA:
eliminar este bloque `<condition>` para reactivar provisioning multi-campus"*. Koha hoy es
Lima-only por diseño, no por bug.

Se ejecutó el recompute puntual pedido (`POST /users/6bf6aba0-...?options=recompute` con body
`<objectModification/>` vacío — el endpoint exige body, `options=recompute` solo como query param
da `400`). Resultado: **sin cambios**. Antes y después, 2 shadows (Oracle Estudiantes
`6a91f7e1-...` + LDAP `7b4e1c2d-...`), cero Koha. Es el comportamiento **correcto** dado
Juliaca — no hay ningún gap que este caso demuestre.

## La reconciliación diaria YA provisiona Koha para estudiantes Lima nuevos, sin recompute separado

Se buscó un canario real (LIMA, activo, archetype student) y se verificó la hipótesis contra
datos reales de PROD en vez de asumirla:

- **60/60** estudiantes LIMA activos con `createTimestamp` de HOY (foco creado por primera vez,
  primera matrícula que MidPoint ve de esa persona) ya tienen su shadow `koha-upeu`. Ejemplo
  verificado: oid `88fe2b2f-0933-4798-8fbd-0944e63bdf61` (name `324107021`) — User creado
  `2026-07-20T09:57:45.945-05:00`, shadow Koha creado `2026-07-20T09:57:45.990-05:00` (mismo
  segundo), `createChannel=reconciliation`, `synchronizationSituation=linked`.
- **200/200** estudiantes LIMA activos reactivados (`activation/enableTimestamp` desde el
  6-jul-2026 — ciclo leaver→rejoiner) tienen ≥3 shadows incluyendo Koha, con
  `modifyChannel=reconciliation` apuntando al `taskRef` de `recon-oracle-lamb-estudiantes-daily`
  (oid `9bcfb273-3d8e-4acb-84b0-e7c8b490975b`).
- Sobre el universo completo de estudiantes LIMA activos consultado (10.000, tope de la query),
  solo **1** caso con menos de 3 shadows — ver sección siguiente, es un caso de dato duplicado,
  no de recompute faltante.

Esto confirma en vivo lo que el propio comentario de `recon-oracle-lamb-estudiantes.xml` (líneas
17-21) ya documentaba desde el 19-jul: *"el reaction linked->synchronize ya empuja el pipeline
downstream incluido koha-upeu sin necesitar una task de recompute batch separada"* — la
reconciliación de UN resource (Oracle Estudiantes) dispara el clockwork completo del foco
(inbound → template → inducements/constructions → outbound a TODOS los proyectos, incluido
Koha), no solo al resource reconciliado. Es el diseño estándar de MidPoint, no una casualidad de
hoy.

Contexto adicional: `recon-oracle-lamb-estudiantes-daily` nunca había corrido en su primer cron
de las 06:20 (quedó `suspended` durante la ventana, ver
`estudiantes-daily-nunca-corrio-20jul.md` del mismo runbook) y se disparó manualmente hoy
14:25:42–15:05:34 UTC, 24.808/24.925 (99,53%). Los 60+200 casos verificados arriba son la
evidencia de ESA corrida.

## Decisión: NO se crea la task recurrente de recompute

La premisa del encargo está refutada por evidencia en vivo. Crear una `recomputation` diaria
adicional sería automatización para un problema que no existe en el estado actual de PROD —
carga innecesaria sin beneficio, contra el principio de "MidPoint suma, nunca resta" y de mínima
huella. **No se creó ningún task XML nuevo.**

Si en el futuro reaparece la pregunta "¿por qué el estudiante X no llegó a Koha?", el primer
diagnóstico debe ser (en este orden):
1. `extension/campusStudent` (o `campusWorker`) del foco — ¿es `LIMA`? Si no, es exclusión
   correcta por política multi-campus, no un bug.
2. ¿`recon-oracle-lamb-estudiantes-daily` corrió exitosamente anoche? (`lastRunFinishTimestamp`,
   `resultStatus`).
3. Solo si ambos son correctos y aun así falta el shadow, investigar caso puntual (ver siguiente
   sección para el único patrón real encontrado hoy).

## El único caso real encontrado: duplicado de persona en origen Oracle, no bug de IGA

User oid `9ebf2292-acdd-4f36-9d05-91f7374d49ad` (name `202613758`, Ariana Alessandra Yance Ccesa,
LIMA, activo, con `AR-Koha-Patron-Pregrado` en `roleMembershipRef` — la POLICY sí lo incluye)
tiene solo 2 shadows: LDAP + un link **huérfano** al resource Koha viejo archivado
(`9b5a7c81-...`, `administrativeAvailabilityStatus=maintenance`). Se probó el recompute puntual
(mismo mecanismo que en Jahaziel) y **falló** con:

```
Couldn't add shadow object to the repository. Shadow object already exist.
constraint violation: m_shadow_default_primidval_objcls_resrefoid_key
Key (primaryidentifiervalue, objectclassid, resourcereftargetoid)=(11129, 10, e10a539a-...) already exists.
```

Causa raíz confirmada por consulta directa a `m_shadow` (Postgres, solo lectura) + REST: el
borrowernumber Koha `11129` ya está `linked` a **otro** User, oid `9204c289-95da-47cb-b0f6-d8146144c5b3`
(name `323200401`, mismo nombre "ARIANA ALESSANDRA YANCE CCESA"). Ambos Users comparten el
**mismo DNI** (`extension/taxId = urn:schac:personalUniqueID:pe:DNI:PE:72066573`,
`lambDocNum=72066573`) pero con **dos códigos institucionales distintos** (`202613758` y
`323200401`) — la misma persona existe DOS veces en Oracle LAMB con dos matrículas/códigos
diferentes, correlacionadas a dos focos MidPoint separados. `202613758` además tiene
`terminationDateStudent=2026-07-03` y un ciclo disable(04-jul)→enable en su `activation`, lo que
sugiere que es el código "viejo"/inactivo de la persona y `323200401` el vigente — pero eso lo
debe confirmar quien gestiona el dato origen, no MidPoint.

Es la **misma clase de excepción** ya catalogada el 19-jul para el caso `05436990` (memoria
`koha-escalamiento-produccion-diagnostico-2026-07-19.md`: *"duplicado de persona en Oracle
origen (no split-brain MidPoint)"*), ahora encontrada también del lado Estudiantes. El guardarraíl
de unicidad de `m_shadow` (constraint `primaryidentifiervalue+objectclassid+resourcereftargetoid`)
está haciendo exactamente lo que debe: impedir que se cree un segundo patron Koha para la misma
persona física. **No es un bug a arreglar en MidPoint ni con recompute** — el recompute NUNCA va
a lograr crear ese shadow mientras el dato origen tenga dos códigos institucionales para la misma
persona. `dup_card=0` sigue sagrado (ver `NUNCA-PUT-resources-schema-cache.md` / memoria Koha).

### Pendiente — fuera de alcance de hoy

- Escalar a quien gestiona `MOISES`/`DAVID` (dato origen Oracle LAMB) el duplicado de persona
  DNI `72066573` (`202613758` vs `323200401`) para que decidan cuál código institucional es el
  vigente y depuren/mergeen el otro en origen. Hasta entonces `202613758` seguirá sin Koha por
  diseño (constraint de unicidad), correctamente.
- No se buscaron más casos similares fuera de la muestra LIMA (Posgrado/CEPRE/Idiomas/otros
  campus no se revisaron) — si aparece otro caso "estudiante con rol Koha en policy pero sin
  shadow", repetir este mismo diagnóstico (buscar colisión de `primaryidentifiervalue` en
  `m_shadow` sobre `koha-upeu`) antes de asumir que es un problema de orquestación.

## Comandos usados (referencia)

Verificación de campus/afiliación real de un foco:
```
GET /midpoint/ws/rest/users/{oid}
```

Recompute puntual (el endpoint exige body, aunque sea una modificación vacía):
```
POST /midpoint/ws/rest/users/{oid}?options=recompute
Content-Type: application/xml
<objectModification xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3"/>
```

Búsqueda acotada por filtro (archetype + extensión + lifecycleState), vía REST:
```
POST /midpoint/ws/rest/users/search
Content-Type: application/xml
<query xmlns="http://prism.evolveum.com/xml/ns/public/query-3" xmlns:c="..." xmlns:sb="urn:sciback:midpoint:person">
  <filter><and>
    <ref><path>c:archetypeRef</path><value oid="3037fbd2-db02-4ffd-8b1a-83fab5e686aa" type="c:ArchetypeType"/></ref>
    <equal><path>c:extension/sb:campusStudent</path><value>LIMA</value></equal>
    <equal><path>c:lifecycleState</path><value>active</value></equal>
  </and></filter>
</query>
```

Localizar el owner real de un shadow por su oid (búsqueda inversa por `linkRef`):
```
POST /midpoint/ws/rest/users/search
<query ...><filter><ref><path>c:linkRef</path><value oid="{shadowOid}" type="c:ShadowType"/></ref></filter></query>
```

Consulta directa de solo-lectura a `m_shadow` (Postgres, columna real `primaryidentifiervalue`,
no vía REST cuando hay colisión):
```
docker exec midpoint-midpoint_data-1 psql -U midpoint -d midpoint -t -c \
  "select oid, nameorig, resourcereftargetoid, objectclassid, primaryidentifiervalue, exist \
   from m_shadow where resourcereftargetoid='{resourceOid}' and primaryidentifiervalue='{valor}';"
```
