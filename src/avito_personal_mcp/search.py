"""Read-only Avito search using the rendered search-result DOM."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode, urljoin

from playwright.async_api import Page


class SearchDiscoveryError(RuntimeError):
    """Raised when Avito search results cannot be resolved or parsed safely."""


def normalize_search_result(raw: dict[str, Any], origin: str) -> dict[str, Any]:
    """Normalize one search-result card collected from observed stable DOM markers."""

    listing_id = raw.get("id")
    if not isinstance(listing_id, str) or not listing_id.isdigit():
        raise SearchDiscoveryError("Search result has no valid numeric id")

    href = raw.get("href")
    if not isinstance(href, str) or not href:
        raise SearchDiscoveryError("Search result has no listing URL")

    def clean(name: str) -> str | None:
        value = raw.get(name)
        if not isinstance(value, str):
            return None
        value = " ".join(value.split())
        return value or None

    return {
        "id": int(listing_id),
        "title": clean("title"),
        "url": urljoin(origin, href),
        "price": clean("price"),
        "location": clean("location"),
        "date": clean("date"),
        "seller": clean("seller"),
    }


async def search_avito(
    page: Page,
    origin: str,
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search Avito using only the normal rendered SERP and observed data markers."""

    query = query.strip()
    if not query:
        raise SearchDiscoveryError("Search query must not be empty")
    if not 1 <= limit <= 50:
        raise SearchDiscoveryError("Search limit must be between 1 and 50")

    search_url = f"{origin}/rossiya?{urlencode({'q': query})}"
    response = await page.goto(search_url, wait_until="domcontentloaded")
    if response is not None and response.status >= 400:
        raise SearchDiscoveryError(f"Avito search page returned HTTP {response.status}")

    await page.wait_for_timeout(1000)

    raw = await page.evaluate(
        r"""
        (limit) => {
            const root = document.querySelector('[data-marker="catalog-serp"]');
            if (!root) {
                return { hasSerp: false, items: [] };
            }

            const cards = [...root.querySelectorAll('[data-marker^="iva-item/"]')];

            const text = (card, marker) => {
                const el = card.querySelector(`[data-marker="${marker}"]`);
                return el ? (el.textContent || '').trim() || null : null;
            };

            const items = cards.slice(0, limit).map(card => {
                const marker = card.getAttribute('data-marker') || '';
                const id = marker.split('/')[1] || null;
                const titleEl = card.querySelector('[data-marker="item-title"]');
                const link = titleEl?.closest('a[href]') || card.querySelector('a[href]');

                return {
                    id,
                    href: link ? link.getAttribute('href') : null,
                    title: text(card, 'item-title'),
                    price: text(card, 'item-price-value') || text(card, 'item-price'),
                    location: text(card, 'item-location'),
                    date: text(card, 'item-date'),
                    seller: text(card, 'seller-info/summary'),
                };
            });

            return { hasSerp: true, items };
        }
        """,
        limit,
    )

    if not isinstance(raw, dict):
        raise SearchDiscoveryError("Avito search page returned an unexpected DOM result")
    if raw.get("hasSerp") is not True:
        raise SearchDiscoveryError("Avito search page structure did not match the observed SERP DOM")

    items = raw.get("items")
    if not isinstance(items, list):
        raise SearchDiscoveryError("Avito search page returned an invalid result list")

    results: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            results.append(normalize_search_result(item, origin))
        except SearchDiscoveryError:
            continue

    return results
