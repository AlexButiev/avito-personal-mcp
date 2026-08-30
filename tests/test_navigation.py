import pytest

from avito_personal_mcp.navigation import (
    PrivatePageStateError,
    canonical_same_origin_url,
    is_same_origin,
    normalize_origin,
    validate_private_page_state,
)


def test_normalize_origin_canonicalizes_scheme_and_host():
    assert normalize_origin("HTTPS://WWW.AVITO.RU/profile") == "https://www.avito.ru"


def test_same_origin_accepts_path_query_and_fragment():
    assert is_same_origin(
        "https://www.avito.ru/profile?x=1#fragment",
        "https://www.avito.ru",
    )


def test_same_origin_rejects_prefix_confusion():
    assert not is_same_origin(
        "https://www.avito.ru.evil.example/profile",
        "https://www.avito.ru",
    )


def test_same_origin_rejects_scheme_mismatch():
    assert not is_same_origin("http://www.avito.ru/profile", "https://www.avito.ru")


def test_canonical_same_origin_url_strips_query_and_fragment():
    assert canonical_same_origin_url(
        "https://www.avito.ru/item_123456?foo=bar#x",
        "https://www.avito.ru",
    ) == "https://www.avito.ru/item_123456"


def test_canonical_same_origin_url_rejects_off_origin():
    with pytest.raises(ValueError, match="configured Avito origin"):
        canonical_same_origin_url(
            "https://www.avito.ru.evil.example/item_123456",
            "https://www.avito.ru",
        )


def test_normalize_origin_rejects_credentials():
    with pytest.raises(ValueError, match="user information"):
        normalize_origin("https://user:pass@www.avito.ru")


def test_private_page_state_accepts_authenticated_empty_collection():
    validate_private_page_state(
        pathname="/profile",
        expected_path_prefix="/profile",
        authenticated=True,
        has_expected_structure=True,
    )


def test_private_page_state_rejects_auth_expiry():
    with pytest.raises(PrivatePageStateError, match="authentication"):
        validate_private_page_state(
            pathname="/profile",
            expected_path_prefix="/profile",
            authenticated=False,
            has_expected_structure=True,
        )


def test_private_page_state_rejects_wrong_path():
    with pytest.raises(PrivatePageStateError, match="expected path"):
        validate_private_page_state(
            pathname="/login",
            expected_path_prefix="/profile",
            authenticated=False,
            has_expected_structure=False,
        )


def test_private_page_state_rejects_dom_mismatch():
    with pytest.raises(PrivatePageStateError, match="structure"):
        validate_private_page_state(
            pathname="/profile",
            expected_path_prefix="/profile",
            authenticated=True,
            has_expected_structure=False,
        )
