# E1 — Medición en producción (solo lectura) del nombre oficial

**Fecha:** 2026-11-09 (datos leídos entre las 21:38 y las 21:50 UTC)
**Qué se mide:** qué pasaría en producción si se activara E1 con la regla ajustada del 9-nov (§2 de [`03-e1-laboratorio.md`](03-e1-laboratorio.md)): apellidos **y** primer nombre deben calzar, y `displayName` de LDAP en `strong`.
**Cómo:** la decisión de `upeuNombreOficial.resolver` se reprodujo **fuera de MidPoint**, en Python, sobre los datos actuales. La copia en Python da el mismo resultado que MidPoint en los 15 casos del laboratorio que tienen nombre RENIEC.
**Producción NO se tocó:** solo `SELECT` en una transacción de solo lectura (`default_transaction_read_only=on`) contra la base de MidPoint, y `SELECT` en una transacción `READ ONLY` contra Oracle LAMB. Ninguna escritura, tarea, recompute ni simulación en MidPoint. **0 consultas a la API de pago.**

> Sin datos personales: solo conteos. Los resultados por persona quedaron fuera del repo (en la máquina del operador, permisos 600).

---

## 1. Fuentes y supuestos

| Dato | De dónde | Nota |
|---|---|---|
| Población activa | MidPoint: `sb:liveAffiliationWorker ∈ {faculty, staff}` o `sb:liveAffiliationStudent = student` (vínculo vivo) | **21 880 personas**. La aproximación desde Oracle del diseño daba 21 821 |
| Nombre de Lamb (lo que llevarían `upeu:lambGivenName/FamilyName`) | `MOISES.PERSONA` (`NOMBRE`, `PATERNO`, `MATERNO`) por `upeu:lambIdPersona`, con la misma transformación que los inbounds (`toCanonicalName`) | 21 873 de 21 874 encontrados |
| Nombre RENIEC de la caché | `DAVID.CONSULTA_APIS_LOG`, misma deduplicación que el `searchScript` de `reniec-cache` (la consulta exitosa más reciente por DNI). Solo se extrajeron DNI, nombres y apellidos, en el servidor | 129 376 DNI |
| Nombre RENIEC de E0 | Lote verificado de asesores (694 DNI con nombre) | El que cargaría el recurso CSV |
| Enlaces y estado actual | `m_user`, `m_shadow`, `m_ref_projection` | |
| `displayName` actual en LDAP | Atributos guardados en los shadows de `LDAP-IdentityCache-UPeU` dentro de MidPoint | No se consultó el LDAP |

Supuestos: (a) tras cambiar la correlación de `reniec-cache` a `lambDocNum`, una reconciliación completa enlaza cada fila de la caché cuyo DNI pertenece a **un solo** usuario; (b) entre E0 y la caché gana E0 (su fecha es igual o posterior); (c) **la plantilla se aplica a todos los usuarios**, no solo a los activos (ver §6, riesgo 1).

## 2. Activos: resultado de la decisión

| | Personas | Trabajadores | Solo estudiantes |
|---|---|---|---|
| **Evaluados** | **21 880** | 3 857 | 18 023 |
| Con DNI de 8 dígitos | 21 608 | 3 803 | 17 805 |
| Sin DNI (CE, pasaporte, PTP…, o DNI mal formado) → nombre de Lamb | 272 | 54 | 218 |
| Con nombre RENIEC disponible | **5 210** | 937 | 4 273 |
| · de la caché `CONSULTA_APIS_LOG` | 4 875 | 609 | 4 266 |
| · del lote E0 | 335 | 328 | 7 |
| · de las dos a la vez | 0 | 0 | 0 |
| **`reniec_name`** (nombre visible = RENIEC) | **5 161** | 926 | 4 235 |
| **`mismatch`** (se queda Lamb, va a revisión) | **46** | 10 | 36 |
| Sin RENIEC → nombre de Lamb | 16 670 | 2 920 | 13 750 |
| Hay RENIEC pero falta el apellido de Lamb → no se toca | 3 | 1 | 2 |
| `manual_override` | 0 | 0 | 0 |

De los 272 sin DNI de 8 dígitos: 119 carné de extranjería, 80 pasaporte, 38 de tipo 24, 30 de tipo DNI con un número que no tiene 8 dígitos (error de captura en Lamb), 5 de otros tipos.

### Efecto de endurecer la regla (misma población)

