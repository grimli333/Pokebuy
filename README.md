# PokeBuy

PokeBuy is a Python utility for monitoring Pokemon Center card product pages, storing product and stock history, and notifying the user when watched items become available.

The current project state is Milestone 1 collection work with an initial local web UI. Direct URL scraping, SQLite persistence, parser fixtures, curl-cffi HTTP fetching, Chrome/CDP browser collection, session warming, and read-only dashboard/product pages are in place; notifications and cart automation are planned in `doc/TODO.md`.

## Development Setup

Install dependencies:

```sh
uv sync
```

Run verification:

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Some Chrome/CDP tests launch the system browser. If your execution environment blocks GUI or browser process launches, run those tests in a normal local terminal.

Create local configuration:

```sh
cp .env.example .env
```

Runtime data defaults to `.pokebuy/`, which is ignored by git.

## Example Scrape Commands

Direct HTTP scrape:

```sh
uv run pokebuy scrape-url "https://www.pokemoncenter.com/product/10-10318-142/pokemon-tcg-mega-evolution-ascended-heroes-mini-tin-togepi-and-totodile"
```

Debug logging is currently enabled by default. Scrape runs emit JSON debug logs to stderr and `pokebuy.log`, print returned HTML to stderr, and save returned HTML artifacts under `debug/`. Use `--no-debug` to disable debug-level output for a single run. Use `POKEBUY_LOG_FILE_ENABLED=false` to disable file logging.

Browser scrape with system Chrome/CDP and a 60-second manual window for queue or challenge handling:

```sh
uv run pokebuy scrape-url --collector browser --no-headless --manual-wait-seconds 60 "https://www.pokemoncenter.com/product/10-10318-142/pokemon-tcg-mega-evolution-ascended-heroes-mini-tin-togepi-and-totodile"
```

Warm and reuse a persistent browser profile:

```sh
uv run pokebuy warm-session --no-headless --manual-wait-seconds 300 "https://www.pokemoncenter.com/"
uv run pokebuy scrape-url --collector browser --use-profile --no-headless --manual-wait-seconds 30 "https://www.pokemoncenter.com/product/10-10318-142/pokemon-tcg-mega-evolution-ascended-heroes-mini-tin-togepi-and-totodile"
```

No special browser runtime installation is required. PokeBuy automatically locates your system's normal Google Chrome or Chromium executable. If needed, override this path by setting the `CHROME_PATH` environment variable.

## Web UI

Run the local web UI:

```sh
uv run pokebuy web
```

The UI binds to `127.0.0.1:8000` by default and currently exposes a dashboard, product list, product history, settings page, and `/healthz`.

## Safety Defaults

- PokeBuy starts local-first.
- The web UI binds to `127.0.0.1` by default.
- Checkout completion is disabled by default and is not part of the first implementation.
- Add-to-cart automation is planned for a later milestone and will require explicit enablement.
- Browser session state and credentials must stay outside source control.

## Current Implementation Decisions

- Milestone 1 monitors specific Pokemon Center product URLs.
- Related product discovery is deferred until Milestone 3 and should stay limited to Pokemon card products.
- Development polling defaults to 30 seconds or slower.
- The practical target is detecting availability changes within one minute.
- The configuration supports sub-second polling intervals for future experiments, but high-frequency polling needs rate-limit detection and explicit safeguards before use.
- Username/password storage is allowed if it works, but it must use local secret handling and must never be committed.
- Browser login/challenge state is captured in `.pokebuy/browser-profile/` and `.pokebuy/browser-state/`, both ignored by git.
- Structured logs are written to stderr and, by default, `pokebuy.log`.
- Debug output is enabled for current development and writes local artifacts to `debug/`.
- Email notifications come first, then Discord bot notifications.
- SQLite is the default database for the foreseeable future.

## Documentation

- `doc/DESIGN.md`: technical design.
- `doc/TODO.md`: implementation task list.
- `doc/PROGRESS.md`: current project status and decisions.
