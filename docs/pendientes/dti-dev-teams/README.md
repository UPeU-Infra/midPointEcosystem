# Equipos de desarrollo de la DTI — listo para aplicar, **pendiente de aprobación**

**15-sep-2026 · nada de esto está en PROD.** Decisión y mediciones:
[`ADR-065`](../../architecture/adrs/ADR-065-equipos-desarrollo-dti.md).

9 equipos · 27 personas · 6 jefes. Modelo validado por el director de la DTI, David Jefferson
Barrantes Delgado.

| Equipo | `identifier` | Personas | Jefe | Grupo LDAP |
|---|---|---|---|---|
| Lamb Academico | `DTI-DEV-ACADEMICO` | 9 | Samuel David Roncal Vidal | `cn=dti-dev-academico` |
| Lamb Financial | `DTI-DEV-FINANCIAL` | 7 | Juan Hus Quezada Moreno | `cn=dti-dev-financial` |
| Aplicaciones Móviles | `DTI-DEV-MOVILES` | 2 | — director | `cn=dti-dev-moviles` |
| Conservatory | `DTI-DEV-CONSERVATORY` | 2 | Owen Miguelich Mejia Guerra | `cn=dti-dev-conservatory` |
| Lamb Learning | `DTI-DEV-LEARNING` | 2 | Uziel Carpio Villanueva | `cn=dti-dev-learning` |
| Lamb Talent | `DTI-DEV-TALENT` | 2 | Sotil Yarasca Quispe | `cn=dti-dev-talent` |
| DevOps | `DTI-DEV-DEVOPS` | 1 | — director | `cn=dti-dev-devops` |
| Lamb Events | `DTI-DEV-EVENTS` | 1 | — director | `cn=dti-dev-events` |
| Lamb Research | `DTI-DEV-RESEARCH` | 1 | — director | `cn=dti-dev-research` |

## Archivos

| # | Archivo | Qué es |
|---|---|---|
| 01 | `01-archetype-org-team.xml` | Archetype `archetype-org-team`. **Sin** proyección `generic/ou` — ahí está la decisión |
| 02 | `02-orgs-dti-dev.xml` | 9 `OrgType`. `assignment` a DTI (padre) y `inducement` a su rol |
| 03 | `03-roles-ar-dti-dev.xml` | 9 `AR-DTI-Dev-*`. Único efecto: asociación `ri:group` |
| 04 | `04-grupos-ldap.ldif` | 9 `groupOfUniqueNames`. **Lo único que toca el directorio** |
| — | `aplicar.py` | Despliegue idempotente + verificación por relectura. Dry-run por defecto |
| — | `modelo-dti-VALIDADO.json` | El modelo del director. Fuente, no se re-deriva |
| — | `teams.json` · `oids-personas.json` | OIDs congelados y las 27 personas resueltas contra PROD |

## Orden de aplicación (importa)

```bash
source ~/.secrets/midpoint-upeu.env
cd docs/pendientes/dti-dev-teams

python3 aplicar.py                 # 1. dry-run: LEER LA LISTA COMPLETA (R3 del protocolo)
# 2. backup: tag git + pg_dump
# 3. cargar 04-grupos-ldap.ldif en OpenLDAP  ← requiere el visto bueno explícito
python3 aplicar.py --aplicar       # 4. archetype → roles → orgs → assignments → verificación
python3 ../../../upeu/scripts/verificar-arbol-organizativo.py   # 5. debe seguir 6/6
```

Los roles van **antes** que las orgs: cada org induce su rol y la referencia debe resolver.

Si el LDIF aún no está cargado, `aplicar.py --aplicar` no rompe nada: la
`associationTargetSearch` con `createOnDemand=false` no encuentra el grupo y no lo crea. Se
carga el LDIF después y un recompute converge.

## Al desplegar

1. Mover `01`/`02`/`03` a `upeu/orgs/dti/` y `upeu/roles/dti/` — mientras no estén en PROD **no
   pueden** vivir ahí: la invariante I4 del verificador exige que toda org de `upeu/orgs/` exista
   en PROD, y `KNOWN_PENDING_FILES` está vacía a propósito desde el 06-ago-2026.
2. Regenerar `docs/baselines/arbol-organizativo-baseline.json` **en el mismo commit**.
3. Pasar el ADR-065 a *aplicado y verificado* con la evidencia.

## Lo que NO resuelve esto

Las 27 personas ya están en un grupo `dti-*` por `serviceDeskTeam`, y en 8 casos **no coincide**
con su equipo de desarrollo (tabla M5 del ADR). Son dos dimensiones legítimas — cola de tickets
frente a squad de producto — y tras este despliegue una persona estará en dos grupos `dti-*`, que
es correcto. Queda para el director decidir si además quiere alinear las colas de Zammad.
