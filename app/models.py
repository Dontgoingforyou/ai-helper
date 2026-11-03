from pydantic import BaseModel, ConfigDict, Field

MISSING_MARK = "данных нет"

_FIELD_LABELS = (
    ("name", "название"),
    ("manufacturer", "производитель"),
    ("description", "описание"),
)


class ProductInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    manufacturer: str = ""
    specs: dict[str, str] = Field(default_factory=dict)
    description: str = ""
    source_url: str = ""

    def blank_fields(self) -> list[str]:
        labels = [label for attr, label in _FIELD_LABELS if is_blank(getattr(self, attr))]
        for key, value in self.specs.items():
            if is_blank(key) or is_blank(value):
                labels.append(f"характеристика: {key.strip() or 'без названия'}")
        return labels


class SpecRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    value: str


class ProductCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seo_title: str
    seo_description: str
    specs: list[SpecRow]
    search_queries: list[str]
    commercial_block: str
    missing_fields: list[str]


def is_blank(value: str) -> bool:
    return not value.strip()
