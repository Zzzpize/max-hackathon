from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.modules.check import recognize
from app.modules.check.recognize import (
    grounded_at_result,
    is_degenerate,
    label_matches,
    parse_lines,
    recognize_submission,
)

TASKS = [
    {"index": 1, "statement": "Вычисли: 247 + 358 = ?", "expected_answer": "605"},
    {"index": 2, "statement": "Было 84 груши. Продали 27 и 19. Сколько осталось?", "expected_answer": "38 груш"},
    {"index": 3, "statement": "Вычисли: 17 × 4 = ?", "expected_answer": "68"},
    {"index": 4, "statement": "48 пирожков разложили на 6 тарелок. Сколько на каждой?", "expected_answer": "8 пирожков"},
    {"index": 5, "statement": "3 коробки по 12 карандашей, подарил 5. Сколько осталось?", "expected_answer": "31 карандаш"},
]


def test_grounded_at_result_accepts_result_positions():
    assert grounded_at_result("605", "247 + 358 = 605")
    assert grounded_at_result("39 груш", "Ответ: 39 груш")
    assert grounded_at_result("31", "Отв: 31")
    assert grounded_at_result("35", "2) 54 - 19 = 35 (шт)")
    # OCR спутал «=» с «-» — последнее число строки всё равно считается итогом.
    assert grounded_at_result("605", "247 - 358 - 605")
    assert grounded_at_result("20000", "20 000 · 1 = 20 000")


def test_grounded_at_result_rejects_digit_inside_other_number():
    # Главный кейс галлюцинации: «8 пирожков» из строки «Всего: 48 п.»
    assert not grounded_at_result("8 пирожков", "Всего: 48 п.")
    assert not grounded_at_result("8", "54 - 19 = 38")
    assert not grounded_at_result("12", "12 + 12 + 12 = 36")


def test_label_matches():
    assert label_matches("№4", 4)
    assert label_matches("N 4", 4)
    assert label_matches("4. Было: 48 кг", 4)
    assert label_matches("4) 48 : 6", 4)
    assert not label_matches("№14", 4)
    assert not label_matches("48 : 6 = 8", 4)


def test_parse_lines_skips_garbage_and_clamps_boxes():
    lines = parse_lines(
        "```\n0|0.1|0.1|0.1|0.05|№1\nмусор без разделителей\n1|0.2|1.4|0.3|0.05|Ответ: 68\n0|x|0|0|0|битая\n```"
    )
    assert [line["text"] for line in lines] == ["№1", "Ответ: 68"]
    assert lines[1]["photo_index"] == 1
    assert lines[1]["y"] == 1.0


def test_is_degenerate():
    same = [{"text": "12 + 12 + 12 = 36"}] * 3
    assert is_degenerate(same)
    assert not is_degenerate([{"text": "12"}, {"text": "12"}, {"text": "36"}])


def _ocr(*rows: str) -> str:
    return "\n".join(f"{photo}|0.1|0.1|0.5|0.05|{text}" for photo, text in rows)


@pytest.mark.asyncio
async def test_unfinished_task_is_not_invented(monkeypatch):
    """Ученик записал только «Всего: 48 п.» — задача 4 не должна получить ответ,
    даже если сопоставитель попытается его выдумать."""
    ocr = _ocr(
        (0, "№1"), (0, "247 + 358 = 605"),
        (0, "№4"), (0, "Всего: 48 п."),
        (0, "№5"), (0, "12 + 12 + 12 = 36"), (0, "36 - 5 = 31"), (0, "Ответ: 31 карандаш"),
    )
    matched = {"tasks": [
        {"task_index": 1, "status": "answered", "answer": "605", "answer_line_id": "L2", "line_ids": ["L1", "L2"], "confidence": 0.9},
        # Сопоставитель «помог» и выдумал ответ — код обязан его отбросить.
        {"task_index": 4, "status": "answered", "answer": "8 пирожков", "answer_line_id": "L4", "line_ids": ["L3", "L4"], "confidence": 0.9},
        {"task_index": 5, "status": "answered", "answer": "31 карандаш", "answer_line_id": "L8", "line_ids": ["L5", "L6", "L7", "L8"], "confidence": 0.9},
    ]}
    monkeypatch.setattr(recognize.gigachat_client, "transcribe_photos", AsyncMock(return_value=ocr))
    monkeypatch.setattr(recognize.gigachat_client, "complete_json", AsyncMock(return_value=matched))

    result = await recognize_submission([Path("0.jpg")], TASKS)

    assert set(result) == {1, 5}
    assert result[5].answer == "31 карандаш"
    assert result[5].work_lines == ["№5", "12 + 12 + 12 = 36", "36 - 5 = 31", "Ответ: 31 карандаш"]
    assert result[1].photo_boxes[0]["photo_index"] == 0


