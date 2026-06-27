from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Availability(StrEnum):
    UNKNOWN = "unknown"
    OUT_OF_STOCK = "out_of_stock"
    IN_STOCK = "in_stock"
    PREORDER = "preorder"
    BACKORDER = "backorder"
    UNAVAILABLE = "unavailable"


class FetchStatus(StrEnum):
    SUCCESS = "success"
    BLOCKED = "blocked"
    NOT_FOUND = "not_found"
    ERROR = "error"


class NormalizedProductUrl(BaseModel):
    canonical_url: str
    source_product_id: str
    slug: str


class ProductVariantObservation(BaseModel):
    source_variant_id: str
    sku: str | None = None
    title: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


class ProductObservation(BaseModel):
    source: str = "pokemon_center"
    source_product_id: str
    url: str
    slug: str | None = None
    title: str | None = None
    category: str | None = None
    image_url: str | None = None
    variants: list[ProductVariantObservation] = Field(default_factory=list)
    availability: Availability = Availability.UNKNOWN
    price_cents: int | None = None
    currency: str | None = None
    quantity_limit: int | None = None
    raw_state: dict[str, object] = Field(default_factory=dict)
    collector_version: str = "pokemon_center_html_v1"
    fetch_status: FetchStatus = FetchStatus.SUCCESS
    fetch_error: str | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PersistedSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    snapshot_id: UUID
    source_product_id: str
    url: str
    title: str | None
    availability: Availability
    price_cents: int | None
    currency: str | None
    fetch_status: FetchStatus
    fetch_error: str | None
    observed_at: datetime


def new_uuid() -> str:
    return str(uuid4())
