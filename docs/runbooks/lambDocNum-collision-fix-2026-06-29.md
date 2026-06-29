# Runbook — Fix colisión `extension/lambDocNum`/`lambDocType` (CE vs DNI) (2026-06-29)

> Segunda colisión single-valued del mismo patrón que `givenName`
> (ver `givenName-collision-fix-2026-06-29.md`), en otro item.

## Síntoma

Al re-correr el lote EP-PSI-FCS (tras el fix de givenName), 13/40 fallan con:

```
SchemaException: Strong mappings provided more than one value for single-valued
item extension/lambDocNum: [CE:001253556, 01253556]
```

## Causa raíz

`extension/upeu:lambDocNum` y `extension/upeu:lambDocType` son **single-valued**.
Tres resources los escriben `strong`: `trabajadores` (ELISEO), `estudiantes` y
`egresados` (ambos MOISES). En personas con **doble afiliación worker+alum/student**,
dos fuentes clasifican el MISMO documento con **distinto tipo**:

Caso canario verificado en vivo — Gabriela (uid 201520472, OID `00c4ffd5-c2b0-4864-ac1e-654f14e8e85c`):

| Shadow | NUM_DOCUMENTO | TIPO_DOC | CANON_DOC produce |
|---|---|---|---|
| TRABAJADORES (ELISEO) | `001253556` | **1 = DNI** | `01253556` (rama DNI, zfill8) |
| EGRESADOS (MOISES) | `001253556` | **4 = CE** | `CE:001253556` (rama CE, zfill9, prefijo) |

Dos valores `strong` distintos en un item single-valued → `SchemaException` → aborta el clockwork.

Dos defectos encadenados:
1. **Colisión:** `estudiantes` YA tenía el desempate `liveAffiliationWorker == null`
   (cede a trabajadores con empleo vivo), pero **`egresados` NO lo tenía** → egresados
   (rama CE) competía contra trabajadores (rama DNI).
2. **Calidad de dato (Oracle):** **ELISEO (planilla) etiqueta a extranjeros como DNI por
   defecto**; MOISES (MDM de personas) trae el tipo correcto (CE). El número es el mismo.

## Alcance (PROD, solo lectura, 2026-06-29)

- `lambDocNum` con prefijo `CE:`: **546** · con `PP:`: **320**
- `lambDocType` = 4/6/31 (CE): **681** · = 7 (passport): **321**
- **CE-type con `lambDocNum` NO prefijado `CE:`** (mal etiquetados / en riesgo de colisión): **135**
- Passport-type sin prefijo `PP:`: **1**

De los 135, una parte son **stale single-source** (solo shadow TRAB, type=4 correcto en TRAB
pero lambDocNum viejo sin prefijo → se autocorrige al recompute, sin colisión); el resto son
**colisiones dual-source** worker+alum tipo Gabriela (ELISEO DNI vs MOISES CE). El blocker
inmediato del masivo es la colisión, no el etiquetado.

## ❌ Intento v1 (commit b098f78) — NO funcionó: condición sobre valor computado

v1 añadió a egresados el mismo desempate `<condition>liveAffiliationWorker == null</condition>`
que ya tenía estudiantes (heredado de 2026-06-15). **Reimportado en PROD y NO resolvió la
colisión.** Gabriela siguió fallando con `[CE:001253556, 01253556]` pese a tener
`liveAffiliationWorker="staff"` (NO null).

**Por qué falla (anti-patrón):** `liveAffiliationWorker` es un valor **computado por un inbound
en el mismo projector wave**. Usarlo como `<condition>` de OTRO inbound (egresados/lambDocNum)
es frágil: no está disponible/estable cuando se evalúa esa condición → la condición no suprime
el write de egresados → egresados sigue emitiendo `strong` y colisiona con trabajadores.
`strength` no arbitra entre dos `strong` que producen valor (mismo principio que givenName).

## Fix v2 canónico (artefactos listos, sin desplegar) — patrón robusto givenName

Se **abandona la condición** y se aplica EXACTAMENTE el patrón que SÍ funcionó para givenName:
**un único `strong` (trabajadores) por item single-valued; el resto `weak`.**

1. **FunctionLibrary** `canonical/function-libraries/sb-document-normalizer.xml`
   (OID `1c7e4b2d-3f5a-4061-ac9d-8f7e6d5c4b31`) — `toCanonicalDocNumber(rawNum, docType)` +
   `resolveDocClass(docType)`. Fuente única de la forma del documento (sin cambios desde v1).

2. **`trabajadores.xml`** → `lambDocNum` y `lambDocType` siguen **`strong` (ÚNICO winner)**,
   sin condición. lambDocNum vía `toCanonicalDocNumber`.

