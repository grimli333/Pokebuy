from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("source", "source_product_id", name="uq_products_source_product"),
        Index("ix_products_url", "url"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(64))
    source_product_id: Mapped[str] = mapped_column(String(128))
    url: Mapped[str] = mapped_column(String(1024))
    slug: Mapped[str | None] = mapped_column(String(256))
    title: Mapped[str | None] = mapped_column(String(512))
    category: Mapped[str | None] = mapped_column(String(256))
    image_url: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product")
    snapshots: Mapped[list["ProductSnapshot"]] = relationship(back_populates="product")


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "source_variant_id", name="uq_variants_product_source"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    source_variant_id: Mapped[str] = mapped_column(String(128))
    sku: Mapped[str | None] = mapped_column(String(128))
    title: Mapped[str | None] = mapped_column(String(512))
    attributes: Mapped[dict[str, str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    product: Mapped[Product] = relationship(back_populates="variants")
    snapshots: Mapped[list["ProductSnapshot"]] = relationship(back_populates="variant")


class ProductSnapshot(Base):
    __tablename__ = "product_snapshots"
    __table_args__ = (Index("ix_product_snapshots_product_observed", "product_id", "observed_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[str | None] = mapped_column(ForeignKey("product_variants.id"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    availability: Mapped[str] = mapped_column(String(32))
    price_cents: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str | None] = mapped_column(String(8))
    quantity_limit: Mapped[int | None] = mapped_column(Integer)
    raw_state: Mapped[dict[str, object]] = mapped_column(JSON)
    collector_version: Mapped[str] = mapped_column(String(64))
    fetch_status: Mapped[str] = mapped_column(String(32))
    fetch_error: Mapped[str | None] = mapped_column(Text)

    product: Mapped[Product] = relationship(back_populates="snapshots")
    variant: Mapped[ProductVariant | None] = relationship(back_populates="snapshots")


class SchedulerRun(Base):
    __tablename__ = "scheduler_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_name: Mapped[str] = mapped_column(String(128))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))
    error: Mapped[str | None] = mapped_column(Text)
