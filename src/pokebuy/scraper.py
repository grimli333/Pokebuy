from pokebuy.collectors.fetcher import PokemonCenterFetcher
from pokebuy.collectors.pokemon_center import PokemonCenterProductParser
from pokebuy.config import Settings
from pokebuy.db.repository import ProductRepository
from pokebuy.db.session import create_db_engine, create_session_factory, session_scope
from pokebuy.models import PersistedSnapshot
from pokebuy.urls import normalize_product_url


def scrape_product_url(raw_url: str, settings: Settings) -> PersistedSnapshot:
    normalized = normalize_product_url(raw_url)
    fetcher = PokemonCenterFetcher(settings)
    parser = PokemonCenterProductParser()
    fetch = fetcher.fetch(normalized.canonical_url)
    observation = parser.parse_fetch_result(normalized.canonical_url, fetch)

    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        return ProductRepository(session).save_observation(observation)
