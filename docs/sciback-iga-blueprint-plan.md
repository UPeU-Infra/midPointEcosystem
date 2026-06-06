# SciBack IGA Blueprint — Plan de Productización

**Versión:** 2026-06-06
**Fase del roadmap:** Fase 11 (Productización SciBack)
**Prerrequisito:** Fases 1-10 de UPeU estables (estado actual: Fases 1-8 completas, Fase 10 en PROD)
**Repo futuro:** `~/proyectos/sciback/sciback-iga-blueprint` (aún no creado — este doc es el plan)

---

## 1. Objetivo

Separar el `canonical/` de los overlays UPeU para que futuras universidades cliente puedan adoptar los mismos canónicos con sus propios datos, sin duplicar lógica ni copiar XMLs ad hoc.

**Problema actual:** `canonical/` y `upeu/` conviven en el mismo repo (`UPeU-Infra/midPointEcosystem`). Esto hace que:
- Los canónicos tienen referencias implícitas a UPeU (OIDs con dominio, comentarios, carpetas hardcodeadas).
- Un cliente nuevo tendría que clonar todo el repo UPeU y limpiar manualmente.
- No hay una instalación limpia parametrizable.

**Solución:** un repo separado `sciback-iga-blueprint` que contenga solo piezas agnósticas con placeholders, más un mecanismo de overlay per-cliente.

---

## 2. Estructura propuesta del repo `sciback-iga-blueprint`

```
sciback-iga-blueprint/
├── canonical/
│   ├── archetypes/
│   │   ├── user/              ← 8 archetypes UserType (student, faculty, staff,
│   │   │                           alumni, affiliate-*, contractor, service-account)
│   │   ├── org/               ← 8 archetypes OrgType (institution, campus, faculty,
│   │   │                           department, academic-unit, governance,
│   │   │                           partner-institution, project)
│   │   └── role/              ← 2 archetypes RoleType (application-role, business-role)
│   ├── object-templates/
│   │   ├── UserTemplate-Person-Base.xml    ← base con ${INSTITUTION_SCOPE}, ${HOME_ORG}
│   │   ├── UserTemplate-Alumni.xml
│   │   ├── UserTemplate-Student.xml
│   │   ├── UserTemplate-Employee-Faculty.xml
│   │   └── UserTemplate-Employee-Staff.xml
│   ├── policies/
│   │   ├── sod-gov-aprobador-revisor.xml   ← SoD canónica GOV-APROBADOR ⊥ GOV-REVISOR
│   │   └── sod-finanzas-tesoreria.xml      ← SoD financiera (genérica)
│   ├── roles/
│   │   ├── affiliation/       ← R-Affiliation-Student/Faculty/Staff/Alum/Affiliate/Contractor
│   │   └── application/       ← AR-Koha-Patron-Student, AR-LDAP-Person, AR-DSpace-*, AR-OJS-*
│   └── schemas/
│       └── sciback-person-v1.0.xml         ← schema urn:sciback:midpoint:person
│
├── overlay-template/
│   ├── README.md              ← instrucciones de parametrización
│   ├── config.env.template    ← variables a definir por el cliente
│   ├── resources/
│   │   ├── oracle-jdbc-students.xml.tmpl   ← ${JDBC_URL}, ${DB_SCHEMA_SIS}, ${SEM_ACTIVO}
│   │   ├── oracle-jdbc-workers.xml.tmpl    ← ${JDBC_URL}, ${DB_SCHEMA_HR}
│   │   ├── oracle-jdbc-egresados.xml.tmpl
│   │   ├── oracle-jdbc-org.xml.tmpl
│   │   ├── koha-ils.xml.tmpl               ← ${KOHA_URL}, ${KOHA_USER}, ${KOHA_PASS}
│   │   ├── ldap-identity-cache.xml.tmpl    ← ${LDAP_URL}, ${LDAP_BASE_DN}, ${LDAP_BIND_DN}
│   │   └── entra-id-graph.xml.tmpl         ← ${TENANT_ID}, ${CLIENT_ID}, ${CLIENT_SECRET}
│   ├── roles/
│   │   └── business/          ← BR-Docente-TC/TP con ${INSTITUTION_CODE} en names
│   ├── schemas/
│   │   └── institution-local-v1.0.xml.tmpl ← schema urn:${INSTITUTION_CODE}:midpoint:local
│   └── orgs/
│       └── bootstrap-orgs.xml.tmpl         ← árbol org con ${CAMPUS_CODES[]} y ${FACULTY_CODES[]}
│
├── scripts/
│   ├── parametrize.sh         ← reemplaza placeholders desde config.env
│   ├── import-canonical.sh    ← importa canonical/ vía REST API a MidPoint
│   └── import-overlay.sh      ← importa overlay/ parametrizado vía REST API
│
└── docs/
    ├── INSTALL.md             ← cómo parametrizar e instanciar para nuevo cliente
    ├── OVERLAYS.md            ← qué va en overlay vs canónico (criterio detallado)
    ├── PLACEHOLDERS.md        ← tabla completa de todos los ${} y sus valores ejemplo UPeU
    └── CHANGELOG.md           ← historial de versiones del blueprint
```

