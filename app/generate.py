import logging
from typing import Protocol

from app.checks import check_card
from app.enforce import draft_from_input, enforce_card
from app.errors import OutputCheckError
from app.models import ProductCard, ProductInput
from app.parse import parse_card
from app.prompt import build_messages, build_repair_messages

logger = logging.getLogger(__name__)


class CardClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


def generate_card(product: ProductInput, client: CardClient) -> ProductCard:
    label = product.name.strip() or "без названия"
    logger.info("Собираю черновик: %s", label)
    card = _from_model(product, client)
    if card is None:
        logger.warning("Ответ модели без карточки, собираю черновик из входных данных")
        card = draft_from_input(product)
    else:
        card = enforce_card(product, card)
    check_card(product, card)
    logger.info("Черновик готов: %s", label)
    return card


def _from_model(product: ProductInput, client: CardClient) -> ProductCard | None:
    raw = client.complete(build_messages(product))
    try:
        return parse_card(raw)
    except OutputCheckError as exc:
        logger.warning("Черновик не разобран, отправляю одну правку: %s", exc.message)
    raw = client.complete(build_repair_messages(product, raw, "Верни один JSON-объект карточки без текста вокруг."))
    try:
        return parse_card(raw)
    except OutputCheckError as exc:
        logger.warning("Повторный ответ тоже не разобран: %s", exc.message)
        return None
