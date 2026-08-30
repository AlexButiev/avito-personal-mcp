"""Read-only discovery of the user's own Avito listings from the profile DOM.

Avito's personal listings page renders listing cards directly in the document.
This module intentionally relies on stable ``data-marker`` attributes observed
in the authenticated browser session and avoids brittle CSS class names.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from playwright.async_api import Page

from avito_personal_mcp.navigation import (
    PrivatePageStateError,
    has_authenticated_marker,
    validate_private_page_state,
)

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
        response = await page.goto(f"{origin}{PROFILE_PATH}", wait_until="domcontentloaded")
        if response is not None and response.status >= 400:
            raise ListingsDiscoveryError(f"Avito profile page returned HTTP {response.status}")

    await page.wait_for_timeout(1000)
    authenticated = await has_authenticated_marker(page)

    raw = await page.evaluate(
        r"""
        () => {
            const cards = [...document.querySelectorAll('[data-marker^="item-snippet/"]')];
            const hasItemsForm = Boolean(
                document.querySelector('[data-marker="profile/items-form"]')
            );
            const hasTabs = Boolean(
                document.querySelector('[data-marker="personal-items-tabs"]')
            );

            return {
                pathname: location.pathname,
                hasProfileStructure: hasItemsForm && hasTabs,
                items: cards.map(card => {
                    const marker = card.getAttribute('data-marker') || '';
                    const id = marker.split('/')[1] || null;

                    const listingLinks = [...card.querySelectorAll('a[href]')]
                        .filter(a => {
                            const href = a.getAttribute('href') || '';
                            return href && !href.startsWith('/profile/');
                        });

                    const primaryLink = listingLinks.find(a => {
                        const text = (a.textContent || '').trim();
                        const title = (a.getAttribute('title') || '').trim();
                        return text || title;
                    }) || listingLinks[0] || null;

                    let title = null;
                    for (const link of listingLinks) {
                        const candidate = (
                            link.getAttribute('title') ||
                            link.getAttribute('aria-label') ||
                            link.textContent ||
                            ''
                        ).trim();
                        if (candidate) {
                            title = candidate;
                            break;
                        }
                    }

                    const cardText = (
                        card.innerText || card.textContent || ''
                    ).replace(/\s+/g, ' ').trim();
                    const priceMatch = cardText.match(
                        /(?:^|\s)(\d[\d\s\u00a0]*\s?(?:₽|руб\.?))(?:\s|$)/i
                    );
                    const price = priceMatch
                        ? priceMatch[1].replace(/\s+/g, ' ').trim()
                        : null;

                    let state = null;
                    if (card.querySelector(`[data-marker="publish-button/${id}"]`)) {
                        state = 'inactive';
                    } else if (card.querySelector('[data-marker="item-info-row_error"]')) {
                        state = 'attention_required';
                    }

                    return {
                        id,
                        href: primaryLink ? primaryLink.getAttribute('href') : null,
                        title,
                        price,
                        state,
                    };
                }),
            };
        }
        """
    )

    if not isinstance(raw, dict):
        raise ListingsDiscoveryError("Avito profile page returned an unexpected DOM result")

    try:
        validate_private_page_state(
            pathname=raw.get("pathname"),
            expected_path_prefix=PROFILE_PATH,
            authenticated=authenticated,
            has_expected_structure=raw.get("hasProfileStructure") is True,
        )
    except PrivatePageStateError as exc:
        raise ListingsDiscoveryError(str(exc)) from exc

    raw_items = raw.get("items")
    if not isinstance(raw_items, list):
        raise ListingsDiscoveryError("Avito profile page returned an invalid listing list")

    normalized: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        normalized.append(normalize_listing(item, origin))

    return normalized
