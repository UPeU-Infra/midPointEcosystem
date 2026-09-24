/agent midpoint-expert

# Objetivo
Que MidPoint gobierne también los PERMISOS de las personas en los sistemas LAMB, no solo su identidad.
Hoy MidPoint sabe quién es cada persona y su situación (alumno, egresado, trabajador, cesado), pero no
sabe qué roles tiene en LAMB. Esos roles se asignan directamente en Oracle, fuera de gobierno.

Antes de diseñar, consulta las skills `iga-canonical-standards` y `midpoint-best-practices`.
Regla de la casa: modelo canónico primero; los datos de UPeU se adaptan al modelo, nunca al revés.
Lee también docs/runbooks/PROTOCOLO-PRE-EJECUCION-PROD.md.

# Punto de partida medido el 24-09-2026 (vuelve a medirlo antes de usarlo en una cifra de entrega)
1. MidPoint PROD (192.168.15.166) tiene 8 recursos Oracle (Trabajadores v3, Estudiantes v3, Egresados v3,
   Ausencias v1, Grados v1, RENIEC Cache v1, Org, Posiciones). Todos leen Oracle PROD 192.168.13.9:1521/UPEU
   con ScriptedSQL + Groovy, usuario JUANSANCHEZ. Fuente en el repo: upeu/resources/oracle-lamb/*.xml.
2. Leen 31 objetos de DAVID, ELISEO, ENOC y MOISES. Todos existen, están VALID y son legibles. Usan las
   tablas vigentes (MOISES.PERSONA, no las copias ELISEO/GENESIS/MOISES1/MOISES2).
3. NINGÚN recurso lee el modelo de permisos de LAMB. Las apps lo usan: por ejemplo, lamb-wellness arma el
   menú de cada usuario con LAMB_USUARIO_ROL → LAMB_ROL_MODULO → LAMB_MODULO (UserInfoData.php:147-153).
4. JUANSANCHEZ ya puede leer esas tablas (tiene SELECT ANY TABLE por el rol DEVELOP_READ). No hace falta
   pedir permisos para empezar.
5. Los partial_error de las recon diarias son de otra cosa: datos duplicados o incoherentes en Oracle,
   conflictos de correlación y errores de Koha. Están fuera de alcance aquí; no los confundas con este
   trabajo. Si necesitas contarlos por fecha, usa `ma_audit_event` (eventstage='EXECUTION'), NUNCA
   `m_operation_execution`: esa tabla solo guarda los últimos registros por objeto y fabrica "saltos".
6. El MidPoint del lab (192.168.15.150:8081) solo tiene LDAP. El DEV 192.168.15.230 ya no existe (la
   máquina se liberó el 25-ago).

# ⚠️ La clave de correlación ID_PERSONA NO es fiable por sí sola (medido el 23 y 24-09)
- ELISEO.APS_EMPLEADO: 1.325 contratos con más de un ID_PERSONA (29 COD_APS activos). Por eso la ficha
  201810596 mezcló los datos de dos personas (memoria caso-201810596-identidad-cruzada).
- Oracle tiene personas duplicadas (544 fichas en la medición del 4-ago).
- Hay fichas MidPoint cuyo lambIdPersona no coincide con la fila de Oracle enlazada (p. ej. 201410687).
Un rol enlazado solo por ID_PERSONA puede quedar huérfano o asignarse a quien no es. La FASE 0 lo tiene
que medir antes de diseñar nada.

# El modelo de permisos LAMB (Oracle PROD, esquema ELISEO)
- LAMB_USUARIO_ROL (ID_ROL, ID_PERSONA, ID_ENTIDAD, ID_USER, FECHA_REGISTRO): 443.059 asignaciones,
  118.914 personas, 668 roles, 54 entidades. El rol va acotado por ENTIDAD.
- LAMB_ROL (ID_ROL, NOMBRE, ESTADO, ID_MODULO, CODIGO, ES_RESTRINGIDO): 731 roles.
- LAMB_ROL_MODULO (ID_ROL, ID_MODULO, ESTADO): 20.989.
- LAMB_MODULO (ID_MODULO, ID_PADRE, NOMBRE, CODIGO, URL, ESTADO, TIPO_MODULO, ES_RESTRINGIDO, ...): 2.481, en árbol.
- LAMB_ROL_MODULO_ACCION (ID_ROL, ID_MODULO, ID_ACCION, FECHA): 6.565.
- LAMB_ACCION (ID_ACCION, ID_MODULO, NOMBRE, METODO, CLAVE, VALOR, ESTADO): 1.229. La CLAVE es el
  permiso fino (por ejemplo PUEDE_EDITAR_NOTAS_ACAD, CALIFICAR_ACCESO_MASTER), sensible tras el caso de
  cambios de notas de julio.

# Qué te pido, por fases. No avances de fase sin mi aprobación.
FASE 0 — Medición (solo lectura, sin tocar MidPoint):
  a) Cobertura de la correlación. De las personas con al menos un rol LAMB activo:
     - cuántas corresponden a exactamente 1 ficha MidPoint por lambIdPersona;
     - cuántas a NINGUNA ficha (permisos que hoy nadie gobierna); desglósalas por qué son en Oracle, si se
       puede saber (alumno, trabajador, egresado, postulante, externo...);
     - cuántas a MÁS de una ficha, o cuyo ID_PERSONA es un duplicado conocido de otra persona.
  b) Bajas con permisos. Personas con rol LAMB activo que NO tienen vínculo vigente. Una baja consumada
     pierde el archetype (le llega por un assignment), así que "sin archetype activo" se queda corto.
     Cruza también por AUSENCIA en las vistas fuente (Trabajadores, Estudiantes, Egresados) además del
     estado en MidPoint. Si usas PLLA_CESE, recuerda que no tiene ID_PERSONA.
  c) Permisos sensibles. Personas con alguna ACCION sensible (CLAVE tipo PUEDE_EDITAR_NOTAS_*,
     CALIFICAR_*, ...) o con un rol ES_RESTRINGIDO que NO son trabajadores activos. Da la cifra y una
     muestra de 10, identificadas por código de usuario con el DNI y el nombre enmascarados.
  d) Roles restringidos: cuántos son y cuántas personas los tienen.
  Cada cifra con su consulta, para que se pueda repetir.
FASE 1 — Diseño conforme a estándares:
  - Cómo representar esto en MidPoint: roles de aplicación / entitlements (LAMB_ROL) y su asociación con
    la cuenta. Para ID_ENTIDAD, evalúa expresamente el assignment con orgRef (rol acotado por
    organización), que MidPoint trae de serie, frente a un rol por entidad (668 × 54) o un parámetro.
    Justifica con midpoint-best-practices e iga-canonical-standards (RBAC NIST, ISO 27001 A.5.15-A.5.18).
  - Qué hacer con las personas del punto 0.a sin ficha y con las correlaciones dudosas: no las inventes.
  - LAMB_ACCION queda fuera del RBAC de MidPoint en esta fase: se mide, no se modela como roles.
  - Qué va a canonical/ (reutilizable para cualquier universidad) y qué a upeu/.
FASE 2 — Laboratorio: recurso de solo lectura en el lab (192.168.15.150). Comprueba primero si el lab
  llega a Oracle 13.9. Si no llega, propón la alternativa, pero NO copies las 443.059 asignaciones con
  ID_PERSONA reales a un entorno de pruebas: usa un subconjunto o datos seudonimizados (Ley 29733).
  Importa y muestra el resultado. Nada de outbound.
FASE 3 — Producción: solo con un Cambio registrado en ITService antes de ejecutar.
  - Antes de importar, estima el crecimiento de shadows y de auditoría. El disco de PROD está al 72% de
    72 GB, no le queda espacio libre en el volumen y la auditoría ya crece ~11 GB/mes (runbook
    docs/runbooks/backup-midpoint-s3).
  - Primero importar para ver (sin outbound, sin quitar roles). La desasignación automática y las
    campañas de certificación quedan para una decisión posterior y aparte.

# Restricciones
- NUNCA escribir en Oracle. El recurso es de solo lectura (sin create, update ni delete de cuentas).
- No tocar MidPoint PROD sin un Cambio aprobado.
- Autenticación: 3 intentos de login fallidos bloquean la cuenta 15 minutos, y el SSH a .166 da a veces
  "Permission denied" de forma intermitente. Ante un fallo, UN solo reintento; si vuelve a fallar, para.
- JUANSANCHEZ es la cuenta personal de Alberto. Sirve para medir, pero en el diseño final propón una
  cuenta de servicio MIDPOINT_RO con SELECT solo sobre los 31 objetos actuales más estas 6 tablas.
- Datos personales: en tus respuestas, enmascara DNI y nombres. Las evidencias van a una carpeta del
  scratchpad con permisos 700, nunca al repo.
- Separa en tus respuestas lo [OBSERVADO] de lo [HIPÓTESIS].

# Entregable de esta sesión
Solo la FASE 0 (cifras con su consulta) y el borrador de diseño de la FASE 1. Después paramos y decido.
