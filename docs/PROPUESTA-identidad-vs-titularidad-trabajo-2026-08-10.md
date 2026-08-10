# Identidad de la persona vs. titularidad del trabajo — evidencia y propuesta

**Para:** David Urquizo — DTI UPeU
**De:** Ing. Juan Alberto Sánchez — DTI / Infraestructura TI
**Fecha:** 10 de agosto de 2026
**Asunto:** Cómo tratar puesto, rol, función y credencial de acceso en las plataformas institucionales (caso GLPI)

---

## 1. La preocupación planteada

> Si en la plataforma de un área se asignan tareas o procesos a una persona y esa persona cambia de área, no debería llevarse esas tareas o proyectos. Por eso convendría que el usuario se loguee con el **correo de cargo**: el correo es permanente y quien cambia es la persona.

La preocupación es correcta y el riesgo es real. La solución propuesta, sin embargo, resuelve el problema en la capa equivocada.

## 2. Respuesta en una línea

**La identidad y la credencial son siempre de la persona; el trabajo se asigna al *grupo/equipo*, no al individuo.** Así nada se va con quien rota, y no se pierde trazabilidad.

El problema "si la persona se va, se lleva las tareas" **solo se produce cuando el ticket se asigna únicamente a una persona**. La causa no es la identidad: es una práctica de asignación mal configurada. GLPI e ITIL ya resuelven esto sin tocar el login.

---

## 3. Evidencia A — ITIL 4

Fuente: *Incident Management — ITIL 4 Practice Guide*, AXELOS, 11 de enero de 2020 (documento de consulta, no redistribuible; se parafrasea).

| Sección | Qué establece | Consecuencia para nosotros |
|---|---|---|
| §3 (proceso de manejo y resolución) | Debe asegurarse la propiedad de cada incidente. La propiedad **puede transferirse** durante el manejo, pero en todo momento debe existir una persona responsable. | ITIL **no exige** un titular permanente. Exige que el trabajo nunca quede huérfano y que la transferencia sea explícita. |
| §4.1 (roles y competencias) | *"Roles are not job titles."* Una persona puede asumir varios roles y un rol puede asignarse a varias personas. | Rol ≠ puesto ≠ persona. Son tres capas distintas y deben modelarse por separado. |
| §4.1.1 (rol de incident manager) | Cuando no hay un incident manager dedicado, la responsabilidad la asume **la persona o equipo responsable del CI, servicio o producto** (resource owner / service owner / product owner). | El ancla estable de permanencia es **el servicio**, no un buzón de correo. |
| Tabla 2.2 (métricas) | "Number of reassignments" es una métrica oficial de la práctica. | Las reasignaciones son un hecho esperado del proceso: se miden, no se evitan congelando la identidad. |
| §4.2.1 (tiered vs flat) | Recomienda sustituir el escalado rígido por niveles con estructuras planas y colaboración (swarming). | El trabajo pertenece a equipos que colaboran, no a individuos en cadena. |
| §4.2.2 (dinámica de equipo) | Señala como disfunción la cultura donde se premia al "héroe" solitario que resuelve solo. | Anclar el trabajo a la persona produce exactamente esa disfunción. |

## 4. Evidencia B — GLPI

Todo verificado contra la documentación oficial y el código fuente del proyecto (agosto 2026).