3. **`estudiantes.xml` y `egresados.xml`** → `lambDocNum`, `lambDocType` **y `taxId`
   (`dni-to-taxId-urn`) pasan a `weak`** y se les **retira la `<condition>` frágil**. Todas
   canonicalizan con la misma forma (función compartida / misma URN SCHAC).

4. **`taxId`** (latente, mismo patrón): trabajadores ya lo tenía `archived` (inactivo); ahora
   estudiantes/egresados → `weak`; reniec-cache se queda `normal` (solo emite `:DNI:`, RENIEC no
   tiene CE → no colisiona con los weak `:CE:`).

Determinismo (sin condiciones):
- solo-estudiante / solo-egresado → weak provee (no hay strong compitiendo) ✓
- trabajador+egresado (Gabriela) → trabajadores `strong` gana, egresados `weak` NO compite →
  **un solo valor** ✓
- estudiante+egresado puro (sin worker) → ambos weak; leen el mismo MOISES + misma función →
  string idéntico → sin colisión ✓

## ❌ v2 (commit a061839) — incompleto: faltó un 3.er resource (grados)

v2 aplicado y verificado en PROD (estudiantes/egresados weak), pero Gabriela SIGUIÓ colisionando
`[CE:001253556, 01253556]`. Inventario de los 6 shadows de Gabriela reveló un **tercer strong
oculto**: el resource **"Oracle LAMB Grados v1"** (`upeu/resources/oracle-lamb/grados.xml`, OID
`3b2d8c4a-6f17-4e90-a1d5-9c0e7b5a4f62`) tenía `num-documento-to-lambDocNum` **`strong`** (TIPO_DOC=4
CE → "CE:001253556") y `dni-to-taxId-urn` **`strong`**. Era el segundo strong que colisionaba con
trabajadores (DNI → "01253556"). Lección: hacer el **inventario exhaustivo de TODOS los resources**
antes de declarar cerrado un fix de colisión single-valued.

## Fix v3 (artefactos listos, sin desplegar) — cierra grados + inventario exhaustivo

3.b **`grados.xml`** → `num-documento-to-lambDocNum` (era strong) → **`weak`** + función compartida
`toCanonicalDocNumber`; `dni-to-taxId-urn` (era strong) → **`weak`**. (`lambDocType` ya era weak.)

### Inventario EXHAUSTIVO de escritores del documento del foco (verificado por audit de XML)

| Resource / fuente | lambDocNum | lambDocType | taxId |
|---|---|---|---|
| **trabajadores** (ELISEO) | **strong (ÚNICO winner)** | **strong (ÚNICO winner)** | archived ×2 (inactivo) |
| estudiantes (MOISES) | weak | weak | weak |
| egresados (MOISES) | weak | weak | weak |
| **grados (Sec. General)** | weak ✓ (era strong, v3) | weak | weak ✓ (era strong, v3) |
| reniec-cache | — | — | normal (solo `:DNI:`, sin CE) |
| koha-ils | — | — | — (no es target del foco) |
| datasets CSV (CRM/RRHH/SIS) | — | — | — |
| object-templates employee staff/faculty | — (solo comentario) | — | — (Bloque J **lee** lambDoc y escribe identityDocuments) |

**Resultado verificado por audit:** el ÚNICO escritor `strong` + `active` de `lambDocNum`/`lambDocType`
es `trabajadores`. Ningún `strong` activo escribe `taxId` (trabajadores archived; reniec normal;
resto weak). Política single-strong completa.

## ⚠️ Limitación conocida (NO bloquea el masivo) — etiquetado CE→DNI en worker-extranjeros

Con el patrón single-strong, en worker+alum tipo Gabriela **gana trabajadores/ELISEO** (único
strong), que puede traer el tipo MAL (DNI en vez de CE) — y ahora egresados (que tenía el CE
correcto) es `weak` y queda suprimido cuando trabajadores escribe. Consecuencia: su
`identityDocuments.type=DNI` y `schacPersonalUniqueID` quedan con tipo incorrecto (el número es
correcto). Esto es un **defecto de datos preexistente en Oracle (ELISEO)**, no introducido por
este fix; el masivo ya NO crashea. Remediación recomendada (fase aparte, decidir con el usuario):

- **Opción A (preferida, canónica):** invertir el IIA del **tipo** de documento: para
  `lambDocType` (y la rama de `lambDocNum`), MOISES > ELISEO cuando MOISES asserta no-DNI
  (`resolveDocClass != 'DNI'`). Implica un transporte del tipo MOISES legible por trabajadores
  o resolver el tipo en el template. iga-canonical §1.3 (el tipo es hecho MDM/legal, no de nómina).
- **Opción B:** sanitation task que, para los ~135, fije `lambDocType` desde la clase MOISES
  (egresados/estudiantes) y recompute.

