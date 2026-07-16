# Instrucciones para Rudy — Tickets Oracle LAMB

**Owner:** Alberto Sánchez (DTI/Infra)
**Destinatario:** Rudy (DBA Oracle UPeU)
**Contexto:** Proyecto MidPoint IGA — provisioning de identidades desde Oracle LAMB.
**Política absoluta:** Oracle LAMB es **solo lectura**. Ningún INSERT/UPDATE/DELETE/DDL desde MidPoint.

---

## 🟢 ESTADO (revisado 2026-07-16): NO hay nada pendiente que pedirle a Rudy

Los 3 tickets de abajo tenían condiciones de disparo **vencidas o ya resueltas por otra vía**, lo que hacía parecer que había pendientes con Rudy cuando no los hay. Estado real, verificado en vivo:

| Ticket | Estado anterior (engañoso) | Estado REAL |
|---|---|---|
| **RU-001** cuenta de servicio | "🔵 no solicitar todavía — antes de Fase 10" | **Vencido como condición** (Fase 10 cerró el 2026-06-06), pero **SIN urgencia**: se verificó que `JUANSANCHEZ` **no expira nunca** (`user_users`: `EXPIRY_DATE = NUNCA`, `ACCOUNT_STATUS = OPEN`). Deuda de higiene, sin fecha. Ver §RU-001. |
| **RU-002** vista lenta | "🟡 ACTIVO" | **CERRADO.** Ningún resource la usa (grep en `upeu/` + `canonical/` = 0 hits) → se resolvió por la alternativa que el propio ticket contemplaba. La vista **sigue lenta** (medido 2026-07-16: 5,26 s vs 0,01 s de una sana) pero es irrelevante para el IGA. |
| **RU-003** horarios/entorno | "diferido junto con RU-001" | **Mayormente respondido por la operación.** Ver §RU-003. |

> **Regla para no repetir esto:** un ticket cuya condición de disparo es un hito ("antes de Fase X") **debe revisarse cuando ese hito se cierra**. Aquí la Fase 10 cerró el 2026-06-06 y nadie releyó el runbook durante ~40 días. Si se difiere algo, dejar el disparo por **fecha**, no por hito.

---

## Decisión 2026-05-11 — Approach pragmático

**Decisión de Alberto:** Para validar el flujo end-to-end primero, MidPoint PROD usará **temporalmente** la cuenta personal `JUANSANCHEZ` (con rol `DEVELOP_READ`) que ya tiene SELECT sobre los 33 objetos verificados. Una vez validado que el modelo IGA funciona y sabemos exactamente qué tablas se consumen en operación real, pediremos a Rudy crear `MIDPOINT_IGA_RO` con permisos mínimos.

### Plan

| Fase | Cuenta Oracle | Para qué |
|---|---|---|
| **Fases 5-9 (ahora)** | `JUANSANCHEZ` (personal) | Configurar Resources MidPoint, validar inbound mappings, ajustar object templates, probar piloto |
| **Antes de Fase 10 (despliegue real)** | `MIDPOINT_IGA_RO` (dedicada) | Rotación a cuenta de servicio con permisos mínimos verificados en práctica |

### Ventaja del enfoque

- **No bloqueamos el avance** esperando a Rudy
- **Pedimos solo lo necesario** (sabremos qué tablas se usan realmente vs cuáles eran solo "por si acaso")
- **Menos esfuerzo para Rudy** (un solo ticket bien definido al final)
- **ISO 27001 A.8.2** se cumple igual antes de producción real

### Riesgo aceptado

- Credenciales personales en config de MidPoint PROD durante Fases 5-9 (período controlado, solo accede MidPoint, no se publican)
- Audit trail muestra `JUANSANCHEZ` como autor de los inbound — aceptable para pruebas

---

## RU-001 — Crear cuenta de servicio `MIDPOINT_IGA_RO` 🟡 DEUDA DE HIGIENE (sin urgencia)

