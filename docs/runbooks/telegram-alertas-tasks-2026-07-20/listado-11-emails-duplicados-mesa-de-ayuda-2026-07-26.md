# Correos @upeu.edu.pe compartidos entre 2 patrons en Koha (koha-upeu) — para Mesa de Ayuda

**Fecha de la medición:** 2026-07-26 (solo lectura, nada se modificó en Koha, MidPoint, M365 ni Keycloak).
**Encargo:** Frente B (Koha/SSO Keycloak) — insumo para que Mesa de Ayuda contacte a las personas
y/o corrija el dato de origen (Oracle LAMB / M365) según corresponda.

## Nota importante sobre el conteo (léela antes de usar la tabla)

El encargo original (20-jul) diagnosticó **11 grupos / 22 patrons**. Al reproducir la misma
consulta hoy (26-jul) contra `koha_upeu` en vivo, aparecen **13 grupos / 26 patrons**. La
diferencia (+2 grupos) es esperable: las 4 tasks de reconciliación diaria Oracle LAMB→MidPoint→Koha
llevan corriendo automáticamente desde el 21-jul y siguen incorporando gente nueva (ver
`seguimiento-idiomas-import-y-ldap-cleanup-25jul.md`), y esta clase de problema de dato
(colisión de nomenclatura de correo institucional) ya estaba identificada como recurrente, no
como un incidente aislado. **Esta tabla usa el dato de hoy (13/26), que es el vigente y el que
debe trabajar Mesa de Ayuda.**

## Cómo se investigó (fuentes y método)

1. **Koha (`koha_upeu`, 192.168.12.136, solo lectura vía `mysql`):** se reprodujo la consulta de
   emails duplicados sobre `borrowers`, y se revisó `lastseen`, `issues`, `old_issues` y
   `action_logs` de cada uno de los 26 patrons.
2. **Microsoft Entra ID / M365 (tenant real `upeu.edu.pe`, vía Microsoft Graph API con el App
   Registration `MidPoint-IGA-UPeU` / `connector-msgraph`, credenciales en
   `~/.secrets/upeu-infra.env`):** se consultó `signInActivity` (último inicio de sesión real) de
   cada dirección, y se buscó si la "persona perdedora" de cada colisión tiene su **propio** buzón
   real con otra dirección (`$search` por nombre, `startswith` sobre el patrón de correo).
3. **Keycloak (`keyid.upeu.edu.pe`, realm `upeu`, Admin REST):** se localizó la cuenta SSO de cada
   una de las 13 direcciones y se revisaron los `events` tipo `LOGIN` del cliente `koha-upeu`.

## Limitaciones de datos (léelas, son reales, no se inventó ningún dato de actividad)

- **Koha por sí solo NO da ninguna señal de uso para estos 26 patrons.** `lastseen` es `NULL` en
  las 26 filas, `issues` y `old_issues` no tienen ninguna fila para ninguno de los 26
  `borrowernumber` (0 préstamos, nunca). `action_logs` solo registra eventos `MEMBERS
  CREATE`/`MEMBERS MODIFY` — es decir, la sincronización automática MidPoint→Koha, **no** un
  inicio de sesión humano. Conclusión: si el criterio fuera solo Koha, no se podría determinar
  "cuál cuenta se usa más" para ninguno de los 13 grupos — todas están, desde la perspectiva de
  Koha, sin uso.
- **Keycloak (SSO real de `biblioteca.upeu.edu.pe`) tiene retención de eventos de solo 7 días**
  (`eventsExpiration=604800`). Se confirmó que el logging SÍ funciona (se ve un login real de otra
  persona ajena a este listado, `silvia.pizango@upeu.edu.pe`, el 24-jul). Pero **ninguna de las 13
  identidades de este listado tiene un evento `LOGIN` contra el cliente `koha-upeu` en la ventana
  disponible** — es decir, en los últimos 7 días ninguna ha iniciado sesión real al portal de
  biblioteca vía SSO institucional.
- **Por lo tanto, "cuál correo es el más usado" en este informe se basa en `signInActivity` de
  M365/Entra ID** (inicio de sesión real al correo institucional, no a Koha) — es la única fuente
  con señal de actividad real disponible. Se reporta explícitamente cuando una cuenta **nunca ha
  iniciado sesión** (M365 no devuelve el objeto `signInActivity` en absoluto para esas cuentas).
- No se consultó Oracle LAMB para obtener el DNI de cada persona (para no ampliaguar el alcance de
  solo-lectura innecesariamente); la identificación se hizo por **nombre completo + código
  institucional**, que es consistente entre Koha, MidPoint/Oracle y Keycloak (mismo valor en las
  3 fuentes en todos los casos revisados).

---

## Tabla completa (13 grupos / 26 patrons)

