import pytest

from avito_personal_mcp.listing_detail import (
    ListingDetailError,
    extract_listing_id,
    normalize_detail,
)


def test_extract_listing_id_from_integer():
    assert extract_listing_id(7873932069) == 7873932069


def test_extract_listing_id_from_numeric_string():
    assert extract_listing_id("7873932069") == 7873932069


def test_extract_listing_id_from_url():
    url = "https://www.avito.ru/city/category/example_7873932069"
    assert extract_listing_id(url) == 7873932069


def test_extract_listing_id_rejects_invalid_reference():
    with pytest.raises(ListingDetailError, match="Could not extract"):
        extract_listing_id("https://www.avito.ru/profile")


def test_normalize_detail():
    raw = {
        "title": "  Example listing  ",
        "price": "1 200 ₽",
        "description": "  Example   description ",
        "params": ["Condition: used", "  Brand: Example  "],
        "seller_name": " Seller ",
        "expired": True,
        "can_activate": True,
    }

    assert normalize_detail(raw, 1234567890, "https://www.avito.ru/x_1234567890") == {
        "id": 1234567890,
        "url": "https://www.avito.ru/x_1234567890",
        "title": "Example listing",
        "price": "1 200 ₽",
        "description": "Example description",
        "params": ["Condition: used", "Brand: Example"],
        "seller_name": "Seller",
        "state": "inactive",
    }
