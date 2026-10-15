from dataclasses import dataclass


@dataclass(frozen=True)
class SearchField:
    field: str
    value: str


@dataclass(frozen=True)
class LinkField:
    text: str
    url: str


@dataclass(frozen=True)
class TextField:
    text: str

    @property
    def citation_text(self):
        return self.text


@dataclass(frozen=True)
class FieldElement:
    text: str
    tag: str
    search: list[SearchField] | None = None
    browse: str | None = None

    @property
    def citation_text(self):
        return self.text

    def __str__(self):
        return self.text


@dataclass(frozen=True)
class PairedField:
    original: FieldElement | TextField
    transliterated: FieldElement | TextField | None = None

    @property
    def citation_text(self):
        if self.transliterated:
            return self.transliterated.text
        return self.original.text
