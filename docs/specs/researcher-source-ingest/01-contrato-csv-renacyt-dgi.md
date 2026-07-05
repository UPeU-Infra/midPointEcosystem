# Contrato de datos — CSV RENACYT/CONCYTEC que la DGI entrega al IGA

**Estado:** DISEÑO (no aplicado) · **Fecha:** 2026-07-04
**Rama:** `feature/researcher-source-ingest` · **NO merge a main, NO aplicar a PROD**
**Skills consultadas:** `iga-canonical-standards` (IIA §1.3, SCHAC §4, vocab RENACYT), `midpoint-best-practices` (schema is the law, identifiers inmutables)
**Insumo:** `scratchpad/17-fuente-orcid-renacyt.md` (hallazgo: los 4 atributos NO existen estructurados en Oracle LAMB)

---

## 0. Propósito y autoridad (IIA)

Los atributos de identidad-investigador (RENACYT nivel/condición, código CONCYTEC, CTI Vitae, área OCDE)
**no existen como dato estructurado y confiable en Oracle LAMB**. La única fuente utilizable es un
**CSV curado anual/semestral que produce la Dirección General de Investigación (DGI) de UPeU**.

- **IIA de la calificación RENACYT (nivel, condición, código, área): la DGI.** La DGI es el custodio
  institucional del padrón que CONCYTEC (autoridad legal nacional) publica; la DGI lo depura y lo
  entrega normalizado. En el modelo canónico (`iga-canonical-standards §1.3`) esto significa: el
  inbound del resource CSV es **`strength=strong`** para estos atributos; ningún sistema downstream
  los modifica.
- **Oracle LAMB NO es fuente de estos atributos.** El texto sucio de
  `MOISES.PERSONA_ACAD_CALIF_INV` (~85 personas, 80 con DNI) sirve **solo como lista-semilla de DNIs**
  para medir cobertura inicial del CSV DGI (ver §7), NUNCA como valor del nivel.
- **ORCID NO entra por este CSV como fuente primaria.** Su IIA primaria es el propio investigador vía
  self-service en el RIMS (ver spec `03-canal-orcid-rims-iga.md`). El CSV DGI puede traer ORCID como
  **columna opcional de respaldo** (`strength=weak`, ver §2 y `02`).

---

## 1. Formato del archivo

| Propiedad | Valor obligatorio |
|---|---|
| Nombre sugerido | `renacyt-dgi-upeu-YYYYMMDD.csv` (fecha de corte del padrón) |
| Encoding | **UTF-8** (sin BOM) |
| Delimitador de campo | **`;`** (punto y coma) — evita choque con comas de nombres de área OCDE |
| Delimitador multivalor | no aplica (1 valor por celda; ver regla de 1 fila por persona §4) |
| Cabecera | **Sí**, primera línea, nombres de columna EXACTOS como en §2 |
| Comillas | `"` solo si el valor contiene el delimitador; modo `DEFAULT` |
| Fin de línea | LF o CRLF (indiferente) |
| Terminador decimal | no aplica (no hay campos numéricos con decimales) |

> Nota MidPoint: el CSV connector v2.9 (OID `3517c9ef`) **requiere `fieldDelimiter` explícito**.
> Se fija `;` en el resource (`02-resource-renacyt-csv.xml`). Si la DGI solo puede exportar con `,`,
> ajustar el `fieldDelimiter` del resource — pero preferir `;` para robustez.

---

## 2. Columnas (contrato exacto)

Orden recomendado. Los nombres de cabecera son **case-sensitive** y deben coincidir con el resource.

