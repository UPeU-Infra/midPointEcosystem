# Auditoría — SchemaType `upeuPerson` actual

**Fecha:** 2026-05-11
**Auditor:** Alberto Sánchez (vía Claude Code)
**OID:** `b7d55017-599f-4f2f-9493-9f64bba62c5b`
**Entrega:** Fase 1.1 del [roadmap IGA 2026](../../docs/roadmap-iga-2026.md)

---

## Resumen ejecutivo

| Aspecto | DEV (192.168.15.230) | PROD (192.168.15.166) |
|---|---|---|
| Versión label en el schema | **v2.2** | **v2.3** |
| Versión repo MidPoint | 104 | 2 |
| ComplexTypes definidos | 7 | 8 (uno más: `ExternalSystemRefsType`) |
| Elementos top-level | 25 | 34 |
| Última modificación | 2026-02-09 | reciente |
| Bytes XML | 23,196 | 25,740 |

🚨 **Drift confirmado:** DEV está retrasado vs PROD. PROD es la verdad operativa. **Para diseñar v3.0 nos basamos en PROD.**

---

## ComplexTypes en PROD (v2.3)

| ComplexType | Propósito |
|---|---|
| `DemographicsType` | Datos demográficos extra (no en core) |
| `ContactInfoType` | Datos contacto secundarios |
| `EmploymentDataType` | Fechas laborales (hire/termination) |
| `AffiliationDataType` | Afiliación primaria/secundaria + campus |
| `AcademicStatusType` | Status académico ampliado |
| `FederatedIdentityType` | IDs en sistemas federados |
| `UniqueIdentifiersType` | Identificadores únicos institucionales |
| **`ExternalSystemRefsType`** (NUEVO en PROD) | Referencias a IDs en sistemas downstream |

---

## Análisis atributo por atributo

Cada fila evalúa el atributo actual contra el modelo canónico (eduPerson/SCHAC/SCIM core + best practices Evolveum) y decide para v3.0:

- ✅ **KEEP** — se mantiene en v3.0 (es UPeU-specific y no hay equivalente core)
- 🔄 **MIGRATE** — se mantiene pero se renombra/reformatea para alinear con estándar
- 📤 **MOVE-TO-CORE** — eliminar de extension; el dato vive en campo core MidPoint (`name`, `fullName`, etc.)
- 🧮 **COMPUTE** — eliminar de extension; el valor se deriva en object template (no se persiste)
- 🗑️ **REMOVE** — eliminar completamente (obsoleto / decisión arquitectónica)

### `DemographicsType`

| Atributo PROD | Tipo | Decisión v3.0 | Razón |
|---|---|---|---|
| `birthDate` | string | 🔄 MIGRATE → `xsd:date` + alinear con `schacDateOfBirth` (`urn:oid:1.3.6.1.4.1.25178.1.2.3`) | Tipo correcto. SCHAC define exactamente esto. |
| `gender` | string | 🔄 MIGRATE → ISO 5218 (1/2/0/9), considerar `eduPersonDisplayPronouns` para pronombre | SCHAC `schacGender` está DEPRECATED. Usar ISO 5218 numérico. |
| `country` | string | ✅ KEEP en extension. Alias semántico con `schacCountryOfResidence` (ISO 3166-1 alpha-3) | No hay equivalente en MidPoint core. |
| `province` | string | ✅ KEEP | UPeU-specific (regional Perú). |
| `streetAddress` | string | 📤 MOVE-TO-CORE → usar `UserType/locality` o SCIM-style `addresses` | MidPoint core ya tiene address. |

### `ContactInfoType`

| Atributo PROD | Tipo | Decisión v3.0 | Razón |
|---|---|---|---|
| `secondaryMail` | string | 📤 MOVE-TO-CORE → `UserType/emailAddress` (multi) o SCIM `emails[type=other]` | El core acepta multi-valor; no duplicar. |
| `phoneNumberAlt` | string | 📤 MOVE-TO-CORE → `UserType/telephoneNumber` (multi) | Core soporta multi. |
| `personalWeb` | string | ✅ KEEP en extension | No hay core equivalent. |