---

## 3. Criterio canónico vs overlay

### Regla de oro

Una pieza es **canónica** si aplica a *cualquier* universidad peruana licenciada por SUNEDU sin modificación. Es **overlay** si depende de datos, tablas, esquemas o particularidades de una institución específica.

### Tabla de decisión

| Pieza | Capa | Razón |
|---|---|---|
| 8 archetypes UserType (student, faculty, staff, alumni, affiliate-*, contractor, service-account) | **canónico** | Vocabulario universal eduPerson/SCHAC. Cualquier universidad los necesita. |
| 8 archetypes OrgType (institution, campus, faculty, department, academic-unit, governance, partner-institution, project) | **canónico** | Ley 30220 + estructura universitaria genérica. |
| 2 archetypes RoleType (application-role, business-role) | **canónico** | RBAC genérico. |
| Schema `urn:sciback:midpoint:person` | **canónico** | Atributos no cubiertos por eduPerson/SCHAC/SCIM, agnósticos de institución. |
| Object templates base + per-archetype | **canónico** (con placeholders) | La lógica de `fullName`, `emailAddress`, `ePPN` es la misma para todas; los valores literales (`@upeu.edu.pe`) se parametrizan con `${INSTITUTION_SCOPE}`. |
| Roles de afiliación (R-Affiliation-*) | **canónico** | Vocabulario eduPerson cerrado. |
| AR-LDAP-Person, AR-Koha-Patron-Student/Faculty, AR-DSpace-*, AR-OJS-* | **canónico** | Estos servicios son comunes en universidades peruanas. Los OIDs son canónicos (estables). |
| SoD GOV-APROBADOR ⊥ GOV-REVISOR | **canónico** | Iso 27001 A.8.2 aplica a todas. |
| Resources Oracle JDBC (trabajadores, estudiantes, egresados, org) | **overlay** | Los nombres de vistas, schemas, joins y columnas son propios de LAMB (UPeU). Otra universidad tiene Oracle con esquema diferente. |
| Resource Koha ILS | **overlay** (template) | La URL, credenciales y versión del conector cambian por cliente. La lógica de mapeo es reutilizable como template. |
| Resource LDAP Identity Cache | **overlay** (template) | URL, base DN, bind DN varían por cliente. El template es genérico. |
| Resource Entra ID | **overlay** (template) | Tenant ID, client ID, client secret son por cliente. |
| Schema `urn:upeu:midpoint:local` | **overlay** | `lambDocNum`, `laboralStatus`, referencias a LAMB son UPeU-only. |
| OrgTree UPeU (campus, facultades, departamentos) | **overlay** | Los 199 orgs son el catálogo real de UPeU, no genérico. |
| Roles MOF-* | **overlay** | Derivados de `ELISEO.LAMB_ROL` (role mining UPeU). |
| Partner institutions (Colegio Unión, Clínica Good Hope, ISTAT, AGTU) | **overlay** | Red adventista UPeU-específica. |
| BR-Docente-TC/TP con regímenes ENOC | **overlay** | Los valores de `ID_CATEGORIAOCUPACIONAL` y `MOISES.PERSONA_ACAD_REGIMEN` son de LAMB. |
| `schacHomeOrganization = upeu.edu.pe` | **overlay** | El dominio es por cliente. |

### Patrón de decisión rápida

```
¿Aplica a cualquier universidad peruana sin cambios?
    SÍ → canonical/
    NO → ¿Es la misma lógica pero con valores distintos?
             SÍ → canonical/ con placeholders ${VAR}
             NO → overlay/${CLIENTE}/
```

---

## 4. Placeholders principales

