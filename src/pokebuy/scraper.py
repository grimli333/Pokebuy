from typing import Literal

from pokebuy.collectors.browser import PokemonCenterBrowserFetcher
from pokebuy.collectors.fetcher import FetchResult, PokemonCenterFetcher
from pokebuy.collectors.pokemon_center import PokemonCenterProductParser
from pokebuy.config import Settings
from pokebuy.db.repository import ProductRepository
from pokebuy.db.session import create_db_engine, create_session_factory, session_scope
from pokebuy.models import PersistedSnapshot, ProductObservation
from pokebuy.urls import normalize_product_url

CollectorMode = Literal["http", "browser", "auto"]


def collect_product_url(
    raw_url: str,
    settings: Settings,
    *,
    collector_mode: CollectorMode = "http",
    browser_headless: bool | None = None,
    browser_manual_wait_seconds: float | None = None,
    browser_use_profile: bool = False,
) -> tuple[ProductObservation, FetchResult]:
    normalized = normalize_product_url(raw_url)
    parser = PokemonCenterProductParser()

    if collector_mode == "browser":
        fetch = PokemonCenterBrowserFetcher(
            settings,
            headless=browser_headless,
            manual_wait_seconds=browser_manual_wait_seconds,
            use_persistent_profile=browser_use_profile,
        ).fetch(normalized.canonical_url)
    else:
        fetch = PokemonCenterFetcher(settings).fetch(normalized.canonical_url)
        if collector_mode == "auto" and fetch.fetch_status.value == "blocked":
            fetch = PokemonCenterBrowserFetcher(
                settings,
                headless=browser_headless,
                manual_wait_seconds=browser_manual_wait_seconds,
                use_persistent_profile=browser_use_profile,
            ).fetch(normalized.canonical_url)

    return parser.parse_fetch_result(normalized.canonical_url, fetch), fetch


def scrape_product_url(
    raw_url: str,
    settings: Settings,
    *,
    collector_mode: CollectorMode = "http",
    browser_headless: bool | None = None,
    browser_manual_wait_seconds: float | None = None,
    browser_use_profile: bool = False,
) -> PersistedSnapshot:
    observation, _fetch = collect_product_url(
        raw_url,
        settings,
        collector_mode=collector_mode,
        browser_headless=browser_headless,
        browser_manual_wait_seconds=browser_manual_wait_seconds,
        browser_use_profile=browser_use_profile,
    )

    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        return ProductRepository(session).save_observation(observation)
