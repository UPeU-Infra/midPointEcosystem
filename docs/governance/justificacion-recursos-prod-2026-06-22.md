# Justificación técnica — Ampliación de disco y RAM del servidor MidPoint PROD

**Proyecto:** IGA UPeU (Identity Governance & Administration)
**Servidor:** `midpoint.upeu` (192.168.15.166) — MidPoint 4.10.2 sobre Docker + PostgreSQL nativo
**Fecha:** 2026-06-22
**Autor:** DTI / Infraestructura — J. Alberto Sánchez
**Dirigido a:** Infraestructura (provisión de recursos del host PROD)

---

## 1. Resumen ejecutivo

Se solicita **ampliar el disco** del servidor MidPoint de producción de **67 GB a 150 GB** (mínimo) y **ampliar la RAM de 16 GB a 24 GB**.

Motivos, con cifras reales medidas en PROD:

- El volumen raíz (67 GB) llegó al **98 % de uso** (63 GB ocupados, 1,5 GB libres). La base de datos `midpoint` pesa **45 GB**, de los cuales **38 GB (84 %) son auditoría** (1,74 millones de registros de deltas antes/después de cada cambio de identidad).
- MidPoint **no almacena "solo metadatos"**: el repositorio guarda una *shadow* (réplica local del estado) por **cada cuenta en cada uno de los ~7 sistemas conectados**, y el subsistema de auditoría guarda el **delta completo (antes/después) de cada operación** — esto es comportamiento documentado y de diseño, no un defecto de configuración.
- El host tiene 16 GB de RAM con el heap de la JVM configurado en 9 GB; las operaciones masivas del pipeline IGA (recompute/reconciliación sobre **35.450 usuarios**) ya provocaron un incidente **OutOfMemory** y dejaron el sistema "en recuperación post-OOM".
- Para liberar el espacio de auditoría hace falta `pg_repack` / `VACUUM FULL`, que en PostgreSQL **requiere espacio libre adicional del orden del tamaño de la tabla** a compactar (~35 GB). Hoy no hay margen para ejecutarlo: por eso el disco no se libera solo.

---

## 2. Por qué MidPoint NO es "solo metadatos" y consume disco

Existe la idea de que un IGA "solo guarda identidades y esquemas", por lo que su huella en disco debería ser pequeña. Es incorrecto. Por diseño documentado, MidPoint mantiene en su repositorio PostgreSQL **dos grandes categorías de datos voluminosos**: (a) una réplica local del estado de cada cuenta de cada sistema conectado (*shadows*), y (b) el registro de auditoría con el **delta completo** de cada cambio.

### 2.1. El repositorio guarda objetos serializados completos, no punteros

La documentación del repositorio nativo PostgreSQL confirma que MidPoint serializa el objeto completo y los deltas dentro de la fila de la base de datos:

> "serialized objects (`fullObject`, `delta`) are stored as JSON by default (saves space)... extensions are stored in `JSONB` columns inline with the rows."
> — Evolveum, *Native PostgreSQL Repository*, https://docs.evolveum.com/midpoint/reference/repository/native-postgresql/

Es decir, cada objeto (usuario, rol, org, shadow) lleva su representación completa serializada (`fullObject`), y cada modificación lleva su `delta` serializado. No son "pequeños metadatos".

### 2.2. Una *shadow* por cada cuenta en cada sistema conectado (réplica de estado)

MidPoint crea y persiste un objeto **shadow** por cada cuenta que existe (o existió) en cada *resource* conectado. La documentación lo describe como una proyección/representación local persistente del objeto remoto:

> "Resource object shadows are objects in an IDM repository... Resource object shadows may cache the information from their particular resource object to speed up information access."
> — Evolveum, *Shadow Objects*, https://docs.evolveum.com/midpoint/reference/resources/shadow/

En UPeU PROD hay **~7 resources conectados** (Oracle LAMB ×4, OpenLDAP, Microsoft Entra ID, Koha). Con **35.450 usuarios**, cada uno con presencia potencial en varios sistemas, esto genera **decenas de miles de shadows** persistentes en el repositorio. Cada shadow es una fila con su `fullObject` serializado. Esto multiplica el almacenamiento: no es el tamaño de "una identidad", es el tamaño de "el estado de todas las cuentas en todos los sistemas".

