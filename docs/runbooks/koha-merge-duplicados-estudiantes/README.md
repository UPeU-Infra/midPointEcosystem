# Fusión de cuentas Koha duplicadas (estudiante/egresado) — UPeU BUL

**Fecha de preparación:** 2026-06-02
**Estado:** PREPARADO. NO EJECUTADO. Requiere aprobación del usuario.
**Alcance:** instancia Koha `bul` (BD `koha_bul`), host app `192.168.12.135`, BD `192.168.12.130`.
**Constraint de esta fase:** Koha y Oracle **SOLO LECTURA**. Aún no se fusiona nada.

---

## 0. Resumen ejecutivo

Existen **100 pares de cuentas duplicadas** en Koha BUL detectados en vivo (clave = DNI):
una persona con DOS cuentas, una con `cardnumber` = **código institucional** (9-10 dígitos, *keeper*)
y otra con `cardnumber` = **DNI** (8 dígitos, *loser*).

| Clasificación | Pares | Acción |
|---|---|---|
| `STUDENT_MERGE` (estudiante/egresado puro) | 76 | Fusionar keeper←loser |
| `STUDENT_NAME_VARIANT_REVIEW` (mismo DNI, ortografía de nombre difiere) | 8 | Revisión humana antes de fusionar |
| `WORKER_EXCLUDE` (uno de los dos es trabajador) | 16 | **NO fusionar** en esta tanda |
| **Total** | **100** | |

> Nota sobre el conteo previo (129): el análisis anterior incluía emparejamientos
> adicionales por nombre que NO se sostienen en la vista viva con clave DNI. La cifra
> autoritativa hoy contra la BD viva es **100 pares (84 estudiante + 16 trabajador)**.
> El recuento debe reconfirmarse justo antes de ejecutar (ver §6).

Dos entregables:
- **A** — Script Perl de fusión por lotes (`koha_merge_estudiantes.pl`) usando el mecanismo nativo.
- **B** — Lista revisable (`koha_merge_pares_REVISABLE.csv`) para fusión manual en la UI de Koha.

---

## 1. Mecanismo nativo `Koha::Patron->merge_with` (verificado en el servidor)

Fuente: `/usr/share/koha/lib/Koha/Patron.pm` (Koha **25.11.03-2**). No existe script
shipped en `misc/` para merge de patrones (solo `merge_authorities`). El merge se hace
vía el método del modelo.

Firma: `$keeper->merge_with(\@loser_ids)`. Comportamiento:

1. Corre **dentro de una transacción** (`txn_do`) — atómico por keeper.
2. Para cada loser: copia sus `extended_attributes` al keeper (tolerante a no-repetibles).
3. **Reasigna (UPDATE, no DELETE)** todas las tablas de `$RESULTSET_PATRON_ID_MAPPING`
   del loser al keeper. Tablas que reasigna (historial preservado):

   `Accountline, Aqbasketuser, Aqbudget, Aqbudgetborrower, ArticleRequest,`
   `BorrowerDebarment, BorrowerFile, BorrowerModification, ClubEnrollment,`
   `Issue (préstamos vivos), OldIssue (préstamos históricos), Reserve, OldReserve,`
   `ItemsLastBorrower, Illrequest, Linktracker, Message, MessageQueue, Rating,`
   `Review, SearchHistory, Statistic, Suggestion, TagAll, Virtualshelfcontent,`
   `Virtualshelfshare, Virtualshelve`

4. **`move_to_deleted()`** → inserta una copia íntegra del loser en `deletedborrowers`
   (preserva el registro histórico de la persona).
5. Luego `delete()` el loser de `borrowers`.
6. Si `BorrowersLog` está activo, registra acción `PATRON_MERGE`.

**Conclusión:** `merge_with` **NO destruye historial** — lo reasigna al keeper y archiva
el loser en `deletedborrowers`. Es el mecanismo correcto y seguro.

Salvaguardas internas: no fusiona patrones `protected` ni `anonymous` (ni como keeper ni como loser).

---

## 2. Entregable A — Script Perl de fusión por lotes

Archivo: [`koha_merge_estudiantes.pl`](./koha_merge_estudiantes.pl)
Entrada: [`koha_merge_input_pares.tsv`](./koha_merge_input_pares.tsv) (84 pares estudiante; los 16 trabajador **no están** en este TSV).

Verificado: `perl -c` dentro de `koha-shell bul` → **syntax OK** (todos los `use Koha::*` resuelven).

### Cómo se invoca

