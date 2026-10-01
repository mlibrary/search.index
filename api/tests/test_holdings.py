import pytest
import pymarc
import json
import io
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from api.holdings import (
    PhysicalHolding,
    ElectronicItem,
    HathiTrustItem,
    AlmaDigitalItem,
    FindingAids,
    FindingAidItem,
    ReservableItem,
    ClementsItem,
    has_physical_holdings,
    AlmaLoans,
    Holdings,
)


@pytest.fixture
def solr_doc():
    bib = {}
    with open("tests/fixtures/land_birds_solr.json") as data:
        bib = json.load(data)
    return bib["response"]["docs"][0]


@pytest.fixture
def holdings_data(solr_doc):
    return json.loads(solr_doc["hol"])


@pytest.fixture
def record(solr_doc):
    marc = solr_doc["fullrecord"]
    return pymarc.parse_xml_to_array(io.StringIO(marc))[0]


@pytest.fixture
def loan_data():
    loan = None
    with open("tests/fixtures/loans/alma_loans_example.json") as data:
        loan = json.load(data)
    return loan


@pytest.fixture
def physical_holdings():
    return [
        {
            "hol_mmsid": "22857812530006381",
            "callnumber": "QL 691 .J3 S25 1983",
            "library": "MUSM",
            "location": "BIR",
            "info_link": "http://lib.umich.edu/locations-and-hours/museums-library",
            "display_name": "Research Museums Center Birds Division",
            "floor_location": "some_floor_location",
            "public_note": None,
            "items": [
                {
                    "barcode": "39015052384248",
                    "library": "SOME_LIBRARY",
                    "location": "SOME_LOCATION",
                    "info_link": "http://lib.umich.edu/locations-and-hours/museums-library",
                    "display_name": "Some display name",
                    "fulfillment_unit": "General",
                    "location_type": "OPEN",
                    "can_reserve": False,
                    "permanent_library": "MUSM",
                    "permanent_location": "BIR",
                    "temp_location": True,
                    "callnumber": "QL 691 .J3 S25 1983",
                    "public_note": "some_public_note",
                    "process_type": "some_process_type",
                    "item_policy": "01",
                    "description": "description",
                    "inventory_number": "inventory_number",
                    "item_id": "23857812520006381",
                    "material_type": "BOOK",
                    "record_has_finding_aid": False,
                }
            ],
            "summary_holdings": None,
            "record_has_finding_aid": False,
        }
    ]


@pytest.fixture
def physical_holding(physical_holdings):
    return physical_holdings[0]


@pytest.fixture
def physical_item(physical_holding):
    return physical_holding["items"][0]


@pytest.fixture
def bib_id():
    "9912345"


def test_has_physical_holdings(holdings_data):
    assert has_physical_holdings(holdings_data) is True


def test_has_physical_holdings_is_false_when_there_are_none(solr_doc):
    assert has_physical_holdings([]) is False


def test_has_physical_holdings_is_false_when_all_elec(holdings_data):
    for h in holdings_data:
        h["library"] = "ELEC"
    assert has_physical_holdings(holdings_data) is False


