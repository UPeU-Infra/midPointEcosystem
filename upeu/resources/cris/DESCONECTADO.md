# Outbound MidPoint -> DSpace-CRIS: DESCONECTADO (2026-06-18/19)

## Decisión

El outbound de provisioning **MidPoint -> DSpace-CRIS está DESCONECTADO** por decisión del
usuario: MidPoint todavía no es controlable para gobernar el CRIS. El CRIS se llenará de
forma **manual vía API / JSON / XML**. La configuración NO se destruye: se preserva intacta
en el repo y se neutraliza el camino de escritura para poder reactivarla más adelante.

## Qué se neutralizó (reversible, sin borrar)

| Objeto | OID | Antes | Ahora |
|---|---|---|---|
| Resource CRIS `DSpace-CRIS UPeU` | `3f8b2d61-7c94-4a05-9e3b-6d1f8a2c5e70` | proposed | proposed (sin cambio; NO borrado) |
| AR-CRIS-Person (RoleType) | `c4e8f1a2-9b03-4d57-8e62-1a4f7c0d9e35` | active | **draft** |
| AR-CRIS-OrgUnit (RoleType) | `bdfe5f18-99f1-437b-80e6-ccffb52215ad` | active | **draft** |
| Inducement AR-CRIS-Person en BR-Investigador | `70c1606c-9d56-42ce-989f-a025c98f9c0b` (inducement id=42) | presente | **removido** (comentado en repo) |

Notas:
- AR-CRIS-Person / AR-CRIS-OrgUnit son **RoleType (Application Roles)**, no Archetypes
  (a pesar del prefijo "AR-"). En `lifecycleState=draft` su construction NO aplica al holder,
  por lo que **NO proyectan nada al CRIS** aunque queden assignments/membership residuales.
- BR-Visitante-Investigacion NO inducía AR-CRIS-Person (verificado: solo BR-Investigador lo
  inducía). No hubo que tocar BR-Visitante-Investigacion.
- El conector, los scripts ScriptedREST (`scripts/`), el resource XML completo y los roles
  quedan INTACTOS en el repo.

## Verificación de la desconexión

Recompute scoped del investigador Itler (`fedf00f8-9713-4479-935b-53f7cd975095`,
código 200210072) tras los cambios:
- **NO creó ningún shadow CRIS nuevo** (linkRef estable en 10; los únicos shadows CRIS del
  foco son 3 residuos `dead=true` / `exists=false` de pruebas previas, no tocados aquí).
- **NO hubo llamada outbound de escritura** (add/modify) al conector CRIS.
- Búsqueda indexada: 0 focos con membership/assignment efectivo a AR-CRIS-Person; 0 shadows
  vivos en el resource CRIS.

## Inbound Oracle: NO TOCADOS (solo leen Oracle -> MidPoint, no escriben al CRIS)

| Resource | OID | Estado |
|---|---|---|
| Oracle LAMB Investigacion DGI (Org) | `5a3d7e92-4c61-4b8f-9a02-7e1c3d6b2f84` | active |
| Oracle LAMB Investigadores Afiliacion | `8c4f1a36-9d27-4e58-bb03-1f6a2c7d3e95` | active |

## Items ya en el CRIS: NO TOCADOS

Los ~405 items Person y los OrgUnit que ya están cargados en el CRIS **NO se tocan**.
Su destino es decisión separada del usuario.

## Cómo reactivar (cuando MidPoint vuelva a gobernar el CRIS)

1. AR-CRIS-Person (`c4e8f1a2`) y AR-CRIS-OrgUnit (`bdfe5f18`): `lifecycleState` draft -> active.
2. BR-Investigador (`70c1606c`): restaurar el inducement a AR-CRIS-Person (bloque comentado en
   `upeu/roles/business/BR-Investigador.xml`).
3. Resource CRIS (`3f8b2d61`): proposed -> active cuando se valide el piloto.
4. Recompute de la población investigadora para materializar la proyección.

Antes de reactivar masivamente: revisar el driver serializado endurecido post-OOM
(`upeu/tasks/fase5-cris/`) por límites de workers/lotes y gates de heap.
