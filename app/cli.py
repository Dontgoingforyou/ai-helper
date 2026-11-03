import argparse
import json
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.errors import InvalidInputError, LLMError, OutputCheckError
from app.generate import generate_card
from app.llm_client import LLMClient
from app.logging_config import configure_logging
from app.models import ProductInput
from app.render import render_json, render_markdown

logger = logging.getLogger(__name__)

_EXIT_INPUT = 2
_EXIT_LLM = 3
_EXIT_CHECK = 4


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = _parse_args(argv)
    try:
        product = load_product(args.path)
        card = generate_card(product, LLMClient(get_settings()))
        rendered = render_json(card) if args.format == "json" else render_markdown(card)
        _write(args.output, rendered)
        if args.json_output is not None:
            _write(args.json_output, render_json(card))
    except InvalidInputError as exc:
        print(exc.message, file=sys.stderr)
        return _EXIT_INPUT
    except OutputCheckError as exc:
        print(exc.message, file=sys.stderr)
        return _EXIT_CHECK
    except LLMError as exc:
        print(exc.message, file=sys.stderr)
        return _EXIT_LLM
    except Exception:
        logger.exception("Неожиданный сбой при сборке карточки")
        print("Не удалось собрать карточку. Подробности в логе.", file=sys.stderr)
        return 1
    return 0


def load_product(path: Path) -> ProductInput:
    if not path.is_file():
        raise InvalidInputError(f"Файл не найден: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InvalidInputError(f"Не удалось прочитать файл: {path}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidInputError(f"Некорректный JSON в {path}: строка {exc.lineno}") from exc
    if not isinstance(payload, dict):
        raise InvalidInputError("Ожидался JSON-объект с полями товара")
    try:
        return ProductInput.model_validate(payload)
    except ValidationError as exc:
        raise InvalidInputError(_field_message(exc)) from exc


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Черновик карточки товара по JSON прибора")
    parser.add_argument("path", type=Path, help="JSON с name, manufacturer, specs, description")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path, help="Куда записать результат. Без флага — stdout")
    parser.add_argument("--json-output", type=Path, help="Дополнительно записать JSON карточки")
    return parser.parse_args(argv)


def _write(path: Path | None, text: str) -> None:
    if path is None:
        sys.stdout.write(text)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _field_message(exc: ValidationError) -> str:
    parts: list[str] = []
    for error in exc.errors()[:8]:
        location = ".".join(str(item) for item in error["loc"]) or "корень"
        parts.append(f"{location}: {error['msg']}")
    return "Некорректные поля товара: " + "; ".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
