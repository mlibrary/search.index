from pydantic import BaseModel, ConfigDict, Field, AliasGenerator
from typing import Optional
import datetime
from enum import Enum


def to_kebab_case(string: str) -> str:
    return string.replace("_", "-")


############
# Holdings #
############


class AlmaDigitalItem(BaseModel):
    url: str
    delivery_description: str | None
    label: str | None
    public_note: str | None


class HathiTustItem(BaseModel):
    id: str
    url: str
    description: str | None
    source: str
    status: str


class ElectronicItem(BaseModel):
    url: str | None
    campuses: list[str]
    interface_name: str | None
    collection_name: str | None
    description: str | None
    public_note: str | None
    note: str | None
    is_available: bool


class LibLoc(BaseModel):
    library: str | None
    location: str | None


class PhysicalLocation(BaseModel):
    url: str | None
    text: str | None
    floor: Optional[str] = None
    code: LibLoc
    temporary: bool


class FindingAidItem(BaseModel):
    url: str | None
    call_number: str | None
    description: str | None


class FindingAids(BaseModel):
    physical_location: PhysicalLocation | None
    items: list[FindingAidItem]


class PhysicalItem(BaseModel):
    item_id: str
    barcode: str | None
    fulfillment_unit: str
    call_number: str | None
    process_type: str | None
    due_back_at: datetime.datetime | None
    item_policy: str | None
    description: str | None
    inventory_number: str | None
    material_type: str | None
    reservable: bool
    physical_location: PhysicalLocation | None
    url: str | None


class PhysicalHolding(BaseModel):
    holding_id: str | None
    call_number: str | None
    summary: list[str] | None
    public_note: list[str] | None
    physical_location: PhysicalLocation
    items: list[PhysicalItem]


class Holdings(BaseModel):
    hathi_trust_items: list[HathiTustItem]
    alma_digital_items: list[AlmaDigitalItem]
    electronic_items: list[ElectronicItem]
    finding_aids: FindingAids | None
    physical: list[PhysicalHolding]


class OnlinejournalsHoldings(BaseModel):
    electronic_items: list[ElectronicItem]


############
# Metadata #
############
class TextField(BaseModel):
    text: str
    tag: Optional[str] = None


class BareTextField(BaseModel):
    text: str


class PairedTextField(BaseModel):
    transliterated: Optional[TextField] = None
    original: TextField


class FieldedSearchField(BaseModel):
    field: str
    value: str


class SearchField(TextField):
    search: list[FieldedSearchField]


class BareSearchField(BareTextField):
    search: list[FieldedSearchField]


class PairedSearchField(BaseModel):
    transliterated: Optional[SearchField] = None
    original: SearchField


class BrowseField(SearchField):
    browse: str
    tag: Optional[str] = None


class PairedBrowseField(BaseModel):
    transliterated: Optional[BrowseField] = None
    original: BrowseField


class AcademicDiscipline(BaseModel):
    list: list[str]


class TaggedCitation(BaseModel):
    content: str
    ris: list[str]
    meta: list[str]


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


class CatalogCitation(BaseModel):
    tagged: list[TaggedCitation]
    csl: CatalogCSL


class ArticlesCitation(BaseModel):
    tagged: list[TaggedCitation]
    csl: ArticlesCSL