**Estado (revisado 2026-07-16):** la condición original ("antes de Fase 10") **está vencida** — la Fase 10 cerró el **2026-06-06** y PROD sigue usando `JUANSANCHEZ` en los 7 resources Oracle (`egresados`, `estudiantes`, `grados`, `org`, `posiciones`, `reniec-cache`, `trabajadores`). **Pero NO es urgente**, y conviene decir por qué en vez de dejarlo como alarma perpetua:

- **No hay riesgo con fecha.** Verificado en vivo (`SELECT ... FROM user_users`): `JUANSANCHEZ` → `ACCOUNT_STATUS = OPEN`, **`EXPIRY_DATE = NUNCA`**. La hipótesis de "si el password expira, el IGA se cae" **no aplica**.
- **Lo que sí queda, menor:** (a) el audit trail de ~54k identidades queda firmado como `JUANSANCHEZ`; (b) si Alberto deja el rol/puesto, su cuenta se desactiva y PROD muere; (c) `DEVELOP_READ` es más amplio que el mínimo necesario; (d) ISO 27001 A.8.2 (cumplimiento, no riesgo operativo).
- **En contra de hacerlo ahora:** funciona hace meses, y rotar credenciales en 7 resources tiene su propio riesgo de rotura.

**Cuándo hacerlo:** cuando haya otro motivo para escribirle a Rudy (agrupar), o si cambia el contexto (rotación de rol de Alberto, auditoría, incidente de seguridad). **No abrir un ticket solo por esto.**

**Ventaja ya cobrada:** el diferimiento tenía un objetivo — *"pedir solo lo necesario, sabiendo qué tablas se usan de verdad"*. **Ya se cumplió**: tras meses de operación real se sabe exactamente qué objetos consume MidPoint. Si se ejecuta, **revisar la lista de 34 objetos de abajo contra el uso real** antes de enviarla (probablemente sobran).

**Para:** Fase 10 del [roadmap](./roadmap-iga-2026.md) (despliegue PROD definitivo) — *hito ya cerrado el 2026-06-06*.
**Sistema:** Oracle LAMB UPeU (`192.168.13.9:1521/UPEU`).

### Acción solicitada

**1. Crear usuario:**
```sql
CREATE USER MIDPOINT_IGA_RO IDENTIFIED BY "<password-fuerte-32-caracteres>";
GRANT CREATE SESSION TO MIDPOINT_IGA_RO;
GRANT CONNECT TO MIDPOINT_IGA_RO;
ALTER USER MIDPOINT_IGA_RO PASSWORD EXPIRE NEVER;
ALTER USER MIDPOINT_IGA_RO PROFILE DEFAULT;
ALTER USER MIDPOINT_IGA_RO ACCOUNT UNLOCK;
```

**2. Otorgar SELECT sobre los 34 objetos** (lista completa abajo):

