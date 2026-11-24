import pytest
from pydantic import BaseModel

import config
from llm import client


class Hello(BaseModel):
    message: str


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))


def test_retries_once_on_bad_json(monkeypatch):
    replies = iter(["not json at all", '{"message": "hi"}'])
    monkeypatch.setattr(client, "_chat", lambda s, u: next(replies))
    result = client.call_json("t", "sys", "user", Hello)
    assert result.message == "hi"


def test_fails_after_two_bad_replies(monkeypatch):
    monkeypatch.setattr(client, "_chat", lambda s, u: "nope")
    with pytest.raises(client.LLMError):
        client.call_json("t", "sys", "user", Hello)


def test_second_call_uses_cache(monkeypatch):
    calls = []

    def fake(s, u):
        calls.append(1)
        return '{"message": "cached"}'

    monkeypatch.setattr(client, "_chat", fake)
    client.call_json("t", "sys", "user", Hello)
    client.call_json("t", "sys", "user", Hello)
    assert len(calls) == 1


def test_strips_code_fences(monkeypatch):
    monkeypatch.setattr(client, "_chat", lambda s, u: '```json\n{"message": "ok"}\n```')
    assert client.call_json("t", "sys", "user", Hello).message == "ok"

def test_error_message_names_the_step(monkeypatch):
    def boom(s, u):
        raise client.LLMError("rate limited")

    monkeypatch.setattr(client, "_chat", boom)
    with pytest.raises(client.LLMError, match="classify"):
        client.call_json("classify", "sys", "user", Hello)

def test_model_can_be_overridden_per_stage(monkeypatch):
    monkeypatch.setattr(config, "GROQ_MODEL", "main-model")
    monkeypatch.delenv("GROQ_MODEL_QUALITY", raising=False)
    assert client._model_for("quality") == "main-model"
    monkeypatch.setenv("GROQ_MODEL_QUALITY", "small-model")
    assert client._model_for("quality") == "small-model"