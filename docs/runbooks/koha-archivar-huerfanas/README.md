# Archivar cuentas Koha huérfanas antiguas (legacy, cero-uso) — UPeU BUL

**Fecha de preparación:** 2026-06-02
**Estado:** PREPARADO. NO EJECUTADO. Requiere backup + dry-run + aprobación explícita del usuario.
**Alcance:** instancia Koha `bul` (BD `koha_bul`), host app `192.168.12.135`, BD MariaDB `192.168.12.130`.
**Constraint de esta fase:** Koha y Oracle LAMB **SOLO LECTURA**. Aún no se archiva/borra nada.

> "Archivar" aquí = `delete_patrons.pl`, que **mueve la cuenta a `deletedborrowers`**
> (la "BD de archivados" de Koha) ANTES de borrarla de `borrowers`. NO es destrucción.

---

## 0. Resumen ejecutivo

Dos entregables en este directorio:

| Tarea | Resultado |
|---|---|
| **TAREA 1** — Email como criterio adicional de fusión | El email aporta **46 pares NUEVOS** sobre los 100 ya hallados por DNI. Ver §1. |
| **TAREA 2** — Set seguro de huérfanas a archivar | **6,673 cuentas** legacy, cero-uso, no-activas en Oracle, sin gemela canónica. Ver §2–§5. |

**Embudo del set seguro (TAREA 2):**

| Paso | Cuentas | Comentario |
|---|---|---|
| Legacy total (ESTUDI/ALUMNI/VISITA/DOCEN/ADMINIST/INVESTI/POSGRADO/JUBILADO/ADMIN) | 19,472 | categorías NO eduPerson |
| − con CUALQUIER uso (issues/old_issues/reserves/old_reserves/accountlines/debarments) o staff/protected | → 18,213 | cero-uso absoluto |
| − **activos hoy en Oracle** (matrícula sem 279/267 **o** contrato 7124 vivo) | **−11,428** | **EXCLUIDOS por seguridad** (les tocará cuenta canónica al reanudar recons) |
| = no activos en Oracle | 6,685 | |
| − con gemela canónica (es caso de fusión, no archivado) | −12 | |
| = **SET SEGURO FINAL a archivar** | **6,673** | |

El hallazgo crítico: de las 18,213 cuentas "cero-uso", **el 63% (11,428) sigue siendo
persona activa en Oracle** (estudiante matriculado que nunca usó la biblioteca, o trabajador
vigente). Esas NO se tocan. Solo se archivan las 6,673 que son legacy + cero-uso + **sin
afiliación viva** + sin gemela canónica.

Desglose del set seguro por categoría:

| categoría | cuentas |
|---|---|
| ALUMNI | 2,749 |
| ESTUDI | 1,965 |
| VISITA | 1,563 |
| DOCEN | 372 |
| INVESTI | 24 |
| **Total** | **6,673** |

---

## 1. TAREA 1 — Email como criterio adicional de fusión

Se buscaron cuentas que comparten el **mismo email institucional `@upeu.edu.pe`** entre una
cuenta legacy (cardnumber código/DNI) y otra cuenta, **que el puente DNI NO emparejó**.

- **52 emails institucionales compartidos** por 104 cuentas en total.
- **50 grupos** involucran al menos una cuenta legacy.
- **4 grupos** ya estaban cubiertos por el puente DNI (uno de sus borrowernumbers ya está en los 100 pares).
- **46 pares NUEVOS** que el DNI no había detectado:

| Clasificación | Pares nuevos | Acción propuesta |
|---|---|---|
| `EMAIL_MATCH_SAME_NAME_FUSION_CAND` (mismo email + mismo nombre) | **37** | Candidato a fusión adicional. Patrón típico: `ALUMNI(código)` + `staff/ADMINIST(DNI)` = egresado que ahora trabaja → involucra un **trabajador**, por lo que entra como `WORKER_EXCLUDE` (tratamiento aparte, NO en la tanda automática estudiante). |
| `EMAIL_MATCH_DIFF_NAME_REVIEW` (mismo email + nombre distinto) | **9** | **Revisión humana obligatoria.** Hay dos sub-casos (ver abajo). |
| `EMAIL_MATCH_DNI_DISTINTO_REVIEW` (mismo email + DNI distinto) | **0** | No se hallaron cuentas compartidas/familiares por DNI. |

