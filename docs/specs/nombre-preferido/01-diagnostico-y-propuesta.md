# Nombre preferido de persona: diagnóstico y propuesta de diseño

**Slug:** `nombre-preferido`
**Estado:** DISEÑO **probado en el laboratorio** (16-nov-2026, midPoint 4.11.0, datos sintéticos; resultados en el §12). No hay nada desplegado en PROD. Producción solo se leyó (GET por REST y `SELECT` en una transacción de solo lectura).
**Fecha:** 2026-11-16 (lecturas de PROD a las 15:55 y 15:57 UTC)
**Relacionado:** [`../nombre-oficial-reniec/01-diseno.md`](../nombre-oficial-reniec/01-diseno.md), sección «Nombre oficial» de [`CLAUDE.md`](../../../CLAUDE.md) (l. 79-90), `docs/upgrade-4.11/INVENTARIO-PROD-4.10.md:215`, `docs/upgrade-4.11/PLAN-Y-ROADMAP.md:59`.
**Skills consultadas:** `midpoint-best-practices` (§1.4, §4, §6 regla 2, §11.1, §11.3, §12) e `iga-canonical-standards` (§1.3 IIA, §3.1 eduPerson, §5.4 SCIM, §9, §11).

> Sin datos personales: solo conteos y ejemplos ficticios. El repo es público.

Convención de citas: `archivo:línea` (repo), URL (docs.evolveum.com), **[PROD-n]** (consulta a producción; lista en el §11) o **[KE]** (informe koha-expert del 16-nov). ❓ = sin verificar.

---

## 0. Resumen

1. **El hueco ya existe en PROD y está vacío.** midPoint 4.11.0 trae `UserType/preferredName` y `UserType/displayName`, los dos `PolyString`. Están en el XSD de `schema-4.11.0.jar` [PROD-6], tienen columna e índice en `m_user` y el cambio de BD 67 ya está aplicado [PROD-2]. Valores hoy: `preferredName` 0, `displayName` 0 y `nickName` 1 (una cuenta de sistema) [PROD-3]. La extensión canónica `sciback:preferredName` está declarada en el schema v35 de PROD, pero nunca se escribió: no tiene fila en `m_ext_item` [PROD-2][PROD-4]. **No hay nada que migrar.** Se recomienda el ítem **nativo** y dar de baja el de extensión.
2. **El nombre oficial no se toca.** `givenName`, `familyName` y `fullName` siguen siendo el nombre oficial, y en LDAP siguen saliendo a `cn`, `givenName` y `sn`. Solo `displayName` (el nativo y el de LDAP) pasa a ser «el preferido si existe; si no, el oficial».
3. **Una premisa del encargo no se sostiene.** Un inbound `normal` **no** se limita a los deltas: según la documentación de 4.11 «se comporta como strong» y también corre al cargar el shadow y en la reconciliación. El único filtro fiable es **`<channel>`** en el mapping (`liveSync`/`asyncUpdate`). Ver §3.2.
4. **Hoy solo hay una fuente real: la API REST (Discovery).** Ningún recurso puede ser fuente por live sync. LDAP no debe serlo, porque su `displayName` es un valor calculado y leerlo de vuelta provocaría un eco. Koha, Zammad y Entra no tienen `SyncOp`, o están en `proposed`. En PROD no hay ni una tarea de live sync [PROD-5]. El diseño deja preparado el inbound de Koha para cuando exista su `SyncOp` [KE].
5. **Discovery no puede apoyarse solo en el correo.** Con el correo institucional se identifica como mucho a ~62 % de las personas con cuenta LDAP: 11 953 de las 31 136 cuentas `account/default` no tienen `emailAddress` en MidPoint [PROD-7], y hay 59 direcciones institucionales repetidas que afectan a 121 usuarios [PROD-3]. La clave buena es `name` (= `uid` LDAP). Ver §6.
6. **Hay que coordinarlo con E1 (nombre oficial).** E1 **no está en PROD**: `UserTemplate-Nombre-Oficial` no figura entre las 7 plantillas de PROD [PROD-2], y el atributo LDAP `displayName` sigue en **`weak`** en PROD (v276) aunque el repo ya dice `strong` [PROD-4]. Las dos piezas tocan el mismo atributo 87: se hace **un solo** cambio.
7. **Probado en el laboratorio el 16-nov-2026** (midPoint 4.11.0, datos sintéticos, §12). Funciona, con tres correcciones: (a) las cuentas de Discovery y de autoservicio necesitan permiso de ejecución sobre sus `ShadowType`, porque sin él la API devuelve 403 **con el foco ya guardado** y LDAP sin escribir; (b) un 204 no garantiza que LDAP esté escrito (con LDAP caído también fue 204, con la operación pendiente); (c) el live sync de Koha necesita un feed limitado a `preferred_name` (R5 se reprodujo) y `errorHandling` para que un valor inválido no detenga la tarea. Las expresiones pasan a MEL.

---

## 1. Estado medido

### 1.1 midPoint 4.11 y el esquema de usuario

| Comprobación | Resultado | Fuente |
|---|---|---|
| Versión en PROD | `evolveum/midpoint:4.11.0-ubuntu` | [PROD-1] |
| `m_global_metadata.schemaChangeNumber` | 67 (el cambio 58 del inventario ya pasó) | [PROD-1]; `INVENTARIO-PROD-4.10.md:215` |
| Columnas `m_user` | `displaynameorig/norm`, `preferrednameorig/norm`, `nicknameorig/norm` | [PROD-2] |
| Índices | `m_user_displaynameorig_idx`, `m_user_preferrednameorig_idx` (btree sobre `orig`) | [PROD-2] |
| XSD `UserType/preferredName` | `t:PolyStringType`, «the name that the user prefers to use for display purposes. It does not replace legal-name attributes such as given name, family name, or full name, and it is not intended to be used as a login name, account identifier, or correlation identifier» | [PROD-6] |
| XSD `UserType/displayName` | `t:PolyStringType`, `a:access read` (calculado), «Effective visible name of the user … for UI, reporting, and outbound provisioning» | [PROD-6] |
| XSD `UserType/nickName` | «Familiar or otherwise informal way to address a person … usually changeable by the user itself» | [PROD-6] |
| Usuarios | 66 157; `preferredName` 0; `displayName` 0; `nickName` 1 (arquetipo *System user*) | [PROD-3] |
| Extensión `sciback:preferredName` / `displayPronouns` | Declaradas en el schema `e800335c…` v35 (l. 90-95 del objeto vivo), con 0 valores: no hay fila en `m_ext_item` | [PROD-2][PROD-4]; `canonical/schemas/sciback-person-v1.0.xml:88-93` |
| Plantilla 4.11 `Person Object Template` (`…0380`, v3) | Importada, con el mapping `generate-display-name` (MEL): `preferredName` si no está vacío, si no `fullName`, `range=all`. **No se aplica a nadie**: el arquetipo Person (`…0702`) y `defaultObjectPolicyConfiguration` de `UserType` apuntan a `UserTemplate-Person-Base` (`855caaca…`) | [PROD-4]; https://docs.evolveum.com/midpoint/release/4.11.0/ |
| `UserTemplate-Person-Base` en PROD (v143) | No menciona `displayName`, `preferredName` ni `nickName` | [PROD-4] |

