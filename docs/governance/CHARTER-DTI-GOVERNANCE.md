# Charter — Programa de Gobierno y Calidad de TI (DTI/OTI)

> **Documento de alcance — Fase 0**
> Proyecto: Auditoría y optimización M365 como piloto del SGSI
> Fecha: 2026-06-16 · Estado: BORRADOR para revisión de David Urquizo
> Repo: `UPeU-Infra/midPointEcosystem` · Ruta: `docs/governance/`

---

## 1. Propósito

Posicionar al área de TI (DTI en UPeU; **OTI** en universidades estatales) para
**certificarse en gobierno y calidad de TI**, tomando la **auditoría de Microsoft 365
como caso piloto demostrable**.

El piloto M365 no es un fin en sí mismo: es la **primera evidencia operativa** de un
programa más amplio de gobierno de TI. El objetivo declarado del programa es alcanzar una
**certificación reconocida** que alinee a la oficina de TI con el ecosistema de
licenciamiento (SUNEDU), gobierno digital y protección de datos del Estado peruano.

## 2. Hallazgo de fondo (corrige supuesto inicial)

> No existe una "certificación SUNEDU" ni una ISO que se mapee 1:1 al licenciamiento
> universitario. SUNEDU es **licenciamiento** y SINEACE es **acreditación** — ninguno
> certifica al área de TI ni exige ISO 27001 explícitamente.

La certificación que **sí alinea a la oficina de TI con todo el ecosistema de auditoría**
es **ISO/IEC 27001 (SGSI)**, por la cadena de obligaciones legales verificada
(ver `ANEXO-NORMATIVO-PERU.md`):

| Tipo de universidad | Origen de la obligación de SGSI |
|---|---|
| **Estatal (OTI)** | Obligación **directa**: DL 1412 + DS 029-2021-PCM (art. 105 SGSI) + NTP-ISO/IEC 27001:2022 (Res. 003-2023-PCM/SGTD) |
| **Privada (UPeU)** | Obligación **indirecta** vía: Ley 29733 + DS 016-2024-JUS (datos personales), DS 126-2025-PCM (servicios educativos digitales), Ley 30096 (responsabilidad penal) |

En ambos casos **ISO/IEC 27001 es el estándar técnico que satisface todas las
obligaciones de forma articulada**. Para UPeU es adopción voluntaria pero documentada;
para una estatal es cumplimiento legal — lo que hace de este programa un **producto
SciBack replicable a universidades estatales**.

## 3. Arquitectura de certificación

```
COBIT 2019  ───────────── backbone de gobierno (une los dominios en un modelo medible)
ISO/IEC 38500  ────────── gobierno corporativo de TI
     │
     ├── ISO/IEC 27001 (SGSI)   ← ANCLA de certificación
     │       ├── ISO/IEC 27017  (controles de seguridad cloud / M365)
     │       ├── ISO/IEC 27018  (protección de PII en la nube)
     │       └── ISO/IEC 27701  (extensión de privacidad → Ley 29733)
     │
     └── ISO/IEC 20000-1 (ITSM) ← 2da ola: calidad de servicio de TI (GLPI, capacidad)
```

**Recomendación (pendiente de ratificación):** certificar **ISO/IEC 27001 primero**
(satisface las obligaciones legales y es el referente que cualquier auditor reconoce),
con **ISO/IEC 20000-1** como segunda ola para "calidad de servicio". COBIT 2019 como
columna vertebral de diseño.

> El piloto M365 produce evidencia directa del **Anexo A.8 de ISO 27001** (gestión de
> activos) y de la **gestión de capacidad de ISO 20000-1** — no es trabajo aparte.

## 4. Marco de la auditoría

La auditoría se ancla a estándares para que sea defendible y reutilizable como evidencia
de certificación (no un Excel ad-hoc):

| Referencia | Rol en la auditoría |
|---|---|
| **ISO 19011** | *Metodología*: cómo se conduce la auditoría (plan, evidencia, hallazgos, no conformidades) |
| **COBIT 2019** | *Qué* objetivos de gobierno se evalúan (APO06 costos, BAI09 activos, APO13 seguridad, DSS01 operación) |
| **ISO 27017 / 27018 / CSA CCM** | *Controles cloud/M365* específicos (datos en la nube, PII, retención) |

## 5. Mapa de madurez de gobierno DTI (los 8 dominios)

| # | Dominio | Estado UPeU | Norma / marco |
|---|---|---|---|
| 1 | **Identidad (IGA)** | ✅ Operativo (MidPoint) | ISO 24760, NIST 800-63 |
| 2 | **Datos** | 🔄 En camino (VocBench, catálogos INEI/SUNEDU) | DAMA-DMBOK, ISO 38505, ISO 8000 |
| 3 | **Seguridad de la información (ISMS)** | ❌ Gap | **ISO/IEC 27001** + 27017/27018 |
| 4 | **Servicios TI (ITSM)** | 🟡 Parcial (GLPI) | **ISO/IEC 20000-1** (ITIL 4) |
| 5 | **Costos / cloud (FinOps)** | ❌ Gap ← **piloto M365** | COBIT APO06, FinOps Framework |
| 6 | **Activos y configuración (CMDB)** | ❌ Gap | ISO 19770, COBIT BAI09 |
| 7 | **Riesgo y continuidad (BCP/DRP)** | ❌ Gap | ISO 22301, ISO 27005 |
| 8 | **Privacidad** | 🟡 Implícito | Ley 29733 + DS 016-2024-JUS, ISO 27701 |

