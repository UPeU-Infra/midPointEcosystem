# Nota para el DTI — Por qué se entra con el correo propio y no con el del área

**Fecha:** 07-sep-2026 · **Para:** Dirección de Tecnologías de la Información
**Origen:** consultas del equipo durante las pruebas de Zammad
**Base normativa:** [`DECISION-email-governance.md`](DECISION-email-governance.md), ratificada el 04-jun-2026

---

## 1. Primero, un malentendido que conviene deshacer

Varias personas han comentado que «las notificaciones de Zammad llegan a mi correo personal».
**Comprobado en el sistema: no es así.** Las notificaciones llegan al **correo institucional
nominal** de cada persona.

Hay **tres** cosas distintas que en el uso diario se llaman igual:

| | ejemplo | qué identifica |
|---|---|---|
| **Nominal institucional** | `jsanchez@upeu.edu.pe` | a **una persona** |
| **De cargo o funcional** | `mesadeservicio@upeu.edu.pe` | a **un puesto** |
| **Privado** | una cuenta de Gmail | nada institucional |

Lo que Zammad recibe es el **nominal institucional**. El correo privado sí está registrado en el
sistema de identidad —hace falta para contactar a alguien que ha causado baja— pero **no se envía a
ningún sistema** y no recibe notificaciones de trabajo.

Así que cuando se dice «me llega a mi correo personal», lo que se quiere decir es *«me llega al mío
y no al del área»*. Es una diferencia de costumbre, no un error del sistema.

---

## 2. Por qué se entra con la identidad propia

Porque un correo de cargo **no es una persona**, y el sistema de identidad solo sabe gobernar
personas. Cuatro consecuencias concretas:

**No se sabe quién hizo qué.** Si tres personas entran como `tesoreria@`, no hay forma de saber
quién cerró un ticket, quién aprobó un acceso o quién borró algo. Se pierde la trazabilidad, que es
lo que hace auditable un sistema.

**Las bajas dejan de funcionar.** Cuando una persona deja el cargo, el buzón sigue vivo con todos
sus accesos. No hay a quién retirárselos. Es justo el problema que hemos estado cerrando este año.

**Obliga a compartir contraseñas.** Eso anula el segundo factor y cualquier política de credenciales.

**Un cargo cambia de manos; una identidad no.** El identificador de una persona no se reasigna nunca.
Un buzón de cargo, por definición, se hereda.

---

## 3. Dónde sí cabe el correo de cargo

**La costumbre tiene una razón buena detrás**, y no hay que eliminarla: hay avisos que no van
dirigidos a nadie en particular.

| tipo de aviso | a dónde debe ir |
|---|---|
| «**te** han asignado el ticket #123» | al correo nominal de esa persona |
| «ha entrado un ticket en la cola de Mesa de Servicio» | al **buzón de la cola** |

Zammad admite un correo por cola. **Ahí es donde encaja el buzón de área**, sin tocar la forma de
entrar de nadie. Si el DTI quiere que los avisos de cola lleguen a `mesadeservicio@`, se configura y
listo.

Y el buzón de cargo, cuando debe existir, se modela como **recurso con titulares**: pertenece al
área, se le asigna a quien ocupa el puesto, y cuando cambia el titular cambia la asignación. El
buzón sobrevive a las personas —que es lo que la institución quiere— pero cada acceso sigue teniendo
nombre y apellido.

---

## 4. Y sobre la continuidad, que es la preocupación real

Lo que de verdad se busca con el correo de cargo es **que el trabajo no se pare cuando alguien
falta**. Eso ya está resuelto, y mejor.

El **7 de septiembre**, cuando Flor Flores entró de vacaciones, Ruth Fuentes recibió el acceso a la
cola de Mesa de Servicio **hasta el 21 de septiembre**:

- puede **abrir y atender tickets**, no solo leer avisos;
- el permiso **caduca solo** el día 21, sin que nadie tenga que acordarse;
- y **queda registrado** quién atendió qué durante la cobertura.

Un buzón compartido da la continuidad, pero pierde las otras dos cosas: nadie sabe quién respondió,
y el acceso no se retira nunca porque nadie recuerda que se dio.

---

## 5. Qué se pide al DTI

1. **Mantener el acceso con la identidad propia.** No es una preferencia técnica: es lo que permite
   auditar y lo que permite retirar accesos cuando alguien cambia de puesto.
2. **Decir qué colas necesitan buzón propio** para los avisos de grupo. Eso se configura en Zammad.
3. **Para las ausencias, usar la cobertura temporal** en lugar de compartir buzón. Se pide, se
   concede con fecha de fin y se retira sola.

Nada de esto cambia los buzones de área que ya existen: siguen funcionando para recibir correo. Lo
que no van a hacer es servir para entrar a los sistemas.

---

## 6. Fundamento normativo

| Punto | Norma |
|---|---|
| Una identidad se refiere a **una entidad**; el identificador la distingue unívocamente | ISO/IEC 24760-1 |
| Ciclo de vida completo de la identidad: alta, modificación y **baja** | ISO/IEC 27001:2022 **A.5.16** |
| Gestión de la información de autenticación (compartir contraseñas la anula) | ISO/IEC 27001:2022 **A.5.17** |
| Provisión y **revisión periódica** de accesos; mínimo privilegio | ISO/IEC 27001:2022 **A.5.18** |
| Accesos privilegiados con **registro de auditoría** | ISO/IEC 27001:2022 **A.8.2** |
| El identificador federado (ePPN) es **único y no reasignable** | eduPerson 202208 |
| El autenticador se vincula al suscriptor; compartirlo degrada el nivel de garantía | NIST SP 800-63-3 |
| Un **cargo es un rol** («job function within the context of an organization»), y los roles **se asignan** a usuarios: no son usuarios | NIST RBAC · ANSI/INCITS 359-2012 |

La decisión institucional que desarrolla todo esto es
[`DECISION-email-governance.md`](DECISION-email-governance.md) §1.2, ratificada el 04-jun-2026.
