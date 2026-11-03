import json
import re

from pydantic import ValidationError

from app.errors import OutputCheckError
from app.models import ProductCard

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def parse_card(raw: str) -> ProductCard:
    payload = _extract_object(raw)
    try:
        card = ProductCard.model_validate(payload)
    except ValidationError as exc:
        raise OutputCheckError(_schema_message(exc)) from exc
    return card.model_copy(
        update={
            "seo_title": card.seo_title.strip(),
            "seo_description": card.seo_description.strip(),
            "commercial_block": card.commercial_block.strip(),
            "search_queries": [item.strip() for item in card.search_queries if item.strip()],
            "missing_fields": [item.strip() for item in card.missing_fields if item.strip()],
            "specs": card.specs,
        }
    )


def _extract_object(raw: str) -> dict[str, object]:
    text = raw.strip()
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    found = _json_objects(text)
    for payload in found:
        if "seo_title" in payload:
            return payload
    if found:
        return found[0]
    raise OutputCheckError("Ответ модели не содержит JSON-объект")


def _json_objects(text: str) -> list[dict[str, object]]:
    decoder = json.JSONDecoder()
    found: list[dict[str, object]] = []
    index = 0
    while True:
        start = text.find("{", index)
        if start < 0:
            return found
        try:
            payload, offset = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            index = start + 1
            continue
        if isinstance(payload, dict):
            found.append(payload)
        index = start + max(offset, 1)


def _schema_message(exc: ValidationError) -> str:
    parts: list[str] = []
    for error in exc.errors()[:8]:
        location = ".".join(str(item) for item in error["loc"])
        parts.append(f"{location}: {error['msg']}")
    return "Структура JSON не совпадает со схемой карточки: " + "; ".join(parts)
