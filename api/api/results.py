import requests
import re
import asyncio
from dataclasses import dataclass
from api.record import Record, OnlinejournalsRecord
from api.services import S


async def get_catalog_results(query_params: dict):
    parser_params = {
        "query": query_params["query"],
        "start": query_params["offset"],
        "rows": query_params["limit"],
        "fq[]": CatalogFilterQuery(query_params).query(),
        "sort": BaseResults.sort_map[query_params["sort"]],
    }
    response = requests.Session().get(
        f"{S.parser_url}/catalog/search", params=parser_params
    )
    return await CatalogResults.create(data=response.json(), query_params=query_params)


def get_onlinejournals_results(query_params: dict):
    parser_params = {
        "query": query_params["query"],
        "start": query_params["offset"],
        "rows": query_params["limit"],
        "fq[]": OnlinejournalsFilterQuery(query_params).query(),
        "sort": BaseResults.sort_map[query_params["sort"]],
    }
    response = requests.Session().get(
        f"{S.parser_url}/onlinejournals/search", params=parser_params
    )
    return OnlinejournalsResults(data=response.json(), query_params=query_params)


def get_onlinejournals_browse_academic_discipline(query_params: dict):
    parser_params = {
        "start": query_params["offset"],
        "rows": query_params["limit"],
    }

    response = requests.Session().get(
        f"{S.parser_url}/onlinejournals/browse_academic_discipline/{query_params['academic_discipline']}",
        params=parser_params,
    )
    return OnlinejournalsResults(
        data=response.json(),
        query_params=query_params,
        recommended_academic_discipline=query_params["academic_discipline"],
    )


class FilterHandler:
    def __init__(self, filter_to_facet):
        self.filter_to_facet = filter_to_facet
        self.facet_to_filter = {}

        for filter_field in self.filter_to_facet.keys():
            self.facet_to_filter[self.filter_to_facet[filter_field]] = filter_field

    def filter_field_for(self, f):
        if f in self.facet_to_filter:
            return self.facet_to_filter[f]

    def facet_field_for(self, f):
        if f in self.filter_to_facet:
            return self.filter_to_facet[f]


catalog_filter_handler = FilterHandler(
    {
        "availability": "availability",
        "format": "format",
        "subject": "topicStr",
        "date_of_publication": "publishDateRange",
        "language": "language",
        "collection": "collection",
        "academic_discipline": "hlb3Str",
        "author": "authorStr",
        "place_of_publication": "place_of_publication",
        "region": "geographicStr",
        "location": "building",
        "library": "institution",
    }
)

onlinejournals_filter_handler = FilterHandler(
    {
        "subject": "topicStr",
        "language": "language",
        "place_of_publication": "place_of_publication",
        "academic_discipline": "hlb3Str",
    }
)


class BaseResults:
    sort_map = {
        "relevance": "score desc",
        "date_asc": "publishDateTrie asc",
        "date_desc": "publishDateTrie desc",
        "author_asc": "authorSort asc",
        "author_desc": "authorSort desc",
        "date_added": "cat_date desc",
        "title_asc": "titleSort asc",
        "title_desc": "titleSort desc",
    }
    inverse_sort_map = {v: k for k, v in sort_map.items()}

    def __init__(self, data: dict, query_params: dict, records: list = []):
        self.data = data
        self.query_params = query_params
        self.records = records

    @property
    def total(self):
        return self.data["response"]["numFound"]

    @property
    def limit(self):
        return self.data["responseHeader"]["params"]["rows"]

    @property
    def offset(self):
        return self.data["response"]["start"]

    @property
    def sort(self):
        response_sort = self.data["responseHeader"]["params"]["sort"]
        if response_sort in self.inverse_sort_map:
            return self.inverse_sort_map[response_sort]


class CatalogResults(BaseResults):
    @classmethod
    async def create(cls, data: dict, query_params: dict):

        async def fetch_record(data):
            return await Record.create(
                data, ht_search_only=query_params["ht_search_only"]
            )

        records = await asyncio.gather(*map(fetch_record, data["response"]["docs"]))
        return CatalogResults(data=data, query_params=query_params, records=records)

    fh = catalog_filter_handler

    @property
    def filters(self):
        facet_fields = self.data["facet_counts"]["facet_fields"]

        result = []
        for f in facet_fields.keys():
            if f in self.fh.facet_to_filter:
                if f == "availability":
                    r = AvailabilityFilter(
                        field=f,
                        values=facet_fields[f],
                        ht_search_only=self.query_params["ht_search_only"],
                    )
                else:
                    r = CatalogFilter(field=f, values=facet_fields[f])
                result.append(r)

        return result


