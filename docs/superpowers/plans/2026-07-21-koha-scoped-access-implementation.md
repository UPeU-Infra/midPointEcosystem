# Koha Scoped Staff Access and Multicampus Mobility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dejar a `jsanchez@upeu.edu.pe` como único superadmin humano SSO, reducir el resto a funciones y bibliotecas autorizadas, y conservar una sola cuenta por persona con circulación multicampus.

**Architecture:** MidPoint mantiene una única proyección Koha `account/default` y calcula la unión de funciones y bibliotecas desde assignments vigentes. El conector materializa permisos, `STAFF_SCOPE` y un estado versionado de autorización con un protocolo fail-closed; Koha valida estado, hash, función y biblioteca en servidor. El rollout humano queda bloqueado hasta que el PoC demuestre denegación directa en CGI, REST, jobs y operaciones batch incluidas en el primer alcance.

**Tech Stack:** MidPoint 4.10.2 XML/Groovy, SchemaType, connector-koha Java/Maven, Koha 26.05 Perl/Mojolicious/CGI, MariaDB solo lectura para verificaciones, Keycloak OIDC.

---

## Límites y repositorios

Este cambio cruza tres repositorios, pero se ejecuta como una sola entrega coordinada:

| Repositorio | Responsabilidad |
|---|---|
| `/Users/alberto/proyectos/productos/iga/canonico` | SchemaType, roles, mappings, deltas MidPoint, auditoría y runbook. |
| `/Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha` | Round-trip de `STAFF_SCOPE`, atomicidad y pruebas del conector. |
| `/Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha` | PoC/enforcement Koha, mínimo privilegio de `svc_midpoint` y pruebas E2E. |

No modificar el Koha viejo `.135`. No usar SQL para conceder permisos. Las consultas SQL de auditoría son read-only.

### Rutas reproducibles y dependencias duras

```bash
IGA_REPO=/Users/alberto/proyectos/productos/iga/canonico
IGA_WT=/Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access
CONNECTOR_REPO=/Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha
CONNECTOR_WT=/Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha/.worktrees/koha-staff-scope
KOHA_REPO=/Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha
KOHA_WT=/Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope
```

Toda orden Git usa `git -C <ruta>`. Cada repositorio se commitea, publica y etiqueta por separado. No se despliega desde un worktree sucio.

Dependencias obligatorias:

1. PROD está bloqueado hasta obtener `PLUGIN_GATE=PASS`, `CONNECTOR_GATE=PASS`, `SVC_GATE=PASS`, `DEV_E2E=GO` y `ROLLBACK_DRILL=PASS`.
2. Si el plugin no intercepta una ruta protegida, Tasks 7-10 quedan en `NO-GO`.
3. Si `svc_midpoint` no funciona con `flags=0` y el conjunto exacto de permisos mínimos, no se toca ninguna cuenta humana.
4. El JAR, plugin y objetos MidPoint se despliegan como una versión coordinada; no se activa un estado humano si alguno difiere.

## Archivos previstos

### IGA

- Modify: `upeu/schemas/upeu-local-v1.0.xml` — parámetro `kohaLibraries` en `AssignmentType`.
- Modify: `upeu/resources/koha-upeu.xml` — unión funcional, `STAFF_SCOPE`, eliminación de `flags=1` para Dirección/Soporte.
- Modify: `upeu/roles/application/AR-Koha-Superadmin.xml` — guard preventivo para el OID de Juan.
- Modify: `upeu/roles/application/AR-Koha-Librarian-{Circulacion,ProcesosTecnicos,Direccion,Soporte,Supervision}.xml` — documentación y construction única si corresponde.
- Create: `upeu/roles/application/AR-Koha-Librarian-RegistroUsuarios.xml` — función independiente si la matriz final la requiere.
- Create: `upeu/tests/koha-scoped-access-static.sh` — pruebas XML y invariantes estáticas.
- Create: `upeu/tests/koha-scoped-access-dev.sh` y `upeu/tests/fixtures/koha-scoped-access/*.xml` — pruebas conductuales individuales en DEV.
- Create: `test-vectors/staff-authz-v1.json` — vector canónico compartido Java/Perl.
- Create: `docs/runbooks/koha-scoped-access-2026-07-21/README.md` — inventario, deltas, pilotos y rollback.

### Connector

- Modify: `src/main/java/com/identicum/connectors/mappers/PatronMapper.java` — round-trip multivaluado de `STAFF_SCOPE` y estado/hash usando `extended_attributes` existente.
- Modify: `src/main/java/com/identicum/connectors/services/PatronService.java` — protocolo de actualización fail-closed entre REST y JDBC.
- Create: `deploy/install-connector-koha.sh` — build, backup, checksum e instalación determinista del único JAR versionado.
- Test: `src/test/java/com/identicum/connectors/mappers/ExtendedAttributesTest.java`.
- Test: `src/test/java/com/identicum/connectors/services/PatronServiceTest.java`.
- Test: `src/test/java/com/identicum/connectors/KohaConnectorIntegrationTest.java`.
- Test: `test-vectors/staff-authz-v1.json` — copia idéntica validada por checksum.

### Koha UPeU

- Create: `plugins/Koha/Plugin/Com/UPeU/StaffScope.pm` — PoC y, solo si cubre la matriz, enforcement.
- Create: `plugins/t/StaffScope.t` — pruebas positivas, negativas y fail-closed.
- Create: `deploy/t/11-svc-midpoint-least-privilege.t` — pruebas del script técnico.
- Create: `test-vectors/staff-authz-v1.json` — copia idéntica validada por checksum.
- Create: `plugins/Makefile` — empaquetado `.kpz` reproducible.
- Create: `deploy/11-svc-midpoint-least-privilege.pl` — permisos API mínimos mediante Koha ORM.
- Create: `deploy/12-verify-scoped-access.pl` — verificación no destructiva de cuentas/scopes.
- Create: `context/24-koha-scoped-access-2026-07-21.md` — evidencia de PoC y matriz de rutas.

