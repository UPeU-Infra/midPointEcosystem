# Fase 14 — Gobierno operativo del IGA · Fase 15 — Onboarding repetible de áreas

**Versión:** 2026-08-03 rev1 · **Owner:** Alberto Sánchez · **Estado:** propuesta, sin ejecutar
**Base medida:** [`docs/runbooks/estado-prod-2026-08-03/RUNBOOK.md`](../../runbooks/estado-prod-2026-08-03/RUNBOOK.md) (commit `b552f36`)
**Continúa:** [`docs/ROADMAP.md`](../../ROADMAP.md) (Fases 0-13) · [`CHARTER-DTI-GOVERNANCE.md`](../../governance/CHARTER-DTI-GOVERNANCE.md)
**Marco:** *Practical Identity Management with MidPoint* v2.3 caps. 7-10 · ISO/IEC 27001:2022 A.5.15-A.8.3 · ISO/IEC 24760 · NIST RBAC INCITS 359-2012

---

## 0. Por qué esta fase existe

El `ROADMAP.md` cerró las Fases 0-11 y dejó 12-13 bloqueadas por terceros. Las once fases
cerradas construyeron **el motor de aprovisionamiento**: schema, archetypes, object
templates, LDAP HA, resources, RBAC bottom-up, deploy. Ninguna construyó **la capa de
gobierno**: certificación, ownership, aprobación, evidencia de auditoría.

El `CHARTER-DTI-GOVERNANCE.md` §5 marca el dominio 1 (Identidad/IGA) como
**"✅ Operativo (MidPoint)"**. Medido contra ISO 27001 el 2026-08-03, eso es cierto para
A.5.16 (gestión de identidades) y falso para A.5.18 (revisión de derechos) y A.8.2
(acceso privilegiado). El charter usa el IGA como el dominio *maduro* que respalda al
resto del programa de certificación — así que la brecha del IGA es también una brecha
del programa.

**Regla que ordena esta fase:** *ningún área nueva entra al IGA hasta que la casa
tenga los seis controles de la Fase 14 operando sobre CRAI.* CRAI/Koha es el banco de
pruebas; lo que no funcione con un área no va a funcionar con seis.

---

## 1. Línea base medida (2026-08-03)

Todo lo de abajo salió de Postgres y del REST API de PROD, no del repo.

| Control | Norma | Medido | Objetivo Fase 14 |
|---|---|---|---|
| Campañas de certificación | ISO 27001 A.5.18 | **0** definitions / 0 campaigns / 0 cases | ≥1 campaña cerrada con evidencia |
| Owners de resources y business roles | Libro cap. 10.5 · policy `Require owner` | **0** `relation=owner`, 10 `manager` en total | 12/12 resources, 35/35 BR |
| SoD de negocio | INCITS 359 *Constrained RBAC* | **2** reglas, ambas sobre roles internos GOV | ≥5 reglas sobre riesgo real |
| Aprobación de acceso privilegiado | ISO 27001 A.8.2 | **0** cases de aprobación (2.936 son de correlación) | Metarol sobre `MOF-*`/`GOV-*`/`SYS-*` |
| Retención de audit trail | ISO 27001 A.5.16 / A.8.2 | **39 días** (25-jun→03-ago), sin `auditRecords` en `cleanupPolicy` | Política declarada (propuesto: P1Y) |
| Observabilidad de tasks | — (prerequisito de todo) | Notifier apagado 27-jul; Koha murió 28-jul; detectado 03-ago | Alerta por severidad, MTTD < 24 h |
| Roles con archetype | Libro cap. 8 | **11 sin archetype** de 89 | 0 |
| Cases de correlación abiertos | ISO 24760 (identidad no resuelta) | **102**, del 17-25 may | 0 |

**Lo que ya está conforme y no se toca:** 35 roles `business-role` + 33 `application-role`
con cascada por inducements (INCITS 359 §6.4 ✅), lifecycle ISO 24760 en uso real
(54.513 active / 7.968 archived / 732 draft ✅), `SecurityPolicy` + `ValuePolicy`
presentes, 39 marks built-in, `accessRequest` + `roleCatalog` ya configurados en la
system configuration.

---

## 2. Fase 14 — seis workstreams

Orden por **dependencia**, no por importancia. G1 habilita G3 y G5; G0 evita que todo lo
demás se degrade en silencio.

### G0 — Recuperar la observabilidad `[4-6 h · sin terceros · BLOQUEA TODO]`

