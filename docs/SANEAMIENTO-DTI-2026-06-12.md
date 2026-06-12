# Reporte de Saneamiento — Casos residuales IGA UPeU

**Fecha:** 2026-06-12
**Origen:** residuos del masivo Paso C (Bsort/ciclo/nivel) + auditoría LDAP + optimización Koha.
**Total casos:** 22 doble-correo + 2 doble-apellido + 82 KOHA-DUAL + 2 ítems infra Koha + 3 decisiones diferidas.

> **Hallazgo clave:** la mayoría de los "casos de calidad de datos" son **fixable en MidPoint (nuestro lado)**, NO requieren DTI ni corrección en Oracle. Solo los KOHA-DUAL (koha-expert) y los ítems de infra (DTI) están fuera de MidPoint.

---

## 1. Doble correo @upeu (22) — FIXABLE EN MIDPOINT

**Causa:** estos estudiantes tienen DOS correos `@upeu.edu.pe` en Oracle — uno en `CORREO_INST` (institucional, correcto) y otro en `CORREO` (campo "personal" que NO debería ser @upeu). MidPoint toma ambos como `emailAddress` → `Attempt to add 2 values to single-valued emailAddress` → el foco aborta antes de provisionar (sin Bsort/ciclo/foto).

**Fix recomendado (MidPoint, NO DTI):** ajustar el inbound de `emailAddress` para que SOLO `CORREO_INST` alimente el correo institucional; `CORREO` nunca debe aportar un `@upeu` a `emailAddress` (es campo personal → debería ser gmail/otro). Esto resuelve los 22 sin tocar Oracle. Ejecutar tras el backfill de fotos (requiere recompute).

**Alternativa DTI (opcional, saneamiento en origen):** limpiar el campo `CORREO` (personal) en `MOISES.PERSONA_NATURAL` donde contenga un `@upeu` duplicado.

| Código | CORREO_INST (institucional) | CORREO (personal, conflictivo) | Apellidos |
|---|---|---|---|
| 200711417 | wagnerrios@upeu.edu.pe | wagnerrios8@upeu.edu.pe | Rios Pinto |
| 201121349 | wilberthq@upeu.edu.pe | wilberhuanca@upeu.edu.pe | Huanca Tintaya |
| 201810134 | merytarapa@upeu.edu.pe | mery.tarapa@upeu.edu.pe | Tarapa Mamani |
| 201910245 | joe.saavedra@upeu.edu.pe | joesaavera@upeu.edu.pe | Saavedra Diaz |
| 201911116 | jesicallicahua@upeu.edu.pe | jesicalilcahua17@gmail.com *(personal OK)* | Llicahua Huachaca |
| 201911873 | elian.mendigure@upeu.edu.pe | yaneth.mendigure@upeu.edu.pe | Mendigure Condori |
| 202012075 | andreaverastegui@upeu.edu.pe | andrea.verastegui@upeu.edu.pe | Verastegui Velásquez |
| 202121279 | gian.huancas@upeu.edu.pe | gianpool.huancas@upeu.edu.pe | Huancas Cruz |
| 202121956 | cinthia.perez.@upeu.edu.pe | cinthia.perez@upeu.edu.pe | Perez Guerrero |
| 202122387 | milardo.infante@upeu.edu.pe | milardoinfante@upeu.edu.pe | Infante Chilon |
| 202211670 | mariluz.lozano@upeu.edu.pe | celsolozano@upeu.edu.pe | Lozano Larico |
| 202212844 | erick.mendonza@upeu.edu.pe | erick.mendoza@upeu.edu.pe | Mendoza Ojeda |
| 202220245 | jenifer.cahuaza@upeu.edu.pe | jcahuaza04@upeu.edu.pe | Cahuaza Ruiz |
| 202220342 | shannel.zapata@upeu.edu.pe | shannel.zapata@upeu.edu.pe *(idénticos)* | Zapata Campoblanco |
| 202310027 | daniel.mamani.t@upeu.edu.pe | luis.mt@upeu.edu.pe | Mamani Torpoco |
| 202310522 | vincent.perezj@upeu.edu.pe | vincent.perez@upeu.edu.pe | Perez Calero |
| 202310701 | fabiola.sanchez@upeu.edu.pe | fabiola.sanchezs@upeu.edu.pe | SANCHEZ AGUILAR |
| 202312404 | armando.ramirez@upeu.edu.pe | armando.ramirrz@upeu.edu.pe | RAMIREZ ARCE |
| 202312607 | ruben.huallpa@upeu.edu.pe | luz.hr@upeu.edu.pe | Huallpa Rafaile |
| 202410882 | josias.mamanih@upeu.edu.pe | jonathan.mamani@upeu.edu.pe | Mamani Huesemberg |
| 202614798 | lucy.farceque@upeu.edu.pe | *(vacío)* | FARCEQUE CRUZ |
| M20150085 | shanell.morales@upeu.edu.pe | shanell.morales@colegiounion.edu.pe *(personal OK)* | Morales Coca |

