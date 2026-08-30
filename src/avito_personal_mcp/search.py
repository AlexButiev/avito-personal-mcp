"""Read-only Avito search using the rendered search-result DOM."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


class SearchDiscoveryError(RuntimeError):
    """Raised when Avito search results cannot be resolved or parsed safely."""


LISTING_ID_RE = re.compile(r"_(\d+)(?:\?|$)")


def normalize_search_result(raw: dict[str, Any], origin: str) -> dict[str, Any]:
    """Normalize one search-result card collected from observed stable DOM markers."""

    href = raw.get("href")
    if not isinstance(href, str) or not href:
        raise SearchDiscoveryError("Search result has no listing URL")

    listing_id = raw.get("id")
    if not isinstance(listing_id, str) or not listing_id.isdigit():
        match = LISTING_ID_RE.search(href)
        if not match:
            raise SearchDiscoveryError("Search result has no valid numeric id")
        listing_id = match.group(1)

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


async def _submit_search_form(page: Page, origin: str, query: str) -> None:
    """Submit Avito's observed normal search form instead of guessing search URLs."""

    input_selector = '[data-marker="search-form/suggest/input"]'
    serp_selector = '[data-marker="catalog-serp"]'

    # Start from Avito's normal home page so the search is not accidentally
    # scoped to whichever listing/category tab happened to be selected by CDP.
    response = await page.goto(origin, wait_until="domcontentloaded")
    if response is not None and response.status >= 400:
        raise SearchDiscoveryError(f"Avito home page returned HTTP {response.status}")

    search_input = page.locator(input_selector).first
    if not await search_input.count():
        raise SearchDiscoveryError("Avito search form did not match the observed page structure")

    await search_input.fill(query)
    before_url = page.url

    # Live reconnaissance showed that pressing Enter in the observed search
    # input reliably triggers Avito's normal search flow. The page may first
    # visit a short-lived intermediate URL before rendering the final SERP.
    await search_input.press("Enter")

    try:
        await page.wait_for_url(lambda url: str(url) != before_url, timeout=10_000)
    except PlaywrightTimeoutError:
        pass

    try:
        await page.locator(serp_selector).wait_for(state="attached", timeout=15_000)
    except PlaywrightTimeoutError as exc:
        raise SearchDiscoveryError(
            "Avito search did not reach the observed search-results page"
        ) from exc

    # Give client-side hydration a short moment so item cards are populated.
    await page.wait_for_timeout(750)


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

    await _submit_search_form(page, origin, query)

    raw = await page.evaluate(
        r"""
        (limit) => {
            const root = document.querySelector('[data-marker="catalog-serp"]');
            if (!root) {
                return { hasSerp: false, items: [] };
            }

            const text = (card, marker) => {
                const el = card?.querySelector(`[data-marker="${marker}"]`);
                return el ? (el.textContent || '').trim() || null : null;
            };

            const findCard = (titleEl) => {
                let el = titleEl.parentElement;
                for (let depth = 0; el && depth < 12; depth++, el = el.parentElement) {
                    if (el.matches?.('[data-marker="item"]')) {
                        return el;
                    }
                    if (
                        el.querySelector?.('[data-marker="item-price"]') ||
                        el.querySelector?.('[data-marker="item-price-value"]') ||
                        el.querySelector?.('[data-marker="item-location"]') ||
                        el.querySelector?.('[data-marker="item-date"]')
                    ) {
                        return el;
                    }
                }
                return titleEl.parentElement;
            };

            const titles = [...root.querySelectorAll('[data-marker="item-title"]')];
            const items = titles.slice(0, limit).map(titleEl => {
                const card = findCard(titleEl);
                const href = titleEl.getAttribute('href');

                return {
                    id: null,
                    href,
                    title: (titleEl.textContent || '').trim() || null,
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
        raise SearchDiscoveryError(
            "Avito search page structure did not match the observed SERP DOM"
        )

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
