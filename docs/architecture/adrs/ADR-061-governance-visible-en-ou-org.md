# ADR-061 — Las orgs de gobierno se publican en `ou=org`

**Fecha:** 14-ago-2026
**Estado:** **aplicado y verificado** (14-ago-2026)
**Ámbito:** árbol organizativo — cambio 🟡 (ADR + simulación `preview` + canario + baseline)
**Rector:** [`ARQUITECTURA-ARBOL-ORGANIZATIVO.md`](../ARQUITECTURA-ARBOL-ORGANIZATIVO.md)
**Antecede:** [`ADR-060`](ADR-060-limpieza-shadows-huerfanos-ou.md) — ver su §Corrección

## Contexto

InOut (aforo del CRAI) resuelve el área de cada persona uniendo dos ramas del directorio:
el código va en `departmentNumber` de la persona, el nombre en `ou=org`. Reportó 56 códigos
sin entrada; tras el ADR-060 y el import del resource Org quedan **21 códigos y 274 personas
sin área**.

La causa de las que faltan **no es un hueco de datos**: es que **el archetype decide quién
proyecta a LDAP**, y tres archetypes no llevan el `inducement` con la `construction`:

| Archetype | Orgs que proyectan |
|---|---|
| `archetype-org-department` | 94 de 100 |
| `Academic-Program` | 26 de 26 |
| `archetype-org-faculty` | 4 de 5 |
| **`archetype-org-governance`** | **0 de 12** |
| `archetype-org-academic-unit` | 0 de 16 |
| `archetype-org-research-center` | 0 de 7 |

`RECTORADO` es `governance`: **nunca iba a publicarse**, por diseño del archetype. Ningún
recompute lo cambia — se verificó con un recompute individual que terminó en `success` sin
crear proyección.

## Decisión

**Añadir a `archetype-org-governance` el `inducement` con la `construction` hacia
LDAP-IdentityCache (`kind=generic`, `intent=ou`)**, el mismo que ya llevan los archetypes
que sí publican.

**Solo `governance` por ahora.** `academic-unit` (16 orgs) y `research-center` (7) quedan
fuera de este ADR: son poblaciones distintas y su visibilidad en el directorio merece su
propia decisión.

### Las 12 orgs afectadas

| Org | `identifier` |
|---|---|
| ASAMBLEA-UNIVERSITARIA | `1` |
| CONSEJO-UNIVERSITARIO | `2` |
| **RECTORADO** | **`3`** |
| VICERRECTORADO-BIENESTAR-UNIVERSITARIO | `4` |
| VICERRECTORADO-ACADEMICO | `5` |
| VICERRECTORADO-ADMINISTRATIVO | `6` |
| SECRETARIA-GENERAL | `23` |
| DIR-PLANIFICACION-CALIDAD | `24` |
| ASESORIA-LEGAL | `65` |
| AUDITORIA-INTERNA | `66` |
| CU-DIR | `cu-dir-01` |
| GOBIERNO-UNIVERSITARIO | `gov.upeu` |

## Por qué funciona sin tocar nada más

**El `identifier` ya es el `ID_AREA`.** El mapping de `ou` del objectType `generic/ou` usa
`$focus/identifier`:

```groovy
def rawId = identifier?.toString()?.trim()
def v = (rawId && !rawId.contains('.')) ? rawId : focusName?.toString()?.trim()
```

Así que `RECTORADO` publicará **`ou=3`** — exactamente lo que InOut busca. No hay que cambiar
la clave de nadie ni tocar `departmentNumber` en las 24.824 personas.

## Impacto medido

| | |
|---|---|
| Códigos que resuelve | **8** de 21 (`3`, `4`, `5`, `6`, `23`, `24`, `65`, `66`) |
| **Personas que recuperan su área** | **119** |
| ...de ellas, personal (staff/faculty) | **112** |
| Personas sin área | 274 → **~155** |

Los 13 códigos restantes son de otros archetypes o de entidades ajenas a UPeU, y no los cubre
este ADR.

## ⚠️ Las dos excepciones

`CU-DIR` (`cu-dir-01`) y `GOBIERNO-UNIVERSITARIO` (`gov.upeu`) **no tienen identifier
numérico**. Por la regla del mapping:

