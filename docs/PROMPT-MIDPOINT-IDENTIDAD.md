# Prompt de arranque — MidPoint / IGA UPeU

> Pegar al iniciar una sesión de trabajo sobre identidad en UPeU. Da el estado
> real del sistema, sus fuentes autoritativas y los puntos donde la identidad se
> cruza con el tesauro institucional. Actualizado 2026-08-05.

---

## Quién eres en esta sesión

Trabajas sobre el **IGA de la Universidad Peruana Unión**: MidPoint 4.10.x
gobernando el ciclo de vida de ~35 450 identidades (1 679 estudiantes activos,
30 491 alumni, más docentes y administrativos).

**Política del proyecto, no negociable:** toda tarea de MidPoint —XML, archetypes,
roles, resources, tasks, ninja, REST API, diagnóstico, operación en PROD— se
delega al sub-agente `midpoint-expert`, que a su vez consulta las skills
`midpoint-best-practices` e `iga-canonical-standards` antes de decidir nada.
No descubras MidPoint empíricamente desde el hilo principal.

**Regla rectora:** el modelo canónico manda; los datos de UPeU se adaptan al
modelo, nunca al revés.

---

## El sistema

| | |
|---|---|
| **PROD** | `192.168.15.166` (alias SSH `midpoint-prod`, usuario `juansanchez`) |
| Dev / Sandbox | `192.168.15.230` / `.231` (usuario `ticrai`) |
| Secretos | `~/.secrets/midpoint-upeu.env` (PROD) · `~/.secrets/upeu-infra.env` (dev) |
| Repo | `~/proyectos/productos/iga/canonico` — estructura `canonical/` + `upeu/` |
| Conectividad | VPN corporativa **o** túnel WireGuard OCI (`~/.secrets/wg-upeu-oci/wg-mac.sh up`). PROD `.166` es el ancla del túnel |

Si `.166` y el resto de `192.168.x` no responden, es la red, no el servidor.

### Fuente autoritativa: Oracle LAMB

`192.168.13.9:1521/UPEU` — credenciales en `~/.secrets/oracle-lamb.env`.
**Es Oracle 11.2: `python-oracledb` no la soporta en modo thin**, hay que
inicializar el Instant Client (`ORACLE_CLIENT_LIB_DIR` está en el `.env`).
Helper listo: `~/proyectos/productos/vocbench/instituciones/upeu/scripts/sprint4/lib_oracle.py`.

| Esquema | Qué gobierna |
|---|---|
| `MOISES` | MDM de personas — `PERSONA`, `PERSONA_NATURAL`, `TRABAJADOR` |
| `DAVID` | Académico y matrícula — `ACAD_MATRICULA`, `ACAD_PROGRAMA_ESTUDIO`, `TIPO_PROGRAMA` |
| `ELISEO` | RRHH, nómina, asistencia |
| `JOSUE` | Académico histórico |

> **NUNCA ejecutar INSERT / UPDATE / DELETE / DDL en Oracle LAMB.** Es solo lectura.

### Estándares que el modelo debe respetar

eduPerson 202208, SCHAC 1.6.0, SCIM 2.0, ISO/IEC 24760, NIST SP 800-63-3,
RBAC INCITS 359 e ISO/IEC 27001:2022. Ya hay en uso `eduPersonAffiliation`,
`eduPersonScopedAffiliation`, `eduPersonPrimaryOrgUnitDN`, `eduPersonOrgUnitDN`,
`eduPersonUniqueId`, `eduPersonPrincipalName`, más atributos SCHAC.

---

## Lo que cambió fuera de MidPoint y te afecta

Entre julio y agosto de 2026 se reconstruyó el **tesauro institucional de
programas académicos** en VocBench, y en el proceso apareció un problema que
toca directamente a la identidad.

### El hallazgo: `CODIGO_SUNEDU` de Oracle no es el código oficial

