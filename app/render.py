import json

from app.models import ProductCard


def render_markdown(card: ProductCard) -> str:
    specs = "\n".join(f"- {row.name}: {row.value}" for row in card.specs)
    queries = "\n".join(f"- {query}" for query in card.search_queries)
    gaps = "\n".join(f"- {item}" for item in card.missing_fields) or "- нет"
    return (
        f"# {card.seo_title}\n\n"
        f"{card.seo_description}\n\n"
        f"## Характеристики\n\n{specs}\n\n"
        f"## Поисковые запросы\n\n{queries}\n\n"
        f"## Для менеджера\n\n{card.commercial_block}\n\n"
        f"## Чего не хватает во входе\n\n{gaps}\n\n"
        f"Служебно: заголовок {len(card.seo_title)} символов, "
        f"описание {len(card.seo_description)} символов.\n"
    )


def render_json(card: ProductCard) -> str:
    return json.dumps(card.model_dump(), ensure_ascii=False, indent=2) + "\n"
