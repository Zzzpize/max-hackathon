import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.llm.gigachat import gigachat_client
from app.modules.roadmap import pipeline


def test_overlapping_weeks_rejected():
    def segment(index, weeks):
        return {
            "index": index, "weeks": weeks, "topic": "Дроби",
            "objectives": "Изучить тему", "hours": 4, "materials_hint": "",
        }

    for weeks in ("2", "2-3", "1-4", "3-5"):
        with pytest.raises(ValueError, match="пересекаются"):
            pipeline.validate_content({"segments": [segment(1, "2-4"), segment(2, weeks)]})

    content = pipeline.validate_content({
        "segments": [segment(1, "1-2"), segment(2, "3-4")]
    })
    assert [item["weeks"] for item in content["segments"]] == ["1-2", "3-4"]


@pytest.mark.asyncio
async def test_overlapping_weeks_from_llm_retry(monkeypatch):
    first = {
        "index": 1, "weeks": "1-2", "topic": "Сложение",
        "objectives": "Складывать", "hours": 4, "materials_hint": "",
    }
    second = {**first, "index": 2, "weeks": "2-3", "topic": "Вычитание"}
    invalid = {"title": "План", "segments": [first, second]}
    valid = {"title": "План", "segments": [first, {**second, "weeks": "3-4"}]}
    completion = AsyncMock(side_effect=[json.dumps(invalid), json.dumps(valid)])
    monkeypatch.setattr(gigachat_client, "chat_completion", completion)

    roadmap = await pipeline.generate_roadmap("teacher", "math", 3, "План по арифметике")

    assert roadmap.content["segments"][1]["weeks"] == "3-4"
    assert completion.await_count == 2
    assert "пересекаются" in json.loads(completion.await_args_list[1].args[1])["previous_error"]


@pytest.mark.asyncio
async def test_invalid_llm_response_retries(monkeypatch):
    class EmptyResponseClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def achat(self, _request):
            return SimpleNamespace(choices=[])

    async def fake_client():
        return EmptyResponseClient()

    monkeypatch.setattr(gigachat_client, "_client", fake_client)
    with pytest.raises(ValueError, match="без текста"):
        await gigachat_client.chat_completion("system", "user")

    valid = {
        "title": "План",
        "segments": [{
            "index": 1, "weeks": "1-2", "topic": "Дроби",
            "objectives": "Научиться работать с дробями",
            "hours": 4, "materials_hint": "",
        }],
    }
    completion = AsyncMock(side_effect=[ValueError("без текста"), json.dumps(valid)])
    monkeypatch.setattr(gigachat_client, "chat_completion", completion)

    roadmap = await pipeline.generate_roadmap(
        "teacher", "math", 3, "Нужен план по дробям"
    )

    assert roadmap.content["segments"][0]["topic"] == "Дроби"
    assert completion.await_count == 2
    assert json.loads(completion.await_args_list[1].args[1])["previous_error"] == "без текста"
