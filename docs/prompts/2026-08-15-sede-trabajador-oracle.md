# Dos consultas a Oracle LAMB — sede de trabajador (18 personas) e identidades sin fuente (26)

**Para:** sesión con acceso a Oracle LAMB (`192.168.13.9/UPEU`)
**De:** la sesión del IGA (MidPoint)
**Fecha:** 15-ago-2026 (ampliado el 16-ago con el encargo B)
**Regla que no se toca:** **Oracle LAMB es de SOLO LECTURA. Política absoluta.** Aquí solo se
consulta; ningún `UPDATE`, `INSERT` ni `DELETE`, ni siquiera "de prueba".

Son dos encargos independientes; pueden resolverse por separado:

- **A — sede de trabajador:** 3 trabajadoras en activo sin carné porque el IGA no sabe su sede.
- **B — identidades sin fuente:** 26 personas que MidPoint tiene como estudiantes activos y no
  aparecen en ninguna tabla de Oracle. Hay que decidir si existen.

---

# ENCARGO A — de dónde sale la sede de un trabajador

## Qué se necesita

**3 trabajadoras en activo no pueden obtener carné de biblioteca** porque el IGA no sabe en qué
sede trabajan. Koha exige `library_id` (la sucursal: BUL, BUJ, BUT, CIA) para crear un patron, y
sin campus el alta se rechaza:

```
400 {"errors":[{"message":"Missing property.","path":"/body/library_id"}]}
```

Hace falta **saber de qué columna de Oracle sale la sede de un trabajador cuando las vías
actuales fallan**, para poder añadirla a la consulta del resource.

## Las 3 personas (y las otras 15)

| COD_APS | ID_PERSONA | NUM_DOCUMENTO | Nombre | Estado |
|---|---|---|---|---|
| `70071601` | `4056920` | 70071601 | Yessenia Luz Damian Cordova | `A` activo, categoría 3 |
| `73127501` | `4055269` | 73127501 | Ana Cristina Llancari Torre | `A` activo, categoría 3 |
| `92589986` | `9054` | **74738644** | Titi Anelit Carrasco Fasanando | `A` activo, categoría 3 |

Las tres tienen `liveAffiliationWorker=staff`, `hireDate` y `employmentContractCode` en el IGA:
son trabajadoras reales, no residuos.

Otras **15 personas** tienen el mismo problema pero ya no están activas (12 archivadas con
patron ya creado, 3 activas que sí lo tienen), así que el impacto se concentra en estas 3.
Sus documentos, por si sirven para el diagnóstico: `02530108`, `06672032`, `10298095`,
`41371678`, `47632350`, `61296848`, `70672417`, `71231962`, `71619566`, `72914004`, `73045489`,
`74866683`, `75778245`, `80617454`, `80830945`.

## Cómo obtiene hoy la sede el IGA (y por dónde puede fallar)

El `searchScript` del resource **Trabajadores** (`upeu/resources/oracle-lamb/trabajadores.xml`)
la resuelve por **dos vías**, y se queda con la primera que dé resultado:

```sql
COALESCE(osc.NOMBRE, os.NOMBRE) AS SEDE_NOMBRE
```

**Vía 1 — la sede del puesto del trabajador:**
```sql
LEFT JOIN ELISEO.ORG_SEDE_AREA osa ON osa.ID_SEDEAREA = t.ID_SEDEAREA
LEFT JOIN ELISEO.ORG_SEDE     os  ON os.ID_SEDE      = osa.ID_SEDE
```
Falla si `ENOC.VW_TRABAJADOR.ID_SEDEAREA` viene `NULL`.

**Vía 2 — la sede deducida del departamento del contrato:**
```sql
LEFT JOIN (
  SELECT cc2.COD_APS, ds.ID_SEDE AS CONTRACT_SEDE
  FROM ( ... contrato vigente por COD_APS, con ID_DEPTO ... ) cc2
  LEFT JOIN (
      SELECT ID_DEPTO, MIN(ID_SEDE) AS ID_SEDE
      FROM ELISEO.ORG_SEDE_AREA
      WHERE ESTADO = '1' AND ID_DEPTO IS NOT NULL
      GROUP BY ID_DEPTO
      HAVING COUNT(DISTINCT ID_SEDE) = 1        -- ← SOSPECHOSO
  ) ds ON ds.ID_DEPTO = cc2.ID_DEPTO
) cs ON cs.COD_APS = e.COD_APS
LEFT JOIN ELISEO.ORG_SEDE osc ON osc.ID_SEDE = cs.CONTRACT_SEDE
```

