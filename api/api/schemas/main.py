from pydantic import BaseModel, ConfigDict
from typing import Optional
from .holdings import Holdings, OnlinejournalsHoldings, ArticleHolding
from .metadata import (
    TextField,
    PairedTextField,
    PairedSearchField,
    PairedBrowseField,
    BareTextField,
    BareSearchField,
    AcademicDiscipline,
    LinkField,
)
from .citation import (
    DatabasesCitation,
    ArticlesCitation,
    CatalogCitation,
)
import datetime
from enum import Enum


##########
# Record #
##########
class Record(BaseModel):
    id: str
    title: list[PairedTextField]
    format: list[str] = []
    availability: list[str] = []
    main_author: list[PairedBrowseField] = []
    preferred_title: list[PairedSearchField] = []
    related_title: list[PairedSearchField] = []
    other_titles: list[PairedSearchField] = []
    new_title: list[PairedSearchField] = []
    new_title_issn: list[TextField] = []
    previous_title: list[PairedSearchField] = []
    previous_title_issn: list[TextField] = []
    contributors: list[PairedBrowseField] = []
    published: list[PairedTextField] = []
    created: list[PairedTextField] = []
    distributed: list[PairedTextField] = []
    manufactured: list[PairedTextField] = []
    edition: list[PairedTextField] = []
    series: list[PairedTextField] = []
    series_statement: list[PairedTextField] = []
    biography_history: list[PairedTextField] = []
    summary: list[PairedTextField] = []
    in_collection: list[PairedSearchField] = []
    access: list[PairedTextField] = []
    finding_aids: list[PairedTextField] = []
    terms_of_use: list[PairedTextField] = []
    language: list[BareTextField] = []
    language_note: list[PairedTextField] = []
    performers: list[PairedTextField] = []
    date_place_of_event: list[PairedTextField] = []
    preferred_citation: list[PairedTextField] = []
    location_of_originals: list[PairedTextField] = []
    funding_information: list[PairedTextField] = []
    source_of_acquisition: list[PairedTextField] = []
    related_items: list[PairedTextField] = []
    numbering: list[PairedTextField] = []
    current_publication_frequency: list[PairedTextField] = []
    former_publication_frequency: list[PairedTextField] = []
    numbering_notes: list[PairedTextField] = []
    source_of_description_note: list[PairedTextField] = []
    copy_specific_note: list[PairedTextField] = []
    references: list[PairedTextField] = []
    copyright_status_information: list[PairedTextField] = []
    note: list[PairedTextField] = []
    arrangement: list[PairedTextField] = []
    copyright: list[PairedTextField] = []
    physical_description: list[PairedTextField] = []
    map_scale: list[PairedTextField] = []
    reproduction_note: list[PairedTextField] = []
    original_version_note: list[PairedTextField] = []
    playing_time: list[PairedTextField] = []
    media_format: list[PairedTextField] = []
    audience: list[PairedTextField] = []
    content_advice: list[PairedTextField] = []
    awards: list[PairedTextField] = []
    production_credits: list[PairedTextField] = []
    bibliography: list[PairedTextField] = []
    isbn: list[BareTextField] = []
    issn: list[BareTextField] = []
    call_number: list[BareTextField] = []
    oclc: list[BareTextField] = []
    gov_doc_number: list[BareTextField] = []
    publisher_number: list[PairedTextField] = []
    report_number: list[BareTextField] = []
    lc_subjects: list[BareTextField] = []
    remediated_lc_subjects: list[BareTextField] = []
    other_subjects: list[BareTextField] = []
    academic_discipline: list[AcademicDiscipline] = []
    contents: list[PairedTextField] = []
    bookplate: list[BareTextField] = []
    indexing_date: datetime.date
    holdings: Holdings
    marc: dict
    citation: CatalogCitation

    model_config = ConfigDict(populate_by_name=True)