### 2.3. La auditoría guarda el delta completo (antes/después) de CADA operación — el gran consumidor

El subsistema de auditoría nativo registra, por cada evento, **todos los deltas asociados** (los cambios concretos aplicados a los objetos):

> "Each record can have multiple deltas associated with it, these are stored in `ma_audit_delta`."
> — Evolveum, *Native Audit*, https://docs.evolveum.com/midpoint/reference/repository/native-audit/

La misma documentación reconoce que esto crece y que por eso existen mecanismos de limpieza y particionado:

> "MidPoint already has one mechanism to clean up the audit tables - the precreated Cleanup task, executed once a day." (con política basada en `maxAge` o `maxRecords`); y para alto volumen, "declarative partitioning by range" para poder descartar particiones enteras.
> — Evolveum, *Native Audit*, https://docs.evolveum.com/midpoint/reference/repository/native-audit/

La retención por defecto que trae MidPoint es de **3 meses**:

> ```xml
> <c:cleanupPolicy>
>   <c:auditRecords><c:maxAge>P3M</c:maxAge></c:auditRecords>
>   <c:closedTasks><c:maxAge>P1M</c:maxAge></c:closedTasks>
> </c:cleanupPolicy>
> ```
> "the Cleanup task removing all audit records older than three months."
> — Evolveum, *Removing Obsolete Information*, https://docs.evolveum.com/midpoint/reference/deployment/removing-obsolete-information/

**Consecuencia:** cada vez que el pipeline IGA recalcula (recompute) o reconcilia un foco, se generan deltas que se auditan. Durante las fases de migración del proyecto el caudal fue de **100.000 a 300.000 eventos de auditoría por día**. A ese ritmo, incluso con retención reducida, la auditoría domina el tamaño de la base.

### 2.4. Evidencia medida en PROD UPeU (caso real)

| Componente | Tamaño | % de la DB | Qué es |
|---|---:|---:|---|
| `ma_audit_delta_default` | **35 GB** (32 GB en TOAST) | 78 % | Deltas serializados antes/después de cada cambio (~1,74 M registros) |
| `ma_audit_event_default` | 2,15 GB | 5 % | Cabecera de cada evento de auditoría |
| **Subtotal auditoría** | **~38 GB** | **84 %** | — |
| `m_user`, `m_shadow_*`, `m_assignment`, etc. | ~7 GB | 16 % | Identidades, shadows, asignaciones, roles, orgs |
| **Total DB `midpoint`** | **~45 GB** | 100 % | — |

Escala del tenant: **35.450 usuarios, 122 orgs, 72 roles**, ~7 resources → decenas de miles de shadows.

> Nota técnica (evidencia empírica local, sin cita documental específica): en PostgreSQL un `DELETE` de registros de auditoría **marca las filas como muertas pero no devuelve el espacio físico al sistema operativo**. Recuperar disco requiere `VACUUM FULL` o `pg_repack`, que reescriben la tabla en una copia nueva y **necesitan espacio libre del orden del tamaño de la tabla** (~35 GB). Por eso, aunque ya redujimos la retención, el disco no baja: literalmente no cabe la operación de compactación con 1,5 GB libres.

**Conclusión de la sección:** el consumo de disco de MidPoint es esperable y de diseño. No es desperdicio ni mala configuración: es el costo de mantener (a) la réplica del estado de todas las cuentas conectadas y (b) un rastro de auditoría completo —exigido además por nuestro marco ISO 27001 (A.5.16/A.8.15)— de cada cambio de identidad.

---

## 3. Por qué MidPoint necesita más RAM

### 3.1. Dimensionamiento documentado por Evolveum

La guía oficial de requisitos de sistema escala los recursos según el número de usuarios:

| Métrica | Mínimo | <5K usuarios | **5K–50K usuarios** | 50K–100K usuarios |
|---|---|---|---|---|
| CPU | 1 core | 4 cores | **8 cores** | 16 cores |
| RAM | 4 GB | 8 GB | **16 GB** | 16 GB |
| Disco | 2 GB | 10 GB | **20 GB** | 40 GB |

> — Evolveum, *System Requirements*, https://docs.evolveum.com/midpoint/install/system-requirements/

