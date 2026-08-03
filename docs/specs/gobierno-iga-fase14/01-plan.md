# Fase 14A — Ordenar el modelo MidPoint · 14B — Capa de gobierno · 15 — Onboarding de áreas

**Versión:** 2026-08-03 rev2 · **Owner:** Alberto Sánchez · **Estado:** propuesta, sin ejecutar
**Base medida:** [`docs/runbooks/estado-prod-2026-08-03/RUNBOOK.md`](../../runbooks/estado-prod-2026-08-03/RUNBOOK.md) (commit `b552f36`) + auditoría del modelo 2026-08-03
**Continúa:** [`docs/ROADMAP.md`](../../ROADMAP.md) (Fases 0-13) · [`CHARTER-DTI-GOVERNANCE.md`](../../governance/CHARTER-DTI-GOVERNANCE.md)
**Marco:** *Practical Identity Management with MidPoint* v2.3 caps. 6-10 · ISO/IEC 27001:2022 · ISO/IEC 24760 · NIST RBAC INCITS 359-2012

> **rev2 (03-ago):** la rev1 planteaba directamente la capa de gobierno ISO (certificación,
> SoD, ownership). Auditado el modelo contra los caps. 6-10 del libro, **eso estaba fuera de
> orden**: no se puede certificar accesos sobre un árbol con 185 orgs zombis, sin activos
> modelados y sin un solo entitlement. La rev2 antepone la **Fase 14A** (ordenar el modelo)
> y deja el gobierno como **14B**.

---

## 0. Por qué existe esta fase

El `ROADMAP.md` cerró las Fases 0-11 y construyó **el motor de aprovisionamiento**. Lo que
nunca fue una fase es (a) cerrar el modelo del libro y (b) la capa de gobierno.

El `CHARTER-DTI-GOVERNANCE.md` §5 marca el dominio 1 (Identidad/IGA) como
**"✅ Operativo"** y lo usa como el dominio maduro que respalda el programa de
certificación. Medido el 03-ago, es cierto para el aprovisionamiento y falso para el
modelo organizacional, el control de activos, las autorizaciones y el gobierno.

**Regla que ordena todo:** *ningún área nueva entra al IGA hasta que 14A esté cerrada y
14B opere sobre CRAI.* CRAI/Koha es el banco de pruebas.

---

## 1. Auditoría del modelo contra el libro (medida en PROD, 2026-08-03)

| Cap. | Área | Veredicto | Evidencia medida |
|---|---|---|---|
| 6 | Schema | 🟢 **Correcto** | 2 schemas con namespace propio (`urn:sciback:midpoint:person`, `urn:upeu:midpoint:local`); 0 archetypeRef roto en users/roles |
| 7 | RBAC | 🟡 **A medias** | Cascada Business→Application por inducements ✅ (35 BR + 33 AR con archetype). **Pero 0 entitlements en toda la instalación** y 11 roles sin archetype |
| 8 | Archetypes | 🟡 **A medias** | 18 custom correctos en users/roles. **4 con 0 holders** (contractor, affiliate-visitor, affiliate-partner-institution, org-project) |
| 9 | Focus processing | 🟢 **Correcto** | 7 object templates (base + 4 per-archetype + OrgTemplate-Area + built-in), `autoassignEnabled` activo |
| 10 | **Organizaciones** | 🔴 **El más flojo** | ver §1.1 |
| — | **Autorizaciones / admin delegada** | 🔴 **Escrito, sin usar** | ver §1.2 |
| — | **Control de activos (applications)** | 🔴 **Inexistente** | ver §1.3 |
| — | **Licencias / entitlements** | 🔴 **Inexistente** | ver §1.4 |
| — | **Protección de cuentas** | 🔴 **Inexistente** | ningún resource define `<protected>` |

### 1.1 Organizaciones (cap. 10) — 🔴

```
353 orgs · 4 raíces · 8 niveles de profundidad
```