### `EmploymentDataType`

| Atributo PROD | Tipo | Decisión v3.0 | Razón |
|---|---|---|---|
| `hireDate` | date | ✅ KEEP (UPeU-specific HR) | Trigger Joiner policy. |
| `terminationDate` | date | ✅ KEEP (UPeU-specific HR) | Trigger Leaver policy + `schacExpiryDate` derivado. |

### `AffiliationDataType`

| Atributo PROD | Tipo | Decisión v3.0 | Razón |
|---|---|---|---|
| `primaryAffiliationCode` | string | 🧮 COMPUTE en object template como **`eduPersonPrimaryAffiliation`** + **`eduPersonAffiliation`** (multi) | Atributo derivable desde archetype + employmentType. No persistir. |
| `primaryAffiliationName` | string | 🗑️ REMOVE | Derivable (es display del code). |
| `languageSkills` | string | ✅ KEEP | UPeU-specific, no en core. |
| `campus` | string | 🔄 MIGRATE → **referencia a OrgType campus** (no string plano). El usuario tiene `assignment` a OrgType (`C-LIM`/`C-JUL`/`C-TPP`). | Evolveum best-practice §5: campus es entidad jerárquica, no flag. |
| `employeeType` | string | 📤 MOVE-TO-CORE → `UserType/employeeType` (multi) | Core ya tiene este atributo, NO duplicar. |

### `AcademicStatusType`

| Atributo PROD | Tipo | Decisión v3.0 | Razón |
|---|---|---|---|
| `studentCycle` | int | ✅ KEEP | UPeU-specific (1-10 ciclos académicos). |
| `academicProgram` | string | 🔄 MIGRATE → referencia a OrgType `program` (no string) | Es entidad jerárquica. |
| `academicProgramCode` | string | ✅ KEEP como `identifier` del OrgType program | Inmutable persistente Evolveum §5.3. |
| `alumniStatus` | string | 🗑️ REMOVE | Derivable: si archetype=`alumni` → status alumni; no necesita atributo. |
| `studyModality` | string | ✅ KEEP | UPeU-specific (presencial/virtual/semipresencial). |
| `faculty` | string | 🔄 MIGRATE → referencia a OrgType `faculty` | Es entidad jerárquica. |
| `academicPhase` | string | 🧮 COMPUTE en object template (`Pregrado`/`Maestría`/`Doctorado` derivado de studentCycle) | Derivable. |
| `advisorId` | string | 🔄 MIGRATE → `userRef` con relation `advisor` (no string plano) | Evolveum §5.5: relaciones, no strings. |
| `projects` | string | 🗑️ REMOVE de schema persona; modelar como OrgType `project` con assignments | Datos transaccionales no van en identity schema. |
| `courses` | string | 🗑️ REMOVE de schema persona; modelar como ServiceType o lookup table | Datos transaccionales no van en identity schema. |

### `FederatedIdentityType`

| Atributo PROD | Tipo | Decisión v3.0 | Razón |
|---|---|---|---|
| `orcid` | string | 🔄 MIGRATE → formato URI completo `https://orcid.org/{orcid}` alineado con `eduPersonOrcid` (`urn:oid:1.3.6.1.4.1.5923.1.1.1.16`) | eduPerson exige URI. |
| `keycloakSub` | string | 🗑️ REMOVE | El `sub` Keycloak lo gestiona Keycloak. NO viaja en MidPoint. Si necesitas correlation, usar `eduPersonUniqueId` que ES estable y federado. |

### `UniqueIdentifiersType`

