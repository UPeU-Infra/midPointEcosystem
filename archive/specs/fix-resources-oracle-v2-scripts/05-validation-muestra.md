# Validación end-to-end de la muestra IGA — auditoría sin escritura

**Spec:** doc/specs/fix-resources-oracle-v2-scripts/
**Fecha:** 2026-05-13 / 14
**Alcance:** auditoría de los 21 usuarios de la muestra original (creados antes de las 21:00 UTC del 2026-05-13). NO se ejecutó ningún cambio en PROD.
**Estándares aplicados:** eduPerson 202208, SCHAC URN Registry, SCIM 2.0 (RFC 7643), ISO 24760, NIST 800-63-3, INCITS 359 (RBAC), Evolveum best practices.

---

## 0. Limpieza previa — task `27333f76` (import accidental de 30K egresados)

| Item | Estado |
|---|---|
| Task `27333f76-643e-487b-aa02-26164fa46b8f` | SUSPENDED — `progress=28390/30629` |
| Acción aplicada en esta sesión | Ninguna (instrucción del usuario: "déjala suspended o márquela completada según best practice") |
| Recomendación midpoint-best-practices | Marcar la task como `closed` (no reanudar) y purgar via `tasks/cleanup`. La interrupción ya cerró transacciones por bucket; reanudar generaría re-procesamiento sin valor. |
| Daño colateral | **30,622 focuses extra de egresados creados (29,624 sin archetype, sin BR, sin OU; en `m_user` con `personalnumber` poblado).** Total focuses PROD: 30,645 (esperado: 22). |
| Acción correctiva pendiente | Bulk delete por filtro `createTimestamp >= 2026-05-13T21:00:00Z AND name != administrator`. NO ejecutado en esta auditoría. |

> **Nota IGA:** estos 30K focuses NO son parte de la "muestra" a validar. Quedan fuera de scope del reporte. Solo los 21 focuses muestra (+ admin) se auditaron a continuación.

---

## 1. SCHEMAS — `urn:upeu:midpoint:person:v3` + `urn:upeu:midpoint:lamb:v1`

**Estado: ⚠️ Gap parcial**

Schema v3 OID `035fa9b7-ea88-4428-bdb7-62f4f2ef7207` tiene los 28 atributos canónicos catalogados en `m_ext_item` (IDs 16–28, 46–48, 57). Schema lamb v1 OID `11111111-…-001` aporta `lambPersonaId` (id=49). Ambos están registrados como ItemDefinitions activas.

Cobertura observada en los 21 focuses:

