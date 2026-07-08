# Conector MidPoint → RENIEC vía apiperu.dev

**Slug:** `connector-reniec-midpoint`
**Autor:** Claude Code
**Fecha:** 2026-04-24
**Repositorio destino:** `~/proyectos/sciback/connector-reniec/`
**Relacionado:** Oracle LAMB→MidPoint IGA, connector-koha, schema ext v2.3

---

## 1) Intent & Assumptions

**Task brief:** Crear un conector ConnId para MidPoint 4.9.5 que consulte la API apiperu.dev
(intermediario sobre el registro reducido de SUNAT/RENIEC) para validar y enriquecer datos
demográficos de usuarios UPeU usando el DNI como clave. RENIEC actúa como fuente de verdad
para `nombres`, `apellido_paterno` y `apellido_materno`.

**Assumptions:**
- El conector es **read-only** (RENIEC no se puede escribir)
- La correlación de identidad es por DNI (`taxIdentifier` en MidPoint)
- Oracle LAMB sigue siendo la fuente primaria de identidad (crea usuarios); RENIEC solo enriquece atributos
- apiperu.dev es el intermediario práctico; acceso directo a RENIEC requiere convenio burocrático costoso
- El token Bearer ya existe en `~/.secrets/apiperu.env` (cuenta personal de Alberto, plan gratuito 100/mes)
- Para producción se crea cuenta institucional UPeU con plan Basic (S/ 15/mes = 50K consultas)
- El conector se hospeda en `sciback/connector-reniec/` como producto canónico reutilizable

**Out of scope:**
- Validación biométrica o de vigencia del documento (requiere acceso directo a RENIEC)
- Datos sensibles: domicilio, fecha de nacimiento, sexo, foto (no disponibles en apiperu.dev)
- Consulta RUC o tipo de cambio (apiperu.dev ofrece otros endpoints, fuera de scope aquí)
- Integración con Keycloak o EntraID (el conector solo habla con MidPoint)
- Stack CDC (Debezium/Kafka) — ese es otro proyecto

---

## 2) Pre-reading Log

- `connector-koha/pom.xml`: parent `connector-parent:1.5.2.0` de `com.evolveum.polygon`; Java 1.8 como target; assembly descriptor genera JAR con `lib/` para dependencias
- `connector-koha/KohaConnector.java`: implementa `Connector + CreateOp + UpdateOp + DeleteOp + SchemaOp + SearchOp<KohaFilter> + TestOp`; modelo de referencia completo
- `connector-koha/KohaConfiguration.java`: implementa `Configuration`; `GuardedString` para secretos; validación en `validate()`
- `connector-koha/KohaFilterTranslator.java`: extiende `AbstractFilterTranslator`; traduce EqualsFilter por Uid/Name/email/cardnumber; retorna null para filtros no soportados
- `connector-koha/KohaAuthenticator.java`: manejo de Bearer token con refresh automático, thread-safe; patrón reutilizable para apiperu.dev (más simple, token estático)
- `connector-koha/src/main/resources/Messages.properties`: i18n en español; clave `connector.identicum.rest.display`
- `connector-koha/src/main/resources/midpoint/KohaResource.xml`: template de resource XML con schema handling; referencia para el resource RENIEC
- `midpoint/resources/`: directorio vacío — no hay resources XML commiteados aún
- `midpoint/archetypes/`: directorio vacío — pendiente de poblarse
- Documentación apiperu.dev: endpoint `/api/dni` (POST) y también funciona como GET `/api/dni/{numero}`; plan gratuito 100/mes; plan Basic S/ 15/50K consultas
- Test real realizado: `GET https://apiperu.dev/api/dni/72436559` con Bearer → respuesta exitosa con `nombres`, `apellido_paterno`, `apellido_materno`, `codigo_verificacion`
- Marco legal: Ley 29733 + DS 016-2024-JUS vigente desde 2025-03-30; Art. 14 cubre a UPeU sin necesidad de consentimiento explícito del titular

---

## 3) Codebase Map

**Módulo nuevo a crear:** `sciback/connector-reniec/`

```
connector-reniec/
├── pom.xml                                          (parent: connector-parent:1.5.2.0)
├── src/main/java/com/sciback/midpoint/connectors/
│   ├── ReniecConnector.java                         (PoolableConnector + TestOp + SchemaOp + SearchOp)
│   ├── ReniecConfiguration.java                     (bearerToken GuardedString, baseUrl, testDni)
│   ├── ReniecFilter.java                            (byDni: String)
│   ├── ReniecFilterTranslator.java                  (AbstractFilterTranslator, solo EqualsExpression por Uid/dni)
│   └── services/
│       ├── ReniecApiClient.java                     (HttpClient java.net.http, Bearer token, timeout)
│       └── PersonMapper.java                        (JSON → ConnectorObject, nombres en INITCAP)
├── src/main/assembly/connector.xml                  (copia del patrón koha)
├── src/main/resources/
│   ├── com/sciback/midpoint/connectors/Messages.properties
│   └── midpoint/ReniecResource.xml                  (template de resource para MidPoint)
└── src/test/java/com/sciback/midpoint/connectors/
    ├── ReniecConfigurationTest.java
    ├── ReniecFilterTranslatorTest.java
    └── ReniecConnectorIntegrationTest.java
```

