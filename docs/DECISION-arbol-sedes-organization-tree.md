# Decision Record — Árbol de sedes en el Organization Tree (dimensión sede, UPeU / SciBack-IGA)

**Estado:** APROBADO, pendiente de ejecución · **Fecha:** 2026-08-05 · **Decisor:** Alberto Sánchez
**Contexto de origen:** auditoría del canal Trabajadores del 4-ago-2026 (validación área↔Oracle 2.322/2.322) + gap analysis contra el libro de MidPoint + revisión de conformidad con `dw-olap`.

**Esta es la única fuente de verdad sobre cómo se modela la dimensión sede/campus en el IGA.** El diseño anterior (campus como nodos intermedios del árbol funcional con colegios colgando) queda superseded por este DR al ejecutarse la Fase 3.

---

## 1. Veredicto (resumen ejecutable)

| Concepto | Valor canónico | NO es | Fundamento |
|---|---|---|---|
| Dimensión sede | **Árbol organizacional paralelo** con raíz propia `Sedes UPeU`, sincronizado desde `ELISEO.ORG_SEDE` | NO nodos intermedios del árbol funcional; NO solo un atributo | Libro MidPoint cap. 10 *Multiple Organizational Structures*; Kimball (dimensión conformada) |
| Clave de la org sede | `identifier = ID_SEDE` (1/2/3) — inmutable | **NO el nombre** ("Filial Juliaca" puede renombrarse) | Libro: *"Always use organizational unit identifiers"*; DL 1412 regl. art. 10.b (identificador único); Kimball (natural key estable) |
| Alcance | **Solo `ID_SEDE IN (1,2,3)`**: Sede Lima, Filial Juliaca, Filial Tarapoto | NO ISTAT (4), NO Clínica Good Hope (5), NO AGTU (6) — entidades jurídicas distintas | Decisión de Alberto 2026-08-05; Ley 29733 art. 7 (proporcionalidad) |
| Pertenencia persona→sede | `assignment` a la org sede vía `assignmentTargetSearch` en los object templates de empleado, buscando por `identifier = ID_SEDE` | NO mapping ad-hoc en el resource; NO reemplaza a `campusWorker` | Libro cap. 9 (pipeline inbound→template); §4.3 de la skill |
| `campusWorker` (ext 220) | **Se conserva** como atributo conformado (LIMA/JULIACA/TARAPOTO) | NO se elimina — LDAP, Koha (gate BUJ/BUT) y el DW lo consumen | Coincide con `dim_sede.sede_codigo` de dw-olap |
| Intersección sede×área | **Se consulta** (dos pertenencias del user), no se materializa | NO nodos combinados "EP X — Juliaca" | 149 áreas son multi-sede en `ORG_SEDE_AREA` → explosión de nodos |
| Manager de sede | `assignment` a la org con `relation=manager` | **NO atributo "manager" en el user** (anti-pattern explícito del libro) | Libro cap. 10 *Managers*; ISO 27001 A.5.1/A.5.2 |
| Colegios/ISTAT/CRAI (5 nodos hoy bajo campus) | Se mueven al árbol funcional bajo nodo nuevo `Unidades Adscritas` | NO se quedan bajo los campus — son unidades funcionales, no lugares | Separación de dimensiones funcional vs geográfica |

**Regla transversal que este DR fija:** *clave sobre el identificador inmutable de la fuente, nunca sobre el nombre*. Es la misma regla en las tres tradiciones que gobiernan este producto: libro de MidPoint (identificadores persistentes), Kimball (dimensiones conformadas), DL 1412 regl. art. 10.b (identificador único). Aplica también al DW: `dim_sede` debe re-clavarse sobre `ID_SEDE` (tarea entregada a la sesión de dw-olap; hallazgo: su SK actual se genera sobre `sede_nombre`).

---

## 2. Contrato de conformidad IGA ↔ DW (Kimball)

Una sola fuente autoritativa, dos consumidores, mismas claves:

| Concepto | Fuente autoritativa | Clave inmutable | Código conformado | MidPoint | dw-olap |
|---|---|---|---|---|---|
| Sede | `ELISEO.ORG_SEDE` | `ID_SEDE` | LIMA / JULIACA / TARAPOTO | org `identifier=ID_SEDE` + `campusWorker` | `dim_sede.sede_codigo`; `fct_resultado_indicador` ámbitos `Sede`/`ProgramaSede` |
| Área | `ELISEO.VW_AREA` | `ID_AREA` | — | org `identifier=ID_AREA` ✅ **validado 2.322/2.322 el 4-ago** | `dim_docente_area.id_area` |
| Persona | `ELISEO.VW_APS_EMPLEADO` | `ID_PERSONA` | — | `extension/lambIdPersona` | `dim_docente_area.docente_id` |

Nota de coherencia deliberada: `dim_sede` del DW **sí** incluye ISTAT (aparece en landings de postulantes) mientras este árbol no lo incluye. No es desalineamiento: el DW reporta hechos históricos; el IGA gestiona accesos vigentes de personal UPeU. Nadie debe "corregir" uno para que se parezca al otro.

