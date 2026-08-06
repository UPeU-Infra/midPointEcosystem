# Estado del árbol organizativo — cierre de jornada 2026-08-06

**Medido en vivo al cierre.** Complementa [`ARQUITECTURA-ARBOL-ORGANIZATIVO.md`](ARQUITECTURA-ARBOL-ORGANIZATIVO.md)
(documento rector) y [`HALLAZGO-managers-org-fuente-oracle-2026-08-06.md`](HALLAZGO-managers-org-fuente-oracle-2026-08-06.md).

---

## 1. Estado verificado

| Medida | Valor | Nota |
|---|---|---|
| **Personas en LDAP** | **75.793** | ✅ intactas toda la jornada |
| Orgs en MidPoint | **175** | de 353 al inicio (se limpiaron 178 `LINEA-*`) |
| Verificador del árbol | **6/6 invariantes** | único aviso: 7 `CII-*` |
| Rama de sedes | **212 assignments** | Lima/Juliaca/Tarapoto pobladas |
| OUs de campus en LDAP | **3/3 enlazadas** | `sede-lima`, `sede-juliaca`, `sede-tarapoto` |
| OUs bajo las sedes | **1 / 0 / 0** | desde 42/14/6 en el peor momento |
| OUs totales en `ou=org` | 106 | eran 30 al inicio — **requiere inventario** |
| linkRefs rotos | 8 | eran 0 antes de la Fase 1 |
| Orgs sin shadow de OU | 78 | mezcla de legítimas y pendientes |

## 2. Lo que se completó hoy

1. **Limpieza CRIS 2ª pasada** — 763 shadows huérfanos + 178 orgs `LINEA-*` borrados con backup.
   PROD: 353 → 175 orgs.
2. **2.854 linkRefs rotos de usuarios** eliminados (artefacto de la migración del 19-may).
3. **Relink de las 3 OUs de campus** — receta documentada (discovery + `PATCH add linkRef`).
4. **Limpieza quirúrgica de los 2 archivos mixtos** — 32 orgs retiradas; `KNOWN_PENDING` vacía.
5. **6 roles `R-Affiliation-*` versionados** (drift de un mes) y **3 orgs `EP-*`** incorporadas.
6. **Documento rector + baseline + verificador** de 6 invariantes.
7. **Rama de sedes poblada** — 212 assignments desde `ORG_SEDE_AREA`, excluyendo la espina
   institucional (Asamblea, Rectorado, VRs, facultades no cuelgan de un campus).
8. **Corrección del DN** — archetype campus retirado de las **dos** listas `OU_ARCH`
   (resource `7b4e1c2d` v222 → **v224**).

## 3. Pendientes, por prioridad

### 🔴 P1 — Higiene de la Fase 1 (deuda creada hoy)

| # | Qué | Detalle |
|---|---|---|
| 1.1 | **Inventariar las 106 OUs** de `ou=org` contra las 175 orgs | Eran 30 al inicio. Decidir cuáles son legítimas (orgs que ahora sí se proyectan) y cuáles sobran. **Hacer esto ANTES de borrar nada.** |
| 1.2 | 8 linkRefs rotos + shadows de OU sin owner | Residuo del lote de 41. Patrón conocido: `PATCH ?options=raw`. |
| 1.3 | `ou=cu-admin` bajo `sede-lima` | Único hijo que queda bajo una sede; impidió el borrado accidental de esa OU. |
| 1.4 | 4 OUs bajo `ou=16`/`ou=58` | Deuda **previa**, no de hoy. ⚠️ En `ou=51` y `ou=53` son la ÚNICA OU de su org. |

### 🟡 P2 — Decisiones de negocio (no técnicas)

| # | Qué |
|---|---|
| 2.1 | **7 orgs `CII-*` con 310 personas** — último resto del CRIS; exige reubicación antes de tocar |
| 2.2 | **Managers `org:manager`** — BLOQUEADO: falta regla de Talento Humano sobre quién es el titular en `ORG_AREA_RESPONSABLE` (421 grupos con más de un responsable) |
| 2.3 | **16 orgs `EP *` funcionales (546 docentes)** vs las 26 `EP-*` académicas — fusionar o separar por archetype |
| 2.4 | Los 2 RDN duplicados restantes (`ou=54`, `ou=67`) |

### 🟢 P3 — Fuera del árbol

Ver `HALLAZGO-programas-academicos-vocbench`: paso 1 (quitar `'P'||CODIGO_SUNEDU`, 9.367
identidades) y paso 3 (regenerar el puente) siguen abiertos.

## 4. Reglas nuevas aprendidas hoy (ya en el documento rector y en memoria)

1. **El DN de las OUs es JERÁRQUICO**, no plano: se construye apilando los ancestros cuyo
   archetype esté en `OU_ARCH`. Ver un DN de muestra NO prueba que sea plano.
2. **El conector LDAP SÍ mueve** (cambio de padre); lo que **no** sabe es **renombrar** el RDN.
   Son cosas distintas: el incidente del 5-ago fue lo segundo.
3. **HTTP 240 y 250 son "handled error" de MidPoint** — 2xx que no significan éxito ni fracaso.
   **La verdad se comprueba en Postgres, nunca en el código HTTP.**
4. **Las orgs multi-sede generan un shadow por sede** → la sede no puede estar en el DN.
5. **La reconciliación de `generic/ou` NO recalcula el DN** (simulado: 150 objetos, 0 cambios).
   Mover OUs exige recompute del FOCO.
6. **Un `LIKE '%ou=sede-%'` casa también con `ou=sede-lima` misma.** Anclar los filtros de DN al
   componente correcto y **revisar la lista antes de ejecutar un lote**.
