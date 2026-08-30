from avito_personal_mcp.search import normalize_search_result


def test_normalize_search_result() -> None:
    result = normalize_search_result(
        {
            "id": "1234567890",
            "href": "/syktyvkar/noutbuki/example_1234567890",
            "title": "  Ноутбук Lenovo  ",
            "price": " 45 000 ₽ ",
            "location": " Сыктывкар ",
            "date": " сегодня в 10:00 ",
            "seller": " Частное лицо ",
        },
        "https://www.avito.ru",
    )

    assert result == {
        "id": 1234567890,
        "title": "Ноутбук Lenovo",
        "url": "https://www.avito.ru/syktyvkar/noutbuki/example_1234567890",
        "price": "45 000 ₽",
        "location": "Сыктывкар",
        "date": "сегодня в 10:00",
        "seller": "Частное лицо",
    }


def test_normalize_search_result_allows_missing_optional_text() -> None:
    result = normalize_search_result(
        {
            "id": "1234567890",
            "href": "/item_1234567890",
            "title": "Item",
            "price": None,
            "location": None,
            "date": None,
            "seller": None,
        },
        "https://www.avito.ru",
    )

    assert result["price"] is None
    assert result["location"] is None
    assert result["date"] is None
    assert result["seller"] is None


def test_normalize_search_result_extracts_id_from_observed_href() -> None:
    result = normalize_search_result(
        {
            "id": None,
            "href": (
                "/syktyvkar/noutbuki/noutbuk_8361138738"
                "?context=sanitized"
            ),
            "title": "Ноутбук",
            "price": "10 000 ₽",
            "location": "Сыктывкар",
            "date": None,
            "seller": None,
        },
        "https://www.avito.ru",
    )

    assert result["id"] == 8361138738
    assert result["url"].startswith(
        "https://www.avito.ru/syktyvkar/noutbuki/noutbuk_8361138738"
    )
