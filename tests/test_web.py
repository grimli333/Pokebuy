from pathlib import Path

from fastapi.testclient import TestClient

from pokebuy.config import Settings
from pokebuy.db.models import Base
from pokebuy.db.repository import ProductRepository
from pokebuy.db.session import create_db_engine, create_session_factory, session_scope
from pokebuy.models import Availability, ProductObservation, ProductVariantObservation
from pokebuy.web.app import create_app


def test_healthz(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_renders_empty_state(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))

    response = client.get("/")

    assert response.status_code == 200
    assert "Dashboard" in response.text
    assert "No product snapshots have been saved yet." in response.text


def test_products_render_persisted_snapshot(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _save_sample_product(settings)
    client = TestClient(create_app(settings))

    response = client.get("/products")

    assert response.status_code == 200
    assert "Sample Pokemon TCG Product" in response.text
    assert "In Stock" in response.text
    assert "$12.99" in response.text


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'pokebuy.sqlite3'}",
        debug_enabled=False,
        log_file_enabled=False,
    )


def _save_sample_product(settings: Settings) -> None:
    engine = create_db_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    observation = ProductObservation(
        source_product_id="10-00000-001",
        url="https://www.pokemoncenter.com/product/10-00000-001/sample",
        slug="sample",
        title="Sample Pokemon TCG Product",
        image_url="https://example.com/product.jpg",
        variants=[
            ProductVariantObservation(
                source_variant_id="10-00000-001",
                sku="10-00000-001",
                title="Sample Pokemon TCG Product",
            )
        ],
        availability=Availability.IN_STOCK,
        price_cents=1299,
        currency="USD",
    )
    with session_scope(session_factory) as session:
        ProductRepository(session).save_observation(observation)
