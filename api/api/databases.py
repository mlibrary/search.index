from api.solr import SolrDocProcessor
from api.clients.solr_client import WebsiteSolrClient
import json
from api.entities import LinkField


async def record_for(id: str):
    data = await WebsiteSolrClient().get_databases_record(id)
    return Record(data)


class Record:
    def __init__(
        self,
        data: dict,
        recommended_academic_discipline=None,
    ):
        self.data = data
        self.solr_processor = SolrDocProcessor(data)
        self.recommended_academic_discipline = recommended_academic_discipline

    @property
    def id(self):
        return self._get("id", kind="plain")

    @property
    def title(self):
        return self._get("title")

    # this is probably wrong
    @property
    def description(self):
        return self._get("body")

    @property
    def type(self):
        return self._get("category", kind="list")

    @property
    def access_type(self):
        return self._get("smfield_access_type")

    @property
    def alt_title(self):
        return self._get("alt")

    @property
    def coverage(self):
        return self._get("smfield_coverage")

    @property
    def special_message(self):
        return self._get("ssfield_special_message")

    @property
    def more_information(self):
        result = []
        for link in self._get("smfield_help_links", kind="list"):
            link = json.loads(link)
            result.append(LinkField(text=link["text"], url=link["href"]))
        return result

    @property
    def platform(self):
        return self._get("smfield_platform")

    @property
    def new(self):
        return bool(self._get("new", kind="plain"))

    @property
    def trial(self):
        return bool(self._get("bsfield_trial", kind="plain"))

    @property
    def permalink(self):
        return self._get("ssfield_permalink", kind="plain")

    @property
    def academic_discipline(self):
        return self._get("smfield_taxonomy_delimited", kind="academic_discipline")

    @property
    def citation(self):
        return {"tagged": [], "csl": {}}

    def _get(self, field: str, kind: str = "text_field"):
        return self.solr_processor.get_kind(field, kind)