`DAVID.ACAD_PROGRAMA_ESTUDIO.CODIGO_SUNEDU` **no coincide** con el código que
UPeU declara ante SUNEDU en su Formato de Licenciamiento A4. Verificado en vivo:

| Programa en Oracle | `CODIGO_SUNEDU` | Código oficial A4 |
|---|---|---|
| Administración, Presencial | `2` y `101` (dos filas) | **P04** |
| Psicología, Presencial | `23` y `126` | **P33** |
| Enfermería, Presencial | `15` y `109` | **P22** |
| Ingeniería Ambiental | `16`, `60`, `110`, `122` | **P24 / P100 / P130** |

Es un correlativo interno que nunca se sincronizó con las altas y bajas
declaradas al regulador. En el tesauro llegó a producir 16 de 17 mapeos de
posgrado apuntando a un programa equivocado. **Si algún mapping, rol o informe
de MidPoint usa `CODIGO_SUNEDU` como si fuera el código oficial, está
propagando el error.** Contexto completo: ADR-004 del proyecto VocBench.

### Lo que MidPoint sí usa

Las vistas de integración serializan `LISTAGG(PE.CODIGO, '|')` como
`CODIGOS_PROGRAMA`, y el mapping lo deserializa con
`input?.split('\\|')?.toList()`. `PE.CODIGO` es un **código interno de plan**
(valores como `,10111,` o `,50105,30110,`), distinto tanto del código SUNEDU
como del INEI. No es un identificador que sirva fuera de LAMB.

Dimensión del desajuste: Oracle tiene **938 programas activos** (141 con algún
`CODIGO_SUNEDU`), porque desdobla por sección, filial y plan. La oferta oficial
son **121 P-codes + 62 SEG-codes**, que en el tesauro se agrupan en **108
conceptos** de programa.

---

## El tesauro, y qué te ofrece

| | |
|---|---|
| Plataforma | VocBench3 14.0 — https://vocbench.upeu.edu.pe/ |
| Proyecto | `Tesauro_Institucional_UPeU` |
| Secretos | `~/.secrets/vocbench-upeu.env` |
| baseURI | `http://upeu.edu.pe/sys/programas/` |
| Repo | `~/proyectos/productos/vocbench/instituciones/upeu` |

**Contenido, todo trazable a documento oficial:**

- **108 conceptos de programa** con los **121 P-codes** y **62 SEG-codes**
  oficiales como `skos:altLabel` — una búsqueda por código resuelve al concepto.
- **La modalidad, explícita:** `upeu:codigoSuneduPresencial`,
  `codigoSuneduSemipresencial`, `codigoSuneduDistancia`. Administración es P04
  presencial, P05 semipresencial y P95 a distancia: un solo programa, tres ofertas.
- Jerarquía derivada del Clasificador INEI 2022:
  `nivel → campo específico (2 díg.) → campo detallado (3 díg.) → programa`.
- **96 programas con código INEI de 8 dígitos** validado contra el catálogo
  oficial; los 12 restantes no existen en el Clasificador (corte 31-12-2022) y
  están clasificados en su campo, no inventados.
- **42 anclajes a ISCED-F** (`data.europa.eu/esco/isced-f/`) con la relación
  correcta —`exactMatch`, `broadMatch`, `narrowMatch`, `closeMatch`— derivada de
  la tabla oficial CNP 2022 ↔ CINE 2013.
- `upeu:nivelAcademico`, `upeu:gradoAcademico`, `upeu:denominacionTitulo` por concepto.

**Auditoría:** `python3 scripts/sprint4/10-auditar-tesauro.py` — hoy 0 hallazgos
estructurales. **Respaldo antes de tocar:** `bash scripts/sprint4/03-backup-vocbench.sh`.

---

## Los puntos de contacto que hay que resolver

Esto es lo que está abierto. No lo des por decidido: valídalo con el
`midpoint-expert` y contra las skills canónicas antes de implementar.