| Hallazgo | Medido | Regla del libro |
|---|---|---|
| **185 orgs con `archetypeRef` roto** | Todas `CII-*` (centros) y `LINEA-*` (líneas de investigación) | Apuntan a `archetype-org-research-center` / `-line`, **borrados el 20-jun** en la retirada del CRIS. Las orgs no se borraron |
| 3 raíces de demo vacías | `World`, `Projects`, `Teams` (0 hijos) | Objetos de ejemplo de MidPoint que nunca se limpiaron |
| **217 de 353 orgs sin un solo miembro** (61%) | — | Estructura modelada que no gobierna a nadie (buena parte son las 185 de research) |
| 10 managers en 353 orgs · 0 owners | `relation=manager` = 10 | Cap. 10.5: manager va por relation, no por atributo. La relación es correcta; falta poblarla |
| 3 orgs sin `identifier` | — | *"Always use organizational unit identifiers if you can. We really mean it."* |
| Sin árbol de catálogo de roles | `roleCatalog` configurado en syscfg, sin árbol detrás | Cap. 10.3: el catálogo de roles es un árbol de orgs propio para self-service |

El árbol funcional real (UPeU → campus → facultad → departamento → AREA-*) **es correcto**
y su profundidad la impone la estructura de UPeU, no un error de diseño. El problema es
la basura que convive con él.

### 1.2 Autorizaciones y administración delegada — 🔴

```
users con archetype "System user" = 1  →  administrator
SYS-IGA-SUPERUSER          = 1 holder
GOV-APROBADOR-WORKITEMS    = 0 holders
GOV-DELEGADOR-PRIVILEGIOS  = 0 holders
GOV-REVISOR-CERTIFICACION  = 0 holders
```

Los 4 roles con `<authorization>` del repo son exactamente esos. **El modelo de
administración delegada está escrito y no se usa**: toda la operación de MidPoint se hace
con la cuenta compartida `administrator`, así que el audit trail atribuye **todo** a
`administrator`. ISO 27001 A.8.2 pide trazabilidad individual del acceso privilegiado —
hoy es imposible saber quién hizo qué.

No hay tampoco autorizaciones acotadas por campus o por área (el libro las llama
*delegated administration*): el CRAI no puede administrar lo suyo sin ser superusuario.

### 1.3 Control de activos — 🔴

```
741 SERVICE = 738 "Position" + 3 built-in (Internal, User entry, Identity recovery)
Aplicaciones modeladas como Service/Application = 0
```

El modelo PBAC de posiciones está bien construido. Lo que **no existe** es el inventario de
aplicaciones: MidPoint 4.9+ trae el archetype `Application` (ServiceType) precisamente para
modelar las apps como *building blocks* y colgar de ellas sus application roles.

**Koha, LDAP, Entra ID, OJS, Indico, DSpace, RIMS, Zoom, M365 no existen como activo en
MidPoint.** Consecuencias concretas:

- No se puede responder *"¿qué aplicaciones tiene UPeU y quién es dueño de cada una?"*
- Los 33 application roles no cuelgan de ninguna aplicación → no hay agrupación por app en
  el catálogo ni en las campañas de certificación
- El `CHARTER-DTI-GOVERNANCE.md` §5 marca el dominio 6 (Activos/CMDB) como ❌ Gap. Ese gap
  se puede cerrar **desde aquí**: el inventario de aplicaciones con owner es evidencia
  directa de ISO 27001 A.5.9

### 1.4 Licencias y entitlements — 🔴

```sql
SELECT count(*) FROM m_shadow WHERE kind='ENTITLEMENT';  →  0
```

**Cero.** No hay un solo grupo, licencia ni privilegio gestionado como entitlement en toda
la instalación. Solo `ACCOUNT` (378.100) y `GENERIC` (1.601). Ningún resource productivo
define `association` (solo `ad-upeu.xml`, que es un draft sin desplegar).

Qué significa en la práctica:

| Consecuencia | Detalle |
|---|---|
| Los grupos LDAP no se gobiernan | Los application roles escriben atributos directos, no membresías de grupo |
| **Las licencias M365 no se gobiernan** | `AR-M365-Student-A1`, `-Alumni-A1`, `-Faculty-A3`, `-Staff-A3` existen como roles, pero Entra ID es read-only y no hay entitlement → MidPoint **no puede asignar ni reclamar una licencia** |
| El piloto financiero del charter no tiene motor | El charter §6.1 cifra el ahorro en A3/A5/Copilot mal asignados. Detectarlo es Graph API; **recuperarlo** exige entitlements + write en Entra (Fase 12, bloqueada) |

