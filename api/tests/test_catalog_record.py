import pytest
import json
import pymarc
import string
import responses
from datetime import datetime
from dataclasses import dataclass, field
from api.catalog_record import Record, MARC, SolrDoc, TaggedCitation, CSL, BaseRecord
from api.entities import FieldElement, PairedField
from api.marc import (
    FieldRuleset,
)
from api.services import S
from dataclasses import asdict


@pytest.fixture()
def solr_bib():
    bib = {}
    with open("tests/fixtures/land_birds_solr.json") as data:
        bib = json.load(data)
    return bib["response"]["docs"][0]


@pytest.fixture()
def api_output():
    with open("tests/fixtures/land_birds.json") as data:
        return json.load(data)


@pytest.fixture
def loan_data():
    return json.loads('{"total_record_count": 0}')


def serialize(my_list: list):
    if len(my_list) > 0 and (
        isinstance(my_list[0], dict) or isinstance(my_list[0], str)
    ):
        return my_list
    return [asdict(element) for element in my_list]


class TestRecord:
    fields = [
        "format",
        "language",
        "isbn",
        "call_number",
        "oclc",
        "lc_subjects",
        "academic_discipline",
        "availability",
    ]

    @pytest.mark.parametrize("field", fields)
    def test_fields_success(self, field, solr_bib, api_output):
        subject = Record(solr_bib)

        assert serialize(getattr(subject, field)) == api_output[field]

    def test_title_with_only_default_script(self, solr_bib):
        solr_bib["title_display"].pop(1)
        subject = Record(solr_bib)
        expected = serialize(subject.title)[0]["original"]["text"]
        assert expected == solr_bib["title_display"][0]

    def test_title_with_no_title(self, solr_bib):
        solr_bib.pop("title_display")
        subject = Record(solr_bib)
        assert serialize(subject.title) == []

    def test_language_with_no_lanugages(self, solr_bib):
        solr_bib.pop("language")
        subject = Record(solr_bib)
        assert serialize(subject.language) == []

    def test_formats_with_no_formats(self, solr_bib):
        solr_bib.pop("format")
        subject = Record(solr_bib)
        assert serialize(subject.format) == []

    def test_main_author_no_vernacular(self, solr_bib):
        solr_bib["main_author"].pop(1)
        solr_bib["main_author_display"].pop(1)
        subject = Record(solr_bib)
        assert len(subject.main_author) == 1

    def test_with_no_main_author(self, solr_bib):
        solr_bib.pop("main_author_display")
        subject = Record(solr_bib)
        assert serialize(subject.main_author) == []

    def test_with_no_academic_disciplines(self, solr_bib):
        solr_bib.pop("hlb3Delimited")
        subject = Record(solr_bib)
        assert serialize(subject.academic_discipline) == []

    def test_marc(self, solr_bib):
        record = pymarc.record.Record()
        field = pymarc.Field(
            tag="245",
            indicators=pymarc.Indicators("0", "1"),
            subfields=[
                pymarc.Subfield(code="a", value="The pragmatic programmer : "),
                pymarc.Subfield(code="b", value="from journeyman to master /"),
                pymarc.Subfield(code="c", value="Andrew Hunt, David Thomas."),
            ],
        )

        record.add_field(field)

        xml = pymarc.record_to_xml(record)
        solr_bib["fullrecord"] = xml.decode("UTF8")

        subject = Record(solr_bib)
        assert (subject.marc) == json.loads(record.as_json())

    @responses.activate
    def test_holdings_is_not_None(self, solr_bib, loan_data):
        mms_id = solr_bib["id"]
        responses.get(
            f"{S.alma_api_url}/bibs/{mms_id}/loans?limit=100",
            json=loan_data,
            status=200,
        )
        subject = Record(solr_bib)
        assert subject.holdings is not None

    @responses.activate
    def test_physical_holdings_is_not_None(self, solr_bib, loan_data):
        mms_id = solr_bib["id"]
        responses.get(
            f"{S.alma_api_url}/bibs/{mms_id}/loans?limit=100",
            json=loan_data,
            status=200,
        )
        subject = Record(solr_bib)
        assert subject.holdings.physical is not None


class TestSolrDoc:
    def test_title(self, solr_bib):
        subject = SolrDoc(solr_bib)
        assert serialize(subject.title) == [
            {
                "transliterated": {
                    "text": "Sanʼya no tori = Concise field guide to land birds / kaisetsu Saeki Akimitsu ; e Taniguchi Takashi."
                },
                "original": {
                    "text": "山野の鳥 = Concise field guide to land birds / 解說佐伯彰光 ; 絵谷口高司."
                },
            }
        ]

    def test_issn(self, solr_bib):
        solr_bib["issn"] = ["some_issn"]
        subject = SolrDoc(solr_bib)
        assert serialize(subject.issn) == [{"text": "some_issn"}]

    def test_gov_doc_number(self, solr_bib):
        solr_bib["sudoc"] = ["some_gov_doc_number"]
        subject = SolrDoc(solr_bib)
        assert serialize(subject.gov_doc_number) == [{"text": "some_gov_doc_number"}]

    def test_report_number(self, solr_bib):
        solr_bib["rptnum"] = ["some_report_number"]
        subject = SolrDoc(solr_bib)
        assert serialize(subject.report_number) == [{"text": "some_report_number"}]

    def test_remediated_lc_subjects(self, solr_bib):
        solr_bib["remediated_lc_subject_display"] = ["some -- subject"]
        subject = SolrDoc(solr_bib)
        assert serialize(subject.remediated_lc_subjects) == [
            {"text": "some -- subject"}
        ]

    def test_other_subjects(self, solr_bib):
        solr_bib["non_lc_subject_display"] = ["some -- subject"]
        subject = SolrDoc(solr_bib)
        assert serialize(subject.other_subjects) == [{"text": "some -- subject"}]

    def test_bookplate(self, solr_bib):
        solr_bib["bookplate"] = ["bookplate"]
        subject = SolrDoc(solr_bib)
        assert serialize(subject.bookplate) == [{"text": "bookplate"}]

    def test_indexing_date(self, solr_bib):
        solr_bib["date_of_index"] = "some_valid_date_string"
        subject = SolrDoc(solr_bib)
        assert subject.indexing_date == "some_valid_date_string"

    def test_main_author(self, solr_bib):
        subject = SolrDoc(solr_bib)
        assert serialize(subject.main_author) == [
            {
                "transliterated": {
                    "text": "Saeki, Akimitsu.",
                    "search": [{"field": "author", "value": "Saeki, Akimitsu."}],
                    "browse": "Saeki, Akimitsu.",
                },
                "original": {
                    "text": "佐伯彰光.",
                    "search": [{"field": "author", "value": "佐伯彰光."}],
                    "browse": "佐伯彰光.",
                },
            }
        ]

    def test_published(self, solr_bib):
        subject = SolrDoc(solr_bib)
        assert serialize(subject.published) == [
            {
                "transliterated": {
                    "text": "Tōkyō : Nihon Yachō no Kai, 1983",
                },
                "original": {"text": "東京 : 日本野鳥の会, 1983"},
            }
        ]

    def test_edition(self, solr_bib):
        subject = SolrDoc(solr_bib)
        assert serialize(subject.edition) == [
            {
                "transliterated": {"text": "3-teiban."},
                "original": {"text": "3訂版."},
            }
        ]


