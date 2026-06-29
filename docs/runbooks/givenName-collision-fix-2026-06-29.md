# Runbook — Fix colisión `givenName`/`familyName` por variantes de tilde (2026-06-29)

## Síntoma

Al recomputar personas (bulk action `recompute`) algunas fallan con `fatal_error`:

```
SchemaException: Strong mappings provided more than one value for single-valued
item givenName: [Rubi Nelida, Rubi Nélida]
```

Bloquea el backfill masivo MidPoint→LDAP (consumido por RIMS).

## Causa raíz

`givenName`/`familyName` son **single-valued** en `UserType`. Dos inbound mappings
`strong` los escribían simultáneamente en personas con **doble afiliación**:

| Fuente | Mapping | Valor para DNI 76732620 (Rubi) |
|---|---|---|
| `resource:trabajadores` (OID `6a91f7e1-...-0e0e21`) | `nombre-to-givenName` (strong, passthrough de `NOMBRE`) | `Rubi Nélida` (CON tilde — Oracle ya lo trae bien) |
| `resource:reniec-cache` (OID `c4d5e6f7-...-789abc`) | `reniec-content-to-givenName` (strong, Title Case de JSON RENIEC) | `Rubi Nelida` (SIN tilde — RENIEC elimina diacríticos) |

`strength` **no arbitra** entre dos mappings que ambos producen valor: MidPoint intenta
materializar los dos en un item single-valued → `SchemaException`. La "excepción canónica"
del `IIA-MATRIX.md` (principal strong + override strong) era inválida para single-valued.

Hallazgo adicional crítico: **RENIEC entrega el nombre SIN tildes** (la API/portal los
elimina), así que ni siquiera es la fuente de mejor calidad para el display. trabajadores
ya trae el nombre con diacríticos correctos.

Las inbound corren ANTES del object template (pipeline focal: synchronization → inbound →
focus policy/template → outbound), así que el conflicto NO se puede arreglar en el template:
la `SchemaException` ocurre al consolidar los inbound. **El fix va en la capa inbound.**

## Alcance (medido en PROD, solo lectura, 2026-06-29)

- Personas con shadow `reniec-cache` validado (`dataQualityStatus=reniec_validated`): **1.449**
- De ellas, **trabajadores** (staff/faculty/employee) → 2 fuentes strong en colisión: **386** (caso roto principal)
- De ellas, **student/alum** → solo fuentes weak, riesgo residual de accent: **1.063**
- Disagreement canónico estudiantes↔egresados sobre el mismo DNI (muestra 115 comunes): **0** → tras canonicalizar, las fuentes académicas coinciden.

## Fix canónico aplicado (artefactos listos, sin desplegar)

1. **Nueva FunctionLibrary** `canonical/function-libraries/sb-name-normalizer.xml`
   (OID `0b6f3a1c-2d4e-4f5a-9b8c-7e6d5c4b3a2f`), función `toCanonicalName(raw)`:
   Title Case español + Unicode NFC + colapso de espacios. Fuente única de la forma del nombre.

2. **`trabajadores.xml`** → IIA **ÚNICO `strong`** de `givenName`/`familyName`.
   `givenName` ahora llama a `toCanonicalName`; `familyName` aplica la misma forma inline
   (concatena 2 sources). Conserva tildes correctas.

3. **`reniec-cache.xml`** → `givenName`/`familyName` degradados a **`weak` + `<condition>`
   last-resort** (solo rellenan si el foco aún no tiene valor). RENIEC sigue siendo IIA
   `strong` de `birthDate` y `dataQualityStatus` (sin colisión). Misma canonicalización.

4. **`estudiantes.xml` / `egresados.xml`** → siguen `weak`; ahora pasan por la misma
   canonicalización (`toCanonicalName` / forma idéntica inline) para que valores coincidentes
   sean byte-idénticos y no colisionen.

Resultado: **un único `strong`** por item single-valued; el resto `weak`. Colisión sólo posible
ante nombres genuinamente distintos (defecto de datos real, no silenciado).

## Plan de aplicación en PROD (ejecutar con autorización del usuario)

