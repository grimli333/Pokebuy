# PokeBuy Technical Design

## 1. Purpose

PokeBuy is a Python utility for monitoring Pokemon Center product availability, recording product and inventory signals over time, notifying the user when watched items become available, and optionally assisting with cart and checkout workflows.

The first production-quality version should prioritize reliable stock monitoring, history capture, and notifications. Automated purchasing is treated as a later, opt-in capability because it depends on website behavior, account state, payment flow, and Pokemon Center terms and controls that may change outside this project.

## 2. Goals

- Monitor Pokemon Center product pages and product listings for stock, price, title, variant, image, and metadata changes.
- Maintain historical product snapshots for analysis and prediction.
- Notify the user through email and Discord when watched items meet configured conditions.
- Provide a local or hosted web UI for watchlists, recent events, charts, calendars, and configuration.
- Support user-authenticated browser automation for login and cart workflows.
- Keep credentials, cookies, and checkout actions auditable and isolated.
- Use proven Python libraries for browser automation, HTTP, scheduling, persistence, UI, and notifications.

## 3. Non-Goals

- Do not bypass CAPTCHAs, anti-bot protections, rate limits, or access controls.
- Do not store full payment card details or CVV values.
- Do not complete purchases without explicit user opt-in and clear audit logging.
- Do not rely on brittle selectors as the only source of product state when structured page data or APIs are available.
- Do not build a large custom front-end framework before monitoring and notifications work.

## 4. Assumptions

- Python 3.12 or newer is available for local development.
- The first deployment will run locally and can use a single process or small set of local processes.
- SQLite is acceptable for local development and early single-user use.
- PostgreSQL should be supported before multi-user or always-on hosted use.
- Pokemon Center page structure and checkout flow are unstable integration boundaries and must be versioned/tested.
- The first implementation monitors specific product URLs only.
- By Milestone 3, PokeBuy should discover related Pokemon card products from observed product pages or normal site navigation.
- The user can provide Pokemon Center credentials interactively or through local credential storage, but the project should not require credentials for Milestones 1 and 2.
- Getting products into the cart is in scope before purchase completion. Completing purchases automatically is out of scope for the first implementation.
- Email notifications should be implemented first, followed by a Discord bot.
- SQLite is the default database target and is acceptable indefinitely unless real deployment pressure requires a different store.
- Related Pokemon card discovery can use both product-page recommendations and category/search pages.
- The practical polling goal is to notice products going live within one minute. Higher-frequency polling, including any approach near 10 Hz, must be introduced cautiously with rate-limit detection and backoff.

## 5. Recommended Stack

### Runtime and Project Tooling

- Python 3.12 or newer
- `uv` for dependency and virtual environment management
- `ruff` for linting and formatting
- `mypy` or `pyright` for type checking
- `pytest` for unit and integration tests

### Browser and Scraping

- `curl_cffi` for direct HTTP requests where pages or JSON endpoints can be safely fetched with browser-compatible TLS and HTTP behavior.
- System Chrome or Chromium controlled through the DevTools Protocol (CDP), using `websocket-client`, for browser-backed flows such as manual session warming, login, rendered page inspection, cart assistance, and queue observation.
- `selectolax` or `beautifulsoup4` for parsing HTML when structured data is not available.
- `pydantic` for normalized product, stock, notification, and configuration models.

### Storage

- `sqlalchemy` 2.x ORM for persistence.
- `alembic` for migrations.
- SQLite for development, single-user local mode, and the default long-term store.
- PostgreSQL only if hosted or multi-process requirements justify it later.

### Background Work

- `apscheduler` for the initial single-node scheduler.
- Optional later migration to `rq`, `dramatiq`, or `celery` if distributed workers are needed.

### Web UI and API

- `fastapi` for the HTTP API and web app host.
- `jinja2` plus `htmx` for server-rendered interactive pages.
- `plotly` or `altair` for charts.
- `python-multipart` for settings forms if needed.

### Notifications

- Python standard library `smtplib` or `aiosmtplib` for email notifications.
- `discord.py` for Discord bot notifications after email is working.
- Direct Discord webhooks can remain a fallback if bot setup is heavier than expected.
- `jinja2` templates for notification bodies.

### Configuration and Secrets

- `pydantic-settings` for environment-backed configuration.
- `.env` support for local development.
- OS keychain or a secrets backend for credentials and session cookies before hosted use.

## 6. System Architecture

