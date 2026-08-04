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
