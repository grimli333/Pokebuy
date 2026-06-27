# PokeBuy Progress

Last updated: 2026-06-27

## Current Status

PokeBuy has completed Phase 0 foundation work and started Milestone 1. Direct HTTP product scraping, parser fixtures, SQLite persistence, migrations, and the `scrape-url` CLI are implemented. Browser fallback, scheduler polling, notifications, browser automation, and the web UI have not been implemented yet.

Completed work:

- Expanded `doc/DESIGN.md` from a concept brief into a full technical design.
- Created `doc/TODO.md` with phased implementation tasks and acceptance checks.
- Captured user decisions that guide the first implementation.
- Created Python package scaffold under `src/pokebuy`.
- Added `pyproject.toml`, `uv.lock`, `ruff`, `mypy`, and `pytest` setup.
- Added environment-backed settings in `pokebuy.config`.
- Added structured logging setup in `pokebuy.logging`.
- Added `.env.example`, `.gitignore`, and `README.md`.
- Added import and configuration smoke tests.
- Added Pydantic domain models for product observations and persisted snapshots.
- Added SQLAlchemy product, variant, snapshot, and scheduler run tables.
- Added Alembic initial migration.
- Added product URL normalization for Pokemon Center product URLs.
- Added `httpx` fetcher with blocked-response detection.
- Added Pokemon Center HTML/JSON-LD parser with fixture tests.
- Added SQLite repository persistence for successful and failed snapshots.
- Added `pokebuy migrate` and `pokebuy scrape-url` CLI commands.

## Milestone Progress

| Milestone | Status | Notes |
| --- | --- | --- |
| Phase 0: Project foundation | Complete | Package scaffold, config, logging, tooling, and smoke tests are in place. |
| Milestone 1: Reading Pokemon Center data | In progress | Direct HTTP collector, parser fixtures, SQLite persistence, migrations, and CLI are implemented. Playwright fallback and extra fixtures remain. |
| Milestone 2: Triggering notifications | Not started | Email is first, followed by Discord bot notifications. |
| Milestone 3: Login and cart assistance | Not started | Designed as Playwright-based and explicitly opt-in. Should also discover related Pokemon card products. |
| Milestone 4: Graphical web UI | Not started | Designed as FastAPI, Jinja, HTMX, and charting pages. |
| Milestone 5: Prediction and advanced automation | Not started | Deferred until enough historical data exists. |

## Assumptions Made

- Python 3.12 or newer will be used.
- The initial utility can be single-user and local-first.
- SQLite is acceptable indefinitely unless future deployment pressure requires another store.
- PostgreSQL should be deferred until hosted or multi-process requirements justify it.
- Playwright is the right tool for authenticated browser flows.
- Direct HTTP collection should be used where normal page behavior exposes sufficient product data.
- Automated checkout completion should remain disabled until explicitly approved and redesigned with additional safety controls.
- Username/password storage is acceptable if it works, but it must stay outside source control and should use OS keychain or encrypted local storage.
- Browser-session login remains a useful account integration path.
- Initial monitoring should support specific product URLs.
- By Milestone 3, related product discovery should cover Pokemon card products only.
- Local web binding to `127.0.0.1` is acceptable initially.
- Development/test polling can run every 30 seconds or slower. A future high-frequency target near 10 Hz needs additional safeguards and site-behavior validation.
- The practical polling target is detecting availability changes within one minute.
- The first cart automation target is add-to-cart and queue assistance, not purchase completion.
- Email notifications should be implemented first, followed by a Discord bot.
- Related Pokemon card discovery can use both product-page recommendations and category/search pages.

## Risks and Constraints

- Pokemon Center page structure and checkout behavior may change without notice.
- Product availability signals may differ between listing pages, product pages, and cart flows.
- Aggressive polling can create operational, account, or terms-of-use risk.
- Login, cart, and checkout flows may involve CAPTCHA, multi-factor prompts, or other manual steps.
- Prediction quality will be poor until PokeBuy has enough clean historical snapshots and stock events.
- Hosted deployment requires stronger authentication, CSRF protection, secret management, and database operations than local-only mode.
- High-frequency polling can create operational, account, or terms-of-use risk and must not be enabled casually.
- Rendered-browser automation may be required if structured product data is unavailable.

## Verification

Latest verification:

- `uv sync`: passed using local CPython 3.14.3, compatible with project requirement `>=3.12`.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed.
- `uv run mypy`: passed.
- `uv run pytest`: passed, 11 tests.
- Direct HTTP against both provided Pokemon Center URLs returned bot-protection HTML and was persisted as `blocked` snapshots.

## Open Questions for User

- What safeguards are required before attempting high-frequency polling near 10 Hz?

## Next Recommended Step

Continue Milestone 1 from `doc/TODO.md`:

- Add Playwright fallback collection for rendered page inspection.
- Add sanitized `unknown` and `not_found` parser/fetch fixtures.
- Use a real browser session to discover whether product data is available after normal JavaScript and bot-protection handling.
- Keep scheduler and notification behavior deferred until the collection path is reliable enough.
