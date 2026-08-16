# 98 ex-trabajadores conservan su cuenta de Microsoft 365 activa

**Fecha:** 16-ago-2026 (**sustituye a la versión del 15-ago, que decía 34**)
**Para:** DTI — administración de Entra ID / M365
**De:** IGA (MidPoint)
**Estado:** medido en producción, **pendiente de verificación de RRHH antes de actuar**

---

## ⚠️ Corrección respecto a la versión anterior

La versión del 15-ago informaba de **34 personas**. Al re-medir el 16-ago con un criterio más
amplio aparecieron **98**. Las 64 adicionales **no son casos nuevos**: ya estaban dadas de baja
cuando se hizo el primer informe —21 desde el 25-jun, 34 desde el 25-jul— y no se detectaron.

**Si la lista de 34 ya se envió a DTI, hay que reemplazarla por esta.**

## Qué se ha encontrado

**98 personas dadas de baja en el sistema de identidad conservan su cuenta de Entra ID
habilitada** (`accountEnabled=True`): correo, Teams, OneDrive y SharePoint operativos.

| Baja registrada | Personas | Días con la cuenta abierta (al 16-ago) |
|---|---|---|
| 2026-06-25 | 21 | 52 |
| 2026-06-26 | 4 | 51 |
| 2026-07-25 | 34 | 22 |
| 2026-08-04 | 5 | 12 |
| 2026-08-08 | 1 | 8 |
| 2026-08-16 | 33 | (baja procesada hoy) |

Entra ID es **solo lectura** desde MidPoint —sin capacidades de `create`, `update` ni `delete`—
así que el IGA no puede cerrarlas: la acción corresponde a DTI.

## En qué se basa

Para cada una de las 98, medido el 16-ago-2026:

| Señal | Resultado |
|---|---|
| `lifecycleState` | fuera de servicio en las 98 (65 `archived`, 33 `draft`) |
| Presencia en el feed de Trabajadores (que consulta Oracle LAMB) | **0 shadows en las 98** |
| Cuenta en LDAP | **no**, en 97 de 98 |
| Cuenta en Entra ID | **sí, y habilitada, en las 98** — verificado shadow por shadow |

Las tres primeras señales apuntan a una baja consumada. La cuarta es la que no acompaña.

> Sobre los 33 en `draft`: son bajas que el Validity Scanner procesó hoy. El estado `draft` en
> lugar de `archived` es una peculiaridad del cálculo interno del IGA y **no significa que sean
> altas pendientes**: no están en la fuente de RR.HH., no tienen accesos activos salvo M365.

## La lista

