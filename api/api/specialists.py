import httpx
from api.services import S
from api.results import solr_escape
from api.catalog_results import FilterQuery as CatalogFilterQuery
from api.onlinejournals_results import FilterQuery as OnlinejournalsFilterQuery


class SpecialistFetcher:
    def __init__(self, config):
        self.name = config.get("name")
        self.ad_field = config.get("ad_field")
        self.fq_klass = config.get("fq_klass")

    async def get_specialists(self, query_params: dict):
        ad_response = await self.fetch_ad_response(query_params)
        top_academic_disciplines = self.get_top_academic_disciplines(ad_response.json())

        website_response = await self.fetch_website_solr_specialists(
            self.website_solr_query_params(top_academic_disciplines, query_params)
        )

        specialists = self.specialist_response(website_response.json())
        return {
            "specialists": specialists,
            "academic_disciplines": top_academic_disciplines,
        }

    async def fetch_ad_response(self, query_params: dict):
        fq = self.fq_klass(query_params)
        parser_params = {
            "query": query_params["query"],
            "fq[]": fq.query(),
        }
        async with httpx.AsyncClient() as client:
            return await client.get(
                f"{S.parser_url}/{self.name}/academic_disciplines", params=parser_params
            )

    def get_top_academic_disciplines(self, data: dict):
        term_threshold = 25
        term_counts = {}
        for doc in data["response"]["docs"]:
            if self.ad_field in doc:
                for term in doc[self.ad_field]:
                    if term in term_counts:
                        term_counts[term] += 1
                    else:
                        term_counts[term] = 1

        result = []
        for term in term_counts.keys():
            if term_counts[term] >= term_threshold:
                result.append(
                    {"discipline": solr_escape(term), "count": term_counts[term]}
                )
        return result

    def website_solr_query_params(self, top_academic_disciplines, query_params):
        fq_academic_disciplines = []
        for f in query_params.get("filters", []):
            term, value = f.split(":")
            if term == "academic_discipline":
                fq_academic_disciplines.append(solr_escape(value))

        fq = "+source:drupal-users +status:true"
        if fq_academic_disciplines:
            ad_str = " AND ".join(fq_academic_disciplines)
            fq += f" +(taxonomy_name:({ad_str}))"

        query = " OR ".join([tad["discipline"] for tad in top_academic_disciplines])

        bq = [
            f"taxonomy_name:({tad['discipline']})^{tad['count']}"
            for tad in top_academic_disciplines
        ]

        return {
            "mm": 1,
            "qf": "taxonomy_name",
            "pf": "taxonomy_name",
            "q": query,
            "fq": fq,
            "bq": bq,
            "rows": 10,
            "defType": "edismax",
            "fl": "*",
            "wt": "json",
        }

    def specialist_response(self, data):
        specialists = []
        for person in data["response"]["docs"]:
            specialists.append(
                {
                    "name": person["title"],
                    "uniqname": person["ssfield_uniqname"],
                    "title": person.get("job_title", None),
                    "email": person["email"][0],
                    "phone": person.get("ssfield_phone", None),
                    "academic_disciplines": person["taxonomy_name"],
                }
            )
        return specialists

    async def fetch_website_solr_specialists(self, params):
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{S.website_solr_url}/solr/www.lib/select", params=params
            )
        return resp


fetchers = {}
for fetcher in [
    {"name": "catalog", "ad_field": "hlb3Str", "fq_klass": CatalogFilterQuery},
    {
        "name": "onlinejournals",
        "ad_field": "hlb3Str",
        "fq_klass": OnlinejournalsFilterQuery,
    },
]:
    fetchers[fetcher["name"]] = SpecialistFetcher(fetcher)


async def get_specialists(datastore: str, query_params: dict):
    return await fetchers[datastore].get_specialists(query_params)
