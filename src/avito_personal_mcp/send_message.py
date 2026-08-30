"""Guarded Avito message sending through the observed messenger UI."""

from __future__ import annotations

import hashlib
import re
import secrets
import time
from dataclasses import dataclass
from urllib.parse import quote

from playwright.async_api import Page

CHAT_ID_RE = re.compile(r"^[A-Za-z0-9_~-]{3,200}$")
MAX_MESSAGE_LENGTH = 4000
CONFIRMATION_TTL_SECONDS = 120


class SendMessageError(RuntimeError):
    """Raised when guarded message sending cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class PendingConfirmation:
    chat_id: str
    message_digest: str
    expires_at: float


_PENDING_CONFIRMATIONS: dict[str, PendingConfirmation] = {}


def validate_chat_id(chat_id: str) -> str:
    value = chat_id.strip()
    if not CHAT_ID_RE.fullmatch(value):
        raise SendMessageError("Invalid Avito chat/channel id.")
    return value


def validate_message_text(text: str) -> str:
    if not isinstance(text, str):
        raise SendMessageError("Message text must be a string.")
    value = text.strip()
    if not value:
        raise SendMessageError("Message text cannot be empty or whitespace-only.")
    if len(value) > MAX_MESSAGE_LENGTH:
        raise SendMessageError(
            f"Message text is too long; maximum is {MAX_MESSAGE_LENGTH} characters."
        )
    return value


def _message_digest(chat_id: str, text: str) -> str:
    payload = f"{chat_id}\0{text}".encode()
    return hashlib.sha256(payload).hexdigest()


def _purge_expired(now: float | None = None) -> None:
    current = time.monotonic() if now is None else now
    expired = [
        token
        for token, pending in _PENDING_CONFIRMATIONS.items()
        if pending.expires_at <= current
    ]
    for token in expired:
        _PENDING_CONFIRMATIONS.pop(token, None)


def create_confirmation(chat_id: str, text: str) -> tuple[str, int]:
    """Create a short-lived, process-memory-only confirmation token."""

    chat_id = validate_chat_id(chat_id)
    text = validate_message_text(text)
    _purge_expired()

    token = secrets.token_urlsafe(24)
    _PENDING_CONFIRMATIONS[token] = PendingConfirmation(
        chat_id=chat_id,
        message_digest=_message_digest(chat_id, text),
        expires_at=time.monotonic() + CONFIRMATION_TTL_SECONDS,
    )
    return token, CONFIRMATION_TTL_SECONDS


def consume_confirmation(token: str, chat_id: str, text: str) -> None:
    """Validate and consume a token before any intentional send action."""

    chat_id = validate_chat_id(chat_id)
    text = validate_message_text(text)
    _purge_expired()

    pending = _PENDING_CONFIRMATIONS.pop(token, None)
    if pending is None:
        raise SendMessageError("Confirmation token is invalid, expired, or already used.")
    if pending.chat_id != chat_id:
        raise SendMessageError("Confirmation does not match the requested chat.")
    if not secrets.compare_digest(pending.message_digest, _message_digest(chat_id, text)):
        raise SendMessageError("Confirmation does not match the requested message text.")


def sanitized_preview(text: str, limit: int = 160) -> str:
    """Return a compact preview suitable for an MCP confirmation response."""

    value = " ".join(validate_message_text(text).split())
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


async def _current_outgoing_matches(page: Page, text: str) -> int:
    """Count visible outgoing text messages exactly matching ``text``."""

    return await page.locator(
        '[data-marker="message"][class*="message-base-module-right-"] '
        '[data-marker="messageText"]'
    ).evaluate_all(
        """
        (nodes, expected) => nodes.filter(
            node => (node.textContent || '').trim() === expected
        ).length
        """,
        text,
    )


async def send_confirmed_message(
    page: Page,
    origin: str,
    chat_id: str,
    text: str,
) -> dict[str, object]:
    """Send one already-confirmed text message using observed Avito UI controls.

    The caller must consume a confirmation token before calling this function.
    This routine deliberately performs no automatic send retry.
    """

    chat_id = validate_chat_id(chat_id)
    text = validate_message_text(text)
    channel_url = f"{origin}/profile/messenger/channel/{quote(chat_id, safe='~_-')}"

    if not page.url.startswith(channel_url):
        response = await page.goto(channel_url, wait_until="domcontentloaded")
        if response is not None and response.status >= 400:
            raise SendMessageError(f"Avito returned HTTP {response.status} for the conversation.")

    await page.wait_for_timeout(500)

    if "/profile/login" in page.url or "/login" in page.url:
        raise SendMessageError("Avito authentication is required.")

    composer = page.locator('[data-marker="reply/input"]')
    if await composer.count() != 1:
        raise SendMessageError("Message composer is unavailable or the messenger DOM changed.")

    before_matches = await _current_outgoing_matches(page, text)

    await composer.fill(text)
    await page.wait_for_timeout(150)

    send_button = page.locator('[data-marker="reply/send"]')
    if await send_button.count() != 1:
        await composer.fill("")
        raise SendMessageError("Send control did not appear after entering the message.")

    # Intentional write action. There is deliberately no retry after this click.
    await send_button.click()

    deadline = time.monotonic() + 6.0
    while time.monotonic() < deadline:
        await page.wait_for_timeout(200)
        after_matches = await _current_outgoing_matches(page, text)
        if after_matches > before_matches:
            return {
                "status": "sent",
                "chat_id": chat_id,
                "verified": True,
            }

    return {
        "status": "send_unverified",
        "chat_id": chat_id,
        "verified": False,
        "message": (
            "The send control was clicked once, but the resulting outgoing message could not "
            "be verified from the observed UI. The MCP did not retry to avoid duplicates."
        ),
    }
