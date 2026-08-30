"""Read-only discovery of the user's own Avito listings from the profile DOM.

Avito's personal listings page renders listing cards directly in the document.
This module intentionally relies on stable ``data-marker`` attributes observed
in the authenticated browser session and avoids brittle CSS class names.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from playwright.async_api import Page

ITEM_MARKER_RE = re.compile(r"^item-snippet/(\d+)$")
PROFILE_PATH = "/profile"


class ListingsDiscoveryError(RuntimeError):
    """Raised when own-listing discovery cannot be completed safely."""


def normalize_listing(raw: dict[str, Any], origin: str) -> dict[str, Any]:
    """Normalize one listing record collected from the profile DOM."""

    listing_id = raw.get("id")
    if not isinstance(listing_id, str) or not listing_id.isdigit():
        raise ListingsDiscoveryError("Listing card has no valid numeric id")

    href = raw.get("href")
    url = urljoin(origin, href) if isinstance(href, str) and href else None

    title = raw.get("title")
    if isinstance(title, str):
        title = title.strip() or None
    else:
        title = None

    price = raw.get("price")
    if isinstance(price, str):
        price = price.strip() or None
    else:
        price = None

    state = raw.get("state")
    if isinstance(state, str):
        state = state.strip() or None
    else:
        state = None

    return {
        "id": int(listing_id),
        "title": title,
        "url": url,
        "price": price,
        "state": state,
    }


async def discover_own_listings(page: Page, origin: str) -> list[dict[str, Any]]:
    """Collect listing metadata from ``/profile`` without triggering write actions."""

    if not page.url.startswith(f"{origin}{PROFILE_PATH}"):
        await page.goto(f"{origin}{PROFILE_PATH}", wait_until="domcontentloaded")

    await page.wait_for_timeout(1000)

    raw_items = await page.evaluate(
        """
        () => {
            const cards = [...document.querySelectorAll('[data-marker^="item-snippet/"]')];

            return cards.map(card => {
                const marker = card.getAttribute('data-marker') || '';
                const id = marker.split('/')[1] || null;

                const listingLinks = [...card.querySelectorAll('a[href]')]
                    .filter(a => {
                        const href = a.getAttribute('href') || '';
                        return href && !href.startsWith('/profile/');
                    });

                const primaryLink = listingLinks[0] || null;
                const title = primaryLink
                    ? (primaryLink.getAttribute('title') || primaryLink.textContent || null)
                    : null;

                const textNodes = [...card.querySelectorAll('*')]
                    .map(el => (el.textContent || '').trim())
                    .filter(Boolean);

                const price = textNodes.find(text => /(?:₽|руб\.?)/i.test(text)) || null;

                let state = null;
                if (card.querySelector('[data-marker="item-info-row_error"]')) {
                    state = 'attention_required';
                } else if (card.querySelector(`[data-marker="publish-button/${id}"]`)) {
                    state = 'inactive';
                }

                return {
                    id,
                    href: primaryLink ? primaryLink.getAttribute('href') : null,
                    title,
                    price,
                    state,
                };
            });
        }
        """
    )

    if not isinstance(raw_items, list):
        raise ListingsDiscoveryError("Avito profile page returned an unexpected DOM result")

    normalized: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        normalized.append(normalize_listing(item, origin))

    return normalized