PokeBuy is organized into clear modules:

- `pokebuy.config`: application settings, environment parsing, and secret references.
- `pokebuy.models`: Pydantic domain models for products, snapshots, events, watchlists, and notifications.
- `pokebuy.db`: SQLAlchemy models, repositories, migrations, and database session management.
- `pokebuy.collectors`: product discovery, page fetchers, parsers, and stock snapshot creation.
- `pokebuy.collectors.browser`: Chrome/CDP session management, rendered page collection, profile warming, login, cart, and checkout helpers.
- `pokebuy.scheduler`: recurring jobs for polling watchlists and refreshing product data.
- `pokebuy.analysis`: stock-event detection, trend analysis, and prediction logic.
- `pokebuy.notifications`: email, Discord, message rendering, throttling, and delivery logs.
- `pokebuy.web`: FastAPI routes, web UI templates, static assets, and API schemas.
- `pokebuy.cli`: command-line entry points for setup, one-shot scrape, scheduler, and admin tasks.

The first implementation should support a single-process mode:

1. FastAPI serves the web UI and local API.
2. APScheduler runs polling jobs inside the app process.
3. Collectors fetch product data and write snapshots.
4. Analysis compares new snapshots with prior state and emits events.
5. Notification workers deliver messages and log outcomes.

For hosted or always-on use, split the process model:

1. Web process serves FastAPI.
2. Worker process runs scheduler and collector jobs.
3. PostgreSQL stores shared state.
4. Optional Redis-backed queue coordinates retries and notification delivery.

## 7. Core Domain Model

### Product

Represents a Pokemon Center product identity.

Fields:

- `id`: internal UUID
- `source`: fixed value such as `pokemon_center`
- `source_product_id`: product ID or SKU from Pokemon Center when available
- `url`: canonical product URL
- `slug`: URL slug if available
- `title`: latest known title
- `category`: optional category path
- `image_url`: primary image URL
- `created_at`
- `updated_at`

### ProductVariant

Represents a purchasable variant when a product has size, style, pack type, or SKU differences.

Fields:

- `id`
- `product_id`
- `source_variant_id`
- `sku`
- `title`
- `attributes`: JSON map for variant dimensions
- `created_at`
- `updated_at`

### ProductSnapshot

Stores observed product state at a point in time.

Fields:

- `id`
- `product_id`
- `variant_id`
- `observed_at`
- `availability`: `unknown`, `out_of_stock`, `in_stock`, `preorder`, `backorder`, `unavailable`
- `price_cents`
- `currency`
- `quantity_limit`
- `raw_state`: JSON field for normalized page/API signals
- `collector_version`
- `fetch_status`
- `fetch_error`

### StockEvent

Represents a meaningful transition derived from snapshots.

Fields:

- `id`
- `product_id`
- `variant_id`
- `event_type`: `restocked`, `sold_out`, `price_changed`, `new_product`, `metadata_changed`
- `started_at`
- `ended_at`
- `previous_snapshot_id`
- `current_snapshot_id`
- `summary`

### WatchlistItem

Defines what the user wants monitored.

Fields:

- `id`
- `name`
- `product_id`
- `url`
- `enabled`
- `desired_availability`
- `max_price_cents`
- `min_quantity`
- `poll_interval_seconds`
- `notification_policy_id`
- `auto_cart_enabled`
- `auto_checkout_enabled`
- `created_at`
- `updated_at`

### NotificationPolicy

Controls notification channels and throttling.

Fields:

- `id`
- `name`
- `channels`: email, Discord webhook, Discord bot DM/channel
- `cooldown_seconds`
- `notify_on_restock`
- `notify_on_price_drop`
- `notify_on_new_product`
- `created_at`
- `updated_at`

### NotificationDelivery

Stores notification attempts.

Fields:

- `id`
- `event_id`
- `policy_id`
- `channel`
- `status`: `pending`, `sent`, `failed`, `suppressed`
- `attempted_at`
- `error`
- `payload_hash`

### BrowserSession

Tracks browser-controlled sessions without exposing secrets in logs.

Fields:

- `id`
- `label`
- `storage_state_path`
- `status`
- `last_validated_at`
- `created_at`
- `updated_at`

### CartAttempt

Audits add-to-cart or checkout-assist actions.

Fields:

