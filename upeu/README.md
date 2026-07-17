# `upeu/` — Capa overlay UPeU (tenant-specific)

**Fecha:** 2026-05-19 (consolidación)
**Tenant:** Universidad Peruana Unión

---

## Contrato de esta capa

Contenido **específico a UPeU**. Adapta y extiende `canonical/` con:

- Schema overlay (`upeu-local-v1.0`, namespace `urn:upeu:midpoint:local`) para atributos exclusivos LAMB/Oracle (`taxId`, `studentCycle`, `primaryAffiliationCode`, `photoUrl`, etc.).
- Resources contra los IIAs UPeU (Oracle LAMB, OpenLDAP `ldap-identity-trust`, Entra ID tenant UPeU, Koha ILS BUL/BUJ/BUT/CIA, AD `lim.upeu.edu.pe`).
- Jerarquía orgánica concreta (UPeU root + facultades + campus + Colegio Unión + academic programs).
- Roles funcionales UPeU (BR-Docente-TC, MOF-Decano, GOV-APROBADOR-WORKITEMS, etc.).
- Catálogo Positions Ley 30220 / Resol. 0001-2026 (738 cargos).

## Estructura

```
upeu/
├── schemas/
│   └── upeu-local-v1.0.xml             # urn:upeu:midpoint:local — overlay
├── archetypes/
│   ├── auxiliary/                       # aux-affiliation-* (decisión pendiente: deprecate)
│   └── custom/                          # archetype-person, archetype-position, archetype-affiliation-role
├── orgs/                                # Jerarquía UPeU completa
│   ├── campus/, academic-programs/, colegio-union/, partners/
├── resources/
│   ├── oracle-lamb/                     # 4 resources v3 (trabajadores/estudiantes/egresados/posiciones)
│   ├── ldap-identity-cache.xml          # OpenLDAP ldap-identity-trust
│   ├── entra-id-graph.xml               # Microsoft Graph (read-only Fase 1-11)
│   ├── koha-ils.xml                     # Koha ILS UPeU
│   ├── ad-upeu.xml                      # AD UPeU (lifecycle=draft, Fase 12)
│   └── datasets/                        # CSV/PG demo (testing only)
├── roles/
│   ├── affiliation/                     # R-Affiliation-* (6 roles, futuro canonical)
│   ├── application/                     # AR-* (vendor-specific: Koha, M365, Indico, DSpace, Zoom, WiFi)
│   ├── business/                        # BR-* (Docente-TC/TP, Estudiante-*, etc.)
│   ├── governance/                      # GOV-* (revisor cert., aprobador workitems)
│   ├── mof/                             # MOF-* Manual Operativo Funciones UPeU
│   └── system/                          # SYS-IGA-SUPERUSER
├── services/
│   └── positions/                       # 13 positions versionados (738 vía task LAMB)
├── lookup-tables/
│   └── program-resolver-lamb.xml
├── object-collections/
├── dashboards/
├── auth/
│   └── oidc-entra-id.xml
├── object-templates/                    # FUTURO: overrides per-archetype UPeU
├── tasks/
│   ├── simulations/, pilots/
└── system/
    └── system-configuration.xml
```

## Naming

Kebab-case sin prefijo de tipo en filename donde sea limpio. Excepciones legítimas que mantenemos:
- `R-Affiliation-*`, `AR-*`, `BR-*`, `GOV-*`, `MOF-*`, `SYS-*` — son convenciones UPeU ya consolidadas en PROD; renombrar masivo no se hace en esta consolidación.
- `position-NNN-{slug}` — incluye id catálogo Resol. 0001-2026.
- `org-OU-CAMPUS-{LIMA|JULIACA|TARAPOTO}` — convención existente.

## OIDs — UPeU (PROD)

- Los OIDs de los objetos en `upeu/` son los vivos en PROD (`192.168.15.166`).
- Cuando esta capa se reutilice para otra institución: regenerar OIDs (no copiar).
- Los OIDs de `canonical/` SÍ pueden ser portables entre instituciones.

## Decisiones doctrinales reflejadas aquí

1. **NO conector MidPoint→Keycloak.** *(Sigue vigente.)* ⚠️ **Corregida la arquitectura que citaba esta línea (ADR-058, 17-jul-2026):** decía `MidPoint→OpenLDAP←Keycloak User Federation`. **No se federa LDAP en Keycloak.** Es `MidPoint→OpenLDAP→app` (la app lee con bind propio); **Keycloak solo autentica** y queda fuera de la vía de datos. Ver [`ADR-058`](../../../../sciback/sciback-core-docs/docs/architecture/adrs/058-keycloak-solo-autentica.md).
2. **UPeU usa Microsoft 365**, no Google Workspace.
3. **AD UPeU** queda `lifecycle=draft` hasta Fase 12 (Entra ID gobierna primero).
4. **Schemas como SchemaType objects en DB**, no XSDs físicos.
5. **Cuentas privilegiadas las gestiona David Urquizo** (no MidPoint).
6. **Oracle LAMB solo lectura.** Política absoluta.
