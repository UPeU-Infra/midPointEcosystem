# Diccionario de atributos eduPerson para SAML federado

> Referencia técnica de los atributos eduPerson estándar que se exponen vía Keycloak SAML a vendors externos (Scopus, WoS, EBSCO, etc.). Este es el "contrato" entre MidPoint UPeU y el mundo externo.
>
> **Estándar base:** eduPerson 202208 v4.4.0 (REFEDS/Internet2). Solo se documentan los atributos que UPeU efectivamente usa o planea usar. No se inventan atributos fuera del estándar.
>
> **Fuente de atributos (2026-06-06):** MidPoint 4.10.2 provisiona atributos a OpenLDAP HA (Node1: 192.168.15.168:389, Node2: 192.168.15.169:389); ⛔ *(ADR-058, 17-jul-2026: la antigua nota "Keycloak User Federation lee de OpenLDAP" queda retirada — no se federa LDAP en Keycloak; las apps leen el LDAP con bind propio.)* Los atributos eduPerson derivados (ePPN, ePSA, eduPersonAffiliation, schacHomeOrganization) están **pendientes de mapear** en el outbound LDAP (Fase 13). Los campos fuente del schema canónico son `urn:sciback:midpoint:person` y overlay `urn:upeu:midpoint:local`.
>
> **Modelo de afiliación actual:** la afiliación se deriva del archetype estructural del usuario en MidPoint (no de `primaryAffiliationCode` — atributo deprecado). El mapeo archetype→eduPersonAffiliation se documenta en la sección correspondiente.

## Atributos núcleo (siempre se emiten)

### eduPersonPrincipalName (ePPN)

- **URN OID**: `urn:oid:1.3.6.1.4.1.5923.1.1.1.6`
- **Tipo**: identificador único persistente
- **Formato**: `<localpart>@<scope>` (ej: `jsanchez@upeu.edu.pe`)
- **Mutabilidad**: NO debe cambiar durante la vida del user
- **Uso vendor**: identificación única para licenciamiento
- **Source**: UserType `name` o derivado de `emailAddress`

### eduPersonScopedAffiliation (ePSA)

- **URN OID**: `urn:oid:1.3.6.1.4.1.5923.1.1.1.9`
- **Tipo**: rol institucional con scope
- **Formato**: `<role>@<scope>`
- **Valores válidos del rol** (eduPerson v2):
  - `faculty` — docente con cargo
  - `student` — estudiante matriculado
  - `staff` — personal administrativo no docente
  - `member` — cualquier persona afiliada (catch-all)
  - `affiliate` — colaboradores externos
  - `alum` — egresados con acceso
  - `library-walk-in` — walk-in users biblioteca
- **Multivaluado**: SÍ (un user puede ser `faculty@upeu.edu.pe` y `staff@upeu.edu.pe`)
- **Mutabilidad**: SÍ (cambia con la vida del user)
- **Uso vendor**: AUTORIZACIÓN — el vendor decide si dejar entrar
- **Source UPeU**: derivado de `extension/primaryAffiliationCode` + `extension/campus`

### eduPersonAffiliation

- **URN OID**: `urn:oid:1.3.6.1.4.1.5923.1.1.1.1`
- **Diferencia con ePSA**: solo el rol, sin scope
- **Cuándo usarlo**: algunos vendors antiguos solo aceptan este

### mail

- **URN OID**: `urn:oid:0.9.2342.19200300.100.1.3`
- **Source**: UserType `emailAddress`

### displayName

- **URN OID**: `urn:oid:2.16.840.1.113730.3.1.241`
- **Source**: UserType `fullName` o `givenName + " " + familyName`

### eduPersonTargetedID (ePTID)

- **URN OID**: `urn:oid:1.3.6.1.4.1.5923.1.1.1.10`
- **Tipo**: identificador opaco distinto por cada SP
- **Privacidad**: no permite correlación entre vendors
- **Calculado por**: Keycloak automáticamente
- **Cuándo emitirlo**: cuando el vendor lo prefiera para minimizar PII (Ley 29733)

## Atributos para reporting (opcionales según vendor)

### eduPersonOrgUnitDN

- **URN OID**: `urn:oid:1.3.6.1.4.1.5923.1.1.1.4`
- **Source UPeU**: `extension/faculty`
- **Uso**: segmentación reportes COUNTER por facultad

### departmentNumber

- **URN OID**: `urn:oid:2.16.840.1.113730.3.1.2`
- **Source UPeU**: `extension/academicProgram`
- **Uso**: segmentación reportes por programa académico

### organizationName (o)

- **URN OID**: `urn:oid:2.5.4.10`
- **Valor UPeU**: constante `"Universidad Peruana Unión"`

### organizationalUnit (ou)

- **URN OID**: `urn:oid:2.5.4.11`
- **Source UPeU**: `extension/campus` mapeado
- **Uso**: sede física (Lima, Tarapoto, Juliaca)

### localityName (l)

- **URN OID**: `urn:oid:2.5.4.7`
- **Source UPeU**: derivado de `campus`

### schacHomeOrganization

- **URN OID**: `urn:oid:1.3.6.1.4.1.25178.1.2.9`
- **Valor UPeU**: constante `"upeu.edu.pe"`

### schacHomeOrganizationType

- **URN OID**: `urn:oid:1.3.6.1.4.1.25178.1.2.10`
- **Valor UPeU**: constante `"urn:schac:homeOrganizationType:int:university"`

### eduPersonEntitlement

- **URN OID**: `urn:oid:1.3.6.1.4.1.5923.1.1.1.7`
- **Tipo**: URI representando un derecho específico
- **Cuándo usarlo**: para licenciamiento granular (ej: solo posgrado puede acceder)
- **Ejemplo**: `urn:upeu:entitlement:postgrado-only`

