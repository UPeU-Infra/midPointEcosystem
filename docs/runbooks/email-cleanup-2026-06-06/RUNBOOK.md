# Runbook: Email Cleanup 2026-06-06/07

**Objetivo:** Eliminar los emails numéricos (`codigo@upeu.edu.pe`) de todos los usuarios `active` en MidPoint PROD y establecer Entra ID como fuente de verdad para `emailAddress`.

**Ejecutado por:** Juan Alberto Sánchez  
**Fechas:** 2026-06-06 / 2026-06-07  
**Estado:** ✅ COMPLETADO

---

## 1. Estado inicial (antes de la limpieza)

| Categoría | Cantidad |
|---|---|
| Active sin email | ~11,836 |
| Active con email numérico (`\d+@upeu.edu.pe`) | 21,222 |
| Active con email real | 21,345 |
| **Total active** | **~54,403** |

Los emails numéricos (`201123128@upeu.edu.pe`, `97004321@upeu.edu.pe`, etc.) eran generados por MidPoint a partir del código universitario almacenado en Oracle LAMB (`CORREO_INST` = código). Fueron creados en fases anteriores cuando Oracle tenía un mapping STRONG sin guard de dominio.

---

## 2. Arquitectura objetivo

### Jerarquía de fuentes para `emailAddress`

| Prioridad | Fuente | Resource | Strength | Guard |
|---|---|---|---|---|
| 1 | `ri:mail` | Entra ID Graph | **STRONG** | `@upeu.edu.pe` + no numérico |
| 2 | `icfs:name` (UPN) | Entra ID Graph | WEAK | `@upeu.edu.pe` + no numérico |
| 3 | `CORREO_INST` | Oracle Trabajadores | WEAK | `@upeu.edu.pe` + no numérico |
| 4 | `CORREO_UPEU` | Oracle Estudiantes | WEAK | `@upeu.edu.pe` + no numérico |
| 5 | `ri:email` | Koha ILS | WEAK | `@upeu.edu.pe` + no numérico |
| — | **null** | — | — | `emailReviewNeeded=true` |

**Principio:** MidPoint solo usa emails que existen en fuentes reales. No inventa ni genera emails. Si ninguna fuente tiene email válido → campo vacío + flag de revisión.

**Guard universal aplicado en todos los inbounds:**
```groovy
def v = (input ?: '').toString().trim().toLowerCase();
if (!v.endsWith('@upeu.edu.pe')) return null;
def local = v.substring(0, v.indexOf('@'));
return local ==~ /\d+/ ? null : v
```

### Mappings en UserTemplate-Person-Base.xml

| Mapping | Tipo | Acción |
|---|---|---|
| `B-email-sanitize-numeric` | Template STRONG | Borra emailAddress si es numérico |
| `B-email-review-flag` | Template NORMAL | Setea `emailReviewNeeded=true` si emailAddress es null |

---

## 3. Archivos modificados

| Archivo | Commit | Cambio |
|---|---|---|
| `canonical/object-templates/UserTemplate-Person-Base.xml` | `a00ae20` | E2-retract-orphan condition: multi-línea → una línea con `;` |
| `canonical/object-templates/UserTemplate-Person-Base.xml` | `feec4e1` | B-email-sanitize-numeric: agregado `<target><path>emailAddress</path></target>` |
| `upeu/resources/entra-id-graph.xml` | `9917447` | `icfs:name` emailAddress inbound: `strong` → `weak` (UPN ≠ ri:mail) |
| `upeu/resources/entra-id-graph.xml` | *(sesión)* | `ri:mail` emailAddress inbound: agregado guard dominio + numérico |
| `upeu/resources/oracle-lamb/trabajadores.xml` | `402d11e` | `correo-inst-to-emailAddress`: agregado guard dominio; reimportado a PROD |
| `upeu/resources/oracle-lamb/estudiantes.xml` | `402d11e` | `correo-upeu-to-emailAddress`: agregado guard dominio; reimportado a PROD |
| `upeu/resources/koha-ils.xml` | `81dfba0` | `email-inbound`: agregado guard dominio (causa raíz de errores "2 values") |

---

## 4. Cronología de rondas y causas raíz

### r2 — Fallida
**Síntoma:** Task `cleanup-numeric-emails.xml` con `iterativeScripting` → 54,445 failures  
**Causa raíz:** Variable incorrecta. En `iterativeScripting`, la variable del objeto es `input`, no `object`.

### r4 — Fallida
**Síntoma:** FATAL_ERROR en usuarios con Entra ID  
**Causa raíz:** Oracle Trabajadores/Estudiantes en PROD tenía guard SOLO anti-numérico pero NO de dominio. Oracle proponía gmail/hotmail como ADD simultáneo con Entra ID proponiendo `@upeu.edu.pe` → conflicto "2 values" en campo single-valued.  
**Fix aplicado:** Reimportar Oracle trabajadores + estudiantes (el guard de dominio ya existía en el repo local desde commit `402d11e`, faltaba en PROD).