- `id`
- `watchlist_item_id`
- `product_id`
- `variant_id`
- `started_at`
- `finished_at`
- `status`: `started`, `carted`, `requires_user_action`, `failed`, `cancelled`
- `browser_session_id`
- `error`
- `audit_summary`

## 8. Data Collection Design

Collectors should prefer the least fragile source that provides enough data:

1. Structured data embedded in product pages.
2. Public JSON endpoints used by the page, if visible through normal site behavior.
3. Rendered DOM inspection through system Chrome controlled over CDP.
4. Text and selector fallback only when no structured source exists.

If Pokemon Center does not expose a stable structured path, PokeBuy can fall back to full rendered-browser control of the normal website UI. This is treated as an automation fallback, not as permission to bypass CAPTCHA, queueing, rate limits, or account controls.

Each collector returns a normalized `ProductObservation`:

- Product identity
- Variant identities
- Availability state
- Price
- Image and title metadata
- Quantity limit if visible
- Raw evidence fields
- Collector version
- Fetch status

Collector rules:

- Use rate limits and jitter.
- Use identifiable user-agent configuration where appropriate.
- Persist failed fetches with enough detail for debugging.
- Avoid infinite retries.
- Keep raw HTML storage optional and disabled by default.
- Version parser behavior so historical records can be interpreted.

## 9. Availability Detection

Availability is normalized into stable states:

- `unknown`: collector could not determine state.
- `out_of_stock`: product exists but cannot be purchased.
- `in_stock`: product can be added to cart.
- `preorder`: product can be ordered for future fulfillment.
- `backorder`: product can be ordered but delayed.
- `unavailable`: product page is gone, blocked, or unavailable in region.

The detector should store the evidence used for the decision, such as:

- Add-to-cart button enabled state.
- Visible stock text.
- JSON inventory status.
- Variant-level purchase state.
- HTTP status and redirect state.

## 10. Notification Flow

1. Scheduler selects enabled watchlist items due for polling.
2. Collector creates a product snapshot.
3. Analysis compares the current snapshot to the previous snapshot.
4. Analysis emits a `StockEvent` if a configured transition occurred.
5. Notification service evaluates policy, cooldown, and duplicate suppression.
6. Notification service sends email and/or Discord message.
7. Delivery result is persisted.

Duplicate suppression should use:

- Product ID
- Variant ID
- Event type
- Snapshot ID or event window
- Notification policy
- Channel

## 11. Prediction Design

Prediction should be introduced after enough history exists. Initial prediction can be simple and explainable:

- Restock frequency per product and category.
- Time of day and day of week clustering.
- Product lifecycle age.
- Recent page metadata changes.
- Price and listing changes.
- Calendar heatmap of observed restock windows.

The first model should produce a `PredictionSignal`, not an automated purchase decision.

Fields:

- `product_id`
- `generated_at`
- `signal_type`
- `confidence`: 0.0 to 1.0
- `predicted_window_start`
- `predicted_window_end`
- `explanation`

Do not build opaque machine learning before enough clean event data exists. Start with rule-based scoring and add statistical models only after the database contains meaningful history.

## 12. Browser Automation Design

Browser automation uses system Chrome or Chromium controlled through CDP plus a persistent browser profile and exported storage state.

Supported actions:

- Launch controlled browser.
- Navigate to login page.
- Let user complete login manually if needed.
- Save storage state after successful login.
- Validate session by loading an account or cart page.
- Navigate to product page.
- Select variant if configured.
- Add product to cart.
- Assist the user through waiting-room or queue flows when normal browser automation can observe them.
- Stop for user confirmation before checkout completion unless explicitly enabled.

Rules:

- Never log passwords, cookies, authorization headers, or payment details.
- Store browser storage state outside source control.
- Mark sessions stale after validation failure.
- Do not bypass CAPTCHA or multi-factor prompts.
- Make checkout completion a separate feature flag, disabled by default.
- Record every automated cart or checkout action in `CartAttempt`.
- If username/password storage is implemented, store secrets outside source control and prefer OS keychain or encrypted local storage.

## 13. Web UI Design

The web UI should be operational and compact, not a marketing site.

Initial pages:

- Dashboard: watched items, current stock state, latest events, notification status.
- Products: searchable product list and snapshot history.
- Watchlist: add URL, set target conditions, set poll interval, enable notifications.
- Events: restocks, sold-out transitions, price changes, fetch failures.
- Analytics: stock calendar, restock frequency, price history charts.
- Notifications: email and Discord configuration, test delivery.
- Sessions: browser login/session state and manual validation controls.
- Settings: runtime configuration, polling limits, database info.