class TestPhysicalHolding:
    fields = [
        ("holding_id", "hol_mmsid"),
        ("call_number", "callnumber"),
        ("summary", "summary_holdings"),
        ("public_note", "public_note"),
    ]

    @pytest.mark.parametrize("field,solr_field", fields)
    def test_outer_fields(
        self, field, solr_field, physical_holding, bib_id, loans=AlmaLoans()
    ):
        subject = PhysicalHolding(
            physical_holding, bib_id=bib_id, record=record, loans=loans
        )
        assert getattr(subject, field) == physical_holding[solr_field]

    def test_physical_location(self, physical_holding, bib_id):
        subject = PhysicalHolding(
            physical_holding, bib_id=bib_id, record=record, loans=AlmaLoans()
        ).physical_location
        assert subject.url == physical_holding["info_link"]
        assert subject.text == physical_holding["display_name"]
        assert subject.floor == physical_holding["floor_location"]
        assert subject.code.library == physical_holding["library"]
        assert subject.code.location == physical_holding["location"]
        assert subject.temporary is False

    item_fields = [
        ("item_id", "item_id"),
        ("barcode", "barcode"),
        ("fulfillment_unit", "fulfillment_unit"),
        ("call_number", "callnumber"),
        ("process_type", "process_type"),
        ("item_policy", "item_policy"),
        ("description", "description"),
        ("inventory_number", "inventory_number"),
        ("material_type", "material_type"),
        ("reservable", "can_reserve"),
    ]

    @pytest.mark.parametrize("field,solr_field", item_fields)
    def test_items_is_a_list_of_items(
        self, field, solr_field, physical_holding, bib_id, record
    ):
        holding = PhysicalHolding(
            physical_holding, bib_id=bib_id, record=record, loans=AlmaLoans()
        )
        items = holding.items
        subject = items[0]
        expected = physical_holding["items"][0][solr_field]
        assert getattr(subject, field) == expected

    def test_items_finds_loan_info(self, physical_holding, bib_id, record, loan_data):

        holding = PhysicalHolding(
            physical_holding, bib_id=bib_id, record=record, loans=AlmaLoans(loan_data)
        )
        subject = holding.items[0]
        assert subject.process_type == "LOAN"
        assert subject.due_back_at == datetime.fromisoformat("2026-08-28T21:00:00Z")

    def test_items_has_None_due_back_at_when_it_is_not_due(
        self, physical_holding, bib_id, record
    ):
        holding = PhysicalHolding(
            physical_holding, bib_id=bib_id, record=record, loans=AlmaLoans()
        )
        subject = holding.items[0]
        assert subject.process_type == "some_process_type"
        assert subject.due_back_at is None

    def test_item_has_get_this_url(self, physical_holding, bib_id, record):
        item = physical_holding["items"][0]
        subject = PhysicalHolding(
            physical_holding, bib_id=bib_id, record=record, loans=AlmaLoans()
        ).items[0]
        expected = f"https://search.lib.umich.edu/catalog/record/{bib_id}/get-this/{item['barcode']}"
        assert subject.url == expected

    def test_item_has_request_this_url(self, physical_holding, bib_id, record):
        item = physical_holding["items"][0]

        item["can_reserve"] = True
        item["library"] = "SPEC"
        expected = "https://aeon.lib.umich.edu/logon?"
        subject = PhysicalHolding(
            physical_holding, bib_id=bib_id, record=record, loans=AlmaLoans()
        ).items[0]
        assert expected in subject.url

    def test_item_has_a_physical_location(
        self, physical_holding, bib_id, record=record
    ):
        subject = (
            PhysicalHolding(
                physical_holding, bib_id=bib_id, record=record, loans=AlmaLoans()
            )
            .items[0]
            .physical_location
        )
        expected = physical_holding["items"][0]
        assert subject.url == expected["info_link"]
        assert subject.text == expected["display_name"]
        assert subject.floor is None
        assert subject.code.library == expected["library"]
        assert subject.code.location == expected["location"]
        assert subject.temporary is expected["temp_location"]


@pytest.fixture
def electronic_item():
    return {
        "library": "ELEC",
        "link": "https://na04.alma.exlibrisgroup.com/view/uresolver/01UMICH_INST/openurl-UMAA?u.ignore_date_coverage=true&portfolio_pid=531314984450006381&Force_direct=true",
        "link_text": "Available online",
        "campuses": ["ann_arbor", "flint"],
        "interface_name": "Miscellaneous Ejournals",
        "collection_name": "Miscellaneous Ejournals",
        "authentication_note": [
            "Open access for all users.",
            "Authorized U-M users (+ guests in U-M Libraries).",
        ],
        "description": " Available from 2001.",
        "public_note": "Some public note",
        "note": "Miscellaneous Ejournals. Miscellaneous Ejournals. Open access for all users. Authorized U-M users (+ guests in U-M Libraries)",
        "finding_aid": False,
        "status": "Available",
    }


