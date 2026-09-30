import pymarc
from urllib.parse import urlencode
from dataclasses import dataclass
from datetime import datetime
from api.marc import Processor, FieldRuleset
from api.clients.exlibris_client import AlmaClient


class AlmaDigitalItem:
    def __init__(self, alma_digital_item_data: dict):
        self.data = alma_digital_item_data

    @property
    def url(self):
        return self.data.get("link")

    @property
    def delivery_description(self):
        return self.data.get("delivery_description")

    @property
    def label(self):
        return self.data.get("label")

    @property
    def public_note(self):
        return self.data.get("public_note")


class HathiTrustItem:
    def __init__(self, ht_item_data: dict):
        self.data = ht_item_data

    @property
    def id(self):
        return self.data.get("id")

    @property
    def url(self):
        return f"http://hdl.handle.net/2027/{self.id}"

    @property
    def description(self):
        return self.data.get("description")

    @property
    def source(self):
        return self.data.get("source")

    @property
    def status(self):
        return self.data.get("status")


class ElectronicItem:
    def __init__(self, electronic_item_data: dict):
        self.data = electronic_item_data

    @property
    def url(self):
        return self.data.get("link")

    @property
    def campuses(self):
        return self.data.get("campuses") or []

    @property
    def interface_name(self):
        return self.data.get("interface_name")

    @property
    def collection_name(self):
        return self.data.get("collection_name")

    @property
    def description(self):
        return self.data.get("description")

    @property
    def public_note(self):
        return self.data.get("public_note")

    @property
    def note(self):
        return self.data.get("note")

    @property
    def is_available(self):
        return (
            self.data.get("status") == "Available"
            or self.data.get("link_text") == "Available online"
        )


@dataclass(frozen=True)
class LibLoc:
    library: str
    location: str


@dataclass(frozen=True)
class PhysicalLocation:
    url: str
    text: str = None
    floor: str = None
    code: LibLoc = None
    temporary: bool = False


class PhysicalItem:
    def __init__(
        self,
        physical_item_data: dict,
        bib_id: str,
        record=None,
        loan={},
    ):
        self.loan = loan
        self.data = physical_item_data
        self.bib_id = bib_id
        self.record = record

    @property
    def item_id(self):
        return self.data.get("item_id")

    @property
    def barcode(self):
        return self.data.get("barcode")

    @property
    def fulfillment_unit(self):
        return self.data.get("fulfillment_unit")

    @property
    def call_number(self):
        return self.data.get("callnumber")

    @property
    def process_type(self):
        if self.loan:
            return "LOAN"
        return self.data.get("process_type")

    @property
    def due_back_at(self):
        if self.loan:
            return datetime.fromisoformat(self.loan["due_date"])

    @property
    def item_policy(self):
        return self.data.get("item_policy")

    @property
    def description(self):
        return self.data.get("description")

    @property
    def inventory_number(self):
        return self.data.get("inventory_number")

    @property
    def material_type(self):
        return self.data.get("material_type")

    @property
    def reservable(self):
        return self.data.get("can_reserve")

    @property
    def url(self):
        if self.reservable:
            return ReservableItem.given(
                physical_item_data=self.data, record=self.record
            ).url
            # send over the marc record to some classes that can parse the Reserve This item
        return f"https://search.lib.umich.edu/catalog/record/{self.bib_id}/get-this/{self.barcode}"

    @property
    def physical_location(self):
        return PhysicalLocation(
            url=self.data.get("info_link"),
            text=self.data.get("display_name"),
            code=LibLoc(
                library=self.data.get("library"), location=self.data.get("location")
            ),
            temporary=self.data.get("temp_location"),
        )


