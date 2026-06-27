import json
from pathlib import Path
from typing import Annotated

import typer
from alembic import command
from alembic.config import Config

from pokebuy.collectors.browser import warm_pokemon_center_session
from pokebuy.config import get_settings
from pokebuy.db.models import Base
from pokebuy.db.repository import ProductRepository
from pokebuy.db.session import create_db_engine, create_session_factory, session_scope
from pokebuy.logging import configure_logging
from pokebuy.scraper import CollectorMode, collect_product_url

app = typer.Typer(no_args_is_help=True)


@app.command()
def init() -> None:
    """Create local runtime directories and database tables."""

    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.browser_state_dir.mkdir(parents=True, exist_ok=True)
    settings.browser_profile_dir.mkdir(parents=True, exist_ok=True)
    engine = create_db_engine(settings)
    Base.metadata.create_all(engine)
    typer.echo(f"Initialized PokeBuy data directory at {settings.data_dir}")


@app.command()
def migrate() -> None:
    """Run database migrations."""

    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")
    typer.echo("Database migrations applied")


@app.command("scrape-url")
def scrape_url(
    url: Annotated[str, typer.Argument(help="Pokemon Center product URL")],
    collector: Annotated[
        CollectorMode,
        typer.Option(help="Collector mode: http, browser, or auto"),
    ] = "http",
    headless: Annotated[
        bool | None,
        typer.Option(help="Override browser headless mode when using browser collection"),
    ] = None,
    manual_wait_seconds: Annotated[
        float | None,
        typer.Option(help="Seconds to leave a headed browser open before capturing HTML"),
    ] = None,
    use_profile: Annotated[
        bool,
        typer.Option(help="Reuse the persistent PokeBuy browser profile"),
    ] = False,
    print_html: Annotated[
        bool,
        typer.Option(help="Print the raw returned HTML to stderr before the JSON snapshot"),
    ] = False,
    dump_html: Annotated[
        Path | None,
        typer.Option(help="Write the raw returned HTML to this file"),
    ] = None,
    log_level: Annotated[str, typer.Option(help="Logging level")] = "WARNING",
) -> None:
    """Fetch one product URL, persist a snapshot, and print normalized output."""

    configure_logging(log_level)
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    observation, fetch = collect_product_url(
        url,
        settings,
        collector_mode=collector,
        browser_headless=headless,
        browser_manual_wait_seconds=manual_wait_seconds,
        browser_use_profile=use_profile,
    )
    if dump_html is not None:
        dump_html.parent.mkdir(parents=True, exist_ok=True)
        dump_html.write_text(fetch.text, encoding="utf-8")
        typer.echo(f"Wrote returned HTML to {dump_html}", err=True)
    if print_html:
        typer.echo("----- POKEBUY RETURNED HTML BEGIN -----", err=True)
        typer.echo(fetch.text, err=True)
        typer.echo("----- POKEBUY RETURNED HTML END -----", err=True)

    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        snapshot = ProductRepository(session).save_observation(observation)
    typer.echo(json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True))


@app.command("warm-session")
def warm_session(
    url: Annotated[
        str,
        typer.Argument(help="Pokemon Center URL to open for login/challenge capture"),
    ] = "https://www.pokemoncenter.com/",
    headless: Annotated[
        bool | None,
        typer.Option(help="Override browser headless mode"),
    ] = None,
    manual_wait_seconds: Annotated[
        float,
        typer.Option(help="Seconds to leave the browser open for manual login/challenge work"),
    ] = 300.0,
) -> None:
    """Open a persistent browser profile and save Pokemon Center session state."""

    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    message = warm_pokemon_center_session(
        settings,
        url=url,
        headless=headless,
        manual_wait_seconds=manual_wait_seconds,
    )
    typer.echo(message)


@app.command("show-config")
def show_config() -> None:
    """Print non-secret runtime paths and polling configuration."""

    settings = get_settings()
    payload = {
        "env": settings.env,
        "database_url": settings.database_url,
        "data_dir": str(Path(settings.data_dir)),
        "browser_state_dir": str(Path(settings.browser_state_dir)),
        "browser_profile_dir": str(Path(settings.browser_profile_dir)),
        "poll_min_seconds": settings.poll_min_seconds,
        "http_timeout_seconds": settings.http_timeout_seconds,
        "browser_timeout_seconds": settings.browser_timeout_seconds,
        "browser_manual_wait_seconds": settings.browser_manual_wait_seconds,
        "browser_headless": settings.browser_headless,
        "auto_cart_enabled": settings.auto_cart_enabled,
        "auto_checkout_enabled": settings.auto_checkout_enabled,
    }
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))