UPeU tiene **35.450 usuarios**, lo que lo ubica en el tramo **5K–50K** (RAM recomendada 16 GB). **El host ya está en el límite inferior recomendado** (16 GB), no por encima. Y ese tramo es para uso en régimen estable; nuestro pipeline aún ejecuta operaciones masivas de migración que son más exigentes.

> Importante: esos 16 GB son para **todo el host**, pero aquí conviven en el mismo servidor la JVM de MidPoint **y** el PostgreSQL del repositorio. La tabla asume típicamente DB separada; el documento de Evolveum incluso lista requisitos de servidor de base de datos aparte. Tener app + DB juntas en 16 GB deja menos margen del que la tabla sugiere.

### 3.2. La JVM y su heap

La misma guía define la relación heap/memoria del contenedor:

> "With `MaxRAMPercentage=70–80`, the JVM heap will be ~70–80% of the allocated memory limit while the remainder covers metaspace, direct buffers, JIT, and threads."
> — Evolveum, *System Requirements*, https://docs.evolveum.com/midpoint/install/system-requirements/

Configuración real del contenedor MidPoint PROD (medida en `/opt/midpoint/docker-compose.yml`):

- `MP_MEM_MAX=9216m` (heap máximo 9 GB), `MP_MEM_INIT=5120m`, `mem_limit: 10g`
- PostgreSQL: `mem_limit: 3.5g`, `maintenance_work_mem=512MB`

Sumando límites de contenedor (10 GB MidPoint + 3,5 GB Postgres = **13,5 GB**) sobre un host de **16 GB**, queda muy poco para el sistema operativo, buffers de FS y picos. La medición en vivo lo confirma: `free -h` muestra **9,2 GB usados / 2,5 GB libres** y **swap en uso (568 MB)** — el host ya está rozando su techo.

### 3.3. Operaciones masivas: reconciliación, recompute e import

El proyecto IGA ejecuta de forma recurrente operaciones sobre los 35.450 focos:

- **Recompute** de todos los usuarios (recalcular roles/asignaciones/atributos derivados).
- **Reconciliación** contra los resources (comparar estado MidPoint vs. estado real de cada sistema).
- **Import** inbound desde Oracle LAMB.

Estas operaciones cargan en memoria contextos de cómputo (*lens context*), objetos y sus deltas. La documentación reconoce explícitamente que ciertas estructuras incrementan el consumo de memoria:

> "...results in larger data structures... This increases memory consumption, storage consumption at database level and processing time necessary for creation, serialization and deserialization of these metadata."
> — Evolveum, *Performance Tuning*, https://docs.evolveum.com/midpoint/reference/diag/performance/

### 3.4. Incidente OutOfMemory real (evidencia local)

> (Evidencia empírica local, registrada en la memoria del proyecto; sin cita documental.) El upgrade a 4.10.2 estuvo acompañado de un **OutOfMemory**; el sistema quedó "en recuperación post-OOM". Operaciones grandes (queries masivas y recompute de 35K usuarios) llevaron el **heap al 98 %**, obligando a reiniciar el servicio en más de una ocasión.

Esto es exactamente el patrón que la guía de Evolveum busca evitar al recomendar 16 GB **holgados** (no al límite) para este tramo de usuarios. Subir a 24 GB permite elevar el heap con seguridad y dejar margen para Postgres y el SO.

---

## 4. Petición concreta y dimensionamiento

### 4.1. Disco: de 67 GB a **150 GB** (mínimo recomendado)

Justificación del número:

| Concepto | Tamaño |
|---|---:|
| DB actual `midpoint` | 45 GB |
| Espacio libre para ejecutar `pg_repack`/`VACUUM FULL` sobre `ma_audit_delta` (~tamaño de la tabla) | ~35 GB |
| Crecimiento de auditoría con retención P7D a régimen normal (post-migración) | ~15–20 GB |
| Sistema operativo, imágenes Docker, logs, WAL, dumps de backup | ~25 GB |
| Colchón operativo (evitar volver a 98 %) | ~25 GB |
| **Total recomendado** | **~150 GB** |

Con 150 GB: (1) cabe el `pg_repack` que hoy es **imposible** ejecutar y que es el único modo de recuperar los ~35 GB de auditoría ya borrada lógicamente; (2) queda margen para backups (`pg_dump`) y crecimiento; (3) se sale del estado crítico de 98 %.

