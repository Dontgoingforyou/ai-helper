import json
from pathlib import Path

import pytest
from app.cli import main
from app.errors import LLMError, OutputCheckError
from tests.conftest import product_with_gap, valid_card


def test_invalid_json_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    code = main([str(path)])

    assert code == 2
    captured = capsys.readouterr()
    assert "Некорректный JSON" in captured.err


def test_writes_markdown_and_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    product = product_with_gap()
    card = valid_card(product)
    monkeypatch.setattr("app.cli.generate_card", lambda loaded, client: card)
    source = tmp_path / "in.json"
    source.write_text(json.dumps(product.model_dump(), ensure_ascii=False), encoding="utf-8")
    markdown = tmp_path / "nested" / "card.md"
    payload = tmp_path / "card.json"

    code = main([str(source), "--output", str(markdown), "--json-output", str(payload)])

    assert code == 0
    text = markdown.read_text(encoding="utf-8")
    assert text.startswith("# Манометр DM 02")
    assert "данных нет" in text
    assert "seo_title" in payload.read_text(encoding="utf-8")


def test_llm_error_exits_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "in.json"
    source.write_text(json.dumps(product_with_gap().model_dump()), encoding="utf-8")

    def fail(loaded: object, client: object) -> object:
        raise LLMError("Не задан AI_API_KEY")

    monkeypatch.setattr("app.cli.generate_card", fail)
    code = main([str(source)])

    assert code == 3
    assert "AI_API_KEY" in capsys.readouterr().err


def test_check_error_exits_4(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "in.json"
    source.write_text(json.dumps(product_with_gap().model_dump()), encoding="utf-8")

    def fail(loaded: object, client: object) -> object:
        raise OutputCheckError("Черновик не прошёл проверку: выдуманное число")

    monkeypatch.setattr("app.cli.generate_card", fail)
    assert main([str(source)]) == 4
    assert "выдуманное число" in capsys.readouterr().err
