from __future__ import annotations

import json

import pytest

from avito_personal_mcp import server


@pytest.mark.asyncio
async def test_selfcheck_does_not_return_tab_urls_or_titles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_list_open_pages(_: object) -> list[dict[str, str]]:
        return [
            {
                "url": "https://www.avito.ru/city?q=private+search",
                "title": "Private search title",
            },
            {
                "url": "https://example.test/private",
                "title": "Unrelated private tab",
            },
        ]

    monkeypatch.setattr(server, "list_open_pages", fake_list_open_pages)

    result = await server.avito_selfcheck()

    assert result["status"] == "ok"
    assert result["open_pages"] == 2
    assert result["avito_pages"] == 1
    assert "pages" not in result
    rendered = json.dumps(result)
    assert "private" not in rendered
    assert "Private" not in rendered


@pytest.mark.asyncio
async def test_search_forwards_validated_options_and_reports_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSession:
        closed = False

        async def close(self) -> None:
            self.closed = True

    session = FakeSession()
    page = object()

    async def fake_connect_to_chrome(_: object) -> FakeSession:
        return session

    async def fake_search_avito(
        actual_page: object,
        origin: str,
        query: str,
        limit: int,
        min_price: int | None,
        max_price: int | None,
        sort: str | None,
    ) -> list[dict[str, object]]:
        assert actual_page is page
        assert origin == "https://www.avito.ru"
        assert (query, limit, min_price, max_price, sort) == (
            "мини ПК",
            3,
            10_000,
            100_000,
            "price_asc",
        )
        return [{"id": 123}]

    monkeypatch.setattr(server, "connect_to_chrome", fake_connect_to_chrome)
    monkeypatch.setattr(server, "find_avito_page", lambda *_: page)
    monkeypatch.setattr(server, "search_avito", fake_search_avito)

    result = await server.avito_search(
        "мини ПК",
        limit=3,
        min_price=10_000,
        max_price=100_000,
        sort="price_asc",
    )

    assert result == {
        "status": "ok",
        "query": "мини ПК",
        "count": 1,
        "applied": {
            "min_price": 10_000,
            "max_price": 100_000,
            "sort": "price_asc",
        },
        "results": [{"id": 123}],
    }
    assert session.closed is True
