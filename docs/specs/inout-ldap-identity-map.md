# Contrato InOut←IGA — `identity_map` LDAP (aforo CRAI, D-11.bis)

> **Estado:** diseño aprobado, **NO aplicado a PROD**. Requiere OK de Alberto para desplegar (§7).
> **Fecha:** 2026-07-16 · **Verificado contra PROD** (solo lectura) el 2026-07-16.
> **Principio rector.** MidPoint es la única fuente de verdad. InOut es un **segundo consumidor**
> del mismo identity cache LDAP que ya alimenta a RIMS — **no** un eje paralelo de gobernanza.
> Ningún operador edita estos atributos: MidPoint los reescribe en cada recompute/reconcile.

## 1. Los 4 atributos (+ el carné, que ya existía)

InOut lee `ou=people,dc=upeu,dc=edu,dc=pe` con la cuenta de solo lectura
`cn=rims-reader,ou=services,dc=upeu,dc=edu,dc=pe` (credenciales: `~/.secrets/ldap-rims-reader.env`).

| Rol en InOut | Atributo LDAP | Valores | Origen (IIA → item del foco) | Índice `eq` |
|---|---|---|---|---|
| **Carné (COD_UPEU)** | `uid` | `202611481` | `$focus/name` | ✅ ya existe |
| **DNI plano** | `scibackDocumentNumber` | `61532826` | `sciback:identityDocuments[primary].number` | ➕ a crear |
| **Facultad** | `scibackFacultyCode` | `FCS`\|`FIA`\|`FACIHED`\|`FCE`\|`FACTEO`\|`EPG` | `sciback:facultyName` (LAMB `ELISEO.ORG_AREA.NOMBRE`) | ➕ a crear |
| **Campus / sede** | `scibackCampusCode` | `LIMA`\|`JULIACA`\|`TARAPOTO` | `campusStudent ?: campusWorker ?: locality` | ➕ a crear |
| **ID canónico inmutable** | `eduPersonUniqueId` | `<ID_PERSONA>@upeu.edu.pe` | `sciback:externalSystemId` (ID_PERSONA, MDM MOISES) | ➕ a crear |

## 2. `identity_map` y filtro de búsqueda (para el `LdapProvider` de InOut)

```python
LDAP_URL       = 'ldap://192.168.15.168:389'   # réplica: 192.168.15.169
BIND_DN        = 'cn=rims-reader,ou=services,dc=upeu,dc=edu,dc=pe'
BASE_PEOPLE    = 'ou=people,dc=upeu,dc=edu,dc=pe'

identity_map = {
    'carne':     'uid',                     # COD_UPEU
    'dni':       'scibackDocumentNumber',   # DNI (8 díg) o CE
    'facultad':  'scibackFacultyCode',
    'sede':      'scibackCampusCode',
    'person_id': 'eduPersonUniqueId',       # ancla estable, NO cambia entre matrículas
}

# D-11.bis: carné O DNI resuelven al MISMO registro, indistintamente.
search_filter = '(|(uid={v})(scibackDocumentNumber={v}))'
```

**Guardar `person_id` (`eduPersonUniqueId`), no el carné**, como llave de la persona en los
registros de aforo: el COD_UPEU es human-friendly y puede cambiar; `ID_PERSONA` no.

### Notas de implementación
- Escapar el valor escaneado antes de interpolar (RFC 4515) — es input de un lector físico.
- Ambos atributos del filtro son `SINGLE-VALUE` + indexados `eq` → la búsqueda es O(1) sobre ~37.5k entries.
- Si el scan no matchea, el resultado es **0 entries** (no error): tratar como "persona no reconocida".
- `.169` es réplica de datos válida para lectura (syncrepl); los índices se aplican en ambos nodos (§5).

## 3. Cobertura y honestidad del dato (leer antes de construir reportes)

| Atributo | Cobertura real | Qué hacer en InOut |
|---|---|---|
| `uid` | 100% de personas activas | — |
| `scibackDocumentNumber` | Alta; ausente si la persona no tiene documento primario en LAMB | Fallback: resolver solo por carné |
| `scibackFacultyCode` | **Solo ESTUDIANTES** (+3 staff). `facultyName` no se puebla para docentes/staff (verificado, contrato Koha §5) | El aforo-por-facultad de no-estudiantes vendrá **vacío**. Reportar "sin facultad", no imputar |
| `scibackCampusCode` | Alta, pero **sin default deliberado** | Si el campus no mapea → atributo **ausente**. Reportar "sin campus" |
| `eduPersonUniqueId` | 100% (mixto: `ID_PERSONA@` para quien tiene ID_PERSONA; fallback `COD_UPEU@` para el resto) | Usarlo como opaco: no parsearlo |

