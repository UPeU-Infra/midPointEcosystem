# Koha consolidado: autorización del personal y movilidad multicampus

**Fecha:** 2026-07-21  
**Estado:** aprobado funcionalmente; implementación condicionada al PoC de enforcement server-side  
**Ámbito:** Koha UPeU consolidado, MidPoint PROD y SSO Keycloak

## 1. Objetivo

Separar dos políticas que no deben confundirse:

1. **Movilidad de usuarios/patrones:** una persona mantiene un único patrón y puede usar las bibliotecas de otros campus durante una visita temporal.
2. **Autorización del personal CRAI:** cada trabajador accede únicamente a las funciones y bibliotecas asignadas; solo Juan Alberto Sánchez conserva superlibrarian global.

No se cambia la afiliación, el campus autoritativo, el lifecycle ni el archetype de ninguna persona. RR. HH. y el sistema académico continúan siendo las IIAs de esos atributos. Los permisos excepcionales se gobiernan con assignments MidPoint.

## 2. Estado vivo verificado

Instancia Koha consolidada: `koha-common 26.05.01-1`.

Bibliotecas:

| Código | Biblioteca |
|---|---|
| `BUL` | Biblioteca Lima |
| `BUJ` | Biblioteca Juliaca |
| `BUT` | Biblioteca Tarapoto |
| `CIA` | Biblioteca CIA |

Preferencias relevantes:

| Preferencia | Valor vivo | Decisión |
|---|---:|---|
| `IndependentBranches` | `0` | Conservar; permite movilidad entre campus. |
| `AllowReturnToBranch` | `anywhere` | Conservar; devolución en cualquier biblioteca. |
| `AutomaticItemReturn` | `1` | Conservar; genera el retorno/transferencia correspondiente. |
| `UseBranchTransferLimits` | `0` | Conservar mientras no exista política aprobada de bloqueos entre sedes. |
| `CircControl` | `ItemHomeLibrary` | Conservar; la política de préstamo la determina la biblioteca propietaria del ejemplar. |
| `HomeOrHoldingBranch` | `homebranch` | Conservar. |
| `ReservesControlBranch` | `PatronLibrary` | Revisar en la fase de reservas, sin cambiarlo en este despliegue. |

Existen 54 reglas globales de circulación para `affiliate`, `alum`, `faculty`, `staff`, `student` y `WALKIN`. No hay todavía reglas específicas por branch. Los 3.564 ejemplares de CIA tienen `notforloan=1`; el valor no tiene descripción en `authorised_values`, por lo que la condición de consulta en sala debe probarse intentando un préstamo y no inferirse solo desde la columna.

Inventario vivo `flags=1`:

| Tipo | Cuenta |
|---|---|
| Break-glass local | `SUPERADMIN/superadmin` |
| Servicio no interactivo | `SVC-MIDPOINT/svc_midpoint` |
| Humano objetivo superadmin | Juan Alberto Sánchez |
| Humano a reducir | Walter Eloy Luque Condori |
| Humano a reducir | Elvira Mavel Brañes Juan de Dios |
| Humano a reducir | Juan Felipe Campos Adanaque |
| Humano a reducir | David Leandro Orrego Granados |
| Humano a reducir | Christiam Pool Castillo Cahuaza |

“Solo Juan es superadmin” significa un solo **humano con SSO**. La cuenta break-glass es la única excepción local, exigida por el guardarraíl operativo: no se vincula a Keycloak/MidPoint, se custodia y se audita. `svc_midpoint` no es una excepción permanente: debe perder `flags=1` antes del rollout humano.

Koha 26.05 declara en Swagger que la API usada por el conector requiere `borrowers:list_borrowers` para búsquedas/lecturas y `borrowers:edit_borrowers` para crear, actualizar y mantener atributos extendidos. `delete_borrowers` no se concede porque el resource tiene delete deshabilitado. El permiso mínimo de `svc_midpoint` se probará primero en DEV; no se reduce en PROD hasta verificar create/read/update y reconciliación individual.

## 3. Principios de autorización

