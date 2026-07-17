# LDAP cn=config — cambios RIMS←IGA (Fases 1-4)

Cambios aplicados manualmente en OpenLDAP (.168 y .169) porque `cn=config` **NO está
replicado** (solo `olcDatabase={1}mdb`/`dc=upeu,dc=edu,dc=pe` lo está). Aplicar SIEMPRE en
ambos nodos. Los datos (`ou=org`, `cn=rims-reader`) sí replican.

Orden de aplicación:
1. `01-schema-isni.ldif`        — attr `isni` + extiende `upeuPerson` (Fase 2, P5)
2. `02-schema-scibackorgunit.ldif` — objectClass `scibackOrgUnit` + 5 attrs + `c` (Fase 3)
3. `03-ou-org-base.ldif`        — entry base `ou=org` (Fase 3) — solo en un nodo (replica)
4. `04-acl-mdb.ldif`            — ACL completa olcDatabase={1}mdb (Fase 3 ou=org + Fase 4 rims-reader + **regla `{4}` de `ou=alumni`**)
5. `05-rims-reader-entry.ldif.tmpl` — entry `cn=rims-reader` (Fase 4) — userPassword via slappasswd
6. `06-schema-inout-person.ldif` — attrs `scibackDocumentNumber`/`scibackFacultyCode`/`scibackCampusCode` + extiende `upeuPerson` (contrato InOut←IGA, D-11.bis)
7. `07-index-inout.ldif`        — índices `eq` de los 3 attrs nuevos + `eduPersonUniqueId` (aplicar DESPUÉS de 06)
8. `08-index-affiliation.ldif`  — índice `eq` de `eduPersonAffiliation` (**cierre de drift**: ya estaba en PROD sin versionar). Es el índice de los DOS filtros de InOut: `member` (ou=people) y `alum` (ou=alumni)
9. `09-ou-alumni-base.ldif`     — entry base `ou=alumni` — **dato → solo en UN nodo** (replica)
10. `10-limits-rims-reader.ldif` — `size=unlimited` para `rims-reader`. **⚠️ VERSIONADO, NO APLICADO** — espera la ventana de sync que anunciará InOut
11. `11-fix-frontend-sizelimit-169.ldif` — `olcSizeLimit` 500→10000 en `.169` (**aplicado 2026-07-16**; solo en .169)

## ⚠️ Cuál va en UN nodo y cuál en LOS DOS (error fácil de cometer)

| Tipo | Ficheros | Dónde |
|---|---|---|
| **`cn=config`** (schema, ACL, índices, límites) | 01, 02, 04, 06, 07, 08, 10, 11 | **AMBOS nodos** — `cn=config` NO replica |
| **Datos** (entries del árbol `dc=upeu,dc=edu,dc=pe`) | 03, 05, 09 | **UN nodo** — syncrepl los propaga; aplicarlos en los dos crea conflicto |

## Rama `ou=alumni` (2026-07-16) — aplicada

Directorio de **CONSULTA** de egresados para el aforo CRAI de InOut. **No es rama de
autenticación**: sin `userPassword`, sin `memberOf`, sin `mail`, y `cn=keycloak` con `none`
**explícito** en la ACL regla `{4}` (que va **ANTES** de la catch-all `{5}`). Estado tras el build:
**26.757 entries**, 100% carné/DNI/nombre, 99,82% facultad. Contrato completo y la **deuda de
deprovisioning** documentada en
[`docs/specs/inout-ldap-identity-map.md`](../../../docs/specs/inout-ldap-identity-map.md) §9.

⚠️ **El DN de Keycloak es `cn=keycloak,dc=upeu,dc=edu,dc=pe`** — NO cuelga de `ou=services`, a
diferencia de `cn=midpoint` y `cn=rims-reader`. `~/.secrets/ldap-upeu.env` tenía un DN inexistente;
**verificar DNs contra el directorio vivo, nunca desde el `.env`** (ver cabecera de `04`).

## Límite de tamaño — estado real (verificado 2026-07-16)

`cn=rims-reader` **no tiene `olcLimits` propio** → hereda el del frontend (**10.000** tras aplicar
el `11`; antes: 10.000 en `.168` y **500** en `.169`). Con `ou=people`=47.527 y `ou=alumni`=26.757,
**cualquier enumerado completo se corta en 10.000 con resultados parciales** (`sizeLimitExceeded`,
que un cliente distraído no mira). Para resolver un scan (1 entry) no aplica. **Antes del primer
sync masivo de InOut hay que aplicar el `10`.** Nota: `cn=keycloak` está igual de capado (se
verificó que solo ve 10.000 de las 47.527 de `ou=people`) — preexistente, se reporta aparte.

Password de `cn=rims-reader`: `~/.secrets/ldap-rims-reader.env` (NO se versiona).

## Contrato InOut←IGA (06 + 07)

InOut (aforo CRAI) es un **segundo consumidor** del mismo identity cache LDAP, y reutiliza
la cuenta `cn=rims-reader`. **No requiere cambio de ACL**: la regla `{2}` de `04-acl-mdb.ldif`
ya otorga `read` sobre todo el subtree `ou=people` sin restricción por atributo (verificado en
PROD 2026-07-16: `rims-reader` ya lee `schacPersonalUniqueID`, que contiene el DNI en URN → el
DNI plano al mismo lector no añade exposición nueva).

Contrato de atributos y el `identity_map` que consume InOut: [`docs/specs/inout-ldap-identity-map.md`](../../../docs/specs/inout-ldap-identity-map.md).

Estado PROD verificado (2026-07-16, solo lectura) que condiciona estos dos ldif:
- `cn={12}upeu,cn=schema,cn=config`; `upeuPerson` = `olcObjectClasses {0}` → de ahí el `delete/add {0}`.
- `olcAttributeTypes {0}..{7}` = OIDs `.1.1`..`.1.8` → siguientes libres `.1.9/.1.10/.1.11`.
- `uid eq` **ya existe** en ambos nodos → el carné COD_UPEU no necesita índice nuevo.