**Problema medido:** `subscriptionIdentifier` ausente en la system configuration → el nag
de Evolveum degrada **todas** las tasks a `PARTIAL_ERROR` → el notifier Telegram spameaba
→ se apagó el 27-jul (`fe3b702`) → `recon-koha-upeu-daily` murió el 28-jul → detectado
el 03-ago. **MTTD = 6 días.**

| # | Tarea | Entregable |
|---|---|---|
| G0.1 | Reanudar `recon-koha-upeu-daily` (Koha verificado sano: 401 en 36 ms) | Task `RUNNABLE`, primera corrida limpia |
| G0.2 | Reactivar el notifier filtrando por `FATAL_ERROR` + `SUSPENDED`, ignorando `PARTIAL_ERROR` mientras dure el nag | `notification-telegram-alerts` v2 en repo y PROD |
| G0.3 | Watchdog independiente del notifier: query a `m_task` que alerte si una task programada no cierra `SUCCESS`/`PARTIAL_ERROR` en 26 h | Script + cron, fuera de MidPoint |
| G0.4 | Decidir `subscriptionIdentifier`: cotizar subscription Evolveum vs convivir con el nag | ADR corto con la decisión |

**Criterio de aceptación:** matar una task de prueba en PROD y recibir la alerta en < 30 min.

> Nota de diseño: la lección del 27-jul no es "no apagar alertas", es **subir el umbral en
> vez de cortar el cable**. G0.2 es exactamente eso.

### G1 — Ownership: que todo tenga dueño `[8-12 h · sin terceros]`

**Problema medido:** 490.591 role-memberships, de los cuales `relation=owner` = **0** y
`manager` = 10. La policy built-in `Require owner` existe y no tiene nada que exigir.

Sin owner no hay a quién certificar (G3) ni a quién enrutar una aprobación (G5). **Es el
cimiento de la fase.**

| # | Tarea | Entregable |
|---|---|---|
| G1.1 | Definir el *catálogo de dueños*: para cada uno de los 12 resources, quién es owner de negocio y quién owner técnico | `docs/governance/CATALOGO-OWNERS.md` |
| G1.2 | Asignar `relation=owner` a los 12 resources (p. ej. Koha → Dirección CRAI; LDAP/Entra → DTI; Oracle LAMB → dueño del dato, ver `IIA-MATRIX.md`) | 12 assignments en PROD + repo |
| G1.3 | Asignar `owner` + `approver` a los 35 business roles | 35 × 2 assignments |
| G1.4 | Activar la policy `Require owner` en modo `enforce` para roles y resources nuevos | `globalPolicyRule` versionada |
| G1.5 | Managers de org por `relation=manager` (hoy solo 10 en 353 orgs) — al menos los 3 campus y las facultades | assignments + verificación |

**Anclaje:** libro cap. 10.5 — *"MidPoint assigns managers to organizational units. That is
the right way to do it."* El anti-patrón (manager como atributo del user) **no** está
presente hoy; lo que falta es poblar la relación correcta.

**Criterio de aceptación:**
```sql
SELECT count(*) FROM m_ref_role_membership rm JOIN m_uri u ON u.id=rm.relationid
WHERE u.uri LIKE '%#owner';   -- debe pasar de 0 a ≥47
```

### G2 — Evidencia: audit trail que aguante una auditoría `[3-4 h · sin terceros]`

**Problema medido:** 1.661.065 eventos cubriendo **39 días**. `cleanupPolicy` declara
`closedTasks P30D`, `closedCases P30D`, `outputReports P7D`, `objectResults P7D` — y
**no declara `auditRecords`**. La retención real la decide `audit-partition-maintenance.sh`,
no una política.

| # | Tarea | Entregable |
|---|---|---|
| G2.1 | Decidir la retención (propuesto **P1Y**: cubre un ciclo académico completo + auditoría anual) y declararla en `cleanupPolicy/auditRecords` | system-configuration versionada |
| G2.2 | Proyectar el volumen: julio pesó 1.328 MB → P1Y ≈ 12-16 GB sobre una BD de 19 GB. Decidir disco o archivado externo antes de activar | Nota de capacidad |
| G2.3 | Alinear `audit-partition-maintenance.sh` con la política (que el script ejecute la decisión, no la tome) | Script actualizado |
| G2.4 | Reporte de evidencia: "quién otorgó qué acceso y cuándo", exportable | Report object en PROD |

**Anclaje:** ISO 27001 A.5.16 y A.8.2 piden el audit trail como evidencia primaria.
39 días no cubre un semestre.

### G3 — Certificación de accesos `[16-20 h la primera · 4 h las siguientes]`

**Problema medido:** cero campañas en la historia de la instalación. El rol
`GOV-REVISOR-CERTIFICACION` existe desde mayo y nunca revisó nada.

