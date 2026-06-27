from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from pokebuy.db.models import Base, ProductSnapshot
from pokebuy.db.repository import ProductRepository
from pokebuy.models import Availability, FetchStatus, ProductObservation


def test_repository_persists_failed_snapshot() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        persisted = ProductRepository(session).save_observation(
            ProductObservation(
                source_product_id="10-10318-142",
                url="https://www.pokemoncenter.com/product/10-10318-142/example",
                slug="example",
                availability=Availability.UNKNOWN,
                fetch_status=FetchStatus.BLOCKED,
                fetch_error="blocked",
            )
        )
        session.commit()

        snapshot = session.scalars(select(ProductSnapshot)).one()

    assert persisted.fetch_status == FetchStatus.BLOCKED
    assert snapshot.fetch_error == "blocked"


def test_repository_persists_successful_snapshot() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        persisted = ProductRepository(session).save_observation(
            ProductObservation(
                source_product_id="10-10180-101",
                url="https://www.pokemoncenter.com/product/10-10180-101/example",
                slug="example",
                title="Pokemon TCG: Example Product",
                availability=Availability.IN_STOCK,
                price_cents=799,
                currency="USD",
            )
        )
        session.commit()

        snapshot = session.scalars(select(ProductSnapshot)).one()

    assert persisted.fetch_status == FetchStatus.SUCCESS
    assert persisted.availability == Availability.IN_STOCK
    assert snapshot.price_cents == 799
