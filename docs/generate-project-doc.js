const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
  TableOfContents
} = require('docx');
const fs = require('fs');

// ── Colors ──────────────────────────────────────────────────────────────────
const C = {
  upeuBlue: "1A3A5C",
  accent: "2563EB",
  lightBlue: "DBEAFE",
  mediumBlue: "93C5FD",
  headerBg: "1E3A5F",
  rowAlt: "F0F7FF",
  rowAlt2: "E8F4FD",
  green: "16A34A",
  greenBg: "DCFCE7",
  yellow: "CA8A04",
  yellowBg: "FEF9C3",
  red: "DC2626",
  redBg: "FEE2E2",
  gray: "6B7280",
  white: "FFFFFF",
  black: "111827",
  borderGray: "D1D5DB",
};

// ── Helpers ──────────────────────────────────────────────────────────────────
const sp = (bef, aft) => ({ spacing: { before: bef || 0, after: aft || 0 } });
const cellBorder = (color) => {
  const b = { style: BorderStyle.SINGLE, size: 4, color: color || C.borderGray };
  return { top: b, bottom: b, left: b, right: b };
};
const noBorder = () => {
  const b = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  return { top: b, bottom: b, left: b, right: b };
};
const shading = (fill) => ({ fill, type: ShadingType.CLEAR });
const cell = (text, opts = {}) => new TableCell({
  borders: cellBorder(opts.borderColor || C.borderGray),
  width: opts.width ? { size: opts.width, type: WidthType.DXA } : undefined,
  shading: opts.bg ? shading(opts.bg) : undefined,
  verticalAlign: opts.valign || VerticalAlign.CENTER,
  margins: { top: 80, bottom: 80, left: 120, right: 120 },
  columnSpan: opts.span,
  children: [new Paragraph({
    alignment: opts.align || AlignmentType.LEFT,
    children: [new TextRun({
      text: text,
      bold: opts.bold || false,
      color: opts.color || C.black,
      size: opts.size || 20,
      font: "Arial",
    })]
  })]
});

const hCell = (text, w) => cell(text, { bg: C.headerBg, bold: true, color: C.white, width: w, size: 20 });
const hdr = (level, text, opts = {}) => new Paragraph({
  heading: level,
  pageBreakBefore: opts.pageBreak || false,
  children: [new TextRun({ text, bold: true, font: "Arial", size: opts.size || (level === HeadingLevel.HEADING_1 ? 36 : level === HeadingLevel.HEADING_2 ? 28 : 24), color: opts.color || (level === HeadingLevel.HEADING_1 ? C.upeuBlue : C.black) })]
});
const para = (text, opts = {}) => new Paragraph({
  alignment: opts.align || AlignmentType.LEFT,
  ...sp(opts.before || 80, opts.after || 80),
  children: [new TextRun({ text, font: "Arial", size: opts.size || 20, bold: opts.bold || false, color: opts.color || C.black, italics: opts.italic || false })]
});
const bullet = (text, ref = "bullets") => new Paragraph({
  numbering: { reference: ref, level: 0 },
  ...sp(40, 40),
  children: [new TextRun({ text, font: "Arial", size: 20, color: C.black })]
});
const divider = () => new Paragraph({
  border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.mediumBlue, space: 1 } },
  children: [new TextRun("")]
});
const spacer = () => new Paragraph({ children: [new TextRun("")] });

// ── Ficha table ───────────────────────────────────────────────────────────────
function fichaRow(label, value, altBg) {
  return new TableRow({ children: [
    cell(label, { bg: C.lightBlue, bold: true, width: 3200, size: 20 }),
    cell(value, { bg: altBg ? C.rowAlt : C.white, width: 6160, size: 20 }),
  ]});
}

// ── Risk row ─────────────────────────────────────────────────────────────────
function riskRow(id, desc, prob, imp, level, mit, bgColor) {
  const cols = [700, 2800, 600, 600, 700, 2960];
  const vals = [id, desc, prob, imp, level, mit];
  return new TableRow({ children: vals.map((v, i) => cell(v, { bg: bgColor, width: cols[i], size: 18 })) });
}

// ── Cronograma row ────────────────────────────────────────────────────────────
function cronRow(fase, desc, q1, q2, q3, q4, estado, alt) {
  return new TableRow({ children: [
    cell(fase, { bg: alt ? C.rowAlt : C.white, width: 1200, size: 18, bold: true }),
    cell(desc, { bg: alt ? C.rowAlt : C.white, width: 2600, size: 18 }),
    cell(q1, { bg: alt ? C.rowAlt : C.white, width: 700, size: 18, align: AlignmentType.CENTER }),
    cell(q2, { bg: alt ? C.rowAlt : C.white, width: 700, size: 18, align: AlignmentType.CENTER }),
    cell(q3, { bg: alt ? C.rowAlt : C.white, width: 700, size: 18, align: AlignmentType.CENTER }),
    cell(q4, { bg: alt ? C.rowAlt : C.white, width: 700, size: 18, align: AlignmentType.CENTER }),
    cell(estado, { bg: alt ? C.rowAlt : C.white, width: 1760, size: 18, bold: true, color: estado.includes("COMPLETA") || estado.includes("VALIDADO") ? C.green : estado.includes("PARCIAL") || estado.includes("ACTIVO") ? C.yellow : estado.includes("BLOQUEADO") ? C.red : C.gray }),
  ]});
}

