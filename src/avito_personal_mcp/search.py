"""Read-only Avito search using the rendered search-result DOM."""

from __future__ import annotations

import re
from typing import Any, TypedDict
from urllib.parse import urljoin

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from avito_personal_mcp.navigation import canonical_same_origin_url


class SearchDiscoveryError(RuntimeError):
    """Raised when Avito search results cannot be resolved or parsed safely."""


LISTING_ID_RE = re.compile(r"_(\d+)(?:\?|$)")
PRICE_TEXT_RE = re.compile(r"\d[\d\s\u00a0]*")

# These values are not URL parameters. They are the data markers observed on
# Avito's rendered sort menu. Keeping the public API as logical names means a
# client cannot pass an arbitrary selector or a frontend-specific code.
SORT_MARKERS = {
    "default": "sort/custom-option(101)",
    "price_asc": "sort/custom-option(1)",
    "price_desc": "sort/custom-option(2)",
    "date_desc": "sort/custom-option(104)",
    "discount_desc": "sort/custom-option(172297_desc)",
}

SERP_SELECTOR = '[data-marker="catalog-serp"]'
TITLE_SELECTOR = '[data-marker="item-title"]'
SEARCH_INPUT_SELECTOR = '[data-marker="search-form/suggest/input"]'
SEARCH_SUBMIT_SELECTOR = '[data-marker="search-form/submit-button"]'
FILTERS_BUTTON_SELECTOR = '[data-marker="filters-popup/button"]'
PRICE_FROM_SELECTOR = '[data-marker="price-from/input"]'
PRICE_TO_SELECTOR = '[data-marker="price-to/input"]'
FILTERS_CONFIRM_SELECTOR = '[data-marker="filters-popup/confirm-button"]'
SORT_TITLE_SELECTOR = '[data-marker="sort/title"]'


class SearchOptions(TypedDict):
    """Validated first-slice options supported by Avito's observed generic UI."""

    min_price: int | None
    max_price: int | None
    sort: str | None


def validate_search_options(
    min_price: int | None,
    max_price: int | None,
    sort: str | None,
) -> SearchOptions:
    """Validate the deliberately small, observed first slice of SERP filters."""

    for field_name, value in (("min_price", min_price), ("max_price", max_price)):
        # bool is an int subclass, but accepting True as a price makes neither
        # the API nor a future JSON client unambiguous.
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise SearchDiscoveryError(f"{field_name} must be a non-negative integer")
        if value is not None and value < 0:
            raise SearchDiscoveryError(f"{field_name} must be a non-negative integer")

    if min_price is not None and max_price is not None and min_price > max_price:
        raise SearchDiscoveryError("min_price must not be greater than max_price")

    if sort is not None and sort not in SORT_MARKERS:
        supported = ", ".join(SORT_MARKERS)
        raise SearchDiscoveryError(f"sort must be one of: {supported}")

    return {
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort,
    }


def normalize_search_result(raw: dict[str, Any], origin: str) -> dict[str, Any]:
    """Normalize one search-result card collected from observed stable DOM markers."""

    href = raw.get("href")
    if not isinstance(href, str) or not href:
        raise SearchDiscoveryError("Search result has no listing URL")

    try:
        safe_url = canonical_same_origin_url(urljoin(origin, href), origin)
    except ValueError as exc:
        raise SearchDiscoveryError(
            "Search result URL is outside the configured Avito origin"
        ) from exc

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
        "url": safe_url,
        "price": clean("price"),
        "location": clean("location"),
        "date": clean("date"),
        "seller": clean("seller"),
    }


def _display_price_as_int(value: object) -> int | None:
    """Extract the first displayed whole-ruble amount from an Avito price."""

    if not isinstance(value, str):
        return None
    match = PRICE_TEXT_RE.search(value)
    if match is None:
        return None
    digits = "".join(filter(str.isdigit, match.group()))
    return int(digits) if digits else None


