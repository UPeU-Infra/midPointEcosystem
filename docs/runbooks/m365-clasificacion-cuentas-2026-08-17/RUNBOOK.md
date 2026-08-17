# Clasificación y depuración de cuentas M365 — cascada de procedencia (2026-08-17)

Reescritura del requerimiento de **David Urquizo** (`requerimiento-original-urquizo.docx`, 24 secciones)
para el estudio de las cuentas de Microsoft 365 de UPeU. **Solo lectura**: no se modificó nada en M365,
Entra ID, MidPoint ni Oracle LAMB.

## Qué cambia respecto al requerimiento original

El documento de Urquizo plantea deducir la naturaleza de cada cuenta **analizando semánticamente**
`displayName`, `userPrincipalName`, `givenName` y `surname`, con un «diccionario dinámico» de palabras
clave (`contab`→Contabilidad), niveles de confianza y una buena regla anti-falsos-positivos.

El método es correcto, pero su supuesto de partida no: **trata el tenant como única fuente de verdad**.
UPeU ya tiene esas respuestas escritas en los sistemas que gobiernan la identidad.

| Urquizo lo infiere del nombre | Ya existe como dato |
|---|---|
| `TipoCuenta: Personal / Administrativa` | **archetype** de MidPoint (`archetype-user-student`, `-alumni`, `-employee-staff`, `-employee-faculty`, `-service-account`) |
| `AreaCargo` por diccionario de palabras | **103 unidades reales** del árbol organizativo, con nombre oficial de Oracle (`AREA-91` = «EP Administración») |
| Sede detectando `lima`/`.jul`/`.tpp` | `campusStudent` / `campusWorker` como atributo |
| Categorías nuevas | `eduPersonAffiliation` del esquema canónico |

Deducir «Contabilidad» de la cadena `contab` cuando existe un `AREA-<código>` con su nombre oficial
crea **una tercera taxonomía** —ni la de Oracle ni la del IGA— que nadie mantiene.

**La heurística no se descarta: baja al último escalón y queda marcada como inferencia.**

## Cascada de procedencia (columna `Fuente` de los entregables)

| Nivel | Fuente | Cuentas | % |
|---|---|---|---|
| N0 | Forma de la cuenta (invitado externo, alias numérico sin identidad) | 792 | 1,1% |
| **N1** | **MidPoint — archetype, afiliación, campus y unidad heredados** | **23.424** | **31,1%** |
| **N2a** | **Oracle LAMB — `CORREO_INST` coincide** | **8.101** | **10,8%** |
| **N2b** | **Oracle LAMB — el alias numérico ES un documento real** | **4.901** | **6,5%** |
| | **Subtotal verificado** | **37.218** | **49,4%** |
| N3 | Alias estructuralmente coherente con el nombre | 14.078 | 18,7% |
| N3 | Nombre coincide en el MDM Oracle (410.996 personas) | 5.935 | 7,9% |
| N3 | Nombre coincide en MidPoint | 3.612 | 4,8% |
| N3 | Semántica de función institucional | 3.056 | 4,1% |
| N3 | Sin evidencia suficiente | 11.445 | 15,2% |

## Dos indicadores que NO son lo mismo

Error corregido durante la construcción: marcar «requiere revisión manual» todo lo que no fuera N1
inflaba la cifra a 53.856 y mezclaba dos problemas distintos.

- **`RequiereRevisionManual` = 30.098** → no sabemos *qué es* la cuenta. Trabajo de DTI.
- **`FueraDelGobiernoIGA` = 51.177** → sabemos qué es, pero MidPoint no la gobierna. Trabajo del
  equipo de identidad. Incluye las 13.002 cuentas de personas reales que Oracle conoce y el IGA no.

## Resultados

**Clasificación** (75.344 cuentas): Personal 60.051 · Observado 11.525 · Administrativa 2.976 ·
Invitado externo 743 · Otros 49. Confianza: Alta 34.490 · Media 28.068 · Baja 1.723 ·
Revisión manual 11.063. Con área asignada: 18.999.

