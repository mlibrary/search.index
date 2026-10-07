import requests
import asyncio
from api.results import (
    FilterHandler,
    FilterValue,
    BaseResults,
    SolrFilterQuery,
    Filter,
)
from api.catalog_record import Record
from api.services import S


async def get_results(query_params: dict):
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