La nota de la versión 4.11 confirma el diseño: «`displayName` was added to `UserType` and is populated by the default person object template from `preferredName`» y «Existing users may not have `displayName` populated immediately after upgrade» (https://docs.evolveum.com/midpoint/release/4.11.0/). En UPeU no se rellena porque esa plantilla no está en la cadena.

### 1.2 Destinos y posibles fuentes

| Recurso (PROD) | Cuentas vivas | Qué hace hoy con el nombre | ¿Live sync? | Fuente |
|---|---|---|---|---|
| LDAP-IdentityCache-UPeU (v276) | `default` 31 657 · `alumni` 28 899 | `cn` ← `fullName` strong; `givenName`/`sn` strong; **`displayName` ← `fullName` WEAK** (solo `account/default`; `alumni` no lo publica); `eduPersonNickname` existe en el esquema, sin mapping | Capacidad `liveSync` nativa, sin tarea | [PROD-4][PROD-7]; repo `ldap-identity-cache.xml:14145-14185`, `:14341-14355` (el repo dice strong: **drift**), `:11987` |
| Koha ILS UPeU consolidado (v36911, conector 1.7.1) | 35 488 | `firstname` ← `givenName` y `surname` ← `familyName`, **normal**; inbounds **weak** a `givenName`/`familyName`; `preferred_name` en el esquema, **sin mapping** | No (sin `SyncOp`) | [PROD-4][PROD-7]; `koha-upeu.xml:677`, `:1004-1050`, `:2063-2128`; [KE] |
| Zammad UPeU (v37, conector 0.2.0) | 67 | `firstname` ← `givenName` **strong**; `lastname` ← `familyName` strong | No: el conector implementa `SearchOp, CreateOp, UpdateDeltaOp, DeleteOp`, no `SyncOp` | [PROD-4][PROD-7]; `connector-zammad/src/main/java/com/identicum/connectors/ZammadConnector.java:39-40` |
| UPEU-EntraID-Graph (v187) | 76 898 | objectType en **`proposed`** (inerte en producción); outbounds de `givenName`/`surname` con *gate* de canarios; `displayName` solo como inbound `proposed` | No se usa | [PROD-4]; `entra-id-graph.xml:13-27`, `:124`, `:355-365` |
| UPEU-AD (`ad-upeu.xml`) | — | En draft, no está entre los 12 recursos de PROD | — | [PROD-5] |

**Entra es solo nube.** `docs/ENTRA-ID-ESTRUCTURA-UPEU.md:34` y `:68-69` dicen «cloud-only, sin sync AD on-prem», con `onPremisesSyncEnabled: null` medido por Graph. Lo confirma la memoria del 19-oct («no hay sync con AD (todas cloud-only)»). Si un día se escribe en Entra, se escribe directamente por Graph, sin pasar por AD. ❓ No se volvió a medir hoy en Graph.

**Canales que PROD ha usado alguna vez** (`m_uri`): `init`, `user`, `objectImport`, `rest`, `import`, `reconciliation`, `recompute`, `discovery`. Nunca `liveSync` ni `asyncUpdate` [PROD-5].

### 1.3 Autoservicio y cuentas de servicio

- **Rol `End user` (`…0008`, v2):** 0 titulares [PROD-3]. Sus autorizaciones son las de fábrica: `#selfAll` en la GUI, `#read` sobre `self`, y `#modify` en ejecución solo de `credentials` y `assignment` [PROD-4].
- **Autenticación:** la política de seguridad de PROD (`…0120`) solo tiene `loginForm` (GUI) y `httpBasic` (REST) [PROD-4]. El módulo OIDC con Entra de `upeu/auth/oidc-entra-id.xml` no está desplegado y aún lleva marcadores `{{…}}`. **Hoy no existe autoservicio de MidPoint para las personas.**
- **Patrón de cuenta de servicio REST:** existe una sola, `svc-ai-identity`, con arquetipo `archetype-user-service-account` (`05ceed56…`) y el rol `role-svc-ai-identity-reader` (v3). El rol da `#read` sobre `UserType` con una lista de ítems permitidos, `#read` de `OrgType` (`name`, `displayName`, `identifier`) y `authorization-rest-3#all` [PROD-4]. En el repo está en `upeu/roles/system/role-svc-ai-identity-reader.xml:30-54` (desfasado: PROD añadió `parentOrgRef` y la lectura de Org).

---

## 2. Decisiones de modelo

### D1. Qué escribe la persona: su **nombre de pila preferido**, no un nombre completo libre — **decidida 16-nov-2026 (Alberto)**

La persona indica cómo quiere que la llamen («Liz», «Pepe», un nombre social). Los apellidos siguen siendo los oficiales.

**Decisión (Alberto, 16-nov-2026):** `displayName` = `preferredName` + " " + `familyName`, o `fullName` si no hay preferido. `givenName`, `familyName` y `fullName` no se tocan nunca.

- **Koha:** `preferred_name` sustituye a `firstname` al mostrar al lector y Koha lo rellena con `firstname` si queda vacío [KE] (`Koha/Patron.pm:261-264`). Es un nombre de pila.
- **eduPerson:** `eduPersonNickname` es «the informal name by which they are accustomed to be hailed» (`iga-canonical-standards` §3.1). SCIM `nickName` dice lo mismo (§5.1).
- **Zammad:** solo tiene `firstname`/`lastname`, así que encaja sin ambigüedad.
- **Riesgos menores:** con los apellidos fijos se limita la suplantación («Rector», nombre de otra persona) y la identificación en contexto académico sigue siendo posible.

**Diferencia con la plantilla de fábrica.** La 4.11 trata `preferredName` como un nombre completo (ejemplos del XSD: «Jack Smith», «Liz Johnson») y hace `displayName = preferredName ?: fullName`. Con D1, UPeU calcula `displayName = preferredName + ' ' + familyName` (y `fullName` si no hay preferido). Es una decisión canónica de SciBack y queda documentada aquí.
*Alternativa descartada:* un nombre completo libre en `preferredName`. Habría que moderar más, Koha mostraría «Liz Johnson Pérez Pérez» (preferred + surname) y obligaría a cada destino a partir el valor.

### D2. Ítem nativo `preferredName`, no la extensión

`midpoint-best-practices` §1.4 y §6 regla 2 («usar lo que ya existe»), e `iga-canonical-standards` §11 regla 1. El nativo tiene columna indexada, soporte en la GUI y semántica oficial de 4.11, y la extensión está vacía (§1.1).
**Migración:** no hace falta copiar nada (0 valores). Se marca `sciback:preferredName` como `a:deprecated` en `canonical/schemas/sciback-person-v1.0.xml` y en el schema de PROD; se retira en la versión siguiente. `01-spec.md:352` pasa a decir `preferredName` (nativo) → `eduPersonNickname`.

### D3. `displayPronouns`: fuera de la v1 — **decidido 16-nov-2026 (Alberto)**

LDAP no tiene `eduPersonDisplayPronouns`: no está en `upeu/ldap/ldifs/03-eduperson.ldif` ni en el esquema del recurso en PROD [PROD-7]. Ningún destino lo consume. Además, puede revelar identidad de género, un dato sensible según la Ley 29733. Se queda en la extensión, sin canal de escritura, hasta que haya un consumidor y una base legal. Alberto lo dejó fuera de la v1 el 16-nov-2026.

### D4. IIA del nombre preferido: la propia persona

`iga-canonical-standards` §1.3 (la tabla ya pone a «El usuario (self-service)» como IIA de la contraseña). **MidPoint guarda el valor y es la única fuente de distribución.** Los sistemas conectados son *canales de entrada* de la persona, no IIAs paralelas. De ahí sale la regla «gana el último cambio» (§3.3).

---

## 3. Diseño en MidPoint

### 3.1 Un solo escritor de `displayName`: la plantilla `UserTemplate-Nombre-Preferido`

Se sigue el mismo patrón que `UserTemplate-Nombre-Oficial` (`upeu/object-templates/UserTemplate-Nombre-Oficial.xml:7-13`): una plantilla pequeña que `UserTemplate-Person-Base` incluye con `includeRef` (como en `canonical/object-templates/UserTemplate-Person-Base.xml:65`). Es la **única** que escribe `displayName`. **Nadie** escribe `preferredName` en una plantilla.

```xml
<objectTemplate xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
                oid="ce40e768-5767-475f-a653-65d9753d6ff5">
  <name>UserTemplate-Nombre-Preferido</name>
  <description>Único escritor de displayName. displayName = preferredName + familyName (oficial)
    si hay preferido; si no, fullName (oficial). No toca givenName/familyName/fullName.</description>
  <mapping>
    <name>NP1-displayName-preferido-o-oficial</name>
    <strength>strong</strength>
    <source><path>preferredName</path></source>
    <source><path>familyName</path></source>
    <source><path>fullName</path></source>
    <expression>
      <script>
        <language>http://midpoint.evolveum.com/xml/ns/public/expression/language#mel</language>
        <code>
          cel.bind(p, stringify(preferredName).trim(),
            p != '' ? format.concatName([p, familyName])
                    : (isBlank(stringify(fullName)) ? nil : stringify(fullName)))
        </code>
      </script>
    </expression>
    <target>
      <path>displayName</path>
      <set><predefined>all</predefined></set>
    </target>
  </mapping>
</objectTemplate>
```

Probado tal cual en el laboratorio (§12, T2). Es el fichero `sistemas/nombre-preferido/objetos/11-UserTemplate-Nombre-Preferido.xml` del repo `UPeU-Infra/lab-identidad`. En 4.11 el mapping de una plantilla va en `<mapping>` (como la 380); `<item><ref>…<mapping>` también vale.

- `range=all`, igual que la plantilla 380 de 4.11 (https://docs.evolveum.com/midpoint/release/4.11.0/). Un ítem de un solo valor no tiene rango implícito (`midpoint-best-practices` §11.1), así que se declara. Esto exige que esta plantilla sea la única que escribe `displayName`. Hoy no lo escribe nadie [PROD-4].
- **En MEL, no en Groovy** (cambio tras el laboratorio). MEL funciona con los perfiles de expresión de 4.11 (una instalación nueva aplica `configuration` a plantillas y recursos, y ahí Groovy está prohibido) y en PROD, que no tiene perfiles. Así esta pieza nueva no engorda la migración F5 (`PLAN-Y-ROADMAP.md:59`). Lleva `<language>…#mel</language>` explícito, porque en PROD el lenguaje por defecto sigue siendo Groovy. ❓ Confirmar en la SIM PRE/POST de PROD que la 4.11 de PROD evalúa MEL (en el laboratorio no se puede probar Groovy sin tocar la configuración compartida con midPilot).
- **Saneado del valor de entrada** (recortar, juntar espacios, ≤ 40 caracteres, solo letras, espacio, guion y apóstrofo, sin dígitos): **lo valida quien escribe** (Discovery) y **MidPoint lo hace cumplir** con una regla de política global que rechaza la modificación si no cumple el patrón. Un mapping no sirve: escribiría sobre su propia fuente. Sintaxis probada en el laboratorio (§12, T6):

```xml
<!-- PATCH add a systemConfiguration (c:globalPolicyRule) -->
<globalPolicyRule>
  <name>NP-validar-preferredName</name>
  <policyConstraints>
    <and>
      <modification>                      <!-- solo si la operación CAMBIA preferredName -->
        <name>cambia-preferredName</name>
        <item>preferredName</item>
      </modification>
      <objectState>                       <!-- evalúa el estado DESPUÉS de la operación -->
        <name>preferredName-invalido</name>
        <expression><script>
          <language>http://midpoint.evolveum.com/xml/ns/public/expression/language#mel</language>
          <code>
            cel.bind(v, stringify(object.preferredName),
              v != '' &amp;&amp; (v.size() &gt; 40 || !v.matches(r"^\p{L}+(?:[ '-]\p{L}+)*$")))
          </code>
        </script></expression>
      </objectState>
    </and>
  </policyConstraints>
  <policyActions><enforcement/></policyActions>
  <focusSelector><type>UserType</type></focusSelector>
</globalPolicyRule>
```

  - El `<and>` con `<modification>` es imprescindible: sin él, un valor inválido heredado bloquearía **cualquier** otra modificación de la persona (las recons de Oracle incluidas). Medido: con un valor inválido puesto en *raw*, otra modificación pasa.
  - El rechazo es **HTTP 409** con el mensaje «Object state after operation matches constraint "preferredName-invalido"». Se aplica a todos los canales: REST, GUI y live sync (§3.2).
  - Pasa «Rector»: el patrón no filtra palabras. La mitigación sigue siendo D1 (apellidos fijos) y la auditoría (R6).
  - Rechaza una tilde en forma descompuesta (NFD: `e` + U+0301). **Discovery debe normalizar a NFC** antes de enviar.

### 3.2 Entradas desde recursos: solo por `<channel>`, nunca por reconciliación

Lo que dice la documentación de 4.11 (https://docs.evolveum.com/midpoint/reference/support-4.11/expressions/mappings/, sección *Normal Mappings*): «In inbound mappings, normal strength behaves similarly to strong». Un inbound normal se evalúa «whenever a shadow (account) is loaded into memory during processing» y se aplica «during reconciliation». **Por eso `strength=normal` no protege**: un inbound normal metería en la reconciliación diaria de Koha (09:15) el valor viejo que tenga Koha.

El filtro correcto es la **restricción de canal** del mapping, del mismo documento, sección *Channel Constraints*: `channel` «Limits application of this mapping only to specific channel». En el XSD, `channel`/`exceptChannel` están en `EvenMoreAbstractMappingType` y los heredan los inbounds: verificado en `schema-4.9.1.jar` y en `schema-4.11.0.jar` (`common-core-3.xsd`, l. 5619-5643), y **por comportamiento en 4.11** con un control negativo (§12, T7a/T7f): con `<channel>liveSync` la reconciliación no mete el valor; sin él, sí. Los URI de canal están en `SchemaConstants`/`Channel` (`…/channels-3#liveSync`, `#asyncUpdate`, `#reconciliation`, `#import`, `#recompute`, `#rest`, `#user`).

Además, para un destino de un solo valor el rango por defecto del inbound es `all` («The target value will be replaced», https://docs.evolveum.com/midpoint/reference/support-4.11/expressions/mappings/inbound-mapping/). El último evento que se procesa reemplaza el valor.

**Plantilla de inbound para Koha** (no se puede activar hasta que el conector tenga `SyncOp`, §4.3). Probada en el laboratorio con un CSV que imita a Koha (`firstname`, `surname`, `preferred_name`), porque el conector CSV sí tiene live sync:

```xml
<attribute>
  <ref>ri:preferred_name</ref>
  <inbound>
    <name>NP-koha-preferred-in</name>
    <lifecycleState>proposed</lifecycleState>          <!-- inerte hasta el canario -->
    <strength>strong</strength>
    <channel>http://midpoint.evolveum.com/xml/ns/public/common/channels-3#liveSync</channel>
    <channel>http://midpoint.evolveum.com/xml/ns/public/common/channels-3#asyncUpdate</channel>
    <source><name>firstname</name><path>$projection/attributes/ri:firstname</path></source>
    <expression><script>
      <language>http://midpoint.evolveum.com/xml/ns/public/expression/language#mel</language>
      <code>
        // Koha nunca deja preferred_name vacío: si es igual a firstname es «sin preferido» [KE]
        cel.bind(v, stringify(input).trim(),
          (v == '' || v.equalsIgnoreCase(stringify(firstname).trim())) ? nil : v)
      </code>
    </script></expression>
    <target><path>preferredName</path></target>
  </inbound>
</attribute>
```

Medido en el laboratorio (§12, T7): la reconciliación no lo mete; el live sync sí, y llega a LDAP en la misma operación; `preferred_name = firstname` o vacío borra el preferido (el rango `all` por defecto del inbound sobre un ítem de un solo valor); el eco de lo que MidPoint escribe no produce ningún delta.

**Dos condiciones para activarlo con Koha, confirmadas en el laboratorio:**

1. **El feed solo puede emitir cambios humanos de `preferred_name` (R5 confirmado).** Con un feed que manda el lector entero ante cualquier cambio, un evento **ajeno** (en la prueba, solo cambió `surname`) volvió a meter el `preferred_name` viejo que tenía la fuente y pisó el valor que la persona había puesto por Discovery. El `<channel>` no lo evita: el evento sí es de live sync. Por eso el `SyncOp` de koha-expert tiene que leer `action_logs`, emitir solo filas cuyo diff incluya `preferred_name` y excluir `interface='api'`/`svc_midpoint` [KE].
2. **La tarea de live sync necesita tolerar los rechazos de la regla de validación.** Un valor inválido que llega por live sync lo rechaza la regla del §3.1, pero **la tarea se queda `SUSPENDED` / `FATAL_ERROR`** y ya no procesa los cambios siguientes. Con este `controlFlow` la tarea termina en `PARTIAL_ERROR`, el valor inválido no entra (queda en la auditoría) y el resto sí:

```xml
<activity>
  <work><liveSynchronization><resourceObjects>…</resourceObjects></liveSynchronization></work>
  <controlFlow><errorHandling><entry>
    <situation><errorCategory>policy</errorCategory></situation>
    <reaction><ignore/></reaction>
  </entry></errorHandling></controlFlow>
</activity>
```

   El valor inválido se queda en Koha (el outbound `normal` no lo corrige). Además, conviene que la tarea de live sync tenga como dueño una cuenta de servicio propia: la auditoría registra como iniciador al dueño de la tarea.

### 3.3 «Gana el último cambio»

- **Mecanismo:** cada canal de entrada escribe `preferredName` directamente, solo cuando hay un evento real: `rest`/`user` (la persona en Discovery o en la GUI) o `liveSync` (la persona en Koha). Ningún proceso masivo lo escribe: ni `import`, ni `reconciliation`, ni `recompute`, ni los recursos de Oracle. El orden de procesamiento de MidPoint da el «último gana». Si llegan dos cambios a la vez, los resuelve el control de concurrencia del foco: el arquetipo Person tiene `conflictResolution/action=recompute` [PROD-4].
- **Eco:** MidPoint propaga el valor a Koha en el mismo clockwork. Cuando el evento de esa escritura vuelve por live sync, trae el mismo valor (no hace nada) y además lo filtra el `SyncOp` (`interface='api'`). LDAP **nunca** es fuente: su `displayName` es calculado (preferido + apellidos, o el oficial) y leerlo de vuelta metería el nombre oficial completo como «preferido».
- **¿Metadatos de valor o procedencia?** No hacen falta, y para este ítem tampoco hay de serie: en 4.11 la procedencia está activada por defecto solo en propiedades **multivalor** (https://docs.evolveum.com/midpoint/reference/support-4.11/concepts/metadata/), y `preferredName` es de un solo valor. Quién cambió qué y por qué canal queda en la auditoría (`ma_audit_event.channel` + `ma_audit_delta`), que es la evidencia para ISO 27001 A.5.16. Un esquema de transportes por fuente con marca de tiempo (como E1) solo se justificaría si una fuente no pudiera entregar *eventos*. ❓ Reabrirlo si el `SyncOp` de Koha no es viable.

### 3.4 Comportamiento por operación

| Operación (canal) | `preferredName` | `displayName` (foco) | Destinos |
|---|---|---|---|
| PATCH REST de Discovery (`rest`) / GUI (`user`) | cambia | se recalcula en el mismo clockwork | LDAP/Koha/Zammad se escriben en la misma operación; si LDAP no responde, queda operación pendiente y la respuesta **sigue siendo 204** (medido, §6.4); la completa la siguiente reconciliación |
| Recompute (`recompute`) | no se toca | idempotente (strong, `range=all`) | outbounds strong idempotentes; Koha `normal` no escribe si sus fuentes no cambian |
| Reconciliación Oracle (`reconciliation`/`import`) | no se toca: ningún recurso Oracle tiene inbound de `preferredName` (verificado en el repo) | se recalcula si cambia el nombre oficial | igual que hoy |
| Reconciliación Koha 09:15 (`reconciliation`) | no se toca: el inbound tiene `<channel>liveSync` | — | el outbound `normal` de `preferred_name` **no corrige deriva** en la reconciliación («Weak and normal mappings will not overwrite or delete a value», doc. de mappings; **medido en el laboratorio**, T7a). Se acepta, para no pisar al bibliotecario |
| Live sync Koha (futuro, `liveSync`) | cambia si el lector cambió `preferred_name` | se recalcula | se propaga a LDAP y Zammad; a Koha vuelve el mismo valor (no hace nada) |
| Alta de persona desde Oracle | vacío | = `fullName` | LDAP `displayName` = oficial; Koha `preferred_name` = `givenName` (lo mismo que haría Koha) |

---

## 4. Por recurso

### 4.1 LDAP-IdentityCache-UPeU: **solo destino**

| Atributo | Hoy (PROD) | Propuesta |
|---|---|---|
| `cn`, `givenName`, `sn` | oficial, strong | **sin cambio** (nombre oficial, `CLAUDE.md:79-90`) |
| `displayName` (`account/default`, attr id 87) | `weak` ← `fullName` | `strong` ← `$focus/displayName`, con `fullName` de respaldo |
| `displayName` (`account/alumni`) | no se publica | **añadir** el mismo mapping (28 899 cuentas; si no, Discovery no tendría nada que leer para los egresados) ❓ decisión |
| `eduPersonNickname` (multivalor) | sin mapping | `strong` ← `preferredName`, con `tolerant=false` si MidPoint es el único que lo escribe ❓ medir antes cuántas entradas LDAP lo tienen hoy |

```xml
<attribute id="87">
  <ref>ri:displayName</ref>
  <outbound>
    <name>NP-ldap-displayName</name>
    <strength>strong</strength>
    <source><path>$focus/displayName</path></source>
    <source><path>$focus/fullName</path></source>
    <expression><script>
      <language>http://midpoint.evolveum.com/xml/ns/public/expression/language#mel</language>
      <code>isBlank(stringify(displayName)) ? fullName : displayName</code>
    </script></expression>
  </outbound>
</attribute>
<attribute>
  <ref>ri:eduPersonNickname</ref>
  <tolerant>false</tolerant>
  <outbound>
    <name>NP-ldap-eduPersonNickname</name>
    <strength>strong</strength>
    <source><path>$focus/preferredName</path></source>
  </outbound>
</attribute>
```

Probado en el laboratorio (§12, T3/T5): `displayName` sale como preferido + apellidos y vuelve al oficial al borrar el preferido; `eduPersonNickname` aparece y desaparece; `cn`/`givenName`/`sn` no cambian; un recompute no produce ningún delta; la reconciliación repone un `displayName` alterado a mano y **retira** un `eduPersonNickname` añadido a mano (`tolerant=false`). Observación aparte: en esa misma prueba un `cn` añadido a mano **no** se retiró (el mapping de `cn` es tolerante y `cn` es multivalor en LDAP); revisar cómo está `cn` en PROD.

- **Choque con E1:** E1 propone el mismo atributo 87 `weak → strong` desde `fullName` (`03-e1-laboratorio.md:136`). Medido el 9-nov, ese cambio actualiza `displayName` a **7 115 activos** (~13 100 en total) (`04-medicion-prod.md:62-71`, `:137`). Se hace **un solo PATCH** con la expresión de arriba: cuando nadie tenga preferido, da lo mismo que E1. Ojo: hay drift entre el repo (`ldap-identity-cache.xml:14341-14355`, strong) y PROD (weak) [PROD-4]. Antes de nada, exportar el `schemaHandling` de PROD.
- El recurso se modifica **solo con PATCH del ítem**, verificando `version` y `?options=raw` (`CLAUDE.md`, «NUNCA PUT»; `midpoint-best-practices` §11.4).
- Discovery lee el `displayName` del LDAP al iniciar sesión, no del token: lo exige ADR-058, porque los atributos de Keycloak se quedan congelados (memoria del 27-ago). Ojo con la réplica `.169`: hay retardo de replicación.

### 4.2 Entra ID: **ni fuente ni destino por ahora**

El objectType está en `proposed` [PROD-4] y Entra es solo nube (§1.2). Cuando se active la escritura (Fase 12): `ri:displayName` ← `$focus/displayName` con el mismo *gate*; `givenName`/`surname` siguen siendo los oficiales. El inbound `ri:displayName → fullName` (`entra-id-graph.xml:355-365`, `proposed`) **no debe pasar nunca a `active`**: metería en el nombre oficial un nombre visible editable en M365.

### 4.3 Koha (consolidado, `koha-upeu.xml`): **destino ahora; fuente cuando haya `SyncOp`**

Hechos del informe koha-expert del 16-nov [KE]:
- Conector 1.7.1 en PROD (`pom.xml:8`, tag `v1.7.1`; confirmado [PROD-7]). Koha `.136` = 26.05.05. `koha-ils.xml` es histórico.
- Koha **nunca deja `preferred_name` vacío**: en cada `store()` lo rellena con `firstname` (`Koha/Patron.pm:261-264`). De 35 488 lectores: 0 vacíos, 35 460 iguales a `firstname` y 28 distintos (2 con cambio humano registrado). Si se manda null o vacío, Koha vuelve a poner `firstname`. Si MidPoint cambia `firstname`, `preferred_name` se queda con el valor viejo.
- El conector lee y escribe `preferred_name` (`PatronMapper.java:132`, `:180-195`, `:305-355`). Su PUT lee, superpone y escribe, así que no pisa el campo si MidPoint no lo manda (`PatronService.java:192-209`). Hoy no hay mapping `ri:preferred_name` (confirmado en el repo: solo `koha-upeu.xml:677`, esquema; y en PROD [PROD-4]).
- Sin `SyncOp`/`getLatestSyncToken` (`KohaConnector.java:39`). `updated_on` no sirve de cursor: 7 866 cambios en 24 h, casi todos ecos de `svc_midpoint`. Es viable un `SyncOp` por JDBC sobre `action_logs` (con `BorrowersLog=1` hay antes y después por campo, usuario e interfaz), con cursor `action_id` y excluyendo `interface='api'`/`svc_midpoint`. Requiere `GRANT SELECT` de `action_logs` a `koha_connector`, ~250-350 líneas y 1,5-2 días, con versión nueva del conector.
- En el OPAC el lector puede pedir el cambio (`OPACPatronDetails=1`). Queda en `borrower_modifications` y lo aprueba el personal (`AutoApprovePatronProfileSettings=0`). ⚠️ `PatronSelfModificationBorrowerUnwantedField` está vacío: **el lector también puede pedir cambios de `firstname`/`surname` (nombre oficial)**.

**Propuesta para el outbound (destino, fase 1):**

```xml
<attribute>
  <ref>ri:preferred_name</ref>
  <outbound>
    <name>NP-koha-preferred-out</name>
    <strength>normal</strength>
    <source><path>$focus/preferredName</path></source>
    <source><path>$focus/givenName</path></source>
    <expression><script><code>
def p = preferredName != null ? basic.stringify(preferredName).trim() : ''
p ?: (givenName != null ? basic.stringify(givenName).trim() : null)
    </code></script></expression>
  </outbound>
</attribute>
```

- **Por qué `normal` con respaldo `givenName`, y no la condición «no vacío» que sugiere koha-expert:**
  - Se respeta lo que pide koha-expert: no escribir en la reconciliación y no pisar al bibliotecario. `normal` solo escribe cuando cambian sus fuentes; `weak` nunca escribiría, porque el destino nunca está vacío; `strong` pisaría.
  - Además, si la persona **borra** su preferido, Koha vuelve a `givenName` (lo mismo que haría Koha por sí solo). Con «no vacío» se quedaría el valor viejo.
  - Y se corrige el defecto de que `preferred_name` se quede viejo cuando cambia el nombre oficial.
  - Coste: cuando cambie `givenName`, a quien tenga un valor puesto por el bibliotecario (≤ 28) se le reemplaza.
- **Los 35 460 que son copia de `firstname`:** no se tocan. `normal` no escribe sin cambio en las fuentes, y el valor coincide de todos modos.
- **Los 28 distintos:** decidir si se siembran una vez en MidPoint, revisados y con auditoría (PATCH de administrador, no inbound), o si se descartan. ❓ Decisión de Alberto o del CRAI.
- **Antes de abrir Koha como fuente:** que el CRAI ponga `firstname`, `surname` (y `middle_name`) en `PatronSelfModificationBorrowerUnwantedField`. Esos cambios hoy pasarían en Koha sin que MidPoint los corrija, porque el outbound `normal` no corrige en la reconciliación. ❓ Lo ve koha-expert.

### 4.4 Zammad: **solo destino**

PROD (v37): `firstname` ← `givenName` strong y `lastname` ← `familyName` strong [PROD-4]. El recurso **no está en el repo** (drift de GitOps: hay que versionarlo). El conector 0.2.0 no tiene `SyncOp` (`ZammadConnector.java:39-40`). Propuesta: `firstname` strong ← `preferredName ?: givenName`; `lastname` sin cambio. Son 67 cuentas, agentes y clientes de la mesa [PROD-7]. Zammad no es un registro legal, así que el preferido es lo correcto allí.

---

## 5. Autoservicio en MidPoint (GUI)

**Hoy no es viable para las personas:** el rol End user tiene 0 titulares y no hay módulo OIDC (§1.3). Se deja preparado el rol, para cuando haya inicio de sesión federado (proyecto aparte):

```xml
<role oid="27f7c7bd-4b6c-43cd-8368-90e31a847867">
  <name>role-self-preferred-name</name>
  <authorization>
    <name>self-preferred-name-request</name>
    <action>http://midpoint.evolveum.com/xml/ns/public/security/authorization-model-3#modify</action>
    <phase>request</phase>
    <object><special>self</special></object>
    <item>preferredName</item>
  </authorization>
  <authorization>
    <name>self-preferred-name-execution</name>
    <action>http://midpoint.evolveum.com/xml/ns/public/security/authorization-model-3#modify</action>
    <phase>execution</phase>
    <object><special>self</special></object>
    <!-- sin <item>: en ejecución se modifican también displayName y lo que la plantilla
         recalcule; la puerta real es la fase request (patrón del rol End user, id 10) -->
  </authorization>
  <authorization>
    <name>self-preferred-name-shadows-execution</name>
    <!-- OBLIGATORIA (laboratorio 16-nov): sin ella, 403 con el foco YA cambiado y las cuentas no -->
    <action>http://midpoint.evolveum.com/xml/ns/public/security/authorization-model-3#add</action>
    <action>http://midpoint.evolveum.com/xml/ns/public/security/authorization-model-3#modify</action>
    <phase>execution</phase>
    <object><type>ShadowType</type><owner><special>self</special></owner></object>
  </authorization>
</role>
```

- Fases según https://docs.evolveum.com/midpoint/reference/support-4.11/security/authorization/configuration/: «Request: when operation enters the IDM Model component», «Execution: when operation leaves the IDM Model component», y «A single `deny` in any of the phases denies entire operation».
- **Por qué la ejecución no se limita a `preferredName`:** cada modificación pasa por toda la plantilla (bloques D, E y J de Person-Base). Si arrastra cambios latentes en otros ítems (`midpoint-best-practices` §11.3), una autorización de ejecución restringida haría fallar la operación entera. El rol End user de fábrica sigue el mismo criterio: la restricción va en la fase *request* (descripción de su autorización 10, [PROD-4]). **Resuelto en el laboratorio (§12, T-AUTO):** no basta. Sin la autorización de ejecución sobre `ShadowType` con `owner self` (como la id 11 del rol End user), el PATCH devuelve **403** pero el foco **ya quedó cambiado** (`preferredName` y `displayName`) y LDAP no: un estado inconsistente que nadie ve. Con ella, la persona cambia su `preferredName` (204, llega a LDAP), y modificar su `givenName`, `familyName`, `displayName`, `emailAddress` o el preferido de otra persona da 403. Un valor inválido da 409 (la regla del §3.1).
- `givenName`, `familyName`, `fullName` y `displayName` no se pueden pedir: la fase *request* solo permite `preferredName`. La GUI de autoservicio mostrará muchos más campos (`#selfAll`). Hay que reducir el formulario con `adminGuiConfiguration`. ❓

---

## 6. Contrato para Discovery

### 6.1 Cuenta y rol (siguiendo el patrón de `svc-ai-identity`)

- **Usuario:** `svc-discovery-preferred-name` (OID propuesto `a9b862db-1b3d-498c-8e5e-4a0a4f9a2266`), arquetipo `archetype-user-service-account` (`05ceed56-9a60-4531-903f-c7748b36de8a`), con contraseña en `~/.secrets/` del lado de Discovery. Nunca en el repo.
- **Rol:** `role-svc-discovery-preferred-name`, arquetipo application-role, como `role-svc-ai-identity-reader`. A diferencia de ese rol, se usan acciones REST **por operación** en vez de `#all`. Las acciones son `#searchObjects` y `#modifyObject` (https://docs.evolveum.com/midpoint/reference/support-4.11/interfaces/rest/operations/search-op-rest/ y …/modify-op-rest/). La documentación dice que las autorizaciones REST son «necessary, but not sufficient» (…/security/authorization/service/).
- **Alcance de objetos** *fail-closed*: solo usuarios con un arquetipo de persona (alumno, administrativo, docente, egresado). Ojo: quien pierde todas sus asignaciones pierde el `archetypeRef` (memoria `entra-ex-trabajadores-98-2026-08-16`) y queda **fuera** a propósito.

```xml
<role oid="8c0d4560-76ff-4c20-b683-3c4d498886ed">
  <name>role-svc-discovery-preferred-name</name>
  <assignment><targetRef oid="279ad5be-a892-4add-946f-8cb3740bfc31" type="c:ArchetypeType"/></assignment>
  <authorization>
    <name>discovery-rest-ops</name>
    <action>http://midpoint.evolveum.com/xml/ns/public/security/authorization-rest-3#searchObjects</action>
    <action>http://midpoint.evolveum.com/xml/ns/public/security/authorization-rest-3#modifyObject</action>
  </authorization>
  <authorization>
    <name>discovery-read-min</name>
    <action>http://midpoint.evolveum.com/xml/ns/public/security/authorization-model-3#read</action>
    <object>
      <type>UserType</type>
      <filter><q:text>archetypeRef matches (oid = "3037fbd2-db02-4ffd-8b1a-83fab5e686aa")
        or archetypeRef matches (oid = "6460facf-3abf-4851-966e-0c95aa1a6c46")
        or archetypeRef matches (oid = "c93083ca-f4c5-4704-acf4-d53b97c9556e")
        or archetypeRef matches (oid = "87552943-9600-493b-88ca-74b7d3ba93e4")</q:text></filter>
    </object>
    <item>name</item>
    <item>emailAddress</item>
    <item>preferredName</item>
    <item>displayName</item>
  </authorization>
  <authorization>
    <name>discovery-modify-request</name>
    <action>http://midpoint.evolveum.com/xml/ns/public/security/authorization-model-3#modify</action>
    <phase>request</phase>
    <object><type>UserType</type><filter><!-- mismo filtro --></filter></object>
    <item>preferredName</item>
  </authorization>
  <authorization>
    <name>discovery-modify-execution</name>
    <action>http://midpoint.evolveum.com/xml/ns/public/security/authorization-model-3#modify</action>
    <phase>execution</phase>
    <object><type>UserType</type><filter><!-- mismo filtro --></filter></object>
  </authorization>
  <authorization>
    <name>discovery-shadows-execution</name>
    <!-- OBLIGATORIA (laboratorio 16-nov). Acotada a las cuentas cuyo DUEÑO está en el alcance -->
    <action>http://midpoint.evolveum.com/xml/ns/public/security/authorization-model-3#add</action>
    <action>http://midpoint.evolveum.com/xml/ns/public/security/authorization-model-3#modify</action>
    <phase>execution</phase>
    <object>
      <type>ShadowType</type>
      <owner><type>UserType</type><filter><!-- mismo filtro --></filter></owner>
    </object>
  </authorization>
</role>
```

OIDs de arquetipo tomados de `canonical/archetypes/user/*.xml`. El rol completo, con el filtro repetido en las cuatro autorizaciones, es `sistemas/nombre-preferido/objetos/40-role-svc-discovery-preferred-name.xml` del repo `UPeU-Infra/lab-identidad`.

**Resuelto en el laboratorio (§12, T4):**
- (a) **El filtro Axiom con `or` funciona** en las autorizaciones: una persona sin arquetipo de persona, la propia cuenta de servicio y `administrator` no salen en las búsquedas y su PATCH da 403.
- (b) **La autorización de ejecución sobre `ShadowType` es obligatoria.** Sin ella el PATCH devuelve 403 **después de guardar el foco**: `preferredName` y `displayName` quedan cambiados y LDAP/Koha no. Se acotó al dueño (`<owner>` con el mismo filtro de arquetipos), en vez de a toda `ShadowType`, y funciona igual.
- (c) **Lectura *fail-closed*:** la búsqueda devuelve solo `oid`, `version`, `name`, `emailAddress`, `preferredName` y `displayName`. Buscar por un ítem no legible (`telephoneNumber`, `givenName`) devuelve 200 con **0 resultados aunque la persona exista**, así que no sirve de oráculo. `GET /users/{oid}` da 403 (el rol solo da `#searchObjects`).

### 6.2 Cómo encontrar a la persona

Medido en PROD [PROD-3][PROD-7]:

| Dato | Valor |
|---|---|
| Usuarios con `emailAddress` | 32 063 de 66 157 (sin correo: 34 094) |
| Activos (`lifecycleState=active`) sin correo | 25 325 de 49 710 |
| Personas con cuenta LDAP `default` sin correo | **11 953 de 31 136** (su `mail` LDAP también está vacío, porque sale de `emailAddress`) |
| Direcciones institucionales repetidas | 59 direcciones → 121 usuarios (máx. 3 por dirección); 39 → 81 entre activos |
| Mismo correo con distinta grafía | 0 |
| Índice sobre `emailaddress` | **no hay** (búsqueda secuencial sobre ~66 000 filas) |

**Recomendación:**
1. **Clave primaria: `name`.** Es el código institucional: único, indexado, igual al `uid` LDAP y al localpart del ePPN (memoria del 26-ago: ePPN == uid al 100 %). Si Discovery puede sacar el `uid` (del LDAP al iniciar sesión, o de un claim fiable), busca por `name`. ❓ Qué claims recibe Discovery del IdP: según ADR-058 y la memoria del 27-ago, los mappers del IdP solo copian `username`, `firstName`, `lastName` y `email`.
2. **Respaldo: `emailAddress`,** exacto y en minúsculas. Si hay **0** resultados: «aún no podemos guardar tu nombre preferido», sin escribir nada. Si hay **más de 1**: no se escribe y se registra para revisión. Solo con **1** se sigue.
3. La falta de correo (GAP-2, enriquecimiento de `emailAddress`) es un **bloqueante de cobertura** que este diseño no resuelve.

### 6.3 Llamadas

**Buscar** (`POST /midpoint/ws/rest/users/search`, `Content-Type: application/json`, `Accept: application/json`):

```json
{ "query": { "filter": { "text": "name = \"201900000\"" } } }
```
o, de respaldo:
```json
{ "query": { "filter": { "text": "emailAddress = \"persona.ficticia@upeu.edu.pe\"" } } }
```

Respuesta 200 con la lista de objetos. Discovery solo ve `oid`, `name`, `emailAddress`, `preferredName` y `displayName`. **Comprobado en 4.11:** la forma `{"query":{"filter":{"text":"…"}}}` funciona y la respuesta es `{"object":{"object":[ … ]}}` (lista vacía: sin la clave interna `object`). La comparación de `emailAddress` distingue mayúsculas: Discovery lo envía en minúsculas.

**Modificar** (`PATCH /midpoint/ws/rest/users/{oid}`; según la doc, PATCH y POST son equivalentes y se prefiere PATCH):

```json
{ "objectModification": { "itemDelta": {
    "modificationType": "replace", "path": "preferredName", "value": "Liz" } } }
```

Para **borrar**: el mismo cuerpo sin `value` (también vale `"modificationType":"delete"` con el valor actual). **Comprobado en 4.11:** el `PolyString` acepta la cadena simple (y también `{"orig":"Liz"}`). Si el mismo PATCH lleva otro ítem (`givenName`), se rechaza entero con 403 y no se aplica nada.

### 6.4 Respuestas y qué hace Discovery

Códigos **medidos** en el laboratorio (§12):

| Código | Cuándo (medido) | Acción de Discovery |
|---|---|---|
| 204 | Éxito. **No garantiza que LDAP esté escrito:** con LDAP caído también devolvió 204, con la operación pendiente (`IN_PROGRESS` en la auditoría) que completó la siguiente reconciliación | Leer el `displayName` del LDAP; si no está, «guardado; se propagará» y comprobar en el siguiente inicio de sesión. **No reintentar el PATCH** |
| 403 | Ítem distinto de `preferredName`, persona fuera del alcance, cuenta de servicio o `administrator`, asignaciones | No reintentar; alertar |
| 404 | `oid` inexistente | Volver a buscar |
| 409 | Valor rechazado por la regla del §3.1 («Object state after operation matches constraint "preferredName-invalido"») | Mensaje de validación |
| 502 | Error de configuración o de comunicación de un destino que midPoint no deja pendiente (medido con el CSV sin permiso de escritura): **no se guardó nada** | Reintentar con espera (máx. 3) |
| 240 / 250 | Documentados (error manejado / parcial), **no observados** en estas pruebas | Igual que 204 |

**¿Cómo sabe Discovery que llegó al LDAP?** Normalmente, con un 204 LDAP ya se escribió en la misma operación (medido: el valor está en LDAP al volver la respuesta). Pero **un 204 no lo garantiza**: con LDAP caído la respuesta también fue 204 y el cambio quedó como operación pendiente (§6.4). Por eso Discovery lee `displayName` (o `eduPersonNickname`) del LDAP que consulta, con unos segundos de margen por la réplica. Si el valor no aparece, vuelve a comprobarlo al siguiente inicio de sesión, sin repetir el PATCH. Para los egresados (`account/alumni`), hasta que se decida §4.1, Discovery debe usar `cn` de respaldo.

---

## 7. Encaje con el nombre oficial (E1)

- `givenName`, `familyName` y `fullName` siguen con su único escritor (`UserTemplate-Nombre-Oficial`, cuando E1 llegue a PROD). La plantilla nueva solo **lee** `familyName`/`fullName`.
- Documentos, actas, diplomas, RENATI/SUNEDU y CRIS/PerúCRIS deben seguir leyendo `cn`/`givenName`/`sn` (LDAP) o `fullName` (MidPoint), **nunca** `displayName` ni `eduPersonNickname`. Hay que decírselo a cada consumidor. ❓ Inventario de consumidores de `displayName` LDAP (Keycloak, OJS, DSpace, CRIS…).
- Orden propuesto: (1) E1 y el atributo 87 en un solo cambio con la expresión del §4.1; (2) la plantilla de `displayName`; (3) los outbounds de Koha y Zammad; (4) la cuenta de Discovery; (5) el inbound de Koha cuando haya `SyncOp`.

## 8. Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | Cambio masivo de `displayName` en LDAP al pasar 87 a strong (7 115 activos, ~13 100 en total) | Es el de E1: un solo cambio, SIM PRE/POST, canario acotado y tandas en la ventana segura (protocolo PRE-EJECUCIÓN) |
| R2 | Una autorización de ejecución demasiado estrecha → los PATCH de Discovery fallan por cambios latentes. **Peor de lo previsto:** el 403 llega con el foco ya guardado y las cuentas sin escribir | Ejecución amplia sobre `UserType` y sobre las `ShadowType` de los usuarios del alcance; la puerta es la fase request (§5, §6.1). Medido en el laboratorio (T4, T-AUTO) |
| R3 | Cada PATCH arrastra cambios latentes de esa persona (regla 5 del contexto) | Recompute previo planificado; al pilotar, revisar en auditoría los primeros PATCH |
| R4 | Un inbound de Koha mal filtrado por canal → la reconciliación de las 09:15 reintroduce valores viejos | `<channel>liveSync`: **probado** en el laboratorio con control negativo (T7a/T7f: con canal no entra; sin canal entra) |
| R5 | Un feed de live sync no limitado a `preferred_name` → borra **o reintroduce** preferidos viejos | **Confirmado** en el laboratorio (T7g): un evento ajeno reintrodujo el valor viejo. `SyncOp` por `action_logs` que emita solo cambios de `preferred_name` [KE] |
| R6 | Abuso: nombres ofensivos, suplantación | D1 (apellidos fijos), validación en las dos puntas, auditoría y posibilidad de que DTI o CRAI lo reviertan |
| R7 | Privacidad: un nombre social puede revelar identidad de género | Publicar `displayName` a los SP solo donde haga falta; pronombres fuera (D3) |
| R8 | Drift de GitOps: LDAP 87 (repo strong / PROD weak), Zammad sin XML en el repo, rol `svc-ai` desfasado | Exportar PROD antes de cualquier PATCH y versionar |
| R9 | Cobertura de Discovery limitada por la falta de correo (§6.2) | Clave `name`; GAP-2 aparte |
| R10 | Alguien cambia la plantilla de UserType a la 380 de 4.11 (`range=all` en `name`/`fullName`) | Documentado: la 380 no se usa en UPeU |
| R11 | El OPAC de Koha deja pedir cambios del nombre oficial | `PatronSelfModificationBorrowerUnwantedField` (koha-expert / CRAI) |
| R12 | Un valor inválido que llega por live sync **detiene la tarea** (`SUSPENDED`) y con ella todos los cambios siguientes | `controlFlow/errorHandling` `policy → ignore` en la tarea de live sync (§3.2), medido en el laboratorio (T7h) |

## 9. Plan de prueba en el laboratorio (192.168.15.150)

Se usó el midPoint **4.11.0** de `:8091` (el de midPilot); el de la plataforma (`:8081`) sigue en 4.10.2. Resultado por prueba (detalle en el §12):

| Prueba | Qué se comprueba | Resultado (16-nov-2026) |
|---|---|---|
| T1 | El XSD y la columna `preferredName`/`displayName` existen en la instancia | ✅ |
| T2 | Plantilla NP1 con y sin preferido; borrar el preferido | ✅ (MEL; también al cambiar el apellido oficial) |
| T3 | LDAP attr 87 + `eduPersonNickname` (`tolerant=false`) | ✅ recompute = 0 deltas |
| T4 | Cuenta de servicio: búsquedas, PATCH 204, PATCH de otros ítems 403, lectura limitada, fuera de alcance 403 | ✅ **con corrección**: hace falta ejecución sobre `ShadowType` |
| T5 | Reconciliación del LDAP con un `displayName` alterado a mano | ✅ |
| T6 | Política de validación | ✅ 409 (regla global, §3.1) |
| T7 | Fuente Koha simulada con CSV + live sync: a) reconciliación no entra; b) live sync entra; c) = `firstname` borra; d) vacío borra; e) eco sin delta; f) control negativo sin `<channel>`; g) evento ajeno (R5); h) valor inválido | ✅ a–f; g **confirma R5**; h **exige `errorHandling`** |
| T8 | Dos cambios casi simultáneos (REST y live sync) | ⏸ no probado |
| T9 | Auditoría | ✅ canal (`rest`/`liveSync`) e iniciador en `ma_audit_event`, delta en `ma_audit_delta` |
| T10 | MEL | ✅ todo el lab es MEL; Groovy no probado (desactivado en una 4.11 nueva) |
| T-AUTO | Autoservicio por REST con `role-self-preferred-name` | ✅ **con corrección**: ShadowType `owner self` |
| T-ERR | Un destino falla durante el PATCH de Discovery | LDAP caído → **204** con operación pendiente; CSV sin escritura → 502 sin cambios |