| Atributo canónico (eduPerson/SCHAC) | Mapeo UPeU v3 | Poblados | Vacíos | Notas |
|---|---|---|---|---|
| `schacPersonalUniqueID` (DNI) | `extension/upeu3:taxId` | 21/21 ✅ | 0 | Formato URN SCHAC correcto. 2 casos (`44303558` Veronica, `24893998` Freddy, `40153362` Erika, `40458823` Ethel, `48573883` Melissa, `73619763` Andres, `06812979`, `07517981`) llevan CUSPP/AFP-encoded en vez de DNI puro — Known Issue heredado del bug pre-fix `ROW_NUMBER`. |
| `eduPersonAffiliation` | (no derivado) | 0/21 ❌ | 21 | Bug: ningún template asigna `subtypes`/`organization` a partir del archetype. Lo dicta `iga-canonical-standards §2.1` (eduPerson 202208) — debe ser `student/faculty/staff/alum` literal y multivalor. |
| `eduPersonScopedAffiliation` | (no derivado) | 0/21 ❌ | 21 | Mismo gap. Debe ser `<affiliation>@upeu.edu.pe`. |
| `birthDate` | `extension/upeu3:birthDate` | 19/21 ⚠️ | 2 (`200010114`, `202313535`) | Vista Lamb no devuelve fecha en esos casos. |
| `gender` (ISO 5218) | `extension/upeu3:gender` | 21/21 ✅ | 0 | Valores `0/1/2`. |
| `hireDate` | `extension/upeu3:hireDate` | 9/21 ✅ | 12 (correctamente vacíos en estudiantes/egresados) | OK. |
| `terminationDate` | `extension/upeu3:terminationDate` | 2/21 ✅ | 19 | OK (solo Melissa y Andres tienen). |
| `nationality` (ISO 3166-1 alpha-3) | `extension/upeu3:nationality` | 11/21 ⚠️ | 10 staff/faculty | Solo poblado en estudiantes+egresados. Trabajadores NO lo derivan (faltan inbounds en resource trabajadores-v2). 1 valor inválido: `202611420` = `ZZZ` (debería ser código de Mozambique, MOZ). |
| `studyLevel` | `extension/upeu3:studyLevel` | 3/21 ✅ | 18 | Solo egresados. Estudiantes activos NO lo tienen — gap (debería derivarse de `NIVEL_ENSENANZA` en estudiantes también). |
| `disability` | `extension/upeu3:disability` | 9/21 ⚠️ | 12 | Solo en estudiantes activos. Egresados NO. |
| `studyModality` | `extension/upeu3:studyModality` | 3/21 ✅ | 18 | Solo egresados. |
| `studentCycle` | `extension/upeu3:studentCycle` | 8/21 ✅ | 13 | OK (solo students). |
| `academicProgramCode` | `extension/upeu3:academicProgramCode` | 8/21 ✅ | 13 | OK (multivalor — Yessenia tiene 2). |
| `lambPersonaId` (IIA primary key) | `extension/lamb:lambPersonaId` | 21/21 ✅ | 0 | OK. |
| `externalSystemId` (cross-system fusion) | `extension/upeu3:externalSystemId` | 3/21 ✅ | 18 | Solo poblado en egresados puros. **Gap dual-identity**: los 3 fusionados (10867326+9610165, 44303558+200720272, 24893998+9810042) NO tienen `externalSystemId` aunque sí `personalNumber` con el código alterno. Inconsistencia con la regla canónica documentada en `project_oracle_iga.md`. |
| `eduPersonOrgUnitDN` / `eduPersonOrgDN` | `organizationalUnit` + `parentOrgRef` | **0/21 ❌** | 21 | Ver pilar 3. |
| `eduPersonPrimaryAffiliation` | `subtypes[0]` o derivable de archetype | **0/21 ❌** | 21 | Ningún focus tiene `subtypes` ni atributo derivado. Bloqueador para Keycloak/Indico claims. |
| `eduPersonOrcid` | `extension/upeu3:orcid` | 0/21 — | — | Atributo no presente en `m_ext_item` aún. Pendiente. |
| `mail` | `emailAddress` | 0/21 ❌ | 21 | **Ningún focus tiene email**. CORREO_UPEU venía null en muchos casos pero no se intentó construir `<name>@upeu.edu.pe` desde `name`. |

**Gaps prioritarios pilar 1:**
- ❌ Falta inbound `nationality` en trabajadores-v2.
- ❌ Falta inbound `studyLevel` en estudiantes-v2.
- ❌ Falta derivación de `eduPersonAffiliation` y `subtypes` en object templates por archetype.
- ❌ Falta construcción de `emailAddress` (regla canónica eduPerson §2.7).
- ⚠️ Inconsistencia `personalNumber` vs `externalSystemId` para focuses fusionados.

---

## 2. PERFILES DE USUARIOS (focuses)

**Estado: ⚠️ Gap parcial — datos correctos, pero pobres en proyección canónica**

Inventario de los 21 focuses muestra:

