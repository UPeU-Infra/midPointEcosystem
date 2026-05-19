# MidPoint 4.9.5 — Despliegue en Producción UPeU

**Slug:** `midpoint-prod-upeu`
**Author:** Claude Code
**Date:** 2026-04-15
**Branch:** preflight/midpoint-prod-upeu
**Related:** UPeU-Infra/midPointEcosystem · UPeU-Infra/connector-koha

---

## 1) Intent & Assumptions

- **Task brief:** Levantar MidPoint 4.9.5 en el servidor de producción (192.168.15.166, Ubuntu 24.04, limpio) replicando y madurando lo ya construido en el entorno de desarrollo (192.168.15.230). Incluye Docker, configuración de base de datos, migración de todos los objetos del repo `midPointEcosystem`, conector Koha, y activación gradual de recursos para identidades reales de UPeU.

- **Assumptions:**
  - El servidor de prod ya tiene acceso SSH configurado (usuario `juansanchez`, password en `~/.secrets/midpoint-upeu.env`)
  - La BD Lamb Academic de producción está accesible desde el servidor 192.168.15.166 (por confirmar — puerto y host exactos)
  - El repo `UPeU-Infra/midPointEcosystem` es la fuente de verdad de todos los objetos MidPoint
  - El conector `connector-koha-1.1.0.jar` existe en el servidor dev y debe llevarse a prod
  - No se migran usuarios del dev a prod — prod se puebla desde la primera reconciliación con Lamb Academic real
  - El keystore de dev se copia a prod para reusar los passwords cifrados de los recursos

- **Out of scope:**
  - Nginx / SSL / reverse proxy (se puede agregar después)
  - Activación del recurso Active Directory (AD on-premise no confirmado)
  - Integración con Moodle, DSpace, OJS, FreeRADIUS (fases posteriores)
  - Migración de usuarios de prueba (sci-*)
  - Configuración de alertas / monitoreo externo

---

## 2) Pre-reading Log

- `context.md`: documento estratégico completo — arquitectura, esquema de identidad v2.2 (7 ComplexTypes, namespace `urn:upeu:midpoint:person`), fases, decisiones técnicas pendientes, estado auditado 2026-04-09
- `scripts/db/reset-test-data.sh`: script para resetear BD de pruebas con credenciales hardcoded de dev — **no aplica a prod**
- `scripts/db/seed-usuarios-ficticios.sql`: 10 casos de prueba para @sciback.edu — **no aplica a prod**
- `archetypes/ resources/ roles/ tasks/`: todas vacías (solo .gitkeep) — son placeholders de la plantilla genérica SciBack
- `/home/ticrai/proyectos/midpoint-docker/docker-compose.yml` (dev): compose funcional con postgres:16-bullseye + midpoint:4.9.5-ubuntu + patrón data_init. Credenciales hardcodeadas en `environment:`. Sin límites de memoria ni logging configurado.
- `/home/ticrai/proyectos/midPointEcosystem/midpoint/`: estructura GitOps completa — archetypes (4), auth, dashboards, object-templates (1), org (5 XMLs), policies (2), resources (5 dirs), roles (4), simulations, tasks (3)
- `docs/arquitectura.html`: 3 flujos documentados — Aprovisionamiento, SSO Keycloak+EntraID, Ciclo de vida

---

## 3) Codebase Map

### Objetos MidPoint activos en dev (fuente: midPointEcosystem en 192.168.15.230)

| Tipo | Archivos / Cantidad | Estado |
|------|---------------------|--------|
| Arquetipos | StudentType, ProfessorType, AdministrativeStaffType, TechnicalStaffType (4 XML) | ✅ Activos |
| Object Template | UserTemplate-UPEU.xml (1 XML) | ✅ Activo |
| Organizaciones | 000-UPeU-root, 010-Facultades, 020-Rectorado, 030-AreaTecnologia, 040-Posgrado (5 XMLs + 88 orgUnits en DB) | ✅ Activos |
| Roles | Role-Student, Role-Professor, Role-Staff, role-employee-legacy (4 XML base + 67 en DB) | ✅ Activos |
| Recursos | db-sis (Lamb Academic JDBC), entra-id (Graph API), ad (esqueleto), db-crm, db-rrhh | ✅/⏳ |
| Auth | oidc-entra-id.xml | ✅ Activo |
| Policies | policy-sod-basic.xml, policy-owners-required.xml | ✅ Activos |
| Dashboards | dashboard-operacion-iga.xml | ✅ Activo |
| Tasks | task-import-SIS-simulation.xml, task-reconcile-SIS-simulation.xml, task-reconcile-AD-simulation.xml | ⚠️ Simulación |
| ConnId JAR | connector-koha-1.0.2.jar (confirmar ruta en servidor dev) | ✅ Activo |

### Infraestructura objetivo

