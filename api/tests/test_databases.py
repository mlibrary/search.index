import pytest
import json
from api.databases import Record


@pytest.fixture()
def solr_bib():
    bib = {}
    with open("tests/fixtures/record/databases_record.json") as data:
        bib = json.load(data)
    return bib["response"]["docs"][0]


# still need academic_discipline
class TestRecord:
    fields = {
        "id": "202644",
        # "format": ["database"],
        "type": ["Video"],
        "permalink": "https://ddm.dnd.lib.umich.edu/database/link/202644",
    }

    @pytest.mark.parametrize("field", fields.keys())
    def test_fields(self, field, solr_bib):
        subject = Record(solr_bib)
        assert getattr(subject, field) == self.fields[field]

    text_fields = {
        "title": "Music Online: Rock and Pop Music in Video",
        "description": "<p>Music Online: Rock and Pop Music in Video features documentary interviews, news archives, and performances to provide an overview of musical artists' lives and cultural impact.</p>",
        "access_type": "Authorized U-M users (+ guests in U-M Libraries)",
        "alt_title": "Rock and Pop Music in Video",
        "coverage": "Coverage",
        "special_message": "Special Message",
        "more_information": "Help!",
        "platform": "Music Online",
    }

    @pytest.mark.parametrize("field", text_fields.keys())
    def test_text_fields(self, field, solr_bib):
        subject = Record(solr_bib)
        assert getattr(subject, field)[0].text == self.text_fields[field]

    bool_fields = {
        "new": True,
        "trial": False,
    }

    @pytest.mark.parametrize("field", bool_fields.keys())
    def test_bool_fields(self, field, solr_bib):
        subject = Record(solr_bib)
        assert getattr(subject, field) is self.bool_fields[field]