### r5 — Fallida
**Síntoma:** FATAL_ERROR persistente en usuarios con shadow Koha  
**Causa raíz real:** `koha-ils.xml` `email-inbound` no tenía guard de dominio. Los registros Koha almacenan emails personales (gmail, hotmail) del borrower en `ri:email`. Sin filtro, Koha proponía gmail como ADD en la misma wave que Entra ID proponía `@upeu.edu.pe` → "2 values". **Esta era la causa raíz principal** del error en cascada.  
**Fix aplicado:** Guard dominio en Koha email-inbound (commit `81dfba0`).

### r6 — Fallida (parcialmente)
**Síntoma:** Errores "2 values" con dos emails `@upeu.edu.pe` distintos  
**Causa raíz:** Algunos usuarios tienen UPN ≠ ri:mail en Entra ID (ej: `jorgemaquera@upeu.edu.pe` vs `jorge.maquera@upeu.edu.pe`). Ambos inbounds (`icfs:name` y `ri:mail`) eran STRONG → conflicto STRONG+STRONG.  
**Fix aplicado:** `icfs:name` → emailAddress cambiado de STRONG a WEAK (commit `9917447`). `ri:mail` permanece STRONG como campo canónico M365.

### r7 — Fallida
**Síntoma:** Task completó sin errores pero 21,223 emails numéricos sin cambio  
**Causa raíz:** `B-email-sanitize-numeric` en el template tenía `<source>` y `<expression>` correctos pero **carecía de `<target>`**. Sin `<target>`, el null STRONG generado por la expression era descartado silenciosamente → los 21,223 emails nunca se limpiaron en r4/r5/r6/r7.  
**Fix aplicado:** Agregado `<target><path>emailAddress</path></target>` (commit `feec4e1`).

### r8 — Fallida (silenciosa)
**Síntoma:** Task completó en 01:27 Lima pero 21,223 emails numéricos sin cambio  
**Causa raíz:** El template en PROD sí tenía el target correcto (reimportado antes de r8). El problema es que la recomputation con `reconcile=true` **cuelga** al intentar reconciliar contra Entra ID (bug MidPoint 4.10: `CreateCapability` missing en el connector MSGraph). El clockwork no completaba la wave de reconciliation para usuarios con shadow Entra ID.

### r9 — Fallida
**Síntoma:** Iteraciones, cero cambios en DB  
**Causa raíz:** `.replace()` sin argumentos en `raw()` es un no-op en Groovy.  
**Fix:** Usar `.replaceRealValues(java.util.Collections.emptyList())`.

### r10 — Fallida
**Síntoma:** Groovy syntax error en ejecución  
**Causa raíz:** MidPoint normaliza el contenido de `<code>` al deserializar el task XML a una sola línea. El script multi-línea `import UserType\ndef user = input` se convierte en `import UserType def user = input` → Groovy syntax error.  
**Fix:** Script en una **sola línea** con `;` como separadores de statements.

### r11 — ✅ ÉXITO
**Mecanismo:** `iterativeScripting` con:
- Variable `input` (correcta para este tipo de activity)
- Guard en Groovy: `emailStr.matches('^\\d+@upeu\\.edu\\.pe$')`
- Delta: `.replaceRealValues(java.util.Collections.emptyList())`
- `ModelExecuteOptions.raw()` vía reflection
- **Script en una sola línea** (CDATA inline) — crítico para sobrevivir normalización MidPoint
- Canary PASS: usuario `7e21d884` (`201440023@upeu.edu.pe`) → email borrado

**Resultado:** 21,222 emails numéricos eliminados en ~N minutos.

---

## 5. Estado final

| Categoría | Cantidad |
|---|---|
| Active numéricos (`\d+@upeu.edu.pe`) | **0** ✅ |
| Active con email real | 21,345 (invariante) |
| Active sin email | 33,059 |
| **Total active** | **~54,404** |

### Desglose de los 33,059 sin email

| Origen | Aprox. |
|---|---|
| Tenían email numérico, ahora limpio (nunca tuvieron email real) | ~21,222 |
| Nunca tuvieron email en ninguna fuente | ~11,837 |
| **Total** | **~33,059** |

Estos usuarios **no tienen email institucional asignado en ningún sistema fuente** (sin `ri:mail` en Entra ID, sin `CORREO_INST` válido en Oracle, sin email válido en Koha). MidPoint refleja correctamente la realidad: campo vacío. No es un bug.

