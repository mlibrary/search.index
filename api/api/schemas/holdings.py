from pydantic import BaseModel
from typing import Optional
import datetime


class AlmaDigitalItem(BaseModel):
    url: str
    delivery_description: str | None
    label: str | None
    public_note: str | None


class HathiTustItem(BaseModel):
    id: str
    url: str
    description: str | None
    source: str
    status: str


class ElectronicItem(BaseModel):
    url: str | None
    campuses: list[str]
    interface_name: str | None
    collection_name: str | None
    description: str | None
    public_note: str | None
    note: str | None
    is_available: bool


class LibLoc(BaseModel):
    library: str | None
    location: str | None


class PhysicalLocation(BaseModel):
    url: str | None
    text: str | None
    floor: Optional[str] = None
    code: LibLoc
    temporary: bool


class FindingAidItem(BaseModel):
    url: str | None
    call_number: str | None
    description: str | None


class FindingAids(BaseModel):
    physical_location: PhysicalLocation | None
    items: list[FindingAidItem]


class PhysicalItem(BaseModel):
    item_id: str
    barcode: str | None
    fulfillment_unit: str
    call_number: str | None
    process_type: str | None
    due_back_at: datetime.datetime | None
    item_policy: str | None
    description: str | None
    inventory_number: str | None
    material_type: str | None
    reservable: bool
    physical_location: PhysicalLocation | None
    url: str | None


class PhysicalHolding(BaseModel):
    holding_id: str | None
    call_number: str | None
    summary: list[str] | None
    public_note: list[str] | None
    physical_location: PhysicalLocation
    items: list[PhysicalItem]


class Holdings(BaseModel):
    hathi_trust_items: list[HathiTustItem]
    alma_digital_items: list[AlmaDigitalItem]
    electronic_items: list[ElectronicItem]
    finding_aids: FindingAids | None
    physical: list[PhysicalHolding]


class OnlinejournalsHoldings(BaseModel):
    electronic_items: list[ElectronicItem]


class ArticleHolding(BaseModel):
    source: str
    availability: str
    url: str