*Nota:* el correo institucional canónico es siempre `CORREO_INST`. En los casos *(personal OK)* el conflicto puede ser por otro inbound; revisar individualmente.

---

## 2. Doble apellido (2) — FIXABLE EN MIDPOINT

**Causa:** `familyName` recibe 2 valores que difieren solo en **acento/mayúsculas** (strong mapping → conflicto single-valued).

| Código | Variante 1 | Variante 2 |
|---|---|---|
| 201710021 | Fernandez Salomon | Fernández Salomón |
| 201521028 | Diaz Chavarri | DIAZ CHAVARRI |

**Fix recomendado (MidPoint):** normalizar acentos/mayúsculas en el inbound de `familyName` (canonicalizar a una forma, ej. la acentuada con Title Case) para que no genere doble valor. No requiere DTI.

---

## 3. KOHA-DUAL (82) — MERGE EN KOHA (koha-expert)

**Causa:** la misma persona tiene DOS borrowers en Koha (cardnumber distinto: código vs DNI, o duplicado histórico). Al reconciliar, Koha responde `AlreadyExistsException: patron API Conflict`. **NUNCA hacer link** (dual-projection FATAL) → **merge** vía koha-expert (keeper = el del código universitario, preservar historial de préstamos).

**Códigos (82):**
```
9910124 200210468 200310423 200310536 201151166 201220753 201311041 201440045
201510209 201511072 201511131 201520235 201610234 201611131 201711667 201712328
201810025 201810099 201811030 201811726 201811776 201910078 201910364 201911258
201912585 201912869 202010197 202010969 202011097 202012261 202012275 202014651
202100012 202110721 202110788 202121839 202121928 202211463 202211622 202313549
202313571 202413657 202413801 202510151 202510237 202510358 202511539 202521131
202610458 202611552 323200490 324100780 324103878 324103904 324104478 324104957
324105947 324106044 324106067 324106157 324106562 324106569 324106954 324107125
324107182 324107566 324107980 324108348 324108798 324108901 324109206 324109246
324109459 324109661 324109869 324110135 324110227 324110476 324111046 324111113
324111165 324111265
```
*(OIDs MidPoint completos en host PROD `/tmp/pasoC_kohadual.txt` + `/tmp/pasoC_errors.txt`.)*

---

## 4. Infra Koha — REQUIERE DTI (sudo .135/.130)

Optimizado 2026-06-12 (madrugada): `max_connections` 250→500, Plack `--max-requests` 50 en BUL. Pendiente, requiere validación/decisión DTI:

| Ítem | Detalle | Comando/acción |
|---|---|---|
| **Workers instancias secundarias** | bul=8(activo)/but=4/cia=4/buj=2 en host con swap. cia/but/buj casi idle de madrugada pero falta dato de pico diurno. | Tras revisar uso diurno, reducir workers en `/etc/koha/sites/{but,cia,buj}/koha-conf.xml` + `koha-plack --restart`. |
| **Template roto `library_name_title`** | 1,461 errores en `plack-error.log` BUL: `Template process failed: library_name_title: not found`. Include de tema UPeU roto. | Identificar la plantilla OPAC/intranet con `INCLUDE library_name_title` y restaurar/quitar el include. |
| **RAM host .135** | 11 GiB con 4 instancias, swap en reposo. Sizing oficial Koha: 4 GiB+/instancia. | Considerar subir RAM a ≥16 GiB. |
| `skip_name_resolve` | **NO aplicar** — los grants MariaDB usan hostnames; `/etc/hosts` ya resuelve `koha-app` local. No era el cuello. | (descartado, documentado) |

---

## 5. Decisiones diferidas (Fase 12 / arquitectura)

| Tema | Decisión pendiente |
|---|---|
| **Egresados-SSO** | ~20,058 entradas `alum` stale en OpenLDAP que Keycloak federa → ¿los egresados deben tener SSO? Si NO → barrido de deprovisioning (write-free). |
| **eduPersonPrincipalName** | Hoy NO determinista (trae alias M365 o vacío). Revisar si debe ser `código@upeu.edu.pe` determinista para SSO académico. Requiere recompute. |
| **GAP-3 Entra (resuelto parcialmente)** | Los 16,911 fantasmas exist=false fueron purgados y 17,476 cuentas reales correlacionadas (2026-06-11). El write/gobierno Entra sigue bloqueado por permisos (DU-001b, David Urquizo). |

---

## Resumen de propietarios

| Owner | Ítems | Cuándo |
|---|---|---|
| **MidPoint (nosotros)** | 22 doble-correo (email inbound), 2 doble-apellido (familyName inbound) | Tras backfill foto (requiere recompute) |
| **koha-expert** | 82 KOHA-DUAL merge | Madrugada (writes Koha) |
| **DTI** | Workers Koha secundarios, template roto, RAM .135 | Coordinar |
| **Decisión usuario** | Egresados-SSO, ePPN determinista | Fase 12 |
