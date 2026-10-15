from api.solr import SolrDocProcessor
from api.clients.solr_client import WebsiteSolrClient
import json
from api.entities import LinkField
from datetime import datetime


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
    def brief_description(self):
        return self._get("teaser")

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
        return Citation(self.data)

    def _get(self, field: str, kind: str = "text_field"):
        return self.solr_processor.get_kind(field, kind)


class TaggedCitation:
    TAG_MAPPING = [
        {"field": "id", "ris": ["ID"], "meta": ["id"]},
        {"field": "title", "ris": ["T1", "TI"], "meta": ["title"]},
        {"field": "ssfield_special_message", "ris": ["N2"], "meta": []},
        {"field": "permalink", "ris": ["L2"], "meta": []},
        {"field": "alt", "ris": ["J2"], "meta": []},
        {"field": "teaser", "ris": ["N2"], "meta": []},
        {"field": "body", "ris": ["N2"], "meta": []},
        {"field": "taxonomy_name", "ris": ["KY"], "meta": ["keywords"]},
    ]

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
        result += self._end_record_tag()
        return result

    def _non_record_tags(self):
        return [
            {
                "content": "DBASE",
                "ris": ["TY"],
                "meta": [],
            },
            {
                "content": "U-M Database Search",
                "ris": ["DB"],
                "meta": [],
            },
            {
                "content": "University of Michigan Library",
                "ris": ["DP"],
                "meta": [],
            },
            {
                "content": datetime.now().strftime("%Y-%m-%d"),
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


class CSL:
    def __init__(self, doc):
        self.doc = doc

    @property
    def id(self):
        return self.doc.get("id")

    @property
    def title(self):
        return self.doc.get("title")


class Citation:
    def __init__(self, doc):
        self.doc = doc

    @property
    def tagged(self):
        return TaggedCitation(self.doc).to_list()

    @property
    def csl(self):
        return CSL(self.doc)