---

## 3. Estructura objetivo

### Árbol funcional (existente — cambio mínimo)

Intacto salvo un movimiento: los 5 hijos actuales de los nodos campus pasan a un nodo nuevo:

```
Universidad Peruana Unión [UPeU]
├─ Gobierno Universitario → … (sin cambios; validado contra Oracle el 4-ago)
└─ Unidades Adscritas                          ← NUEVO
   ├─ Colegio Unión [AREA-97]
   ├─ Colegio Adventista del Titicaca [AREA-695]
   ├─ Colegio Unión - Tarapoto [AREA-8208]
   ├─ ISTAT [AREA-760]
   └─ Dirección del CRAI [DIR-CRAI-LIMA]
```

### Árbol de sedes (nuevo — raíz propia, pestaña propia)

```
Sedes UPeU  «archetype-org-sede»
├─ SEDE-1   identifier=1  · Sede Lima       · tipo=Sede
├─ SEDE-2   identifier=2  · Filial Juliaca  · tipo=Filial
└─ SEDE-3   identifier=3  · Filial Tarapoto · tipo=Filial
```

Convención de nombres (libro cap. 10): `name` = técnico único (`SEDE-{ID_SEDE}`), `identifier` = clave inmutable (`ID_SEDE`), `displayName` = legible (NOMBRE de `ORG_SEDE`).

Los 3 nodos `OU-CAMPUS-*` existentes **se reutilizan** (mismo OID; se les añade `identifier` y se reubican bajo la raíz nueva). No se borran ni se recrean: menos deltas, se preserva historia.

Cada trabajador termina con **dos pertenencias**: su área (árbol funcional) y su sede (árbol nuevo). Réplica exacta del par `ID_SEDEAREA` que `VW_TRABAJADOR` ya usa como unidad real.

### Qué habilita (hoy imposible navegando)

| Pregunta | Hoy | Con este DR |
|---|---|---|
| ¿Quién trabaja en EP Ing. Civil? | ✅ | ✅ árbol funcional |
| ¿Quién trabaja en Juliaca? | solo filtrando atributo | ✅ árbol de sedes |
| ¿Quién es de Ing. Civil en Juliaca? | ❌ | ✅ intersección de pertenencias |
| ¿Quién es responsable de la Filial Juliaca? | ❌ (12 managers en toda la universidad) | ✅ `relation=manager` sobre SEDE-2 |

---

## 4. Plan de ejecución — 6 fases

| # | Qué | Cómo | Riesgo / gate |
|---|---|---|---|
| **0** | **Calidad del dato en la fuente** (Ley 29733 art. 8): (a) `campusWorker='CIA'` en 1 persona — valor fuera de catálogo; (b) 6 vigentes sin `ID_SEDE`/`ID_AREA` en Oracle; (c) **los 63 shadows congelados desde el 25-jul** (73 vigentes sin afiliación) | Corrección en Oracle/RRHH, NO en mappings (*garbage in, garbage out* — libro, HR Feed Recommendations) | Bloqueante parcial: (c) debe resolverse antes de la Fase 2 o el árbol nace con datos del 25-jul |
| **1** | Crear `archetype-org-sede` (estructural, display propio) + raíz `Sedes UPeU` + objectType `generic/sede` (`kind=generic`, `focus=OrgType`, `archetypeRef`) en el resource `Oracle LAMB Org`, leyendo `ORG_SEDE` con filtro `ID_SEDE IN (1,2,3)`. Reutilizar los 3 `OU-CAMPUS-*` (añadir `identifier`, reubicar bajo la raíz) | Generic synchronization (libro cap. 10 §5.6) — las orgs nacen de la fuente, no de XML manual. **Resources: solo PATCH, nunca PUT** | Bajo — objetos nuevos, ninguna persona tocada |
| **2** | Item sobre `assignment` en `UserTemplate-EmployeeStaff` y `UserTemplate-EmployeeFaculty` con `assignmentTargetSearch` por `identifier = ID_SEDE` (el dato ya viaja en la consulta canónica). Conditions relativistas → un traslado Lima→Juliaca muda el assignment solo | Pipeline canónico inbound→template (libro cap. 9) | **Simulación `preview` obligatoria** — recompute de ~2.400 users. Leer resultados desde `fullobject` de `m_simulation_result_processed_object`, NUNCA con JOIN a `m_shadow` (trampa documentada 3×) |
| **3** | Crear `Unidades Adscritas` y mover los 5 nodos; verificar grafo acíclico después | Org hierarchy con assignments (nunca inducements) | **Simulación previa** — `parentOrgRef` de ~91 personas; RIMS/InOut/Pulso DTI podrían leerlo |
| **4** | Nombrar managers: assignment con `relation=manager` sobre SEDE-2, SEDE-3 y áreas priorizadas | Patrón canónico del libro; alimenta el compliance dashboard (mark `Unowned`, ISO 27001 A.5.1/A.5.2) | Bajo — assignments aditivos |
| **5** | Verificación doble: (a) nominal Oracle↔MidPoint por `ID_SEDE`, persona por persona, **meta 100%** (mismo método que validó áreas); (b) conteo por sede del árbol = ámbito `Sede` del `fct_resultado_indicador` para docentes — dos sistemas leyendo la misma clave deben dar el mismo número | Medir, no razonar | Solo lectura |