Después: protocolo PRE-EJECUCIÓN en PROD (respaldo → SIM PRE con configuración de producción → cambio inerte `proposed` → SIM POST → canario con lista de nombres → auditoría → lote).

## 10. Pendientes (❓)

Resueltos el 16-nov-2026: D1 y D3 (Alberto); la sintaxis y el código de la regla de validación (409); `<channel>` en 4.11; la forma JSON de `filter.text`; el `PolyString` como cadena; la autorización sobre `ShadowType` (obligatoria); la versión del laboratorio (4.11.0 en `:8091`).

1. Si `account/alumni` publica `displayName` en LDAP.
2. Cuántas entradas LDAP tienen hoy `eduPersonNickname` (antes de `tolerant=false`).
3. Qué claims recibe Discovery (¿`uid`/`name`?) y a qué LDAP (maestro o réplica) consulta.
4. Confirmar en la SIM de PROD que MEL se evalúa allí (PROD no tiene perfiles de expresión y su lenguaje por defecto es Groovy).
5. Siembra o descarte de los 28 `preferred_name` distintos de Koha; `SyncOp` de Koha que emita **solo** cambios de `preferred_name` (R5) y `PatronSelfModificationBorrowerUnwantedField` (koha-expert).
6. Inventario de consumidores de `displayName` LDAP.
7. Volver a medir en Graph que Entra sigue siendo solo nube.
8. T8 (concurrencia REST + live sync), la GUI de autoservicio (`adminGuiConfiguration`, login federado) y las pruebas con Koha y Zammad reales.
9. Revisar si el `cn` de PROD es tolerante: en el laboratorio un `cn` añadido a mano no lo retiró la reconciliación (§4.1).