### 1. Un puente `PE.CODIGO` → URI del tesauro

Hoy no existe. MidPoint sabe qué programa cursa cada persona en vocabulario
LAMB, y el tesauro es el único sitio donde ese programa tiene identidad
institucional estable (URI), código oficial SUNEDU, código INEI y equivalencia
internacional.

Lo que hay que construir es una tabla de equivalencia explícita
`PE.CODIGO → URI del concepto`, **nunca una inferencia por nombre**: los
nombres de Oracle traen sección y sede pegadas («Administración - Sección
Juliaca - Sección Jul»), y el desdoble 938 → 108 no es trivial.

Cuestión de diseño a resolver: ¿dónde vive esa tabla? Candidatos son un recurso
de MidPoint, una vista en el CDC (`iga/instituciones/upeu/oracle-pg-cdc`), o
`upeu:codigoLamb` como propiedad en el propio tesauro. **No es obvia**; decídela
con el `midpoint-expert` y déjala en un ADR.

### 2. La modalidad ya está en ambos lados — verificar que concuerdan

MidPoint clasifica por `TIPO_PROGRAMA`: `EP` (Escuela Profesional), `SP`
(Semipresencial), `AD` (a Distancia), `MG` (Maestría)… y de ahí derivan los
roles `BR-Student-Pregrado`, `BR-Student-Posgrado-Master`, etc.

El tesauro distingue exactamente la misma dimensión, pero por P-code. **Son la
misma información expresada dos veces**, así que se pueden contrastar: `EP`
debería corresponder a `upeu:codigoSuneduPresencial`, `SP` a
`…Semipresencial`, `AD` a `…Distancia`. Si un estudiante figura en MidPoint como
`AD` y su programa no tiene código a distancia en el A4, hay una matrícula en
una modalidad no licenciada — **eso es un hallazgo de cumplimiento, no un bug de
datos**. Vale la pena construir esa comprobación.

### 3. Qué atributo eduPerson debe llevar el programa

Pregunta abierta. `eduPersonOrgUnitDN` y `eduPersonPrimaryOrgUnitDN` ya están en
uso; hay que decidir si el programa académico va ahí, si usa
`eduPersonEntitlement` con la URI del tesauro, o si merece un atributo de
extensión propio. **Consultar `iga-canonical-standards` antes de proponer**: la
semántica de eduPerson es estrecha y no admite interpretaciones libres.

Lo que sí es firme: si el programa se publica como atributo de identidad, el
valor debe ser **la URI del tesauro**, no un nombre ni un código de LAMB. Es lo
que hace que Indico, DSpace, OJS y los dashboards puedan cruzarse con la
identidad sin cadenas de texto.

### 4. Vigencia temporal

El tesauro refleja la oferta del periodo **2026-1** y guarda también **2025-2**.
Ya existe `docs/DECISION-vigencia-temporal-afiliaciones.md` en este repo: revisa
si su criterio de vigencia concuerda con que un programa pueda dejar de estar
licenciado mientras sus egresados conservan la afiliación.

---

## Fuentes documentales — dónde está cada cosa

Nada de lo anterior se afirma de memoria. Todo tiene documento detrás:

| Fuente | Ruta | Qué resuelve |
|---|---|---|
| Formatos de Licenciamiento **A4** y **A8** | `productos/vocbench/instituciones/upeu/fuentes/sunedu/` | Los P-codes y SEG-codes oficiales. Lo que UPeU declaró ante SUNEDU |
| **Clasificador Nacional 2022** (RJ 067-2024-INEI) | `sciback/biblioteca/inei/` — repo `SciBack/biblioteca` | Catálogo de programas, definiciones normativas de los 133 campos, correspondencia CINE 2013, código institucional (UPeU = `260000038`) |
| Derivados en CSV | `productos/vocbench/instituciones/upeu/data/` | Todo el pipeline trabaja sobre estos, no sobre los binarios |
| **ADR-004** | `…/vocbench/…/docs/decisiones/ADR-004-pcodes-formato-a4-fuente-canonica.md` | Por qué Oracle dejó de ser fuente de los códigos |
| **ADR-001** | `…/ADR-001-arquitectura-skos-anclada-isced-f.md` | El anclaje ISCED-F y por qué no todo es `exactMatch` |
| Informes vivos | `…/data/auditoria-tesauro.md`, `inei-validacion.md`, `inei-resolucion-discrepancias.md` | Estado y qué quedó pendiente, con su fundamento |

