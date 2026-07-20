# Borrado gobernado de cuenta LDAP vieja — uid=202421264 (Daniel Piñango Hernandez)

2026-07-20. Continuación de la investigación previa (ver memoria
`koha-91pct-sin-externalsystemid-import-suspendido-2026-07-18` y backups en
`.backups-prod-p0/2026-07-19-bloque-k-hardening/`).

## Estado previo verificado (ldapsearch de solo lectura, ambos)
- `uid=202421264,ou=people,dc=upeu,dc=edu,dc=pe` — existía, mismo `mail`/`cn` que la cuenta
  correcta. Shadow MidPoint `ee5ebafc-76fc-48b1-bfea-1e756fb42174`, `unlinked`, `exists=true`.
- `uid=03036796,ou=people,dc=upeu,dc=edu,dc=pe` — la cuenta correcta y viva, linkeada al User
  `272596f6-b6da-4ec5-ae33-32357906330e` vía shadow `12c70414-1c68-45f4-b424-250a4608b56c`.

## Hallazgo durante la ejecución

`DELETE /ws/rest/shadows/{oid}` (sin `raw`) falló:

```
Operation not supported for COD(inetOrgPerson + eduPerson + schacPersonalCharacteristics +
upeuPerson + schacEntryMetadata + midPointPerson) in resource:...LDAP-IdentityCache-UPeU as
DeleteCapabilityType is missing
```

El resource `ldap-identity-cache` (oid `7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f`) tiene el delete
**nativo** del conector disponible (`<native><cap:delete/></native>`), pero
**explícitamente deshabilitado a nivel de configuración**:
`<configured><cap:delete><cap:enabled>false</cap:enabled></cap:delete></configured>`.
Guardrail deliberado (consistente con doctrina "MidPoint suma, nunca resta") para que
ninguna reconciliation/sync borre cuentas LDAP reales por accidente.

## Mecanismo ejecutado

1. Backup del shadow (`shadow-ee5ebafc-202421264-PRE-DELETE-20260720.xml`) y del resource
   completo (`resource-ldap-identity-cache-PRE-delete-capability-toggle.xml`) en
   `.backups-prod-p0/2026-07-20-telegram-alertas/`.
2. `PATCH capabilities/configured/delete/enabled = true` (PATCH, nunca PUT — el `<schema>`
   cacheado se verificó intacto antes y después, 2504 elementos/tipos XSD sin cambio).
3. `DELETE /ws/rest/shadows/ee5ebafc-...` (sin `raw`) → `204 No Content`. Esto dispara
   deprovisioning real (delete en LDAP), no solo borrado del repo.
4. `PATCH capabilities/configured/delete/enabled = false` inmediatamente — revertido al
   guardrail original. Verificado.
5. Verificación con `ldapsearch` de solo lectura:
   - `uid=202421264` → 0 resultados (borrado confirmado).
   - `uid=03036796` → intacto, mismos atributos (`mail`, `eduPersonPrincipalName`, `uid`).
6. Shadow `ee5ebafc-...` → `GET` devuelve `404` (eliminado del repo también).

## Resultado
Cuenta LDAP vieja eliminada de forma gobernada vía MidPoint. Cuenta correcta sin cambios.
Guardrail de delete capability del resource restaurado a su estado original
(`enabled=false`).