## Gate de seguridad

Si el plugin no puede negar de forma central y verificable las rutas CGI/REST requeridas, **detener el rollout**. No sustituir enforcement por CSS/JS. Documentar la brecha y crear un plan separado para un parche core versionado; no reducir los admins humanos en PROD hasta que función y scope puedan desplegarse juntos.

### Task 1: Congelar inventario, matriz y fixtures

**Files:**
- Create: `docs/runbooks/koha-scoped-access-2026-07-21/README.md`

- [ ] **Step 1: Capturar el baseline read-only de superadmins**

Run:

```bash
source ~/.secrets/koha-plus-prod.env && ssh "$KOHA_PLUS_SSH_USER@$KOHA_PLUS_SSH_HOST" "sudo koha-mysql upeu --batch --raw --execute=\"SELECT borrowernumber,cardnumber,userid,email,branchcode,flags FROM borrowers WHERE flags=1 ORDER BY borrowernumber;\""
```

Expected: break-glass, `svc_midpoint`, Juan y cinco admins humanos actuales.

- [ ] **Step 2: Registrar la matriz piloto aprobada**

Añadir al runbook:

```text
Juan Alberto Sánchez Condor / jsanchez@upeu.edu.pe -> SUPERADMIN / ALL
Elvira Mavel Brañes Juan de Dios                 -> ADMIN_LOCAL / BUL
David Leandro Orrego Granados                    -> ADMIN_LOCAL / BUL
Walter Eloy Luque Condori                        -> ADMIN_LOCAL / BUJ
Christiam Pool Castillo Cahuaza                  -> ADMIN_LOCAL / BUT
Jaime                                             -> CATALOGACION / BUL,CIA
```

Dejar `Juan Felipe Campos Adanaque` como “pendiente de función local” hasta confirmar si es Dirección, Soporte o Supervisión; no inferir el tier solo por `flags=1`.

- [ ] **Step 3: Elegir fixtures DEV sin transacciones reales**

Registrar un patron staff de prueba por `BUL`, `BUJ`, `BUT`, un catalogador `BUL+CIA`, un ejemplar prestable por sede y un ejemplar CIA `notforloan=1`.

- [ ] **Step 4: Guardar backups lógicos de objetos, no tablas completas**

Exportar vía REST los focos/shadows piloto, roles, SchemaType y resource `koha-upeu`; guardar fuera de Git con modo `600`.

- [ ] **Step 5: Commit**

```bash
git -C /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access add docs/runbooks/koha-scoped-access-2026-07-21/README.md
git -C /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access commit -m "docs: capture Koha scoped access rollout baseline"
git -C /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access push -u origin feature/koha-scoped-access
```

### Task 2: Añadir el parámetro tipado `kohaLibraries`

**Files:**
- Modify: `upeu/schemas/upeu-local-v1.0.xml`
- Create: `upeu/tests/koha-scoped-access-static.sh`

- [ ] **Step 1: Escribir la prueba estática que debe fallar**

Crear `upeu/tests/koha-scoped-access-static.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
xmllint --noout "$ROOT/upeu/schemas/upeu-local-v1.0.xml"
xmllint --xpath "count(//*[local-name()='complexType' and @name='AssignmentExtensionType']/*[local-name()='sequence']/*[local-name()='element' and @name='kohaLibraries' and @maxOccurs='unbounded'])" "$ROOT/upeu/schemas/upeu-local-v1.0.xml" | grep -qx '1'
```

- [ ] **Step 2: Ejecutar y comprobar el fallo**

Run: `bash /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access/upeu/tests/koha-scoped-access-static.sh`  
Expected: FAIL porque `AssignmentExtensionType/kohaLibraries` todavía no existe.

- [ ] **Step 3: Añadir la extensión de assignment**

Agregar dentro de la definición XSD del SchemaType:

```xml
<xsd:complexType name="AssignmentExtensionType">
  <xsd:annotation>
    <xsd:appinfo>
      <a:extension ref="c:AssignmentType"/>
      <a:displayName>Parámetros de asignación UPeU</a:displayName>
    </xsd:appinfo>
  </xsd:annotation>
  <xsd:sequence>
    <xsd:element name="kohaLibraries" type="xsd:string" minOccurs="0" maxOccurs="unbounded">
      <xsd:annotation><xsd:appinfo>
        <a:displayName>Biblioteca Koha autorizada</a:displayName>
        <a:help>Vocabulario: BUL|BUJ|BUT|CIA. Parámetro del assignment, no atributo global del foco.</a:help>
      </xsd:appinfo></xsd:annotation>
    </xsd:element>
  </xsd:sequence>
</xsd:complexType>
```

- [ ] **Step 4: Ejecutar la prueba**

Run: `bash /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access/upeu/tests/koha-scoped-access-static.sh`  
Expected: PASS.

- [ ] **Step 5: Importar primero en MidPoint DEV**

Aplicar con REST `PATCH` del SchemaType, nunca `PUT`; leerlo nuevamente y validar que un assignment de prueba acepta uno y varios `upeu:kohaLibraries`.

- [ ] **Step 6: Commit**

```bash
git -C /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access add upeu/schemas/upeu-local-v1.0.xml upeu/tests/koha-scoped-access-static.sh
git -C /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access commit -m "feat: add Koha library scope assignment parameter"
git -C /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access push
```

### Task 3: Hacer aditiva la autorización MidPoint