## 11. Consultas a PROD (solo lectura, 2026-11-16)

Dos sesiones SSH al `.166`, cada una con un solo script. Postgres con `default_transaction_read_only=on`. REST solo con GET (`?options=raw`).

- **[PROD-1]** `date -u`; `docker ps` (imágenes); `SELECT * FROM m_global_metadata`.
- **[PROD-2]** `information_schema.columns` de `m_user`; `pg_indexes` (display/preferred/nick); `m_ext_item` (preferred/pronoun/nick/displayName); `m_object` tipo `SCHEMA`; `m_object_template`.
- **[PROD-3]** Conteos en `m_user`: total, `nicknameorig`, `displaynameorig`, `preferrednameorig`; `nickName` por arquetipo; correo: total, sin correo, distintos, institucionales, repetidos (direcciones/usuarios/máx.), variantes de grafía, repetidos por arquetipo y ciclo de vida; `m_role` (End user/svc/reader) y titulares de End user (`m_ref_role_membership`, `m_assignment`); usuarios con arquetipo de servicio y sus roles.
- **[PROD-4]** GET de: schemas `e800335c…` y `64ed4155…` (`preferredName`/`displayPronouns`); `systemConfigurations/…0001` (`defaultObjectPolicyConfiguration`); `objectTemplates/…0380` y `855caaca…`; `archetypes/…0702`; `roles/…0008` (autorizaciones) y `fd083a83…`; `users/ef55f087…` (estructura, sin datos de persona); `securityPolicies/…0120`; recursos LDAP (`7b4e1c2d…`, attr `displayName`, `liveSync`), Koha (`e10a539a…`, `preferred_name`), Entra (`2f11c057…`, `lifecycleState`/outbounds) y Zammad (`7a11d0d0…`, `schemaHandling`).
- **[PROD-5]** `m_resource` (12); `m_task` con `liveSynchronization`/`asynchronousUpdate` (0); `m_uri` de canales; `m_object` tipo `SECURITY_POLICY`.
- **[PROD-6]** `common-core-3.xsd` dentro de `BOOT-INF/lib/schema-4.11.0.jar` de `/opt/midpoint/lib/midpoint.jar` (leído en memoria por un pipe; sin escribir en el contenedor): `UserType/preferredName`, `displayName`, `nickName`.
- **[PROD-7]** Correo por `lifecycleState`; personas con cuenta LDAP `default` sin correo; repetidos solo entre activos; índice sobre `emailaddress`; shadows vivos por recurso e intent (LDAP, Koha, Entra, Zammad); `m_connector` de Koha/Zammad y su `connectorVersion`; esquema LDAP (`eduPersonNickname`, `eduPersonDisplayPronouns`, intents).

