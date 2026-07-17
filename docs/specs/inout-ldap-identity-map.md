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

---

# 9. Rama `ou=alumni` — EGRESADOS (aplicado a PROD el 2026-07-16)

> **Estado:** ✅ **APLICADO Y OPERATIVO**. A diferencia de §1-§8, esta sección describe
> configuración viva en PROD.

**Decisión de negocio:** los egresados **SÍ son público real del CRAI** (un egresado puede usar
cualquier CRAI). Pero **NO vuelven a `ou=people`**: `BR-Egresado.xml` removió `AR-LDAP-Person` el
2026-05-26 por least privilege — `ou=people` es el Identity Cache de autenticación **ACTIVA**
(WiFi 802.1X, Keycloak User Federation) y un egresado no tiene contrato ni matrícula vigente.

La rama `ou=alumni` resuelve la tensión: **da identificación sin dar autenticación.**

## 9.1 Lo que cambia para InOut: SOLO el `BASE_DN`

Mismo `LdapProvider`, mismo bind `cn=rims-reader`, mismo `identity_map`. **Cero código nuevo.**

```python
BASE_ALUMNI  = 'ou=alumni,dc=upeu,dc=edu,dc=pe'    # <-- lo único distinto

# El mismo search_filter de §2 sirve para resolver el scan:
search_filter = '(|(uid={v})(scibackDocumentNumber={v}))'

# Predicado de "es egresado" (equivalente de (eduPersonAffiliation=member) en ou=people):
alumni_filter = '(&(objectClass=inetOrgPerson)(eduPersonAffiliation=alum))'
```

**`member` NO aplica aquí, y no es un descuido:** eduPerson 202208 — `member` es afiliación
derivada de faculty/student/staff/employee; **`alum` NO implica `member`** (un egresado no es
miembro de la institución). Buscar `member` en esta rama devuelve 0.

⚠️ **Filtrar por `eduPersonAffiliation`, NUNCA por `eduPersonPrimaryAffiliation`.**
`eduPersonAffiliation` está indexado `eq` (ver `08-index-affiliation.ldif`);
`eduPersonPrimaryAffiliation` **no lo está** → usarlo degrada a full-scan de ~26.8k entries en
silencio.

## 9.2 Atributos disponibles (medidos en PROD sobre los 26.801 alumni activos)

| Rol en InOut | Atributo | Cobertura **medida** | Nota |
|---|---|---|---|
| **Carné (COD_UPEU)** | `uid` | **100%** | `$focus/name` |
| **DNI plano** | `scibackDocumentNumber` | **100%** (1 sin dato) | mismo extractor que `ou=people` |
| **Nombre** | `cn` / `sn` / `givenName` | **100%** | — |
| **Facultad de egreso** | `scibackFacultyCode` | **99,82%** (26.752/26.801) | ver 9.3 |
| Campus | `scibackCampusCode` | **NO SE MAPEA** | no es dimensión fiable del egresado |
| Género | — | **NO EXISTE** (11,37%) | ver 9.4 |

**Atributos deliberadamente ausentes** (verificado en PROD: 0 entries con cada uno):
`userPassword`, `memberOf`, `mail`. **La rama no es autenticable por construcción**, no por
configuración de Keycloak. Si alguien mapeara `userPassword` aquí, la regla ACL `{1}`
(`by anonymous auth`, que se evalúa ANTES de la `{4}`) la volvería autenticable pese a la `{4}`.

## 9.3 Facultad: `organizationalUnit`, NO `facultyName`

**Trampa real.** El `scibackFacultyCode` de `ou=people` deriva de
`extension/sciback:facultyName` — que en alumni da **0%**. La facultad de egreso vive en
**`$focus/organizationalUnit`** (`egresados.xml:356`, `NOM_FACULTAD → organizationalUnit`), con
**100%** de cobertura. El mapping del intent `alumni` usa esa fuente, y **no se puede copiar el
script de `ou=people` tal cual**: `organizationalUnit` es **PolyString multivalor**, no string plano.

Distribución medida (2026-07-16):

