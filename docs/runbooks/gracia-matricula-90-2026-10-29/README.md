# Gracia de matrícula: 90 días tras el fin real (2026-10-29) — PREPARADO, NO DESPLEGADO

Rama `fix/gracia-matricula-90` (desde `fix/activacion-vinculo-vivo-v2`). Sin PII: las listas de personas
(canario, lotes) se generan FUERA del repo.

## 1. Mecanismo actual (PROD: template v137, e22 v209)

| Pieza | Dónde | Qué hace |
|---|---|---|
| Pone/quita 217 | e22 `objectType[3297]/attribute[3324 SCHOOL_NAME]/inbound[3327]` (`estudiantes.xml`, `school-name-to-liveAffiliationStudent`) | strong: `'student'` si `DATE_EXPIRY` ≥ `LocalDate.now()` (zona del JVM = UTC) o sin fecha; si no, `null` ⇒ **el inbound retira 217** con la cuenta viva |
| `DATE_EXPIRY` | `searchScript` de e22 | `MAX(FECHA_FIN)` de `ACAD_MODULO_DETALLE` de los semestres del **horizonte** (267/279/283 + semestres con algún módulo `FECHA_FIN >= SYSDATE`), cursos `ESTADO='1'` |
| `terminationDateStudent` (ext 218) | e22 `attribute[3333]/inbound[3334]` | strong, copia de `DATE_EXPIRY`. Con la cuenta muerta el inbound no corre ⇒ queda congelado |
| R1v2 | template `item[5830]/mapping[5844]` | rango: retira 217 si `!hasLinkedAccount(e22)` |
| L / ACT | template 5770 / 5847 | sin 215/216/217 ⇒ `draft`/`archived`; ACT solo limpia DISABLED |
| Triggers | template `mapping[5829]` N2-absence | precedente en PROD de un mapping que planta `TriggerType` (357 triggers vivos, Trigger Scanner cada 300 s) |

**Hallazgo (medido 29-oct):** `DATE_EXPIRY` **retrocede** cuando un semestre sale del horizonte: de los 39 con cuenta
viva, 21 tienen hoy `DATE_EXPIRY` 2026-06-30 aunque su módulo terminó el 28-oct. Una gracia calculada sobre
`DATE_EXPIRY` a secas no los cubriría. Y 6 de los 46 son **retiros** (cursos del semestre 283 en `ESTADO=3`
desde el 28-oct, fin previsto 27-nov): no deben tener gracia.

## 2. Diseño

| Id | Dónde | Regla |
|---|---|---|
| G1 5848 | template, `extension/studentEnrollmentLastEnd` | Fin real con memoria: sube con 218; si 218 baja y el fin previo **ya pasó** ⇒ conserva (salida del horizonte); si baja **antes** del fin previsto ⇒ acepta el menor (retiro/anulación) |
| G2 5849 | template, `extension/studentEnrollmentEffectiveEnd` | `G1 + N`. **N vive solo aquí.** Con 215/216 vivo ⇒ `G1` (sin gracia: alumno+personal no cambia) |
| IN 3381 | e22 `attribute[3324]/inbound` | `'student'` si `DATE_EXPIRY` ≥ hoy (igual que 3327) **o** hoy ≤ G2 del foco |
| R1v3 5850 | template `item[5830]` | rango: como R1v2, salvo cuenta muerta con hoy ∈ [G1, G2] |
| T1 5851 | template `mapping` → `trigger` | cuenta muerta en gracia ⇒ trigger de recompute en G2+1 (00:00 Lima); patrón N2 |

Por qué así: el inbound lee `focus` = `getObjectCurrentOrNew()` (`FullInboundsProcessing` l.120), es decir, G2
**persistido**: por eso G1/G2 se activan un día ANTES (fase A). `timeFrom` en R1v3 se descartó: en 4.10.2
`FocalMappingSetEvaluation` l.168 crea trigger para todo mapping con `timeFrom` futuro **sin mirar la condición**
(≈18.000: todos los alumnos vigentes); el patrón N2 solo planta para quien lo necesita. Una function library tampoco hace falta: N
está en un único `<code>` y el inbound lee el resultado (G2), no N.

**Cambiar N:** `patch-N-template-cambiar-N.xml.ejemplo` (replace de `mapping[5849]/expression`) + recompute de
quien tenga G1 en los últimos max(N viejo, N nuevo) días. Bajar N no adelanta triggers ya plantados (disparan
y recomputan, inocuo).

## 3. Ficheros