- `flags=1` queda reservado a Juan entre humanos con SSO y a `SUPERADMIN/superadmin` como break-glass local independiente. `svc_midpoint` debe operar con permisos API granulares.
- Director, TI o responsable de biblioteca no equivalen a superlibrarian.
- Función y alcance son ejes independientes.
- Un usuario conserva una sola proyección `account/default` y un solo shadow en el resource Koha consolidado.
- El `branchcode` del patrón es su biblioteca de origen; no representa todas las bibliotecas en las que un trabajador puede operar.
- MidPoint asigna policy; Koha materializa y hace cumplir la autorización.
- No se usa SQL directo para conceder permisos.

## 4. Modelo RBAC seleccionado

### 4.1 Roles funcionales

| Rol | Capacidad |
|---|---|
| `AR-Koha-Superadmin` | Todas las funciones y bibliotecas; asignación manual y privilegiada. |
| `AR-Koha-AdminBiblioteca` | Administración operativa de una o más bibliotecas, sin administración global del sistema. |
| `AR-Koha-Circulacion` | Préstamos, devoluciones y renovaciones; reservas se excluyen del primer rollout. |
| `AR-Koha-Catalogacion` | Registros bibliográficos, ejemplares, autoridades e importación MARC según permisos aprobados. |
| `AR-Koha-RegistroUsuarios` | Buscar, crear y actualizar patrones dentro del alcance permitido. |

Los roles existentes `AR-Koha-Librarian-*` podrán conservar sus OID y renombrarse solo si el análisis de fan-in confirma que no rompe templates ni lookup tables. La implementación debe evitar role explosion: el alcance no se codifica creando un rol distinto para cada combinación de bibliotecas.

### 4.2 Parámetro de alcance

Cada assignment funcional admite un parámetro multivaluado:

```text
kohaLibraries = [BUL, CIA, BUJ, BUT]
```

Ejemplos:

| Persona | Rol | Alcance |
|---|---|---|
| Juan Alberto Sánchez | `AR-Koha-Superadmin` | Todas |
| Elvira Mavel Brañes Juan de Dios | `AR-Koha-AdminBiblioteca` | `BUL` |
| David | `AR-Koha-AdminBiblioteca` | `BUL` |
| Walter Eloy Luque Condori | `AR-Koha-AdminBiblioteca` | `BUJ` |
| Christiam Pool Castillo Cahuaza | `AR-Koha-AdminBiblioteca` | `BUT` |
| Jaime | `AR-Koha-Catalogacion` | `BUL`, `CIA` |

El alcance debe tener `validFrom`/`validTo` en la activación del assignment cuando sea temporal. Si cada biblioteca requiere fechas distintas, se usan assignments separados. La fuente RR. HH. puede asignar la función base; excepciones transversales, como Jaime en CIA o Elvira como TI, se asignan manualmente con auditoría y fecha de revisión.

La convergencia es determinista:

```text
effectivePermissions = unión canónica de permisos de assignments activos
effectiveLibraries   = unión canónica, única y ordenada de kohaLibraries activos
```

Todos los roles reutilizan la misma construction `resource=e10a539a…, kind=account, intent=default`, por lo que MidPoint fusiona policy sobre un solo shadow. Retirar un assignment elimina únicamente sus contribuciones; un recompute repetido debe ser idempotente y no alterar las contribuciones de otros assignments.

## 5. Materialización en Koha

### 5.1 Permisos funcionales

El resource `upeu/resources/koha-upeu.xml` debe dejar de devolver `flags=1` para Dirección y Soporte/TI.

Resultado objetivo:

- Juan: `flags=1`, sin permisos granulares adicionales.
- Resto del personal: permiso base `catalogue` para entrar al staff y `user_permissions` granulares según función.
- Ningún responsable local recibe permisos de administración global, plugins, configuración del sistema, SQL o asignación de superlibrarian salvo aprobación explícita.

La lista final de `user_permissions` se validará contra las tablas `userflags` y `permissions` de Koha 26.05 antes del PATCH del resource; no se inferirán bits numéricos.

### 5.2 Alcance por biblioteca

Koha core ofrece restricciones por biblioteca y grupos, pero no representa de forma nativa una matriz individual multivaluada como “Jaime puede catalogar en BUL y CIA; otro catalogador BUL solo puede BUL”. Por eso se selecciona este diseño:

1. MidPoint gobierna `kohaLibraries` en el assignment.
2. El conector materializa la unión vigente en un atributo extendido gobernado y no editable desde Koha: un valor por biblioteca, por ejemplo `{"type":"STAFF_SCOPE","value":"BUL"}`.
3. Un componente de autorización Koha UPeU valida el alcance antes de operaciones sobre patrones, ejemplares, circulación y administración local.
4. El control es server-side; ocultar botones o filtrar JavaScript no constituye seguridad.

