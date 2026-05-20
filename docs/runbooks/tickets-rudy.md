# Instrucciones para Rudy — Tickets Oracle LAMB

**Owner:** Alberto Sánchez (DTI/Infra)
**Destinatario:** Rudy (DBA Oracle UPeU)
**Contexto:** Proyecto MidPoint IGA — provisioning de identidades desde Oracle LAMB.
**Política absoluta:** Oracle LAMB es **solo lectura**. Ningún INSERT/UPDATE/DELETE/DDL desde MidPoint.

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

## RU-001 — Crear cuenta de servicio `MIDPOINT_IGA_RO` ⚪ DIFERIDO

**Estado:** 🔵 No solicitar todavía. Se ejecuta **antes de Fase 10** (despliegue real), no ahora. Durante Fases 5-9 usamos `JUANSANCHEZ`.

**Para:** Fase 10 del [roadmap](./roadmap-iga-2026.md) (despliegue PROD definitivo).
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

## RU-002 — Diagnóstico de la vista `DAVID.VW_DATOS_IDENTIDAD_USUARIO` 🟡 ACTIVO

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

---

## RU-003 — Confirmación de horario de ejecución de queries de MidPoint ⚪ DIFERIDO

**Estado:** Diferido — preguntar junto con RU-001 antes de Fase 10.

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
