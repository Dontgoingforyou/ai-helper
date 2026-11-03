import json
from pathlib import Path

import pytest
from app.cli import load_product
from app.errors import InvalidInputError
from tests.conftest import PDF_SAMPLE


def test_pdf_sample_has_no_gaps(tmp_path: Path) -> None:
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(PDF_SAMPLE, ensure_ascii=False), encoding="utf-8")

    product = load_product(path)

    assert product.blank_fields() == []
    assert product.specs["класс точности"] == "1,5"


def test_blank_spec_is_reported(tmp_path: Path) -> None:
    payload = {
        "name": "Манометр DM 02",
        "manufacturer": "",
        "specs": {"питание": "  "},
        "description": "Измерение давления.",
    }
    path = tmp_path / "gap.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    product = load_product(path)

    assert product.blank_fields() == ["производитель", "характеристика: питание"]


@pytest.mark.parametrize(
    ("payload", "fragment"),
    [
        ("{", "Некорректный JSON"),
        ("[]", "JSON-объект"),
        (json.dumps({"price": "10"}), "Некорректные поля"),
        (json.dumps({"specs": {"питание": 9}}), "Некорректные поля"),
    ],
)
def test_rejects_bad_input(tmp_path: Path, payload: str, fragment: str) -> None:
    path = tmp_path / "bad.json"
    path.write_text(payload, encoding="utf-8")

    with pytest.raises(InvalidInputError, match=fragment):
        load_product(path)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError, match="Файл не найден"):
        load_product(tmp_path / "no.json")


def test_real_fixtures_keep_source() -> None:
    root = Path(__file__).resolve().parents[1]
    full = load_product(root / "fixtures" / "cem-dt-8890a.json")
    sparse = load_product(root / "fixtures" / "cem-dt-8897.json")

    assert "137,9 кПа" in full.specs["максимальное давление"]
    assert "60 кПа" in full.description
    assert sparse.blank_fields() == ["характеристика: питание", "характеристика: температура хранения"]
    assert "pribor.ru" in full.source_url
    assert "pribor.ru" in sparse.source_url
