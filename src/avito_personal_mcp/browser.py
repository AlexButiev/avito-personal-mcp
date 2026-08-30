"""Chrome connection layer.

This module only attaches to a Chrome instance explicitly started by the user
with remote debugging enabled. It does not launch Chrome, read profile files
directly, or export cookies/session state.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import monotonic

from playwright.async_api import Browser, Page, Playwright, async_playwright

from .config import Settings
from .navigation import is_same_origin


class BrowserAccessGate:
    """Serialize browser work and apply a small process-local pacing interval."""

    def __init__(self, min_interval_seconds: float = 0.25) -> None:
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must be non-negative")
        self.min_interval_seconds = min_interval_seconds
        self._lock = asyncio.Lock()
        self._last_started_at: float | None = None

    async def acquire(self) -> None:
        """Wait for exclusive browser access and enforce the minimum start interval."""

        await self._lock.acquire()
        try:
            now = monotonic()
            if self._last_started_at is not None:
                delay = self.min_interval_seconds - (now - self._last_started_at)
                if delay > 0:
                    await asyncio.sleep(delay)
            self._last_started_at = monotonic()
        except BaseException:
            self._lock.release()
            raise

    def release(self) -> None:
        """Release exclusive browser access."""

        if not self._lock.locked():
            raise RuntimeError("Browser access gate is not acquired")
        self._lock.release()


_BROWSER_ACCESS = BrowserAccessGate()


@dataclass(slots=True)
class ChromeSession:
    playwright: Playwright
    browser: Browser
    access_gate: BrowserAccessGate | None = field(default=None, repr=False)

    async def close(self) -> None:
        """Disconnect Playwright without intentionally terminating user Chrome."""

        try:
            await self.playwright.stop()
        finally:
            if self.access_gate is not None:
                gate = self.access_gate
                self.access_gate = None
                gate.release()


async def connect_to_chrome(settings: Settings) -> ChromeSession:
    """Attach to the user-controlled Chrome instance over CDP.

    Browser access is process-local, exclusive, and lightly paced so concurrent MCP
    requests cannot navigate the same user-controlled Avito tab over one another.
    """

    await _BROWSER_ACCESS.acquire()
    playwright: Playwright | None = None
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp(settings.cdp_url)
    except BaseException:
        try:
            if playwright is not None:
                await playwright.stop()
        finally:
            _BROWSER_ACCESS.release()
        raise
    return ChromeSession(
        playwright=playwright,
        browser=browser,
        access_gate=_BROWSER_ACCESS,
    )


def find_avito_page(session: ChromeSession, origin: str) -> Page | None:
    """Return the first open page belonging exactly to the configured Avito origin."""

    for context in session.browser.contexts:
        for page in context.pages:
            if is_same_origin(page.url, origin):
                return page
    return None


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
