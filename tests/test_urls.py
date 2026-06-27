import pytest

from pokebuy.urls import ProductUrlError, normalize_product_url


def test_normalize_product_url() -> None:
    normalized = normalize_product_url(
        "https://pokemoncenter.com/product/10-10318-142/example-product?utm_source=test"
    )

    assert (
        normalized.canonical_url
        == "https://www.pokemoncenter.com/product/10-10318-142/example-product"
    )
    assert normalized.source_product_id == "10-10318-142"
    assert normalized.slug == "example-product"


def test_rejects_non_product_url() -> None:
    with pytest.raises(ProductUrlError):
        normalize_product_url("https://www.pokemoncenter.com/category/trading-card-game")