| Baja | Código | Nombre | Cuenta M365 | Estado IGA |
|---|---|---|---|---|
| 2026-06-25 | `05399987` | Moises Caira Huanca | `moises.caira@upeu.edu.pe` | archived |
| 2026-06-25 | `16775250` | Jackeline Ayde Muguerza Garcia | `jackeline.muguerza.g@upeu.edu.pe` | archived |
| 2026-06-25 | `40401800` | Edward Amilcar Mallqui Montalvo | `edward.mallqui@upeu.edu.pe` | archived |
| 2026-06-25 | `40953340` | William John Oliva Salas | `40953340@upeu.edu.pe` | archived |
| 2026-06-25 | `42446177` | JOSE MOISES OLORTEGUI REYNA | `42446177@upeu.edu.pe` | archived |
| 2026-06-25 | `44704828` | Reyna Amalia Rojas Garcia | `44704828@upeu.edu.pe` | archived |
| 2026-06-25 | `46824830` | CARLOS ALBERTO VELEZ CALDERON | `carlos.velez@upeu.edu.pe` | archived |
| 2026-06-25 | `47924780` | Angie Elizabeth Muñoz Paredes | `angie.munoz@upeu.edu.pe` | archived |
| 2026-06-25 | `48819381` | Elias Daniel Aguirre Paredes | `Elias.Daniel.Aguirre.Pa@upeu.edu.pe` | archived |
| 2026-06-25 | `49089518` | Milena Aguirre Garrido | `milena.aguirre@upeu.edu.pe` | archived |
| 2026-06-25 | `548644005` | Michael Thomas White | `michaelwhite@upeu.edu.pe` | archived |
| 2026-06-25 | `70004723` | Abigail Paola Ipanaque Zarate | `abigail.ipanaque@upeu.edu.pe` | archived |
| 2026-06-25 | `71937970` | Nury Roxana Cari Turpo | `71937970@upeu.edu.pe` | archived |
| 2026-06-25 | `72121114` | Katty Bexavet Castillo Palmadera | `katty.castillo@upeu.edu.pe` | archived |
| 2026-06-25 | `734472422` | Fabiola Mecedes Melgar Vaca | `fabiola.melgar.m@upeu.edu.pe` | archived |
| 2026-06-25 | `73877807` | Lucita Aurora Araujo Cercado | `lucita.araujo@upeu.edu.pe` | archived |
| 2026-06-25 | `73903954` | Osmar Alex Vasquez Urbina | `osmar.vasquez@upeu.edu.pe` | archived |
| 2026-06-25 | `73986840` | Joseph Valentin Ramirez Ramos | `joseph.ramirez@upeu.edu.pe` | archived |
| 2026-06-25 | `74242597` | NORY MARIBEL CABANILLAS VASQUEZ | `nory.cabanillas@upeu.edu.pe` | archived |
| 2026-06-25 | `74969546` | WILLY ABNER OCAÑA ALVARADO | `willyocana@upeu.edu.pe` | archived |
| 2026-06-25 | `76809824` | Gerardo Andres Cordova Castillo | `76809824@upeu.edu.pe` | archived |
| 2026-06-26 | `16481376` | Rosa Luz Lopez Martinez | `rosa.lopezm@upeu.edu.pe` | archived |
| 2026-06-26 | `42130024` | Edson Leonel Mandujano Romero | `edsonmandujano@upeu.edu.pe` | archived |
| 2026-06-26 | `43148480` | Hernán Diaz Osorio | `hernan.diaz@upeu.edu.pe` | archived |
| 2026-06-26 | `70376659` | Luz Vanessa Panca Humpiri | `luz.panca@upeu.edu.pe` | archived |
| 2026-07-25 | `01127359` | Luis Armando Cuzco Trigozo | `luis.cuzco@upeu.edu.pe` | archived |
| 2026-07-25 | `01188959` | Delia Esperanza Portella Melgarejo | `delia.portella@upeu.edu.pe` | archived |
| 2026-07-25 | `01325501` | Jorge Luis Quiñonez Ticona | `jorge.quinonez@upeu.edu.pe` | archived |
| 2026-07-25 | `01329298` | Moises Araca Chile | `moises.araca@upeu.edu.pe` | archived |
| 2026-07-25 | `02167357` | Yury Añazco Supo | `yury.supo@upeu.edu.pe` | archived |
| 2026-07-25 | `02410349` | Gladis Nimia Chayña Vilcapaza | `gladis.chayna@upeu.edu.pe` | archived |
| 2026-07-25 | `02412015` | Judith Valeriana Yanqui Ortiz | `yudith.yanqui@upeu.edu.pe` | archived |
| 2026-07-25 | `02413573` | Thania Armida Valencia Maquera | `thania.valencia@upeu.edu.pe` | archived |
| 2026-07-25 | `02434910` | Bertha Viza Quispe | `bertha.viza@upeu.edu.pe` | archived |
| 2026-07-25 | `02555563` | Luz Angelica Ccopa TURPO | `luz.ccopa@upeu.edu.pe` | archived |
| 2026-07-25 | `06636199` | José Carlos Gastelu Guzman | `jose.gastelu@upeu.edu.pe` | archived |
| 2026-07-25 | `09336056` | Ivan Nicolas Figueroa Gonzalez | `ivanfigueroa@upeu.edu.pe` | archived |
| 2026-07-25 | `16670476` | Elsa Lizet Idrogo Arrascue | `elsaidrogo@upeu.edu.pe` | archived |
| 2026-07-25 | `21407461` | María Cecilia Girao Araujo | `mariagirao@upeu.edu.pe` | archived |
| 2026-07-25 | `22997723` | Lucinda Vela Vargas | `lucindavela@upeu.edu.pe` | archived |
| 2026-07-25 | `29394949` | Nancy Margarita Ortiz Rodriguez | `nancy.ortiz@upeu.edu.pe` | archived |
| 2026-07-25 | `31663735` | Kiko Felix Depaz Celi | `kiko.depaz@upeu.edu.pe` | archived |
| 2026-07-25 | `40192228` | Renny Daniel Diaz Aguilar | `rennydaniel@upeu.edu.pe` | archived |
| 2026-07-25 | `40408206` | Edgar Alfonso Garcia Oporto | `edgar.garcia@upeu.edu.pe` | archived |
| 2026-07-25 | `40796888` | William Apaza Mamani | `william.apaza@istat.edu.pe` | archived |
| 2026-07-25 | `41168562` | Larry Steve Pachari Centeno | `steve.pachari@upeu.edu.pe` | archived |
| 2026-07-25 | `41169423` | Guillermo Carlos Contreras Nogales | `guillermo.contreras@upeu.edu.pe` | archived |
| 2026-07-25 | `41782913` | Nestor Alejandro Cruz Calapuja | `nestor.cruz@upeu.edu.pe` | archived |
| 2026-07-25 | `42361774` | Jade Sheil Perez Tenazoa | `jade.perez@upeu.edu.pe` | archived |
| 2026-07-25 | `43537049` | Liliana Elizabeth Puma Maron | `liliana.puma@upeu.edu.pe` | archived |
| 2026-07-25 | `43960192` | Luis Angello Coarite Asencio | `angellocoarite@upeu.edu.pe` | archived |
| 2026-07-25 | `46530134` | Liz Rubi Blaz Vilchez | `liz.blaz@upeu.edu.pe` | archived |
| 2026-07-25 | `46555229` | Annie Eshel Jaimes Duarte | `anniejaimes@upeu.edu.pe` | archived |
| 2026-07-25 | `46815141` | Christian Michel Cunya Pardo | `michelcunya@upeu.edu.pe` | archived |
| 2026-07-25 | `46819549` | Dario Ccaccya Ccaccya | `darioccaccya@upeu.edu.pe` | archived |
| 2026-07-25 | `71057807` | Aileen Pilar Pacompia Calsin | `aileen.pacompia@upeu.edu.pe` | archived |
| 2026-07-25 | `71318245` | Ricky Bray Saavedra Mego | `ricky.saavedra@upeu.edu.pe` | archived |
| 2026-07-25 | `75914610` | Moisés Lucio Talavera Antazu | `moises.talavera@upeu.edu.pe` | archived |
| 2026-07-25 | `77176693` | Ruth Zaida Esteba Valencia | `ruthesteba@upeu.edu.pe` | archived |
| 2026-08-04 | `01157608` | Jose Reategui Vega | `jose.reategui@upeu.edu.pe` | archived |
| 2026-08-04 | `01291373` | Litza Santos Damasceno | `asistente.eventos@upeu.edu.pe` | archived |
| 2026-08-04 | `18022154` | Luis Armando Garcia Hidalgo | `luisgarciah@upeu.edu.pe` | archived |
| 2026-08-04 | `23999632` | Adolfo Morales Acurio | `adolfo.morales@upeu.edu.pe` | archived |
| 2026-08-04 | `42846492` | Homero Sanchez Vasquez | `42846492@upeu.edu.pe` | archived |
| 2026-08-08 | `08684132` | Veronica Juana Guerrero Iriarte | `veronicaguerrero@upeu.edu.pe` | archived |
| 2026-08-16 | `05220667` | Josimar Da Silva Souza | `005220667@upeu.edu.pe` | draft |
| 2026-08-16 | `06810462` | Hugo Alberto Alcantara Ventura | `06810462@upeu.edu.pe` | draft |
| 2026-08-16 | `07664222` | MEDRANO Ortega Maria Del Pilar | `pilar@upeu.edu.pe` | draft |
| 2026-08-16 | `07664416` | FRANCISCO QUINTEROS DEL AGUILA | `franciscoquinteros@upeu.edu.pe` | draft |
| 2026-08-16 | `10350511` | Hugo Fernando Morales Morales | `hugo.morales@upeu.edu.pe` | draft |
| 2026-08-16 | `10728917` | Roddy Jhanet MACHCO ROJAS | `10728917@upeu.edu.pe` | draft |
| 2026-08-16 | `10819969` | Aydee Puente De La Vega Alvarez | `aydee.alvarez@upeu.edu.pe` | draft |
| 2026-08-16 | `15724649` | Roberto Castulo Mejia Alejandro | `roberto.mejia@upeu.edu.pe` | draft |
| 2026-08-16 | `15856546` | Nidia Judith Aldave Carrion | `nidiaaldave@upeu.edu.pe` | draft |
| 2026-08-16 | `21505281` | Jose Antonio Lujan Soria | `21505281@upeu.edu.pe` | draft |
| 2026-08-16 | `28067877` | Elias Royer Alfaro Revilla | `28067877@upeu.edu.pe` | draft |
| 2026-08-16 | `40353570` | Itala Verónica Muguerza Garcia | `itala.muguerza@upeu.edu.pe` | draft |
| 2026-08-16 | `40608535` | Henry Lincold Salazar Campusano | `40608535@upeu.edu.pe` | draft |
| 2026-08-16 | `40718513` | Rolando Moises Condori Quaquera | `40718513@upeu.edu.pe` | draft |
| 2026-08-16 | `41868466` | Ruth Aurora Diaz Osorio | `ruth.osorio@upeu.edu.pe` | draft |
| 2026-08-16 | `42149296` | Fernando Cabanillas Guelles | `fernandocabanillas@upeu.edu.pe` | draft |
| 2026-08-16 | `42344461` | Carlos ROMERO Mozombite | `carlos.romerom@upeu.edu.pe` | draft |
| 2026-08-16 | `42439673` | Abner David Castillo Neira | `abnercastillo@upeu.edu.pe` | draft |
| 2026-08-16 | `42503821` | Gilber Alfonso Sambrano Quispe | `42503821@upeu.edu.pe` | draft |
| 2026-08-16 | `42535066` | Lucas Alfredo Cruz Puma | `42535066@upeu.edu.pe` | draft |
| 2026-08-16 | `42620959` | Wilmer Mendoza Yoctun | `wilmer.mendoza@upeu.edu.pe` | draft |
| 2026-08-16 | `43132504` | Juan Alberto Campos Silva | `albertocampos@upeu.edu.pe` | draft |
| 2026-08-16 | `43220816` | Grissella Lizeth Rios Paucar | `43220816@upeu.edu.pe` | draft |
| 2026-08-16 | `44242083` | Augusto Yaxvier Alvarado Olazabal | `yaxvieralvarado@upeu.edu.pe` | draft |
| 2026-08-16 | `44481749` | Diego Alonso Mesia Angeles | `diego.mesia@upeu.edu.pe` | draft |
| 2026-08-16 | `45119279` | Asmavet Maria SANTIAGO LOPEZ | `45119279@upeu.edu.pe` | draft |
| 2026-08-16 | `47164865` | SAMUEL ELI BARBOZA CALDERON | `samuel.barboza@upeu.edu.pe` | draft |
| 2026-08-16 | `47686459` | Giomara Francis Diaz Mitma | `47686459@upeu.edu.pe` | draft |
| 2026-08-16 | `61833417` | Shirley Paredes Rodriguez | `61833417@upeu.edu.pe` | draft |
| 2026-08-16 | `70759374` | Jhonatan Fernandez Huamani | `70759374@upeu.edu.pe` | draft |
| 2026-08-16 | `771245575` | Mayrin Gianella ESPINOZA Quiroz | `77380977@upeu.edu.pe` | draft |
| 2026-08-16 | `771245604` | Elizabet Paucar Vega | `elizabetpaucar@upeu.edu.pe` | draft |
| 2026-08-16 | `803487990` | Gabriella Andrea Esquivel Lorenzo | `gabriella.esquivelt@upeu.edu.pe` | draft |

## Qué se pide

1. **RRHH confirma** que estas 98 personas ya no tienen vínculo laboral vigente.
2. Con esa confirmación, **DTI cierra las cuentas** según el procedimiento de la institución
   (bloqueo, retención del buzón, y liberación de licencia).
3. Si alguna **sí** tiene vínculo vigente, es un fallo del feed de Trabajadores y hay que
   avisar al IGA: significa que Oracle LAMB no la está reportando.

## Por qué el IGA no lo resuelve solo

Por decisión de arquitectura, **Entra ID es un destino de solo lectura**: MidPoint lee de ahí
para correlacionar identidades, pero no escribe. Mientras siga así, el cierre de cuentas de
ex-trabajadores es necesariamente un paso manual de DTI, y conviene que tenga una periodicidad
acordada — este informe cubre un momento concreto, no es un control continuo.
