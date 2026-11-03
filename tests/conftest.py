import json

from app.models import MISSING_MARK, ProductCard, ProductInput, SpecRow

PDF_SAMPLE = {
    "name": "Манометр показывающий DM 02",
    "manufacturer": "Манотомь",
    "specs": {
        "диапазон измерений": "0–1,6 МПа",
        "класс точности": "1,5",
        "присоединение": "G1/2",
        "диаметр корпуса": "100 мм",
    },
    "description": "Прибор предназначен для измерения избыточного давления.",
}


def product_with_gap() -> ProductInput:
    return ProductInput(
        name="Манометр DM 02",
        manufacturer="Манотомь",
        specs={
            "диапазон измерений": "0–1,6 МПа",
            "класс точности": "1,5",
            "питание": "",
        },
        description="Прибор предназначен для измерения избыточного давления.",
    )


def padded(seed: str, target: int = 900) -> str:
    unit = seed.strip() or "Данных мало."
    text = unit
    while len(text) < target:
        text = f"{text} {unit}"
    while len(text) > 1200 and " " in text:
        text = text.rsplit(" ", 1)[0]
    return text


def valid_card(product: ProductInput, description: str | None = None) -> ProductCard:
    specs = [SpecRow(name=key, value=value if value.strip() else MISSING_MARK) for key, value in product.specs.items()]
    seed = description or product.description or product.name
    return ProductCard(
        seo_title=product.name[:70],
        seo_description=padded(seed),
        specs=specs,
        search_queries=[product.name, product.manufacturer or "производитель", "измерение"],
        commercial_block="Область применения во входных данных не названа.",
        missing_fields=product.blank_fields(),
    )


def card_json(card: ProductCard) -> str:
    return json.dumps(card.model_dump(), ensure_ascii=False)
