from __future__ import annotations

import pytest

from avito_personal_mcp import send_message
from avito_personal_mcp.send_message import (
    SendMessageError,
    consume_confirmation,
    create_confirmation,
    sanitized_preview,
    validate_chat_id,
    validate_message_text,
)


@pytest.fixture(autouse=True)
def clear_pending_confirmations() -> None:
    send_message._PENDING_CONFIRMATIONS.clear()
    yield
    send_message._PENDING_CONFIRMATIONS.clear()


def test_validate_chat_id_accepts_observed_channel_characters() -> None:
    assert validate_chat_id("abc~DEF_123-xyz") == "abc~DEF_123-xyz"


@pytest.mark.parametrize("value", ["", " ", "../escape", "abc/def", "abc?def", "abc def"])
def test_validate_chat_id_rejects_unsafe_values(value: str) -> None:
    with pytest.raises(SendMessageError):
        validate_chat_id(value)


def test_validate_message_text_trims_outer_whitespace() -> None:
    assert validate_message_text("  hello world  ") == "hello world"


def test_validate_message_text_rejects_blank() -> None:
    with pytest.raises(SendMessageError):
        validate_message_text(" \n\t ")


def test_validate_message_text_rejects_over_limit() -> None:
    with pytest.raises(SendMessageError):
        validate_message_text("x" * (send_message.MAX_MESSAGE_LENGTH + 1))


def test_confirmation_is_one_time_use() -> None:
    token, ttl = create_confirmation("chat_123", "hello")

    assert ttl == send_message.CONFIRMATION_TTL_SECONDS
    consume_confirmation(token, "chat_123", "hello")

    with pytest.raises(SendMessageError, match="invalid, expired, or already used"):
        consume_confirmation(token, "chat_123", "hello")


def test_confirmation_rejects_changed_chat() -> None:
    token, _ = create_confirmation("chat_123", "hello")

    with pytest.raises(SendMessageError, match="requested chat"):
        consume_confirmation(token, "chat_456", "hello")

    assert token not in send_message._PENDING_CONFIRMATIONS


def test_confirmation_rejects_changed_message() -> None:
    token, _ = create_confirmation("chat_123", "hello")

    with pytest.raises(SendMessageError, match="message text"):
        consume_confirmation(token, "chat_123", "different")

    assert token not in send_message._PENDING_CONFIRMATIONS


def test_expired_confirmation_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    now = 1000.0
    monkeypatch.setattr(send_message.time, "monotonic", lambda: now)
    token, _ = create_confirmation("chat_123", "hello")

    monkeypatch.setattr(
        send_message.time,
        "monotonic",
        lambda: now + send_message.CONFIRMATION_TTL_SECONDS + 1,
    )

    with pytest.raises(SendMessageError, match="invalid, expired, or already used"):
        consume_confirmation(token, "chat_123", "hello")


def test_preview_collapses_whitespace_and_truncates() -> None:
    assert sanitized_preview("hello\n\nworld") == "hello world"
    preview = sanitized_preview("x" * 200, limit=20)
    assert preview == "x" * 19 + "…"