| Placeholder | Ejemplo UPeU | Descripción |
|---|---|---|
| `${INSTITUTION_CODE}` | `UPEU` | Código corto (3-6 chars uppercase) |
| `${INSTITUTION_NAME}` | `Universidad Peruana Union` | Nombre oficial sin tildes (para XML) |
| `${INSTITUTION_SCOPE}` | `upeu.edu.pe` | Dominio para ePPN y email |
| `${HOME_ORG_TYPE_URN}` | `urn:schac:homeOrganizationType:eu:higherEducationalInstitution` | Tipo SCHAC |
| `${NAMESPACE_URI}` | `urn:upeu:midpoint:local` | Namespace del schema overlay |
| `${JDBC_URL}` | `jdbc:oracle:thin:@192.168.13.9:1521:UPEU` | URL JDBC del ERP |
| `${DB_SCHEMA_SIS}` | `DAVID` | Schema Oracle para SIS (estudiantes) |
| `${DB_SCHEMA_HR}` | `MOISES` | Schema Oracle para HR (trabajadores) |
| `${DB_SCHEMA_ORG}` | `ELISEO` | Schema Oracle para estructura org |
| `${SEM_ACTIVO}` | `279,267` | IDs de semestres activos (query LAMB) |
| `${LDAP_BASE_DN}` | `dc=upeu,dc=edu,dc=pe` | Base DN del OpenLDAP |
| `${LDAP_URL_PRIMARY}` | `ldap://192.168.15.168:389` | URL LDAP Node1 |
| `${LDAP_URL_SECONDARY}` | `ldap://192.168.15.169:389` | URL LDAP Node2 (failover) |
| `${KOHA_URL}` | `http://192.168.15.x:8080` | URL base Koha |
| `${TENANT_ID}` | `xxxxxxxx-...` | Entra ID Tenant ID |
| `${CAMPUS_CODES}` | `LM,JU,TA` | Códigos de campus (comma-separated) |

---

## 5. Dependencias para ejecutar la Fase 11

Para que la extracción del blueprint sea viable, las siguientes condiciones deben estar estables en UPeU:

| Condición | Estado (2026-06-06) |
|---|---|
| Fase 1 Schema — canónico y overlay definidos y en PROD | COMPLETA |
| Fase 2 Archetypes + Org tree — 18 archetypes + 199 orgs | COMPLETA |
| Fase 3 Object templates — base + 4 per-archetype | COMPLETA |
| Fase 4 OpenLDAP HA — N-Way Multimaster operativo | COMPLETA |
| Fase 5 Resources READ — 6 resources Oracle activos | COMPLETA |
| Fase 6 Resources WRITE OpenLDAP — outbound validado | COMPLETA |
| Fase 7 RBAC — ARs/BRs/MOFs/GOVs/SoD implementados | COMPLETA |
| Fase 9 Piloto end-to-end validado | PENDIENTE |
| Schema canónico sin hardcodes UPeU en archivos `canonical/` | PENDIENTE (limpieza) |
| OIDs canónicos estables (no cambiarán en nuevas versiones) | PARCIAL — verificar |

**Prerrequisito real para Fase 11:** completar Fase 9 (piloto end-to-end). Sin un flujo completo validado, extraer el blueprint sin testar es arriesgado.

---

## 6. Pasos de ejecución (cuando se inicie Fase 11)

### Paso 11.1 — Auditoría de hardcodes en `canonical/`

Antes de extraer, auditar `canonical/` buscando referencias UPeU:
```bash
grep -r "upeu" canonical/ --include="*.xml" -l
grep -r "MOISES\|DAVID\|ELISEO" canonical/ --include="*.xml" -l
grep -r "192\.168\." canonical/ --include="*.xml" -l
```
Cualquier match en `canonical/` es un hardcode a limpiar (reemplazar por placeholder o mover a `upeu/`).

### Paso 11.2 — Crear repo `sciback-iga-blueprint`

```bash
mkdir -p ~/proyectos/sciback/sciback-iga-blueprint
cd ~/proyectos/sciback/sciback-iga-blueprint
git init
# Copiar canonical/ desde este repo
cp -r ~/proyectos/upeu/midPointEcosystem/canonical/ ./
# Crear estructura overlay-template/ + scripts/ + docs/ (ver §2)
```

### Paso 11.3 — Parametrizar canonical/ con placeholders

Reemplazar todos los valores literales UPeU en los XMLs copiados:
- `upeu.edu.pe` → `${INSTITUTION_SCOPE}`
- `Universidad Peruana Union` → `${INSTITUTION_NAME}`
- `UPEU` → `${INSTITUTION_CODE}`
- OIDs canónicos: **NO cambiar** — son estables y deben ser idénticos en todas las instancias.