## 6. Alcance del piloto M365

### 6.1 Objetivo del ahorro

Cuantificar en S/. la brecha entre **lo que se paga** y **lo que se usa**, atacando
cuatro fugas:

| Fuga | Señal técnica | Fuente Graph |
|---|---|---|
| Licencias en cuentas muertas | `signInActivity.lastSignIn` > 90/180 días | `AuditLog.Read.All` |
| Seats pagados sin asignar | `prepaidUnits` vs `consumedUnits` por SKU | `subscribedSkus` |
| Sobre-dimensionado (A3/A5/Copilot a quien usa A1) | uso real por servicio | `Reports.Read.All` |
| Bajas no ejecutadas (deuda técnica) | `enabled=true` sin afiliación viva en Oracle/MidPoint | cruce con foco MidPoint |

> UPeU es tenant **Education**: A1 es gratis; A3/A5 y Copilot son pagados. El ahorro real
> está en A3/A5/Copilot mal asignados, no en A1.

### 6.2 Cuotas de almacenamiento por perfil

**No existe norma (ISO ni ley peruana) que dicte GB por usuario.** El método defendible:

1. **Base estadística propia:** vía `Reports.Read.All` → `getOneDriveUsageAccountDetail`
   + `getMailboxUsageDetail` → `storageUsedInBytes` por usuario, segmentado por categoría
   (estudiante / docente / administrativo / egresado, usando el archetype de MidPoint).
   Calcular **percentiles p50 / p90 / p95**. Cuota propuesta = **p95 + headroom**, no el
   default de Microsoft (buzón A1 = 50 GB; OneDrive hasta 1 TB).
2. **Respaldo normativo del *método* (no del número):**
   - **ISO/IEC 20000-1 §8.3.3** — gestión de capacidad (dimensionar a demanda real).
   - **Ley 29733 + DS 016-2024-JUS** — principio de **minimización**: no retener datos
     más allá de lo necesario → justifica cuotas ajustadas + política de retención
     (purgar data de egresados tras N años).
   - **FinOps** — eficiencia de costo.

## 7. Permisos Microsoft Graph requeridos

App de conector (read-only, admin-consent del Global Admin):

| Permiso Graph | Para qué | ¿Lo tenemos? |
|---|---|---|
| `User.Read.All` | Usuarios | ✅ App MidPoint (`94dd7b5b`) |
| `Group.Read.All` | Grupos | ✅ App MidPoint |
| `Directory.Read.All` | `subscribedSkus`, directorio | ✅ App MidPoint |
| `AuditLog.Read.All` | `signInActivity` (cuentas muertas) — **crítico** | ❌ Falta |
| `Reports.Read.All` | Reportes de uso por servicio + almacenamiento | ❌ Falta |
| `Application.Read.All` | Enterprise Apps / service principals | ❌ Falta |
| `Policy.Read.All` | Conditional Access / políticas | ❌ Falta |

**Decisión pendiente (David Urquizo):** ¿app dedicada nueva read-only (recomendado:
least-privilege, aislada del IGA PROD) o extender la app de MidPoint? Los 4 permisos
faltantes requieren su admin-consent.

## 8. Fases

| Fase | Entregable | Bloqueo |
|---|---|---|
| **0 — Charter y marco** | Este documento + anexo normativo | — (en curso) |
| **1 — Inventario** | SKUs, usuarios, grupos, cruce archetypes MidPoint | Permisos actuales (✅) |
| **2 — Uso real** | Cuentas muertas, uso por servicio, percentiles de almacenamiento → cuotas | 4 permisos nuevos |
| **3 — Apps y políticas** | Enterprise Apps, SP huérfanos, Conditional Access | `Application.Read.All`, `Policy.Read.All` |
| **4 — Informe de auditoría** | Hallazgos ISO 19011/COBIT, ahorro en S/., roadmap de certificación | Fases 1–3 |

## 9. Métricas de éxito

- **Ahorro identificado** en S/. (licencias A3/A5/Copilot recuperables).
- **% de cuentas con licencia y sin login** > umbral (90/180 d).
- **% de seats pagados sin asignar** por SKU.
- **Cuotas de almacenamiento propuestas** por categoría con base p95.
- **Nº de no conformidades** detectadas vs controles ISO 27001 Anexo A.
- **Nivel de madurez COBIT** (línea base) de los 8 dominios.

## 10. Decisiones pendientes

1. **App Graph** — dedicada vs extender MidPoint → David Urquizo.
2. **Target de certificación** — ISO 27001 primero (recomendado) vs 20000-1 vs ambas.
3. **Umbral de inactividad** para "cuenta muerta" (90 vs 180 días).
4. **Política de retención** para egresados (input para cuotas).

---

*Referencias normativas verificadas contra fuentes primarias en
[`ANEXO-NORMATIVO-PERU.md`](ANEXO-NORMATIVO-PERU.md).*