```bash
# DRY-RUN (por defecto, NO modifica nada) — copiar antes el script y el TSV al server
sudo koha-shell bul -c \
  "perl /home/juansanchez/koha_merge_estudiantes.pl \
   --input /home/juansanchez/koha_merge_input_pares.tsv"

# EJECUCIÓN REAL (requiere --commit explícito + backup previo, ver §4)
sudo koha-shell bul -c \
  "perl /home/juansanchez/koha_merge_estudiantes.pl \
   --input /home/juansanchez/koha_merge_input_pares.tsv --commit"
```

Opciones: `--batch N` (default 25), `--pause S` (default 5s), `--include-variant`
(incluye los 8 name-variant; por defecto se SALTAN y se listan para revisión),
`--only-dni DNI` (procesar un solo caso, ideal para piloto), `--log FILE`.

### Validaciones pre-merge por par (cada una hace SKIP + marca para revisión si falla)
- keeper `cardnumber` debe ser código de **9-10 dígitos**; loser debe ser **DNI de 8 dígitos == dni**.
- Salvaguarda anti-DNI: si el keeper tuviera `cardnumber = DNI` → SKIP (nunca el DNI como keeper).
- Revalida `cardnumber` de keeper y loser **contra la BD viva** (detecta drift respecto al TSV).
- SKIP si keeper o loser no existen, o son `protected`.
- Trabajadores: ya excluidos del TSV; además SKIP defensivo si apareciera `WORKER_EXCLUDE`.
- Name-variant: SKIP por defecto (revisión manual), salvo `--include-variant`.

### Log por par
keeper, loser, DNI, nombres, categoría, #transacciones que se moverían/movieron,
flag historial, a qué cuenta apunta MidPoint, advertencia SSO si el keeper no tiene
email `@upeu.edu.pe`, y resultado (DRY-RUN / OK / FAIL / SKIP).

### Lotes
Cada 25 pares procesados: log de lote + `sleep` (default 5s).

---

## 3. Entregable B — Lista revisable para UI manual

Archivo: [`koha_merge_pares_REVISABLE.csv`](./koha_merge_pares_REVISABLE.csv) (los 100 pares).

Ordenada por `category` (STUDENT_MERGE → NAME_VARIANT_REVIEW → WORKER_EXCLUDE) y DNI.
Columnas clave para fusión manual:
`keeper_borrowernumber, keeper_cardnumber (=código), keeper_*`,
`loser_borrowernumber, loser_cardnumber (=DNI), loser_*`,
`keeper_total_tx, loser_total_tx`, desglose `cur/old/res/acc`,
`has_historial`, `name_variant_review`, `is_worker`,
`mp_points_to`, `mp_koha_cardnumber`, `mp_koha_patron_id`.

**Procedimiento UI:** Usuarios → buscar por DNI → seleccionar las 2 cuentas →
*Merge patrons* → elegir como **keeper la del `keeper_cardnumber` (código)** → confirmar.
**Verificar siempre que el keeper conserve el email institucional.**

---

## 4. Consideraciones críticas

### 4.1 Interacción con MidPoint (HALLAZGO IMPORTANTE)

Se auditó vía REST a qué cuenta Koha apunta el `linkRef` del shadow de MidPoint para
los **84 pares estudiante**:

| MidPoint apunta a… | Pares estudiante | Significado |
|---|---|---|
| `KEEPER(codigo)` | 33 | Caso favorable: MP ya linkeado al keeper. Fusionar NO rompe el link. |
| `LOSER(dni)` | **17** | **PELIGRO**: MP linkeado a la cuenta-DNI. Al fusionarla, `move_to_deleted`+`delete` **rompe el linkRef** del shadow. |
| `NO_MP_USER` | 34 | La persona aún no tiene user en MidPoint (recons suspendidas / matrícula 2023-2024 sin provisionar). El merge es seguro respecto a MP. |

Los 17 casos `LOSER(dni)` están listados explícitamente en el log y en el CSV. Ejemplos:
DNI 71239042, 74217488, 75541713, 75706177, 75798786 (varios CON historial).

**Manejo propuesto (en este orden de preferencia):**
1. **Fusionar DESPUÉS de cerrar el keystone CANON_KEY** (name=código). Cuando MidPoint quede
   alineado al código y re-provisione Koha, los shadows pasarán a apuntar al keeper (código),
   convirtiendo los 17 `LOSER(dni)` en `KEEPER(codigo)`. Entonces el merge no rompe nada.
   → **Secuencia recomendada (§5).**
2. Si se fusiona antes: tras el merge, **re-correlacionar/re-linkear** en MidPoint
   (Koha resource → reconciliación o import; el correlador por email/cardnumber re-vincula
   el shadow superviviente del keeper). Los 17 quedarían como `linkRef` roto hasta la recon.
   Riesgo: un recompute intermedio podría intentar recrear la cuenta DNI borrada.

