# Runbook: Upgrade MidPoint Docker Compose

## Versiones validadas

- 4.9.5 → 4.10.2 (fecha: 2026-05-15) — completado con éxito en PROD UPeU

## Pre-requisitos

- La versión origen debe ser la última release del branch anterior (4.9.5 es la última 4.9.x).
- Verificar espacio en disco: mínimo 5 GB libres para descargar las nuevas imágenes sin eliminar las antiguas todavía.
- Backup del archivo `/opt/midpoint/.env` antes de modificarlo.
- Tener los secretos REST disponibles para smoke-tests post-upgrade.

## Procedimiento probado

### Fase 0 — Pre-verificación (sin downtime)

1. Cargar credenciales y verificar expression profiles en system config:
   ```bash
   source ~/.secrets/midpoint-upeu.env
   curl -s -L -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
     "$MIDPOINT_URL_PUBLIC/ws/rest/systemConfigurations/00000000-0000-0000-0000-000000000001" \
     -H "Accept: application/xml" | grep -E "script-safe|script-limited|expressionProfile|permissive|prohibitive"
   ```

2. Snapshot de OIDs de conectores activos (guardar para comparar post-upgrade):
   ```bash
   curl -s -L -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
     "$MIDPOINT_URL_PUBLIC/ws/rest/connectors" -H "Accept: application/xml" | \
     grep -oP '(?<=<name>)[^<]+|(?<=oid=")[^"]+' | paste - -
   ```

3. Backup del `.env` y actualizar la versión:
   ```bash
   sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
     "cp /opt/midpoint/.env /opt/midpoint/.env.backup-$(date +%Y%m%d) && \
      sed -i 's/MP_VER=4.9.5/MP_VER=4.10.2/' /opt/midpoint/.env"
   ```

4. Pull de las nuevas imágenes sin downtime (tardan ~5-8 min según ancho de banda):
   ```bash
   sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
     "cd /opt/midpoint && docker compose pull"
   ```

### Fase 1 — Upgrade del schema de base de datos (CRITICO)

**ADVERTENCIA:** El `data_init` del compose hace `CREATE` (no `UPGRADE`). En upgrades desde una
versión existente, el script `postgres.sql` falla con "type already exists" y el init concluye
con "Repository init is not needed". El schema NO se actualiza automáticamente.

Es necesario ejecutar el upgrade de schema manualmente ANTES de arrancar midpoint_server:

```bash
# Upgrade schema REPOSITORY (v50 → v51 en la transición 4.9→4.10)
sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
  "docker run --rm --network midpoint_net --workdir /opt/midpoint \
   -e MP_SET_midpoint_repository_jdbcUsername=midpoint \
   -e MP_SET_midpoint_repository_jdbcPassword=<DB_PASSWORD> \
   -e MP_SET_midpoint_repository_jdbcUrl=jdbc:postgresql://midpoint_data:5432/midpoint \
   -e MP_SET_midpoint_repository_database=postgresql \
   -e MP_INIT_CFG=/opt/midpoint/var \
   -v midpoint_home:/opt/midpoint/var \
   evolveum/midpoint:4.10.2-alpine \
   bash -c 'bin/midpoint.sh init-native && bin/ninja.sh run-sql --upgrade --mode REPOSITORY'"

# Upgrade schema AUDIT
sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
  "docker run --rm --network midpoint_net --workdir /opt/midpoint \
   -e MP_SET_midpoint_repository_jdbcUsername=midpoint \
   -e MP_SET_midpoint_repository_jdbcPassword=<DB_PASSWORD> \
   -e MP_SET_midpoint_repository_jdbcUrl=jdbc:postgresql://midpoint_data:5432/midpoint \
   -e MP_SET_midpoint_repository_database=postgresql \
   -e MP_INIT_CFG=/opt/midpoint/var \
   -v midpoint_home:/opt/midpoint/var \
   evolveum/midpoint:4.10.2-alpine \
   bash -c 'bin/midpoint.sh init-native && bin/ninja.sh run-sql --upgrade --mode AUDIT'"
```

Ambos comandos deben terminar con: `[INFO] Scripts executed successfully.`

### Fase 2 — Downtime y arranque

5. Stop + start con nueva versión:
   ```bash
   sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
     "cd /opt/midpoint && docker compose down && docker compose up -d"
   ```

6. Esperar healthcheck (3-5 min):
   ```bash
   sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
     "until docker inspect midpoint_server --format '{{.State.Health.Status}}' | grep -q healthy; \
      do sleep 10; echo 'waiting...'; done && echo 'HEALTHY'"
   ```

### Fase 3 — Verificación post-upgrade

7. Verificar resources (todos deben estar `up`):
   ```bash
   curl -s -L -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
     "$MIDPOINT_URL_PUBLIC/ws/rest/resources" -H "Accept: application/xml" | \
     grep -E "<name>|lastAvailabilityStatus"
   ```

8. Comparar OIDs de conectores con el snapshot del paso 2.

9. Verificar schemas de extensión activos:
   ```bash
   curl -s -L -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
     "$MIDPOINT_URL_PUBLIC/ws/rest/schemas" -H "Accept: application/xml" | \
     grep -E "<name>|namespace"
   ```