@pytest.fixture()
def a_to_z_str():
    return " ".join(list(string.ascii_lowercase))


def create_record_with_paired_field(
    tag: str,
    subfields: str = (string.ascii_lowercase + "12345"),
    ind1: str = "",
    ind2: str = "",
):
    record = pymarc.record.Record()
    subfields = [pymarc.Subfield(code=code, value=code) for code in list(subfields)]

    vsubfields = subfields.copy()

    subfields.append(pymarc.Subfield(code="6", value="880-06"))
    vsubfields.append(pymarc.Subfield(code="6", value=f"{tag}-06"))

    field = pymarc.Field(
        tag=tag, indicators=pymarc.Indicators(ind1, ind2), subfields=subfields
    )

    vfield = pymarc.Field(
        tag="880", indicators=pymarc.Indicators(ind1, ind2), subfields=vsubfields
    )

    record.add_field(field)
    record.add_field(vfield)
    return record


class TestMARC:
    ###################
    # preferred_title #
    ###################
    @pytest.mark.parametrize("tag", ["130", "240", "243"])
    def test_preferred_title_130_240_243(self, tag, a_to_z_str):
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={
                "text": a_to_z_str,
                "search": [
                    {
                        "field": "title",
                        "value": "a b c d e f g h i j k m n o p q r s t u v w x y z",  # missing an l
                    }
                ],
            },
        )

        assert serialize(subject.preferred_title) == expected

    def test_preferred_title_730(self):
        record = create_record_with_paired_field(tag="730", ind2="2")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="730",
            elements={
                "text": "a b c d e f g h j k l m n o p q r s t u v w x y z",
                "search": [
                    {
                        "field": "title",
                        "value": "a b c d e f g h j k l m n o p q r s t u v w x y z",  # missing an i
                    }
                ],
            },
        )

        assert serialize(subject.preferred_title) == expected

    def test_preferred_title_730_no_ind2(self):
        record = create_record_with_paired_field(tag="730", ind2="1")
        subject = MARC(record)
        assert (subject.preferred_title) == []

    #################
    # related_title #
    #################

    def test_related_title_730_blank_ind2(self):
        record = create_record_with_paired_field(tag="730", ind2=None)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="730",
            elements={
                "text": "a b c d e f g h j k l m n o p q r s t u v w x y z",
                "search": [
                    {
                        "field": "title",
                        "value": "a b c d e f g h j k l m n o p q r s t u v w x y z",  # missing an i
                    }
                ],
            },
        )
        assert serialize(subject.related_title) == expected

    def test_related_title_730_present_ind2(self):
        record = create_record_with_paired_field(tag="730", ind2="1")
        subject = MARC(record)
        assert (subject.related_title) == []

    @pytest.mark.parametrize("tag", ["700", "710"])
    def test_related_title_700_710_ind2_not_2_and_t(self, tag):
        record = create_record_with_paired_field(tag=tag, ind2="1")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={
                "text": "a b c d e f g j k l m n o p q r s t",
                "search": [
                    {
                        "field": "title",
                        "value": "f j k l m n o p r s t",
                    }
                ],
            },
        )

        assert serialize(subject.related_title) == expected

    def test_related_title_711_ind2_not_2_and_t(self):
        record = create_record_with_paired_field(tag="711", ind2="1")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="711",
            elements={
                "text": "a b c d e f g j k l m n o p q r s t",
                "search": [
                    {
                        "field": "title",
                        "value": "f k l m n o p r s t",
                    }
                ],
            },
        )
        assert serialize(subject.related_title) == expected

    @pytest.mark.parametrize("tag", ["700", "710", "711"])
    def test_related_title_ind2_not_2_no_t(self, tag):
        no_t = string.ascii_lowercase.replace("t", "")
        record = create_record_with_paired_field(tag=tag, ind2="2", subfields=no_t)
        subject = MARC(record)
        assert (subject.related_title) == []

    @pytest.mark.parametrize("tag", ["700", "710", "711"])
    def test_related_title_ind2_and_t(self, tag):
        record = create_record_with_paired_field(tag=tag, ind2="2")
        subject = MARC(record)
        assert (subject.related_title) == []

    ################
    # other_titles #
    ################

    @pytest.mark.parametrize("tag", ["246", "247", "740"])
    def test_other_titles_246_247_740_with_t_and_indicator_2(self, tag, a_to_z_str):
        record = create_record_with_paired_field(tag=tag, ind2="2")
        subject = MARC(record)

        expected = self.expected_paired_field(
            tag=tag,
            elements={
                "text": a_to_z_str,
                "search": [{"field": "title", "value": a_to_z_str}],
            },
        )

        assert serialize(subject.other_titles) == expected

    @pytest.mark.parametrize("tag", ["700", "710", "711"])
    def test_other_titles_700_710_711_with_t_and_indicator_2(self, tag):
        record = create_record_with_paired_field(tag=tag, ind2="2")
        subject = MARC(record)
        if tag in ["700", "710"]:
            expected = self.expected_paired_field(
                tag=tag,
                elements={
                    "text": "a b c d e f g j k l m n o p q r s t",
                    "search": [{"field": "title", "value": "f j k l m n o p r s t"}],
                },
            )
        else:  # 711
            expected = self.expected_paired_field(
                tag=tag,
                elements={
                    "text": "a b c d e f g j k l m n o p q r s t",
                    "search": [
                        {"field": "title", "value": "f k l m n o p r s t"}
                    ],  # this does not have a $j
                },
            )
        assert serialize(subject.other_titles) == expected

    @pytest.mark.parametrize("tag", ["700", "710", "711"])
    def test_other_titles_700_710_711_with_t_and_no_indicator_2(self, tag):
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = []
        assert subject.other_titles == expected

    @pytest.mark.parametrize("tag", ["700", "710", "711"])
    def test_other_titles_700_710_711_with_indicator_2_and_no_t(self, tag):
        sfs = string.ascii_lowercase.replace("t", "")
        record = create_record_with_paired_field(tag=tag, subfields=sfs, ind2="2")
        subject = MARC(record)
        assert subject.other_titles == []

    ##############
    # new_title #
    ##############
    def test_new_title(self):
        record = create_record_with_paired_field(tag="785")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="785",
            elements={
                "text": "a s t",
                "search": [
                    {"field": "author", "value": "a"},
                    {"field": "title", "value": "s t"},
                ],
            },
        )
        assert serialize(subject.new_title) == expected

    def test_new_title_with_empty_author(self):
        record = create_record_with_paired_field(tag="785")
        record["785"]["a"] = ""
        record["880"]["a"] = ""
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="785",
            elements={
                "text": "s t",
                "search": [
                    {"field": "title", "value": "s t"},
                ],
            },
        )

        assert serialize(subject.new_title) == expected

    def test_new_title_with_missing_author(self):
        record = create_record_with_paired_field(tag="785", subfields="st")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="785",
            elements={
                "text": "s t",
                "search": [
                    {"field": "title", "value": "s t"},
                ],
            },
        )

        assert serialize(subject.new_title) == expected

    ##################
    # new_title_issn #
    ##################
    def test_new_title_issn(self):
        record = create_record_with_paired_field(tag="785")
        subject = MARC(record)
        expected = [{"tag": "785", "text": "x", "browse": None, "search": None}]
        assert serialize(subject.new_title_issn) == expected

    def test_new_title_issn_does_not_have_duplicates(self):
        record = create_record_with_paired_field(tag="785")
        subfields = [
            pymarc.Subfield(code=code, value=code)
            for code in list(string.ascii_lowercase)
        ]
        field = pymarc.Field(tag="785", subfields=subfields)
        record.add_field(field)

        subject = MARC(record)
        expected = [{"tag": "785", "text": "x", "browse": None, "search": None}]
        assert serialize(subject.new_title_issn) == expected

    ##################
    # previous_title #
    ##################
    def test_previous_title(self):
        record = create_record_with_paired_field(tag="780")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="780",
            elements={
                "text": "a s t",
                "search": [
                    {"field": "author", "value": "a"},
                    {"field": "title", "value": "s t"},
                ],
            },
        )
        assert serialize(subject.previous_title) == expected

    #######################
    # previous_title_issn #
    #######################
    def test_previous_title_issn(self):
        record = create_record_with_paired_field(tag="780")
        subject = MARC(record)
        expected = [{"tag": "780", "text": "x", "browse": None, "search": None}]
        assert serialize(subject.previous_title_issn) == expected

    ################
    # contributors #
    ################
    @pytest.mark.parametrize("tag", ["700", "710"])
    def test_contributors_with_indicator_2_not_2_and_no_t_and_e_present(self, tag):
        # this should not show 4
        sfs = string.ascii_lowercase.replace("t", "") + "4"
        record = create_record_with_paired_field(tag=tag, subfields=sfs)

        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={
                "text": "a b c d e g j n q u",
                "search": [{"field": "author", "value": "a b c d g j n q u"}],
                "browse": "a b c d g j n q u",
            },
        )

        assert serialize(subject.contributors) == expected

    @pytest.mark.parametrize("tag", ["700", "710"])
    def test_contributors_with_indicator_2_not_2_and_no_t_and_e_not_present(self, tag):
        # this should show 4 (and not e because it is not there)
        sfs = string.ascii_lowercase.replace("t", "") + "4"
        sfs = sfs.replace("e", "")
        record = create_record_with_paired_field(tag=tag, subfields=sfs)

        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={
                "text": "a b c d g j n q u 4",
                "search": [{"field": "author", "value": "a b c d g j n q u"}],
                "browse": "a b c d g j n q u",
            },
        )

        assert serialize(subject.contributors) == expected

    @pytest.mark.parametrize("tag", ["700", "710"])
    def test_contributors_with_indicator_2_not_2_and_no_t_and_e_not_present_4_starts_with_http(
        self, tag
    ):
        # this should show 4 (and not e because it is not there)
        sfs = string.ascii_lowercase.replace("t", "") + "4"
        sfs = sfs.replace("e", "")
        record = create_record_with_paired_field(tag=tag, subfields=sfs)
        record[tag]["4"] = "http://some-website"
        record["880"]["4"] = "http://some-website"

        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={
                "text": "a b c d g j n q u",
                "search": [{"field": "author", "value": "a b c d g j n q u"}],
                "browse": "a b c d g j n q u",
            },
        )

        assert serialize(subject.contributors) == expected

    @pytest.mark.parametrize("tag", ["711"])
    def test_contributors_711_with_indicator_2_not_2_and_no_t_and_e_present(self, tag):
        # this should not show 4
        sfs = string.ascii_lowercase.replace("t", "") + "4"
        record = create_record_with_paired_field(tag=tag, subfields=sfs)

        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={
                "text": "a b c d e g j n q u",
                "search": [{"field": "author", "value": "a c d e g n q u"}],
                "browse": "a c d e g n q u",
            },
        )

        assert serialize(subject.contributors) == expected

    @pytest.mark.parametrize("tag", ["711"])
    def test_contributors_711_with_indicator_2_not_2_and_no_t_and_e_not_present(
        self, tag
    ):
        # this should show 4 (but not e because it's not there)
        sfs = string.ascii_lowercase.replace("t", "") + "4"
        sfs = sfs.replace("e", "")
        record = create_record_with_paired_field(tag=tag, subfields=sfs)

        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={
                "text": "a b c d g j n q u 4",
                "search": [{"field": "author", "value": "a c d g n q u"}],
                "browse": "a c d g n q u",
            },
        )

        assert serialize(subject.contributors) == expected

    @pytest.mark.parametrize("tag", ["711"])
    def test_contributors_711_with_indicator_2_not_2_and_no_t_and_e_not_present_4_has_http(
        self, tag
    ):
        # this should show 4 (but not e because it's not there)
        sfs = string.ascii_lowercase.replace("t", "") + "4"
        sfs = sfs.replace("e", "")
        record = create_record_with_paired_field(tag=tag, subfields=sfs)
        record["711"]["4"] = "http://some-website"
        record["880"]["4"] = "http://some-website"

        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={
                "text": "a b c d g j n q u",
                "search": [{"field": "author", "value": "a c d g n q u"}],
                "browse": "a c d g n q u",
            },
        )

        assert serialize(subject.contributors) == expected

    @pytest.mark.parametrize("tag", ["700", "710", "711"])
    def test_contributors_with_indicator_2_not_2_and_t(self, tag):
        sfs = string.ascii_lowercase + "4"
        record = create_record_with_paired_field(tag=tag, subfields=sfs)
        subject = MARC(record)
        assert subject.contributors == []

    @pytest.mark.parametrize("tag", ["700", "710", "711"])
    def test_contributors_with_indicator_2_as_2_and_no_t(self, tag):
        sfs = string.ascii_lowercase.replace("t", "") + "4"
        record = create_record_with_paired_field(tag=tag, subfields=sfs, ind2="2")
        subject = MARC(record)
        assert subject.contributors == []

    ###########
    # created #
    ###########
    def test_created_264_with_ind_1_as_0(self, a_to_z_str):
        record = create_record_with_paired_field(tag="264", ind2="0")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="264",
            elements={
                "text": a_to_z_str,
            },
        )
        assert serialize(subject.created) == expected

    def test_created_not_ind_1_as_0(self):
        record = create_record_with_paired_field(tag="264", ind2="1")
        subject = MARC(record)
        assert serialize(subject.created) == []

    ###############
    # distributed #
    ###############
    def test_distributed_264_with_ind_1_as_2(self, a_to_z_str):
        record = create_record_with_paired_field(tag="264", ind2="2")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="264",
            elements={
                "text": a_to_z_str,
            },
        )
        assert serialize(subject.distributed) == expected

    def test_distributed_not_ind_1_as_2(self):
        record = create_record_with_paired_field(tag="264", ind2="1")
        subject = MARC(record)
        assert serialize(subject.distributed) == []

    ################
    # manufactured #
    ################
    def test_manufactured_260(self):
        record = create_record_with_paired_field(tag="260")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="260",
            elements={
                "text": "e f g",
            },
        )

        assert serialize(subject.manufactured) == expected

    def test_manufactured_260_with_missing_fields(self):
        record = create_record_with_paired_field(tag="260", subfields="a")
        subject = MARC(record)
        assert subject.manufactured == []

    def test_manufactured_264_with_indicator2_as_3(self, a_to_z_str):
        record = create_record_with_paired_field(tag="264", ind2="3")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="264",
            elements={
                "text": a_to_z_str,
            },
        )

        assert serialize(subject.manufactured) == expected

    ##########
    # series #
    ##########

    @pytest.mark.parametrize("tag", ["400", "410", "411", "440", "490"])
    def test_series(self, tag, a_to_z_str):
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": a_to_z_str},
        )
        assert serialize(subject.series) == expected

    def test_series_with_only_880(self, a_to_z_str):
        record = create_record_with_paired_field(tag="400")
        record.remove_fields("400")

        subject = MARC(record)
        expected = [
            {
                "original": {
                    "text": a_to_z_str,
                    "tag": "880",
                    "browse": None,
                    "search": None,
                },
                "transliterated": None,
            }
        ]
        assert serialize(subject.series) == expected

    def test_series_with_only_400(self, a_to_z_str):
        record = create_record_with_paired_field(tag="400")
        record.remove_fields("880")

        subject = MARC(record)
        expected = [
            {
                "original": {
                    "text": a_to_z_str,
                    "tag": "400",
                    "browse": None,
                    "search": None,
                },
                "transliterated": None,
            }
        ]
        assert serialize(subject.series) == expected

    ####################
    # series statement #
    ####################

    @pytest.mark.parametrize("tag", ["440", "800", "810", "811", "830"])
    def test_series_statement(self, tag, a_to_z_str):
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": a_to_z_str},
        )
        assert serialize(subject.series_statement) == expected

    #####################
    # biography_history #
    #####################

    def test_biography_history(self):
        record = create_record_with_paired_field(tag="545")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="545",
            elements={"text": "a"},
        )
        assert serialize(subject.biography_history) == expected

    ###########
    # summary #
    ###########

    def test_summary(self):
        record = create_record_with_paired_field(tag="520")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="520",
            elements={"text": "a b c 3"},
        )
        assert serialize(subject.summary) == expected

    def test_summary_ind_1_4(self):
        record = create_record_with_paired_field(tag="520", ind1="4")
        subject = MARC(record)
        assert serialize(subject.summary) == []

    #################
    # in collection #
    #################

    def test_in_collection_with_t_and_w(self):
        record = create_record_with_paired_field(tag="773")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="773",
            elements={
                "text": "t",
                "search": [{"field": "isn", "value": "w"}],
            },
        )
        assert serialize(subject.in_collection) == expected

    def test_in_collection_with_w_and_no_t(self):
        sfs = string.ascii_lowercase.replace("t", "")
        record = create_record_with_paired_field(tag="773", subfields=sfs)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="773",
            elements={
                "text": "w",
                "search": [{"field": "isn", "value": "w"}],
            },
        )
        assert serialize(subject.in_collection) == expected

    ##########
    # access #
    ##########

    def test_access(self):
        record = create_record_with_paired_field(tag="506")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="506",
            elements={"text": "a b c"},
        )
        assert serialize(subject.access) == expected

    ################
    # finding_aids #
    ################
    def test_finding_aids_without_u_subfield(self):
        sfs = string.ascii_lowercase.replace("u", "") + "3"
        record = create_record_with_paired_field(tag="555", subfields=sfs)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="555",
            elements={"text": "a b c d 3"},
        )
        assert serialize(subject.finding_aids) == expected

    def test_finding_aids_with_u_subfield(self):
        record = create_record_with_paired_field(tag="555")
        subject = MARC(record)
        assert serialize(subject.finding_aids) == []

    ################
    # terms_of_use #
    ################
    def test_terms_of_use(self, a_to_z_str):
        record = create_record_with_paired_field(tag="540")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="540",
            elements={"text": a_to_z_str},
        )
        assert serialize(subject.terms_of_use) == expected

    #################
    # language_note #
    #################
    def test_language_note(self, a_to_z_str):
        record = create_record_with_paired_field(tag="546")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="546",
            elements={"text": a_to_z_str},
        )
        assert serialize(subject.language_note) == expected

    ##############
    # performers #
    ##############
    def test_performers(self):
        record = create_record_with_paired_field(tag="511")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="511",
            elements={"text": "a"},
        )
        assert serialize(subject.performers) == expected

    #######################
    # date_place_of_event #
    #######################
    def test_date_place_of_event(self):
        record = create_record_with_paired_field(tag="518")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="518",
            elements={"text": "a d o p 2 3"},
        )
        assert serialize(subject.date_place_of_event) == expected

    ######################
    # preferred_citation #
    ######################

    def test_preferred_citation(self):
        tag = "524"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.preferred_citation) == expected

    #########################
    # location_of_originals #
    #########################
    def test_location_of_originals(self, a_to_z_str):
        tag = "535"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": f"{a_to_z_str} 3"},
        )
        assert serialize(subject.location_of_originals) == expected

    #######################
    # funding_information #
    #######################
    def test_funding_information(self):
        tag = "536"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.funding_information) == expected

    ########################
    # source_of_acquistion #
    ########################
    def test_source_of_acquisition(self):
        tag = "541"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.source_of_acquisition) == expected

    #################
    # related_items #
    #################
    def test_related_items(self):
        tag = "580"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.related_items) == expected

    #############
    # numbering #
    #############
    def test_numbering(self):
        tag = "362"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.numbering) == expected

    #################################
    # current_publication_frequency #
    #################################
    def test_current_publication_frequency(self):
        tag = "310"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a b"},
        )
        assert serialize(subject.current_publication_frequency) == expected

    ################################
    # former_publication_frequency #
    ################################
    def test_former_publication_frequency(self):
        tag = "321"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a b"},
        )
        assert serialize(subject.former_publication_frequency) == expected

    ###################
    # numbering_notes #
    ###################
    def test_numbering_notes(self):
        tag = "515"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.numbering_notes) == expected

    ##############################
    # source_of_description_note #
    ##############################
    def test_source_of_description_note(self):
        tag = "588"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.source_of_description_note) == expected

    ######################
    # copy_specific_note #
    ######################
    def test_copy_specific_note(self):
        tag = "590"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.copy_specific_note) == expected

    ##############
    # references #
    ##############
    def test_references(self, a_to_z_str):
        tag = "510"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": a_to_z_str},
        )
        assert serialize(subject.references) == expected

    ################################
    # copyright_status_information #
    ################################
    def test_copyright_status_information(self, a_to_z_str):
        tag = "542"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": a_to_z_str},
        )
        assert serialize(subject.copyright_status_information) == expected

    ########
    # note #
    ########

    @pytest.mark.parametrize(
        "tag",
        [
            "500",
            "501",
            "502",
            "525",
            "526",
            "530",
            "547",
            "550",
            "552",
            "561",
            "565",
            "584",
            "585",
        ],
    )
    def test_note(self, tag):
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.note) == expected

    ###############
    # arrangement #
    ###############
    def test_arrangement(self):
        tag = "351"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a b 3"},
        )
        assert serialize(subject.arrangement) == expected

    #############
    # copyright #
    #############
    def test_copyright_with_ind_2_as_4(self, a_to_z_str):
        tag = "264"
        record = create_record_with_paired_field(tag=tag, ind2="4")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": a_to_z_str},
        )
        assert serialize(subject.copyright) == expected

    def test_copyright_with_ind_2_not_4(self):
        tag = "264"
        record = create_record_with_paired_field(tag=tag, ind2="1")
        subject = MARC(record)
        assert serialize(subject.copyright) == []

    ########################
    # physical description #
    ########################

    def test_physical_description(self, a_to_z_str):
        record = create_record_with_paired_field(tag="300")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag="300",
            elements={"text": a_to_z_str},
        )
        assert serialize(subject.physical_description) == expected

    #############
    # map_scale #
    #############
    def test_map_scale(self):
        tag = "255"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.map_scale) == expected

    #####################
    # reproduction_note #
    #####################
    def test_reproduction_note(self, a_to_z_str):
        tag = "533"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": f"{a_to_z_str} 3 5"},
        )
        assert serialize(subject.reproduction_note) == expected

    #########################
    # original_version_note #
    #########################
    def test_original_version_note(self, a_to_z_str):
        tag = "534"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": f"{a_to_z_str} 3 5"},
        )
        assert serialize(subject.original_version_note) == expected

    ################
    # playing_time #
    ################
    def test_playing_time(self):
        tag = "306"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.playing_time) == expected

    ################
    # media_format #
    ################
    def test_media_format(self):
        tag = "538"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.media_format) == expected

    ############
    # audience #
    ############
    def test_audience(self):
        tag = "521"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.audience) == expected

    ##################
    # content_advice #
    ##################
    def test_content_advice_ind1_as_4(self):
        tag = "520"
        record = create_record_with_paired_field(tag=tag, ind1="4")
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a b c 3"},
        )
        assert serialize(subject.content_advice) == expected

    def test_content_advice_ind1_not_4(self):
        tag = "520"
        record = create_record_with_paired_field(tag=tag, ind1="1")
        subject = MARC(record)
        assert serialize(subject.content_advice) == []

    ##########
    # awards #
    ##########
    def test_awards(self):
        tag = "586"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.awards) == expected

    ######################
    # production_credits #
    ######################
    def test_production_credits(self):
        tag = "508"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.production_credits) == expected

    ################
    # bibliography #
    ################
    def test_bibliography(self):
        tag = "504"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a"},
        )
        assert serialize(subject.bibliography) == expected

    ####################
    # publisher_number #
    ####################
    def test_publisher_number(self):
        tag = "028"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": "a b"},
        )
        assert serialize(subject.publisher_number) == expected

    ############
    # contents #
    ############
    def test_contents(self, a_to_z_str):
        tag = "505"
        record = create_record_with_paired_field(tag=tag)
        subject = MARC(record)
        expected = self.expected_paired_field(
            tag=tag,
            elements={"text": a_to_z_str},
        )
        assert serialize(subject.contents) == expected

    def expected_paired_field(self, tag: str, elements: dict):
        result = [
            {
                "transliterated": asdict(FieldElement(tag=tag, **elements)),
                "original": asdict(FieldElement(tag="880", **elements)),
            }
        ]
        return result


