# Prompt de onboarding — SSO Académico (caso de uso nuevo para MidPoint UPeU)

> Copiar este prompt completo en una nueva sesión de Claude Code abierta en `/Users/alberto/proyectos/upeu/midpoint`.

---

## Prompt para copiar y pegar

```
Hola. Hay un caso de uso NUEVO para MidPoint UPeU que se descubrió el
2026-05-08 y que toca planificar antes de avanzar más con el schema:
federación SAML con vendors de bases de datos científicas.

CONTEXTO RÁPIDO

El CRAI UPeU paga ~USD 127,600/año en 14 bases de datos (Scopus, Web of
Science, EBSCO 3 sedes, ScienceDirect — este último subvencionado por
CONCYTEC, etc.). Hoy autentican a los users contra Lamb Academic (Oracle)
vía URL `lamb-academic.upeu.edu.pe`. SciBack está diseñando un producto
que usa Keycloak como IdP SAML 2.0 federado con cada vendor — y el
schema v2.3 que ya tenemos en MidPoint es la pieza que provee los
atributos eduPerson enriquecidos.

Hallazgo clave del diagnóstico de Keycloak prod (2026-05-08):
- 20 users en realm `upeu`, 18 son LOCALES sin federationLink
- AD CRAI / AD ACADEMIC tienen mappers MÍNIMOS (solo username, mail,
  firstName, lastName)
- Scope OIDC `upeu` ya tiene mappers diseñados para los atributos
  enriquecidos, pero los atributos NUNCA SE LLENAN porque no hay
  Resource que los provisione
- MidPoint prod NO está conectado a Keycloak prod todavía

LO QUE NECESITO QUE HAGAS

1. LEE EN ESTE ORDEN:
   - docs/sso-academico-vendors-mapping.md (mapeo schema v2.3 →
     eduPerson SAML — el documento más importante)
   - docs/eduperson-attributes-reference.md (diccionario de atributos)
   - schema/README-extension-guia.md (recordatorio del schema v2.3
     existente)
   - schema/MAPPING-PLAN-lamb-to-extension.md (inbound mappings Lamb
     existentes)

2. EVALÚA Y CONFIRMA:
   - ¿El schema v2.3 efectivamente cubre todos los atributos eduPerson
     necesarios sin modificación?
   - ¿Hay algún ComplexType que se debería extender?
   - ¿El cálculo de `eduPersonScopedAffiliation` (faculty/student/staff)
     desde `extension/primaryAffiliationCode` está bien planteado?

3. PLANIFICA EL RESOURCE KEYCLOAK:
   Diseña el XML del Resource MidPoint que provisiona users hacia
   Keycloak prod (https://identity.upeu.edu.pe/admin/realms/upeu) con
   todos los atributos enriquecidos. Connector sugerido:
   ConnIdRESTConnector. Pero evalúa alternativas (existe
   `keycloak-connid-connector` de la comunidad).

4. DISEÑA EL OBJECT TEMPLATE:
   ¿Hay que extender el Object Template de UserType para que aplique
   las reglas de derivación (calcular `scopedAffiliation` con scope por
   sede)?

5. RESPÉTAME ESTAS REGLAS:
   - Política Lamb: SOLO LECTURA absoluta (`policy_oracle_readonly`)
   - NO modificar el schema v2.3 a menos que sea imprescindible
   - NO romper la sincronización Lamb existente (todos los nuevos
     atributos eduPerson son DERIVADOS o pasan por outbound, no inbound)
   - La conexión Keycloak es OUTBOUND ONLY (MidPoint provisiona, no
     consume)

6. ENTRÉGAME UN REPORTE CON:
   - Confirmación o gaps del schema v2.3
   - Lista de tareas concretas en orden de ejecución
   - XML draft del Resource Keycloak (no aplicar todavía, solo draft)
   - Object Template extensions necesarias
   - Estimación de tiempo de cada tarea
   - Riesgos y mitigaciones

7. NO IMPLEMENTES NADA TODAVÍA. Solo diseño y plan. La implementación
   real se decide después de que yo (Alberto) revise tu propuesta.

CONTEXTO ADICIONAL DISPONIBLE EN EL CODEBASE

- Schema v2.3 está consolidado en MidPoint repo (no XSD físico)
- OID SchemaType: b7d55017-599f-4f2f-9493-9f64bba62c5b
- Namespace: urn:upeu:midpoint:person
- MidPoint prod: 4.9.5 en 192.168.15.166
- Keycloak prod: 26.6.1 en identity.upeu.edu.pe (192.168.12.88)
- Acceso vía secrets en ~/.secrets/keycloak-prod.env y
  ~/.secrets/midpoint-upeu.env

CONTEXTO COMERCIAL (para que entiendas el porqué)

Este caso de uso es un "esteroide" para el proyecto IGA porque:
- Justifica la inversión en governance ante el CRAI/Biblioteca
- Conecta MidPoint con USD 127k/año de gasto bibliográfico
- Permite reportes COUNTER segmentados por facultad × programa × sede
- Es replicable como producto SciBack a otras universidades peruanas
- UNIQ (próximo cliente SciBack) lo va a necesitar también, pero con
  Google Workspace EDU como source en lugar de AD

Cuando termines la planificación, generaré un correo a Elsevier Latam
con la metadata Keycloak para iniciar el primer piloto SAML real.

Listo. Empieza por leer los 4 documentos en el orden indicado y
después dame tu evaluación.
```

---

## Cómo usar este prompt

1. Abrir terminal en `/Users/alberto/proyectos/upeu/midpoint/`
2. Iniciar Claude Code: `claude`
3. Copiar TODO el contenido del bloque ` ``` ` arriba
4. Pegar y enter

El agente del proyecto MidPoint:
- Ya tendrá las memorias persistentes que sembré en los 3 contextos relevantes
- Va a leer los 4 documentos clave que ya creamos
- Va a evaluar el schema v2.3 actual frente al nuevo caso de uso
- Va a producir un plan de implementación
- NO va a aplicar cambios — solo diseño

## Qué esperar como output

El agente debe entregar:

1. ✅ Confirmación de que el schema v2.3 cubre el caso (o gap específico)
2. ✅ Draft del XML del Resource Keycloak
3. ✅ Lista de Object Template modifications
4. ✅ Plan en orden de ejecución
5. ✅ Riesgos identificados

## Después de obtener el output

1. Revísalo
2. Si está OK: dile al agente "implementa" para que proceda
3. Si hay ajustes: itera en la conversación

Si el agente sugiere modificar el schema v2.3, **detente y consúltame** — esa decisión tiene impacto en otros sistemas que ya consumen el schema (GUIA Node, Koha enricher, etc.).
