# LDAP cn=config — cambios RIMS←IGA (Fases 1-4)

Cambios aplicados manualmente en OpenLDAP (.168 y .169) porque `cn=config` **NO está
replicado** (solo `olcDatabase={1}mdb`/`dc=upeu,dc=edu,dc=pe` lo está). Aplicar SIEMPRE en
ambos nodos. Los datos (`ou=org`, `cn=rims-reader`) sí replican.

Orden de aplicación:
1. `01-schema-isni.ldif`        — attr `isni` + extiende `upeuPerson` (Fase 2, P5)
2. `02-schema-scibackorgunit.ldif` — objectClass `scibackOrgUnit` + 5 attrs + `c` (Fase 3)
3. `03-ou-org-base.ldif`        — entry base `ou=org` (Fase 3) — solo en un nodo (replica)
4. `04-acl-mdb.ldif`            — ACL completa olcDatabase={1}mdb (Fase 3 ou=org + Fase 4 rims-reader)
5. `05-rims-reader-entry.ldif.tmpl` — entry `cn=rims-reader` (Fase 4) — userPassword via slappasswd
6. `06-schema-inout-person.ldif` — attrs `scibackDocumentNumber`/`scibackFacultyCode`/`scibackCampusCode` + extiende `upeuPerson` (contrato InOut←IGA, D-11.bis)
7. `07-index-inout.ldif`        — índices `eq` de los 3 attrs nuevos + `eduPersonUniqueId` (aplicar DESPUÉS de 06)

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
