# Personas con 2+ correos personales en Entra ID — listado por campus para DTI

**Fecha de la medición:** 2026-08-03 · **Solo lectura**: no se modificó nada en M365, Entra ID,
MidPoint, Koha ni Oracle LAMB.

**Entregable:** `~/Downloads/Entra_Duales_Correo_por_Campus_UPeU_2026-08-03.xlsx`
(no versionado — regenerable con los scripts de esta carpeta).

## Qué se midió

Cuentas habilitadas del tenant `upeu.edu.pe` que comparten el mismo `displayName` y tienen dos o
más buzones personales `@upeu.edu.pe`. El patrón dominante es la nomenclatura vieja sin punto
conviviendo con la canónica: `albinoramos@` + `albino.ramos@`.

Universo: **75.061 cuentas Entra** (tenant completo vía Graph) × **63.214 focos MidPoint** ×
**Oracle LAMB** para la sede de egresados.

## Resultado

| | Casos |
|---|---|
| **Personas con 2+ correos personales** | **533** |
| — LIMA | 413 (43 consolidar · 195 borrar · 175 revisar) |
| — JULIACA | 85 (22 · 46 · 17) |
| — TARAPOTO | 10 (1 · 8 · 1) |
| — sin campus atribuible | 25 (todos focos `archived`, sin código ni DNI) |
| ⚠ Buzón de área mezclado — **no borrar** | 12 |
| ⚠ Homónimos (personas distintas) — **no tocar** | 6 |
| Buzones de área / rol y pools de licencias | 188 |
| **Total grupos detectados** | **739** |

Cobertura de campus: **95%** de las personas (508/533).

## Cascada de campus (columna «Fuente campus» del Excel)

1. `campusStudent` (ext 219) / `campusWorker` (ext 220) de MidPoint — 321 casos.
2. **`DAVID.VW_PERSONA_EGRESADO.SEDE` de Oracle LAMB — 203 casos.** MidPoint solo puebla campus
   para afiliaciones vivas, así que los egresados quedan sin él; la vista de Oracle sí lo tiene
   (`Sede Lima` / `Filial Juliaca` / `Filial Tarapoto`) aunque el resource `egresados.xml`
   **no mapea esa columna**. Ver "Hallazgos" abajo.
3. Atributos de Entra (`officeLocation` / `city` / `department`) — 2 casos. Prácticamente inútil:
   el tenant no tiene esos campos poblados.

## Hallazgos que cambian el criterio respecto al Excel del 2026-06-05

El listado anterior (742 casos) agrupaba **solo por `displayName` normalizado**. Eso produce tres
clases de falso positivo que, si DTI ejecuta "borrar la no usada", causan daño real:

1. **Buzones de área con nombre de persona (12 casos).** `remuneraciones@`, `soporte@`,
   `calidad.facihed@`, `gestiondocumental.crai@` llevan como `displayName` el nombre de quien los
   administra, así que caen en el mismo grupo que su correo personal. Borrar "la que no se usa"
   deja sin buzón a un área. → hoja propia, veredicto *no borrar sin verificar*.
2. **Homónimos reales (6 casos).** Dos personas distintas con el mismo nombre; se confirma porque
   cada correo resuelve a un **DNI diferente** en MidPoint. Mismo patrón ya documentado en
   [`../telegram-alertas-tasks-2026-07-20/listado-11-emails-duplicados-mesa-de-ayuda-2026-07-26.md`](../telegram-alertas-tasks-2026-07-20/listado-11-emails-duplicados-mesa-de-ayuda-2026-07-26.md).
3. **Pools de licencias (6 grupos).** Hasta **53 cuentas** `labuno.01@ … labuno.36@` bajo el
   displayName "Licencia Autodesk". No es una persona con correos duplicados.

Además:

4. **Placeholders numéricos excluidos.** El criterio anterior descartaba solo local-part de 8
   dígitos (DNI); ahora se descarta **cualquier local-part 100% numérico** (`005436990@`,
   `1250062773@` = códigos y CE), alineado con el correlator de `emailAddress` del resource Entra.
5. **10 cuentas propuestas para borrar tienen tokens vivos** — sin login interactivo, pero con
   actividad no-interactiva de ≤30 días: hay un móvil o cliente de correo todavía conectado.
   Borrarlas rompe ese dispositivo sin aviso. Van marcadas en naranja con veredicto
   `BORRAR — con tokens vivos`.

