# Los atributos de identidad de Keycloak están fosilizados — pero hoy nadie los consume

**27-ago-2026 · nota de deuda técnica para DTI**
**Estado: medido en producción. No hay incidente de acceso. No requiere acción urgente de nadie.**

## Resumen

Los atributos de identidad que Keycloak guarda (`affiliation`, `eppn`, `epuid`,
`eduperson_entitlement`) son **el sedimento de una federación LDAP que se importó y luego se
retiró**. Están congelados en mayo-junio de 2026 y difieren de lo que el IGA sabe hoy en **3.014
personas (6,5 %)**.

**Pero ninguna aplicación en uso los lee.** Eso es lo que convierte esto en deuda técnica y no en
un incidente de seguridad.

## Quién usa Keycloak de verdad

Medido sobre los eventos de autenticación de 7 días:

| Cliente | Eventos | ¿Consume los atributos fosilizados? |
|---|---|---|
| `koha-upeu` | 851 | **No** |
| `rims-provisioning` | 213 | **No** (cuenta de servicio) |
| `sgc-frappe` | 12 | **No** |
| **todos los demás** | **0** | — |

Los tres únicos clientes que sí leen `affiliation` o `eppn` —`rims-upeu`, `rims-upeu-legacy` y
`devsupeu-backend`— **no registran actividad**. RIMS es además un laboratorio en reparación, no
un sistema en servicio.

De modo que las **753 personas cuyo token dice afiliación activa siendo egresadas** no conservan
ningún acceso por esa vía: no hay quien lea ese dato. La cifra sigue siendo cierta; su
consecuencia práctica, hoy, es ninguna.

## De dónde viene el sedimento

| Comprobación | Valor |
|---|---|
| Proveedores de almacenamiento de usuarios (`UserStorageProvider`) | **ninguno** |
| Usuarios con `LDAP_ENTRY_DN` / `LDAP_ID` | **54.320** |
| Usuarios con `federation_link` | **0** — los 54.366 son cuentas locales |
| Creación de esas cuentas | **33.198 en may-2026 + 20.073 en jun-2026**; agosto: **4** |

Una importación masiva en mayo y junio, y desde entonces nada. Por eso el desfase se desvía en
**las dos direcciones** (895 `alum`→`student`, 636 `student`→`alum`, 449 `staff`→`faculty`…):
es una foto fija, no un retraso de propagación.

**La cadena MidPoint → Entra ID → Keycloak no transporta la afiliación**: el IdP `MicrosoftUPeU`
pide solo `openid profile email`, sus 4 mappers traen nombre y correo, y su `syncMode` es
**`IMPORT`** —escribe al crear la cuenta y nunca la actualiza—.

## Un detalle que engaña al leer la configuración

Conviven dos nombres de atributo y **uno no existe**:

| Atributo | Usuarios que lo tienen | Quién lo lee |
|---|---|---|
| `affiliation` | 54.320 (el real) | `rims-upeu`, `rims-upeu-legacy`, `devsupeu-backend` — todos inactivos |
| `primaryAffiliation` | **0** | scope `upeu` (12 clientes) y `academic-databases-eduperson` |

**El claim `primaryAffiliation` del scope `upeu` va vacío para todo el mundo.** Quien mire solo la
configuración concluirá que 12 clientes reciben la afiliación; ninguno la recibe.

## Lo que sí se corrigió hoy: el ePPN

Al inventariar apareció algo que sí merecía acción inmediata: **1.500 personas tenían su DNI
publicado como `eppn`** — lo que el IGA retiró del LDAP el 26 de agosto y Keycloak seguía
conservando.

**Corregido**: las 1.497 con entrada en el directorio tienen ya el mismo
`eduPersonPrincipalName` que el LDAP. Verificado entrada por entrada: **1.497 coinciden, 0
difieren**. El valor anterior sigue disponible en `eduPersonPrincipalNamePrior` del LDAP para
reconciliar.

Durante la operación hubo un error mío: entre las 15:35 y las 16:03 esas cuentas tuvieron en
Keycloak el `eppn` de otra persona. **Verificado que no llegó a nadie**: en esa franja solo hubo
16 inicios de sesión, todos de `koha-upeu`, y Koha no recibe el claim `eppn` (no tiene el scope
`academic-databases-eduperson` ni mappers propios que lo lean). Los clientes que sí lo leen
tuvieron cero actividad. Causa y lecciones en
[`2026-08-27-INCIDENTE-eppn-cruzado-keycloak.md`](2026-08-27-INCIDENTE-eppn-cruzado-keycloak.md).

## Qué hacer, y con qué prisa

**Prisa: ninguna.** No hay accesos indebidos que cortar.

**El riesgo es futuro y es real:** la próxima aplicación que se integre contra Keycloak leerá
`affiliation` y lo creerá bueno. Cuando RIMS vuelva de reparación, será la primera. Las opciones,
por orden de preferencia:

1. **Retirar los atributos fosilizados de Keycloak.** Es lo que manda el ADR-058 —*«Keycloak dice
   QUIÉN eres. El LDAP dice QUÉ eres»*—. Quien necesite saber qué es una persona lo lee del LDAP
   en vivo, como ya hace RIMS con `cn=rims-reader`.
2. **Documentarlos como caducados** mientras tanto, para que nadie los adopte por descuido.
3. **Volver a federar** es la peor: reintroduce exactamente el problema en cuanto la
   sincronización se detenga, que es lo que ya ocurrió una vez.

**Dos avisos para quien monte un bind LDAP nuevo**, porque muerden en silencio: `olcSizeLimit` es
10.000 y trunca listas **sin error visible** (solo `cn=midpoint` y `cn=rims-reader` tienen
`size=unlimited`), y **`ldap.upeu.edu.pe` no resuelve al LDAP real** — apunta a `192.168.13.160`,
que no responde ni en 389 ni en 636.

**Candidato a retirar:** `midpoint-provisioner`, con permiso `manage-users` sobre 54.000 usuarios
y sin una sola petición registrada. Superficie de ataque sin contrapartida.

## Historial de correcciones de este documento

Este documento se ha corregido **dos veces**, y las dos por la misma razón: haber dado por buena
una conclusión sin medirla hasta el final.

1. La primera versión decía «nadie aprovisiona Keycloak» y daba por expuestos a 12 clientes. La
   causa real es la federación retirada, y el claim de esos 12 va vacío.
2. La segunda presentaba 753 accesos indebidos y pedía respuesta urgente a tres equipos. **Había
   medido la configuración, no el uso.** Ninguno de esos tres clientes está en servicio.

Las cifras del desfase (3.014 / 753) no han cambiado en ninguna revisión: se midieron sobre
`affiliation`, que es el atributo que sí existe. Lo que cambió las dos veces fue la interpretación.

## Hallazgo colateral, sin relación

**4.386 `IDENTITY_PROVIDER_LOGIN_ERROR` en `indico-upeu` en 7 días**, más 3.940 sin cliente
asociado. Es el mayor volumen de eventos del realm con diferencia y merece revisarse aparte.