**No empezar por las 63.214 identidades.** Primera campaña deliberadamente pequeña y real:

| Alcance de la campaña piloto | Volumen aprox. |
|---|---|
| `SYS-IGA-SUPERUSER` + 3 roles `GOV-*` | ~5 asignaciones |
| 25 roles `MOF-*` (cargos de dirección) | ~40 asignaciones |
| 7 roles `AR-Koha-Librarian-*` (incluye el `CIA-Admin` no versionado) | ~15 asignaciones |

~60 asignaciones, revisor = el owner definido en G1.

| # | Tarea | Entregable |
|---|---|---|
| G3.1 | `AccessCertificationDefinition` para acceso privilegiado, iteración trimestral | XML versionado |
| G3.2 | Ejecutar la campaña piloto en DEV (`192.168.15.230`) | Campaña cerrada en DEV |
| G3.3 | Ejecutar en PROD con revisores reales | Campaña cerrada + decisiones aplicadas |
| G3.4 | Runbook de la campaña recurrente | `docs/runbooks/certificacion-accesos/` |
| G3.5 | Segunda campaña: acceso a Koha por categoría (patrons), muestreo, no censo | Definición lista para Q4 |

**Criterio de aceptación:** `m_access_cert_campaign` ≥ 1 con estado cerrado y decisiones
(`accept`/`revoke`) registradas; las revocaciones se materializaron en Koha/LDAP.

**Anclaje:** ISO 27001 A.5.18 — la evidencia que pide cualquier auditor.

### G4 — SoD de negocio `[6-8 h · sin terceros]`

**Problema medido:** 2 reglas activas, ambas separando roles internos de MidPoint
(`SoD-Aprobador-excluye-Revisor` y su simétrica). La única regla que nació de un conflicto
real (`SoD-Excluye-Koha-Administrativo-05436990`) se acotó a **un solo usuario** y luego se
archivó — mitigación individual, no política.

Reglas candidatas (a validar con los owners de G1):

| # | Exclusión | Riesgo que cubre |
|---|---|---|
| S1 | `AR-Koha-Librarian-*` ⊥ `AR-Koha-Patron-Administrativo` | Quien administra la biblioteca no se auto-gestiona préstamos (el conflicto que ya explotó) |
| S2 | Administración de RR.HH. ⊥ administración de nómina | Fraude clásico, A.8.2 |
| S3 | `SYS-IGA-SUPERUSER` ⊥ cualquier rol operativo de negocio | Cuenta administrativa separada de la personal |
| S4 | `GOV-APROBADOR-WORKITEMS` ⊥ solicitante del mismo ámbito | Nadie aprueba lo propio |
| S5 | Rol de docente ⊥ rol de registrador de notas del mismo programa | Integridad académica |

| # | Tarea | Entregable |
|---|---|---|
| G4.1 | Taller con owners: validar S1-S5 y descartar lo que no aplique | Acta corta |
| G4.2 | Implementar como `policyRule` con `exclusion`, primero en modo `report` | Policies en DEV |
| G4.3 | Medir violaciones existentes antes de pasar a `enforce` | Reporte de violaciones |
| G4.4 | Pasar a `enforce` sólo tras remediar el stock | Policies activas en PROD |

**Anclaje:** INCITS 359 *Constrained RBAC* (SSoD estático). MidPoint lo implementa con
`policyRule/exclusion` (skill `iga-canonical-standards` §6.5).

> Secuencia obligatoria `report` → medir → remediar → `enforce`. Activar SoD en enforce con
> violaciones preexistentes rompe recomputes masivos.

### G5 — Aprobación de acceso privilegiado `[8-10 h · sin terceros]`

**Problema medido:** de 2.936 cases, cero son de aprobación. Todo acceso en UPeU es
birthright automático. Para acceso ordinario **eso es correcto y no se cambia**. Para
acceso privilegiado, A.8.2 pide asignación *event-by-event* con registro.

| # | Tarea | Entregable |
|---|---|---|
| G5.1 | Metarol `metarole-privileged-approval` con `approvalProcess` | XML versionado |
| G5.2 | Aplicarlo a `SYS-IGA-SUPERUSER`, `GOV-*`, `MOF-*` de dirección y `AR-Koha-Librarian-*` | Assignments de metarol |
| G5.3 | Enrutar la aprobación al `approver` definido en G1 | Verificado con solicitud de prueba |
| G5.4 | Publicar el `roleCatalog` (ya configurado, sin uso) para solicitud self-service | Catálogo visible |

**Criterio de aceptación:** una solicitud de `AR-Koha-Librarian-Circulacion` genera un case
de aprobación, lo aprueba el owner de CRAI, y el audit trail lo registra.

