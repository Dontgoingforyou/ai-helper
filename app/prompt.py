import json

from app.models import MISSING_MARK, ProductInput

SYSTEM_PROMPT = f"""Ты готовишь черновик карточки товара для B2B-магазина контрольно-измерительных приборов.
Верни один JSON-объект и ничего больше: без Markdown, без пояснений до или после JSON.

Ключи:
- seo_title: строка не длиннее 70 символов, считая пробелы
- seo_description: строка от 800 до 1200 символов, считая пробелы
- specs: массив объектов {{"name": "...", "value": "..."}}
- search_queries: от 3 до 5 строк
- commercial_block: кому подходит прибор и какую измерительную задачу решает
- missing_fields: массив строк

Правила фактов:
- Имена и значения характеристик копируй из входного specs. Не переводи единицы, не округляй и не сокращай числа.
- Не добавляй строки specs, которых нет во входе.
- Если значение характеристики пустое, запиши value ровно «{MISSING_MARK}».
- Если во входе два разных числа об одном свойстве, оставь оба. Третье число не выбирай и не вычисляй.
- Не добавляй класс точности, пылевлагозащиту, интерфейс, стандарт, цену, артикул,
  отрасль или материал, если этой строки нет во входе.
- seo_title и search_queries составляй только из name, manufacturer, specs и description.
  Не пересказывай description своими словами и не склеивай соседние слова.
- seo_description заполни дословными фразами из description и строками «имя: значение» из specs.
- commercial_block — одна или две дословные фразы из description о назначении прибора.
- Каждое число в этих полях должно уже встречаться во входе.
- Если область применения не названа, так и напиши.
  Не подставляй котельную, нефтегаз, пищевое производство и другие отрасли.
- missing_fields скопируй из входа дословно. Если список пуст, верни пустой массив.
"""


def build_messages(product: ProductInput) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _user_payload(product)},
    ]


def build_repair_messages(product: ProductInput, previous: str, problems: str) -> list[dict[str, str]]:
    instruction = (
        "Предыдущий JSON не принят. Исправь только перечисленные ошибки и верни новый JSON.\n"
        "Факты по-прежнему только из входа. Не добавляй числа и характеристики.\n"
        f"Ошибки: {problems}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _user_payload(product)},
        {"role": "assistant", "content": previous},
        {"role": "user", "content": instruction},
    ]


def _user_payload(product: ProductInput) -> str:
    payload = {
        "name": product.name,
        "manufacturer": product.manufacturer,
        "specs": product.specs,
        "description": product.description,
        "missing_fields": product.blank_fields(),
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"Собери карточку по этому входу. source_url в факты не входит и ниже не передан.\n{rendered}"