| Capacidad de GLPI | Evidencia |
|---|---|
| Un ticket admite **usuario, grupo y proveedor simultáneamente** como "Assigned to" | `src/CommonITILActor.php`: `REQUESTER=1`, `ASSIGN=2`, `OBSERVER=3`, con conteos independientes `countUsers()/countGroups()/countSuppliers()` sobre el mismo tipo `ASSIGN` |
| Los grupos tienen banderas de rol: `is_assign` ("Assigned to"), **`is_task` ("Can be in charge of a task")**, `is_requester`, `is_watcher`, `is_manager`, `is_notify` | `src/Group.php` |
| Las **tareas** se asignan a un técnico, **a un grupo**, o quedan sin asignar | Doc. oficial — *Task* |
| Asignación automática: primero por el **grupo técnico del activo**; si no hay, por el **grupo técnico de la categoría** | Doc. oficial — *Business rules for tickets* / *Entities* |
| Las reglas de negocio pueden fijar automáticamente "assigned to group" | Doc. oficial — *Business rules for tickets* |
| En **Proyectos**, el equipo se compone de usuarios, **grupos**, proveedores y contactos | Doc. oficial — *Projects* |
| Al eliminar un usuario, **los tickets se conservan**; solo se retira la asociación del usuario | Doc. oficial — *Users* |
| Reasignación disponible: acción masiva **"Add an actor"** (requiere permiso UPDATE), reglas de negocio y plugin Escalade | `src/Ticket.php` (registro de la acción masiva `add_actor`) |
| **Sustitutos autorizados** para validaciones, con rango de fechas configurable | Doc. oficial — *Authorized substitutes* |

**Lectura:** GLPI ya trae, de fábrica, todos los mecanismos para que el trabajo no dependa de la persona. No hace falta modificar el esquema de identidad.

## 5. Evidencia C — Estándares de identidad y normativa

| Fuente | Qué dice | Aplicación |
|---|---|---|
| ISO/IEC 24760-1 §3.1.3 | El *identifier* distingue a la entidad y debe ser estable e independiente de atributos de negocio | El correo es atributo de contacto, no identificador |
| eduPerson 202208 | `eduPersonPrincipalName` es de valor único y **no reasignable** | Un buzón que hereda el siguiente titular del cargo viola la no-reasignación |
| ISO/IEC 27001:2022 A.5.16 y A.8.2 | Identidad única por persona; acceso privilegiado trazable | Una cuenta compartida por cargo elimina el no repudio |
| MidPoint (Semančík, *Practical Identity Management with MidPoint*) | *"The term user represents physical person"*; los roles pueden representar puestos de trabajo y responsabilidades | El cargo se modela como Role/Org, nunca como usuario |
| DS 029-2021-PCM art. 14.1 y 17 | Se autentica a una **persona natural** identificada por CUI/CUE; el correo figura como atributo de contacto, no como identificador | Referencia de buena práctica (obliga a entidades públicas) |
| DS 029-2021-PCM art. 57.2 | En la casilla electrónica de una **persona jurídica**, accede el representante legal **previa autenticación de su identidad personal**, y puede delegar en otros | Es exactamente el patrón correcto para un buzón de cargo |
| Ley 29733 art. 2.4 | Dato personal es la información que identifica o hace identificable a una persona natural | Refuerza la trazabilidad individual del tratamiento |

## 6. Qué se rompería con el login por correo de cargo

1. **Auditoría.** El historial de GLPI registra el `users_id`. Con cuenta compartida el log diría "soporte@ cerró el ticket", nunca quién. Se pierde el no repudio (ISO 27001 A.5.16 / A.8.2).
2. **Métricas ITIL inutilizables.** First-time resolution rate, carga por técnico, número de reasignaciones y el planning colapsan a un único usuario ficticio.
3. **Credenciales.** Contraseña compartida, sin MFA individual; la salida de una sola persona obliga a rotar la clave de toda el área.
4. **Gobierno de identidad.** Un cargo no tiene ciclo de vida (no ingresa ni egresa) ni correlaciona con Oracle LAMB. En el modelo canónico del IGA un cargo es `OrgType`/`RoleType`, nunca un `UserType`.

## 7. Modelo propuesto — cuatro capas separadas

| Capa | Qué es | Dónde vive | ¿Sobrevive a la rotación? |
|---|---|---|---|
| **Persona** | Identidad + credencial | MidPoint `UserType`; `name` = código institucional; login por correo nominativo / ePPN | No — se va con la persona (correcto) |
| **Puesto** | Cargo formal | `OrgType` + `assignment` con `relation=manager/owner`; catálogo de posiciones UPeU | Sí |
| **Función / equipo** | Grupo de trabajo operativo | Business role en MidPoint → **grupo GLPI** aprovisionado por el IGA | Sí |
| **Trabajo** | Tickets, tareas, proyectos | Asignados **siempre al grupo** (titular) + técnico como ejecutor opcional | Sí — permanece en el grupo |
| **Buzón de cargo** | `soporte@`, `admision@` | Buzón compartido colgado de la organización; acceso delegado a los titulares | Sí — pero **nunca es credencial de acceso** |