| OID | name | personalNumber | archetype | BR | taxId OK | lambPersonaId |
|---|---|---|---|---|---|---|
| 96fd2a57… | 00066766 | 00066766 | staff | BR-Admin-Area | ✅ | 21961 |
| 18c17daa… | 06812979 | 06812979 | staff | BR-Admin-Area | ⚠️ CUSPP | 7556 |
| 1ed429b0… | 07517981 | 07517981 | faculty | BR-Docente-TC | ⚠️ CUSPP | 7581 |
| c4ff2732… | 10867326 | 10867326 | staff | BR-Admin-Area | ✅ | 15922 |
| 010daa6f… | 24893998 | 24893998 | staff | BR-Admin-Area | ⚠️ CUSPP | 9840 |
| 4d51cf01… | 40153362 | 40153362 | faculty | BR-Docente-TC | ⚠️ CUSPP | 7492 |
| 8c6f9ddb… | 40458823 | 40458823 | faculty | BR-Docente-TC | ⚠️ CUSPP | 7718 |
| 1f2d0f99… | 44303558 | 44303558 | staff | BR-Admin-Area | ⚠️ CUSPP | 9732 |
| ed8a8e61… | 48573883 | 48573883 | staff | BR-Admin-Area | ⚠️ CUSPP | 29205 |
| 6289bdfd… | 73619763 | 73619763 | staff | BR-Admin-Area | ⚠️ CUSPP | 10008 |
| a3702ba8… | 200410398 | 200410398 | student | BR-Estudiante-Posgrado | ✅ | 13345 |
| b0cdf5e0… | M20180020 | M20180020 | student | BR-Estudiante-Pregrado | ✅ | 197462 |
| cb84949d… | 200010114 | 200010114 | student | BR-Estudiante-Pregrado | ✅ | 13459 |
| b9eb185e… | 201910946 | 201910946 | student | BR-Estudiante-Doctorado | ✅ | 78722 |
| 114398be… | 202611423 | 202611423 | student | BR-Estudiante-Pregrado | ✅ (CO PP) | 4010816 |
| f283b975… | 202614474 | 202614474 | student | BR-Estudiante-Pregrado | ✅ | 277511 |
| c9073f16… | 202611420 | 202611420 | student | BR-Estudiante-Pregrado | ⚠️ XX/ZZZ | 4017774 |
| c8c6d473… | 200820165 | 200820165 | student | BR-Estudiante-Pregrado | ✅ | 7527 |
| b7d5affb… | 200210050 | 200210050 | alumni | BR-Egresado | ✅ | 7932 |
| e58a8987… | 202313535 | 202313535 | alumni | BR-Egresado | ✅ | 357934 |
| 8900477d… | 200910432 | 200910432 | alumni | BR-Egresado | ✅ | 45363 |

**Hallazgos:**

1. ✅ **21 focuses, 0 duplicados**. Las 3 fusiones dual-identity reportadas en `project_oracle_iga.md` no aparecen aquí: los 3 trabajadores que también tenían código de estudiante (Alberto 9610165, Veronica 200720272, Freddy 9810042) están como un solo focus con archetype `staff`. ✅ Cumple ISO 24760 §6.4 (1 persona física = 1 subject).

2. ❌ **Inconsistencia dual-identity sin `externalSystemId`**. La doctrina dice: "Código alternativo SIS para fusionados → `externalSystemId`". Pero el extension JSONB solo lo tiene en 3 egresados puros (`200210050`, `200910432`, `202313535`), NO en los 3 fusionados. Hay que decidir: ¿el `externalSystemId` cubre solo egresados, o también los códigos cruzados de fusión? Si lo segundo, falta inbound en trabajadores-v2.

3. ❌ **lifecycleState vacío en los 21**. Known Issue ya registrado. Ningún template setea `lifecycleState`. Bajo NIST 800-63-3 §4.1.2 esto rompe el ciclo `proposed/active/suspended/archived`.

4. ❌ **0 focuses con `emailAddress`**. Bloquea Keycloak/Indico/Koha email-based provisioning.

5. ❌ **0 focuses con `costCenter`, `localityorig`** — campos core de MidPoint que mapean a `eduPersonOrgUnitDN`/`schacHomeOrganization` no se están poblando.

---

## 3. ORGANIZACIÓN (OUs / OrgType)

**Estado: ❌ Crítico — desconexión completa entre focuses y org tree**

| Métrica | Valor |
|---|---|
| OrgType en repo | **91** (1 institution + 3 campus + 5 faculty + 12 governance + 31 academic-unit + 36 department + 3 partner-institution) |
| Archetypes de org | 8 (institution, campus, faculty, department, academic-unit, governance, partner-institution, project) |
| **Focuses con assignment a OrgType** | **0/21** ❌ |
| **Focuses con `parentOrgRef`** | **0/21** ❌ |
| Focuses con `costCenter`/`organizationalUnit` poblados | 0/21 ❌ |

**Causa raíz:** los object templates per-archetype (`UserTemplate-Employee-Staff`, `-Faculty`, `-Student`, `-Alumni`) NO tienen mapeos hacia:
- `parentOrgRef` (vía `assignmentTargetSearch` con `targetType=OrgType`),
- `organizationalUnit`,
- `costCenter`,
- `locality`.