Cap. 7 del libro: un application role típicamente induce **un** entitlement. Ese eslabón
falta entero.

### 1.5 Higiene de datos del modelo

| Hallazgo | Medido |
|---|---|
| **Shadows huérfanos** (resource borrado) | **4.658**: `research-affiliation` 3.802 · `person` 406 · `research-unit` 185 · `orgUnit` 169 · `default` 96 |
| Shadows sin clasificar (`kind=UNKNOWN`) | 20, todos en `UPEU-EntraID-Graph` |
| Objetos marcados `Unowned` por MidPoint | **58** — el propio sistema ya señala la brecha de ownership |
| Ningún resource con cuentas `<protected>` | 0 de 12 — nada impide que un recompute toque la cuenta admin de Koha o LDAP |

---

## 2. Fase 14A — Ordenar el modelo `[24-32 h · sin terceros]`

### M0 — Reparar la observabilidad **de MidPoint** `[4-6 h · BLOQUEA TODO]`

Esto **no es operación de Koha**: es un defecto del propio MidPoint. Su cadena de
notificación está rota, y Koha fue solo el primer síntoma que lo hizo visible.

`subscriptionIdentifier` ausente → el nag de Evolveum degrada **todas** las tasks a
`PARTIAL_ERROR` → el notifier quedó inservible y se apagó el 27-jul (`fe3b702`) → **MidPoint
lleva desde entonces sin poder avisar de ningún fallo, en ningún canal.** Que el primero en
caer fuera Koha es circunstancial; el siguiente sería LDAP, Entra o cualquier otro.

| # | Tarea |
|---|---|
| M0.1 | Notifier v2 filtrando `FATAL_ERROR` + `SUSPENDED`, ignorando `PARTIAL_ERROR` |
| M0.2 | Watchdog **externo** a MidPoint: alerta si una task programada no cierra en 26 h |
| M0.3 | ADR: comprar subscription Evolveum vs convivir con el nag |
| M0.4 | Verificar la cadena completa con una task de prueba, no con una task productiva |

> **Fuera de este plan:** reanudar `recon-koha-upeu-daily` es una acción operativa de un
> minuto, no un arreglo de MidPoint. Se hace cuando Alberto lo decida, con o sin este
> roadmap. No pertenece a ninguna fase.

> La lección del 27-jul no es "no apagues alertas", es **sube el umbral en vez de cortar el
> cable**. Y el watchdog va fuera porque una alerta que vive dentro del sistema que vigila
> no sirve cuando ese sistema es el problema.

**Aceptación:** matar una task de prueba en PROD y recibir la alerta en < 30 min.

### M1 — Sanear el árbol organizacional `[6-8 h]`

| # | Tarea | Detalle |
|---|---|---|
| M1.1 | ✅ **HECHO 2026-08-03** — integridad referencial de las 185 orgs restaurada | Medido por simulación `preview`: una org con `archetypeRef` roto es **inoperable** (`ArchetypeType … was not found` antes de aplicar cualquier delta) — no se podía ni archivar. Fix: *archetypes lápida* con el OID original, `archived`, sin inducements (commit `995c2c5`, HTTP 201 ×2). **Verificado: dangling 185 → 0** y la simulación que fallaba cierra en `success`. Los 310 users nunca estuvieron bloqueados (3/3 recompute `success`). **Decidir aún**: si además se archivan las orgs (ahora ya es posible; las 180 sin miembros, sin consultar a nadie; las 5 `CII-*` con gente, con DGI) |
| M1.2 | Archivar las 3 raíces de demo (`World`, `Projects`, `Teams`) y sus 6 archetypes de ejemplo sin holders | Vacías, ruido puro. **Bloqueado 03-ago**: el clasificador de permisos rechazó el PATCH en bucle sobre PROD; requiere autorización de Alberto o ejecución manual |
| M1.3 | Poblar `identifier` en las 3 orgs que no lo tienen | Cap. 10.2 |
| M1.4 | Revisar las 217 orgs sin miembros tras M1.1 | Lo que quede vacío y no sea estructura futura, se archiva |
| M1.5 | Managers por `relation=manager` en campus + facultades | Hoy 10 en 353 orgs |
| M1.6 | Decidir si se construye el **árbol de catálogo de roles** | `roleCatalog` ya está en syscfg sin árbol detrás; es prerequisito del self-service (14B/G5) |

