import pytest

from avito_personal_mcp.listings import ListingsDiscoveryError, normalize_listing


def test_normalizes_listing():
    listing = normalize_listing(
        {
            "id": "1234567890",
            "href": "/city/category/example_1234567890",
            "title": "  Example listing  ",
            "price": "  1 500 ₽  ",
            "state": " inactive ",
        },
        "https://www.avito.ru",
    )

    assert listing == {
        "id": 1234567890,
        "title": "Example listing",
        "url": "https://www.avito.ru/city/category/example_1234567890",
        "price": "1 500 ₽",
        "state": "inactive",
    }


def test_allows_missing_optional_fields():
    listing = normalize_listing(
        {
            "id": "1234567890",
            "href": None,
            "title": None,
            "price": None,
            "state": None,
        },
        "https://www.avito.ru",
    )

    assert listing == {
        "id": 1234567890,
        "title": None,
        "url": None,
        "price": None,
        "state": None,
    }


def test_rejects_invalid_listing_id():
    with pytest.raises(ListingsDiscoveryError, match="valid numeric id"):
        normalize_listing(
            {
                "id": "not-an-id",
                "href": "/example",
            },
            "https://www.avito.ru",
        )
