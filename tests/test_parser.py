from pathlib import Path

from pokebuy.collectors.fetcher import FetchResult
from pokebuy.collectors.pokemon_center import PokemonCenterProductParser
from pokebuy.models import Availability, FetchStatus


def fixture(name: str) -> str:
    return Path("tests/fixtures", name).read_text()


def test_parse_in_stock_product_fixture() -> None:
    observation = PokemonCenterProductParser().parse_success(
        "https://www.pokemoncenter.com/product/10-10180-101/pokemon-tcg-eevee-and-umbreon-twilight-card-sleeves-65-sleeves",
        fixture("product_in_stock.html"),
    )

    assert observation.source_product_id == "10-10180-101"
    assert observation.availability == Availability.IN_STOCK
    assert observation.price_cents == 799
    assert observation.currency == "USD"
    assert observation.title == "Pokemon TCG: Eevee & Umbreon Twilight Card Sleeves (65 Sleeves)"


def test_parse_out_of_stock_product_fixture() -> None:
    observation = PokemonCenterProductParser().parse_success(
        "https://www.pokemoncenter.com/product/10-10318-142/pokemon-tcg-mega-evolution-ascended-heroes-mini-tin-togepi-and-totodile",
        fixture("product_out_of_stock.html"),
    )

    assert observation.source_product_id == "10-10318-142"
    assert observation.availability == Availability.OUT_OF_STOCK
    assert observation.price_cents == 999


def test_parse_unknown_product_fixture() -> None:
    observation = PokemonCenterProductParser().parse_success(
        "https://www.pokemoncenter.com/product/10-00000-000/pokemon-tcg-mystery-product",
        fixture("product_unknown.html"),
    )

    assert observation.source_product_id == "10-00000-000"
    assert observation.availability == Availability.UNKNOWN
    assert observation.price_cents == 1299


def test_parse_blocked_fetch_result() -> None:
    fetch = FetchResult(
        url="https://www.pokemoncenter.com/product/10-10318-142/example",
        status_code=403,
        text="Please enable JS",
        fetch_status=FetchStatus.BLOCKED,
        fetch_error="Pokemon Center returned bot-protection or CAPTCHA HTML",
        headers={"x-datadome": "protected", "set-cookie": "secret"},
    )

    observation = PokemonCenterProductParser().parse_fetch_result(
        "https://www.pokemoncenter.com/product/10-10318-142/example",
        fetch,
    )

    assert observation.fetch_status == FetchStatus.BLOCKED
    assert observation.availability == Availability.UNKNOWN
    assert observation.raw_state["response_headers"] == {"x-datadome": "protected"}


def test_parse_not_found_fetch_result() -> None:
    fetch = FetchResult(
        url="https://www.pokemoncenter.com/product/10-404/not-found",
        status_code=404,
        text="<html>not found</html>",
        fetch_status=FetchStatus.NOT_FOUND,
        fetch_error="product page returned 404",
        headers={},
    )

    observation = PokemonCenterProductParser().parse_fetch_result(
        "https://www.pokemoncenter.com/product/10-404/not-found",
        fetch,
    )

    assert observation.fetch_status == FetchStatus.NOT_FOUND
    assert observation.availability == Availability.UNKNOWN
    assert observation.raw_state["http_status"] == 404
