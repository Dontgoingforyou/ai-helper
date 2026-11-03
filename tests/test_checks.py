from pathlib import Path

import pytest
from app.checks import check_card, collect_problems
from app.cli import load_product
from tests.conftest import product_with_gap, valid_card


def test_accepts_copied_facts() -> None:
    product = product_with_gap()

    check_card(product, valid_card(product))


def test_rejects_title_over_70() -> None:
    product = product_with_gap()
    card = valid_card(product).model_copy(update={"seo_title": "М" * 71})

    problems = collect_problems(product, card)

    assert any("seo_title: 71" in problem for problem in problems)


def test_rejects_short_description() -> None:
    product = product_with_gap()
    card = valid_card(product).model_copy(update={"seo_description": "Короткий текст."})

    problems = collect_problems(product, card)

    assert any("seo_description" in problem for problem in problems)


def test_rejects_invented_number() -> None:
    product = product_with_gap()
    card = valid_card(product).model_copy(update={"commercial_block": "Выход 4–20 мА для котельной."})

    problems = collect_problems(product, card)

    assert any("числа, которых нет во входе" in problem for problem in problems)


def test_rejects_extra_spec_and_dropped_value() -> None:
    product = product_with_gap()
    card = valid_card(product)
    specs = list(card.specs)
    specs[0] = specs[0].model_copy(update={"value": "данных нет"})
    specs.append(specs[0].model_copy(update={"name": "пылевлагозащита", "value": "IP65"}))
    broken = card.model_copy(update={"specs": specs})

    problems = collect_problems(product, broken)

    assert any("есть во входе" in problem for problem in problems)
    assert any("пылевлагозащита" in problem for problem in problems)


def test_missing_mark_for_blank_spec_is_required() -> None:
    product = product_with_gap()
    card = valid_card(product)
    specs = [row.model_copy(update={"value": "9 В"}) if row.name == "питание" else row for row in card.specs]

    problems = collect_problems(product, card.model_copy(update={"specs": specs}))

    assert any("питание" in problem and "данных нет" in problem for problem in problems)


def test_thousand_separator_is_same_number() -> None:
    product = product_with_gap().model_copy(
        update={"description": product_with_gap().description + " Масса партии 9 970 г."}
    )
    card = valid_card(product).model_copy(update={"commercial_block": "В описании указано 9970 г."})

    check_card(product, card)


@pytest.mark.parametrize("query_count", [2, 6])
def test_rejects_query_count(query_count: int) -> None:
    product = product_with_gap()
    card = valid_card(product).model_copy(update={"search_queries": [product.name] * query_count})

    problems = collect_problems(product, card)

    assert any("search_queries" in problem for problem in problems)


def test_filled_field_cannot_be_listed_as_missing() -> None:
    product = product_with_gap()
    card = valid_card(product).model_copy(update={"missing_fields": ["название", "характеристика: питание"]})

    problems = collect_problems(product, card)

    assert any("название" in problem and "заполнено" in problem for problem in problems)


def test_both_conflicting_pressures_from_fixture_are_allowed() -> None:
    product = load_product(Path(__file__).resolve().parents[1] / "fixtures" / "cem-dt-8890a.json")
    card = valid_card(product).model_copy(update={"commercial_block": "На странице указаны 60 кПа и 137,9 кПа."})

    check_card(product, card)
    invented = card.model_copy(update={"commercial_block": "Рабочее давление 100 кПа."})
    assert any("100" in problem for problem in collect_problems(product, invented))