### Paso 11.4 — Crear overlay-template/ desde upeu/

Tomar los resources de `upeu/resources/` como punto de partida para los templates `.xml.tmpl`. Sustituir:
- IPs y URLs → `${KOHA_URL}`, `${LDAP_URL_PRIMARY}`, `${JDBC_URL}`
- Schemas Oracle → `${DB_SCHEMA_SIS}`, `${DB_SCHEMA_HR}`
- Credenciales → `${JDBC_USER}`, `${JDBC_PASS}` (o referencias a `~/.secrets/`)

### Paso 11.5 — Script `parametrize.sh`

Script que dado un `config.env` de cliente, reemplaza todos los `${PLACEHOLDER}` en los XMLs:
```bash
#!/bin/bash
set -euo pipefail
source "$1"  # config.env del cliente
find overlay-template/ -name "*.xml.tmpl" | while read f; do
    out="${f%.tmpl}"
    envsubst < "$f" > "$out"
done
```

### Paso 11.6 — Documentar en `docs/INSTALL.md`

Proceso completo para instanciar el blueprint para un cliente nuevo:
1. Clonar `sciback-iga-blueprint`
2. Copiar `overlay-template/` como `overlay/<cliente>/`
3. Crear `overlay/<cliente>/config.env` con los valores del cliente
4. Ejecutar `scripts/parametrize.sh overlay/<cliente>/config.env`
5. Ejecutar `scripts/import-canonical.sh` (importa canonical/ vía REST API)
6. Ejecutar `scripts/import-overlay.sh overlay/<cliente>/` (importa overlay parametrizado)
7. Verificar Test Connection de cada resource
8. Ejecutar import/reconcile piloto (50 usuarios)

### Paso 11.7 — Repo GitOps del cliente

Cada cliente tiene su repo GitOps propio (análogo a `UPeU-Infra/midPointEcosystem`):
```
github.com/<CLIENTE>-Infra/midPointEcosystem
├── canonical/      ← git submodule o copia de sciback-iga-blueprint/canonical/
├── <cliente>/      ← overlay parametrizado (equivalente a upeu/ en UPeU)
└── docs/           ← documentación operativa del cliente
```

---

## 7. Relación con el repo actual

```
UPeU-Infra/midPointEcosystem  (este repo — referencia + overlay UPeU)
    │
    ├── canonical/         ← FUENTE para sciback-iga-blueprint/canonical/
    ├── upeu/              ← FUENTE para overlay-template/ + ejemplo overlay UPeU
    └── docs/specs/sciback-iga-blueprint/  ← este doc + 01-iga-blueprint-peru.md
    
    ↓ extracción (Fase 11)
    
SciBack/sciback-iga-blueprint  (futuro repo canónico SciBack)
    ├── canonical/         ← agnóstico, parametrizado, estable
    ├── overlay-template/  ← esqueleto de overlay para cualquier cliente
    └── docs/              ← INSTALL.md, OVERLAYS.md, PLACEHOLDERS.md

    ↓ instanciación por cliente
    
<CLIENTE>-Infra/midPointEcosystem
    ├── canonical/         ← igual que SciBack (git submodule o copia estable)
    └── <cliente>/         ← overlay parametrizado con los datos del cliente
```

---

## 8. Principios de mantenimiento del blueprint

1. **Bug fixes en canónico van al blueprint, nunca al overlay.** Si se corrige lógica en `canonical/` de UPeU, el fix se porta a `sciback-iga-blueprint/canonical/` y los demás clientes hacen `git pull`.
2. **El cliente nunca es upstream.** Los overlays de cliente (`upeu/`, `uniq/`, etc.) nunca se suben al blueprint canónico.
3. **OIDs estables.** Los OIDs en `canonical/` son inmutables entre versiones del blueprint. Un OID canónico que cambia rompe todas las instancias activas.
4. **Versioning semántico.** El blueprint usa `vMAJOR.MINOR.PATCH`: MAJOR para breaking changes en OIDs o estructura, MINOR para nuevas piezas canónicas, PATCH para correcciones.
5. **Toda mejora generalizable de UPeU primero al blueprint.** Si se implementa algo en UPeU que claramente aplica a cualquier universidad, se porta al blueprint antes de hacer `git pull` en otro cliente.

---

**Fin del documento de plan.**
Referencia de implementación: `canonical/` de este repo + `docs/specs/sciback-iga-blueprint/01-iga-blueprint-peru.md`
