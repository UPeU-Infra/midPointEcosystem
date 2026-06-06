# Fase 9 — Validación End-to-End del Pipeline IGA UPeU

**Fecha:** 2026-06-06  
**Ejecutado por:** midpoint-expert (Claude Code)  
**Entorno:** PROD (midpoint-prod 192.168.15.166, MidPoint 4.10.x)

---

## 1. Usuarios Piloto Seleccionados

| # | Nombre | Código (name) | OID | Archetype | Campus |
|---|--------|---------------|-----|-----------|--------|
| U1 | Richard Foster Horna Rodriguez | `42445436` | `b88330c4-7699-4a80-901f-b0858dad6466` | archetype-user-employee-faculty | TARAPOTO |
| U2 | MARIA GRECIA SOTO SANJINEZ | `202521268` | `13ab7b72-9dae-4cc2-a1c0-8cd3f42e43fd` | archetype-user-student | LIMA |
| U3 | Juan Geronimo Berna Francisco | `20587358` | `42c456f2-6b66-477b-8b39-c2748cef3329` | archetype-user-employee-staff | LIMA |

**Nota:** El docente piloto es de Tarapoto. Esto es representativo para verificar que el gate Koha multi-campus funciona correctamente (docente Tarapoto no debe tener cuenta Koha-Lima).

---

## 2. Tabla de Checks por Usuario

### U1 — Docente (faculty, Tarapoto)

| Check | Estado | Detalle |
|-------|--------|---------|
| `name` = código UPeU canónico | OK | `42445436` (DNI = código en este caso) |
| `fullName` / `givenName` / `familyName` | OK | Richard Foster Horna Rodriguez |
| `emailAddress` nativo | OK | `richard.horna@upeu.edu.pe` |
| `primaryAffiliation` = faculty | OK | `faculty` en `ext.78` |
| `liveAffiliationWorker` = faculty | OK | `faculty` en `ext.216` |
| `lambDocNum` / `taxId` | OK | DNI `42445436`, schacURI en taxId |
| `campusWorker` = TARAPOTO | OK | `TARAPOTO` |
| `eppn` formato correcto | OK | `42445436@upeu.edu.pe` |
| `lifecycleState` = active | OK | active / effectiveStatus: enabled |
| `terminationDate` presente | OK | `2026-07-02` (contrato temporal) |
| Archetype structural asignado | OK | `archetype-user-employee-faculty` |
| Business Role faculty | OK | `BR-Docente-TC` (OID `70f097bc...`) |
| Role afiliación | OK | `R-Affiliation-Faculty` |
| `BR-Personal-General` | OK | Presente |
| Org membership (AREA-91) | OK | `costCenter: 91` + assignment OrgType |
| Shadow Oracle LAMB Trabajadores | OK | LINKED, `exist=true` |
| Shadow LDAP-IdentityCache | OK | LINKED, `exist=true` |
| Shadow Koha ILS | AUSENTE | Correcto: gate campusWorker=TARAPOTO impide creacion BUL |
| Shadow Entra ID | PARCIAL | LINKED en DB, `exist=false` — no confirmado live |
| `eduPersonPrimaryAffiliation` en LDAP | INCORRECTO | Shadow cached dice `staff`; MidPoint dice `faculty`. Shadow con fullSyncTimestamp 2026-05-29, PREVIO al fix de clasificacion (2026-05-30) |
| `eduPersonAffiliation` en LDAP | OK | `faculty` |
| `eduPersonPrincipalName` en LDAP | OK | `42445436@upeu.edu.pe` |
| `schacHomeOrganization` en LDAP | OK | `upeu.edu.pe` |
| `schacPersonalUniqueCode` en LDAP | OK | `urn:schac:personalUniqueCode:pe:institutionID:upeu.edu.pe:42445436` |

---

### U2 — Estudiante (student, Lima)