## Mapeo de valores afiliación (UPeU) — estado 2026-06-06

`eduPersonAffiliation` se **deriva del archetype estructural** del usuario MidPoint (archetype único por persona — Semančík §8.3). El atributo `primaryAffiliationCode` fue deprecado; ya no se usa.

| Archetype MidPoint (OID) | eduPersonAffiliation (multivalor) | eduPersonScopedAffiliation | eduPersonPrimaryAffiliation |
|---|---|---|---|
| `archetype-user-employee-faculty` (`c93083ca`) | `faculty`, `employee`, `member` | `faculty@upeu.edu.pe` | `faculty` |
| `archetype-user-student` (`3037fbd2`) | `student`, `member` | `student@upeu.edu.pe` | `student` |
| `archetype-user-employee-staff` (`6460facf`) | `staff`, `employee`, `member` | `staff@upeu.edu.pe` | `staff` |
| `archetype-user-alumni` (`87552943`) | `alum`, `member` | `alum@upeu.edu.pe` | `alum` |
| `archetype-user-affiliate-partner-institution` | `affiliate` | `affiliate@upeu.edu.pe` | `affiliate` |
| `archetype-user-contractor` | `affiliate` | `affiliate@upeu.edu.pe` | `affiliate` |
| `archetype-user-affiliate-researcher` | `affiliate`, `member` | `affiliate@upeu.edu.pe` | `affiliate` |

**Prelación `eduPersonPrimaryAffiliation`** (cuando una persona tiene múltiples roles): `staff > faculty > student > alum > affiliate`.

**Multi-afiliación:** un docente que estudia posgrado tiene archetype `employee-faculty` (structural) + role de afiliación estudiante (business role). El outbound LDAP debe emitir ambos valores multivalor: `faculty`, `student`, `employee`, `member`.

El outbound mapping al LDAP cache calculará `eduPersonAffiliation`, `ePSA` y `eduPersonPrimaryAffiliation` desde el archetype + roles de afiliación activos del objeto focus. **Estado: pendiente (Fase 13).**

## Multivalor: cuando un user tiene múltiples roles

Caso típico: docente que también estudia posgrado.

```
eduPersonAffiliation: faculty
eduPersonAffiliation: student
eduPersonScopedAffiliation: faculty@upeu.edu.pe
eduPersonScopedAffiliation: student@upeu.edu.pe
```

El vendor recibe ambos valores y aplica reglas según licenciamiento.

## Mappings Oracle LAMB → MidPoint → OpenLDAP (tabla IIA)

| Atributo LDAP (outbound) | Fuente en MidPoint | IIA origen | Estado |
|---|---|---|---|
| `uid` | `name` (UserType) | MidPoint (calculado = código institucional) | Activo |
| `cn` / `displayName` | `fullName` (UserType) | MOISES.PERSONA_NATURAL | Activo |
| `givenName` / `sn` | `givenName`, `familyName` | MOISES.PERSONA_NATURAL (RENIEC fallback) | Activo |
| `mail` | `emailAddress` (UserType) | MidPoint (calculado `{code}@upeu.edu.pe`) | Activo |
| `employeeNumber` | `employeeNumber` (core) | MOISES.TRABAJADOR.cod_trabajador | Activo |
| `eduPersonPrincipalName` | `{name}@upeu.edu.pe` | MidPoint (object template) | **Pendiente Fase 13** |
| `eduPersonAffiliation` | derivado de archetype | MidPoint (calculado) | **Pendiente Fase 13** |
| `eduPersonScopedAffiliation` | derivado de archetype + scope | MidPoint (calculado) | **Pendiente Fase 13** |
| `eduPersonPrimaryAffiliation` | prelación desde archetype | MidPoint (calculado) | **Pendiente Fase 13** |
| `schacHomeOrganization` | constante `upeu.edu.pe` | Constante institucional | **Pendiente Fase 13** |
| `schacPersonalUniqueID` | `identityDocuments[primary].number` URN-encoded | MOISES.PERSONA_NATURAL.DNI | **Pendiente Fase 13** |
| `ou` (org unit) | `parentOrgRef` → OrgType identifier | ELISEO.ORG_AREA | **Pendiente Fase 13** |
| `o` (organization) | constante `Universidad Peruana Union` | Constante institucional | **Pendiente Fase 13** |

## Mínimo viable por vendor (referencia rápida)

| Vendor | Atributos mínimos | Estado UPeU |
|---|---|---|
| Scopus, ScienceDirect (Elsevier) | ePPN + ePSA + mail | Pendiente Fase 13 |
| Web of Science (Clarivate) | ePPN + ePSA | Pendiente Fase 13 |
| EBSCOhost | userId + ePSA + sede para reportes | Pendiente Fase 13 |
| ProQuest | ePPN + ePSA + mail | Pendiente Fase 13 |
| JSTOR | ePPN o ePTID + ePSA | Pendiente Fase 13 |
| AccessMedicina (McGraw-Hill) | mail + displayName + ePSA | Pendiente Fase 13 |
| UpToDate (Wolters Kluwer) | mail + displayName | Pendiente Fase 13 |
| vLex | mail + displayName + ePSA + DNI | Pendiente Fase 13 |
| IEEE Xplore | ePPN + ePSA | Pendiente Fase 13 |

## Ley 29733 (Datos Personales Perú) — minimización

Solo se debe enviar al vendor lo estrictamente necesario:
- Identificadores: ePPN o (preferible) ePTID anonimizado
- Rol: ePSA
- Email institucional: para notificaciones del servicio
- NO enviar: DNI (salvo vLex que lo exige), edad, dirección, datos académicos detallados sin necesidad
- `schacPersonalUniqueID` (DNI en URN) solo a vendors que lo requieran explícitamente y con fundamento legal