```sql
-- MDM personas (MOISES)
GRANT SELECT ON MOISES.PERSONA            TO MIDPOINT_IGA_RO;
GRANT SELECT ON MOISES.PERSONA_NATURAL    TO MIDPOINT_IGA_RO;
GRANT SELECT ON MOISES.TRABAJADOR         TO MIDPOINT_IGA_RO;
GRANT SELECT ON MOISES.TRABAJADOR_PUESTO  TO MIDPOINT_IGA_RO;
GRANT SELECT ON MOISES.CARRERA_PROFESIONAL TO MIDPOINT_IGA_RO;

-- Vistas oro estudiantes / docentes (DAVID)
GRANT SELECT ON DAVID.VW_PERSONA_ALUMNO        TO MIDPOINT_IGA_RO;
GRANT SELECT ON DAVID.VW_PERSONA_EGRESADO      TO MIDPOINT_IGA_RO;
GRANT SELECT ON DAVID.VW_PERSONA_NATURAL       TO MIDPOINT_IGA_RO;
GRANT SELECT ON DAVID.VW_PERSONA_COMUN         TO MIDPOINT_IGA_RO;
GRANT SELECT ON DAVID.VW_PERSONA_DOCENTE       TO MIDPOINT_IGA_RO;
GRANT SELECT ON DAVID.VW_PERSONA_CONTRATO      TO MIDPOINT_IGA_RO;
GRANT SELECT ON DAVID.VW_PERSONA_GRADO         TO MIDPOINT_IGA_RO;
GRANT SELECT ON DAVID.VW_FICHA_MATRICULA       TO MIDPOINT_IGA_RO;
GRANT SELECT ON DAVID.VW_HORARIO_DOCENTE       TO MIDPOINT_IGA_RO;
GRANT SELECT ON DAVID.VW_ALUMNO_PLAN_PROGRAMA  TO MIDPOINT_IGA_RO;
GRANT SELECT ON DAVID.VW_ALUMNO_SEMESTRE       TO MIDPOINT_IGA_RO;
GRANT SELECT ON DAVID.ACAD_PROGRAMA_ESTUDIO    TO MIDPOINT_IGA_RO;
GRANT SELECT ON DAVID.ACAD_MATRICULA           TO MIDPOINT_IGA_RO;
-- GRANT SELECT ON DAVID.VW_DATOS_IDENTIDAD_USUARIO TO MIDPOINT_IGA_RO; -- BLOQUEADO por RU-002

-- Empleados / nómina / org (ELISEO)
GRANT SELECT ON ELISEO.VW_APS_EMPLEADO         TO MIDPOINT_IGA_RO;
GRANT SELECT ON ELISEO.APS_EMPLEADO            TO MIDPOINT_IGA_RO;
GRANT SELECT ON ELISEO.APS_CARGO               TO MIDPOINT_IGA_RO;
GRANT SELECT ON ELISEO.ORG_SEDE                TO MIDPOINT_IGA_RO;
GRANT SELECT ON ELISEO.ORG_DEPENDENCIA         TO MIDPOINT_IGA_RO;
GRANT SELECT ON ELISEO.ORG_NIVEL_GESTION       TO MIDPOINT_IGA_RO;
GRANT SELECT ON ELISEO.ORG_ESCUELA_PROFESIONAL TO MIDPOINT_IGA_RO;
GRANT SELECT ON ELISEO.ORG_AREA                TO MIDPOINT_IGA_RO;
GRANT SELECT ON ELISEO.ORG_SEDE_AREA           TO MIDPOINT_IGA_RO;
GRANT SELECT ON ELISEO.VW_SEDE_AREA            TO MIDPOINT_IGA_RO;

-- Catálogo docente (ENOC)
GRANT SELECT ON ENOC.CAT_DOCENTE         TO MIDPOINT_IGA_RO;
GRANT SELECT ON ENOC.CAT_DOCENTE_ESTADO  TO MIDPOINT_IGA_RO;

-- Roles legacy (para role mining en Fase 7)
GRANT SELECT ON ELISEO.LAMB_ROL                TO MIDPOINT_IGA_RO;
GRANT SELECT ON ELISEO.LAMB_USUARIOS           TO MIDPOINT_IGA_RO;
GRANT SELECT ON ELISEO.LAMB_ROL_ENTIDAD_DEPTO  TO MIDPOINT_IGA_RO;
```

**Total: 33 objetos** (TABLES + VIEWS, ningún privilegio adicional).

**NO otorgar:**
- ❌ Ningún `INSERT`, `UPDATE`, `DELETE`, `EXECUTE`, `ALTER`.
- ❌ Ningún rol del sistema (`DBA`, `RESOURCE`, `IMP_FULL_DATABASE`, etc.).
- ❌ `CREATE TABLE` o similar — la cuenta NO necesita crear nada.
- ❌ `DEVELOP_READ` (es para humanos que exploran, no para servicios).

**3. Restricción de acceso por IP:**

Configurar en `sqlnet.ora` del servidor LAMB:
```
tcp.invited_nodes = (192.168.15.166)   # MidPoint PROD
```
o equivalente vía ACLs Oracle Network. Solo MidPoint PROD debe poder conectarse con esta cuenta.

**4. Política de password:**
- 32 caracteres aleatorios
- Sin expiración (cuenta de servicio)
- Cambio cada 12 meses por política institucional

### Output esperado

Compartir vía canal seguro (1Password / Bitwarden / Keeper) o sobre cifrado:
- `MIDPOINT_IGA_RO_USER=MIDPOINT_IGA_RO`
- `MIDPOINT_IGA_RO_PASS=<password>`
- `MIDPOINT_IGA_RO_DSN=192.168.13.9:1521/UPEU`

