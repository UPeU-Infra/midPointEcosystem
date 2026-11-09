# Nombre oficial de persona desde RENIEC — diseño por etapas

**Slug:** `nombre-oficial-reniec`
**Estado:** DISEÑO — nada desplegado. Cada etapa necesita el visto bueno de DTI/Infra antes de ejecutarse.
**Fecha:** 2026-11-09
**Reemplaza a:** `docs/specs/connector-reniec-midpoint/01-brainstorm.md` (abril 2026, conector en vivo contra apiperu.dev). Ver §8.
**Relacionado:** `DECISION-canonical-identifier.md`, `DECISION-vigencia-temporal-afiliaciones.md`, `IIA-MATRIX.md` §2.1, `runbooks/givenName-collision-fix-2026-06-29.md`, `governance/matriz-fuentes-oracle-lamb.md` (P1/P2).

---

## 1. Por qué

1. **CONCYTEC observó al repositorio de tesis** (nov-2026): el mismo asesor aparece escrito de varias formas. Pide una sola forma oficial por persona, aplicada en todo el repositorio.
2. **Decisión de UPeU (CRAI, 9-nov-2026, con acuerdo de DTI/Infra): el nombre oficial es el del DNI**, tal como lo registra RENIEC (con sus tildes o sin ellas, con apellido de casada), solo pasado de MAYÚSCULAS a altas y bajas.
3. Ya se aplicó en el repositorio de tesis (etapa 2 de asesores, 1 476 valores). Pero si cada sistema (DSpace, DSpace-CRIS, Koha, OJS) resuelve el nombre por su cuenta, volverán a divergir. **La forma oficial debe vivir una sola vez, en MidPoint, y de ahí salir a todos.** Es el primer paso de un control de autoridades de personas para toda UPeU.

## 2. Situación actual (verificada en el repo, 2026-11-09)

| Pieza | Qué hace hoy |
|---|---|
| `givenName` / `familyName` | **Vienen de Lamb** (`trabajadores.xml`, inbound strong único). Fix del 29-jun por colisión de dos strong sobre un ítem single-valued |
| `reniec-cache.xml` | Lee `DAVID.CONSULTA_APIS_LOG`. Nombres en **weak**: solo rellena si el foco no tiene valor. Es strong para `dataQualityStatus`, `reniecValidationDate` y `birthDate` |
| `dataQualityStatus` | `reniec_validated` = hay consulta RENIEC y el apellido calza. **No** significa que el nombre visible sea el de RENIEC |
| LDAP | Publica `upeuDataQualityStatus` y `upeuReniecValidationDate` (clase `upeuPerson`) |
| `sciback-person-v1.0.xml` | Trae `identityDocuments[].verifiedBy` / `verifiedAt`, sin recurso que los llene |

**Premisa a corregir:** el comentario de `reniec-cache.xml` dice que RENIEC «entrega el nombre sin diacríticos, degradando el dato». Medido el 9-nov: RENIEC devuelve lo que figura en el DNI. Hay DNI con tildes («HERNÁNDEZ», «JOSÉ», 5 de 5 iguales a la caché) y DNI sin ellas («RODRIGUEZ»). Con la decisión del §1, que el DNI no lleve tilde **no es degradar: es el dato oficial**.

## 3. Alcance de esta etapa: solo personas ACTIVAS

Para no gastar consultas en quien ya no está en UPeU:

- **Dentro:** trabajadores con contrato vigente y estudiantes con matrícula vigente, con el mismo criterio de vigencia que usan los recursos (`DECISION-vigencia-temporal-afiliaciones.md`).
- **Fuera, para otra etapa:** egresados sin matrícula vigente, ex trabajadores y jubilados.
- **Fuera siempre de RENIEC:** carné de extranjería, PTP, CPP y pasaporte. RENIEC solo cubre DNI (Ley 26497). Su nombre sigue saliendo de Lamb.

### Medición (Oracle, solo lectura, 2026-11-09)

Activos = `ELISEO.VW_APS_EMPLEADO` (`ID_ENTIDAD=7124`, `ESTADO='A'`, sin término o término futuro) ∪ `DAVID.ACAD_ALUMNO_CONTRATO` con módulo de `FECHA_FIN >= hoy`. Es una aproximación del criterio de los recursos, suficiente para dimensionar.