| | Regla anterior (solo apellidos) | Regla nueva (apellidos + primer nombre, por palabras) |
|---|---|---|
| `reniec_name` | 5 178 | 5 161 (−17) |
| `mismatch` | 29 | 46 (+17) |

## 3. Activos: cuántos cambian de nombre visible

| Cambio de `givenName`/`familyName` respecto de hoy | Total | Por nombre RENIEC | Por pasar a Lamb sin RENIEC | Por `mismatch` |
|---|---|---|---|---|
| Sin cambio | 15 236 | 1 975 | 13 239 | 19 |
| **Solo tildes o mayúsculas** | **6 539** | 3 144 | **3 381** | 14 |
| **Cambian palabras** | **105** | 42 | 50 | 13 |
| **Total que cambia** | **6 644** | 3 186 | 3 431 | 27 |

**Hallazgo:** 3 431 activos cambian de nombre **sin tener RENIEC**. Son estudiantes (solo 2 trabajadores) cuyo nombre en MidPoint está hoy en MAYÚSCULAS (3 159 de los 3 431): el inbound de estudiantes es `weak` y nunca corrigió un valor puesto antes. Con E1 la plantilla escribe el nombre de Lamb en `strong` y pasa a altas y bajas. Es el comportamiento diseñado («sin RENIEC → Lamb»), pero no es un efecto de RENIEC y hay que contarlo en el anuncio.

## 4. `displayName` en LDAP (activos)

| | Personas |
|---|---|
| Con cuenta LDAP `account/default` (la única que publica `displayName`) | 21 878 |
| **`displayName` que cambiaría** | **7 115** |
| · porque cambia el nombre (§3) | 6 639 |
| · porque ya hoy es distinto de `cn` y el nombre no cambia (valor fijado al crear la cuenta) | 476 |

Con `weak` (estado actual) esos 7 115 seguirían mostrando el nombre anterior en `displayName` y el nuevo en `cn`, `givenName` y `sn`.

## 5. Enlaces con `reniec-cache`, DNI duplicados y `upeuDataQualityStatus`

### Enlaces que se crearían de golpe

| | Shadows |
|---|---|
| Shadows de `reniec-cache` hoy | 128 154 (1 453 enlazados, 8 desenlazados, 126 693 sin usuario) |
| **Se enlazarían en la primera reconciliación** (DNI de un solo usuario) | **9 817** (3 926 de activos, 5 891 de no activos) |
| Ambiguos (el DNI lo tienen dos usuarios): no se enlazan | 1 |
| Siguen sin usuario | 116 883 |

Además, unos 180 activos están en la caché con consultas más recientes que la última importación: su shadow se crearía en esa misma reconciliación. Los 1 453 enlaces actuales (por `sb:taxId`) son coherentes: el DNI del shadow es el `lambDocNum` del dueño en 1 452; el otro dueño no tiene DNI de 8 dígitos.

**DNI duplicados:** 16 DNI de 8 dígitos los comparten 32 usuarios (2 por DNI); 3 de esos usuarios están activos. La correlación no los enlaza (más de un candidato) y se quedan con el nombre de Lamb.

### Consumidores de `upeuDataQualityStatus`

Hoy en todo MidPoint: 1 450 `reniec_validated`, 3 `mismatch`, el resto vacío.

| Transición | Activos | No activos | Total |
|---|---|---|---|
| `reniec_validated` → `reniec_name` | 759 | 668 | 1 427 |
| `reniec_validated` → `mismatch` | 8 | 10 | 18 |
| `reniec_validated` se queda (falta el apellido de Lamb) | 1 | 4 | 5 |
| vacío → `reniec_name` | 4 402 | 6 112 | 10 514 |
| vacío → `mismatch` | 38 | 26 | 64 |
| `mismatch` → `reniec_name` | 0 | 3 | 3 |

Efecto en `eduPersonAssurance` (LDAP, solo con `personalNumber`): las ~10 500 que pasan a `reniec_name` **suben** a IAP/medium-high (`cappuccino`); las 18 que pasan de `reniec_validated` a `mismatch` **bajan** a low (`espresso`). Cualquier consumidor que filtre por `upeuDataQualityStatus=reniec_validated` dejará de ver a casi todos: ese valor ya no se produce.

## 6. Los 46 `mismatch` de activos, por patrón