### G6 — Higiene que bloquea el gobierno `[6-8 h · sin terceros]`

No es limpieza cosmética: cada punto impide que un control de arriba funcione.

| # | Tarea | Por qué bloquea |
|---|---|---|
| G6.1 | Archetype a los 11 roles sin él (4 `AR-M365-*`, 2 `AR-Zoom-*`, 3 `AR-RIMS-Cataloger-Campus-*`, `AR-Koha-Patron-Staff`) | Sin archetype no heredan el metarol de G5 ni entran en las campañas de G3 |
| G6.2 | Cerrar los 102 cases de correlación abiertos desde mayo (todos del Koha viejo) | Son identidades sin resolver: ISO 24760 §identity resolution |
| G6.3 | Versionar los 6 roles que solo viven en PROD (5 `AR-RIMS-*` + `role-svc-ai-identity-reader`) | Lo no versionado es lo no gobernado |
| G6.4 | Borrar `AR-Koha-Patron-DryRun.xml` (untracked, ya inexistente en PROD) | Residuo que ensucia el diff repo↔PROD |
| G6.5 | Separar `upeu/tasks/` vivo de campañas cerradas → `archive/` | Hoy no se puede responder "qué corre" leyendo el repo |
| G6.6 | Rutina semanal de diff repo↔PROD (roles, resources, tasks) | El drift reapareció el 20-jul y el 03-ago: es crónico, necesita automatización |

---

## 3. Fase 15 — Modelo de onboarding de áreas

CRAI/Koha entró al IGA sin patrón: se descubrió sobre la marcha, con campañas de
recompute, canarios que crearon duplicados y ocho meses de runbooks forenses. **Ese costo
no se puede pagar seis veces más.** La Fase 15 convierte lo aprendido en un procedimiento.

### 3.1 Pipeline de áreas candidatas

| Área | Sistema | Estado hoy | IIA definida | Prioridad |
|---|---|---|---|---|
| CRAI | Koha consolidado | ✅ en producción | Sí | *banco de pruebas de Fase 14* |
| CRAI | InOut (aforo) | contrato LDAP definido | Sí | 1 — misma área, sin resource nuevo |
| DTI | Entra ID / M365 | Fase 12 **bloqueada** (permisos) | Sí | 2 — desbloquear con David Urquizo |
| DGI / Revistas | OJS | 3 AR versionados, sin resource | Parcial | 3 |
| Secretaría / Eventos | Indico | 2 AR versionados, sin resource | No | 4 |
| Repositorio | DSpace | 2 AR versionados, sin resource | Parcial | 5 |
| SciBack | RIMS (SCIM) | resource activo, 3 shadows, **roles sin versionar** | Sí | regularizar en G6.3 |
| Redes | Smart WiFi (802.1X) | 3 AR versionados, vía LDAP | Sí | 6 |
| Colegio Unión | (por definir) | 15 orgs modeladas, sin sistema | No | 7 |

> Investigación/CRIS quedó **retirado del alcance de MidPoint** el 2026-06-20
> (`ROADMAP.md` §RETIRADO). No vuelve por esta fase.

### 3.2 Plantilla de onboarding — 9 pasos, con puerta de entrada y de salida

Basada en la *First Steps Methodology* de Evolveum, adaptada a lo que costó CRAI.

**Puerta de entrada (no se empieza sin esto):**

1. **Owner de negocio nombrado** — persona concreta, no un área. Sin owner no hay onboarding.
2. **IIA declarada** en `IIA-MATRIX.md` — qué atributo es autoritativo de quién. Si dos
   sistemas se disputan un atributo, se resuelve *antes*, no durante.
3. **Alcance de identidades por escrito** — qué archetypes entran, qué campus, qué volumen
   estimado.

**Ejecución:**

4. **Resource en `lifecycleState=proposed`** — inducements suprimidos, sin efecto real
   (patrón verificado empíricamente el 18-jul, ver memoria del proyecto).
5. **Dry-run con rol dedicado** y un puñado de focos reales; comparar campo a campo contra
   el sistema destino.
6. **Canario acotado** — con lista explícita de OIDs, nunca un filtro amplio.
   *Lección del 20-jul: un canario mal acotado creó 2 Users duplicados que se
   auto-aprovisionaron a LDAP y Koha reales en minutos.*
7. **Escalamiento por lotes** con verificación entre lotes, no un `reconcile` global.

**Puerta de salida (el área no se declara "onboardeada" sin los cinco):**

