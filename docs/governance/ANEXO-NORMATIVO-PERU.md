# Anexo Normativo — Marco legal peruano para SGSI / ISO 27001 en TI universitaria

> Verificado contra fuentes primarias (El Peruano, gob.pe, SUNEDU, PCM/SGTD) — 2026-06-16.
> Acompaña al [`CHARTER-DTI-GOVERNANCE.md`](CHARTER-DTI-GOVERNANCE.md).
> Donde no se pudo confirmar el detalle con fuente primaria, se indica explícitamente.

---

## Resumen ejecutivo

**Para una universidad privada (UPeU)**, la obligación legal de implementar un SGSI **no**
proviene de la Ley de Gobierno Digital (esa rige a entidades del Estado), sino de la
combinación de:
- **(a)** Ley 29733 + DS 016-2024-JUS — protección de datos personales,
- **(b)** DS 126-2025-PCM — como proveedor de servicios educativos digitales,
- **(c)** Ley 30096 — marco de responsabilidad penal.

**ISO/IEC 27001** es el estándar que satisface técnicamente todas estas obligaciones de
forma articulada. Para **universidades estatales (OTI)** la obligación de SGSI con
**NTP-ISO/IEC 27001:2022** es **directa** (DL 1412 + DS 029-2021-PCM + Res. 003-2023-PCM/SGTD).

| Norma | Priv. | Estatal | Qué exige |
|---|:--:|:--:|---|
| DL 1412 + DS 029-2021-PCM | No directo | **Sí** | SGSI, Comité Gob. Digital, Oficial de Seguridad |
| RM 004-2016-PCM + Res. 003-2023-PCM/SGTD | No | **Sí** | NTP-ISO/IEC 27001:2022 obligatoria |
| Ley 29733 + DS 016-2024-JUS | **Sí** | **Sí** | Seguridad de datos, Oficial de Datos, brechas 48h |
| DU 007-2020 + DS 126-2025-PCM | **Sí** | **Sí** | Notificación incidentes CNSD, controles seguridad digital |
| Ley 30096 | **Sí** (penal) | **Sí** (penal) | Responsabilidad penal por custodia inadecuada |
| SUNEDU CBC (Ley 30220) | **Sí** (licenc.) | **Sí** (licenc.) | Sin mención explícita de SGSI/ISO 27001 |
| SINEACE | Voluntario | Voluntario | Sin requisito de SGSI explícito |

---

## 1. DL 1412 — Ley de Gobierno Digital (2018)

- **Cita:** Decreto Legislativo N.° 1412 — El Peruano, 13-sep-2018. **Vigente.**
- **Qué establece:** marco de gobernanza del gobierno digital (identidad, servicios,
  arquitectura, interoperabilidad, **seguridad digital**, datos). Obliga a entidades
  públicas a implementar un SGSI. Rector: PCM vía SGTD.
- **Alcance:** Administración Pública (incluye universidades **públicas**). Las privadas
  no están en el ámbito directo.