| # | Columna (cabecera) | Oblig. | Tipo / formato | Destino MidPoint (`urn:sciback:midpoint:person`) | Notas |
|---|---|---|---|---|---|
| 1 | `dni` | **Sí** | 8 dígitos (DNI) o alfanumérico (CE/PASSPORT) | correlación → `identityDocuments[type].number` | Clave de correlación. Ver §3 |
| 2 | `tipo_doc` | **Sí** | vocab `DNI\|CE\|PASSPORT` | (solo para desambiguar la correlación type-aware) | Default `DNI` si vacío |
| 3 | `nivel_renacyt` | **Sí** | vocab normalizado (§5.1) | `renacytLevel` | strong |
| 4 | `condicion_renacyt` | **Sí** | vocab normalizado (§5.2) | `renacytStatus` | strong |
| 5 | `area_ocde` | No | texto (nombre área OCDE) | `researcherCategory` **o** dejar sin mapear (ver §6) | Ver decisión §6 |
| 6 | `concytec_id` | No | `P0NNNNNN` (P + 7 dígitos) | `concytecId` | strong si presente |
| 7 | `cti_vitae_id` | No | entero (ej. `161494`) | `ctiVitaeId` | strong si presente |
| 8 | `fecha_calificacion` | No | `YYYY-MM-DD` | (auditoría; no atributo de identidad — ver §6) | Metadato |
| 9 | `fecha_vigencia_fin` | No | `YYYY-MM-DD` | (auditoría / futuro trigger de expiración) | Metadato |
| 10 | `orcid` | No | `0000-0000-0000-0000` (16 dígitos, guiones) | `orcid` (**weak**, respaldo) | IIA primaria = RIMS self-service |

**Por qué estos destinos** (validado contra `docs/specs/researcher-identity-schema-dspace-cris-mapping.md`):
`renacytLevel`, `renacytStatus`, `concytecId`, `ctiVitaeId`, `orcid` YA existen en el schema canónico
en PROD (namespace `urn:sciback:midpoint:person`, OID `e800335c-…42693`) con outbounds a LDAP ya
cableados. **No se crea ningún atributo nuevo** ("schema is the law / no duplicar").

**Fuera de alcance de este CSV:** `isni` (diferido, ver §8), `scopusAuthorId` (IIA = DSpace-CRIS),
`researcherStatus`/`primaryResearcherStatus` (eje 2 institucional, IIA = lista oficial DGI + detección
CRIS, canal distinto).

---

## 3. Correlación por DNI (cómo casa contra los focos existentes)

- El CSV se indexa por **DNI** (columna `dni`).
- La correlación canónica del deployment usa **`name` = código institucional** y el DNI vive en el
  contenedor `identityDocuments`. Por eso NO se correla por `name`.
- Se replica el patrón **probado en PROD** (resource `trabajadores.xml`): un inbound `beforeCorrelation`
  normaliza el DNI del CSV a un campo de transporte `extension/upeu:lambDocNum` (type-aware, prefijo
  `CE:`/`PP:` para no-DNI) y MidPoint correla `UserType` donde `lambDocNum == DNI_del_CSV`.
- Detalle técnico completo en `02-resource-renacyt-csv.xml` (§ correlation).

**Consecuencia operativa:** solo se enriquecen focos que YA existen en el IGA (personas provisionadas
desde LAMB). Un DNI del CSV sin foco correlacionado NO crea usuario (`reaction unlinked` = no-op /
informe), porque la identidad-investigador es un **enriquecimiento**, no una fuente de alta de personas.

---

## 4. Reglas de calidad (que la DGI debe garantizar)

