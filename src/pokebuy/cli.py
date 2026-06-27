import json
from pathlib import Path
from typing import Annotated

import typer
from alembic import command
from alembic.config import Config

from pokebuy.config import get_settings
from pokebuy.db.models import Base
from pokebuy.db.session import create_db_engine
from pokebuy.logging import configure_logging
from pokebuy.scraper import scrape_product_url

app = typer.Typer(no_args_is_help=True)


@app.command()
def init() -> None:
    """Create local runtime directories and database tables."""

    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.browser_state_dir.mkdir(parents=True, exist_ok=True)
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
    log_level: Annotated[str, typer.Option(help="Logging level")] = "WARNING",
) -> None:
    """Fetch one product URL, persist a snapshot, and print normalized output."""

    configure_logging(log_level)
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    snapshot = scrape_product_url(url, settings)
    typer.echo(json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True))


@app.command("show-config")
def show_config() -> None:
    """Print non-secret runtime paths and polling configuration."""

    settings = get_settings()
    payload = {
        "env": settings.env,
        "database_url": settings.database_url,
        "data_dir": str(Path(settings.data_dir)),
        "browser_state_dir": str(Path(settings.browser_state_dir)),
        "poll_min_seconds": settings.poll_min_seconds,
        "http_timeout_seconds": settings.http_timeout_seconds,
        "auto_cart_enabled": settings.auto_cart_enabled,
        "auto_checkout_enabled": settings.auto_checkout_enabled,
    }
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))
