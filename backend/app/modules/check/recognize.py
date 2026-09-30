"""Распознавание ответов ученика в два прохода + проверка кодом.

Почему так. Раньше один vision-запрос получал фото вместе с условиями задач
и сам решал, где какой ответ. Модель знала, что в задаче «48 пирожков на
6 тарелок» ждут 8, и дописывала «48 : 6 = 8, Ответ: 8 пирожков» к задаче,
которую ученик не решал (или которой вообще не было на фото). Промптом это
не лечилось — модель подделывала и цитату, и координаты.

Теперь:
  1. transcribe — vision-модель НЕ видит условий, только переписывает
     рукописный текст построчно. Ей неоткуда взять «ожидаемые» ответы.
  2. match — text-only модель сопоставляет строки расшифровки с заданиями.
     Картинки у неё нет, дописать отсутствующее нечем.
  3. ground — код проверяет, что ответ стоит в строке расшифровки на месте
     результата («= 39», «Ответ: 39», последнее число строки), а в решении
     есть числа из условия этого задания или его номер. «8» внутри «48»
     не проходит — сравниваются целые числа.

Любая неуверенность уходит в «требует ручной проверки», а не в выдуманное
«верно».
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.llm.gigachat import gigachat_client
from app.modules.check.prompts import MATCH_ANSWERS_SYSTEM, TRANSCRIBE_SYSTEM

logger = logging.getLogger(__name__)

_THOUSANDS = re.compile(r"(?<=\d)[  ](?=\d{3}(?!\d))")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_LETTERS = re.compile(r"[\s.,;:!?()\[\]«»\"'\-]+")


@dataclass
class RecognizedTask:
    answer: str
    confidence: float
    photo_boxes: list[dict] = field(default_factory=list)
    work_lines: list[str] = field(default_factory=list)


def numbers(text: str) -> list[str]:
    """Целые числа строки: «20 000» → 20000, «0,5» → 0.5."""
    return [n.replace(",", ".") for n in _NUMBER.findall(_THOUSANDS.sub("", text))]


def _compact(text: str) -> str:
    return _LETTERS.sub("", text.lower())


def grounded_at_result(answer: str, line: str) -> bool:
    """Ответ стоит в строке на месте результата: после «=», после «Ответ»,
    последним числом строки или строка целиком — это ответ («39 груш»)."""
    answer_numbers = numbers(answer)
    if not answer_numbers:
        compact = _compact(answer)
        return bool(compact) and compact in _compact(line)

    target = re.escape(answer_numbers[0])
    line_numbers = numbers(line)
    if line_numbers and line_numbers[-1] == answer_numbers[0]:
        return True
    normalized = _THOUSANDS.sub("", line.lower()).replace(",", ".").strip()
    if re.fullmatch(rf"[\(\[]?\s*{target}\s*[\)\]]?[\sа-яёa-z.]*", normalized):
        return True
    pattern = rf"(?:=|отв[а-яё]*\.?\s*:?)\s*[\(\[]?\s*{target}(?![\d.])"
    return re.search(pattern, normalized) is not None


def label_matches(line: str, index: int) -> bool:
    """Строка — пометка номера задания: «№4», «N4», «4.», «4)»."""
    return re.match(rf"^\s*(?:(?:№|n|N)\s*{index}\b|{index}\s*[.)])", line) is not None


def parse_lines(content: str) -> list[dict]:
    """Разобрать ответ OCR формата `фото|x|y|w|h|текст`. Кривые строки пропускаются."""
    lines = []
    for raw in content.splitlines():
        parts = raw.strip().strip("`").split("|", 5)
        if len(parts) != 6:
            continue
        try:
            photo_index = int(parts[0])
            x, y, w, h = (min(max(float(v), 0.0), 1.0) for v in parts[1:5])
        except ValueError:
            continue
        text = parts[5].strip()
        if text:
            lines.append({"photo_index": photo_index, "x": x, "y": y, "w": w, "h": h, "text": text})
    return lines


def is_degenerate(lines: list[dict]) -> bool:
    """Модель зациклилась: одна и та же строка 3+ раз подряд."""
    run = 1
    for prev, cur in zip(lines, lines[1:]):
        run = run + 1 if prev["text"] == cur["text"] else 1
        if run >= 3:
            return True
    return False


def dedupe(lines: list[dict]) -> list[dict]:
    result = []
    for item in lines:
        if result and result[-1]["text"] == item["text"] and result[-1]["photo_index"] == item["photo_index"]:
            continue
        result.append(item)
    return result


def unit_words(tasks: list[dict]) -> list[str]:
    """Слова-единицы из эталонных ответов («груш», «карандаш») — подсказка OCR
    для чтения почерка. Без чисел и условий, чтобы не дать материала для
    «решения» задачи."""
    words = set()
    for task in tasks:
        for word in re.findall(r"[А-Яа-яЁё]{3,}", str(task.get("expected_answer", ""))):
            words.add(word.lower())
    return sorted(words)


def ground(match: dict, task: dict, lines: dict[str, dict]) -> RecognizedTask | None:
    """Проверить сопоставление кодом. None — не доверяем, пусть проверит учитель."""
    if match.get("status") != "answered":
        return None
    answer = str(match.get("answer") or "").strip()
    answer_line = lines.get(str(match.get("answer_line_id")))
    if not answer or answer_line is None:
        return None
    if not grounded_at_result(answer, answer_line["text"]):
        logger.warning(
            "recognize guard: task %s answer %r not at result position in %r",
            task["index"], answer, answer_line["text"],
        )
        return None

    cited = [lines[lid] for lid in (match.get("line_ids") or []) if lid in lines]
    if answer_line not in cited:
        cited.append(answer_line)
    statement_numbers = set(numbers(str(task.get("statement", ""))))
    context_numbers = {n for line in cited for n in numbers(line["text"])} - set(numbers(answer))
    has_label = any(label_matches(line["text"], task["index"]) for line in cited)
    if not (statement_numbers & context_numbers) and not has_label:
        logger.warning(
            "recognize guard: task %s answer %r has no task context in %r",
            task["index"], answer, [line["text"] for line in cited],
        )
        return None

    try:
        confidence = float(match.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    ordered = sorted(cited, key=lambda line: line["order"])
    return RecognizedTask(
        answer=answer,
        confidence=max(0.0, min(confidence, 1.0)),
        photo_boxes=[{
            "photo_index": answer_line["photo_index"],
            "x": answer_line["x"], "y": answer_line["y"],
            "w": answer_line["w"], "h": answer_line["h"],
        }],
        work_lines=[line["text"] for line in ordered],
    )


async def recognize_submission(photos: list[Path], tasks: list[dict]) -> dict[int, RecognizedTask]:
    """Вернуть {task_index: RecognizedTask} только для задач, которым доверяем."""
    user = f"Перепиши весь рукописный текст с {len(photos)} фото."
    units = unit_words(tasks)
    if units:
        user += " Слова, которые могут встречаться в записях: " + ", ".join(units) + "."

    parsed = parse_lines(await gigachat_client.transcribe_photos(photos, TRANSCRIBE_SYSTEM, user))
    if is_degenerate(parsed):
        logger.warning("recognize: degenerate OCR output, retrying with higher temperature")
        parsed = parse_lines(
            await gigachat_client.transcribe_photos(photos, TRANSCRIBE_SYSTEM, user, temperature=0.4)
        )
    parsed = dedupe(parsed)
    if not parsed:
        logger.warning("recognize: OCR returned no lines")
        return {}

    lines = {}
    for order, item in enumerate(parsed, 1):
        lines[f"L{order}"] = {**item, "order": order}

    listing = "\n".join(f"{lid} (фото {line['photo_index']}): {line['text']}" for lid, line in lines.items())
    task_list = "\n".join(f"{task['index']}. {task['statement']}" for task in tasks)
    matched = await gigachat_client.complete_json(
        MATCH_ANSWERS_SYSTEM,
        f"Строки расшифровки:\n{listing}\n\nЗадания:\n{task_list}",
    )

    if not isinstance(matched.get("tasks"), list):
        # Модель дважды вернула не-JSON. Это не «ученик ничего не решил» —
        # пусть очередь перезапустит проверку позже, а не закрывает работу.
        raise RuntimeError("match step returned no task list")

    by_index: dict[int, dict] = {}
    for item in matched["tasks"]:
        try:
            by_index[int(item["task_index"])] = item
        except (KeyError, TypeError, ValueError):
            continue

    result: dict[int, RecognizedTask] = {}
    claimed: dict[str, int] = {}
    for task in tasks:
        match = by_index.get(task["index"])
        if match is None:
            continue
        grounded = ground(match, task, lines)
        if grounded is None:
            continue
        line_id = str(match.get("answer_line_id"))
        rival = claimed.get(line_id)
        if rival is not None and rival in result:
            # Одна строка ответа не может принадлежать двум задачам — оставляем
            # более уверенное сопоставление, при равенстве не доверяем обоим.
            if grounded.confidence > result[rival].confidence:
                del result[rival]
            else:
                if grounded.confidence == result[rival].confidence:
                    del result[rival]
                continue
        claimed[line_id] = task["index"]
        result[task["index"]] = grounded

    for lid, line in lines.items():
        logger.warning("recognize line %s p%s: %r", lid, line["photo_index"], line["text"])
    for index, item in result.items():
        logger.warning("recognize task %s: answer=%r lines=%r", index, item.answer, item.work_lines)
    return result
