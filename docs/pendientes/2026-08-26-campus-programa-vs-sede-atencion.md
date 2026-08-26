# La sede de Koha sale del campus del PROGRAMA, no de dónde estudia la persona

**26-ago-2026 · diagnóstico, sin cambios aplicados**
**Responde a:** [`upeu/docs/prompts/2026-08-26-koha-sede-alumnos-juliaca.md`](../../upeu/docs/prompts/2026-08-26-koha-sede-alumnos-juliaca.md)

Walter (CRAI Juliaca) reportó tres alumnos de Juliaca asignados a la biblioteca de Lima (`BUL`),
a los que su sede no puede atender. Todo lo de aquí está medido en producción; **no se aplicó
ningún cambio**, como pedía el encargo.

## 1. El mapping desplegado hace lo que se describía

`library-id-outbound` (`ri:library_id`, `strong`) resuelve con precedencia
**`campusStudent` → `campusWorker` → `campusEgreso` → `locality`**, con dos excepciones previas:
un OID de superadmin y `campusWorker == 'CIA'`. Con `campusStudent = LIMA`, **`locality` no se
llega a evaluar**. Confirmado leyendo el recurso desplegado, no el repo.

## 2. `campusStudent` y `locality` son el mismo dato con distinta fuerza

Ambos salen de **la misma columna** (`ri:SEDE_NOMBRE`, resource *Oracle LAMB Estudiantes v3*) y
con **el mismo script**:

```groovy
def v = (input ?: '').toString().trim()
['Sede Lima':'LIMA','Filial Tarapoto':'TARAPOTO','Filial Juliaca':'JULIACA'].getOrDefault(v, 'LIMA')
```

| Inbound | Fuerza | Destino |
|---|---|---|
| `sede-nombre-to-locality` | **weak** | `locality` |
| `sede-nombre-to-campusStudent` | **strong** | `extension/sciback:campusStudent` |

Dos consecuencias:

- **Corregir `campusStudent` a mano no aguanta.** Es `strong` desde Oracle: el siguiente
  recálculo lo revierte. Es exactamente lo que ocurrió con `emailAddress`.
- ⚠️ **`getOrDefault(v, 'LIMA')` inventa Lima** cuando el valor no está en el diccionario. No es
  la causa de estos tres casos, pero es una trampa latente: contradice el criterio del mapping
  equivalente de LDAP (`scibackCampusCode`), que dice *"sin default: valor desconocido → null,
  no se inventa"*. Un nombre de sede nuevo o con otra grafía mandaría gente a Lima en silencio.

## 3. El dato de Oracle NO está mal

Los tres casos, leídos de su shadow de Estudiantes:

```
202212553 · SEDE_NOMBRE = 'Sede Lima' · SCHOOL_NAME = Inglés · pregrado
202312727 · SEDE_NOMBRE = 'Sede Lima' · SCHOOL_NAME = Inglés · pregrado
202411784 · SEDE_NOMBRE = 'Sede Lima' · SCHOOL_NAME = Inglés · pregrado
```

Los tres son de la escuela **Inglés (Centro de Idiomas)**. El programa está adscrito a Lima y
ellos lo cursan en Juliaca. **Oracle dice la verdad sobre el programa**; lo que no existe en el
modelo es *dónde estudia la persona*.

**La hipótesis del encargo —"el dato está mal en LAMB y lo corrige Registros Académicos"— queda
descartada.** No hay nada que corregir en el origen.

## 4. No son tres: son 1.900

**1.900 personas activas** tienen `campusStudent` distinto de `locality`. Es la segunda rama de
la disyuntiva del propio encargo: **decisión de política, no error de datos**.

## 5. Por qué no basta con que `locality` desempate

La opción que se planteaba —usar `locality` cuando difiera— tiene dos problemas:

1. Reasignaría la sede de **1.900 personas de golpe**, con un mapping `strong` que escribe en
   Koha en la siguiente reconciliación.
2. **`locality` es `weak`**: puede venir de cualquier fuente y nadie lo gobierna con rigor.
   Apoyar la sede de atención en el atributo menos fiable del modelo cambia un problema por otro.

## 6. Lo que falta es una pieza del modelo

**Campus del programa ≠ sede de atención.** Hoy solo existe el primero. El segundo necesita
atributo propio, fuente definida y gobierno — es modelo nuevo, no un ajuste de mapping.

Mientras tanto, para desbloquear a Walter caben dos caminos, y la diferencia no es técnica:

- **excepción explícita para esos tres**, al estilo de la que ya existe para `CIA`; o
- **regla para todos los de Idiomas en filiales**, que ya son cientos.

Decidir cuál es el criterio *antes* de escribir el código evita que la excepción se convierta en
la regla por acumulación.
