# Personas activas sin sede — DOS problemas distintos, no uno

**Medido:** 12-ago-2026 · **Fuente:** MidPoint PROD

> Corrección sobre la primera versión de este documento: los 19 casos **no son el
> mismo problema**. Solo 5 necesitan que se complete la sede. Los otros 14 ni
> siquiera estan matriculados, y pedir su sede seria un encargo mal planteado.

---

## A) 5 trabajadores VIGENTES sin sede — escalar a RR. HH.

Tienen **ficha viva en Oracle Trabajadores** y la reconciliacion de hoy los toco
(11:08-11:13). Uno se dio de alta ayer. Son personal contratado **hoy**.

Koha exige `library_id` para crear el patron y su ficha no trae sede:

```
{"errors":[{"message":"Missing property.","path":"/body/library_id"}],"status":400}
```

| Código | Nombre | Tipo | ¿Tiene Koha? |
|---|---|---|---|
| `41371678` | Roxana Elizabeth Kala Mendoza | Administrativo | sí |
| `70071601` | Yessenia Luz Damian Cordova | Administrativo | **no** |
| `73127501` | Ana Cristina Llancari Torre | Administrativo | **no** |
| `75778245` | Angela Yaqueline Zamudio Castro | Administrativo | sí |
| `92589986` | Titi Anelit Carrasco Fasanando | Administrativo | **no** |

**Qué se pide:** completar la sede en Oracle LAMB. En cuanto este, la recon diaria
les crea la cuenta sola — no hay que lanzar nada desde el IGA.

**No se imputa una sede por defecto:** meteria a la persona en la biblioteca
equivocada, con sus prestamos y sanciones en la sede que no le toca.

---

## B) 14 estudiantes que NO estan matriculados — no es un problema de sede

| | |
|---|---|
| Ficha viva en Oracle Estudiantes | **0** de 14 |
| Creados | todos el **2026-05-27**, el mismo dia |
| Ultima modificacion | 16-17 de julio; nadie los toca desde entonces |

Son `User` creados en bloque en una carga del 27-may que **nunca tuvieron o ya
perdieron su ficha de matricula**. Ninguna reconciliacion los mira porque no estan
en la fuente.

**Que NO se les tiene cuenta de biblioteca es correcto:** quien no esta matriculado
no debe tenerla. Aqui no falta la sede.

**La pregunta real para Registros Academicos:** por que existen como estudiantes
activos sin matricula. Preinscritos que no llegaron a matricularse, bajas mal
procesadas, o restos de la carga de mayo.

Codigos: `202412763`, `202520151`, `202520474`, `202520477`, `202520889`, `202610156`, `202611115`, `202613206`, `202613796`, `202613860`, `202613878`, `202614012`, `202614149`, `202614408`

> El codigo 2025-2026 indica el cohorte, **no** prueba de matricula. Leerlo como
> "ingresos recientes" fue el error de la primera version.
