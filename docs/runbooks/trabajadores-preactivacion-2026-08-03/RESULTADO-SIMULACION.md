# Simulación pre-activación de `recon-oracle-lamb-trabajadores-daily` — RESULTADO

**Fecha:** 2026-08-04 · **Task:** `3cb0c47a-7f89-4f24-98fb-7b2723748b1a` (`mode=preview`)
**SimulationResult:** `a241d818-5ba3-4966-9f33-ebfc8f22aef4`
**Ventana:** 08:34:00 → 09:14:26 (40 min) · **progress:** 7.542 · **failureCount: 0**
**Definición de la task:** `upeu/tasks/trabajadores-preactivacion-2026-08-03/sim-recon-trabajadores-preview.xml`

## VEREDICTO: ❌ NO reactivar todavía

La corrida es técnicamente sana (0 fallos, ningún `Operation not supported`), pero produciría
**dos efectos inaceptables sin decisión previa**: 3 duplicados de persona y 114 borrados de
entradas LDAP vivas.

---

## 1. Cifras

| Objeto | Estado | Nº |
|---|---|---|
| SHADOW | UNMODIFIED | 26.821 |
| **USER** | **MODIFIED** | **6.671** |
| SHADOW | MODIFIED | 2.033 |
| USER | UNMODIFIED | 703 |
| **SHADOW** | **ADDED** | **189** (100 LDAP + 89 Koha) |
| 🔴 **SHADOW** | **DELETED** | **180** (todos LDAP) |
| 🔴 **USER** | **ADDED** | **18** |

Marcas de evento:

| Marca | Nº |
|---|---|
| Resource object affected | 2.376 |
| **Projection deactivated** | **1.124** (1.123 LDAP + 1 Koha) |
| Focus assignments changed | 314 |
| Focus role membership changed | 310 |
| Projection activated | 297 |
| Focus parent organization reference changed | 282 |
| Focus archetype changed | 278 |
| **Focus deactivated** | **114** |
| Focus activated | 74 |
| Projection renamed / identifier changed | 3 / 3 |
| Focus renamed | 1 |
| **Shadow correlation state changed** | **0 ← el guardarraíl no dispara ni una vez** |

**Errores: 1 solo mensaje en toda la corrida** — colisión de proyección Entra ID
(`76443853@upeu.edu.pe` vs `james.raymundo@upeu.edu.pe`, mismo foco). Es el `partial_error`.
`totalFailureCount = 0` en todas las partes.

---

## 2. 🔴 Hallazgo 1 — crearía 3 duplicados de persona, y el guardarraíl NO los ve

De las 18 altas de `User`, **3 son personas que YA existen en MidPoint** (comparado por
`fullName` normalizado — mayúsculas + acentos, el mismo método con el que se detectó el caso
Orlando):

| Alta que se crearía | Ya existe como | Estado del existente | Por qué no correlaciona |
|---|---|---|---|
| `000614192` Luzirene Gomes de Alcantara | **`00614192`** | archived | **padding de ceros** |
| `44528386f` Katty Aracelly Porras Espinoza | **`44528386`** | archived | **sufijo `f`** en el documento |
| `001642451` Evanilda Ruth Valeriano Tiñini | **`201520024`** | active | código de trabajador vs código de estudiante — misma persona, dos canales |

Las otras 15 altas no tienen homónimo: son personas nuevas legítimas.

### Por qué esto invalida la conclusión de la Fase 0 del 03-ago

La Fase 0 midió `personalNumber` ↔ `CANON_KEY` y dio **0 drift de padding**, y con eso se dio
por cerrado el riesgo R3 del guardarraíl. **La medición fue correcta pero de alcance
insuficiente:** solo cubrió los **7.364 usuarios linkados**. El caso Luzirene (`00614192`,
*archived*, sin link) queda fuera de esa población — y es exactamente el caso que el tier 2 del
guardarraíl no atrapa.

**Consecuencia:** el guardarraíl 2-tier, que nunca se validó con un canario real (pendiente
desde el 26-jul), aquí queda **refutado empíricamente**: 0 `disputed` frente a 3 duplicados
reales. No protege.

---

## 3. 🔴 Hallazgo 2 — 114 personas desaparecerían del LDAP (no se deshabilitan: se borran)

Los 180 shadows LDAP a borrar se descomponen así, agrupando por foco:

| Situación | Focos |
|---|---|
| Conserva presencia en LDAP (mudanza o dual resuelto) | 66 |
| 🔴 **Se queda SIN ninguna entrada LDAP** | **114** |

Las 66 que conservan presencia son movimientos entre OUs, que el conector implementa como
delete + add porque no soporta rename:

| Dirección | Nº |
|---|---|
| `ou=people` → `ou=alumni` | 26 |
| `ou=alumni` → `ou=people` | 21 |

