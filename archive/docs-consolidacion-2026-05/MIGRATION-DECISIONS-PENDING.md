# MIGRATION-DECISIONS-PENDING — Consolidación 2026-05-19

Decisiones que **NO** estaban explícitamente en `AUDIT-CONSOLIDATION-2026-05-19.md` §6/§7 y se tomaron por el ejecutor con criterio de skills. Requieren confirmación de Alberto antes de marcarlas como definitivas.

---

## 1. `midpoint-project.yaml` — re-targeted, no mencionado en audit

**Situación:** El archivo `midpoint/midpoint-project.yaml` (config de `ninja` para deploy) apuntaba al árbol viejo (`./archetypes`, `./org`, `./policies`, etc.). El audit no lo menciona.

**Decisión tomada:** Movido a la raíz `midPointEcosystem/midpoint-project.yaml` con `sources:` actualizado para listar las carpetas `canonical/*` + `upeu/*`. Versión subida a `2.0.0`, midpointVersion a `4.10.*` (post-upgrade).

**Riesgo:** Si alguien usa `ninja` desde el contenedor MidPoint y este archivo se interpreta automáticamente, podría intentar deploy. **No bloquea PROD** (ninja en PROD no se ejecuta automáticamente).

**Acción pendiente:** Confirmar si Alberto quiere conservar el yaml o eliminarlo (en cualquier caso, el deploy a PROD se hace vía REST API selectivo).

---

## 2. Archetypes "missing" detectados — repo no tenía los 8 archetypes-user que el audit cita

**Audit §3.1 dice:** "5 versionados" (employee-faculty, employee-staff, alumni, partner-institution, researcher), pero el repo solo tenía 4 user-archetypes en `midpoint/archetypes/`:
- `archetype-user-student.xml` ✓
- `archetype-user-employee-faculty.xml` ✓
- `archetype-user-employee-staff.xml` ✓
- `archetype-user-alumni.xml` ✓
- (FALTAN en repo: `affiliate-partner-institution`, `affiliate-researcher`, `contractor`, `service-account`)

**Decisión tomada:** Movidos los 4 existentes a `canonical/archetypes/user/`. Los 4 faltantes **NO** se crearon (no hay material origen).

**Acción pendiente cuando PROD vuelva:** descargar desde REST los XMLs reales de los archetypes:
- `archetype-user-affiliate-partner-institution`
- `archetype-user-affiliate-researcher`
- `archetype-user-contractor`
- `archetype-user-service-account`

y commitearlos a `canonical/archetypes/user/`.

---

## 3. Archetypes "extra" en repo no listados en audit

Archetypes que SÍ estaban en el repo pero el audit no los menciona explícitamente:

- `archetype-person.xml` → movido a `upeu/archetypes/custom/` (decisión: parece archetype base UPeU, probablemente custom).
- `archetype-position.xml` → movido a `upeu/archetypes/custom/` (Pilar PBAC, UPeU-specific Ley 30220).
- `archetype-affiliation-role.xml` → movido a `upeu/archetypes/custom/` (parece meta-archetype para R-Affiliation-*; revisar).
- `archetype-org-academic-program.xml` → movido a `canonical/archetypes/org/` (academic-program es concepto canónico — `eduPersonOrgUnitDN` candidato).

**Acción pendiente:** Revisar los 3 archetypes `upeu/archetypes/custom/` y confirmar si:
(a) `archetype-position` debe canonicar (Position-Based Access Control aparece en skill `midpoint-best-practices` como pattern) o quedarse como UPeU-specific.
(b) `archetype-affiliation-role` es redundante con `R-Affiliation-*` (los 6 birthright roles) — posible deprecation.
(c) `archetype-person` es base de los 4 user-archetypes — verificar via `superArchetypeRef`.

---

## 4. Org-archetypes canónicos faltantes en repo

**Audit §6.3 dice:** Los 8 archetypes-org existen en PROD (`institution`, `campus`, `faculty`, `department`, `academic-unit`, `governance`, `partner-institution`, `project`) pero NO están versionados en `midPointEcosystem`. Solo se versionaba `archetype-org-academic-program`.

**Decisión tomada:** Movido `archetype-org-academic-program` a `canonical/archetypes/org/org-academic-program.xml`. Los 8 faltantes NO se crearon.

**Acción pendiente post-OOM:** Descargar desde REST los XMLs reales de los 8 `archetype-org-*` y commitearlos a `canonical/archetypes/org/`. OIDs reales están en PROD `m_archetype`.

