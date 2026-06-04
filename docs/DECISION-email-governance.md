# DECISIÓN CANÓNICA — Gobernanza de correo institucional UPeU

**Estado:** RATIFICADA (validada vs estándares IGA + libro Semančík/Evolveum, 2026-06-04)
**Ámbito:** modelo de `emailAddress` / `mail` en el IGA UPeU (Oracle LAMB → MidPoint → LDAP/Entra/Koha)
**SSOT:** este documento.

---

## 1. Enunciado de la regla (refinado y canónico)

### 1.1 Un solo correo principal por persona, alias ilimitados
- Cada persona tiene **un (1) solo buzón personal institucional** = su correo PRINCIPAL canónico, formato `nombre.apellido@upeu.edu.pe`.
- Una persona puede tener **alias ilimitados** (apuntan al mismo buzón). Los alias **NO** son identidades ni cuentas separadas.

**Separación de capas (obligatoria — eduPerson + schema MidPoint):**

| Concepto | Atributo canónico | Multiplicidad | Dónde vive |
|---|---|---|---|
| Identidad principal (login, federación) | `eduPersonPrincipalName` (ePPN) | **single, no reasignable** | LDAP cache / Keycloak |
| Correo principal canónico | `emailAddress` (MidPoint) → `mail` primario | **single** (schema core MidPoint) | foco MidPoint |
| Alias entregables | valores adicionales de `mail` / `proxyAddresses` | multi | LDAP cache / Entra-M365 (Fase 12) |

- Los alias **NO se materializan como `emailAddress`** (es single-value por schema; "schema is the law"). Van como `mail` multivaluado en LDAP o `proxyAddresses` en M365.
- A los SP federados (REFEDS R&S) se publica el `mail` principal (o ePSA `student@upeu.edu.pe` por privacidad), **nunca la lista de alias**.

### 1.2 Correos de cargo / funcionales — entidades separadas
Los correos de cargo (`gerencia.infraestructura@upeu.edu.pe`) y de sistema (`noreply-ojs@upeu.edu.pe`) **NO son personas** y **NUNCA** se correlacionan como `emailAddress` de una persona física.

Modelado canónico:
- **Cargo institucional** → buzón colgado de la `OrgType` (o `ServiceType`) que lo posee. El titular actual se modela como `assignment` con `relation="manager"`/`owner` a esa org; el acceso al buzón compartido se concede vía rol/entitlement.
- **Cuenta de sistema** (`noreply-*`) → archetype **`service-account`** (UserType service-account o ServiceType). Sin auth interactiva.

### 1.3 Cadena de autoridad del `emailAddress` (IIA + fallback)
- **IIA autoritativa = Oracle LAMB `CORREO_INST`** → inbound **`strong` + `<range>`** (gobierna; reemplaza valor obsoleto, no acumula).
- **Fallback no-autoritativo = Entra ID `mail`** → inbound **`weak`** (solo aporta valor **si `emailAddress` está vacío**; NUNCA sobrescribe a Oracle).
- **Consolidación = un único `emailAddress`** en el foco MidPoint.

> Esto NO viola "una sola IIA por atributo" (`iga-canonical-standards §1.3`): hay **una IIA (Oracle)** + **un enricher de fallback (Entra)**. La precedencia es inequívoca por la fuerza del mapping (`strong` vs `weak`). Entra es inbound-only (proposed) hasta Fase 12 → solo lectura → consistente con leerlo como fallback.

### 1.4 Buzón principal ante duplicados (one person, multiple accounts)
Cuando una persona tiene **varias cuentas** que representan el mismo buzón personal (caso Tito: `dan.tito` + `dantito`), es un **duplicado de reality**, NO un multiaccount legítimo. MidPoint reconcilia reality→policy: **1 account-link válido por persona por resource**.

**Criterio de selección del PRINCIPAL (en orden):**
1. **Coincidencia con el ePPN canónico** (`nombre.apellido`): `dan.tito` (forma canónica) gana sobre `dantito`. El ePPN single/no-reasignable es el árbitro.
2. **Uso real** (último login vía `signInActivity` — requiere `AuditLog.Read.All` + Entra ID P1) y datos vinculados (licencia M365 activa, historial). Evita destruir un buzón con historial.
3. **Desempate:** `meta.created` más antiguo (SCIM §5.1).

Las cuentas duplicadas → **correlación negada** (shadow no-owned/unmatched) + **cola de deprovisioning Fase 12** (Entra inbound-only hoy no permite borrado; forzarlo reproduce `ObjectAlreadyExistsException`). El blindaje `getLinkedShadow` try/catch (tarea #65) es coherente: shadow huérfano no fuerza fallback.

---

## 2. Implicancias operativas

1. **Reduce el reporte a DTI:** los ~13.7k estudiantes y ~157 trabajadores sin `CORREO_INST` en Oracle, pero CON buzón en Entra, obtienen su correo vía el fallback `weak` de Entra — no necesitan correo nuevo. Solo quedan para DTI los que no tienen buzón en ninguna fuente.
2. **Limpieza de duplicados** (tipo Tito) requiere `AuditLog.Read.All` (pendiente — David Urquizo) para aplicar el criterio #2 de uso real.
3. **Pendiente Fase 12:** deprovisioning real de cuentas duplicadas en Entra (hoy solo correlación negada + cola).

---

## 3. Fundamento normativo (citas ancla)

- **eduPerson 202208 §3.1/§3.3** — ePPN single-value, no reasignable; `mail` (de inetOrgPerson, RFC 4524/2798) multivaluado.
- **ISO 24760 §1.1** — identity (conjunto de atributos) vs identifier (atributo distintivo único). Alias = valores del mismo atributo, no identidades nuevas.
- **SCIM §5.4 / §5.1** — `emails[primary].value → emailAddress`; `meta.created` para desempate.
- **MidPoint / Semančík** — `midpoint-best-practices` §1.1 (`emailAddress` core single), §3.2 (archetype Person/service-account), §4.2 (strength weak/normal/strong + range), §2.1/§6.4 (reality vs policy), §5.1/§5.5/§5.8 (Org abstract role, `relation=manager`, multiaccount tags), §6.6 ("suma, no resta").
- **iga-canonical-standards** §1.3 (IIA por-atributo + precedencia), §10.1 (service-account), §8.1 (R&S exige un `mail`), §7 (ISO 27001 A.5.16 — evidencia de gobierno de identidad).

---

## 4. Historial
- **2026-06-04** — Regla enunciada por J. A. Sánchez (DTI/Infra UPeU), validada doctrinalmente vs `iga-canonical-standards` + `midpoint-best-practices` + libro Semančík. Ratificada con 4 refinamientos de precisión (capas de identificador, modelado de cargos, semántica strong/weak, criterio de cuenta principal). Pendiente `AuditLog.Read.All` para la fase de limpieza de duplicados por uso real.