## 12. Resultados del laboratorio (16-nov-2026)

**Dónde:** laboratorio UPeU, midPoint **4.11.0** de `sistemas/midpilot` (`:8091`), con datos **sintéticos**: 7 personas ficticias (`2099000NN`), la cuenta `svc-discovery-preferred-name` y una rama propia `ou=nombre-preferido` en el OpenLDAP del laboratorio (el recurso tiene esa rama como `baseContext`). Koha se simuló con un CSV (el conector CSV tiene live sync y el de Koha no). Nada conecta con PROD, Oracle LAMB ni el LDAP `.168/.169`. Koha y Zammad reales quedaron fuera de esta ronda.

**Cómo se reproduce:** repo `UPeU-Infra/lab-identidad`, `sistemas/nombre-preferido/` (`01-montar.sh`, `02-pruebas.sh`, `99-retirar.sh`; README con el detalle). Los arquetipos de prueba usan **los OID de PROD** para que los filtros de las autorizaciones sean los reales. Los objetos que irían a PROD llevan ya su OID definitivo:

| Objeto | OID |
|---|---|
| `UserTemplate-Nombre-Preferido` | `ce40e768-5767-475f-a653-65d9753d6ff5` |
| `role-svc-discovery-preferred-name` | `8c0d4560-76ff-4c20-b683-3c4d498886ed` |
| usuario `svc-discovery-preferred-name` | `a9b862db-1b3d-498c-8e5e-4a0a4f9a2266` |
| `role-self-preferred-name` | `27f7c7bd-4b6c-43cd-8368-90e31a847867` |
| regla global `NP-validar-preferredName` | (contenedor de `systemConfiguration`; en el laboratorio, id 9101) |