Las **114 restantes coinciden exactamente con los 114 `Focus deactivated`**: son las bajas. Al
perder la última asignación que otorgaba la cuenta, MidPoint deprovisiona **borrando la entrada**,
no deshabilitándola.

**Verificado contra el LDAP real** (`192.168.15.168`, bind `cn=rims-reader`): las entradas
existen hoy. Muestra de 6/6 presentes en `ou=people`. No son shadows fantasma; el borrado sería
real e irreversible.

De esos 114 focos, **120 de los 133 usuarios implicados ya tenían `disableTimestamp`** — o sea
ya eran bajas conocidas dentro de MidPoint; lo que faltaba era materializarlas.

### Por qué importa

Contradice el objetivo del arreglo del leaver gap y la petición P1 de Pulso DTI
(`productos/devsupeu/canonico/docs/consultas/2026-08-03-contrato-atributos-ldap-pulso-dti.md`):
lo que se pidió es una **señal de baja** (`midPointAccountStatus=disabled`), no la desaparición
de la ficha. Una entrada borrada no da señal: los consumidores (RIMS, InOut, Pulso DTI) ven un
hueco, pierden el ancla `eduPersonUniqueId`, y si la persona regresa se le crea una entrada nueva.
Cortar el acceso es correcto; hacerlo por borrado es una decisión de diseño que nadie tomó.

---

## 4. ✅ Lo que SÍ funciona (confirmado por esta corrida)

- **El arreglo del leaver gap opera.** Cero errores `Operation not supported` en 7.542 objetos.
  Verificado en vivo sobre el canario: `uid=20894196` ya publica `midPointAccountStatus: disabled`
  en LDAP.
- **1.123 proyecciones LDAP se deshabilitarían** — y **1.097 de sus dueños ya tenían
  `disableTimestamp`**. Es decir: no es una desactivación nueva, es el **backfill del estado que
  el directorio nunca reflejó**. Solo 26 serían bajas nuevas. Este efecto es correcto y deseado,
  aunque masivo.
- **`employeeNumber`** se propaga sin incidencias: el grueso de los 6.671 `User MODIFIED` no lleva
  ninguna marca de evento (~5.300), consistente con un cambio silencioso de atributo.
- **No hay tormenta de altas.** 18 usuarios nuevos, no miles. La hipótesis de aluvión queda
  descartada.

---

## 5. Qué hacer antes de reactivar

| # | Acción | Bloquea |
|---|---|---|
| 1 | **Resolver los 3 duplicados a mano** (`000614192`, `44528386f`, `001642451`): decidir si se relinkan al `User` existente o se corrige el dato en Oracle | Sí |
| 2 | **Arreglar el guardarraíl** para que el tier 2 normalice padding y sufijos alfabéticos antes de comparar — hoy no atrapa ninguno de los 3 | Sí |
| 3 | **Decidir la política de baja en LDAP**: ¿borrar la entrada (comportamiento actual) o deshabilitarla y conservarla? Si es lo segundo, hay que cambiar el `objectType` de LDAP antes de correr nada. Afecta a 114 personas en la primera corrida | Sí |
| 4 | Repetir esta simulación tras 1-3 y comprobar que `USER ADDED` baja a 15 y que los borrados son solo los 66 movimientos | Sí |
| 5 | Resolver la colisión de proyección Entra del foco `76443853` / `james.raymundo` | No |

**Método:** las tres decisiones son de producto, no técnicas. Ninguna se puede tomar desde el
IGA sin Alberto.

---

## 6. Reproducir el análisis

```sql
-- resumen por tipo y estado
SELECT objecttype, state, count(*) FROM m_simulation_result_processed_object
 WHERE owneroid='a241d818-5ba3-4966-9f33-ebfc8f22aef4' GROUP BY 1,2 ORDER BY 3 DESC;

-- marcas de evento
SELECT o.nameOrig, count(*) FROM m_processed_object_event_mark em
  JOIN m_object o ON o.oid=em.targetoid
 WHERE em.owneroid='a241d818-5ba3-4966-9f33-ebfc8f22aef4' GROUP BY 1 ORDER BY 2 DESC;
```

Notas de método aprendidas aquí:

- `m_simulation_result_processed_object` se une al resultado por **`owneroid`**, no por
  `simulationResultOid`. Las marcas se unen por `(owneroid, processedobjectcid)`.
- `fullobject` es **JSON en claro** (`convert_from(...,'UTF8')`); `objectbefore` / `objectafter`
  vienen vacíos.
- ⚠️ Los `ADDED` pueden traer `focusrecordid` **NULL** (18 de 207). Un `NOT IN` contra una
  subconsulta con NULL devuelve **cero filas siempre** — ese error dio un falso "0 focos sin
  recreación" antes de corregirlo. Usar `NOT EXISTS` o filtrar los NULL.
