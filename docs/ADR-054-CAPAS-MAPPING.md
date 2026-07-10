# Mapeo de capas ADR-054 ↔ estructura MidPoint (IGA)

> **Decisión (2026-07-09): NO se aplica el folder-model literal de ADR-054 a este repo.**
> IGA es una **excepción documentada**, por una razón técnica dura (abajo). La separación de
> capas existe **lógicamente**, no como carpetas hermanas.

## El conflicto

- **ADR-054** (modelo SciBack de 3 capas) quiere: `canonico/` (agnóstico) y `instituciones/<cliente>/`
  como **carpetas/repos separados**.
- **MidPoint** necesita desplegar `canonical/` + `upeu/` como **UN solo proyecto ordenado**:
  `midpoint-project.yaml` tiene `objectsRoot: "."` y carga ~35 `sources` en un **orden que importa**
  (schemas → archetypes → object-templates → policies → roles), mezclando ambas capas. `ninja` importa
  ese proyecto completo a producción (MidPoint .166).

Mover `upeu/` a una carpeta hermana rompería las 28 rutas `./upeu/...` del yaml → falla el deploy.
No es un `git mv`; sería un rediseño con paso de ensamblado. Por eso **no se mueve**.

## Mapeo real de capas (cómo leer esta estructura)

| Capa ADR-054 | Dónde vive en IGA | Contenido |
|---|---|---|
| **Capa 1 · Canónico** (agnóstico) | `canonico/canonical/` | eduPerson/SCHAC, RBAC INCITS 359, object-templates, policies, ISO 24760 — reutilizable en cualquier universidad |
| **Capa 3 · Institución UPeU** (overlay) | `canonico/upeu/` | archetypes custom, orgs (campus/programas/colegio-unión), resources (Oracle LAMB), roles (afiliación/MOF/gobernanza), tasks, dashboards — 100% UPeU |
| **Capa 3 · Satélites UPeU** (repos propios) | `instituciones/upeu/` | `connector-koha` (repo `UPeU-Infra/connector-koha`) y `oracle-pg-cdc` — componentes con ciclo propio, NO parte del proyecto MidPoint desplegable |

La separación **canonical vs upeu** dentro de `canonico/` **es** la separación capa1/capa3 — a la manera
nativa de MidPoint (un proyecto, dos capas ordenadas), no a la manera de carpetas de ADR-054.

## Nota de propiedad intelectual

El repo es `UPeU-Infra/midPointEcosystem` (de UPeU, desplegado a producción UPeU), no un canónico de
SciBack. Forzarle el folder-model de SciBack va en contra de cómo nació. La destilación agnóstica
reutilizable es el subárbol `canonical/`; el día que aparezca un 2º cliente, **eso** es lo que se
reutiliza, y `upeu/` es lo que se reemplaza por el overlay del nuevo tenant.

## Si algún día se quiere el folder-model estricto

Sería un mini-proyecto (brainstorm → plan → prueba en lab `midpoint-dev` antes de tocar .166):
separar `canonical/`/`upeu/` en carpetas ADR-054 + un **build de ensamblado** que las combine y
regenere `midpoint-project.yaml` para el deploy. No hacerlo con un movimiento de carpetas.