**Files:**
- Modify: `upeu/resources/koha-upeu.xml`
- Modify: `upeu/roles/application/AR-Koha-Superadmin.xml`
- Modify/Create: roles funcionales listados en “Archivos previstos”.
- Modify: `upeu/tests/koha-scoped-access-static.sh`
- Create: `upeu/scripts/20-patch-koha-scoped-objects.sh`

- [ ] **Step 1: Ejecutar fan-in y congelar el significado de los roles existentes**

Antes de editar o renombrar roles, ejecutar en `codebase-memory/query_graph`:

```cypher
MATCH (a)-[r:IMPORTS|CALLS|USAGE]->(b)
WHERE b.file_path CONTAINS 'AR-Koha-Librarian-'
  AND NOT a.file_path CONTAINS 'upeu/roles/application/'
RETURN DISTINCT a.file_path, a.name, type(r)
```

Registrar el resultado en el runbook. Mantener los OID y mapearlos exactamente así; no renombrarlos:

| OID | Rol actual | Función canónica |
|---|---|---|
| `dd74503c-7c12-4631-80ec-416aebc35319` | Circulacion | `CIRCULACION` |
| `337e8dc4-324e-454d-8c70-dcd50159af30` | ProcesosTecnicos | `CATALOGACION` |
| `d3303cec-7b05-4415-a19d-84a1c899f4c4` | Direccion | `ADMIN_LOCAL` |
| `8d3daccf-a76b-41ed-a772-1ccc5d273329` | Soporte | `ADMIN_LOCAL` |
| `03a2fc51-cda6-49d6-82b0-a00499afaf24` | Supervision | `CIRCULACION+REGISTRO_USUARIO` |
| `d698dc99-1a8c-479c-9eec-2a0214fdbf04` | Superadmin | `SUPERADMIN` solo Juan |

Cada rol funcional induce la misma construction `resource=koha-upeu`, `kind=account`, `intent=default`; la unión ocurre dentro de esa única construction y nunca crea una segunda proyección.

- [ ] **Step 2: Extender pruebas con invariantes de privilegio**

La prueba debe verificar:

```bash
! rg -n "assigned\.intersect\(admins\).*return 1" upeu/resources/koha-upeu.xml
rg -n "STAFF_SCOPE" upeu/resources/koha-upeu.xml
test "$(rg -o '763c5096-8010-427b-8c2b-b993268d270c' upeu/roles/application/AR-Koha-Superadmin.xml | wc -l | tr -d ' ')" = 1
! rg -n "d57aada4-1139-4b44-93b7-032afb077e30" upeu/roles/application/AR-Koha-Superadmin.xml
```

Expected before implementation: FAIL.

- [ ] **Step 3: Reescribir `flags` con baseline seguro**

Regla:

```groovy
if (assigned.contains(SUPERADMIN_ROLE)) return 1
if (!hasLiveCraiAccess) return null
if (!effectiveFunctionalRoles.isEmpty()) return 4  // catalogue, entrada staff
return null
```

Dirección y Soporte nunca retornan `1`.

- [ ] **Step 4: Reescribir `user_permissions` como unión**

Construir un `LinkedHashSet<String>` y sumar cada función activa. No usar `return` por prioridad. Canonicalizar con `sort()` antes de devolver.

Permisos iniciales:

```text
CIRCULACION      -> 1:circulate_remaining_permissions, 4:list_borrowers,
                    4:edit_borrowers
CATALOGACION     -> 9:edit_catalogue, 9:edit_items, 13:label_creator
REGISTRO_USUARIO -> 4:list_borrowers, 4:edit_borrowers
ADMIN_LOCAL      -> unión aprobada de las tres funciones, sin parameters,
                    permissions, plugins, reports SQL ni staffaccess global
```

Validar todos los pares contra `userflags` y `permissions` de Koha 26.05 antes de fijarlos. El primer rollout excluye explícitamente reservas, importación MARC, procesos batch, parámetros globales, gestión de permisos, plugins y reportes SQL. Añadir pruebas negativas para `place_holds`, `manage_staged_marc`, `stage_marc_import`, `parameters`, `permissions`, `plugins` y `reports`.

- [ ] **Step 5: Materializar scope y estado de autorización**

Iterar solo assignments efectivos (`activation/effectiveStatus=enabled`, dentro de `validFrom/validTo`) de roles Koha, leer `assignment/extension/upeu:kohaLibraries`, filtrar `BUL|BUJ|BUT|CIA`, hacer `unique().sort()` y producir un JSON por biblioteca:

```text
{"type":"STAFF_SCOPE","value":"BUL"}
```

Agregar `STAFF_SCOPE`, `STAFF_SCOPE_STATE` y `STAFF_AUTHZ_HASH` al rango gobernado de `extended_attributes`. Empty set para un staff funcional debe quedar en `deny`, visible como error de policy y nunca caer a ALL.

La entrada del hash es JSON UTF-8 sin BOM ni salto final, con claves en el orden fijo `flags,permissions,scopes,version`, sin whitespace, enteros JSON, strings escapados según RFC 8259, arrays sin nulos/duplicados y ordenados lexicográficamente por bytes UTF-8. Todos los campos existen; `permissions` y `scopes` vacíos se representan como `[]`. La salida es SHA-256 hexadecimal lowercase. Golden vector común Java/Perl:

```text
{"flags":4,"permissions":["1:circulate_remaining_permissions","4:edit_borrowers","4:list_borrowers"],"scopes":["BUL"],"version":"v1"}
c7b1bb78552d674e428ca0a965e9a59ad17268fdde3e47576508477ba5ffbd62
```

- [ ] **Step 6: Añadir policy preventiva de Superadmin**

La asignación `AR-Koha-Superadmin` debe aceptar solo el focus OID `763c5096-8010-427b-8c2b-b993268d270c`. Probar conductualmente en DEV: asignación a Juan permitida; asignación a Elvira (`d57aada4-1139-4b44-93b7-032afb077e30`) rechazada con policy violation.