**La hipótesis principal está en ese `HAVING COUNT(DISTINCT ID_SEDE) = 1`:** el departamento
solo resuelve a sede si existe en **una sola** sede. Un departamento presente en Lima y Juliaca
a la vez devuelve `NULL` a propósito, para no adivinar. Si además la persona no tiene
`ID_SEDEAREA` propio, se queda sin sede por las dos vías.

Encaja con algo ya conocido en este proyecto: hay **orgs multi-sede** que dieron problemas al
recomputar el árbol organizativo el 6-ago.

## Qué comprobar (todo `SELECT`)

**1. Confirmar por dónde falla cada una de las tres:**
```sql
SELECT e.COD_APS, t.ID_SEDEAREA, osa.ID_SEDE AS SEDE_POR_PUESTO, os.NOMBRE AS NOMBRE_POR_PUESTO
FROM ELISEO.VW_APS_EMPLEADO e
JOIN ENOC.VW_TRABAJADOR t ON t.ID_PERSONA = e.ID_PERSONA
LEFT JOIN ELISEO.ORG_SEDE_AREA osa ON osa.ID_SEDEAREA = t.ID_SEDEAREA
LEFT JOIN ELISEO.ORG_SEDE      os  ON os.ID_SEDE      = osa.ID_SEDE
WHERE e.COD_APS IN ('70071601','73127501','92589986');
```

**2. Ver su departamento de contrato y a cuántas sedes resuelve:**
```sql
SELECT cc.COD_APS, cc.ID_DEPTO,
       COUNT(DISTINCT osa.ID_SEDE) AS SEDES_DEL_DEPTO,
       LISTAGG(DISTINCT osa.ID_SEDE, ',') WITHIN GROUP (ORDER BY osa.ID_SEDE) AS CUALES
FROM ( /* el mismo subquery de contrato vigente del searchScript */ ) cc
LEFT JOIN ELISEO.ORG_SEDE_AREA osa ON osa.ID_DEPTO = cc.ID_DEPTO AND osa.ESTADO = '1'
WHERE cc.COD_APS IN ('70071601','73127501','92589986')
GROUP BY cc.COD_APS, cc.ID_DEPTO;
```
Si `SEDES_DEL_DEPTO > 1`, la hipótesis queda confirmada.

**3. Y la pregunta de fondo — ¿hay otra columna con la sede?** Buscar en las tablas de RR.HH.
cualquier campo de sede/filial/local que hoy no se esté usando:
```sql
SELECT owner, table_name, column_name
FROM all_tab_columns
WHERE owner IN ('ELISEO','ENOC','DAVID','MOISES')
  AND (column_name LIKE '%SEDE%' OR column_name LIKE '%FILIAL%'
       OR column_name LIKE '%CAMPUS%' OR column_name LIKE '%LOCAL%')
ORDER BY owner, table_name, column_name;
```
Interesa sobre todo si el **contrato** (`ELISEO`, tablas de contrato/planilla) lleva su propia
sede: sería la fuente más fiable, porque la sede del contrato es la que manda.

**4. Cuántos hay en total.** Si la causa es el `HAVING`, conviene saber el tamaño real del
problema y no solo estos 18 —que son los que llegaron a intentar escribir en Koha—:
```sql
-- trabajadores activos sin sede por ninguna de las dos vías
```

## Qué se busca como respuesta

1. **Por qué** estas 3 no resuelven sede (vía 1, vía 2, o ambas).
2. **Si existe una columna mejor** —idealmente la sede del contrato— para añadir como tercera
   vía en el `COALESCE`.
3. **Cuántos trabajadores activos** están en la misma situación.
4. Si no hay ninguna columna fiable: **cuál es la sede real de estas 3 personas**, preguntando a
   RR.HH. si hace falta, para desbloquearlas a mano mientras se arregla el origen.

