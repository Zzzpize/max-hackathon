from datetime import datetime
from urllib.parse import unquote

import fitz
import httpx
import pytest

from app.main import app
from app.models import Homework
from app.modules.homework.export import render_pdf, render_txt


@pytest.fixture
def homework():
    return Homework(
        teacher_id="1", title="Домашка: дроби", subject="math", grade=4,
        topic="Сложение дробей", prompt="Внутренний запрос учителя",
        notes="Личная заметка",
        tasks=[
            {"index": 1, "statement": "Сложи 1/4 и 1/4.", "expected_answer": "1/2"},
            {"index": 2, "statement": "Объясни, почему 2/4 = 1/2.",
             "expected_answer": "Числитель и знаменатель разделены на 2."},
            {"index": 3, "statement": "Сравни: 1/3 < 2/3.\nОбъясни знак.",
             "expected_answer": "При равных знаменателях 1 < 2."},
        ],
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )


def test_txt_contains_all_tasks(homework):
    txt = render_txt(homework).decode("utf-8")
    questions, answers = txt.split("---\nОтветы (для учителя)\n")
    assert "Предмет: Математика, класс: 4" in questions
    assert "Тема: Сложение дробей" in questions
    for task in homework.tasks:
        assert f"{task['index']}. {task['statement']}" in questions
        assert f"{task['index']}. {task['expected_answer']}" in answers
    assert homework.notes not in txt and homework.prompt not in txt


def test_pdf_a4_has_separate_answer_page(homework):
    content = render_pdf(homework)
    assert content.startswith(b"%PDF-")
    with fitz.open(stream=content, filetype="pdf") as document:
        assert len(document) == 2
        assert document[0].rect.width == pytest.approx(595, abs=1)
        assert document[0].rect.height == pytest.approx(842, abs=1)
        questions, answers = [page.get_text() for page in document]
        assert "Домашнее задание" in questions and "Математика" in questions
        assert "Ответы (для учителя)" not in questions
        assert "Ответы (для учителя)" in answers
        for task in homework.tasks:
            assert " ".join(task["statement"].split()) in " ".join(questions.split())
            assert task["expected_answer"] in answers
        assert len(document[0].get_drawings()) >= 12  # Four solution lines per task.


@pytest.mark.parametrize("format", ["txt", "pdf"])
def test_export_without_answers(homework, format):
    content = (render_txt if format == "txt" else render_pdf)(homework, with_answers=False)
    if format == "pdf":
        with fitz.open(stream=content, filetype="pdf") as document:
            assert len(document) == 1
            text = "\n".join(page.get_text() for page in document)
    else:
        text = content.decode("utf-8")
    assert "Ответы (для учителя)" not in text
    assert homework.tasks[1]["expected_answer"] not in text
    assert homework.notes not in text and homework.prompt not in text


def test_pdf_paginates_and_escapes_markup(homework):
    homework.tasks = [
        {"index": i, "statement": f"Задача {i}: <b>текст</b> & число < 5.",
         "expected_answer": f"Ответ номер {i}."}
        for i in range(1, 31)
    ]
    homework.tasks[0]["statement"] += " Длинное условие." * 300
    with fitz.open(stream=render_pdf(homework), filetype="pdf") as document:
        text = "\n".join(page.get_text() for page in document)
        assert len(document) > 2
        assert "<b>текст</b> & число < 5." in text
        assert "Задача 30" in text and "Ответ номер 30." in text


@pytest.mark.asyncio
async def test_export_endpoints(sessions, auth_headers, homework):
    async with sessions() as session:
        session.add(homework)
        await session.commit()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
        headers=auth_headers(1),
    ) as client:
        url = f"/homework/{homework.id}/export"
        for format, content_type in (("txt", "text/plain"), ("pdf", "application/pdf")):
            response = await client.get(url, params={"format": format})
            assert response.status_code == 200, response.text
            assert response.headers["content-type"].startswith(content_type)
            header = response.headers["content-disposition"]
            assert 'attachment; filename="homework-' in header
            assert "filename*=UTF-8''homework-" in header
            assert "дроби" in unquote(header) and header.endswith(f".{format}")
        response = await client.get(url, params={"format": "txt", "with_answers": "false"})
        assert "Ответы (для учителя)" not in response.text
        assert (await client.get(url, params={"format": "docx"})).status_code == 422
        assert (await client.get(url)).status_code == 422
