# La afiliación que viaja en el token es una foto de mayo-junio de 2026

**27-ago-2026 · para DTI y los equipos de las aplicaciones federadas**
**Estado: medido en producción. Antes de actuar hace falta una respuesta de tres equipos.**

## Resumen

El atributo de afiliación que Keycloak entrega en el token **no lo mantiene nadie**. Es el
sedimento de una **federación LDAP que se importó y luego se retiró**: los 54.366 usuarios del
realm `upeu` son hoy **cuentas locales** (`federation_link = NULL`) que conservan los atributos
tal y como estaban el día de la importación.

Comparado con lo que el IGA sabe hoy, **difiere para 3.014 personas (6,5 %)**. En **753** el
token concede una afiliación activa a alguien que el IGA ya tiene como egresado.

## La cadena que se suele suponer, y dónde se corta

La suposición razonable es: **MidPoint → Entra ID → Keycloak**. MidPoint sí aprovisiona Entra
ID, y Keycloak sí usa Entra ID como proveedor de identidad. Pero **ese camino no transporta la
afiliación**, por dos motivos medidos:

| Comprobación | Valor en producción |
|---|---|
| Scopes que Keycloak pide a Entra ID (`MicrosoftUPeU`) | `openid profile email` — nada más |
| Mappers de ese IdP | 4: `username`, `given_name`, `family_name`, `email` |
| `syncMode` del IdP | **`IMPORT`** — escribe solo al **crear** la cuenta, nunca la actualiza |

Aunque Entra ID tuviera la afiliación al día, Keycloak **no la pide y no la mapearía**. Y con
`syncMode = IMPORT`, ni siquiera refresca el nombre o el correo en logins posteriores.

## De dónde salen entonces los atributos

De una federación LDAP que **ya no existe**:

| Comprobación | Valor |
|---|---|
| Proveedores de almacenamiento de usuarios (`UserStorageProvider`) | **ninguno** — lista vacía |
| Usuarios con `LDAP_ENTRY_DN` / `LDAP_ID` | **54.320** |
| Usuarios con `federation_link` | **0** — los 54.366 son cuentas locales |
| Creación de esas cuentas | **33.198 en mayo-2026 + 20.073 en junio-2026** |
| Creadas en agosto-2026 | **4** |

El patrón es inequívoco: una importación masiva en mayo y junio, y desde entonces el goteo se
detiene. Los atributos quedaron **fosilizados en ese instante**. Por eso el desfase se desvía en
las dos direcciones — quien se graduó después de la foto sigue apareciendo como estudiante, y
quien fue contratado después conserva su rol anterior:

```
895  el token dice alum     y el IGA dice student
636  el token dice student  y el IGA dice alum
449  el token dice staff    y el IGA dice faculty
435  el token dice alum     y el IGA dice faculty
286  el token dice alum     y el IGA dice staff
 82  el token dice staff    y el IGA dice student
 69  el token dice faculty  y el IGA dice alum
```

Nadie escribe esos atributos hoy: las **23 escrituras** sobre usuarios registradas desde el
5-mayo son **todas de `admin-cli`** (consola de administración). El cliente
`midpoint-provisioner`, que tiene permiso `manage-users`, **no ha escrito ninguna**.

## Quién está expuesto de verdad — son 3 clientes, no 13

Aquí hay un matiz que cambia el tamaño del problema. Conviven **dos nombres de atributo**, y uno
de los dos **no existe**:

| Atributo | Usuarios que lo tienen | Quién lo lee |
|---|---|---|
| `affiliation` | **54.320** (el real, congelado) | `rims-upeu`, `rims-upeu-legacy`, `devsupeu-backend` |
| `primaryAffiliation` | **0** | scope `upeu` (12 clientes) y scope `academic-databases-eduperson` |

**El claim `primaryAffiliation` del scope `upeu` va vacío para todo el mundo**, porque apunta a
un atributo que ningún usuario tiene. Los 12 clientes que llevan ese scope —`koha-upeu`,
`indico-upeu`, `librechat`, `onyx`, `guia-node`, `mayan-sgc`, `sgc-frappe`, `cloudflare-access`,
`dgi-ingest-connector`, `rims-provisioning`, `devsupeu-backend`, `midpoint-provisioner`— reciben
un claim inexistente. Si alguno de ellos **autorizara** con él, hoy estaría fallando de forma
visible; que no lo haga sugiere que no lo usa.

