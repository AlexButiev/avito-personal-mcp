"""Read-only discovery of the authenticated user's Avito chat list."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.async_api import Page

from avito_personal_mcp.navigation import (
    PrivatePageStateError,
    has_authenticated_marker,
    validate_private_page_state,
)


class ChatsDiscoveryError(RuntimeError):
    """Raised when the messenger page cannot be resolved or parsed safely."""


CHANNEL_PATH_RE = re.compile(r"^/profile/messenger/channel/([^/?#]+)$")


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _extract_chat_id(href: str) -> str:
    path = urlparse(href).path
    match = CHANNEL_PATH_RE.fullmatch(path)
    if not match:
        raise ChatsDiscoveryError("Chat link has no valid channel identifier")
    return match.group(1)


def normalize_chat(raw: dict[str, Any], origin: str) -> dict[str, Any]:
    """Normalize one chat collected from the observed messenger channel DOM."""

    href = raw.get("href")
    if not isinstance(href, str) or not href:
        raise ChatsDiscoveryError("Chat has no channel link")

    chat_id = _extract_chat_id(href)
    user_title = _clean(raw.get("user_title"))
    item_title = _clean(raw.get("item_title"))
    item_price = _clean(raw.get("item_price"))
    last_message = _clean(raw.get("last_message"))
    datetime = _clean(raw.get("datetime"))

    lines_raw = raw.get("lines")
    lines = [line for line in (_clean(item) for item in lines_raw or []) if line]

    # Some Avito service chats do not render a channels/user-title marker. The
    # first visible line is still the channel title inside the same channelLink.
    if user_title is None and lines:
        user_title = lines[0]

    if user_title is None:
        raise ChatsDiscoveryError("Chat has no counterpart or channel title")

    return {
        "id": chat_id,
        "url": urljoin(origin, href),
        "user_title": user_title,
        "item_title": item_title,
        "item_price": item_price,
        "last_message": last_message,
        "datetime": datetime,
    }


async def discover_chats(page: Page, origin: str) -> list[dict[str, Any]]:
    """Return the visible chat list from Avito's normal authenticated messenger page."""

    response = await page.goto(f"{origin}/profile/messenger", wait_until="domcontentloaded")
    if response is not None and response.status >= 400:
        raise ChatsDiscoveryError(f"Avito messenger page returned HTTP {response.status}")

    await page.wait_for_timeout(750)
    authenticated = await has_authenticated_marker(page)

    raw = await page.evaluate(
        r"""
        () => {
            const links = [
                ...document.querySelectorAll(
                    'a[data-marker="channels/channelLink"][href]'
                )
            ];

            return {
                pathname: location.pathname,
                hasMessengerStructure: Boolean(
                    document.querySelector('[data-marker^="channels/"]')
                ),
                chats: links.map(link => ({
                    href: link.getAttribute('href'),
                    user_title: link.querySelector(
                        '[data-marker="channels/user-title"]'
                    )?.textContent?.trim() || null,
                    item_title: link.querySelector(
                        '[data-marker="channels/item-title"]'
                    )?.textContent?.trim() || null,
                    item_price: link.querySelector(
                        '[data-marker="channels/item-price"]'
                    )?.textContent?.trim() || null,
                    last_message: link.querySelector(
                        '[data-marker="channels/last-message"]'
                    )?.textContent?.trim() || null,
                    datetime: link.querySelector(
                        '[data-marker="channels/channel-datetime"]'
                    )?.textContent?.trim() || null,
                    lines: (link.innerText || '')
                        .split('\n')
                        .map(line => line.trim())
                        .filter(Boolean),
                })),
            };
        }
        """
    )

    if not isinstance(raw, dict):
        raise ChatsDiscoveryError("Avito messenger returned an invalid page payload")

    try:
        validate_private_page_state(
            pathname=raw.get("pathname"),
            expected_path_prefix="/profile/messenger",
            authenticated=authenticated,
            has_expected_structure=raw.get("hasMessengerStructure") is True,
        )
    except PrivatePageStateError as exc:
        raise ChatsDiscoveryError(str(exc)) from exc

    chats = raw.get("chats")
    if not isinstance(chats, list):
        raise ChatsDiscoveryError("Avito messenger returned an invalid chat list")

    results: list[dict[str, Any]] = []
    for chat in chats:
        if not isinstance(chat, dict):
            continue
        try:
            results.append(normalize_chat(chat, origin))
        except ChatsDiscoveryError:
            continue

    return results