```
192.168.15.166 (prod)
├── Docker Compose
│   ├── midpoint_data       → postgres:16-bullseye  :5432 (solo red interna)
│   ├── data_init           → midpoint:4.9.5 (one-shot, init schema)
│   └── midpoint_server     → midpoint:4.9.5-ubuntu :8080
├── /opt/midpoint/
│   ├── docker-compose.yml
│   ├── .env.prod           (secretos — fuera del repo)
│   └── connectors/
│       └── connector-koha-1.1.0.jar
└── /home/juansanchez/proyectos/midPointEcosystem/  (git clone)
```

### Flujo de datos en producción

```
BD Lamb Academic (prod) ──JDBC──► MidPoint 4.9.5
                                        │
                            ┌───────────┼───────────┐
                            ▼           ▼           ▼
                       Azure EntraID  Koha         AD (fase 3)
                            │
                       Keycloak SSO
```

### Blast radius

- **Alto:** Recurso Lamb Academic — fuente de verdad. Error en mappings puede crear/modificar usuarios masivamente
- **Alto:** Azure EntraID — afecta acceso a Microsoft 365, Teams, email de toda la universidad
- **Medio:** Koha — afecta acceso a biblioteca (Koha patron vinculado por userid=email)
- **Bajo:** AD on-premise — no confirmado si existe activo

---

## 4) Root Cause Analysis

_No aplica — este es un despliegue nuevo, no una corrección de bug._

---

## 5) Research — Soluciones y Decisiones Técnicas

### 5.1 Docker Compose para producción

**Cambios necesarios respecto al compose de dev:**

- **Límites de memoria** (servidor tiene 9.7GB):
  - `midpoint_server`: `mem_limit: 3g`, `JAVA_OPTS=-Xms1g -Xmx2560m`
  - `midpoint_data`: `mem_limit: 2g`
  - Reservar ~4GB para OS + Docker + overhead

- **Secretos vía `.env.prod`** (no en `environment:` inline):
  ```
  MP_DB_PASSWORD=<strong-password>
  MP_ADMIN_PASSWORD=<strong-password>
  ```
  El compose referencia `${MP_DB_PASSWORD}`. El archivo `.env.prod` va en `/opt/midpoint/` con permisos 600, fuera del repo git.

- **Logging con rotación** (disco de 17GB, limitado):
  ```yaml
  logging:
    driver: "json-file"
    options:
      max-size: "100m"
      max-file: "5"
  ```

- **Healthcheck en midpoint_data** para que `depends_on` funcione correctamente:
  ```yaml
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U midpoint"]
    interval: 10s
    timeout: 5s
    retries: 5
  ```

- **Puerto 5432 NO expuesto al host** en prod — solo accesible dentro de la red Docker interna

- **Volumen del conector:**
  ```yaml
  - /opt/midpoint/connectors:/opt/midpoint/var/icf-connectors:ro
  ```

**Recomendación:** Crear un `docker-compose.prod.yml` separado del de dev, con todas estas mejoras, en el directorio `/opt/midpoint/` del servidor.

---

### 5.2 Orden de importación de objetos

MidPoint tiene dependencias entre objetos. Orden correcto:

1. **SystemConfiguration** — schema de extensión, políticas globales, referencia al object template
2. **ObjectTemplate** (UserTemplate-UPEU) — referenciado por arquetipos
3. **Arquetipos** (4) — dependen del template
4. **Roles** (67) — roles de sistema primero, luego roles de negocio
5. **OrgUnits** (88) — estructura organizacional jerárquica (ninja resuelve el orden)
6. **Políticas** (2) — policy-sod-basic, policy-owners-required
7. **Recursos** (en modo `test` desactivado) — db-sis, entra-id, koha
8. **Auth** — oidc-entra-id
9. **Dashboard** — dashboard-operacion-iga
10. **Tasks** — importar en estado `SUSPENDED`, activar manualmente tras verificación

**Herramienta:** `ninja.sh import` es la más confiable para importación masiva. Soporta archivos con múltiples objetos `<objects>` y hace dos pasadas para resolver referencias cruzadas.

---

### 5.3 Estrategia de migración del keystore

El keystore de dev (`midpoint_home:/opt/midpoint/var/keystore.jceks`) cifra los passwords de los recursos (Lamb Academic, EntraID, Koha). Opciones:

- **Opción A — Copiar keystore de dev a prod:** Los passwords cifrados en los XMLs de dev funcionarán en prod sin reingresarlos. Riesgo: el keystore de prod queda igual que el de dev.
- **Opción B — Keystore nuevo en prod:** Más seguro. Requiere reingresar todos los passwords de recursos en la GUI o via REST después de importar los XMLs.

**Recomendación:** Opción B para producción real. Usar passwords fuertes distintos al dev. Los XMLs de recursos se importan con `<clearValue>` temporalmente y luego se borran del XML — MidPoint los re-cifra con el keystore de prod.

---

### 5.4 Activación gradual de recursos

Para no impactar servicios activos en la primera reconciliación:

1. **Fase A** — Solo Lamb Academic en modo `import` (solo lectura de la BD, sin provisionar a ningún target). Verificar que los usuarios se crean con los arquetipos correctos, extension attributes populados, lifecycle state correcto.

