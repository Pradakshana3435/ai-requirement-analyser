import hashlib
import json
import re
import time
import threading
from pathlib import Path
from typing import Type, TypeVar

from groq import APIConnectionError, APIStatusError, Groq, RateLimitError
from pydantic import BaseModel, ValidationError

import config
import os

T = TypeVar("T", bound=BaseModel)

PROMPT_VERSION = "v1"  # bump when you change prompts, so old cache entries are ignored
MAX_TRIES = 5
MAX_WAIT = 90  # seconds; if the server asks for longer, fail instead of waiting
MAX_TOKENS = {"split": 4096, "classify": 1500, "quality": 2500, "pairs": 1500,
              "suggest": 3500, "newfacts": 2500, "summary": 600}

JSON_SUFFIX = "\n\nRespond with a single valid JSON object only. No markdown, no commentary."


class LLMError(Exception):
    """Raised with a readable message when the model call fails."""


_client = None
_local = threading.local()


def _get_client() -> Groq:
    global _client
    if _client is None:
        if config.LLM_PROVIDER != "groq":
            raise LLMError(f"Provider '{config.LLM_PROVIDER}' is not implemented. Use groq.")
        _client = Groq(api_key=config.require_key())
    return _client

def _model_for(step: str) -> str:
    """Model for one stage. Override with GROQ_MODEL_<STEP> in .env."""
    return os.getenv(f"GROQ_MODEL_{step.upper()}") or config.GROQ_MODEL

def _cache_path(step: str, system: str, user: str) -> Path:
    key = json.dumps([PROMPT_VERSION, _model_for(step), step, system, user])
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return Path(config.CACHE_DIR) / f"{step}_{digest}.json"


def _chat(system: str, user: str) -> str:
    """One model call with backoff for rate limits and network errors."""
    step = getattr(_local, "step", "")
    model = _model_for(step)
    extra = {"reasoning_effort": "low"} if "gpt-oss" in model else None
    delay = 2
    for attempt in range(MAX_TRIES):
        start = time.time()
        try:
            resp = _get_client().chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system + JSON_SUFFIX},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                max_tokens=MAX_TOKENS.get(step, 4096),
                response_format={"type": "json_object"},
                extra_body=extra,
            )
            print(f"[llm] {step}: {time.time() - start:.1f}s", flush=True)
            return resp.choices[0].message.content or ""
        except (RateLimitError, APIConnectionError) as exc:
            headers = getattr(getattr(exc, "response", None), "headers", None) or {}
            try:
                retry_after = float(headers.get("retry-after"))
            except (TypeError, ValueError):
                retry_after = None
            if retry_after is not None and retry_after > MAX_WAIT:
                raise LLMError(
                    f"Rate limit on {model}: the server asks to wait {retry_after / 60:.0f} min "
                    "(probably the daily token limit). Use another model for this stage, or try later."
                ) from exc
            if attempt == MAX_TRIES - 1:
                raise LLMError(f"Model unavailable after {MAX_TRIES} tries: {exc}") from exc
            wait = retry_after + 1 if retry_after is not None else delay
            print(f"[llm] {step}: rate limited or network error, waiting {wait:.0f}s "
                  f"(try {attempt + 1}/{MAX_TRIES})", flush=True)
            time.sleep(wait)
            delay *= 2
        except APIStatusError as exc:
            if exc.status_code == 400 and "json_validate_failed" in str(exc):
                print(f"[llm] {step}: empty or invalid JSON from model", flush=True)
                return ""
            raise LLMError(f"Groq API error {exc.status_code}: {exc.message}") from exc
    raise LLMError("Model call failed.")


def _parse(text: str, schema: Type[T]) -> T:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    return schema.model_validate(json.loads(text))


def _chat_for(step: str, system: str, user: str) -> str:
    _local.step = step
    try:
        return _chat(system, user)
    except LLMError as exc:
        raise LLMError(f"[{step}] {exc}") from exc


def call_json(step: str, system: str, user: str, schema: Type[T]) -> T:
    """Call the model and return a validated `schema` object. Cached on disk."""
    path = _cache_path(step, system, user)
    if path.exists():
        try:
            return schema.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError:
            path.unlink(missing_ok=True)  # stale or corrupt cache entry

    text = _chat_for(step, system, user)
    try:
        result = _parse(text, schema)
    except (json.JSONDecodeError, ValidationError) as err:
        retry_user = (
            f"{user}\n\nYour previous reply was invalid: {err}\n"
            "Return only valid JSON that matches the requested structure."
        )
        text = _chat_for(step, system, retry_user)
        try:
            result = _parse(text, schema)
        except (json.JSONDecodeError, ValidationError) as err2:
            raise LLMError(f"[{step}] Model returned invalid JSON twice: {err2}") from err2

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.model_dump_json(), encoding="utf-8")
    return result