### 4.2 Backup obligatorio antes de ejecutar
```bash
# en el server de BD (192.168.12.130) o vía app server
mysqldump --single-transaction --routines koha_bul \
  > /home/juansanchez/backups/koha_bul_pre_merge_$(date +%Y%m%d_%H%M%S).sql
```
Tablas mínimas a respaldar si se quiere backup acotado: `borrowers, deletedborrowers,`
`borrower_attributes, issues, old_issues, reserves, old_reserves, accountlines`.

### 4.3 SSO / email (Keycloak matchea por email)
El keeper **debe conservar el email institucional** (`@upeu.edu.pe`). El script emite
`[WARN]` cuando el keeper no lo tiene. En esos casos, antes de fusionar, asegurar que el
keeper tenga el email `@upeu.edu.pe` (varios losers-DNI tienen el institucional y el keeper
un gmail — revisar en el CSV columnas `keeper_email`/`loser_email`).

### 4.4 Reconfirmar contra la BD viva
Los conteos son de **2026-06-02**. Antes de ejecutar, regenerar el TSV/CSV con el query de
§6 y correr primero **DRY-RUN**. El script revalida cardnumbers contra la BD viva y hace
SKIP ante cualquier drift.

---

## 5. Secuencia recomendada (orden canónico)

1. **Cerrar keystone CANON_KEY** (name=código) en MidPoint — alinear focus al código.
2. Re-provisionar/reconciliar resource Koha ILS → shadows apuntan al keeper (código).
3. Re-auditar links (re-correr §4.1) → confirmar que los 17 `LOSER(dni)` pasaron a `KEEPER(codigo)`.
4. **Backup** `mysqldump koha_bul` (§4.2).
5. **Reconfirmar lista** contra BD viva (§6) → regenerar TSV/CSV.
6. **DRY-RUN** del script → revisar log (ceros de FAIL, SKIPs esperados, WARN de email).
7. Corregir emails de keepers sin `@upeu.edu.pe` si aplica.
8. **Piloto**: `--only-dni <uno con historial>` con `--commit` → verificar en UI que el
   historial quedó en el keeper y el loser está en `deletedborrowers`.
9. **Ejecución real** `--commit` en lotes para los 76 `STUDENT_MERGE`.
10. **Name-variant (8)**: fusión manual en UI (entregable B) o `--include-variant` tras revisión.
11. **Trabajadores (16)**: NO en esta tanda — tratamiento aparte.
12. Post-merge: reconciliación Koha en MidPoint para sanear cualquier `linkRef`.

---

## 6. Query para reconfirmar la lista (SOLO LECTURA)

```sql
-- Clave-persona = DNI: (a) atributo DNI de 8 díg, (b) cardnumber de 8 díg.
CREATE TEMPORARY TABLE pk AS
  SELECT borrowernumber, attribute AS dni FROM borrower_attributes
   WHERE code='DNI' AND attribute REGEXP '^[0-9]{8}$'
  UNION
  SELECT borrowernumber, cardnumber AS dni FROM borrowers
   WHERE cardnumber REGEXP '^[0-9]{8}$';
CREATE TEMPORARY TABLE dup AS
  SELECT dni FROM pk GROUP BY dni HAVING COUNT(DISTINCT borrowernumber)>1;
SELECT p.dni, b.borrowernumber, b.cardnumber, b.categorycode, b.userid,
       b.surname, b.firstname, b.email,
       (SELECT COUNT(*) FROM issues i      WHERE i.borrowernumber=b.borrowernumber) cur,
       (SELECT COUNT(*) FROM old_issues oi WHERE oi.borrowernumber=b.borrowernumber) old,
       (SELECT COUNT(*) FROM reserves r    WHERE r.borrowernumber=b.borrowernumber) res,
       (SELECT COUNT(*) FROM accountlines a WHERE a.borrowernumber=b.borrowernumber) acc
FROM pk p JOIN dup d ON d.dni=p.dni
JOIN borrowers b ON b.borrowernumber=p.borrowernumber
GROUP BY b.borrowernumber
ORDER BY p.dni, LENGTH(b.cardnumber) DESC;
```

Trabajador = `categorycode IN ('faculty','staff','DOCEN','ADMINIST','INVESTI','JUBILADO')`
en cualquiera de las dos cuentas del par → `WORKER_EXCLUDE`.

---

## 7. Archivos

| Archivo | Descripción |
|---|---|
| `koha_merge_estudiantes.pl` | Script Perl de fusión por lotes (dry-run por defecto). |
| `koha_merge_input_pares.tsv` | 84 pares estudiante (entrada del script; trabajadores excluidos). |
| `koha_merge_pares_REVISABLE.csv` | 100 pares con todo el detalle, para fusión manual en UI. |
| `README.md` | Este runbook. |
