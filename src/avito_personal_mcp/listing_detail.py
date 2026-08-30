"""Read-only discovery of one Avito listing from the rendered listing page."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import Page

from avito_personal_mcp.listings import discover_own_listings

LISTING_ID_RE = re.compile(r"(?:^|_)(\d{4,})(?:$|[/?#])")


class ListingDetailError(RuntimeError):
    """Raised when a listing detail page cannot be resolved or parsed safely."""


def extract_listing_id(value: int | str) -> int:
    """Extract a numeric Avito listing id from an integer, numeric string, or URL."""

    if isinstance(value, int):
        if value <= 0:
            raise ListingDetailError("Listing id must be positive")
        return value

    if not isinstance(value, str):
        raise ListingDetailError("Listing reference must be an id or Avito URL")

    text = value.strip()
    if text.isdigit():
        return int(text)

    match = LISTING_ID_RE.search(urlparse(text).path)
    if not match:
        raise ListingDetailError("Could not extract listing id from the supplied reference")
    return int(match.group(1))


async def resolve_listing_url(page: Page, origin: str, reference: int | str) -> tuple[int, str]:
    """Resolve a canonical own-listing URL without guessing Avito endpoint paths."""

    listing_id = extract_listing_id(reference)

    if isinstance(reference, str) and reference.strip().startswith(origin):
        parsed = urlparse(reference.strip())
        return listing_id, f"{origin}{parsed.path}"

    listings = await discover_own_listings(page, origin)
    for listing in listings:
        if listing.get("id") == listing_id and isinstance(listing.get("url"), str):
            return listing_id, listing["url"]

    raise ListingDetailError("Listing id was not found among the authenticated user's listings")


def normalize_detail(raw: dict[str, Any], listing_id: int, url: str) -> dict[str, Any]:
    """Normalize safe listing metadata collected from stable DOM markers."""

    def clean(name: str) -> str | None:
        value = raw.get(name)
        if not isinstance(value, str):
            return None
        value = " ".join(value.split())
        return value or None

    raw_params = raw.get("params")
    if not isinstance(raw_params, list):
        raw_params = []

    params: list[str] = []
    for value in raw_params:
        if not isinstance(value, str) or not value.strip():
            continue
        normalized = " ".join(value.split())
        if normalized in params:
            continue
        params.append(normalized)

    # Avito's parameter block may expose both the complete row (for example
    # ``State: Used``) and a nested label node (``State:``). Keep only the
    # complete value when both are present.
    params = [
        value
        for value in params
        if not (
            value.endswith(":")
            and any(other != value and other.startswith(f"{value} ") for other in params)
        )
    ]

    state = "inactive" if raw.get("expired") or raw.get("can_activate") else "active_or_unknown"

    return {
        "id": listing_id,
        "url": url,
        "title": clean("title"),
        "price": clean("price"),
        "description": clean("description"),
        "params": params,
        "seller_name": clean("seller_name"),
        "state": state,
    }


async def discover_listing_detail(
    page: Page,
    origin: str,
    reference: int | str,
) -> dict[str, Any]:
    """Read one listing page using only observed stable ``data-marker`` attributes."""

    listing_id, url = await resolve_listing_url(page, origin, reference)
    if page.url.split("?", 1)[0] != url:
        response = await page.goto(url, wait_until="domcontentloaded")
        if response is not None and response.status >= 400:
            raise ListingDetailError(f"Listing page returned HTTP {response.status}")

    await page.wait_for_timeout(750)

    raw = await page.evaluate(
        """
        () => {
            const text = (selector) => {
                const el = document.querySelector(selector);
                return el ? (el.textContent || '').trim() || null : null;
            };

            const paramsRoot = document.querySelector('[data-marker="item-view/item-params"]');
            const params = paramsRoot
                ? [...paramsRoot.querySelectorAll('li, p, span, div')]
                    .map(el => (el.textContent || '').trim())
                    .filter(Boolean)
                    .filter((value, index, array) => array.indexOf(value) === index)
                    .filter(value => value.length <= 300)
                : [];

            return {
                title: text('[data-marker="item-view/title-info"]')
                    || text('[data-marker="item-view-seller/title-info"]'),
                price: text('[data-marker="item-view/item-price"]')
                    || text('[data-marker="item-view-seller/item-price"]'),
                description: text('[data-marker="item-view/item-description"]'),
                params,
                seller_name: text('[data-marker="seller-info/name"]'),
                expired: Boolean(document.querySelector('[data-marker="expired-item-note"]')),
                can_activate: Boolean(document.querySelector('[data-marker="activate-item-button"]')),
                has_title_marker: Boolean(document.querySelector('[data-marker="item-view/title-info"], [data-marker="item-view-seller/title-info"]')),
            };
        }
        """
    )

    if not isinstance(raw, dict):
        raise ListingDetailError("Avito listing page returned an unexpected DOM result")
    if not raw.get("has_title_marker"):
        raise ListingDetailError("Avito listing page structure did not match the observed listing DOM")

    return normalize_detail(raw, listing_id, url)