> Si se quiere un único aprovisionamiento que no requiera revisitar en 12–18 meses, **200 GB** es la cifra cómoda.

### 4.2. RAM: de 16 GB a **24 GB**

- Mínimo documentado para el tramo 5K–50K usuarios: **16 GB** — que es lo que hay hoy, ya en el límite y con app+DB compartiendo host.
- Recomendado para esta instalación (app MidPoint + PostgreSQL en el mismo host, con operaciones masivas de migración aún activas y un OOM previo): **24 GB**.
- Reparto objetivo con 24 GB: ~12 GB heap MidPoint, ~4 GB PostgreSQL, ~8 GB SO + buffers de FS + picos, eliminando el uso de swap.

### 4.3. CPU

El host ya tiene **16 vCPU** (`nproc=16`), por encima de los 8 cores recomendados para el tramo. **No se solicita ampliar CPU.**

### Estado actual del host (medido 2026-06-22)

```
RAM total: 16 GB  | usada 9,2 GB | libre 2,5 GB | swap en uso 568 MB
CPU: 16 vCPU
Disco /: 67 GB total | 63 GB usado | 1,5 GB libre | 98 %
Heap MidPoint: MP_MEM_MAX=9216m (mem_limit 10g) ; PostgreSQL mem_limit 3,5g
```

---

## 5. Medidas de mitigación ya aplicadas (no es derroche)

Antes de pedir más recursos se aplicaron mitigaciones; se documentan para mostrar diligencia:

1. **Reducción de retención de auditoría** de P14D a **P7D** (temporal, vía REST) — alineado con que la limpieza es el mecanismo recomendado por Evolveum (*Native Audit*, *Removing Obsolete Information*).
2. **Limpieza de logs** de Docker (`-json.log` rotados) → +770 MB recuperados.
3. **Verificación de imágenes Docker**: no hay imágenes colgadas (dangling) ni versiones antiguas podables; las 2 imágenes presentes están en uso.
4. **Vacuum de journald** para liberar el root temporalmente y permitir operaciones de mantenimiento.

**Por qué NO bastan:**

- Reducir la retención (P14D→P7D) **no devuelve los ~35 GB ya ocupados**: en PostgreSQL el `DELETE` no libera espacio físico sin `VACUUM FULL`/`pg_repack`, y esa compactación **no cabe** con 1,5 GB libres. Se necesita **primero ampliar el disco** para poder ejecutarla.
- La RAM no se puede "limpiar": el dimensionamiento documentado para 35K usuarios es 16 GB **como recomendación de partida**, y aquí el host comparte memoria con la base de datos y sufrió un OOM. La única vía segura es **añadir RAM**.

---

## 6. Referencias

URLs verificadas (responden y contienen el texto citado):

1. **System Requirements (sizing CPU/RAM/disco, JVM/MaxRAMPercentage)** — https://docs.evolveum.com/midpoint/install/system-requirements/
2. **Native PostgreSQL Repository (`fullObject`/`delta` serializados, JSONB inline)** — https://docs.evolveum.com/midpoint/reference/repository/native-postgresql/
3. **Native Audit (`ma_audit_event`/`ma_audit_delta`, múltiples deltas por evento, cleanup task, particionado)** — https://docs.evolveum.com/midpoint/reference/repository/native-audit/
4. **Shadow Objects (réplica/proyección local por cuenta de cada resource)** — https://docs.evolveum.com/midpoint/reference/resources/shadow/
5. **Removing Obsolete Information (`cleanupPolicy`, `maxAge` P3M por defecto)** — https://docs.evolveum.com/midpoint/reference/deployment/removing-obsolete-information/
6. **Performance Tuning (incremento de consumo de memoria por estructuras de datos)** — https://docs.evolveum.com/midpoint/reference/diag/performance/

Afirmaciones marcadas como **evidencia empírica local sin cita documental**: (a) que `DELETE` en PostgreSQL no libera disco sin `VACUUM FULL`/`pg_repack` (comportamiento estándar de PostgreSQL, no de MidPoint); (b) el incidente OutOfMemory y los picos de heap al 98 % en PROD; (c) las cifras de tamaño por tabla y el caudal de 100K–300K eventos/día (medidos en el host, no en documentación de Evolveum).
