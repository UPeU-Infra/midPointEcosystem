# Fuentes autoritativas del Estado — nombres y políticas canónicas

**Estado:** VIGENTE · fijado el 2026-08-11
**Regla:** cuando estos documentos y un sistema interno discrepan, **manda el documento**.
El IGA adopta el vocabulario del Estado; no se inventan códigos ni denominaciones.

---

## 1. Los tres identificadores oficiales

| Identificador | Qué nombra | Documento que lo fija |
|---|---|---|
| **P-code / SEG-code** (`P25`, `SEG61`) | el programa de estudios | Formatos de Licenciamiento **A4 y A8 2026-1** — 183 programas |
| **Código de local** (`SL01`, `F01L01`, `F02L01`) | el campus | **RCD N° 054-2018-SUNEDU/CD**, Anexo 01, Tabla N° 01 |
| **Código INEI** (8 dígitos) | el programa en el clasificador nacional | **Clasificador Nacional de Programas 2022 (INEI)** |

SUNEDU usa **P-code y código de local juntos** en sus resoluciones. Verificado en la
[RCD N° 140-2022-SUNEDU/CD](https://busquedas.elperuano.pe/dispositivo/NL/2136040-1)
(20-dic-2022), que aprueba P06, P22, P25 y P31 sobre los locales SL01, F01L01 y F02L01.

## 2. Los locales

| Código | Local | Ubicación |
|---|---|---|
| `SL01` | Sede Lima | Carretera Central Km 19, Ñaña, Lurigancho-Chosica, Lima |
| `F01L01` | Filial Juliaca | Fundo Chullunquiani Illapuso, San Román, Puno |
| `F02L01` | Filial Tarapoto | Jr. Los Mártires 340, Morales, San Martín |

Solo cambian por resolución del Consejo Directivo. **No se editan** para reflejar
reorganizaciones internas de UPeU.

## 3. Tres niveles que NO deben mezclarse

| Nivel | Qué es | Fuente | Cambia cuando |
|---|---|---|---|
| **Autorización de programa** | qué puede dictar UPeU | A4/A8 | SUNEDU lo aprueba o lo cierra |
| **Local reconocido** | qué campus existen ante el Estado | RCD 054-2018 y modificatorias | resolución del CD |
| **Oferta real por campus** | qué se dicta hoy en cada sede | Oracle LAMB | alumnos, presupuesto — decisión interna |

Los dos primeros son **actos del Estado**; el tercero es **operación**. El cruce
programa × campus para reportes se **regenera de Oracle**, nunca se congela en el repo:
en cuanto una filial abre o cierra un programa, una tabla fija pasa a mentir.

⚠️ **El P-code es agnóstico al campus.** Un mismo programa puede dictarse en varias sedes
(19 de 103 lo hacen). Derivar el campus del P-code es imposible por definición, no por
falta de datos.

## 4. Cómo se usa en el IGA

| Atributo | Dónde vive | Fuente |
|---|---|---|
| `academicProgramSuneduCode` | persona | A4/A8 vía LookupTable del tesauro |
| `suneduLocalCode` | **Org de campus** | RCD 054-2018 |
| `campusEgreso` | persona | `DAVID.VW_PERSONA_EGRESADO.SEDE` |
| `academicProgramIneiCode` | persona | Clasificador INEI 2022 — **solo** repositorio de tesis |

### Por qué `campusEgreso` es un atributo aparte

`campusStudent` describe **dónde estudia hoy** y se vacía al perder la matrícula, por diseño.
El campus de egreso es un **hecho consumado**: si una filial deja de ofertar un programa,
quien ya egresó de él allí sigue siendo de esa filial. Derivarlo de la oferta vigente daría
una respuesta distinta cada año.

Lo consume el outbound `library_id` de Koha, que sin campus rechaza el alta con
*Missing property: library_id*.

## 5. Documentos

- `~/Downloads/programas pxx upeu/` — Formatos A4 y A8 2026-1
- `~/Downloads/resolucion upeu licenciamiento/` — RCD 054-2018 y su Anexo 01
- `~/Downloads/clasificador_de_carreras_inei/` — Clasificador Nacional 2022
- [RCD 140-2022 en El Peruano](https://busquedas.elperuano.pe/dispositivo/NL/2136040-1)

**Cadena de modificatorias conocida:** 054-2018 → 033-2021 → 056-2021 → 140-2022 → …
La lista pública de SUNEDU solo muestra la licencia original; las modificatorias no aparecen
ahí. Para la vinculación programa × local **al día** hay que reunir la cadena completa.