class ReservableItem:
    @staticmethod
    def given(physical_item_data, record):
        match physical_item_data["library"]:
            case "BENT":
                cls = BentleyItem
            case "CLEM":
                cls = ClementsItem
            case _:
                cls = ReservableItem

        return cls(physical_item_data, record)

    """
    The rules come a spreadsheet in the issue SEARCH-1421
    """

    def __init__(self, physical_item_data, record):
        self.data = physical_item_data
        self.record = record
        self.processor = Processor(record)

    @property
    def title(self):
        rulesets = [FieldRuleset(tags=["245"], text_sfs="abk")]
        return self._format_paired_fields(rulesets)

    @property
    def author(self):
        rulesets = [
            FieldRuleset(tags=["100", "110"], text_sfs="abcd"),
            FieldRuleset(tags=["111"], text_sfs="anbc"),
            FieldRuleset(tags=["130"], text_sfs="aplskf"),
        ]
        return self._format_paired_fields(rulesets)

    @property
    def date(self):
        rulesets = [
            FieldRuleset(tags=["260", "264"], text_sfs="c"),
            FieldRuleset(tags=["245"], text_sfs="f"),
        ]
        fields = self.processor.generate_unpaired_fields(rulesets)
        if fields:
            return "; ".join([str(f) for f in fields])

    @property
    def edition(self):
        rulesets = [FieldRuleset(tags=["250"], text_sfs="a")]
        return self._format_paired_fields(rulesets)

    @property
    def publisher(self):
        rulesets = [FieldRuleset(tags=["260", "264"], text_sfs="b")]
        return self._format_paired_fields(rulesets)

    @property
    def place(self):
        rulesets = [FieldRuleset(tags=["260", "264"], text_sfs="a")]
        return self._format_paired_fields(rulesets)

    @property
    def extent(self):
        rulesets = [FieldRuleset(tags=["300"], text_sfs="abcf")]
        return self._format_paired_fields(rulesets)

    @property
    def isbn(self):
        """
        This is from the Metadata Component spreadsheet
        """
        rulesets = [
            FieldRuleset(tags=["020"], text_sfs=["a"]),
            FieldRuleset(tags=["020"], text_sfs=["z"]),
        ]
        fields = self.processor.generate_unpaired_fields(rulesets)
        if fields:
            return str(fields[0])

    @property
    def issn(self):
        """
        This is from the Metadata Component spreadsheet
        """
        rulesets = [
            FieldRuleset(tags=["022"], text_sfs=["a"]),
            FieldRuleset(tags=["022"], text_sfs=["y"]),
            FieldRuleset(tags=["022"], text_sfs=["z"]),
            FieldRuleset(tags=["776"], text_sfs=["x"]),
        ]
        fields = self.processor.generate_unpaired_fields(rulesets)
        if fields:
            return str(fields[0])

    @property
    def sysnum(self):
        return self.record["001"].value()

    @property
    def genre(self):
        return self.data.get("material_type")

    @property
    def barcode(self):
        return self.data.get("barcode")

    @property
    def description(self):
        return self.data.get("description")

    @property
    def library_code(self):
        return self.data.get("library")

    @property
    def location_code(self):
        return self.data.get("location")

    @property
    def call_number(self):
        return self.data.get("callnumber")

    @property
    def inventory_number(self):
        return self.data.get("inventory_number")

    @property
    def fields(self):
        return {
            "Action": "10",
            "Form": "30",
            "callnumber": self.call_number,
            "genre": self.genre,
            "title": self.title,
            "author": self.author,
            "date": self.date,
            "edition": self.edition,
            "publisher": self.publisher,
            "place": self.place,
            "extent": self.extent,
            "barcode": self.barcode,
            "description": self.description,
            "sysnum": self.sysnum,
            "location": self.library_code,
            "sublocation": self.location_code,
            "fixedshelf": self.inventory_number,
            "issn": self.issn,
            "isbn": self.isbn,
        }

    @property
    def url(self):
        # get rid of empty fields
        fields = {k: v for k, v in self.fields.items() if v is not None}
        return self.base_url() + urlencode(fields)

    def base_url(self):
        return "https://aeon.lib.umich.edu/logon?"

    def _format_paired_fields(self, rulesets, separator="; "):
        paired_fields = self.processor.generate_paired_fields(rulesets)
        return self._join_paired_fields(paired_fields, separator)

    def _join_paired_fields(self, paired_fields, separator="; "):
        if paired_fields:
            return separator.join(
                [self._join_paired_field(pf, separator) for pf in paired_fields]
            )

    def _join_paired_field(self, paired_field, separator="; "):
        pf = [paired_field.original.text]
        if paired_field.transliterated:
            pf.append(paired_field.transliterated.text)
        return separator.join(pf)


class BentleyItem(ReservableItem):
    def base_url(self):
        return "https://aeon.bentley.umich.edu/login?"


class ClementsItem(ReservableItem):
    def base_url(self):
        return "https://aeon.clements.umich.edu/logon?"

    @property
    def author(self):
        rulesets = [
            FieldRuleset(tags=["100"], text_sfs="abcd"),
            FieldRuleset(tags=["110"], text_sfs="ab"),
            FieldRuleset(tags=["111"], text_sfs="acd"),
            FieldRuleset(tags=["130"], text_sfs="aplskf"),
        ]
        return self._format_paired_fields(rulesets)

    @property
    def genre(self):
        mapping = {
            "BOOK": "Book",
            "ISSBD": "Book",
            "ISSUE": "Book",
            "SCORE": "Graphics",
            "OTHERVM": "Graphics",
            "MIXED": "Manuscripts",
            "ATLAS": "Map",
            "MAP": "Map",
        }
        value = self.data.get("material_type")
        return mapping.get(value)

    @property
    def restricted(self):
        rulesets = [
            FieldRuleset(tags=["506"], text_sfs="abc"),
        ]
        return self._format_paired_fields(rulesets)

    @property
    def fields(self):
        result = super().fields
        result["accessrestricted"] = self.restricted
        return result


