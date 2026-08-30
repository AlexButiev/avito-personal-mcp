from avito_personal_mcp.favorites import normalize_favorite


def test_normalize_favorite_with_location_and_date() -> None:
    result = normalize_favorite(
        {
            "marker": "item-2320509622",
            "lines": [
                "Дубовая шепа и руководство по использованию",
                "350 ₽",
                "Волгоградская обл., Нехаевский р-н,",
                "Нехаевское сельское поселение, станица Нехаевская",
                "07 июля, 21:42",
            ],
            "links": [
                {
                    "href": "/nehaevskaya/produkty_pitaniya/dubovaya_shepa_2320509622?context=x",
                    "text": None,
                },
                {
                    "href": "/nehaevskaya/produkty_pitaniya/dubovaya_shepa_2320509622?context=x",
                    "text": "Дубовая шепа и руководство по использованию",
                },
            ],
        },
        "https://www.avito.ru",
    )

    assert result == {
        "id": 2320509622,
        "title": "Дубовая шепа и руководство по использованию",
        "url": "https://www.avito.ru/nehaevskaya/produkty_pitaniya/dubovaya_shepa_2320509622?context=x",
        "price": "350 ₽",
        "location": (
            "Волгоградская обл., Нехаевский р-н, "
            "Нехаевское сельское поселение, станица Нехаевская"
        ),
        "date": "07 июля, 21:42",
    }


def test_normalize_favorite_inactive_card_without_location() -> None:
    result = normalize_favorite(
        {
            "marker": "item-7655256815",
            "lines": ["Клюква,варенье", "159 ₽", "Найти похожие"],
            "links": [
                {
                    "href": "/syktyvkar/produkty_pitaniya/klyukvavarene_7655256815?context=x",
                    "text": "Клюква,варенье",
                },
                {
                    "href": "/selection-items?ids=7655256815&type=similar",
                    "text": "Найти похожие",
                },
            ],
        },
        "https://www.avito.ru",
    )

    assert result["id"] == 7655256815
    assert result["title"] == "Клюква,варенье"
    assert result["price"] == "159 ₽"
    assert result["location"] is None
    assert result["date"] is None