| `organizationalUnit` | → código | N |
|---|---|---|
| Facultad de Ciencias Empresariales | `FCE` | 8.139 |
| Escuela General de Posgrado | `EPG` | 6.100 |
| Facultad de Ingenier**í**a y Arquitectura | `FIA` | 4.497 |
| Facultad de Ciencias de la Salud | `FCS` | 4.476 |
| Facultad de Ciencias Humanas y Educaci**ó**n | `FACIHED` | 2.302 |
| Facultad de Teolog**í**a | `FACTEO` | 1.238 |
| *Beca 18 · Capacitacion Continua · Centro de Idiomas · Ciencias Contables y Administrativas · DGI - Cursos y Capacitaciones* | *(sin código)* | 49 |

⚠️ **Las tildes son parte de la clave.** El switch hace match **exacto**. Normalizar
`Ingeniería`/`Educación`/`Teología` a ASCII deja sin código a **8.037 personas (30%)**. Se detectó
al escribir el mapping y se validó explícitamente en el canary.

Los 49 sin mapeo → atributo **ausente** (`null`), **no `UNKNOWN`**: mejor sin valor que con una
facultad inventada que contamine el reporte de aforo. *`Ciencias Contables y Administrativas` (8)
parece FCE legacy — decisión abierta, no se asumió.*

## 9.4 Género: NO se promete

Cobertura medida **11,37%** (3.048/26.801) y **sin IIA**: `egresados.xml` no tiene inbound de sexo
(verificado: `grep -i "sexo|gender"` → 0 resultados). **No se mapea.** InOut lo muestra vacío.
Mapear un atributo con 11% de cobertura y sin fuente autoritativa es peor que no tenerlo: invita a
construir reportes sobre un dato que no existe.

## 9.5 Seguridad: por qué Keycloak tiene `none` EXPLÍCITO

ACL regla **`{4}`**, insertada **ANTES** de la catch-all `{5}` (`04-acl-mdb.ldif`). Sin ella,
`ou=alumni` caería en la `{5}`, que da `read` a `cn=keycloak` → los ~26.800 egresados entrarían en
su User Federation → **se violaría el propio `BR-Egresado` que esta rama existe para respetar**.

⚠️ **El DN de Keycloak es `cn=keycloak,dc=upeu,dc=edu,dc=pe`** — NO cuelga de `ou=services`, a
diferencia de `cn=midpoint` y `cn=rims-reader`. `~/.secrets/ldap-upeu.env` tenía un DN
**inexistente** (`cn=keycloak,ou=services,...`); escribir la denegación desde ese valor habría
producido una cláusula que no matchea a nadie. **Verificar DNs contra el directorio vivo, nunca
desde el `.env`.** (El `.env` se corrigió el 2026-07-16.)

Verificación funcional ejecutada en **ambos nodos**:

| Bind | Rama | Resultado |
|---|---|---|
| `cn=keycloak` | `ou=alumni` | ✅ `No such object (32)` — la rama le es invisible |
| `cn=keycloak` | `ou=people` | ✅ sigue leyendo (no se rompió la federación) |
| `cn=rims-reader` | `ou=alumni` | ✅ lee |

## 9.6 ⚠️ DEUDA CONSCIENTE — esta rama nace SIN DEPROVISIONING

> **Aceptada explícitamente por Alberto el 2026-07-16 para desbloquear a InOut.**
> **NO ES UN OLVIDO.** Quien lea esto en 6 meses debe saber que fue una decisión, no un descuido.

**Mecánica del gap.** Cuando un egresado deja de ser activo, la `condition` de `AR-LDAP-Alumni`
pasa a `false` → MidPoint quiere borrar el shadow → el resource tiene
`<cap:delete><enabled>false` (**blindaje anti-delete, a nivel de RESOURCE**: MidPoint no soporta
capabilities por objectType, así que no se puede habilitar solo para este intent sin exponer
`ou=people`) → **el borrado no ocurre**. Y **no hay `<activation>` ni `<existence>` mapping** en
este resource → tampoco hay atributo que se marque como inactivo. **La entry se congela** con sus
últimos valores, incluido `eduPersonAffiliation=alum`.