| Grupo | Personas | Con DNI | Otro documento | Ya en caché RENIEC | Consultados el 9-nov (asesores) | **Faltan** |
|---|---|---|---|---|---|---|
| Trabajadores activos | 3 867 | 3 810 | 57 | 611 | 328 | **2 871** |
| Estudiantes activos (no trabajadores) | 17 954 | 17 787 | 166 | 4 248 | 8 | **13 531** |
| **Total** | 21 821 | 21 597 | 223 | 4 859 | 336 | **16 402** |

Trampa medida: `MOISES1.VW_PERSONA_NATURAL` tiene varias filas por persona (DNI más tipos 97/98, 6, 4…). Hay que preferir `ID_TIPODOCUMENTO IN (1,24)`; tomar cualquier fila da 477 trabajadores con DNI en vez de 3 810.

**Costo:** cada consulta se paga y el saldo contratado **es compartido con admisión**. Los 16 402 pendientes serían más de la mitad del saldo disponible en noviembre de 2026. Por eso va por etapas y con aprobación en cada una.

## 4. Principios

1. **Nunca una consulta pagada desde MidPoint.** Un conector en vivo consultaría en cada recompute, importación o reconciliación y gastaría sin control. MidPoint **solo lee la caché**. Las consultas las hace un proceso por lotes, fuera de MidPoint, aprobado lote a lote.
2. **MidPoint es la fuente del nombre oficial (decisión 2026-11-09).** Es la consulta más actualizada y desde él se actualizan los demás sistemas (LDAP, M365, Koha, certificados y diplomas, DSpace, CRIS, OJS). Para mejorarlo, en este orden:
   1. Cargar en MidPoint lo ya verificado contra RENIEC (p. ej. los 694 asesores del 9-nov, hoy en la tabla `dniruc_asesores_20261109` del repositorio).
   2. `DAVID.CONSULTA_APIS_LOG`: la caché RENIEC que alimenta admisión, sin costo. Conviene además que lo consultado fuera se registre ahí (pedido a DTI Desarrollo), pero **no es requisito** para cargarlo en MidPoint.
   3. La API de pago: **solo en casos extremos y urgentes**, con aprobación expresa y lote por lote.
3. **No repetir consultas.** Si el DNI ya está en la caché con `STATUS='S'`, no se consulta. La caché no caduca para el nombre; solo se revalida a pedido (cambio de apellido por matrimonio, corrección en RENIEC).
4. **Minimizar datos (Ley 29733).** La API devuelve foto, dirección, padres, estado civil y fecha de nacimiento. Para este fin solo se usan apellidos y nombres. Qué guarda la caché lo decide DTI, no este proceso.
5. **Lamb sigue siendo la fuente que crea a la persona.** RENIEC solo fija la forma oficial del nombre de quien tiene DNI.

## 5. Cambio en MidPoint (sin consultas: costo cero)

Hoy chocan dos inbounds strong sobre un ítem single-valued (runbook del 29-jun). En vez de invertir los strong, **el nombre se resuelve en un solo lugar: el object template**, con prioridad explícita:

1. Si hay nombre RENIEC (caché) para el DNI primario → se usa ese, en altas y bajas (`sb-name-normalizer`, misma regla que en tesis: partículas `de`, `del`, `la`… en minúscula).
2. Si no → el de Lamb, como hoy.

Para eso los dos recursos dejan de escribir `givenName`/`familyName` y escriben a extensiones de transporte (`upeu:lambGivenName`, `upeu:lambFamilyName`, `upeu:reniecGivenName`, `upeu:reniecFamilyName`). El template elige. Así no hay dos strong sobre el mismo ítem.

Además:
- `identityDocuments[DNI].verifiedBy = RENIEC` y `verifiedAt = FECHA_REGISTRO` (vocabulario canónico que ya existe).
- `dataQualityStatus` gana un valor: `reniec_name` = el nombre visible ES el de RENIEC. `reniec_validated` se mantiene para el caso actual.
- Se corrige el comentario de `reniec-cache.xml` (§2).

**Efecto inmediato sin gastar nada:** cambian de nombre los activos que ya están en la caché o se consultaron el 9-nov: **5 195 personas** (4 859 + 336). Antes de activarlo, un informe con cuántos cambian y de qué tipo (solo tildes, apellido de casada, letras distintas), igual que en tesis.

## 6. Etapas

