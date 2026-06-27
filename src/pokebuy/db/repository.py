from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from pokebuy.db import models as db
from pokebuy.models import (
    Availability,
    FetchStatus,
    PersistedSnapshot,
    ProductObservation,
    ProductVariantObservation,
    new_uuid,
)


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_observation(self, observation: ProductObservation) -> PersistedSnapshot:
        now = datetime.now(UTC)
        product = self._product_for_observation(observation, now)
        variant = (
            self._variant_for_observation(product, observation.variants[0], now)
            if observation.variants
            else None
        )

        snapshot = db.ProductSnapshot(
            id=new_uuid(),
            product_id=product.id,
            variant_id=variant.id if variant else None,
            observed_at=observation.observed_at,
            availability=observation.availability.value,
            price_cents=observation.price_cents,
            currency=observation.currency,
            quantity_limit=observation.quantity_limit,
            raw_state=observation.raw_state,
            collector_version=observation.collector_version,
            fetch_status=observation.fetch_status.value,
            fetch_error=observation.fetch_error,
        )
        self._session.add(snapshot)
        self._session.flush()

        return PersistedSnapshot(
            product_id=UUID(product.id),
            snapshot_id=UUID(snapshot.id),
            source_product_id=product.source_product_id,
            url=product.url,
            title=product.title,
            availability=Availability(snapshot.availability),
            price_cents=snapshot.price_cents,
            currency=snapshot.currency,
            fetch_status=FetchStatus(snapshot.fetch_status),
            fetch_error=snapshot.fetch_error,
            observed_at=snapshot.observed_at,
        )

    def _product_for_observation(
        self, observation: ProductObservation, now: datetime
    ) -> db.Product:
        stmt = select(db.Product).where(
            db.Product.source == observation.source,
            db.Product.source_product_id == observation.source_product_id,
        )
        product = self._session.scalars(stmt).one_or_none()
        if product is None:
            product = db.Product(
                id=new_uuid(),
                source=observation.source,
                source_product_id=observation.source_product_id,
                url=observation.url,
                slug=observation.slug,
                title=observation.title,
                category=observation.category,
                image_url=observation.image_url,
                created_at=now,
                updated_at=now,
            )
            self._session.add(product)
            self._session.flush()
            return product

        product.url = observation.url
        product.slug = observation.slug
        product.updated_at = now
        if observation.title:
            product.title = observation.title
        if observation.category:
            product.category = observation.category
        if observation.image_url:
            product.image_url = observation.image_url
        return product

    def _variant_for_observation(
        self,
        product: db.Product,
        variant_observation: ProductVariantObservation,
        now: datetime,
    ) -> db.ProductVariant:
        stmt = select(db.ProductVariant).where(
            db.ProductVariant.product_id == product.id,
            db.ProductVariant.source_variant_id == variant_observation.source_variant_id,
        )
        variant = self._session.scalars(stmt).one_or_none()
        if variant is None:
            variant = db.ProductVariant(
                id=new_uuid(),
                product_id=product.id,
                source_variant_id=variant_observation.source_variant_id,
                sku=variant_observation.sku,
                title=variant_observation.title,
                attributes=variant_observation.attributes,
                created_at=now,
                updated_at=now,
            )
            self._session.add(variant)
            self._session.flush()
            return variant

        variant.sku = variant_observation.sku
        variant.title = variant_observation.title
        variant.attributes = variant_observation.attributes
        variant.updated_at = now
        return variant