Solo tienen `assignmentTargetSearch` para `RoleType` (Business Roles). El template base solo proyecta `birthDate/hireDate/terminationDate/taxId/givenName/familyName/employeeNumber`. Total mappings inspeccionados: 11 en base + 1 (assignmentTargetSearch) en faculty → ninguno toca org.

**Estándar violado:** `iga-canonical-standards §3` — eduPersonOrgUnitDN es atributo obligatorio de R&S para institución superior. SCHAC `schacHomeOrganizationalUnit` también requerido.

**Recomendación (a aprobar por usuario, NO ejecutado):**
1. Agregar inbound en trabajadores-v2: `ORG_DEPTO/ORG_AREA/ORG_ESCUELA` desde Lamb → `extension/lamb:lambDeptoCode` (ya existe en schema).
2. En cada UserTemplate-Employee-* y UserTemplate-Student, agregar `<mapping>` con `<assignmentTargetSearch>` filtrando por `archetype-org-department` o `archetype-org-academic-unit` por `identifier=$lambDeptoCode`.
3. Idem para `costCenter` (← `costCenter` del OrgType padre via mapping derivado).

---

## 4. ROLES (RBAC INCITS 359)

**Estado: ⚠️ Parcial — hay roles, pero sin proyección hacia resources**

| Categoría | Conteo | Notas |
|---|---|---|
| Business Roles (BR-*) activos | 11 | BR-Admin-Area, BR-Docente-TC/TP, BR-Estudiante-Pregrado/Posgrado/Doctorado, BR-Egresado, BR-Decano, BR-Bibliotecario, BR-Investigador, BR-Visitante-Investigacion |
| Application Roles (AR-*) activos | 20 | Cubre Koha, Keycloak, M365, OJS, DSpace, Indico, WiFi, Vendor academic |
| Roles archivados (deprecados) | 4 | BR-DOCENTE, BR-ESTUDIANTE, BR-PERSONALADM, también APP-ENTRAID-USER y APP-KOHA-PATRON sin lifecycle |
| Funcionales MOF | 8 | MOF-DECANO, MOF-DIRECTOR, MOF-COORDINADOR, etc. (sin lifecycle) |

**Asignación a focuses muestra:**
- ✅ 21/21 focuses tienen exactamente 1 BR asignado, derivado correctamente del archetype vía `assignmentTargetSearch` en el template.
- ✅ La derivación es policy-driven (no hardcoded por user) — cumple `midpoint-best-practices §4`.
- ❌ **0 focuses tienen Application Role asignado**. Los BR no tienen `inducement` hacia los AR-* que les corresponderían.
- ❌ Resultado neto: 0 provisioning a Entra ID, M365, Keycloak, Koha. Las 220 shadows de Entra ID son legacy pre-canónicas (sin link a focus muestra).

**Estándar violado:** INCITS 359 §6.3 (Role Hierarchy). Sin la cadena BR→inducement→AR→outbound, los BR son etiquetas sin efecto operativo.

**Recomendación:**
1. Auditar XML de cada BR-* y verificar que tenga `<inducement><targetRef oid="...AR..."/></inducement>` para cada AR pertinente. Por ejemplo:
   - BR-Estudiante-Pregrado → induce AR-Koha-Patron-Student + AR-WiFi-Estudiantes + AR-M365-Student-A1 + AR-Keycloak-RealmAccess-UPeU + AR-Vendor-Academic-Access
   - BR-Docente-TC → induce AR-Koha-Patron-Faculty + AR-WiFi-Docentes + AR-M365-Faculty-A3 + AR-Keycloak-RealmAccess-UPeU + AR-Vendor-Academic-Access + AR-OJS-Author
2. Verificar que cada AR-* tenga `<inducement><construction>` apuntando al resource correcto con outbound mapping.
3. Borrar/migrar los 4 archivados y los APP-* sin lifecycle.

---

## 5. ARQUETIPOS (ISO 24760 subject classification)

**Estado: ✅ OK con observaciones menores**

