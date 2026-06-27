from urllib.parse import urlsplit, urlunsplit

from pokebuy.models import NormalizedProductUrl

POKEMON_CENTER_HOST = "www.pokemoncenter.com"


class ProductUrlError(ValueError):
    pass


def normalize_product_url(raw_url: str) -> NormalizedProductUrl:
    parsed = urlsplit(raw_url.strip())
    if not parsed.scheme:
        parsed = urlsplit(f"https://{raw_url.strip()}")

    host = parsed.netloc.lower()
    if host == "pokemoncenter.com":
        host = POKEMON_CENTER_HOST

    if host != POKEMON_CENTER_HOST:
        msg = "expected a pokemoncenter.com product URL"
        raise ProductUrlError(msg)

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 3 or parts[0] != "product":
        msg = "expected URL path like /product/<product-id>/<slug>"
        raise ProductUrlError(msg)

    source_product_id = parts[1]
    slug = parts[2]
    canonical_path = f"/product/{source_product_id}/{slug}"
    canonical_url = urlunsplit(("https", POKEMON_CENTER_HOST, canonical_path, "", ""))

    return NormalizedProductUrl(
        canonical_url=canonical_url,
        source_product_id=source_product_id,
        slug=slug,
    )