- [ ] **Step 7: Añadir fixtures MidPoint y pruebas conductuales**

Crear `upeu/tests/fixtures/koha-scoped-access/{active,future,expired,disabled,union-order-a,union-order-b,remove-cia,empty-scope}.xml` y el runner `upeu/tests/koha-scoped-access-dev.sh`. El runner solo acepta `--focus-oid` explícito, aplica PATCH por container ID, ejecuta recompute individual y cuenta shadows `account/default`; rechaza cualquier opción de task/reconcile masiva.

RED antes del mapping:

```bash
bash /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access/upeu/tests/koha-scoped-access-dev.sh --env dev --focus-oid TEST_FOCUS_OID --case all
```

Expected: falla al menos unión/scope/expiración. GREEN posterior: mismo comando PASS para assignment activo, futuro, expirado y deshabilitado; unión independiente del orden; retiro diferencial `BUL,CIA -> BUL`; recompute individual idempotente; scope vacío fail-closed; exactamente un shadow antes/después.

- [ ] **Step 8: Validar XML y pruebas**

Run:

```bash
cd /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access && bash upeu/tests/koha-scoped-access-static.sh
cd /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access && xmllint --noout upeu/resources/koha-upeu.xml upeu/roles/application/AR-Koha-*.xml
```

Expected: PASS.

Crear y probar `upeu/scripts/20-patch-koha-scoped-objects.sh` con `--check/--apply/--verify`, allowlist fija de OID/items y rechazo explícito de PUT o endpoints de task/reconcile. `--check` debe pasar sin escribir.

- [ ] **Step 9: Commit**

```bash
git -C /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access add upeu/resources/koha-upeu.xml upeu/roles/application upeu/tests test-vectors upeu/scripts/20-patch-koha-scoped-objects.sh
git -C /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access commit -m "feat: derive additive Koha permissions and staff scope"
git -C /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access push
```

### Task 4: Implementar materialización atómica fail-closed en connector-koha

**Files:**
- Modify/Test: archivos del bloque Connector.

- [ ] **Step 1: Crear una rama/worktree propia del connector**

Run:

```bash
git -C /Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha worktree add /Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha/.worktrees/koha-staff-scope -b feature/koha-staff-scope
```

- [ ] **Step 2: Escribir pruebas fallidas**

Casos mínimos en `ExtendedAttributesTest`:

```java
assertRoundTrip(List.of(
  "{\"type\":\"STAFF_SCOPE\",\"value\":\"BUL\"}",
  "{\"type\":\"STAFF_SCOPE\",\"value\":\"CIA\"}"
));
```

Añadir pruebas de eliminación diferencial `BUL,CIA -> BUL`, preservación de pares no gobernados y payload vacío.

Añadir pruebas de fallo inyectado después de cada frontera del protocolo: antes/después de `deny`, después de JDBC, después de verificación y antes de `active`. En todos los casos parciales el patron debe quedar denegado, nunca con permisos nuevos y scope antiguo ni a la inversa.

- [ ] **Step 3: Ejecutar solo las pruebas relevantes**

Run:

```bash
mvn -q -f /Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha/.worktrees/koha-staff-scope/pom.xml -Dtest=ExtendedAttributesTest,PatronServiceTest,KohaConnectorIntegrationTest test
```

Expected: el nuevo caso falla si existe normalización o pérdida de valores.

- [ ] **Step 4: Implementar el protocolo exacto**

Para create/update/recompute/delete lógico de autorización:

1. Calcular versión, scope ordenado, permisos ordenados y hash canónico con la serialización exacta y golden vector compartido.
2. REST: escribir `STAFF_SCOPE_STATE=deny:<version>`, el nuevo `STAFF_SCOPE` y `STAFF_AUTHZ_HASH=<hash>`.
3. JDBC: en una transacción reemplazar `flags` y `user_permissions` por el conjunto exacto.
4. Leer REST y JDBC, recalcular hash y exigir igualdad exacta.
5. REST: cambiar únicamente a `STAFF_SCOPE_STATE=active:<version>`.
6. Leer nuevamente; si cualquier paso falla, lanzar error y conservar/forzar estado `deny`.

El plugin recalcula el mismo hash desde scope, flags y permisos actuales y solo autoriza si el estado es `active`, la versión es soportada y el hash coincide. El rollback empieza siempre escribiendo `deny`; no existe fallback a la autorización anterior. JUnit y Perl deben consumir el mismo archivo fixture `test-vectors/staff-authz-v1.json`. Si este protocolo no puede probarse de extremo a extremo, marcar `CONNECTOR_GATE=FAIL` y detener el rollout.

Si los fallos inyectados, round-trip, golden vector y suite completa pasan, registrar `CONNECTOR_GATE=PASS` con checksum del artefacto.

- [ ] **Step 5: Ejecutar suite completa**

Run: `mvn -f /Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha/.worktrees/koha-staff-scope/pom.xml test`  
Expected: BUILD SUCCESS.

Crear `deploy/install-connector-koha.sh` con `--apply/--verify`: obtiene una versión exacta de `pom.xml`, exige exactamente un JAR correspondiente, construye con Maven container, conserva backup/checksum del JAR activo, instala con modo `0644` y compara checksums. Probar primero con un directorio temporal; un glob con cero o múltiples candidatos debe fallar.

- [ ] **Step 6: Commit y release candidata**

```bash
git -C /Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha/.worktrees/koha-staff-scope add src/main src/test test-vectors deploy/install-connector-koha.sh pom.xml
git -C /Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha/.worktrees/koha-staff-scope commit -m "feat: materialize Koha authorization fail closed"
git -C /Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha/.worktrees/koha-staff-scope push -u origin feature/koha-staff-scope
mvn -f /Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha/.worktrees/koha-staff-scope/pom.xml -DskipTests package
```