**Resultado:** `02-pruebas.sh` da **88 ✅ / 0 ❌**, también en un ciclo completo desde cero (`99-retirar` → `01-montar` → `02-pruebas`, 16:57–16:59 UTC). midPilot quedó intacto: sus 240 usuarios y sus 300 cuentas CSV no se tocaron.

### 12.1 Lo que confirma el diseño

- **Plantilla (T2):** sin preferido, `displayName` = `fullName`; con «Lucía», «Lucía» + apellidos; si cambia el apellido oficial, `displayName` lo sigue; al borrar el preferido, vuelve al oficial (`range=all`). `givenName`/`familyName`/`fullName` no cambian. Un `displayName` escrito a mano por el administrador lo repone la plantilla en la misma operación.
- **LDAP (T3/T5):** `displayName` y `eduPersonNickname` como en el §4.1; `cn`/`givenName`/`sn` oficiales. Un recompute de todos los sintéticos produce **0 deltas** de usuario. La reconciliación repone `displayName` y retira un `eduPersonNickname` intruso (`tolerant=false`).
- **Contrato Discovery (T4):** búsqueda por `name` → 1. Correo único → 1; repetido → 2 (Discovery no escribe); en mayúsculas → 0. Fuera de alcance y `administrator` → 0. PATCH → 204 y el valor ya está en LDAP. 403 para `givenName`, `familyName`, `fullName`, `emailAddress`, `displayName`, `telephoneNumber`, asignaciones, la propia cuenta de servicio, `administrator` y personas sin arquetipo de persona. Un PATCH mixto (`preferredName` + `givenName`) se rechaza entero. 404 para un oid inexistente.
- **Validación (T6):** 409 para dígitos, URL, correo, doble espacio, espacios al borde, 41 caracteres, emoji, HTML, guion inicial y tilde descompuesta (NFD). Acepta «José Luis», «O'Brien», «Ana-María», «Ñañez» y 40 caracteres.
- **Canal de entrada (T7):** `<channel>` funciona en 4.11. Con canal, la reconciliación no mete el valor de la fuente; sin canal (control negativo), sí. El live sync lo mete y llega a LDAP. Un valor = `firstname` o vacío borra el preferido y la fuente vuelve a `firstname`. El eco de lo que escribe MidPoint no produce ningún delta. El outbound `normal` no pisa la fuente en la reconciliación.
- **Auditoría (T9):** cada delta de `preferredName` queda con su canal (`rest`, `liveSync`) y su iniciador (`svc-discovery-preferred-name`; en live sync, el dueño de la tarea).
- **Autoservicio (T-AUTO):** la persona cambia su preferido (204, llega a LDAP). No puede cambiar su nombre oficial, su correo, su `displayName` ni el preferido de otra persona (403). Un valor inválido da 409.