| ID | Regla | Motivo |
|---|---|---|
| Q1 | **Exactamente 1 fila por persona** (por `dni`). Sin duplicados. | Evita el problema contradictorio de Oracle (una persona con Nivel 3/6/7 en filas distintas). Un investigador tiene UNA calificación vigente. |
| Q2 | `dni` presente y válido (8 dígitos si `tipo_doc=DNI`; alfanumérico si CE/PASSPORT). | Sin DNI no hay correlación. En Oracle, 5 de 85 no tenían DNI cruzable. |
| Q3 | `nivel_renacyt` ∈ vocabulario §5.1. Sin texto libre, sin romanos+arábigos mezclados. | El schema tiene vocab controlado; el inbound normaliza, pero el CSV debe llegar ya limpio. |
| Q4 | `condicion_renacyt` ∈ vocabulario §5.2. | Igual que Q3. |
| Q5 | `concytec_id` (si presente) matchea `^P0\d{6}$`. | Formato del código RENACYT. |
| Q6 | `cti_vitae_id` (si presente) es entero. | Formato CTI Vitae. |
| Q7 | `orcid` (si presente) pasa checksum **MOD 11-2** (ISO 7064). | El IGA lo revalida en el outbound; llegar ya válido evita descartes. |
| Q8 | Fechas en `YYYY-MM-DD` (ISO 8601). | Parsing determinista. |
| Q9 | Una sola calificación **vigente** por persona (la más reciente si hubo re-calificación). | Q1 + coherencia temporal. |

---

## 5. Vocabularios controlados

### 5.1 `nivel_renacyt` (destino `renacytLevel`)

El CSV debe entregar el valor ya en la forma canónica del schema. Reglamento RENACYT vigente
(Res. Pres. Ejecutiva 045-2021-CONCYTEC-PE).

| Valor canónico (schema) | Aliases aceptados en el CSV (el inbound normaliza) |
|---|---|
| `DISTINGUIDO` | `Investigador Distinguido`, `Distinguido`, `DIST` |
| `NIVEL_I` | `I`, `Nivel I`, `1` |
| `NIVEL_II` | `II`, `Nivel II`, `2` |
| `NIVEL_III` | `III`, `Nivel III`, `3` |
| `NIVEL_IV` | `IV`, `Nivel IV`, `4` |
| `NIVEL_V` | `V`, `Nivel V`, `5` |
| `NIVEL_VI` | `VI`, `Nivel VI`, `6` |
| `NIVEL_VII` | `VII`, `Nivel VII`, `7` |

> **PENDIENTE (verificar antes de go-live):** el env menciona un vocabulario provisional distinto
> ("Carlos Monge Medrano" = MONGE_I/II/III/DIST; "María Rostworowski" = ROSTW_I…VII). El **schema
> canónico en PROD usa `DISTINGUIDO | NIVEL_I..NIVEL_VII`** (Reglamento 2021). Se adopta el del schema
> (no se toca el XSD: "datos institucionales se adaptan al canónico"). Confirmar con la DGI/reglamento
> vigente qué etiquetas literales usa el padrón actual y ajustar SOLO la tabla de aliases del inbound
> — nunca el vocab del schema.

### 5.2 `condicion_renacyt` (destino `renacytStatus`)

| Valor canónico (schema) | Aliases aceptados en el CSV |
|---|---|
| `ACTIVO` | `Activo`, `ACTIVO`, `Vigente` |
| `ACTIVO_AFILIADO` | `Activo Afiliado`, `Afiliado` |
| `NO_ACTIVO` | `No Activo`, `Inactivo`, `No Vigente` |
| `EXCLUIDO` | `Excluido`, `Retirado` |

Solo `ACTIVO`/`ACTIVO_AFILIADO` habilitan liderar proyectos/asesorar tesis (Reglamento Art. 11).

---

## 6. Decisiones sobre columnas sin destino directo

- **`area_ocde`**: el schema no tiene un atributo OCDE dedicado. Opciones: (a) mapear a
  `researcherCategory` (vocab libre), o (b) **no mapear** (dejar como columna informativa/auditoría).
  **Recomendación: (b) no mapear en la Fase 1** — `researcherCategory` tiene otra semántica
  (SENIOR/JUNIOR institucional). Si se requiere el área OCDE gobernada, crear atributo dedicado en un
  cambio de schema aparte. Marcada **PENDIENTE**.
- **`fecha_calificacion` / `fecha_vigencia_fin`**: no son atributos de identidad. Se dejan como
  metadato del CSV (útiles para el informe de cobertura y, a futuro, para un trigger de expiración de
  la vigencia RENACYT). No se mapean a foco en Fase 1.

---