##########
# Record #
##########
class Record(BaseModel):
    id: str
    title: list[PairedTextField]
    format: list[str]
    availability: list[str]
    main_author: list[PairedBrowseField]
    preferred_title: list[PairedSearchField]
    related_title: list[PairedSearchField]
    other_titles: list[PairedSearchField]
    new_title: list[PairedSearchField]
    new_title_issn: list[TextField]
    previous_title: list[PairedSearchField]
    previous_title_issn: list[TextField]
    contributors: list[PairedBrowseField]
    published: list[PairedTextField]
    created: list[PairedTextField]
    distributed: list[PairedTextField]
    manufactured: list[PairedTextField]
    edition: list[PairedTextField]
    series: list[PairedTextField]
    series_statement: list[PairedTextField]
    biography_history: list[PairedTextField]
    summary: list[PairedTextField]
    in_collection: list[PairedSearchField]
    access: list[PairedTextField]
    finding_aids: list[PairedTextField]
    terms_of_use: list[PairedTextField]
    language: list[BareTextField]
    language_note: list[PairedTextField]
    performers: list[PairedTextField]
    date_place_of_event: list[PairedTextField]
    preferred_citation: list[PairedTextField]
    location_of_originals: list[PairedTextField]
    funding_information: list[PairedTextField]
    source_of_acquisition: list[PairedTextField]
    related_items: list[PairedTextField]
    numbering: list[PairedTextField]
    current_publication_frequency: list[PairedTextField]
    former_publication_frequency: list[PairedTextField]
    numbering_notes: list[PairedTextField]
    source_of_description_note: list[PairedTextField]
    copy_specific_note: list[PairedTextField]
    references: list[PairedTextField]
    copyright_status_information: list[PairedTextField]
    note: list[PairedTextField]
    arrangement: list[PairedTextField]
    copyright: list[PairedTextField]
    physical_description: list[PairedTextField]
    map_scale: list[PairedTextField]
    reproduction_note: list[PairedTextField]
    original_version_note: list[PairedTextField]
    playing_time: list[PairedTextField]
    media_format: list[PairedTextField]
    audience: list[PairedTextField]
    content_advice: list[PairedTextField]
    awards: list[PairedTextField]
    production_credits: list[PairedTextField]
    bibliography: list[PairedTextField]
    isbn: list[BareTextField]
    issn: list[BareTextField]
    call_number: list[BareTextField]
    oclc: list[BareTextField]
    gov_doc_number: list[BareTextField]
    publisher_number: list[PairedTextField]
    report_number: list[BareTextField]
    lc_subjects: list[BareTextField]
    remediated_lc_subjects: list[BareTextField]
    other_subjects: list[BareTextField]
    academic_discipline: list[AcademicDiscipline]
    contents: list[PairedTextField]
    bookplate: list[BareTextField]
    indexing_date: datetime.date
    holdings: Holdings
    marc: dict
    citation: CatalogCitation

    model_config = ConfigDict(populate_by_name=True)


class ResultRecord(BaseModel):
    id: str
    title: list[PairedTextField]
    # format: list[str]
    # availability: list[str]
    main_author: list[PairedBrowseField]
    # preferred_title: list[PairedSearchField]
    # related_title: list[PairedSearchField]
    # other_titles: list[PairedSearchField]
    # new_title: list[PairedSearchField]
    # new_title_issn: list[TextField]
    # previous_title: list[PairedSearchField]
    # previous_title_issn: list[TextField]
    # contributors: list[PairedBrowseField]
    published: list[PairedTextField]
    # created: list[PairedTextField]
    # distributed: list[PairedTextField]
    # manufactured: list[PairedTextField]
    # edition: list[PairedTextField]
    series: list[PairedTextField]
    # series_statement: list[PairedTextField]
    # biography_history: list[PairedTextField]
    # summary: list[PairedTextField]
    # in_collection: list[PairedSearchField]
    # access: list[PairedTextField]
    # finding_aids: list[PairedTextField]
    # terms_of_use: list[PairedTextField]
    # language: list[BareTextField]
    # language_note: list[PairedTextField]
    # performers: list[PairedTextField]
    # date_place_of_event: list[PairedTextField]
    # preferred_citation: list[PairedTextField]
    # location_of_originals: list[PairedTextField]
    # funding_information: list[PairedTextField]
    # source_of_acquisition: list[PairedTextField]
    # related_items: list[PairedTextField]
    # numbering: list[PairedTextField]
    # current_publication_frequency: list[PairedTextField]
    # former_publication_frequency: list[PairedTextField]
    # numbering_notes: list[PairedTextField]
    # source_of_description_note: list[PairedTextField]
    # copy_specific_note: list[PairedTextField]
    # references: list[PairedTextField]
    # copyright_status_information: list[PairedTextField]
    # note: list[PairedTextField]
    # arrangement: list[PairedTextField]
    # copyright: list[PairedTextField]
    # physical_description: list[PairedTextField]
    # map_scale: list[PairedTextField]
    # reproduction_note: list[PairedTextField]
    # original_version_note: list[PairedTextField]
    # playing_time: list[PairedTextField]
    # media_format: list[PairedTextField]
    # audience: list[PairedTextField]
    # content_advice: list[PairedTextField]
    # awards: list[PairedTextField]
    # production_credits: list[PairedTextField]
    # bibliography: list[PairedTextField]
    # isbn: list[BareTextField]
    # issn: list[BareTextField]
    # call_number: list[BareTextField]
    # oclc: list[BareTextField]
    # gov_doc_number: list[BareTextField]
    # publisher_number: list[PairedTextField]
    # report_number: list[BareTextField]
    # lc_subjects: list[BareTextField]
    # remediated_lc_subjects: list[BareTextField]
    # other_subjects: list[BareTextField]
    # academic_discipline: list[AcademicDiscipline]
    # contents: list[PairedTextField]
    # bookplate: list[BareTextField]
    # indexing_date: datetime.date
    holdings: Holdings
    # marc: dict
    citation: CatalogCitation

    model_config = ConfigDict(populate_by_name=True)


