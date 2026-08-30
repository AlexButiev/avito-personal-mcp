import pytest

from avito_personal_mcp.chats import ChatsDiscoveryError, normalize_chat


def test_normalize_regular_chat() -> None:
    result = normalize_chat(
        {
            "href": "/profile/messenger/channel/u2i-S9GumlRtHafzXtK9V_L~kg",
            "user_title": "Андрей",
            "item_title": "Мощный минипк R7-7840HS 32gbDDR5 780m 1tbSSD",
            "item_price": "45\u00a0000 ₽",
            "last_message": "Просто принесли на выкуп. Проверил и продаю",
            "datetime": "0:20",
            "lines": [
                "Андрей",
                "Мощный минипк R7-7840HS 32gbDDR5 780m 1tbSSD",
                "45\u00a0000 ₽",
                "Просто принесли на выкуп. Проверил и продаю",
                "0:20",
            ],
        },
        "https://www.avito.ru",
    )

    assert result == {
        "id": "u2i-S9GumlRtHafzXtK9V_L~kg",
        "url": "https://www.avito.ru/profile/messenger/channel/u2i-S9GumlRtHafzXtK9V_L~kg",
        "user_title": "Андрей",
        "item_title": "Мощный минипк R7-7840HS 32gbDDR5 780m 1tbSSD",
        "item_price": "45 000 ₽",
        "last_message": "Просто принесли на выкуп. Проверил и продаю",
        "datetime": "0:20",
    }


def test_normalize_service_chat_uses_local_title_fallback() -> None:
    result = normalize_chat(
        {
            "href": "/profile/messenger/channel/a2u-191717891-24847877",
            "user_title": None,
            "item_title": None,
            "item_price": None,
            "last_message": None,
            "datetime": None,
            "lines": ["Поддержка Авито", "Будем рады помочь"],
        },
        "https://www.avito.ru",
    )

    assert result["id"] == "a2u-191717891-24847877"
    assert result["user_title"] == "Поддержка Авито"
    assert result["item_title"] is None
    assert result["last_message"] is None


def test_normalize_chat_rejects_non_channel_url() -> None:
    with pytest.raises(ChatsDiscoveryError):
        normalize_chat(
            {
                "href": "/profile/messenger",
                "user_title": "Андрей",
                "lines": ["Андрей"],
            },
            "https://www.avito.ru",
        )