No desplegar el JAR en PROD en esta tarea.

### Task 5: PoC de enforcement Koha 26.05

**Files:**
- Create: `plugins/Koha/Plugin/Com/UPeU/StaffScope.pm`
- Create: `plugins/t/StaffScope.t`
- Create: `plugins/Makefile`
- Create: `deploy/13-install-staff-scope-plugin.sh`
- Create: `context/24-koha-scoped-access-2026-07-21.md`

- [ ] **Step 1: Crear rama/worktree del overlay UPeU**

Run:

```bash
git -C /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha worktree add /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope -b feature/staff-scope
```

- [ ] **Step 2: Inventariar puntos de enforcement**

Registrar para login/cambio de branch, circulación, patrones, ejemplares, transferencias, CGI directo, REST, jobs y batch:

```text
ruta | método | permiso core | objeto | branch objetivo | hook/punto core | prueba negativa
```

- [ ] **Step 3: Escribir pruebas fail-closed**

`StaffScope.t` debe cubrir al menos:

```perl
is_deeply effective_scope($patron), [qw(BUL CIA)];
ok authorize($patron, 'edit_item', { homebranch => 'CIA' });
ok !authorize($patron, 'edit_item', { homebranch => 'BUJ' });
ok !authorize($patron, 'edit_item', { homebranch => undef });
ok !authorize($patron, 'place_hold', { branchcode => 'BUL' });
ok !authorize($patron, 'stage_marc_import', { branchcode => 'BUL' });
```

Repetir pruebas positivas y negativas por cada ruta CGI/REST incluida. Para jobs, batch, reservas e importación MARC del primer rollout, la única expectativa válida es denegación. Probar request directo sin UI y registrar status/redirect/body.

Ejecutar RED antes del plugin y GREEN después:

```bash
cd /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope && prove -lv plugins/t/StaffScope.t
```

Expected RED: paquete/hook ausente o casos negativos fallan. Expected GREEN: todos los casos puros y las rutas instrumentadas pasan.

- [ ] **Step 4: Implementar el núcleo puro**

Separar `effective_scope`, `target_branch`, `canonical_authz_hash` y `authorize`. El plugin no intenta resolver OID de MidPoint: el bypass superlibrarian se basa exclusivamente en `flags=1`; el guard del rol MidPoint limita el superadmin SSO al focus OID de Juan y la auditoría exige que los únicos `flags=1` sean Juan y el break-glass local. Para el resto, estado distinto de `active`, versión no soportada, hash inconsistente, scope ausente/inválido u objeto sin biblioteca resoluble retorna deny. Ninguna decisión depende solo de la UI, email o nombre mutable.

- [ ] **Step 5: Conectar únicamente rutas realmente interceptables**

Ejecutar pruebas directas CGI, REST, jobs y batch en Koha DEV. Si una ruta protegida evita el plugin o no entrega branch objetivo, marcar PoC `FAILED`, no empaquetar como solución. El log de cada denegación debe incluir `userid`, función, biblioteca efectiva, biblioteca/objeto objetivo, operación y razón, sin datos sensibles.

- [ ] **Step 6: Gate de decisión**

Expected para continuar: todas las rutas del primer rollout tienen prueba negativa PASS.  
Si no: documentar la brecha y detener Tasks 7-10 hasta aprobar un plan de parche core.

Crear `deploy/13-install-staff-scope-plugin.sh` con `--apply/--verify`, destino fijo por `--instance`, checksum origen/destino, instalación por `install_plugins.pl --include` y health HTTP. Probarlo primero contra un directorio temporal y luego en DEV.

- [ ] **Step 7: Commit**

```bash
git -C /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope add plugins deploy/13-install-staff-scope-plugin.sh test-vectors context/24-koha-scoped-access-2026-07-21.md
git -C /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope commit -m "feat: prove server-side Koha staff scope enforcement"
git -C /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope push -u origin feature/staff-scope
```

### Task 6: Reducir `svc_midpoint` en DEV

**Files:**
- Create: `deploy/11-svc-midpoint-least-privilege.pl`
- Create: `deploy/t/11-svc-midpoint-least-privilege.t`

- [ ] **Step 1: Escribir modo `--check`**

El script debe resolver `userid=svc_midpoint`, mostrar flags/permisos actuales y salir sin modificar.

- [ ] **Step 2: Escribir modo `--apply` con Koha ORM**

Objetivo:

```text
flags = 0
borrowers:list_borrowers
borrowers:edit_borrowers
ningún otro user_permission
sin delete_borrowers, login SSO staff ni login OPAC
```

No usar `UPDATE`/`INSERT` SQL manual.

- [ ] **Step 3: Escribir primero pruebas del script**

Probar `--check`, `--apply`, idempotencia, usuario inexistente y snapshot inválido. Las aserciones deben comparar conjuntos exactos: `flags=0` y solamente `list_borrowers + edit_borrowers`; cualquier permiso adicional falla.

Run RED/GREEN:

```bash
cd /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope && prove -lv deploy/t/11-svc-midpoint-least-privilege.t
```

Expected RED antes del script; PASS después.

- [ ] **Step 4: Probar OAuth y CRUD en DEV**

Ejecutar token, búsqueda, create/update de fixture, extended attributes y reconcile individual. Probar DELETE y esperar `403`. Probar login SSO staff y OPAC de `svc_midpoint` y esperar denegación. Confirmar que create/update funciona con `flags=0`; si requiere elevarlo, `SVC_GATE=FAIL`.

- [ ] **Step 5: Rollback DEV y repetición**

Verificar que el script es idempotente y que el rollback usa el snapshot del patron técnico, no valores hardcoded. Después del ensayo, reaplicar el baseline mínimo exacto y repetir CRUD/DELETE/SSO antes de declarar `SVC_GATE=PASS`.