| Atributo PROD | Tipo | Decisión v3.0 | Razón |
|---|---|---|---|
| `taxId` | string | 🔄 MIGRATE → formato URN canónico `urn:schac:personalUniqueID:pe:DNI:PE:{value}` (publicar como `schacPersonalUniqueID`) | SCHAC `urn:oid:1.3.6.1.4.1.25178.1.2.15`. |
| `institutionalIdCard` | string | 🔄 MIGRATE → URN canónico `urn:schac:personalUniqueCode:pe:institutionalIdCard:upeu.edu.pe:{value}` (publicar como `schacPersonalUniqueCode`) | SCHAC §14. |
| `universityIdCard` | string | 🗑️ REMOVE — duplicado/sinónimo de `institutionalIdCard` | Mantener uno solo. |
| `externalSystemId` | string | 📤 MOVE-TO-CORE → `UserType/employeeNumber` (es el ID en Lamb, inmutable, primary correlation key) | Evolveum §1.5: identifiers inmutables se prefieren a human-friendly. |

### `ExternalSystemRefsType` (NUEVO en PROD v2.3)

| Atributo PROD | Tipo | Decisión v3.0 | Razón |
|---|---|---|---|
| `kohaPatronId` | string | 📤 MOVE → `LinkRef` / shadow attribute del Resource Koha | Es identifier en proyección, no atributo focal. Evolveum §5.8. |
| `moodleUserId` | string | 🗑️ REMOVE | **UPeU NO usa Moodle** (decisión 2026-05-11). |
| `erpAccountId` | string | 📤 MOVE → `LinkRef` del Resource ERP correspondiente | Identifier en proyección. |

**Conclusión:** `ExternalSystemRefsType` completo se **ELIMINA** en v3.0. Los IDs de sistemas downstream no viven en el focus; viven en sus shadows. El correlation se hace por `employeeNumber`/`eduPersonUniqueId`.

---

## Resumen de cambios propuestos para v3.0

| Acción | Cantidad |
|---|---|
| ✅ KEEP en extension | **7** atributos |
| 🔄 MIGRATE (renombrar / cambiar tipo / URN-encode) | **10** atributos |
| 📤 MOVE-TO-CORE (eliminar de extension, usar core MidPoint) | **5** atributos |
| 🧮 COMPUTE (eliminar de extension, derivar en object template) | **3** atributos |
| 🗑️ REMOVE (eliminar totalmente) | **9** atributos |
| **TOTAL atributos actuales** | **34** |
| **Atributos previstos v3.0** | **17** (50% reducción) |

---

## Atributos canónicos NUEVOS a agregar en v3.0

Estos NO existen en v2.3 pero los necesitamos por estándar:

| Atributo | Mecanismo en MidPoint | Razón |
|---|---|---|
| **`eduPersonPrincipalName` (ePPN)** | Computed en object template: `{employeeNumber}@upeu.edu.pe` | Identificador federado canónico. |
| **`eduPersonUniqueId` (ePUI)** | Computed en object template: `{employeeNumber}@upeu.edu.pe` (alt: hash estable + scope) | Estándar federación, no reasignable. |
| **`eduPersonAffiliation` (multi)** | Computed desde archetype + condiciones (member, student, faculty, staff, employee, alum) | eduPerson vocabulario canónico. |
| **`eduPersonScopedAffiliation` (multi)** | Computed: `{affiliation}@upeu.edu.pe` por cada affiliation | REFEDS R&S obligatorio. |
| **`schacHomeOrganization`** | Constante `upeu.edu.pe` | SCHAC obligatorio. |
| **`schacHomeOrganizationType`** | Constante `urn:schac:homeOrganizationType:eu:higherEducationalInstitution` | SCHAC (namespace `pe:` no registrado oficialmente). |
| **`displayName`** | MidPoint core: `fullName` | SAML R&S obligatorio. |
| **`eduPersonAssurance` (multi)** | Computed según IAL alcanzado (`https://refeds.org/assurance/IAP/medium` o `/high`) | NIST 800-63 / REFEDS. |

---

## ComplexTypes propuestos v3.0

Reducción de 8 → 5 ComplexTypes:

| ComplexType v3.0 | Cubre |
|---|---|
| `DemographicsType` | birthDate, gender (ISO 5218), country, province (UPeU-only) |
| `EmploymentDataType` | hireDate, terminationDate |
| `AcademicStatusType` | studentCycle, academicProgramCode, studyModality |
| `ContactExtType` | personalWeb, languageSkills (lo que no entra en core) |
| `PeruvianIdentifiersType` | taxId (DNI URN-encoded), institutionalIdCard (URN-encoded) |

