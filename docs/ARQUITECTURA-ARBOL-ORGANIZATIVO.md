# Arquitectura del árbol organizativo UPeU — documento rector

**Estado:** VIGENTE · aprobado por Alberto el 2026-08-06
**Valida contra:** *Practical Identity Management with MidPoint* (Semančík/Evolveum, rev 2.3), cap. 10
**Supersede:** el §3 de [`DECISION-arbol-sedes-organization-tree.md`](DECISION-arbol-sedes-organization-tree.md) (el resto de ese ADR sigue vigente) y el árbol manual archivado en `archive/orgs-arbol-manual-2026-08-06/`
**Blindaje ejecutable:** [`upeu/scripts/verificar-arbol-organizativo.py`](../upeu/scripts/verificar-arbol-organizativo.py) + [`docs/baselines/arbol-organizativo-baseline.json`](baselines/arbol-organizativo-baseline.json)

---

## 1. Decisiones, con su argumento y su respaldo en el libro

### D1 — Un solo árbol corporativo bajo la raíz `UPeU`; las sedes son una rama, no otra organización

UPeU opera de forma corporativa: sus áreas son institucionales y se despliegan en campus. La sede
es **una dimensión de la misma organización**, no una organización aparte.

```
UPeU  (raíz — OID 00000000-…, la real de PROD)
├── rama FUNCIONAL      Asamblea (1) → Consejo (2) → Rectorado (3)
│                        ├── VR Académico (5) → Facultades (8–12) → 26 EP
│                        ├── VR Administrativo (6)
│                        ├── VR Bienestar (4)
│                        └── Dirección General de Campus (430)
│                            └── Colegio Unión · Centro de Idiomas · Conservatorio · CRAI · Inst. Superior
└── rama SEDES          Campus Lima · Campus Juliaca · Campus Tarapoto
                         └── las áreas de despliegue por campus se asignan TAMBIÉN a su sede
```

**Libro:** MidPoint no exige raíces separadas ni las prohíbe — exige un grafo acíclico:
*"The structure may not even be a tree. As long as it is an acyclic directed graph it will work
just fine. It can have multiple roots, it may have alternate paths."* La forma (rama vs raíz) es
cosmética para el motor; lo que da comportamiento es el archetype (D3). Elegimos rama única por
fidelidad al modelo corporativo real de UPeU.

**Multi-parent:** que un área cuelgue de la rama funcional **y** de su sede es un "alternate path"
explícitamente permitido. La restricción única del libro: *"Just avoid cycles."*

### D2 — La estructura viene de las fuentes, jamás se dibuja a mano

| Rama | Fuente autoritativa | Mecanismo |
|---|---|---|
| Funcional | `ELISEO.ORG_AREA` (id + parent) | resource Org, generic synchronization — **ya corre** |
| Sedes | `ELISEO.ORG_SEDE` / `ORG_SEDE_AREA` | Fase 1 del ADR de sedes (clave en `extension/sedeId`, **no** en `identifier`) |
| Política (filtro) | Organigrama oficial 2026 (Res. 0001-2026/UPeU-AU) | referencia Reality-vs-Policy — no se sincroniza |

**Libro:** el capítulo *Organizational Structure Synchronization* modela exactamente esto — una
tabla con `orgnum` + `parentOrgNum` sincronizada por generic synchronization — y ridiculiza los
organigramas mantenidos a mano. El árbol manual del repo (raíz `UPeU` paralela, `Facultades`,
`Rectorado`…) nunca existió en PROD y fue archivado el 2026-08-06.

**Reality vs Policy (medido 2026-08-06):** el organigrama es lo que Calidad espera; Oracle es lo
que RRHH registra. El diff es información de gobernanza, no un error a "corregir" en MidPoint:
- Cajas del organigrama sin área en Oracle → gap que se **reporta** a Planificación/GTH.
- Áreas reales bajo el grano del organigrama (Limpieza 95 personas, Control Patrimonial 74,
  Residencias…) → **se quedan**: son donde la gente trabaja.
- Si Oracle contradice la Resolución → hallazgo de calidad de datos, se escala, no se parchea.

