# E1 — El object template elige el nombre oficial: ensayo en el laboratorio

**Fecha:** 2026-11-09
**Dónde:** MidPoint del laboratorio UPeU (`192.168.15.150:8081`, 4.10.2). **Producción NO se tocó**: los cambios a sus XML están en el repo, sin desplegar.
**Diseño:** [`01-diseno.md`](01-diseno.md) §5. Etapa anterior: [`02-e0-laboratorio.md`](02-e0-laboratorio.md).
**Consultas a RENIEC / API de pago:** 0.

> Sin datos personales: los usuarios de prueba (`e1test911…924`) llevan DNI ficticios `000009xx` y nombres inventados.

---

## 0. Purga de la auditoría del laboratorio (pedido aprobado)

La corrida de E0 con el CSV real dejó DNI y nombres reales en el laboratorio. Se purgaron solo esos registros:

| Qué | Cuántos | Identificación |
|---|---|---|
| Eventos `DISCOVER_OBJECT` del import real | 694 | tarea `bc5350d1-…`, recurso CSV, 16:31:01–16:31:42 UTC |
| Eventos `EXECUTE_CHANGES_RAW` del borrado raw de esos shadows (REQUEST + EXECUTION) | 1 388 | `administrator`, 16:32:22–16:33:52 UTC; el DNI va en `ma_audit_delta.objectnameorig` |
| Deltas hijas (`ma_audit_delta`) | 2 082 | las de esos eventos |
| Referencias (`ma_audit_ref`) | 0 | — |
| Estadísticas de la tarea de import (guardaban el último objeto procesado) | 1 objeto | tarea borrada y reimportada limpia desde el repo |

MidPoint no tiene un mecanismo soportado para purgar por selección (el cleanup de auditoría es por antigüedad o por cantidad), así que se hizo **SQL directo en una transacción**, con los DNI solo en memoria y conteo antes y después: eventos 3 685 → 1 603, deltas 3 659 → 1 577 (−2 082 en ambos). Después, `VACUUM FULL` de las tablas tocadas.

**Verificación** contra los 694 DNI del lote: 0 apariciones en `ma_audit_event` (todas las columnas de texto), en `ma_audit_delta` (nombre, delta y resultado), en `ma_audit_ref`, en `m_shadow`, en `m_object.fullobject` (todos los objetos), en el log del contenedor y en `/opt/midpoint/var`. Además, una muestra de 3 DNI en auditoría y deltas: 0. **El resto de la auditoría del laboratorio se conservó.**

---

## 1. Qué se cambió

### Artefactos nuevos

| Objeto | Archivo | OID |
|---|---|---|
| Función `toOfficialName` (en la librería existente) | `canonical/function-libraries/sb-name-normalizer.xml` | `0b6f3a1c-…` (sin cambio) |
| Librería de decisión `upeuNombreOficial.resolver(focus, campo)` | `upeu/function-libraries/upeu-nombre-oficial.xml` | `3da5013a-18cf-427f-99c2-26f466faacdb` |
| Plantilla `UserTemplate-Nombre-Oficial` (único escritor del nombre y de `dataQualityStatus`) | `upeu/object-templates/UserTemplate-Nombre-Oficial.xml` | `0943af72-231e-4aef-a0fd-7cbad1357fe7` |
| 4 ítems de transporte: `upeu:lambGivenName`, `lambFamilyName`, `reniecGivenName`, `reniecFamilyName` | `upeu/schemas/upeu-local-v1.0.xml` (L12c) | schema `64ed4155-…` |

### Cambios en XML de producción (en el repo, **sin desplegar**)

| Archivo | Cambio |
|---|---|
| `upeu/resources/oracle-lamb/trabajadores.xml` | `givenName`/`familyName` → `upeu:lambGivenName`/`lambFamilyName` (sigue `strong`, misma forma) |
| `upeu/resources/oracle-lamb/estudiantes.xml`, `egresados.xml` | Ídem (siguen `weak`) |
| `upeu/resources/oracle-lamb/reniec-cache.xml` | Nombres → `upeu:reniecGivenName`/`reniecFamilyName` (`strong`, sin condición, `toOfficialName`); inbound de `dataQualityStatus` → `archived`; **correlación por `upeu:lambDocNum`** en vez de `sb:taxId`; comentario de los diacríticos corregido |
| `upeu/resources/reniec-verificados-csv.xml` | `toCanonicalName` → `toOfficialName` |
| `upeu/resources/ldap-identity-cache.xml` | `eduPersonAssurance`: «high» también con `reniec_name` |
| `canonical/object-templates/UserTemplate-Person-Base.xml` | `includeRef` a `UserTemplate-Nombre-Oficial`; Bloque J añade `verifiedAt` al DNI cuando el nombre visible es el de RENIEC |
| `upeu/schemas/upeu-local-v1.0.xml` | Vocabulario de `dataQualityStatus`: nuevo `reniec_name` |

### Objetos solo de laboratorio

