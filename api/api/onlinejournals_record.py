from __future__ import annotations
import re
import pymarc
import io

# import string
import json
import fastapi_structured_logging
from api.clients.solr_client import SolrClient
from api.solr import SolrDocProcessor

# from api.marc import Processor, FieldRuleset, TRIM_CHARS
from api.holdings import (
    electronic_items,
    EmptyHoldings,
)  # get_alma_loans, Holdings, EmptyHoldings, OnlinejournalsHoldings
# from api.csl import BaseCSL
# from datetime import datetime

from api.catalog_record import BaseRecord, Citation

logger = fastapi_structured_logging.get_logger()


def record_for(id: str) -> Record:
    data = SolrClient().get_onlinejournals_record(id)
    return Record.create(data)


class Record(BaseRecord):
    @classmethod
    def create(cls, data: dict, recommended_academic_discipline=None):
        holdings_data = json.loads(data.get("hol"))
        holdings = Holdings(holdings_data)
        return Record(
            data=data,
            holdings=holdings,
            recommended_academic_discipline=recommended_academic_discipline,
        )

    def __init__(
        self,
        data: dict,
        holdings=EmptyHoldings(),
        recommended_academic_discipline=None,
    ):
        self.data = data
        BaseRecord.__init__(self, data)
        self.record = pymarc.parse_xml_to_array(io.StringIO(data["fullrecord"]))[0]
        self.recommended_academic_discipline = recommended_academic_discipline
        self.holdings = holdings

    @property
    def recommended_resource(self):
        if self.recommended_academic_discipline:
            normalized_ad = re.sub(
                r"\s+", "_", self.recommended_academic_discipline
            ).lower()
            result = SolrDocProcessor(self.data).get(f"{normalized_ad}_bb")
            return bool(result)

    @property
    def citation(self):
        return Citation(marc_record=self.record, base_record=self, solr_doc=self.data)


class Holdings:
    def __init__(self, holdings_data: list):
        self.data = holdings_data

    @property
    def electronic_items(self):
        return electronic_items(self.data)