- [ ] **Step 6: Commit**

```bash
git -C /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope add deploy/11-svc-midpoint-least-privilege.pl deploy/t/11-svc-midpoint-least-privilege.t
git -C /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope commit -m "security: reduce MidPoint Koha API service privileges"
git -C /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope push
```

### Task 7: Desplegar el stack DEV inactivo

**Files:**
- Use: `upeu/scripts/20-patch-koha-scoped-objects.sh` — PATCH y read-back de SchemaType/roles/resource.
- Use: `deploy/13-install-staff-scope-plugin.sh` — instalación idempotente y health del plugin.
- Modify: runbook IGA y evidencia Koha.

- [ ] **Step 1: Publicar tags candidatos y comprobar SHA**

Crear `koha-scope-dev-2026-07-21` en cada rama y publicarlo. En cada checkout remoto ejecutar `git fetch --tags`, `git pull --ff-only` y exigir:

```bash
test "$(git rev-parse HEAD)" = "$(git rev-list -n 1 koha-scope-dev-2026-07-21)"
```

Koha DEV no tenía checkout: crearlo una sola vez con `git clone git@github.com:UPeU-Infra/upeu-koha.git /home/juansanchez/upeu-koha`; después usar siempre `git -C /home/juansanchez/upeu-koha pull --ff-only`.

- [ ] **Step 2: Instalar plugin DEV en estado deny por defecto**

El script `deploy/13-install-staff-scope-plugin.sh` usa un staging temporal y sincroniza únicamente `Koha/Plugin/Com/UPeU/StaffScope*`; nunca ejecuta `--delete` sobre `plugins/Koha/` ni puede tocar plugins ajenos. Ejecutar:

```bash
sudo /home/juansanchez/upeu-koha/deploy/13-install-staff-scope-plugin.sh --instance upeu --apply
sudo /home/juansanchez/upeu-koha/deploy/13-install-staff-scope-plugin.sh --instance upeu --verify
```

`--verify` obtiene ambos hashes y exige igualdad con `test`, confirma la clase instalada vía `install_plugins.pl --include` y health HTTP 200. Sin estado `active` válido, todos los fixtures scoped quedan denegados.

- [ ] **Step 3: Construir e instalar JAR candidato DEV**

En el host MidPoint DEV, usar el instalador versionado, sin globs:

```bash
/home/juansanchez/connector-koha/deploy/install-connector-koha.sh --repo /home/juansanchez/connector-koha --target /opt/midpoint/connectors --apply
/home/juansanchez/connector-koha/deploy/install-connector-koha.sh --repo /home/juansanchez/connector-koha --target /opt/midpoint/connectors --verify
```

El script obtiene la versión exacta de `pom.xml`, exige un solo JAR, compara origen/destino con `test` y falla ante cero/múltiples artefactos. Solicitar aprobación antes de reiniciar MidPoint DEV. Después del reinicio: `curl --fail -u "$MIDPOINT_DEV_ADMIN_USER:$MIDPOINT_DEV_ADMIN_PASS" "$MIDPOINT_DEV_URL/ws/rest/users?paging=maxSize=1"` y verificar HTTP 200.

- [ ] **Step 4: PATCH de objetos MidPoint DEV sin activación humana**

`upeu/scripts/20-patch-koha-scoped-objects.sh --env dev --check` valida OID, versión y XML; `--apply` emite únicamente REST PATCH de los items modificados y hace GET/read-back por OID. Ejecutar:

```bash
bash /home/juansanchez/midPointEcosystem/upeu/scripts/20-patch-koha-scoped-objects.sh --env dev --check
bash /home/juansanchez/midPointEcosystem/upeu/scripts/20-patch-koha-scoped-objects.sh --env dev --apply
bash /home/juansanchez/midPointEcosystem/upeu/scripts/20-patch-koha-scoped-objects.sh --env dev --verify
```

Prohibido PUT. No asignar roles a humanos ni fixtures todavía. Registrar checksums, SHA y health; este paso solo deja disponible el stack inactivo.

### Task 8: Ensayar rollback, redesplegar y ejecutar E2E DEV

**Files:**
- Modify: runbook IGA y evidencia Koha.

- [ ] **Step 1: Aplicar un único fixture DEV y comenzar rollback en deny**

Usar REST PATCH por focus/container ID, nunca task masiva. Escribir `STAFF_SCOPE_STATE=deny:<rollback-version>` y verificar denegación CGI/REST antes de tocar assignments o artefactos.

- [ ] **Step 2: Neutralizar permisos humanos antes de retirar enforcement**

Con el plugin actual todavía activo, materializar en cada fixture scoped `flags=0`, `user_permissions=[]`, estado `deny`; leer por REST/JDBC y comprobar denegación CGI/REST directa. Este estado neutro es obligatorio antes de cualquier downgrade.

- [ ] **Step 3: Retirar assignment y revertir sin abrir una ventana global**

Retirar el assignment por container ID y recompute individual; verificar un shadow. Revertir resource/roles/SchemaType y JAR. No retirar el último enforcement que entiende `deny`: instalar primero un `deny-shim` compatible y verificarlo, o conservar el plugin actual permanentemente. Solo después puede desactivarse la versión completa. Nunca restaurar el XML que daba `flags=1` a Dirección/Soporte ni elevar `svc_midpoint`.

- [ ] **Step 4: Verificar y repetir fronteras de fallo**

Comprobar `flags=0`, permisos vacíos, denegación CGI/REST, SSO no privilegiado y un shadow. Ensayar fallos REST/JDBC/verificación/activación. Solo entonces `ROLLBACK_DRILL=PASS`.

- [ ] **Step 5: Redesplegar el stack candidato y baseline técnico**