**Dependencias del módulo nuevo:**
- `connector-parent:1.5.2.0` — ConnId framework base (ya en local Maven o Maven Central)
- `java.net.http.HttpClient` — Java 11+ built-in, sin dependencia extra
- `org.json:json` — ya usado en koha, versión 20250517
- **Sin** Apache HttpClient (simplificación respecto a koha, el API es simple)

**Integración en MidPoint UPeU:**
- Resource XML: `midpoint/resources/resource-reniec-api.xml` (nuevo archivo en repo upeu/midpoint)
- Schema extension: `extension/reniecNombres`, `extension/reniecPaterno`, `extension/reniecMaterno` (agregar a schema v2.3)
- Object Template: mappings con `strength=strong` desde los campos staging RENIEC hacia `givenName`, `familyName`
- Arquetipos Student/Professor: agregar asignación al resource RENIEC como fuente de atributos

**Blast radius:**
- Solo lectura en apiperu.dev — sin riesgo de corrupción de datos
- Cuota de API: 100 consultas/mes en plan gratuito; en pruebas masivas usar plan de pago
- No afecta Oracle LAMB ni Koha — conector independiente

---

## 4) Root Cause Analysis

*(No aplica — es desarrollo de funcionalidad nueva, no bug fix)*

---

## 5) Research

### 5.1 API apiperu.dev — Detalles técnicos confirmados

**Endpoint DNI:**
- `POST https://apiperu.dev/api/dni` con body `{"dni": "12345678"}`
- También funciona: `GET https://apiperu.dev/api/dni/{numero}` — confirmado con test real
- Headers: `Authorization: Bearer <token>`, `Accept: application/json`

**Respuesta exitosa:**
```json
{
  "success": true,
  "data": {
    "numero": "72436559",
    "nombre_completo": "GONZALES ORDOÑEZ, ANTHONY DAVID",
    "nombres": "ANTHONY DAVID",
    "apellido_paterno": "GONZALES",
    "apellido_materno": "ORDOÑEZ",
    "codigo_verificacion": 6,
    "direccion": "",
    "ubigeo": [null, null, null]
  }
}
```

**Casos de respuesta a manejar en el conector:**
- `{"success": true, "data": {...}}` → OK, mapear atributos
- `{"success": false, ...}` → DNI no encontrado en la fuente (no es error técnico)
- HTTP 401/403 → token inválido → `ConnectionFailedException`
- HTTP 429 → cuota agotada → `ConnectorIOException` con mensaje claro
- HTTP 5xx → error servidor → `ConnectorIOException` con retry automático opcional

**Limitación crítica conocida:**
apiperu.dev NO consulta RENIEC directamente. Usa el **registro reducido de SUNAT**, que:
- No incluye datos de **menores de edad** (sin actividad tributaria)
- No incluye domicilio, fecha de nacimiento, sexo
- Puede no retornar resultado para personas sin actividad tributaria
- Para estudiantes menores o ingresantes recientes → `success: false` es esperable

**Endpoint de prueba sin consumir cuota DNI:**
`POST https://apiperu.dev/api/tipo-de-cambio` — responde con tipo de cambio SOL/USD y valida el token. Usar en `testOp()` para no consumir consultas.

### 5.2 Arquitectura ConnId para conector read-only

**Interfaces a implementar (mínimo necesario):**
```java
public class ReniecConnector implements PoolableConnector, TestOp, SchemaOp, SearchOp<ReniecFilter>
```

**NO implementar:** `CreateOp`, `UpdateOp`, `DeleteOp`, `SyncOp`

MidPoint detecta automáticamente las capacidades del conector por las interfaces implementadas. En el XML del resource se declara explícitamente:
```xml
<capabilities>
    <configured>
        <cap:create><cap:enabled>false</cap:enabled></cap:create>
        <cap:update><cap:enabled>false</cap:enabled></cap:update>
        <cap:delete><cap:enabled>false</cap:enabled></cap:delete>
    </configured>
</capabilities>
```

**SearchOp con solo búsqueda por DNI (sin scan masivo):**