### Sub-casos de los 9 `DIFF_NAME` (CRÍTICO)

No todos son la misma persona. El email institucional fue en varios casos **reciclado/recortado**
y ahora colisiona entre personas DISTINTAS:

- **Email reciclado → NO fusionar** (personas diferentes que comparten un alias corto):
  `juan.ruiz@` (Ruiz Cerda Juan Miguel ≠ Ruiz Soto Juan Martín),
  `lauraem@` (Laura Epifania Mejía ≠ Samira Lopez Santillan),
  `lizethflores@` (Yanqui Diaz Evelin ≠ Flores Rodrigo Lizeth),
  `andy.malaver@` (Jheraldine Malaver ≠ Andy Malaver — hermanos posiblemente).
- **Misma persona con variante ortográfica → fusión tras revisión**:
  `juanfelixq@` (Quispe Gonzales Juan Felix en ambas),
  `javierquispet@` (Quispe/Qui**p**e Tenorio Javier),
  `cgalvez@` (Galvez Vivanco César Augusto, una con surname="DESCONOCIDO"),
  `jemima.balbin@` (Balbín Arévalo).

> Conclusión TAREA 1: **el email suma 37 candidatos de fusión sólidos** (todos con trabajador
> ⇒ van a la pista WORKER, no a la automática) **+ 9 a revisar manualmente** (de los cuales
> ~4–5 son mismas personas y ~4 son emails reciclados que NO deben fusionarse).
> Detalle completo en `tarea1_pares_email_nuevos.tsv`.

---

## 2. Script shipped de Koha — `delete_patrons.pl` (revisado en el servidor)

Ruta real: **`/usr/share/koha/bin/cronjobs/delete_patrons.pl`**
(NO `misc/cronjobs/`; en el packaging Debian de UPeU vive en `bin/cronjobs/`). Koha **25.11**.

### Flags confirmados

| Flag | Efecto |
|---|---|
| `--not_borrowed_since=DATE` | patrones sin préstamo desde DATE (usa `old_issues.timestamp`). |
| `--expired_before=DATE` | `dateexpiry < DATE`. |
| `--last_seen=DATE` | `lastseen < DATE` (requiere syspref `TrackLastPatronActivityTriggers`; aquí `lastseen` es casi todo NULL → poco útil). |
| `--category_code=CAT` | filtra por categoría (repetible). |
| `--library=LIB` | filtra por sucursal. |
| `--file=FILE` | lista de `borrowernumber` (uno por línea). Si se combinan otros filtros, **intersecta** (solo borra los del archivo que además cumplan). |
| `--without_restriction_type=TYPE` | excluye los que tengan ese tipo de restricción. |
| `-c, --confirm` | **sin este flag = DRY-RUN** (no borra; solo reporta). |
| `-v, --verbose` | detalle por patrón. |

### CRÍTICO — ¿archiva antes de borrar? SÍ

El bucle de borrado hace, por cada patrón (con `--confirm`):

```perl
my $deleted = eval { $patron->move_to_deleted; };   # 1) copia íntegra a deletedborrowers
...
eval { $patron->delete };                            # 2) borra de borrowers
```

- **`move_to_deleted()`** (`Koha/Patron.pm`): inserta una copia completa del registro en
  **`deletedborrowers`** (con `updated_on` = ahora). **Es el archivado.** El historial de la
  persona se preserva ahí.
- **`->delete()`**: corre en transacción; **cancela los holds** del patrón (`$hold->cancel`),
  desvincula listas (`virtualshelves->disown_or_delete`), borra `borrower_modifications`, y
  finalmente borra de `borrowers`. Registra `MEMBERS/DELETE` en el log si `BorrowersLog` activo.

### Salvaguardas internas (red adicional, además de nuestro pre-filtrado)

`GetBorrowersToExpunge` (`C4/Members.pm`) y el bucle excluyen automáticamente:

- `category_type = 'S'` (staff) — nunca borra staff.
- `flags IS NULL OR flags = 0` — nunca borra cuentas con permisos de staff.
- Garantes (`guarantor_id`) — nunca borra a quien avala a otro patrón.
- `protected = 1`.
- Préstamo **vivo** (`issues` / `currentissue NOT NULL`).
- `AnonymousPatron`.
- En el bucle: **`non_issues_charges`** (multas/saldo pendiente) → SKIP.