class OnlinejournalsResults(BaseResults):
    fh = onlinejournals_filter_handler

    def __init__(
        self, data: dict, query_params: dict, recommended_academic_discipline=None
    ):
        self.data = data
        self.query_params = query_params
        self.recommended_academic_discipline = recommended_academic_discipline

    @property
    def records(self):
        return [
            OnlinejournalsRecord.create(
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
                result.append(OnlinejournalsFilter(field=f, values=facet_fields[f]))

        return result


def solr_escape(string):
    result = re.sub(r'([+\-&|!(){}\[\]\^"~*?:\\\/])', r"\\\1", string)
    return re.sub(r"\s+", "\\\\ ", result)


class BaseFilterQuery:
    fh = catalog_filter_handler

    def __init__(self, data: dict):
        self.data = data
        self.facets = {}
        for f in data["filters"]:
            field, value = f.split(":", 1)
            facet = (
                self.fh.filter_to_facet[field]
                if field in self.fh.filter_to_facet
                else None
            )
            # if facet isn't in the facet list skip it
            if not facet:
                continue

            if facet not in self.facets:
                self.facets[facet] = []
            self.facets[facet].append(value)

        self.filter_param = [f.split(":", 1) for f in data["filters"]]


class SolrFilterQuery(BaseFilterQuery):
    def basic_facet(self, field, values):
        escaped = map(lambda v: solr_escape(v), values)
        value = " AND ".join(escaped)
        return f"{field}:({value})"


class OnlinejournalsFilterQuery(SolrFilterQuery):
    fh = onlinejournals_filter_handler

    def query(self):
        result = []
        for field in self.facets.keys():
            result.append(self.basic_facet(field, self.facets[field]))

        return result


class CatalogFilterQuery(SolrFilterQuery):
    fh = catalog_filter_handler

    def query(self):
        result = []
        for field in self.facets.keys():
            match field:
                case "availability":
                    next
                case "institution":
                    next
                case _:
                    result.append(self.basic_facet(field, self.facets[field]))

        if self.institution():
            result.append(self.institution())
        result.append(self.availability())
        return result

    def institution(self):
        institution_map = {
            "aa": "UM Ann Arbor Libraries",
            "flint": "Flint Thompson Library",
            "clements": "William L. Clements Library",
            "bentley": "Bentley Historical Library",
            "all": "all",
        }
        if "institution" in self.facets:
            filtered = filter(
                lambda v: v in institution_map.keys(), self.facets["institution"]
            )
            mapped = list(map(lambda v: institution_map[v], filtered))
            if "all" in mapped or not mapped:
                return None
            return self.basic_facet("institution", mapped)

    def availability(self):
        full_text = {
            "Available Online": "hathi_trust_full_text_or_electronic_holding",
            "Hathi Trust": "hathi_trust_full_text",
            "Physical": "physical",
        }
        search_only = {
            "Available Online": "hathi_trust_or_electronic_holding",
            "Hathi Trust": "hathi_trust",
            "Physical": "physical",
        }

        options = search_only if self.data["ht_search_only"] else full_text
        result = f"availability:physical OR availability:{options['Available Online']}"
        if "availability" in self.facets:
            filtered = filter(
                lambda v: v in options.keys(), self.facets["availability"]
            )
            mapped = list(map(lambda v: options[v], filtered))

            if len(mapped) > 0:
                result = " AND ".join(mapped)
                result = f"availability:({result})"

        return f"({result})"


# problems with filter data.
# 1. the fields aren't the correct names
# 2. location filter has the wrong name (time for the other api???)
# 3. some of them (just search only?) are empty
# 4. availability has some special rules
class Filter:
    def __init__(self, field: str, values: list):
        self.field = self.fh.filter_field_for(field)
        self.values = self.get_values(values)

    def get_values(self, values):
        result = []
        for x in range(0, len(values), 2):
            result.append(FilterValue(text=values[x], count=values[x + 1]))
        return result


class OnlinejournalsFilter(Filter):
    fh = onlinejournals_filter_handler


class CatalogFilter(Filter):
    fh = catalog_filter_handler


class AvailabilityFilter(CatalogFilter):
    def __init__(self, field: str, values: list, ht_search_only: bool):
        self.ht_search_only = ht_search_only
        self.field = self.fh.filter_field_for(field)
        basic_values = self.get_values(values)
        self.values = self.get_availability_values(basic_values, ht_search_only)

    def get_availability_values(self, basic_values, ht_search_only):
        full_text = {
            "hathi_trust_full_text_or_electronic_holding": "Available Online",
            "hathi_trust_full_text": "Hathi Trust",
            "physical": "Physical",
        }
        search_only = {
            "hathi_trust_or_electronic_holding": "Available Online",
            "hathi_trust": "Hathi Trust",
            "physical": "Physical",
        }

        options = search_only if self.ht_search_only else full_text
        result = []
        for bv in basic_values:
            if bv.text in options:
                fv = FilterValue(text=options[bv.text], count=bv.count)
                result.append(fv)

        return result


@dataclass(frozen=True)
class FilterValue:
    text: str
    count: int
