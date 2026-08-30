"""Read-only discovery of the authenticated user's Avito favorites."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.async_api import Page


class FavoritesDiscoveryError(RuntimeError):
    """Raised when the favorites page cannot be resolved or parsed safely."""


CARD_MARKER_RE = re.compile(r"^item-(\d+)$")
DATE_RE = re.compile(
    r"^(?:сегодня|вчера|\d{1,2}\s+[а-яё]+)(?:,?\s+в?\s*\d{1,2}:\d{2})?$",
    re.IGNORECASE,
)


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _listing_path_matches_id(href: str, listing_id: str) -> bool:
    path = urlparse(href).path
    return bool(re.search(rf"_{re.escape(listing_id)}$", path))


def normalize_favorite(raw: dict[str, Any], origin: str) -> dict[str, Any]:
    """Normalize one favorite collected from the observed favorites-card DOM."""

    marker = raw.get("marker")
    if not isinstance(marker, str):
        raise FavoritesDiscoveryError("Favorite card has no marker")

    match = CARD_MARKER_RE.fullmatch(marker)
    if not match:
        raise FavoritesDiscoveryError("Favorite card marker has no valid listing id")
    listing_id = match.group(1)

    links = raw.get("links")
    if not isinstance(links, list):
        raise FavoritesDiscoveryError("Favorite card has no links")

    href: str | None = None
    title: str | None = None
    for link in links:
        if not isinstance(link, dict):
            continue
        candidate = link.get("href")
        if not isinstance(candidate, str) or not candidate:
            continue
        if not _listing_path_matches_id(candidate, listing_id):
            continue

        href = candidate
        text = _clean(link.get("text"))
        if text:
            title = text
            break

    if href is None:
        raise FavoritesDiscoveryError("Favorite card has no listing URL")

    lines_raw = raw.get("lines")
    lines = [line for line in (_clean(item) for item in lines_raw or []) if line]
    if title is None and lines:
        title = lines[0]
    if title is None:
        raise FavoritesDiscoveryError("Favorite card has no title")

    remaining = lines[:]
    if remaining and remaining[0] == title:
        remaining = remaining[1:]

    price = next((line for line in remaining if "₽" in line), None)
    if price in remaining:
        remaining = remaining[remaining.index(price) + 1 :]

    remaining = [line for line in remaining if line.casefold() != "найти похожие"]

    date = next((line for line in reversed(remaining) if DATE_RE.fullmatch(line)), None)
    if date in remaining:
        remaining = remaining[: remaining.index(date)]

    location = " ".join(remaining) or None

    return {
        "id": int(listing_id),
        "title": title,
        "url": urljoin(origin, href),
        "price": price,
        "location": location,
        "date": date,
    }


async def discover_favorites(page: Page, origin: str) -> list[dict[str, Any]]:
    """Return favorites from Avito's normal authenticated favorites page."""

    response = await page.goto(f"{origin}/favorites", wait_until="domcontentloaded")
    if response is not None and response.status >= 400:
        raise FavoritesDiscoveryError(f"Avito favorites page returned HTTP {response.status}")

    await page.wait_for_timeout(750)

    raw = await page.evaluate(
        r"""
        () => {
            const tabs = document.querySelector('[data-marker="favorites-tabs"]');
            const cards = [...document.querySelectorAll('[data-marker^="item-"]')]
                .filter(el => /^item-\d+$/.test(el.getAttribute('data-marker') || ''));

            return {
                hasFavoritesPage: Boolean(tabs),
                cards: cards.map(card => ({
                    marker: card.getAttribute('data-marker'),
                    lines: (card.innerText || '')
                        .split('\n')
                        .map(line => line.trim())
                        .filter(Boolean),
                    links: [...card.querySelectorAll('a[href]')].map(a => ({
                        href: a.getAttribute('href'),
                        text: (a.textContent || '').trim() || null,
                    })),
                })),
            };
        }
        """
    )

    if not isinstance(raw, dict) or raw.get("hasFavoritesPage") is not True:
        raise FavoritesDiscoveryError(
            "Avito favorites page structure did not match the observed favorites DOM"
        )

    cards = raw.get("cards")
    if not isinstance(cards, list):
        raise FavoritesDiscoveryError("Avito favorites page returned an invalid card list")

    results: list[dict[str, Any]] = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        try:
            results.append(normalize_favorite(card, origin))
        except FavoritesDiscoveryError:
            continue

    return results