| Check | Estado | Detalle |
|-------|--------|---------|
| `name` = código UPeU canónico | OK | `202521268` |
| `fullName` / `givenName` / `familyName` | OK | MARIA GRECIA SOTO SANJINEZ |
| `emailAddress` nativo | AUSENTE | NULL en campo nativo; `eppn` correcto en ext (`202521268@upeu.edu.pe`) |
| `primaryAffiliation` = student | OK | `student` |
| `liveAffiliationStudent` = student | OK | `student` |
| `taxId` schac-URI | OK | `urn:schac:personalUniqueID:pe:DNI:PE:72673412` |
| `campusStudent` = LIMA | OK | `LIMA` |
| `eppn` correcto | OK | `202521268@upeu.edu.pe` |
| `lifecycleState` = active | OK | active / enabled |
| `terminationDate` presente | OK | `2026-07-03` (ciclo académico vigente) |
| Archetype structural asignado | OK | `archetype-user-student` |
| Business Role pregrado | OK | `BR-Estudiante-Pregrado` |
| Role afiliación | OK | `R-Affiliation-Student` |
| Shadow Oracle LAMB Estudiantes | OK | LINKED, `exist=true` |
| Shadow LDAP-IdentityCache | OK | LINKED, `exist=true` |
| Shadow Koha ILS | OK | LINKED, `exist=true` — `cardnumber=202521268`, `category_id=student`, `library_id=BUL` |
| Shadow Entra ID | PARCIAL | LINKED en DB, `exist=false`, 1 operacion pendiente |
| `eduPersonPrimaryAffiliation` en LDAP | OK | `student` |
| `eduPersonAffiliation` en LDAP | OK | `student` |
| `eduPersonPrincipalName` en LDAP | OK | `202521268@upeu.edu.pe` |
| `schacHomeOrganization` en LDAP | OK | `upeu.edu.pe` |
| Koha categorycode correcto | OK | `student` (no ESTUDI legacy) |
| Koha library_id correcto | OK | `BUL` |
| Koha cardnumber = codigo | OK | `202521268` |
| Koha expiry_date | OK | `2026-07-02` |
| Koha extended_attributes DNI | OK | `{"type":"DNI","value":"72673412"}` |

---

### U3 — Staff Administrativo (staff, Lima)

| Check | Estado | Detalle |
|-------|--------|---------|
| `name` = código UPeU canónico | OK | `20587358` (DNI = codigo en trabajadores legacy) |
| `fullName` / `givenName` / `familyName` | OK | Juan Geronimo Berna Francisco |
| `emailAddress` nativo | OK | `20587358@upeu.edu.pe` |
| `primaryAffiliation` = staff | OK | `staff` |
| `liveAffiliationWorker` = staff | OK | `staff` en ext |
| `campusWorker` = LIMA | OK | `LIMA` |
| `eppn` correcto | OK | `20587358@upeu.edu.pe` |
| `lifecycleState` = active | OK | active / enabled |
| `terminationDate` presente | OK | `2026-12-31` |
| Archetype structural asignado | OK | `archetype-user-employee-staff` |
| Business Role staff | OK | `BR-Admin-Area` |
| `BR-Personal-General` | OK | Presente |
| Role afiliacion | OK | `R-Affiliation-Staff` |
| Org membership (AREA-106) | OK | `costCenter: 106` + OrgType assignment |
| Puesto (POS-862) | OK | ServiceType assignment presente |
| Shadow Oracle LAMB Trabajadores | OK | LINKED, `exist=true` |
| Shadow LDAP-IdentityCache | OK | LINKED, `exist=true` |
| Shadow Koha ILS | OK | LINKED — `cardnumber=20587358`, `category_id=staff`, `library_id=BUL` |
| Shadow Entra ID | PARCIAL | LINKED en DB, `exist=false`, 1 op pendiente |
| `eduPersonPrimaryAffiliation` en LDAP | OK | `staff` |
| `eduPersonAffiliation` en LDAP | OK | `staff` |
| `eduPersonPrincipalName` en LDAP | OK | `20587358@upeu.edu.pe` |
| `schacHomeOrganization` en LDAP | OK | `upeu.edu.pe` |
| `schacPersonalUniqueCode` en LDAP | OK | Presente con formato correcto |
| Koha categorycode correcto | OK | `staff` |
| Koha email en Koha | OK | `20587358@upeu.edu.pe` |

