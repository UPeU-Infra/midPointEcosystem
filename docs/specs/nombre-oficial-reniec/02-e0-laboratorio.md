# E0 — Nombres verificados contra RENIEC en MidPoint: ensayo en el laboratorio

**Fecha:** 2026-11-09
**Dónde:** MidPoint del laboratorio UPeU (`192.168.15.150:8081`, 4.10.2, la misma imagen que producción). **Producción NO se tocó.**
**Diseño:** [`01-diseno.md`](01-diseno.md) §5 y §6 (E0).
**Consultas a RENIEC / API de pago:** 0.

> Este documento no contiene DNI ni nombres reales (el repo es público). Los ejemplos usan DNI ficticios `000009xx` y nombres inventados.

---

## 1. Qué se creó

| Objeto | Archivo | OID |
|---|---|---|
| Recurso «RENIEC verificados (CSV)», solo lectura | `upeu/resources/reniec-verificados-csv.xml` | `082811dd-d4c4-4b3f-b288-e06f89d3383e` |
| Tarea de importación (se entrega **suspendida**) | `upeu/tasks/import-reniec-verificados-csv.xml` | `bc5350d1-94bd-403b-89d7-636011eabcaa` |
| 4 ítems nuevos en el schema `urn:upeu:midpoint:local` | `upeu/schemas/upeu-local-v1.0.xml` (L12b) | schema `64ed4155-…` (sin cambio de OID) |

Ítems nuevos (todos `xsd:string`, single-valued, **de transporte**: no se publican ni son el nombre visible):

| Ítem | Contenido |
|---|---|
| `upeu:reniecVerifiedGivenName` | Nombres del DNI, en altas y bajas (`sb-name-normalizer`) |
| `upeu:reniecVerifiedFamilyName` | Paterno + materno, en altas y bajas (materno opcional) |
| `upeu:reniecVerifiedBy` | `RENIEC` (vocabulario de `sciback:IdentityDocumentType/verifiedBy`) |
| `upeu:reniecVerifiedAt` | `AAAA-MM-DD` de la consulta (formato de `sciback:…/verifiedAt`) |

**No se cambia `givenName`/`familyName`.** Elegir el nombre visible y llenar `identityDocuments[DNI].verifiedBy/verifiedAt` es E1.

### Decisiones y por qué

1. **Overlay (`upeu/`), no canónico.** Son campos de transporte de una fuente concreta de UPeU (un lote CSV). El destino canónico ya existe: `givenName`/`familyName` (core) y `sciback:identityDocuments[].verifiedBy/verifiedAt`. *Schema is the law*: no se extiende el canónico.
2. **Ítems propios del CSV, no `upeu:reniecGivenName`/`reniecFamilyName`.** El §5 del diseño reserva esos dos para `reniec-cache` (la caché `CONSULTA_APIS_LOG`). Si el CSV escribiera los mismos ítems, habría **dos inbounds sobre un ítem single-valued**: cuando DTI Desarrollo registre estos DNI en la caché (pedido del §6) o cuando la caché tenga una versión más reciente (apellido de casada), los valores diferirían y MidPoint lanzaría `SchemaException`, el mismo choque del runbook `givenName-collision-fix-2026-06-29`. Un ítem, una IIA. El template de E1 decide entre ambas fuentes (p. ej. la de `verifiedAt` más reciente).
3. **No se escribe `identityDocuments` desde el recurso.** Es un contenedor multivalor que construye el Bloque J del `UserTemplate-Person-Base`; un inbound añadiría un segundo valor de documento DNI en vez de completar el existente. Además, el Bloque J ya pone `verifiedBy=RENIEC` a **todo** DNI por su tipo, sin verificación real: E1 debe corregirlo con estos datos.
4. **Correlación por `extension/upeu:lambDocNum` (DNI, 8 dígitos), no por `sb:taxId`** como `reniec-cache`. Es la clave de trabajadores, estudiantes, egresados y grados desde el CANON_KEY del 2-jun-2026: `taxId` era *type-blind* (fusionaba un CE y un DNI con el mismo número), está **deprecado** en el schema canónico y el Bloque J2 lo **vacía** en cuanto el usuario tiene `identityDocuments`. Medido en el lab: 0 usuarios con `taxId`; y `extension/identityDocuments/number` no se puede buscar (el repositorio rechaza la consulta). El inbound a `lambDocNum` corre **solo en `beforeCorrelation`**: el recurso nunca lo escribe en el usuario (su IIA es Lamb).
5. **Solo lectura doble:** `readOnly=true` en el conector y capacidades create/update/delete deshabilitadas. `unmatched` → ninguna acción (no crea personas); `deleted` → `unlink`.
6. **`connectorRef` por filtro de tipo** (`CsvConnector`), no por OID: el OID del ConnectorType cambia entre instancias.
7. **El CSV vive fuera del repo**, en `/opt/midpoint/var/reniec-verificados/reniec-verificados.csv` dentro del contenedor (volumen persistente), directorio 700 y archivo 600, dueño root. Columnas: `dni,ap_paterno,ap_materno,nombres,fuente,fecha_verificacion`, UTF-8, comillas dobles, MAYÚSCULAS como RENIEC. El paso a altas y bajas lo hace el inbound, no el CSV.

