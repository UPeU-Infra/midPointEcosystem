# Guion — Video explicativo: Proyecto de Identidad Digital UPeU
**Para:** Equipo DTI, David Urquizo, David Barrantes  
**Duración estimada:** 4–6 minutos  
**Tono:** Cercano, práctico, sin jerga técnica  
**Formato:** Presentación animada o voz en off con infografías  

---

## INTRO (0:00 – 0:30)

> **Narrador:**  
> Hola equipo. Si alguna vez creaste una cuenta de Microsoft 365 manualmente para un estudiante nuevo, o te dijeron que había un usuario en Azure que nadie sabía de dónde vino — este video es para ti.

> Vamos a explicar qué está cambiando con el **Proyecto de Identidad Digital de UPeU**, qué van a ver diferente en Azure, y por qué eso es una muy buena noticia para el área de DTI.

*[Animación: logo UPeU + íconos de sistemas]*

---

## PARTE 1: EL PROBLEMA DE HOY (0:30 – 1:30)

> **Narrador:**  
> Hoy, la UPeU tiene más de **35,000 personas** — estudiantes, docentes, administrativos. Y sus datos viven en el sistema académico Oracle.

> El problema es que Azure no sabe nada de eso. Cuando un estudiante nuevo se matricula, alguien en DTI tiene que crear su cuenta a mano. Cuando se cambia de carrera, nadie actualiza Azure. Y cuando un estudiante se retira… su cuenta sigue activa.

*[Infografía: Oracle aislado, Azure aislado, DTI en el medio haciendo todo manual — flechas de persona a persona, no automatizadas]*

> Eso genera:
> - **Perfiles incompletos** en Microsoft 365
> - **Tiempo perdido** en tareas repetitivas
> - **Riesgos de seguridad** por cuentas que deberían estar cerradas
> - **Datos que no cuadran** entre sistemas

---

## PARTE 2: LA SOLUCIÓN — EL MOTOR DE IDENTIDAD (1:30 – 2:30)

> **Narrador:**  
> La solución es un **motor central de identidad** — un sistema que lee los datos de Oracle y los distribuye automáticamente a todos los demás sistemas.

*[Animación tipo engranaje central: Oracle → Motor → Azure, Koha, LAMB, LDAP, Keycloak]*

> Piénsenlo como un **traductor automático** que trabaja las 24 horas. Oracle dice "este estudiante se matriculó en Ingeniería de Sistemas, sede Lima" — y el motor lo convierte en: cuenta en Azure con el perfil completo, acceso a los sistemas LAMB, acceso a la biblioteca Koha, y el directorio corporativo actualizado.

> Todo eso, sin que DTI haga nada manualmente.

---

## PARTE 3: QUÉ VAN A VER DIFERENTE EN AZURE (2:30 – 3:30)

> **Narrador:**  
> Entonces, ¿qué va a cambiar en Azure cuando esto entre en operación?

> **Primero: los perfiles van a estar completos.**

*[Mostrar perfil de usuario en Azure: antes vacío, después con carrera, facultad, sede, código, tipo de persona]*

> Van a ver campos como la carrera, la facultad, la escuela, la sede, el código de estudiante. Datos que hoy no están ahí. Y lo mejor: el sistema los mantiene actualizados solo.

> **Segundo: van a aparecer Unidades Administrativas.**

*[Animación: carpetas en Azure que dicen "Facultad de Ingeniería", "Sede Lima", "Docentes Activos"]*

> Una Unidad Administrativa en Azure es simplemente un **grupo inteligente** que contiene a los usuarios de una facultad, una sede o un tipo de persona. El sistema las crea y las gestiona automáticamente. Esto permite aplicar configuraciones y políticas de Microsoft 365 por grupo — sin tener que hacerlo uno por uno.

---

## PARTE 4: LA REGLA DE ORO (3:30 – 4:00)

> **Narrador:**  
> Ahora bien — van a encontrar cosas en Azure que no pusieron ustedes. Y aquí viene la regla más importante:

*[Pantalla grande, texto claro: "Si no lo creó DTI manualmente → no tocarlo sin coordinación"]*