| Etapa | Qué | Consultas a la API | Condición para pasar a la siguiente |
|---|---|---|---|
| **E0** | Cargar en MidPoint los nombres ya verificados contra RENIEC (694 del 9-nov) por un recurso CSV de solo lectura «RENIEC verificados», inbound a las extensiones de transporte del §5 (deja auditoría y origen). En paralelo, pedir a DTI Desarrollo que los registre en `CONSULTA_APIS_LOG` | 0 | Valores cargados en el lab y luego en producción |
| **E1** | Cambio del §5 en el lab, informe de impacto, luego producción | 0 | Visto bueno de DTI/Infra al informe; 0 errores de recompute |
| **E2** | Trabajadores activos sin nombre RENIEC: esperar a que la caché los cubra. Con la API de pago **solo si es extremo y urgente**, en lotes de ~500, docentes primero | 0 por defecto (máx. ~2 871) | Aprobación de DTI/Infra **por lote** |
| **E3** | Estudiantes activos: la caché los irá cubriendo (admisión). API de pago solo en caso extremo y urgente | 0 por defecto (máx. ~13 531) | Ídem, y decisión de la Dirección DTI sobre el gasto |
| **E4** (otra etapa) | Egresados, ex trabajadores, jubilados | por medir | Proyecto aparte |
| **E5** | Publicar la autoridad a los consumidores (§7) | 0 | E1 en producción |

La caché crece sola: admisión consulta a cada ingresante desde enero de 2025, por eso 4 248 estudiantes activos ya están. **Antes de cada lote de E3 se vuelve a medir**: lo que admisión haya consultado entre tanto ya no se paga.

### Proceso por lotes (E2, E3)

Script fuera de MidPoint, en el repo (`upeu/scripts/`), con lo aprendido el 9-nov:
- Lista = activos con DNI − caché − ya consultados. Tope duro por ejecución.
- Una consulta por segundo. Vigila `data.count` (saldo) en cada respuesta, como pidió DTI Desarrollo, y se detiene si baja más de lo esperado o hay 3 errores seguidos.
- Reanudable, sin repetir DNI.
- Los DNI sin resultado (HTTP 404, no se cobran) quedan anotados para no reintentarlos.
- Resultado → `CONSULTA_APIS_LOG` (vía DTI Desarrollo). MidPoint lo toma en la siguiente importación de `reniec-cache`.

## 7. Hacia una autoridad de personas para toda UPeU (E5, esbozo)

Identificador: el **código institucional** (`name`), no el DNI (`DECISION-canonical-identifier.md`). Junto a él: nombre oficial, ORCID, ISNI (ya en el esquema LDAP, `01-schema-isni.ldif`).

| Consumidor | Cómo usaría la autoridad |
|---|---|
| DSpace (tesis) | Autoridad nativa (`ChoiceAuthority`): al depositar, el asesor se elige de la lista y se guarda su identificador |
| DSpace-CRIS | Entidades Persona creadas y actualizadas desde MidPoint |
| Koha | Registros de autoridad MARC (100 + 024 con ORCID e identificador UPeU), solo autores UPeU |
| OJS | Sin autoridades nativas: ORCID, y cruce de autores UPeU por ORCID |

Detalle en una especificación propia cuando E1 esté en producción.

## 8. Por qué se descarta el borrador de abril

`connector-reniec-midpoint/01-brainstorm.md` proponía un conector ConnId en vivo contra apiperu.dev. Se descarta:
- apiperu.dev es una cuenta personal, «no usar para producción UPeU», y según la matriz de fuentes usa el registro de SUNAT, no RENIEC directo.
- UPeU ya paga un proveedor de consultas DNI y ya tiene la caché que alimenta admisión.
- Un conector en vivo contradice el principio 1 (§4): gasto sin control.

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| Cambiar el nombre visible de miles de personas a la vez | E1 con informe previo y en el lab primero |
| Nombre RENIEC sin tildes que la persona sí usa | Es la regla decidida (§1). Las excepciones las resuelve el CRAI o RR. HH., con `dataQualityStatus=manual_override` |
| Consumir el lote compartido con admisión | Aprobación por lote; medir antes de cada lote; tope duro |
| DNI equivocado en Lamb (en tesis hubo 221 casos) | Si el apellido de RENIEC no calza con el de Lamb → `mismatch`, no se cambia el nombre, va a revisión |
| Datos sensibles de la respuesta | Solo apellidos y nombres en este proceso (§4.4) |

## 10. Pendientes para decidir

1. Visto bueno a E0 (recurso CSV en el lab) y al pedido a DTI Desarrollo para `CONSULTA_APIS_LOG`.
2. Visto bueno a E1 (diseño del §5) para prepararlo en el lab.
3. Tamaño de lote y ritmo para E2.
4. Si E3 se hace, cuánto del lote se le asigna (Dirección DTI).
