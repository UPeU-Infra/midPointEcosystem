# Estructura Entra ID — Universidad Peruana Unión

**Fecha de snapshot:** 2026-05-19
**Autor:** Alberto Sánchez — DTI UPeU
**Destinatario principal:** David Urquizo — CTO InfraTI, DTI Lima (`daiurqz@upeu.edu.pe`)
**Estado:** Borrador de trabajo — insumo para Fase 12 IGA

---

## Tabla de contenidos

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Tenant y dominios](#2-tenant-y-dominios)
3. [Licencias](#3-licencias)
4. [Usuarios](#4-usuarios)
5. [Administrative Units (estado actual)](#5-administrative-units-estado-actual)
6. [Roles y permisos (estado actual)](#6-roles-y-permisos-estado-actual)
7. [Grupos](#7-grupos)
8. [App Registrations](#8-app-registrations)
9. [Diseño propuesto IGA — Administrative Units](#9-diseño-propuesto-iga--administrative-units)
10. [Diseño propuesto — Roles delegados por sede](#10-diseño-propuesto--roles-delegados-por-sede)
11. [Diseño propuesto — Grupos de seguridad a crear](#11-diseño-propuesto--grupos-de-seguridad-a-crear)
12. [Prerrequisitos para activar IGA](#12-prerrequisitos-para-activar-iga)
13. [Problemas a resolver](#13-problemas-a-resolver)

---

## 1. Resumen ejecutivo

El tenant Entra ID de la UPeU contiene **73.196 usuarios activos** y es el directorio de identidad más grande de la institución en nube. Sin embargo, el estado actual refleja un crecimiento orgánico sin gobernanza: los atributos de departamento y tipo de empleado están vacíos en prácticamente el 100% de los usuarios, no existen dynamic groups, los roles de directorio se asignan con scope global cuando deberían ser scoped por Administrative Unit, y 999 grupos M365/Teams se crearon sin ninguna política de ciclo de vida.

### Lo que funciona bien

- El tenant está consolidado en un solo directorio (cloud-only, sin sync AD on-prem).
- Las Administrative Units para ISTAT, UNION-PE e IMPRENTAUNION-COM existen y tienen scope correcto para la delegación a sus respectivos administradores locales.
- La App Registration `MidPoint-UPeU` ya existe y es la base del conector IGA.
- La licencia A3 Faculty incluye Azure AD P1, que habilita dynamic groups y Conditional Access — capacidades que aún no se usan.

### Hallazgos criticos

| # | Hallazgo | Impacto |
|---|---|---|
| C1 | `department`, `officeLocation`, `companyName`, `employeeType` vacíos en ~99.9% de usuarios | MidPoint no puede correlacionar ni clasificar usuarios sin atributos estructurados |
| C2 | 84 de 86 role assignments con scope en tenant completo | Un administrador de Juliaca tiene los mismos poderes que uno de Lima |
| C3 | 0 dynamic groups | No es posible automatizar membresías basadas en atributos |
| C4 | 999 grupos M365/Teams sin gobernanza | No hay propietario, sin fecha de expiración, sin naming policy |
| C5 | Dos licencias sobreusadas (`M365EDU_A5_FACULTY` 16/15, `Teams_Premium` 19/18) | Riesgo de incumplimiento con Microsoft |
| C6 | `Microsoft_365_Copilot_EDU` con 8 asignaciones y 0 licencias prepagadas | Posible costo no presupuestado |
| C7 | ~30 App Registrations sin nombre claro o de prueba | Surface de ataque expandida, riesgo de tokens huerfanos |
| C8 | `mesa.sti@upeu.edu.pe` acumula Helpdesk + User + Exchange + Teams + otros roles simultaneamente | Violación del principio de menor privilegio |

### Impacto en el proyecto IGA

Entra ID está declarado como **solo lectura en Fases 1 a 11** del roadmap IGA. MidPoint lee Entra ID para correlacionar identidades, pero no escribe. La escritura (provisioning outbound) se habilita en Fase 12 una vez que el modelo de atributos esté resuelto. Las acciones propuestas en este documento son preparatorias para esa fase: sin atributos estructurados, Entra ID no puede ser target de provisioning útil.

---

## 2. Tenant y dominios

### Datos del tenant

| Campo | Valor |
|---|---|
| Nombre de organización | Universidad Peruana Unión |
| Tenant ID | `cfbd88b4-94bc-4fba-98bd-64d0726394a3` |
| Dominio principal | `upeu.edu.pe` |
| Dominio onmicrosoft | `upeuedupe.onmicrosoft.com` |
| Sync AD on-prem | No — `onPremisesSyncEnabled: null`, `onPremisesLastSyncDateTime: null` (Graph API) |
| Modelo de usuario | Cloud-only (sin AD Connect configurado) |

### Dominios registrados

Datos obtenidos directamente de la Graph API (`GET /organization?$select=verifiedDomains`).

| Dominio | Usuarios | Default | Initial | Capacidades |
|---|---:|:---:|:---:|---|
| `upeu.edu.pe` | 72.439 | ✓ | — | Email, OfficeCommunicationsOnline, OrgIdAuthentication, Yammer, Intune |
| `union.pe` | 339 | — | — | Email |
| `upeuedupe.onmicrosoft.com` | 264 | — | ✓ | Email, OfficeCommunicationsOnline |
| `istat.edu.pe` | 84 | — | — | Email |
| `imprentaunion.com` | 70 | — | — | Email, OfficeCommunicationsOnline, Intune |
| **Total** | **73.196** | | | |

> **Nota:** la API no expone el nombre legal de la organización propietaria de cada dominio. Los nombres de entidad mostrados en versiones anteriores de este documento ("Instituto Tecnológico Adventista del Titicaca", "Productos Unión S.A.C.", "Imprenta Unión") fueron inferidos por el redactor y deben ser verificados con David Urquizo antes de usarlos en documentación oficial.

### Implicancias de la estructura multi-dominio

El tenant UPeU aloja **al menos cuatro dominios de diferentes organizaciones** en un único directorio. Esto es operativamente correcto para tener SSO unificado con M365, pero requiere que la gobernanza de identidades trate a cada dominio como un ámbito de administración separado. Las Administrative Units ya reflejan parcialmente este diseño (ver sección 5).

> **Pendiente de verificar con David Urquizo:** cuál es el sistema de identidad de origen para los usuarios de `istat.edu.pe`, `union.pe` e `imprentaunion.com`. No se puede asumir desde los datos del tenant.

---

## 3. Licencias

### Licencias activas

| SKU | Nombre | Usadas | Disponibles | Uso % | Estado |
|---|---|---|---|---|---|
| `STANDARDWOFFPACK_FACULTY` | Office 365 A1 Faculty | 40.949 | 500.000 | 8% | Normal |
| `STANDARDWOFFPACK_STUDENT` | Office 365 A1 Student | 15.959 | 1.000.000 | 2% | Normal |
| `M365EDU_A3_STUUSEBNFT` | M365 A3 Student | 12.864 | 39.400 | 33% | Normal |
| `M365EDU_A3_FACULTY` | M365 A3 Faculty | 265 | 985 | 27% | Normal |
| `M365EDU_A5_FACULTY` | M365 A5 Faculty | **16** | **15** | **107%** | SOBREUSADA |
| `M365EDU_A5_STUUSEBNFT` | M365 A5 Student | 56 | 600 | 9% | Normal |
| `POWER_BI_PRO_FACULTY` | Power BI Pro Faculty | 51 | 74 | 69% | Vigilar |
| `VISIOCLIENT` | Visio Plan 2 | 4 | 4 | 100% | Limite |
| `Teams_Premium_(for_Departments)` | Teams Premium | **19** | **18** | **106%** | SOBREUSADA |
| `Microsoft_365_Copilot_EDU` | M365 Copilot Edu | 8 | 0 prepagadas | N/A | REVISAR |

### Capacidades IGA habilitadas por licencia

La licencia **M365 A3** incluye **Azure AD P1** (ahora Entra ID P1). Las licencias **M365 A5** incluyen **Entra ID P2**. Esto significa que UPeU tiene habilitadas las siguientes capacidades relevantes para IGA que actualmente no se usan:

| Capacidad | Licencia requerida | Estado UPeU |
|---|---|---|
| Dynamic Groups (reglas de membresía automática) | Entra ID P1 (A3+) | Disponible, NO usada |
| Conditional Access policies | Entra ID P1 (A3+) | Disponible, uso limitado |
| Administrative Units con roles scoped | Entra ID P1 (A3+) | Disponible, uso parcial |
| Privileged Identity Management (PIM) | Entra ID P2 (A5) | Disponible para 16 usuarios A5 |
| Access Reviews | Entra ID P2 (A5) | Disponible para 16 usuarios A5 |
| Entitlement Management | Entra ID P2 (A5) | Disponible para 16 usuarios A5 |

**Conclusion:** UPeU tiene las licencias necesarias para implementar gobierno de identidades robusto en Entra ID. El gap no es de licencias sino de configuracion.

### Alertas inmediatas

- **M365EDU_A5_FACULTY sobreusada (16/15):** revocar una asignacion o comprar 1 licencia adicional.
- **Teams_Premium sobreusada (19/18):** idem.
- **M365 Copilot EDU (8 asignadas, 0 prepagadas):** investigar si estas son licencias de trial activo o si se estan consumiendo sin contrato. Riesgo de facturacion imprevista.

---

## 4. Usuarios

### Volumetria

| Metrica | Valor |
|---|---|
| Total usuarios en directorio | 73.196 |
| Usuarios habilitados | 73.116 |
| Usuarios deshabilitados | 80 |
| Usuarios con licencia asignada | 69.483 |
| Usuarios sin licencia | 3.713 |

### Problema central: atributos estructurales vacios

Los atributos que MidPoint usa para clasificar, correlacionar y asignar roles en Entra ID estan practicamente vacios:

| Atributo Entra ID | Equivalente canonico | Vacios | Con valor | Observacion |
|---|---|---|---|---|
| `department` | `organizationalUnit` / OU org | 72.475 | 721 (~1%) | No estructurado; valores ad-hoc |
| `officeLocation` | `locality` / sede | 72.943 | 253 (~0.3%) | Practicamente no usado |
| `companyName` | `organization` | 73.195 | 1 (<0.01%) | Solo 1 usuario tiene valor |
| `employeeType` | `employeeType` (core MidPoint) | 73.196 | 0 (0%) | Nadie tiene valor |
| `jobTitle` | `title` | No medido | Variable | Uso inconsistente |

### Impacto en IGA

Sin estos atributos poblados, Entra ID no puede ser un target de provisioning util. MidPoint no puede:

1. Saber si un usuario de Entra ID es estudiante, docente o administrativo.
2. Aplicar politicas de licencia diferenciadas por tipo de afiliacion.
3. Crear dynamic groups por sede, facultad o tipo de usuario.
4. Hacer reconciliacion correcta sin falsos positivos.

**La solucion no es poblar atributos manualmente.** La solucion es que MidPoint, en Fase 12, sea quien escriba estos atributos desde Oracle LAMB como IIA. El flujo sera:

```
Oracle LAMB (IIA) → MidPoint → Entra ID (atributos estructurados)
                             → Dynamic Groups (reglas en Entra ID)
                             → Licencias asignadas por grupo
```

Hasta que Fase 12 este activa, Entra ID permanece como fuente de lectura para correlacion de UPN solamente.

### Estrategia de correlacion actual (Fases 1-11)

MidPoint correlaciona usuarios Entra ID con identidades MidPoint usando el UPN (`userPrincipalName`). El UPN sigue el patron `{primer.apellido}@upeu.edu.pe` para usuarios regulares. La correlacion definitiva usara `employeeNumber` o `externalSystemId` una vez que Fase 12 active el write-back.

---

## 5. Administrative Units (estado actual)

### Las 5 AUs existentes

| AU | Miembros | Proposito declarado | Analisis |
|---|---|---|---|
| **DTI** | 11 | Personal DTI Lima — cuentas funcionales de soporte | Correcto como AU pero deberia ser un Security Group. Las AUs son para delegar administracion de usuarios, no para agrupar cuentas funcionales. |
| **IMPRENTAUNION-COM** | 45 | Usuarios del dominio `imprentaunion.com` | Correcto. Tiene Helpdesk Administrator scoped para Andy Espinoza. |
| **ISTAT** | 10 | Usuarios del dominio `istat.edu.pe` | Correcto. Tiene Helpdesk Administrator scoped para `notify@istat.edu.pe`. |
| **ITService** | 19 | Correos desatendidos y cuentas de servicio | Incorrecto como AU. Deberia ser un Security Group etiquetado. Las cuentas de servicio no necesitan AU de delegacion administrativa. |
| **UNION-PE** | 223 | Usuarios del dominio `union.pe` | Correcto. Tiene User Administrator + Helpdesk Administrator scoped para Sergio Calizaya. |

### Hallazgos

1. **IMPRENTAUNION-COM, ISTAT y UNION-PE estan bien conceptualizadas:** corresponden a entidades legales distintas con sus propios administradores. Este patron debe mantenerse.
2. **DTI como AU es un anti-patron:** una AU modela un dominio de administracion delegada, no un grupo de personas. El personal DTI Lima deberia estar en un Security Group `GRP-DTI-Lima`. Si se necesita que alguien administre solo cuentas DTI, ahi si tiene sentido una AU.
3. **ITService como AU es un anti-patron:** las cuentas de servicio no son un dominio de usuarios que necesitan administracion delegada. Convertir a Security Group `GRP-ServiceAccounts`.
4. **No existe AU para UPeU-Core (dominio principal):** los 73K usuarios de `upeu.edu.pe` no tienen AU, por lo que todos los role assignments que los afectan tienen scope en tenant completo. Este es el gap mas importante para la Fase 12.
5. **No existen AUs por sede (Lima, Juliaca, Tarapoto):** la delegacion de Helpdesk y User Administrator para sedes se hace con scope global, cuando deberia ser scoped.

---

## 6. Roles y permisos (estado actual)

### Resumen de assignments

| Metrica | Valor |
|---|---|
| Total role assignments | 86 |
| Scope tenant completo | 84 |
| Scope AU UNION-PE | 2 |
| Scope AU ISTAT | 1 |
| Scope AU IMPRENTAUNION-COM | 1 |
| Roles con 5+ assignments | Global Admin (3), Helpdesk Admin (10), User Admin (13), Exchange Admin (12) |

### Principals con Global Administrator

| Usuario | UPN | Observacion |
|---|---|---|
| David Urquizo | `daiurqz@upeu.edu.pe` | CTO InfraTI, DTI Lima — Global Admin correcto para este cargo |
| DIGETI Direccion General TI | `digesi@upeu.edu.pe` | Cuenta funcional de direccion — revisar si necesita Global Admin o si Billing Admin alcanza |
| Microsoft Office 365 Portal | (service principal) | Service principal de Microsoft — normal |

**Observacion:** dos cuentas humanas con Global Administrator es el minimo aceptable. Sin embargo, `digesi@upeu.edu.pe` es una cuenta funcional compartida (no personal), lo que significa que multiples personas pueden ejercer Global Admin sin auditoria individual. Recomendacion: migrar `digesi@upeu.edu.pe` a Billing Administrator y que el Global Admin sea solo `daiurqz@upeu.edu.pe` con PIM para elevacion just-in-time.

### Problema de acumulacion de roles en `mesa.sti@upeu.edu.pe`

La cuenta `mesa.sti@upeu.edu.pe` acumula simultaneamente: Helpdesk Administrator, User Administrator, Authentication Administrator, Exchange Administrator, Teams Administrator y posiblemente otros. Esto viola el principio de menor privilegio y crea un punto unico de compromiso critico. Si esta cuenta se ve comprometida, el atacante tiene control casi total del tenant.

### Roles globales que deberian ser scoped

Los siguientes roles estan asignados con scope en tenant completo pero su funcion es local:

| Rol | Usuarios afectados | Scope correcto |
|---|---|---|
| Helpdesk Administrator | `mesadeayuda.jul@upeu.edu.pe`, `mesadeayuda.tpp@upeu.edu.pe`, `digesi.tarapoto@upeu.edu.pe`, `dti.jul@upeu.edu.pe` | AU por sede (Juliaca, Tarapoto) |
| User Administrator | `direccionti.fcs@upeu.edu.pe`, `coordti.epg@upeu.edu.pe`, `direccionti.fia@upeu.edu.pe`, `ti.fce@upeu.edu.pe`, `teologia.ti@upeu.edu.pe` | AU por facultad o AU UPeU-Core |
| Authentication Administrator | `alexileiva@upeu.edu.pe`, `ti.medicina@upeu.edu.pe` | AU por facultad |
| Exchange Administrator | `notify@istat.edu.pe`, `jefatura.ti@union.pe` | AU ISTAT, AU UNION-PE (ya existen) |

### Tabla completa de role assignments por principal (84 assignments scope global)

| Rol | Principal | UPN |
|---|---|---|
| Global Administrator | David Urquizo | daiurqz@upeu.edu.pe |
| Global Administrator | DIGETI Direccion General TI | digesi@upeu.edu.pe |
| Global Administrator | Microsoft Office 365 Portal | (service principal) |
| Helpdesk Administrator | Mesa de Servicios TI | mesa.sti@upeu.edu.pe |
| Helpdesk Administrator | Mesa de Ayuda Juliaca | mesadeayuda.jul@upeu.edu.pe |
| Helpdesk Administrator | Mesa de Ayuda Tarapoto | mesadeayuda.tpp@upeu.edu.pe |
| Helpdesk Administrator | Miguel Chaponan | soporte@upeu.edu.pe |
| Helpdesk Administrator | DTI Tarapoto | digesi.tarapoto@upeu.edu.pe |
| Helpdesk Administrator | Jenson Chambi (DTI Juliaca) | dti.jul@upeu.edu.pe |
| Helpdesk Administrator | Alcy Saavedra (redes UNION) | redes@union.pe |
| Helpdesk Administrator | Sistema Academico EPG | sistemaacademico.epg@upeu.edu.pe |
| Helpdesk Administrator | Soporte Posgrado | soporteposgrado@upeu.edu.pe |
| User Administrator | Mesa de Servicios TI | mesa.sti@upeu.edu.pe |
| User Administrator | Coordinador de Sistemas FCS | direccionti.fcs@upeu.edu.pe |
| User Administrator | Coordinador TI EPG | coordti.epg@upeu.edu.pe |
| User Administrator | Direccion TI FIA | direccionti.fia@upeu.edu.pe |
| User Administrator | TI FCE Semipresencial | ti.fcesemi@upeu.edu.pe |
| User Administrator | TI PROESAD UPEU FT | tiproesad.tpp@upeu.edu.pe |
| User Administrator | Web Master EPG | webmaster.epg@upeu.edu.pe |
| User Administrator | Zileri Arapa TI EP Teologia | teologia.ti@upeu.edu.pe |
| User Administrator | ti.fce | ti.fce@upeu.edu.pe |
| User Administrator | Atencion al estudiante Academico UPeU | ae.academico@upeu.edu.pe |
| User Administrator | Jos Villegas (Plataforma Virtual) | aulavirtual@upeu.edu.pe |
| User Administrator | Sergio Calizaya Milla (UNION TI) | jefatura.ti@union.pe |
| Authentication Administrator | Alexi Josue Leiva Gonzales | alexileiva@upeu.edu.pe |
| Authentication Administrator | Medicina TI | ti.medicina@upeu.edu.pe |
| Authentication Administrator | Mesa de Ayuda Juliaca | mesadeayuda.jul@upeu.edu.pe |
| Authentication Administrator | Mesa de Servicios TI | mesa.sti@upeu.edu.pe |
| License Administrator | Coordinacion de Operaciones y Servicios TI Lima | costi.lim@upeu.edu.pe |
| License Administrator | Denis Villegas STI | ad.sti@upeu.edu.pe |
| License Administrator | Tesoreria UPeU | tesoreria@upeu.edu.pe |
| Exchange Administrator | Joselito Valdez | joselito@upeu.edu.pe |
| Exchange Administrator | Yostey Acuna | yostey.acuna@upeu.edu.pe |
| Exchange Administrator | Denis Villegas STI | ad.sti@upeu.edu.pe |
| Exchange Administrator | Mesa de Servicios TI | mesa.sti@upeu.edu.pe |
| Exchange Administrator | Mesa de Ayuda Juliaca | mesadeayuda.jul@upeu.edu.pe |
| Exchange Administrator | Mesa de Ayuda Tarapoto | mesadeayuda.tpp@upeu.edu.pe |
| Exchange Administrator | Jenson Chambi DTI Juliaca | dti.jul@upeu.edu.pe |
| Exchange Administrator | Notify ISTAT | notify@istat.edu.pe |
| Exchange Administrator | Sergio Calizaya Milla (UNION) | jefatura.ti@union.pe |
| Exchange Administrator | Miguel Chaponan | soporte@upeu.edu.pe |
| Security Administrator | Denis Villegas STI | ad.sti@upeu.edu.pe |
| SharePoint Administrator | Shiane Farfan Vergara | shiane.farfan@upeu.edu.pe |
| SharePoint Administrator | automatizacion.crai | automatizacion.crai@upeu.edu.pe |
| Teams Administrator | Mesa de Servicios TI | mesa.sti@upeu.edu.pe |
| Billing Administrator | David Barrantes (Director DTI) | digeti@upeu.edu.pe |
| Dynamics 365 Administrator | David Vilca Ccama | davidvilca@upeu.edu.pe |
| Compliance Administrator | Soporte COEM | soportecoem@upeu.edu.pe |
| Global Reader | Jenson Chambi DTI Juliaca | dti.jul@upeu.edu.pe |
| Reports Reader | Admin CRM | admincrm@upeu.edu.pe |

**Nota:** `mesa.sti@upeu.edu.pe` aparece en al menos 6 roles distintos con scope global. Requiere revision urgente.

---

## 7. Grupos

### Estado actual

| Tipo | Cantidad | Observacion |
|---|---|---|
| M365 Groups / Teams | 995 | Creados por usuarios sin gobernanza |
| Security Groups (cloud-only) | 2 | Sin dynamic membership |
| Distribution Lists | Variable (incluido en M365) | |
| Dynamic Groups | **0** | Ninguno configurado |
| AD-synced Groups | **0** | No hay AD on-prem |

### Los 2 security groups existentes

| Nombre | Proposito declarado | Analisis |
|---|---|---|
| "Estrategias basadas en la ciencia..." | No claro | Nombre no descriptivo, proposito desconocido. Revisar y probablemente eliminar. |
| `windows11` | Politica Windows 11 Enterprise (Intune) | Unico security group con proposito tecnico claro. |

### Problemas

1. **0 dynamic groups** significa que ninguna membresía se actualiza automaticamente. Si un usuario cambia de facultad o tipo, ningun grupo se actualiza.
2. **995 grupos M365/Teams** sin naming policy, sin propietario obligatorio, sin expiracion. Se acumulan indefinidamente.
3. **Sin security groups para licenciamiento:** las licencias se asignan individualmente (probablemente via Microsoft School Data Sync o manualmente), no via grupos. Esto hace imposible auditar quien tiene que licencia por que razon.
4. **Sin grupos para Conditional Access:** no hay grupos que definan politicas de acceso por tipo de usuario.

### Lo que se necesita para IGA

MidPoint en Fase 12 creara y mantendra security groups en Entra ID con estas caracteristicas:

- Creados por MidPoint (no por usuarios finales)
- Named con convencion `GRP-{TIPO}-{SCOPE}` (ej. `GRP-Student-Lima`)
- Con `description` que documente el origen IGA
- Usados como base para asignacion de licencias y Conditional Access
- Nunca editados manualmente una vez bajo gobierno IGA

---

## 8. App Registrations

### Volumen total: 200 aplicaciones

El tenant tiene 200 App Registrations, lo que indica una proliferacion no gobernada. Muchas de estas son bots de Copilot Studio creados por usuarios de negocio sin participacion de TI central.

### Aplicaciones relevantes para IGA

| App | Fecha creacion | Proposito | Estado IGA |
|---|---|---|---|
| `MidPoint-UPeU` | 2026-04-16 | Conector IGA — Graph API read/write | Activa — ampliar permisos Fase 12 |
| `KeycloakUPeU` | 2024-05-13 | SSO Keycloak ↔ Entra ID | Activa — mantener |
| `ITService-UPeU` | 2022-12-01 | Automatizacion TI interna | Revisar si coexiste con MidPoint |
| `CANVAS UPEU` | 2022-11-23 | LMS Canvas — SSO/provisioning | Activa — inventariar permisos |
| `Autodesk SSO UPeU` | 2024-05-07 | SSO Autodesk | Activa — mantener |
| `Lamb Learning` / `Lamb Mission` | Variable | Sistemas academicos UPeU | Revisar alcance |
| `n8n` | 2026-02-06 | Automatizacion de procesos | Revisar si duplica con MidPoint |

### Bots Copilot Studio (~50 apps)

Aproximadamente 50 App Registrations corresponden a bots de Microsoft Copilot Studio creados por distintas unidades (Portafolio Internado Medicina, Colportaje, etc.). Cada bot crea automaticamente su App Registration con permisos que varían. Problemas:

- Sin inventario centralizado de permisos delegados vs aplicacion.
- Sin revisiones periodicas de acceso.
- Tokens potencialmente activos sin propietario que los monitoree.
- Algunos pueden tener permisos excesivos heredados de templates.

### Apps de Dynamics 365 (~20 apps)

Relacionadas con el despliegue de Dynamics 365 Sales (CRM). Gestionadas por David Vilca Ccama (Dynamics 365 Administrator). Fuera del alcance inmediato de IGA pero deben incluirse en el inventario de aplicaciones del catalogo IGA.

### Apps sin nombre claro (~30 apps)

Aproximadamente 30 App Registrations con nombres como "app-1", timestamps, o nombres de prueba. Candidatas a revision y eliminacion tras auditoria de propietario.

### Accion requerida

Antes de Fase 12, David Urquizo debe ejecutar una auditoria de App Registrations con:

1. Identificar propietario de cada app.
2. Revocar apps huerfanas (sin propietario, sin uso en 90+ dias).
3. Documentar permisos de `MidPoint-UPeU` y expandirlos segun necesidades Fase 12.
4. Establecer proceso de aprobacion para nuevas App Registrations.

---

## 9. Diseño propuesto IGA — Administrative Units

### Principio de diseño

Cada AU modela un **dominio de delegacion administrativa**, no un grupo de usuarios. La estructura propuesta sigue el patron: una AU por entidad legal + una AU por sede para UPeU-Core.

### AUs propuestas

```
Tenant UPeU
├── AU: UPeU-Core-Lima          ← upeu.edu.pe usuarios sede Lima
├── AU: UPeU-Core-Juliaca       ← upeu.edu.pe usuarios sede Juliaca (FILIAL)
├── AU: UPeU-Core-Tarapoto      ← upeu.edu.pe usuarios sede Tarapoto (FILIAL)
├── AU: UNION-PE                ← dominio union.pe (YA EXISTE — mantener)
├── AU: ISTAT                   ← dominio istat.edu.pe (YA EXISTE — mantener)
└── AU: IMPRENTAUNION-COM       ← dominio imprentaunion.com (YA EXISTE — mantener)
```

### AUs a convertir en Security Groups

| AU actual | Accion | Reemplazar con |
|---|---|---|
| DTI | Convertir | Security Group `GRP-DTI-Lima` |
| ITService | Convertir | Security Group `GRP-ServiceAccounts` |

### Como MidPoint poblaria las AUs (Fase 12)

MidPoint asignaria usuarios a AUs via outbound mapping basado en atributos del usuario:

| Condicion (desde Oracle LAMB) | AU destino |
|---|---|
| `campus = 'Lima'` AND `organization = 'upeu.edu.pe'` | AU: UPeU-Core-Lima |
| `campus = 'Juliaca'` AND `organization = 'upeu.edu.pe'` | AU: UPeU-Core-Juliaca |
| `campus = 'Tarapoto'` AND `organization = 'upeu.edu.pe'` | AU: UPeU-Core-Tarapoto |
| `domain = 'union.pe'` | AU: UNION-PE |
| `domain = 'istat.edu.pe'` | AU: ISTAT |
| `domain = 'imprentaunion.com'` | AU: IMPRENTAUNION-COM |

La membresía en AUs en Entra ID no se gestiona via dynamic groups sino via el outbound resource MidPoint→Entra ID. MidPoint es la unica fuente de verdad para la asignacion de AU membership.

---

## 10. Diseño propuesto — Roles delegados por sede

### Modelo target

Reemplazar los 84 role assignments con scope global por assignments scoped a AU:

| Rol | Scope actual | Scope propuesto | Quien |
|---|---|---|---|
| Helpdesk Administrator | Tenant (global) | AU: UPeU-Core-Lima | `mesa.sti@upeu.edu.pe` |
| Helpdesk Administrator | Tenant (global) | AU: UPeU-Core-Juliaca | `mesadeayuda.jul@upeu.edu.pe`, `dti.jul@upeu.edu.pe` |
| Helpdesk Administrator | Tenant (global) | AU: UPeU-Core-Tarapoto | `mesadeayuda.tpp@upeu.edu.pe`, `digesi.tarapoto@upeu.edu.pe` |
| Helpdesk Administrator | AU ISTAT | AU: ISTAT (ya correcto) | `notify@istat.edu.pe` |
| Helpdesk Administrator | AU UNION-PE | AU: UNION-PE (ya correcto) | `jefatura.ti@union.pe` |
| Helpdesk Administrator | AU IMPRENTAUNION-COM | AU: IMPRENTAUNION-COM (ya correcto) | `andy.espinoza@imprentaunion.com` |
| User Administrator | Tenant (global) | AU: UPeU-Core-Lima | `mesa.sti@upeu.edu.pe` |
| User Administrator | Tenant (global) | AU por facultad (a definir) | `direccionti.fcs@upeu.edu.pe`, `ti.fce@upeu.edu.pe`, `teologia.ti@upeu.edu.pe`, etc. |
| Authentication Administrator | Tenant (global) | AU: UPeU-Core-Lima | `alexileiva@upeu.edu.pe`, `ti.medicina@upeu.edu.pe`, `mesa.sti@upeu.edu.pe` |
| Exchange Administrator | AU ISTAT | AU: ISTAT (ya correcto) | `notify@istat.edu.pe` |
| Exchange Administrator | AU UNION-PE | AU: UNION-PE (ya correcto) | `jefatura.ti@union.pe` |

### Roles que quedan en scope global (justificados)

| Rol | Principal | Justificacion |
|---|---|---|
| Global Administrator | David Urquizo (`daiurqz@upeu.edu.pe`) | CTO InfraTI DTI Lima — administrador del tenant, scope global correcto |
| Billing Administrator | David Barrantes (`digeti@upeu.edu.pe`) | Las suscripciones son tenant-wide |
| Security Administrator | Denis Villegas (`ad.sti@upeu.edu.pe`) | La seguridad es tenant-wide |
| Exchange Administrator | Joselito Valdez, Yostey Acuna, Denis Villegas | Exchange Online es tenant-wide |
| SharePoint Administrator | Shiane Farfan, `automatizacion.crai` | SharePoint Online es tenant-wide |
| Compliance Administrator | Soporte COEM | Compliance es tenant-wide |
| Dynamics 365 Administrator | David Vilca Ccama | Dynamics 365 es tenant-wide |

### Roles a revisar (posiblemente eliminar o reducir)

| Principal | Roles actuales | Recomendacion |
|---|---|---|
| `mesa.sti@upeu.edu.pe` | Helpdesk + User + Auth + Exchange + Teams (global) | Reducir a Helpdesk Admin scoped a AU Lima. Los otros roles a cuentas dedicadas. |
| `digesi@upeu.edu.pe` | Global Administrator | Bajar a Billing Administrator o similar. Si necesita Global Admin, usar PIM (just-in-time). |
| `jefatura.ti@union.pe` | User Admin global + Helpdesk AU UNION-PE | Eliminar User Admin global. Solo AU UNION-PE. |
| `dti.jul@upeu.edu.pe` | Helpdesk + Exchange + Global Reader (global) | Reducir a Helpdesk scoped AU Juliaca. Quitar Exchange y Global Reader globales. |

---

## 11. Diseño propuesto — Grupos de seguridad a crear

### Grupos de seguridad prioritarios (pre-Fase 12)

A diferencia de los grupos M365/Teams (que los crean usuarios), estos grupos los crea y mantiene el equipo DTI o MidPoint. Son la base para Conditional Access y asignacion de licencias.

| Nombre | Tipo | Proposito | Membresía | Quien gestiona |
|---|---|---|---|---|
| `GRP-Helpdesk-Lima` | Security | Agentes de helpdesk sede Lima | Manual → MidPoint Fase 12 | DTI Lima |
| `GRP-Helpdesk-Juliaca` | Security | Agentes de helpdesk sede Juliaca | Manual → MidPoint Fase 12 | DTI Juliaca |
| `GRP-Helpdesk-Tarapoto` | Security | Agentes de helpdesk sede Tarapoto | Manual → MidPoint Fase 12 | DTI Tarapoto |
| `GRP-DTI-Lima` | Security | Personal DTI Lima (reemplaza AU DTI) | Manual | DTI Lima |
| `GRP-ServiceAccounts` | Security | Cuentas desatendidas y de servicio (reemplaza AU ITService) | Manual | DTI Lima |
| `GRP-LIC-A3-Faculty` | Security | Receptores licencia M365 A3 Faculty | MidPoint Fase 12 | MidPoint |
| `GRP-LIC-A1-Student` | Security | Receptores licencia O365 A1 Student | MidPoint Fase 12 | MidPoint |
| `GRP-LIC-A1-Faculty` | Security | Receptores licencia O365 A1 Faculty | MidPoint Fase 12 | MidPoint |
| `GRP-CA-MFA-Required` | Security | Usuarios que requieren MFA (Conditional Access) | MidPoint Fase 12 | MidPoint |
| `GRP-CA-Trusted-Devices` | Security | Dispositivos corporativos confiables (Intune) | Intune | DTI |

### Grupos a crear antes de MidPoint (accion inmediata de David)

Los tres grupos de Helpdesk por sede pueden crearse ahora manualmente para permitir scope correcto en role assignments:

```
GRP-Helpdesk-Lima       → miembros actuales: mesa.sti, soporte, alexileiva, ti.medicina
GRP-Helpdesk-Juliaca    → miembros actuales: mesadeayuda.jul, dti.jul
GRP-Helpdesk-Tarapoto   → miembros actuales: mesadeayuda.tpp, digesi.tarapoto
```

---

## 12. Prerrequisitos para activar IGA

### Permisos que David Urquizo debe conceder a `MidPoint-UPeU`

La App Registration `MidPoint-UPeU` existe desde 2026-04-16. Para que MidPoint pueda operar en Fase 12 (provisioning outbound hacia Entra ID), David debe conceder los siguientes permisos via la consola de Entra ID (`App registrations > MidPoint-UPeU > API permissions`):

**Permisos de lectura (ya deberan estar activos para Fases 1-11):**

| Permission | Tipo | Justificacion |
|---|---|---|
| `User.Read.All` | Application | Leer todos los usuarios para correlacion |
| `Group.Read.All` | Application | Leer grupos para inventario |
| `Directory.Read.All` | Application | Leer estructura del directorio |
| `AuditLog.Read.All` | Application | Lectura de audit log para evidencia ISO 27001 |
| `AdministrativeUnit.Read.All` | Application | Leer AUs para correlacion |

**Permisos de escritura (activar en Fase 12 — requieren aprobacion explicita):**

| Permission | Tipo | Justificacion |
|---|---|---|
| `User.ReadWrite.All` | Application | Escribir atributos estructurados (department, employeeType, officeLocation) |
| `Group.ReadWrite.All` | Application | Crear y mantener security groups IGA |
| `AdministrativeUnit.ReadWrite.All` | Application | Agregar/remover usuarios de AUs |
| `Directory.ReadWrite.All` | Application | Operaciones de directorio generales |

**IMPORTANTE:** los permisos de escritura requieren `Grant admin consent` por parte de David Urquizo. No se activan solos con la asignacion. Este es el paso que Alberto no puede hacer por su cuenta.

### Acciones previas que debe ejecutar David (sin MidPoint)

| # | Accion | Razon | Urgencia |
|---|---|---|---|
| D1 | Resolver licencias sobreusadas (`A5_Faculty`, `Teams_Premium`) | Compliance Microsoft | Inmediata |
| D2 | Investigar y resolver `Copilot_EDU` 8 asignadas / 0 prepagadas | Evitar facturacion imprevista | Inmediata |
| D3 | Crear AUs `UPeU-Core-Lima`, `UPeU-Core-Juliaca`, `UPeU-Core-Tarapoto` | Base para scope de roles | Alta |
| D4 | Reducir scope de 84 role assignments globales a AUs correspondientes | Seguridad — menor privilegio | Alta |
| D5 | Separar roles de `mesa.sti@upeu.edu.pe` en cuentas dedicadas | Eliminar punto unico de compromiso | Alta |
| D6 | Conceder permisos de lectura a `MidPoint-UPeU` y hacer Grant admin consent | Habilitar correlacion IGA | Alta |
| D7 | Auditar App Registrations sin propietario (target: 200 → menos de 100) | Reducir superficie de ataque | Media |
| D8 | Implementar naming policy para grupos M365/Teams | Gobernanza de grupos | Media |
| D9 | Habilitar expiracion de grupos M365 (90-180 dias) | Higiene del directorio | Media |
| D10 | Mover `digesi@upeu.edu.pe` de Global Admin a rol menor + PIM | Menor privilegio en cuentas funcionales | Media |

---

## 13. Problemas a resolver

Lista priorizada de problemas identificados. Clasificados por impacto en el proyecto IGA y en la seguridad del tenant.

### Criticos (bloquean Fase 12 o representan riesgo de seguridad activo)

| # | Problema | Impacto | Accion |
|---|---|---|---|
| P1 | `department`, `employeeType`, `officeLocation`, `companyName` vacios en ~100% usuarios | MidPoint no puede clasificar ni correlacionar usuarios en Entra ID | Resolver via write-back MidPoint Fase 12. No poblar manualmente. |
| P2 | 84 role assignments con scope global cuando deberian ser scoped | Un Helpdesk de Juliaca puede resetear passwords de cualquier usuario del tenant | Crear AUs por sede y re-scopear. Accion D3 + D4. |
| P3 | `mesa.sti@upeu.edu.pe` con 6+ roles globales simultaneamente | Punto unico de compromiso critico | Separar en cuentas dedicadas por funcion. Accion D5. |
| P4 | 0 dynamic groups con P1 habilitado | Licencias y Conditional Access no pueden automatizarse | Crear dynamic groups tras resolver atributos. Post-Fase 12. |
| P5 | Licencias sobreusadas (`A5_Faculty` 16/15, `Teams_Premium` 19/18) | Incumplimiento contractual con Microsoft | Accion D1 — inmediata. |
| P6 | `Copilot_EDU` 8 asignadas / 0 prepagadas | Posible deuda oculta | Accion D2 — inmediata. |

### Importantes (degradan la calidad del gobierno de identidades)

| # | Problema | Impacto | Accion |
|---|---|---|---|
| P7 | 0 security groups para licenciamiento | No hay auditoria de "quien tiene que licencia por que" | Crear GRP-LIC-* y migrar asignaciones. Post-Fase 12 con MidPoint. |
| P8 | `digesi@upeu.edu.pe` como Global Admin (cuenta funcional compartida) | Multiples personas con Global Admin sin auditoria individual | Bajar a Billing Admin + PIM. Accion D10. |
| P9 | AU `DTI` y AU `ITService` con proposito incorrecto (son grupos, no dominios de delegacion) | Confusion en el modelo de governance | Convertir a Security Groups. |
| P10 | ~30 App Registrations sin nombre o huerfanas | Superficie de ataque activa con tokens validos potencialmente | Auditoria y limpieza. Accion D7. |
| P11 | ~50 bots Copilot Studio sin gobernanza de permisos | Permisos delegados no revisados en Graph API | Inventariar y aplicar Access Reviews (requiere Entra P2). |
| P12 | No existe AU `UPeU-Core` para los 73K usuarios de `upeu.edu.pe` | Sin base estructural para governance del dominio principal | Crear AUs por sede. Accion D3. |

### Menores (mejoras de higiene)

| # | Problema | Accion |
|---|---|---|
| P13 | 995 grupos M365/Teams sin naming policy ni expiracion | Implementar naming policy + expiracion 180 dias. Accion D8 + D9. |
| P14 | Security Group "Estrategias basadas en la ciencia..." sin proposito claro | Revisar y eliminar o renombrar. |
| P15 | `jefatura.ti@union.pe` con User Administrator global ademas de roles AU UNION-PE | Revocar User Admin global. Solo AU UNION-PE es suficiente. |
| P16 | `dti.jul@upeu.edu.pe` con Exchange Administrator + Global Reader globales | Revocar ambos. Solo Helpdesk scoped a AU Juliaca. |

---

## Apendice — Relacion con el roadmap IGA

Este documento es insumo para la planificacion de la **Fase 12** del roadmap IGA UPeU (provisioning outbound hacia Entra ID). Las fases anteriores (1-11) tratan Entra ID como solo lectura.

| Fase IGA | Accion sobre Entra ID |
|---|---|
| Fase 5 (actual) | Resource Entra ID read-only — correlacion de usuarios via UPN |
| Fases 6-11 | Sin cambios en Entra ID. Provisioning va a OpenLDAP + Keycloak. |
| Fase 12 | Write-back MidPoint→Entra ID: atributos estructurados + AU membership + security groups + asignacion de licencias via grupos |

**Prerequisito no negociable para Fase 12:** David Urquizo debe completar las acciones D1-D6 de la seccion 12 antes de que MidPoint pueda escribir en Entra ID de forma segura y util.

---

*Documento generado el 2026-05-19 por Alberto Sánchez (DTI UPeU). Snapshot basado en datos del tenant a la misma fecha.*