| Fichero | Efecto en producción |
|---|---|
| `patch-00-schema-v34-mas-2-items.xml` | replace de `c:definition` = **v34 de PROD** + 2 elementos. Regenerar con `g90_build.py repo` si la versión ya no es 34 (el replace pisa el definition entero) |
| `patch-01-template-proposed.xml` | +G1/G2/R1v3/T1 `proposed`; R1v2 5844 → `deprecated` ⇒ inerte en producción |
| `patch-02-e22-inbound-proposed.xml` | +inbound 3381 `proposed`; 3327 → `deprecated` ⇒ inerte en producción |
| `patch-10-template-G1G2-activar.json` | Fase A: publica G1/G2 (nadie los consume aún) |
| `patch-11c/12c` (fuera del repo: `g90_build.py canario <dir> <codigos>`) | Canario: R1v3/T1/inbound acotados (5852/5853/3382) `active`; 5844/3327 `archived` |
| `patch-20-template-global-activar.json` + `patch-21-e22-global-activar.json` | Global |
| `rollback-00/01/02/10/11c/12c/20/21` | Vuelta atrás de cada paso |

Simulación: `lib/sim.py` + `lib/sim-inyectada.groovy` (template y e22 parcheados EN MEMORIA, clockwork en modo
SIMULATED_*; los ítems nuevos se sustituyen por `lastReviewedAt`/`schacExpiryDate`, definidos y sin uso en PROD,
porque el schema nuevo aún no existe). `g90_build.py sim <dir> [hoy]` genera esas variantes.

## 4. Despliegue (ventana 16:10–07:00 UTC; `date -u` antes de cada paso; `rest.sh` = PATCH + versión)

1. Respaldo (`backup-pre.sh` del runbook de activación) + GET raw de schema/template/e22.
2. `patch-00` (schema v34→35); verificar ambos `xsd:element` y que la UI muestra los ítems.
3. `patch-01` (template 137→138) y `patch-02` (e22 209→210; `<schema>` intacto, test connection).
4. SIM PRE = SIM POST en producción (deben coincidir); SIM dev de la muestra = §5.
5. `patch-10` (fase A). Esperar una recon de Estudiantes (G1/G2 para ~30.000) o recompute acotado.
6. Lote de backfill (fuera del repo): replace G1/G2 para los que ya retrocedieron (Oracle, horizonte −90 d).
7. Canario: `patch-11c` + `patch-12c`; recompute **reconcile=true** de la lista; verificar en auditoría.
8. Global: `patch-20` + `patch-21`. La siguiente recon de Estudiantes aplica la gracia (ver efecto retroactivo).
9. Lote único: añadir 217 a las cuentas muertas en gracia (no-retiros); T1 planta su trigger.

## 5. Simulación (29-oct, 18:25–18:38 UTC, sin persistencia; muestra 79 = los 46 + 33 controles)

`lib/sim.py` con template/e22 parcheados en memoria; recompute `reconcile=true`. El PATCH del schema se aplicó a
una copia en memoria: 102 → 104 `xsd:element`, parsea.

| Corrida | Config | Resultado |
|---|---|---|
| R0 | producción, PROD tal cual | línea base (cambios latentes ajenos: title/costCenter/rejectedAt) |
| R1 | producción + patch-01/02 | **= R0** (2 diferencias, solo `modifyTimestamp`): los proposed/deprecated son inertes |
| R2 | desarrollo + patch-01/02, sin datos | 13 de los 46 (fin 28-oct, sin retroceso) → active; 21 con retroceso → solo G1/G2 (sin backfill no hay gracia); 6 cuentas muertas → solo G1/G2; 6 retiros sin cambio; controles: solo G1/G2 |
| R3 | desarrollo + G1/G2 de backfill + 217 a las 6 muertas | **40/46 → active/ENABLED** (LDAP enabled + `student`; Koha enabled), 6 triggers en fin+90+1; **6 retiros siguen draft** (incl. el que tenía 217 inyectado: R1v3 lo retira); vigentes, duales, 216-solo, 215-solo: solo G1/G2 (duales EFF = G1) |
| R4 | R3 con HOY = 2027-01-27 | los de fin 28-oct pierden 217 (inbound y R1v3); fin 29-oct siguen (inclusivo); duales pierden 217 al pasar su fin |
| R5 | producción + fase A + canario (8) | **solo los 7 no-retiro del canario cambian**; el retiro del canario sigue draft; fuera del canario R1v3 retira como R1v2 |

Efecto global medido (PG + Oracle, 29-oct): al activar en global recuperan 217 los alumnos-solo con cuenta e22 viva
y fin en los últimos 90 días (**288**, incluidos 13 de los 46) en la recon siguiente; **66** más con retroceso
necesitan el backfill; **6** cuentas muertas necesitan el lote de 217. Alumno+personal en la ventana (**560**): sin
cambio (EFF = G1).

