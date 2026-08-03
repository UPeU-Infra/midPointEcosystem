# Estado de MidPoint PROD — medición en vivo 2026-08-03

Medido por SSH a `midpoint-prod` (192.168.15.166) y consultas directas a Postgres +
REST API. Todo lo de abajo es **observado**, no inferido del repo.

Hora de la medición: 2026-08-03 14:13 UTC (09:13 local, el host corre UTC-5; **los
timestamps de `m_task` en Postgres están en UTC**).

## Plataforma

| | |
|---|---|
| Host | `midpoint.upeu` — up 69 días, load 0.36 |
| Contenedores | `midpoint_server` = `evolveum/midpoint:4.10.2-ubuntu` (up 8 días, healthy)<br>`midpoint-midpoint_data-1` = `postgres:16-bullseye` (up 4 semanas, healthy) |
| Disco `/` | 40 G usados de 67 G (62 %) — 25 G libres |
| RAM | 15 Gi total, 5,6 Gi disponibles |
| Tamaño BD | 19 GB |

## Inventario de objetos

| Tipo | Cantidad |
|---|---|
| USER | 63.214 (54.514 activos) |
| CASE | 2.936 |
| SERVICE | 741 |
| ORG | 353 |
| ROLE | 89 |
| ARCHETYPE | 86 |
| TASK | 70 |
| RESOURCE | 12 |
| CONNECTOR | 17 |

### Users por archetype estructural

| Archetype | Users |
|---|---|
| `archetype-user-alumni` | 27.630 |
| `archetype-user-student` | 25.101 |
| `archetype-user-employee-staff` | 8.528 |
| `archetype-user-employee-faculty` | 889 |
| `archetype-user-service-account` | 1 |

Los auxiliares `AuxAff-*` coinciden 1:1 con los estructurales. Suma = 62.149 →
**~1.065 users sin archetype estructural** (incluye los ~749 sin afiliación viva ya
documentados como decisión de producto pendiente).

### Shadows por resource

| Resource | Ciclo | Vivos | Muertos |
|---|---|---|---|
| Oracle LAMB RENIEC Cache v1 | active | 128.154 | 0 |
| UPEU-EntraID-Graph | active | 75.073 | 0 |
| LDAP-IdentityCache-UPeU | active | 55.804 | 6 |
| Oracle LAMB Egresados v3 | active | 31.239 | 0 |
| Koha ILS UPeU (consolidado) | active | 28.352 | 0 |
| Oracle LAMB Estudiantes v3 | active | 25.419 | 3 |
| Koha ILS | **archived** | 19.230 | 0 |
| Oracle LAMB Trabajadores v3 | active | 7.371 | 145 |
| Oracle LAMB Grados v1 | active | 6.953 | 0 |
| LAMB-Oracle-Posiciones | active | 738 | 0 |
| Oracle LAMB Org | active | 133 | 242 |
| RIMS-SciBack | (sin ciclo) | 3 | 0 |

El resource viejo `Koha ILS` sigue **archived** con sus 19.230 shadows intactos, como
se dejó el 19-jul.

## Tasks — lo que está roto

### 🔴 `recon-koha-upeu-daily` SUSPENDED desde el 28-jul (6 días sin correr)

OID `58ef8e82-867e-432a-923e-98adcd7c57fa`, último intento 2026-07-28 12:15–12:28 UTC,
`FATAL_ERROR`. Causa raíz leída del `operationResult`:

```
Error communicating with the resource (Koha ILS UPeU (consolidado): Koha Patron,
ConnId com.identicum.connectors.KohaConnector v1.6.0): Connection failed:
ConnectionFailedException(Connection to Koha service timed out for request to
'http://192.168.12.136:8001/api/v1/patrons?_per_page=100&_page=7'. Details: Read timed out)
```

**Fue un timeout transitorio de Koha, no un bug de configuración.** Verificado hoy
desde el propio host de MidPoint: `192.168.12.136:8001` responde `HTTP 401` en 36 ms y
el ping da 0,39 ms / 0 % pérdida. El servicio está sano; la task quedó suspendida y
nadie la reanudó.

Impacto: **6 días sin reconciliación Koha** — altas, bajas y cambios de categoría no se
han propagado al Koha consolidado desde el 28-jul.

### 🔴 `recon-oracle-lamb-trabajadores-daily` SUSPENDED desde el 25-jul

OID `23b9fde4-6a5f-4c84-9370-0971fb27be73`, `PARTIAL_ERROR`. Suspensión deliberada tras
el incidente del canario que creó 2 Users duplicados auto-aprovisionados a LDAP/Koha.
El canal automático de Trabajadores sigue sin funcionar desatendido — pendiente decidir
cómo reconciliar el resto sin repetir el riesgo.

### 🟡 Tasks que sí corren, con errores parciales

| Task | Última corrida (UTC) | Resultado |
|---|---|---|
| `recon-oracle-lamb-egresados-daily` | 08-03 11:45 → 13:11 | `PARTIAL_ERROR` |
| `recon-oracle-lamb-estudiantes-daily` | 08-03 11:20 → 12:10 | `PARTIAL_ERROR` |

### 🟢 `recon-entra-id-daily` en ejecución, viva

Arrancó 02:00 local y lleva ~7 h corriendo, pero **no está colgada**: `progress` =
140.827 sobre `expectedTotal` = 75.053 y el último mensaje es de hace un minuto. No es
el patrón de cuelgue del connector msgraph.

Scanners `Validity` y `Trigger`: `SUCCESS`, corriendo cada pocos minutos.

## Drift repo ↔ PROD (roles)

Comparados los 89 roles de `m_role` contra los `<name>` de `upeu/roles/` + `canonical/`.

**En PROD y NO versionados (6 reales):**

- `AR-RIMS-Admin`
- `AR-RIMS-Cataloger`
- `AR-RIMS-Cataloger-Campus-LIMA`
- `AR-RIMS-Cataloger-Campus-JULIACA`
- `AR-RIMS-Cataloger-Campus-TARAPOTO`
- `role-svc-ai-identity-reader`

(`End user` es built-in de MidPoint, no cuenta.)

El resource `upeu/resources/rims-sciback-scim.xml` sí está versionado, pero los 5 roles
que lo consumen nunca entraron al repo. Con 3 shadows en `RIMS-SciBack`, el canal está
recién estrenado.

**En repo y NO en PROD:**

- `AR-Koha-Patron-DryRun` — archivo **untracked**, y el rol ya **no existe en PROD**.
  Es residuo local del dry-run cerrado el 19-jul; se puede borrar.
- `R-assign-koha-jubilado` — verificar si llegó a desplegarse.

## Acciones pendientes que salen de esta medición

1. **Reanudar `recon-koha-upeu-daily`** (Koha está sano). Es lo más urgente: 6 días de
   deriva acumulada entre MidPoint y Koha.
2. Decidir el destino del canal de Trabajadores (sigue suspendido desde el 25-jul).
3. Versionar los 5 roles `AR-RIMS-*` + `role-svc-ai-identity-reader`, o declararlos
   explícitamente fuera del repo.
4. Borrar `upeu/roles/application/AR-Koha-Patron-DryRun.xml` (ya no existe en PROD).
5. Revisar por qué egresados y estudiantes cierran en `PARTIAL_ERROR` todos los días.
