from pydantic import BaseModel, Field


class FormField(BaseModel):
    id: str | None = None
    name: str | None = None
    index: int | None = None
    label: str | None = None
    placeholder: str | None = None
    type: str | None = "text"
    autocomplete: str | None = None
    ariaLabel: str | None = None
    title: str | None = None
    pattern: str | None = None
    options: list[dict] = Field(default_factory=list)


class MapIn(BaseModel):
    fields: list[FormField] = Field(max_length=200)
