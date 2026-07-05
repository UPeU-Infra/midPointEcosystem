# Ingesta de identidad-investigador al IGA UPeU

**Estado:** DISEÑO EN PAPEL — no aplicado a PROD, sin insumo real todavía.
**Rama:** `feature/researcher-source-ingest` (NO merge a main).
**Fecha:** 2026-07-04 · **Skills:** `iga-canonical-standards`, `midpoint-best-practices`.

Pipeline para poblar en LDAP los 4 atributos de identidad-investigador hoy en **0**
(ORCID, RENACYT nivel/condición, CTI Vitae/concytecId, ISNI). El schema canónico
(`urn:sciback:midpoint:person`) y los outbounds a LDAP YA existen; solo falta alimentar el foco.

## Insumo

`scratchpad/17-fuente-orcid-renacyt.md` — hallazgo: los 4 atributos NO existen estructurados en
Oracle LAMB. RENACYT solo como texto sucio en `MOISES.PERSONA_ACAD_CALIF_INV` (~85 personas) → sirve
solo como lista-semilla de DNIs.

## Decisiones tomadas (usuario)

- **RENACYT / CTI Vitae / concytecId → CSV curado de la DGI + CSV connector MidPoint** (IIA = DGI).
- **ORCID → self-service en el RIMS** (IIA primaria = investigador), canal REST inbound RIMS→IGA.
- **ISNI → diferido.**

## Archivos

| Archivo | Contenido |
|---|---|
| `01-contrato-csv-renacyt-dgi.md` | Contrato de datos del CSV que la DGI entrega: columnas, tipos, formato, vocab, reglas de calidad, lista-semilla. |
| `renacyt-dgi-upeu-EJEMPLO.csv` | CSV de ejemplo (8 filas ficticias). |
| `02-resource-renacyt-csv.xml` | Esqueleto resource CSV (connector v2.9): inbounds strong, correlación por DNI (vía `upeu:lambDocNum`), normalización de vocab, task de import escalonable. |
| `03-canal-orcid-rims-iga.md` | Diseño del canal ORCID self-service RIMS→IGA (PULL REST, correlación por ePUID, MOD 11-2 en 3 puntos, reparto RIMS vs IGA). |
| `04-frontera-y-pendientes.md` | Alcance por atributo, fuera-de-alcance, pendientes externos (DGI/CONCYTEC/RIMS) y técnicos, orden de ejecución. |

## Regla

Modelo canónico primero; los datos DGI/RIMS se adaptan al schema, nunca al revés. Ningún atributo
nuevo se crea (todos existen ya en PROD). Este diseño NO crea personas: solo enriquece focos
provisionados desde LAMB.
</content>
