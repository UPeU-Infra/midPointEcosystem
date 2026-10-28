# Initial objects en la subida a 4.11.0

> **Regla:** `ninja initial-objects` se ejecuta **siempre con una lista blanca de OID**
> (`--oid …`), nunca sobre el conjunto entero ni con una lista negra. Una lista negra deja
> pasar lo que se olvidó; una lista blanca solo toca lo que se leyó.

## De dónde salen las listas (medido el 28-oct-2026)

Se cruzaron tres fuentes:

1. `m_object` de PROD: OID, tipo, nombre y `version` de cada objeto con OID de Evolveum
   (`version = 1` = intacto desde que se importó).
2. Los initial objects del tag `v4.10.2` (lo que PROD trae hoy de fábrica).
3. Los del tag `v4.11.0`.

Resultado: 191 initial objects en 4.11.0, **78 cambiados** respecto a 4.10.2 y **20 nuevos**.

| Fichero | Cuántos | Qué se hace |
|---|---|---|
| [`aplicar-sin-merge.oids`](aplicar-sin-merge.oids) | 39 | Cambiados en 4.11 e **intactos** en PROD: reports, marks, colecciones de auditoría, value policy, template 380 (sin uso), policies y dashboard de compliance. Se reemplazan por la versión 4.11 (`--no-merge`). Pasan sus scripts de Groovy a MEL con `language#mel` explícito. |
| [`revisar-a-mano.oids`](revisar-a-mano.oids) | 35 | Cambiados en 4.11 y **modificados** en PROD (archetypes de tareas v2 por la reparación de `archetypeRef` del 3-ago, 702 Person v16, lookups, dashboard admin v2), más la Security Policy (intacta pero gobierna el login). Informe de merge y decisión uno a uno. Por defecto **no se tocan**. |
| [`nunca.oids`](nunca.oids) | 10 | SystemConfiguration, administrator, los roles 004/008/00a/00b/00c (UPeU reutilizó los OID de Evolveum `…000a/…000b/…000c` para sus roles GOV-*) y las 3 tareas de sistema. **Nunca** con ninja. |

Los **20 nuevos** de 4.11 (marcas 739–748, orígenes 602/603, archetypes de smart integration
y de tareas 539/540, `064-archetype-governance-policy`, `070-initial-open-source-connectors`)
**no los toca ninja**: midPoint los crea solo en el primer arranque. Ninguno choca con un OID
de PROD (comprobado).

> ⚠️ `070-initial-open-source-connectors` es un `AllowedConnectorsList` firmado. Ver
> «Verificación de conectores» en [`../README.md`](../README.md).

## Comandos (ventana F3, después de `run-sql --upgrade` y ANTES de arrancar midPoint)

Desde `/opt/midpoint`, con `MP_VER=4.11.0` en el `.env` y el volumen ya en 1000:1000:

```bash
C="docker compose -f docker-compose.yml -f upgrade-4.11/docker-compose.upgrade-window.yml -f upgrade-4.11/docker-compose.4.11.yml"
IO=~/midPointEcosystem/upeu/infra/upgrade-4.11/initial-objects
oids() { grep -o '^[0-9a-f-]\{36\}' "$1" | tr '\n' ' '; }

# 1. Informe de TODO lo que 4.11 cambiaria (solo lectura), para el expediente de la ventana:
$C run --rm --no-deps ninja initial-objects --dry-run --report --report-style DELTA \
   -o /opt/midpoint/var/export/io-411-todo-delta.xml -O

# 2. Informe de la lista blanca (solo lectura) y LECTURA del informe antes del paso 3:
$C run --rm --no-deps ninja initial-objects --dry-run --report --report-style DELTA --no-merge \
   --oid $(oids $IO/aplicar-sin-merge.oids) -o /opt/midpoint/var/export/io-411-aplicar-delta.xml -O

# 3. Aplicar la lista blanca:
$C run --rm --no-deps ninja initial-objects --no-merge --oid $(oids $IO/aplicar-sin-merge.oids)

# Leer un informe desde el host:
docker run --rm -v midpoint_midpoint_home:/v:ro --entrypoint cat postgres:16-bullseye /v/export/io-411-aplicar-delta.xml | less
```

Comprobación antes del paso 3: en el informe del paso 2 **no puede aparecer** ningún OID de
`nunca.oids` ni de `revisar-a-mano.oids`:

```bash
docker run --rm -v midpoint_midpoint_home:/v:ro --entrypoint cat postgres:16-bullseye /v/export/io-411-aplicar-delta.xml \
  | grep -c -F -f <(grep -o '^[0-9a-f-]\{36\}' $IO/nunca.oids $IO/revisar-a-mano.oids | cut -d: -f2)   # debe dar 0
```

Comprobación después: `version` de los 39 objetos subió en 1 y los 10 de `nunca.oids`
conservan su `version` (consulta en el runbook F3, paso 10).

## ❓ Lo que solo el ensayo F1 puede confirmar

- Que `--oid` acepta 39 valores separados por espacios en una sola invocación
  (`variableArity = true` en `InitialObjectsOptions` de v4.11.0, así que debería).
- Que el informe de merge de los 35 de `revisar-a-mano.oids` no trae nada imprescindible.
  En particular, el 702 Person: según el inventario, 4.11 solo le añade claves de traducción.
- Cuánto tarda (en mayo, con 4.10.2, el paso entero fue de segundos).
