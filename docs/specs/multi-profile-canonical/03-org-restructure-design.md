# 03 — Re-estructuración del árbol organizacional: UPeU + Colegio Unión

**Fecha:** 2026-05-14
**Instancia:** midpoint-prod (192.168.15.166), MidPoint 4.9.5
**Decisión doctrinal previa (Juan Alberto Sánchez Condor, 2026-05-14):**
> *"Colegio Unión como una organización separada a UPeU."*

Este documento materializa esa decisión bajo `iga-canonical-standards` y `midpoint-best-practices`.

Skills consultadas: `iga-canonical-standards` §1.2 (lifecycle), §1.3 (IIA), §4.2 (`schacHomeOrganization`), §10.2 (OrgType archetypes); `midpoint-best-practices` §5.2 (org tree design — acyclic), §5.3 (tipos canónicos), §5.4 (Role hierarchy ≠ Org hierarchy), §5.5 (managers), §6 (10 reglas de oro).

---

## 1. Decisión de topología — Dos institutions hermanas sin raíz común

### 1.1 Opciones evaluadas

| Opción | Descripción | Pros | Contras | Veredicto |
|---|---|---|---|---|
| **A. Raíz común** `ASOCIACION-EDUCATIVA-ADVENTISTA-PERU` que contiene `UPeU` y `COLEGIO-UNION` como children institutions | Modela la red IASD-Educación como agrupador | Refleja propietario corporativo común; gobierno futuro centralizable | Persona jurídica "Asociación Educativa Adventista del Perú" NO existe como entidad legal única en Perú (UPeU pertenece a la red IASD vía División Sudamericana; Colegio Unión es operado por la Asociación Peruana Central). Crear un nodo administrativo sin entidad jurídica viola el principio de **fidelidad a la realidad** (ISO 24760-1 §3.1.2). Además contamina `schacHomeOrganization`: cada institución debe tener el suyo y un nodo padre no aporta valor SAML. | Rechazada |
| **B. Dos institutions hermanas independientes** (cada una raíz de su propio sub-árbol, sin parent común) | `UPeU` y `COLEGIO-UNION` ambos `archetype-org-institution`, ambos sin `parentOrgRef` | Refleja realidad jurídica peruana; cada institución es IIA de su propio dominio; `schacHomeOrganization` único por institución (SCHAC §6); soporta ePSA scoped distinto por dominio (`student@upeu.edu.pe` vs `student@colegiounion.edu.pe`); Evolveum permite múltiples árboles paralelos (best-practices §5.2: *"As long as it is an acyclic directed graph it will work just fine"*). Las personas con afiliación dual (un docente que da clases en ambos) reciben **un único focus con dos `parentOrgRef`** — uno a cada institution — y dos `eduPersonScopedAffiliation` derivados. | Requiere que `Person` correlator detecte multi-org (ya implementado en spec `multi-profile-canonical` §2.6: `externalSystemId` multi-valued y correlator tier-based por `taxId`). | **Elegida** |
| C. Mover Colegio Unión bajo UPeU como `partner-institution` | Mantiene una sola raíz | Trata Colegio Unión como subordinado a UPeU — incorrecto: no es proveedor de UPeU, es institución hermana propia. Bajaría `schacHomeOrganization` a un nivel donde se confundiría con sub-org de UPeU. | Contradice decisión doctrinal explícita "organización separada". | Rechazada |

### 1.2 Justificación canónica de la opción B

1. **ISO 24760-1 §3.1.2** — *"identity is the representation of an entity in a particular domain"*. UPeU y Colegio Unión son **dominios de identidad distintos**. Aunque puedan compartir personas (afiliación dual), cada dominio tiene su propio identity register, su propia IIA y su propio set de atributos autoritativos.
2. **SCHAC 1.6.0 §6** — `schacHomeOrganization` es el FQDN DNS administrativo. Cada institución usa un FQDN distinto (`upeu.edu.pe`, presumiblemente `colegiounion.edu.pe`). Un nodo padre artificial NO puede tener un `schacHomeOrganization` válido propio, y tampoco puede sustituir el de las hijas (asignar `iasdperu.org` haría que SAML SPs como Scopus reciban un home org que no existe en sus listas de licencia).
3. **midpoint-best-practices §5.2** — *"Multiple parallel trees are supported. The only restriction is acyclic directed graph."* Dos árboles paralelos (uno por institución) es el patrón canónico para multi-tenancy con dominios independientes.
4. **REFEDS R&S §8.1** — Los SPs académicos (Scopus, EBSCO, Web of Science) verifican `schacHomeOrganization` contra su lista de licencias. Cada institución licencia por separado; mezclarlos provocaría bypass de licencia o denegación de acceso.
5. **midpoint-best-practices §5.4** — *"Privileges of Sales and Marketing Division are not included in Indirect Sales Department"* (org hierarchy NO hereda privilegios). Un nodo padre artificial no aportaría herencia útil — cada institución diseña sus propios birthright roles.

