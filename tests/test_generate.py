import pytest
from app.config import Settings
from app.errors import LLMError
from app.generate import generate_card
from app.llm_client import LLMClient
from app.prompt import build_messages
from tests.conftest import card_json, product_with_gap, valid_card


class Scripted:
    def __init__(self, answers: list[str]) -> None:
        self._answers = list(answers)
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return self._answers.pop(0)


class Flaky(LLMClient):
    def __init__(self) -> None:
        super().__init__(Settings(ai_api_key="test-key", ai_retries=1))
        self.calls = 0

    def _create(self, messages: list[dict[str, str]]) -> str:
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("timeout")
        return '{"ok": true}'


def test_returns_card_without_repair() -> None:
    product = product_with_gap()
    client = Scripted([card_json(valid_card(product))])

    card = generate_card(product, client)

    assert card.seo_title == product.name
    assert len(client.calls) == 1


def test_fixes_length_and_industry_without_second_call() -> None:
    product = product_with_gap()
    draft = valid_card(product).model_copy(
        update={
            "seo_title": "М" * 71,
            "seo_description": "Слишком коротко.",
            "commercial_block": "Подходит для лабораторий и котельных.",
        }
    )
    client = Scripted([card_json(draft)])

    card = generate_card(product, client)

    assert len(client.calls) == 1
    assert len(card.seo_title) <= 70
    assert 800 <= len(card.seo_description) <= 1200
    assert "лаборатор" not in card.commercial_block.casefold()
    assert "котельн" not in card.commercial_block.casefold()


def test_falls_back_when_model_returns_no_json() -> None:
    product = product_with_gap()
    client = Scripted(["сначала рассуждение без карточки", "и повтор без json"])

    card = generate_card(product, client)

    assert len(client.calls) == 2
    assert card.specs[-1].value == "данных нет"
    assert 800 <= len(card.seo_description) <= 1200


def test_prompt_does_not_send_source_url() -> None:
    product = product_with_gap().model_copy(update={"source_url": "https://www.pribor.ru/secret-path"})

    user = build_messages(product)[1]["content"]

    assert "secret-path" not in user
    assert "характеристика: питание" in user
    assert "0–1,6 МПа" in user


def test_retries_network_then_returns() -> None:
    client = Flaky()

    assert client.complete([{"role": "user", "content": "ping"}]) == '{"ok": true}'
    assert client.calls == 2


def test_missing_api_key() -> None:
    client = LLMClient(Settings(ai_api_key=" "))

    with pytest.raises(LLMError, match="AI_API_KEY"):
        client.complete([{"role": "user", "content": "ping"}])


def test_unknown_error_is_not_retried() -> None:
    class Boom(LLMClient):
        def _create(self, messages: list[dict[str, str]]) -> str:
            raise ValueError("bug")

    client = Boom(Settings(ai_api_key="test-key", ai_retries=3))

    with pytest.raises(ValueError, match="bug"):
        client.complete([{"role": "user", "content": "ping"}])