Yo lo guardaré en `~/.secrets/oracle-lamb-midpoint.env` (permisos 600).

### Justificación

- **ISO 27001 A.8.2** — Privileged Access Rights: cuentas de servicio dedicadas para cada sistema técnico.
- **ISO 27001 A.5.16** — Identity Management: separación entre identidad humana (Juan) e identidad de servicio (MidPoint).
- **Audit trail diferenciable:** queries de MidPoint son trazables sin mezclar con mi exploración manual.

---

## RU-002 — Diagnóstico de la vista `DAVID.VW_DATOS_IDENTIDAD_USUARIO` ✅ CERRADO (no enviar)

**Estado (verificado 2026-07-16): CERRADO — no hace falta pedir nada.**
- **Ningún resource del IGA la usa.** `grep -rl VW_DATOS_IDENTIDAD_USUARIO upeu/ canonical/` → **0 hits**. Se resolvió por la alternativa que el propio ticket ya contemplaba (reconstruir los joins desde `VW_PERSONA_NATURAL` + `VW_PERSONA_COMUN`), que es lo que hacen hoy los searchScripts.
- **El síntoma sigue vivo pero es irrelevante para nosotros.** Medido hoy: `SELECT 1 ... WHERE 1=0` sobre esa vista → **5,26 s**; contra `MOISES.PERSONA_NATURAL` (control) → **0,01 s**. Sigue lenta, pero ya no la consumimos.
- Si algún día se quisiera usar como "vista oro" de identidad consolidada, este ticket se reabre **con esta medición como evidencia**.

<details>
<summary>Contenido original del ticket (histórico, no enviar)</summary>

**Para:** Fase 5 (es la vista oro de identidad consolidada — la más importante).
**Sistema:** Oracle LAMB UPeU.
**Mensaje WhatsApp listo:**

> Hola Rudy, la vista `DAVID.VW_DATOS_IDENTIDAD_USUARIO` me da timeout cuando hago SELECT (incluso con `WHERE 1=0`). ¿Puedes revisar si está rota o muy pesada? Las otras `VW_PERSONA_*` responden bien. Gracias!

### Síntoma

```sql
SELECT 1 FROM DAVID.VW_DATOS_IDENTIDAD_USUARIO WHERE 1=0;
```
**timeout > 5 segundos.** Otras vistas similares (`VW_PERSONA_ALUMNO`, `VW_PERSONA_DOCENTE`, etc.) responden en < 1s.

### Hipótesis

- La vista tiene un JOIN muy pesado sin índices
- La vista tiene un subquery cíclico o cartesiano no detectado
- La vista referencia objetos en otros schemas que demoran en resolver

### Acción solicitada

1. Revisar la definición de la vista:
```sql
SELECT text FROM all_views WHERE owner='DAVID' AND view_name='VW_DATOS_IDENTIDAD_USUARIO';
```
2. Compartir el plan de ejecución:
```sql
EXPLAIN PLAN FOR SELECT * FROM DAVID.VW_DATOS_IDENTIDAD_USUARIO WHERE rownum < 2;
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);
```
3. Si la vista es lenta por diseño, evaluar:
   - Crear índices faltantes (si los joins lo permiten)
   - Crear una **vista materializada** refreshable (`REFRESH ON DEMAND` o `REFRESH FAST`)
   - Documentar en alternativa los joins que reemplazan a la vista

### Por qué importa

Esta vista parece ser la **identidad consolidada** (datos centralizados). Es candidata natural para el inbound mapping principal de MidPoint. Si queda inaccesible:
- Tendremos que reconstruir los joins manualmente desde `VW_PERSONA_NATURAL` + `VW_PERSONA_COMUN` + tablas de identificadores. Funciona pero duplica lógica que ya existe en la vista.

</details>

---

## RU-003 — Confirmación de horario de ejecución de queries de MidPoint 🟢 RESPONDIDO por la operación

**Estado (revisado 2026-07-16):** las 4 preguntas ya las contestó la práctica tras meses de operación. **No hace falta preguntarlas.**