Repetir Task 7 por los mismos tags/checksums, reaplicar a `svc_midpoint` `flags=0` + exactamente `list_borrowers/edit_borrowers`, y repetir CRUD, DELETE 403 y SSO denegado. Expected: `PLUGIN_GATE=PASS`, `CONNECTOR_GATE=PASS`, `SVC_GATE=PASS`.

- [ ] **Step 6: Ejecutar matriz E2E**

Asignar scopes solo a fixtures. Probar allow/deny por CGI, REST, job y batch para BUL, BUL+CIA, BUJ y BUT; un único shadow; otro catalogador BUL no hereda CIA; el de BUL+CIA no accede BUJ/BUT; orden de assignments indiferente; expiración/retiro diferencial; recompute idempotente; SSO staff/OPAC; logs de denegación completos.

- [ ] **Step 7: Registrar GO/NO-GO**

Solo `DEV_E2E=GO` si `PLUGIN_GATE=PASS`, `CONNECTOR_GATE=PASS`, `SVC_GATE=PASS`, `ROLLBACK_DRILL=PASS` y toda la matriz anterior es PASS.

### Task 9: Preparar y ejecutar piloto PROD

**Files:**
- Modify: `docs/runbooks/koha-scoped-access-2026-07-21/README.md`

- [ ] **Step 1: Crear tags y backups previos**

Crear y publicar tags inmutables en cada repo:

```bash
git -C /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access tag koha-scope-prod-2026-07-21
git -C /Users/alberto/proyectos/productos/iga/canonico/.worktrees/koha-scoped-access push origin koha-scope-prod-2026-07-21
git -C /Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha/.worktrees/koha-staff-scope tag koha-scope-prod-2026-07-21
git -C /Users/alberto/proyectos/productos/iga/instituciones/upeu/connector-koha/.worktrees/koha-staff-scope push origin koha-scope-prod-2026-07-21
git -C /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope tag koha-scope-prod-2026-07-21
git -C /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope push origin koha-scope-prod-2026-07-21
```

Exportar por REST objetos MidPoint y snapshot lógico ORM de las cuentas piloto/configuración plugin. No incluir secretos en Git.

- [ ] **Step 2: Actualizar checkouts PROD y desplegar enforcement**

Rutas verificadas:

```text
MidPoint PROD: /home/juansanchez/midPointEcosystem
Connector PROD: /home/juansanchez/connector-koha
Koha PROD:      /home/juansanchez/upeu-koha
```

Por SSH ejecutar `git -C <ruta> fetch --tags`, validar el SHA/tag y `git -C <ruta> pull --ff-only`. Instalar primero plugin, después JAR y finalmente PATCH de SchemaType/roles/resource. Solicitar aprobación explícita antes de reiniciar Plack o MidPoint. Tras cada artefacto, verificar checksum y health antes de continuar.

Después de integrar las ramas aprobadas a la rama de despliegue, ejecutar exactamente:

```bash
source /Users/alberto/.secrets/koha-plus-prod.env && ssh "$KOHA_PLUS_SSH_USER@$KOHA_PLUS_SSH_HOST" "git -C /home/juansanchez/upeu-koha fetch --tags && git -C /home/juansanchez/upeu-koha pull --ff-only && test \"\$(git -C /home/juansanchez/upeu-koha rev-parse HEAD)\" = \"\$(git -C /home/juansanchez/upeu-koha rev-list -n 1 koha-scope-prod-2026-07-21)\""
source /Users/alberto/.secrets/midpoint-upeu.env && sshpass -p "$MIDPOINT_PROD_PASS" ssh "$MIDPOINT_PROD_USER@$MIDPOINT_PROD_HOST" "git -C /home/juansanchez/connector-koha fetch --tags && git -C /home/juansanchez/connector-koha pull --ff-only && test \"\$(git -C /home/juansanchez/connector-koha rev-parse HEAD)\" = \"\$(git -C /home/juansanchez/connector-koha rev-list -n 1 koha-scope-prod-2026-07-21)\""
source /Users/alberto/.secrets/midpoint-upeu.env && sshpass -p "$MIDPOINT_PROD_PASS" ssh "$MIDPOINT_PROD_USER@$MIDPOINT_PROD_HOST" "git -C /home/juansanchez/midPointEcosystem fetch --tags && git -C /home/juansanchez/midPointEcosystem pull --ff-only && test \"\$(git -C /home/juansanchez/midPointEcosystem rev-parse HEAD)\" = \"\$(git -C /home/juansanchez/midPointEcosystem rev-list -n 1 koha-scope-prod-2026-07-21)\""
```

No usar `git checkout <tag>` en PROD ni desplegar commits no integrados. El SHA leído debe coincidir con el commit etiquetado aprobado.

Instalar y verificar mediante scripts versionados:

```bash
source /Users/alberto/.secrets/koha-plus-prod.env && ssh "$KOHA_PLUS_SSH_USER@$KOHA_PLUS_SSH_HOST" "sudo /home/juansanchez/upeu-koha/deploy/13-install-staff-scope-plugin.sh --instance upeu --apply && sudo /home/juansanchez/upeu-koha/deploy/13-install-staff-scope-plugin.sh --instance upeu --verify"
source /Users/alberto/.secrets/midpoint-upeu.env && sshpass -p "$MIDPOINT_PROD_PASS" ssh "$MIDPOINT_PROD_USER@$MIDPOINT_PROD_HOST" "/home/juansanchez/connector-koha/deploy/install-connector-koha.sh --repo /home/juansanchez/connector-koha --target /opt/midpoint/connectors --apply && /home/juansanchez/connector-koha/deploy/install-connector-koha.sh --repo /home/juansanchez/connector-koha --target /opt/midpoint/connectors --verify"
source /Users/alberto/.secrets/midpoint-upeu.env && sshpass -p "$MIDPOINT_PROD_PASS" ssh "$MIDPOINT_PROD_USER@$MIDPOINT_PROD_HOST" "bash /home/juansanchez/midPointEcosystem/upeu/scripts/20-patch-koha-scoped-objects.sh --env prod --check && bash /home/juansanchez/midPointEcosystem/upeu/scripts/20-patch-koha-scoped-objects.sh --env prod --apply && bash /home/juansanchez/midPointEcosystem/upeu/scripts/20-patch-koha-scoped-objects.sh --env prod --verify"
```

