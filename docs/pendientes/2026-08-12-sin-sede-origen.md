# Personas activas sin sede en el origen — bloquea su cuenta de biblioteca

**Fecha de medición:** 12-ago-2026 · **Fuente:** MidPoint PROD (`m_user`)

## Qué pasa

Koha exige `library_id` (sede) para crear un patron. Estas personas no tienen sede
en ninguno de los tres campos (`campusStudent`, `campusWorker`, `campusEgreso`),
porque **la ficha de Oracle no la trae**. El alta falla con:

```
{"errors":[{"message":"Missing property.","path":"/body/library_id"}],"status":400}
```

**No es un fallo del IGA ni de Koha.** En cuanto Oracle traiga la sede, la
reconciliación diaria les crea la cuenta sola: no hay que lanzar nada.

**No se imputa una sede por defecto** a propósito: metería a la persona en la
biblioteca equivocada, con sus préstamos y sanciones en la sede que no le toca.

## Estudiantes — 14 · escalar a Registros Académicos

| Código | Nombre | Nivel | ¿Tiene Koha? |
|---|---|---|---|
| `202412763` | Marvin Aldo Medina Taipe | Pregrado | **no** |
| `202520151` | NELIDA EUGENIA HUALLPA CHECMAPUCO | Pregrado | **no** |
| `202520474` | ANA MARIA PAPEL SOTOMOLLO | Pregrado | **no** |
| `202520477` | Alexia Pashanasi Isuiza | Pregrado | **no** |
| `202520889` | KATHERINE MISHELL LARICO ESPINOZA | Pregrado | **no** |
| `202610156` | ALEXANDER JESUS ROJAS MACEDO | Pregrado | **no** |
| `202611115` | MARILUZ ANGELA QUISPE QUISPE | Pregrado | **no** |
| `202613206` | Valentina Belen Esquivel Velarde | Pregrado | **no** |
| `202613796` | ELIT ROLANDO VARGAS TIPULA | Pregrado | **no** |
| `202613860` | ALEX ROBERTO NAYRA CASTILLO | Pregrado | **no** |
| `202613878` | Deywint Emanuel Huaman Campos | Pregrado | **no** |
| `202614012` | YENNY MARIELA CHUQUITARQUI PARICAHUA | Pregrado | **no** |
| `202614149` | Aldo Jimmy Larico Larico | Pregrado | **no** |
| `202614408` | JHOSELINE KATHY ROJAS MACHACA | Pregrado | **no** |

## Personal — 5 · escalar a RR. HH.

| Código | Nombre | Tipo | ¿Tiene Koha? |
|---|---|---|---|
| `41371678` | Roxana Elizabeth Kala Mendoza | Administrativo | sí |
| `70071601` | Yessenia Luz Damian Cordova | Administrativo | **no** |
| `73127501` | Ana Cristina Llancari Torre | Administrativo | **no** |
| `75778245` | Angela Yaqueline Zamudio Castro | Administrativo | sí |
| `92589986` | Titi Anelit Carrasco Fasanando | Administrativo | **no** |

## Resumen

- **19** personas activas sin sede.
- **17** no tienen cuenta de biblioteca hoy.
- Las 2 que sí la tienen la obtuvieron por adopción de un patron previo;
  el `library_id` solo bloquea el alta nueva.
- **12 de los 14 estudiantes son código 2025-2026**: el hueco se está produciendo
  ahora, en las altas nuevas, no es deterioro histórico.

## Qué se pide

Completar la sede de estas fichas en el sistema de origen (Oracle LAMB).
