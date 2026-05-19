# `canonical/` — Capa canónica IGA (agnóstica al tenant)

**Fecha:** 2026-05-19 (consolidación)
**Autoridad:** `iga-canonical-standards` v2026-05 + `midpoint-best-practices` v2024-11

---

## Contrato de esta capa

Contenido **agnóstico a la institución**. Diseñado contra estándares:

- **eduPerson 202208 v4.4.0** (Internet2/REFEDS) — vocabulario de afiliaciones, ePPN, ePSA, eduPersonOrcid.
- **SCHAC 1.6.0** — identificadores y atributos europeos/internacionales.
- **NIST RBAC INCITS 359** — separación 3-capas BR → AR → Entitlement.
- **NIST SP 800-63-3** — IAL/AAL/FAL.
- **ISO/IEC 24760-1/2/3** — framework de identity management (terminología, lifecycle, IIA).
- **ISO/IEC 27001:2022** controles A.5.15/16/17/18, A.8.2/3 — owners, SoD, gobierno.
- **SCIM 2.0** (RFC 7643/7644) — modelo de datos cross-platform.

Cualquier institución universitaria peruana debería poder reutilizar esta capa cambiando solo `upeu/` por su propio overlay.

## Estructura

```
canonical/
├── schemas/
│   └── sciback-person-v1.0.xml         # urn:sciback:midpoint:person — schema canónico SciBack
├── archetypes/
│   ├── user/                            # eduPerson sub-types (student/faculty/staff/alumni/...)
│   └── org/                             # OrgType jerárquico (institution/campus/faculty/...)
├── object-templates/
│   └── UserTemplate-Person-Base.xml    # Template base (ROADMAP: split per-archetype)
├── policies/
│   ├── policy-owners-required.xml      # ISO 27001 A.5.18
│   └── policy-sod-basic.xml            # RBAC INCITS 359 §6.3 SoD
├── function-libraries/
│   └── sb-program-resolver.xml         # Resolver canónico de programas SKOS
└── roles/                               # FUTURO: roles canónicos (R-Affiliation-* a canonificarse)
```

## Reglas

1. **Schema is the law.** Antes de extender, buscar en core (`UserType` ya tiene `givenName`, `familyName`, `personalNumber`, etc.). Solo agregar al `<extension>` lo que NO encaje.
2. **IIA documentada.** Cada atributo tiene UNA Identity Information Authority.
3. **OIDs estables.** Los OIDs aquí están en PROD UPeU. NO modificar — los nuevos clientes SciBack pueden re-importar con OIDs propios.
4. **Naming canónico:** kebab-case sin prefijo de tipo dentro de cada carpeta (`user-student.xml`, no `archetype-user-student.xml`).
5. **`displayName` y `name` interno del XML** se mantienen para no romper UI/refs internas. Solo cambia el filename.

## Lo que NO va aquí

- Resources (siempre tenant-specific por host/IIA → `upeu/resources/`).
- Lookup tables con valores institucionales (`program-resolver-lamb` → `upeu/lookup-tables/`).
- Orgs de la institución (jerarquía concreta → `upeu/orgs/`).
- Application roles dependientes de un vendor (`AR-Koha-Patron-Student` → `upeu/roles/application/`).
- Business roles UPeU (`BR-Docente-TC` → `upeu/roles/business/`).
- MOF (Manual Operativo Funciones) → `upeu/roles/mof/`.
