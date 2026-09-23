from __future__ import annotations
from api.clients.solr_client import SolrClient
from api.solr import SolrDocProcessor
from api.marc import Processor, FieldRuleset, TRIM_CHARS
from api.holdings import get_alma_loans
from api.csl import BaseCSL
import re
import pymarc
import io
import string
import json
import fastapi_structured_logging

logger = fastapi_structured_logging.get_logger()

# from dataclasses import dataclass
# from collections.abc import Callable
from api.holdings import Holdings
from datetime import datetime


def record_for(id: str) -> Record:
    data = SolrClient().get_record(id)
    return Record(data)


def catalog_record_for(id: str) -> Record:
    data = SolrClient().get_record(id)
    return Record(data)


def onlinejournals_record_for(id: str) -> Record:
    data = SolrClient().get_onlinejournals_record(id)
    return OnlinejournalsRecord(data)


class SolrDoc:
    def __init__(self, data: dict):
        self.data = data
        # can't just be processor because of multiple inheritance
        self.solr_processor = SolrDocProcessor(data)

    @property
    def id(self):
        return self.solr_processor.get("id")

    @property
    def title(self):
        return self.solr_processor.get_paired_field("title_display")

    @property
    def published(self) -> list:
        return self.solr_processor.get_paired_field("publisher_display")

    @property
    def edition(self) -> list:
        return self.solr_processor.get_paired_field("edition")

    @property
    def lc_subjects(self):
        return self.solr_processor.get_text_field("lc_subject_display")

    @property
    def language(self):
        return self.solr_processor.get_text_field("language")

    @property
    def isbn(self):
        return self.solr_processor.get_text_field("isbn")

    @property
    def issn(self):
        return self.solr_processor.get_text_field("issn")

    @property
    def gov_doc_number(self):
        return self.solr_processor.get_text_field("sudoc")

    @property
    def report_number(self):
        return self.solr_processor.get_text_field("rptnum")

    @property
    def call_number(self):
        return self.solr_processor.get_text_field("callnumber_browse")

    @property
    def oclc(self):
        return self.solr_processor.get_text_field("oclc")

    @property
    def remediated_lc_subjects(self):
        return self.solr_processor.get_text_field("remediated_lc_subject_display")

    @property
    def other_subjects(self):
        return self.solr_processor.get_text_field("non_lc_subject_display")

    @property
    def bookplate(self):
        return self.solr_processor.get_text_field("bookplate")

    @property
    def indexing_date(self):
        return self.data.get("date_of_index")

    @property
    def availability(self) -> list:
        return self.solr_processor.get_list("availability")

    @property
    def format(self):
        return self.solr_processor.get_list("format")

    @property
    def main_author(self):
        main = self.data.get("main_author_display") or []
        search = self.data.get("main_author") or []

        match len(main):
            case 0:
                return []
            case 1:
                return [
                    {
                        "original": {
                            "text": main[0],
                            "search": [{"field": "author", "value": search[0]}],
                            "browse": search[0],
                        }
                    }
                ]
            case _:
                return [
                    {
                        "transliterated": {
                            "text": main[0],
                            "search": [{"field": "author", "value": search[0]}],
                            "browse": search[0],
                        },
                        "original": {
                            "text": main[1],
                            "search": [{"field": "author", "value": search[1]}],
                            "browse": search[1],
                        },
                    }
                ]

    @property
    def academic_discipline(self):
        return [
            {"list": discipline.split(" | ")}
            for discipline in self.solr_processor.get_list("hlb3Delimited")
        ]


