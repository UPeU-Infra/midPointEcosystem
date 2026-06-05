# Fase 3d — Connector Koha v1.3.10 + cierre residual onboarding student-Lima

Fecha: 2026-06-05 · PROD `midpoint-prod` (192.168.15.166)
Resource Koha OID `9b5a7c81-47aa-42ac-9a08-4de8b64935af` · Connector v1.3.10 OID `566c1121-785d-43be-8679-d939d2c8144b`

## Objetivo
Cerrar el residual de onboarding: estudiantes con archetype student + campusStudent=LIMA + active
SIN cuenta Koha. Universo medido en MidPoint = **321** (de 12,410 student-Lima-active; 12,089 ya con cuenta).

## Deploy v1.3.10
1. Backup pg_dump de m_shadow/m_resource/m_connector (`/tmp/bkp_koha_v1310_20260605_142022.sql`, 3.3MB).
   Rollback v1.3.9 retenido en `/opt/midpoint/connectors/connector-koha-1.3.9.jar`.
2. `curl -L` del jar v1.3.10 del release a `/opt/midpoint/connectors/` — sha256 `d676c4c1…9130c` verificado OK.
3. `docker restart midpoint_server` → healthy.
4. PATCH `connectorRef` del resource al OID v1.3.10 (JSON delta `replace`). **Lección:** el OID correcto
   del KohaConnector v1.3.10 es `566c1121-…` — un primer intento usó OID equivocado (`3517c9ef`, que era
   un CsvConnector) por un grep mal alineado → Test Connection falló con "Wrong namespace CsvConnector".
   Resolver el OID con query XML precisa filtrando `connectorType` + `connectorVersion`.
5. Test Connection: **success** todas las fases. Credenciales (encryptedData OAuth+JDBC) preservadas por
   el PATCH quirúrgico (no toca connectorConfiguration).

## Hallazgo arquitectónico clave — el fix v1.3.10 requería cambio en el RESOURCE
El connector v1.3.10 hace adopt-by-DNI ante un 409 leyendo `payload.extended_attributes[].type=="DNI"`.
Pero el resource Koha **no enviaba** ese par: el outbound de `ri:extended_attributes` sólo emitía
`{"type":"STUDY_LEVEL",…}`. Sin el par DNI en el payload del CREATE, el adopt-by-DNI se omitía → 409
irrecuperable. El JDBC fallback además usaba el `name` (código) como "DNI", no el DNI real.

**Fix (commits `93ed2b4` + `9d031f6`):** agregar emisión del par `{"type":"DNI","value":<dni>}` desde
`extension/upeu:lambDocNum` (8 dígitos). `<outbound>` es **single-valued** en MidPoint → no se permiten
dos; se combinó STUDY_LEVEL + DNI en UN outbound que retorna `List`. DNI no está en
`intolerantValuePattern` → tolerado (MidPoint lo añade pero no lo gobierna destructivamente).
Re-import del resource vía **PUT** `?options=overwrite` (el POST `/resources/{oid}?overwrite` espera
ObjectModification, no objeto completo). Credenciales preservadas (ciphertext idéntico repo↔PROD).

## Clasificación del residual (cruce MidPoint↔Koha por DNI/código)
- **310 COD-only** — borrower legacy con cardnumber=código, **orphan shadow** (piv=borrowernumber, sin owner).
  Camino: **`POST /shadows/{oid}/import`** (linkea sin crear) + recompute (converge categoría ESTUDI→student,
  library BUL). El recompute focus-driven NO sirve solo: choca el unique-constraint `m_shadow_…_primaryidentifiervalue`.
- **9 DNI-only** — borrower legacy con cardnumber=DNI. Camino: **recompute** → adopt-by-DNI v1.3.10
  (resuelve por cardnumber=DNI `_match=exact`, adopta 1:1, cardnumber=DNI preservado por mapping weak).
- **1 sin borrower** — recompute crea nuevo.

## Canary (GATE) — PASS
- DNI-only ×3 (29389/28785/29394): shadow Koha linkeado al borrower EXISTENTE (adoptado, no creado),
  categoría student, branchcode converge BUJ→BUL en 2º recompute. 0 dup, 0 storm.
- COD-only ×1 (663): orphan import → owner asociado → recompute → ESTUDI→student, cardnumber=código, BUL.
- 0 cardnumber duplicado, 0 fusión, load Koha estable ~2.9 en todo momento.

## Ejecución masiva
- **309 orphan imports** serializados (driver `/tmp/import_orphans.sh`, creds por argumento, gate heap>90%):
  309/309 ok, heap estable 47%. (+663 canary = 310).
- **311 recompute convergencia** COD (driver `/tmp/recompute_foci.sh`): 310 ok, 1 fail (userid conflict).
- **9 recompute** DNI-only: 7 ok, 2 fail.

## Resultado final
| Métrica | ANTES | DESPUÉS |
|---|---|---|
| student-Lima-active con cuenta Koha | 12,089 | **12,407 / 12,410 (99.98%)** |
| residual sin cuenta | 321 | **3** |
| Koha categorycode=student | 12,559 | **12,868** (+309) |
| Koha categorycode=ESTUDI | 1,826 | **1,517** (−309) |
| Koha TOTAL borrowers | 19,721 | **19,721** (invariante — 0 creados) |
| Koha DUP_CARD | 0 | **0** (sagrado) |

## 3 irreducibles (requieren koha-expert / análisis caso a caso)
1. **9710231 / DNI 40154147** — borrower 85810 cardnumber=9710231 (7 dígitos), categoría ALUMNI; orphan
   shadow por userid importado pero el correlador exige cardnumber>=8 dígitos → __NO_MATCH__ → 0 owner.
2. **202210151 / DNI 72896218** — borrower 26239 cardnumber=código, categoría ESTUDI; sin orphan shadow
   linkeable por piv; recompute da 409 sin adopt resoluble.
3. **323200401 / DNI 72066573** — Koha devuelve 409 "matching these details" pero NO existe borrower con
   cardnumber/userid/email/DNI-attr resoluble (homónimo por PatronDuplicate de Koha firstname+surname+dob);
   foco con emailAddress vacío. El connector no puede adoptar sin identificador único.

## Estado del sistema
- MidPoint heap 47.9%, 0 tareas colgadas (todo vía REST síncrono, sin tasks creadas).
- Connector v1.3.10 operativo, Test Connection 8/8. Delete capability NO tocada.
- **1 restart de MidPoint** autorizado intermedio (heap llegó a 98.67% tras query grande → 45% post-restart).

## Drivers reutilizables (SciBack)
- `import_orphans.sh` — import serializado de orphan shadows con gate de heap. Creds por argumento.
- `recompute_foci.sh` — PATCH no-op (`description`) por foco para disparar clockwork+outbound SIN reconcile
  (evita el "too many clicks" del Entra CreateCapability). Gate heap.
- **Patrón canónico residual onboarding ILS:** clasificar residual por (cardnumber==código | cardnumber==DNI |
  sin-borrower); orphan-by-piv → import; cardnumber==DNI → adopt-by-DNI (requiere par DNI en payload outbound).