| Métrica | Valor |
|---|---|
| Archetypes UserType activos | 8 (staff, faculty, student, alumni, contractor, service-account, affiliate-researcher, affiliate-partner-institution) |
| Focuses muestra con archetype único | 21/21 ✅ |
| Distribución muestra | 9 staff + 3 faculty + 7 student + 3 alumni |
| Mapping archetype↔template | ✅ Cada UserTemplate corresponde a un archetype (verificado por Faculty template) |

**Observaciones:**

1. ✅ Cada focus tiene exactamente 1 `archetypeRef` direct assignment — cumple `midpoint-best-practices §3` (anti-pattern: archetype vía inducement).
2. ✅ Caso fusión multi-afiliación (10867326 = staff Y egresado SIS): se eligió `staff` como archetype canónico (IIA primaria HR según ISO 24760 §7.2). El estatus de egresado se preserva en `personalNumber`. Decisión correcta.
3. ⚠️ **Pero no se proyecta el ePSA múltiple**: la persona es a la vez `staff@upeu.edu.pe` Y `alum@upeu.edu.pe`. Ningún mecanismo está derivando el array. Bug de pilar 1 + pilar 4.
4. ⚠️ Archetype `archetype-user-employee` (parent abstracto) no existe — los staff/faculty heredan directo de algún `archetype-user-employee` agnóstico? Verificar `inducement` en `iga-canonical-standards §1.4` (subtipo jerárquico Person→Employee→Staff).

---

## 6. TAREAS (sync + reconciliation)

**Estado: ⚠️ Parcial — tareas existen pero todas suspended o ad-hoc**

Las 3 recurring oficiales:

| OID | Nombre | Estado | Binding | Recurrence | Schedule |
|---|---|---|---|---|---|
| 6a91f7e1-…-31 | task-recon-trabajadores-v2 | SUSPENDED | LOOSE | RECURRING | (no inspeccionado) |
| 6a91f7e1-…-32 | task-recon-estudiantes-v2 | SUSPENDED | LOOSE | RECURRING | (no inspeccionado) |
| 6a91f7e1-…-33 | task-recon-egresados-v2 | SUSPENDED | LOOSE | RECURRING | (no inspeccionado) |

Tareas ad-hoc y de testing acumuladas: **42 tasks** relacionadas con LAMB/import/recon, la mayoría con estado `CLOSED PARTIAL_ERROR` o `SUSPENDED FATAL_ERROR`. Falta limpieza.

**Hallazgos:**

1. ✅ Handler correcto `…/synchronization/task/reconciliation/handler-3` (Activity-based) en las recientes (`Recon-trabajadores-phaseB-…` etc.).
2. ❌ **NO existe Live Sync task** para ninguno de los 3 resources. Bajo `midpoint-best-practices §6.2`: para fuente con timestamp (Oracle LAMB tiene `FEC_INICIO`/`FEC_TERMINO`/`MODIFY_TIMESTAMP`?), debería haber `LiveSyncEventHandler` además de reconciliation periódica. Si la fuente no expone `__LAST_MODIFIED__`, OK quedarse con reconciliation pura — pero se necesita confirmar.
3. ❌ Las 3 recurring están SUSPENDED. Requieren `WHERE ROWNUM=1` removido y un schedule prudente (cron `0 0 2 * * ?` nocturno) antes de reactivar.
4. ⚠️ Acumulación de 42 tasks de prueba — `midpoint-best-practices §6.5` recomienda Cleanup Task para tasks `CLOSED` > 7 días. No está activa.
5. ❌ `binding=LOOSE` es OK para reconciliation, pero falta `worker-threads` para 30K egresados. Para reconciliation masiva debería ser `multi-node` activity con `workerThreads >= 4` por node (`midpoint-best-practices §6.4`).

---

## Tabla resumen — cobertura de campos canónicos × usuarios muestra

