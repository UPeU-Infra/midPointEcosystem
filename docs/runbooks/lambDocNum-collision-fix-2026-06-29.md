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

## Fix canónico aplicado (artefactos listos, sin desplegar)

1. **Nueva FunctionLibrary** `canonical/function-libraries/sb-document-normalizer.xml`
   (OID `1c7e4b2d-3f5a-4061-ac9d-8f7e6d5c4b31`):
   - `toCanonicalDocNumber(rawNum, docType)` → número type-aware con prefijo CE:/PP:
     (DNI 1/24 zfill8; CE 4/6/31/22/23 zfill9 + `CE:`; PASS 7/9 `PP:`+upper).
   - `resolveDocClass(docType)` → `DNI|CE|PASS|OTHER`.
   - **Fuente única** de la forma del documento (elimina las 3 copias inline de CANON_DOC).

2. **`egresados.xml`** → `num-documento-to-lambDocNum` y `id-tipodocumento-to-lambDocType`
   reciben el **mismo desempate `liveAffiliationWorker == null`** que ya tenía estudiantes.
   Con empleo vivo, egresados cede → gana trabajadores → **un único strong** → sin colisión.
   En `beforeCorrelation` el focus aún no está cargado → condición true → SÍ emite la clave de
   correlación (cero regresión de correlación). lambDocNum vía función compartida.

3. **`estudiantes.xml` / `trabajadores.xml`** → `lambDocNum` ahora llama a
   `toCanonicalDocNumber` (mismo output byte-idéntico para igual `(num,type)`), eliminando
   la copia inline. trabajadores sigue `strong` sin condición (IIA con empleo vivo).

Resultado: **un único `strong`** efectivo por item single-valued (trabajadores cuando hay
empleo vivo; si no, estudiantes/egresados, que leen el mismo MOISES y producen el mismo
string). Colisión sólo posible entre dos fuentes MOISES con tipos genuinamente distintos
(no observado: ambas leen `MOISES.PERSONA_NATURAL`).

## ⚠️ Limitación conocida (NO bloquea el masivo) — etiquetado CE→DNI en worker-extranjeros

Con el desempate, en worker+alum tipo Gabriela **gana trabajadores/ELISEO**, que puede traer
el tipo MAL (DNI en vez de CE). Consecuencia: su `identityDocuments.type=DNI` y
`schacPersonalUniqueID` quedan con tipo incorrecto (el número es correcto). Esto es un
**defecto de datos preexistente en Oracle (ELISEO)**, no introducido por este fix; el masivo
ya NO crashea. Remediación recomendada (fase aparte, decidir con el usuario):

- **Opción A (preferida, canónica):** invertir el IIA del **tipo** de documento: para
  `lambDocType` (y la rama de `lambDocNum`), MOISES > ELISEO cuando MOISES asserta no-DNI
  (`resolveDocClass != 'DNI'`). Implica un transporte del tipo MOISES legible por trabajadores
  o resolver el tipo en el template. iga-canonical §1.3 (el tipo es hecho MDM/legal, no de nómina).
- **Opción B:** sanitation task que, para los ~135, fije `lambDocType` desde la clase MOISES
  (egresados/estudiantes) y recompute.

El número canónico (`number` en identityDocuments) es correcto en ambos casos; sólo el `type`
y el subtipo SCHAC quedan por corregir en ese subconjunto.

## Plan de aplicación en PROD (ejecutar con autorización del usuario)

> GitOps. Nunca `scp`. Tag git de backup antes de tocar resources.

### 1. Commit + push (local)

```bash
cd /Users/alberto/proyectos/upeu/midPointEcosystem
git add canonical/function-libraries/sb-document-normalizer.xml \
        upeu/resources/oracle-lamb/trabajadores.xml \
        upeu/resources/oracle-lamb/estudiantes.xml \
        upeu/resources/oracle-lamb/egresados.xml \
        docs/runbooks/lambDocNum-collision-fix-2026-06-29.md
git commit -m "fix(iga): colisión lambDocNum single-valued (CE vs DNI) — desempate egresados + sb-document-normalizer"
git push
```

### 2. Pull en PROD

```bash
source ~/.secrets/midpoint-upeu.env
sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no midpoint-prod \
  "cd /home/juansanchez/midPointEcosystem && git pull --ff-only"
```

### 3. Importar la FunctionLibrary PRIMERO (los resources la referencian)

```bash
set -a; source ~/.secrets/midpoint-upeu.env; set +a
curl -s -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
  -H "Content-Type: application/xml" \
  -X POST "$MIDPOINT_URL_PUBLIC/ws/rest/functionLibraries" \
  --data-binary @canonical/function-libraries/sb-document-normalizer.xml
# si ya existiera: PUT /functionLibraries/1c7e4b2d-3f5a-4061-ac9d-8f7e6d5c4b31?options=overwrite
```

### 4. Reimportar los 3 resources (overwrite por OID)

```bash
for f in trabajadores estudiantes egresados; do
  oid=$(grep -m1 -oE 'oid="[0-9a-f-]{36}"' upeu/resources/oracle-lamb/$f.xml | head -1 | sed 's/oid="//;s/"//')
  curl -s -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
    -H "Content-Type: application/xml" \
    -X PUT "$MIDPOINT_URL_PUBLIC/ws/rest/resources/$oid?options=overwrite" \
    --data-binary @upeu/resources/oracle-lamb/$f.xml
  echo "  reimported $f ($oid)"
done
```

### 5. Test Connection (sanity)

```bash
for oid in 6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21 6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22 \
           6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23; do
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

`git revert` del commit + reimport (PUT overwrite) de los 3 resources con la versión previa.
La FunctionLibrary es aditiva (puede quedar o borrarse después).
