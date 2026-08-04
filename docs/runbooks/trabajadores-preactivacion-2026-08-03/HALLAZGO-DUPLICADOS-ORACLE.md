# Fichas de persona duplicadas en el maestro de LAMB

**Fecha:** 2026-08-04 · **Medido en vivo** contra `ELISEO.VW_APS_EMPLEADO` (192.168.13.9)
**Origen:** los 3 duplicados que destapó la simulación de pre-activación
(`RESULTADO-SIMULACION.md`) resultaron ser la punta de un problema mayor.
**Destinatario:** DBAs de LAMB / RRHH · **No es accionable desde MidPoint**

---

## 1. Es un problema de Oracle, no de Recursos Humanos

La evidencia es el `ID_CONTRATO`. Los contratos de las personas afectadas **aparecen bajo los dos
`ID_PERSONA`**, con la misma `ID_ENTIDAD`, mismo `ID_CATEGORIAOCUPACIONAL`, mismo `ID_DEPTO` y
mismas fechas de inicio. Ejemplos:

| Persona | `ID_CONTRATO` compartidos | `ID_PERSONA` |
|---|---|---|
| Luzirene Gomes de Alcantara | 17192, 23899, 25932, 28770, 29553, 34006, 34931, 36338, 38675, 39223, 41078, 43369, 45067, 46366, 48108, 48218 | 11173 **y** 192480 |
| Katty Porras Espinoza | 57431, 62064, 62406 | 3999385 **y** 4055270 |

Un contrato se firma una vez. Si el mismo `ID_CONTRATO` cuelga de dos fichas, lo duplicado es la
**ficha de persona**, no el contrato. Lo confirma el `COD_ASISTENCIA` —el código de marcación y
planilla— que es **idéntico** en ambas fichas (614192, 44528386).

> **RRHH tiene un expediente por persona. El maestro de LAMB guarda dos fichas apuntando a él.**

**Causa aparente:** en todos los pares, la ficha nueva trae `NUM_CUSPP` y la vieja no. El duplicado
se crea al re-empadronar a la persona (afiliación AFP, o corrección de documento) generando ficha
nueva en vez de editar la existente.

### Límite de esta medición

**No se ha verificado el sistema de planillas.** Que `ID_CONTRATO` y `COD_ASISTENCIA` sean únicos
hace improbable el pago duplicado, pero eso se comprueba en remuneraciones, no en esta vista.

---

## 2. Dimensión

Controlado por `ID_ENTIDAD` (⚠️ `ID_CONTRATO` **no** es único globalmente: sin ese control el
conteo pasa de 1.199 a 5.689 — artefacto).

| | |
|---|---|
| `COD_ASISTENCIA` distintos en la vista | 35.270 |
| **Humanos con ficha duplicada** (`COD_ASISTENCIA` con 2+ `ID_PERSONA`) | **544** (1,5 %) |
| **…de esos, con contrato VIVO** (`ESTADO='A'`, `ID_ENTIDAD=7124`) | **16** ← accionable |
| `COD_ASISTENCIA` con 2+ `NOM_PERSONA` (homonimia real, **no** duplicado) | 138 |

Trabajadores vivos (`ESTADO='A'`, `ID_ENTIDAD=7124`): 7.924 filas → **3.541 personas**
(3.556 `ID_PERSONA`, 3.543 `COD_APS`; la diferencia es justo el ruido de estos duplicados).

---

## 3. Los 16 con contrato vivo

### 3.1 🔴 Documento equivocado — lo más grave

No es un problema de identidad: es un **dato de RRHH incorrecto** en un trabajador activo.

| Persona | `COD_ASISTENCIA` | Documento ficha A | Documento ficha B |
|---|---|---|---|
| CHURA MUÑUICO, Ruth Yenny | 41538729 | `41538729` (9741) | **`40538729`** (221342) |
| TIPO MAMANI, Noe Wilber | 47259697 | `47259697` (191491) | **`47259698`** (16628) |
| CHOQUE MAMANI, Anderson | 70405908 | `70405908` (9636) | **`23926979`** (3921969) |
| APAZA CALLA, Emanuel Humberto | 29602459 | `29602459` (206083) | **`71459568`** (7912) |

### 3.2 Cambio de documento (CE → DNI)