### 12.2 Correcciones que hubo que hacer al diseño

1. **Autorización de ejecución sobre `ShadowType`: obligatoria** en los dos roles (§5, §6.1). Sin ella, el PATCH devuelve **403 después de guardar el foco**, así que el valor queda en MidPoint y no en LDAP ni en Koha. Para Discovery se acotó a las cuentas cuyo dueño está en el alcance; para el autoservicio, `owner self`.
2. **Códigos REST medidos (§6.4):** con LDAP caído, **204** y operación pendiente (`IN_PROGRESS`), que completó la reconciliación siguiente. No se vieron 240 ni 250. Si el error de un destino no queda pendiente (el CSV sin permiso de escritura), da 502 y no se guarda nada. La regla de validación da 409.
3. **Live sync (§3.2):** R5 se reprodujo, porque un evento ajeno reintrodujo el valor viejo de la fuente. Además, un valor inválido deja la tarea en `SUSPENDED`, lo que exige `errorHandling` `policy → ignore`.
4. **MEL en lugar de Groovy** para todas las expresiones nuevas (§3.1).
5. **Sintaxis de la regla de validación** y su guardia `<and>` + `<modification>` (§3.1).

### 12.3 Hallazgos de 4.11.0 útiles fuera de este diseño

- **PATCH replace de `c:connectorConfiguration` entero → HTTP 500** (`IllegalStateException: An attempt to modify an immutable: XNode…` en `TrustDescriptorSetter`). El PATCH de una sola propiedad (`c:connectorConfiguration/icfc:configurationProperties/cfg:host`) sí funciona y sube la `version`. Hay que tenerlo en cuenta en la receta «nunca PUT, siempre PATCH» de PROD.
- **La REST de 4.11 no tiene `POST /{type}/{oid}/recompute`** (404; tampoco figura en la documentación de operaciones REST de 4.11). Para recomputar hay que usar una tarea, o `POST /tasks/{oid}/run` para relanzarla.
- En una instalación 4.11 **nueva**, la configuración del sistema trae perfiles de expresión por tipo (`configuration` para plantillas, recursos y la propia configuración; `safe` para roles y arquetipos). PROD no los tiene porque no se importó la configuración de 4.11.
- El conector CSV 2.10 escribe el fichero con finales de línea CRLF.