### 1.3 Topología elegida (estado objetivo Fase 3)

```
UPeU [institution]                                    schacHomeOrganization=upeu.edu.pe
├── DIR-GENERAL-CAMPUS [department]
│   ├── DIR-GENERAL-CAMPUS-JULIACA, ...-LIMA, ...-TARAPOTO
│   └── DIR-INSTITUTO-SUPERIOR
├── GOBIERNO-UNIVERSITARIO [governance]
│   └── (RECTORADO, VR-*, FACULTAD-*, etc.)
├── OU-CAMPUS-JULIACA / LIMA / TARAPOTO [campus]
├── P-AGTU [partner-institution]
├── P-CGH  [partner-institution]
└── P-ISTAT [partner-institution]
                                                      ─── árboles independientes ───
COLEGIO-UNION [institution]                           schacHomeOrganization=colegiounion.edu.pe (TBD verificar)
└── DIR-COLEGIO-LIMA [academic-unit]                  ← migrado desde UPeU.DIR-GENERAL-CAMPUS-LIMA
    (children internos: Inicial/Primaria/Secundaria — diferidos a 2da iteración)
```

**Nota intencional:** los nodos `P-AGTU`, `P-CGH`, `P-ISTAT` permanecen bajo UPeU como `partner-institution` porque son **proveedores/aliados** de UPeU (no instituciones hermanas con dominio propio). No se migran en este ejercicio.

---

## 2. Decisiones complementarias

### 2.1 Archetype para Colegio Unión

**`archetype-org-institution`** (OID `455d90ab-b54a-4aa7-a402-a6b6ffc0c0d9`) — el mismo que UPeU.

Justificación: ambas son instituciones educativas formales con dominio DNS propio. No requiere archetype nuevo. Reutilizar fortalece la consistencia y reduce mantenimiento (1 archetype = 1 set de policies, autorizaciones e inducements canónicos).

### 2.2 `schacHomeOrganization` — dónde vive

**Hallazgo del schema v3.0:** `schacHomeOrganization` está definido en `SPEC-v3.md` como **constante derivada en outbound** (`upeu.edu.pe` hardcoded), NO como atributo persistido en OrgType. Esto era válido bajo la asunción de raíz única; deja de serlo con dos institutions.

**Decisión:**

1. **Corto plazo (Fase 3 actual):** poblar el `identifier` de cada `institution` con el FQDN. UPeU.identifier = `upeu.edu.pe`, COLEGIO-UNION.identifier = `colegiounion.edu.pe` (TBD). Esto cumple `midpoint-best-practices §5.2` (*"Always use organizational unit identifiers if you can. We really mean it."*) y deja la fuente de verdad lista para outbound futuros.
2. **Mediano plazo (Fase 6 OpenLDAP/Keycloak):** la outbound expression que pueble `schacHomeOrganization` en LDAP recorrerá `parentOrgRef` del focus hasta encontrar el primer ancestro con archetype `archetype-org-institution` y leerá su `identifier`. Ya NO será una constante hardcoded — será una función de resolución de árbol. Esto soporta nativamente la afiliación dual (un docente con `parentOrgRef` a ambas institutions emitirá dos `schacHomeOrganization` o uno por SP destino según política).
3. **Largo plazo opcional:** si el outbound necesita búsqueda eficiente, considerar agregar `extension/upeu3:schacHomeOrganization` a OrgType como cache. Diferido — actualmente `identifier` basta.

### 2.3 Nombre y `displayName` de UPeU institution

UPeU root actual NO tiene `displayName` ni `identifier` (verificado vía REST). Aprovechar este cambio para poblarlos:

- `name`: `UPeU` (mantener, es el identificador técnico)
- `displayName`: `Universidad Peruana Unión`
- `identifier`: `upeu.edu.pe`
- `extension`: vacía por ahora

### 2.4 Estructura interna de Colegio Unión

**Diferida a 2da iteración** (decisión Juan Alberto). En esta iteración solo se crea:
- `COLEGIO-UNION` (institution) — raíz del árbol
- Migrar `DIR-COLEGIO-LIMA` como hijo directo

Niveles educativos (Inicial/Primaria/Secundaria), sedes adicionales (Juliaca/Tarapoto si aplica), facultades simbólicas — **TBD para Juan Alberto**.