- `cu-dir-01` no lleva punto → publicará `ou=cu-dir-01`.
- `gov.upeu` **lleva punto** → cae al `else` y publicará `ou=gobierno-universitario`.

Ninguna de las dos resuelve ningún `departmentNumber`, así que no aportan a InOut, pero **sí
crean entradas nuevas en el directorio**. Es el mismo mecanismo que produce los `area.*` que
InOut reportó aparte.

Se aceptan tal cual: son unidades reales del árbol y su publicación es coherente. Si más
adelante se quiere que resuelvan por número, es un cambio de `identifier` — y eso **gobierna
el DN**, con la advertencia del rector de que el conector **no sabe renombrar**.

## Riesgos

- **12 entradas nuevas** en `ou=org` de golpe. Mitigación: canario con `RECTORADO` antes del
  resto.
- **Conflicto de DN**: `ou=692,ou=16` y `ou=713,ou=113` siguen dando `Found conflicting
  existing object`. Es un problema independiente (OUs anidadas cuyo shadow se regenera
  huérfano) y no afecta a estas 12, cuyos DN son planos y libres — verificado: ninguna de
  las 8 tiene hoy entrada en LDAP.
- **Reversible**: retirar el `inducement` deja de proyectar. Las entradas creadas
  permanecerían (el conector **no tiene `DeleteCapability`**), lo que habría que limpiar a
  mano si se revierte.

## Verificación

1. Verificador de invariantes **antes** — última corrida: **6/6 ✅**, 191 orgs.
2. Simulación `preview` del cambio en el archetype.
3. Canario: `RECTORADO` → debe aparecer `ou=3,ou=org` con `description: Rectorado`.
4. Las 11 restantes.
5. Verificador **después**: 6/6.
6. Cierre: personas sin unidad resoluble por debajo de 274 (esperado ~155).
7. Regenerar la baseline en el mismo commit, citando este ADR.


---

## Resultado de la ejecución (14-ago-2026)

**Simulación previa:** 12 orgs `governance`, 0 con proyección, **0 colisiones de DN** sobre
los 12 destinos calculados uno a uno.

**Canario `RECTORADO`** — exactamente lo previsto:

```
dn: ou=3,ou=org,dc=upeu,dc=edu,dc=pe
ou: 3
description: Rectorado
```

**Las 11 restantes:** `progress 11 | success`, sin un solo error.

### Las 12 en el directorio

| DN | description |
|---|---|
| `ou=1` | Asamblea Universitaria |
| `ou=2` | Consejo Universitario |
| **`ou=3`** | **Rectorado** |
| `ou=4` | Vicerrectorado de Bienestar Universitario |
| `ou=5` | Vicerrectorado Académico |
| `ou=6` | Vicerrectorado Administrativo |
| `ou=23` | Secretaría General |
| `ou=24` | Dirección de Planificación y Gestión de la Calidad |
| `ou=65` | Asesoría Legal |
| `ou=66` | Auditoría Interna |
| `ou=cu-dir-01` | Dirección General |
| `ou=gobierno-universitario` | Gobierno Universitario |

Las dos excepciones se comportaron como el ADR predijo: `cu-dir-01` publicó por su
identifier y `gov.upeu` —con punto— cayó al `else` y publicó por nombre.

### Métrica de cierre

| | Inicio de la jornada | Tras ADR-060 + import | **Tras ADR-061** |
|---|---|---|---|
| Unidades en `ou=org` | 104 | 155 | **163** |
| Códigos sin resolver | 50 | 21 | **13** |
| **Personas sin área** | **1.033** | 274 | **160** |

**873 personas recuperan su unidad** en el aforo del CRAI.

**Verificador de invariantes: 6/6 ✅** antes y después. 191 orgs, sin cambios estructurales
(este ADR añade proyecciones, no nodos).

### Lo que queda fuera

Los 13 códigos restantes: `20`, `68`, `69`, `70`, `97`, `695`, `8208` son de
`archetype-org-academic-unit` y `research-center` —fuera de este ADR por decisión explícita—
y `819`, `2219`, `4342`, `7867`, `7996`, `7997` pertenecen a otras entidades o no cumplen el
filtro del feed (ver ADR-060).

Sigue abierto, e independiente, el conflicto de DN de `ou=692,ou=16` y `ou=713,ou=113`.