**El riesgo real se concentra en los tres que leen `affiliation`: RIMS (dos clientes) y
`devsupeu-backend`.**

## Lo que se pide — una sola pregunta, a tres equipos

> **¿Tu aplicación toma decisiones de acceso con el claim `affiliation`, o solo lo muestra o
> registra?**

Va a los responsables de **RIMS** y **devsupeu-backend**. De la respuesta depende si las 753
personas con afiliación activa caducada son un incidente de acceso o una molestia cosmética.

## Qué hacer después, según la respuesta

**Si autorizan con el claim:** deben leer la afiliación del **LDAP en vivo**, como manda el
ADR-058 —*«Keycloak dice QUIÉN eres. El LDAP dice QUÉ eres»*—. RIMS ya tiene su bind
`cn=rims-reader`. **Dos avisos que muerden en silencio:** `olcSizeLimit` es 10.000 y trunca
listas **sin error visible** (solo `cn=midpoint` y `cn=rims-reader` tienen `size=unlimited`), y
**`ldap.upeu.edu.pe` no resuelve al LDAP real** — apunta a `192.168.13.160`, que no responde ni
en 389 ni en 636; hay que conectar por IP.

**En cualquier caso, el sedimento hay que limpiarlo.** Dejar 54.320 cuentas con una afiliación
de hace tres meses es una trampa para la próxima aplicación que se integre y la crea buena. Las
opciones son retirar el atributo, o volver a federar el LDAP de forma sostenida — pero lo segundo
es justo lo que el ADR-058 desaconseja, y reintroduce el problema en cuanto la sincronización se
pare, que es exactamente lo que ya pasó una vez.

**No se propone** resucitar `midpoint-provisioner`: un cliente con permiso para modificar 54.000
usuarios que nadie usa es superficie de ataque sin contrapartida.

## Aparte y ya hecho: el `eppn` de 1.497 personas cambió hoy

Al inventariar los atributos apareció algo más urgente que la afiliación: **1.500 personas tenían
su DNI publicado como `eppn`** — justo lo que el IGA retiró del LDAP el 26 de agosto y que
Keycloak seguía sirviendo, porque su copia es de mayo-junio.

**Ya está corregido**: las 1.497 con entrada en el directorio tienen ahora el mismo
`eduPersonPrincipalName` que el LDAP. Verificado entrada por entrada: 1.497 coinciden, 0 difieren.

**Lo que esto significa para quien vincule por `eppn`:** el identificador de esas personas cambió
—en el LDAP en agosto, en Keycloak hoy—. Para reconciliar, el LDAP conserva el valor anterior en
**`eduPersonPrincipalNamePrior`**, que existe precisamente para esto (eduPerson 202208 exige que
el ePPN no sea reasignable sin dejar rastro).

### Y una franja de esta tarde que conviene que sepáis

Entre las **15:35 y las 16:03** aproximadamente, esas 1.497 cuentas tuvieron en Keycloak **el
`eppn` de otra persona**. Fue un error mío: el volcado que extraje del LDAP salió desplazado una
posición porque el `awk` asumía que `uid` venía antes que el ePPN en el LDIF, y en OpenLDAP viene
después. Lo detecté en la verificación final y lo reparé el mismo día.

**Si en esa franja alguien inició sesión, vuestra aplicación pudo recibir un identificador que no
era el suyo.** Merece la pena revisar registros creados o modificados en esa ventana antes de
darlos por buenos. El estado actual es correcto y está verificado contra el directorio.

Detalle completo, causa y las reglas que salen de ahí:
[`2026-08-27-INCIDENTE-eppn-cruzado-keycloak.md`](2026-08-27-INCIDENTE-eppn-cruzado-keycloak.md).

## Corrección respecto a la versión anterior de este documento

La primera versión atribuía el desfase a que «nadie aprovisiona Keycloak» y presentaba a los 12
clientes del scope `upeu` como expuestos. **El efecto era correcto, la causa y el alcance no.**
La causa es una federación LDAP importada y retirada; el alcance real son 3 clientes, porque el
claim del scope `upeu` está vacío. Las cifras del desfase no cambian: se midieron sobre
`affiliation`, que es el atributo que sí existe.

## Hallazgo colateral, sin relación con lo anterior

En 7 días de eventos hay **4.386 `IDENTITY_PROVIDER_LOGIN_ERROR` en `indico-upeu`** y 3.940 más
sin cliente asociado. Es un volumen alto que merece revisarse por separado.