El número canónico (`number` en identityDocuments) es correcto en ambos casos; sólo el `type`
y el subtipo SCHAC quedan por corregir en ese subconjunto.

## Plan de aplicación v2 en PROD (ejecutar con autorización del usuario)

> GitOps. Nunca `scp`. La FunctionLibrary `sb-document-normalizer` YA está en PROD (importada
> en v1, commit b098f78). v2 solo cambia strengths/condiciones en los 3 resources → basta
> reimportarlos.

### 1. Commit + push (local) — v3 solo toca grados.xml + docs

```bash
cd /Users/alberto/proyectos/upeu/midPointEcosystem
git add upeu/resources/oracle-lamb/grados.xml \
        docs/runbooks/lambDocNum-collision-fix-2026-06-29.md docs/IIA-MATRIX.md
git commit -m "fix(iga) v3: cierra colisión lambDocNum — grados (3.er strong oculto) a weak; inventario exhaustivo"
git push
```

### 2. Pull en PROD

```bash
source ~/.secrets/midpoint-upeu.env
sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
  "cd /home/juansanchez/midPointEcosystem && git pull --ff-only"
```

### 3. (FunctionLibrary ya presente — no reimportar)

`sb-document-normalizer` (OID `1c7e4b2d-3f5a-4061-ac9d-8f7e6d5c4b31`) ya está en PROD (v1).

### 4. Reimportar grados (overwrite por OID) — único resource cambiado en v3

```bash
set -a; source ~/.secrets/midpoint-upeu.env; set +a
oid=$(grep -m1 -oE 'oid="[0-9a-f-]{36}"' upeu/resources/oracle-lamb/grados.xml | head -1 | sed 's/oid="//;s/"//')
curl -s -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
  -H "Content-Type: application/xml" \
  -X PUT "$MIDPOINT_URL_PUBLIC/ws/rest/resources/$oid?options=overwrite" \
  --data-binary @upeu/resources/oracle-lamb/grados.xml
echo "  reimported grados ($oid)"   # esperado: 3b2d8c4a-6f17-4e90-a1d5-9c0e7b5a4f62
```

> Nota: estudiantes/egresados/trabajadores ya están en PROD con su versión v2 correcta (commit
> a061839); v3 no los modifica. Solo grados.

### 5. Test Connection (sanity)

```bash
# v3: basta probar grados (el único reimportado). Los demás ya estaban OK en v2.
for oid in 3b2d8c4a-6f17-4e90-a1d5-9c0e7b5a4f62; do
  curl -s -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
    -X POST "$MIDPOINT_URL_PUBLIC/ws/rest/resources/$oid/test" | grep -o '"status":"[a-z_]*"' | head -1
done
```

### 6. Recompute del canario Gabriela (OID `00c4ffd5-c2b0-4864-ac1e-654f14e8e85c`)

```bash
curl -s -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
  -H "Content-Type: application/xml" \
  -X POST "$MIDPOINT_URL_PUBLIC/ws/rest/rpc/executeScript" \
  --data-binary '<s:executeScript xmlns:s="http://midpoint.evolveum.com/xml/ns/public/model/scripting-3">
    <s:action><s:type>recompute</s:type></s:action>
    <s:input>
      <s:value xsi:type="c:UserType" xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <c:oid>00c4ffd5-c2b0-4864-ac1e-654f14e8e85c</c:oid>
      </s:value>
    </s:input>
  </s:executeScript>'
```

Esperado: status `success`, sin `SchemaException` de lambDocNum. (lambDocNum quedará
`01253556` por la limitación conocida ELISEO→DNI; eso es el item de remediación aparte.)

### 7. Re-correr el lote EP-PSI-FCS (40) y verificar 0 fatal_error de lambDocNum.

## Verificación

- `GET /users/00c4ffd5-...` → `extension/lambDocNum` single value, recompute `success`.
- Re-medir alcance: el conteo "CE-type con lambDocNum NO prefijado CE:" debe BAJAR (los
  stale single-source se autocorrigen; los dual-worker quedan por la limitación conocida).
- Lote EP-PSI-FCS: 0 `SchemaException` de `lambDocNum`.

## Rollback

`git revert` del commit v3 + reimport (PUT overwrite) de `grados.xml` con la versión previa.
La FunctionLibrary es aditiva (puede quedar o borrarse después).

## Post-mortem / lección

La colisión single-valued no se cierra hasta que **TODOS** los inbound `strong` activos al item
quedan reducidos a uno solo. Se necesitaron 3 iteraciones porque el inventario inicial no fue
exhaustivo (v1 condición frágil; v2 cubrió estudiantes/egresados pero omitió grados). **Antes de
declarar cerrado:** correr el audit de XML que lista TODO escritor `strong`+`active` del item
(ver sección "Inventario EXHAUSTIVO") y confirmar que solo queda trabajadores.