| Patrón | Casos |
|---|---|
| Apellidos comparten una palabra pero no calzan (materno distinto, o casada que reemplaza al materno) | 12 |
| Primer nombre con errata (1-2 letras) y el segundo nombre de Lamb sí está en RENIEC | 12 |
| Apellido con errata (1-2 letras) | 10 |
| Otro primer nombre y apellidos sin ninguna palabra en común (probable DNI de otra persona) | 3 |
| Primer nombre con errata | 2 |
| Otro primer nombre | 2 |
| Otro primer nombre, pero el segundo nombre de Lamb sí está en RENIEC | 2 |
| Apellidos sin ninguna palabra en común | 1 |
| Otro primer nombre y apellidos que comparten una palabra | 1 |
| Errata en el primer nombre y en un apellido | 1 |

Origen: 41 de la caché, 5 de E0. Muestra al azar de 10 (sin nombres ni DNI):

1. Estudiante, caché: errata en el primer nombre; el segundo nombre calza.
2. Trabajador, caché: apellidos comparten una palabra.
3. Estudiante, caché: errata en el primer nombre y en un apellido.
4. Trabajador, E0: apellidos comparten una palabra.
5. Estudiante, caché: apellidos comparten una palabra.
6. Estudiante, caché: apellidos comparten una palabra.
7. Estudiante, caché: otro primer nombre y apellidos que comparten una palabra.
8. Estudiante, caché: apellidos comparten una palabra.
9. Estudiante, caché: errata en un apellido.
10. Trabajador, E0: otro primer nombre y ningún apellido en común (probable DNI equivocado).

Los 17 que la regla nueva añade a `mismatch` son, en su mayoría, erratas de Lamb en el primer nombre de la misma persona. Es el precio de no aceptar un DNI de otra persona que comparte apellido; los resuelve la revisión (§7.2).

## 7. Riesgos y decisiones nuevas

1. **La plantilla no se limita a los activos.** El diseño (§3) acota E1 a activos, pero `UserTemplate-Nombre-Oficial` se aplica a todo usuario que pase por `Person-Base`. Activarla cambia también a no activos: **6 783 `reniec_name`, 36 `mismatch`, 7 956 nombres visibles y 5 973 `displayName`**. Decidir antes de producción: aceptarlo (es el mismo dato oficial) o añadir a los mappings una condición de vínculo vivo.
2. **3 431 activos (y 2 647 no activos) cambian de nombre sin RENIEC**, de MAYÚSCULAS a altas y bajas, porque el nombre de Lamb pasa a `strong` para estudiantes y egresados. Cambio legítimo pero visible: incluirlo en el aviso.
3. **Volumen del primer recompute:** ~14 600 nombres visibles y ~13 100 `displayName` (activos más no activos), además de ~10 500 cambios de `eduPersonAssurance`. Hacerlo por tandas, en la ventana segura, con SIM PRE/POST.
4. **9 817 enlaces nuevos de `reniec-cache` en una sola reconciliación.** Hacerla antes de activar la plantilla (sin la plantilla los transportes no cambian el nombre) y verificar el conteo.
5. **`reniec_validated` desaparece en la práctica** (1 427 de 1 450 pasan a `reniec_name`). Avisar a los consumidores de `upeuDataQualityStatus` antes del despliegue.
6. **`mismatch` necesita un responsable:** 46 activos y 36 no activos. Sin cola de revisión, se quedan con el nombre de Lamb indefinidamente.
7. **Calidad de datos de Lamb**: 30 activos con tipo DNI y número mal formado, y 16 DNI duplicados entre usuarios. Ninguno recibe nombre RENIEC.

## 8. Reproducir

Los scripts de la medición no se versionan porque escriben datos personales. Resumen del procedimiento, todo en solo lectura:
1. MidPoint: exportar de `m_user` los activos (§1) con `lambIdPersona`, `lambDocType`, `lambDocNum`, `dataQualityStatus` y el nombre actual; de `m_ref_projection` + `m_shadow` los enlaces de LDAP y `reniec-cache` (con el `displayName` guardado); y los shadows de `reniec-cache`.
2. Oracle: `MOISES.PERSONA` por `ID_PERSONA`, y `CONSULTA_APIS_LOG` con la deduplicación del `searchScript`, extrayendo en el servidor solo `nombres`, `ap_paterno` y `ap_materno`.
3. Aplicar `toCanonicalName` (Lamb), `toOfficialName` (RENIEC) y la regla de `upeuNombreOficial.resolver`.
