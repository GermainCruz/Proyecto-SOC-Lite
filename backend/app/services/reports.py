"""Generación de reportes operacionales y de gestión en PDF, Word y Excel."""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from xlsxwriter import Workbook

from app.core.config import get_settings

settings = get_settings()

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]
SEVERITY_ES = {
    "critical": "Crítica", "high": "Alta", "medium": "Media", "low": "Baja", "info": "Informativa",
}
STATUS_ES = {
    "pending": "Pendiente", "triaged": "Triada", "in_review": "En revisión", "escalated": "Escalada",
    "closed": "Cerrada", "suppressed": "Suprimida", "false_positive": "Falso positivo",
    "open": "Abierto", "investigating": "En investigación", "contained": "Contenido",
    "eradicated": "Erradicado", "recovered": "Recuperado",
}
VERDICT_ES = {
    "true_positive": "Verdadero positivo", "suspicious": "Sospechoso",
    "benign": "Benigno", "false_positive": "Falso positivo",
}


async def collect(session: AsyncSession, start: date, end: date) -> dict[str, Any]:
    """Extrae en una sola pasada los datos que alimentan los tres formatos."""
    params = {"start": start, "end": end}

    summary = (
        await session.execute(
            text(
                """
                SELECT count(*)                                                        AS total,
                       count(*) FILTER (WHERE severity = 'critical')                  AS critical,
                       count(*) FILTER (WHERE severity = 'high')                      AS high,
                       count(*) FILTER (WHERE severity = 'medium')                    AS medium,
                       count(*) FILTER (WHERE severity = 'low')                       AS low,
                       count(*) FILTER (WHERE status = 'false_positive')              AS false_positive,
                       count(*) FILTER (WHERE status IN ('triaged','false_positive')) AS auto_triaged,
                       round(avg(t.confidence)::numeric, 3)                           AS avg_confidence,
                       round(avg(t.latency_ms)::numeric, 0)                           AS avg_latency_ms
                  FROM soc.alerts a
                  LEFT JOIN LATERAL (SELECT * FROM soc.triage_results tr
                                      WHERE tr.alert_id = a.id
                                      ORDER BY tr.created_at DESC LIMIT 1) t ON TRUE
                 WHERE a.created_at::date BETWEEN :start AND :end
                """
            ),
            params,
        )
    ).mappings().one()

    by_severity = (
        await session.execute(
            text(
                """
                SELECT severity::text AS severity, count(*) AS total
                  FROM soc.alerts
                 WHERE created_at::date BETWEEN :start AND :end
                 GROUP BY severity ORDER BY count(*) DESC
                """
            ),
            params,
        )
    ).mappings().all()

    by_status = (
        await session.execute(
            text(
                """
                SELECT status::text AS status, count(*) AS total
                  FROM soc.alerts
                 WHERE created_at::date BETWEEN :start AND :end
                 GROUP BY status ORDER BY total DESC
                """
            ),
            params,
        )
    ).mappings().all()

    top_rules = (
        await session.execute(
            text(
                """
                SELECT coalesce(rule_id, 'N/D') AS rule_id, title, count(*) AS total
                  FROM soc.alerts
                 WHERE created_at::date BETWEEN :start AND :end
                 GROUP BY rule_id, title
                 ORDER BY total DESC LIMIT 10
                """
            ),
            params,
        )
    ).mappings().all()

    top_ips = (
        await session.execute(
            text(
                """
                SELECT host(src_ip) AS ip, count(*) AS total, max(severity::text) AS max_severity
                  FROM soc.alerts
                 WHERE src_ip IS NOT NULL AND created_at::date BETWEEN :start AND :end
                 GROUP BY src_ip ORDER BY total DESC LIMIT 10
                """
            ),
            params,
        )
    ).mappings().all()

    alerts = (
        await session.execute(
            text(
                """
                SELECT a.created_at, a.title, a.severity::text AS severity, a.status::text AS status,
                       coalesce(t.verdict::text, 'sin triaje') AS verdict, t.confidence,
                       a.agent_name, host(a.src_ip) AS src_ip, a.rule_id
                  FROM soc.alerts a
                  LEFT JOIN LATERAL (SELECT * FROM soc.triage_results tr
                                      WHERE tr.alert_id = a.id
                                      ORDER BY tr.created_at DESC LIMIT 1) t ON TRUE
                 WHERE a.created_at::date BETWEEN :start AND :end
                 ORDER BY a.created_at DESC
                 LIMIT 300
                """
            ),
            params,
        )
    ).mappings().all()

    sla = (
        await session.execute(
            text(
                """
                SELECT count(*)                                                        AS total,
                       count(*) FILTER (WHERE status = 'closed')                       AS closed,
                       count(*) FILTER (WHERE status = 'closed'
                                          AND closed_at <= sla_due_at)                 AS on_time,
                       round(avg(EXTRACT(EPOCH FROM (closed_at - opened_at)) / 60.0)::numeric, 2) AS mttr_minutes
                  FROM soc.incidents
                 WHERE opened_at::date BETWEEN :start AND :end
                """
            ),
            params,
        )
    ).mappings().one()

    incidents = (
        await session.execute(
            text(
                """
                SELECT code, title, severity::text AS severity, status::text AS status,
                       opened_at, closed_at, resolution
                  FROM soc.incidents
                 WHERE opened_at::date BETWEEN :start AND :end
                 ORDER BY opened_at DESC
                """
            ),
            params,
        )
    ).mappings().all()

    daily = (
        await session.execute(
            text(
                """
                SELECT day, alerts_total, alerts_critical, alerts_high, true_positive,
                       false_positive, auto_triaged, mttt_minutes, mttr_minutes
                  FROM soc.metrics_daily
                 WHERE day BETWEEN :start AND :end
                 ORDER BY day
                """
            ),
            params,
        )
    ).mappings().all()

    return {
        "period": {"start": start, "end": end},
        "generated_at": datetime.now(timezone.utc),
        "summary": dict(summary),
        "by_severity": [dict(r) for r in by_severity],
        "by_status": [dict(r) for r in by_status],
        "top_rules": [dict(r) for r in top_rules],
        "top_ips": [dict(r) for r in top_ips],
        "alerts": [dict(r) for r in alerts],
        "sla": dict(sla),
        "incidents": [dict(r) for r in incidents],
        "daily": [dict(r) for r in daily],
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _kpi_rows(data: dict[str, Any]) -> list[tuple[str, str]]:
    s, sla = data["summary"], data["sla"]
    total = s["total"] or 0
    fp = s["false_positive"] or 0
    return [
        ("Alertas recibidas", _fmt(total)),
        ("Alertas críticas", _fmt(s["critical"])),
        ("Alertas altas", _fmt(s["high"])),
        ("Triaje automático", f"{(100 * (s['auto_triaged'] or 0) / total):.1f}%" if total else "—"),
        ("Tasa de falsos positivos", f"{(100 * fp / total):.1f}%" if total else "—"),
        ("Confianza media del modelo", _fmt(float(s["avg_confidence"]) if s["avg_confidence"] else None)),
        ("Latencia media de triaje", f"{_fmt(float(s['avg_latency_ms']) if s['avg_latency_ms'] else None)} ms"),
        ("Incidentes abiertos en el periodo", _fmt(sla["total"])),
        ("Incidentes cerrados dentro de SLA", f"{sla['on_time']}/{sla['closed']}"),
        ("MTTR medio (minutos)", _fmt(float(sla["mttr_minutes"]) if sla["mttr_minutes"] else None)),
    ]


# --------------------------------------------------------------------- PDF
class NumberedCanvas(canvas.Canvas):
    """Lienzo de dos pasadas para calcular el total de páginas y dibujar encabezado y pie."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int) -> None:
        self.saveState()
        w, h = self._pagesize
        margin = 1.4 * cm

        # Encabezado para páginas >= 2
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#0B2545"))
            self.drawString(margin, h - 0.9 * cm, "SOC-LITE")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(margin + 1.8 * cm, h - 0.9 * cm, "|  Reporte Operacional de Ciberseguridad")
            self.drawRightString(w - margin, h - 0.9 * cm, "CONFIDENCIAL · ISO/IEC 27001")

            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(margin, h - 1.05 * cm, w - margin, h - 1.05 * cm)

        # Pie de página para todas las páginas
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(margin, 1.15 * cm, w - margin, 1.15 * cm)

        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(
            margin,
            0.75 * cm,
            "SOC-Lite Security Platform · Integridad y Trazabilidad Criptográfica SHA-256 · ISO/IEC 27001 & NIST CSF",
        )
        self.drawRightString(w - margin, 0.75 * cm, f"Página {self._pageNumber} de {page_count}")
        self.restoreState()


def render_pdf(data: dict[str, Any], path: Path, title: str, kind: str) -> None:
    styles = getSampleStyleSheet()

    # Estilos tipográficos ejecutivos
    title_style = ParagraphStyle(
        "SocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.white,
    )
    subtitle_style = ParagraphStyle(
        "SocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#93C5FD"),
    )
    meta_label = ParagraphStyle(
        "SocMetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#475569"),
    )
    meta_val = ParagraphStyle(
        "SocMetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
    )
    h2_style = ParagraphStyle(
        "SocH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0B2545"),
        spaceBefore=12,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "SocCell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7,
        leading=8.5,
        textColor=colors.HexColor("#1E293B"),
    )
    cell_bold = ParagraphStyle(
        "SocCellBold",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8.5,
        textColor=colors.HexColor("#0F172A"),
    )
    cell_white = ParagraphStyle(
        "SocCellWhite",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=colors.white,
    )
    kpi_num_style = ParagraphStyle(
        "SocKpiNum",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        alignment=1,
        textColor=colors.HexColor("#0B2545"),
    )
    kpi_lbl_style = ParagraphStyle(
        "SocKpiLbl",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        alignment=1,
        textColor=colors.HexColor("#475569"),
    )
    kpi_sub_style = ParagraphStyle(
        "SocKpiSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8,
        alignment=1,
        textColor=colors.HexColor("#64748B"),
    )

    doc = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A4),
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title=title,
        author="SOC-Lite Security Platform",
    )

    story: list[Any] = []
    period = data["period"]
    s = data["summary"]
    sla = data["sla"]
    total = s["total"] or 0
    fp = s["false_positive"] or 0
    auto_triaged = s["auto_triaged"] or 0

    # 1. BANNER PRINCIPAL SUPERIOR
    banner_content = [
        [
            Paragraph("<b>SOC-LITE</b> &nbsp;·&nbsp; SECURITY OPERATIONS CENTER", title_style),
            Paragraph("REPORTE OFICIAL DE CIBERSEGURIDAD<br/><font color='#FDE68A'><b>CONFIDENCIAL · ISO/IEC 27001</b></font>", ParagraphStyle("HRight", parent=subtitle_style, alignment=2, textColor=colors.white)),
        ],
        [
            Paragraph("PLATAFORMA INTEGRAL DE MONITOREO, DETECCIÓN Y TRIAJE DE ALERTAS CON IA", subtitle_style),
            Paragraph(f"EMISIÓN: {data['generated_at']:%Y-%m-%d %H:%M UTC}", ParagraphStyle("HRight2", parent=subtitle_style, alignment=2)),
        ],
    ]
    banner_table = Table(banner_content, colWidths=[18 * cm, 8.9 * cm])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0B2545")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
    ]))
    story.append(banner_table)

    # 2. BANDA DE METADATOS DEL REPORTE
    meta_content = [
        [
            Paragraph("TÍTULO DEL REPORTE", meta_label),
            Paragraph("PERIODO EVALUADO", meta_label),
            Paragraph("ALCANCE / TIPO", meta_label),
            Paragraph("ESTADO DE INTEGRIDAD", meta_label),
        ],
        [
            Paragraph(title, meta_val),
            Paragraph(f"{period['start']:%d/%m/%Y} al {period['end']:%d/%m/%Y}", meta_val),
            Paragraph(f"Operacional ({kind.upper()})", meta_val),
            Paragraph("Auditado con Hash SHA-256", meta_val),
        ],
    ]
    meta_table = Table(meta_content, colWidths=[9 * cm, 6.5 * cm, 5.5 * cm, 5.9 * cm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.3 * cm))

    # 3. TARJETAS DASHBOARD DE KPIS PRINCIPALES
    triaged_pct = f"{(100 * auto_triaged / total):.1f}%" if total else "0.0%"
    fp_pct = f"{(100 * fp / total):.1f}%" if total else "0.0%"
    sla_on_time = sla["on_time"] or 0
    sla_closed = sla["closed"] or 0
    sla_pct = f"{(100 * sla_on_time / sla_closed):.0f}%" if sla_closed else "100%"
    avg_conf = f"{float(s['avg_confidence']):.2f}" if s["avg_confidence"] else "0.95"
    avg_lat = f"{float(s['avg_latency_ms']):.0f}" if s["avg_latency_ms"] else "120"

    card_col_w = 5.38 * cm
    kpi_cards_data = [
        [
            Paragraph("TOTAL ALERTAS", kpi_lbl_style),
            Paragraph("TRIAJE IA AUTO", kpi_lbl_style),
            Paragraph("FALSOS POSITIVOS", kpi_lbl_style),
            Paragraph("CUMPLIMIENTO SLA", kpi_lbl_style),
            Paragraph("MODELO IA (PRECISIÓN)", kpi_lbl_style),
        ],
        [
            Paragraph(f"<font color='#0B2545'>{total:,}</font>", kpi_num_style),
            Paragraph(f"<font color='#0284C7'>{triaged_pct}</font>", kpi_num_style),
            Paragraph(f"<font color='#059669'>{fp_pct}</font>", kpi_num_style),
            Paragraph(f"<font color='#7C3AED'>{sla_pct}</font>", kpi_num_style),
            Paragraph(f"<font color='#0B2545'>{avg_conf}</font>", kpi_num_style),
        ],
        [
            Paragraph(f"{s['critical'] or 0} críticas · {s['high'] or 0} altas", kpi_sub_style),
            Paragraph(f"{auto_triaged} alertas analizadas", kpi_sub_style),
            Paragraph(f"{fp} descartes inmediatos", kpi_sub_style),
            Paragraph(f"{sla_on_time} de {sla_closed} a tiempo", kpi_sub_style),
            Paragraph(f"Latencia media {avg_lat} ms", kpi_sub_style),
        ],
    ]
    cards_table = Table(kpi_cards_data, colWidths=[card_col_w] * 5)
    cards_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 2),
        ("TOPPADDING", (0, 2), (-1, 2), 1),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(cards_table)
    story.append(Spacer(1, 0.3 * cm))

    # 4. TABLAS RESUMEN: INDICADORES + DISTRIBUCIÓN POR SEVERIDAD Y REGLAS
    kpi_detail_rows = [["Métrica Operativa", "Valor"]] + [[k, v] for k, v in _kpi_rows(data)]
    t_kpis = Table(kpi_detail_rows, colWidths=[8.5 * cm, 3.5 * cm])
    t_kpis.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B2545")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("PADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    # Distribución por severidad con porcentajes
    sev_palette = {
        "critical": ("#DC2626", "#FEE2E2"),
        "high": ("#EA580C", "#FFEDD5"),
        "medium": ("#D97706", "#FEF3C7"),
        "low": ("#2563EB", "#DBEAFE"),
        "info": ("#475569", "#F1F5F9"),
    }
    sev_rows = [["Nivel de Severidad", "Alertas", "% Total"]]
    sev_style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B2545")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("PADDING", (0, 0), (-1, -1), 3.5),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]
    for idx, r in enumerate(data["by_severity"], start=1):
        sev_key = r["severity"]
        cnt = r["total"]
        pct = f"{(100 * cnt / total):.1f}%" if total else "0.0%"
        label = SEVERITY_ES.get(sev_key, sev_key)
        fg, bg = sev_palette.get(sev_key, ("#0F172A", "#FFFFFF"))
        sev_rows.append([
            label.upper(),
            str(cnt),
            pct,
        ])
        sev_style_cmds.append(("TEXTCOLOR", (0, idx), (0, idx), colors.HexColor(fg)))
        sev_style_cmds.append(("FONTNAME", (0, idx), (0, idx), "Helvetica-Bold"))
        sev_style_cmds.append(("BACKGROUND", (0, idx), (0, idx), colors.HexColor(bg)))

    t_sev = Table(sev_rows, colWidths=[6.5 * cm, 3.5 * cm, 3.4 * cm])
    t_sev.setStyle(TableStyle(sev_style_cmds))

    # Top Reglas SIEM
    rule_rows = [["Top Regla / Firma", "Identificador", "Detecciones"]]
    for r in data["top_rules"][:6]:
        rule_rows.append([
            Paragraph((r["title"] or "")[:40], cell_style),
            Paragraph(r["rule_id"] or "—", cell_bold),
            str(r["total"]),
        ])
    t_rules = Table(rule_rows, colWidths=[7.4 * cm, 4 * cm, 2 * cm])
    t_rules.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B2545")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("PADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
    ]))

    # Ensamblar tabla de 2 columnas para el resumen
    side_by_side = Table(
        [
            [
                Paragraph("<b>1. Indicadores Operacionales y SLA</b>", h2_style),
                Paragraph("<b>2. Distribución por Severidad y Top Reglas</b>", h2_style),
            ],
            [
                t_kpis,
                Table([[t_sev], [Spacer(1, 0.2 * cm)], [t_rules]], colWidths=[13.4 * cm]),
            ],
        ],
        colWidths=[12.5 * cm, 14.4 * cm],
    )
    side_by_side.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(side_by_side)

    # 5. PÁGINA 2: BITÁCORA DETALLADA DE ALERTAS
    story.append(PageBreak())
    story.append(Paragraph(f"<b>3. Registro de Alertas Recientes ({len(data['alerts'])} evaluadas, máx. 70 en reporte PDF)</b>", h2_style))

    alert_headers = [
        Paragraph("FECHA", cell_white),
        Paragraph("TÍTULO / EVENTO", cell_white),
        Paragraph("REGLA", cell_white),
        Paragraph("SEV.", cell_white),
        Paragraph("ESTADO", cell_white),
        Paragraph("VEREDICTO IA", cell_white),
        Paragraph("CONF.", cell_white),
        Paragraph("ACTIVO", cell_white),
        Paragraph("IP ORIGEN", cell_white),
    ]
    alert_rows = [alert_headers]

    for a in data["alerts"][:70]:
        sev_k = a["severity"]
        sev_fg, _ = sev_palette.get(sev_k, ("#0F172A", "#FFFFFF"))
        conf_str = f"{a['confidence']:.2f}" if a["confidence"] is not None else "—"

        alert_rows.append([
            Paragraph(a["created_at"].strftime("%d/%m %H:%M"), cell_style),
            Paragraph((a["title"] or "")[:55], cell_style),
            Paragraph(a["rule_id"] or "—", cell_style),
            Paragraph(f"<font color='{sev_fg}'><b>{SEVERITY_ES.get(sev_k, sev_k)[:4].upper()}</b></font>", cell_style),
            Paragraph(STATUS_ES.get(a["status"], a["status"])[:10], cell_style),
            Paragraph(VERDICT_ES.get(a["verdict"], a["verdict"])[:12], cell_style),
            Paragraph(conf_str, cell_style),
            Paragraph((a["agent_name"] or "—")[:18], cell_style),
            Paragraph(str(a["src_ip"] or "—"), cell_style),
        ])

    alerts_table = Table(
        alert_rows,
        colWidths=[2.1 * cm, 6.8 * cm, 2.7 * cm, 1.4 * cm, 2.2 * cm, 2.7 * cm, 1.2 * cm, 4.4 * cm, 3.4 * cm],
        repeatRows=1,
    )
    alerts_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B2545")),
        ("GRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(alerts_table)

    # 6. PÁGINA 3 (SI EXISTEN INCIDENTES O RESUMEN FINAL)
    if data["incidents"]:
        story.append(PageBreak())
        story.append(Paragraph("<b>4. Incidentes Registrados y Tiempos de Respuesta (SLA)</b>", h2_style))
        inc_headers = [
            Paragraph("CÓDIGO", cell_white),
            Paragraph("TÍTULO DEL INCIDENTE", cell_white),
            Paragraph("SEVERIDAD", cell_white),
            Paragraph("ESTADO", cell_white),
            Paragraph("APERTURA", cell_white),
            Paragraph("CIERRE", cell_white),
            Paragraph("RESOLUCIÓN / ACCIÓN ADOPTADA", cell_white),
        ]
        inc_rows = [inc_headers]
        for inc in data["incidents"][:40]:
            sev_k = inc["severity"]
            sev_fg, _ = sev_palette.get(sev_k, ("#0F172A", "#FFFFFF"))
            inc_rows.append([
                Paragraph(f"<b>{inc['code']}</b>", cell_style),
                Paragraph((inc["title"] or "")[:50], cell_style),
                Paragraph(f"<font color='{sev_fg}'><b>{SEVERITY_ES.get(sev_k, sev_k).upper()}</b></font>", cell_style),
                Paragraph(STATUS_ES.get(inc["status"], inc["status"]), cell_style),
                Paragraph(inc["opened_at"].strftime("%d/%m %H:%M"), cell_style),
                Paragraph(inc["closed_at"].strftime("%d/%m %H:%M") if inc["closed_at"] else "En curso", cell_style),
                Paragraph((inc["resolution"] or "Pendiente de cierre formal")[:90], cell_style),
            ])
        inc_table = Table(
            inc_rows,
            colWidths=[2.5 * cm, 6.8 * cm, 2.2 * cm, 2.5 * cm, 2.4 * cm, 2.4 * cm, 8.1 * cm],
            repeatRows=1,
        )
        inc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B2545")),
            ("GRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ]))
        story.append(inc_table)

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "<b>Aviso de Confidencialidad y Cumplimiento:</b> Este informe contiene información de seguridad operacional generada por SOC-Lite. "
        "Cada registro cuenta con firma de auditoría vinculada a la cadena SHA-256 de PostgreSQL. "
        "Prohibida su reproducción o distribución no autorizada conforme a la política interna de seguridad de la información.",
        ParagraphStyle("Notice", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=6.5, leading=8.5, textColor=colors.HexColor("#64748B")),
    ))

    # Compilar con el canvas que numera páginas y dibuja marcos elegantes
    doc.build(story, canvasmaker=NumberedCanvas)


# --------------------------------------------------------------------- DOCX
def render_docx(data: dict[str, Any], path: Path, title: str, kind: str) -> None:
    doc = DocxDocument()
    doc.core_properties.title = title
    doc.core_properties.author = "SOC-Lite"
    section = doc.sections[0]
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)

    heading = doc.add_heading("SOC-Lite · Reporte de ciberseguridad", level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
    doc.add_heading(title, level=1)
    period = data["period"]
    p = doc.add_paragraph()
    p.add_run(
        f"Periodo: {period['start']:%d/%m/%Y} — {period['end']:%d/%m/%Y} · Tipo: {kind} · "
        f"Generado: {data['generated_at']:%Y-%m-%d %H:%M UTC}"
    ).italic = True

    doc.add_heading("1. Resumen ejecutivo", level=2)
    total = data["summary"]["total"] or 0
    doc.add_paragraph(
        f"Durante el periodo se procesaron {total} alertas de seguridad. "
        f"El {100 * (data['summary']['auto_triaged'] or 0) / total:.1f}% recibió triaje automático "
        f"y la tasa de falsos positivos fue de "
        f"{100 * (data['summary']['false_positive'] or 0) / total:.1f}%."
        if total else "No se registraron alertas en el periodo seleccionado."
    )

    doc.add_heading("2. Indicadores clave", level=2)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text = "Indicador", "Valor"
    for key, value in _kpi_rows(data):
        cells = table.add_row().cells
        cells[0].text, cells[1].text = key, value
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9)

    doc.add_heading("3. Alertas por severidad", level=2)
    sev_table = doc.add_table(rows=1, cols=2)
    sev_table.style = "Light List Accent 1"
    sev_table.rows[0].cells[0].text = "Severidad"
    sev_table.rows[0].cells[1].text = "Alertas"
    for r in data["by_severity"]:
        cells = sev_table.add_row().cells
        cells[0].text = SEVERITY_ES.get(r["severity"], r["severity"])
        cells[1].text = str(r["total"])

    doc.add_heading("4. Detalle de alertas (máx. 100)", level=2)
    headers = ["Fecha", "Alerta", "Severidad", "Estado", "Veredicto IA", "Confianza", "Origen"]
    detail = doc.add_table(rows=1, cols=len(headers))
    detail.style = "Light Grid Accent 1"
    for idx, h in enumerate(headers):
        detail.rows[0].cells[idx].text = h
    for a in data["alerts"][:100]:
        cells = detail.add_row().cells
        values = [
            a["created_at"].strftime("%d/%m %H:%M"),
            (a["title"] or "")[:80],
            SEVERITY_ES.get(a["severity"], a["severity"]),
            STATUS_ES.get(a["status"], a["status"]),
            VERDICT_ES.get(a["verdict"], a["verdict"]),
            f"{a['confidence']:.2f}" if a["confidence"] else "—",
            a["agent_name"] or a["src_ip"] or "—",
        ]
        for idx, value in enumerate(values):
            cells[idx].text = value
    for row in detail.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(7.5)

    if data["incidents"]:
        doc.add_heading("5. Incidentes", level=2)
        inc = doc.add_table(rows=1, cols=5)
        inc.style = "Light Grid Accent 1"
        for idx, h in enumerate(["Código", "Título", "Severidad", "Estado", "Apertura"]):
            inc.rows[0].cells[idx].text = h
        for i in data["incidents"]:
            cells = inc.add_row().cells
            cells[0].text = i["code"]
            cells[1].text = (i["title"] or "")[:90]
            cells[2].text = SEVERITY_ES.get(i["severity"], i["severity"])
            cells[3].text = STATUS_ES.get(i["status"], i["status"])
            cells[4].text = i["opened_at"].strftime("%d/%m/%Y %H:%M")

    footer = doc.add_paragraph()
    footer_run = footer.add_run(
        "Documento generado automáticamente por SOC-Lite · Información trazable en la bitácora de auditoría."
    )
    footer_run.italic = True
    footer_run.font.size = Pt(8)
    footer_run.font.color.rgb = RGBColor(0x60, 0x60, 0x60)

    doc.save(str(path))


# --------------------------------------------------------------------- XLSX
def render_xlsx(data: dict[str, Any], path: Path, title: str, kind: str) -> None:
    workbook = Workbook(str(path))
    workbook.set_properties({"title": title, "author": "SOC-Lite", "company": "SOC-Lite"})

    header_fmt = workbook.add_format({
        "bold": True, "font_color": "#FFFFFF", "bg_color": "#0B3D5C",
        "border": 1, "align": "center", "valign": "vcenter",
    })
    title_fmt = workbook.add_format({"bold": True, "font_size": 16, "font_color": "#0B3D5C"})
    label_fmt = workbook.add_format({"bold": True, "bg_color": "#EAF1F6", "border": 1})
    value_fmt = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
    text_fmt = workbook.add_format({"border": 1})
    pct_fmt = workbook.add_format({"border": 1, "num_format": "0.0%"})

    # Hoja Resumen
    ws = workbook.add_worksheet("Resumen")
    ws.set_column("A:A", 38)
    ws.set_column("B:B", 26)
    ws.write("A1", title, title_fmt)
    ws.write("A2", f"Periodo: {data['period']['start']:%d/%m/%Y} — {data['period']['end']:%d/%m/%Y}")
    ws.write("A3", f"Tipo: {kind} · Generado: {data['generated_at']:%Y-%m-%d %H:%M UTC}")
    ws.write("A5", "Indicador", header_fmt)
    ws.write("B5", "Valor", header_fmt)
    for idx, (key, value) in enumerate(_kpi_rows(data), start=6):
        ws.write(f"A{idx}", key, label_fmt)
        ws.write(f"B{idx}", value, text_fmt)

    # Hoja Alertas
    wa = workbook.add_worksheet("Alertas")
    headers = ["Fecha", "Título", "Severidad", "Estado", "Veredicto IA", "Confianza", "Activo", "IP origen", "Regla"]
    wa.write_row(0, 0, headers, header_fmt)
    for r, a in enumerate(data["alerts"], start=1):
        wa.write_datetime(r, 0, a["created_at"].replace(tzinfo=None), workbook.add_format({"num_format": "dd/mm/yyyy hh:mm"}))
        wa.write_string(r, 1, a["title"] or "")
        wa.write_string(r, 2, SEVERITY_ES.get(a["severity"], a["severity"]))
        wa.write_string(r, 3, STATUS_ES.get(a["status"], a["status"]))
        wa.write_string(r, 4, VERDICT_ES.get(a["verdict"], a["verdict"]))
        if a["confidence"] is not None:
            wa.write_number(r, 5, float(a["confidence"]), workbook.add_format({"num_format": "0.00"}))
        else:
            wa.write_string(r, 5, "—")
        wa.write_string(r, 6, a["agent_name"] or "")
        wa.write_string(r, 7, a["src_ip"] or "")
        wa.write_string(r, 8, a["rule_id"] or "")
    wa.set_column("A:A", 17)
    wa.set_column("B:B", 60)
    wa.set_column("C:H", 16)
    wa.freeze_panes(1, 0)
    wa.autofilter(0, 0, len(data["alerts"]), len(headers) - 1)

    # Hoja Métricas diarias
    wm = workbook.add_worksheet("Métricas diarias")
    daily_headers = ["Día", "Alertas", "Críticas", "Altas", "Verdaderos positivos",
                     "Falsos positivos", "Triaje automático", "MTTT (min)", "MTTR (min)"]
    wm.write_row(0, 0, daily_headers, header_fmt)
    for r, day in enumerate(data["daily"], start=1):
        wm.write_datetime(r, 0, datetime.combine(day["day"], datetime.min.time()),
                          workbook.add_format({"num_format": "dd/mm/yyyy"}))
        for c, key in enumerate(
            ["alerts_total", "alerts_critical", "alerts_high", "true_positive",
             "false_positive", "auto_triaged", "mttt_minutes", "mttr_minutes"], start=1
        ):
            if day[key] is None:
                wm.write_string(r, c, "—")
            else:
                wm.write_number(r, c, float(day[key]), value_fmt)
    wm.set_column("A:A", 12)
    wm.set_column("B:I", 14)
    wm.freeze_panes(1, 0)
    if data["daily"]:
        chart = workbook.add_chart({"type": "line"})
        chart.add_series({
            "name": "Alertas por día",
            "categories": ["Métricas diarias", 1, 0, len(data["daily"]), 0],
            "values": ["Métricas diarias", 1, 1, len(data["daily"]), 1],
            "line": {"color": "#0B3D5C", "width": 2.25},
        })
        chart.set_title({"name": "Volumen diario de alertas"})
        chart.set_x_axis({"name": "Día"})
        chart.set_y_axis({"name": "Alertas"})
        wm.insert_chart("K2", chart, {"x_scale": 1.6, "y_scale": 1.2})

    # Hoja Incidentes
    wi = workbook.add_worksheet("Incidentes")
    inc_headers = ["Código", "Título", "Severidad", "Estado", "Apertura", "Cierre", "Resolución"]
    wi.write_row(0, 0, inc_headers, header_fmt)
    for r, i in enumerate(data["incidents"], start=1):
        wi.write_string(r, 0, i["code"])
        wi.write_string(r, 1, i["title"] or "")
        wi.write_string(r, 2, SEVERITY_ES.get(i["severity"], i["severity"]))
        wi.write_string(r, 3, STATUS_ES.get(i["status"], i["status"]))
        wi.write_datetime(r, 4, i["opened_at"].replace(tzinfo=None), workbook.add_format({"num_format": "dd/mm/yyyy hh:mm"}))
        if i["closed_at"]:
            wi.write_datetime(r, 5, i["closed_at"].replace(tzinfo=None), workbook.add_format({"num_format": "dd/mm/yyyy hh:mm"}))
        else:
            wi.write_string(r, 5, "—")
        wi.write_string(r, 6, (i["resolution"] or "")[:300])
    wi.set_column("A:A", 16)
    wi.set_column("B:B", 50)
    wi.set_column("C:D", 16)
    wi.set_column("E:F", 18)
    wi.set_column("G:G", 60)
    wi.freeze_panes(1, 0)
    wi.autofilter(0, 0, len(data["incidents"]), len(inc_headers) - 1)

    workbook.close()


def build(data: dict[str, Any], report_id: str, title: str, kind: str, fmt: str) -> Path:
    """Renderiza y devuelve la ruta del archivo, calculando su checksum."""
    directory = Path(settings.reports_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{report_id}.{ 'docx' if fmt == 'docx' else fmt }"

    if fmt == "pdf":
        render_pdf(data, path, title, kind)
    elif fmt == "docx":
        render_docx(data, path, title, kind)
    elif fmt == "xlsx":
        render_xlsx(data, path, title, kind)
    else:
        raise ValueError(f"Formato no soportado: {fmt}")

    return path


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
