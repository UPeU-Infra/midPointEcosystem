# Plan — las 15 orgs `academic-program` publican la URI obsoleta

**Fecha:** 2026-08-05 · **Medido en vivo** · **Nada ejecutado**
**Contexto:** [`HALLAZGO-programas-academicos-vocbench-2026-08-05.md`](HALLAZGO-programas-academicos-vocbench-2026-08-05.md)

---

## El hallazgo

Al revisar cómo las orgs `academic-program` identifican su programa apareció un defecto que no
estaba en el radar: **15 de las 23 orgs publican en `extension/sb:academicProgramUri` una URI que
el tesauro ya declaró sustituida.**

Es el mismo defecto que hoy se corrigió en las personas (resource Estudiantes v183/v184), pero en
las organizaciones. Nadie lo había tocado.

**Consecuencia inmediata:** tras la reconciliación del 6-ago, un estudiante de Medicina publicará
`programa/medicina-humana` mientras **su propia org publica `c_353ae8f7`**. Cualquier consumidor
que cruce persona↔programa por URI —RIMS, InOut, Pulso DTI— verá dos identificadores distintos
para el mismo programa.

## Cómo identifican su programa (respuesta a la pregunta de origen)

Por **`EP-XXX`**, en tres sitios a la vez:

```xml
<name>EP-ARQ</name>
<identifier>EP-ARQ</identifier>
<extension>
  <sb:academicProgramCode>EP-ARQ</sb:academicProgramCode>
  <sb:academicProgramUri>…/c_e399e0aa</sb:academicProgramUri>   ← obsoleta
```

🔴 **Corolario para el prompt de VocBench** (`PROMPT-consumir-puente-tesauro-2026-08-05.md` §2):
propone que `academicProgramCode` del usuario lleve el **P-code**. El bloque **D6** del
`user-template-student` asigna la org desde ese atributo y **espera `EP-XXX`**. Cambiarlo solo en
el usuario dejaría a los ~25.000 estudiantes sin organización de programa. Si se adopta el P-code,
hay que migrar **a la vez** las 23 orgs y D6, en una sola operación.

## Las 15 orgs y su destino

| Org | URI actual | URI canónica |
|---|---|---|
| `EP-ARQ` | `c_e399e0aa` | `programa/arquitectura-y-urbanismo` |
| `EP-ICIV` | `c_be8b346d` | `programa/ingenieria-civil` |
| `EP-SIS` | `c_bbf436cf` | `programa/ingenieria-de-sistemas` |
| `EP-ENF` | `c_c5f87ee9` | `programa/enfermeria` |
| `EP-MED` | `c_353ae8f7` | `programa/medicina-humana` |
| `EP-PSI-FCS` | `c_b48bff58` | `programa/psicologia` |
| `EP-PSI-FCHE` | `programa/psicologia-fche` | `programa/psicologia` |
| `EP-CON` | `programa/contabilidad-gestion-tributaria` | `…-y-aduanera` |
| `EP-EDU-CIN` | `programa/educacion-ciencias-naturales` | `…-especialidad-ciencias-naturales-y-tecnologia` |
| `EP-EDU-EFI` | `programa/educacion-educacion-fisica` | `…-especialidad-educacion-fisica-recreacion-y-deportes` |
| `EP-EDU-IES` | `programa/educacion-ingles-espanol` | `…-especialidad-ingles-y-espanol` |
| `EP-EDU-INI` | `programa/educacion-inicial` | `…-inicial-y-puericultura` |
| `EP-EDU-MAT` | `programa/educacion-matematica` | `…-especialidad-matematica-analisis-datos-y-computacion` |
| `EP-EDU-MUA` | `programa/educacion-musica-artes` | `…-especialidad-musica-y-artes-visuales` |
| `EP-EDU-PRI` | `programa/educacion-primaria` | `…-primaria-y-pedagogia-terapeutica` |

Las otras 8 ya publican la URI canónica y **no se tocan**.

⚠️ **`EP-PSI-FCS` y `EP-PSI-FCHE` acabarían con la MISMA URI** (`programa/psicologia`). Son dos
escuelas —Ciencias de la Salud y Ciencias Humanas y Educación— que el tesauro fusionó en un
concepto. Es coherente con el tesauro pero **pierde la distinción entre ambas**. Decidir antes de
aplicar: o se asume la fusión, o el tesauro debe volver a separarlas (es la misma cuestión abierta
del `PROMPT-migrar-15-epcodes`, §colisión de Psicología).

## 🔴 Esto SÍ dispara provisioning a LDAP

`academicProgramUri` tiene un outbound en el resource `ldap-identity-cache` bajo
**`kind=generic` / `intent=ou`** (línea ~15246): la URI de la org **se proyecta a su OU**.

No es un cambio de metadato. Es la misma lección del incidente de sedes de esta mañana —*toda org
proyecta a LDAP*—, con una diferencia que reduce el riesgo: allí se cambió el `identifier`, que
gobierna el **DN** y exige un rename que el conector no soporta; **aquí solo cambia el valor de un
atributo**, que sí es un `modify` normal.

**No tocar `identifier` ni `name`.** Solo `extension/sb:academicProgramUri`.

## Procedimiento

### Paso 1 — Simulación

```bash
curl -s -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" -X POST \
  "$MIDPOINT_URL/midpoint/ws/rest/tasks" -H "Content-Type: application/xml" \
  --data-binary @sim-orgs-uri.xml
```

Task de `reconciliation` sobre `ldap-identity-cache`, `kind=generic` / `intent=ou`, con
`<execution><mode>preview</mode></execution>`. Leer el `SimulationResult` **cuando la task cierre**
(las métricas no se materializan antes) y comprobar que solo aparecen `MODIFIED` sobre las 15 OUs,
sin ningún `ADDED` ni cambio de DN.

### Paso 2 — Canario

Aplicar **una sola** org (`EP-MED`, la de menor riesgo por tener destino inequívoco) y verificar
en LDAP con `ldapsearch` que la OU cambió el atributo y **conserva su DN y sus hijos**.

### Paso 3 — Resto

Las 14 restantes. PATCH individuales ya generados en el scratchpad
(`orgs-uri/EP-*.xml`, uno por org), todos de la forma:

```xml
<itemDelta>
  <t:modificationType>replace</t:modificationType>
  <t:path xmlns:sb="urn:sciback:midpoint:person">extension/sb:academicProgramUri</t:path>
  <t:value>…URI canónica…</t:value>
</itemDelta>
```

### Paso 4 — Verificación

- Ninguna org con URI que tenga `dct:isReplacedBy` en el tesauro.
- Las 23 OUs conservan su DN y su jerarquía.
- Coherencia persona↔org: un estudiante de Medicina y su org publican la misma URI.

## Reversión

Volver a poner la URI anterior con el mismo `replace`. No hay cambio de DN, así que no aplica el
problema de shadows huérfanos que bloqueó la reversión en el incidente de sedes.