### 🔎 Hallazgo lateral para el modelo IGA (no accionado)

`DAVID.VW_PERSONA_EGRESADO` expone `ID_SEDE` y `SEDE`, pero el `searchScript` de
[`upeu/resources/oracle-lamb/egresados.xml`](../../../upeu/resources/oracle-lamb/egresados.xml)
no las trae (sí trae `NOM_FACULTAD` y `ESCUELA_PROFESIONAL`). Por eso ningún egresado tiene campus
en MidPoint y hubo que ir a Oracle a mano. Si se quiere el campus de alumni disponible en el
modelo, es añadir la columna al `SELECT` y un inbound a `campusStudent` (o a un `campusAlumni`
nuevo). **No se hizo aquí**: toca un resource de producción y excede el encargo.

Las orgs `OU-CAMPUS-LIMA/JULIACA/TARAPOTO` existen en MidPoint pero **no tienen ni un solo usuario
colgado** — son estructurales vacías, no sirven como fuente de campus.

## Cómo regenerar

```bash
# 1) Tenant completo desde Graph (~6 min, 75k cuentas)
source ~/.secrets/upeu-infra.env
python3 entra_pull_campus.py "$MIDPOINT_AZ_TENANT_ID" "$MIDPOINT_AZ_CLIENT_ID" \
  "$MIDPOINT_AZ_CLIENT_SECRET" <scratch>/entra_users.json

# 2) Focos MidPoint (PROD, solo lectura)
sshpass -p "$MIDPOINT_PROD_PASS" ssh midpoint-prod "docker exec midpoint-midpoint_data-1 \
  psql -U midpoint midpoint -c \"COPY (SELECT nameorig, replace(coalesce(ext->>'72',''), \
  'urn:schac:personalUniqueID:pe:DNI:PE:',''), coalesce(ext->>'74',''), coalesce(givennameorig,''), \
  coalesce(familynameorig,''), coalesce(emailaddress,''), coalesce(ext->>'78',''), \
  coalesce(ext->>'219',''), coalesce(ext->>'220',''), lifecyclestate FROM m_user) \
  TO STDOUT WITH CSV HEADER\"" > <scratch>/mp_users.csv

# 3) Sede de egresados desde Oracle (clase OraQ.java compilada en el host PROD, ver más abajo)
#    -> <scratch>/sede_egresados.tsv  (TSV: CODIGO \t SEDE)

# 4) Análisis + Excel
python3 analisis_duales.py && python3 gen_excel.py
```

Para el paso 3, el contenedor `midpoint_server` tiene `ojdbc11` pero **no** `javac`; el host de
PROD sí lo tiene. Se compila en el host y se copia el `.class` con `docker cp`:

```bash
javac -d /tmp/orq /tmp/orq/OraQ.java
docker cp /tmp/orq/OraQ.class midpoint_server:/tmp/OraQ.class
docker exec midpoint_server java -cp /tmp:/opt/midpoint/var/lib/ojdbc11-23.6.0.24.10.jar \
  OraQ 'jdbc:oracle:thin:@192.168.13.9:1521/UPEU' "$ORACLE_USER" "$ORACLE_PASS" "<SELECT>"
```

## Estructura del Excel entregado

`LEEME` · `Resumen` · `LIMA (413)` · `JULIACA (85)` · `TARAPOTO (10)` · `SIN CAMPUS (25)` ·
`OJO buzon de area (12)` · `NO FUSIONAR (6)` · `No personales (188)`.

Las 7 columnas finales de cada hoja (azules) están vacías para que DTI las llene y devuelva el
archivo: `DECISIÓN DTI` (lista desplegable) · `CORREO A CONSERVAR` · `CORREO(S) A BORRAR / ALIAS` ·
`¿EJECUTADO EN M365?` · `FECHA` · `RESPONSABLE` · `OBSERVACIONES`.

## Criterio de "en uso"

Login **interactivo** (la persona escribió su contraseña) en los últimos 90 días. El
no-interactivo no cuenta como uso humano — es refresco de tokens — pero sí se usa como señal de
riesgo antes de borrar (punto 5 de Hallazgos).
