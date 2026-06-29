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

Password de `cn=rims-reader`: `~/.secrets/ldap-rims-reader.env` (NO se versiona).