| Pregunta original | Lo que sabemos hoy |
|---|---|
| ¿Hay horario protegido donde no pegarle? | Los crons de reconcile corren a las **02:00 UTC** desde mayo-2026 sin ninguna queja de LAMB. Si hubiera ventana protegida, ya habría saltado. |
| ¿Hay índices para `WHERE fecha_modificacion > sysdate-1`? | Los 4 resources Oracle operan con volúmenes reales (30.917 objetos en la corrida GAP-2) dentro de tiempos aceptables. |
| **¿Es Oracle 11g/12c/19c?** | **Oracle 11.2.0.4** — confirmado. (Consecuencia práctica ya conocida: **no soporta `FETCH FIRST n ROWS ONLY`** → usar `rownum`.) |
| ¿Límite de sesiones concurrentes? | Nunca se topó. Los recomputes usan `workerThreads=1` por límites de RAM de MidPoint, no de Oracle. |

**Único residuo con valor:** si algún día se crea `MIDPOINT_IGA_RO` (RU-001), preguntar entonces si a esa cuenta le aplica algún límite de sesiones — pero va **dentro** de ese ticket, no aparte.

<details>
<summary>Contenido original del ticket (histórico)</summary>

**Para:** Fase 5 + Fase 7 (operación continua).
**Sistema:** Oracle LAMB.

### Contexto

MidPoint hará:
- **Imports masivos** (full sync) — semanal, fuera de horario operativo
- **Live sync polls** — cada 15-30 min, todo el día (livianos, solo deltas)
- **Reconciliation** — diaria, madrugada

### Preguntas para Rudy

1. ¿Hay horario protegido en LAMB donde NO debemos pegarle? (cierre nómina, reportes contables, etc.)
2. ¿Hay índices que MidPoint pueda aprovechar para filtros `WHERE fecha_modificacion > sysdate-1`? Si no, ¿podemos agregar uno?
3. ¿Es Oracle 11g/12c/19c? — afecta features SQL disponibles
4. ¿Hay límite de sesiones concurrentes por usuario que aplique a `MIDPOINT_IGA_RO`?

</details>

---

## Información que Rudy quizás necesite

**Cliente que se conectará:**
- Software: MidPoint 4.10.2 (Java 21)
- Driver: Oracle JDBC `ojdbc11.jar` (compatible Oracle 11g+)
- Host cliente: `192.168.15.166` (MidPoint PROD, Ubuntu 24.04)
- Conexión: JDBC URL `jdbc:oracle:thin:@//192.168.13.9:1521/UPEU`
- Frecuencia esperada:
  - Reconciliation diaria: ~50K registros consultados (incremental)
  - Live sync cada 15 min: ~100 registros (delta)
  - Operaciones individuales: ~1-5 queries por user provisionado

**Acceso solicitado por:**
- Juan Alberto Sánchez (DTI/Infraestructura TI Campus Lima)
- Email: `juan_alberto@upeu.edu.pe`
- Para: proyecto MidPoint IGA UPeU

---

## Tareas completadas

_(2026-05-20)_

- **Conexión MidPoint → Oracle LAMB funcional**: MidPoint PROD tiene 4 resources JDBC activos contra Oracle LAMB (Trabajadores v3, Estudiantes v3, Egresados v3, Posiciones). 35.450 usuarios sincronizados. El acceso JDBC directo con cuenta `JUANSANCHEZ` (DEVELOP_READ) es operativo.
- **TCP 389 abierto**: OpenLDAP Identity Cache activo en 192.168.15.168:389, Keycloak User Federation activa con 37.491 entradas. El acceso de red MidPoint PROD → OpenLDAP y Keycloak → OpenLDAP está confirmado.

---

## Plantilla para nuevas tareas

```markdown
### RU-NNN — Título corto 🟡

**Para:** Fase X.Y del roadmap
**Sistema:** Oracle LAMB (192.168.13.9)
**Contexto:** [3-5 líneas]

**Acción solicitada:**
1. [paso 1]
2. [paso 2]

**Justificación:** [norma ISO / razón técnica]

**Output esperado:** [qué necesita Alberto de vuelta]
```
