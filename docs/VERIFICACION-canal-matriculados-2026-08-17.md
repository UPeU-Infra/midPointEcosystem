# El canal de matriculados llega a Koha — verificación de punta a punta (17-ago-2026)

Pregunta que originó la medición: **¿los matriculados recientes están pasando a Koha?**

## Respuesta: sí, sin pérdidas

Usuarios creados en el IGA en los **últimos 14 días**, con su cobertura en los dos destinos:

| Alta en el IGA | Estudiantes `active` | En Koha | En LDAP |
|---|---|---|---|
| 09-ago | 8 | 8 | 8 |
| 10-ago | 19 | 19 | 19 |
| 11-ago | 148 | 148 | 148 |
| 12-ago | 82 | 82 | 82 |
| 13-ago | 6 | 6 | 6 |
| 14-ago | 126 | 126 | 126 |
| 15-ago | 30 | 30 | 30 |
| 16-ago | 5 | 5 | 5 |
| 17-ago | 1 | 1 | 1 |
| **Total** | **425** | **425** | **425** |

**425 de 425.** Lo mismo para el personal del período: 8 `staff` (6 con Koha + LDAP, 2 solo LDAP — son los del `library_id` sin campus) y 1 `faculty` completo.

La cadena Oracle → MidPoint → Koha/LDAP funciona sin intervención: el aprovisionamiento ocurre
como efecto de las reconciliaciones diarias de LAMB, no hace falta nada más.

## El lote de 1.157 que parece un problema y no lo es

En la misma medición aparecen **1.157 fichas creadas el 14-ago** en `lifecycleState=draft`, sin
Koha, sin LDAP y con **0 assignments**. A primera vista es idéntico al patrón de los congelados
por el `existence`
(ver [`pendientes/2026-08-15-existence-ldap-congela-personas.md`](pendientes/2026-08-15-existence-ldap-congela-personas.md)).

No lo es. Las **1.157 tienen shadow de Oracle Estudiantes**, y sus datos de matrícula lo
explican — muestra de 15, espaciada a lo largo del lote:

```
202520626 | DATE_EXPIRY 2025-12-19 | TIPO_ALUMNO RE
202015469 | DATE_EXPIRY 2025-11-28 | TIPO_ALUMNO RE
321200059 | DATE_EXPIRY 2025-11-30 | TIPO_ALUMNO RE
…  15 de 15 con la vigencia CADUCADA
```

Son antiguos alumnos que el feed devuelve por historial: el IGA los reconoce, no les concede
afiliación viva, y por eso **no les da carné ni cuenta de directorio**. Es el comportamiento
correcto — dar carné de biblioteca a quien ya no está matriculado sería el error contrario.

### Cómo distinguir un congelado de una vigencia caducada

Los dos se ven igual desde `m_user` (`draft`/`archived`, 0 assignments, sin `primaryAffiliation`).
La diferencia está en el shadow de la fuente:

| | Congelado por el `existence` | Vigencia caducada |
|---|---|---|
| Shadow de la fuente Oracle | puede faltar o estar sin procesar | **está, y con datos completos** |
| `DATE_EXPIRY` | vigente | **en el pasado** |
| Qué corresponde hacer | corregir el mapping y reprocesar | **nada: el estado es correcto** |

Antes de tratar un lote de `draft` como avería, leer `DATE_EXPIRY` del shadow de origen.

## De dónde salió el lote

Se crearon el **14-ago**, el día en que se corrigió el `category_id` de Koha y la reconciliación
de Estudiantes pasó de 9.962 fallos a 613 — el porqué de esa corrección está escrito en el
propio mapping, en [`upeu/resources/koha-upeu.xml`](../upeu/resources/koha-upeu.xml)
(`category-id-from-primary-affiliation`). Al desatascarse el canal, procesó filas que hasta
entonces abortaban y creó estas fichas. Encaja con las fechas, aunque **no está probado**.

## Cómo se midió

```sql
-- cobertura de los nuevos por destino
WITH nuevos AS (
  SELECT u.oid, date(u.createTimestamp) AS creado, u.lifecycleState AS lc, u.ext->>'78' AS prim,
         EXISTS (SELECT 1 FROM m_ref_projection r JOIN m_shadow s ON s.oid=r.targetoid
                 WHERE r.owneroid=u.oid AND s.resourceRefTargetOid='e10a539a-cb7f-4c72-a19f-60f7f62e4b96') AS en_koha,
         EXISTS (SELECT 1 FROM m_ref_projection r JOIN m_shadow s ON s.oid=r.targetoid
                 WHERE r.owneroid=u.oid AND s.resourceRefTargetOid='7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f') AS en_ldap
  FROM m_user u WHERE u.createTimestamp > now() - interval '14 days'
)
SELECT creado, lc, coalesce(prim,'-'), en_koha, en_ldap, count(*)
FROM nuevos GROUP BY 1,2,3,4,5 ORDER BY 1,3;
```

Recordatorio de OIDs, que es fácil equivocarse: Koha consolidado es
`e10a539a-cb7f-4c72-a19f-60f7f62e4b96` — **no** `e10a539a-6c31-…`, que no existe y devuelve
`false` en toda la columna sin avisar.