**Consecuencia operativa:** *"presencia en `ou=alumni`" == "egresado activo"* **solo el día del
build**. Después deriva. Drift estimado hoy: **~723 (2,6%** de 27.524 BR-Egresado totales**)**, y
crece lento.

**Es exactamente el mecanismo que produjo los 20.012 huérfanos de `ou=people`** — egresados a los
que se removió `AR-LDAP-Person` el 2026-05-26 y cuya entry nunca se pudo borrar (verificado
2026-07-16: muestra aleatoria de 300 → **300/300** tienen `BR-Egresado` activo, y **97,7% ya no
tienen shadow** en MidPoint: son invisibles para el IGA). **Se está sembrando la misma semilla, a
sabiendas y acotada.**

**Se cierra junto con el leaver gap, no antes y no por separado:** es el mismo problema — blindaje
anti-delete sin contrapartida de archivado (ISO 24760: `archived`, no `destroyed`). Ya lo piden
tres frentes. Opciones sobre la mesa (ninguna decidida): mapear `schacExpiryDate`, o dejar la
construction siempre activa y derivar un status de `lifecycleState` para que InOut lo filtre.

**Nota aparte — los 20.012 huérfanos SÍ son visibles a Keycloak** (están en `ou=people`, donde
`cn=keycloak` tiene `read`). No pueden autenticarse por bind (`userPassword` = **0 entries en todo
el directorio**), pero sí se importan en su User Federation. **Es preexistente a esta rama y se
levanta como tema aparte.** No se tocó.

## 9.7 Artefactos de la rama alumni

| Archivo | Contenido |
|---|---|
| `upeu/ldap/rims-iga-contract/04-acl-mdb.ldif` | ACL con la regla `{4}` (`ou=alumni`, keycloak `none`) + catch-all renumerada a `{5}` |
| `upeu/ldap/rims-iga-contract/08-index-affiliation.ldif` | `eduPersonAffiliation eq` (cierre de drift; ya estaba en PROD) |
| `upeu/ldap/rims-iga-contract/09-ou-alumni-base.ldif` | Entry base `ou=alumni` (**dato → replica; aplicar en UN nodo**) |
| `upeu/ldap/rims-iga-contract/10-limits-rims-reader.ldif` | `size=unlimited` para `rims-reader` — **versionado, NO aplicado** (espera ventana de InOut) |
| `upeu/ldap/rims-iga-contract/11-fix-frontend-sizelimit-169.ldif` | `olcSizeLimit` 500→10000 en `.169` (**aplicado**) |
| `upeu/roles/application/AR-LDAP-Alumni.xml` | AR nuevo (OID `d87d28d4-5f1d-4917-96e3-393b788f6d12`), guard = complemento exacto del de `AR-LDAP-Person` |
| `upeu/roles/business/BR-Egresado.xml` | Inducement a `AR-LDAP-Alumni` |
| `upeu/resources/ldap-identity-cache.xml` | objectType `account/alumni` + `delineation` en ambos intents |

⚠️ **`ldap-identity-cache.xml` SOLO por PATCH, NUNCA PUT.** Su `<schema>` cacheado está
desactualizado respecto a PROD → un PUT dejó el resource `broken` (commits `670b312`/`8ab4dc9`).
El intent `alumni` y los `delineation` se aplicaron con `itemDelta` **`add`**, que no toca el
`<schema>` ni el objectType existente.

## 9.8 Límite de tamaño — leer antes del primer sync masivo

`cn=rims-reader` **no tiene `olcLimits` propio** → hereda el del frontend = **10.000**. La rama
tiene ~26.800 entries → **un enumerado completo se corta en 10.000 con resultados parciales**, y
LDAP lo señala con `sizeLimitExceeded` que un cliente distraído no mira. **Antes del primer sync
masivo de InOut hay que aplicar `10-limits-rims-reader.ldif`.** Para el uso normal (resolver un
scan → 1 entry) no aplica.
