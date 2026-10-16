import requests
from requests.auth import HTTPBasicAuth

import httpx
from api.services import S
from api.metrics import SOLR_HISTOGRAM
import fastapi_structured_logging

logger = fastapi_structured_logging.get_logger()


class NotFoundError(Exception):
    pass


class SolrClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.base_url = f"{S.solr_url}/solr/biblio"
        if S.solr_cloud_on:
            self.session.auth = HTTPBasicAuth(S.solr_user, S.solr_password)

    @SOLR_HISTOGRAM.labels(datastore="catalog").time()
    def get_record(self, id: str):
        params = {"q": f"id:{id}"}
        url = f"{self.base_url}/select"
        response = self.session.get(url, params=params)
        if response.json()["response"]["numFound"] == 0:
            raise NotFoundError()
        return response.json()["response"]["docs"][0]

    @SOLR_HISTOGRAM.labels(datastore="onlinejournals").time()
    def get_onlinejournals_record(self, id: str):
        params = {"q": f"id:{id} AND format:Serial AND location:ELEC"}
        url = f"{self.base_url}/select"
        response = self.session.get(url, params=params)
        if response.json()["response"]["numFound"] == 0:
            raise NotFoundError()
        return response.json()["response"]["docs"][0]

    def get_onlinejournals_academic_disciplines(self):
        params = {
            "q": "format:Serial AND location:ELEC",
            "facet": "on",
            "facet.field": ["hlb3Str", "hlb3Delimited"],
            "facet.limit": -1,
            "rows": 0,
        }
        url = f"{self.base_url}/select"
        response = self.session.get(url, params=params)
        return response.json()["facet_counts"]["facet_fields"]


class WebsiteSolrClient:
    def __init__(self) -> None:
        self.url = f"{S.website_solr_url}/solr/www.lib/select"

    async def get_databases_record(self, id: str):
        params = {"q": f"id:{id} AND type:database", "wt": "json"}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.url, params=params)
                response.raise_for_status()
                if response.json()["response"]["numFound"] == 0:
                    raise NotFoundError()
                return response.json()["response"]["docs"][0]
            except httpx.RequestError as e:
                logger.error("A request error occurred:", e)