El `FilterTranslator` solo traduce filtros `EQUALS` por `__UID__` (DNI). Para cualquier otro filtro retorna `null` (framework filtra en cliente, que en este caso retorna vacío porque nunca hay resultados no-filtrados).

En `executeQuery()`: si `query == null` (scan masivo) → lanzar `UnsupportedOperationException`. Esto impide que una tarea de import accidental consuma toda la cuota de la API.

**Implicación de diseño:** El resource RENIEC se usa únicamente como **fuente de atributos** en correlaciones, no como fuente de identidad. MidPoint nunca hace scan masivo de RENIEC; solo consulta DNIs específicos de usuarios ya correlacionados con Oracle LAMB.

### 5.3 Precedencia de atributos (RENIEC > Oracle LAMB)

**Patrón recomendado — Staging en extension + Object Template:**

```
Oracle LAMB inbound → extension/lambNombres (strength=normal)
RENIEC inbound     → extension/reniecNombres (strength=normal)

Object Template → givenName (strength=strong):
  if (reniecNombres != null) return INITCAP(reniecNombres)
  return INITCAP(lambNombres)
```

Este patrón es robusto: si RENIEC no devuelve dato (menor de edad, DNI no en SUNAT), el sistema cae suavemente a Oracle LAMB sin bloquear el aprovisionamiento.

**Alternativa simple** (si solo son dos fuentes): `strength=strong` directamente en el inbound RENIEC + `condition` en LAMB que solo aplica si el campo RENIEC está vacío. Menos flexible pero más simple de configurar.

### 5.4 Rate limiting y caché

**En MidPoint resource XML:**
```xml
<caching>
    <cachingStrategy>passive</cachingStrategy>
</caching>
```
Con `passive`, los atributos del shadow RENIEC se almacenan en la DB de MidPoint. Las evaluaciones de política (GUI, reconciliación de políticas) usan el caché sin llamar a la API.

**En el conector Java (Guava Cache con TTL 24h):**
```java
private static final LoadingCache<String, Optional<PersonaData>> dniCache =
    CacheBuilder.newBuilder()
        .maximumSize(50_000)       // ~3MB para 50K DNIs
        .expireAfterWrite(24, TimeUnit.HOURS)
        .build(key -> Optional.ofNullable(apiClient.getByDni(key)));
```
- Cache estático (`static`) para compartir entre instancias del pool
- `Optional` para cachear también los "no encontrado" y no repetir consultas fallidas
- TTL de 24h balanceo entre frescura de datos y ahorro de cuota

**Estrategia de reconciliación recomendada para UPeU:**
- Tarea de enriquecimiento inicial: un run único para los ~15K usuarios con DNI (usa cuota del plan Basic 50K en un mes)
- Reconciliación periódica: mensual o al detectar cambio en Oracle LAMB
- Trigger en tiempo real: cuando un usuario se provisionaa por primera vez

### 5.5 Marco legal — Síntesis

**Base legal confirmada (doble cobertura):**
1. Art. 14 Ley 29733, num. 1: UPeU como entidad universitaria pública en ejercicio de sus competencias institucionales (gestión de accesos a sistemas académicos)
2. Art. 14 Ley 29733, num. 2: datos provenientes de fuentes accesibles al público (registro reducido SUNAT)

**Obligaciones vigentes (DS 016-2024-JUS, desde 2025-03-30):**
- Verificar inscripción del banco de datos en SIPDP/ANPD (gratuito, virtual)
- Finalidad documentada: "validación de identidad para gestión de accesos institucionales"
- Minimización de datos: almacenar solo `nombres`, `apellido_paterno`, `apellido_materno`; NO `codigo_verificacion` ni `direccion` si no hay caso de uso
- Notificación de incidentes a ANPD en 48h (aplica a la DB de MidPoint)

**NO se requiere:**
- Convenio formal con RENIEC (eso sería para el web service oficial directo)
- Consentimiento de los titulares (cubierto por Art. 14)

**Riesgo residual:**
apiperu.dev es un intermediario privado no oficial. Si SUNAT/RENIEC restringe el acceso al registro reducido, el servicio podría degradarse. Riesgo bajo a corto plazo; mitigación: convenio RENIEC futuro como alternativa.

---

## 6) Clarifications

Las siguientes decisiones requieren tu validación antes de iniciar la implementación:

1. **Método HTTP**: El test real confirmó que funciona `GET /api/dni/{numero}`. La documentación oficial de apiperu.dev dice `POST /api/dni` con body JSON. ¿Usamos GET (más simple, sin body) o POST (según doc oficial)?

2. **Scope de atributos RENIEC a almacenar**: ¿Almacenamos solo `nombres`, `apellido_paterno`, `apellido_materno`? ¿O también `codigo_verificacion` (útil para validar el dígito del DNI) y `nombre_completo` (redundante pero conveniente)?