Los instaladores rechazan múltiples JAR, guardan backup con checksum, comparan origen/destino y hacen health (`mainpage.pl` HTTP 200; MidPoint REST HTTP 200). Solicitar aprobación antes de cualquier reinicio requerido.

- [ ] **Step 3: Reducir `svc_midpoint` y verificar gate**

Aplicar baseline exacto `flags=0`, solamente `list_borrowers + edit_borrowers`; verificar CRUD/recompute individual, DELETE 403 y SSO staff/OPAC denegado antes de tocar humanos.

- [ ] **Step 4: Dejar armado el rollback PROD fail-closed**

Secuencia obligatoria, ejecutable por lista explícita de `borrowernumber`/focus OID:

1. Con plugin vigente, escribir `deny:<rollback-version>`.
2. Materializar vía conector/ORM `flags=0` y permisos vacíos para cada humano afectado; verificar REST/JDBC y denegación CGI/REST.
3. Retirar assignments por container ID y recompute individual; verificar un shadow.
4. Revertir mappings y JAR solo después del estado neutro. Mantener el plugin actual o instalar antes el `deny-shim`; nunca retirar el último componente que entiende `deny` mientras exista algún humano con permisos no vacíos.
5. Mantener humanos en acceso neutro hasta corregir/reaplicar el stack. Reaplicar a `svc_midpoint` su baseline mínimo; nunca restaurar `flags=1` de Dirección/Soporte.

Guardar la lista de deltas inversos y comprobarla con `--check`; no ejecutar todavía.

- [ ] **Step 5: Piloto humano único**

Elegir primero un admin local que esté acompañado operativamente. Aplicar función+scope en la misma ventana y reconciliar solo su foco.

- [ ] **Step 6: Validar positivo y negativo**

Debe entrar por SSO, operar en su branch y recibir `403`/denegación directa fuera del scope. Verificar `flags=4`, estado/hash activos y un solo shadow.

- [ ] **Step 7: Ampliar de uno en uno**

Orden sugerido: Elvira BUL → Walter BUJ → Christiam BUT → David BUL → Jaime BUL+CIA → Juan Felipe tras confirmar su tier.

- [ ] **Step 8: Verificar invariante global**

Expected en humanos SSO: solo `jsanchez@upeu.edu.pe` con `flags=1`. Break-glass local intacto; `svc_midpoint` granular.

### Task 10: Validar movilidad multicampus sin cambiar home library

**Files:**
- Create: `deploy/12-verify-scoped-access.pl`
- Modify: runbook/evidencia.

- [ ] **Step 1: Confirmar preferencias sin modificarlas**

Expected: `IndependentBranches=0`, `AllowReturnToBranch=anywhere`, `AutomaticItemReturn=1`, `CircControl=ItemHomeLibrary`, `UseBranchTransferLimits=0`.

- [ ] **Step 2: Préstamo cruzado con fixture**

Un patron BUJ usa un ejemplar BUL y viceversa. No cambiar `borrowers.branchcode`.

- [ ] **Step 3: Devolución cruzada**

Devolver en otra sede y comprobar transferencia/retorno esperado.

- [ ] **Step 4: Prueba negativa CIA**

Intentar prestar un fixture CIA `notforloan=1`; Expected: bloqueo sin override.

- [ ] **Step 5: Validación final y commit de evidencia**

```bash
git -C /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope add deploy/12-verify-scoped-access.pl context/24-koha-scoped-access-2026-07-21.md
git -C /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope commit -m "test: verify Koha multicampus circulation and scope"
git -C /Users/alberto/proyectos/productos/koha/instituciones/upeu/upeu-koha/.worktrees/staff-scope push
```

## Resultado de aceptación

- Solo `jsanchez@upeu.edu.pe` es superadmin humano SSO.
- Break-glass continúa local e independiente.
- `svc_midpoint` tiene `flags=0`, solamente `list_borrowers + edit_borrowers`, DELETE 403 y no puede iniciar sesión por SSO staff/OPAC.
- Admins locales y Jaime están limitados a sus bibliotecas incluso por URL/API directa.
- Christiam Pool Castillo es admin local de Tarapoto (`BUT`) y no accede administrativamente a `BUL`, `BUJ` ni `CIA`.
- Elvira y David son admin local solo `BUL`; Walter solo `BUJ`; ninguno accede a parámetros globales, permisos, plugins, reportes SQL, reservas ni importación/batch.
- Jaime puede catalogar en `BUL+CIA`; otro catalogador `BUL` no hereda `CIA`.
- Cada persona conserva un patrón y un shadow consolidado.
- El login SSO staff funciona para cada empleado autorizado; OPAC sigue autenticando por SSO según su cuenta de patron, sin convertirlo en staff fuera de su rol.
- Un recompute individual repetido no eleva privilegios, no revierte scopes y no crea shadows adicionales.
- Toda denegación auditable registra usuario, función, biblioteca efectiva, objeto/biblioteca objetivo y operación.
- Los usuarios viajan y usan otra sede sin cambiar su biblioteca de origen.
- Devoluciones cruzadas generan la transferencia prevista.
- CIA sigue bloqueando préstamos de sus 3.564 ejemplares.
