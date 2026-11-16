from pydantic import BaseModel


class TextField(BaseModel):
    text: str
    tag: str | None = None


class BareTextField(BaseModel):
    text: str


class LinkField(BareTextField):
    url: str


class PairedTextField(BaseModel):
    transliterated: TextField | None = None
    original: TextField


class FieldedSearchField(BaseModel):
    field: str
    value: str


class SearchField(TextField):
    search: list[FieldedSearchField]


class BareSearchField(BareTextField):
    search: list[FieldedSearchField]


class PairedSearchField(BaseModel):
    transliterated: SearchField | None = None
    original: SearchField


class BrowseField(SearchField):
    browse: str
    tag: str | None = None


class PairedBrowseField(BaseModel):
    transliterated: BrowseField | None = None
    original: BrowseField


class AcademicDiscipline(BaseModel):
    list: list[str]
