# PokeBuy TODO

This task list follows the milestones in `doc/DESIGN.md`. Keep tasks small enough to verify with a command, a test, or a visible UI behavior.

## Phase 0: Project Foundation

- [x] Choose package manager and project layout.
- [x] Create Python package scaffold under `src/pokebuy`.
- [x] Add `pyproject.toml` with runtime and development dependencies.
- [x] Add `ruff`, type checking, and `pytest` configuration.
- [x] Add `.gitignore` entries for `.env`, `.pokebuy/`, browser state, logs, caches, and local databases.
- [x] Add base `README.md` with setup, local run, and safety notes.
- [x] Create `pokebuy.config` using `pydantic-settings`.
- [x] Create a sample `.env.example` with documented variables.
- [x] Add structured logging setup with optional file output.
- [x] Add first smoke test that imports the package.

Acceptance checks:

- [x] `uv sync` or the chosen install command creates a working environment.
- [x] `ruff check .` passes.
- [x] `ruff format --check .` passes.
- [x] `mypy` passes.
- [x] `pytest` passes.

## Phase 1: Reading Pokemon Center Data

- [x] Define Pydantic domain models for products, variants, observations, snapshots, and availability states.
- [x] Create SQLAlchemy database models for products, variants, snapshots, and scheduler runs.
- [x] Add Alembic migrations.
- [x] Implement database session management and repositories.
- [x] Implement product URL normalization.
- [x] Implement `curl_cffi` product fetcher with timeout and blocked-response detection.
- [x] Add collector retry and rate-limit hooks.
- [x] Add toggleable debug logging and returned-HTML artifacts for collector troubleshooting.
- [x] Implement parser interface for normalized `ProductObservation` output.
- [x] Add first Pokemon Center product parser using fixture-driven tests.
- [x] Add Chrome/CDP fallback collector for rendered page inspection.
- [x] Add persistent browser profile warm-up command for manual login/challenge capture.
- [x] Store snapshot fetch status and error details.
- [x] Add CLI command `pokebuy scrape-url <url>`.
- [x] Add sanitized fixtures for `in_stock` and `out_of_stock` states.
- [x] Add fixture coverage for bot-protection `blocked` responses.
- [x] Add sanitized fixtures for `unknown` and `not_found` states.
- [x] Verify live Pokemon Center browser collection using the warmed persistent profile.
- [x] Keep Milestone 1 product monitoring limited to specific product URLs.

Acceptance checks:

- [x] `pokebuy scrape-url <product-url>` prints normalized product data.
- [x] A successful scrape writes product and snapshot rows.
- [x] Parser tests pass against fixtures.
- [x] Failed fetches are persisted without crashing the scheduler path.

## Phase 2: Notifications

- [ ] Add watchlist database model and repository.
- [ ] Add notification policy database model and repository.
- [ ] Add stock event detection from snapshot transitions.
- [ ] Add duplicate suppression and cooldown logic.
- [ ] Add notification delivery log table.
- [ ] Implement email notification transport.
- [ ] Implement Discord bot notification transport after email works.
- [ ] Optionally implement Discord webhook fallback if bot setup is too heavy.
- [ ] Add notification templates.
- [ ] Add `pokebuy test-notification` CLI command.
- [ ] Add APScheduler integration for due watchlist polling.
- [ ] Add `pokebuy watch-once` CLI command.
- [ ] Add tests for restock, sold-out, price-change, cooldown, and failure cases.

Acceptance checks:

- [ ] A restock transition creates one `StockEvent`.
- [ ] A configured email recipient receives a test notification.
- [ ] A configured Discord bot recipient receives a test notification.
- [ ] Duplicate events inside the cooldown window are suppressed and logged.

## Phase 3: Login and Cart Assistance

- [ ] Add Chrome/CDP browser session manager.
- [ ] Add storage-state directory management outside source control.
- [ ] Extend `pokebuy warm-session` or add a dedicated login command for account/session validation.
- [ ] Implement session validation flow.
- [ ] Add `BrowserSession` database model.
- [ ] Add add-to-cart workflow for a product URL and optional variant.
- [ ] Discover related Pokemon card products from observed product pages or normal site navigation.
- [ ] Add `CartAttempt` database model and audit logging.
- [ ] Add global `POKEBUY_AUTO_CART_ENABLED` feature flag.
- [ ] Keep checkout completion disabled by default.
- [ ] Add screenshots or redacted diagnostics for failed browser automation.
- [ ] Add manual integration checklist for login and cart validation.

Acceptance checks:

- [ ] User can complete login manually in a controlled browser.
- [ ] Saved browser state can be validated later.
- [ ] Add-to-cart attempts are logged with status and error detail.
- [ ] Checkout completion cannot run unless an explicit future feature flag is added.

## Phase 4: Web UI

- [x] Add FastAPI app scaffold.
- [x] Add Jinja template layout and static asset structure.
- [x] Add HTMX support for form and table updates.
- [x] Add dashboard page showing watched products, current state, latest events, and notification failures.
- [x] Add products page with product detail and snapshot history.
- [ ] Add watchlist page with add/edit/disable controls.
- [ ] Add events page with filters.
- [ ] Add analytics page with stock calendar and price history charts.
- [ ] Add notifications settings page with test actions.
- [ ] Add sessions page for warm-session/login status and validation.
- [x] Add settings page with masked sensitive values.
- [ ] Add CSRF protection before non-localhost exposure.
- [ ] Add `pokebuy web` CLI command.

Acceptance checks:

- [ ] Web app runs locally and binds to `127.0.0.1` by default.
- [ ] User can add a watched product from the UI.
- [ ] User can see snapshot history and recent events.
- [ ] Sensitive configuration values are masked.

## Phase 5: Prediction and Advanced Automation

- [ ] Add restock frequency aggregation.
- [ ] Add day-of-week and time-of-day analysis.
- [ ] Add `PredictionSignal` model and persistence.
- [ ] Add explainable rule-based prediction generator.
- [ ] Add prediction chart and calendar overlay in the UI.
- [ ] Add auto-cart policy controls per watchlist item.
- [ ] Reassess checkout-completion requirements, legal constraints, and safety controls.
- [ ] Add explicit design update before implementing automated checkout completion.

Acceptance checks:

- [ ] Prediction output includes confidence, time window, and explanation.
- [ ] Prediction UI clearly separates observed history from forecasted signals.
- [ ] Auto-cart remains opt-in and auditable.

## Cross-Cutting Tasks

- [ ] Add redaction helpers for logs and diagnostics.
- [ ] Add global polling minimum and jitter.
- [x] Add health endpoint for web process.
- [ ] Add scheduler run status tracking.
- [ ] Add backup/export command for SQLite database.
- [ ] Add documentation for local-only mode.
- [ ] Add documentation for hosted mode with PostgreSQL.
- [ ] Add manual runbook for parser breakage when Pokemon Center changes its pages.
- [ ] Add release checklist.

## Open User Decisions

- [ ] Decide operational safeguards required before high-frequency polling near 10 Hz.
