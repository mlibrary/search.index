import pytest
import json
from api.databases import Record
from datetime import datetime, timedelta


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

    def test_more_information(self, solr_bib):
        subject = Record(solr_bib)
        expected = {"text": "Help", "url": "https://www.some_url"}
        assert subject.more_information[0].text == expected["text"]
        assert subject.more_information[0].url == expected["url"]

    def test_special_message_when_there_are_no_dates(self, solr_bib):
        start = datetime.now() - timedelta(days=1)
        end = datetime.now() + timedelta(days=1)
        date_format = "%Y-%m-%dT$H:%M:%SZ"
        solr_bib["special_message_start"] = datetime.strftime(start, date_format)
        solr_bib["special_message_end"] = datetime.strftime(end, date_format)
        subject = Record(solr_bib)
        assert subject.special_message[0].text == "Special Message"

    def test_special_message_does_not_show_when_out_of_date_range(self, solr_bib):
        start = datetime.now() - timedelta(days=2)
        end = datetime.now() - timedelta(days=1)
        date_format = "%Y-%m-%dT$H:%M:%SZ"
        solr_bib["special_message_start"] = datetime.strftime(start, date_format)
        solr_bib["special_message_end"] = datetime.strftime(end, date_format)
        subject = Record(solr_bib)
        assert subject.special_message == []

    def test_special_message_shows_dates_when_one_of_dates_indicates_its_in_range(
        self, solr_bib
    ):
        end = datetime.now() + timedelta(days=2)
        date_format = "%Y-%m-%dT$H:%M:%SZ"
        solr_bib["special_message_end"] = datetime.strftime(end, date_format)
        subject = Record(solr_bib)
        assert subject.special_message[0].text == "Special Message"

    def test_special_message_does_not_show_when_one_of_the_dates_is_out_of_range_range(
        self, solr_bib
    ):
        end = datetime.now() - timedelta(days=5)
        date_format = "%Y-%m-%dT$H:%M:%SZ"
        solr_bib["special_message_end"] = datetime.strftime(end, date_format)
        subject = Record(solr_bib)
        assert subject.special_message == []

    def test_academic_disciplines(self, solr_bib):
        expected = [
            {"list": ["Arts", "Music"]},
            {"list": ["General Information Sources", "Images and Videos"]},
            {
                "list": [
                    "General Information Sources",
                    "Images and Videos",
                    "Videos and Moving Image Media",
                ]
            },
        ]
        subject = Record(solr_bib)
        assert subject.academic_discipline == expected
