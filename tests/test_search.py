import pytest

from avito_personal_mcp import search
from avito_personal_mcp.search import (
    FILTERS_BUTTON_SELECTOR,
    PRICE_FROM_SELECTOR,
    PRICE_TO_SELECTOR,
    SEARCH_INPUT_SELECTOR,
    SEARCH_SUBMIT_SELECTOR,
    SERP_SELECTOR,
    TITLE_SELECTOR,
    SearchDiscoveryError,
    _submit_search_form,
    _validate_observed_result_options,
    normalize_search_result,
    validate_search_options,
)


def test_validate_search_options_returns_only_supported_values() -> None:
    assert validate_search_options(10_000, 100_000, "price_asc") == {
        "min_price": 10_000,
        "max_price": 100_000,
        "sort": "price_asc",
    }


@pytest.mark.parametrize(
    ("min_price", "max_price", "sort", "message"),
    [
        (-1, None, None, "min_price must be a non-negative integer"),
        (None, -1, None, "max_price must be a non-negative integer"),
        (True, None, None, "min_price must be a non-negative integer"),
        (100, 99, None, "min_price must not be greater than max_price"),
        (None, None, "newest_first", "sort must be one of"),
    ],
)
def test_validate_search_options_rejects_invalid_values(
    min_price: int | None,
    max_price: int | None,
    sort: str | None,
    message: str,
) -> None:
    with pytest.raises(SearchDiscoveryError, match=message):
        validate_search_options(min_price, max_price, sort)


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
            "href": "/syktyvkar/noutbuki/noutbuk_8361138738?context=sanitized",
            "title": "Ноутбук",
            "price": "10 000 ₽",
            "location": "Сыктывкар",
            "date": None,
            "seller": None,
        },
        "https://www.avito.ru",
    )

    assert result["id"] == 8361138738
    assert result["url"] == "https://www.avito.ru/syktyvkar/noutbuki/noutbuk_8361138738"


def test_normalize_search_result_accepts_absolute_same_origin_url() -> None:
    result = normalize_search_result(
        {
            "id": "1234567890",
            "href": "https://www.avito.ru/item_1234567890?context=sanitized",
            "title": "Item",
        },
        "https://www.avito.ru",
    )

    assert result["url"] == "https://www.avito.ru/item_1234567890"


def test_observed_result_options_reject_cards_outside_price_bounds() -> None:
    with pytest.raises(SearchDiscoveryError, match="below the requested minimum"):
        _validate_observed_result_options(
            [{"price": "14 999 ₽"}],
            {"min_price": 15_000, "max_price": 35_000, "sort": "price_asc"},
        )


def test_observed_result_options_reject_nonascending_price_order() -> None:
    with pytest.raises(SearchDiscoveryError, match="not ordered by ascending"):
        _validate_observed_result_options(
            [{"price": "20 000 ₽"}, {"price": "19 900 ₽"}],
            {"min_price": None, "max_price": None, "sort": "price_asc"},
        )


@pytest.mark.parametrize(
    "href",
    [
        "https://www.avito.ru.evil.example/item_1234567890",
        "//evil.example/item_1234567890",
    ],
)
def test_normalize_search_result_rejects_off_origin_url(href: str) -> None:
    with pytest.raises(SearchDiscoveryError, match="outside the configured Avito origin"):
        normalize_search_result(
            {
                "id": "1234567890",
                "href": href,
                "title": "Item",
            },
            "https://www.avito.ru",
        )


@pytest.mark.asyncio
async def test_submit_search_waits_for_readiness_before_one_visible_click() -> None:
    """The observed client-side action is ready after the settle interval."""

    class FakeResponse:
        status = 200

    class FakeLocator:
        def __init__(self, page: "FakePage", selector: str) -> None:
            self.page = page
            self.selector = selector

        @property
        def first(self) -> "FakeLocator":
            return self

        async def count(self) -> int:
            if self.selector in {SERP_SELECTOR, TITLE_SELECTOR}:
                return int(self.page.submit_clicks == 1)
            return 1

        async def fill(self, value: str) -> None:
            assert self.selector == SEARCH_INPUT_SELECTOR
            self.page.filled_query = value

        async def click(self) -> None:
            assert self.selector == SEARCH_SUBMIT_SELECTOR
            assert self.page.settling_waits == [1_500]
            self.page.submit_clicks += 1
            self.page.url = "https://www.avito.ru/syktyvkar/noutbuki"

    class FakePage:
        def __init__(self) -> None:
            self.url = "https://www.avito.ru"
            self.filled_query: str | None = None
            self.submit_clicks = 0
            self.settling_waits: list[int] = []

        async def goto(self, url: str, **_: object) -> FakeResponse:
            self.url = url
            return FakeResponse()

        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator(self, selector)

        async def wait_for_url(self, predicate: object, **_: object) -> None:
            assert callable(predicate)
            assert predicate(self.url)

        async def wait_for_timeout(self, timeout: int) -> None:
            self.settling_waits.append(timeout)

    page = FakePage()

    await _submit_search_form(page, "https://www.avito.ru", "ноутбук")

    assert page.filled_query == "ноутбук"
    assert page.submit_clicks == 1
    assert page.settling_waits == [1_500]
    assert page.url == "https://www.avito.ru/syktyvkar/noutbuki"


@pytest.mark.asyncio
async def test_price_filter_updates_upper_bound_before_lower_and_commits_lower(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve both bounds in Avito's reactive expanded price widget."""

    class FakeLocator:
        def __init__(self, page: "FakePage", selector: str) -> None:
            self.page = page
            self.selector = selector

        @property
        def first(self) -> "FakeLocator":
            return self

        async def count(self) -> int:
            return 1

        async def is_visible(self) -> bool:
            return self.selector != FILTERS_BUTTON_SELECTOR

        async def fill(self, value: str) -> None:
            self.page.fills.append((self.selector, value))
            self.page.values[self.selector] = value

        async def press(self, key: str) -> None:
            self.page.presses.append((self.selector, key))

        async def input_value(self) -> str:
            return self.page.values[self.selector]

    class FakePage:
        url = "https://www.avito.ru/syktyvkar/noutbuki"

        def __init__(self) -> None:
            self.fills: list[tuple[str, str]] = []
            self.presses: list[tuple[str, str]] = []
            self.values = {PRICE_FROM_SELECTOR: "", PRICE_TO_SELECTOR: ""}
            self.waits: list[int] = []

        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator(self, selector)

        async def wait_for_timeout(self, timeout: int) -> None:
            self.waits.append(timeout)

    page = FakePage()
    refreshes: list[tuple[str, str]] = []

    async def fake_wait_for_serp_refresh(
        _: FakePage,
        before_url: str,
        operation: str,
    ) -> None:
        refreshes.append((before_url, operation))

    monkeypatch.setattr(search, "_wait_for_serp_refresh", fake_wait_for_serp_refresh)

    await search._apply_price_filter(page, 15_000, 35_000)

    assert page.fills == [
        (PRICE_TO_SELECTOR, "35000"),
        (PRICE_FROM_SELECTOR, "15000"),
    ]
    assert page.presses == [(PRICE_FROM_SELECTOR, "Enter")]
    assert page.waits == [1_500]
    assert refreshes == [(page.url, "price filter")]
