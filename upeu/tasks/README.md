# `upeu/tasks/` — solo lo que corre

**Regla:** aquí vive únicamente la **configuración de tasks operativas**. Las campañas
puntuales ya ejecutadas van a [`archive/tasks-campanas-2026/`](../../archive/tasks-campanas-2026/).

Antes del saneamiento del 2026-08-03 esta carpeta tenía **73 XML de task, de los cuales 67
(el 92 %) eran campañas cerradas** — la mayoría ni siquiera existía ya en PROD. Con eso no
se podía responder *"¿qué está corriendo?"* leyendo el repo: había que consultar Postgres.

## Criterio de clasificación (medido contra PROD, no supuesto)

| Se queda aquí | Se archiva |
|---|---|
| Task **desplegada y viva** en PROD (`RUNNABLE`/`RUNNING`) | Task que **ya no existe** en PROD |
| Task **suspendida** que debe volver a correr | Task `CLOSED` de tipo `SINGLE` (one-shot) |
| Task **recurrente por diseño**, aunque no esté desplegada ahora | Carpeta de campaña con fecha en el nombre |

Verificación reproducible: cruzar el `oid` del elemento raíz de cada XML contra `m_task`
en PROD. Lo hace [`upeu/scripts/diff-repo-prod.sh`](../scripts/diff-repo-prod.sh).

## Estado al 2026-08-03

| Task | Estado en PROD |
|---|---|
| `entra-id-sync/recon-entra-id-daily.xml` | 🟢 `RUNNABLE` |
| `recon-oracle-lamb-egresados.xml` | 🟢 `RUNNABLE` |
| `recon-oracle-lamb-estudiantes.xml` | 🟢 `RUNNABLE` |
| `entra-id-sync/livesync-entra-id.xml` | 🔴 `SUSPENDED` — connector msgraph, ver memoria del 16-jul |
| `reconcile-koha-daily.xml` (`recon-koha-upeu-daily`) | 🔴 `SUSPENDED` desde el 28-jul — Koha ya está sano, solo falta reanudarla |
| `recon-oracle-lamb-trabajadores.xml` | 🔴 `SUSPENDED` desde el 25-jul — deliberado, tras el incidente del canario |
| `recon-oracle-lamb-grados.xml` | ⚪ versionada, **no desplegada** en PROD |
| `shadow-cleanup-koha-semanal.xml` | ⚪ versionada, **no desplegada** en PROD |

> Las dos últimas son recurrentes por diseño y están versionadas pero no corren en PROD.
> No es drift de configuración —el repo es la referencia— pero conviene decidir si deben
> desplegarse o retirarse.

## Al crear una campaña nueva

Carpeta con fecha (`<tema>-YYYY-MM-DD/`), y al terminar se mueve a `archive/`. Los XML de
campaña se conservan: son la evidencia de qué se ejecutó y con qué alcance.
