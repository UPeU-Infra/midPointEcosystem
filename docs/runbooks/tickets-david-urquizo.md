# Instrucciones para David Urquizo — Tareas IGA UPeU

**Owner:** Alberto Sánchez (DTI/Infra)
**Destinatario:** David Urquizo (admin Microsoft 365 + Entra ID + AD UPeU)
**Contexto:** Proyecto MidPoint IGA — gestión de identidades centralizada.

Este documento concentra las tareas que MidPoint **no puede ejecutar por API** y que requieren acción manual de David en los sistemas Microsoft que él administra.

---

## Alcance acotado (decisión 2026-05-11)

| Sistema | Fase actual (1–11) | Fase 12 (futuro) |
|---|---|---|
| **Entra ID UPeU** | **Solo lectura** — correlación de identidades y licencias | Gobierno completo (writes coordinados con David) |
| **AD UPeU actual** | ❌ OUT del alcance — no se toca | Decisión sobre AD nuevo, si Entra ID no alcanza |
| **M365 (licencias A1/A3)** | Solo lectura inventario | Asignación por archetype (gobernado por MidPoint) |
| **Google Workspace** | No aplica (UPeU usa M365) | — |

---

## Reglas del documento

1. **Cada tarea tiene un ID** (`DU-NNN`) para tracking.
2. **Estado**: 🟡 Pendiente · 🔵 En curso · 🟢 Completada · ⚫ Bloqueada · ⚪ Diferida (Fase 12).
3. **Alberto agrega** tareas a medida que avanzan las fases.
4. **David ejecuta** y marca completada con timestamp y notas.

---

## Tareas activas para Fases 1–11

### DU-001b — Ampliar permisos App `MidPoint-UPeU` con 4 permisos read faltantes 🟡

**Para:** Fase 5.5 (Resource Entra ID READ ONLY — completar cobertura).
**Sistema:** Microsoft Entra ID UPeU (`upeu.onmicrosoft.com`) — App Registration ya existente.
**Contexto:**

La App `MidPoint-UPeU` (appId `94dd7b5b-...`, creada 2026-04-16) ya tiene 3 permisos Application concedidos:
- `User.Read.All` ✅
- `Group.Read.All` ✅
- `Directory.Read.All` ✅

MidPoint puede leer usuarios y grupos. Para completar la cobertura de lectura necesitamos 4 más.

**Acción solicitada:**

En el tenant UPeU, sobre la App Registration `MidPoint-UPeU` existente (appId `94dd7b5b-...`):

1. Ir a **Azure Portal → Entra ID → App registrations → MidPoint-UPeU → API permissions**.
2. Agregar los siguientes permisos (**Microsoft Graph**, tipo **Application**, no Delegated):
   - `AdministrativeUnit.Read.All`
   - `RoleManagement.Read.Directory`
   - `AuditLog.Read.All`
   - `Application.Read.All`
3. **Grant admin consent** explícitamente para los 4 permisos nuevos.
4. Confirmar que el total queda en 7 permisos Application con estado "Granted for UPeU".

**Justificación:**

| Permiso | Para qué lo necesita MidPoint |
|---|---|
| `AdministrativeUnit.Read.All` | Leer las 5 AUs existentes (3 correctas, 2 anti-patrón detectadas en análisis 2026-05-19) |
| `RoleManagement.Read.Directory` | Auditar 86 role assignments actuales — prerequisito para governance de roles |
| `AuditLog.Read.All` | Logs de cambios de identidad — prerequisito para informes de cumplimiento |
| `Application.Read.All` | Inventariar 200 app registrations (incluye bots Copilot Studio a revisar) |

**Output esperado:** Confirmación de "Granted" en los 4 permisos. No se necesita nuevo secreto.

---

### DU-001a — Credenciales Graph API para tenant UPeU real (no sandbox) 🟡

**Para:** Fase 5.5 (Resource Entra ID READ ONLY).
**Sistema:** Microsoft Entra ID UPeU (`upeu.onmicrosoft.com` o equivalente productivo).
**Contexto:**

Verifiqué que el `msgraph.env` actual de Alberto apunta al tenant `SciBack` (sandbox personal de SciBack como producto), NO al tenant UPeU productivo:

- App: `SciBack-ClaudeCode`
- Tenant ID: `267b5db1-0490-4716-9aaf-3cb94a321357`
- Dominio: `sciback.com`
- 12 usuarios simulados

Para que MidPoint pueda **leer** Entra ID UPeU necesitamos credenciales propias del tenant productivo.

**Acción solicitada:**

1. En el tenant UPeU productivo, crear App Registration:
   - **Nombre:** `MidPoint-IGA-UPeU-Read`
   - **Tipo:** Single tenant, application
2. **API permissions** (Microsoft Graph, tipo **Application**, no Delegated):
   - `User.Read.All`
   - `Group.Read.All`
   - `Directory.Read.All`
   - `Organization.Read.All`
   - `LicenseAssignment.Read.All` (si existe)
