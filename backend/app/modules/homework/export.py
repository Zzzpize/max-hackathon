from datetime import date
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from app.models import Homework
from app.modules.roadmap.export import SUBJECT_RU


def render_txt(hw: Homework, with_answers: bool = True) -> bytes:
    lines = [
        "Домашнее задание",
        f"Предмет: {SUBJECT_RU[hw.subject]}, класс: {hw.grade}",
        f"Тема: {hw.topic}",
        f"Дата: {date.today():%d.%m.%Y}",
        "",
    ]
    for task in hw.tasks:
        lines.extend((f"{task['index']}. {task['statement']}", ""))
    if with_answers:
        lines.extend(("---", "Ответы (для учителя)"))
        lines.extend(f"{task['index']}. {task['expected_answer']}" for task in hw.tasks)
    return "\n".join(lines).encode("utf-8")


def render_pdf(hw: Homework, with_answers: bool = True) -> bytes:
    font_path = next(
        path for path in (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        ) if path.exists()
    )
    if "HomeworkUnicode" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("HomeworkUnicode", str(font_path)))

    style = ParagraphStyle("homework", fontName="HomeworkUnicode", fontSize=10, leading=15)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=42, rightMargin=42)
    content = [
        Paragraph("Домашнее задание", style),
        Paragraph(escape(f"Предмет: {SUBJECT_RU[hw.subject]}, класс: {hw.grade}"), style),
        Paragraph(escape(f"Тема: {hw.topic}"), style),
        Paragraph(f"Дата: {date.today():%d.%m.%Y}", style),
        Spacer(1, 20),
    ]
    for task in hw.tasks:
        content.extend((
            Paragraph(escape(f"{task['index']}. {task['statement']}").replace("\n", "<br/>"), style),
            Spacer(1, 60),
        ))
    if with_answers:
        content.extend((PageBreak(), Paragraph("Ответы (для учителя)", style), Spacer(1, 12)))
        for task in hw.tasks:
            content.extend((
                Paragraph(escape(f"{task['index']}. {task['expected_answer']}").replace("\n", "<br/>"), style),
                Spacer(1, 8),
            ))
    doc.build(content)
    return buffer.getvalue()
