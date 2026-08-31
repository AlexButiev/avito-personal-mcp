import pytest

from avito_personal_mcp.listing_detail import (
    ListingDetailError,
    extract_listing_id,
    normalize_detail,
    resolve_listing_url,
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


async def test_resolve_listing_url_uses_exact_public_url_without_own_listing_lookup(
    monkeypatch: pytest.MonkeyPatch,
):
    async def unexpected_lookup(*_args, **_kwargs):
        raise AssertionError("An explicit listing URL must not inspect own listings")

    monkeypatch.setattr(
        "avito_personal_mcp.listing_detail.discover_own_listings", unexpected_lookup
    )

    assert await resolve_listing_url(
        None,  # type: ignore[arg-type]
        "https://www.avito.ru",
        "https://www.avito.ru/city/category/exact_listing_1234567890?context=search",
    ) == (1234567890, "https://www.avito.ru/city/category/exact_listing_1234567890")


async def test_resolve_listing_url_resolves_bare_id_only_from_own_listings(
    monkeypatch: pytest.MonkeyPatch,
):
    async def own_listings(*_args, **_kwargs):
        return [{"id": 1234567890, "url": "https://www.avito.ru/own_1234567890"}]

    monkeypatch.setattr("avito_personal_mcp.listing_detail.discover_own_listings", own_listings)

    assert await resolve_listing_url(None, "https://www.avito.ru", 1234567890) == (
        1234567890,
        "https://www.avito.ru/own_1234567890",
    )


async def test_resolve_listing_url_rejects_unknown_bare_id_without_guessing_url(
    monkeypatch: pytest.MonkeyPatch,
):
    async def no_own_listings(*_args, **_kwargs):
        return []

    monkeypatch.setattr(
        "avito_personal_mcp.listing_detail.discover_own_listings", no_own_listings
    )

    with pytest.raises(ListingDetailError, match="URLs are never guessed from IDs"):
        await resolve_listing_url(None, "https://www.avito.ru", "1234567890")