## 7. Lista-semilla Oracle para validar cobertura inicial

De `MOISES.PERSONA_ACAD_CALIF_INV` filtrando RENACYT/CONCYTEC/DINA vigentes salen **~85 personas
distintas, 80 con DNI cruzable**. Uso:

1. Extraer esos ~80 DNIs (query read-only; NO usar el nivel, que es texto sucio).
2. Cruzar contra la columna `dni` del CSV que entregue la DGI.
3. **Métrica de cobertura mínima:** el CSV DGI debe contener al menos esos ~80 DNIs. Si faltan, la DGI
   tiene un padrón incompleto → gap a resolver antes de go-live.
4. El CSV puede (y debe) traer MÁS personas que la semilla (Oracle está incompleto y sucio); la semilla
   es piso, no techo.

---

## 8. Frontera y pendientes

- **ISNI: DIFERIDO.** No se pide en el CSV. Se poblará por aporte del investigador o cruce ORCID↔ISNI a
  futuro. No bloquea nada. (Outbound `isni` a LDAP ya existe por el contrato RIMS←IGA, queda inerte.)
- **PENDIENTE 1:** confirmar con la DGI si **ya produce hoy** un CSV/planilla RENACYT normalizado (env
  menciona `~/proyectos/upeu/calidad-upeu/scripts/renacyt/enriched.csv` con niveles `I..VII` +
  `Investigador Distinguido`, condición `Activo`). Si existe, este contrato solo formaliza/ajusta ese
  export. Si no, la DGI debe crearlo con este contrato.
- **PENDIENTE 2:** confirmar si CONCYTEC ofrece **descarga masiva / API del padrón RENACYT** que la DGI
  pueda usar como fuente del CSV. Nota previa del repo: **no hay REST API RENACYT**. Mientras, el CSV
  manual de la DGI es el mecanismo.
- **PENDIENTE 3:** verificar etiquetas literales del vocab de nivel vigente (§5.1).
- **PENDIENTE 4:** formato exacto del código CTI Vitae que la DGI maneje (`P0NNNNNN` vs entero de perfil).

---

## 9. CSV de ejemplo (ficticio, 8 filas)

Archivo de muestra: `renacyt-dgi-upeu-EJEMPLO.csv` (en esta misma carpeta). Contenido:

```
dni;tipo_doc;nivel_renacyt;condicion_renacyt;area_ocde;concytec_id;cti_vitae_id;fecha_calificacion;fecha_vigencia_fin;orcid
41970870;DNI;NIVEL_IV;ACTIVO;Ingeniería y Tecnología;P0130769;161494;2023-05-12;2026-05-11;0000-0002-1825-0097
07654321;DNI;NIVEL_II;ACTIVO;Ciencias Naturales;P0098765;158220;2022-11-03;2025-11-02;0000-0001-5109-3700
72783226;DNI;DISTINGUIDO;ACTIVO_AFILIADO;Ciencias Médicas y de la Salud;P0011223;140501;2021-08-19;2027-08-18;
48636923;DNI;NIVEL_I;ACTIVO;Ciencias Sociales;P0155001;172044;2024-02-01;2027-01-31;0000-0003-4227-1111
76575561;DNI;NIVEL_III;ACTIVO;Humanidades;P0122334;149887;2023-09-30;2026-09-29;0000-0002-9079-5933
10203040;CE;NIVEL_V;NO_ACTIVO;Ciencias Agrícolas;P0100999;;2019-06-15;2022-06-14;
50607080;DNI;NIVEL_VI;ACTIVO;Ingeniería y Tecnología;P0140222;180912;2024-07-22;2027-07-21;0000-0001-7737-2020
90807060;DNI;NIVEL_VII;EXCLUIDO;Ciencias Naturales;;;2018-03-10;2021-03-09;
```

Nota: DNIs y códigos son ficticios; los DNIs coinciden intencionalmente con casos conocidos del
deployment solo para ilustrar la correlación — no implican calificación real.
</content>
</invoke>