---

## 13. Respuesta de Discovery (16-nov-2026) y bloqueante de red

Lo informó la sesión de Discovery, medido en su EC2 y en PROD de Discovery:

- **Claims:** Discovery pide `openid profile email` al realm `upeu`. Guarda el `sub` (UUID) y el correo; **no recibe el código**. El código lo obtiene de Koha: busca al lector por correo exacto y toma su `userid`.
- **Identificación:** primero `name` = `userid` de Koha; de respaldo, `emailAddress` en minúsculas.
  - Como `userid ← name` es `weak` en Koha, se añade una salvaguarda: si la persona se encontró por `name` y el `emailAddress` de midPoint no coincide con el correo del SSO (habiendo ambos), no se escribe.
- **Lectura de vuelta:** Discovery **no lee LDAP**: su EC2 (AWS, cuenta upeu-repo) no alcanza la LAN. Lee `preferred_name` del lector de Koha, y si es igual a `firstname` lo toma como «sin preferido». Por eso el outbound **`NP-koha-preferred-out` (§4.3) pasa a ser requisito para PROD**, no una fase posterior.
- **Bloqueante:** la EC2 de Discovery tampoco alcanza midPoint. `192.168.15.166` no es enrutable desde AWS y `identity.upeu.edu.pe` no está en DNS público (internamente resuelve al balanceador `192.168.12.199`). Opciones, a decidir por Alberto con redes:
  1. Publicar solo `POST /ws/rest/users/search` y `PATCH /ws/rest/users/{oid}`, restringidos a la IP elástica de Discovery y con TLS.
  2. VPN sitio a sitio AWS↔UPeU.
  3. Discovery escribe `preferred_name` en Koha (ya lo alcanza) y midPoint lo recoge por live sync. No expone midPoint, pero exige el `SyncOp` de Koha (§4.3, 1,5–2 días), y la validación deja de ser síncrona (sin 409): Discovery tendría que validar antes de escribir.
- En el laboratorio la cuenta `svc-discovery-preferred-name` funciona desde la VPN; sus credenciales están en `~/.secrets/lab-identidad.env` (`LAB_NP_SVC_*`), fuera del repo.
