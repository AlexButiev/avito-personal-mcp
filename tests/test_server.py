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