class TestElectronicItem:
    fields = [
        ("url", "link"),
        ("campuses", "campuses"),
        ("interface_name", "interface_name"),
        ("collection_name", "collection_name"),
        ("description", "description"),
        ("public_note", "public_note"),
        ("note", "note"),
    ]

    @pytest.mark.parametrize("field,solr_field", fields)
    def test_outer_fields(self, field, solr_field, electronic_item):
        subject = ElectronicItem(electronic_item)
        assert getattr(subject, field) == electronic_item[solr_field]

    def test_is_available(self, electronic_item):
        subject = ElectronicItem(electronic_item)
        assert subject.is_available is True

    def test_is_available_when_unavailable(self, electronic_item):
        electronic_item["status"] = "Not Available"
        electronic_item["link_text"] = "Not Available"
        subject = ElectronicItem(electronic_item)
        assert subject.is_available is False

    def test_is_available_when_link_text_is_Available_Online(self, electronic_item):
        electronic_item["link_text"] = "Available online"
        electronic_item["status"] = None
        subject = ElectronicItem(electronic_item)
        assert subject.is_available is True


@pytest.fixture
def finding_aid_item():
    return {
        "link": "http://quod.lib.umich.edu/c/clementsead/umich-wcl-M-341gag?view=text",
        "library": "ELEC",
        "link_text": "Finding aid",
        "description": "Thomas Gage Papers",
        "finding_aid": True,
    }


@pytest.fixture
def finding_aid_physical_holding():
    return {
        "hol_mmsid": "22900647900006381",
        "callnumber": "Manuscripts",
        "library": "CLEM",
        "location": "NONE",
        "info_link": "https://clements.umich.edu/",
        "display_name": "William L. Clements",
        "floor_location": "",
        "public_note": [],
        "items": [
            {
                "barcode": "B4555680",
                "library": "CLEM",
                "location": "NONE",
                "info_link": "https://clements.umich.edu/",
                "display_name": "William L. Clements",
                "fulfillment_unit": "Limited",
                "location_type": "CLOSED",
                "can_reserve": False,
                "permanent_library": "CLEM",
                "permanent_location": "NONE",
                "temp_location": False,
                "callnumber": "Manuscripts M-341",
                "public_note": None,
                "process_type": None,
                "item_policy": None,
                "description": None,
                "inventory_number": None,
                "item_id": "23900647890006381",
                "material_type": "MIXED",
                "record_has_finding_aid": True,
            }
        ],
        "summary_holdings": None,
        "record_has_finding_aid": True,
    }


class TestFindingAids:
    def test_location(self, finding_aid_physical_holding, finding_aid_item):
        subject = FindingAids(
            physical_holding=finding_aid_physical_holding,
            items=[finding_aid_item],
        )
        assert subject.physical_location.text == "William L. Clements"

    def test_items(self, finding_aid_physical_holding, finding_aid_item):
        subject = FindingAids(
            physical_holding=finding_aid_physical_holding,
            items=[finding_aid_item],
        )
        assert subject.items[0].url == finding_aid_item["link"]


class TestFindingAidItem:
    def test_url(self, finding_aid_item, finding_aid_physical_holding):
        subject = FindingAidItem(
            finding_aid_item_data=finding_aid_item,
            physical_holding=finding_aid_physical_holding,
        )
        assert subject.url == finding_aid_item["link"]

    def test_decription(self, finding_aid_item, finding_aid_physical_holding):
        subject = FindingAidItem(
            finding_aid_item_data=finding_aid_item,
            physical_holding=finding_aid_physical_holding,
        )
        assert subject.description == finding_aid_item["description"]

    def test_call_number(self, finding_aid_item, finding_aid_physical_holding):
        subject = FindingAidItem(
            finding_aid_item_data=finding_aid_item,
            physical_holding=finding_aid_physical_holding,
        )
        assert subject.call_number == "Manuscripts M-341"

    def test_call_number_handles_missing_item(
        self, finding_aid_item, finding_aid_physical_holding
    ):
        finding_aid_physical_holding["items"] = None
        subject = FindingAidItem(
            finding_aid_item_data=finding_aid_item,
            physical_holding=finding_aid_physical_holding,
        )
        assert subject.call_number is None