**Por qué `scibackCampusCode` no tiene default.** En Koha, un `library_id` vacío rompe la creación
de la cuenta, y por eso su mapping cierra con un default conservador `BUL`. Aquí el atributo es
**demográfico, de reporte**: un default incorrecto no falla ruidosamente — contamina en silencio el
aforo, atribuyendo personas a un campus donde no están. **Mejor sin valor que con un campus inventado.**

**Por qué no hay código `CIA`.** CIA (Centro de Investigación Adventista) **no es un campus**: es un
edificio con biblioteca especializada **dentro del campus Lima**, al que se le puede poner un lector
InOut en sus puertas. El edificio es **dimensión del LECTOR de InOut**, no atributo de la persona: un
alumno de Teología pertenece al campus `LIMA` y puede escanear tanto en la puerta del CRAI Lima como
en la del CIA. (En Koha `CIA` sí existe, pero como *branchcode de circulación* — otra semántica, no
se copia aquí. Tampoco se copian `BUL`/`BUJ`/`BUT`.)

**Vocabulario de facultad compartido con Koha.** `scibackFacultyCode` reutiliza **exactamente** el
switch `Bsort1` ya resuelto en `upeu/resources/koha-ils.xml` (`statistics1-outbound`): misma fuente
canónica (`sciback:facultyName`), mismos códigos (authorised_values verificados en Koha PROD). InOut
y Koha comparten vocabulario → los reportes cuadran entre sistemas.

## 4. Decisiones de diseño canónicas (justificación)

- **DNI plano en atributo dedicado, no en `schacPersonalUniqueID` ni en `employeeNumber`.**
  SCHAC 1.6.0 obliga a que `schacPersonalUniqueID` sea URN
  (`urn:schac:personalUniqueID:pe:DNI:PE:61532826`) — se conserva intacto (RIMS/Keycloak lo consumen
  así) y **no** se sobrecarga con el valor plano. `employeeNumber` (inetOrgPerson/SCIM Enterprise) es
  el número asignado por el **empleador** — aquí ese rol lo cumple `personalNumber` →
  `schacPersonalUniqueCode` — usarlo para el documento nacional sería un anti-pattern semántico
  (está vacío en PROD, pero se deja libre). eduPerson/inetOrgPerson no tienen atributo para
  "documento nacional en plano" → `iga-canonical-standards` §11 regla 12: se define atributo custom
  bajo el arco OID propio, no se abusa de uno estándar.
- **`eduPersonUniqueId` = `ID_PERSONA@upeu.edu.pe`.** eduPerson 202208 §.1.13 exige opaco, inmutable
  y no reasignable. Hoy en PROD vale `202611481@upeu.edu.pe` (= COD_UPEU@), que no cumple. ID_PERSONA
  (MDM MOISES) es inmutable y estable entre matrículas y entre los ejes estudiante/egresado/trabajador.
- **Reutilización, no reinvención.** Facultad reutiliza el switch Bsort1 de Koha; campus reutiliza la
  precedencia `campusStudent ?: campusWorker ?: locality` del `library-id-outbound` de Koha (misma
  pregunta: "¿dónde está VIVO el vínculo?"), pero **no** su mapa de branchcodes.
- **Sin cambio de ACL.** La regla `{2}` de `04-acl-mdb.ldif` ya otorga a `cn=rims-reader` `read` sobre
  todo el subtree `ou=people`, sin restricción por atributo → los atributos nuevos son legibles
  automáticamente. Verificado en PROD: `rims-reader` ya lee `schacPersonalUniqueID` (que **contiene el
  DNI** en URN) → exponer el DNI plano al mismo lector **no añade exposición nueva**.
  *Opcional a futuro (gobierno, no bloqueante):* cuenta propia `cn=inout-reader` para trazabilidad
  separada de InOut vs RIMS.

## 5. Estado PROD verificado (2026-07-16, solo lectura)

```
# Índices — IDÉNTICOS en .168 y .169
olcDbIndex: uid eq          ← el carné YA es buscable por igualdad
olcDbIndex: mail eq | memberOf eq | entryCSN eq | entryUUID eq | objectClass eq

# Schema
dn: cn={12}upeu,cn=schema,cn=config
olcObjectClasses: {0} 1.3.6.1.4.1.47378.2.1 upeuPerson      ← siguiente OID libre: .2.3
olcObjectClasses: {1} 1.3.6.1.4.1.47378.2.2 scibackOrgUnit
olcAttributeTypes: {0}..{7} = OIDs .1.1 .. .1.8             ← siguientes libres: .1.9/.1.10/.1.11

# Entry real (bind cn=rims-reader)
dn: uid=202611481,ou=people,dc=upeu,dc=edu,dc=pe
uid: 202611481
eduPersonUniqueId: 202611481@upeu.edu.pe                    ← = COD_UPEU@, a migrar (§6)
schacPersonalUniqueID: urn:schac:personalUniqueID:pe:DNI:PE:61532826   ← DNI solo en URN
(employeeNumber: ausente)
objectClass: inetOrgPerson eduPerson schacPersonalCharacteristics schacEntryMetadata midPointPerson upeuPerson
```
`upeuPerson` ya cuelga de cada entry → los 3 atributos nuevos aterrizan sin tocar la lista de
`auxiliaryObjectClass` del resource.