class MARC:
    def __init__(self, record: pymarc.record.Record):
        self.record = record
        self.processor = Processor(record)

    @property
    def preferred_title(self) -> list:
        no_l = string.ascii_lowercase.replace("l", "")
        no_i = string.ascii_lowercase.replace("i", "")
        rulesets = [
            FieldRuleset(
                tags=["130", "240", "243"],
                search=[{"subfields": no_l, "field": "title"}],
            ),
            FieldRuleset(
                tags=["730"],
                text_sfs=no_i,
                search=[{"subfields": no_i, "field": "title"}],
                filter=lambda field: field.indicator2 == "2",
            ),
        ]
        return self.processor.generate_paired_fields(rulesets)

    @property
    def related_title(self) -> list:
        no_i = string.ascii_lowercase.replace("i", "")
        display_sfs = "abcdefgjklmnopqrst"

        def is_a_title(field: pymarc.Field) -> bool:
            return field.get_subfields("t") and field.indicator2 != "2"

        rulesets = [
            FieldRuleset(
                tags=["730"],
                text_sfs=no_i,
                search=[{"subfields": no_i, "field": "title"}],
                filter=lambda field: not field.indicator2,
            ),
            FieldRuleset(
                tags=["700", "710"],
                text_sfs=display_sfs,
                search=[{"subfields": "fjklmnoprst", "field": "title"}],
                filter=is_a_title,
            ),
            FieldRuleset(
                tags=["711"],
                text_sfs=display_sfs,
                search=[{"subfields": "fklmnoprst", "field": "title"}],
                filter=is_a_title,
            ),
        ]
        return self.processor.generate_paired_fields(rulesets)

    @property
    def other_titles(self) -> list:
        """
        Could add "tag" and "linkage" to the output to enable matching up parallel fields
        I wouldn't want to fetch any paired fields from solr then though
        """

        def is_a_title(field: pymarc.Field) -> bool:
            return field.get_subfields("t") and field.indicator2 == "2"

        rulesets = (
            FieldRuleset(
                tags=["246", "247", "740"],
                search=[{"subfields": string.ascii_lowercase, "field": "title"}],
            ),
            FieldRuleset(
                tags=["700", "710"],
                text_sfs="abcdefgjklmnopqrst",
                search=[{"subfields": "fkjlmnoprst", "field": "title"}],
                filter=is_a_title,
            ),
            FieldRuleset(
                tags=["711"],
                text_sfs="abcdefgjklmnopqrst",
                search=[{"subfields": "fklmnoprst", "field": "title"}],
                filter=is_a_title,
            ),
        )

        return self.processor.generate_paired_fields(rulesets)

    @property
    def new_title(self):
        ruleset = FieldRuleset(
            tags=["785"],
            text_sfs="ast",
            search=[
                {"subfields": "a", "field": "author"},
                {"subfields": "st", "field": "title"},
            ],
        )
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def new_title_issn(self):
        ruleset = FieldRuleset(
            tags=["785"],
            text_sfs="x",
        )
        return self.processor.generate_unpaired_fields(tuple([ruleset]))

    @property
    def previous_title(self):
        ruleset = FieldRuleset(
            tags=["780"],
            text_sfs="ast",
            search=[
                {"subfields": "a", "field": "author"},
                {"subfields": "st", "field": "title"},
            ],
        )
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def previous_title_issn(self):
        ruleset = FieldRuleset(
            tags=["780"],
            text_sfs="x",
        )
        return self.processor.generate_unpaired_fields(tuple([ruleset]))

    @property
    def contributors(self):

        def is_not_a_title(field: pymarc.Field) -> bool:
            return not field.get_subfields("t") and field.indicator2 != "2"

        def has_valid_4(field: pymarc.Field) -> bool:
            return not (
                field.get_subfields("e")
                or any(sf.startswith("http") for sf in field.get_subfields("4"))
            )

        def show_4(field: pymarc.Field) -> bool:
            return has_valid_4(field) and is_not_a_title(field)

        def do_not_show_4(field: pymarc.Field) -> bool:
            return not has_valid_4(field) and is_not_a_title(field)

        display_sfs = "abcdegjnqu"
        display_sfs_with_4 = display_sfs + "4"
        search_sfs = "abcdgjnqu"
        search2_sfs = "acdegnqu"
        rulesets = (
            FieldRuleset(
                tags=["700", "710"],
                search=[{"subfields": search_sfs, "field": "author"}],
                text_sfs=display_sfs_with_4,
                browse_sfs=search_sfs,
                filter=show_4,
            ),
            FieldRuleset(
                tags=["711"],
                search=[{"subfields": search2_sfs, "field": "author"}],
                text_sfs=display_sfs_with_4,
                browse_sfs=search2_sfs,
                filter=show_4,
            ),
            FieldRuleset(
                tags=["700", "710"],
                search=[{"subfields": search_sfs, "field": "author"}],
                text_sfs=display_sfs,
                browse_sfs=search_sfs,
                filter=do_not_show_4,
            ),
            FieldRuleset(
                tags=["711"],
                search=[{"subfields": search2_sfs, "field": "author"}],
                text_sfs=display_sfs,
                browse_sfs=search2_sfs,
                filter=do_not_show_4,
            ),
        )

        return self.processor.generate_paired_fields(tuple(rulesets))

    @property
    def created(self):
        rulesets = (
            FieldRuleset(tags=["264"], filter=lambda field: field.indicator2 == "0"),
        )

        return self.processor.generate_paired_fields(rulesets)

    @property
    def distributed(self):
        rulesets = (
            FieldRuleset(tags=["264"], filter=lambda field: field.indicator2 == "2"),
        )

        return self.processor.generate_paired_fields(rulesets)

    @property
    def manufactured(self):
        rulesets = (
            FieldRuleset(tags=["260"], text_sfs="efg"),
            FieldRuleset(tags=["264"], filter=lambda field: field.indicator2 == "3"),
        )

        return self.processor.generate_paired_fields(rulesets)

    @property
    def series(self):
        ruleset = FieldRuleset(tags=["400", "410", "411", "440", "490"])
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def series_statement(self):
        ruleset = FieldRuleset(tags=["440", "800", "810", "811", "830"])
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def biography_history(self):
        ruleset = FieldRuleset(tags=["545"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def summary(self):
        ruleset = FieldRuleset(
            tags=["520"],
            text_sfs="abc3",
            filter=lambda field: field.indicator1 != "4",
        )
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def in_collection(self):
        rulesets = (
            FieldRuleset(
                tags=["773"],
                text_sfs="t",
                search=[{"subfields": "w", "field": "isn"}],
                filter=lambda field: field.get("t"),
            ),
            FieldRuleset(
                tags=["773"],
                text_sfs="w",
                search=[{"subfields": "w", "field": "isn"}],
                filter=lambda field: not field.get("t"),
            ),
        )
        return self.processor.generate_paired_fields(rulesets)

    @property
    def access(self):
        ruleset = FieldRuleset(tags=["506"], text_sfs="abc")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def finding_aids(self):
        ruleset = FieldRuleset(
            tags=["555"],
            text_sfs="abcd3",
            filter=lambda field: not field.get("u"),
        )
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def terms_of_use(self):
        ruleset = FieldRuleset(tags=["540"])
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def language_note(self):
        ruleset = FieldRuleset(tags=["546"])
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def performers(self):
        ruleset = FieldRuleset(tags=["511"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def date_place_of_event(self):
        ruleset = FieldRuleset(tags=["518"], text_sfs="adop23")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def preferred_citation(self):
        ruleset = FieldRuleset(tags=["524"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def location_of_originals(self):
        ruleset = FieldRuleset(tags=["535"], text_sfs=f"{string.ascii_lowercase}3")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def funding_information(self):
        ruleset = FieldRuleset(tags=["536"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def source_of_acquisition(self):
        ruleset = FieldRuleset(tags=["541"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def related_items(self):
        ruleset = FieldRuleset(tags=["580"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def numbering(self):
        ruleset = FieldRuleset(tags=["362"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def current_publication_frequency(self):
        ruleset = FieldRuleset(tags=["310"], text_sfs="ab")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def former_publication_frequency(self):
        ruleset = FieldRuleset(tags=["321"], text_sfs="ab")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def numbering_notes(self):
        ruleset = FieldRuleset(tags=["515"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def source_of_description_note(self):
        ruleset = FieldRuleset(tags=["588"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def copy_specific_note(self):
        ruleset = FieldRuleset(tags=["590"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def references(self):
        ruleset = FieldRuleset(tags=["510"])
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def copyright_status_information(self):
        ruleset = FieldRuleset(tags=["542"])
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def note(self):
        ruleset = FieldRuleset(
            tags=[
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
            text_sfs="a",
        )
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def arrangement(self):
        ruleset = FieldRuleset(tags=["351"], text_sfs="ab3")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def copyright(self):
        ruleset = FieldRuleset(
            tags=["264"], filter=lambda field: field.indicator2 == "4"
        )

        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def physical_description(self):
        ruleset = FieldRuleset(tags=["300"])
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def map_scale(self):
        ruleset = FieldRuleset(tags=["255"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def reproduction_note(self):
        ruleset = FieldRuleset(tags=["533"], text_sfs=f"{string.ascii_lowercase}35")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def original_version_note(self):
        ruleset = FieldRuleset(tags=["534"], text_sfs=f"{string.ascii_lowercase}35")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def playing_time(self):
        ruleset = FieldRuleset(tags=["306"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def media_format(self):
        ruleset = FieldRuleset(tags=["538"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def audience(self):
        ruleset = FieldRuleset(tags=["521"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def content_advice(self):
        ruleset = FieldRuleset(
            tags=["520"],
            text_sfs="abc3",
            filter=lambda field: field.indicator1 == "4",
        )
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def awards(self):
        ruleset = FieldRuleset(tags=["586"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def production_credits(self):
        ruleset = FieldRuleset(tags=["508"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def bibliography(self):
        ruleset = FieldRuleset(tags=["504"], text_sfs="a")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def publisher_number(self):
        ruleset = FieldRuleset(tags=["028"], text_sfs="ab")
        return self.processor.generate_paired_fields(tuple([ruleset]))

    @property
    def contents(self):
        ruleset = FieldRuleset(tags=["505"])
        return self.processor.generate_paired_fields(tuple([ruleset]))


class BaseRecord(SolrDoc, MARC):
    def __init__(self, data: dict):
        self.data = data
        self.record = pymarc.parse_xml_to_array(io.StringIO(data["fullrecord"]))[0]
        SolrDoc.__init__(self, data)
        MARC.__init__(self, self.record)

    @property
    def marc(self):
        return json.loads(self.record.as_json())

    @property
    def holdings(self):
        holdings_data = json.loads(self.data.get("hol"))
        loans = get_alma_loans(self.id, holdings_data)
        holdings = Holdings(
            holdings_data, bib_id=self.id, record=self.record, loans=loans
        )
        return holdings


class TaggedCitation:
    TAG_MAPPING = [
        {
            "kind": "solr",
            "field": "id",
            "ris": ["ID"],  # should this also be N2?
            "meta": ["id"],
        },
        {
            "kind": "base",
            "field": "bibliography",
            "ris": ["AB"],  # should this also be N2?
            "meta": ["abstract"],
        },
        {
            "kind": "marc",
            "ruleset": FieldRuleset(
                tags=["100", "101", "110", "111", "700", "710", "711"],
                text_sfs="abcdefgjklnpqtu4",
                rstrip_chars=TRIM_CHARS,
            ),
            "ris": ["AU"],
            "meta": ["author"],
        },
        {"kind": "base", "field": "call_number", "ris": ["CN"], "meta": []},
        {
            "kind": "marc",
            "ruleset": FieldRuleset(
                tags=["260"],
                text_sfs="a",
            ),
            "ris": ["CP", "CY"],
            "meta": [],
        },
        {
            "kind": "solr",
            "field": "display_date",
            "ris": ["DA", "PY", "Y1"],
            "meta": ["date", "publication_date", "online_date", "cover_date", "year"],
        },
        {
            "kind": "marc",
            "ruleset": FieldRuleset(
                tags=["700"],
                text_sfs="ab",
                filter=lambda field: (
                    field.indicator1 == "0" and re.match("ed", field.get("e", ""))
                ),
                rstrip_chars=TRIM_CHARS,
            ),
            "ris": ["ED", "A2"],
            "meta": ["editor"],
        },
        {
            "kind": "base",
            "field": "edition",
            "ris": ["ET"],
            "meta": [],
        },
        {
            "kind": "marc",
            "ruleset": FieldRuleset(
                tags=["245"], text_sfs="abnp", rstrip_chars=TRIM_CHARS
            ),
            "ris": ["JF", "T1", "TI"],  # JF seems sus; how do we know it's a journal?
            "meta": ["title", "journal_title"],
        },
        {
            "kind": "base",
            "field": "lc_subjects",
            "ris": ["KW"],
            "meta": ["keywords"],
        },
        {
            "kind": "base",
            "field": "remediated_lc_subjects",
            "ris": ["KW"],
            "meta": ["keywords"],
        },
        {
            "kind": "base",
            "field": "other_subjects",
            "ris": ["KW"],
            "meta": ["keywords"],
        },
        {
            "kind": "solr",
            "field": "hlb3Delimited",
            "ris": ["KW"],
            "meta": ["keywords"],
        },
        {  # are we even using 856s?
            "kind": "marc",
            "ruleset": FieldRuleset(
                tags=["856"],
                text_sfs="u",
            ),
            "ris": ["L2"],
            "meta": ["fulltext_html_url", "abstract_html_url"],
        },
        {
            "kind": "base",
            "field": "language",
            "ris": ["LA"],
            "meta": ["language"],
        },
        {
            "kind": "marc",
            "ruleset": FieldRuleset(
                tags=["300"],
                text_sfs="a",
            ),
            "ris": ["M1", "NV"],
            "meta": ["id"],
        },
        {
            "kind": "base",
            "field": "summary",
            "ris": ["N2"],  # should this also be AB
            "meta": ["abstract"],
        },
        {
            "kind": "base",
            "field": "content_advice",
            "ris": ["N2"],  # should this also be AB
            "meta": ["abstract"],
        },
        {
            "kind": "marc",
            "ruleset": FieldRuleset(
                tags=["264", "260"],
                text_sfs="b",
                rstrip_chars=TRIM_CHARS,
            ),
            "ris": ["PB"],
            "meta": ["publisher"],
        },
        {
            "kind": "base",
            "field": "isbn",
            "ris": ["SN"],
            "meta": ["isbn"],
        },
        {
            "kind": "base",
            "field": "issn",
            "ris": ["SN"],
            "meta": ["issn"],
        },
        # should we include report_number or gov_doc_number?
        {
            "kind": "base",
            "field": "previous_title",
            "ris": ["T2"],
            "meta": ["journal_title", "book_title", "conference", "conference_title"],
        },
        {"kind": "base", "field": "series", "ris": ["T3"], "meta": ["series_title"]},
    ]

    TYPE_MAPPING = {
        "archival material manuscript": "MANSCPT",
        "article": "JOUR",
        "atlas": "MAP",
        "audio": "SOUND",
        "audio (music)": "MUSIC",
        "audio (spoken word)": "SOUND",
        "audio cd": "SOUND",
        "audio lp": "SOUND",
        "audio recording": "SOUND",
        "book": "BOOK",
        "book / ebook": "BOOK",
        "book chapter": "CHAP",
        "cdrom": "DBASE",
        "computer file": "DBASE",
        "conference": "CONF",
        "conference proceeding": "CONF",
        "data file": "DBASE",
        "data set": "DBASE",
        "dictionaries": "DICT",
        "dissertation": "THES",
        "ebook": "EBOOK",
        "electronic resource": "WEB",
        "encyclopedias": "ENCYC",
        "gen": "GEN",
        "government document": "GOVDOC",
        "image": "ADVS",
        "internet communication": "ICOMM",
        "journal": "JFULL",
        "journal / ejournal": "JFULL",
        "journal article": "JOUR",
        "magazine": "MGZN",
        "magazine article": "MGZN",
        "map": "MAP",
        "maps-atlas": "MAP",
        "motion picture": "VIDEO",
        "music": "MUSIC",
        "music recording": "MUSIC",
        "musical score": "MUSIC",
        "music score": "MUSIC",
        "newsletter": "NEWS",
        "newsletter article": "NEWS",
        "newsletter articles": "NEWS",
        "newspaper": "NEWS",
        "newspaper article": "NEWS",
        "newspaper articles": "NEWS",
        "paper": "CPAPER",
        "patent": "PAT",
        "publication article": "JOUR",
        "reference entry": "JOUR",
        "report": "RPRT",
        "review": "JOUR",
        "serial": "SER",
        "sheet music": "MUSIC",
        "software": "DBASE",
        "spoken word recording": "SOUND",
        "streaming audio": "SOUND",
        "streaming video": "VIDEO",
        "student thesis": "THES",
        "text resource": "JOUR",
        "thesis": "THES",
        "trade publication article": "JOUR",
        "video": "VIDEO",
        "video recording": "VIDEO",
        "video (blu-ray)": "VIDEO",
        "video (dvd)": "VIDEO",
        "video (vhs)": "VIDEO",
        "video games": "VIDEO",
        "web resource": "WEB",
    }

    def __init__(
        self, marc_record, base_record, solr_doc={}, type_mapping=TYPE_MAPPING
    ):
        self.solr_processor = SolrDocProcessor(solr_doc)
        self.processor = Processor(marc_record)
        self.base_record = base_record
        self.type_mapping = type_mapping

    def to_list(self, tag_mapping=TAG_MAPPING):
        result = [self._type()]
        result += self._non_record_tags()
        for element in tag_mapping:
            for x in self._get_result(element):
                result.append(x)

        result += self._end_record_tag()

        return result

    def _get_result(self, element):
        match element["kind"]:
            case "base":
                contents = self._get_base_content(element)
            case "solr":
                contents = self._get_solr_content(element)
            case _:
                contents = self._get_marc_content(element)

        return [
            {"content": content, "ris": element["ris"], "meta": element["meta"]}
            for content in contents
        ]

    def _type(self):
        formats = (
            self.solr_processor.get_list("format")
            if self.solr_processor.get_list("format")
            else ["Article"]
        )

        formats = [f.lower() for f in formats]
        content = "GEN"
        for f in formats:
            c = self.type_mapping.get(f.lower())
            if c:
                content = c
                break

        return {
            "content": content,
            "ris": ["TY"],
            "meta": [],
        }

    def _get_base_content(self, element):
        field_content_list = getattr(self.base_record, element["field"])
        return self._get_content(field_content_list)

    def _get_marc_content(self, element):
        field_content_list = self.processor.generate_paired_fields(
            rulesets=[element["ruleset"]]
        )
        return self._get_content(field_content_list)

    def _get_solr_content(self, element):
        field_content_list = self.solr_processor.get_list(element["field"])
        return self._get_content(field_content_list)

    def _get_content(self, field_content_list):
        result = []
        for field_value in field_content_list:
            if type(field_value) is str:
                result.append(field_value)
            elif hasattr(field_value, "citation_text"):
                result.append(field_value.citation_text)
            else:
                result.append(field_value["text"])
        return result

    def _non_record_tags(self):
        return [
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

    def _end_record_tag(self):
        return [
            {
                "content": "",
                "ris": ["ER"],
                "meta": [],
            },
        ]


class CSL(BaseCSL):
    TYPE_MAPPING = {
        "Article": "article-journal",
        "Archival Material": "article-journal",
        "Archive": "article-journal",
        "Audio Recording": "article",
        "Clothing": "article",
        "Furnishing": "article",
        "Serial": "article-journal",
        "Government Document": "article",
        "Journal / eJournal": "article-journal",
        "Journal": "article-journal",
        "Magazine": "article-magazine",
        "Market Research": "article-journal",
        "Model": "article",
        "Microform": "article",
        "Mixed Material": "article",
        "Publication": "article-journal",
        "Publication Article": "article-journal",
        "Reference": "article-journal",
        "Spoken Word Recoding": "article",
        "Audio (spoken word)": "article",
        "Standard": "article",
        "Unknown": "article",
        "Trade Publication Article": "article-journal",
        "Transcript": "article",
        "Artifact": "article",
        "Reference Entry": "article-journal",
        "Magazine Article": "article-magazine",
        "Newspaper Article": "article-newspaper",
        "Journal Article": "article-journal",
        "bill": "bill",
        "Biography": "book",
        "Book / eBook": "book",
        "Book": "book",
        "Dictionaries": "book",
        "Directories": "book",
        "Encyclopedias": "book",
        "broadcast": "broadcast",
        "Book Chapter": "chapter",
        "CDROM": "dataset",
        "Computer File": "dataset",
        "Data File": "dataset",
        "Data Set": "dataset",
        "Software": "dataset",
        "Statistics": "dataset",
        "Dataset": "dataset",
        "entry": "entry",
        "entry-dictionary": "entry-dictionary",
        "entry-encyclopedia": "entry-encyclopedia",
        "figure": "figure",
        "Image": "graphic",
        "Photographs and Pictorial Works": "graphic",
        "Photographs & Pictorial Works": "graphic",
        "Photograph": "graphic",
        "Drawing": "graphic",
        "Painting": "graphic",
        "Graphic Arts": "graphic",
        "Visual Material": "graphic",
        "Board Games": "graphic",
        "interview": "interview",
        "legislation": "legislation",
        "Case": "legal_case",
        "Manuscript": "manuscript",
        "Newsletter": "article-newspaper",
        "Newspaper": "article-newspaper",
        "Play": "book",
        "Poem": "book",
        "Postcard": "graphic",
        "Archival Material Manuscript": "manuscript",
        "Atlas": "map",
        "Map": "map",
        "Map-Atlas": "map",
        "Maps-Atlas": "map",
        "Video Recording": "motion_picture",
        "Video (Blu-ray)": "motion_picture",
        "Video (DVD)": "motion_picture",
        "Video (VHS)": "motion_picture",
        "Video Games": "motion_picture",
        "Sheet Music": "musical_score",
        "Music Score": "musical_score",
        "Musical Score": "musical_score",
        "Pamphlet": "pamphlet",
        "Conference": "paper-conference",
        "Conference Proceeding": "paper-conference",
        "Paper": "paper-conference",
        "Patent": "patent",
        "Audio CD": "song",
        "Audio LP": "song",
        "Streaming Audio": "song",
        "Music Recording": "song",
        "Audio": "song",
        "Music": "song",
        "Audio (music)": "song",
        "Motion Picture": "motion_picture",
        "Streaming Video": "motion_picture",
        "Video Game": "motion_picture",
        "Video": "motion_picture",
        "post": "post",
        "post-weblog": "post-weblog",
        "Personal Narrative": "personal_communication",
        "Report": "report",
        "Technical Report": "report",
        "review": "review",
        "Book Review": "review-book",
        "Review": "review-book",
        "Presentation": "speech",
        "Dissertation": "thesis",
        "Student Thesis": "thesis",
        "treaty": "treaty",
        "Electronic Resource": "webpage",
        "Finding Aid": "webpage",
        "Web Resource": "webpage",
        "Text Resource": "article",
        "Newsletter Article": "article",
    }

    def __init__(self, base_record=None, marc_record=None, solr_doc={}):
        self.solr_processor = SolrDocProcessor(solr_doc)
        self.processor = Processor(marc_record)
        self.base_record = base_record

    @property
    def id(self):
        return self.solr_processor.get("id")

    @property
    def title(self):
        rulesets = (
            FieldRuleset(tags=["245"], text_sfs="abp", rstrip_chars=TRIM_CHARS),
        )
        result = self._get_marc_content(rulesets)
        if result is None:
            logger.error(f"missing_csl_title for {self.id}")
            result = ""
        return result

    @property
    def edition(self):
        return self._get_base_content("edition")

    @property
    def collection_title(self):
        return self._get_base_content("series")

    @property
    def isbn(self):
        return self.solr_processor.get("isbn")

    @property
    def issn(self):
        return self.solr_processor.get("issn")

    @property
    def call_number(self):
        result = self.solr_processor.get("callnumber")
        if result:
            return result[0]

    @property
    def publisher_place(self):
        rulesets = (
            FieldRuleset(
                tags=["260"],
                text_sfs="a",
                rstrip_chars=TRIM_CHARS,
            ),
            FieldRuleset(
                tags=["264"],
                text_sfs="a",
                filter=lambda field: field.indicator2 == "1",
                rstrip_chars=TRIM_CHARS,
            ),
        )
        return self._get_marc_content(rulesets)

    @property
    def publisher(self):
        rulesets = (
            FieldRuleset(
                tags=["260"],
                text_sfs="b",
                rstrip_chars=TRIM_CHARS,
            ),
            FieldRuleset(
                tags=["264"],
                text_sfs="b",
                filter=lambda field: field.indicator2 == "1",
                rstrip_chars=TRIM_CHARS,
            ),
        )
        return self._get_marc_content(rulesets)

    @property
    def issued(self):
        date_str = self.solr_processor.get("display_date")
        if date_str:
            return {"literal": date_str}

    @property
    def author(self):
        result = []
        field_e_strings = [
            "ed",
            "ed.",
            "editor",
            "editor.",
            "trans.",
            "translator",
            "translator.",
        ]
        # regular main authors
        main_author_rulesets = (
            FieldRuleset(
                tags=["100", "700"],
                text_sfs="a",
                filter=lambda field: (
                    field.indicator1 == "1" and field.get("e") not in field_e_strings
                ),
                rstrip_chars=TRIM_CHARS,
            ),
            FieldRuleset(
                tags=["100", "700"],
                text_sfs="ab",
                filter=lambda field: (
                    field.indicator1 == "0" and field.get("e") not in field_e_strings
                ),
                rstrip_chars=TRIM_CHARS,
            ),
        )

        result = self._to_author(self._get_marc_contents(main_author_rulesets))
        # corporate authors
        corporate_author_rulesets = (
            FieldRuleset(
                tags=["110", "111", "710", "711"],
                text_sfs="ab",
                filter=lambda field: field.get("e") not in field_e_strings,
                rstrip_chars=TRIM_CHARS,
            ),
        )
        corporate_authors = self._to_literal(
            self._get_marc_contents(corporate_author_rulesets)
        )
        if corporate_authors:
            for c in corporate_authors:
                result.append(c)
        if result:
            return result

    @property
    def editor(self):
        field_e_strings = ["ed", "ed.", "editor", "editor."]
        rulesets = (
            FieldRuleset(
                tags=["700"],
                text_sfs="a",
                filter=lambda field: (
                    field.indicator1 == "1" and field.get("e") in field_e_strings
                ),
                rstrip_chars=TRIM_CHARS,
            ),
            FieldRuleset(
                tags=["700"],
                text_sfs="ab",
                filter=lambda field: (
                    field.indicator1 == "0" and field.get("e") in field_e_strings
                ),
                rstrip_chars=TRIM_CHARS,
            ),
        )
        result = self._to_author(self._get_marc_contents(rulesets))
        if result:
            return result

    @property
    def number(self):
        if self._get_base_content("report_number"):
            return self._get_base_content("report_number")
        return self._get_base_content("numbering")

    def _formats(self):
        return self.solr_processor.get("format")

    def _get_marc_contents(self, rulesets):
        result = self.processor.generate_unpaired_fields(rulesets)
        if result:
            return [r.text for r in result]

    def _get_marc_content(self, rulesets):
        result = self.processor.generate_unpaired_fields(rulesets)
        if result:
            return result[0].text

    def _get_base_content(self, field):
        result = getattr(self.base_record, field)
        if result:
            if hasattr(result[0], "text"):
                return result[0].text
            elif result[0].transliterated:
                return result[0].transliterated.text
            else:
                return result[0].original.text

    def _to_author(self, author_list):
        result = []
        if author_list:
            for name in author_list:
                if ", " in name:
                    family, given = name.split(", ")
                    result.append({"family": family, "given": given})
                else:
                    result.append({"literal": name})
        return result

    def _to_literal(self, string_list):
        if string_list:
            return [{"literal": s} for s in string_list]


class Citation:
    def __init__(self, marc_record, base_record, solr_doc={}):
        self.marc_record = marc_record
        self.base_record = base_record
        self.solr_doc = solr_doc

    @property
    def tagged(self):
        return TaggedCitation(
            marc_record=self.marc_record,
            base_record=self.base_record,
            solr_doc=self.solr_doc,
        ).to_list()

    @property
    def csl(self):
        return CSL(
            marc_record=self.marc_record,
            base_record=self.base_record,
            solr_doc=self.solr_doc,
        )


class Record(BaseRecord):
    def __init__(self, data: dict):
        self.data = data
        self.record = pymarc.parse_xml_to_array(io.StringIO(data["fullrecord"]))[0]
        BaseRecord.__init__(self, data)

    @property
    def citation(self):
        return Citation(marc_record=self.record, base_record=self, solr_doc=self.data)


class OnlinejournalsBaseRecord(BaseRecord):
    @property
    def holdings(self):
        holdings_data = json.loads(self.data.get("hol"))
        # don't need to look for loans
        loans = []
        holdings = Holdings(
            holdings_data, bib_id=self.id, record=self.record, loans=loans
        )
        return holdings


class OnlinejournalsRecord(OnlinejournalsBaseRecord):
    def __init__(self, data: dict, recommended_academic_discipline=None):
        self.data = data
        self.record = pymarc.parse_xml_to_array(io.StringIO(data["fullrecord"]))[0]
        self.recommended_academic_discipline = recommended_academic_discipline
        OnlinejournalsBaseRecord.__init__(self, data)

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