El grueso son estudiantes — encaja con GAP-2: 13,733 estudiantes sin `CORREO_INST` en Oracle (Lima 9,175 / Juliaca 5,299 / Tarapoto 1,717). Reporte generado para DTI.

---

## 6. Lecciones aprendidas — Patrones reutilizables SciBack

### L1: Guard universal para emails institucionales
Todos los inbounds que mapean a `emailAddress` deben tener este guard:
```groovy
def v = (input ?: '').toString().trim().toLowerCase();
if (!v.endsWith('@upeu.edu.pe')) return null;
def local = v.substring(0, v.indexOf('@'));
return local ==~ /\d+/ ? null : v
```
Aplica a: Oracle, Koha, Entra ID (icfs:name y ri:mail).

### L2: Fuentes externas no filtradas → "2 values"
Koha almacena emails personales (gmail, hotmail) en `ri:email`. Sin guard de dominio, propone gmail como ADD simultáneamente con otra fuente → conflicto "2 values" en campo single-valued. **Regla:** cualquier resource que traiga datos de usuarios externos (borrowers, empleados) DEBE tener guard de dominio en el inbound de emailAddress.

### L3: UPN ≠ ri:mail en Entra ID
El UPN (`icfs:name`) es el login de Microsoft 365 y puede diferir del mailbox real (`ri:mail`). Usar UPN como STRONG para emailAddress causa conflicto cuando ambos campos tienen valores distintos. **Regla:** `icfs:name` → emailAddress = WEAK; `ri:mail` → emailAddress = STRONG.

### L4: Template mapping sin `<target>` = silently discarded
Un mapping de template con `<source>` y `<expression>` pero sin `<target>` no produce ningún error. El output simplemente se descarta. Difícil de detectar. **Regla:** verificar siempre que los mappings de template tengan `<target>` explícito.

### L5: Self-referential template mapping + reconcile bug
Un mapping de template `source=emailAddress → target=emailAddress` (STRONG null para limpiar el campo) es válido en teoría, pero `recomputation` con `reconcile=true` cuelga en MidPoint 4.10 cuando el usuario tiene shadow Entra ID (bug CreateCapability MSGraph). No usar `reconcile=true` en recomputation masiva mientras Entra ID esté en `proposed`.

### L6: iterativeScripting — CDATA multilínea falla en REST
MidPoint normaliza el contenido de `<code>` a una sola línea al deserializar tasks vía REST API. El script multi-línea `import X\ndef y` se convierte en `import X def y` → Groovy syntax error. **Regla:** en tasks importados vía REST, usar siempre CDATA inline (una línea, `;` como separador). CDATA multilínea solo es válido en boot import (`/var/objects/`) o vía ninja.

### L7: iterativeScripting — variable correcta es `input`
En `iterativeScripting`, la variable del objeto procesado es `input`, NO `object`. Usar `object` causa 100% de failures sin mensaje de error claro.

### L8: Entra ID clientSecret no está en el XML
El `clientSecret` de Entra ID Graph NO se almacena en `entra-id-graph.xml` (gestionado en keystore cifrado MidPoint). Cada REST PUT del resource wipa el secret → re-inyectar inmediatamente después de cada PUT. Ver procedimiento en comentario del XML.

---

## 7. Pendientes post-cleanup

| Item | Estado |
|---|---|
| Verificar `emailReviewNeeded=true` para los 33,059 sin email | Pendiente |
| Desglose de 33,059 por archetype (estudiante/trabajador/alumni) | Pendiente |
| GAP-2: reporte DTI para 13,733 estudiantes sin CORREO_INST | Generado localmente |
| Fase 12: Entra ID write (requiere DU-001b David Urquizo) | Bloqueado |

---

## 8. Artefactos

| Archivo | Descripción |
|---|---|
| `upeu/tasks/email-cleanup-2026-06-06/cleanup-numeric-emails-r11.xml` | Task final válido — patrón reutilizable |
| `upeu/tasks/email-cleanup-2026-06-06/recompute-clean-emails-r4.xml` | r4: primera ronda recompute |
| `upeu/tasks/email-cleanup-2026-06-06/recompute-clean-emails-r8.xml` | r8: última ronda recompute (fallida por bug reconcile) |
| `canonical/object-templates/UserTemplate-Person-Base.xml` | Mappings B-email-sanitize-numeric + B-email-review-flag |
| `upeu/resources/entra-id-graph.xml` | icfs:name WEAK + ri:mail STRONG con guards |
| `upeu/resources/koha-ils.xml` | email-inbound con guard dominio |
| `upeu/resources/oracle-lamb/trabajadores.xml` | correo-inst-to-emailAddress con guard dominio |
| `upeu/resources/oracle-lamb/estudiantes.xml` | correo-upeu-to-emailAddress con guard dominio |
