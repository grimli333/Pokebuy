from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any, cast

from bs4 import BeautifulSoup
from bs4.element import Tag

from pokebuy.collectors.fetcher import FetchResult
from pokebuy.models import Availability, FetchStatus, ProductObservation, ProductVariantObservation
from pokebuy.urls import normalize_product_url

PRICE_RE = re.compile(r"\$([0-9]+(?:\.[0-9]{2})?)")


class ProductParseError(ValueError):
    pass


class PokemonCenterProductParser:
    collector_version = "pokemon_center_html_v1"

    def parse_success(self, url: str, html: str) -> ProductObservation:
        normalized = normalize_product_url(url)
        soup = BeautifulSoup(html, "html.parser")
        raw_json_ld = self._json_ld_objects(soup)
        product_json = self._first_product_json(raw_json_ld)

        title = self._title(soup, product_json)
        image_url = self._image(soup, product_json)
        price_cents, currency = self._price(soup, product_json)
        availability = self._availability(soup, product_json)
        variant = ProductVariantObservation(
            source_variant_id=normalized.source_product_id,
            sku=normalized.source_product_id,
            title=title,
        )

        if title is None and not raw_json_ld:
            msg = "could not identify product data in HTML"
            raise ProductParseError(msg)

        return ProductObservation(
            source_product_id=normalized.source_product_id,
            url=normalized.canonical_url,
            slug=normalized.slug,
            title=title,
            image_url=image_url,
            variants=[variant],
            availability=availability,
            price_cents=price_cents,
            currency=currency,
            raw_state={
                "json_ld_count": len(raw_json_ld),
                "availability_evidence": availability.value,
            },
            collector_version=self.collector_version,
        )

    def parse_fetch_result(self, url: str, fetch: FetchResult) -> ProductObservation:
        normalized = normalize_product_url(url)
        if fetch.fetch_status != FetchStatus.SUCCESS:
            return ProductObservation(
                source_product_id=normalized.source_product_id,
                url=normalized.canonical_url,
                slug=normalized.slug,
                availability=Availability.UNKNOWN,
                raw_state={
                    "http_status": fetch.status_code,
                    "final_url": fetch.url,
                    "response_headers": self._safe_headers(fetch.headers),
                },
                collector_version=self.collector_version,
                fetch_status=fetch.fetch_status,
                fetch_error=fetch.fetch_error,
            )

        try:
            return self.parse_success(url, fetch.text)
        except ProductParseError as exc:
            return ProductObservation(
                source_product_id=normalized.source_product_id,
                url=normalized.canonical_url,
                slug=normalized.slug,
                availability=Availability.UNKNOWN,
                raw_state={"parse_error": str(exc), "http_status": fetch.status_code},
                collector_version=self.collector_version,
                fetch_status=FetchStatus.ERROR,
                fetch_error=str(exc),
            )

    def _json_ld_objects(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        objects: list[dict[str, Any]] = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            if not script.string:
                continue
            try:
                payload = json.loads(script.string)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                objects.append(payload)
            elif isinstance(payload, list):
                objects.extend(item for item in payload if isinstance(item, dict))
        return objects

    def _first_product_json(self, objects: list[dict[str, Any]]) -> dict[str, Any] | None:
        for item in objects:
            item_type = item.get("@type")
            if item_type == "Product" or (isinstance(item_type, list) and "Product" in item_type):
                return item
        return None

    def _title(self, soup: BeautifulSoup, product_json: dict[str, Any] | None) -> str | None:
        name = product_json.get("name") if product_json else None
        if isinstance(name, str):
            return name.strip()

        for attrs in [{"property": "og:title"}, {"name": "twitter:title"}]:
            content = self._meta_content(soup, attrs)
            if content:
                return content

        if soup.title and soup.title.string:
            return soup.title.string.strip()
        return None

    def _image(self, soup: BeautifulSoup, product_json: dict[str, Any] | None) -> str | None:
        if product_json:
            image = product_json.get("image")
            if isinstance(image, str):
                return image
            if isinstance(image, list) and image and isinstance(image[0], str):
                return image[0]

        return self._meta_content(soup, {"property": "og:image"})

    def _meta_content(self, soup: BeautifulSoup, attrs: dict[str, str]) -> str | None:
        tag = soup.find("meta", attrs=cast(Any, attrs))
        if not isinstance(tag, Tag):
            return None
        content = tag.get("content")
        return content.strip() if isinstance(content, str) else None

    def _price(
        self,
        soup: BeautifulSoup,
        product_json: dict[str, Any] | None,
    ) -> tuple[int | None, str | None]:
        offer = product_json.get("offers") if product_json else None
        if isinstance(offer, list):
            offer = offer[0] if offer else None

        if isinstance(offer, dict):
            cents = self._price_to_cents(offer.get("price"))
            currency = offer.get("priceCurrency")
            return cents, currency if isinstance(currency, str) else None

        text = soup.get_text(" ", strip=True)
        match = PRICE_RE.search(text)
        if match:
            return self._price_to_cents(match.group(1)), "USD"
        return None, None

    def _price_to_cents(self, value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(Decimal(str(value).replace("$", "").strip()) * 100)
        except (InvalidOperation, ValueError):
            return None

    def _availability(
        self,
        soup: BeautifulSoup,
        product_json: dict[str, Any] | None,
    ) -> Availability:
        offer = product_json.get("offers") if product_json else None
        if isinstance(offer, list):
            offer = offer[0] if offer else None
        if isinstance(offer, dict) and isinstance(offer.get("availability"), str):
            normalized = offer["availability"].lower()
            if "instock" in normalized or "in_stock" in normalized:
                return Availability.IN_STOCK
            if (
                "outofstock" in normalized
                or "out_of_stock" in normalized
                or "soldout" in normalized
            ):
                return Availability.OUT_OF_STOCK
            if "preorder" in normalized:
                return Availability.PREORDER
            if "backorder" in normalized:
                return Availability.BACKORDER

        text = soup.get_text(" ", strip=True).lower()
        if "out of stock" in text or "sold out" in text:
            return Availability.OUT_OF_STOCK
        if "pre-order" in text or "preorder" in text:
            return Availability.PREORDER
        if "backorder" in text:
            return Availability.BACKORDER
        if "add to cart" in text or "in stock" in text:
            return Availability.IN_STOCK
        return Availability.UNKNOWN

    def _safe_headers(self, headers: dict[str, str]) -> dict[str, str]:
        allowed = {
            "content-type",
            "x-datadome",
            "x-cache",
            "server",
            "x-cdn",
        }
        return {key.lower(): value for key, value in headers.items() if key.lower() in allowed}