| name | birthDate | gender | hireDate | termDate | taxId | nationality | studyLevel | disability | studyMod | cycle | progCode | externalId | lambId | OU | email |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 00066766 (staff) | ✅ | ✅ | ✅ | — | ✅ | ❌ | — | — | — | — | — | — | ✅ | ❌ | ❌ |
| 06812979 (staff) | ✅ | ✅ | ✅ | — | ⚠️ | ❌ | — | — | — | — | — | — | ✅ | ❌ | ❌ |
| 07517981 (faculty) | ✅ | ✅ | ✅ | — | ⚠️ | ❌ | — | — | — | — | — | — | ✅ | ❌ | ❌ |
| 10867326 (staff/alum) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | — | — | — | — | — | ❌* | ✅ | ❌ | ❌ |
| 24893998 (staff/alum) | ✅ | ✅ | ✅ | — | ⚠️ | ❌ | — | — | — | — | — | ❌* | ✅ | ❌ | ❌ |
| 40153362 (faculty) | ✅ | ✅ | ✅ | — | ⚠️ | ❌ | — | — | — | — | — | — | ✅ | ❌ | ❌ |
| 40458823 (faculty) | ✅ | ✅ | ✅ | — | ⚠️ | ❌ | — | — | — | — | — | — | ✅ | ❌ | ❌ |
| 44303558 (staff/alum) | ✅ | ✅ | ✅ | — | ⚠️ | ❌ | — | — | — | — | — | ❌* | ✅ | ❌ | ❌ |
| 48573883 (staff) | ✅ | ✅ | ✅ | ✅ | ⚠️ | ❌ | — | — | — | — | — | — | ✅ | ❌ | ❌ |
| 73619763 (staff) | ✅ | ✅ | ✅ | ✅ | ⚠️ | ❌ | — | — | — | — | — | — | ✅ | ❌ | ❌ |
| 200010114 (student) | ❌ | ✅ | — | — | ✅ | ✅ | ❌ | ✅ | — | ✅ | ✅ | — | ✅ | ❌ | ❌ |
| 200410398 (student) | ✅ | ✅ | — | — | ✅ | ✅ | ❌ | ✅ | — | ✅ | ✅ | — | ✅ | ❌ | ❌ |
| 200820165 (student) | ✅ | ✅ | — | — | ✅ | ✅ | ❌ | ✅ | — | ✅ | ✅ | — | ✅ | ❌ | ❌ |
| 201910946 (student) | ✅ | ✅ | — | — | ✅ | ✅ | ❌ | ✅ | — | ✅ | ✅ | — | ✅ | ❌ | ❌ |
| 202611420 (student) | ✅ | ✅ | — | — | ⚠️ | ⚠️ZZZ | ❌ | ✅ | — | ✅ | ✅ | — | ✅ | ❌ | ❌ |
| 202611423 (student) | ✅ | ✅ | — | — | ✅ | ✅ | ❌ | ✅ | — | ✅ | ✅ | — | ✅ | ❌ | ❌ |
| 202614474 (student) | ✅ | ✅ | — | — | ✅ | ✅ | ❌ | ✅ | — | ✅ | ✅ | — | ✅ | ❌ | ❌ |
| M20180020 (student) | ✅ | ✅ | — | — | ✅ | ✅ | ❌ | ✅ | — | ✅ | ✅ | — | ✅ | ❌ | ❌ |
| 200210050 (alumni) | ✅ | ✅ | — | — | ✅ | ✅ | ✅ | ❌ | ✅ | — | — | ✅ | ✅ | ❌ | ❌ |
| 200910432 (alumni) | ✅ | ✅ | — | — | ✅ | ✅ | ✅ | ❌ | ✅ | — | — | ✅ | ✅ | ❌ | ❌ |
| 202313535 (alumni) | ❌ | ✅ | — | — | ✅ | ✅ | ✅ | ❌ | ✅ | — | — | ✅ | ✅ | ❌ | ❌ |

\* = inconsistencia dual-identity (debería tener externalSystemId con código SIS).
✅ = OK | ⚠️ = poblado pero con dato dudoso | ❌ = vacío incorrecto | — = vacío correcto (no aplica al archetype).

---

## Lista priorizada de fixes pendientes

### Alta (bloquean SSO y provisioning canónico)
1. **Conectar BR → AR vía inducement** (pilar 4). Sin esto, 0 provisioning. Auditar XML de cada BR.
2. **Mapear OU desde Lamb a focus** (pilar 3): inbound `ID_DEPTO`/`ORG_AREA` → `extension/lamb:lambDeptoCode`, y template con `assignmentTargetSearch` a OrgType. Sin esto no hay eduPersonOrgUnitDN.
3. **Construir `emailAddress`** en UserTemplate-Person-Base: `name + '@upeu.edu.pe'` (con strength `weak`). Bloquea Keycloak claims.
4. **Cerrar task `27333f76`** y borrar 30,622 focuses de egresados accidentales. Limpiar 30,629 shadows huérfanos del resource egresados.
5. **Limpiar lifecycleState** en los 21 focuses muestra: setear `active` explícito (o agregar mapping en template base).

