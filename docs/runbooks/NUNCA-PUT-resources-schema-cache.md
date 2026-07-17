# 🔴 NUNCA despliegues un resource con PUT — usa PATCH del elemento concreto

> **Regla:** en este repo, `PUT` sobre un `ResourceType` desplegado es una operación **destructiva**.
> Se despliega **siempre con `PATCH`** del elemento que cambia.
> **Medido el 2026-07-17: afecta a 8 de los 11 resources desplegados.** No es un caso especial de
> un resource: es la forma normal del repo.

## Por qué

Un `ResourceType` de MidPoint lleva un elemento **`<schema>` cacheado**: el schema del recurso tal
como el conector lo devolvió la última vez (`retrievalTimestamp`). **Ese cache lo genera y lo posee
PROD, no el repo.** El repo versiona la *configuración* (connectorConfiguration, schemaHandling,
synchronization); el `<schema>` es *estado en runtime*.

`PUT` = *reemplaza el objeto entero*. Por tanto el `<schema>` de PROD se sustituye por lo que traiga
el fichero del repo. Y ahí hay **dos** formas de romperlo, opuestas y con el mismo final:

| | Qué tiene el repo | Qué hace el PUT | Resultado |
|---|---|---|---|
| **Tipo 1** | **ningún `<schema>`** | **arranca** el cache de PROD | resource sin schema → `ConfigurationException` → **502** / `broken` |
| **Tipo 2** | un `<schema>` **stale o vacío** | **pisa** el cache bueno con el viejo | MidPoint valida el `schemaHandling` contra un schema que no tiene esos atributos → referencia huérfana → **502** / `broken` |

### Precedentes reales (no es teórico)

- **`a776e5a`** — **en `trabajadores.xml` (e21), este mismo resource.** El `<schema>` cacheado quedó
  stale (`retrievalTimestamp` 2026-06-29, anterior al F5-prep de `TEACHING_PROGRAMS`). MidPoint
  validó el `schemaHandling` contra ese cache viejo → `ConfigurationException: attribute
  TEACHING_PROGRAMS not found` → **el reconcile de foco completo de docentes abortaba con 502**.
  Se curó con un **test connection** (regenera el cache desde el `schemaScript` actual).
- **`670b312` / `8ab4dc9`** — `ldap-identity-cache.xml` (`7b4e1c2d-…`) quedó **`broken`** tras un PUT.
  De ahí la regla ya escrita para ese resource: **solo PATCH**.

## Censo — 8 de 11 desplegados son PUT-peligrosos (medido 2026-07-17)

Método: `<schema>` presente en `m_resource.fullObject` (PROD, psql) vs `<schema>` en el fichero del
repo, comparando los `xsd:element name="…"` declarados.

**Tipo 1 — el repo NO lleva `<schema>` y PROD SÍ (un PUT lo arranca). Los 7 de la familia Oracle LAMB ScriptedSQL:**

| Resource | OID |
|---|---|
| Oracle LAMB **Trabajadores v3** | `6a91f7e1-…-0e21` |
| Oracle LAMB **Estudiantes v3** | `6a91f7e1-…-0e22` |
| Oracle LAMB **Egresados v3** | `6a91f7e1-…-0e23` |
| Oracle LAMB **Grados v1** | `3b2d8c4a-…` |
| Oracle LAMB **Org** | `9e2f4c7a-…` |
| **LAMB-Oracle-Posiciones** | `f2422f42-…` |
| Oracle LAMB **RENIEC Cache v1** | `c4d5e6f7-…` |

**Tipo 2 — el repo lleva `<schema>` pero vacío/stale:**

| Resource | Repo | PROD | Un PUT… |
|---|---|---|---|
| **UPEU-EntraID-Graph** (`2f11c057-…`) | `<schema>` con **0** `xsd:element` | **6** (`accountEnabled`, `displayName`, `mailEnabled`, `mailNickname`, `securityEnabled`, `userPrincipalName`) | **borra los 6** |

**Aparentemente sanos a granularidad de elemento** (repo == PROD): `koha-ils.xml` (9=9),
`ldap-identity-cache.xml` (23=23), `rims-sciback-scim.xml` (0=0).

> ⚠️ **`ldap-identity-cache` mide "igual" y aun así un PUT lo dejó `broken` (`670b312`).** Mi
> instrumento compara **nombres de `xsd:element`**: es demasiado grueso para ver deriva a nivel de
> *atributo*, anotación o `retrievalTimestamp`. **"Igual a granularidad de elemento" NO es "seguro
> de hacer PUT".** El incidente documentado gana sobre mi medición. La regla es la misma para todos:
> **PATCH**.

## Qué hacer en su lugar

`PATCH` con un `objectModification` que toque **solo** el elemento que cambia. Ejemplo real
(fix del `__UID__` de e21, 2026-07-17 — aplicado, HTTP 204, `version` 315→316):

```xml
<objectModification xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3"
    xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
    xmlns:t="http://prism.evolveum.com/xml/ns/public/types-3"
    xmlns:icfc="http://midpoint.evolveum.com/xml/ns/public/connector/icf-1/connector-schema-3"
    xmlns:cfg="http://midpoint.evolveum.com/xml/ns/public/connector/icf-1/bundle/net.tirasa.connid.bundles.db.scriptedsql/net.tirasa.connid.bundles.db.scriptedsql.ScriptedSQLConnector">
    <itemDelta>
        <t:modificationType>replace</t:modificationType>
        <t:path>c:connectorConfiguration/icfc:configurationProperties/cfg:searchScript</t:path>
        <t:value><!-- el searchScript nuevo, XML-escapado --></t:value>
    </itemDelta>
</objectModification>
```

```bash
curl -X PATCH "$MIDPOINT_URL/midpoint/ws/rest/resources/<oid>" \
  -u "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS" \
  -H 'Content-Type: application/xml' --data-binary @patch.xml     # -> HTTP 204
```

**Verificación obligatoria después** (no lo asumas — es justo lo que fuiste a evitar):

1. `<schema>` sigue ahí y con sus elementos → psql sobre `m_resource.fullObject`.
2. **Test connection** → `POST .../resources/<oid>/test` → todo `success`.
3. `schemaHandling` / `capabilities` / `connectorRef` **intactos**.

> Nota: el PATCH **re-serializa** el `<schema>` (p. ej. reordena las declaraciones `xmlns`). Eso es
> **benigno**: mismo conjunto de caracteres, mismos `xsd:element`. Compara **contenido**, no bytes,
> o te asustarás sin motivo.

## Si ya la liaste (resource `broken` / 502)

**Test connection.** Regenera el `<schema>` cacheado desde el conector (para los ScriptedSQL, desde
el `schemaScript` actual). Es lo que curó el incidente `a776e5a`. Si no basta, restaura el objeto
desde el backup del resource.

## GitOps: por qué esto NO es "el repo está mal"

El repo **no es fiel a PROD en `<schema>`, y es correcto que no lo sea**: el `<schema>` es *estado en
runtime del conector*, no configuración. Versionarlo sería versionar un cache — y garantiza que se
quede stale (el tipo 2 de arriba). **El repo es fuente de verdad de la configuración; PROD es fuente
de verdad del `<schema>`.** Por eso el vehículo de despliegue es `PATCH`, no `PUT`.
