from pydantic import AliasGenerator, BaseModel, ConfigDict, Field


def to_kebab_case(string: str) -> str:
    return string.replace("_", "-")


class TaggedCitation(BaseModel):
    content: str
    ris: list[str] = []
    meta: list[str] = []


class CSLLiteral(BaseModel):
    literal: str


class CSLDateParts(BaseModel):
    model_config = ConfigDict(
        # CSL has kebab case JSON keys
        alias_generator=AliasGenerator(
            serialization_alias=lambda field_name: to_kebab_case(field_name)
        )
    )
    date_parts: list[list] | None


class CSLName(BaseModel):
    family: str | None
    given: str | None


class CSL(BaseModel):
    model_config = ConfigDict(
        # CSL has kebab case JSON keys
        alias_generator=AliasGenerator(
            serialization_alias=lambda field_name: to_kebab_case(field_name)
        )
    )
    id: str
    type: str
    title: str
    author: list[CSLName | CSLLiteral] | None
    issued: CSLLiteral | None
    publisher: str | None
    isbn: list[str] | None = Field(serialization_alias="ISBN")
    issn: list[str] | None = Field(serialization_alias="ISSN")
    edition: str | None


class CatalogCSL(CSL):
    collection_title: str | None
    call_number: str | None
    publisher_place: str | None
    editor: list[CSLName | CSLLiteral] | None
    number: str | None


class ArticlesCSL(CSL):
    page: str | None
    container_title: str | None
    volume: str | None
    issue: str | None
    genre: str | None
    doi: str | None


class DatabasesCSL(BaseModel):
    id: str
    title: str


class GuidesandmoreCSL(BaseModel):
    id: str
    type: str
    title: str
    author: list[CSLName | CSLLiteral] | None
    issued: CSLDateParts | None
    url: str | None = Field(serialization_alias="URL")


class CatalogCitation(BaseModel):
    tagged: list[TaggedCitation]
    csl: CatalogCSL


class ArticlesCitation(BaseModel):
    tagged: list[TaggedCitation]
    csl: ArticlesCSL


class DatabasesCitation(BaseModel):
    tagged: list[TaggedCitation]
    csl: DatabasesCSL


class GuidesandmoreCitation(BaseModel):
    tagged: list[TaggedCitation]
    csl: GuidesandmoreCSL
