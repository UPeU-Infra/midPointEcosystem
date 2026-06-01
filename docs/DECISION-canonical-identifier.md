# Decision Record — Identificador canónico de persona (UPeU / SciBack-IGA)

**Estado:** RATIFICADO · **Fecha:** 2026-06-01 · **Supersede:** cualquier afirmación previa en `IIA-MATRIX.md`, `ARCHITECTURE.md` e `IDENTITY-PROFILES.md` que mapee el DNI a `name`/`personalNumber`.

**Esta es la ÚNICA fuente de verdad sobre el identificador de persona.** Cualquier otro doc que contradiga este DR está drifted y debe corregirse contra él.

---

## 1. Veredicto (resumen ejecutable)

| Concepto | Valor canónico | NO es | Estándar |
|---|---|---|---|
| `name` (login MidPoint) | Código institucional inmutable: `LAMB.CODIGO` (estudiantes) / `LAMB.COD_APS` (trabajadores) / asignado por DTI | **NO el DNI** | ISO 24760 §3.1.3 *identifier*; libro MidPoint §6.1 (PolyString) / §4.4 (identificadores inmutables) |
| `personalNumber` | **`== name`** (réplica del código institucional para compat SCIM) | **NO el DNI** | SCIM 2.0 `employeeNumber` RFC 7643 §4.3 |
| `extension/institutionalCode` | **`== name`** (alias semántico para visualización) | **NO el DNI** | [UPeU-LOCAL] |
| DNI (y CE/PASSPORT/PTP/CPP/CSR) | `identityDocuments[]` tipado → primario exportado como `schacPersonalUniqueID` (URN) y reflejado en `extension/sb:taxId` | **NO es login, NO es `name`, NO es `personalNumber`** | SCHAC 1.6.0 `schacPersonalUniqueID`; Ley 26497 RENIEC; DL 1350 Migración |
| Carné Koha (`cardnumber`) | **`== name`** (código institucional). DNI va como atributo secundario | **NO el DNI como llave** | derivado de lo anterior |

**Triple alias canónico:** `name == personalNumber == institutionalCode` = el código institucional. El DNI vive en una dimensión distinta (documento de identidad / llave de correlación), **nunca** es ninguno de los tres.

---

## 2. Fundamento por estándar

### 2.1 ISO/IEC 24760-1 §3.1.3 — *identifier*
El *identifier* es el atributo que distingue unívocamente la entidad **dentro de un dominio**. Debe ser estable e independiente de atributos de negocio o nacionales. El DNI es un **dato nacional emitido por un tercero (el Estado)**: no todos lo tienen (extranjeros), puede corregirse, y su semántica es legal-fiscal, no de login. Usarlo como identifier acopla la identidad institucional a un registro externo → anti-canónico. → `name` = código institucional propio.

### 2.2 eduPerson 202208
- `eduPersonUniqueId` (`.1.13`) = identificador omnidireccional **no reasignable**, federado, derivado del código institucional estable (`{personalNumber}@upeu.edu.pe`), **no del DNI**.
- `eduPersonPrincipalName` (ePPN) = `{name}@scope`; tampoco es el DNI.
- El DNI **no aparece** en el vocabulario de identificadores eduPerson — es dato SCHAC, no eduPerson.

### 2.3 SCHAC 1.6.0 — separación explícita de las dos dimensiones
- **`schacPersonalUniqueID`** (`.15`) = **identificador legal oficial del Estado** (DNI/CE). URN: `urn:schac:personalUniqueID:pe:DNI:PER:{dni}`. **PII sensible — NO se publica a SPs** salvo necesidad estricta.
- **`schacPersonalUniqueCode`** (`.14`) = **código único institucional** (carné/ESI). URN: `urn:schac:personalUniqueCode:pe:studentID:upeu.edu.pe:{name}`.

El propio estándar separa "código institucional" (Code) de "documento legal" (ID). Mezclarlos rompe SCHAC. → DNI ⟶ `schacPersonalUniqueID`; código institucional (`name`) ⟶ `schacPersonalUniqueCode`.

