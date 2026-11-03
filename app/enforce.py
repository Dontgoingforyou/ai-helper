import re

from app.checks import DESCRIPTION_MAX, DESCRIPTION_MIN, QUERY_MAX, QUERY_MIN, TITLE_MAX, has_unknown_numbers, normalize
from app.models import MISSING_MARK, ProductCard, ProductInput, SpecRow, is_blank

_CLAIM_STEMS = (
    "лаборатор",
    "производств",
    "вентиляц",
    "котельн",
    "нефтегаз",
    "пищев",
    "предприят",
    "институт",
    "исследователь",
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_NO_APPLICATION = "Область применения во входных данных не названа."


def enforce_card(product: ProductInput, card: ProductCard) -> ProductCard:
    corpus = _corpus(product)
    return ProductCard(
        seo_title=_fit_title(card.seo_title, product, corpus),
        seo_description=_fit_description(card.seo_description, product, corpus),
        specs=_specs_from_input(product),
        search_queries=_fit_queries(card.search_queries, product, corpus),
        commercial_block=_fit_commercial(card.commercial_block, product, corpus),
        missing_fields=product.blank_fields(),
    )


def draft_from_input(product: ProductInput) -> ProductCard:
    empty = ProductCard(
        seo_title="",
        seo_description="",
        specs=[],
        search_queries=[],
        commercial_block="",
        missing_fields=[],
    )
    return enforce_card(product, empty)


def _corpus(product: ProductInput) -> str:
    parts = [product.name, product.manufacturer, product.description, *product.specs.values()]
    return normalize(" ".join(parts))


def _specs_from_input(product: ProductInput) -> list[SpecRow]:
    return [SpecRow(name=key, value=value if value.strip() else MISSING_MARK) for key, value in product.specs.items()]


def _fit_title(title: str, product: ProductInput, corpus: str) -> str:
    candidate = title.strip()
    if _text_ok(candidate, product, corpus) and len(candidate) <= TITLE_MAX:
        return candidate
    trimmed = _trim_words(candidate, TITLE_MAX)
    if trimmed and _text_ok(trimmed, product, corpus):
        return trimmed
    fallback = product.name.strip() or product.manufacturer.strip() or "Прибор"
    return _trim_words(fallback, TITLE_MAX)


def _fit_description(model_text: str, product: ProductInput, corpus: str) -> str:
    parts = _usable_parts(model_text, product, corpus)
    parts.extend(_usable_parts(product.description, product, corpus))
    parts.extend(_spec_lines(product))
    return _assemble(parts, DESCRIPTION_MIN, DESCRIPTION_MAX)


def _fit_commercial(_model_text: str, product: ProductInput, corpus: str) -> str:
    parts = _usable_parts(product.description, product, corpus)[:2]
    if not parts:
        return _NO_APPLICATION
    return _trim_words(" ".join(parts), 700)


def _fit_queries(model_queries: list[str], product: ProductInput, corpus: str) -> list[str]:
    kept = _take_queries(model_queries, product, corpus, QUERY_MAX)
    if len(kept) >= QUERY_MIN:
        return kept
    extra = _take_queries(_query_fillers(product), product, corpus, QUERY_MIN - len(kept))
    return (kept + extra)[:QUERY_MAX]


def _take_queries(queries: list[str], product: ProductInput, corpus: str, limit: int) -> list[str]:
    kept: list[str] = []
    seen: set[str] = set()
    for query in queries:
        cleaned = query.strip()
        key = normalize(cleaned)
        if not cleaned or key in seen or not _text_ok(cleaned, product, corpus):
            continue
        seen.add(key)
        kept.append(cleaned)
        if len(kept) == limit:
            break
    return kept


def _query_fillers(product: ProductInput) -> list[str]:
    fillers = [product.name, product.manufacturer]
    for key, value in product.specs.items():
        if value.strip():
            fillers.append(f"{product.name} {key}".strip())
    return fillers


def _spec_lines(product: ProductInput) -> list[str]:
    lines: list[str] = []
    for key, value in product.specs.items():
        shown = value.strip() or MISSING_MARK
        lines.append(f"{key}: {shown}.")
    return lines


def _usable_parts(text: str, product: ProductInput, corpus: str) -> list[str]:
    return [part for part in _sentences(text) if _text_ok(part, product, corpus)]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE.split(text.strip()) if part.strip()]


def _text_ok(text: str, product: ProductInput, corpus: str) -> bool:
    if is_blank(text) or has_unknown_numbers(product, text):
        return False
    folded = normalize(text)
    return all(stem not in folded or stem in corpus for stem in _CLAIM_STEMS)


def _assemble(parts: list[str], low: int, high: int) -> str:
    unique = _unique(parts) or ["Описание собирается только из входных данных."]
    text = ""
    for index in range(40):
        if len(text) >= low:
            break
        candidate = f"{text} {unique[index % len(unique)]}".strip()
        if len(candidate) <= high:
            text = candidate
            continue
        trimmed = _trim_words(candidate, high)
        if len(trimmed) >= low:
            return trimmed
        break
    if len(text) > high:
        return _trim_words(text, high)
    return text


def _unique(parts: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for part in parts:
        key = normalize(part)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(part.strip())
    return result


def _trim_words(text: str, limit: int) -> str:
    value = text.strip()
    if len(value) <= limit:
        return value
    cut = value[:limit].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-")
