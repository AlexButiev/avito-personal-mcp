"""Read-only discovery of messages from one authenticated Avito conversation."""

from __future__ import annotations

import re
from typing import Any

from playwright.async_api import Page

from avito_personal_mcp.navigation import (
    PrivatePageStateError,
    has_authenticated_marker,
    validate_private_page_state,
)


class ChatMessagesDiscoveryError(RuntimeError):
    """Raised when one Avito conversation cannot be resolved or parsed safely."""


CHAT_ID_RE = re.compile(r"^[A-Za-z0-9_~.-]+$")


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _validate_chat_id(chat_id: object) -> str:
    if not isinstance(chat_id, str):
        raise ChatMessagesDiscoveryError("Chat id must be a string")
    value = chat_id.strip()
    if not value or not CHAT_ID_RE.fullmatch(value):
        raise ChatMessagesDiscoveryError("Chat id has an invalid format")
    return value


def _validate_limit(limit: object) -> int:
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ChatMessagesDiscoveryError("Message limit must be an integer")
    if limit < 1 or limit > 100:
        raise ChatMessagesDiscoveryError("Message limit must be between 1 and 100")
    return limit


def normalize_message(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize one message from the observed Avito messenger DOM."""

    direction_class = _clean(raw.get("direction_class"))
    if direction_class and "message-base-module-right-" in direction_class:
        direction = "outgoing"
    elif direction_class and "message-base-module-left-" in direction_class:
        direction = "incoming"
    else:
        direction = "unknown"

    text = _clean(raw.get("text"))
    datetime = _clean(raw.get("datetime"))
    has_image = raw.get("has_image") is True

    if text is not None:
        message_type = "text"
    elif has_image:
        message_type = "image"
    else:
        message_type = "other"

    return {
        "direction": direction,
        "type": message_type,
        "text": text,
        "datetime": datetime,
    }


async def discover_chat_messages(
    page: Page,
    origin: str,
    chat_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return recent visible messages from one Avito conversation read-only.

    Navigating to a conversation may cause Avito itself to mark that conversation
    as read. This function performs no intentional message mutation.
    """

    normalized_chat_id = _validate_chat_id(chat_id)
    normalized_limit = _validate_limit(limit)
    target_path = f"/profile/messenger/channel/{normalized_chat_id}"

    if page.url.startswith(origin + target_path):
        response = None
    else:
        response = await page.goto(origin + target_path, wait_until="domcontentloaded")

    if response is not None and response.status >= 400:
        raise ChatMessagesDiscoveryError(
            f"Avito conversation page returned HTTP {response.status}"
        )

    await page.wait_for_timeout(750)

    raw = await page.evaluate(
        r"""
        (limit) => {
            const messages = [
                ...document.querySelectorAll('[data-marker="message"]')
            ];

            return {
                pathname: location.pathname,
                hasMessenger: Boolean(
                    document.querySelector('[data-marker="desktop-messenger"]') ||
                    document.querySelector('[data-marker^="channels/"]') ||
                    document.querySelector('[data-marker="reply/input"]') ||
                    document.querySelector('[data-marker="message"]')
                ),
                messages: messages.slice(-limit).map(message => {
                    const classNames = typeof message.className === 'string'
                        ? message.className.split(/\s+/).filter(Boolean)
                        : [];
                    const directionClass = classNames.find(name =>
                        /message-base-module-(left|right)-/.test(name)
                    ) || null;
                    const time = message.querySelector('time[datetime]');

                    return {
                        direction_class: directionClass,
                        text: message.querySelector(
                            '[data-marker="messageText"]'
                        )?.textContent?.trim() || null,
                        has_image: Boolean(
                            message.querySelector('[data-marker="messageImage"]')
                        ),
                        datetime: time?.getAttribute('datetime') || null,
                    };
                }),
            };
        }
        """,
        normalized_limit,
    )

    if not isinstance(raw, dict):
        raise ChatMessagesDiscoveryError("Avito conversation returned an invalid page payload")

    try:
        validate_private_page_state(
            pathname=raw.get("pathname"),
            expected_path_prefix=target_path,
            authenticated=await has_authenticated_marker(page),
            has_expected_structure=raw.get("hasMessenger") is True,
        )
    except PrivatePageStateError as exc:
        raise ChatMessagesDiscoveryError(str(exc)) from exc

    messages = raw.get("messages")
    if not isinstance(messages, list):
        raise ChatMessagesDiscoveryError("Avito conversation returned an invalid message list")

    results: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        results.append(normalize_message(message))

    return results