⚠️ Observado al simular: el pool ConnId de e22 tenía 3 conexiones Oracle muertas en silencio; el primer acceso
tras el reposo esperó ~50 min (≈17 min por conexión: `tcp_retries2=15`) cerrándolas una a una **con el lock del
pool tomado**. Probable causa de recons de Estudiantes lentas. No se tocó nada; queda como hallazgo aparte.

## 6. Registro de despliegue

| Fecha (UTC) | Paso | Resultado |
|---|---|---|
| 2026-10-30 02:47 | 1 respaldo raw de schema v34, template v137, e22 v209 (fuera del repo) | OK; `patch-00` parte de la v34 viva (102 elementos, idénticos) |
| 2026-10-30 02:49 | 2 `patch-00` | schema v35, 104 `xsd:element` |
| 2026-10-30 02:49 | 3 `patch-01` + `patch-02` | template v138, e22 v210; `<schema>` de e22 intacto (30), test connection todo `success` |
| 2026-10-30 02:52 | 5 `patch-10` (fase A) | template v139: 5848/5849 `active`; 5850/5851/3381 `proposed`; 5844/3327 `deprecated` |
| — | 4 SIM PRE/POST | no repetida: R1 = R0 ya probó que patch-01/02 son inertes; verificado por lifecycleState |
| 2026-10-30 11:20–12:08 | recon Estudiantes (48 min) | G1/G2 en 30.130 de 30.241 con 218; G2−G1 = 90 d en 25.100 y 0 en 5.030 (los de 215/216), sin excepciones; 30.113 éxitos, 29 fallos (antes 104). 111 sin G1: 108 sin cuenta e22 viva (incluye las 6 del lote 217) + 3 entre los fallos |
| 2026-10-30 13:18 | 6 backfill (una conexión SSH por PATCH) | cortado por el .166 (rechaza ráfagas de SSH): 6 de 72 aplicados |
| 2026-10-30 13:18 | 7 canario | solo `patch-11c` (template v140); `patch-12c` y el recompute no llegaron |
| 2026-10-30 13:19 | 8 global, **sin canario verificado** | template v141, e22 v211 (no v212: el replace sobre `inbound[3382]`, que nunca se creó, fue no-op; comprobado: 0 restos, `<schema>` 30). Config = estado global previsto; `5852`/`5853` quedan `archived` |
| 2026-10-30 13:19 | 9 | detenido por su chequeo previo (sin G1/G2) |
| 2026-10-30 13:26 | 6 resto (`una-sesion.sh`: 1 conexión) | 72/72 en 10 s, 0 errores |
| 2026-10-30 13:27–13:29 | 7 canario (verificación de la global), recompute reconcile=true | SUCCESS: 5 → `active` + student, LDAP y Koha MODIFY SUCCESS; 1 sigue draft (gracia vencida); las 2 muertas sin cambio |
| 2026-10-30 14:06 | 9 lote 217 a las 6 cuentas muertas | 6/6 `active` + student, LDAP y Koha SUCCESS, 1 trigger cada una en G2+1 00:00 Lima |
| pendiente | recon Estudiantes 31-oct 11:20 UTC | debe reactivar ≈288; medir |

Decisiones del 29-oct: se acepta el efecto retroactivo (≈288), se aplica el backfill (66) y alumno+personal sin gracia.

## Limpieza (preparada 2-nov-2026, ejecutable ya, en ventana 16:10–07:00 UTC, después del paso 7 de activacion-vinculo-vivo)
`limpieza/limpieza.sh` borra lo que el paso global del 30-oct dejó `archived`: template 5844 (R1v2), 5852 (R1v3
canario), 5853 (T1 canario) y el inbound 3327 de e22 (217 sin gracia). No calculan nada: el borrado no cambia ninguna
ficha. Guardas: ventana, ninguna recon corriendo, los 4 `archived` y los vivos de la gracia (5848..5851,
e22 3381) `active`, `<schema>` de e22 con 30 `xsd:element`, parches regenerados del GET de ese momento idénticos a los
revisados, versiones sin cambios justo antes del PATCH (se toman de la lectura: el template estará en v142 si ya se hizo
el paso 7 de activacion-vinculo-vivo). Después: versiones +1, los 4 ausentes, vivos intactos, `<schema>` 30, test
connection de e22. Respaldo: `limpieza/out/{tpl,e22}-antes.xml`.
⚠️ Tras la limpieza `rollback-20/21` dejan de servir solos (cambian el estado de algo que ya no existe): primero
`limpieza.sh --rollback` (re-añade los 4 `archived`; ❓ no probado en PROD) y luego `rollback-20/21`.
No incluye e22 3329/3362 (`archived`, de trabajos anteriores a la gracia).