@dataclass(frozen=True)
class BaseRecordFake:
    field_name: list = field(default_factory=[])


@pytest.fixture()
def empty_marc_record():
    return pymarc.record.Record()


@pytest.fixture()
def base_mapping():
    return [{"kind": "base", "field": "field_name", "ris": ["EX"], "meta": ["example"]}]


@pytest.fixture()
def marc_mapping():
    return [
        {
            "kind": "marc",
            "ruleset": FieldRuleset(tags=["300"], text_sfs="abc"),
            "ris": ["EX"],
            "meta": ["example"],
        }
    ]


class TestTaggedCitation:
    def test_to_list_for_base_paired_field(self, base_mapping, empty_marc_record):
        base_record_stub = BaseRecordFake(
            field_name=[
                PairedField(original=FieldElement(text="CONTENT STRING", tag=None))
            ],
        )
        expected = [{"content": "CONTENT STRING", "ris": ["EX"], "meta": ["example"]}]
        subject = TaggedCitation(
            base_record=base_record_stub, marc_record=empty_marc_record
        ).to_list(tag_mapping=base_mapping)

        for example in expected:
            assert example in subject

    def test_to_list_for_base_multiple_paired_fields(
        self, base_mapping, empty_marc_record
    ):
        base_record_stub = BaseRecordFake(
            field_name=[
                PairedField(original=FieldElement(text="CONTENT1", tag=None)),
                PairedField(
                    original=FieldElement(text="CONTENT2", tag=None),
                    transliterated=FieldElement(text="TCONTENT2", tag=None),
                ),
            ]
        )

        expected = [
            {"content": "CONTENT1", "ris": ["EX"], "meta": ["example"]},
            {"content": "TCONTENT2", "ris": ["EX"], "meta": ["example"]},
        ]

        subject = TaggedCitation(
            base_record=base_record_stub, marc_record=empty_marc_record
        ).to_list(tag_mapping=base_mapping)
        for example in expected:
            assert example in subject

    def test_to_list_for_base_empty(self, base_mapping, empty_marc_record):
        base_record_stub = BaseRecordFake(field_name=[])

        expected = []

        subject = TaggedCitation(
            base_record=base_record_stub, marc_record=empty_marc_record
        ).to_list(tag_mapping=base_mapping)
        for example in expected:
            assert example in subject

    def test_to_list_base_text_list(self, base_mapping, empty_marc_record):
        base_record_stub = BaseRecordFake(
            field_name=[FieldElement(text="CONTENT STRING", tag=None)]
        )

        expected = [{"content": "CONTENT STRING", "ris": ["EX"], "meta": ["example"]}]
        subject = TaggedCitation(
            base_record=base_record_stub, marc_record=empty_marc_record
        ).to_list(tag_mapping=base_mapping)
        for example in expected:
            assert example in subject

    def test_to_list_base_bare_text_list(self, base_mapping, empty_marc_record):
        base_record_stub = BaseRecordFake(field_name=["CONTENT1", "CONTENT2"])

        expected = [
            {"content": "CONTENT1", "ris": ["EX"], "meta": ["example"]},
            {"content": "CONTENT2", "ris": ["EX"], "meta": ["example"]},
        ]
        subject = TaggedCitation(
            base_record=base_record_stub, marc_record=empty_marc_record
        ).to_list(tag_mapping=base_mapping)
        for example in expected:
            assert example in subject

    def test_to_list_marc(self, marc_mapping):
        record = create_record_with_paired_field(tag="300")
        expected = [
            {"content": "a b c", "ris": ["EX"], "meta": ["example"]},
        ]
        subject = TaggedCitation(base_record=None, marc_record=record).to_list(
            tag_mapping=marc_mapping
        )
        for example in expected:
            assert example in subject

    def test_to_list_marc_lone_880(self, marc_mapping):
        record = create_record_with_paired_field(tag="300")
        record.remove_fields("300")
        expected = [
            {"content": "a b c", "ris": ["EX"], "meta": ["example"]},
        ]
        subject = TaggedCitation(base_record=None, marc_record=record).to_list(
            tag_mapping=marc_mapping
        )
        for example in expected:
            assert example in subject

    def test_to_list_solr_display_date(self, empty_marc_record, solr_bib):
        tagged_mapping = [
            {
                "kind": "solr",
                "field": "display_date",
                "ris": ["EX"],
                "meta": ["example"],
            }
        ]
        subject = TaggedCitation(
            base_record=None, marc_record=empty_marc_record, solr_doc=solr_bib
        ).to_list(tagged_mapping)
        expected = [
            {"content": "1983", "ris": ["EX"], "meta": ["example"]},
        ]
        for example in expected:
            assert example in subject

    def test_to_list_solr_academic_discipline(self, empty_marc_record, solr_bib):
        tagged_mapping = [
            {
                "kind": "solr",
                "field": "hlb3Delimited",
                "ris": ["KW"],
                "meta": ["keywords"],
            }
        ]
        subject = TaggedCitation(
            base_record=None, marc_record=empty_marc_record, solr_doc=solr_bib
        ).to_list(tagged_mapping)

        expected = [
            {
                "content": "Science | Biology | Zoology",
                "ris": ["KW"],
                "meta": ["keywords"],
            },
            {
                "content": "Science | Biology | Ecology and Evolutionary Biology",
                "ris": ["KW"],
                "meta": ["keywords"],
            },
        ]
        for example in expected:
            assert example in subject

    def test_non_record_specific_tags(self, empty_marc_record):
        subject = TaggedCitation(
            base_record=None, marc_record=empty_marc_record
        ).to_list(tag_mapping=[])
        expected = [
            {
                "content": "U-M Catalog Search",
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

        for example in expected:
            assert example in subject

    def test_to_list_type_is_first_element(self, empty_marc_record, solr_bib):
        subject = TaggedCitation(
            base_record=None, marc_record=empty_marc_record, solr_doc=solr_bib
        ).to_list([])

        expected = {
            "content": "BOOK",
            "ris": ["TY"],
            "meta": [],
        }

        assert subject[0] == expected

    def test_to_list_type_is_jour_when_no_format(self, empty_marc_record):
        subject = TaggedCitation(
            base_record=None, marc_record=empty_marc_record
        ).to_list([])

        expected = {
            "content": "JOUR",
            "ris": ["TY"],
            "meta": [],
        }

        assert subject[0] == expected

    def test_to_list_type_is_gen_when_no_matching_format(
        self, empty_marc_record, solr_bib
    ):
        solr_bib["format"] = ["some_non_standard_format"]
        subject = TaggedCitation(
            base_record=None, marc_record=empty_marc_record, solr_doc=solr_bib
        ).to_list([])

        expected = {
            "content": "GEN",
            "ris": ["TY"],
            "meta": [],
        }

        assert subject[0] == expected

    def test_to_list_type_tried_again_when_multiple_formats(
        self, empty_marc_record, solr_bib
    ):
        solr_bib["format"] = ["some_non_standard_format", "Video (DVD)"]
        subject = TaggedCitation(
            base_record=None, marc_record=empty_marc_record, solr_doc=solr_bib
        ).to_list([])

        expected = {
            "content": "VIDEO",
            "ris": ["TY"],
            "meta": [],
        }

        assert subject[0] == expected

    def test_end_record_tag(self, empty_marc_record):
        subject = TaggedCitation(
            base_record=None, marc_record=empty_marc_record
        ).to_list(tag_mapping=[])
        expected = {
            "content": "",
            "ris": ["ER"],
            "meta": [],
        }

        assert subject[-1] == expected


class TestCSL:
    def test_id(self, solr_bib):
        subject = CSL(solr_doc=solr_bib)
        assert subject.id == solr_bib["id"]

    def test_title(self):
        record = create_record_with_paired_field(tag="245")
        subject = CSL(marc_record=record)

        assert subject.title == "a b p"

    def test_title_does_not_have_trailing_chars(self):
        record = create_record_with_paired_field(tag="245")
        record["245"]["p"] = "p . /,: / "
        subject = CSL(marc_record=record)
        assert subject.title == "a b p"

    def test_call_number(self, solr_bib):
        solr_bib["callnumber"].append("some other call number")
        subject = CSL(solr_doc=solr_bib)
        assert subject.call_number == solr_bib["callnumber"][0]

    def test_empty_call_number(self, solr_bib):
        del solr_bib["callnumber"]
        subject = CSL(solr_doc=solr_bib)
        assert subject.call_number is None

    def test_edition(self, solr_bib):
        base = BaseRecord(solr_bib)
        subject = CSL(base_record=base, solr_doc=solr_bib)
        assert subject.edition == "3-teiban."

    def test_edition_not_paired(self, solr_bib):
        solr_bib["edition"].pop()
        base = BaseRecord(solr_bib)
        subject = CSL(base_record=base, solr_doc=solr_bib)
        assert subject.edition == "3-teiban."

    def test_isbn(self, solr_bib):
        base = BaseRecord(solr_bib)
        subject = CSL(base_record=base, solr_doc=solr_bib)
        assert subject.isbn == ["9784931150010", "4931150012", "4931150012 :"]

    def test_issn(self, solr_bib):
        solr_bib["issn"] = ["some_issn"]
        base = BaseRecord(solr_bib)
        subject = CSL(base_record=base, solr_doc=solr_bib)
        assert subject.issn == ["some_issn"]

    def test_publisher_place_when_260(self):
        record = create_record_with_paired_field(tag="260")
        subject = CSL(marc_record=record)
        assert subject.publisher_place == "a"

    def test_publisher_place_when_264_and_indicator_2_not_1(self):
        record = create_record_with_paired_field(tag="264", ind2="0")
        subject = CSL(marc_record=record)
        assert subject.publisher_place is None

    def test_publisher_place_when_264_and_indicator_2_is_1(self):
        record = create_record_with_paired_field(tag="264", ind2="1")
        subject = CSL(marc_record=record)
        assert subject.publisher_place == "a"

    def test_publisher_when_260(self):
        record = create_record_with_paired_field(tag="260")
        subject = CSL(marc_record=record)
        assert subject.publisher == "b"

    def test_publisher_when_264_and_indicator_2_not_1(self):
        record = create_record_with_paired_field(tag="264", ind2="0")
        subject = CSL(marc_record=record)
        assert subject.publisher is None

    def test_publisher_when_264_and_indicator_2_is_1(self):
        record = create_record_with_paired_field(tag="264", ind2="1")
        subject = CSL(marc_record=record)
        assert subject.publisher == "b"

    ##############
    # csl editor #
    ##############
    def test_editor_700_and_ind1_is_1_and_e_is_editor(self):
        record = create_record_with_paired_field(tag="700", ind1="1")
        record["700"]["e"] = "editor"
        subject = CSL(marc_record=record)
        assert subject.editor == [{"literal": "a"}]

    def test_editor_has_given_and_family_name_700_and_ind1_is_1_and_e_is_editor(self):
        record = create_record_with_paired_field(tag="700", ind1="1")
        record["700"]["e"] = "editor"
        record["700"]["a"] = "Last, First"
        subject = CSL(marc_record=record)
        assert subject.editor == [{"family": "Last", "given": "First"}]

    def test_editor_700_and_ind1_is_1_and_e_is_not_editor(self):
        record = create_record_with_paired_field(tag="700", ind1="1")
        subject = CSL(marc_record=record)
        assert subject.editor is None

    def test_editor_700_and_ind1_is_not_1_or_0_and_e_is_editor(self):
        record = create_record_with_paired_field(tag="700", ind1="2")
        record["700"]["e"] = "editor"
        subject = CSL(marc_record=record)
        assert subject.editor is None

    def test_editor_700_and_ind1_is_0_and_e_is_editor(self):
        record = create_record_with_paired_field(tag="700", ind1="0")
        record["700"]["e"] = "editor"
        subject = CSL(marc_record=record)
        assert subject.editor == [{"literal": "a b"}]

    def test_editor_700_and_ind1_is_0_and_e_is_not_editor(self):
        record = create_record_with_paired_field(tag="700", ind1="0")
        subject = CSL(marc_record=record)
        assert subject.editor is None

    def test_collection_title(self, solr_bib):
        base = BaseRecord(solr_bib)
        subject = CSL(base_record=base, solr_doc=solr_bib)
        assert subject.collection_title == "Yagai kansatsu handobukku ; 1"

    def test_number_gets_value_from_numbering(
        self,
        solr_bib,
    ):
        record = create_record_with_paired_field(tag="362")

        solr_bib["fullrecord"] = pymarc.marcxml.record_to_xml(record).decode("utf-8")
        base = BaseRecord(solr_bib)
        subject = CSL(base_record=base, solr_doc=solr_bib)

        assert subject.number == "a"

    def test_number_gets_value_from_report_number(self, solr_bib):
        solr_bib["rptnum"] = ["my_report_number"]
        base = BaseRecord(solr_bib)
        subject = CSL(base_record=base, solr_doc=solr_bib)
        assert subject.number == "my_report_number"

    def test_number_chooses_report_number_over_numbering(
        self,
        solr_bib,
    ):
        solr_bib["rptnum"] = ["my_report_number"]
        record = create_record_with_paired_field(tag="362")
        solr_bib["fullrecord"] = pymarc.marcxml.record_to_xml(record).decode("utf-8")
        base = BaseRecord(solr_bib)
        subject = CSL(base_record=base, solr_doc=solr_bib)

        assert subject.number == "my_report_number"

    def test_issued(self, solr_bib):
        expected = {"literal": solr_bib["display_date"]}
        base = BaseRecord(solr_bib)
        subject = CSL(base_record=base, solr_doc=solr_bib)

        assert subject.issued == expected

    def test_issued_when_no_display_date(self, solr_bib):
        del solr_bib["display_date"]
        base = BaseRecord(solr_bib)
        subject = CSL(base_record=base, solr_doc=solr_bib)
        assert subject.issued is None

    ##############
    # csl author #
    ##############
    @pytest.mark.parametrize("tag", ["100", "700"])
    def test_author_and_ind1_is_1_and_e_is_not_editor(self, tag):
        record = create_record_with_paired_field(tag=tag, ind1="1")
        record[tag]["e"] = "author"
        subject = CSL(marc_record=record)
        assert subject.author == [{"literal": "a"}]

    @pytest.mark.parametrize("tag", ["100", "700"])
    def test_author_and_ind1_is_1_and_e_is_editor(self, tag):
        record = create_record_with_paired_field(tag=tag, ind1="1")
        record[tag]["e"] = "editor"
        subject = CSL(marc_record=record)
        assert subject.author is None

    @pytest.mark.parametrize("tag", ["100", "700"])
    def test_author_and_ind1_is_not_1_or_0_and_e_is_not_editor(self, tag):
        record = create_record_with_paired_field(tag=tag, ind1="2")
        record[tag]["e"] = "author"
        subject = CSL(marc_record=record)
        assert subject.author is None

    @pytest.mark.parametrize("tag", ["100", "700"])
    def test_author_and_ind1_is_0_and_e_is_not_editor(self, tag):
        record = create_record_with_paired_field(tag=tag, ind1="0")
        record[tag]["e"] = "author"
        subject = CSL(marc_record=record)
        assert subject.author == [{"literal": "a b"}]

    @pytest.mark.parametrize("tag", ["100", "700"])
    def test_author_and_ind1_is_0_and_e_is_editor(self, tag):
        record = create_record_with_paired_field(tag=tag, ind1="0")
        record[tag]["e"] = "editor"
        subject = CSL(marc_record=record)
        assert subject.author is None

    @pytest.mark.parametrize("tag", ["100", "700"])
    def test_author_has_a_comma(self, tag):
        record = create_record_with_paired_field(tag=tag, ind1="1")
        record[tag]["e"] = "author"
        record[tag]["a"] = "Last, First"
        subject = CSL(marc_record=record)
        assert subject.author == [{"family": "Last", "given": "First"}]

    @pytest.mark.parametrize("tag", ["110", "111", "710", "711"])
    def test_author_corporate_e_is_not_editor(self, tag):
        record = create_record_with_paired_field(tag=tag)
        record[tag]["e"] = "author"
        subject = CSL(marc_record=record)
        assert subject.author == [{"literal": "a b"}]

    @pytest.mark.parametrize("tag", ["110", "111", "710", "711"])
    def test_author_corporate_e_is_editor(self, tag):
        record = create_record_with_paired_field(tag=tag)
        record[tag]["e"] = "editor"
        subject = CSL(marc_record=record)
        assert subject.author is None

    @pytest.mark.parametrize("tag", ["110", "111", "710", "711"])
    def test_author_corporate_with_comma(self, tag):
        record = create_record_with_paired_field(tag=tag)
        record[tag]["e"] = "author"
        record[tag]["a"] = "Last, First"
        subject = CSL(marc_record=record)
        assert subject.author == [{"literal": "Last, First b"}]

    ############
    # csl type #
    ############
    def test_type(self, solr_bib):
        base = BaseRecord(solr_bib)
        subject = CSL(base_record=base, solr_doc=solr_bib)
        assert subject.type == "book"

    def test_type_returns_more_specific_type(self, solr_bib):
        solr_bib["format"] = ["Music", "Musical Score"]
        base = BaseRecord(solr_bib)
        subject = CSL(base_record=base, solr_doc=solr_bib)
        assert subject.type == "musical_score"
