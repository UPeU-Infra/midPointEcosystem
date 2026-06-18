# Fase 5 — Provisioning DGI/investigadores al DSpace-CRIS

Artefactos para proyectar la investigacion UPeU (OrgUnits + Person + afiliacion CERIF)
al CRIS `cris.upeu.edu.pe` via MidPoint.

## ⚠️ Incidente OOM 2026-06-18 + endurecimiento del driver

Una corrida del masivo CRIS con `--workers 4` ahogó el heap del JVM (98.6%) tras
procesar ~395/3.776 focos DGI → OOM → MidPoint reiniciado. El driver murió antes de
su fase de restauración, dejando: resource CRIS en `active` (debía ser `proposed`) y
3 tareas operativas suspendidas (`recon-entra-id-daily`, `import-entra-id-hourly`,
`Cleanup dead shadows Koha`). Restaurado el 2026-06-18 (resource→`proposed`, 3 tareas
reanudadas → runnable/running).

**Causa raíz:** el recompute multihilo (4 workers) acumula lens contexts en heap y el
JVM corre con `-XX:+DisableExplicitGC` (no se puede forzar GC; solo G1 decide). El gate
de heap del driver original solo se evaluaba *entre* lotes → un lote de 4 recomputes
concurrentes disparaba el heap de golpe. Contenedor: límite 10 GiB, Xmx ~9 GiB, JRE
(sin `jcmd`/`jstat` → el heap solo se observa vía `docker stats` MemPerc).

**Verificación del lote provisionado (395):** SIN corrupción del OOM. 0 duplicados por
DNI, 389/390 Persons con exactamente 1 item, `dspace.entity.type` single "Person", DNI
correcto. 1 DNI marcado done sin Person en CRIS (70238948, el foco a media escritura al
morir). 5 sin DNI (dato sucio Oracle). El upsert idempotente por DNI evitó duplicados
pese al kill abrupto. **405 Persons** en la colección Investigadores ahora.

**HALLAZGO pendiente (no es daño del OOM, es defecto funcional preexistente):** las
Persons se crean OK pero **la afiliación CERIF reltype 5 NO se está materializando**
(0/40 de muestra con relación a OrgUnit; hay 221 OrgUnits en CRIS). `syncPersonAffiliations`
hace `log?.warn` y continúa sin fallar → las afiliaciones se pierden silenciosamente.
Requiere diagnóstico aparte antes de continuar el masivo.

**Endurecimiento aplicado a `provision-area-cris.sh`:**
- **Tope duro de concurrencia: `--workers` ≤ 2** (valores mayores se fuerzan a 2). Default 1.
- Procesa en **lotes pequeños** (`--batch`, default 50) con **pausa entre lotes** (20s).
- **Gate de heap ANTES de cada lote**: pausa con espera de GC a ≥75%, **ABORT a ≥88%**.
- **Restart programado** de `midpoint_server` cada `RESTART_EVERY_BATCHES` (8) lotes —o
  antes si el heap no cede tras esperar GC—, con gate de disco previo y espera a `healthy`.
- Gate de disco **ABORT ≥92%** (incidente disk-full relacionado).
- Sigue siendo idempotente y resumible desde el done-file.

Tunables por env: `BATCH_SIZE PAUSE_BETWEEN_BATCHES HEAP_ABORT HEAP_SOFT HEAP_OK RESTART_EVERY_BATCHES GC_WAIT_MAX`.

## Estado (2026-06-18)

**Ejecutado (acotado a DGI, controlado):**
- 186 OrgUnit en CRIS con metadata PerúCRIS completa: DGI + 7 CII (`#unidadDeInvestigacionOInnovacion`)
  + 178 lineas (`#lineaDeInvestigacion`), con `organization.parentOrganization`,
  `dspace.entity.type=OrgUnit` (single), `legalName`, `esRaiz`, `ruc`. Upsert por
  `legalName` (los 3 CII minimos pre-existentes se enriquecieron, no se duplicaron).
- 4 investigadores piloto como Person en CRIS (entity.type single, dni, dc.title);
  1 con afiliacion CERIF reltype 5 rightPlace 0 verificada (Itler).

**NO ejecutado (preparado para otra ocasion):**
- Masivo de toda la poblacion (~3.776 investigadores) — `recompute-dgi-investigadores.xml`
  (estado `suspended`) + `driver-masivo-cris.sh`.
- Reconciliar 16 grupos RENACYT <-> 7 CII.

## Componentes nuevos en el modelo (commit fase 5 DGI)

| OID | Objeto | Rol |
|---|---|---|
| `bdfe5f18-99f1-437b-80e6-ccffb52215ad` | AR-CRIS-OrgUnit | construction kind=generic intent=orgUnit; gate research-center/line/DGI. Espejo de AR-CRIS-Person. |
| `c4e8f1a2-9b03-4d57-8e62-1a4f7c0d9e35` | AR-CRIS-Person | construction kind=account intent=person; gate RENACYT/research-center. |

## Orden de ejecucion del masivo (cuando se decida)

1. Suspender Entra daily/hourly + Koha cleanup (ver cabecera del XML).
2. Resource CRIS `proposed` -> `active` (PATCH `?options=raw`).
3. **OrgUnits primero**, en orden jerarquico (institucion -> facultades -> DGI -> CII -> lineas):
   `driver-masivo-cris.sh ORGUNIT <user> <pass> <oids_ordenados>`.
4. Materializar afiliaciones persona->CII (reconciliar inbound `investigadores-afiliacion`
   8c4f1a36) si aun no estan como assignment.
5. **Personas**: `driver-masivo-cris.sh PERSON <user> <pass> <oids_users>`.
6. Verificar en CRIS (matches por DNI=1, entity.type single, CERIF reltype 5 rightPlace 0).
7. Resource CRIS -> `proposed`. Reanudar tareas Entra/Koha.

## Lecciones (aplican al blueprint SciBack)

- El outbound del objectType orgUnit/person debe leer del `focus` directamente, NO de
  un `<source>`: el binding `input` no se expone fiablemente en construction outbound
  (`No such property: input`).
- Scripts que leen `focus.identifier` (solo en OrgType) deben guardarse con
  `instanceof OrgType` — el lens puede evaluar la condicion de un inducement con un
  foco UserType (persona afiliada al OrgType portador del AR) -> `No such property:
  identifier for UserType`.
- HTTP 240/250 del connector ScriptedREST = exito-con-ruido (shadow dead). Verificar
  el dato en el CRIS, no el codigo HTTP. Idempotente por legalName/dni.
