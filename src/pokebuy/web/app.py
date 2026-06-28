from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, sessionmaker

from pokebuy.config import Settings, get_settings
from pokebuy.db.models import Base
from pokebuy.db.session import create_db_engine, create_session_factory
from pokebuy.web.views import (
    dashboard_stats,
    get_product_summary,
    list_current_products,
    product_snapshots,
    recent_snapshots,
)


def get_session(request: Request) -> Iterator[Session]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_scope(session_factory) as session:
        yield session


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]
PACKAGE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
templates.env.filters["money"] = lambda cents, currency=None: format_money(cents, currency)
templates.env.filters["datetime"] = lambda value: format_datetime(value)
templates.env.filters["label"] = lambda value: format_label(value)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    engine = create_db_engine(resolved_settings)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    app = FastAPI(title="PokeBuy", version="0.1.0")
    app.state.settings = resolved_settings
    app.state.session_factory = session_factory
    app.mount(
        "/static",
        StaticFiles(directory=str(PACKAGE_DIR / "static")),
        name="static",
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def dashboard(
        request: Request,
        session: SessionDep,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "active_nav": "dashboard",
                "stats": dashboard_stats(session),
                "products": list_current_products(session, limit=20),
                "events": recent_snapshots(session, limit=15),
            },
        )

    @app.get("/products", response_class=HTMLResponse)
    def products(
        request: Request,
        session: SessionDep,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "products.html",
            {
                "active_nav": "products",
                "products": list_current_products(session, limit=100),
            },
        )

    @app.get("/products/{product_id}", response_class=HTMLResponse)
    def product_detail(
        product_id: str,
        request: Request,
        session: SessionDep,
    ) -> HTMLResponse:
        product = get_product_summary(session, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return templates.TemplateResponse(
            request,
            "product_detail.html",
            {
                "active_nav": "products",
                "product": product,
                "snapshots": product_snapshots(session, product_id, limit=100),
            },
        )

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "settings.html",
            {
                "active_nav": "settings",
                "settings": resolved_settings,
            },
        )

    return app


def format_money(cents: int | None, currency: str | None = None) -> str:
    if cents is None:
        return "-"
    prefix = "$" if currency in (None, "USD") else f"{currency} "
    return f"{prefix}{cents / 100:.2f}"


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M:%S")


def format_label(value: object) -> str:
    return str(value).replace("_", " ").title()