8. **Los seis controles de Fase 14 aplicados al área nueva:**
   - owner y approver asignados (G1)
   - task de reconciliación con alerta configurada (G0)
   - incluida en el alcance de la próxima campaña de certificación (G3)
   - reglas SoD evaluadas para sus roles (G4)
   - roles con archetype y versionados en repo (G6)
9. **Runbook de operación** + fila en el diff automático repo↔PROD (G6.6).

### 3.3 Criterio de "casa arreglada" (Definition of Done de Fase 14)

Ocho invariantes, todas verificables con una query. Mientras alguna esté en rojo, **no
entra área nueva**:

| # | Invariante | Query / verificación |
|---|---|---|
| 1 | Cero tasks programadas suspendidas > 48 h | `m_task` executionstate |
| 2 | MTTD de fallo de task < 24 h | prueba de alerta |
| 3 | 12/12 resources y 35/35 business roles con owner | `m_ref_role_membership` relation owner |
| 4 | ≥1 campaña de certificación cerrada con evidencia | `m_access_cert_campaign` |
| 5 | Retención de auditoría declarada y ≥ 6 meses de datos | `cleanupPolicy` + `ma_audit_event` |
| 6 | ≥5 reglas SoD de negocio en `enforce`, 0 violaciones abiertas | `m_object` POLICY |
| 7 | Acceso privilegiado con aprobación registrada | `m_case` tipo approval |
| 8 | Diff repo↔PROD = 0 en roles y resources | rutina G6.6 |

---

## 4. Roadmap propuesto

Estimación total **51-68 h**. Asumiendo dedicación parcial (Alberto es el único recurso y
sigue operando el día a día), ~8 semanas.

| Semana | Workstream | Horas | Hito verificable |
|---|---|---|---|
| 1 | **G0** observabilidad + G6.4 | 5-7 | Koha reanudado; alerta probada matando una task |
| 2 | **G2** retención + G6.2 cases | 6-8 | `cleanupPolicy/auditRecords` en PROD; 102 → 0 cases |
| 3-4 | **G1** ownership (el bloque grande) | 8-12 | ≥47 owners; `Require owner` en enforce |
| 4 | G6.1 + G6.3 + G6.5 higiene | 6-8 | 0 roles sin archetype; 0 drift |
| 5-6 | **G3** primera campaña de certificación | 16-20 | Campaña cerrada con revocaciones aplicadas |
| 7 | **G4** SoD en modo report → medir | 6-8 | Reporte de violaciones existentes |
| 8 | **G5** aprobación de privilegiado + G4 enforce | 8-10 | Solicitud de prueba aprobada y auditada |
| 9+ | **Fase 15** — onboarding de InOut con la plantilla | — | Primera área que entra con patrón |

**Ruta crítica:** G0 → G1 → G3. G2 y G6 pueden solaparse. G4 y G5 dependen de G1.

**Sin dependencias de terceros en toda la Fase 14** — es trabajo íntegramente interno, a
diferencia de las Fases 12 y 13 que llevan bloqueadas desde junio. Ese es un argumento
para hacerlo ahora: es lo único de alto valor que no depende de nadie más.

---

## 5. Riesgos

| Riesgo | Mitigación |
|---|---|
| SoD en `enforce` con violaciones preexistentes rompe recomputes masivos | Secuencia obligatoria report → medir → remediar → enforce (G4) |
| P1Y de auditoría desborda el disco (19 GB BD + 25 GB libres) | G2.2 proyecta el volumen **antes** de activar la política |
| Los owners nombrados en G1 no responden en la campaña G3 | Campaña piloto pequeña (~60 asignaciones) y escalamiento por defecto documentado |
| La certificación se vuelve un trámite de "aprobar todo" | Medir tasa de revocación; una campaña con 0 revocaciones es señal de alarma, no de éxito |
| Aparece un área urgente antes de cerrar Fase 14 | La regla de la §3.3 es explícita: entra con la plantilla de Fase 15 o no entra |

---

## 6. Decisiones que requieren a Alberto

1. **Retención de auditoría:** ¿P1Y (propuesto), P6M o P2Y? Impacta disco directamente.
2. **`subscriptionIdentifier`:** ¿cotizar subscription Evolveum o convivir con el nag y
   filtrar alertas por severidad?
3. **Alcance de la campaña piloto:** ¿los ~60 privilegiados propuestos, o incluir también
   los 14 roles de aplicación de Koha?
4. **Owners de negocio:** hay que nombrarlos con nombre y apellido — es la única parte de
   la Fase 14 que no se resuelve técnicamente.
5. **Orden del pipeline de áreas** (§3.1): ¿InOut primero por ser la misma área CRAI, o
   presionar el desbloqueo de Entra ID que tiene más valor institucional?
