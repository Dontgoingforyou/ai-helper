import logging
import time
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.config import Settings
from app.errors import LLMError

logger = logging.getLogger(__name__)

_EXTRA_TEXT_FIELDS = ("reasoning", "reasoning_content")
_RETRY_STATUSES = {429, 500, 502, 503, 504}


class LLMClient:
    def __init__(self, settings: Settings, sdk: Any | None = None) -> None:
        self._settings = settings
        self._sdk = sdk

    def complete(self, messages: list[dict[str, str]]) -> str:
        attempts = self._settings.ai_retries + 1
        last_status: int | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self._create(messages)
            except (APITimeoutError, APIConnectionError, TimeoutError):
                logger.warning("Сбой сети LLM, попытка %s из %s", attempt, attempts)
            except APIStatusError as exc:
                last_status = exc.status_code
                if exc.status_code not in _RETRY_STATUSES:
                    raise LLMError(f"LLM отклонил запрос, статус {exc.status_code}") from exc
                logger.warning("LLM вернул статус %s, попытка %s из %s", exc.status_code, attempt, attempts)
                if attempt < attempts:
                    delay = 45 if exc.status_code == 429 else 2
                    logger.warning("Повтор через %s с", delay)
                    time.sleep(delay)
        if last_status is not None:
            raise LLMError(f"LLM недоступен после повторных попыток, последний статус {last_status}")
        raise LLMError("LLM недоступен после повторных попыток")

    def _create(self, messages: list[dict[str, str]]) -> str:
        response = self._client().chat.completions.create(
            model=self._settings.ai_model,
            temperature=self._settings.ai_temperature,
            max_tokens=self._settings.ai_max_tokens,
            messages=messages,
        )
        if not response.choices:
            raise LLMError("LLM вернул пустой ответ")
        content = _message_text(response.choices[0].message)
        if not content:
            raise LLMError("LLM вернул пустой ответ")
        return content

    def _client(self) -> Any:
        if self._sdk is not None:
            return self._sdk
        key = self._settings.ai_api_key.strip()
        if not key:
            raise LLMError("Не задан AI_API_KEY. Укажите ключ в окружении или в файле .env")
        self._sdk = OpenAI(
            api_key=key,
            base_url=self._settings.ai_base_url,
            timeout=self._settings.ai_timeout,
            max_retries=0,
        )
        return self._sdk


def _message_text(message: Any) -> str:
    parts: list[str] = []
    content = getattr(message, "content", None)
    if isinstance(content, str) and content.strip():
        parts.append(content)
    for field in _EXTRA_TEXT_FIELDS:
        value = getattr(message, field, None)
        if isinstance(value, str) and value.strip():
            parts.append(value)
    extra = getattr(message, "model_extra", None)
    if isinstance(extra, dict):
        for field in _EXTRA_TEXT_FIELDS:
            value = extra.get(field)
            if isinstance(value, str) and value.strip() and value not in parts:
                parts.append(value)
    return "\n".join(parts).strip()