### Referencia de estado al momento de este DR (medido 4-ago-2026)

- `campusWorker` trabajadores activos: LIMA 1.509 · JULIACA 614 · TARAPOTO 231 · 6 sin campus · 1 `CIA`.
- Oracle vigentes por sede: Lima 1.606 · Juliaca 633 · Tarapoto 245 (la brecha son los 73 sin afiliación).
- 52 orgs funcionales tienen personal de más de una sede (p. ej. DTI: 40/18/7) → confirma que la sede NO puede ser rama del árbol funcional.
- 33 trabajadores activos sin ninguna org (~27 sin explicación en fuente).

---

## 5. Encuadre legal (honesto)

- **DL 1412 (Ley de Gobierno Digital) + DS 029-2021-PCM**: obligan a la Administración Pública, **no** a UPeU como universidad privada. Se adoptan como **marco de referencia** del producto (`gobierno-digital-universitario`): identificador único (regl. art. 10.b), atributos otorgados por la entidad autoritativa (art. 10.2 — Oracle LAMB es el registro autoritativo interno), interoperabilidad por estándares (arts. 26-28 — eduPerson/SCHAC ya en uso).
- **Ley 29733 (Protección de Datos Personales)**: obliga directamente. Finalidad (art. 6) y proporcionalidad (art. 7) → solo se materializan las orgs necesarias para la gestión de accesos (no las 811 áreas de Oracle; no las sedes de terceros). Calidad (art. 8) → Fase 0 es requisito legal, no cosmética. Seguridad (art. 9) → Fase 4 (responsables identificables por unidad).

---

## 5.bis 🔴 CORRECCIÓN tras el intento de ejecución de Fase 1 (2026-08-05)

**La especificación de la clave en §1 está REFUTADA por la ejecución. No aplicar tal cual.**

Al cambiar `identifier` de los 3 campus (`SEDE-LIMA` → `SEDE-1`) se descubrió en vivo que:

1. **El `identifier` de un OrgType está acoplado al DN de su OU en LDAP.** El DN se deriva de él:
   `identifier=SEDE-LIMA` → `ou=sede-lima,ou=org,dc=upeu,dc=edu,dc=pe`. Cambiar el identifier
   **no es un cambio de metadato: es un renombrado en el directorio**.
2. **El conector LDAP no soporta rename** (ya conocido para `ou=people`/`ou=alumni`; aplica igual
   a `ou=org`). MidPoint no renombró: **creó `ou=sede-1` nueva** y dejó `ou=sede-lima` con sus
   7 hijos (`ou=cu-admin`, `cu-admin-sec`, `cu-admin-tes`…). Juliaca y Tarapoto fallaron con
   `FATAL_ERROR` y sus OUs originales quedaron intactas.
3. **Toda org proyecta OU a LDAP**: crear la raíz `SEDES-UPEU` generó `ou=sedes-root` sin que se
   hubiera previsto. Una raíz meramente organizativa no debería proyectarse.
4. Colisión ya evitada antes de ejecutar: `identifier` desnudo (1/2/3) choca con `ID_AREA` 1/2/3
   (Asamblea / Consejo / Rectorado) en el filtro `identifier = ID_PARENT`. Por eso NO se usó.

**Rediseño correcto de la Fase 1:** la clave inmutable de correlación va en
**`extension/upeu:sedeId` (= `ID_SEDE`)**, y el correlator del resource `Oracle LAMB Sedes`
apunta a ese ítem. **`identifier` NO se toca** — queda con su valor semántico actual, porque
gobierna el DN de una OU que ya está poblada y consumida por RIMS. Se cumple igual la regla
"clave sobre el identificador inmutable": solo cambia dónde vive esa clave.

Corolario general, más allá de las sedes: **en este despliegue, `identifier` de OrgType es un
dato de provisioning, no una etiqueta libre.** Cualquier cambio sobre él es una operación de
directorio y exige simulación previa.

## 6. Qué NO se decidió aquí (pendientes conexos)

1. Los 63 shadows congelados del 25-jul: causa sin determinar; ver memoria `trabajadores-73-vigentes-sin-afiliacion-2026-08-04`.
2. Los 33 activos sin org (~27 sin explicación en fuente).
3. Extender el árbol de sedes a estudiantes/egresados (`campusStudent`, ext 219) — mismo patrón, decisión aparte.
4. Re-clavado de `dim_sede` en dw-olap — prompt entregado, se ejecuta en esa sesión.