| # | Correo compartido | Persona A (código) | Persona B (código) | Clasificación | Dueño real del correo (M365) | Última actividad M365 | Recomendación |
|---|---|---|---|---|---|---|---|
| 1 | `ariana.rivera@upeu.edu.pe` | Rivera Venturi, Ariana Valentina (202511572) | Rivera Maguiña, Ariana Ester (202610594) | Personas distintas — colisión de nomenclatura | **Rivera Venturi** | 2026-07-21 (interactivo) / 2026-07-22 | Correo queda con Rivera Venturi. Rivera Maguiña **ya tiene su propio buzón real y distinto**: `ariana.rivera94@upeu.edu.pe` (activo, últ. uso 2026-06-24) — corregir el dato de origen (Oracle/Koha) a esa dirección. |
| 2 | `brigith.p.fernandez@upeu.edu.pe` | Pilco Fernandez, Brigith Naydelyn (est. 202510986) | Fernandez Pilco, Veronica (personal, 43651663) | Personas distintas — colisión de nomenclatura | **Pilco Fernandez, Brigith** | 2026-07-25 (no interactivo, la más reciente de los 26) | Correo queda con Brigith Pilco Fernandez. **No se encontró ningún buzón M365 propio para Veronica Fernandez Pilco** (búsqueda por nombre y por DNI, sin resultado) — escalar a M365/RRHH: probablemente nunca se le aprovisionó correo institucional propio. |
| 3 | `enrique.sanchez@upeu.edu.pe` | Sanchez Guzman, Enrique Arturo (est. 202511470) | Sanchez Montero, Juan Enrique (est. 202310601) | Personas distintas — colisión de nomenclatura | **Sanchez Montero, Juan Enrique** | 2026-07-24 (no interactivo) | Correo queda con Sanchez Montero. **No se encontró ningún buzón M365 propio para Enrique Arturo Sanchez Guzman** — escalar a M365: posible falta de aprovisionamiento. |
| 4 | `fiaj.secretaria2@upeu.edu.pe` | Tejada Thorp, Norma Ericka (personal, 43151971) | Condori Quispe, Erika Helen (personal, 70762812) | **Buzón funcional/rol**, no personal (M365: "FIA Secretaria EP Civil") | — (cuenta de rol, no de una persona) | 2026-07-24 (uso real y activo del buzón funcional) | No fusionar ni "elegir" una persona: es una cuenta de cargo (secretaría de la Escuela Profesional de Ing. Civil) compartida legítimamente. Si cada trabajadora necesita su propia cuenta Koha, debería usar su correo personal, no el funcional. |
| 5 | `flor.quispe91@upeu.edu.pe` | Quispe Quispe, Flor De Maria (est. 202123156, matrícula 2021) | Quispe Quispe, Flor De Maria (est. 202512591, matrícula 2026) | **Misma persona** — duplicado de matrícula en Oracle (mismo patrón que caso `05436990`) | Única cuenta real: `flor.quispe91@upeu.edu.pe` | 2026-06-25 (interactivo) | No hay ambigüedad de correo (es la misma persona y el mismo buzón). Escalar a Oracle/Académico para cerrar o fusionar el código duplicado (2021 vs 2026); no accionable desde Koha/M365. |
| 6 | `gabriela.quispe@upeu.edu.pe` | Quispe Quispe, Gabriela (est. 201912017, matrícula 2019) | Quispe Olcese, Ana Gabriela (est. 202212593) | Personas distintas — colisión de nomenclatura | **Quispe Quispe, Gabriela** | 2026-07-25 (no interactivo) | Correo queda con Gabriela Quispe Quispe. Ana Gabriela Quispe Olcese **ya tiene su propio buzón real y distinto**: `gabriela.qo@upeu.edu.pe` (activo, últ. uso 2026-07-25, incluso más reciente) — corregir el dato de origen a esa dirección. |
| 7 | `gerencia.tpp@upeu.edu.pe` | Mathews Paredes, Samuel Stanley (est. 9210069, carnet Koha expira 2026-08-19) | Flores Quinteros, Fernando Gerardo (personal, 200110432) | **Buzón funcional/rol**, no personal (M365: "Director de Operaciones TPP") | — (cuenta de rol) | 2026-07-25 (uso real y activo) | No fusionar. Adicionalmente llama la atención que un **estudiante** (Mathews) esté asociado a un buzón gerencial en Koha — revisar si es un error de mapeo de puesto/cargo en Oracle, aparte del problema del correo compartido. |
| 8 | `jazury.grados@upeu.edu.pe` | Grados Salvador, Jazury Pandora (código moderno 202613966) | Grados Salvador, Jazury Pandora (código legado 324103809) | **Misma persona** — doble shadow/código (patrón "código legado 324xxxxxx" ya documentado) | Única cuenta real: `jazury.grados@upeu.edu.pe` | **Sin actividad — nunca ha iniciado sesión** en M365 | No hay ambigüedad de correo. Consolidar el duplicado interno (mismo mecanismo que jenny.bautista/rosa.luna05 más abajo). Aparte: la persona nunca ha usado su cuenta institucional — verificar si conoce sus credenciales / onboarding pendiente. |
| 9 | `jeison.mamani@upeu.edu.pe` | Nuñez Becerra, Rosa Ines (est. 202321247) | Mamani Ccanahuire, Jeison Augusto (est. 202210224) | Personas distintas — **dato contaminado por valor legado del Koha viejo** (ya identificado en el diagnóstico previo) | **Mamani Ccanahuire, Jeison** | 2026-07-25 (no interactivo) | Correo pertenece a Jeison Mamani. El campo email de Rosa Ines Nuñez Becerra en Koha está simplemente mal (no es su correo, viene de un dato legado) — **no se identificó su correo real** en esta consulta; requiere una búsqueda dedicada por su nombre en M365/Oracle antes de corregir. |
| 10 | `jenny.bautista@upeu.edu.pe` | Bautista Chalco, Jenny Yrene (código legado 324111291) | Bautista Chalco, Jenny Yrene (código moderno 202521444) | **Misma persona** — doble shadow/código | Única cuenta real: `jenny.bautista@upeu.edu.pe` | **Sin actividad — nunca ha iniciado sesión** en M365 | Igual que el caso 8: consolidar duplicado interno, cuenta institucional nunca usada. |
| 11 | `jhon.coaquira@upeu.edu.pe` | Coaquira Paricanaza, Jhon Lenin David (est. 202211705) | Coaquira Ari, Jhon Kenedy (est. 202612399) | Personas distintas — colisión de nomenclatura | **Coaquira Paricanaza, Jhon Lenin** | 2026-07-25 (no interactivo) | Correo queda con Coaquira Paricanaza. Coaquira Ari **ya tiene su propio buzón real y distinto**: `kenedy.ari@upeu.edu.pe` (activo, últ. uso 2026-07-25) — corregir el dato de origen a esa dirección. |
| 12 | `raquel.quispe@upeu.edu.pe` | Quispe Montalico, Raquel Ruth (est. 202313444, carnet Koha **expira en 3 días: 2026-07-29**) | Quispe Panihuara, Raquel Merari (est. 202210598) | Personas distintas — colisión de nomenclatura | **Quispe Panihuara, Raquel Merari** | 2026-07-25 (no interactivo) | Correo queda con Quispe Panihuara. **No se encontró ningún buzón M365 propio para Raquel Ruth Quispe Montalico** — escalar a M365. Adicional: su carnet Koha vence en días, verificar si sigue matriculada. |
| 13 | `rosa.luna05@upeu.edu.pe` | Luna Clemente, Rosa Cristina (código moderno 202521423) | Luna Clemente, Rosa Cristina (código legado 324111289) | **Misma persona** — doble shadow/código | Única cuenta real: `rosa.luna05@upeu.edu.pe` | **Sin actividad — nunca ha iniciado sesión** en M365 | Igual que casos 8 y 10: consolidar duplicado interno, cuenta institucional nunca usada. |