## 6. ⚠️ Migración de correlación RIMS (coordinar ANTES del recompute masivo)

El outbound `eduPersonUniqueId` del resource LDAP (attr `id=436`) está anotado como
**"ancla de correlación RIMS"**. El bloque A3 **cambia el valor del ancla**:

```
ANTES:  eduPersonUniqueId = 202611481@upeu.edu.pe        (COD_UPEU@)
DESPUÉS: eduPersonUniqueId = <ID_PERSONA>@upeu.edu.pe    (opaco, inmutable)
```

Impacto: **toda la población (~37.5k)** cambia de ancla en un solo recompute. Es la jugada
canónicamente correcta (unifica el ancla de RIMS e InOut sobre el identificador más estable), pero
**RIMS debe re-mapear su correlación** antes de que el recompute masivo llegue. **No desplegar el
bloque A3 sin coordinar con RIMS.**

*Alternativa de menor riesgo, si RIMS no puede moverse ahora:* exponer ID_PERSONA en un atributo
plano propio (`scibackPersonId`, OID `.1.12` libre) para InOut, dejando `eduPersonUniqueId` intacto.
Descartada por ahora (aprobada la vía canónica), se documenta como salida.

## 7. Orden de despliegue (NADA aplicado — requiere OK de Alberto)

| # | Paso | Dónde | Nota |
|---|---|---|---|
| 1 | `06-schema-inout-person.ldif` | **.168 Y .169** | cn=config no replica. Re-verificar ordinal `{0}` de `upeuPerson` antes |
| 2 | `07-index-inout.ldif` | **.168 Y .169** | DESPUÉS de (1): slapd rechaza índice sobre atributo inexistente |
| 3 | Refresh Schema del resource `LDAP-IdentityCache-UPeU` | MidPoint | Sin esto, los `ri:sciback*` no existen y el import falla |
| 4 | Import `upeu/resources/ldap-identity-cache.xml` (3 outbounds) | MidPoint | — |
| 5 | Import `canonical/object-templates/UserTemplate-Person-Base.xml` (bloque A3) | MidPoint | ⚠️ **Coordinar RIMS antes** (§6) |
| 6 | Recompute **canario**: `uid=202611481` + 1 docente + 1 staff | MidPoint | Valida cobertura de los 3 perfiles |
| 7 | Verificar con `cn=rims-reader` | LDAP | `(\|(uid=202611481)(scibackDocumentNumber=61532826))` → 1 entry, con los 4 atributos |
| 8 | Recompute masivo de activos | MidPoint | Solo tras (6) y (7) OK |

**Verificación del canario (paso 7):**
```bash
source ~/.secrets/ldap-rims-reader.env
ldapsearch -x -LLL -H ldap://192.168.15.168:389 -D "$RIMS_READER_DN" -w "$RIMS_READER_PASS" \
  -b "$RIMS_READER_BASE_PEOPLE" '(|(uid=202611481)(scibackDocumentNumber=61532826))' \
  uid scibackDocumentNumber scibackFacultyCode scibackCampusCode eduPersonUniqueId
```
Esperado: **una sola entry**, con `scibackDocumentNumber: 61532826`, `scibackCampusCode: LIMA`,
`eduPersonUniqueId: <ID_PERSONA>@upeu.edu.pe` (y `scibackFacultyCode` presente por ser estudiante).

## 8. Artefactos versionados

| Archivo | Contenido |
|---|---|
| `upeu/ldap/rims-iga-contract/06-schema-inout-person.ldif` | 3 attrs (`.1.9`/`.1.10`/`.1.11`) + extiende `upeuPerson` |
| `upeu/ldap/rims-iga-contract/07-index-inout.ldif` | Índices `eq` (3 nuevos + `eduPersonUniqueId`) |
| `upeu/resources/ldap-identity-cache.xml` | 3 bloques `<attribute>` outbound (objectType `account/default`) |
| `canonical/object-templates/UserTemplate-Person-Base.xml` | Bloque A3 (`eduPersonUniqueId` ← `externalSystemId`) |
| `upeu/ldap/rims-iga-contract/README.md` | Orden de aplicación 6 y 7 + nota de ACL |

**Reusabilidad SciBack:** los 3 atributos usan prefijo `sciback*` y semántica agnóstica
(documento nacional primario / código de facultad / código de campus) → son bloque candidato del
blueprint `sciback-iga-blueprint`. Lo específico de UPeU (los códigos `FCS/FIA/...`, los campus
`LIMA/JULIACA/TARAPOTO`) vive en los mappings del overlay, no en el schema.