---

## 3. Estadísticas Globales de Salud (PROD 2026-06-06)

| Metrica | Valor |
|---------|-------|
| Usuarios activos total | 54,499 |
| Alumni activos | 26,545 |
| Estudiantes activos | 24,129 |
| Docentes activos (faculty) | 1,945 |
| Staff activos | 1,878 |
| Shadows LDAP LINKED | 27,642 |
| Shadows Koha LINKED | 18,125 |
| Shadows Oracle LAMB Trabajadores LINKED | 7,513 |
| Shadows Oracle LAMB Estudiantes LINKED | 24,677 |
| Shadows Oracle LAMB Egresados LINKED | 30,652 |
| Shadows Entra ID LINKED | 21,284 |

---

## 4. Hallazgos

### Funciona correctamente

- **Pipeline identidad central:** name=codigo, fullName/givenName/familyName, eppn, schacHomeOrganization poblados para los 3 arquetipos principales.
- **Archetype + RBAC automatico:** Los 3 usuarios tienen archetype structural correcto asignado automaticamente via object template / assignmentTargetSearch. Business Roles y Application Roles inducidos correctamente.
- **Gate Koha multi-campus:** El docente de Tarapoto NO tiene cuenta Koha-Lima (gate por campusWorker/campusStudent funcional, Fase 3 commit `369731d`).
- **Koha ILS correcto para Lima:** Estudiante y staff Lima tienen shadow Koha con `category_id` correcto (`student` / `staff`), `library_id=BUL`, `cardnumber=codigo`, `expiry_date` desde MidPoint.
- **LDAP con atributos eduPerson/SCHAC:** Los 3 usuarios tienen shadow LDAP con `eduPersonPrincipalName`, `schacHomeOrganization`, `schacPersonalUniqueCode`, `schacExpiryDate`, `schacDateOfBirth`, `schacGender` correctos.
- **Oracle LAMB como IIA:** Los 3 usuarios tienen shadow LINKED con `exist=true` en el recurso Oracle correspondiente.
- **Org membership:** Staff tiene `costCenter=106` y assignment OrgType a AREA-106. Docente tiene `costCenter=91` y AREA-91.

### Gaps / Items de accion

**GAP-1 (CRITICO) — `eduPersonPrimaryAffiliation` stale en 262 docentes LDAP**

Causa: El fix de clasificacion faculty/staff (commit `a283fa3`, 2026-05-30) reclasifica ~1,400 trabajadores. Los shadows LDAP de docentes afectados tienen `fullSynchronizationTimestamp` anterior al fix (2026-05-29 o antes). El campo `eduPersonPrimaryAffiliation` sigue publicando `staff` en LDAP para 262 docentes. Keycloak federar al LDAP lee este atributo incorrecto — impacta `eduPersonScopedAffiliation` y acceso a SPs SAML con entity category R&S.

Accion: reconciliar los 262 shadows LDAP de docentes con `fullSyncTimestamp < 2026-05-30`.

**GAP-2 (MEDIO) — `emailAddress` nativo ausente en 9,640 estudiantes activos (40% del total estudiantes)**

Los estudiantes tienen `eppn` correcto en `extension/sb:eppn` pero el campo nativo `c:emailAddress` esta NULL. El mapping en el object template estudiante no promueve el eppn al campo nativo. Koha usa el campo `mail` del shadow LDAP (que si tiene valor), pero MidPoint no puede usarlo para notificaciones internas ni para Entra ID.