def _validate_observed_result_options(
    results: list[dict[str, Any]],
    options: SearchOptions,
) -> None:
    """Fail closed if rendered cards contradict an explicitly requested option."""

    has_price_constraint = (
        options["min_price"] is not None or options["max_price"] is not None
    )
    needs_ordered_price = options["sort"] == "price_asc"
    if not has_price_constraint and not needs_ordered_price:
        return

    prices: list[int] = []
    for result in results:
        price = _display_price_as_int(result.get("price"))
        if price is None:
            raise SearchDiscoveryError(
                "Avito returned a result without a readable price for the requested filter"
            )
        if options["min_price"] is not None and price < options["min_price"]:
            raise SearchDiscoveryError("Avito returned a result below the requested minimum price")
        if options["max_price"] is not None and price > options["max_price"]:
            raise SearchDiscoveryError("Avito returned a result above the requested maximum price")
        prices.append(price)

    if needs_ordered_price and prices != sorted(prices):
        raise SearchDiscoveryError("Avito results are not ordered by ascending displayed price")


async def _results_ready(page: Page, serp_selector: str, title_selector: str) -> bool:
    """Return whether the current live document contains hydrated Avito results."""

    try:
        has_serp = await page.locator(serp_selector).count() > 0
        has_titles = await page.locator(title_selector).count() > 0
    except Exception:
        return False
    return has_serp and has_titles


async def _wait_for_hydrated_results(page: Page, operation: str) -> None:
    """Wait for an observed, populated SERP after a normal UI action."""

    for _ in range(40):
        if await _results_ready(page, SERP_SELECTOR, TITLE_SELECTOR):
            return
        await page.wait_for_timeout(500)

    raise SearchDiscoveryError(
        f"Avito {operation} did not reach the observed search-results page"
    )


async def _wait_for_serp_refresh(
    page: Page,
    before_url: str,
    operation: str,
) -> None:
    """Wait for a post-action refresh without manufacturing or parsing URL state.

    Avito retains old cards while client-side navigation starts, so checking only
    for a populated catalog would accept a stale result set. Depending on its
    current layout, Avito either changes the browser URL or briefly removes the
    hydrated SERP while it applies price/sort state. Both are observable effects
    of the visible controls; this function never parses or constructs URL state.
    """

    saw_unready_serp = False
    for _ in range(40):
        url_changed = page.url != before_url
        hydrated = await _results_ready(page, SERP_SELECTOR, TITLE_SELECTOR)
        if not hydrated:
            saw_unready_serp = True
        if hydrated and (url_changed or saw_unready_serp):
            return
        await page.wait_for_timeout(250)

    raise SearchDiscoveryError(f"Avito {operation} did not refresh the result set")


async def _apply_price_filter(
    page: Page,
    min_price: int | None,
    max_price: int | None,
) -> None:
    """Apply only the observed price controls in Avito's visible filter popup."""

    filters_button = page.locator(FILTERS_BUTTON_SELECTOR).first
    compact_layout = bool(await filters_button.count()) and await filters_button.is_visible()
    if compact_layout:
        # Compact layout: the inputs live inside an observed popup.
        await filters_button.click()

    # The populated SERP is visible before Avito has always completed the
    # client-side initialization of its reactive range widget. Let the visible
    # controls settle before changing either value; otherwise the later widget
    # initialization can overwrite a value which Playwright just entered.
    await page.wait_for_timeout(1_500)

    price_from = page.locator(PRICE_FROM_SELECTOR).first
    price_to = page.locator(PRICE_TO_SELECTOR).first
    if not await price_from.count() or not await price_to.count():
        raise SearchDiscoveryError("Avito price inputs were not found")

    # The search always starts from Avito's normal home page. Explicitly
    # clearing an unspecified bound also avoids inheriting an unexpected UI
    # value if Avito restores a filter during page navigation. The observed
    # widget keeps both values when the upper value is set before the lower
    # value and the lower field commits the completed range.
    await price_to.fill("" if max_price is None else str(max_price))
    await price_from.fill("" if min_price is None else str(min_price))

    before_url = page.url
    if compact_layout:
        # Compact layout: the observed popup exposes a dedicated confirmation
        # control after its price values have been filled.
        confirm_button = page.locator(FILTERS_CONFIRM_SELECTOR).first
        if not await confirm_button.count() or not await confirm_button.is_visible():
            raise SearchDiscoveryError("Avito price filter did not match the observed popup")
        await confirm_button.click()
    else:
        # Expanded layout: apply from the last-updated lower field through
        # Enter; there is no popup or synthetic URL parameter to construct.
        await price_from.press("Enter")
    await _wait_for_serp_refresh(page, before_url, "price filter")

    for label, field, expected in (
        ("minimum", price_from, min_price),
        ("maximum", price_to, max_price),
    ):
        actual_digits = "".join(filter(str.isdigit, await field.input_value()))
        expected_digits = "" if expected is None else str(expected)
        if actual_digits != expected_digits:
            raise SearchDiscoveryError(f"Avito did not retain the requested {label} price")