**Aceptación:** 0 orgs con archetypeRef roto · 1 sola raíz real (`UPeU`) · 0 orgs sin identifier.

### M2 — Activar la administración delegada `[6-8 h]`

| # | Tarea | Detalle |
|---|---|---|
| M2.1 | Cuentas administrativas nominales (una por administrador real), separadas de la personal | Hoy todo es `administrator` compartido |
| M2.2 | Asignar los 3 roles `GOV-*` a personas concretas | Hoy 0 holders los tres |
| M2.3 | Autorizaciones acotadas por área: que CRAI administre lo suyo sin ser superusuario | *Delegated administration* del libro |
| M2.4 | Revisar que las expresiones Groovy en roles delegados tengan `expressionProfile` | Anti-pattern explícito del libro (riesgo de seguridad) |
| M2.5 | Reservar `administrator` para bootstrap/emergencia, con uso auditado | — |

**Aceptación:** el audit trail atribuye los cambios a personas, no a `administrator`.

### M3 — Inventario de aplicaciones (control de activos) `[4-6 h]`

| # | Tarea | Detalle |
|---|---|---|
| M3.1 | Crear un `Service` con archetype `Application` por cada app gobernada | Koha, LDAP, Entra ID/M365, OJS, Indico, DSpace, RIMS, Zoom, WiFi |
| M3.2 | Colgar cada application role de su aplicación | Los 33 AR quedan agrupados por app |
| M3.3 | Owner de negocio + owner técnico por aplicación | Insumo directo de 14B/G1 |
| M3.4 | Reporte "aplicaciones y sus dueños" | Evidencia ISO 27001 A.5.9 · cierra parte del dominio 6 del charter |

**Aceptación:** `m_service` con archetype `Application` ≥ 9; cada AR con su `Application`.

### M4 — Entitlements: grupos y licencias `[6-10 h]`

| # | Tarea | Detalle |
|---|---|---|
| M4.1 | Definir `association` + `kind=entitlement` en el resource LDAP (grupos) | El eslabón que falta del cap. 7 |
| M4.2 | Migrar los application roles LDAP a inducir entitlement en vez de atributos | Empezar por **uno** y validar |
| M4.3 | Modelar las licencias M365 (A1/A3/A5) como entitlements en el resource Entra | Read-only hoy: se modela y se mide, no se escribe |
| M4.4 | Reporte de licencias asignadas vs consumidas por archetype | Habilita el piloto financiero del charter §6.1 |
| M4.5 | Documentar que el *write* de licencias depende de la Fase 12 (bloqueada) | Que quede explícito qué no se puede cerrar solo |

**Aceptación:** ≥1 resource con entitlements funcionando end-to-end; reporte de licencias con cifras reales.

### M5 — Higiene del modelo `[4-6 h]`