## 2. Cómo se probó (en vivo)

Estado inicial del lab: 4.10.2, schemas `sciback` v1.4 y `upeu-local` v7 (mismos ítems que el repo), un solo recurso (LDAP), sin `sb-name-normalizer`, 27 usuarios de prueba sin `lambDocNum`. **El MidPoint del lab estaba colgado por `OutOfMemoryError` desde el 3-nov** (heap 2 GB, REST sin responder); se reinició el contenedor sin cambiar configuración.

1. Importada la función `sb-name-normalizer` (repo canónico, mismo OID que PROD).
2. Schema `upeu-local`: **PATCH** `replace` de `definition` → v7 → v8, con los 4 ítems.
3. Recurso importado; test de conexión con error de refinamiento: el conector CSV 2.9 publica el identificador como `ri:dni` (con `frameworkAttributeName=__NAME__`), **no** como `icfs:name`. Corregido en el repo y en el lab con **PATCH** del `ref` (no PUT); versión 2 → 4; test de conexión: 6/6 pasos «success».
4. 8 usuarios de prueba (`e0test901…908`, DNI ficticios) y un CSV de prueba de 9 filas con los casos límite.
5. Tarea de importación ejecutada tres veces: CSV de prueba, CSV de prueba con un cambio, y CSV real.

## 3. Resultados

| Caso | Resultado |
|---|---|
| Partículas (`DE LA CRUZ`, `LUIS DEL CARMEN`, `DE LOS SANTOS`, `Y LOPEZ`) | `Quispe de la Cruz`, `Luis del Carmen`, `De los Santos y Lopez` (inicial en mayúscula) ✔ |
| Tildes y Ñ del origen | Se conservan (`José María`, `Ñahui`, `Pérez`) ✔ |
| DNI sin tildes donde Lamb sí las tiene | Transporte `Garcia Torres`; `familyName` sigue `García Torres` (E0 no lo toca) ✔ |
| Sin apellido materno | `Ñahui` ✔ |
| Punto en el apellido (`STA. ROSA`) | `Sta. Rosa` ✔ |
| DNI de 7 dígitos en el CSV | Rellenado a 8 y correlaciona ✔ |
| Usuario con carné de extranjería (`lambDocNum=CE:0…`) y el mismo número como DNI en el CSV | **No** correlaciona (`unmatched`) ✔ |
| Usuario con DNI solo en `identityDocuments` (sin `lambDocNum`) | No correlaciona (`unmatched`) — limitación esperada |
| DNI sin usuario | `unmatched`, no se crea nadie ✔ |
| Auditoría del primer import | Por usuario: `linkRef` + 4 ítems `reniecVerified*`. **Ni `givenName`, ni `familyName`, ni `lambDocNum`** ✔ |
| Segunda pasada sin cambios | 0 modificaciones de usuario (idempotente) ✔ |
| Segunda pasada con un materno cambiado | Solo cambia `reniecVerifiedFamilyName` de ese usuario ✔ |
| **CSV real (694 filas)** | 694 leídas, 694 «success», 0 errores en el log, **0 usuarios modificados** (ninguno de esos DNI existe en el lab) ✔ |
| Forma producida vs la ya aplicada en el repositorio de tesis (etapa 2 de asesores) | **694 de 694 idénticas** (comparación local, sin MidPoint) ✔ |