**Actividad** (fecha de referencia 2026-08-17, no el 30-jun que fijaba el documento):
Activa 2026 30.510 (40,5%) · Inactiva >2 años 21.127 (28,0%) · **Nunca inició sesión 15.433 (20,5%)** ·
Inactiva 1-2 años 6.876 · Creadas recientemente 1.384 · Información insuficiente 14.
Riesgo: Bajo 31.894 · Medio 6.890 · Alto 26.978 · **Crítico 9.582**.

**El hallazgo de fondo no es de clasificación sino de gobierno:** 36.560 cuentas sin uso en más de dos
años o sin ningún acceso jamás, frente a **109 cuentas deshabilitadas** en todo el directorio. El alta
está automatizada (`API Lamb Academic` ejecuta el 74% de las creaciones); la baja no existe.

## Verificaciones hechas antes de decidir

- **VocBench** (`Tesauro_Institucional_UPeU`, SKOS-XL): 9 esquemas, **todos académicos** — programas,
  segunda especialidad, facultades, líneas de investigación, ISCED-F 2013, temas, posgrado, programas en
  implementación, tipos de actividad. **No hay vocabulario de unidades administrativas**, por eso el
  catálogo de áreas sale del árbol organizativo. Publicarlo como esquema SKOS es recomendación del informe.
- **Árbol organizativo**: 191 orgs hoy (no 353 — la diferencia son los 178 `LINEA-*` borrados el 6-ago),
  de las cuales **103 son `AREA-*` y las 103 tienen `displayName` oficial**.
- **Informes de Microsoft**: `Reports.Read.All` **no concedido** a `MidPoint-IGA-UPeU`
  (403 `S2SUnauthorized`). Sin ese permiso no hay serie histórica real de uso.

## Entregables

| Archivo | Contenido |
|---|---|
| `Analisis_Clasificacion_Cuentas_<fecha>.xlsx` | LEEME · Dashboard · Áreas administrativas · Catálogo de unidades · Clasificación (75.344 × 29 col) |
| `Analisis_Actividad_Cuentas_<fecha>.xlsx` | LEEME · Dashboard Actividad · Actividad (75.344 × 22 col) |
| `Informe_Analisis_Cuentas_Institucionales_<fecha>.html` | 11 secciones, autocontenido, imprimible |

Se entrega **HTML en lugar de Word** por indicación de Alberto.

## Cómo regenerar

```bash
# 1) tenant completo (~8 min, incluye lastPasswordChangeDateTime)
source ~/.secrets/upeu-infra.env
python3 entra_pull2.py "$MIDPOINT_AZ_TENANT_ID" "$MIDPOINT_AZ_CLIENT_ID" \
  "$MIDPOINT_AZ_CLIENT_SECRET" <scratch>/entra_users2.json

# 2) MidPoint: focos con archetype, orgs y campus  -> mp_full.csv
# 3) MidPoint: catálogo de unidades                -> mp_orgs.csv
# 4) Oracle (clase OraQ.java, ver runbook entra-duales-correo-2026-08-03):
#      CORREO_INST + documento  -> ora_correo.tsv
#      NUM_DOCUMENTO            -> ora_doc.tsv
#      MOISES.PERSONA (nombres) -> ora_nombres.tsv
python3 clasificar.py && python3 gen_entregables.py && python3 gen_informe.py
```

Las consultas SQL exactas están en el histórico de la sesión; las claves de cruce son
`m_user.emailaddress`, `m_user.nameorig` (= código institucional), `ext->>'72'` (DNI),
`ext->>'74'` (código), `ext->>'78'` (afiliación), `ext->>'219'/'220'` (campus).

## Pendiente / siguiente paso natural

El informe recomienda asignar **responsable a cada cuenta funcional**. Eso no es un Excel: es un
`ownerRef` en MidPoint. Convertir las 2.976 cuentas administrativas detectadas en objetos gobernados
—con archetype de cuenta funcional y dueño— es el delta accionable que cierra este estudio.