### 2.4 SCIM 2.0 — RFC 7643 §4.3 (`employeeNumber`)
`employeeNumber` = *"numeric or alphanumeric identifier assigned to a person, typically based on order of hire or association with an organization"*. Es un **identificador asignado por la organización**, no un documento nacional. Por eso `personalNumber == name` (código institucional) es el mapeo correcto, y **NO** `personalNumber == DNI`. (Nota proyecto: se usa `personalNumber`, no `employeeNumber` nativo, por doctrina `feedback_no_deprecated_fields.md`; SCIM `employeeNumber` se materializa en outbound desde `personalNumber`.)

### 2.5 Libro MidPoint (Semančík v2.3)
- §6.1 — `name` es PolyString, debe ser **inmutable**; el rename es costoso ("rename hell"). El DNI puede corregirse en RENIEC → no apto como `name`.
- §4.4 — preferir **identificadores inmutables ya existentes** en vez de generar logins human-friendly. El código institucional cumple; el DNI no es universal.
- §9.4.4 (Iteration) — *"The best strategy is to avoid using those generated human-friendly identifiers altogether."* Refuerza usar el código institucional numérico como `name`.

### 2.6 Restricción legal peruana
- **Ley 26497 (RENIEC):** el DNI es de 8 dígitos y aplica **solo a peruanos**.
- **DL 1350 (Migración):** extranjeros usan CE / PTP / CPP / CSR / Pasaporte. **No tienen DNI.**
- Conclusión: un esquema "DNI universal como carné/login" es **legalmente inviable** — dejaría a estudiantes y personal extranjero sin identificador. El **código institucional sí existe para todos** → es la única base válida de `name`/`cardnumber`.

---

## 3. Veredicto sobre `personalNumber` (resolución de la contradicción)

**Canónico: `personalNumber == name == institutionalCode` (código institucional). NO es el DNI.**

- `IIA-MATRIX.md` decía `personalNumber (DNI)` → **ERROR de drift, corregido** (ver §6).
- Razón: SCIM RFC 7643 §4.3 define `employeeNumber`/`personalNumber` como identificador **asignado por la organización**, exactamente la semántica del código institucional. El DNI es documento nacional → pertenece a `identityDocuments[]`/`schacPersonalUniqueID`, no a `personalNumber`.
- Confirmado por `01-spec.md` §4.1.1.b y `sciback-iga-blueprint` §Pilar 1.

**Nota operativa (caso COD_APS == DNI):** que algunos `COD_APS` coincidan numéricamente con el DNI (p.ej. Juan Alberto Sánchez: `COD_APS=10867326 == DNI 10867326`) es **coincidencia histórica del dato origen, NO política**. La tarea #58 ("padding COD_APS con ceros a la izquierda") demuestra que COD_APS es un **código propio con su propia regla de formato** — se normaliza independientemente del DNI. Canónicamente `name` deriva del COD_APS/CODIGO normalizado (CANON_KEY), no del DNI, aunque a veces los dígitos coincidan.

---

## 4. Veredicto sobre el carné de Koha (`cardnumber`)

**Canónico: `cardnumber == name` (código institucional). El DNI es atributo secundario, no la llave.**

- Justificación: el carné de biblioteca es un **identificador institucional** del patrón, no un documento del Estado. Debe ser estable, universal (extranjeros incluidos) y reusable entre sistemas → coincide exactamente con `name`/`schacPersonalUniqueCode`.
- El conector Koha ya mapea `cardnumber-outbound = $focus/name` → **es el comportamiento correcto y debe mantenerse**.
- DNI en Koha: como **`extended_attribute` secundario** (búsqueda en mostrador / correlación legacy), nunca como `cardnumber` autoritativo.

**Por qué hoy "se ven" como DNI los trabajadores:** su `name = COD_APS` coincide numéricamente con el DNI en muchos casos (caso testigo Sánchez). NO es que el carné sea el DNI: es el código institucional que casualmente igual al DNI. Estudiantes (carné = código universitario ≠ DNI) lo evidencian: 1,455 con código vs 283 con DNI = legado a reconciliar hacia `name`.