class OnlinejournalsResultRecord(ResultRecord):
    recommended_resource: bool | None
    holdings: OnlinejournalsHoldings


class OnlinejournalsRecord(Record):
    holdings: OnlinejournalsHoldings


class ArticleHolding(BaseModel):
    source: str
    availability: str
    url: str


class ArticlesRecord(BaseModel):
    id: str
    peer_reviewed: bool
    retraction_notice_url: Optional[str] = None
    title: list[BareTextField]
    abstract: list[BareTextField]
    author: list[BareSearchField]
    journal_title: list[BareTextField]
    issue: list[BareTextField]
    volume: list[BareTextField]
    pages: list[BareTextField]
    publication_date: list[BareTextField]
    publisher: list[BareTextField]
    genre: list[BareTextField]
    issn: list[BareTextField]
    eissn: list[BareTextField]
    isbn: list[BareTextField]
    eisbn: list[BareTextField]
    doi: list[BareTextField]
    oclc: list[BareTextField]
    pmid: list[BareTextField]
    language: list[BareTextField]
    subject: list[BareTextField]
    edition: list[BareTextField]
    holdings: list[ArticleHolding]
    citation: ArticlesCitation


class ArticlesResultRecord(BaseModel):
    id: str
    # formats: list[str]
    peer_reviewed: bool
    retraction_notice_url: Optional[str] = None
    title: list[BareTextField]
    abstract: list[BareTextField]
    author: list[BareSearchField]
    journal_title: list[BareTextField]
    issue: list[BareTextField]
    volume: list[BareTextField]
    pages: list[BareTextField]
    publication_date: list[BareTextField]
    publisher: list[BareTextField]
    # genre: list[BareTextField]
    # issn: list[BareTextField]
    # eissn: list[BareTextField]
    # isbn: list[BareTextField]
    # eisbn: list[BareTextField]
    # doi: list[BareTextField]
    # oclc: list[BareTextField]
    # pmid: list[BareTextField]
    # language: list[BareTextField]
    subject: list[BareTextField]
    edition: list[BareTextField]
    holdings: list[ArticleHolding]
    citation: ArticlesCitation


class Specialist(BaseModel):
    name: str
    uniqname: str
    title: Optional[str] = None
    email: str
    phone: Optional[str] = None
    academic_disciplines: list[str]


class SpecialistAcademicDiscipline(BaseModel):
    discipline: str
    count: int


class Specialists(BaseModel):
    specialists: list[Specialist]
    academic_disciplines: list[SpecialistAcademicDiscipline]


class FilterValue(BaseModel):
    text: str
    count: int


class Filter(BaseModel):
    field: str
    values: list[FilterValue]


class Results(BaseModel):
    records: list[ResultRecord]
    filters: list[Filter]
    limit: int
    offset: int
    total: int
    sort: str | None


class OnlinejournalsResults(Results):
    records: list[OnlinejournalsResultRecord]


class ArticlesResults(Results):
    records: list[ArticlesResultRecord]


class BrowseAcademicDiscipline(BaseModel):
    name: str
    count: int
    disciplines: list["BrowseAcademicDiscipline"] = []


BrowseAcademicDiscipline.model_rebuild()


class Sort(str, Enum):
    relevance = "relevance"
    date_asc = "date_asc"
    date_desc = "date_desc"
    author_asc = "author_asc"
    author_desc = "author_desc"
    date_added = "date_added"
    title_asc = "title_asc"
    title_desc = "title_desc"


class ArticlesSort(str, Enum):
    relevance = "relevance"
    date_asc = "date_asc"
    date_desc = "date_desc"


class Response(BaseModel):
    detail: str


class Response404(Response):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "detail": "Record not found",
                }
            ]
        }
    )
