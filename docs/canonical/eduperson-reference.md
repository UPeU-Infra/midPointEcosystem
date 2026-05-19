# Diccionario de atributos eduPerson para SAML federado

> Referencia técnica de los atributos eduPerson estándar que se exponen vía Keycloak SAML a vendors externos (Scopus, WoS, EBSCO, etc.). Este es el "contrato" entre MidPoint UPeU y el mundo externo.

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

## Mapeo de valores `primaryAffiliationCode` (UPeU específico)

| primaryAffiliationCode (Lamb/MidPoint) | eduPersonAffiliation | Notas |
|---|---|---|
| `DOCENTE_TC` (Tiempo Completo) | `faculty` | Docente principal |
| `DOCENTE_TP` (Tiempo Parcial) | `faculty` | Docente part-time |
| `ESTUDIANTE_PRE` | `student` | Pregrado |
| `ESTUDIANTE_POS` | `student` | Posgrado (también member) |
| `ADMIN` | `staff` | Administrativo |
| `TRABAJADOR` | `staff` | Personal de servicios |
| `EGRESADO` | `alum` | Si tiene acceso vigente |
| `INVITADO` | `affiliate` | Externos con afiliación temporal |

## Multivalor: cuando un user tiene múltiples roles

Caso típico: docente que también estudia posgrado.

```
eduPersonAffiliation: faculty
eduPersonAffiliation: student
eduPersonScopedAffiliation: faculty@upeu.edu.pe
eduPersonScopedAffiliation: student@upeu.edu.pe
```

El vendor recibe ambos valores y aplica reglas según licenciamiento.

## Mínimo viable por vendor (referencia rápida)

| Vendor | Atributos mínimos |
|---|---|
| Scopus, ScienceDirect (Elsevier) | ePPN + ePSA + mail |
| Web of Science (Clarivate) | ePPN + ePSA |
| EBSCOhost | userId + ePSA + (sede para reportes) |
| ProQuest | ePPN + ePSA + mail |
| JSTOR | ePPN o ePTID + ePSA |
| AccessMedicina (McGraw-Hill) | mail + displayName + ePSA |
| UpToDate (Wolters Kluwer) | mail + displayName |
| vLex | mail + displayName + ePSA + DNI |
| IEEE Xplore | ePPN + ePSA |

## Ley 29733 (Datos Personales Perú) — minimización

Solo se debe enviar al vendor lo estrictamente necesario:
- ✅ Identificadores: ePPN o (preferible) ePTID anonimizado
- ✅ Rol: ePSA
- ✅ Email institucional: para notificaciones del servicio
- ❌ NO enviar: DNI (salvo vLex que lo exige), edad, dirección, datos académicos detallados sin necesidad
