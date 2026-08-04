# 🔴 160 ex-trabajadores conservan sus accesos — bajas sin procesar desde el 25-jul

**Medido:** 2026-08-03 · **Estado:** detectado, **sin remediar** · **Requiere decisión de Alberto**

## Qué pasa

`recon-oracle-lamb-trabajadores-daily` (OID `23b9fde4-6a5f-4c84-9370-0971fb27be73`) está
**SUSPENDIDA desde el 25-jul-2026**. Es el canal por el que MidPoint se entera de las bajas
de personal. Nueve días sin correr.

Medido contra Oracle (`ELISEO.VW_APS_EMPLEADO`, `ID_ENTIDAD=7124`, el mismo criterio que usa
el resource):

| | |
|---|---|
| Contratos terminados desde el 25-jul | **346** |
| De ellos, **bajas reales** (sin ningún otro contrato vivo) | **344** |
| **Siguen `active` en MidPoint** | **161** |
| Ya archivadas | 1 |

Las ~182 restantes no están en MidPoint (documentos de otras entidades o nunca importadas).

## Accesos que conservan esas personas

Roles asignados (medido sobre los que siguen `active`):

| Rol | Personas |
|---|---|
| `AR-LDAP-Person` | **160** |
| `BR-Personal-General` | 160 |
| `AR-Zoom-Pro` | 160 |
| `AR-Indico-User` | 160 |
| `AR-EntraID-User` | 160 |
| `BR-Admin-Area` | 148 |
| `AR-Koha-Patron-Administrativo` | 148 |
| `AR-WiFi-Staff` | 148 |
| `AR-M365-Staff-A3` | 148 |
| `R-Affiliation-Staff` | 148 |

Y proyecciones vivas: **Koha 135**, **Entra ID 40**.

`AR-LDAP-Person` es el más grave: de la cuenta LDAP cuelgan **WiFi 802.1X, InOut, RIMS** y
toda app que haga bind propio. Son 160 personas que ya no trabajan en UPeU y **siguen
entrando a la red y a los sistemas**.

## Cómo se llegó aquí (cadena completa)

1. **25-jul** — la task se suspende tras el incidente del canario de `CANON_KEY`, que creó
   2 Users duplicados auto-aprovisionados a LDAP y Koha reales. Suspenderla fue **correcto**
   en ese momento.
2. **27-jul** — se desactiva el notifier de Telegram por el spam de falsos `partial_error`
   (nag de Evolveum sin `subscriptionIdentifier`). Desde entonces **MidPoint no puede avisar
   de nada**.
3. **25-jul → 03-ago** — 344 bajas se acumulan sin procesar. Nadie se entera: no hay alerta,
   y la task suspendida no llama la atención por sí sola.

Es el mismo patrón que dejó `recon-koha-upeu-daily` 6 días caída: **una suspensión correcta
que nadie revierte, en un sistema que perdió la capacidad de avisar.**

## Decisión pendiente

Reanudar la task procesaría las bajas — pero es exactamente la task que causó el incidente
del 25-jul, y volvería a correr sobre toda la población (7.541 personas con el grace de 730 d).

Opciones, de menor a mayor riesgo:

1. **Recompute acotado a los 161 OIDs** — sin tocar la reconciliación. Aplica la política de
   baja a esas personas concretas. Canario primero. **No resuelve la causa**: mañana habrá
   bajas nuevas sin procesar.
2. **Reanudar la task con el guardarraíl de correlación 2-tier** ya desplegado en PROD (v322,
   commit `7671d8b` del 26-jul), que es justo lo que se creó para evitar el duplicado. Habría
   que verificar que sigue activo antes.
3. **Reanudar sin más** — no recomendado hasta confirmar el guardarraíl.

En cualquier caso, **M0 (la alerta) deja de ser opcional**: sin canal de aviso, esto se
repetirá y volverá a descubrirse por casualidad.

## Verificación reproducible

```sql
-- Oracle: bajas reales desde una fecha
SELECT DISTINCT t.NUM_DOCUMENTO FROM ELISEO.VW_APS_EMPLEADO t
WHERE t.ID_ENTIDAD=7124 AND t.FEC_TERMINO BETWEEN TO_DATE('2026-07-25','YYYY-MM-DD') AND SYSDATE
AND NOT EXISTS (SELECT 1 FROM ELISEO.VW_APS_EMPLEADO v
                WHERE v.ID_ENTIDAD=7124 AND v.NUM_DOCUMENTO=t.NUM_DOCUMENTO
                AND v.ESTADO='A' AND (v.FEC_TERMINO IS NULL OR v.FEC_TERMINO >= SYSDATE));
```

Población de referencia (03-ago): **5.603** personas con contrato vivo; **7.541** incluyendo
el grace de 730 días.

---

## 🔴 CANARIO EJECUTADO (03-ago) — el recompute NO corta el acceso real

Canario: **William Gabriel Ubia Mendez** (`200410157`, DNI 42137188), contrato terminado el
2026-07-31, dual trabajador+egresado. Recompute `full` sobre un único foco.

### En MidPoint: correcto

| Antes (11 roles) | Después (5 roles) |
|---|---|
| `AR-M365-Staff-A3`, `AR-WiFi-Staff`, `AR-Zoom-Pro`, `AR-EntraID-User`, `AR-Indico-User`, `AR-Koha-Patron-Administrativo`, `AR-LDAP-Person`, `BR-Admin-Area`, `BR-Personal-General`, `R-Affiliation-Staff`, `AR-Koha-Patron-Trabajadores` | `BR-Egresado`, `R-Affiliation-Alumni`, `AR-LDAP-Alumni`, `AR-Vendor-Academic-Access`, `AR-Koha-Patron-Trabajadores` |

