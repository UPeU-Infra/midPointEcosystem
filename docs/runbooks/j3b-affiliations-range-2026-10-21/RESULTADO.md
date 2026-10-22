# J3b con rango — resultado del despliegue (21-22 oct 2026)

**Desplegado.** Template `855caaca-68c4-4f7f-8ff8-b4e35dd7d390` v130 → **v131** por PATCH (`patch-01-j3b-range.json`), 22-oct ~02:33 UTC.
Verificado con GET raw: la única diferencia es `<target><set><predefined>all</predefined></set></target>` en `mapping[5790]`.

## Respaldo (en .166, `~/backups/j3b-20261021/`)
- `template-pre.xml` (v130), `template-post.xml` (v131), `affiliations-pre.tsv.gz` (54.582 usuarios), `SHA256SUMS`.
- LDAP `ou=people` (ePA/ePSA/ePPA) antes del cambio: 50.738 entradas, en el scratchpad de la sesión.

## Simulaciones (preview, configuración de producción, 50 usuarios)
- **Antes del PATCH** ya había cambios latentes ajenos a J3b: zero-set de J3 en archivados (archetype, primaryAffiliation,
  `administrativeStatus` → disabled) y, en Koha, borrado de `STUDY_LEVEL`/`STUDYCYCLE` a quien ya no tiene
  `primaryAffiliation=student` (diseño del outbound `extended-attributes-study-level-and-dni`, `tolerant=false`).
- **Después del PATCH** lo único nuevo: `affiliations` en el foco y `eduPersonAffiliation`/`eduPersonScopedAffiliation` en LDAP.

## Ejecución
| Paso | Resultado |
|---|---|
| Canario real (4) | SUCCESS; foco, LDAP .168 y .169 correctos; Koha: 2 egresados pierden STUDY_* (esperado) |
| L1 solo foco (7 trozos) | SUCCESS |
| L2 bajas con cuentas (3 trozos) | SUCCESS — 1.280 LDAP (ePA/ePSA), 968 Koha (STUDY_*), 8 archivados → disabled |
| L3 activos | Trozo 01 PARTIAL_ERROR ajeno a J3b (`secondary_email` con 2 valores, `jenson`); el resto no hizo falta: la recon diaria del 22-oct aplicó J3b a los activos |

## Medido al final (22-oct 15:00 UTC)
- `medir-residuo.sql`: **7.678 → 4**. Tres son los excluidos a propósito (`202512729` foco congelado; `202310499`,
  `202413587` shadow de Entra duplicado) y uno (`202624610`) el ítem de trabajador oscilante.
- `eduPersonAffiliation=member` en `ou=people`: **23.600 → 21.450**, igual en .168 y .169.
- `pendingOperationCount` = 0.

## Pendiente
- `eduPersonScopedAffiliation` es tolerante: los valores rancios previos no se limpian (p. ej. `student@` en egresados).
  Requiere `tolerant=false` en el resource LDAP (PATCH aparte).
- Caso `jenson` (dos correos → Koha `secondary_email` single-valued).
