from datetime import date
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.models.homework import Homework


SUBJECT_RU = {
    "math": "Математика",
    "algebra": "Алгебра",
    "physics": "Физика",
    "geometry": "Геометрия",
}


def _header(hw: Homework) -> list[str]:
    return [
        "Домашнее задание",
        f"Предмет: {SUBJECT_RU[hw.subject]}, класс: {hw.grade}",
        f"Тема: {hw.topic}",
        f"Дата: {date.today():%d.%m.%Y}",
    ]


def render_txt(hw: Homework, with_answers: bool = True) -> bytes:
    lines = [*_header(hw), ""]
    for task in hw.tasks:
        lines.extend([f"{task['index']}. {task['statement']}", ""])
    if with_answers:
        lines.extend(["---", "Ответы (для учителя)"])
        lines.extend(f"{task['index']}. {task['expected_answer']}" for task in hw.tasks)
    return ("\n".join(lines) + "\n").encode("utf-8")


def _font_name() -> str:
    name = "HomeworkUnicode"
    if name not in pdfmetrics.getRegisteredFontNames():
        font_path = next((
            path for path in (
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
                Path("C:/Windows/Fonts/arial.ttf"),
            ) if path.is_file()
        ), None)
        if font_path is None:
            raise RuntimeError("Для PDF установите шрифт DejaVu Sans (fonts-dejavu-core)")
        pdfmetrics.registerFont(TTFont(name, str(font_path)))
    return name


def render_pdf(hw: Homework, with_answers: bool = True) -> bytes:
    font = _font_name()
    style = ParagraphStyle("homework", fontName=font, fontSize=11, leading=16)
    heading = ParagraphStyle(
        "homework-heading", parent=style, fontSize=16, leading=22, spaceAfter=12
    )

    def paragraph(value: str, paragraph_style: ParagraphStyle = style) -> Paragraph:
        # Teacher/LLM text is plain text, never ReportLab markup.
        return Paragraph(escape(value).replace("\n", "<br/>"), paragraph_style)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=42, rightMargin=42,
        topMargin=42, bottomMargin=42,
    )
    header = _header(hw)
    story = [paragraph(header[0], heading)]
    story.extend(paragraph(line) for line in header[1:])
    story.append(Spacer(1, 16))

    for task in hw.tasks:
        solution_lines = Table([[""] for _ in range(4)], colWidths=[doc.width], rowHeights=18)
        solution_lines.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ]))
        story.append(KeepTogether([
            paragraph(f"{task['index']}. {task['statement']}"),
            Spacer(1, 6), solution_lines, Spacer(1, 16),
        ]))

    if with_answers:
        story.extend([PageBreak(), paragraph("Ответы (для учителя)", heading)])
        for task in hw.tasks:
            story.extend([
                paragraph(f"{task['index']}. {task['expected_answer']}"),
                Spacer(1, 10),
            ])

    doc.build(story)
    return buffer.getvalue()
