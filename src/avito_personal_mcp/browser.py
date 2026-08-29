"""Chrome connection layer.

This module only attaches to a Chrome instance explicitly started by the user
with remote debugging enabled. It does not launch Chrome, read profile files
directly, or export cookies/session state.
"""

from __future__ import annotations

from dataclasses import dataclass

from playwright.async_api import Browser, Playwright, async_playwright

from .config import Settings


@dataclass(slots=True)
class ChromeSession:
    playwright: Playwright
    browser: Browser

    async def close(self) -> None:
        await self.browser.close()
        await self.playwright.stop()


async def connect_to_chrome(settings: Settings) -> ChromeSession:
    """Attach to the user-controlled Chrome instance over CDP."""

    playwright = await async_playwright().start()
    try:
        browser = await playwright.chromium.connect_over_cdp(settings.cdp_url)
    except Exception:
        await playwright.stop()
        raise
    return ChromeSession(playwright=playwright, browser=browser)


async def list_open_pages(settings: Settings) -> list[dict[str, str]]:
    """Return non-sensitive metadata about currently open browser pages."""

    session = await connect_to_chrome(settings)
    try:
        pages: list[dict[str, str]] = []
        for context in session.browser.contexts:
            for page in context.pages:
                pages.append({"url": page.url, "title": await page.title()})
        return pages
    finally:
        await session.close()
