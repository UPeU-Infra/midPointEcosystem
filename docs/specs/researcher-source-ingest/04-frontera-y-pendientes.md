# Frontera de alcance y pendientes — ingesta identidad-investigador

**Estado:** DISEÑO (no aplicado) · **Fecha:** 2026-07-04 (rev. 2026-07-05) · **Rama:** `feature/researcher-source-ingest`

Resumen del alcance del pipeline diseñado y lo que queda fuera / por confirmar antes de go-live.
Los 4 atributos objetivo hoy están en **0** en LDAP (confirmado en `scratchpad/17-fuente-orcid-renacyt.md`).

> ⚠️ **CORRECCIÓN 2026-07-05 — la investigación del 04-jul estaba incompleta para ORCID.**
> Se dijo "ORCID cobertura = 0 en Oracle" porque solo se buscó el patrón en texto libre de
> `MOISES.PERSONA_ACAD_CALIF_INV`. Un cruce más profundo (motivado por pregunta del usuario: "¿esos
> investigadores RENACYT están registrados en LAMB research/DGI?") encontró que **`ESTHER.DGI_PERFIL`
> tiene una columna ORCID dedicada, con datos reales y de buena calidad**: el propio sistema DGI ya
> corre un self-service de ORCID. Ver §6 (nuevo) para el detalle y el impacto en el diseño.

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

## 6. HALLAZGO 2026-07-05 — `ESTHER.DGI_PERFIL.ORCID` ya existe como self-service en producción

Verificado por lectura directa (túnel Oracle vía jump OCI, SOLO LECTURA):

- **`ESTHER.DGI_PERFIL`** (`ID_PERFIL, ID_PERSONA, ORCID, URL_FOTO, ID_PERSONA_REG, FECHA_REG, ID_PERSONA_ACT, FECHA_ACT`) es un perfil de investigador que el propio sistema DGI ya permite auto-registrar.
- **306 filas, las 306 con ORCID no nulo.** Fechas de registro **23-abr-2025 → 02-jul-2026** (activo, uso continuo hasta hace 3 días) → **es un self-service YA en producción**, no un diseño futuro.
- **Calidad alta:** 303/306 (99%) pasan checksum MOD 11-2; 2 con formato correcto pero checksum inválido; 1 con formato inválido; **1 ORCID duplicado** (2 personas con el mismo ORCID — revisar antes de importar).
- **Overlap con los 84 investigadores RENACYT vigentes:** 27 de 84 (32%) ya tienen su ORCID en `DGI_PERFIL`.
- **Overlap con la población `DGI_INVESTIGADOR`** (4.242 tesistas/asesores, tabla de participación — confirma que NO reconcilia RENACYT, solo 3/84 overlap ahí): 166 de 4.242 (4%) tienen ORCID en `DGI_PERFIL`.

### Impacto en el diseño (actualiza `02` y `03`)

1. **No hace falta partir de cero con el self-service ORCID.** Antes de construirlo en el RIMS, hay **306 ORCID reales que importar como semilla** al IGA. Recomendación: añadir un **inbound adicional de solo lectura `DGI-PERFIL-ORCID`** (mismo patrón que el CSV RENACYT: connector contra Oracle vía vista/extracto read-only, o CSV export de esta tabla) que alimente `sciback:orcid` con `strength=weak` (rellena vacíos) **antes** de que el canal RIMS self-service (`strong`, autoridad del titular) quede operativo. Correlación: por `ID_PERSONA` → resolver a DNI (`MOISES.PERSONA_NATURAL.NUM_DOCUMENTO`) → `identityDocuments[DNI]`, igual patrón que el CSV RENACYT.
2. **El self-service del RIMS (`03-canal-orcid-rims-iga.md`) sigue siendo el diseño correcto para el futuro** (fuente autoritativa continua, no un extracto puntual) — pero ya no es la única fuente ni el punto de partida en cero. Cuando el RIMS reemplace a DGI, este flujo de `DGI_PERFIL` se apaga y el RIMS pasa a ser la única fuente.
3. **Antes de importar:** deduplicar el 1 ORCID repetido (decidir cuál de las 2 personas es la titular real, o marcar ambas para revisión manual) y descartar los 3 con checksum/formato inválido (o corregirlos a mano si el error es obvio, p. ej. dígito de control mal tecleado).
4. **No confundir con RENACYT:** `DGI_PERSONA_VALIDACION` (60/84 overlap) NO es RENACYT — sus columnas (`ID_TIPO_VALIDADOR`, `CUPO`, `EXPERIENCIA`, `TIPO='I'`) son validación de elegibilidad de jurado/asesor por programa (workflow interno de DGI), no identidad de investigador. Se descarta como fuente de RENACYT.

**PENDIENTE nuevo (P7):** confirmar con la DGI si `DGI_PERFIL` es el "perfil de investigador" oficial de su plataforma (para saber si seguirá vivo mientras el RIMS no reemplace a DGI, y si debe tratarse como fuente *strong* en vez de *weak* — si es la plataforma oficial que los investigadores ya usan activamente, podría ser preferible a esperar el self-service nuevo en el RIMS).

---

## 5. Orden de ejecución sugerido (cuando se apruebe salir de papel)

1. Cerrar P1–P4 con la DGI (contrato CSV firme).
2. Extraer lista-semilla (~80 DNIs Oracle) para métrica de cobertura.
3. Importar resource CSV a un entorno de pruebas (`pruebas-alberto-1`), SIMULACIÓN primero.
4. Lote semilla → lote completo (ver task escalonable en `02-resource-renacyt-csv.xml`).
5. En paralelo, cerrar P5/P6 con el chat RIMS; crear `RIMS-ORCID-INBOUND`.
6. Validar publicación LDAP (`eduPersonOrcid`, `scibackRenacyt*`) y assertions Keycloak.
7. Recién entonces: PR a `main` + despliegue GitOps a PROD.