### D3 — El carácter lo dan los archetypes, no la posición

**Libro:** *"midPoint does not even recognize the difference between functional and project
organizational structures… If there is a need for the structures to behave differently, it has to
be explicitly configured. Which is usually done by using archetypes."*

Vigentes: `Academic-Program` (26 orgs EP-*). La rama de sedes usará su archetype de campus; las
áreas funcionales el suyo. Los archetypes retirados (p. ej. `archetype-org-research-line`) quedan
como **lápidas** en `upeu/archetypes/retired/` para integridad referencial — nunca se reactivan.

### D4 — El árbol es para gobernanza; los destinos reciben proyecciones, nunca el árbol

| Destino | Recibe | NO recibe |
|---|---|---|
| **LDAP** | atributos planos en la persona: `scibackCampusCode`, `scibackFacultyCode`, `campusWorker` (D-11.bis; los consume InOut/RIMS) | movimientos de entrada entre OUs (el conector no soporta rename) |
| **AD** | grupos de seguridad derivados de la membresía de org | una jerarquía de OUs espejo del organigrama (antipatrón) |
| **Entra ID** | grupos (no existe jerarquía de OUs en cloud) | — |

La relación árbol→destinos va en una sola dirección: del árbol se **calculan** atributos y
grupos. Ningún destino refleja la estructura. Esto habilita Conditional Access por sede, grupos
por área y certificaciones por manager sin volver a tocar el modelo.

**Regla derivada del incidente 2026-08-05:** en este entorno **toda org proyecta una OU a LDAP**
(outbound `generic/ou` en `ldap-identity-cache`). Los nodos nuevos de la rama de sedes deben
**excluirse explícitamente de ese outbound** o aceptarse su OU con decisión escrita.

### D5 — Managers como relación sobre la org

**Libro:** *"MidPoint assigns managers to organizational units. That is the right way to do it."*
El cargo viene del organigrama (política); el titular, de `posiciones.xml`/Oracle (realidad); se
materializa como assignment con `relation=org:manager`. Es requisito para certificaciones y
aprobaciones por jefe (cap. 1 y 11).

🔴 **Medido el 2026-08-06 — D5 DEPENDE DE D1, y falta una regla de negocio.** La fuente es
`ELISEO.ORG_AREA_RESPONSABLE`, pero **no es una jefatura única**: 421 grupos
`(ID_SEDEAREA, ID_NIVEL)` tienen más de un responsable (Imprenta Unión: 123). Y su grano es
**`ID_SEDEAREA`**, no `ID_AREA` — el jefe de Contabilidad en Juliaca y el de Lima colapsan hoy
sobre la misma org. **Primero la rama de sedes, después los managers.** Detalle:
[`HALLAZGO-managers-org-fuente-oracle-2026-08-06.md`](HALLAZGO-managers-org-fuente-oracle-2026-08-06.md).

### D6.bis — Las raíces `Projects` / `Teams` / `World` son del PRODUCTO, no vestigios

Intentar borrarlas devuelve `Attempt to delete indestructible object`: son **objetos iniciales de
MidPoint 4.10** (`indestructible=true`, «Root object of all projects»), creados por el upgrade.
Se conservan en `raices_permitidas` de la baseline y no se tocan — MidPoint las recrearía.

### D6 — Qué NO pertenece al árbol

- **Líneas de investigación** (`LINEA-*`) y **centros CII-***: restos del CRIS retirado el
  2026-06-20. **Limpieza ejecutada el 2026-08-06**: 763 shadows huérfanos y las 178 LINEA-*
  borrados (raw, con backup). ⚠️ Quedan las 7 CII-* con 310 personas: reubicación antes de tocar.
  Hallazgo lateral de la limpieza: **2.854 linkRefs rotos en USUARIOS** (previos, de purgas
  anteriores) — pendiente medir origen antes de limpiar.
- **Conceptos del tesauro** (programas, temas): viven en VocBench; el IGA los referencia por URI.
- **Cajas del organigrama sin realidad en RRHH**: no se fabrican orgs para complacer la política.

---

## 2. Blindaje — el contrato de cambio

La estructura NO se toca "porque parece mejor". Tres niveles:

### 🔴 INMUTABLE (no hay procedimiento válido para cambiarlo)

| Qué | Por qué |
|---|---|
| `identifier` de cualquier org | gobierna el DN de su OU; el conector LDAP no soporta rename → OU duplicada + shadow huérfano (incidente 2026-08-05). La clave inmutable de sede va en `extension/sedeId` |
| OIDs | "OIDs estables. Filename puede cambiar; OID nunca" (convención del repo) |
| La raíz `UPeU` y el conjunto de raíces | una raíz nueva = una OU nueva en LDAP sin decisión |

### 🟡 SOLO con ADR + simulación `preview` + canario + baseline regenerada

- Cambiar padres o crear/retirar **nodos estructurales** (espina, facultades, campus, EP).
- Alta de la rama de sedes (Fase 1 del ADR) y cualquier archetype de org nuevo.
- Tocar el outbound `generic/ou` del resource LDAP.
- El cambio y la regeneración de `docs/baselines/arbol-organizativo-baseline.json` van **en el
  mismo commit**, citando el ADR. Editar la baseline sin ADR = falsificar el blindaje.

### 🟢 LIBRE (lo gestiona la sincronización — son datos, no estructura)

- Altas/bajas/renombres de `AREA-NNN` desde Oracle. No se versionan (decisión 2026-08-06:
  versionarlas sería congelar datos).

### Verificación

```bash
source ~/.secrets/midpoint-upeu.env
python3 upeu/scripts/verificar-arbol-organizativo.py
```

Corre **antes y después de cualquier cambio estructural** y en cada auditoría. Protege 6
invariantes (raíces exactas, identifiers intactos, espina intacta, anti-drift repo→PROD y
PROD→repo, restos del CRIS sin crecer). Estado 2026-08-06 tras las limpiezas: **6/6 ✅**, `KNOWN_PENDING` **vacía**, `LINEA-*` en **0**
(I6 endurecida: ahora FALLA si reaparece alguna). Único aviso vivo: las 7 `CII-*` con 310
personas, pendientes de decisión de reubicación.

### Prohibiciones permanentes (lecciones pagadas)

1. **Nunca `PUT` a un resource** — arranca el `<schema>` cacheado (runbook propio).
2. **Nunca crear orgs a mano en PROD sin versionarlas** — así aparecieron EP-DER/EP-III/EP-ISW y
   los 6 roles `R-Affiliation-*` huérfanos de repo.
3. **Nunca crear conceptos/orgs desde un sistema consumidor** — así nacieron los 17 pares
   duplicados del tesauro.
4. **Source multivalor ⇒ nunca `<function>` en un mapping** — usar `<script>` (regresión
   2026-08-05).

---

## 3. Trabajo autorizado pendiente (en orden)

| # | Qué | Ampara |
|---|---|---|
| 1 | ✅ **HECHO 2026-08-06** — Limpieza CRIS 2ª pasada: 16 linkRefs desenganchados (raw), **763 shadows huérfanos y 178 LINEA-\* borrados** (backup validado en `backup-cris-20260806`). PROD: 353→175 orgs. Queda SOLO la decisión CII-\* (310 personas) | purga 2026-08-03 + memoria `lineas-investigacion-no-son-de-oracle` |
| 2 | ✅ **HECHO 2026-08-06** — 32 orgs no desplegadas retiradas a `archive/…-RETIRADAS.xml`; **`KNOWN_PENDING` VACÍA**: el repo ya no describe ninguna org inexistente | archivado 2026-08-06 |
| 3 | **Rama de sedes** (Fase 1 rediseñada: `extension/sedeId`, simulación, exclusión del outbound ou) — **bloquea el punto 4** | ADR sedes §5.bis + este doc D1/D4 |
| 4 | Managers `org:manager` — **BLOQUEADO por el 3** y por una regla de negocio de Talento Humano sobre quién es el titular | D5 + `HALLAZGO-managers-org-fuente-oracle-2026-08-06.md` |
| 5 | Decisión sobre los 16 `EP *` funcionales (546 docentes) vs las 26 EP académicas | medición 2026-08-06 |