Antes del despliegue se debe ejecutar un PoC sobre Koha 26.05 para confirmar hooks suficientes. El PoC debe construir esta matriz para cada operación protegida:

```text
operación → CGI/REST/job/batch → objeto → biblioteca objetivo
          → punto de enforcement → prueba positiva → prueba negativa directa
```

La prueba negativa debe invocar directamente la URL o API; ocultar navegación no cuenta. Toda ruta sin biblioteca objetivo inequívoca se deniega por defecto. Si los hooks de plugins no cubren todos los endpoints CGI/REST/jobs relevantes, se requiere un parche core mínimo, versionado y probado sobre el paquete Koha UPeU. No se desplegará un control parcial presentado como restricción fuerte.

`STAFF_SCOPE` es autoritativo desde MidPoint, no aparece en formularios editables y contiene solo la unión de assignments vigentes. La actualización de permisos y scope debe ser atómica; ausencia, formato inválido o estado intermedio niegan operaciones administrativas.

### 5.3 Regla de autorización

```text
permitir = superlibrarian
        OR (operación ∈ permisos_funcionales
            AND biblioteca_objetivo ∈ kohaLibraries
            AND assignment vigente)
```

La biblioteca objetivo se determina normativamente así:

| Operación | Condición de alcance |
|---|---|
| Seleccionar/cambiar biblioteca de sesión | La biblioteca seleccionada debe pertenecer a `effectiveLibraries`. |
| Préstamo/devolución/renovación presencial | Biblioteca de sesión dentro del scope; el ejemplar puede provenir de otra sede según reglas de circulación. |
| Transferir ejemplar | Biblioteca origen y destino dentro del scope, salvo tarea técnica central explícita. |
| Crear/modificar ejemplar | `homebranch` y `holdingbranch` resultantes dentro del scope. |
| Editar registro bibliográfico global | Permitido por función; no autoriza holdings fuera del scope. |
| Buscar/ver patrón | `branchcode` del patrón dentro del scope; los datos mínimos necesarios para circulación cruzada se exponen mediante una vista operacional limitada. |
| Crear/modificar patrón | `branchcode` resultante dentro del scope. |
| Reservas | Excluidas del primer rollout hasta aprobar §7. |
| Importación/batch | Denegado en el primer rollout; requiere diseño específico de partición por branch. |
| Administración sin objeto de branch | Denegada salvo superadmin. |

La biblioteca de sesión no es confiable por sí sola: el selector y cualquier endpoint de cambio de branch también quedan bajo enforcement.

## 6. Movilidad de usuarios/patrones

Un viaje temporal no produce ningún cambio en MidPoint ni en el `branchcode` del patrón.

Flujo:

1. La persona se autentica por SSO o presenta su identificador/carné en el campus visitado.
2. Koha usa el mismo `borrowernumber`; no crea un segundo patrón.
3. Las reglas se resuelven actualmente por la biblioteca de origen del ejemplar (`CircControl=ItemHomeLibrary`).
4. El préstamo registra la biblioteca que realiza la operación.
5. La devolución puede hacerse en cualquier sede (`AllowReturnToBranch=anywhere`).
6. Si corresponde, Koha genera transferencia a la biblioteca de origen (`AutomaticItemReturn=1`).

CIA conserva su política material: todos sus ejemplares tienen `notforloan=1`. La movilidad del usuario no anula esta restricción y una prueba negativa de préstamo debe confirmar el comportamiento.

## 7. Reservas y transporte

En esta fase no se cambia `ReservesControlBranch=PatronLibrary`. Se levantará una matriz separada para decidir:

- sedes permitidas de recogida;
- colecciones que pueden viajar;
- tiempos de traslado;
- límites locales de reservas;
- excepciones para CIA y materiales `notforloan`.

Hasta aprobar esa matriz, la circulación presencial multicampus puede funcionar sin modificar la política global de reservas.

## 8. Seguridad y auditoría

