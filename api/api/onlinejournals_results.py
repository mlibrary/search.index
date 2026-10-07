import requests
from api.onlinejournals_record import Record
from api.results import BaseResults, FilterHandler, BaseFilter, SolrFilterQuery
from api.services import S


def get_onlinejournals_results(query_params: dict):
    parser_params = {
        "query": query_params["query"],
        "start": query_params["offset"],
        "rows": query_params["limit"],
        "fq[]": FilterQuery(query_params).query(),
        "sort": BaseResults.sort_map[query_params["sort"]],
    }
    response = requests.Session().get(
        f"{S.parser_url}/onlinejournals/search", params=parser_params
    )
    return Results(data=response.json(), query_params=query_params)


def get_onlinejournals_browse_academic_discipline(query_params: dict):
    parser_params = {
        "start": query_params["offset"],
        "rows": query_params["limit"],
    }

    response = requests.Session().get(
        f"{S.parser_url}/onlinejournals/browse_academic_discipline/{query_params['academic_discipline']}",
        params=parser_params,
    )
    return Results(
        data=response.json(),
        query_params=query_params,
        recommended_academic_discipline=query_params["academic_discipline"],
    )


filter_handler = FilterHandler(
    {
        "subject": "topicStr",
        "language": "language",
        "place_of_publication": "place_of_publication",
        "academic_discipline": "hlb3Str",
    }
)


class Results(BaseResults):
    fh = filter_handler

    def __init__(
        self, data: dict, query_params: dict, recommended_academic_discipline=None
    ):
        self.data = data
        self.query_params = query_params
        self.recommended_academic_discipline = recommended_academic_discipline

    @property
    def records(self):
        return [
            Record.create(
                data=data,
                recommended_academic_discipline=self.recommended_academic_discipline,
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