El buzón de cargo se conserva para lo que sirve: la comunicación externa estable. Lo que no hace es autenticar.

## 8. Reglas operativas propuestas para GLPI UPeU

1. **Invariante:** ningún ticket sin grupo asignado. El técnico individual es adicional, nunca sustituto del grupo.
2. Configurar grupo técnico por categoría y por activo → la asignación al área ocurre automáticamente.
3. Los grupos de GLPI se aprovisionan desde MidPoint (espejo de los business roles); no se crean a mano.
4. **Procedimiento de rotación de área:** MidPoint retira el business role → la persona sale del grupo; los tickets del grupo no se mueven. Paso obligatorio complementario: barrer los tickets donde figure como técnico individual y reasignarlos.
5. Configurar sustitutos autorizados durante la transición, para no bloquear validaciones pendientes.
6. Proyectos y tareas de proyecto: equipo por grupo, nunca por persona sola.
7. Indicadores de control: tickets con técnico pero sin grupo (debe tender a cero) y número de reasignaciones.

## 9. Pendiente de medición antes de implementar

No se pudo medir el estado actual: la API de GLPI DEV rechaza la conexión con `ERROR_NOT_ALLOWED_IP` (ve la IP `192.168.15.166`). Debe registrarse ese cliente API o ejecutarse desde la LAN. Con acceso corresponde medir:

- porcentaje de tickets abiertos con grupo asignado frente a los que solo tienen técnico;
- cuántos grupos tienen activas las banderas `is_assign` e `is_task`;
- cuántas categorías tienen grupo técnico definido — si son pocas, la asignación automática hoy no está operando.

Esas tres cifras determinan el tamaño real del problema y el esfuerzo de la corrección.

## 10. Fuentes

- *Incident Management — ITIL 4 Practice Guide*, AXELOS, 2020 (§3, §4.1, §4.1.1, §4.2.1, §4.2.2, Tabla 2.2).
- GLPI — [Defining actors and roles](https://help.glpi-project.org/documentation/modules/assistance/actors) · [Groups](https://help.glpi-project.org/documentation/modules/administration/groups) · [Business rules for tickets](https://help.glpi-project.org/documentation/modules/administration/rules/ticketbusinessrules) · [Task](https://help.glpi-project.org/documentation/modules/assistance/tabs/task) · [Projects](https://help.glpi-project.org/documentation/modules/tools/projects) · [Users](https://help.glpi-project.org/documentation/modules/administration/users) · [Authorized substitutes](https://glpi-user-documentation.readthedocs.io/fr/master/modules/user-settings/authorized-substitutes.html)
- Código fuente GLPI: [`src/CommonITILActor.php`](https://github.com/glpi-project/glpi/blob/main/src/CommonITILActor.php) · [`src/Group.php`](https://github.com/glpi-project/glpi/blob/main/src/Group.php) · [`src/Ticket.php`](https://github.com/glpi-project/glpi/blob/main/src/Ticket.php)
- ISO/IEC 24760-1:2019 · ISO/IEC 27001:2022 (A.5.16, A.8.2) · eduPerson 202208 (REFEDS/Internet2).
- R. Semančík et al., *Practical Identity Management with MidPoint*, v2.3, Evolveum.
- DS 029-2021-PCM, Reglamento de la Ley de Gobierno Digital (arts. 14, 17, 53, 57) · Ley 29733, Ley de Protección de Datos Personales (art. 2.4).
- Decisiones internas concordantes: `DECISION-email-governance.md` §1.2 y `DECISION-canonical-identifier.md` (repo `midPointEcosystem`).
