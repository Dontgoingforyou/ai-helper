import re

from app.errors import OutputCheckError
from app.models import MISSING_MARK, ProductCard, ProductInput, is_blank

TITLE_MAX = 70
DESCRIPTION_MIN = 800
DESCRIPTION_MAX = 1200
QUERY_MIN = 3
QUERY_MAX = 5

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_THOUSANDS = re.compile(r"(?<=\d)\s+(?=\d{3}(?:\D|$))")
_DASHES = str.maketrans({"–": "-", "—": "-", "−": "-", "…": "-", "ё": "е"})


def normalize(text: str) -> str:
    folded = _THOUSANDS.sub("", text).casefold().translate(_DASHES)
    return re.sub(r"\s+", "", folded.replace(",", "."))


def is_missing_mark(value: str) -> bool:
    return normalize(value) == normalize(MISSING_MARK)


def collect_problems(product: ProductInput, card: ProductCard) -> list[str]:
    problems: list[str] = []
    problems.extend(_length_problems(card))
    problems.extend(_gap_problems(product, card))
    problems.extend(_spec_problems(product, card))
    problems.extend(_number_problems(product, card))
    return problems


def check_card(product: ProductInput, card: ProductCard) -> None:
    problems = collect_problems(product, card)
    if problems:
        raise OutputCheckError("Черновик не прошёл проверку: " + "; ".join(problems))


def _length_problems(card: ProductCard) -> list[str]:
    problems: list[str] = []
    title = card.seo_title.strip()
    if not title:
        problems.append("пустой seo_title")
    elif len(title) > TITLE_MAX:
        problems.append(f"seo_title: {len(title)} символов, максимум {TITLE_MAX}")

    description = card.seo_description.strip()
    if not description:
        problems.append("пустой seo_description")
    elif not DESCRIPTION_MIN <= len(description) <= DESCRIPTION_MAX:
        problems.append(f"seo_description: {len(description)} символов, нужно {DESCRIPTION_MIN}–{DESCRIPTION_MAX}")

    query_count = len([query for query in card.search_queries if query.strip()])
    if not QUERY_MIN <= query_count <= QUERY_MAX:
        problems.append(f"search_queries: {query_count}, нужно {QUERY_MIN}–{QUERY_MAX}")
    if is_blank(card.commercial_block):
        problems.append("пустой commercial_block")
    return problems


def _gap_problems(product: ProductInput, card: ProductCard) -> list[str]:
    reported = {normalize(item) for item in card.missing_fields}
    problems = [f"не указан пробел: {label}" for label in product.blank_fields() if normalize(label) not in reported]
    filled = _filled_labels(product)
    problems.extend(
        f"поле «{label}» заполнено, но попало в пробелы" for label in filled if normalize(label) in reported
    )
    return problems


def _filled_labels(product: ProductInput) -> list[str]:
    labels: list[str] = []
    if not is_blank(product.name):
        labels.append("название")
    if not is_blank(product.manufacturer):
        labels.append("производитель")
    if not is_blank(product.description):
        labels.append("описание")
    return labels


def _spec_problems(product: ProductInput, card: ProductCard) -> list[str]:
    expected = {normalize(key): (key, value) for key, value in product.specs.items()}
    seen: dict[str, str] = {}
    problems: list[str] = []
    for row in card.specs:
        key = normalize(row.name)
        if key in seen:
            problems.append(f"характеристика «{row.name}» повторяется")
            continue
        seen[key] = row.value
        problems.extend(_one_spec(row.name, key, row.value, expected))
    problems.extend(
        f"нет характеристики «{source_name}»" for key, (source_name, _) in expected.items() if key not in seen
    )
    return problems


def _one_spec(
    display_name: str,
    key: str,
    actual: str,
    expected: dict[str, tuple[str, str]],
) -> list[str]:
    if key not in expected:
        return [f"характеристика «{display_name}» отсутствует во входных данных"]
    source_name, source_value = expected[key]
    if is_blank(source_value):
        if not is_missing_mark(actual):
            return [f"для «{source_name}» нет входного значения, ожидается «{MISSING_MARK}»"]
        return []
    if is_missing_mark(actual):
        return [f"значение «{source_name}» есть во входе, но в черновике «{MISSING_MARK}»"]
    if normalize(source_value) not in normalize(actual):
        return [f"значение «{source_name}» должно совпадать с входом"]
    return []


def _number_problems(product: ProductInput, card: ProductCard) -> list[str]:
    allowed = _corpus_numbers(product)
    found = _card_numbers(card)
    unknown = sorted(found - allowed)
    if not unknown:
        return []
    shown = ", ".join(unknown[:12])
    return [f"в черновике есть числа, которых нет во входе: {shown}"]


def has_unknown_numbers(product: ProductInput, text: str) -> bool:
    return bool(_numbers_from([text]) - _corpus_numbers(product))


def _corpus_numbers(product: ProductInput) -> set[str]:
    parts = [product.name, product.manufacturer, product.description, *product.specs.values()]
    return _numbers_from(parts)


def _card_numbers(card: ProductCard) -> set[str]:
    parts = [card.seo_title, card.seo_description, card.commercial_block, *card.search_queries]
    parts.extend(row.name for row in card.specs)
    parts.extend(row.value for row in card.specs if not is_missing_mark(row.value))
    return _numbers_from(parts)


def _numbers_from(parts: list[str]) -> set[str]:
    found: set[str] = set()
    for part in parts:
        squeezed = _THOUSANDS.sub("", part)
        found.update(match.group(0).replace(",", ".") for match in _NUMBER.finditer(squeezed))
    return found
