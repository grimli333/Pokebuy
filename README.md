# PokeBuy

PokeBuy is a Python utility for monitoring Pokemon Center card product pages, storing product and stock history, and notifying the user when watched items become available.

The current project state is Phase 0 foundation work. Application scraping, notifications, browser automation, and the web UI are planned in `doc/TODO.md`.

## Development Setup

Install dependencies:

```sh
uv sync
```

Run verification:

```sh
uv run ruff check .
uv run mypy
uv run pytest
```

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

Browser scrape with a visible browser and a 60-second manual window for queue or challenge handling:

```sh
uv run pokebuy scrape-url --collector browser --no-headless --manual-wait-seconds 60 "https://www.pokemoncenter.com/product/10-10318-142/pokemon-tcg-mega-evolution-ascended-heroes-mini-tin-togepi-and-totodile"
```

Warm and reuse a persistent browser profile:

```sh
uv run pokebuy warm-session --no-headless --manual-wait-seconds 300 "https://www.pokemoncenter.com/"
uv run pokebuy scrape-url --collector browser --use-profile --no-headless --manual-wait-seconds 30 "https://www.pokemoncenter.com/product/10-10318-142/pokemon-tcg-mega-evolution-ascended-heroes-mini-tin-togepi-and-totodile"
```

Install Playwright's browser runtime if needed:

```sh
uv run playwright install chromium
```

## Safety Defaults

- PokeBuy starts local-first.
- The web UI will bind to `127.0.0.1` by default when implemented.
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
- Email notifications come first, then Discord bot notifications.
- SQLite is the default database for the foreseeable future.

## Documentation

- `doc/DESIGN.md`: technical design.
- `doc/TODO.md`: implementation task list.
- `doc/PROGRESS.md`: current project status and decisions.