> **No borren ni modifiquen lo que gestiona el sistema.** Si ven un atributo raro en un usuario, o una Unidad Administrativa que no reconocen, no la eliminen. El sistema la restauraría en el próximo ciclo — pero borrarla puede causar inconsistencias temporales.

> Ante cualquier duda, consulten primero con el responsable del proyecto.

---

## PARTE 5: VENTAJAS PARA EL EQUIPO DTI (4:00 – 5:00)

> **Narrador:**  
> ¿Y qué ganan ustedes directamente?

*[Infografía con 6 íconos animados]*

> - **Cero onboarding manual.** Inicio de ciclo: las cuentas se crean solas.
> - **Cero offboarding olvidado.** El estudiante se retira → cuenta desactivada automáticamente.
> - **Datos confiables.** Todo viene de Oracle. Si Oracle dice que alguien está activo, Azure lo refleja.
> - **Políticas más precisas.** Con grupos por facultad, pueden aplicar licencias y configuraciones específicas sin trabajo manual.
> - **Auditoría completa.** Cada cambio queda registrado. Si algo falla, hay trazabilidad de qué cambió, cuándo y por qué.
> - **Un solo flujo para todo.** El mismo ciclo que actualiza Azure, actualiza Koha, LAMB y el resto — sin duplicar trabajo.

---

## CIERRE (5:00 – 5:30)

> **Narrador:**  
> Estamos en la etapa de integración con Azure. Una vez que el sistema tenga los permisos necesarios de lectura en Entra ID, podrá mapear correctamente las facultades y sedes, y comenzar a sincronizar.

> El siguiente paso será un **piloto conjunto** con el equipo de DTI, antes de la activación masiva. Nadie va a quedar sorprendido — todo se coordina con ustedes.

> Si tienen preguntas sobre lo que están viendo en Azure o quieren revisar algo puntual, contáctenme directamente.

*[Pantalla final: nombre, cargo, correo / señal de contacto]*

> Gracias.

---

## NOTAS DE PRODUCCIÓN

| Elemento | Recomendación |
|----------|--------------|
| **Herramienta** | Canva Video, PowerPoint con narración, o Loom |
| **Voz** | Narrador en off o voz IA (ElevenLabs, Murf) |
| **Duración real** | Ajustar a ~4 min si se usa voz IA (leer ~130 ppm) |
| **Slides de apoyo** | Usar `identidad-upeu-slides.html` como base visual |
| **NotebookLM** | Cargar este guion como fuente → generar Audio Overview |
| **Audiencia** | DTI técnico (David Urquizo, David Barrantes) — no usuarios finales |

---

## PARA NOTEBOOKLM — CONTEXTO ADICIONAL

*(Agregar como segunda fuente junto al guion para que NotebookLM tenga contexto)*

**Proyecto:** Sistema de Gestión de Identidades (IGA) de la Universidad Peruana Unión (UPeU), Lima, Perú.

**Sistema usado:** MidPoint 4.10 — plataforma open source de gestión de identidades de Evolveum.

**Fuente de datos:** Oracle LAMB Academic — sistema académico oficial con 35,000+ personas registradas (estudiantes, docentes, administrativos de múltiples sedes: Lima, Juliaca, Tarapoto y más).

**Destinos conectados:** Microsoft Azure / Entra ID (M365), OpenLDAP (directorio corporativo), Koha (sistema de biblioteca), LAMB Academic / Financial / Talent (ecosistema académico), Keycloak (SSO corporativo).

**Estado actual:** Motor IGA operativo. Koha y LDAP integrados. Azure en proceso de integración (pendiente permisos de Entra ID).

**Qué cambia en Azure:**
1. Perfiles de usuario enriquecidos con datos académicos (carrera, facultad, sede, código, tipo).
2. Unidades Administrativas nuevas por facultad, escuela y sede.
3. Activación/desactivación automática según estado de matrícula.
4. Grupos dinámicos por tipo de persona.

**Mensaje clave para DTI:** El proyecto elimina el trabajo manual de onboarding/offboarding, garantiza datos confiables en todos los sistemas, y permite políticas de M365 más precisas por grupo. Lo que aparece nuevo en Azure es gestionado por el sistema — no modificar sin coordinación.