`docs/specs/nombre-oficial-reniec/lab/`: `build_lab.py` genera los simuladores **copiando literalmente** los `<attribute>` de nombre de `trabajadores.xml`, `estudiantes.xml` y `reniec-cache.xml` (y la correlación de este último) sobre el conector CSV, **con el mismo OID que en PROD**, para que `hasLinkedAccount` funcione igual. También genera una plantilla de laboratorio (incluye `UserTemplate-Nombre-Oficial` + copia de los Bloques B y J de `Person-Base`) y un arquetipo que solo llevan los usuarios de prueba. **No desplegar en PROD.**

## 2. Diseño y por qué

**Un solo escritor por ítem.** Ningún recurso escribe ya `givenName`, `familyName` ni `dataQualityStatus`. Cada fuente deja su versión en su propio transporte y la plantilla elige. Así no se repite el choque del 29-jun: dos inbounds sobre un ítem single-valued se consolidan **antes** del template y lanzan `SchemaException`. El orden de fases (inbound → template → outbound) queda así:
1. Inbound: cada fuente escribe solo su transporte (`lamb*`, `reniec*`, `reniecVerified*`). Entre fuentes Lamb se mantiene lo de hoy: trabajadores `strong`, estudiantes y egresados `weak`.
2. Template: `resolver(focus, campo)` decide **una vez, con la misma lógica**, para `givenName`, `familyName`, `dataQualityStatus` y `verifiedAt`.
3. Outbound: LDAP, etc. reciben el nombre elegido.

**Regla de decisión** (`upeuNombreOficial.resolver`):
1. `manual_override` → los mappings no corren (condición): no se toca nada.
2. Hay nombre RENIEC **con enlace vivo** al recurso (CSV o caché) → si hay dos, gana la de fecha de verificación más reciente (empate → CSV).
3. Se compara el apellido RENIEC con `lambFamilyName`, sin tildes, mayúsculas, guiones ni apóstrofos: igual, o uno contiene al otro por palabras completas. Calza → nombre RENIEC, `reniec_name`, `verifiedAt`. No calza → nombre de Lamb, `mismatch`.
4. Sin RENIEC vivo → nombre de Lamb. Si antes era `reniec_name`/`mismatch` → `pending`; si no, se deja como está.
5. Hay RENIEC pero aún no hay apellido de Lamb (transición) → no se cambia nada.

**Enlace roto o fila retirada → vuelve al nombre de Lamb, estado `pending`.** Justificación: retirar una fila significa que esa verificación ya no vale (p. ej. un DNI equivocado). Los valores de transporte quedan en el usuario porque un inbound no los retira (`midpoint-best-practices` §11.1), pero la decisión los ignora porque mira el enlace vivo. Verificado: el shadow queda «muerto» con relación `related` y `hasLinkedAccount` devuelve `false`.

**`toOfficialName`** solo pone en minúscula `de`, `del`, `la`, `las`, `los` e `y` (regla de UPeU), capitaliza tras guion y apóstrofo y conserva las tildes del origen. `toCanonicalName` no cambia: Lamb sigue usándola. Sobre las 694 filas reales del lote de asesores (comparación en memoria), la forma coincide **694/694** con la ya aplicada en el repositorio de tesis.

**`reniec-cache` correlaciona ahora por `lambDocNum`.** Con `sb:taxId` (que el Bloque J2 vacía) no enlazaba a nadie nuevo. Sin este cambio, los valores de la caché no llegarían a la decisión. Efecto en PROD: **muchos shadows `unmatched` se enlazarán de golpe en la primera reconciliación**. Hay que medirlo antes (§5).

## 3. Pruebas (en vivo, laboratorio)

Orden realista: import de trabajadores → estudiantes → caché → CSV. Después, recomputes.

| Caso | Usuario | Resultado |
|---|---|---|
| RENIEC coincide (DNI con tildes, Lamb sin ellas) | 911 | `José María` / `Quispe de la Cruz`, `reniec_name`, `verifiedAt=2026-11-09` ✔ |
| Solo cambian tildes (DNI sin tildes, Lamb con ellas) | 912 | `Lucia` / `Perez Rojas`, `reniec_name` ✔ (es la regla: el del DNI) |
| Apellido de casada | 913 | `Garcia Torres de Paz` (contiene el de Lamb), `reniec_name` ✔ |
| Apellido que no calza | 914 | Se queda el de Lamb, `mismatch`, sin `verifiedAt` ✔ |
| Sin RENIEC | 915 | Nombre de Lamb, estado sin cambios ✔ |
| `manual_override` | 916 | Nombre manual intacto aunque hay RENIEC que calza ✔ |
| Retirar la fila del CSV + reconciliación | 917 | Vuelve a Lamb, `pending`, `verifiedAt` desaparece ✔ |
| Solo caché RENIEC (partícula inicial) | 918 | `Luis Alberto` / `Del Carmen Rojas`, `verifiedAt` = fecha de la caché ✔ |
| CSV y caché a la vez (fechas distintas) | 919 | Gana el CSV (más reciente) ✔ |
| Guion y apóstrofo | 920 | `Jean-Pierre` / `D'Angelo Saint-Hilaire` ✔ |
| Doble fuente Lamb (trabajador `strong` + estudiante `weak` con otras tildes) | 921 | `lambGivenName` = el de trabajadores, sin choque ✔ |
| RENIEC sin Lamb (transición) | 923 | Nombre actual intacto, estado sin cambios ✔ |
| `Y` como partícula, `E` como inicial | 924 | `De los Santos y Lopez` / `Maria E` ✔ |
| Bloque J viejo → nuevo | todos | Un solo documento DNI por persona (sin duplicados); `verifiedAt` solo con `reniec_name` ✔ |
| Dos recomputes sin cambios | todos | **0 modificaciones** (auditoría) ✔ |
| `SchemaException` / «more than one value» | — | **0** en todo el período ✔ |
| Tareas | — | 4 imports, 1 reconciliación y 4 recomputes, todos `success`, 0 fallos ✔ |