class ResultRecord(BaseModel):
    id: str
    title: list[PairedTextField]
    # format: list[str] = []
    # availability: list[str] = []
    main_author: list[PairedBrowseField] = []
    # preferred_title: list[PairedSearchField] = []
    # related_title: list[PairedSearchField] = []
    # other_titles: list[PairedSearchField] = []
    # new_title: list[PairedSearchField] = []
    # new_title_issn: list[TextField] = []
    # previous_title: list[PairedSearchField] = []
    # previous_title_issn: list[TextField] = []
    # contributors: list[PairedBrowseField] = []
    published: list[PairedTextField] = []
    # created: list[PairedTextField] = []
    # distributed: list[PairedTextField] = []
    # manufactured: list[PairedTextField] = []
    # edition: list[PairedTextField] = []
    series: list[PairedTextField] = []
    # series_statement: list[PairedTextField] = []
    # biography_history: list[PairedTextField] = []
    # summary: list[PairedTextField] = []
    # in_collection: list[PairedSearchField] = []
    # access: list[PairedTextField] = []
    # finding_aids: list[PairedTextField] = []
    # terms_of_use: list[PairedTextField] = []
    # language: list[BareTextField] = []
    # language_note: list[PairedTextField] = []
    # performers: list[PairedTextField] = []
    # date_place_of_event: list[PairedTextField] = []
    # preferred_citation: list[PairedTextField] = []
    # location_of_originals: list[PairedTextField] = []
    # funding_information: list[PairedTextField] = []
    # source_of_acquisition: list[PairedTextField] = []
    # related_items: list[PairedTextField] = []
    # numbering: list[PairedTextField] = []
    # current_publication_frequency: list[PairedTextField] = []
    # former_publication_frequency: list[PairedTextField] = []
    # numbering_notes: list[PairedTextField] = []
    # source_of_description_note: list[PairedTextField] = []
    # copy_specific_note: list[PairedTextField] = []
    # references: list[PairedTextField] = []
    # copyright_status_information: list[PairedTextField] = []
    # note: list[PairedTextField] = []
    # arrangement: list[PairedTextField] = []
    # copyright: list[PairedTextField] = []
    # physical_description: list[PairedTextField] = []
    # map_scale: list[PairedTextField] = []
    # reproduction_note: list[PairedTextField] = []
    # original_version_note: list[PairedTextField] = []
    # playing_time: list[PairedTextField] = []
    # media_format: list[PairedTextField] = []
    # audience: list[PairedTextField] = []
    # content_advice: list[PairedTextField] = []
    # awards: list[PairedTextField] = []
    # production_credits: list[PairedTextField] = []
    # bibliography: list[PairedTextField] = []
    # isbn: list[BareTextField] = []
    # issn: list[BareTextField] = []
    # call_number: list[BareTextField] = []
    # oclc: list[BareTextField] = []
    # gov_doc_number: list[BareTextField] = []
    # publisher_number: list[PairedTextField] = []
    # report_number: list[BareTextField] = []
    # lc_subjects: list[BareTextField] = []
    # remediated_lc_subjects: list[BareTextField] = []
    # other_subjects: list[BareTextField] = []
    # academic_discipline: list[AcademicDiscipline] = []
    # contents: list[PairedTextField] = []
    # bookplate: list[BareTextField] = []
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


class ArticlesRecord(BaseModel):
    id: str
    peer_reviewed: bool
    retraction_notice_url: Optional[str] = None
    title: list[BareTextField] = []
    abstract: list[BareTextField] = []
    author: list[BareSearchField] = []
    journal_title: list[BareTextField] = []
    issue: list[BareTextField] = []
    volume: list[BareTextField] = []
    pages: list[BareTextField] = []
    publication_date: list[BareTextField] = []
    publisher: list[BareTextField] = []
    genre: list[BareTextField] = []
    issn: list[BareTextField] = []
    eissn: list[BareTextField] = []
    isbn: list[BareTextField] = []
    eisbn: list[BareTextField] = []
    doi: list[BareTextField] = []
    oclc: list[BareTextField] = []
    pmid: list[BareTextField] = []
    language: list[BareTextField] = []
    subject: list[BareTextField] = []
    edition: list[BareTextField] = []
    holdings: list[ArticleHolding]
    citation: ArticlesCitation


class ArticlesResultRecord(BaseModel):
    id: str
    # formats: list[str]
    peer_reviewed: bool
    retraction_notice_url: Optional[str] = None
    title: list[BareTextField] = []
    abstract: list[BareTextField] = []
    author: list[BareSearchField] = []
    journal_title: list[BareTextField] = []
    issue: list[BareTextField] = []
    volume: list[BareTextField] = []
    pages: list[BareTextField] = []
    publication_date: list[BareTextField] = []
    publisher: list[BareTextField] = []
    # genre: list[BareTextField] = []
    # issn: list[BareTextField] = []
    # eissn: list[BareTextField] = []
    # isbn: list[BareTextField] = []
    # eisbn: list[BareTextField] = []
    # doi: list[BareTextField] = []
    # oclc: list[BareTextField] = []
    # pmid: list[BareTextField] = []
    # language: list[BareTextField] = []
    subject: list[BareTextField] = []
    edition: list[BareTextField] = []
    holdings: list[ArticleHolding]
    citation: ArticlesCitation


class DatabasesRecord(BaseModel):
    id: str
    title: list[BareTextField]
    description: list[BareTextField] = []
    brief_description: list[BareTextField] = []
    type: list[str] = []
    access_type: list[BareTextField] = []
    alt_title: list[BareTextField] = []
    coverage: list[BareTextField] = []
    special_message: list[BareTextField] = []
    more_information: list[LinkField] = []
    platform: list[BareTextField] = []
    new: bool = False
    trial: bool = False
    permalink: str
    academic_discipline: list[AcademicDiscipline] = []
    citation: DatabasesCitation


class DatabasesResultRecord(BaseModel):
    id: str
    title: list[BareTextField]
    # description: list[BareTextField] = []
    brief_description: list[BareTextField] = []
    type: list[str] = []
    access_type: list[BareTextField] = []
    # alt_title: list[BareTextField] = []
    coverage: list[BareTextField] = []
    special_message: list[BareTextField] = []
    # more_information: list[LinkField] = []
    # platform: list[BareTextField] = []
    new: bool = False
    trial: bool = False
    permalink: str
    # academic_discipline: list[AcademicDiscipline] = []
    citation: DatabasesCitation


###############
# Specialists #
###############
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


###########
# Results #
###########


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


class DatabasesResults(Results):
    records: list[DatabasesResultRecord]


###########
# Browse  #
###########


class BrowseAcademicDiscipline(BaseModel):
    name: str
    count: int
    disciplines: list["BrowseAcademicDiscipline"] = []


BrowseAcademicDiscipline.model_rebuild()

###########
# Sorts   #
###########


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


class DatabasesSort(str, Enum):
    relevance = "relevance"
    title_asc = "title_asc"
    title_desc = "title_desc"


#############
# Responses #
#############


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