## Contexto útil

Este mismo problema se resolvió el 11-ago para los egresados: faltaba `campusEgreso` y Koha
rechazaba el alta con este error exacto. Se pobló para 4.685 personas y el canal se desatascó.
Aquí es el equivalente para trabajadores.

El mapping del IGA **ya avisa** cuando no puede resolverlo, con nombre y apellidos en el log:
```
WARN koha library_id: campus no resuelto para 02530108 (cs=null, cw=null, ce=null, loc=null) -> sin branch
```
`cs`=campusStudent, `cw`=campusWorker, `ce`=campusEgreso, `loc`=ubicación. En las 18 personas,
**las cuatro vienen null**.

---

# ENCARGO B — 26 identidades que MidPoint tiene y Oracle no

## Qué son

**26 personas figuran en MidPoint como estudiantes `active`, con rol `BR-Estudiante-Pregrado`,
y no tienen shadow de NINGUNA fuente Oracle** — ni Estudiantes, ni Trabajadores, ni Egresados.

No nacieron del MDM: las creó MidPoint **desde el Koha viejo**, a partir de patrons que existían
en el ILS pero no en la fuente autoritativa.

| Creadas | Canal | n |
|---|---|---|
| 2026-05-27 | `reconciliation` | 20 |
| 2026-06-05 | `import` | 6 |

## Por qué importa

La cadena de consecuencias ya está medida:

1. sin origen en Oracle → sin `ID_PERSONA` → **`extension/sciback:externalSystemId` nulo**;
2. `cardnumber` de Koha se alimenta de ese campo → **patron sin carné** (son 26 de los 33.717
   del Koha consolidado, es decir, prácticamente todos los que están así);
3. y como no están en ninguna fuente, **ninguna reconciliación las toca**: se quedan `active`
   indefinidamente, con lo que traían de mayo. No fallan; son invisibles.

Mientras no se resuelva, cualquier intento de darles servicio produce un patron inútil (sin
`cardnumber` no hay préstamo).

## Los 26 códigos

```
202310206  202410977  202420956  202514113  202610070  202610078  202610079  202610618
202612606  202612713  202612761  202612812  202612813  202612834  202613145  202613206
202613778  202614152  202614283  202614339  202614346  202614468  324103441  324105266
324105410  324105420
```

Los que empiezan por `3241…` son de la serie que en otros contextos corresponde a códigos de
posgrado/otra numeración; conviene no asumir que los 26 son del mismo tipo.

## Qué comprobar (todo `SELECT`)

**1. ¿Existen con ese mismo código?**
```sql
SELECT COD_ALUMNO, ID_PERSONA, NUM_DOCUMENTO, ESTADO
FROM <tabla de alumnos>            -- la que alimenta el resource Estudiantes
WHERE COD_ALUMNO IN ('202310206','202410977', /* … los 26 … */);
```

**2. Si no aparecen por código: ¿existen como PERSONA por documento?** El IGA no tiene su DNI
(nunca lo recibió de Oracle), pero sí lo tiene Koha. Si hace falta, se puede extraer del ILS y
mandarlo en una segunda vuelta — **decirlo y se envía**, no hace falta adivinar.

**3. ¿Hubo matrícula alguna vez?** Aunque hoy no estén activos, saber si estuvieron matriculados
distingue dos casos muy distintos: *ex-alumno que ya no está* frente a *persona que nunca estuvo
en el MDM* (por ejemplo, un usuario externo de biblioteca dado de alta a mano en Koha años
atrás).

## Qué se busca como respuesta

Para cada uno de los 26, cuál de estos tres es:

1. **Está en Oracle con otro código** → hay que correlacionarlo en el IGA y recuperará su
   `ID_PERSONA` y su carné.
2. **Estuvo y ya no** → corresponde darlo de baja en el IGA; hoy sigue `active` por inercia.
3. **Nunca estuvo en Oracle** → es una identidad que solo existió en la biblioteca. Decisión de
   producto: o se le da un origen legítimo, o se retira. Un IGA no debería sostener identidades
   que su fuente autoritativa desconoce.

Con eso el IGA puede cerrar el caso; sin eso, cualquier acción es adivinar.