Implementation:

- FastAPI routes render Jinja templates.
- HTMX updates tables, forms, and detail panels without a large JavaScript app.
- Plotly or Altair renders charts from API endpoints.
- Sensitive settings are masked in the UI.

## 14. CLI Design

Provide a CLI for setup and automation:

- `pokebuy init`: create config, database, and directories.
- `pokebuy migrate`: run database migrations.
- `pokebuy scrape-url <url>`: run one product scrape and print normalized output.
- `pokebuy watch-once`: poll due watchlist items once.
- `pokebuy worker`: run scheduler and background jobs.
- `pokebuy web`: run FastAPI app.
- `pokebuy warm-session`: open Chrome with the persistent PokeBuy profile and save storage state after manual login or challenge handling.
- `pokebuy test-notification`: send a test email or Discord message.

Use `typer` for CLI implementation.

## 15. Configuration

Environment variables:

- `POKEBUY_ENV`: `dev`, `test`, or `prod`
- `POKEBUY_DATABASE_URL`: SQLAlchemy database URL
- `POKEBUY_SECRET_KEY`: local encryption/signing key
- `POKEBUY_DATA_DIR`: path for runtime data
- `POKEBUY_BROWSER_STATE_DIR`: path for exported browser storage state
- `POKEBUY_BROWSER_PROFILE_DIR`: path for the persistent Chrome profile used by CDP collection
- `POKEBUY_POLL_MIN_SECONDS`: global minimum poll interval
- `POKEBUY_HTTP_TIMEOUT_SECONDS`: request timeout
- `POKEBUY_HTTP_MAX_ATTEMPTS`: maximum direct HTTP fetch attempts
- `POKEBUY_HTTP_RETRY_BACKOFF_SECONDS`: base retry backoff for transient direct HTTP failures
- `POKEBUY_HTTP_RETRY_AFTER_MAX_SECONDS`: maximum delay honored from `Retry-After`
- `POKEBUY_WEB_HOST`: web UI bind host, default `127.0.0.1`
- `POKEBUY_WEB_PORT`: web UI bind port, default `8000`
- `POKEBUY_LOG_FILE_ENABLED`: enable structured file logging
- `POKEBUY_LOG_FILE_PATH`: path for the structured log file, default `pokebuy.log`
- `POKEBUY_DEBUG_ENABLED`: enable structured debug logs and debug artifacts
- `POKEBUY_DEBUG_PRINT_HTML`: print returned HTML to stderr while debug is enabled
- `POKEBUY_DEBUG_REDACT_HTML`: redact known challenge cookie values from debug HTML output
- `POKEBUY_DEBUG_DIR`: path for debug artifacts such as returned HTML
- `POKEBUY_DISCORD_WEBHOOK_URL`: optional Discord webhook
- `POKEBUY_SMTP_HOST`: SMTP host
- `POKEBUY_SMTP_PORT`: SMTP port
- `POKEBUY_SMTP_USERNAME`: SMTP username
- `POKEBUY_SMTP_PASSWORD`: SMTP password
- `POKEBUY_EMAIL_FROM`: sender email
- `POKEBUY_EMAIL_TO`: default recipient email
- `POKEBUY_AUTO_CART_ENABLED`: global add-to-cart feature flag
- `POKEBUY_AUTO_CHECKOUT_ENABLED`: global checkout feature flag, default false

Development defaults should use `POKEBUY_POLL_MIN_SECONDS=30`. The first practical target is detecting availability changes within one minute. The configuration type should support sub-second values, such as `0.1`, for later high-frequency monitoring experiments after rate limits, site behavior, and operational safeguards are understood.

Files and directories:

- `.env`: local development config, ignored by git
- `.pokebuy/`: default local runtime directory
- `.pokebuy/browser-state/`: exported browser storage state, ignored by git
- `.pokebuy/browser-profile/`: persistent Chrome profile, ignored by git
- `.pokebuy/logs/`: local logs, ignored by git
- `pokebuy.log`: default structured log file, ignored by git
- `debug/`: local debug artifacts such as returned HTML, ignored by git if configured locally

## 16. Security and Privacy