> **Importante sobre `move_to_deleted` + holds:** `->delete` **cancela holds vivos**. Nuestro
> set seguro tiene **0 reserves y 0 old_reserves**, así que no hay holds que perder. Aun así,
> el dry-run lo reconfirma.

> **Importante sobre `--file` solo:** si se invoca con `--file` **sin** otros filtros, el script
> NO re-aplica `GetBorrowersToExpunge` (ese embudo solo corre cuando hay filtros de fecha/categoría).
> En ese modo, las únicas salvaguardas activas son las del **bucle** (charges, protected,
> anonymous). Por eso nuestra lista ya viene pre-filtrada con TODOS los criterios (§3) y,
> de forma defensiva, la invocación recomendada combina `--file` **con** `--category_code`
> para forzar también el embudo interno (staff/flags/garante/préstamo-vivo). Ver §4.

---

## 3. Definición del SET SEGURO (todas las condiciones a la vez)

Una cuenta entra al set seguro **solo si cumple TODO**:

1. **Categoría legacy** (NO eduPerson): `ESTUDI, ALUMNI, VISITA, DOCEN, ADMINIST, INVESTI, POSGRADO, JUBILADO, ADMIN`.
2. **`category_type <> 'S'`**, `flags IS NULL OR 0`, `protected = 0`.
3. **CERO uso de biblioteca**: 0 filas en `issues`, `old_issues`, `reserves`, `old_reserves`,
   `accountlines`, `borrower_debarments`. (Cualquier historial ⇒ se preserva, NO se archiva por esta vía.)
4. **NO es persona activa hoy en Oracle**: su `cardnumber` (código o DNI) y su atributo `DNI`
   **NO** aparecen entre:
   - estudiantes con matrícula vigente sem **279/267** (misma query que el resource `estudiantes.xml`), ni
   - trabajadores con contrato **7124** `ESTADO='A'` y `FEC_TERMINO` vigente (misma fuente que `trabajadores.xml`).
5. **Sin gemela canónica**: su identificador no coincide con ninguna cuenta `student/alum/faculty/staff`
   (esas 12 son fusión, no archivado — se derivan al runbook `koha-merge-duplicados-estudiantes`).

### Umbral de antigüedad — nota

`dateexpiry` **no** es buen discriminador aquí: 12,021 ESTUDI del universo cero-uso tienen
`dateexpiry=2026` por una **renovación en bloque**, y `lastseen` es NULL en el 99.5% (nunca
hicieron login). Por eso el discriminador real de "huérfana antigua" es la combinación
**cero-uso + sin afiliación viva en Oracle** (criterio 3+4), que es más fuerte que una fecha.

Como **capa opcional más conservadora**, dentro del set seguro hay **1,918 cuentas con
`dateexpiry < 2 años`** (antes de 2024-06-02). Se puede empezar por ese subconjunto si se
prefiere un primer lote ultra-conservador (columna `dateexpiry` en el CSV permite filtrarlo).

### Las 12 excluidas por gemela canónica

Tienen una cuenta `student/alum/faculty/staff` con el mismo DNI/código (p. ej. borrowernumber
23180/25140/25434/25609 ALUMNI con attr DNI que ya existe como canónica). **Van a fusión**, no
a archivado.

---

## 4. Preparar la ejecución (NO ejecutar)

### 4.1 Backup obligatorio previo

```bash
# en el app server (192.168.12.135), vía koha-shell, o directo contra la BD
mysqldump --single-transaction --routines koha_bul \
  > /home/juansanchez/backups/koha_bul_pre_archive_$(date +%Y%m%d_%H%M%S).sql
```

Backup acotado mínimo si se quiere: `borrowers, deletedborrowers, borrower_attributes, holds`.

### 4.2 Subir la lista de borrowernumbers al server

`borrowernumbers_set_seguro.txt` (6,673 líneas) — vía `git pull` del repo en el app server,
o `koha-shell`. **Nunca scp** (política UPeU).

### 4.3 DRY-RUN (por defecto, NO borra)

Invocación recomendada — `--file` + `--category_code` (fuerza también el embudo interno de
salvaguardas), **sin `--confirm`**:

```bash
sudo koha-shell bul -c "perl /usr/share/koha/bin/cronjobs/delete_patrons.pl \
  --file /home/juansanchez/borrowernumbers_set_seguro.txt \
  --category_code ESTUDI --category_code ALUMNI --category_code VISITA \
  --category_code DOCEN --category_code INVESTI \
  --verbose"
```

