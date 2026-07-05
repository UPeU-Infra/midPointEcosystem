# Frontera de alcance y pendientes — ingesta identidad-investigador

**Estado:** DISEÑO (no aplicado) · **Fecha:** 2026-07-04 · **Rama:** `feature/researcher-source-ingest`

Resumen del alcance del pipeline diseñado y lo que queda fuera / por confirmar antes de go-live.
Los 4 atributos objetivo hoy están en **0** en LDAP (confirmado en `scratchpad/17-fuente-orcid-renacyt.md`).

---

## 1. Qué cubre este diseño (por atributo)

| Atributo canónico | Fuente (IIA) | Canal | Strength | Estado destino LDAP |
|---|---|---|---|---|
| `renacytLevel` | DGI (CSV curado) | `RENACYT-DGI-CSV` (resource CSV) | strong | outbound `scibackRenacyt*` ya existe |
| `renacytStatus` | DGI (CSV curado) | `RENACYT-DGI-CSV` | strong | ya existe |
| `concytecId` | DGI (CSV curado) | `RENACYT-DGI-CSV` | strong | ya existe |
| `ctiVitaeId` | DGI (CSV curado) | `RENACYT-DGI-CSV` | strong | ya existe |
| `orcid` → `eduPersonOrcid` | Investigador (self-service RIMS) | `RIMS-ORCID-INBOUND` (REST PULL) + CSV DGI respaldo | strong (RIMS) / weak (CSV) | outbound MOD 11-2 ya existe |
| `isni` | — (DIFERIDO) | — | — | outbound `isni` existe pero **inerte** |

Correlación: **DNI** (CSV) y **ePUID** (RIMS). Ninguno de los dos canales **crea personas** — solo
enriquecen focos ya provisionados desde LAMB.

---

## 2. Fuera de alcance (deliberado)

- **ISNI — DIFERIDO.** No se pide en el CSV ni se auto-gestiona. Poblar a futuro por aporte del
  investigador o cruce ORCID↔ISNI. El outbound LDAP `isni` (añadido por el contrato RIMS←IGA) queda
  inerte hasta entonces. No bloquea nada.
- **`scopusAuthorId`** — NO se modela en MidPoint. IIA = DSpace-CRIS (detección por autoría). Si el IGA
  llegara a necesitarlo, se trae como inbound read-only desde el resource DSpace-CRIS.
- **`researcherStatus` / `primaryResearcherStatus`** (eje 2 institucional: oficial-dgi | detectado-autoria
  | externo) — canal distinto (lista oficial DGI + detección CRIS), fuera de esta ingesta de
  identificadores. Ver `docs/specs/researcher-identity-schema-dspace-cris-mapping.md`.
- **`area_ocde`** — el schema no tiene atributo OCDE dedicado; no se mapea en Fase 1 (contrato §6).

---

## 3. Pendientes que requieren acción externa (no código)

| # | Pendiente | Responsable | Bloquea |
|---|---|---|---|
| P1 | **¿La DGI ya produce hoy un CSV RENACYT normalizado?** (env cita `calidad-upeu/scripts/renacyt/enriched.csv` con `I..VII` + `Investigador Distinguido`, condición `Activo`). Si existe, este contrato solo lo formaliza. | Alberto ↔ DGI | resource CSV |
| P2 | **¿CONCYTEC ofrece descarga masiva / API del padrón RENACYT?** Nota previa del repo: *no hay REST API RENACYT*. Confirmar; mientras, el CSV manual DGI es el mecanismo. | Alberto ↔ CONCYTEC/DGI | robustez fuente |
| P3 | **Etiquetas literales del vocab de nivel** vigente (schema usa `DISTINGUIDO|NIVEL_I..NIVEL_VII`; env menciona provisional MONGE_*/ROSTW_*). Confirmar Reglamento vigente y ajustar SOLO aliases del inbound, no el schema. | Alberto ↔ DGI/reglamento | normalización |
| P4 | **Formato exacto del código CTI Vitae** que maneja la DGI (`P0NNNNNN` vs entero de perfil). | Alberto ↔ DGI | mapeo concytecId/ctiVitaeId |
| P5 | **RIMS: feed ORCID read-only + scope OAuth `iga:orcid:read` + persistencia ePUID.** Ver `03-canal-orcid-rims-iga.md §2`. | Chat RIMS | canal ORCID |
| P6 | **¿RIMS implementa verificación OAuth ORCID?** (sube IAL de self-asserted a verificado). | Chat RIMS | mejora IAL (opcional) |

---

## 4. Pendientes técnicos (código, cuando haya insumo real)

- Confirmar OID real del CSV connector v2.9 (`3517c9ef`) y ajustar `connectorRef` del resource.
- Confirmar firma de la FunctionLibrary `toCanonicalDocNumber` (OID `1c7e4b2d-…4b31`): si espera
  código LAMB numérico, traducir `DNI|CE|PASSPORT` textual → `1|4|7` antes de invocarla.
- Path canónico exacto del ePUID en el schema para correlación RIMS (`extension/sciback:eduPersonUniqueId`).
- Connector REST para `RIMS-ORCID-INBOUND` (scripted REST existente vs REST genérico) + su OID.
- OIDs definitivos de resource CSV y de las tasks (usar md5 del código, patrón del deployment).

---

## 5. Orden de ejecución sugerido (cuando se apruebe salir de papel)

1. Cerrar P1–P4 con la DGI (contrato CSV firme).
2. Extraer lista-semilla (~80 DNIs Oracle) para métrica de cobertura.
3. Importar resource CSV a un entorno de pruebas (`pruebas-alberto-1`), SIMULACIÓN primero.
4. Lote semilla → lote completo (ver task escalonable en `02-resource-renacyt-csv.xml`).
5. En paralelo, cerrar P5/P6 con el chat RIMS; crear `RIMS-ORCID-INBOUND`.
6. Validar publicación LDAP (`eduPersonOrcid`, `scibackRenacyt*`) y assertions Keycloak.
7. Recién entonces: PR a `main` + despliegue GitOps a PROD.