- Keep secrets out of git.
- Mask secrets in logs and UI.
- Encrypt or OS-keychain protect credentials before hosted use.
- Store only browser storage state needed for session reuse.
- Do not store payment card numbers or CVV.
- Require explicit feature flags for cart and checkout automation.
- Maintain audit logs for login validation, add-to-cart attempts, and checkout-assist actions.
- Add CSRF protection before exposing the web UI beyond localhost.
- Bind local web UI to `127.0.0.1` by default.

## 17. Reliability and Observability

- Use structured logs with request/job IDs.
- Write structured logs to stderr and optionally to `pokebuy.log`; file logging is enabled by default for local debugging.
- Emit collector debug logs for attempts, retry decisions, browser/CDP navigation, status codes, redacted headers, and debug artifact paths.
- Persist collector errors and notification failures.
- Track scheduler run status and duration.
- Add retry policies with bounded attempts and backoff.
- Add health endpoints for web and worker processes.
- Keep a manual "poll now" action for debugging.
- Add screenshots or HTML excerpts for failing browser/CDP flows when safe and redacted.

## 18. Testing Strategy

### Unit Tests

- URL normalization
- Product parser fixtures
- Availability normalization
- Event detection
- Notification suppression
- Configuration parsing

### Integration Tests

- Database migrations
- Repository read/write flows
- Scheduler polling with fake collectors
- Notification delivery with test transports
- Web routes using FastAPI test client

### Browser Tests

- Chrome/CDP smoke tests against saved fixture pages or benign local/test pages.
- Live Pokemon Center browser tests only when explicitly enabled with an environment flag.
- Chrome/CDP tests require a local Chrome or Chromium install and may need permissions to launch that browser.
- Login/cart tests should be manual or opt-in because they require credentials and real site state.

### Fixture Strategy

- Store sanitized HTML/JSON fixtures for known product states.
- Include at least `in_stock`, `out_of_stock`, `preorder`, `not_found`, and `blocked_or_unknown` examples.
- Keep fixture refresh as a manual command so parser changes are reviewable.

## 19. Milestones

### Milestone 1: Reading Pokemon Center Data

Deliverables:

- Python project scaffold.
- Config loader.
- Database schema and migrations.
- Product URL scraper.
- Snapshot persistence.
- CLI command for one-shot scrape.
- Basic tests with fixtures.

Exit criteria:

- Given a Pokemon Center product URL, PokeBuy records a normalized product and snapshot.
- The collector can distinguish at least `in_stock`, `out_of_stock`, and `unknown`.
- Unit tests pass locally.
- Discovery is limited to explicit product URLs.

### Milestone 2: Triggering Notifications

Deliverables:

- Watchlist model and CRUD.
- Scheduler for recurring polls.
- Event detection.
- Email and Discord notification transports.
- Notification throttling and delivery logs.

Exit criteria:

- A watched product restock event triggers a configured notification exactly once per event window.
- Failed notification attempts are visible in logs and database.
- User can send a test notification.

### Milestone 3: Login and Cart Assistance

Deliverables:

- Chrome/CDP browser session manager.
- Manual login flow and saved storage state.
- Session validation.
- Add-to-cart workflow for watched product.
- Related Pokemon card product discovery from normal product-page or site-navigation signals.
- Cart attempt audit log.

Exit criteria:

- User can manually establish a session.
- PokeBuy can validate the session without exposing secrets.
- With explicit config enabled, PokeBuy can attempt add-to-cart and stop before purchase completion.
- Related product discovery only records Pokemon card products.

### Milestone 4: Graphical Web UI

Deliverables:

- FastAPI web app.
- Dashboard, products, watchlist, events, analytics, notifications, sessions, and settings pages.
- Charts for stock events and price history.
- Calendar view of stock events.

Exit criteria:

- User can configure watchlist and notifications through the UI.
- User can view product history and event charts.
- Sensitive values are masked.

### Milestone 5: Prediction and Checkout Opt-In

Deliverables:

- Rule-based prediction signals.
- Prediction dashboard.
- Auto-cart policy controls.
- Optional checkout-assist policy design.
- Additional review of legal, terms, and safety constraints.

Exit criteria:

- Predictions are explainable and tied to observed history.
- Checkout completion remains disabled unless intentionally implemented and explicitly enabled.

## 20. Open Questions

These require user decisions or live discovery:

- Should PokeBuy be local-only at first, or should the design target hosted deployment immediately?
- Which notification channel should be implemented first: email, Discord webhook, or Discord bot?
- What operational safeguards are required before attempting high-frequency polling near 10 Hz?
