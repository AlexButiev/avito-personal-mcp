"""Read-only Avito search using the rendered search-result DOM."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


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


async def _submit_search_form(page: Page, origin: str, query: str) -> None:
    """Submit Avito's observed normal search form instead of guessing search URLs."""

    input_selector = '[data-marker="search-form/suggest/input"]'
    submit_selector = '[data-marker="search-form/submit-button"]'
    serp_selector = '[data-marker="catalog-serp"]'

    # Start from Avito's normal home page so the search is not accidentally
    # scoped to whichever listing/category tab happened to be selected by CDP.
    response = await page.goto(origin, wait_until="domcontentloaded")
    if response is not None and response.status >= 400:
        raise SearchDiscoveryError(f"Avito home page returned HTTP {response.status}")

    search_input = page.locator(input_selector).first
    submit_button = page.locator(submit_selector).first
    if not await search_input.count() or not await submit_button.count():
        raise SearchDiscoveryError("Avito search form did not match the observed page structure")

    await search_input.fill(query)
    before_url = page.url
    await submit_button.click()

    # Avito may perform the transition through client-side routing. Waiting for
    # the current page's already-reached load state is insufficient; wait for
    # the actual URL transition and then for the observed SERP root.
    try:
        await page.wait_for_url(lambda url: str(url) != before_url, timeout=10_000)
    except PlaywrightTimeoutError:
        # A same-URL refresh is possible; the SERP marker below remains the
        # source of truth for whether search really completed.
        pass

    try:
        await page.locator(serp_selector).wait_for(state="attached", timeout=10_000)
    except PlaywrightTimeoutError as exc:
        raise SearchDiscoveryError(
            "Avito search did not reach the observed search-results page"
        ) from exc

    await page.wait_for_timeout(500)


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