### LDAP del laboratorio (cuentas creadas para 913, 914 y 917)

| Atributo | Fuerza del outbound | Qué pasa |
|---|---|---|
| `givenName` | strong | Toma el nombre elegido y **se actualiza** cuando cambia (917 volvió a Lamb) ✔ |
| `sn` | strong | Ídem ✔ |
| `cn` | strong (de `fullName`) | Ídem ✔ |
| `displayName` | **weak** | Se fija al crear la cuenta y **NO se actualiza**: 917 quedó con el nombre RENIEC después de volver a Lamb ✘ |
| `upeuDataQualityStatus` | strong | `reniec_name` / `mismatch` / `pending` ✔ |
| `eduPersonAssurance` | strong | Con el cambio: `reniec_name` → IAP/medium, high, cappuccino; `mismatch` → low, espresso ✔ |

En PROD, `ldap-identity-cache.xml` tiene el mismo `displayName weak`. Las personas que ya tienen entrada LDAP **no verían el nombre RENIEC en `displayName`**. Además, Entra ID (`givenName`/`surname`) y RIMS (SCIM) son `strong`, y Koha es `normal`. Entra ID está hoy en `proposed` (no escribe).

## 4. Problemas encontrados

1. **Sin el cambio de `eduPersonAssurance`, cada persona que pase a `reniec_name` bajaría de nivel** (de IAP/medium a low): la regla solo miraba `reniec_validated`. Corregido en el repo y en el lab. Otros consumidores de `upeuDataQualityStatus` fuera de MidPoint (RIMS, InOut…) no se revisaron.
2. `displayName` en LDAP es `weak` (ver §3).
3. `reniec_validated` deja de producirse. Las personas enlazadas a la caché pasan a `reniec_name` o `mismatch`. Las que pierdan el enlace conservan `reniec_validated`.
4. El Bloque J sigue poniendo `verifiedBy=RENIEC` a **todo** DNI, verificado o no. E1 solo añade `verifiedAt` cuando la verificación es real. Corregir `verifiedBy` cambiaría el contenedor de ~todas las personas: queda como decisión aparte.
5. La regla «contiene» acepta un apellido RENIEC más largo (casada) y también uno más corto. Un DNI equivocado con un apellido compartido (p. ej. solo «Quispe») pasaría la comparación si Lamb tiene «Quispe». Mitigación posible: exigir también que calcen los nombres de pila, o que el apellido más corto tenga al menos dos palabras. **Decisión pendiente.**

## 5. Qué falta para producción

1. **Visto bueno de DTI/Infra** a este diseño y a la decisión pendiente de §4.5.
2. **Medir antes (solo lectura):**
   - Cuántas personas cambiarían de nombre y de qué tipo (solo tildes, casada, otras letras).
   - Cuántos `mismatch`.
   - Cuántos shadows de `reniec-cache` se enlazarían al correlacionar por `lambDocNum`.
   - Cuántas personas tienen entrada LDAP (por el `displayName`).
3. Orden de despliegue, cada paso con PATCH (nunca PUT en recursos) y verificación de `version`:
   1. Schema (PATCH construido desde la `definition` viva de PROD + los 8 ítems de E0 y E1).
   2. Función `toOfficialName`, librería `upeuNombreOficial` y `UserTemplate-Nombre-Oficial`.
   3. Recursos (los inbounds a transporte) en `proposed`, y `includeRef` + Bloque J en `Person-Base`.
   4. Reconciliación de Lamb para llenar `lamb*` **antes** de activar la plantilla (sin `lamb*` la plantilla no cambia nada, por diseño).
   5. SIM PRE/POST, canario por nombre, luego el lote.
4. LDAP: aplicar el cambio de `eduPersonAssurance` **antes o junto con** la plantilla, y decidir si `displayName` pasa a `strong`.
5. Avisar a los consumidores de `upeuDataQualityStatus` del valor nuevo `reniec_name`.
