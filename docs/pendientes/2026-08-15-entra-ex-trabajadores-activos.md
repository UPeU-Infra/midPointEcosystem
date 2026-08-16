# 34 ex-trabajadores conservan su cuenta de Microsoft 365 activa

**Fecha:** 15-ago-2026
**Para:** DTI — administración de Entra ID / M365
**De:** IGA (MidPoint)
**Estado:** medido en producción, **pendiente de verificación de RRHH antes de actuar**

---

## Qué se ha encontrado

**34 personas archivadas en el sistema de identidad conservan su cuenta de Entra ID
habilitada** (`accountEnabled=True`): correo, Teams, OneDrive y SharePoint operativos.

**33 de ellas llevan así desde el 25-jun-2026** — casi dos meses. La restante desde el 20-jul.

Entra ID es **solo lectura** desde MidPoint, así que el IGA no puede cerrarlas: la acción
corresponde a DTI.

## En qué se basa

Para cada una de las 34, medido en MidPoint el 15-ago-2026:

| Señal | Resultado |
|---|---|
| `lifecycleState` | **`archived`** en las 34 |
| Presencia en el feed de Trabajadores (que consulta Oracle LAMB) | **0 shadows en las 34** |
| Cuenta en LDAP | **no**, en 33 de 34 |
| Cuenta en Koha | **no**, en las 34 |
| Cuenta en Entra ID | **sí, y habilitada, en las 34** |

Las cuatro primeras señales apuntan a una baja consumada. La quinta es la que no acompaña.

## La lista

| Archivado desde | Código | Nombre | Cuenta M365 | ¿LDAP? |
|---|---|---|---|---|
| 2026-06-25 | `42439673` | Abner David Castillo Neira | `abnercastillo@upeu.edu.pe` | no |
| 2026-06-25 | `45119279` | Asmavet Maria SANTIAGO LOPEZ | `45119279@upeu.edu.pe` | no |
| 2026-06-25 | `10819969` | Aydee Puente De La Vega Alvarez | `aydee.alvarez@upeu.edu.pe` | no |
| 2026-06-25 | `42344461` | Carlos ROMERO Mozombite | `carlos.romerom@upeu.edu.pe` | no |
| 2026-06-25 | `44481749` | Diego Alonso Mesia Angeles | `diego.mesia@upeu.edu.pe` | no |
| 2026-06-25 | `28067877` | Elias Royer Alfaro Revilla | `28067877@upeu.edu.pe` | no |
| 2026-06-25 | `771245604` | Elizabet Paucar Vega | `elizabetpaucar@upeu.edu.pe` | no |
| 2026-06-25 | `07664416` | FRANCISCO QUINTEROS DEL AGUILA | `franciscoquinteros@upeu.edu.pe` | no |
| 2026-06-25 | `42149296` | Fernando Cabanillas Guelles | `fernandocabanillas@upeu.edu.pe` | no |
| 2026-06-25 | `803487990` | Gabriella Andrea Esquivel Lorenzo | `gabriella.esquivelt@upeu.edu.pe` | no |
| 2026-06-25 | `42503821` | Gilber Alfonso Sambrano Quispe | `42503821@upeu.edu.pe` | no |
| 2026-06-25 | `47686459` | Giomara Francis Diaz Mitma | `47686459@upeu.edu.pe` | no |
| 2026-06-25 | `43220816` | Grissella Lizeth Rios Paucar | `43220816@upeu.edu.pe` | no |
| 2026-06-25 | `40608535` | Henry Lincold Salazar Campusano | `40608535@upeu.edu.pe` | no |
| 2026-06-25 | `06810462` | Hugo Alberto Alcantara Ventura | `06810462@upeu.edu.pe` | no |
| 2026-06-25 | `10350511` | Hugo Fernando Morales Morales | `hugo.morales@upeu.edu.pe` | no |
| 2026-06-25 | `40353570` | Itala Verónica Muguerza Garcia | `itala.muguerza@upeu.edu.pe` | no |
| 2026-06-25 | `70759374` | Jhonatan Fernandez Huamani | `70759374@upeu.edu.pe` | no |
| 2026-06-25 | `21505281` | Jose Antonio Lujan Soria | `21505281@upeu.edu.pe` | no |
| 2026-06-25 | `05220667` | Josimar Da Silva Souza | `005220667@upeu.edu.pe` | no |
| 2026-06-25 | `43132504` | Juan Alberto Campos Silva | `albertocampos@upeu.edu.pe` | no |
| 2026-06-25 | `42535066` | Lucas Alfredo Cruz Puma | `42535066@upeu.edu.pe` | no |
| 2026-06-25 | `07664222` | MEDRANO Ortega Maria Del Pilar | `pilar@upeu.edu.pe` | no |
| 2026-06-25 | `771245575` | Mayrin Gianella ESPINOZA Quiroz | `77380977@upeu.edu.pe` | no |
| 2026-06-25 | `548644005` | Michael Thomas White | `michaelwhite@upeu.edu.pe` | sí |
| 2026-06-25 | `15856546` | Nidia Judith Aldave Carrion | `nidiaaldave@upeu.edu.pe` | no |
| 2026-06-25 | `15724649` | Roberto Castulo Mejia Alejandro | `roberto.mejia@upeu.edu.pe` | no |
| 2026-06-25 | `10728917` | Roddy Jhanet MACHCO ROJAS | `10728917@upeu.edu.pe` | no |
| 2026-06-25 | `40718513` | Rolando Moises Condori Quaquera | `40718513@upeu.edu.pe` | no |
| 2026-06-25 | `41868466` | Ruth Aurora Diaz Osorio | `ruth.osorio@upeu.edu.pe` | no |
| 2026-06-25 | `47164865` | SAMUEL ELI BARBOZA CALDERON | `samuel.barboza@upeu.edu.pe` | no |
| 2026-06-25 | `61833417` | Shirley Paredes Rodriguez | `61833417@upeu.edu.pe` | no |
| 2026-06-25 | `42620959` | Wilmer Mendoza Yoctun | `wilmer.mendoza@upeu.edu.pe` | no |
| 2026-07-20 | `44242083` | Augusto Yaxvier Alvarado Olazabal | `yaxvieralvarado@upeu.edu.pe` | no |

