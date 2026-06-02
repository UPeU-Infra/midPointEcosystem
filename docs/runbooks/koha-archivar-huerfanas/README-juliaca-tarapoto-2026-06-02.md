# Archivado Koha — cuentas JULIACA + TARAPOTO (gate "Koha solo Lima")

**Fecha:** 2026-06-02
**Decisión:** Koha gobernado por MidPoint = SOLO campus LIMA (branchcode BUL).
Juliaca (BUJ) y Tarapoto (BUT) salen del alcance del IGA. LDAP/Entra ID/M365
SIGUEN siendo multi-campus — NO se tocan.

## Qué hizo MidPoint

1. **Gate de campus** (`upeu/resources/koha-ils.xml`, commit `085e62d`):
   existence + administrativeStatus de Koha se abstienen SOLO para
   `locality IN ('JULIACA','TARAPOTO')`. **LIMA y locality=NULL SIGUEN
   pasando** (los 4,578 NULL se clasifican aparte; un NULL podría ser de
   Lima → deprovisionarlo sería destructivo).
2. **Unlink/borrado de shadow lado MidPoint** (task
   `unlink-koha-no-lima.xml`, OID `b8d3f1a2-...`): borró del repo de MidPoint
   los shadows Koha de los 6,657 foci JULIACA+TARAPOTO. Esto **NO tocó Koha**
   (operación repo-level, sin connector). El patrón en Koha sigue intacto.

## Lista para koha-expert

`koha-cardnumbers-juliaca-tarapoto-2026-06-02.csv` — **6,657 cuentas**.

| Columna | Significado |
|---|---|
| `cardnumber` | **Criterio de archivado.** Es el `__NAME__` del shadow Koha = cardnumber/userid del patrón. Identificador canónico. |
| `focus_locality` | Sede del foco MidPoint (JULIACA / TARAPOTO). |
| `branchcode_shadow_informativo` | branchcode leído del shadow (BUJ/BUT aquí). **NO usar como criterio**: el branchcode en Koha es engañoso (muchos no-Lima quedaron en BUL). Solo informativo. |
| `borrowernumber_guess` | Heurística (mayor número del shadow). **No confiable** — koha-expert debe resolver el borrowernumber por `cardnumber` en Koha, no por este guess. |
| `shadow_oid` | OID del shadow MidPoint (trazabilidad; ya borrado del repo). |

### Distribución
- JULIACA: 4,770 (branchcode shadow = BUJ)
- TARAPOTO: 1,887 (branchcode shadow = BUT)

## Acción para koha-expert

Archivar (NO borrar duro si hay historial) estas cuentas en Koha vía
`delete_patrons.pl` (o el flujo de `deletedborrowers`), **matcheando por
`cardnumber`** (columna 1), NO por branchcode.

## Garantías

- Oracle LAMB: solo lectura. No se tocó.
- LDAP / Entra ID / M365: intactos (multi-campus).
- Foci LIMA: Koha intacto. Foci locality=NULL: Koha PRESERVADO.
- `cardnumber-outbound` sigue weak.