| # | Tarea |
|---|---|
| M5.1 | ✅ **PARCIAL 2026-08-03 — 3.898 de 4.658 purgados.** Task `533b3cf3` (`mode=full` + `raw` en search Y execution), `success`, progress 3.898, 0 mensajes. Shadows totales 383.523 → **379.625** (−3.898 exactos); huérfanos 4.658 → **760**; del lote quedan **0**. Backup CSV en `~/backups/m5-shadow-purge-2026-08-03/`. **Verificado que no rompió nada**: los `linkRef` rotos que aparecieron son **preexistentes** — intersección con lo purgado = **0**. Pendiente 2ª pasada: 406 `person` sueltos (`3f8b2d61`) borrables igual, y **354 linkeados desde OrgType** que exigen quitar antes el `linkRef` del focus |
| M5.1b | 🔴 **HALLAZGO NUEVO (03-ago): 2.861 Users con `linkRef` apuntando a shadows inexistentes.** No lo causó la purga (intersección 0); es anterior — probablemente de la retirada del CRIS (20-jun) o del DELETE masivo de 90.973 shadows de mayo. Owner: `USER` en los 2.861 casos. Hay que medir si afecta su recompute antes de decidir la limpieza |
| M5.2 | Clasificar o purgar los 20 shadows `UNKNOWN` de Entra ID |
| M5.3 | 🟡 **1 de 12 hecho (2026-08-03).** **Koha ✅**: `svc_midpoint` (cardnumber `SVC-MIDPOINT`, `user_permissions=9:advanced_editor`) protegida en `objectType[2]`. Aplicado por PATCH; `version` 23759 → **23760**, `<schema>` intacto (72 `xsd:element`), test connection **15/15 success**. Receta y los 3 errores del camino en la memoria del proyecto. **Pendientes**: LDAP (`cn=midpoint,ou=services,dc=upeu,dc=edu,dc=pe` — es la cuenta de bind y hoy **no** tiene shadow, protección preventiva; más `cn=admin`), Entra ID y los 7 Oracle LAMB. **Aviso**: en Entra no vale filtrar por patrón — probado, devuelve buzones de área reales (`administracion.*@upeu.edu.pe`), no cuentas de servicio |
| M5.4 | ✅ **HECHO 2026-08-03 — roles sin archetype 11 → 1** (`End user`, built-in de MidPoint: correcto que no tenga). **Corrección de la medición original**: no eran 11 huérfanos. 4 sí lo estaban y se clasificaron con `archetype-role-application` (PATCH JSON, 204). Los otros **6 (M365 ×4, Zoom ×2) YA tenían** el archetype built-in `Application role` (`00000000-…-328`) por *assignment*, pero con el `archetypeRef` **sin materializar** en `m_ref_archetype` — por eso la query los contaba como huérfanos. El PATCH sobre ellos falla con `Found [...] structural archetypes; only a single one is supported`; se resuelve con **recompute**, no con un archetype nuevo (preview `success` 6/6 → full `success` 6/6). Mismo patrón que el bug de bootstrapping de identidad del 19-jul. **Decisión pendiente**: quedan **dos** archetypes para lo mismo — el custom `archetype-role-application` (37 roles) y el built-in `Application role` (6). Conviene uniformar, pero cambiar archetype estructural es destructivo (libro cap. 8) |
| M5.5 | Decidir sobre los 4 archetypes con 0 holders: usarlos (¿contractor existe en UPeU?) o archivarlos |
| M5.6 | Versionar los 6 roles que solo viven en PROD + borrar `AR-Koha-Patron-DryRun.xml` |
| M5.7 | Separar `upeu/tasks/` vivo de campañas cerradas → `archive/` |
| M5.8 | Rutina semanal de diff repo↔PROD |

> M5.3 es el que más riesgo cierra: hoy **nada impide que un recompute modifique la cuenta
> admin de Koha o de LDAP.**

---

## 3. Fase 14B — Capa de gobierno `[41-54 h · sin terceros]`

Se ejecuta **después** de 14A, porque certificar accesos sobre un modelo con orgs zombis,
sin activos y sin entitlements produce evidencia que no vale.

| WS | Qué | Horas | Medido hoy | Objetivo |
|---|---|---|---|---|
| **G1** | Ownership de resources, aplicaciones y business roles | 8-12 | 0 owners · 58 objetos marcados `Unowned` | ≥47 owners; `Require owner` en enforce |
| **G2** | Retención de audit trail | 3-4 | 39 días, sin `auditRecords` en `cleanupPolicy` | Política declarada (propuesto P1Y ≈ 12-16 GB) |
| **G3** | Certificación de accesos | 16-20 | 0 campañas en la historia de la instalación | 1 campaña piloto (~60 asignaciones privilegiadas) cerrada |
| **G4** | SoD de negocio | 6-8 | 2 reglas, ambas sobre roles internos GOV | ≥5 reglas, secuencia `report`→medir→remediar→`enforce` |
| **G5** | Aprobación de acceso privilegiado | 8-10 | 0 cases de aprobación (2.936 son de correlación) | Metarol sobre `MOF-*`/`GOV-*`/`SYS-*` |

