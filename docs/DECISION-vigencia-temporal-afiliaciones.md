# DECISIÓN CANÓNICA — Vigencia temporal por afiliación

**Estado:** RATIFICADA (validada vs ISO 24760 + eduPerson + libro Semančík/Evolveum, 2026-06-04)
**Ámbito:** cómo el IGA UPeU modela la vigencia de toda afiliación (académica y laboral) y deriva atributos dependientes de campus/sede/lifecycle.
**SSOT:** este documento.

---

## 1. Enunciado canónico

> **Toda afiliación se modela como un assignment con su ventana de vigencia (`activation/validFrom/validTo`) poblada desde las fechas autoritativas de la IIA (inicio y fin de clases/contrato). Aplica a TODOS los escenarios —pregrado, posgrado, CEPRE, centro de idiomas, conservatorio, colegio, contrato docente/trabajador.**
>
> **La vigencia NO se filtra en el origen (no `WHERE FECHA_FIN >= SYSDATE`): el origen trae el horizonte completo de interés CON sus fechas, y MidPoint —vía Validity Scanner— desactiva ordenadamente cada afiliación al expirar, deprovisionando de forma graceful y dejando audit trail (ISO 27001 A.5.16/A.5.18).**
>
> **Los atributos derivados (`campusStudent`, `campusWorker`, `locality`, home library Koha, `lifecycleState`) se computan SOLO desde assignments con `effectiveStatus=enabled`. Las afiliaciones expiradas EXISTEN pero NO aportan.**
>
> **Para multi-sede / multi-escenario, los atributos de gating son multivalor por tipo de afiliación (`campusStudent` separado de `campusWorker`), agregando todos los campus de afiliaciones enabled del tipo correspondiente.**

---

## 2. Por qué NO filtrar la vigencia en el origen (la trampa)

`WHERE FECHA_FIN >= SYSDATE` en el searchScript reintroduce el **bug de datos huérfanos** ya sufrido con el filtro `ID_ENTIDAD=7124`:

- *"MidPoint always adds, it never subtracts"* (`midpoint-best-practices` §2.6). Si una afiliación deja de llegar al feed, MidPoint recibe **ausencia**, no una instrucción de remoción.
- La remoción por ausencia es frágil (depende de reaction `deleted` + recompute) y deja valores pegados (`campusStudent=JULIACA`, `locality`, costCenter) — el mismo zero-set que ya documentamos.

Con `validTo` el dato **sigue presente pero MidPoint sabe que expiró** → desactiva la construction → deprovisiona ordenado → audit log. Deprovisioning por instrucción explícita, no por ausencia. **No genera huérfanos.**

---

## 3. Arquitectura canónica (2 capas, responsabilidades separadas)

| Capa | Responsabilidad | Qué hace |
|---|---|---|
| **searchScript (Oracle resource)** | Scope de población + horizonte | Trae afiliaciones del horizonte (semestres relevantes, contratos del scope) **incluyendo recién terminadas**. Expone `FECHA_FIN`/`FEC_TERMINO` como atributo del shadow. NO filtra `>= SYSDATE`. El filtro de semestre (`IN (267,279,283)`) queda como **límite de horizonte**, NO como criterio de vigencia. |
| **MidPoint inbound + `assignmentTargetSearch`** | Materializar vigencia | Crea el assignment de campus/org/rol con `<activation><validTo>{FECHA_FIN}</validTo>` poblado desde la fecha de la IIA. Único punto de verdad temporal. |
| **Validity Scanner (task de sistema)** | Expiración en tiempo real | Desactiva assignments al cruzar `validTo`, dispara recompute, deprovisiona graceful, deja audit. No espera a la próxima recon. |
| **Object templates (derivación)** | Atributos derivados | `campusStudent`/`campusWorker`/`locality`/`lifecycleState` se computan agregando SOLO assignments con `effectiveStatus=enabled` (filtro nativo MidPoint, no reimplementado en Groovy). |

---

## 4. Caso testigo: Critsi (código 202613369)

Dos matrículas en Oracle:
- Sem **267 Regular 2026-1** → Ing. Industrial / **Lima** → fin **2026-07-03** → VIGENTE
- Sem **279 Verano 2026-0** → Cepre Regular / **Juliaca** → fin **2026-03-01** → TERMINÓ

Bug: el feed trató los 3 semestres del `IN` como vigentes → arrastró Juliaca (CEPRE terminada) → Koha home library = BUJ → no le prestan libros en Lima.

Fix canónico: poblar `validTo` desde `FECHA_FIN` de cada matrícula. Sem 279 → `validTo` pasado → assignment `disabled` → no aporta Juliaca. Sem 267 → enabled → aporta Lima. Resultado: `campusStudent=LIMA`, locality LIMA, Koha → BUL. **Sin tocar el filtro de semestres ni el gate Koha.**

---

## 5. Multi-sede / multi-escenario

- Multi-afiliación concurrente es canónica (eduPerson §3.2): estudiante-Lima + docente-Juliaca, pregrado + idiomas, etc.
- `campusStudent` y `campusWorker` son **ejes independientes** — uno no contamina al otro.
- Si hay varias afiliaciones enabled del mismo tipo en campus distintos → el atributo de gating es **multivalor** (no se elige un "primario" arbitrario). El gate Koha `campusStudent contains 'LIMA'` ya lo cubre.
- El gate Koha multi-campus (tarea #65) es **correcto y no se toca**; solo se corrige la fuente de `campusStudent`.

---

## 6. Fundamento normativo (citas ancla)

- **ISO 24760-1** — lifecycle temporal `enrolled→established→active→suspended→archived→destroyed` (`iga-canonical-standards` §1.2).
- **MidPoint `activation` multidimensional** (`validFrom/validTo/effectiveStatus`) en foco Y assignment (`midpoint-best-practices` §1.3, glosario §8).
- **Reality vs Policy** — assignment=policy, el motor reconcilia reality; "MidPoint always adds, it never subtracts" (§2.1, §2.6).
- **`assignmentTargetSearch` soporta validity nativo** (§4.2, §4.3).
- **eduPerson §3.2/§3.3** — multi-afiliación concurrente; afiliación primaria = rol presente, no historia.
- **ISO 27001 A.5.16/A.5.18** — audit trail de provisioning/deprovisioning (`iga-canonical-standards` §7).
- **Lifecycle desde HR/SIS, no manual** (`iga-canonical-standards` §1.3, §11 reglas 6-7).

---

## 7. Implicancias de implementación

1. Cada feed (estudiantes, trabajadores, posgrado, CEPRE, idiomas, conservatorio, colegio, egresados) expone su `FECHA_FIN`/`FEC_TERMINO` y la materializa como `validTo` del assignment correspondiente.
2. Los inbounds que escriben `campusStudent`/`campusWorker`/`locality` deben condicionarse a `effectiveStatus=enabled` del assignment fuente.
3. Verificar que el Validity Scanner está activo y con periodo adecuado.
4. Orden de despliegue: estudiantes primero (canary Critsi → BUL), luego dimensionar y extender al resto de escenarios.

---

## 8. Historial
- **2026-06-04** — Principio enunciado por J. A. Sánchez (DTI/Infra UPeU) a raíz del caso Critsi (CEPRE Juliaca terminada contaminando home library Koha). Validado doctrinalmente vs `iga-canonical-standards` + `midpoint-best-practices` + libro Semančík. Ratificado con corrección de modelado clave: vigencia vía `validTo` + Validity Scanner, NO filtro en searchScript (evita bug de huérfanos del filtro 7124).