---

## Resumen por clasificación

- **4 casos — misma persona, duplicado de código/matrícula** (#5, #8, #10, #13): no hay ambigüedad
  de correo (es el mismo buzón real). #8, #10 y #13 comparten el patrón "código legado
  `324xxxxxx`" ya documentado (shadow huérfano del Koha viejo archivado). #5 es duplicado de
  matrícula en Oracle, mismo patrón que el caso `05436990` ya escalado a RRHH/Académico.
- **2 casos — buzón funcional/de rol, no de una persona** (#4, #7): no se "elige" un correo, son
  cuentas de cargo compartidas legítimamente por diseño.
- **1 caso — dato contaminado por valor legado** (#9): el campo email de una de las dos personas
  (Rosa Ines Nuñez Becerra) está mal, apunta al correo de otra persona (Jeison Mamani) por una
  causa ya identificada en el diagnóstico previo (inbound del Koha viejo).
- **6 casos — dos personas físicas distintas comparten el mismo correo candidato** (#1, #2, #3,
  #6, #11, #12) por colisión del algoritmo de nomenclatura (mismo primer nombre + mismo primer
  apellido). De estos:
  - **3 ya tienen su propio buzón M365 real y distinto**, con actividad reciente (#1
    `ariana.rivera94@…`, #6 `gabriela.qo@…`, #11 `kenedy.ari@…`) → corrección simple: apuntar el
    dato de origen (Oracle/Koha) a esa dirección ya existente.
  - **3 NO tienen ningún buzón M365 propio localizable** (#2 Veronica Fernandez Pilco, #3 Enrique
    Arturo Sanchez Guzman, #12 Raquel Ruth Quispe Montalico) → requiere verificar con M365/RRHH si
    tienen correo institucional aprovisionado en absoluto.

## Ninguna cuenta se ha "usado más" dentro de Koha

Es importante que Mesa de Ayuda entienda esto: **ninguno de los 26 patrons ha iniciado sesión ni
hecho un préstamo en Koha** (verificado en la base de datos real). La columna "última actividad"
de la tabla refleja actividad de inicio de sesión en el correo institucional (M365), que es la
única señal de uso real disponible hoy — no actividad dentro de la biblioteca.

## Qué NO se hizo (alcance respetado)

Ninguna corrección se aplicó en Koha, MidPoint, Oracle LAMB, Keycloak ni M365. Este documento es
puramente diagnóstico, para que Mesa de Ayuda decida y ejecute las correcciones de dato (con el
dueño real de cada sistema: Oracle LAMB/Académico para datos de matrícula, M365/RRHH para
aprovisionamiento de correo).