// ═══════════════════════════════════════════════════════════════════════════
// DOCUMENT
// ═══════════════════════════════════════════════════════════════════════════
const doc = new Document({
  creator: "Alberto Sanchez - DTI UPeU",
  title: "DTI-IGA-2026-001 — Sistema de Gobierno de Identidad y Acceso UPeU",
  description: "Documento de proyecto para aprobación interna DTI - Universidad Peruana Unión 2026",

  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "nums", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },

  styles: {
    default: {
      document: { run: { font: "Arial", size: 20, color: C.black } }
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: C.upeuBlue },
        paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 0, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.mediumBlue, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: C.upeuBlue },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: C.black },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 } },
    ]
  },

  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 }, // A4
        margin: { top: 1440, right: 1080, bottom: 1440, left: 1440 }
      }
    },

    headers: {
      default: new Header({
        children: [new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.mediumBlue, space: 2 } },
          children: [
            new TextRun({ text: "DTI-IGA-2026-001 | Gobierno de Identidad y Acceso — UPeU", font: "Arial", size: 16, color: C.gray }),
            new TextRun({ text: "\t2026", font: "Arial", size: 16, color: C.gray }),
          ],
          tabStops: [{ type: "right", position: 9026 }],
        })]
      })
    },

    footers: {
      default: new Footer({
        children: [new Paragraph({
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: C.mediumBlue, space: 2 } },
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "Universidad Peruana Unión — Dirección de Tecnologías de Información | Página ", font: "Arial", size: 16, color: C.gray }),
            new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: C.gray }),
            new TextRun({ text: " de ", font: "Arial", size: 16, color: C.gray }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], font: "Arial", size: 16, color: C.gray }),
          ]
        })]
      })
    },

    children: [

      // ════════════════════════════════
      // PORTADA
      // ════════════════════════════════
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "UNIVERSIDAD PERUANA UNIÓN", font: "Arial", size: 20, bold: true, color: C.gray })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 400 },
        children: [new TextRun({ text: "Dirección de Tecnologías de Información", font: "Arial", size: 20, color: C.gray })]
      }),

      // Bloque titulo con fondo
      new Table({
        width: { size: 9386, type: WidthType.DXA },
        columnWidths: [9386],
        rows: [
          new TableRow({ children: [new TableCell({
            borders: noBorder(),
            shading: shading(C.headerBg),
            margins: { top: 400, bottom: 400, left: 400, right: 400 },
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { before: 0, after: 80 },
                children: [new TextRun({ text: "DOCUMENTO DE PROYECTO", font: "Arial", size: 24, bold: true, color: "93C5FD" })]
              }),
              new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { before: 80, after: 160 },
                children: [new TextRun({ text: "Sistema de Gobierno de Identidad y Acceso", font: "Arial", size: 48, bold: true, color: C.white })]
              }),
              new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { before: 0, after: 200 },
                children: [new TextRun({ text: "Universidad Peruana Unión — Tres Campus", font: "Arial", size: 28, color: "BFDBFE" })]
              }),
              new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { before: 0, after: 0 },
                children: [new TextRun({ text: "Código: DTI-IGA-2026-001", font: "Arial", size: 24, bold: true, color: "93C5FD" })]
              }),
            ]
          })]})
        ]
      }),

      spacer(),

      // Stats rápidos
      new Table({
        width: { size: 9386, type: WidthType.DXA },
        columnWidths: [2346, 2346, 2346, 2348],
        rows: [new TableRow({ children: [
          new TableCell({
            borders: cellBorder(C.mediumBlue),
            shading: shading(C.lightBlue),
            margins: { top: 120, bottom: 120, left: 120, right: 120 },
            children: [
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "35.970", font: "Arial", size: 36, bold: true, color: C.upeuBlue })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Identidades gestionadas", font: "Arial", size: 18, color: C.gray })] }),
            ]
          }),
          new TableCell({
            borders: cellBorder(C.mediumBlue),
            shading: shading(C.lightBlue),
            margins: { top: 120, bottom: 120, left: 120, right: 120 },
            children: [
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "3 Campus", font: "Arial", size: 36, bold: true, color: C.upeuBlue })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Lima | Juliaca | Tarapoto", font: "Arial", size: 18, color: C.gray })] }),
            ]
          }),
          new TableCell({
            borders: cellBorder(C.mediumBlue),
            shading: shading(C.lightBlue),
            margins: { top: 120, bottom: 120, left: 120, right: 120 },
            children: [
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "7 Sistemas", font: "Arial", size: 36, bold: true, color: C.upeuBlue })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Integrados vía IGA", font: "Arial", size: 18, color: C.gray })] }),
            ]
          }),
          new TableCell({
            borders: cellBorder(C.mediumBlue),
            shading: shading(C.lightBlue),
            margins: { top: 120, bottom: 120, left: 120, right: 120 },
            children: [
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "S/ 0", font: "Arial", size: 36, bold: true, color: C.green })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Costo adicional en software", font: "Arial", size: 18, color: C.gray })] }),
            ]
          }),
        ]})]
      }),

      spacer(),

      // Firmas portada
      new Table({
        width: { size: 9386, type: WidthType.DXA },
        columnWidths: [4693, 4693],
        rows: [
          new TableRow({ children: [
            hCell("Aprobado por", 4693),
            hCell("Elaborado por", 4693),
          ]}),
          new TableRow({ children: [
            new TableCell({ borders: cellBorder(C.borderGray), width: { size: 4693, type: WidthType.DXA }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [
              new Paragraph({ spacing: { before: 0, after: 20 }, children: [new TextRun({ text: "David Barrantes", font: "Arial", size: 22, bold: true })] }),
              new Paragraph({ spacing: { before: 0, after: 0 }, children: [new TextRun({ text: "Director de Tecnologías de Información", font: "Arial", size: 18, color: C.gray })] }),
            ]}),
            new TableCell({ borders: cellBorder(C.borderGray), width: { size: 4693, type: WidthType.DXA }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [
              new Paragraph({ spacing: { before: 0, after: 20 }, children: [new TextRun({ text: "Alberto Sanchez", font: "Arial", size: 22, bold: true })] }),
              new Paragraph({ spacing: { before: 0, after: 0 }, children: [new TextRun({ text: "Gestor del Proyecto IGA", font: "Arial", size: 18, color: C.gray })] }),
            ]}),
          ]}),
          new TableRow({ children: [
            cell("Versión: 1.1 | Fecha: 21 de mayo de 2026", { width: 4693, bg: C.rowAlt, size: 18 }),
            cell("Clasificación: Uso interno DTI", { width: 4693, bg: C.rowAlt, size: 18 }),
          ]}),
        ]
      }),

      // PAGE BREAK
      new Paragraph({ children: [new PageBreak()] }),

      // ════════════════════════════════
      // TABLA DE CONTENIDO
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "Tabla de Contenido"),
      new TableOfContents("", { hyperlink: true, headingStyleRange: "1-3" }),
      new Paragraph({ children: [new PageBreak()] }),

      // ════════════════════════════════
      // FICHA DEL PROYECTO
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "Ficha del Proyecto"),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3200, 6160],
        rows: [
          new TableRow({ children: [new TableCell({ columnSpan: 2, borders: cellBorder(C.borderGray), shading: shading(C.headerBg), margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "INFORMACIÓN GENERAL DEL PROYECTO", font: "Arial", size: 22, bold: true, color: C.white })] })] })] }),
          fichaRow("Código del proyecto", "DTI-IGA-2026-001", false),
          fichaRow("Nombre del proyecto", "Sistema de Gobierno de Identidad y Acceso — UPeU", true),
          fichaRow("Tipo de proyecto", "Infraestructura TI / Plataforma institucional transversal", false),
          fichaRow("Unidad ejecutora", "Dirección de Tecnologías de Información (DTI)", true),
          fichaRow("Alcance geográfico", "Campus Lima | Campus Juliaca | Campus Tarapoto", false),
          fichaRow("Director del proyecto", "David Barrantes — Director DTI", true),
          fichaRow("CTO Lima", "David Urquizo — Arquitecto de Soluciones", false),
          fichaRow("Infraestructura", "Rudy Milan — Administrador de Infraestructura", true),
          fichaRow("Gestor del proyecto", "Alberto Sanchez — Especialista IGA", false),
          fichaRow("Fecha de inicio", "Enero 2026 (Fase 0 iniciada)", true),
          fichaRow("Fecha estimada de finalización", "Diciembre 2026 (Fases 1-10 completas; Fases 12-13 sujetas a desbloqueo)", false),
          fichaRow("Presupuesto adicional", "S/ 0 (100% open source + recursos DTI existentes)", true),
          fichaRow("Costo por horas DTI", "~210 horas (estimado total Fases 1-10, 12 y 13)", false),
          fichaRow("Estado actual", "En ejecución — Fases 1-6 completadas, Fase 7 parcial", true),
          fichaRow("Versión del documento", "1.1 — 21 de mayo de 2026 (cifras verificadas contra Oracle LAMB y MidPoint PROD)", false),
          fichaRow("Clasificación", "Uso interno DTI — No publicar externamente", true),
        ]
      }),

      spacer(),

      // ════════════════════════════════
      // RESUMEN EJECUTIVO
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "Resumen Ejecutivo", { pageBreak: true }),

      para("La Universidad Peruana Unión (UPeU) gestiona actualmente 35.970 identidades digitales distribuidas en tres campus (Lima, Juliaca y Tarapoto), con 7 sistemas institucionales críticos que operaban sin un modelo centralizado de identidad, acceso ni ciclo de vida de cuentas.", { after: 120 }),

      para("El presente proyecto, de código DTI-IGA-2026-001, establece una plataforma de Identity Governance & Administration (IGA) basada en MidPoint 4.10.2 — plataforma open source certificada y con respaldo de Evolveum. A través de esta plataforma, DTI ha unificado las fuentes de datos de identidad (Oracle LAMB ERP, Microsoft Entra ID, OpenLDAP, Koha), automatizado el ciclo de vida joiner-mover-leaver y provisionado cuentas en los sistemas integrados de forma trazable y auditada.", { after: 120 }),

      para("A la fecha (mayo 2026), el sistema opera en produccion de forma estable: 34.551 identidades sincronizadas en el directorio OpenLDAP HA, 37.305 en Entra ID (solo lectura), 5.274 cuentas gestionadas en Koha, y un pipeline de reconciliación automático con reconocimiento de estados. La poblacion de egresados y trabajadores está integrada de forma completa; la carga del padrón estudiantil del ciclo regular vigente (aproximadamente 23.620 estudiantes) constituye la principal tarea pendiente de la siguiente fase. El costo total de software adicional es cero (S/ 0), dado que toda la pila tecnológica es open source o ya está licenciada institucionalmente.", { after: 120 }),

      para("El proyecto cumple con la Ley Universitaria 30220, la Ley de Protección de Datos 29733, los lineamientos SUNEDU y SINEACE para acreditación, y los estándares internacionales ISO/IEC 27001:2022 e ISO/IEC 24760. Su culminación habilitará a DTI para gestionar el ciclo de vida de identidades de forma automática, reducir la superficie de ataque por cuentas huérfanas y demostrar controles de acceso ante auditores externos.", { after: 120 }),

      para("Se solicita la aprobación formal del Director DTI para continuar con las fases pendientes (RBAC completo, validación end-to-end, gobierno Entra ID y métricas COUNTER) y formalizar los recursos asignados.", { after: 80 }),

      // ════════════════════════════════
      // SECCIÓN 1: ANTECEDENTES
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "1. Antecedentes y Situación Actual", { pageBreak: true }),

      hdr(HeadingLevel.HEADING_2, "1.1 Contexto institucional"),
      para("La UPeU es una institucion de educacion superior adventista con presencia en tres campus: Lima (sede central), Juliaca (región andina) y Tarapoto (región amazonica). Su comunidad académica, verificada contra la base de datos institucional Oracle LAMB en mayo de 2026, comprende alrededor de 24.000 estudiantes con matrícula vigente en el año académico 2026 (23.620 en el ciclo regular vigente), 30.635 egresados y aproximadamente 3.800 trabajadores activos, de los cuales cerca de 1.190 son docentes universitarios y el resto personal administrativo y operativo."),
      para("La base de datos institucional de verdad es Oracle LAMB — un ERP propio desarrollado sobre Oracle 11g con cuatro esquemas principales: MOISES (recursos humanos), DAVID (académico), ELISEO (estructura organizacional) y JOSUE (finanzas). LAMB es la fuente autoritativa de toda identidad activa en UPeU."),
      para("Los sistemas institucionales que dependen de cuentas de usuario incluyen: Microsoft 365 (correo, Teams, OneDrive), Koha (sistema de biblioteca), Keycloak (SSO institucional), OpenLDAP (directorio de identidades), EJBCA (PKI corporativa), FreeRADIUS (Wi-Fi 802.1X) y repositorios académicos (DSpace, OJS)."),

      hdr(HeadingLevel.HEADING_2, "1.2 Problema identificado"),
      para("Antes del inicio de este proyecto, la situación era la siguiente:"),
      bullet("No existía un modelo centralizado de identidad institucional. Cada sistema administraba sus propias cuentas de forma aislada."),
      bullet("La creación de cuentas fue manual hasta cierto momento y posteriormente se automatizó; sin embargo, el mantenimiento del ciclo de vida (modificaciones y bajas) sigue dependiendo de solicitudes por correo o por sistema de tickets sin SLA definido."),
      bullet("Cuando un trabajador terminaba su contrato o un estudiante concluía su ciclo, sus cuentas no se desactivaban automáticamente en los sistemas destino, generando cuentas huérfanas que representan un riesgo de seguridad (ISO 27001 A.5.15, A.8.2)."),
      bullet("No había trazabilidad de quienes tenían acceso a que sistemas, ni evidencia auditable de los cambios."),
      bullet("El proceso de alta de un docente nuevo podía tardar días o semanas en propagarse a todos los sistemas que necesitaba."),
      bullet("Las licencias M365 se asignaban manualmente sin reglas automáticas basadas en el tipo de vínculo institucional."),
      spacer(),

      hdr(HeadingLevel.HEADING_2, "1.3 Riesgos operativos y regulatorios pre-proyecto"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [400, 5000, 3960],
        rows: [
          new TableRow({ children: [hCell("#", 400), hCell("Riesgo identificado", 5000), hCell("Marco regulatorio asociado", 3960)] }),
          ...[
            ["1", "Cuentas de ex-empleados activas en M365 y Koha tras fin de contrato", "ISO 27001 A.5.15 / Ley 29733 Art. 9"],
            ["2", "Sin evidencia auditable de asignación de permisos para SUNEDU/SINEACE", "SUNEDU CBC / SINEACE Standard 5.4"],
            ["3", "Datos de identidad duplicados o inconsistentes entre Oracle LAMB y Entra ID", "ISO 24760 §4 / NIST 800-63-3"],
            ["4", "Sin control de separación de funciones (SoD) documentado", "ISO 27001 A.8.2 / INCITS 359 RBAC"],
            ["5", "Acceso por defecto sin principio de mínimo privilegio", "DS 029-2021-PCM / ISO 27001 A.8.3"],
          ].map(([n, r, m], i) => new TableRow({ children: [
            cell(n, { bg: i % 2 ? C.rowAlt : C.white, width: 400, size: 18, align: AlignmentType.CENTER }),
            cell(r, { bg: i % 2 ? C.rowAlt : C.white, width: 5000, size: 18 }),
            cell(m, { bg: i % 2 ? C.rowAlt : C.white, width: 3960, size: 18 }),
          ]}))
        ]
      }),

      // ════════════════════════════════
      // SECCIÓN 2: MARCO NORMATIVO
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "2. Marco Normativo y Regulatorio", { pageBreak: true }),

      hdr(HeadingLevel.HEADING_2, "2.1 Marco legal peruano"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2800, 4000, 2560],
        rows: [
          new TableRow({ children: [hCell("Norma", 2800), hCell("Exigencia relevante", 4000), hCell("Cumplimiento IGA", 2560)] }),
          ...[
            ["Ley 30220 — Ley Universitaria", "Transparencia en gestión y rendición de cuentas. Registro de docentes y administrativos con evidencia.", "Trazabilidad completa de asignación de cuentas y roles por tipo de vínculo."],
            ["Ley 29733 — Datos Personales", "Tratamiento licito, seguro y con acceso mínimo de datos personales (Art. 9, 13).", "Principio de mínimo privilegio vía RBAC. Registro de acceso a datos."],
            ["DS 029-2021-PCM — PNGIE", "Política Nacional de Gobierno e Integridad. Seguridad de la información en entidades educativas.", "Controles A.5.15-A.5.18 ISO 27001 implementados."],
            ["DL 1350 / Regl. RENIEC", "Verificacion de identidad para acceso a sistemas públicos (DNI biométrico).", "DNI como correlador canónico (schacPersonalUniqueID). IAL2 en acceso a sistemas críticos."],
            ["SUNEDU — Condiciones Básicas de Calidad (CBC)", "Dimensión 5: docentes con perfil acreditado. Control de acceso a sistemas académicos.", "Arquetipos employee-faculty y student con atributos LAMB verificados."],
            ["SINEACE — Estándares de Acreditación", "Proceso 5.4: gestión de recursos humanos con evidencia de competencias y acceso.", "Object templates + lifecycle automático documentado en repositorio GitOps."],
          ].map(([n, e, c], i) => new TableRow({ children: [
            cell(n, { bg: i % 2 ? C.rowAlt : C.white, width: 2800, size: 18, bold: true }),
            cell(e, { bg: i % 2 ? C.rowAlt : C.white, width: 4000, size: 18 }),
            cell(c, { bg: i % 2 ? C.rowAlt : C.white, width: 2560, size: 18 }),
          ]}))
        ]
      }),

      spacer(),
      hdr(HeadingLevel.HEADING_2, "2.2 Estándares internacionales adoptados"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 1200, 5760],
        rows: [
          new TableRow({ children: [hCell("Estándar", 2400), hCell("Versión", 1200), hCell("Aplicación en este proyecto", 5760)] }),
          ...[
            ["ISO/IEC 24760-1/2/3", "2025", "Terminologia IGA (identity, attribute, IIA, lifecycle). Marco conceptual del modelo canónico."],
            ["ISO/IEC 27001:2022", "2022", "Controles A.5.15 (acceso), A.5.16 (identidad), A.5.17 (credenciales), A.5.18 (derechos), A.8.2 (privilegios), A.8.3 (mínimo acceso)."],
            ["NIST SP 800-63-3", "Rev.3", "Niveles IAL/AAL: IAL2 para docentes/estudiantes (DNI verificado), IAL3 para firma digital diplomas."],
            ["eduPerson 202208 v4.4.0", "2022", "Atributos federados: ePPN, ePSA, eduPersonUniqueId, eduPersonAffiliation, eduPersonOrcid."],
            ["SCHAC 1.6.0", "2021", "Atributos académicos: schacHomeOrganization, schacPersonalUniqueID (DNI en URN), schacExpiryDate."],
            ["SCIM 2.0 (RFC 7643/7644)", "2015", "Modelo user/group core + Enterprise extension. Base del schema canónico."],
            ["NIST RBAC — INCITS 359", "R2022", "Cascada Business Role -> Application Role -> Entitlement. SoD policies."],
            ["REFEDS Research & Scholarship", "1.3", "Bundle de atributos eduPerson para federación con Scopus, EBSCO, Web of Science, IEEE."],
          ].map(([n, v, a], i) => new TableRow({ children: [
            cell(n, { bg: i % 2 ? C.rowAlt : C.white, width: 2400, size: 18, bold: true }),
            cell(v, { bg: i % 2 ? C.rowAlt : C.white, width: 1200, size: 18, align: AlignmentType.CENTER }),
            cell(a, { bg: i % 2 ? C.rowAlt : C.white, width: 5760, size: 18 }),
          ]}))
        ]
      }),

      hdr(HeadingLevel.HEADING_2, "2.3 Consecuencias del incumplimiento"),
      para("El incumplimiento de los marcos anteriores puede derivar en: (a) observaciones críticas en procesos de licenciamiento o acreditación SUNEDU/SINEACE por ausencia de controles de acceso documentados; (b) sanciones bajo la Ley 29733 ante incidentes de filtración de datos personales sin evidencia de tratamiento licito; y (c) riesgos de seguridad materializados por cuentas huérfanas o sin control de separación de funciones. El proyecto IGA elimina de forma sistemática estos riesgos."),

      // ════════════════════════════════
      // SECCIÓN 3: JUSTIFICACIÓN
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "3. Justificación del Proyecto", { pageBreak: true }),

      hdr(HeadingLevel.HEADING_2, "3.1 Necesidad institucional"),
      para("La UPeU ha crecido sostenidamente en los últimos años, incorporando nuevos programas de pregrado y posgrado y herramientas digitales (M365, ecosistema LAMB, Koha, EJBCA, Wi-Fi 802.1X). Este crecimiento ha presionado al equipo DTI a gestionar identidades manualmente en cada sistema, sin visibilidad transversal ni automatización del ciclo de vida. La plataforma IGA resuelve estructuralmente este problema sin costo adicional de licencias."),

      hdr(HeadingLevel.HEADING_2, "3.2 Análisis de alternativas"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 2000, 2000, 2960],
        rows: [
          new TableRow({ children: [hCell("Alternativa", 2400), hCell("Costo anual estimado", 2000), hCell("Tiempo de implementación", 2000), hCell("Observacion", 2960)] }),
          ...[
            ["SailPoint Identity Now (SaaS)", "USD 80.000 – 300.000/año", "6-12 meses", "Costo prohibitivo para universidad peruana. Dependencia de vendor."],
            ["Saviynt Enterprise IGA (SaaS)", "USD 50.000 – 150.000/año", "4-8 meses", "Similar a SailPoint. Sin referencia local."],
            ["Oracle Identity Manager", "USD 100.000+ con soporte", "12-18 meses", "Licenciamiento complejo. Requiere infraestructura adicional."],
            ["Desarrollo a medida", "USD 30.000 – 60.000 por desarrollo + mantenimiento", "12-24 meses", "Riesgo de calidad. Sin estándar. Deuda técnica alta."],
            ["MidPoint 4.10.2 (ELEGIDO)", "S/ 0 software (open source GPLv3)", "6-10 meses", "Estándar internacional. Soporte Evolveum. Stack open source alineado con política UPeU."],
          ].map(([a, c, t, o], i) => new TableRow({ children: [
            cell(a, { bg: i === 4 ? C.greenBg : i % 2 ? C.rowAlt : C.white, width: 2400, size: 18, bold: i === 4 }),
            cell(c, { bg: i === 4 ? C.greenBg : i % 2 ? C.rowAlt : C.white, width: 2000, size: 18 }),
            cell(t, { bg: i === 4 ? C.greenBg : i % 2 ? C.rowAlt : C.white, width: 2000, size: 18 }),
            cell(o, { bg: i === 4 ? C.greenBg : i % 2 ? C.rowAlt : C.white, width: 2960, size: 18 }),
          ]}))
        ]
      }),

      spacer(),
      hdr(HeadingLevel.HEADING_2, "3.3 Valor estratégico"),
      bullet("Habilitador de acreditación: los controles IGA son evidencia directa para indicadores SUNEDU CBC (Dimensión 5) y SINEACE (Estándar 5.4)."),
      bullet("Arquitectura mantenible: el diseño en capas separa el modelo canónico basado en estándares internacionales de las particularidades institucionales de UPeU, lo que facilita el mantenimiento, las auditorías y la evolución futura del sistema."),
      bullet("Seguridad por diseño: elimina cuentas huérfanas sistemáticamente, reduce superficie de ataque y permite demostración de controles ante auditores ISO 27001."),
      bullet("Autonomía tecnológica: sin dependencia de proveedor externo. DTI controla completamente el ciclo de vida de identidades."),

      // ════════════════════════════════
      // SECCIÓN 4: OBJETIVOS
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "4. Objetivos del Proyecto", { pageBreak: true }),

      hdr(HeadingLevel.HEADING_2, "4.1 Objetivo general"),
      para("Establecer y operar una plataforma de Identity Governance & Administration (IGA) sobre MidPoint 4.10.2 que centralice la gestión del ciclo de vida de identidades de la UPeU — desde el ingreso hasta el egreso o cese — automatizando el aprovisionamiento de cuentas y permisos en los sistemas institucionales de los tres campus, con trazabilidad completa y conformidad con ISO 27001:2022 e ISO 24760.", { after: 160 }),

      hdr(HeadingLevel.HEADING_2, "4.2 Objetivos específicos"),
      ...[
        "OE1. Centralizar y normalizar las identidades institucionales (35.970 gestionadas a la fecha, sobre una poblacion objetivo cercana a 58.000 personas entre estudiantes, egresados y trabajadores) desde Oracle LAMB como fuente autoritativa, usando el modelo canónico eduPerson/SCHAC/SCIM.",
        "OE2. Automatizar el ciclo de vida joiner-mover-leaver: creación, modificacion y desactivacion de cuentas en todos los sistemas integrados sin intervención manual del personal DTI.",
        "OE3. Implementar un modelo RBAC en tres capas (Business Role -> Application Role -> Entitlement) que garantice el principio de mínimo privilegio y separe funciones incompatibles (SoD), conforme a ISO 27001 A.8.2-A.8.3.",
        "OE4. Proveer un directorio OpenLDAP HA (N-Way Multimaster en dos nodos) como fuente federada de identidades para Keycloak, habilitando SSO con atributos eduPerson hacia bases de datos académicas (Scopus, EBSCO, Web of Science, IEEE).",
        "OE5. Sincronizar identidades con Microsoft Entra ID para gobernar licencias M365 (A1/A3/A5) según archetype institucional, eliminando asignaciones manuales y licencias huérfanas.",
        "OE6. Producir evidencia auditable del ciclo de vida de identidades y control de acceso, utilizable en procesos de licenciamiento SUNEDU, acreditación SINEACE y auditorías ISO 27001.",
        "OE7. Establecer métricas COUNTER 5 de uso de bases de datos académicas con granularidad por facultad y programa académico, habilitando decisión informada en renovación de suscripciones.",
      ].map(t => bullet(t)),

      // ════════════════════════════════
      // SECCIÓN 5: ALCANCE
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "5. Alcance del Proyecto", { pageBreak: true }),

      hdr(HeadingLevel.HEADING_2, "5.1 Dentro del alcance"),
      bullet("Gestión de identidades de los 4 arquetipos activos en MidPoint: egresados (30.543), personal administrativo (3.144), docentes (135) y estudiantes (1.679 cargados del ciclo Verano 2026; la carga del padrón del ciclo regular completo es una tarea pendiente priorizada)."),
      bullet("Integraciones activas: Oracle LAMB (x4 schemas), Microsoft Entra ID (lectura + escritura en Fase 12), OpenLDAP HA, Koha ILS, Keycloak SSO."),
      bullet("Modelo RBAC con roles de negocio, aplicación y atributos eduPerson/SCHAC para federación SSO."),
      bullet("Pipeline automático de sincronización: Trigger Scanner (5 min), Validity Scanner (15 min), Reconcile LAMB (02:00 UTC diario)."),
      bullet("Gobierno Entra ID: estructura de Administrative Units por campus/sede, asignación automática de licencias M365 por archetype."),
      bullet("Métricas COUNTER 5: harvest SUSHI de Scopus, EBSCO, Web of Science, IEEE Xplore, ProQuest."),
      bullet("Repositorio GitOps (github.com/UPeU-Infra/midPointEcosystem) como fuente de verdad de toda la configuración IGA."),
      spacer(),

      hdr(HeadingLevel.HEADING_2, "5.2 Fuera del alcance"),
      bullet("El Active Directory UPeU actual (192.168.13.150 / lim.upeu.edu.pe) no se incluye en este proyecto. Está mal estructurado y no tiene cobertura global. Una decisión sobre AD nuevo se tomará en Fase 12 si Entra ID no cubre todos los casos de uso."),
      bullet("Las cuentas privilegiadas de administradores de dominio son gestionadas directamente por David Urquizo, no por MidPoint."),
      bullet("Google Classroom: los docentes usan cuentas personales de Google para Google Classroom. No existe un dominio institucional G Suite / Google Workspace en UPeU."),
      bullet("Los 656 roles legacy de LAMB (ELISEO.LAMB_ROL) no se importan masivamente. Solo los que superen el role mining de Fase 7 seran gobernados por MidPoint."),
      bullet("Sistemas de terceros sin API de aprovisionamiento estándar (SCIM/REST/LDAP)."),

      // ════════════════════════════════
      // SECCIÓN 6: BENEFICIARIOS
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "6. Beneficiarios", { pageBreak: true }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 1600, 5360],
        rows: [
          new TableRow({ children: [hCell("Beneficiario", 2400), hCell("Poblacion", 1600), hCell("Beneficio específico", 5360)] }),
          ...[
            ["Estudiantes con matrícula vigente", "~24.000", "Cuenta institucional activa desde el primer día de matrícula. Acceso inmediato a M365, Koha, LDAP y sistemas académicos. Actualmente 1.679 cargados (ciclo Verano 2026); el resto se incorpora al completar la carga del ciclo regular."],
            ["Personal docente", "~1.190", "Alta automática al registrarse en LAMB. Licencia M365 correcta por tipo de contrato (TC/TP). Acceso a bases científicas vía SSO SAML. Actualmente 135 clasificados como archetype faculty; el resto figura provisionalmente como staff (ver nota sección 7.2)."],
            ["Personal administrativo", "3.144", "Acceso a sistemas según función real. Desactivacion automática al cese. Sin cuentas huérfanas que representen riesgo."],
            ["Egresados registrados", "30.635", "Correo alumni activo mientras figure en LAMB. Acceso al catálogo Koha y OPAC externo."],
            ["Equipo DTI", "72", "Eliminación de tareas manuales repetitivas. Visibilidad completa de identidades. Evidencia para auditorías sin recolección adicional. Personal DTI distribuido en los tres campus (Lima 38, Juliaca 23, Tarapoto 11)."],
            ["Autoridades académicas (Decanos, Directores)", "27", "Pueden delegar acceso a sistemas de sus unidades sin intervenir en la configuración técnica. Comprende 5 decanos de facultad, 13 directores de escuela profesional, 2 directores de filial y 7 directores de posgrado. Delegacion de administración en Entra ID por AU (campus/sede)."],
            ["Auditores externos (SUNEDU/SINEACE/ISO)", "— (ocasional)", "Acceso a reportes de ciclo de vida de identidades, registro de cambios y evidencia de controles de acceso exportable desde MidPoint."],
          ].map(([b, p, ben], i) => new TableRow({ children: [
            cell(b, { bg: i % 2 ? C.rowAlt : C.white, width: 2400, size: 18, bold: true }),
            cell(p, { bg: i % 2 ? C.rowAlt : C.white, width: 1600, size: 18, align: AlignmentType.CENTER }),
            cell(ben, { bg: i % 2 ? C.rowAlt : C.white, width: 5360, size: 18 }),
          ]}))
        ]
      }),

      // ════════════════════════════════
      // SECCIÓN 7: DESCRIPCIÓN TÉCNICA
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "7. Descripción Técnica", { pageBreak: true }),

      hdr(HeadingLevel.HEADING_2, "7.1 Arquitectura del sistema"),
      para("El sistema IGA opera en una arquitectura en capas con MidPoint como núcleo orquestador:"),
      bullet("Capa de fuentes autoritativas (IIA): Oracle LAMB ERP — 4 schemas (MOISES/DAVID/ELISEO/JOSUE). Solo lectura. Fuente de verdad para datos de RR.HH. y académicos."),
      bullet("Capa de gobierno (MidPoint 4.10.2): normaliza identidades, aplica object templates, asigna arquetipos y roles, ejecuta el ciclo de vida joiner-mover-leaver."),
      bullet("Capa de directorio (OpenLDAP HA): dos nodos N-Way Multimaster (192.168.15.168 y .169). 34.551 identidades vivas con atributos eduPerson/SCHAC completos. Consumido por Keycloak vía User Federation."),
      bullet("Capa de SSO (Keycloak 26.6.1): actúa como Identity Provider SAML/OIDC. Lee de OpenLDAP vía User Federation. Provee SSO a sistemas internos y vendores académicos externos."),
      bullet("Capa de nube (Microsoft Entra ID): 37.305 identidades sincronizadas (lectura). Gobernará licencias M365 A1/A3/A5 en Fase 12."),
      bullet("Capa de aplicaciones (Koha ILS): 5.274 cuentas gestionadas vía conector Java ConnId v1.2.1."),

      spacer(),
      hdr(HeadingLevel.HEADING_2, "7.2 Modelo de identidad canónico"),
      para("El modelo de identidad sigue los estándares ISO/IEC 24760, eduPerson 202208 y SCHAC 1.6.0, con 8 arquetipos de usuario y 8 de organización:"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 1600, 1600, 3760],
        rows: [
          new TableRow({ children: [hCell("Archetype", 2400), hCell("Cantidad PROD", 1600), hCell("IIA principal", 1600), hCell("eduPersonAffiliation", 3760)] }),
          ...[
            ["alumni (egresados)", "30.543", "Oracle DAVID", "alum"],
            ["employee-staff (personal administrativo) **", "3.144", "Oracle MOISES/ELISEO", "staff, employee, member"],
            ["student (estudiantes) *", "1.679", "Oracle DAVID", "student, member"],
            ["employee-faculty (docentes) **", "135", "Oracle MOISES/ENOC", "faculty, employee, member"],
            ["affiliate-* / contractor / service-account", "0 (pendiente poblar)", "Alta manual / ITSM", "affiliate / n/a"],
          ].map(([a, c, iia, edu], i) => new TableRow({ children: [
            cell(a, { bg: i % 2 ? C.rowAlt : C.white, width: 2400, size: 18, bold: true }),
            cell(c, { bg: i % 2 ? C.rowAlt : C.white, width: 1600, size: 18, align: AlignmentType.CENTER }),
            cell(iia, { bg: i % 2 ? C.rowAlt : C.white, width: 1600, size: 18 }),
            cell(edu, { bg: i % 2 ? C.rowAlt : C.white, width: 3760, size: 18 }),
          ]}))
        ]
      }),
      para("* El archetype student refleja actualmente 1.679 usuarios correspondientes al ciclo Verano 2026. El resource Oracle LAMB Estudiantes está configurado con el identificador de semestre fijo (ID_SEMESTRE = 279); la carga del padrón del ciclo regular vigente — aproximadamente 23.620 estudiantes — requiere parametrizar dinámicamente el semestre y constituye una tarea pendiente priorizada del proyecto.", { italic: true, color: C.gray, size: 18, before: 80 }),
      para("** Los archetypes employee-faculty (135) y employee-staff (3.144) reflejan la clasificación actual del resource Trabajadores, que identifica como docente únicamente a quienes poseen categorización académica formal en ENOC.CAT_DOCENTE (estado 02). La planta docente real es de aproximadamente 1.190 docentes universitarios; los docentes sin categorización formal figuran provisionalmente bajo employee-staff. Ajustar el criterio de clasificación docente/administrativo es una tarea pendiente del proyecto.", { italic: true, color: C.gray, size: 18, before: 40 }),

      spacer(),
      hdr(HeadingLevel.HEADING_2, "7.3 Integraciones activas (estado mayo 2026)"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2600, 1400, 1600, 3760],
        rows: [
          new TableRow({ children: [hCell("Sistema / Resource", 2600), hCell("Sombras", 1400), hCell("Tipo", 1600), hCell("Notas", 3760)] }),
          ...[
            ["Oracle LAMB Trabajadores v3", "3.802", "Lectura (inbound)", "JDBC directo. Correlación por lambDocNum. Cron 02:00 UTC."],
            ["Oracle LAMB Estudiantes v3", "1.674", "Lectura (inbound)", "JDBC. Configurado al ciclo Verano 2026 (ID_SEMESTRE fijo); carga del ciclo regular pendiente."],
            ["Oracle LAMB Egresados v3", "30.635", "Lectura (inbound)", "JDBC directo. Correlación por taxId."],
            ["LAMB-Oracle-Posiciones", "738", "Lectura (inbound)", "Estructura organizacional (orgs/cargos)."],
            ["Koha ILS", "5.274", "Lectura/Escritura", "Conector Java ConnId v1.2.1. Cron 03:00 UTC."],
            ["OpenLDAP HA (LDAP-IdentityCache-UPeU)", "34.551", "Escritura (outbound)", "N-Way Multimaster. eduPerson/SCHAC. Keycloak User Federation activa."],
            ["Microsoft Entra ID (UPEU-EntraID-Graph)", "37.305", "Lectura (solo lectura)", "Graph API v1.0. Escritura diferida a Fase 12 (permisos pendientes David Urquizo)."],
          ].map(([s, n, t, o], i) => new TableRow({ children: [
            cell(s, { bg: i % 2 ? C.rowAlt : C.white, width: 2600, size: 18, bold: true }),
            cell(n, { bg: i % 2 ? C.rowAlt : C.white, width: 1400, size: 18, align: AlignmentType.CENTER }),
            cell(t, { bg: i % 2 ? C.rowAlt : C.white, width: 1600, size: 18 }),
            cell(o, { bg: i % 2 ? C.rowAlt : C.white, width: 3760, size: 18 }),
          ]}))
        ]
      }),
      para("Cifras de sombras vivas verificadas directamente contra la base de datos PostgreSQL de MidPoint PROD el 21 de mayo de 2026.", { italic: true, color: C.gray, size: 18, before: 80 }),

      spacer(),
      hdr(HeadingLevel.HEADING_2, "7.4 Infraestructura y GitOps"),
      para("MidPoint PROD se ejecuta en el servidor 192.168.15.166 (Ubuntu 22.04, Docker, 9.7 GB RAM). Toda la configuración (resources, archetypes, roles, object templates, schemas) se versiona en el repositorio github.com/UPeU-Infra/midPointEcosystem con una estructura en dos capas:"),
      bullet("canonical/: capa estándar agnostica a la institucion, basada en estándares internacionales (archetypes, schemas eduPerson/SCHAC, roles, object templates)."),
      bullet("upeu/: overlay específico UPeU (resources Oracle LAMB, orgs bootstrap, catálogos de sedes/facultades, roles MOF/GOV)."),
      para("El flujo de cambios es siempre: modificar local -> commit -> push -> git pull en servidor PROD -> aplicar vía REST API. Nunca se usa scp."),

      // ════════════════════════════════
      // SECCIÓN 8: PLAN DE TRABAJO
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "8. Plan de Trabajo", { pageBreak: true }),

      hdr(HeadingLevel.HEADING_2, "8.1 Metodología"),
      para("El proyecto sigue la metodología \"First Steps\" de Evolveum para implementaciones MidPoint, adaptada al contexto universitario peruano. Se trabaja en sprints de dos semanas con entregas verificables en cada fase. La regla cardinal es: todo cambio se prueba en MidPoint DEV (192.168.15.230) antes de aplicar en PROD. El repositorio GitOps es la única fuente de verdad de la configuración."),

      hdr(HeadingLevel.HEADING_2, "8.2 Cronograma de fases"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [1200, 2600, 700, 700, 700, 700, 1760],
        rows: [
          new TableRow({ children: [hCell("Fase", 1200), hCell("Descripción", 2600), hCell("Q1 2026", 700), hCell("Q2 2026", 700), hCell("Q3 2026", 700), hCell("Q4 2026", 700), hCell("Estado", 1760)] }),
          cronRow("Fase 0", "Refactor doctrinal y skills IGA", "X", "", "", "", "COMPLETA"),
          cronRow("Fase 1", "Schema canónico v3.0 (eduPerson/SCHAC/SCIM)", "X", "", "", "", "ACTIVA EN PROD", true),
          cronRow("Fase 2", "Arquetipos y org tree (18 custom)", "X", "", "", "", "COMPLETA"),
          cronRow("Fase 3", "Object templates (base + 4 por archetype)", "X", "X", "", "", "COMPLETA", true),
          cronRow("Fase 4", "OpenLDAP HA N-Way Multimaster", "X", "X", "", "", "COMPLETA"),
          cronRow("Fase 5", "Resources READ (LAMB x4 + Koha + Entra ID)", "X", "X", "", "", "ACTIVA / Entra ID incompleto", true),
          cronRow("Fase 6", "Resources WRITE -> OpenLDAP (34.551 sombras)", "", "X", "", "", "VALIDADA"),
          cronRow("Fase 7", "RBAC bottom-up (72 roles, role mining LAMB)", "", "X", "X", "", "PARCIAL (39 activos)", true),
          cronRow("Fase 8", "Replanteo de documentación interna", "", "", "X", "", "NO INICIADA"),
          cronRow("Fase 9", "Validación end-to-end con piloto real", "", "", "X", "", "NO INICIADA", true),
          cronRow("Fase 10", "Deploy PROD formal post-validación", "", "", "X", "", "PROD YA OPERATIVO"),
          cronRow("Fase 12", "Gobierno completo Entra ID (writes + AUs)", "", "", "X", "X", "DIAGNÓSTICO LISTO / BLOQUEADO", true),
          cronRow("Fase 13", "Métricas COUNTER 5 bases académicas", "", "", "", "X", "NO INICIADA"),
        ]
      }),

      spacer(),
      hdr(HeadingLevel.HEADING_2, "8.3 Hitos principales"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [1400, 5000, 2960],
        rows: [
          new TableRow({ children: [hCell("Fecha", 1400), hCell("Hito", 5000), hCell("Entregable", 2960)] }),
          ...[
            ["Ene 2026", "Modelo canónico doctrinal publicado", "Skills IGA + documento ARCHITECTURE.md"],
            ["Feb 2026", "MidPoint PROD con schema + archetipos activos", "35.970 usuarios en PROD (verificado BD)"],
            ["Mar 2026", "OpenLDAP HA + Keycloak User Federation", "34.551 sombras LDAP; Keycloak SSO activo"],
            ["Abr 2026", "Resources Oracle LAMB + Koha + Entra ID activos", "7 resources activos; pipeline de reconciliación"],
            ["May 2026", "Object templates per-archetype + repo 100% en sync", "5 templates activos; conector Koha v1.2.1"],
            ["Jul 2026 (estim.)", "RBAC completo + SoD policies", "72+ roles; 2 reglas SoD ISO 27001 A.8.2"],
            ["Sep 2026 (estim.)", "Validación end-to-end con 3 usuarios piloto", "Reporte de evidencia para SUNEDU/SINEACE"],
            ["Nov 2026 (estim.)", "Gobierno Entra ID activado (writes + AUs)", "Licencias M365 por archetype automatizadas"],
            ["Dic 2026 (estim.)", "Métricas COUNTER 5 operativas", "Dashboard Grafana por facultad/programa"],
          ].map(([f, h, e], i) => new TableRow({ children: [
            cell(f, { bg: i % 2 ? C.rowAlt : C.white, width: 1400, size: 18, bold: true }),
            cell(h, { bg: i % 2 ? C.rowAlt : C.white, width: 5000, size: 18 }),
            cell(e, { bg: i % 2 ? C.rowAlt : C.white, width: 2960, size: 18 }),
          ]}))
        ]
      }),

      hdr(HeadingLevel.HEADING_2, "8.4 Bloqueantes activos"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [600, 3600, 2400, 2760],
        rows: [
          new TableRow({ children: [hCell("#", 600), hCell("Bloqueante", 3600), hCell("Afecta a", 2400), hCell("Acción requerida", 2760)] }),
          ...[
            ["B3", "4 permisos Entra ID faltantes (AdministrativeUnit.Read.All, RoleManagement.Read.Directory, AuditLog.Read.All, Application.Read.All)", "Fase 5.5 + Fase 12", "David Urquizo otorgar permisos en tenant UPeU"],
            ["B4", "Credenciales Graph API write para tenant UPeU real", "Fase 12 (gobierno Entra ID)", "David Urquizo registrar app con scopes write"],
            ["B7", "Convenio RENIEC para validación biométrica (IAL 3)", "Firma de diplomas SUNEDU (futuro)", "Área Jurídica UPeU (no crítico para piloto)"],
          ].map(([n, b, a, acc], i) => new TableRow({ children: [
            cell(n, { bg: C.yellowBg, width: 600, size: 18, bold: true, align: AlignmentType.CENTER }),
            cell(b, { bg: i % 2 ? C.rowAlt : C.white, width: 3600, size: 18 }),
            cell(a, { bg: i % 2 ? C.rowAlt : C.white, width: 2400, size: 18 }),
            cell(acc, { bg: i % 2 ? C.rowAlt : C.white, width: 2760, size: 18, bold: true }),
          ]}))
        ]
      }),

      // ════════════════════════════════
      // SECCIÓN 9: EQUIPO
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "9. Equipo del Proyecto", { pageBreak: true }),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2000, 2200, 2400, 2760],
        rows: [
          new TableRow({ children: [hCell("Nombre", 2000), hCell("Cargo", 2200), hCell("Rol en el proyecto", 2400), hCell("Responsabilidades principales", 2760)] }),
          ...[
            ["David Barrantes", "Director DTI", "Patrocinador / Aprobador", "Aprobación de recursos, representación ante Rectoría, validación de hitos estratégicos."],
            ["David Urquizo", "CTO Lima / Arquitecto de Soluciones", "Arquitecto de soluciones + Administrador Entra ID", "Aprobación de decisiones de arquitectura, gestión de permisos Entra ID (tenant UPeU), cuentas privilegiadas."],
            ["Rudy Milan", "Administrador de Infraestructura", "Infraestructura y redes", "Aprovisionamiento de VMs, apertura de puertos de red, administración de servidores Linux, soporte de acceso a Oracle LAMB."],
            ["Alberto Sanchez", "Especialista IGA / DTI", "Gestor del proyecto + Implementador IGA", "Diseño e implementación de toda la configuración MidPoint, integraciones, RBAC, documentación, GitOps, métricas COUNTER."],
          ].map(([n, c, r, res], i) => new TableRow({ children: [
            cell(n, { bg: i % 2 ? C.rowAlt : C.white, width: 2000, size: 18, bold: true }),
            cell(c, { bg: i % 2 ? C.rowAlt : C.white, width: 2200, size: 18 }),
            cell(r, { bg: i % 2 ? C.rowAlt : C.white, width: 2400, size: 18 }),
            cell(res, { bg: i % 2 ? C.rowAlt : C.white, width: 2760, size: 18 }),
          ]}))
        ]
      }),

      spacer(),
      hdr(HeadingLevel.HEADING_2, "9.1 Modelo de coordinación"),
      para("Las decisiones de arquitectura se documentan en docs/ARCHITECTURE.md y en el ROADMAP.md del repositorio. Los cambios a PROD requieren aprobación explicita del gestor del proyecto. Las cuentas privilegiadas no son gestionadas por MidPoint — las gestiona David Urquizo directamente, con tickets formales en docs/runbooks/tickets-david-urquizo.md."),
      para("La reunión de revisión de hitos se programa con el Director DTI al cierre de cada fase mayor (aprox. cada 4-6 semanas). Los bloqueantes que requieren acción de David Urquizo se escalan con al menos 5 días hábiles de anticipación."),

      // ════════════════════════════════
      // SECCIÓN 10: PRESUPUESTO
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "10. Presupuesto y Recursos", { pageBreak: true }),

      hdr(HeadingLevel.HEADING_2, "10.1 Software y licencias"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3200, 2400, 3760],
        rows: [
          new TableRow({ children: [hCell("Componente", 3200), hCell("Licencia", 2400), hCell("Costo", 3760)] }),
          ...[
            ["MidPoint 4.10.2 (Evolveum)", "Apache 2.0 / GPLv3", "S/ 0"],
            ["OpenLDAP", "OpenLDAP Public License", "S/ 0"],
            ["Keycloak 26.6.1", "Apache 2.0", "S/ 0"],
            ["Conector Java ConnId Koha", "MIT", "S/ 0"],
            ["PostgreSQL (BD de MidPoint)", "PostgreSQL License (BSD)", "S/ 0"],
            ["Java 17 (runtime MidPoint)", "GPL + Classpath Exception", "S/ 0"],
            ["Docker / Docker Compose", "Apache 2.0", "S/ 0"],
            ["Soporte Evolveum (si se contrata)", "Subscription comercial", "Opcional — no incluido en presupuesto base"],
          ].map(([c, l, p], i) => new TableRow({ children: [
            cell(c, { bg: i % 2 ? C.rowAlt : C.white, width: 3200, size: 18, bold: true }),
            cell(l, { bg: i % 2 ? C.rowAlt : C.white, width: 2400, size: 18 }),
            cell(p, { bg: i % 2 ? C.rowAlt : C.white, width: 3760, size: 18, bold: p === "S/ 0", color: p === "S/ 0" ? C.green : C.black }),
          ]}))
        ]
      }),

      spacer(),
      hdr(HeadingLevel.HEADING_2, "10.2 Infraestructura (existente — sin costo adicional)"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3200, 3200, 2960],
        rows: [
          new TableRow({ children: [hCell("Recurso", 3200), hCell("Especificacion", 3200), hCell("Asignado a", 2960)] }),
          ...[
            ["Servidor MidPoint PROD", "192.168.15.166 | Ubuntu 22.04 | Docker | 9.7 GB RAM", "IGA PROD"],
            ["Servidor MidPoint DEV", "192.168.15.230 | Ubuntu 22.04 | Docker", "Pruebas (pre-PROD)"],
            ["OpenLDAP Nodo 1", "192.168.15.168 | Ubuntu | Docker | ulimits 65536", "LDAP HA primario"],
            ["OpenLDAP Nodo 2", "192.168.15.169 | Ubuntu | Docker | ulimits 65536", "LDAP HA replica"],
            ["Servidor Keycloak", "18.218.108.85 (AWS EC2) | Docker", "SSO institucional (keyid.upeu.edu.pe)"],
            ["Oracle LAMB (acceso lectura)", "Oracle 11g | schemas MOISES/DAVID/ELISEO/JOSUE", "Fuente autoritativa"],
          ].map(([r, s, a], i) => new TableRow({ children: [
            cell(r, { bg: i % 2 ? C.rowAlt : C.white, width: 3200, size: 18, bold: true }),
            cell(s, { bg: i % 2 ? C.rowAlt : C.white, width: 3200, size: 18 }),
            cell(a, { bg: i % 2 ? C.rowAlt : C.white, width: 2960, size: 18 }),
          ]}))
        ]
      }),

      spacer(),
      hdr(HeadingLevel.HEADING_2, "10.3 Horas de trabajo DTI"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3600, 1200, 1200, 3360],
        rows: [
          new TableRow({ children: [hCell("Etapa (Fases agrupadas)", 3600), hCell("Horas est.", 1200), hCell("Horas real.", 1200), hCell("Responsable principal", 3360)] }),
          ...[
            ["Fases 0-3: Fundación (schema, archetypes, templates)", "36h", "~40h", "Alberto Sanchez"],
            ["Fase 4: OpenLDAP HA", "11.5h", "~14h", "Alberto Sanchez + Rudy Milan (redes)"],
            ["Fase 5: Resources READ", "25h", "~28h", "Alberto Sanchez + David Urquizo (Entra ID)"],
            ["Fase 6: Resources WRITE + Keycloak", "13h", "~13h", "Alberto Sanchez"],
            ["Fase 7: RBAC completo (pendiente)", "28h", "~20h realizadas", "Alberto Sanchez"],
            ["Fases 8-10: Docs, piloto, deploy PROD", "25h", "Pendiente", "Alberto Sanchez"],
            ["Fase 12: Gobierno Entra ID", "52h", "Pendiente (bloqueado)", "Alberto Sanchez + David Urquizo"],
            ["Fase 13: Métricas COUNTER", "20h", "Pendiente", "Alberto Sanchez"],
          ].map(([e, h, r, resp], i) => {
            const isCompleted = r !== "Pendiente" && !r.includes("bloqueado");
            return new TableRow({ children: [
              cell(e, { bg: i % 2 ? C.rowAlt : C.white, width: 3600, size: 18 }),
              cell(h, { bg: i % 2 ? C.rowAlt : C.white, width: 1200, size: 18, align: AlignmentType.CENTER }),
              cell(r, { bg: isCompleted ? C.greenBg : i % 2 ? C.rowAlt : C.white, width: 1200, size: 18, align: AlignmentType.CENTER, color: isCompleted ? C.green : C.black }),
              cell(resp, { bg: i % 2 ? C.rowAlt : C.white, width: 3360, size: 18 }),
            ]});
          }),
          new TableRow({ children: [
            cell("TOTAL ESTIMADO", { bg: C.headerBg, bold: true, color: C.white, width: 3600, size: 20 }),
            cell("~210h", { bg: C.headerBg, bold: true, color: "93C5FD", width: 1200, size: 20, align: AlignmentType.CENTER }),
            cell("~115h realizadas", { bg: C.headerBg, bold: true, color: "93C5FD", width: 1200, size: 20, align: AlignmentType.CENTER }),
            cell("Proyecto en ejecución", { bg: C.headerBg, color: C.white, width: 3360, size: 18 }),
          ]})
        ]
      }),

      spacer(),
      hdr(HeadingLevel.HEADING_2, "10.4 ROI: comparación con alternativas comerciales"),
      para("Una plataforma IGA comercial equivalente (SailPoint Identity Now, Saviynt o Oracle Identity Manager) tendría un costo anual de entre USD 50.000 y USD 300.000, más un tiempo de implementación de 6 a 18 meses con consultoría externa. La implementación DTI de MidPoint ha alcanzado el mismo resultado en ~115 horas de trabajo interno (a la fecha), con costo adicional de S/ 0 en licencias, usando servidores ya existentes. El ahorro estimado vs alternativa comercial mínima: > USD 50.000/año."),

      // ════════════════════════════════
      // SECCIÓN 11: RIESGOS
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "11. Gestión de Riesgos", { pageBreak: true }),

      hdr(HeadingLevel.HEADING_2, "11.1 Matriz de riesgos"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [700, 2800, 600, 600, 700, 2960],
        rows: [
          new TableRow({ children: [hCell("ID", 700), hCell("Descripción del riesgo", 2800), hCell("Probabilidad", 600), hCell("Impacto", 600), hCell("Nivel", 700), hCell("Plan de mitigacion", 2960)] }),
          riskRow("R-01", "OOM en servidor MidPoint PROD por insuficiencia de RAM bajo carga alta de reconciliación", "Media", "Alto", "MEDIO", "Monitoreo proactivo de heap JVM. Aumento de RAM a 12 GB si supera 85% de uso sostenido.", C.yellowBg),
          riskRow("R-02", "Cambio de estructura de vistas Oracle LAMB sin previo aviso (actualización ERP)", "Baja", "Alto", "MEDIO", "Resources MidPoint con correlación por clave estable (cod_trabajador, DNI). Test de reconciliación tras cada actualización LAMB.", C.white),
          riskRow("R-03", "Demora en obtención de permisos Entra ID (David Urquizo) bloquea Fase 12", "Alta", "Medio", "ALTO", "Escalamiento formal con fecha límite. Fases 1-10 no requieren write Entra ID. Fase 12 tiene fecha floating.", C.redBg),
          riskRow("R-04", "Corrupcion del repositorio GitOps o perdida de configuración", "Muy Baja", "Crítico", "MEDIO", "Repositorio GitHub con historial completo. Tags de versión por hito. Backup PostgreSQL semanal del servidor PROD.", C.white),
          riskRow("R-05", "Resistencia del personal DTI a adoptar el nuevo flujo GitOps", "Media", "Medio", "BAJO", "Documentación clara en runbooks. Capacitacion presencial de 2h para el equipo DTI. Flujo CLI simple documentado.", C.rowAlt),
          riskRow("R-06", "Incidente de seguridad por exposición de credenciales Oracle LAMB", "Baja", "Crítico", "MEDIO", "Secretos en ~/.secrets/ con permisos 600. Cuenta Oracle dedicada MIDPOINT_IGA_RO (lectura). Rotacion anual de passwords.", C.white),
          riskRow("R-07", "Fallo de la federación Keycloak -> OpenLDAP genera indisponibilidad de SSO", "Baja", "Alto", "MEDIO", "OpenLDAP HA con dos nodos. Keycloak configurado con failover a nodo 2. Runbook de recuperación documentado.", C.rowAlt),
        ]
      }),

      spacer(),
      para("Leyenda: Probabilidad y Nivel — BAJO (verde), MEDIO (amarillo), ALTO (rojo).", { italic: true, color: C.gray, size: 18 }),

      // ════════════════════════════════
      // SECCIÓN 12: KPIs
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "12. Indicadores de Éxito (KPIs)", { pageBreak: true }),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3200, 2000, 2000, 2160],
        rows: [
          new TableRow({ children: [hCell("Indicador", 3200), hCell("Meta 2026", 2000), hCell("Estado actual", 2000), hCell("Fuente de medicion", 2160)] }),
          ...[
            ["Identidades activas gestionadas por MidPoint", "> 35.000", "35.970 ✓", "BD PostgreSQL PROD"],
            ["Tiempo de aprovisionamiento de cuenta nueva", "< 24 horas (automático)", "~5 minutos (pipeline)", "Audit logs MidPoint"],
            ["Cobertura de reconciliación diaria LAMB", "100% de recursos activos", "100% (3 crons) ✓", "Task history MidPoint"],
            ["Sombras LDAP vivas sincronizadas", "> 34.000", "34.551 ✓", "Resource LDAP stats"],
            ["Cuentas Koha gestionadas automáticamente", "> 5.000", "5.274 ✓", "Resource Koha stats"],
            ["Identidades Entra ID sincronizadas (lectura)", "> 35.000", "37.305 ✓", "Resource Entra ID stats"],
            ["Estudiantes del ciclo regular cargados en MidPoint", "> 23.000", "Pendiente (resource fijado a Verano 2026)", "Resource Estudiantes"],
            ["Docentes clasificados con archetype faculty", "~1.190", "Pendiente (135; criterio CAT_DOCENTE estado 02)", "BD PostgreSQL PROD"],
            ["Roles activos en repo (GitOps sync)", "100% en repo", "72/72 ✓ (post commit 19590be)", "git diff PROD vs repo"],
            ["Archetypes custom activos en PROD", "18", "18 ✓", "BD PostgreSQL PROD"],
            ["Uptime MidPoint PROD (mensual)", "> 99%", "En seguimiento", "UptimeRobot"],
            ["Cuentas huérfanas post-cese detectadas", "0 en sistemas críticos", "En validación (Fase 9)", "Reconciliation reports"],
            ["Tiempo medio de desactivacion post-cese", "< 24 horas", "Automático (Validity Scanner 15 min)", "Audit logs"],
            ["Evidencia exportable para auditoría SUNEDU", "Sí — disponible en MidPoint", "Disponible desde Fase 9", "Audit reports PDF/CSV"],
          ].map(([ind, meta, est, fuente], i) => {
            const ok = est.includes("✓");
            return new TableRow({ children: [
              cell(ind, { bg: i % 2 ? C.rowAlt : C.white, width: 3200, size: 18 }),
              cell(meta, { bg: i % 2 ? C.rowAlt : C.white, width: 2000, size: 18 }),
              cell(est, { bg: ok ? C.greenBg : i % 2 ? C.rowAlt : C.white, width: 2000, size: 18, color: ok ? C.green : C.black, bold: ok }),
              cell(fuente, { bg: i % 2 ? C.rowAlt : C.white, width: 2160, size: 18 }),
            ]});
          })
        ]
      }),

      // ════════════════════════════════
      // SECCIÓN 13: CONCLUSIONES
      // ════════════════════════════════
      hdr(HeadingLevel.HEADING_1, "13. Conclusiones y Recomendaciones", { pageBreak: true }),

      hdr(HeadingLevel.HEADING_2, "13.1 Logros alcanzados"),
      para("El proyecto DTI-IGA-2026-001 ha alcanzado resultados sustanciales en su primera mitad de ejecución (fases 0-6 completadas, fase 7 parcial):"),
      bullet("35.970 identidades unificadas en MidPoint con modelo canónico eduPerson/SCHAC/SCIM, sin costo adicional de licencias."),
      bullet("7 recursos de identidad activos e integrados: 4 fuentes Oracle LAMB, OpenLDAP HA, Entra ID (lectura) y Koha."),
      bullet("34.551 cuentas vivas sincronizadas en el directorio OpenLDAP con atributos federados, habilitando SSO vía Keycloak hacia sistemas internos."),
      bullet("Pipeline de reconciliación automático operativo: Trigger Scanner (5 min), Validity Scanner (15 min), 3 crons LAMB diarios, Koha cron diario."),
      bullet("Repositorio GitOps 100% en sync con PROD: 18 archetypes, 72 roles, 5 object templates, 7 resources, 2 schemas — todos versionados."),
      bullet("Arquitectura en dos capas (modelo canónico estándar + overlay UPeU) que mantiene la configuración ordenada, versionada y alineada con estándares internacionales (eduPerson, SCHAC, ISO 24760)."),

      spacer(),
      hdr(HeadingLevel.HEADING_2, "13.2 Próximos pasos críticos"),
      bullet("Carga del padrón estudiantil completo: parametrizar dinámicamente el semestre en el resource Oracle LAMB Estudiantes (hoy fijado al ciclo Verano 2026, ID_SEMESTRE = 279) para incorporar los aproximadamente 23.620 estudiantes del ciclo regular vigente."),
      bullet("Corrección del criterio docente/administrativo: ajustar el resource Trabajadores para clasificar como employee-faculty a los aproximadamente 1.190 docentes universitarios reales, no solo a los 135 con categorización académica formal en ENOC.CAT_DOCENTE."),
      bullet("RBAC completo (Fase 7): finalizar role mining LAMB, definir las 2 reglas SoD ISO 27001 A.8.2, y activar la cascada Business Role -> Application Role para todos los arquetipos."),
      bullet("Validación end-to-end (Fase 9): ejecutar el flujo completo joiner-mover-leaver con 3 usuarios piloto reales y documentar evidencia para SUNEDU/SINEACE."),
      bullet("Gobierno Entra ID (Fase 12): una vez David Urquizo otorgue los 4 permisos pendientes, activar el gobierno de licencias M365 A1/A3/A5 por archetype y construir las Administrative Units por campus."),
      bullet("Métricas COUNTER (Fase 13): configurar harvest SUSHI de Scopus, EBSCO, WoS, IEEE para producir reportes de uso por facultad y programa para negociación de renovación de suscripciones."),

      spacer(),
      hdr(HeadingLevel.HEADING_2, "13.3 Solicitud de aprobación"),
      para("Se solicita al Director DTI David Barrantes la aprobación formal de este documento de proyecto, que habilita:"),
      bullet("La continuación de las fases pendientes (7, 8, 9, 12, 13) dentro del calendario establecido."),
      bullet("La gestión formal de los bloqueantes activos: solicitar a David Urquizo los 4 permisos Entra ID faltantes para desbloquer Fase 12."),
      bullet("La asignación formal del equipo del proyecto (David Barrantes, David Urquizo, Rudy Milan, Alberto Sanchez) con los roles y responsabilidades descritos en la Sección 9."),
      bullet("El uso de la infraestructura interna ya existente para completar las fases restantes sin costo adicional."),

      spacer(),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [4680, 4680],
        rows: [
          new TableRow({ children: [hCell("Aprobado por", 4680), hCell("Gestor del Proyecto", 4680)] }),
          new TableRow({ children: [
            new TableCell({
              borders: cellBorder(C.borderGray),
              width: { size: 4680, type: WidthType.DXA },
              margins: { top: 200, bottom: 400, left: 200, right: 200 },
              children: [
                new Paragraph({ spacing: { before: 0, after: 80 }, children: [new TextRun({ text: "David Barrantes", font: "Arial", size: 22, bold: true })] }),
                new Paragraph({ spacing: { before: 0, after: 40 }, children: [new TextRun({ text: "Director de Tecnologías de Información", font: "Arial", size: 18, color: C.gray })] }),
                new Paragraph({ spacing: { before: 200, after: 0 }, children: [new TextRun({ text: "Firma: _________________________ Fecha: _________________________", font: "Arial", size: 18, color: C.gray })] }),
              ]
            }),
            new TableCell({
              borders: cellBorder(C.borderGray),
              width: { size: 4680, type: WidthType.DXA },
              margins: { top: 200, bottom: 400, left: 200, right: 200 },
              children: [
                new Paragraph({ spacing: { before: 0, after: 80 }, children: [new TextRun({ text: "Alberto Sanchez", font: "Arial", size: 22, bold: true })] }),
                new Paragraph({ spacing: { before: 0, after: 40 }, children: [new TextRun({ text: "Especialista IGA — DTI UPeU", font: "Arial", size: 18, color: C.gray })] }),
                new Paragraph({ spacing: { before: 200, after: 0 }, children: [new TextRun({ text: "Fecha: 21 de mayo de 2026", font: "Arial", size: 18, color: C.gray })] }),
              ]
            }),
          ]}),
        ]
      }),

      spacer(),
      para("Documento generado por la Dirección de Tecnologías de Información — Universidad Peruana Unión. Para consultas: jsanchez@upeu.edu.pe", { align: AlignmentType.CENTER, color: C.gray, size: 16, italic: true }),

    ] // end children
  }] // end sections
});

const OUTPUT = "/Users/alberto/proyectos/upeu/midPointEcosystem/docs/DTI-IGA-2026-001-Proyecto.docx";
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUTPUT, buf);
  console.log("✅ Documento generado:", OUTPUT);
}).catch(err => {
  console.error("❌ Error:", err);
  process.exit(1);
});