### 2.5 Migración de `DIR-COLEGIO-LIMA`

**Verificación previa de impacto (ya ejecutada, 2026-05-14):**

```sql
-- Children de DIR-COLEGIO-LIMA: 0
-- Assignments hacia DIR-COLEGIO-LIMA: 0
-- Total focuses afectados: 0
```

El nodo está completamente aislado. **Decisión: re-parentear in-place** (cambiar `parentOrgRef` de `DIR-GENERAL-CAMPUS-LIMA` a `COLEGIO-UNION`). **NO recrear, NO borrar.** Razones:
- Preserva OID (`00000000-0000-0000-0000-240999814505`) → idempotencia con cualquier referencia futura
- 0 focuses afectados → cero riesgo
- Operación atómica vía un solo PATCH REST

El archetype permanece como `academic-unit` por ahora (Juan Alberto puede recategorizar a `campus` o desglosar en niveles educativos en la 2da iteración).

### 2.6 Implicaciones para roles (referencia, NO se ejecuta aquí)

Los BR canónicos actuales (`BR-Docente-TC`, `BR-Estudiante-Pregrado`, etc.) son UPeU-céntricos. Para Colegio Unión se requerirán BRs análogos en una fase futura (`BR-Docente-Colegio`, `BR-Estudiante-Inicial`, etc.) **o** roles paramétricos (best-practices §2.5). Esta decisión queda fuera del alcance de la Fase 3 actual y se aborda cuando Juan Alberto pueble los internals de Colegio Unión.

---

## 3. Plan de ejecución (PROD)

### Fase 2 — Verificaciones previas (COMPLETADA 2026-05-14)

| Check | Resultado |
|---|---|
| Children directos de `DIR-COLEGIO-LIMA` | **0** |
| Assignments hacia `DIR-COLEGIO-LIMA` (cualquier tipo) | **0** |
| Tareas de sync activas que usen DIR-COLEGIO-LIMA | Ninguna (los 3 resources Oracle no referencian este OID) |
| Roles con `assignmentRelation`/`inducement` que dependan de la jerarquía actual | Ninguno (auditoría 02 confirmó: 0 BR/AR usa `assignmentRelation` ni `inducement` cruzado a orgs) |
| Archetype `archetype-org-institution` existe y disponible | OID `455d90ab-b54a-4aa7-a402-a6b6ffc0c0d9` ✓ |

**Veredicto:** riesgo nulo. Procede ejecución.

### Fase 3 — Cambios atómicos en PROD

| # | Acción | Método | Reversible |
|---|---|---|---|
| 3.1 | Crear `COLEGIO-UNION` [institution] como raíz independiente | REST POST `/orgs` | Sí (DELETE) |
| 3.2 | PATCH `UPeU` → setear `displayName=Universidad Peruana Unión`, `identifier=upeu.edu.pe` | REST PATCH | Sí |
| 3.3 | PATCH `COLEGIO-UNION` → setear `identifier=<FQDN-TBD>`, `displayName=Colegio Unión` | REST PATCH | Sí |
| 3.4 | PATCH `DIR-COLEGIO-LIMA` → eliminar `parentOrgRef` actual, agregar `parentOrgRef → COLEGIO-UNION` | REST PATCH (delete+add atómico) | Sí |

**NO se hace:** crear children internos de Colegio Unión, modificar archetype de DIR-COLEGIO-LIMA, tocar partners (P-AGTU/P-CGH/P-ISTAT), recompute masivo, import full.

### Fase 4 — Verificación post-cambio

```sql
-- Conteo: debe pasar de 91 → 92 orgs
SELECT count(*) FROM m_object WHERE objecttype='ORG';

-- Topología: debe haber 2 institutions sin parent
SELECT o.nameorig, COALESCE(p.nameorig,'(root)')
FROM m_object o
LEFT JOIN m_ref_object_parent_org po ON po.ownerOid=o.oid
LEFT JOIN m_object p ON p.oid=po.targetOid
WHERE o.objecttype='ORG' AND o.oid IN (
  SELECT ownerOid FROM m_ref_archetype WHERE targetOid='455d90ab-b54a-4aa7-a402-a6b6ffc0c0d9'
);

-- DIR-COLEGIO-LIMA debe colgar de COLEGIO-UNION
SELECT p.nameorig FROM m_ref_object_parent_org po
JOIN m_object p ON p.oid=po.targetOid
WHERE po.ownerOid='00000000-0000-0000-0000-240999814505';
```

Verificar también vía MidPoint UI: árbol Org renderiza dos raíces.