Índice general del workspace: `sciback/biblioteca-index/INDEX-MAESTRO.md`
(repo `SciBack/biblioteca-index`).

---

## Cómo trabajar

1. **Antes de diseñar**, el `midpoint-expert` consulta `midpoint-best-practices`
   e `iga-canonical-standards`. Sin excepción.
2. **Antes de afirmar** que un código, un programa o una afiliación es de cierta
   forma, verifícalo contra la fuente: el A4/A8 para códigos SUNEDU, el
   Clasificador para INEI, Oracle para matrícula real. No infieras por nombre.
3. **Antes de tocar el tesauro**, respaldo y auditoría; son dos comandos.
4. **Oracle es de solo lectura.** Siempre.
5. Si encuentras una incongruencia en un dato oficial —las hay: el Formato A8
   adscribe la Segunda Especialidad de Enfermería en Gestión en Inmunizaciones a
   *Psicología*— **documéntala y clasifica por contenido**, no la propagues en
   silencio ni la corrijas por tu cuenta en la fuente.
6. Cambios en PROD: pedir confirmación antes de reiniciar servicios o de
   cualquier operación no reversible.

---

## Addendum 2026-08-05 — el puente ya existe a medias, y otras dos correcciones

Tres cosas cambiaron después de escribir este prompt, medidas contra el tesauro vivo.

### 1. `ID_PROGRAMA_ESTUDIO` ya está en el tesauro

El §"Puntos de contacto" decía que el puente `PE.CODIGO → URI` no existe. **Existe a
medias, y con la clave correcta:** 62 conceptos llevan el `ID_PROGRAMA_ESTUDIO` de
Oracle como `skos:notation` con datatype `urn:esther:id_programa_estudio`.

Es exactamente la clave que propone el §5.2 del hallazgo del IGA —interna, inmutable—
y ya está en el sitio correcto. Lo que falta no es diseñarla: es **completarla** para
los conceptos que no la tienen y **generar desde ahí** la LookupTable, en vez de
mantenerla a mano. Se lee del export:

```
data/thesaurus-export.json → programs[].id_programa_estudio_lamb
```

### 2. Los pares duplicados están cerrados

Los 17 pares que hacían que MidPoint enganchara al gemelo sin P-code ya declaran
`dct:isReplacedBy` hacia su canónico. El generador del puente **debe seguir ese enlace**
en vez de tomar la URI tal cual; con esa regla, las URIs obsoletas que hoy publica LDAP
se resuelven solas. El export lo expone en `programs[].replaced_by`.

Sigue en pie el corolario del hallazgo: esto **no cambia LDAP por sí solo**. Mientras
`program-resolver-lamb` sea estática y resuelva por nombre, publicará lo mismo.

### 3. Dos trampas del almacén, que costaron un día

- **El tesauro vive repartido entre el named graph `<…/programas/>` y el default graph.**
  Enumerar grafos con `GRAPH ?g` deja fuera ~2.900 triples y 20 conceptos. Cualquier
  consulta de inventario debe ir **sin filtrar por grafo**; cualquier borrado, a los dos.
- **Las notaciones usan datatypes propios**, no `xsd:string`: `ns/IneiCode8`,
  `ns/KohaCode`, `urn:esther:id_programa_estudio`. Un `DELETE` sin el datatype exacto
  no borra nada y no da error.
