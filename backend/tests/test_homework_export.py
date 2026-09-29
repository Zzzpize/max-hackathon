from datetime import datetime

import httpx
import pytest

from app.main import app
from app.models import Homework
from app.modules.homework.export import render_txt


def homework():
    return Homework(
        teacher_id="1", title="Дроби", subject="math", grade=4,
        topic="Сложение дробей", prompt="Составь задачи по дробям",
        tasks=[
            {"index": 1, "statement": "Сложи 1/2 и 1/4", "expected_answer": "3/4"},
            {"index": 2, "statement": "Сложи 1/3 и 1/3", "expected_answer": "2/3"},
        ],
        created_at=datetime(2026, 9, 29), updated_at=datetime(2026, 9, 29),
    )


def test_txt_contains_all_tasks():
    text = render_txt(homework()).decode("utf-8")
    for value in ("Сложи 1/2", "Сложи 1/3", "Ответы (для учителя)", "3/4", "2/3"):
        assert value in text
    assert text.index("Сложи 1/3") < text.index("Ответы (для учителя)")


def test_txt_without_answers():
    text = render_txt(homework(), with_answers=False).decode("utf-8")
    assert "Сложи 1/2" in text and "Сложи 1/3" in text
    assert "Ответы (для учителя)" not in text
    assert "3/4" not in text and "2/3" not in text


@pytest.mark.asyncio
async def test_export_txt_and_pdf(sessions, auth_headers):
    async with sessions() as session:
        saved = homework()
        session.add(saved)
        await session.commit()
        homework_id = saved.id

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test", headers=auth_headers(1)
    ) as client:
        txt = await client.get(f"/homework/{homework_id}/export?format=txt")
        assert txt.status_code == 200, txt.text
        assert txt.headers["content-type"].startswith("text/plain")
        assert "Сложи 1/2" in txt.text and "3/4" in txt.text
        assert "filename*=UTF-8''homework-" in txt.headers["content-disposition"]

        txt_without_answers = await client.get(
            f"/homework/{homework_id}/export?format=txt&with_answers=false"
        )
        assert txt_without_answers.status_code == 200
        assert "Сложи 1/2" in txt_without_answers.text
        assert "3/4" not in txt_without_answers.text

        pdf = await client.get(f"/homework/{homework_id}/export?format=pdf")
        assert pdf.status_code == 200, pdf.text
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.content.startswith(b"%PDF-") and b"%%EOF" in pdf.content[-100:]
        assert pdf.content.count(b"/Type /Page\n") >= 2

        pdf_without_answers = await client.get(
            f"/homework/{homework_id}/export?format=pdf&with_answers=false"
        )
        assert pdf_without_answers.status_code == 200
        assert pdf_without_answers.content.startswith(b"%PDF-")
        assert pdf_without_answers.content.count(b"/Type /Page\n") == 1

        invalid = await client.get(f"/homework/{homework_id}/export?format=docx")
        assert invalid.status_code == 422