class PhysicalHolding:
    def __init__(
        self, physical_holding_data: list, bib_id: str, record: pymarc.Record, loans
    ):
        self.data = physical_holding_data
        self.bib_id = bib_id
        self.record = record
        self.loans = loans

    @property
    def holding_id(self):
        return self.data.get("hol_mmsid")

    @property
    def call_number(self):
        return self.data.get("callnumber")

    @property
    def summary(self):
        return self.data.get("summary_holdings")

    @property
    def public_note(self):
        return self.data.get("public_note")

    @property
    def physical_location(self):
        return PhysicalLocation(
            url=self.data.get("info_link"),
            text=self.data.get("display_name"),
            floor=self.data.get("floor_location"),
            code=LibLoc(
                library=self.data.get("library"), location=self.data.get("location")
            ),
        )

    @property
    def items(self):
        return [
            PhysicalItem(
                item,
                bib_id=self.bib_id,
                record=self.record,
                loan=self.loans.find(item["item_id"]),
            )
            for item in self.data.get("items", [])
        ]


class FindingAids:
    def __init__(self, items: list, physical_holding: dict):
        self.items_data = items
        self.physical_holding = physical_holding  # the holding with one item

    @property
    def physical_location(self):
        return PhysicalLocation(
            url=self.physical_holding.get("info_link"),
            text=self.physical_holding.get("display_name"),
            floor=self.physical_holding.get("floor_location"),
            code=LibLoc(
                library=self.physical_holding.get("library"),
                location=self.physical_holding.get("location"),
            ),
        )

    @property
    def items(self):
        return [
            FindingAidItem(
                finding_aid_item_data=item_data, physical_holding=self.physical_holding
            )
            for item_data in self.items_data
        ]


class FindingAidItem:
    def __init__(self, finding_aid_item_data: dict, physical_holding: dict):
        self.data = finding_aid_item_data
        self.physical_holding = physical_holding  # the holding with one item

    @property
    def url(self):
        return self.data.get("link")

    @property
    def description(self):
        return self.data.get("description")

    @property
    def call_number(self):
        items = self.physical_holding.get("items")
        item = items[0] if items else None
        return item.get("callnumber") if item else None


def kind_of_holding(holding_item: dict):
    match holding_item["library"]:
        case "ALMA_DIGITAL":
            return "alma_digital"
        case "HathiTrust Digital Library":
            return "hathi_trust"
        case "ELEC":
            if holding_item.get("finding_aid"):
                return "finding_aid"
            else:
                return "electronic"
        case _:
            return "physical"


def has_physical_holdings(holdings_data: list):
    return any(kind_of_holding(holding) == "physical" for holding in holdings_data)


async def get_alma_loans(mms_id, holdings_data: list):
    if has_physical_holdings(holdings_data):
        return AlmaLoans((await AlmaClient().get_loans(mms_id)))
    return AlmaLoans()


class AlmaLoans:
    def __init__(self, data={}):
        self.loans = data.get("item_loan", [])

    def find(self, item_id: str):
        return next(
            (item for item in self.loans if item["item_id"] == item_id),
            None,
        )


def physical_holdings(
    holdings_data: list, bib_id: str, record, loans
) -> list[PhysicalHolding]:
    return [
        PhysicalHolding(holding_item, bib_id=bib_id, record=record, loans=loans)
        for holding_item in holdings_data
        if kind_of_holding(holding_item) == "physical"
    ]


def electronic_items(holdings_data: list) -> list[ElectronicItem]:
    return [
        ElectronicItem(holding_item)
        for holding_item in holdings_data
        if kind_of_holding(holding_item) == "electronic"
    ]


def finding_aids(holdings_data: list) -> list[FindingAidItem]:
    physical_holding = None
    for holding in holdings_data:
        if holding.get("record_has_finding_aid"):
            physical_holding = holding

    items = [
        holding_item
        for holding_item in holdings_data
        if kind_of_holding(holding_item) == "finding_aid"
    ]
    if items:
        return FindingAids(physical_holding=physical_holding, items=items)


def alma_digital_items(holdings_data: list) -> list[AlmaDigitalItem]:
    return [
        AlmaDigitalItem(holding_item)
        for holding_item in holdings_data
        if kind_of_holding(holding_item) == "alma_digital"
    ]


def hathi_trust_items(holdings_data: list) -> list[HathiTrustItem]:
    ht_holding = None
    for holding_item in holdings_data:
        if kind_of_holding(holding_item) == "hathi_trust":
            ht_holding = holding_item

    if ht_holding:
        return [HathiTrustItem(item) for item in ht_holding["items"]]
    else:
        return []


class Holdings:
    def __init__(
        self,
        holdings_data: list,
        bib_id: str,
        record: pymarc.Record,
        loans: AlmaLoans = AlmaLoans(),
    ):
        self.data = holdings_data
        self.bib_id = bib_id
        self.record = record
        self.loans = loans

    @property
    def hathi_trust_items(self):
        return hathi_trust_items(self.data)

    @property
    def alma_digital_items(self):
        return alma_digital_items(self.data)

    @property
    def electronic_items(self):
        return electronic_items(self.data)

    @property
    def finding_aids(self):
        return finding_aids(self.data)

    @property
    def physical(self):
        return physical_holdings(self.data, self.bib_id, self.record, self.loans)


class EmptyHoldings:
    def __init__(self):
        self.hathi_trust_items = []
        self.alma_digital_items = []
        self.electronic_items = []
        self.finding_aids = None
        self.physical = []
