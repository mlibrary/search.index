import re
from dataclasses import dataclass


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


def solr_escape(string):
    result = re.sub(r'([+\-&|!(){}\[\]\^"~*?:\\\/])', r"\\\1", string)
    return re.sub(r"\s+", "\\\\ ", result)


class BaseFilterQuery:
    fh = None

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


class Filter:
    def __init__(self, field: str, values: list):
        self.field = self.fh.filter_field_for(field)
        self.values = self.get_values(values)

    def get_values(self, values):
        result = []
        for x in range(0, len(values), 2):
            result.append(FilterValue(text=values[x], count=values[x + 1]))
        return result


@dataclass(frozen=True)
class FilterValue:
    text: str
    count: int