**Eliminados:** `AffiliationDataType` (todo es computed o core), `FederatedIdentityType` (orcid pasa a core/eduPerson), `UniqueIdentifiersType` (atributos se distribuyen), `ExternalSystemRefsType` (queda obsoleto).

---

## Atributos del core MidPoint que se usan (no extension)

| Atributo core | Mapea de |
|---|---|
| `name` | username (= `employeeNumber` o `studentCode`) |
| `employeeNumber` | externalSystemId (ID en Lamb) |
| `fullName` | computed `givenName + ' ' + familyName` |
| `givenName` | desde Lamb directo |
| `familyName` | desde Lamb directo |
| `emailAddress` | email institucional (multi: secondaryMail también) |
| `telephoneNumber` | phoneNumberAlt + principal |
| `employeeType` | tipo de contrato HR |
| `costCenter` | área administrativa UPeU |
| `organization` | unidad organizacional principal |
| `organizationalUnit` | sub-unidad |
| `locality` | sede primaria (display) |
| `title` | cargo |
| `personalNumber` | DNI plano (sin URN, internal) |
| `activation` | derivado de terminationDate vs today |
| `lifecycleState` | sincronizado desde Lamb |

---

## Riesgos identificados al migrar v2.3 → v3.0

1. **Resource Keycloak actual** depende de `extension/upeu:academicStatus/upeu:faculty` (entre otros). Al cambiar a referencia OrgType, **el resource Keycloak hay que reescribir o eliminar** (decisión: eliminar, ver roadmap Fase 6.4).
2. **Datos existentes** con `extension/upeu:moodleUserId` se pierden al eliminar `ExternalSystemRefsType`. Verificar si algún user real tiene este valor — si sí, ¿lo necesitamos en otro lado?
3. **`primaryAffiliationCode` está poblado por inbound mappings desde Lamb** (documentado en memorias). Al pasar a computed, los inbound mappings ya no escriben — el flujo cambia: archetype determina el affiliation, no Lamb.
4. **Documentos** que referencian v2.2/v2.3 quedarán desactualizados (afecta a 7+ archivos).
5. **18 users locales en Keycloak** (mencionados en memorias) — su correlación depende de identifiers v2.3; verificar si la migración rompe linkRefs.

---

## Próximas decisiones que Alberto debe tomar

| Decisión | Opciones | Recomendación |
|---|---|---|
| **Namespace v3.0** | (a) reusar `urn:upeu:midpoint:person` con bump de versión interna; (b) `urn:upeu:midpoint:person:v3` (separado para coexistir) | (a) reusar con deprecation graceful — MidPoint UI permite mantener atributos `deprecated="true"` para transición. |
| **Estrategia de migración** | (a) big-bang (eliminar v2.3 y crear v3.0); (b) coexistencia con dual-write durante transición | (b) coexistencia 2 semanas — atributos deprecated marcados, mappings nuevos hacia core/computed, eliminación final tras validar. |
| **Drift DEV vs PROD** | (a) Igualar DEV a PROD (v2.3) primero, luego v3.0; (b) Saltar DEV directo a v3.0 desde v2.2 | (b) saltar — DEV se va a sobrescribir igual con v3.0. |
| **`taxId` (DNI)** | (a) Mantener PII en MidPoint con URN encoding; (b) hash y derivar URN en object template | (a) mantener encoded — necesario para auditoría y validación RENIEC. |

---

## Archivos generados en esta auditoría

- `audit/2026-05-11/schemaType-current.xml` — XML DEV (v2.2, 425 líneas)
- `audit/2026-05-11/schemaType-prod.xml` — XML PROD (v2.3, mayor)
- `audit/2026-05-11/AUDIT-schema-v2-current.md` — este reporte

---

## Siguiente paso

**Fase 1.2 — Diseñar SchemaType v3.0 canónico (4h).** Requiere confirmación de Alberto sobre las 4 decisiones arriba.
