# Simulación pre-activación de `recon-oracle-lamb-trabajadores-daily` — RESULTADO

**Fecha:** 2026-08-04 · **Task:** `3cb0c47a-7f89-4f24-98fb-7b2723748b1a` (`mode=preview`)
**SimulationResult:** `a241d818-5ba3-4966-9f33-ebfc8f22aef4`
**Ventana:** 08:34:00 → 09:14:26 (40 min) · **progress:** 7.542 · **failureCount: 0**
**Definición de la task:** `upeu/tasks/trabajadores-preactivacion-2026-08-03/sim-recon-trabajadores-preview.xml`

## VEREDICTO: ❌ NO reactivar todavía

> **⚠️ ESTE DOCUMENTO ESTÁ SUPERADO.** Los tres bloqueantes de §5 se resolvieron el 04-ago por la
> tarde y la simulación se repitió con los tres arreglos actuando a la vez:
> **`USER ADDED` 18 → 15, personas sin entrada LDAP 114 → 0, 0 Users creados.**
> **→ Resultado vigente: [`SIMULACION-FINAL.md`](SIMULACION-FINAL.md)**
> Lo de abajo se conserva porque documenta cómo se detectaron los tres problemas.

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

| Alta que se crearía | Ya existe como | Estado | Documento existente → del alta | `lambIdPersona` |
|---|---|---|---|---|
| `000614192` Luzirene Gomes de Alcantara | **`00614192`** (`49945169-…`) | archived, cesó 28-feb-2026 | `CE:000614192` → `DNI 00614192` | 11173 ≠ **192480** |
| `44528386f` Katty Aracelly Porras Espinoza | **`44528386`** (`daca140b-…`) | archived, cesó 31-may-2026 | `44528386f` → `DNI 44528386` | 3999385 ≠ **4055270** |
| `001642451` Evanilda Ruth Valeriano Tiñini | **`201520024`** (`4799ae35-…`) | **active**, egresada en `ou=alumni` | `PP:9823732` → `CE:001642451` | **68833 = 68833** |

Las otras 15 altas no tienen homónimo: son personas nuevas legítimas.

### La causa NO es el formato del identificador

En los tres casos **la persona cambió de documento** entre un registro y otro (CE→DNI,
con-`f`→sin-`f`, pasaporte→CE). El tier 1 correlaciona por `lambDocNum` y falla porque compara
documentos que ya no son el mismo. **Normalizar padding o sufijos no salvaría a ninguno de los
tres** — es justo el riesgo «cambia al reanclar CE→DNI» que el propio diseño del `CANON_KEY`
anticipó y que aquí se materializa.

Eso parte el problema en dos clases con dueños distintos:

- **Evanilda es resoluble desde el IGA.** Mismo `lambIdPersona` (68833) a ambos lados: un tier de
  correlación por `externalSystemId` / `lambIdPersona` la atraparía sin ambigüedad. Es además el
  caso más grave, porque el `User` existente está **activo** y con cuenta LDAP viva. Prueba
  independiente de que es la misma persona: su foto en LAMB se llama
  `038_0201520024001642451.jpg` — lleva los dos códigos concatenados.
- **Luzirene y Katty son duplicado de origen en Oracle**, misma clase que el caso Orlando: **dos
  `ID_PERSONA` distintos para el mismo humano**. El IGA no puede unirlas por identificador porque
  en la fuente son dos personas. Corresponde a los DBAs. Lo que sí es defecto del IGA es que las
  crearía **en silencio**, sin `disputed`.

Las tres son **recontrataciones**: habían cesado y vuelven con contrato vivo.

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
| 1 | ~~**Resolver los 3 duplicados a mano**~~ → ✅ **RESUELTO 04-ago** por el correlador: `001642451` vincula con el `User` existente; `000614192` y `44528386f` abren `disputed`. **0 Users creados** en preview. Ver [`correlacion-resuelta.md`](correlacion-resuelta.md) | ~~Sí~~ |
| 2 | ~~**Añadir un tier de correlación**~~ → ✅ **RESUELTO 04-ago**: resource version **324**. Tier 2 por `lambIdPersona` (verificado: 0 colisiones entre personas distintas en 58.178 Users) + tier 4 `givenName`+`familyName` con peso 0.55 que fuerza `disputed` ante homónimo. Ver [`correlacion-resuelta.md`](correlacion-resuelta.md) | ~~Sí~~ |
| 3 | ~~**Decidir la política de baja en LDAP**~~ → ✅ **RESUELTO 04-ago**: mapping `activation/existence` condicional en `account/default`, resource version **221**. La baja conserva la entrada y la deshabilita; las mudanzas entre OU siguen funcionando. Validado con canario de tres clases, 0 dual-shadows. Ver [`existence-ldap-resuelto.md`](existence-ldap-resuelto.md). `account/alumni` cerrado también (version **222**) | ~~Sí~~ |
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