**Regla resultante para el conector (a aplicar en otra tarea, NO ejecutada aquí):**
1. `cardnumber` (outbound) = `$focus/name` (código institucional / CANON_KEY normalizado). **Confirmado vigente — mantener.**
2. DNI → mapear a un `extended_attribute` de Koha (p.ej. `NATIONAL_ID`), **secundario**, no a `cardnumber`.
3. Migración legacy: los patrones (estudiantes con DNI como carné, ~283; trabajadores ~46 con código) deben converger a `cardnumber = name`. Tarea de saneamiento aparte.
4. Correlación de entrada se mantiene en 3 capas (`cardnumber=name`, `lambDocNum=DNI normalizado`, `taxId=URN SCHAC`) — válida y robusta contra duplicados legacy (ver `runbooks/koha-ldap-reactivation-2026-05-30.md` §correlación).

---

## 5. Tabla canónica de referencia (copiar a cualquier doc nuevo)

| Atributo focus | Contenido | Origen | Exporta a |
|---|---|---|---|
| `name` | código institucional inmutable | `LAMB.CODIGO` / `LAMB.COD_APS` (CANON_KEY normalizado) | LDAP `uid`, Koha `cardnumber`, ePPN, `eduPersonUniqueId` base |
| `personalNumber` | `== name` | derivado | SCIM `employeeNumber` (outbound) |
| `extension/institutionalCode` | `== name` | derivado | visualización |
| `identityDocuments[].number` (type=DNI) | DNI 8 díg. | RENIEC / LAMB `NUM_DOCUMENTO` | `schacPersonalUniqueID` (URN), `extension/sb:taxId` |
| `extension/sb:taxId` | DNI/CE plano indexed | LAMB | correlación interna (`lambDocNum`) |

**Llaves de correlación de entrada (inbound):** DNI/CE normalizado (`lambDocNum` / `taxId`). **Llave de login/identidad (outbound):** `name` (código institucional). Son dimensiones distintas y NO se cruzan.

---

## 6. Docs corregidos para alinear con este DR (2026-06-01)

| Doc | Antes (drifted) | Después |
|---|---|---|
| `IIA-MATRIX.md` §2.1 L34 | `personalNumber (DNI)` · IIA `trabajadores` · override `reniec-cache` | `personalNumber (== name, código institucional)` · IIA computed-from-`name`. DNI movido a fila propia → `identityDocuments`/`schacPersonalUniqueID` |
| `ARCHITECTURE.md` §2.5 | `personalNumber`/`employeeNumber` mezclados sin afirmar `== name`; `institutionalIdCard` "pendiente verificar tabla" | nota explícita `name == personalNumber == institutionalCode ≠ DNI`; remite a este DR |
| `IDENTITY-PROFILES.md` §2/§4.5 | `NUM_DOCUMENTO (DNI/CE) → personalNumber (core)` como correlación principal | aclarado: DNI correlaciona vía `taxId`/`lambDocNum`; `name`/`personalNumber` = código institucional, NO el DNI |

---

## 7. Referencias

- ISO/IEC 24760-1:2019 §3.1.3 (*identifier*).
- eduPerson 202208 — `eduPersonUniqueId` (.1.13), `eduPersonPrincipalName`.
- SCHAC 1.6.0 — `schacPersonalUniqueID` (.15), `schacPersonalUniqueCode` (.14); SCHAC URN Registry.
- SCIM 2.0 — RFC 7643 §4.3 (`employeeNumber`).
- Semančík et al., *Practical Identity Management with MidPoint* v2.3 — §6.1 (PolyString name), §4.4 (identificadores inmutables), §9.4.4 (Iteration).
- Ley 26497 (RENIEC, DNI 8 díg.); DL 1350 (Migración, documentos de extranjeros).
- Skills `iga-canonical-standards` (§DNI→schacPersonalUniqueID, §código→schacPersonalUniqueCode), `midpoint-best-practices`.
- Specs concordantes: `specs/iga-canonical-model-upeu/01-spec.md` §4.1.1; `specs/sciback-iga-blueprint/01-iga-blueprint-peru.md` Pilar 1.