Cesó como trabajador y quedó como egresado — el comportamiento esperado para un dual.
Version 54 → 56.

### En LDAP: NO se materializó

```
resultStatus = partial_error
"Operation not supported for COD(inetOrgPerson + eduPerson + schacPersonalCharacteristics
 + upeuPerson + schacEntryMetadata + midPointPerson) in resource:7b4e1c2d…"
```

Verificado con `ldapsearch` contra el directorio real:

```
dn: uid=200410157,ou=people,dc=upeu,dc=edu,dc=pe     ← sigue en ou=people
eduPersonPrimaryAffiliation: staff                    ← SIGUE COMO STAFF
eduPersonAffiliation: staff, alum, member
title: Asistente de Entornos Virtuales de Aprendizaje ← conserva el cargo
```

**El recompute cambia MidPoint pero no corta el acceso.** La persona sigue siendo `staff`
en el directorio del que cuelgan WiFi 802.1X, InOut y RIMS.

### Causa: la misma que el dual-shadow

`AR-LDAP-Person` → `AR-LDAP-Alumni` implica mover la entrada de `ou=people` a `ou=alumni`, y
**el outbound de este resource no soporta rename in-place** — exactamente la causa raíz que
`docs/runbooks/ldap-dualshadow-dedup-265/RUNBOOK.md` documenta desde junio y que sigue sin
corregir. El mismo defecto produce dos síntomas distintos: entradas duplicadas al promocionar,
y bajas que no se materializan al cesar.

### Consecuencia para el plan

**La opción 1 (recompute acotado a los 161) queda invalidada como solución.** Aplicarla a los
160 restantes produciría un cambio cosmético en MidPoint —roles retirados— sin cortar un solo
acceso real, y dejaría 160 focos en estado inconsistente con LDAP.

**No se ejecutó sobre nadie más.** El canario queda con los roles ya recalculados en MidPoint
y su entrada LDAP intacta; conviene decidir si se revierte o se deja a la espera del fix.

### Lo que sí cerraría el riesgo

1. **Corregir el outbound `dn`/`uid` del resource LDAP** para que soporte el cambio de rama
   (o modelar alumni sin mover de OU). Es la causa raíz común con el dual-shadow.
2. Mientras tanto, **cortar el acceso donde sí se puede**: deshabilitar la cuenta LDAP
   (`administrativeStatus=disabled`) en vez de moverla — hay que verificar si ese camino
   también choca con `Operation not supported`.

### Decisión sobre el canario (Alberto, 03-ago): **se deja como está**

No se revierte. Los 11 roles de staff que tenía no eran assignments directos sino derivados
del object template desde su afiliación de trabajador; el recompute recalculó su archetype
estructural a `alumni` porque el contrato terminó el 31-jul. Assignments directos actuales:
`archetype-user-alumni`, `AuxAff-Alum`, `BR-Egresado`, `R-Affiliation-Alumni`,
`AR-Koha-Patron-Alumni`, `AR-Koha-Patron-Trabajadores`.

Revertir habría exigido cambiar el archetype estructural (destructivo, libro cap. 8) y
asignar a mano roles antes derivados — y se habría deshecho solo en el siguiente recompute,
porque el dato de origen no cambió. **El estado actual es el correcto según los datos**; el
anterior reflejaba un contrato ya terminado. Su acceso LDAP sigue vivo igual que el de los
otros 160: ni mejor ni peor que antes de la prueba.

---

## 🔴 EL CANAL ESTÁ ROTO EN LAS DOS DIRECCIONES — 3.150 trabajadores vivos NO existen en el IGA

Medido el 03-ago cruzando los **5.603** trabajadores con contrato vivo de
`ELISEO.VW_APS_EMPLEADO` (`ID_ENTIDAD=7124`) contra MidPoint:

| Situación en MidPoint | Personas |
|---|---|
| **NO están** | **3.180** (57 %) |
| `employee-staff` / active | 1.463 |
| `employee-faculty` / active | 852 |
| sin archetype / archived | 49 |
| `alumni` / active | 38 |
| `employee-staff` / archived | 12 |
| `student` / active | 9 |

Y de esos 3.180, comprobado si existen por otra vía:

| | Personas |
|---|---|
| **Sin rastro alguno** (ni User con ese name, ni shadow en ningún resource) | **3.150** |
| Tienen shadow en **otro** resource (entraron como estudiante/egresado) | 26 |
| Son User con `name` = DNI | 1 |

**Es cobertura, no correlación.** No están mal vinculados: no existen. El IGA gobierna
hoy al **43 %** de la plantilla viva.

### Por qué

El canal de Trabajadores lleva semanas sin funcionar en la práctica:

1. `recon-oracle-lamb-trabajadores-daily` **suspendida desde el 25-jul**.
2. Antes de eso arrastraba el bug de `CANON_KEY` duplicado que afectaba a
   **5.573 de 7.379 (75 %)** — ver memoria del 20-jul.

### Consecuencia para todo lo demás

Cualquier control de gobierno construido sobre esta población —certificación de accesos,
ownership, SoD, el outbound de bajas que se arregló hoy— **opera sobre menos de la mitad de
las personas que debería**. No es un problema de diseño de esos controles: es que la
población de entrada está incompleta.

**Esto es lo primero que hay que arreglar del canal de Trabajadores**, antes que las bajas
y antes que reactivar la reconciliación: si se reactiva tal cual, se procesarían bajas de
una población que ya está incompleta.