3. **Grant admin consent** explícitamente.
4. Crear **Client Secret** con vigencia 24 meses, anotar el valor (solo se muestra una vez).
5. Compartir vía canal seguro:
   - Tenant ID
   - Client ID (Application ID)
   - Client Secret

**Output esperado:** archivo `.env` que Alberto guardará como `~/.secrets/msgraph-upeu.env`.

**Justificación:** Permisos mínimos de lectura para mapeo canónico inicial. Sin writes hasta Fase 12.

---

### DU-002 — Inventario de M365 grupos relevantes (read) 🟡

**Para:** Fase 5.5 + Fase 7.1.
**Sistema:** Entra ID UPeU.
**Contexto:**

Una vez DU-001a esté completo, MidPoint puede leer los grupos automáticamente. Pero antes me ayudaría tener tu **mapa actual**:

**Pregunta para David:**

¿Existen ya grupos en Entra ID UPeU que clasifiquen usuarios por:
- Tipo (docentes / estudiantes / staff / egresados)?
- Sede / Campus (Lima / Juliaca / Tarapoto)?
- Facultad o Escuela Profesional?
- Tipo de licencia M365 (A1 vs A3)?

Si sí: compartir lista (nombres + uso). Si no: en Fase 12 los crearemos según modelo canónico.

**Output esperado:** lista (puede ser texto/markdown/screenshot UI).

---

### DU-003 — Reachability red MidPoint DEV → Microsoft Graph 🟢

**Estado:** Verificado por Alberto 2026-05-11.

**Resultado:** Desde MidPoint DEV (`192.168.15.230`) hay conectividad TCP a `graph.microsoft.com:443`. ✅

**Notas:** Oracle LAMB (`192.168.13.9:1521`) NO es alcanzable desde DEV — verificar firewall si Resource JDBC va a vivir en DEV o si conviene desplegarlo solo en PROD.

---

### DU-004 — Confirmar que UPeU usa Microsoft 365 (no Google Workspace) 🟢

**Estado:** Confirmado por Alberto 2026-05-11.

**Confirmación:** UPeU usa **Microsoft 365** (licencias A1/A3). NO usa Google Workspace como suite principal.

**Pregunta residual** (ticket DU-007):

¿Sigue activo algún uso legacy de Google Workspace? `DAVID.ACAD_CARGA_PLAN_CLASSROOM` en Oracle LAMB tiene 79,835 registros con URLs de Google Classroom — pero esas pueden ser solo URLs externas registradas y las cuentas Google podrían ser personales de docentes. Confirmar.

---

### DU-008 — Corrección de tipos de documento en Oracle LAMB (199 personas con CE/Pasaporte mal clasificados como DNI) 🟡

**Para:** Calidad de datos IGA — impacta `taxId` canónico en MidPoint.
**Sistema:** Oracle LAMB (ERP institucional — fuente de verdad de personas).
**Contexto:**

Durante el fix de documentos de identidad de extranjeros (2026-06-06) se detectaron **199 personas activas** cuyo tipo de documento en LAMB aparece como **DNI** pero cuyo número de documento es alfanumérico (contiene letras), lo que indica que son CE (Carné de Extranjería) o Pasaporte. MidPoint no puede inferir el tipo correcto sin que la fuente lo diga bien.

Esto afecta el campo `schacPersonalUniqueID` de cada persona en el directorio institucional.

**Acción solicitada (para el equipo que administra Oracle LAMB / el ERP):**

1. Ejecutar la siguiente consulta en Oracle LAMB para identificar los casos:
   ```sql
   -- Personas con tipo_doc = 'DNI' pero número alfanumérico (CE/Pasaporte)
   SELECT ID_PERSONA, NRO_DOCUMENTO, TIPO_DOCUMENTO
   FROM MOISES.PERSONA_NATURAL
   WHERE TIPO_DOCUMENTO IN ('1', 'DNI') -- ajustar según el código real de DNI en LAMB
     AND REGEXP_LIKE(NRO_DOCUMENTO, '[A-Za-z]')
   ORDER BY NRO_DOCUMENTO;
   ```
2. Corregir el `TIPO_DOCUMENTO` al valor correcto (CE, Pasaporte, según corresponda).
3. Notificar a Alberto cuando esté corregido para lanzar el recompute en MidPoint.

**Justificación:** El identificador `schacPersonalUniqueID` es parte del perfil eduPerson de cada persona y se propaga al LDAP institucional, Keycloak (SSO) y eventualmente al directorio activo. Un tipo de documento incorrecto genera un identificador canónico incorrecto.

**Output esperado:** Confirmación de que los 199 registros fueron corregidos en LAMB, con fecha de corrección.

---

### DU-009 — Revisión de 65 personas con dos números de documento distintos en sus registros 🟡

**Para:** Calidad de datos IGA — detectado durante limpieza 2026-06-06.
**Sistema:** Oracle LAMB (ERP) + MidPoint.
**Contexto:**

