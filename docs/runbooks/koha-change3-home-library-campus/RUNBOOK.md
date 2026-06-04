# Change 3 — home library Koha derivada del campus vivo (no de locality crudo)

Fecha: 2026-06-04
Commit del mapping: `c165d27` (feat(koha): Change 3 — branchcode deriva de campusStudent ?: campusWorker ?: locality)
Resource: `upeu/resources/koha-ils.xml`, mapping `library-id-outbound` (OID resource `9b5a7c81-47aa-42ac-9a08-4de8b64935af`)

## Decisión canónica
`docs/DECISION-vigencia-temporal-afiliaciones.md` §5: `campusStudent`/`campusWorker` = eje IIA vivo (vigencia de afiliación); `locality` = lugar físico / fallback (libre para LDAP/Entra/M365).

## Mapping (exacto, vive en koha-ils.xml ~L1191)
Precedencia: `campusStudent ?: campusWorker ?: locality`.
Mapa: `LIMA->BUL, JULIACA->BUJ, TARAPOTO->BUT, CIA->CIA, ICA->CIA`; default conservador `BUL`.
Multivalor: si `campusStudent` contiene LIMA -> LIMA (precedencia determinista, coherente con el gate multi-campus que solo provisiona Lima hoy).
strong + 3 sources (campusStudent, campusWorker, locality).

## Branches Koha verificados (koha_bul.branches)
BUL = Biblioteca CRAI UPeU Lima · BUJ = Juliaca · BUT = Tarapoto. Los 3 existen.
Gate de existence Koha (tarea #65) hoy solo crea cuenta a vínculo vivo LIMA; el mapping ya emite el branchcode correcto cuando entren BUJ/BUT al IGA.

## Canary (GATE) — 4/4 PASS
| Caso | cardnumber | campus | Koha antes | Koha después | Esperado | Resultado |
|---|---|---|---|---|---|---|
| Flip (student) | 202511593 Sandoval Llanos | campusStudent=LIMA | BUJ | BUL | BUL | PASS (flip) |
| Juliaca-legit (student) | 201811287 Mara Quispe | cs/loc=JULIACA | BUJ | BUJ | BUJ | PASS (no flip) |
| Lima student | 202613369 Critsi Chavarria | campusStudent=LIMA | BUL | BUL | BUL | PASS (estable) |
| Worker Lima | 10867326 Sanchez Condor (DTI) | campusWorker=LIMA | BUL | BUL | BUL | PASS (estable) |

## Mecanismo de propagación
PATCH `?options=reconcile` no-op (replace `c:telephoneNumber` sin valor) -> dispara clockwork + outbound Koha.
El `partial_error` por `UPEU-EntraID-Graph` (CreateCapability missing, resource `2f11c057...`) es RUIDO ESPERADO (Entra inbound-only/proposed) y NO afecta Koha.

## Masivo
Universo de diagnóstico inicial: 260 borrowers BUJ/BUT con focus MidPoint resoluble a eff-campus.
- 85 ya estaban BUL (recomputes previos) + 1 canary = 86.
- 174 procesados por reconcile serializado (script `/tmp/run_masivo.sh` en PROD).

Resultado tras reconcile (campusStudent es VOLÁTIL — se re-materializa por vigencia DENSE_RANK LAST de Change 1):
- **81** resolvieron eff-campus = LIMA -> deben ser BUL. **49 quedaron BUL** (flip OK).
- **93** resolvieron eff-campus = JULIACA/TARAPOTO (re-materializados no-Lima) -> correctamente NO flipearon (67 BUJ + 26 BUT). INVARIANTE: 0 wrongly-flipped.
- **32 LIMA bloqueados** por errores fatales de clockwork PRE-EXISTENTES, ajenos a Change 3:
  - 30: LDAP dual-shadow ("Projection ACCOUNT already exists in lens context" — uid=DNI vs uid=código en `ou=people,dc=upeu`).
  - 1: `studyLevel` single-valued con dos valores (Idiomas+Pregrado).
  - 1: `lambDocNum` strong con dos valores (CE:007867814 vs 07867814).
  Estos 32 flipearán solos cuando se sanee el dual-shadow LDAP / los conflictos de inbound (workstream identifier-canónico, fuera de Change 3).

## Verificación final Koha
- 260 universo: BUL 135 / BUJ 86 / BUT 39.
- Invariante no-Lima: los 93 eff-no-Lima -> 100% en BUJ/BUT (0 a BUL).
- Canary: 4/4 estables/correctos.
- Global: 14,240 borrowers, **0 cardnumber duplicados**; flips fueron updates in-place (no se crearon cuentas).

## Conclusión
Mapping Change 3 correcto y probado. Lo que NO flipeó es por (a) campus que legítimamente NO es Lima al recompute, o (b) bloqueos de datos pre-existentes (LDAP dual-shadow / inbound single-valued). Ningún Juliaca/Tarapoto legítimo ni trabajador Lima se rompió. Invariante "campus vivo LIMA -> BUL" se cumple para todo focus cuyo clockwork puede commitear.
