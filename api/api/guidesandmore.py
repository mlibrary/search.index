from api.solr import SolrDocProcessor
from api.results import BaseResults, FilterHandler, BaseFilter, SolrFilterQuery
from api.services import S
import httpx
from datetime import date


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


filter_handler = FilterHandler({"page_type": "ssfield_page_type"})


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
        return self._get("id", kind="plain")

    @property
    def title(self):
        return self._get("title")

    @property
    def type(self):
        return self._get("type_name")

    @property
    def date(self):
        result = self._get("ssfield_date", kind="plain")
        if result:
            return date.strptime(result, "%B %d, %Y")

    @property
    def description(self):
        return self._get("teaser")

    @property
    def url(self):
        return self._get("url", kind="plain")

    def _get(self, field: str, kind: str = "text_field"):
        return self.solr_processor.get_kind(field, kind)