async def _apply_sort(page: Page, sort: str) -> None:
    """Apply one fixed observed sort option through Avito's rendered menu."""

    sort_marker = SORT_MARKERS[sort]
    sort_title = page.locator(SORT_TITLE_SELECTOR).first
    if not await sort_title.count():
        raise SearchDiscoveryError("Avito sort control was not found")

    await sort_title.click()
    sort_option = page.locator(f'[data-marker="{sort_marker}"]').first
    try:
        await sort_option.wait_for(state="visible", timeout=3_000)
    except PlaywrightTimeoutError as exc:
        raise SearchDiscoveryError("Avito sort menu did not expose the selected option") from exc

    # Avito can remember a previously selected order. Re-selecting an already
    # checked option does not refresh the SERP, so treating its accessible
    # rendered state as success is both faster and more accurate than waiting
    # for a transition which should not occur.
    if await sort_option.get_attribute("aria-checked") == "true":
        await page.keyboard.press("Escape")
        return

    before_url = page.url
    await sort_option.click()
    await _wait_for_serp_refresh(page, before_url, "sort")


async def _submit_search_form(page: Page, origin: str, query: str) -> None:
    """Submit Avito's observed normal search form instead of guessing search URLs."""

    # Start from Avito's normal home page so the search is not accidentally
    # scoped to whichever listing/category tab happened to be selected by CDP.
    try:
        response = await page.goto(origin, wait_until="domcontentloaded", timeout=10_000)
    except PlaywrightTimeoutError as exc:
        raise SearchDiscoveryError("Avito home page did not reach DOM content in time") from exc
    if response is not None and response.status >= 400:
        raise SearchDiscoveryError(f"Avito home page returned HTTP {response.status}")

    search_input = page.locator(SEARCH_INPUT_SELECTOR).first
    submit_button = page.locator(SEARCH_SUBMIT_SELECTOR).first
    if not await search_input.count() or not await submit_button.count():
        raise SearchDiscoveryError("Avito search form did not match the observed page structure")

    await search_input.fill(query)

    # Avito can render an enabled button before the client-side search action
    # has finished attaching after a value change. Waiting for that observed UI
    # settling interval before the one normal click is more reliable than
    # guessing URL state or issuing a duplicate action.
    await page.wait_for_timeout(1_500)
    before_url = page.url
    await submit_button.click()
    try:
        await page.wait_for_url(lambda url: str(url) != before_url, timeout=10_000)
    except PlaywrightTimeoutError as exc:
        raise SearchDiscoveryError(
            "Avito search action did not navigate from the home page"
        ) from exc

    # Avito briefly passes through an intermediate blank DOM before the final
    # SERP hydrates. Poll the live document and require both the root and at
    # least one real listing title before parsing.
    await _wait_for_hydrated_results(page, "search")


async def search_avito(
    page: Page,
    origin: str,
    query: str,
    limit: int = 10,
    min_price: int | None = None,
    max_price: int | None = None,
    sort: str | None = None,
) -> list[dict[str, Any]]:
    """Search Avito using only normal rendered UI controls and result markers."""

    query = query.strip()
    if not query:
        raise SearchDiscoveryError("Search query must not be empty")
    if not 1 <= limit <= 50:
        raise SearchDiscoveryError("Search limit must be between 1 and 50")
    options = validate_search_options(min_price, max_price, sort)

    await _submit_search_form(page, origin, query)
    if options["min_price"] is not None or options["max_price"] is not None:
        await _apply_price_filter(
            page,
            options["min_price"],
            options["max_price"],
        )
    if options["sort"] is not None:
        await _apply_sort(page, options["sort"])

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

    _validate_observed_result_options(results, options)
    return results