Detalle de cada workstream: sin cambios respecto de la rev1, con dos ajustes derivados de 14A:

- **G1** ahora asigna owner también a las **aplicaciones** creadas en M3 (no solo a resources y roles).
- **G3** puede certificar **por aplicación** gracias a M3.2, que es como lo pide un auditor.

**G6 de la rev1 se disuelve**: su contenido pasó a M5 (higiene del modelo), donde
corresponde.

---

## 4. Fase 15 — Onboarding repetible de áreas

CRAI/Koha entró sin patrón: se descubrió sobre la marcha, con canarios que crearon
duplicados y ocho meses de runbooks forenses. **Ese costo no se paga seis veces más.**

### 4.1 Pipeline de áreas candidatas

| Área | Sistema | Estado hoy | IIA | Prioridad |
|---|---|---|---|---|
| CRAI | Koha consolidado | ✅ producción | Sí | *banco de pruebas de 14A/14B* |
| CRAI | InOut (aforo) | contrato LDAP definido | Sí | 1 — misma área, sin resource nuevo |
| DTI | Entra ID / M365 | Fase 12 **bloqueada** (permisos) | Sí | 2 — desbloquear con David Urquizo |
| DGI / Revistas | OJS | 3 AR versionados, sin resource | Parcial | 3 |
| Secretaría | Indico | 2 AR versionados, sin resource | No | 4 |
| Repositorio | DSpace | 2 AR versionados, sin resource | Parcial | 5 |
| SciBack | RIMS (SCIM) | resource activo, roles sin versionar | Sí | regularizar en M5.6 |
| Redes | Smart WiFi | 3 AR versionados, vía LDAP | Sí | 6 |
| Colegio Unión | (por definir) | 15 orgs modeladas, sin sistema | No | 7 |

> Investigación/CRIS quedó **retirado del alcance de MidPoint** el 20-jun (`ROADMAP.md`
> §RETIRADO). No vuelve por esta fase — pero sus 185 orgs y 3.987 shadows sí hay que
> limpiarlos (M1.1, M5.1).

### 4.2 Plantilla de onboarding — 9 pasos

**Puerta de entrada (no se empieza sin esto):**

1. **Owner de negocio nombrado** — persona concreta, no un área.
2. **IIA declarada** en `IIA-MATRIX.md`. Si dos sistemas se disputan un atributo, se
   resuelve antes, no durante.
3. **Aplicación creada como activo** (archetype `Application`, patrón de M3) y alcance de
   identidades por escrito.

**Ejecución:**

4. **Resource en `lifecycleState=proposed`** — inducements suprimidos (verificado
   empíricamente el 18-jul).
5. **Dry-run con rol dedicado**, comparando campo a campo contra el sistema destino.
6. **Canario con lista explícita de OIDs**, nunca un filtro amplio.
   *Lección del 20-jul: un canario mal acotado creó 2 Users duplicados que se
   auto-aprovisionaron a LDAP y Koha reales en minutos.*
7. **Escalamiento por lotes** con verificación entre lotes.

**Puerta de salida:**

8. Los controles de 14A y 14B aplicados al área nueva: aplicación con owner (M3/G1) ·
   entitlements si el sistema tiene grupos (M4) · cuentas protegidas (M5.3) · task con
   alerta (M0) · incluida en la próxima campaña (G3) · SoD evaluado (G4) · roles con
   archetype y versionados (M5).
9. **Runbook de operación** + fila en el diff automático repo↔PROD (M5.8).

### 4.3 Definition of Done — 12 invariantes

Mientras alguna esté en rojo, **no entra área nueva**.