@pytest.mark.asyncio
async def test_answer_from_another_task_is_rejected(monkeypatch):
    """Страницы перепутаны: «Ответ: 31» относится к №5, приписать его №4 нельзя —
    в решении нет чисел из условия №4 и нет пометки «№4»."""
    ocr = _ocr((1, "№5"), (1, "3 * 12 = 36"), (1, "36 - 5 = 31"), (1, "Ответ: 31"), (0, "№3"), (0, "17 × 4 = 68"))
    matched = {"tasks": [
        {"task_index": 4, "status": "answered", "answer": "31", "answer_line_id": "L4", "line_ids": ["L3", "L4"], "confidence": 0.8},
        {"task_index": 3, "status": "answered", "answer": "68", "answer_line_id": "L6", "line_ids": ["L5", "L6"], "confidence": 0.9},
    ]}
    monkeypatch.setattr(recognize.gigachat_client, "transcribe_photos", AsyncMock(return_value=ocr))
    monkeypatch.setattr(recognize.gigachat_client, "complete_json", AsyncMock(return_value=matched))

    result = await recognize_submission([Path("0.jpg"), Path("1.jpg")], TASKS)

    assert set(result) == {3}


@pytest.mark.asyncio
async def test_one_answer_line_cannot_serve_two_tasks(monkeypatch):
    ocr = _ocr((0, "№2"), (0, "84 - 27 - 19 = 38"), (0, "№5"), (0, "12 + 12 + 12 = 36"), (0, "Ответ: 38"))
    matched = {"tasks": [
        {"task_index": 2, "status": "answered", "answer": "38", "answer_line_id": "L5", "line_ids": ["L1", "L2", "L5"], "confidence": 0.9},
        {"task_index": 5, "status": "answered", "answer": "38", "answer_line_id": "L5", "line_ids": ["L3", "L4", "L5"], "confidence": 0.6},
    ]}
    monkeypatch.setattr(recognize.gigachat_client, "transcribe_photos", AsyncMock(return_value=ocr))
    monkeypatch.setattr(recognize.gigachat_client, "complete_json", AsyncMock(return_value=matched))

    result = await recognize_submission([Path("0.jpg")], TASKS)

    assert set(result) == {2}


@pytest.mark.asyncio
async def test_degenerate_ocr_is_retried(monkeypatch):
    looping = _ocr(*[(0, "12 + 12 + 12 = 36")] * 5)
    clean = _ocr((0, "№3"), (0, "17 × 4 = 68"))
    transcribe = AsyncMock(side_effect=[looping, clean])
    matched = {"tasks": [
        {"task_index": 3, "status": "answered", "answer": "68", "answer_line_id": "L2", "line_ids": ["L1", "L2"], "confidence": 0.9},
    ]}
    monkeypatch.setattr(recognize.gigachat_client, "transcribe_photos", transcribe)
    monkeypatch.setattr(recognize.gigachat_client, "complete_json", AsyncMock(return_value=matched))

    result = await recognize_submission([Path("0.jpg")], TASKS)

    assert transcribe.await_count == 2
    assert transcribe.await_args_list[1].kwargs["temperature"] > 0.1
    assert result[3].answer == "68"


@pytest.mark.asyncio
async def test_broken_match_response_is_retried_by_queue_not_closed(monkeypatch):
    """Если сопоставитель вернул мусор — поднимаем ошибку, чтобы очередь
    перепроверила работу, а не закрыла её со «всё на ручную проверку»."""
    monkeypatch.setattr(
        recognize.gigachat_client, "transcribe_photos", AsyncMock(return_value=_ocr((0, "17 × 4 = 68")))
    )
    monkeypatch.setattr(recognize.gigachat_client, "complete_json", AsyncMock(return_value={}))

    with pytest.raises(RuntimeError):
        await recognize_submission([Path("0.jpg")], TASKS)


@pytest.mark.asyncio
async def test_ocr_prompt_has_no_task_statements(monkeypatch):
    """Vision-модель не должна видеть условий задач — иначе снова начнёт «решать»."""
    transcribe = AsyncMock(return_value="")
    monkeypatch.setattr(recognize.gigachat_client, "transcribe_photos", transcribe)

    await recognize_submission([Path("0.jpg")], TASKS)

    user_content = transcribe.await_args_list[0].args[2]
    for task in TASKS:
        assert task["statement"] not in user_content
    assert "48" not in user_content and "6 тарелок" not in user_content
