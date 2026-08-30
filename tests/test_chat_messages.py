import pytest

from avito_personal_mcp.chat_messages import (
    ChatMessagesDiscoveryError,
    _validate_chat_id,
    _validate_limit,
    normalize_message,
)


def test_normalize_incoming_text_message() -> None:
    result = normalize_message(
        {
            "direction_class": "message-base-module-left-ClxRw",
            "text": "  Могу сегодня подъехать?  ",
            "has_image": False,
            "datetime": "2026-05-17T16:38:29",
        }
    )

    assert result == {
        "direction": "incoming",
        "type": "text",
        "text": "Могу сегодня подъехать?",
        "datetime": "2026-05-17T16:38:29",
    }


def test_normalize_outgoing_image_message() -> None:
    result = normalize_message(
        {
            "direction_class": "message-base-module-right-NSqaR",
            "text": None,
            "has_image": True,
            "datetime": "2026-06-01T19:30:12",
        }
    )

    assert result == {
        "direction": "outgoing",
        "type": "image",
        "text": None,
        "datetime": "2026-06-01T19:30:12",
    }


def test_normalize_unknown_other_message() -> None:
    result = normalize_message(
        {
            "direction_class": None,
            "text": None,
            "has_image": False,
            "datetime": None,
        }
    )

    assert result == {
        "direction": "unknown",
        "type": "other",
        "text": None,
        "datetime": None,
    }


def test_validate_chat_id_accepts_observed_formats() -> None:
    assert _validate_chat_id("a2u-191717891-24847877") == "a2u-191717891-24847877"
    assert _validate_chat_id("u2i-S9GumlRtHafzXtK9V_L~kg") == "u2i-S9GumlRtHafzXtK9V_L~kg"


@pytest.mark.parametrize(
    "value",
    ["", "../favorites", "abc/def", "https://www.avito.ru/profile/messenger", 123],
)
def test_validate_chat_id_rejects_unsafe_values(value: object) -> None:
    with pytest.raises(ChatMessagesDiscoveryError):
        _validate_chat_id(value)


@pytest.mark.parametrize("value", [0, 101, -1, True, "10"])
def test_validate_limit_rejects_invalid_values(value: object) -> None:
    with pytest.raises(ChatMessagesDiscoveryError):
        _validate_limit(value)