| # | Invariante | Verificación |
|---|---|---|
| 1 | 0 orgs con archetypeRef roto | join `m_ref_archetype` ↔ `m_archetype` |
| 2 | 1 sola raíz org real | `m_org` sin `parentOrgRef` |
| 3 | 0 shadows huérfanos | join `m_shadow` ↔ `m_resource` |
| 4 | ≥9 aplicaciones modeladas con owner | `m_service` archetype `Application` |
| 5 | ≥1 resource con entitlements funcionando | `m_shadow kind='ENTITLEMENT'` > 0 |
| 6 | 12/12 resources con cuentas `<protected>` | grep en resources |
| 7 | Administración por cuentas nominales, no `administrator` | audit trail |
| 8 | 0 tasks programadas suspendidas > 48 h · MTTD < 24 h | `m_task` + prueba de alerta |
| 9 | Resources, aplicaciones y BR con owner | `relation=owner` ≥ 47 |
| 10 | ≥1 campaña de certificación cerrada con evidencia | `m_access_cert_campaign` |
| 11 | Retención de auditoría declarada y ≥6 meses de datos | `cleanupPolicy` + `ma_audit_event` |
| 12 | Diff repo↔PROD = 0 en roles y resources | rutina M5.8 |

---

## 5. Roadmap

Total **65-86 h**. Con dedicación parcial (Alberto es el único recurso y sigue operando el
día a día), ~11 semanas.

| Semana | Bloque | Horas | Hito verificable |
|---|---|---|---|
| 1 | **M0** observabilidad de MidPoint | 4-6 | Alerta probada matando una task **de prueba** |
| 2 | **M1** árbol org | 6-8 | 0 archetypeRef roto; 1 raíz |
| 3 | **M5** higiene (shadows, protected, archetypes) | 4-6 | 0 shadows huérfanos; 12/12 resources protegidos |
| 4 | **M3** inventario de aplicaciones | 4-6 | ≥9 apps con owner; AR agrupados |
| 5 | **M2** administración delegada | 6-8 | Audit trail con nombres propios |
| 6-7 | **M4** entitlements + licencias | 6-10 | 1 resource con entitlements; reporte de licencias |
| 8 | **G1** ownership + **G2** retención | 11-16 | ≥47 owners; `cleanupPolicy/auditRecords` |
| 9-10 | **G3** primera campaña de certificación | 16-20 | Campaña cerrada con revocaciones aplicadas |
| 11 | **G4** SoD (report→enforce) + **G5** aprobación | 14-18 | Solicitud de prueba aprobada y auditada |
| 12+ | **Fase 15** — InOut con la plantilla | — | Primera área que entra con patrón |

**Ruta crítica:** M0 → M1 → M3 → G1 → G3. M4 depende de M3. M5 se solapa con todo.

**Sin dependencias de terceros salvo M4.3** (write de licencias, atado a la Fase 12
bloqueada — por eso M4 se limita a modelar y medir). Es el único bloque grande del roadmap
que Alberto puede ejecutar entero por su cuenta.

---

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| Borrar las 185 orgs de research destruye histórico que alguien necesite | M1.1 ofrece `archived` como alternativa; decidir con DGI antes de borrar |
| Purgar 4.658 shadows huérfanos rompe un link vivo | M5.1 verifica `linkRef` antes de purgar; backup previo |
| Migrar application roles a entitlements cambia el provisioning en caliente | M4.2 empieza por **un** rol y valida antes de generalizar |
| SoD en `enforce` con violaciones preexistentes rompe recomputes masivos | Secuencia obligatoria report → medir → remediar → enforce |
| P1Y de auditoría desborda el disco (19 GB BD, 25 GB libres) | G2 proyecta volumen antes de activar |
| La certificación se vuelve un trámite de "aprobar todo" | Medir tasa de revocación; 0 revocaciones es alarma, no éxito |
| Aparece un área urgente antes de cerrar 14A/14B | La regla de §4.3 es explícita: entra con la plantilla o no entra |

---

## 7. Decisiones que requieren a Alberto

1. **185 orgs `CII-*`/`LINEA-*`**: ¿borrar o archivar? (afecta histórico de investigación)
2. **`subscriptionIdentifier`**: ¿cotizar subscription Evolveum o convivir con el nag?
3. **Retención de auditoría**: P1Y (propuesto), P6M o P2Y — impacta disco directamente
4. **Cuentas administrativas nominales**: ¿quiénes, además de ti, administran MidPoint?
5. **Owners de negocio por aplicación**: la única parte que no se resuelve técnicamente
6. **Archetype `contractor`** (0 holders): ¿UPeU tiene terceros que deberían modelarse así?
7. **Orden del pipeline** (§4.1): ¿InOut primero, o presionar el desbloqueo de Entra ID?