2. **Fase B** — Activar Koha como target. Impacto acotado (solo afecta acceso a biblioteca).

3. **Fase C** — Activar Azure EntraID. Impacto alto — revisar simulation report exhaustivamente antes. Verificar throttling de Graph API.

4. **Fase D** — Active Directory (pendiente confirmar existencia).

En cada fase: correr primero en modo `simulation`, revisar report, aprobar, luego modo real.

---

### 5.5 Conector Koha

El JAR `connector-koha-1.0.2.jar` (o 1.1.0 según context.md) está en el volumen `midpoint_home` del servidor dev. Debe copiarse a `/opt/midpoint/connectors/` en prod antes de arrancar el contenedor. MidPoint escanea ese directorio al iniciar y registra el conector automáticamente.

Verificación: GUI > Configuration > Repository Objects > Connectors — debe aparecer el conector Koha tras el primer arranque.

---

## 6) Clarificaciones necesarias

Estas decisiones requieren confirmación antes de ejecutar en producción:

1. **Acceso a BD Lamb Academic en prod:** ¿El servidor 192.168.15.166 puede conectarse a la BD Lamb Academic de producción? ¿Cuál es el host:puerto real en prod? ¿Es la misma BD que usa el dev (192.168.15.230:5433) o es una BD de producción separada?

2. **AD on-premise:** ¿UPeU tiene Active Directory on-premise activo y accesible desde 192.168.15.166? Si sí, ¿cuál es el host/puerto del LDAP? Esto determina si el recurso AD se activa en esta fase.

3. **Dominio de correo en prod:** En dev los usuarios de prueba usan `@sciback.edu`. En producción, ¿el email generado debe ser `@upeu.edu.pe`? ¿El Object Template necesita ajuste en la regla de generación de email?

4. **Contraseña admin de prod:** ¿Se usa una contraseña nueva fuerte para el administrator de producción (recomendado) o se mantiene la misma que en dev?

5. **Versión del conector Koha:** context.md dice v1.1.0 pero el repo dice v1.0.2. ¿Cuál es la versión exacta del JAR en el servidor dev? ¿Dónde está ubicado en el filesystem del contenedor?

6. **Acceso GitHub desde servidor prod:** ¿El servidor 192.168.15.166 tiene acceso a internet para hacer `git clone` del repo `UPeU-Infra/midPointEcosystem`? ¿O hay que transferir los archivos de otra forma?

7. **Tareas en producción:** Las 3 tasks actuales son de simulación. Para prod, ¿se crean tasks nuevas reales o se modifican las existentes cambiando el modo? ¿Con qué frecuencia (cron) debe correr la reconciliación con Lamb Academic?

8. **Lamb Academic en prod — ¿misma estructura de tablas?** El recurso db-sis usa una query JDBC sobre la tabla `estudiantes`. ¿La BD de producción de Lamb Academic tiene la misma estructura de columnas que la BD ficticia usada en dev?

---

## 7) Plan de implementación propuesto

Basado en lo que **ya existe** y **no depende de confirmaciones externas**, este es el orden de ejecución independiente:

### Bloque 1 — Infraestructura base (sin dependencias externas)
- [ ] Instalar Docker + Docker Compose en 192.168.15.166
- [ ] Crear estructura de directorios `/opt/midpoint/`
- [ ] Crear `docker-compose.prod.yml` con mejoras de producción
- [ ] Crear `.env.prod` con passwords seguros
- [ ] Arrancar PostgreSQL + data_init + MidPoint
- [ ] Verificar que MidPoint arranca y es accesible en :8080

### Bloque 2 — Conector Koha (requiere JAR del dev)
- [ ] Localizar el JAR en el servidor dev (dentro del volumen midpoint_home)
- [ ] Copiar JAR a `/opt/midpoint/connectors/` en prod
- [ ] Verificar que MidPoint detecta el conector al arrancar

### Bloque 3 — Importación de objetos desde midPointEcosystem
- [ ] Clonar `UPeU-Infra/midPointEcosystem` en prod (o transferir XMLs)
- [ ] Importar objetos en orden definido (sección 5.2) via ninja
- [ ] Verificar en GUI: arquetipos, roles, orgUnits, template, políticas

### Bloque 4 — Recursos (requiere confirmación de accesos)
- [ ] Importar recurso Lamb Academic con host/puerto de prod
- [ ] Test connection desde GUI
- [ ] Importar recurso Koha prod
- [ ] Importar recurso Azure EntraID (mismos credentials que dev o nuevos)

### Bloque 5 — Primera reconciliación (requiere Bloque 4 completo)
- [ ] Ejecutar import-SIS en modo simulación apuntando a Lamb Academic prod
- [ ] Revisar simulation report
- [ ] Aprobar y ejecutar en modo real
- [ ] Verificar usuarios creados con arquetipos y extension attributes correctos

### Bloque 6 — Activación de targets (requiere Bloque 5 verificado)
- [ ] Activar Koha como target — simulation → real
- [ ] Activar Azure EntraID — simulation → real (alto impacto)
- [ ] (Fase futura) Activar AD on-premise