---

## 4. Bloqueante TBD para Juan Alberto

**Confirmar antes de ejecutar paso 3.3:**

> **¿Cuál es el FQDN DNS oficial del Colegio Unión?**
> Hipótesis: `colegiounion.edu.pe`. Verificar con DNS/dig o pregunta directa al área TI/comunicaciones del colegio.
> Si distinto, usar el correcto. Si aún no se tiene FQDN propio, dejar `identifier=COLEGIO-UNION` (placeholder) y abrir TODO en F3 del reporte previo.

Este FQDN definirá el `eduPersonScopedAffiliation` de todas las personas afiliadas al Colegio Unión y será el `schacHomeOrganization` que reciban los SPs federados (cuando exista federación para Colegio Unión).

---

## 5. Próximos pasos (fuera de alcance de esta iteración)

Una vez aplicada la re-estructuración:

1. Juan Alberto define internals de Colegio Unión (sedes + niveles educativos)
2. Continuar con plan F1-F8 del reporte 02 (poblar `schacHomeOrganization` en TODAS las orgs si se decide persistir como extension; corregir duplicación campus, modelar EAPs bajo facultades, vincular focuses a orgs vía `parentOrgRef`, eliminar BR legacy)
3. En Fase 6 (OpenLDAP/Keycloak), implementar la outbound expression que deriva `schacHomeOrganization` recorriendo `parentOrgRef` hasta el ancestro con archetype `institution`

---

## Anexo A — OIDs relevantes

| Objeto | OID | Tipo |
|---|---|---|
| UPeU root | `00000000-0000-0000-0000-497211782216` | Org [institution] |
| DIR-COLEGIO-LIMA | `00000000-0000-0000-0000-240999814505` | Org [academic-unit] |
| DIR-GENERAL-CAMPUS-LIMA (parent actual de DIR-COLEGIO-LIMA) | (consultar) | Org [department] |
| archetype-org-institution | `455d90ab-b54a-4aa7-a402-a6b6ffc0c0d9` | Archetype |
| archetype-org-academic-unit | (consultar al ejecutar) | Archetype |
| COLEGIO-UNION | `a4971f45-6317-473d-b89a-93aae41c8c3a` | Org [institution] (NUEVO, creado 2026-05-14) |
| DIR-GENERAL-CAMPUS-LIMA (parent ANTERIOR de DIR-COLEGIO-LIMA) | `3766918c-7f9b-48eb-80fa-0dfb7a392470` | Org [department] |

---

## Anexo B — Resultado de ejecución (2026-05-14)

| Paso | Estado | Detalle |
|---|---|---|
| 3.1 Crear COLEGIO-UNION | ✓ HTTP 201 | OID `a4971f45-6317-473d-b89a-93aae41c8c3a` |
| 3.2 PATCH UPeU (displayName + identifier) | ✓ HTTP 204 | `Universidad Peruana Unión` / `upeu.edu.pe` |
| 3.3 (consolidado en 3.1) — `identifier=colegiounion.edu.pe` se incluyó en el POST | ✓ | Verificado en m_org |
| 3.4 Re-parentar DIR-COLEGIO-LIMA | ✓ HTTP 204 | Vía swap de assignment id=15 (delete+add). Primer intento falló con `parentOrgRef` directo (correcto: la jerarquía Org se gobierna por assignments según best-practices §5.2, no por parentOrgRef directo) |

### Verificación post-cambio (SQL)

| Métrica | Valor |
|---|---|
| Total orgs | 92 (era 91, +1 COLEGIO-UNION) ✓ |
| Institutions con archetype `archetype-org-institution` | 2: `UPeU`, `COLEGIO-UNION` ✓ |
| Parent de DIR-COLEGIO-LIMA | `COLEGIO-UNION` ✓ |
| `UPeU.identifier` | `upeu.edu.pe` ✓ |
| `COLEGIO-UNION.identifier` | `colegiounion.edu.pe` (confirmado vía DNS: dominio activo, MX Google Workspace) ✓ |
| Focuses con `parentOrgRef` huérfano | 0 ✓ |

### FQDN Colegio Unión — verificación

`dig NS colegiounion.edu.pe` → `ns.rcp.net.pe`, `ns2.rcp.net.pe` (registrador histórico de `.edu.pe`)
`dig MX colegiounion.edu.pe` → 5x records de `*.aspmx.l.google.com` (Google Workspace activo)

Conclusión: dominio operacional confirmado del Colegio Unión. `schacHomeOrganization=colegiounion.edu.pe` es válido cuando la federación SAML llegue a ese ámbito.