10. Aplicar initial objects actualizados con ninja (desde dentro del container):
    ```bash
    sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
      "docker exec midpoint_server /opt/midpoint/bin/ninja.sh initial-objects --report"
    # Si hay merges, aplicarlos:
    docker exec midpoint_server /opt/midpoint/bin/ninja.sh initial-objects
    ```

### Fase 4 — Limpieza

11. Eliminar imágenes antiguas:
    ```bash
    sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
      "docker rmi evolveum/midpoint:4.9.5-ubuntu evolveum/midpoint:4.9.5-alpine"
    ```

## Breaking changes encontrados en UPeU 4.9.5 → 4.10.2

| # | BC | Encontrado | Acción tomada |
|---|---|---|---|
| BC-1 | `script-safe` renombrado a `script-limited` (permissionProfile built-in) | Si — presente en system config | No acción: el config UPeU define su propio permissionProfile `script-safe` como objeto custom, no es el built-in. Sigue funcionando. |
| BC-2 | Script evaluator removido del perfil `safe` built-in | Si — hay evaluador Groovy en perfil `safe` custom | No acción: el perfil `safe` en UPeU es custom (id=218), no el built-in. El evaluador Groovy con `decision=allow` y `permissionProfile=script-safe` sigue activo. |
| BC-3 | DatabaseTable 1.5.2.0 → 1.5.3.0 (OID cambia) | No — no usamos DatabaseTable en resources UPeU | Ninguna |
| BC-4 | 43 initial objects modificados | Si — conflicto con archetype `Project` (OID `1d773496-301b-4c61-bd94-1efc9e8355a4`) que ya existe en repo UPeU con nombre `Project` | Error no bloqueante. initial-objects reporta 1 error persistente. El archetype UPeU tiene precedencia. |
| BC-5 | Schema DB v50 → v51 (no automático en Docker Compose existente) | Si — CRITICO. data_init no hace upgrade, solo create | Ejecutar manualmente `ninja.sh run-sql --upgrade --mode REPOSITORY` y `--mode AUDIT` antes de arrancar midpoint_server. |
| BC-6 | Java 17 → 21 en imagen | Transparente | Ninguna |

## Tiempos observados

- Pull imágenes (4.10.2-ubuntu + 4.10.2-alpine): ~8 min (red campus UPeU)
- Upgrade schema REPOSITORY: <10 s
- Upgrade schema AUDIT: <10 s
- `docker compose down`: ~15 s
- `docker compose up -d` hasta `healthy`: ~4 min
- Total downtime efectivo: ~4.5 min

## Gotchas y advertencias

1. **El `data_init` NO hace upgrade automático de schema.** La lógica del compose detecta el schema como "no vacío" (falla CREATE porque los tipos existen) y concluye "not needed". El schema queda en la versión antigua y midpoint_server no arranca con error `schema version (N) doesn't match expected value (N+1)`. Solución: ejecutar `ninja run-sql --upgrade` manualmente ANTES del `compose up`.

2. **El healthcheck puede reportar `healthy` mientras el server sigue en crash-loop.** El healthcheck de Docker evalúa el endpoint HTTP, pero si el proceso crashea y reinicia, el healthcheck puede pasar en una ventana entre intentos. Verificar siempre los logs con `grep ERROR` después de que el healthcheck pase.

3. **OIDs de conectores bundled NO cambian** — los conectores externos (ScriptedSQL Tirasa, Koha custom, MSGraph, Keycloak custom) mantienen su OID al ser archivos en `/opt/midpoint/var/icf-connectors`. Los conectores bundled nuevos (LdapConnector v3.9.2, AdLdapConnector v3.9.2, CSV v2.9, DatabaseTable v1.5.3.0) se agregan como objetos nuevos junto a las versiones anteriores — no reemplazan ni cambian los OIDs existentes.

4. **El flag `--report-only` no existe en ninja 4.10.2.** Usar `--report` (genera deltas en XML a stdout). La aplicación de initial-objects se ejecuta separada sin flags.

5. **Conflicto archetype `Project` en initial objects:** Evolveum añadió un archetype `Project` built-in en 4.10. Si el repo UPeU ya tiene un objeto con `name=Project` de tipo `ArchetypeType`, ninja reportará un error en la importación pero lo descartará y continuará. No bloquea operación.

## Rollback

Si midpoint_server no arranca después del `compose up` y el upgrade de schema ya se aplicó (irreversible sin restaurar la DB):

```bash
# Opción 1: volver a 4.9.5 NO es viable si el schema ya fue upgradedo a v51.
# Opción 2 (correcta): depurar el error de startup y solucionar en 4.10.2.

# Si el schema aun no fue upgradedo (rollback limpio):
sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
  "cd /opt/midpoint && \
   sed -i 's/MP_VER=4.10.2/MP_VER=4.9.5/' .env && \
   docker compose down && \
   docker compose up -d"
```

**IMPORTANTE:** El rollback solo es viable si el schema de DB NO fue modificado. Una vez ejecutado `ninja run-sql --upgrade`, el schema es v51 y 4.9.5 no lo reconoce. En ese caso el único camino hacia atrás es restaurar un backup de PostgreSQL.