Tras la prueba con datos reales se borraron (raw) los 694 shadows y se restauró el CSV de prueba: en el lab solo quedan datos ficticios en el repositorio de objetos. La auditoría del lab conservaba 694 eventos `DISCOVER_OBJECT` de esa corrida (más 1 388 del borrado raw de los shadows). **Se purgaron el mismo día con aprobación expresa**: ver `03-e1-laboratorio.md` §0.

## 4. Problemas encontrados

1. **MidPoint del lab caído por OOM** desde el 3-nov (heap `MP_MEM_MAX=2048m`; las tareas Validity Scanner y Cleanup quedaron suspendidas por el error). Se reinició; si vuelve a pasar, subir el heap en `plataforma/docker-compose.yml` del lab.
2. `icfs:name` no existe en el recurso CSV: el `ref` correcto es `ri:dni` (corregido).
3. `reniec-cache.xml` sigue correlacionando por `sb:taxId`. Si en producción el Bloque J2 ya vació `taxId`, ese recurso **no enlaza a nadie nuevo** desde entonces. **No medido en PROD** (fuera del alcance de E0): medirlo antes de E1.
4. `sb-name-normalizer` pone en minúscula más partículas que la regla del CRAI (`e`, `a`, `al`, `en`, `con`, `o` además de `de`, `del`, `la`, `las`, `los`, `y`) y no capitaliza tras guion o apóstrofo. En este lote: 0 casos afectados. En lotes de estudiantes podría aparecer (p. ej. un segundo nombre de una letra): revisar la función antes de E3.

## 5. Qué falta

### Para producción (E0)
1. Visto bueno de DTI/Infra. Ventana segura (16:10–07:00 UTC); el import es pequeño.
2. **Schema:** construir el PATCH desde la `definition` **viva de PROD** (`GET ?options=raw`), no desde el archivo del repo, que puede ir por detrás de PROD. Verificar `version` y los 4 ítems tras el 204.
3. Comprobar que la imagen de PROD trae el conector CSV (`connectorType=…CsvConnector`) y que `/opt/midpoint/var` es un volumen persistente.
4. Copiar el CSV (generado desde `dniruc_asesores_20261109`, `nombres IS NOT NULL`) a `/opt/midpoint/var/reniec-verificados/` con `docker exec -i … cat >`, directorio 700 y archivo 600. Comparar `sha256` origen/destino.
5. Importar el recurso y la tarea (suspendida). Test de conexión.
6. Medir antes, en solo lectura, cuántos de los 694 DNI tienen usuario con ese `lambDocNum` (esperado: menos de 694; los asesores externos no están en MidPoint).
7. Canario: copia de la tarea con `<query>` por `ri:dni` sobre 3-5 DNI; revisar en `ma_audit_delta` que solo cambian los 4 ítems `reniecVerified*`. Luego el lote.
8. No hace falta SIM PRE/POST de recompute: E0 no toca el template ni ningún mapping existente; el único efecto posible es el de este recurso, y se verifica en el canario.

### Para E1
1. Template: elegir el nombre visible con prioridad RENIEC (CSV y caché, el de `verifiedAt` más reciente) → Lamb; ignorar los valores de transporte si ya no hay proyección viva del recurso (`midpoint.hasLinkedAccount`), porque un inbound no retira valores al morir el shadow (`midpoint-best-practices` §11.1).
2. Comparar apellido RENIEC vs Lamb antes de aplicarlo: si no calzan → `mismatch`, no cambiar (DNI equivocado en Lamb; en tesis hubo 221 casos).
3. Corregir el Bloque J: `verifiedBy/verifiedAt` solo cuando haya verificación real.
4. `reniec-cache`: pasar sus nombres a `upeu:reniecGivenName/FamilyName` y revisar su correlador (punto 3 de §4).
5. Informe de impacto antes de activarlo (cuántos cambian y de qué tipo).