3. **Comportamiento ante "no encontrado"**: Cuando apiperu.dev devuelve `success: false` para un DNI (menor de edad, sin actividad tributaria), ¿MidPoint debe:
   - (A) Ignorar silenciosamente y mantener los datos de Oracle LAMB
   - (B) Marcar al usuario con un flag `extension/reniecValidado = false`
   - (C) Registrar en logs pero sin bloquear

4. **Cuota de API en desarrollo**: El plan gratuito tiene 100 consultas/mes. Para pruebas de integración con MidPoint real, ¿se crea ya la cuenta institucional UPeU con plan Basic (S/ 15/mes)? ¿O usamos un mock HTTP en tests?

5. **Caché en conector**: El caché estático de 24h compartido entre instancias del pool es eficiente pero significa que en producción un cambio de nombre en RENIEC tarda hasta 24h en reflejarse. ¿Es aceptable? ¿O preferimos TTL más corto (4h) con más llamadas a la API?

6. **Normalización INITCAP**: apiperu.dev devuelve nombres en ALL CAPS (`"ANTHONY DAVID"`). El conector debe aplicar `INITCAP` antes de pasarlos a MidPoint (para consistencia con la decisión ya tomada en las vistas Oracle). ¿Lo hacemos en el `PersonMapper` del conector, o dejamos que lo haga el Object Template de MidPoint?

7. **Nombre del package Java**: ¿`com.sciback.midpoint.connectors` (marca SciBack) o `pe.edu.upeu.midpoint.connectors` (específico UPeU) o `com.identicum.connectors` (continuando el patrón de koha)? Impacta en si este conector es un producto genérico SciBack o específico UPeU.

8. **GitHub repo**: ¿El repo va en la organización `UPeU-Infra` (como connector-koha) o en `SciBack` (ya que vive en sciback/)? ¿O es privado en tu cuenta personal?

9. **Versión Java**: connector-koha usa `maven.compiler.source/target = 1.8` (Java 8). `java.net.http.HttpClient` requiere Java 11+. ¿MidPoint 4.9.5 en producción corre con Java 11 o 17? Si solo hay Java 8 disponible, necesitamos usar Apache HttpClient (como koha) o OkHttp.

10. **Resource XML en upeu/midpoint**: El directorio `midpoint/resources/` está vacío. ¿Commiteamos el `ReniecResource.xml` en ese repo al finalizar? ¿O el template va solo en `sciback/connector-reniec/src/main/resources/midpoint/`?

---

## Appendix — Datos de referencia

### Respuesta real de apiperu.dev (test 2026-04-24)
```
GET https://apiperu.dev/api/dni/72436559
Authorization: Bearer e13fb99a9e22...

{
  "success": true,
  "data": {
    "numero": "72436559",
    "nombre_completo": "GONZALES ORDOÑEZ, ANTHONY DAVID",
    "nombres": "ANTHONY DAVID",
    "apellido_paterno": "GONZALES",
    "apellido_materno": "ORDOÑEZ",
    "codigo_verificacion": 6,
    "direccion": "",
    "direccion_completa": "",
    "ubigeo_reniec": "",
    "ubigeo_sunat": "",
    "ubigeo": [null, null, null]
  },
  "time": 0.0646829605102539
}
```

### Planes apiperu.dev (2026)
| Plan | S//mes | Consultas/mes | Nota |
|------|--------|---------------|------|
| Gratuito | 0 | 100 | Solo dev/testOp |
| Micro | 5 | 2,500 | - |
| Básico | 15 | 50,000 | Suficiente para UPeU (15K usuarios) |
| Plus | 25 | 100,000 | - |
| Premium | 45 | 250,000 | - |

### Atributos MidPoint a crear en schema extension v2.3
```xml
<!-- Staging RENIEC (en extension del usuario) -->
<xsd:element name="reniecNombres" type="xsd:string"/>
<xsd:element name="reniecPaterno" type="xsd:string"/>
<xsd:element name="reniecMaterno" type="xsd:string"/>
<xsd:element name="reniecValidado" type="xsd:boolean"/>
<xsd:element name="reniecUltimaConsulta" type="xsd:dateTime"/>
```

### Conector connector-koha como referencia
- Repo: `/Users/alberto/proyectos/upeu/connector-koha/`
- ConnId version: 1.5.2.0
- Java target: 1.8
- HTTP lib: Apache HttpClient 4.5.14
- JSON lib: org.json 20250517
- Build: `docker run --rm -v $(pwd):/app -w /app maven:3.9-eclipse-temurin-17 mvn package -DskipTests`
