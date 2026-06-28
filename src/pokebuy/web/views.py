from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from pokebuy.db import models as db


@dataclass(frozen=True)
class ProductSummary:
    id: str
    source_product_id: str
    title: str | None
    url: str
    image_url: str | None
    availability: str
    price_cents: int | None
    currency: str | None
    fetch_status: str
    fetch_error: str | None
    observed_at: datetime
    snapshot_id: str


@dataclass(frozen=True)
class SnapshotSummary:
    id: str
    product_id: str
    source_product_id: str
    product_title: str | None
    availability: str
    price_cents: int | None
    currency: str | None
    fetch_status: str
    fetch_error: str | None
    observed_at: datetime


@dataclass(frozen=True)
class DashboardStats:
    product_count: int
    snapshot_count: int
    in_stock_count: int
    blocked_or_error_count: int


def dashboard_stats(session: Session) -> DashboardStats:
    product_count = session.scalar(select(func.count()).select_from(db.Product)) or 0
    snapshot_count = session.scalar(select(func.count()).select_from(db.ProductSnapshot)) or 0
    in_stock_count = (
        session.scalar(
            select(func.count())
            .select_from(db.ProductSnapshot)
            .where(db.ProductSnapshot.availability == "in_stock")
        )
        or 0
    )
    blocked_or_error_count = (
        session.scalar(
            select(func.count())
            .select_from(db.ProductSnapshot)
            .where(db.ProductSnapshot.fetch_status.in_(["blocked", "error"]))
        )
        or 0
    )
    return DashboardStats(
        product_count=product_count,
        snapshot_count=snapshot_count,
        in_stock_count=in_stock_count,
        blocked_or_error_count=blocked_or_error_count,
    )


def list_current_products(session: Session, *, limit: int = 100) -> list[ProductSummary]:
    latest_observed = (
        select(
            db.ProductSnapshot.product_id,
            func.max(db.ProductSnapshot.observed_at).label("observed_at"),
        )
        .group_by(db.ProductSnapshot.product_id)
        .subquery()
    )
    latest_ids = (
        select(
            db.ProductSnapshot.product_id,
            func.max(db.ProductSnapshot.id).label("snapshot_id"),
        )
        .join(
            latest_observed,
            (db.ProductSnapshot.product_id == latest_observed.c.product_id)
            & (db.ProductSnapshot.observed_at == latest_observed.c.observed_at),
        )
        .group_by(db.ProductSnapshot.product_id)
        .subquery()
    )

    rows = session.execute(
        select(db.Product, db.ProductSnapshot)
        .join(latest_ids, db.Product.id == latest_ids.c.product_id)
        .join(db.ProductSnapshot, db.ProductSnapshot.id == latest_ids.c.snapshot_id)
        .order_by(desc(db.ProductSnapshot.observed_at))
        .limit(limit)
    ).all()

    return [_product_summary(product, snapshot) for product, snapshot in rows]


def recent_snapshots(session: Session, *, limit: int = 20) -> list[SnapshotSummary]:
    rows = session.execute(
        select(db.Product, db.ProductSnapshot)
        .join(db.ProductSnapshot, db.ProductSnapshot.product_id == db.Product.id)
        .order_by(desc(db.ProductSnapshot.observed_at))
        .limit(limit)
    ).all()
    return [_snapshot_summary(product, snapshot) for product, snapshot in rows]


def get_product_summary(session: Session, product_id: str) -> ProductSummary | None:
    rows = session.execute(
        select(db.Product, db.ProductSnapshot)
        .join(db.ProductSnapshot, db.ProductSnapshot.product_id == db.Product.id)
        .where(db.Product.id == product_id)
        .order_by(desc(db.ProductSnapshot.observed_at))
        .limit(1)
    ).all()
    if not rows:
        return None
    product, snapshot = rows[0]
    return _product_summary(product, snapshot)


def product_snapshots(
    session: Session,
    product_id: str,
    *,
    limit: int = 100,
) -> list[SnapshotSummary]:
    rows = session.execute(
        select(db.Product, db.ProductSnapshot)
        .join(db.ProductSnapshot, db.ProductSnapshot.product_id == db.Product.id)
        .where(db.Product.id == product_id)
        .order_by(desc(db.ProductSnapshot.observed_at))
        .limit(limit)
    ).all()
    return [_snapshot_summary(product, snapshot) for product, snapshot in rows]


def _product_summary(product: db.Product, snapshot: db.ProductSnapshot) -> ProductSummary:
    return ProductSummary(
        id=product.id,
        source_product_id=product.source_product_id,
        title=product.title,
        url=product.url,
        image_url=product.image_url,
        availability=snapshot.availability,
        price_cents=snapshot.price_cents,
        currency=snapshot.currency,
        fetch_status=snapshot.fetch_status,
        fetch_error=snapshot.fetch_error,
        observed_at=snapshot.observed_at,
        snapshot_id=snapshot.id,
    )


def _snapshot_summary(product: db.Product, snapshot: db.ProductSnapshot) -> SnapshotSummary:
    return SnapshotSummary(
        id=snapshot.id,
        product_id=product.id,
        source_product_id=product.source_product_id,
        product_title=product.title,
        availability=snapshot.availability,
        price_cents=snapshot.price_cents,
        currency=snapshot.currency,
        fetch_status=snapshot.fetch_status,
        fetch_error=snapshot.fetch_error,
        observed_at=snapshot.observed_at,
    )