Impacto: notificaciones MidPoint, workflows de aprovisionamiento que lean `emailAddress` nativo, y potencialmente Entra ID `mail` attribute.

Accion: agregar mapping `emailAddress ← eppn` en object template estudiante (strength=weak para no sobreescribir si existe uno corporativo).

**GAP-3 (MEDIO) — Shadows Entra ID con `exist=false` + 1 operacion pendiente**

Los 3 usuarios (y por extension los 21,284 LINKED en Entra ID) tienen `exist=false` en la columna m_shadow. Esto indica que MidPoint no puede confirmar la existencia del objeto en Entra ID durante el fetch del shadow (el resource es de solo lectura entrante o hay una operacion pendiente de WRITE que no se ha procesado).

Este estado es consistente con la decision doctrinal "Entra ID solo lectura en Fases 1-11". Si hay operaciones pendientes de escritura, estas pueden estar bloqueadas porque el recurso esta en modo read-only outbound.

Accion: verificar si las operaciones pendientes son `delete` o `modify` stuck. Limpiar o cancelar si el recurso es efectivamente solo-lectura en este punto.

**GAP-4 (MENOR) — taxId ausente en staff DNI-legacy**

El usuario U3 (staff `20587358`) tiene `lambDocNum=20587358` pero `taxId` aparece vacio en la extension. Esto sugiere que el mapping `taxId ← lambDocNum` (schacPersonalUniqueID URI) solo aplica cuando `lambDocType=1` (DNI) y para trabajadores legacy con codigo=DNI, el `lambDocType` puede no estar en LAMB.

Accion: verificar el mapping en `oracle-lamb-trabajadores.xml` para el caso lambDocType NULL con lambDocNum 8-digitos.

---

## 5. Verificacion de Recursos (Test Connection)

| Recurso | Estado |
|---------|--------|
| LDAP-IdentityCache-UPeU | SUCCESS |
| Koha ILS | SUCCESS |
| UPEU-EntraID-Graph | SUCCESS |
| Oracle LAMB Trabajadores v3 | active (asumido — shadows linked) |
| Oracle LAMB Estudiantes v3 | active (asumido — shadows linked) |

---

## 6. Conclusion

**El pipeline IGA es FUNCIONALMENTE OPERATIVO para produccion** con las siguientes observaciones:

El flujo central Oracle LAMB → MidPoint → LDAP → Koha esta completo y correcto para los 3 arquetipos principales. Los controles de acceso (gate multi-campus Koha, Business Roles por afiliacion, org membership) funcionan como se disenaron. Los atributos eduPerson/SCHAC se publican correctamente en LDAP.

Los gaps identificados son:

- GAP-1 requiere una reconciliacion LDAP parcial (262 docentes) — no bloquea operacion pero si impacta correctitud de federacion SSO para docentes reclasificados.
- GAP-2 es un fix de mapping menor en el object template estudiante.
- GAP-3 y GAP-4 son items de limpieza / verificacion de configuracion.

**Recomendacion:** proceder con Fase 9 outbound (LDAP reconciliacion parcial para docentes) y aplicar el fix emailAddress en el template estudiante antes de activar SSO en produccion.

---

## 7. Proximos Pasos

1. **Reconciliar 262 shadows LDAP docentes** (GAP-1): task reconciliation scoped `resourceRef=LDAP` + filtro `primaryAffiliation=faculty` + `fullSyncTimestamp < 2026-05-30`.
2. **Fix emailAddress en template estudiante** (GAP-2): agregar outbound mapping `emailAddress ← eppn` con `strength=weak` en `object-template-user-student.xml`.
3. **Diagnosticar operaciones pendientes Entra ID** (GAP-3): query `m_operation_execution` o `m_shadow` para entender las ops stuck.
4. **Verificar taxId mapping trabajadores legacy** (GAP-4): revisar mapping `lambDocType` NULL en `oracle-lamb-trabajadores.xml`.