- Asignaciones privilegiadas manuales deben registrar solicitante, aprobador, motivo y vigencia.
- `AR-Koha-Superadmin` tendrá una policy rule preventiva que rechace su asignación a cualquier foco distinto del OID de Juan; además se auditará el conteo humano efectivo en Koha.
- La cuenta break-glass local `SUPERADMIN/superadmin` permanece fuera de MidPoint, protegida y sin SSO interactivo normal.
- `svc_midpoint` no puede iniciar sesión por SSO ni conservar `flags=1`; su baseline objetivo es `list_borrowers + edit_borrowers`, sujeto al PoC del conector.
- Toda denegación por scope debe registrar usuario, función, biblioteca, objeto y operación.
- Una ausencia o error de `STAFF_SCOPE` niega operaciones administrativas; no cae a acceso global.

## 9. Despliegue por fases

### Fase A — inventario y reducción de privilegios

1. Enumerar todos los `flags=1` y resolver su foco/rol MidPoint.
2. Confirmar que Juan es el único superadmin humano objetivo.
3. Reducir `svc_midpoint` en DEV y probar search/create/update/extended-attributes/reconcile; promover el mínimo privilegio a PROD antes del piloto humano.
4. Construir la matriz persona × función × bibliotecas y aprobarla.
5. Preparar deltas y rollback sin aplicarlos todavía.

### Fase B — PoC de alcance estricto

1. Implementar en entorno de prueba `kohaLibraries`, `STAFF_SCOPE` y enforcement fail-closed.
2. Completar la matriz CGI/REST/job/batch y sus pruebas directas.
3. No modificar todavía los humanos de producción.

### Fase C — función y scope como unidad coordinada

1. Cambiar Dirección/Soporte de superlibrarian a permisos granulares y activar el scope en la misma ventana por piloto.
2. Mantener una sola construction `account/default`.
3. Pilotos: un usuario BUL, Jaime BUL+CIA, un usuario BUJ y un intento denegado fuera de scope.
4. Recomputar exclusivamente los pilotos aprobados.
5. Verificar SSO, permisos positivos y negativos antes de ampliar la cohorte.
6. Ningún usuario scoped pasa a producción con permisos funcionales globales mientras no exista enforcement efectivo.

### Fase D — movilidad y reservas

1. Conservar las preferencias de movilidad ya operativas.
2. Probar préstamo BUL→usuario BUJ y BUJ→usuario BUL.
3. Probar devolución cruzada y transferencia de retorno.
4. Aprobar después la matriz de reservas/recogida.

## 10. Validaciones obligatorias

- Solo Juan tiene `flags=1` entre cuentas humanas SSO; la única cuenta adicional con `flags=1` es el break-glass local. `svc_midpoint` usa permisos API granulares.
- Elvira, David y Walter administran únicamente su scope y no acceden a parámetros globales.
- Jaime cataloga holdings de BUL y CIA, pero recibe denegación en BUJ/BUT.
- Otro catalogador BUL no obtiene CIA por compartir función.
- Cada persona mantiene un solo patrón y un solo shadow Koha consolidado.
- Un usuario de cualquier campus puede recibir un préstamo presencial en otra sede si la categoría y el material lo permiten.
- Una devolución cruzada genera el comportamiento de transferencia esperado.
- Los 3.564 ejemplares CIA permanecen `notforloan=1` y una prueba negativa confirma que no pueden prestarse.
- SSO staff y OPAC continúan funcionando.
- Recompute individual no eleva ni revierte permisos.

## 11. Rollback

- La reducción de `flags=1` es permanente: el baseline seguro es el XML de privilegios reducidos, nunca el XML inseguro anterior.
- Código de enforcement, mappings y assignments se despliegan/revierten como una unidad coordinada.
- Retirar assignments manuales por su container ID; no eliminar focos ni shadows.
- Ante fallo del enforcement, activar modo degradado **fail-closed** para cuentas scoped; recuperación solo mediante Juan o break-glass.
- Desactivar código de scope no puede dejar permisos granulares operando globalmente ni devolver `flags=1`.
- Restaurar preferencias Koha solo desde su snapshot previo; este diseño inicialmente las conserva.
- No usar SQL directo para corregir permisos durante rollback.

## 12. Fuera de alcance

- Cambiar campus, afiliación, cargo, lifecycle o archetype por una visita temporal.
- Duplicar patrones por campus.
- Convertir CIA en biblioteca de origen de usuarios.
- Cambiar masivamente las reglas de reservas sin matriz aprobada.
- Tocar el Koha viejo `.135`.