| Persona | `COD_ASISTENCIA` | Ficha vieja | Ficha nueva |
|---|---|---|---|
| GOMES DE ALCANTARA, Luzirene | 614192 | 11173 · CE `00614192` | 192480 · DNI `000614192` + CUSPP |
| JORDAN CHIRINO, Candy Isabel | 1794507 | 74156 · CE `001794507` + CUSPP | 412415 · DNI `01794507` |
| CARMONA BELLO, Carlos Javier | 3012465 | 385145 · CE `003012465` + CUSPP | 3945028 · DNI `03012465` |
| BALDERAS LOPEZ, Juan Carlos | 4204048 | 211002 · CE `004204048` + CUSPP | 3945027 · DNI `04204048` |
| MERCHAN URDANETA, Isai David | 1777564 | 22021 · DNI `01777564` | 3932677 · CE `001777564` + CUSPP |

### 3.3 Padding de ceros

| Persona | `COD_ASISTENCIA` | Variantes |
|---|---|---|
| **CORTEZ BAZANTES, Orlando Gabriel** *(caso ya conocido)* | 534601 | `000534601` · `00000000534601` · `0534601` |
| TOVAR GALARCIO, Andres Alfonso | 1574315 | `01574315` · `001574315` |
| LOPEZ AVILA, Juan Alexander | 4082096 | `04082096` · `004082096` |
| ROJAS HERNANDEZ, Eliasib Nemecio | 4680920 | `04680920` · `004680920` |
| PEREIRA PINZON, Adrian Alberto | 6158248 | `06158248` · `006158248` |
| VELASQUEZ CALVO, Ana Cristina | 6645032 | `06645032` · `006645032` |
| BERROCAL ROJAS, Jimena Milagros | 60774337 | `60774337` · `060774337` |

---

## 4. 🔴 Lo que sí rompe al IGA: fechas y estados incoherentes

| Medición (controlada por `ID_ENTIDAD` + mismo `NOM_PERSONA`) | |
|---|---|
| Contratos con **2+ `FEC_TERMINO`** distintas según la ficha | **64** |
| Contratos con **2+ `ESTADO`** distintos según la ficha | **124** |

Ejemplo — contrato **48218** de Luzirene:

| Ficha | `FEC_TERMINO` | `ESTADO` |
|---|---|---|
| `ID_PERSONA` 11173 | **2026-02-28** | **A** |
| `ID_PERSONA` 192480 | **2025-02-28** | **I** |

**La fecha de cese que lee MidPoint depende de qué ficha le toque.** Con el leaver gap ya cerrado
(el outbound de `activation` escribe `midPointAccountStatus` en LDAP desde el 03-ago), esto se
traduce en **cortar o mantener accesos con un año de desfase**, en cualquiera de los dos sentidos.

---

## 5. Qué se pide

| # | Acción | Dueño |
|---|---|---|
| 1 | **Corregir los 4 documentos equivocados** (§3.1) — no es deduplicación, es un dato mal capturado | RRHH |
| 2 | Fusionar las fichas duplicadas de los 16 vivos, conservando la que tiene `NUM_CUSPP` | DBAs LAMB |
| 3 | Resolver las 64 `FEC_TERMINO` y 124 `ESTADO` incoherentes — **bloquea la fiabilidad del corte de accesos** | DBAs LAMB |
| 4 | Evitar la causa: al corregir documento o afiliar a AFP, **editar la ficha existente**, no crear una nueva | RRHH / LAMB |
| 5 | Verificar en remuneraciones que ninguna de las 16 genera doble pago (no comprobable desde esta vista) | RRHH |

Las 528 restantes (sin contrato vivo) no son urgentes, pero sí explican parte del ruido histórico
de correlación en MidPoint.

---

## 6. Lo que el IGA hará mientras tanto

No puede unir estas fichas: en la fuente son dos personas distintas. Lo que **sí** corresponde
arreglar en MidPoint (ver `RESULTADO-SIMULACION.md` §recomendaciones):

- **Tier de correlación por `externalSystemId` / `lambIdPersona`** — resuelve el caso Evanilda
  (misma persona, `lambIdPersona` 68833 a ambos lados), que **no** es un duplicado de Oracle: en
  Trabajadores tiene una sola fila limpia, y el choque es contra su registro de egresada.
- **Abrir `disputed` ante homónimo exacto** en vez de crear en silencio, que es lo que dejó pasar
  los 3 casos de la simulación sin una sola señal.