### Media (mejoran calidad pero no bloquean)
6. **Inbound `nationality`** en trabajadores-v2 (faltan los 10 staff/faculty).
7. **Inbound `studyLevel`** en estudiantes-v2 (falta para los 8 students activos).
8. **Derivar `eduPersonAffiliation` y `subtypes`** desde archetype en cada UserTemplate (pilar 1 + 5).
9. **Resolver inconsistencia `externalSystemId` en focuses fusionados** (Alberto, Veronica, Freddy). Documentar regla y aplicar a los 3.
10. **Reconfigurar las 3 recurring tasks**: quitar `WHERE ROWNUM=1` de los 3 resources, setear `workerThreads=4`, `cron` nocturno. Solo activar después de fixes 1-5.

### Baja (housekeeping)
11. Activar `Cleanup Task` para tasks `CLOSED` > 7 días.
12. Borrar/archivar las 38 tasks ad-hoc de testing (mantener solo `…-phaseB-…` + `Recon-trab-v2-post-cleanup-…` + las 3 recurring oficiales).
13. Migrar los 4 roles archivados (BR-DOCENTE, BR-ESTUDIANTE, BR-PERSONALADM) y los APP-* sin lifecycle.
14. Validar el valor `ZZZ` para nacionalidad en 202611420 (probable Mozambique → MOZ).
15. Decidir si Live Sync corresponde para Oracle LAMB (verificar si hay timestamp de modificación en vistas DAVID).

---

## Resumen ejecutivo (≤250 palabras)

**Pilar 1 — Schemas:** ⚠️ Schema v3 + lamb v1 completos (28 atributos en `m_ext_item`). Cobertura por focus aceptable en lo poblado (21/21 taxId, lambPersonaId, gender, birthDate). Pero faltan inbounds canónicos clave: `nationality` en trabajadores, `studyLevel` en estudiantes activos, `emailAddress` en todos, `eduPersonAffiliation/scopedAffiliation` en ningún focus.

**Pilar 2 — Focuses:** ⚠️ 21 focuses limpios, sin duplicados, fusión dual-identity correcta (1 persona = 1 focus). Pero `lifecycleState` vacío en los 21, `emailAddress` vacío en los 21, e inconsistencia: 3 focuses fusionados NO llevan `externalSystemId` aunque sí el código alterno en `personalNumber`.

**Pilar 3 — Organización:** ❌ Crítico. 91 OrgType bien tipificadas en repo, pero **0/21 focuses tienen assignment a OrgType ni `parentOrgRef`**. Object templates no proyectan `costCenter`/`organizationalUnit`/`locality`. Sin esto no hay `eduPersonOrgUnitDN`.

**Pilar 4 — Roles:** ⚠️ 11 BR + 20 AR activos, asignación BR via `assignmentTargetSearch` en templates funciona (21/21). Pero **0 AR asignados a focuses** → 0 inducement BR→AR → 0 provisioning real a Entra/Koha/M365.

**Pilar 5 — Arquetipos:** ✅ OK. 21/21 con archetype único correcto, fusión multi-afiliación canónica (staff gana sobre alumni).

**Pilar 6 — Tareas:** ⚠️ Las 3 recurring suspended. 42 tasks ad-hoc acumuladas. Cleanup Task ausente. Live Sync sin definir.

**Top 3 gaps:** (1) BR no inducen AR — 0 provisioning, (2) ningún focus tiene OU/parentOrgRef — eduPersonOrgUnitDN imposible, (3) 30,622 focuses basura de egresados pendientes de borrado + 30,629 shadows huérfanos.

**Próximo paso recomendado:** decidir orden de fix entre [A] inducement BR→AR (desbloquea SSO), [B] limpieza accidental (urgente higiene), [C] mapeo OU. Sugiero B → A → C en una sola spec.