@pytest.fixture
def ht_item():
    return {
        "id": "mdp.39015040218748",
        "rights": "ic",
        "description": "some_description",
        "collection_code": "MIU",
        "access": False,
        "source": "University of Michigan",
        "status": "Search only (no full text)",
    }


class TestHathiTrustItem:
    fields = ["id", "description", "source", "status"]

    @pytest.mark.parametrize("field", fields)
    def test_outer_fields(self, field, ht_item):
        subject = HathiTrustItem(ht_item)
        assert getattr(subject, field) == ht_item[field]

    def test_url(self, ht_item):
        subject = HathiTrustItem(ht_item)
        assert subject.url == "http://hdl.handle.net/2027/mdp.39015040218748"


def test_search_only_false_ht_items_does_not_include_search_only(ht_item):
    subject = Holdings(
        holdings_data=[{"library": "HathiTrust Digital Library", "items": [ht_item]}],
        ht_search_only=False,
    )
    assert subject.hathi_trust_items == []


def test_search_only_true_ht_items_includes_search_only(ht_item):
    subject = Holdings(
        holdings_data=[{"library": "HathiTrust Digital Library", "items": [ht_item]}],
        ht_search_only=True,
    )
    assert len(subject.hathi_trust_items) == 1


@pytest.fixture
def alma_digital_item():
    return {
        "library": "ALMA_DIGITAL",
        "link": "https://umich.alma.exlibrisgroup.com/discovery/delivery/01UMICH_INST:UMICH/121314984090006381",
        "link_text": "Available online",
        "delivery_description": "1 file/s (pdf)",
        "label": "Some Label",
        "public_note": "Access requires institutional login. Authorized U-M users (no guest access).",
    }


class TestAlmaDigitalItem:
    fields = [
        ("url", "link"),
        ("delivery_description", "delivery_description"),
        ("label", "label"),
        ("public_note", "public_note"),
    ]

    @pytest.mark.parametrize("field,solr_field", fields)
    def test_outer_fields(self, field, solr_field, alma_digital_item):
        subject = AlmaDigitalItem(alma_digital_item)
        assert getattr(subject, field) == alma_digital_item[solr_field]


@pytest.fixture
def base_reservable_item(record, physical_item):
    record.add_field(
        pymarc.Field(
            tag="022",
            indicators=pymarc.Indicators("0", "1"),
            subfields=[
                pymarc.Subfield(code="y", value="y"),
                pymarc.Subfield(code="z", value="z"),
            ],
        )
    )
    return ReservableItem(record=record, physical_item_data=physical_item)


@pytest.fixture
def base_reservable_item_fields():
    return {
        "Action": "10",
        "Form": "30",
        "callnumber": "QL 691 .J3 S25 1983",
        "genre": "BOOK",
        "title": "山野の鳥 = Concise field guide to land birds /; Sanʼya no tori = Concise field guide to land birds /",
        "author": "佐伯彰光.; Saeki, Akimitsu.",
        "date": "1983",
        "edition": "3訂版.; 3-teiban.",
        "publisher": "日本野鳥の会,; Nihon Yachō no Kai,",
        "place": "東京 :; Tōkyō :",
        "extent": "64 p. : ill. ; 18 cm.",
        "barcode": "39015052384248",
        "description": "description",
        "sysnum": "990008019700106381",
        "location": "SOME_LIBRARY",
        "sublocation": "SOME_LOCATION",
        "fixedshelf": "inventory_number",
        "issn": "y",
        "isbn": "4931150012 :",
    }


