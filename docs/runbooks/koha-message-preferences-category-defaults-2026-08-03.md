# Runbook — Defaults de mensajería por categoría en Koha (2026-08-03)

## Contexto

Config **pura de Koha** (`koha_upeu`@`192.168.12.136`, alias secreto
`~/.secrets/koha-plus-prod.env` — **no** confundir con `koha-prod.env`, que es el
Koha viejo archivado). No toca MidPoint, el conector ni ningún `ResourceType`.

Confirmado antes del cambio: `SELECT COUNT(*) FROM borrower_message_preferences
WHERE borrowernumber IS NULL` = **0**. Nunca existió una plantilla de mensajería
por defecto para ninguna `categorycode`. Cada patron nuevo (altas por API del
conector MidPoint→Koha, LDAP auth, import, OPAC self-registration) se crea sin
ninguna preferencia de notificación activa — Alberto tuvo que marcarlas a mano en
su propia cuenta (`borrowernumber=1632`, Piero).

Evidencia cuantitativa de gap: de las 340.213 filas `borrower_message_preferences`
con `borrowernumber` ya existentes antes del cambio, solo **5** tenían una fila en
`borrower_message_transport_preferences` (las 5 de Piero). El resto de patrons
tenía el esqueleto de 13 filas (una por `message_attribute_id`) sin ningún
transporte — es decir, notificaciones activadas en absolutamente 0 casos reales.

## Qué se hizo

Se crearon defaults por **categoría** (`borrowernumber IS NULL`,
`categorycode = <cada una de las 7 categorías reales>`) replicando exactamente el
patrón manual de Piero:

**Email ON** (5 tipos):

| `message_attribute_id` | `message_name` | `days_in_advance` |
|---|---|---|
| 1 | Item_Due | NULL |
| 2 | Advance_Notice | 1 |
| 5 | Item_Check_in | NULL |
| 6 | Item_Checkout | NULL |
| 9 | Auto_Renewals | NULL |

**Sin default** (quedan apagados, igual que Piero): `Hold_Filled` (4),
`Hold_Reminder` (10), `Ill_ready` (7), `Ill_unavailable` (8), `Ill_update` (11),
`Recall_Waiting` (12), `Recall_Requested` (13), `Patron_Expiry` (14).

Categorías reales verificadas en `categories` (no asumidas): `affiliate`, `alum`,
`faculty`, `LOCAL` (cuenta técnica/servicio), `staff`, `student`, `WALKIN`
(visitante). 7 categorías × 5 tipos = **35 filas** en
`borrower_message_preferences` + 35 en `borrower_message_transport_preferences`
(`message_transport_type='email'`).

SQL ejecutado (idéntico patrón repetido por categoría, ejemplo `student`):

```sql
INSERT INTO borrower_message_preferences
  (borrowernumber, categorycode, message_attribute_id, days_in_advance, wants_digest)
VALUES (NULL, 'student', 2, 1, 0);
INSERT INTO borrower_message_transport_preferences
  (borrower_message_preference_id, message_transport_type)
VALUES (LAST_INSERT_ID(), 'email');
```

Ejecutado dentro de una única transacción (`START TRANSACTION; ... COMMIT;`) vía
`sudo mysql koha_upeu` en el propio host (`192.168.12.136`), no vía el usuario
`koha_connector` (ese usuario JDBC no tiene `SELECT`/`INSERT` sobre estas tablas de
config, solo sobre las que usa el conector — confirmado con
`ERROR 1142 SELECT command denied`).

## Verificación

1. **35 filas creadas, con el transporte correcto** — confirmado por query directa
   post-cambio (`categorycode`, `message_attribute_id`, `days_in_advance`,
   `message_transport_type` para las 35 combinaciones).
2. **Ningún patron existente tocado.** `borrower_message_preferences` pasó de
   340.213 a 340.248 filas con `borrowernumber` (sin cambio) + 35 nuevas con
   `borrowernumber IS NULL`. Las 13 filas de Piero (`borrower_message_preference_id`
   340273–340285) quedaron con el mismo ID y mismo contenido — no se regeneraron ni
   se tocaron.
3. **Prueba end-to-end con patron real vía la misma API que usa el conector
   MidPoint** (`POST /api/v1/patrons`, OAuth2 client-credentials,
   `~/.secrets/koha-plus-prod.env`): se creó un patron desechable
   (`categorycode=WALKIN`, sin email, `AutoEmailNewUser=0` y
   `EmailPatronRegistrations=0` confirmados en `systempreferences` para garantizar
   que no se disparara ningún correo). Resultado: Koha generó automáticamente las
   13 filas de `borrower_message_preferences` para el nuevo `borrowernumber`,
   **con los 5 tipos correctos en `email`** (idéntico patrón a Piero) y el resto
   sin transporte. Patron de prueba **borrado** inmediatamente después
   (`DELETE /api/v1/patrons/{id}`, cascada limpia — 0 filas huérfanas, los 35
   defaults de categoría intactos).

## Por qué esto se aplica automático a las altas nuevas (incluidas las del conector)

Mecanismo interno de Koha (`C4::Members::Messaging::SetMessagingPreferencesFromDefaults`,
`/usr/share/koha/lib/C4/Members/Messaging.pm`): para cada `message_attribute_id`
copia el default de la categoría del patron (`GetMessagingPreferences({categorycode,
message_name})`) hacia el nuevo `borrowernumber`. Se confirmó en
`/usr/share/koha/lib/Koha/REST/V1/Patrons.pm` (`sub add`, el mismo endpoint
`POST /api/v1/patrons` que usa el conector Java ConnId) que esta llamada ocurre
**siempre que la syspref `EnhancedMessagingPreferences` esté activa** — verificado
`=1` en esta instancia. No depende de si el alta se hizo desde la UI del staff, el
OPAC self-registration, LDAP auth (`Auth_with_ldap.pm`), import masivo
(`Patrons/Import.pm`) o la API REST: todas esas rutas llaman a la misma función.
**El conector MidPoint→Koha no necesita ningún cambio** — no hay ninguna llamada
adicional que agregar de su lado.

## Rollback (si hiciera falta)

Los 35 defaults son identificables por `borrowernumber IS NULL` — no colisionan con
ninguna fila de patron real (esas siempre tienen `borrowernumber` seteado):

```sql
DELETE FROM borrower_message_preferences WHERE borrowernumber IS NULL;
-- CASCADE borra automáticamente las filas huérfanas en
-- borrower_message_transport_preferences (FK ON DELETE CASCADE)
```
