from pydantic import BaseModel, ConfigDict, Field, AliasGenerator
from typing import Optional


def to_kebab_case(string: str) -> str:
    return string.replace("_", "-")


class TaggedCitation(BaseModel):
    content: str
    ris: list[str] = []
    meta: list[str] = []


class CSLLiteral(BaseModel):
    literal: str


class CSLName(BaseModel):
    family: Optional[str]
    given: Optional[str]


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
    author: Optional[list[CSLName | CSLLiteral]]
    issued: Optional[CSLLiteral]
    publisher: Optional[str]
    isbn: Optional[list[str]] = Field(serialization_alias="ISBN")
    issn: Optional[list[str]] = Field(serialization_alias="ISSN")
    edition: Optional[str]


class CatalogCSL(CSL):
    collection_title: Optional[str]
    call_number: Optional[str]
    publisher_place: Optional[str]
    editor: Optional[list[CSLName | CSLLiteral]]
    number: Optional[str]


class ArticlesCSL(CSL):
    page: Optional[str]
    container_title: Optional[str]
    volume: Optional[str]
    issue: Optional[str]
    genre: Optional[str]
    doi: Optional[str]


class DatabasesCSL(BaseModel):
    id: str
    title: str


class CatalogCitation(BaseModel):
    tagged: list[TaggedCitation]
    csl: CatalogCSL


class ArticlesCitation(BaseModel):
    tagged: list[TaggedCitation]
    csl: ArticlesCSL


class DatabasesCitation(BaseModel):
    tagged: list[TaggedCitation]
    csl: DatabasesCSL