> GitOps. Nunca `scp`. Backup git tag antes de tocar resources.

### 1. Commit + push (local)

```bash
cd /Users/alberto/proyectos/upeu/midPointEcosystem
git add canonical/function-libraries/sb-name-normalizer.xml \
        upeu/resources/oracle-lamb/trabajadores.xml \
        upeu/resources/oracle-lamb/estudiantes.xml \
        upeu/resources/oracle-lamb/egresados.xml \
        upeu/resources/oracle-lamb/reniec-cache.xml \
        docs/IIA-MATRIX.md docs/runbooks/givenName-collision-fix-2026-06-29.md
git commit -m "fix(iga): colisión givenName single-valued por tildes (trabajadores único strong + sb-name-normalizer)"
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
  --data-binary @canonical/function-libraries/sb-name-normalizer.xml
# o, si ya existiera el OID: PUT a /functionLibraries/0b6f3a1c-2d4e-4f5a-9b8c-7e6d5c4b3a2f?options=overwrite
```

### 4. Reimportar los 4 resources (overwrite por OID)

```bash
for f in trabajadores estudiantes egresados reniec-cache; do
  oid=$(grep -m1 -oE 'oid="[0-9a-f-]{36}"' upeu/resources/oracle-lamb/$f.xml | head -1 | sed 's/oid="//;s/"//')
  curl -s -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
    -H "Content-Type: application/xml" \
    -X PUT "$MIDPOINT_URL_PUBLIC/ws/rest/resources/$oid?options=overwrite" \
    --data-binary @upeu/resources/oracle-lamb/$f.xml
  echo "  reimported $f ($oid)"
done
```

### 5. Test Connection de los 4 resources (sanity)

```bash
for oid in 6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21 6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22 \
           6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23 c4d5e6f7-a8b9-0123-cdef-123456789abc; do
  curl -s -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
    -X POST "$MIDPOINT_URL_PUBLIC/ws/rest/resources/$oid/test" | grep -o '"status":"[a-z_]*"' | head -1
done
```

### 6. Recompute del usuario canario (Rubi, OID `006dc348-25ab-4a32-b95f-20f425f7d3e2`)

`/users/{oid}/recompute` da 404 en este deploy → usar bulk action vía `executeScript`:

```bash
read -r -d '' RECOMPUTE <<'XML'
<executeScriptResponse/>
XML
curl -s -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
  -H "Content-Type: application/xml" \
  -X POST "$MIDPOINT_URL_PUBLIC/ws/rest/rpc/executeScript" \
  --data-binary '<s:executeScript xmlns:s="http://midpoint.evolveum.com/xml/ns/public/model/scripting-3">
    <s:action>
      <s:type>recompute</s:type>
    </s:action>
    <s:input>
      <s:value xsi:type="c:UserType" xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <c:oid>006dc348-25ab-4a32-b95f-20f425f7d3e2</c:oid>
      </s:value>
    </s:input>
  </s:executeScript>'
```

Esperado: status `success`, sin `SchemaException`. Verificar `givenName=Rubi Nélida` (CON tilde).

### 7. Recompute del lote EP-PSI-FCS (40 personas) y verificar 0 fatal_error

Repetir el `executeScript recompute` con un `<s:input>` de búsqueda por programa
(`eduPersonOrgUnitDN`/afiliación de EP-PSI-FCS) o por la lista de OIDs del lote ya usada.
Criterio de éxito: las personas con doble afiliación que antes daban `fatal_error` ahora
materializan `schacPersonalUniqueID` + `eduPersonOrgUnitDN` en LDAP sin error.

## Verificación post-fix

- REST: `GET /users/006dc348-...` → `givenName` con tilde, single value.
- LDAP (read-only, `~/.secrets/ldap-rims-reader.env`): `givenName` del uid 201420732 = `Rubi Nélida`.
- Re-correr el conteo de `dataQualityStatus=reniec_validated` no debe cambiar (la calidad RENIEC sigue marcándose).

## Rollback

`git revert` del commit + reimport (PUT overwrite) de las 4 resources con la versión previa.
La FunctionLibrary nueva es aditiva (no rompe nada si queda); puede borrarse después.