Salida esperada: `"Doing a dry run; no patron records will actually be deleted."` y
`"N patrons would have been deleted"`. **N debe ser ≈ 6,673** (puede ser ligeramente menor si
el embudo interno descarta alguno por garante/charge sobrevenido — eso es correcto).

> Variante mínima (solo lista, sin embudo de categoría): quitar los `--category_code`. Da el
> número bruto del archivo; útil para contrastar contra la variante con embudo y ver cuántos
> descarta la salvaguarda interna.

### 4.4 EJECUCIÓN REAL (requiere aprobación + backup hecho)

Igual que §4.3 **añadiendo `--confirm`**. Recomendado por lotes (la lista es grande):
empezar con un **piloto** y luego el resto.

```bash
# PILOTO: primeras 50 líneas
head -50 /home/juansanchez/borrowernumbers_set_seguro.txt > /home/juansanchez/_piloto.txt
sudo koha-shell bul -c "perl /usr/share/koha/bin/cronjobs/delete_patrons.pl \
  --file /home/juansanchez/_piloto.txt --category_code ESTUDI --category_code ALUMNI \
  --category_code VISITA --category_code DOCEN --category_code INVESTI \
  --verbose --confirm"
```

Verificar tras el piloto:
```sql
-- las 50 deben estar en deletedborrowers y NO en borrowers
SELECT COUNT(*) FROM deletedborrowers WHERE borrowernumber IN (...);  -- = 50
SELECT COUNT(*) FROM borrowers        WHERE borrowernumber IN (...);  -- = 0
```

Luego el resto con la lista completa.

### 4.5 Listado revisable (UX manual)

`koha_set_seguro_REVISABLE.csv` — 6,673 filas con
`borrowernumber, cardnumber, categorycode, userid, surname, firstname, email, dateexpiry, lastseen, attr_dni`,
ordenado por categoría y `dateexpiry`. Permite revisión/curado manual antes de archivar, o
recortar a un primer lote (p. ej. solo `dateexpiry < 2024`).

---

## 5. Interacción con MidPoint (recomendación de orden)

Las 6,673 son cuentas **sin afiliación viva en Oracle** ⇒ en MidPoint esas personas están (o
quedarán) `archived`/sin user, y el resource Koha ILS está en `proposed` (no provisiona
outbound todavía). Archivarlas en Koha **no rompe** ningún link vivo de provisioning.

Aun así, orden canónico recomendado:

1. **Backup** `mysqldump koha_bul` (§4.1).
2. **DRY-RUN** (§4.3) → confirmar N ≈ 6,673 y revisar SKIPs.
3. **Piloto 50** con `--confirm` (§4.4) → verificar `deletedborrowers`.
4. **Resto** por lotes con `--confirm`.
5. (Opcional) tras reanudar recons, una reconciliación Koha en MidPoint no recreará estas
   cuentas porque las personas no están activas en Oracle (fuera del resultset de los resources).

---

## 6. Reproducir el análisis (SOLO LECTURA)

- Universo legacy + embudo cero-uso: query en `sql/01_safe_base.sql`.
- Sets vivos Oracle (estudiantes 279/267 + trabajadores 7124): `sql/02_oracle_live.sql`.
- Cruce + gemela canónica + clasificación email: `sql/03_cross.py`.

Conteos a reconfirmar **justo antes de ejecutar** (la BD viva cambia): re-correr el embudo y
regenerar `borrowernumbers_set_seguro.txt`. El dry-run es la verificación final.

---

## 7. Archivos de este directorio

| Archivo | Descripción |
|---|---|
| `README.md` | Este runbook. |
| `koha_set_seguro_REVISABLE.csv` | 6,673 cuentas del set seguro (revisión/UX manual). |
| `borrowernumbers_set_seguro.txt` | Lista de `borrowernumber` para `delete_patrons.pl --file`. |
| `tarea1_pares_email_nuevos.tsv` | 46 pares nuevos por email (TAREA 1), clasificados. |
| `sql/01_safe_base.sql` | Query del embudo cero-uso en Koha. |
| `sql/02_oracle_live.sql` | Queries Oracle de membresía viva (estudiante/trabajador). |
| `sql/03_cross.py` | Cruce Koha×Oracle, gemela canónica, clasificación email. |
</content>
</invoke>