---

## 5. Roles MOF-* y GOV-* no presentes en repo

**Audit §1.1 dice:** PROD tiene ~25 MOF-* y 3 GOV-* roles. **Repo solo versiona affiliation/application/business** (6+20+12 = 38 roles). **Faltan los MOF + GOV en el repo.**

**Decisión tomada:** Crear carpetas vacías `upeu/roles/{mof,governance,system}/` para receptación futura.

**Acción pendiente post-OOM:** Para cada `MOF-*` y `GOV-*` en PROD, descargar XML vía REST y commitearlo. Mismo para `SYS-IGA-SUPERUSER` si no está versionado.

---

## 6. `aux-affiliation-*` vs `R-Affiliation-*` — redundancia detectada por skill

**Audit §3.4 y §5.2 detectan:** 4 `aux-affiliation-*` (auxiliary archetypes multivalor) coexisten con 6 `R-Affiliation-*` (birthright roles). Skill `midpoint-best-practices` §3.3 advierte: *"Auxiliary archetype soporte UI limitado en 4.9 — se recomienda birthright roles en su lugar."*

**Decisión tomada:** Los 4 aux movidos a `upeu/archetypes/auxiliary/` (NO `canonical/`). Decisión final de deprecation **se aplaza** (no se borran, ya están asignados a usuarios reales en PROD).

**Acción pendiente:** Proyecto separado post-consolidación: validar si se pueden retirar los 4 `aux-affiliation-*` y dejar solo los 6 birthright `R-Affiliation-*` como fuente de verdad de la afiliación canónica.

---

## 7. Conector `openstandia/connector-keycloak v1.1.7-SNAPSHOT` huérfano en PROD

**Audit §1.1 detecta:** Conector instalado en PROD `m_connector` pero **sin Resource asociado** (verificación: no hay Resource Keycloak en PROD, `a3f9c1d2-...` no existe en `m_resource`).

**Decisión tomada:** No tocar PROD. Anotado para uninstall post-OOM.

**Acción pendiente post-OOM:** Verificar que ningún role del repo referencia `openstandia/connector-keycloak` y desinstalarlo de PROD vía REST API connector uninstall.

---

## 8. Cómo se ubican los `R-Affiliation-*` (canonical o upeu)

**Audit §5.2 dice:** *"R-Affiliation-* inicialmente en `upeu/` — evaluar mover a `canonical/roles/` post-consolidación. Vocabulario es canónico (eduPerson), pero implementación R-Affiliation-Student.xml actual contiene logic UPeU."*

**Decisión tomada:** Movidos a `upeu/roles/affiliation/`. NO se promueven a `canonical/`.

**Acción pendiente:** Inspeccionar cada `R-Affiliation-*.xml`. Si la "logic UPeU" es solo `displayName/description` localizada y los inducements son agnósticos (apuntan a archetypes canonical/), entonces se pueden refactor a `canonical/roles/affiliation/` con override en `upeu/`.

---

## 9. Posición del HTML `arquitectura.html` (legacy del repo padre)

**Audit §7.4 dice:** *"Diagrama parcialmente obsoleto … REESCRIBIR post-consolidación."*

**Decisión tomada:** Copiado como `docs/arquitectura-legacy.html` (sufijo `-legacy` deja claro que necesita reescritura). El vigente sigue siendo `docs/arquitectura-entraid-iga.html`.

**Acción pendiente:** Reescribir el diagrama oficial UPeU con la realidad post-consolidación (2 schemas + 18 archetypes + 7 resources + PBAC Pilar 3 + foto híbrida + dual-archetype).

---

## 10. Repo GitHub `SciBack/midpoint` — archivado vs eliminado

**Audit §6.8 paso 23 sugiere:** `gh repo delete SciBack/midpoint --confirm`.

**Mandato de Alberto (turno actual):** *"El repo GitHub `SciBack/midpoint`: **NO lo borres todavía**. Solo borra la carpeta local. El repo GitHub se archiva más adelante con `gh repo archive` cuando Alberto confirme."*

**Decisión tomada:** Pendiente. Se documenta como acción posterior. Solo se borra la copia local.

**Acción pendiente:** Cuando Alberto confirme, ejecutar:
```bash
gh repo archive SciBack/midpoint --yes
```
(`archive`, no `delete`, para preservar historia).
