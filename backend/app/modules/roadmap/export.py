from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from app.models.roadmap import Roadmap

SUBJECT_RU = {
    "math": "Математика",
    "algebra": "Алгебра",
    "physics": "Физика",
    "geometry": "Геометрия",
}


def render_txt(roadmap: Roadmap) -> bytes:
    lines = [
        f"План: {roadmap.title}",
        f"Предмет: {SUBJECT_RU[roadmap.subject]}, класс: {roadmap.grade}",
        f"Сгенерирован: {roadmap.created_at:%d.%m.%Y}",
        "",
    ]

    for segment in roadmap.content["segments"]:
        lines.extend([
            f"Недели {segment['weeks']} · {segment['hours']} часов",
            f"Тема: {segment['topic']}",
            f"Цель: {segment['objectives']}",
            f"Материалы: {segment['materials_hint']}",
            "",
        ])

    return "\n".join(lines).encode("utf-8")


def render_pdf(roadmap: Roadmap) -> bytes:
    font_path = next(
        path for path in (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        ) if path.exists()
    )
    if "RoadmapUnicode" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("RoadmapUnicode", str(font_path)))

    style = ParagraphStyle("roadmap", fontName="RoadmapUnicode", fontSize=9, leading=14)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=42, rightMargin=42)
    header = [
        Paragraph(escape(f"План: {roadmap.title}"), style),
        Paragraph(escape(f"Предмет: {SUBJECT_RU[roadmap.subject]}, класс: {roadmap.grade}"), style),
        Paragraph(escape(f"Сгенерирован: {roadmap.created_at:%d.%m.%Y}"), style),
    ]
    rows = []
    for segment in roadmap.content["segments"]:
        left = Paragraph(
            f"Недели {escape(segment['weeks'])}<br/>{segment['hours']} часов", style
        )
        right = Paragraph(
            "<br/>".join(
                f"{label}: {escape(str(segment[key]))}"
                for label, key in (("Тема", "topic"), ("Цель", "objectives"))
            ), style,
        )
        rows.append([left, right])
    table = Table(rows, colWidths=[110, 390], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    doc.build([*header, table])
    return buffer.getvalue()
