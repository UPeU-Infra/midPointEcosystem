# Runbook — Koha en maintenance mode por outage .135 (2026-07-10)

## Contexto

Durante el workstream GAP-2 (backfill de `sb:personalEmail` en egresados/alumni),
Koha (`192.168.12.135:8001`) estaba caído a nivel LAN por la incidencia del
FortiGate del 08-jul. Al recomputar egresados que además son borrower Koha
(duales), el conector Koha lanza un `IllegalArgumentException('Uid cannot be null')`
(search de compensación con host inalcanzable) que MidPoint NO puede degradar vía
`connectorErrorCriticality` (no es categoría `network`/`generic`), abortando el foco.

Ver DT-9, DT-11 en `docs/ROADMAP.md`.

## Estado aplicado (2026-07-10)

El recurso **Koha ILS** (OID `9b5a7c81-47aa-42ac-9a08-4de8b64935af`) está en:

```
administrativeOperationalState/administrativeAvailabilityStatus = maintenance
```

Esto es un **flag operacional transitorio** aplicado vía REST PATCH — **NO** está en
el GitOps (`koha-ils.xml` no lo contiene). Efecto: MidPoint NO contacta el conector
Koha; las operaciones de proyección quedan `pending`; el foco de los duales tiene
éxito (partial). Permitió que el backfill GAP-2 completara los 30,917 egresados.

Resiliencia **permanente** (sí en GitOps, `koha-ils.xml`):
`consistency/connectorErrorCriticality/network=partial` + `generic=partial` (DT-9).

## ACCIÓN PENDIENTE — cuando .135 recupere

1. Verificar que Koha responde:
   `curl -sí http://192.168.12.135:8001/api/v1/...` (o Test Connection en UI).
2. Quitar maintenance (volver a `operational`) vía REST PATCH:

```bash
source ~/.secrets/midpoint-upeu.env
KOHA_OID="9b5a7c81-47aa-42ac-9a08-4de8b64935af"
sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no -o ProxyJump=none midpoint-prod "cat > /tmp/maint-off.xml <<'EOF'
<objectModification xmlns=\"http://midpoint.evolveum.com/xml/ns/public/common/api-types-3\"
                    xmlns:c=\"http://midpoint.evolveum.com/xml/ns/public/common/common-3\"
                    xmlns:t=\"http://prism.evolveum.com/xml/ns/public/types-3\">
    <itemDelta>
        <t:modificationType>replace</t:modificationType>
        <t:path>administrativeOperationalState/administrativeAvailabilityStatus</t:path>
        <t:value>operational</t:value>
    </itemDelta>
</objectModification>
EOF
curl -s -o /dev/null -w '%{http_code}\n' -X PATCH -u \"\$MIDPOINT_ADMIN_USER:\$MIDPOINT_ADMIN_PASS\" -H 'Content-Type: application/xml' --data-binary @/tmp/maint-off.xml http://localhost:8080/midpoint/ws/rest/resources/\$KOHA_OID"
```

3. Ejecutar `reconcile-koha-daily` (o esperar el cron `0 0 3 * * ?`) para replicar
   las operaciones `pending` y re-sincronizar los shadows Koha de los duales.
4. (Opcional) Re-lanzar el import GAP-2 para los ~150 duales que no obtuvieron
   `sb:personalEmail` — la mayoría son irreducibles (sin `CORREO` en
   `MOISES.PERSONA_NATURAL`), verificar antes de re-correr.

## Resultado del backfill GAP-2 (bajo maintenance)

| Métrica | Antes | Después |
|---|---|---|
| alumni con `sb:personalEmail` | 2,959 | 23,622 |
| total users con `sb:personalEmail` | 33,668 | 54,349 |
| duales (alumni + shadow Koha) con `personalEmail` | — | 2,517 / 2,667 |

Task OID `e9a2c7f0-6b1d-4a3e-9c85-0f7a1e2d3b40` — `closed`, 30,917 procesados,
`partial_error` (esperado por proyecciones Koha `pending`, no fatal).

Backups REST previos en PROD: `~/backups-gap2-2026-07-10/`.