- **Fuente:** [El Peruano](https://busquedas.elperuano.pe/normaslegales/decreto-legislativo-que-aprueba-la-ley-de-gobierno-digital-decreto-legislativo-n-1412-1691026-1) · [gob.pe](https://www.gob.pe/institucion/pcm/normas-legales/289706-1412)

## 2. DS 029-2021-PCM — Reglamento de la Ley de Gobierno Digital

- **Cita:** DS N.° 029-2021-PCM — El Peruano, 19-feb-2021. **Vigente con modificaciones**
  (DS 075-2023-PCM; DS 098-2025-PCM).
- **Qué establece:** crea el **Comité de Gobierno Digital** y el **Oficial de Seguridad y
  Confianza Digital** en cada entidad. **Art. 105:** obliga a implementar y mantener un
  SGSI. **Art. 107:** notificar al CNSD en 48 h fallas que comprometan la identidad digital.
- **⚠ Precisión:** la numeración exacta del articulado del Comité y del Oficial no se pudo
  confirmar al 100% con fuente primaria; el **art. 105 (SGSI)** sí está confirmado (citado
  por Res. 003-2023-PCM/SGTD). Para cita de artículo exacto consultar el PDF oficial.
- **Fuente:** [El Peruano](https://busquedas.elperuano.pe/normaslegales/decreto-supremo-que-aprueba-el-reglamento-del-decreto-legisl-decreto-supremo-n-029-2021-pcm-1929103-3/) · [gob.pe](https://www.gob.pe/13326-reglamento-de-la-ley-de-gobierno-digital)

## 3. RM 004-2016-PCM — NTP-ISO/IEC 27001 obligatoria

- **Cita:** RM N.° 004-2016-PCM — El Peruano, 14-ene-2016.
- **Qué establece:** uso **obligatorio** de la NTP-ISO/IEC 27001:**2014** en todas las
  entidades del Sistema Nacional de Informática (DL 604/1991, regido por INEI) → universidades
  **públicas** incluidas; privadas no.
- **Estado:** vigente como norma habilitante pero **superada en la versión de la NTP** por la
  Res. 003-2023-PCM/SGTD (→ versión **2022**). No derogada formalmente, obsoleta en la práctica.
- **Fuente:** [El Peruano](https://busquedas.elperuano.pe/normaslegales/aprueban-el-uso-obligatorio-de-la-norma-tecnica-peruana-ntp-resolucion-ministerial-no-004-2016-pcm-1333015-1/) · [gob.pe](https://www.gob.pe/institucion/pcm/normas-legales/292578-004-2016-pcm)

## 4. Res. 003-2023-PCM/SGTD — SGSI del Estado con NTP-ISO/IEC 27001:2022

- **Cita:** Resolución N.° 003-2023-PCM/SGTD (SGTD) — 08-sep-2023. **Vigente.**
- **Qué establece:** obliga a entidades públicas a implementar y mantener un SGSI usando la
  **NTP-ISO/IEC 27001:2022** (estructura armonizada Annex SL, equivalente a ISO 27001:2022
  internacional). Objetivos: CIA de la información, cultura de seguridad, cumplimiento
  normativo, gestión de riesgos/incidentes.
- **Relación con RM 004-2016-PCM:** la actualiza de facto (referente técnico → 2022).
- **Fuente:** [El Peruano](https://busquedas.elperuano.pe/dispositivo/NL/2212869-1) · [gob.pe](https://www.gob.pe/institucion/pcm/normas-legales/4616713-003-2023-pcm-sgtd) · [PDF](https://cdn.www.gob.pe/uploads/document/file/5105775/RSGTD%20003-2023-PCM-SGTD.pdf)

## 5. Marco de Confianza Digital — DU 007-2020 + DS 126-2025-PCM

- **Cita base:** Decreto de Urgencia N.° 007-2020 — 09-ene-2020. Crea el Marco de Confianza
  Digital y el Registro Nacional de Incidentes de Seguridad Digital (RNISD).
- **Reglamento vigente:** **DS 126-2025-PCM** — publicado 04-nov-2025, **en vigor desde
  03-feb-2026** (90 días tras publicación). No deroga DS 157-2021-PCM (materias distintas).
- **Alcance a universidades:** incluye expresamente "**servicios educativos**" entre los
  proveedores de servicios digitales obligados. Toda universidad con matrícula online / campus
  virtual debe: implementar controles de seguridad digital, **notificar incidentes al CNSD en
  48 h**, gestionar riesgos digitales e incorporar privacidad desde el diseño. **Aplica a
  privadas y públicas.**
- **Fuente:** [DU 006/007-2020 El Peruano](https://busquedas.elperuano.pe/normaslegales/decreto-de-urgencia-que-crea-el-sistema-nacional-de-transfor-decreto-de-urgencia-n-006-2020-1844001-1/) · [DS 126-2025-PCM gob.pe](https://www.gob.pe/institucion/pcm/normas-legales/7370829-126-2025-pcm) · [análisis EY](https://www.ey.com/es_pe/technical/tax-alert/reglamento-ley-marco-confianza-digital-medidas-fortalecimiento)

## 6. Ley 29733 — Protección de Datos Personales + DS 016-2024-JUS

- **Ley:** Ley N.° 29733. **Vigente.**
- **Reglamento vigente:** **DS 016-2024-JUS** — publicado 30-nov-2024, **en vigor desde
  30-mar-2025** (obligación de Oficial de Datos Personales exigible desde 30-nov-2025).
  Reemplaza al DS 003-2013-JUS (derogado).
- **Cambios clave vs DS 003-2013-JUS:** datos en línea regulados explícitamente; alcance
  extraterritorial; **Oficial de Datos Personales obligatorio**; **notificación de brechas en
  48 h** a la ANPDP; portabilidad de datos; **privacidad por diseño obligatoria**.
- **Obligaciones de seguridad (arts. 47-50):** política de seguridad documentada, control de
  acceso, seguridad de equipos dentro/fuera de instalaciones, evaluación de impacto para
  tratamientos de alto riesgo. **Aplica a privadas y públicas.**
- **Fuente:** [LP Derecho](https://lpderecho.pe/reglamento-ley-proteccion-datos-personales-decreto-supremo-016-2024-jus/) · [IAPP](https://iapp.org/news/a/se-publica-el-nuevo-reglamento-de-protecci-n-de-datos-personales-en-per-/) · [PDF](https://img.lpderecho.pe/wp-content/uploads/2024/11/Decreto-Supremo-016-2024-JUS-LPDerecho.pdf)

## 7. Ley 30096 — Delitos Informáticos

- **Cita:** Ley N.° 30096 — 22-oct-2013. **Vigente con modificaciones** (Ley 32314/2025 — IA;
  Ley 32451/2025 — SIM; DL 1700/2026 — tráfico ilícito de datos).
- **Qué establece:** tipifica acceso ilícito, interceptación, daño a datos/sistemas, fraude
  informático, suplantación de identidad digital. Crea **responsabilidad penal por custodia
  inadecuada** de sistemas que permitan accesos ilícitos o robo de datos → justifica el SGSI.
- **Fuente:** [LP Derecho — Ley 30096 actualizada](https://lpderecho.pe/ley-delitos-informaticos-ley-30096/) · [Ley 32314 El Peruano](https://busquedas.elperuano.pe/dispositivo/NL/2394851-2)

## 8. SUNEDU — Ley 30220 y Condiciones Básicas de Calidad

- **Las 8 CBC** del licenciamiento institucional. **Ninguna obliga explícitamente a un SGSI
  ni cita ISO 27001.**
- **Únicas menciones a seguridad de información:**
  - **CBC VIII (Transparencia):** la gestión de información debe respetar "las regulaciones de
    protección de datos y seguridad de la información" (referencia **indirecta**, sin estándar).
  - **Modalidad a distancia/semipresencial:** exige "infraestructura tecnológica que garantice
    el funcionamiento seguro y estable de las plataformas virtuales" (solo programas virtuales).
- **Fuente:** [SUNEDU — Licenciamiento](https://www.sunedu.gob.pe/licenciamiento-institucional/) · [Ley 30220 PDF](https://www.sunedu.gob.pe/wp-content/uploads/2017/04/Ley-universitaria-30220.pdf)

## 9. SINEACE — Modelo de Acreditación

- Evalúa **calidad educativa global**, no gestión de TI como eje específico. Contempla manejo
  de información y sistemas para la toma de decisiones, pero **no exige SGSI ni ISO 27001**.
- **⚠ Precisión:** no se pudo confirmar con fuente primaria el texto exacto de todos los
  estándares del modelo vigente 2023-2024.
- **Fuente:** [Repositorio SINEACE — Modelo Institucional](https://repositorio.sineace.gob.pe/repositorio/handle/20.500.12982/4084)

---

## Conclusión para el Charter

ISO/IEC 27001:2022 (vía NTP-ISO/IEC 27001:2022) es el estándar que:
1. **Cumple** las obligaciones legales de UPeU (Ley 29733/DS 016-2024-JUS, DS 126-2025-PCM, Ley 30096).
2. **Es obligatorio** para universidades estatales (DL 1412 + Res. 003-2023-PCM/SGTD) → producto SciBack vendible.
3. **Es el referente** que SGTD recomienda incluso a entidades no obligadas formalmente.
4. **Satisface** la mención indirecta de seguridad de información de la CBC VIII de SUNEDU.

> Antes de uso formal externo, validar las citas marcadas con ⚠ contra el PDF oficial de cada
> norma, y confirmar la versión de la NTP-ISO/IEC 27001 referenciada al momento de la auditoría.
