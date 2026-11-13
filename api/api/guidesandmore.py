import base64
from datetime import date
from types import MappingProxyType

import httpx

from api.clients.solr_client import WebsiteSolrClient
from api.csl import BaseCSL
from api.entities import TextField
from api.results import BaseFilter, BaseResults, FilterHandler, SolrFilterQuery
from api.services import S
from api.solr import SolrDocProcessor


async def record_for(id: str):
    data = await WebsiteSolrClient().get_record(decode_id(id))
    return Record(data)


async def get_results(query_params: dict):
    parser_params = {
        "query": query_params["query"],
        "start": query_params["offset"],
        "rows": query_params["limit"],
        "fq[]": FilterQuery(query_params).query(),
        "sort": Results.sort_map[query_params["sort"]],
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{S.parser_url}/guidesandmore/search", params=parser_params
        )
    return Results(data=response.json(), query_params=query_params)


filter_handler = FilterHandler({"type": "ssfield_page_type"})


def encode_id(id: str):
    return base64.urlsafe_b64encode(id.encode("ascii")).decode("ascii").split("=")[0]


def decode_id(id: str):
    id = id + "=" * (len(id) % 4)
    return base64.urlsafe_b64decode(id.encode("ascii")).decode("ascii")


class Results(BaseResults):
    sort_map = {
        "relevance": "score desc",
        "title_asc": "sort_title asc",
        "title_desc": "sort_title desc",
        "date_asc": "created asc",
        "date_desc": "created desc",
    }
    fh = filter_handler

    def __init__(self, data: dict, query_params: dict):
        self.data = data
        self.query_params = query_params

    @property
    def records(self):
        return [
            Record(
                data=data,
            )
            for data in self.data["response"]["docs"]
        ]

    @property
    def filters(self):
        facet_fields = self.data["facet_counts"]["facet_fields"]

        result = []
        for f in facet_fields.keys():
            if f in self.fh.facet_to_filter:
                result.append(Filter(field=f, values=facet_fields[f]))

        return result


class FilterQuery(SolrFilterQuery):
    fh = filter_handler

    def query(self):
        result = []
        for field in self.facets.keys():
            result.append(self.basic_facet(field, self.facets[field]))

        return result


class Filter(BaseFilter):
    fh = filter_handler


class Record:
    def __init__(self, data: dict):
        self.data = data
        self.solr_processor = SolrDocProcessor(data)

    @property
    def id(self):
        return encode_id(self._get("id", kind="plain"))

    @property
    def title(self):
        return self._get("title")

    @property
    def type(self):
        return self._get("ssfield_page_type")

    @property
    def published(self):
        result = self._get("ssfield_date", kind="plain")
        if result:
            return date.strptime(result, "%B %d, %Y")

    @property
    def description(self):
        teaser = self._get("teaser", kind="plain")
        if teaser:
            return [TextField(teaser.strip())]
        return []

    @property
    def author(self):
        raw_string = self._get("ssfield_author", "plain")
        if raw_string:
            return [
                TextField(author_string) for author_string in raw_string.split(", ")
            ]
        return []

    @property
    def url(self):
        return self._get("url", kind="plain")

    @property
    def citation(self):
        return Citation(self.data)

    def _get(self, field: str, kind: str = "text_field"):
        return self.solr_processor.get_kind(field, kind)


class TaggedCitation:
    TAG_MAPPING = (
        {"field": "id", "ris": ["ID"], "meta": ["id"]},
        {"field": "title", "ris": ["T1", "TI"], "meta": ["title"]},
        {"field": "url", "ris": ["L2", "UR"], "meta": ["fulltext_html_url"]},
    )

    def __init__(self, doc):
        self.doc = doc

    def to_list(self, tag_mapping=TAG_MAPPING):
        result = self._non_record_tags()
        for element in tag_mapping:
            contents = self.doc.get(element["field"])
            if contents is None:
                continue
            elif type(contents) is str:
                contents = [contents]
            for content in contents:
                result.append(
                    {
                        "content": content,
                        "ris": element.get("ris", []),
                        "meta": element.get("meta", []),
                    }
                )
        result += self._formatted_record_tags()
        result += self._end_record_tag()
        return result

    def _formatted_record_tags(self):
        result = []
        teaser = self.doc.get("teaser")
        if teaser:
            result.append({"content": teaser.strip(), "ris": ["N2"], "meta": []})

        publication_date = self.doc.get("ssfield_date")
        if publication_date:
            publication_date = date.strptime(publication_date, "%B %d, %Y")
            result.append(
                {
                    "content": publication_date.isoformat(),
                    "ris": ["Y1", "PY"],
                    "meta": ["date"],
                }
            )

        return result

    def _non_record_tags(self):
        return [
            {
                "content": "WEB",
                "ris": ["TY"],
                "meta": [],
            },
            {
                "content": "U-M Guides And More Search",
                "ris": ["DB"],
                "meta": [],
            },
            {
                "content": "University of Michigan Library",
                "ris": ["DP"],
                "meta": [],
            },
            {
                "content": date.today().isoformat(),
                "ris": ["Y2"],
                "meta": ["online_date"],
            },
        ]

    def _end_record_tag(self):
        return [
            {
                "content": "",
                "ris": ["ER"],
                "meta": [],
            },
        ]


class CSL(BaseCSL):
    TYPE_MAPPING = MappingProxyType(
        {
            "Research Guides": "webpage",
            "Blogs and Blog Posts": "post-weblog",
            "Online Exhibits": "webpage",
            "Specialty Sites": "webpage",
        }
    )

    def __init__(self, solr_doc):
        self.doc = solr_doc

    @property
    def id(self):
        return self.doc.get("id")

    @property
    def url(self):
        return self.doc.get("url")

    @property
    def title(self):
        return self.doc.get("title")

    @property
    def issued(self):
        """Creation date

        Using date parts as described here: https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html

        """
        result = self.doc.get("ssfield_date")
        if result:
            result = date.strptime(result, "%B %d, %Y")
            return {"date_parts": [[result.year, result.month, result.day]]}

    @property
    def author(self):
        author_string = self.doc.get("ssfield_author")
        if author_string:
            result = []
            for person in author_string.split(", "):
                parts = person.split(" ")
                family = parts.pop()
                given = " ".join(parts)
                result.append({"family": family, "given": given})
            return result

    def _formats(self):
        return [self.doc.get("ssfield_page_type")]


class Citation:
    def __init__(self, doc):
        self.doc = doc

    @property
    def tagged(self):
        return TaggedCitation(self.doc).to_list()

    @property
    def csl(self):
        return CSL(self.doc)
