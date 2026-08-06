# Managers de organización: la fuente existe, pero no dice lo que necesitamos

**Fecha:** 2026-08-06 · **Medido en vivo (Oracle LAMB + PROD)** · **Nada ejecutado**
**Ampara:** D5 de [`ARQUITECTURA-ARBOL-ORGANIZATIVO.md`](ARQUITECTURA-ARBOL-ORGANIZATIVO.md)

---

## 1. La fuente

**`ELISEO.ORG_AREA_RESPONSABLE`** — 11.382 filas históricas.
Columnas: `ID_RESPONSABLE`, **`ID_SEDEAREA`**, **`ID_NIVEL`**, **`ID_ANHO`**, **`ID_PERSONA`**,
`FECHA`, `ACTIVO`.

Vigentes (`ACTIVO='1'`, `ID_ANHO>=2026`): **1.848 filas · 434 sede-áreas · 443 personas**.
Niveles presentes: 1 (495), 2 (243), 3 (583). Existe además `ENOC.PLLA_TIPO_JEFE`
(*Ninguno / Jefe Dirección / Jefe de Área / Jefe Sección / Jefe Grupo*), catálogo aparte.

## 2. Por qué NO se puede mapear a `org:manager` tal cual

### 2.1 No es una jefatura única — es una lista

| Área | Responsables vigentes |
|---|---|
| `113` Imprenta Unión | **123** |
| `107` EP Arquitectura | 57 |
| `104` EP Ingeniería de Sistemas | 53 |
| `27` Servicio de Alimentación | 51 |

**421 grupos `(ID_SEDEAREA, ID_NIVEL)` tienen más de un responsable** en 2026. Ni siquiera
fijando sede y nivel se obtiene una persona: el grano de la tabla no es "el jefe".

Todo apunta a que es una tabla de **autorizadores/aprobadores** (pedidos, compras, permisos),
no de mando. Asignar `org:manager` desde aquí produciría organizaciones con decenas de
"managers" — inútil para certificaciones y peligroso si de ahí cuelgan aprobaciones.

**Falta la regla de negocio**: quién, de esa lista, es el titular. Es pregunta para Talento
Humano, no para inferir desde los datos.

### 2.2 🔴 El grano es `ID_SEDEAREA`, no `ID_AREA` — D5 depende de D1

La tabla asigna responsable a **un área EN una sede**. Las orgs de MidPoint hoy son **por área**
(`identifier = ID_AREA`), sin dimensión de sede.

Consecuencia: *"el jefe de Contabilidad en Juliaca"* y *"el jefe de Contabilidad en Lima"* son
personas distintas que **hoy colapsan sobre la misma org**. Buena parte de la multiplicidad del
punto 2.1 es precisamente eso.

> **Los managers no se pueden modelar correctamente antes de la rama de sedes.**
> El orden del §3 del documento rector debe invertirse: **primero D1 (sedes), después D5**.

### 2.3 Cobertura, para dimensionar

De las 172 orgs de PROD con `identifier`, **93 tienen algún responsable vigente** (54 %); 79 no.
De las 227 áreas con responsable en Oracle, solo 93 existen como org en MidPoint — el resto son
sede-áreas que no se sincronizan o áreas fuera del árbol.

Con el filtro más estricto (`ID_NIVEL=1`, 2026): **167 áreas distintas**.

## 3. Qué hace falta antes de ejecutar

1. **Regla de negocio de Talento Humano**: ¿qué identifica al titular? ¿`ID_NIVEL=1` + el más
   reciente por `FECHA`? ¿Se cruza con `PLLA_TIPO_JEFE`? ¿Hay una tabla de cargos que no hemos
   encontrado?
2. **La rama de sedes (D1)**, para que un responsable por sede tenga org donde colgarse.
3. Solo entonces: `assignment` con `relation=org:manager`, simulación previa y verificación.

## 4. Lo que NO se hará

Elegir un responsable arbitrario de la lista (el primero, el de menor `ID_RESPONSABLE`, el más
reciente) para "tener managers". Un manager equivocado es peor que ninguno: de él cuelgan
certificaciones de acceso y aprobaciones, y su firma quedaría en decisiones de gobierno.

Es la misma regla que D2 del documento rector: **el IGA refleja la realidad, no la fabrica.**
