# EJECUTADO — Archivado ALUMNI huérfano (legacy) — 2026-06-02

**Estado:** COMPLETO Y VERIFICADO. Instancia Koha `bul` (BD `koha_bul`).
**Método:** `delete_patrons.pl` (Koha 25.11) → `move_to_deleted` (a `deletedborrowers`) + `delete`.
**Constraint cumplido:** backup verificado ANTES de borrar; solo categoría `ALUMNI` legacy;
NUNCA tocada `alum` canónica ni cuentas con historial/afiliación viva; Oracle solo lectura.

Cierra el archivado pendiente: los 3,920 estables ESTUDI/VISITA/DOCEN/INVESTI ya se
archivaron temprano hoy; faltaba ALUMNI (esperaba que cerrara recon `CANON-KEY Import Egresados`).

## Set re-derivado contra BD VIVA (no listas viejas)

Embudo aplicado a la categoría `ALUMNI` legacy:

| Paso | Cuentas |
|---|---|
| ALUMNI total (BD viva) | 482 |
| − flags>0 / protected / debarred | → 481 |
| − cualquier uso/historial (issues/old_issues/reserves/old_reserves/accountlines/debarments) y garante | → 480 |
| − con gemela canónica (alum/student/faculty/staff por cardnumber) | → 480 (0 con gemela) |
| − **activos hoy en Oracle** (matrícula sem 279/267 o contrato 7124 vivo), puente código→DNI | **−6** |
| = **SET FINAL ARCHIVADO** | **474** |

Nota técnica: el filtro inicial con `NOT IN (SELECT borrowernumber FROM old_issues)` daba 0 por
**1,622 filas con `borrowernumber NULL`** (historial anonimizado) en `old_issues` — el `NOT IN`
con NULL siempre devuelve vacío. Resuelto con `NOT EXISTS` (NULL-safe).

### Puente código→DNI (Oracle, solo lectura)

Las ALUMNI no tienen atributo `DNI`/`COD_UPEU` poblado; su único id es `cardnumber` (código
universitario). Cruce contra sets vivos Oracle vía JDBC (ojdbc11) en el contenedor `midpoint_server`:
- Estudiantes vivos 279/267: **24,565** filas (CODIGO + NUM_DOCUMENTO).
- Trabajadores 7124 vivos: **3,678** filas (COD_APS + NUM_DOCUMENTO).
- Normalización con y sin ceros a la izquierda (igual que `sql/03_cross.py`).

### Los 6 excluidos por activos en Oracle (NO archivados)

Egresados que retomaron estudios (matrícula viva 279/267) — recibirán cuenta canónica al reanudar recons:

```
84520  202100345   ESTUDIANTE_VIVO
84550  201321865   ESTUDIANTE_VIVO
84716  202121540   ESTUDIANTE_VIVO
85356  200511661   ESTUDIANTE_VIVO
85757  201911843   ESTUDIANTE_VIVO
85810  9710231     ESTUDIANTE_VIVO
```

## Backup (prerequisito absoluto, verificado ANTES de borrar)

- Ruta: `/home/juansanchez/backups/koha_bul_pre_archive_alumni_20260602_085854.sql.gz` (host MariaDB 192.168.12.130)
- Tamaño: **954,136,220 bytes (~954 MB)**
- `gzip -t`: **OK**. `mysqldump --single-transaction --quick --routines`.

## Ejecución

| Fase | Comando | Resultado |
|---|---|---|
| Dry-run | `--file ... --category_code ALUMNI --verbose` | `474 patrons match conditions` → `474 would have been deleted`, 0 cannot |
| Piloto 50 | `... --confirm` | `50 patrons deleted`, 0 cannot |
| Resto 424 | `... --confirm` | `424 patrons deleted`, 0 cannot |

Invocación combinó `--file` + `--category_code ALUMNI` para forzar también el embudo interno
`GetBorrowersToExpunge` (staff/flags/garante/charges/préstamo-vivo) — red de seguridad adicional.

## Verificación final (BD viva)

- set 474 en `deletedborrowers`: **474** ✓
- set 474 aún en `borrowers`: **0** ✓
- `borrowers` ALUMNI: 482 → **8** ✓ (bajó 474)
- `deletedborrowers` total: 40,785 → **41,259** ✓ (subió 474)
- canónicas (alum/student/faculty/staff) tocadas: **0** ✓
- 6 excluidos-activos intactos en `borrowers`: **6** ✓
- OPAC HTTP: **200** ✓

### Las 8 ALUMNI remanentes (todas justificadas)
- `22041` CAT2$UPEU — flags=1 (staff) + 72 old_issues.
- `81555` — tiene historial (old_issues) → preservada.
- 6 activos en Oracle (arriba).

## Artefactos
- `alumni_ARCHIVADO_474_20260602.tsv` — borrowernumber + cardnumber del set archivado.
- `alumni_excluidos_activos_oracle_20260602.tsv` — los 6 excluidos por afiliación viva.

Temporales (`.java` con query Oracle, listas) eliminados de `midpoint_server` y host app Koha.