class TestReservableItem:
    def test_for_gets_spec(self, record, physical_item):
        physical_item["library"] = "BENT"
        assert (
            "aeon.bentley.umich.edu"
            in ReservableItem.given(record=record, physical_item_data=physical_item).url
        )

    def test_title(self, base_reservable_item):
        assert (
            base_reservable_item.title
            == "山野の鳥 = Concise field guide to land birds /; Sanʼya no tori = Concise field guide to land birds /"
        )

    def test_author_has_original_and_transliterated_with_semicolon_sep(
        self, base_reservable_item
    ):
        assert base_reservable_item.author == "佐伯彰光.; Saeki, Akimitsu."

    def test_author_handles_empty_mainauthor(self, record, physical_item):
        record.remove_field(record["100"])
        record.remove_field(record["880"])
        subject = ReservableItem(record=record, physical_item_data=physical_item)
        assert subject.author is None

    def test_date(self, base_reservable_item):
        assert base_reservable_item.date == "1983"

    def test_edition(self, base_reservable_item):
        assert base_reservable_item.edition == "3訂版.; 3-teiban."

    def test_publisher(self, base_reservable_item):
        assert base_reservable_item.publisher == "日本野鳥の会,; Nihon Yachō no Kai,"

    def test_place(self, base_reservable_item):
        assert base_reservable_item.place == "東京 :; Tōkyō :"

    def test_extent(self, base_reservable_item):
        assert base_reservable_item.extent == "64 p. : ill. ; 18 cm."

    def test_genre(self, base_reservable_item):
        assert base_reservable_item.genre == "BOOK"

    def test_barcode(self, base_reservable_item):
        assert base_reservable_item.barcode == "39015052384248"

    def test_description(self, base_reservable_item):
        assert base_reservable_item.description == "description"

    def test_sysnum(self, base_reservable_item):
        assert base_reservable_item.sysnum == "990008019700106381"

    def test_isbn_gets_first_value(self, base_reservable_item):
        assert base_reservable_item.isbn == "4931150012 :"

    def test_issn_gets_first_value(self, base_reservable_item):
        assert base_reservable_item.issn == "y"

    def test_library_code(self, base_reservable_item):
        assert base_reservable_item.library_code == "SOME_LIBRARY"

    def test_location_code(self, base_reservable_item):
        assert base_reservable_item.location_code == "SOME_LOCATION"

    def test_call_number(self, base_reservable_item):
        assert base_reservable_item.call_number == "QL 691 .J3 S25 1983"

    def test_inventory_number(self, base_reservable_item):
        assert base_reservable_item.inventory_number == "inventory_number"

    def test_fields(self, base_reservable_item, base_reservable_item_fields):
        assert base_reservable_item.fields == base_reservable_item_fields

    def test_url_does_not_include_none_values(self, record, physical_item):
        subject = ReservableItem(record=record, physical_item_data=physical_item)
        assert "issn" not in parse_qs(urlparse(subject.url).query)

    def test_url_includes_appropriate_query_params(
        self, base_reservable_item, base_reservable_item_fields
    ):
        url_parts = urlparse(base_reservable_item.url)
        subject = parse_qs(url_parts.query)
        for key in base_reservable_item_fields.keys():
            assert subject[key][0] == base_reservable_item_fields[key]

    def test_clements_restricted(self, record, physical_item):
        record.add_field(
            pymarc.Field(
                tag="506",
                indicators=pymarc.Indicators("0", "1"),
                subfields=[
                    pymarc.Subfield(code="a", value="a"),
                    pymarc.Subfield(code="b", value="b"),
                    pymarc.Subfield(code="c", value="c"),
                    pymarc.Subfield(code="d", value="d"),
                ],
            )
        )
        subject = ClementsItem(record=record, physical_item_data=physical_item)
        assert subject.restricted == "a b c"
        assert subject.fields["accessrestricted"] == "a b c"

    def test_clements_genre(self, record, physical_item):
        subject = ClementsItem(record=record, physical_item_data=physical_item)
        assert subject.genre == "Book"

    def test_clements_author(self, record, physical_item):
        record.remove_field(record["100"])
        record.remove_field(record["880"])
        record.add_field(
            pymarc.Field(
                tag="110",
                indicators=pymarc.Indicators("0", "1"),
                subfields=[
                    pymarc.Subfield(code="a", value="a"),
                    pymarc.Subfield(code="b", value="b"),
                    pymarc.Subfield(code="c", value="c"),
                    pymarc.Subfield(code="d", value="d"),
                ],
            )
        )
        subject = ClementsItem(record=record, physical_item_data=physical_item)
        assert subject.author == "a b"