## ⚠️ Antes de desactivar nada

**Esta lista NO es una orden de desactivación: es una petición de verificación.**

El fundamento es el estado del IGA, y el IGA arrastra datos residuales conocidos — de hecho,
las 34 conservan `primaryAffiliation=staff` **pese a no estar en la fuente**, que es
exactamente el defecto que se corrigió en 645 personas el 12-ago-2026 y que sigue afectando a
unas 2.848 identidades archivadas.

Que la reconciliación de Trabajadores no las traiga es la definición operativa de "sin
contrato vigente" en este sistema, y es una señal fuerte — pero **no sustituye a la
comprobación del contrato en RRHH**. Desactivar el M365 de alguien que sigue trabajando es un
daño inmediato y visible.

**Petición concreta:** que RRHH confirme el cese de estas 34 personas y, con esa confirmación,
DTI deshabilite sus cuentas.

## Lo que se excluye a propósito

Otras **5 personas** cumplen el mismo patrón pero fueron **archivadas hoy mismo**
(15-ago-2026) por la reconciliación diaria. Que su cuenta siga activa unas horas después es el
comportamiento normal, no un hallazgo. Se revisarán en la próxima pasada.

## Por qué aparece esto ahora

Salió al investigar los conflictos de Koha: al medir las identidades archivadas que aún
figuran como habilitadas (**2.857**), 46 tenían cuentas reales y 39 de ellas estaban en Entra.
De esas 39, 34 llevan tiempo archivadas.

Conviene precisar que las 2.857 **no suponen un problema de acceso**: su `effectiveStatus` es
`disabled` en el 100 % de los casos, porque el `lifecycleState=archived` prevalece. El problema
está solo donde hay una cuenta viva en un sistema externo — que es este caso.

## Antecedente

Mismo canal que el informe del 3-ago-2026 sobre las 533 personas con dos o más correos en
Entra por campus.