65 personas activas tienen **dos entradas de documento** en MidPoint con el mismo tipo pero números diferentes. Esto ocurre porque dos mappings distintos (uno legacy, uno nuevo) apuntan a fuentes distintas en LAMB que no coinciden. La causa raíz probable es que el número de documento fue actualizado en una tabla de LAMB pero no en otra.

**Acción solicitada:**

1. Alberto generará un CSV con los 65 casos (OID, código, nombre, número 1, número 2) y lo compartirá.
2. El equipo de LAMB verifica cuál es el número de documento vigente para cada persona.
3. Se corrige en la tabla autoritativa.
4. MidPoint hace recompute automático.

**Output esperado:** CSV revisado con columna "número correcto" marcada.

---

### DU-007 — Decisión sobre Google Classroom 🟡

**Para:** Decidir alcance (probablemente NO se gobierna).
**Sistema:** Google Workspace UPeU (si existe legacy).

**Pregunta:**
- ¿Existe un tenant Google Workspace institucional `upeu.edu.pe`?
- ¿Las clases de Google Classroom las crean docentes con sus cuentas Google personales o institucionales?
- ¿Quién las administra centralmente?
- ¿IGA debe gestionarlo o queda fuera?

**Recomendación inicial:** queda fuera del IGA (no gobernamos cuentas Google), salvo que confirmes que es un sistema institucional crítico.

---

## Tareas diferidas a Fase 12 (cuando MidPoint esté maduro)

### DU-012-1 — Credenciales WRITE en tenant UPeU ⚪

**Para:** Fase 12.4 (Resource Entra ID WRITE).
**Sistema:** Microsoft Entra ID UPeU.

**Acción futura:** Cuando lleguemos a Fase 12, ampliar la App `MidPoint-IGA-UPeU-Read` (o crear `MidPoint-IGA-UPeU-Write` separada) con permissions adicionales:

- `User.ReadWrite.All`
- `Group.ReadWrite.All`
- `Directory.ReadWrite.All`
- `LicenseAssignment.ReadWrite.All`
- (opcional) `RoleManagement.ReadWrite.Directory`

**No solicitar todavía.** Primero validamos modelo en MidPoint Fases 1–11.

---

### DU-012-2 — Política de licenciamiento M365 ⚪

**Para:** Fase 12.4.
**Sistema:** M365 + Entra ID.

**Propuesta inicial (a refinar en Fase 12):**

| Archetype MidPoint | Licencia M365 (SKU sugerida) |
|---|---|
| `student` (Pregrado) | A1 for Students (gratis) |
| `student` (Posgrado/Doctorado) | A1 for Students + OneDrive ampliado |
| `employee-faculty` (TC ordinario) | A3 (pagada) |
| `employee-faculty` (TP) | A1 for Faculty (gratis) o A3 |
| `employee-staff` | A3 (pagada) |
| `alumni` | Sin licencia M365 |
| `contractor` | A1 o sin licencia según contrato |
| `affiliate-partner-institution` | Sin licencia |

**Datos que necesitaremos para la decisión:**
- Cantidad de licencias A3 disponibles
- Licencias huérfanas recuperables (cuentas inactivas)
- Costo por licencia / presupuesto disponible

---

### DU-012-3 — Migración progresiva por archetype ⚪

**Para:** Fase 12.5.

**Plan:** orden de migración para minimizar impacto:
1. `service-account` (low impact)
2. `affiliate-researcher` (pocos usuarios, visitantes)
3. `employee-staff` (más estructurado, RR.HH. autoritativo)
4. `employee-faculty` (incluye categorización docente)
5. `student` (volumen masivo, último)

Cada bloque requiere ventana operativa y rollback documentado.

---

## Tareas RETIRADAS (decisión 2026-05-11)

- ~~**DU-003-orig** — Cuenta de servicio `svc-midpoint-iga` en AD~~. AD UPeU actual queda OUT del alcance. No se gestiona desde MidPoint. Si en Fase 12 se decide construir AD nuevo, se abrirá una nueva tarea aparte.
- ~~**DU-005-orig** — Política sobre creación de cuentas en Entra ID~~. Diferido a Fase 12.

---

## Tareas completadas

- **DU-004** (2026-05-11) — Confirmar stack M365 (vs Google Workspace) — ✅
- **DU-003** (2026-05-11) — Reachability red MidPoint DEV → Graph — ✅

---

## Plantilla para nuevas tareas

```markdown
### DU-NNN — Título corto 🟡

**Para:** Fase X.Y del roadmap
**Sistema:** Entra ID / M365 / otro (NO AD UPeU actual)
**Contexto:** [3-5 líneas]

**Acción solicitada:**
1. [paso 1]
2. [paso 2]

**Justificación:** [norma ISO / razón técnica / dependencia]

**Output esperado:** [qué necesita Alberto de vuelta]
```
