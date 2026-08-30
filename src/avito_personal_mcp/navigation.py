"""Shared navigation and authentication-state helpers.

These helpers intentionally operate on URLs and observed public DOM markers only.
They never inspect cookies, storage state, authorization headers, or credentials.
"""

from __future__ import annotations

from urllib.parse import urlparse

from playwright.async_api import Page

AUTHENTICATED_MARKERS = (
    "header/menu-profile",
    "header/username-button",
    "profile-sidebar",
)


def normalize_origin(origin: str) -> str:
    """Return a canonical ``scheme://host[:port]`` origin."""

    parsed = urlparse(origin.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Origin must be an absolute http(s) URL")
    if parsed.username or parsed.password:
        raise ValueError("Origin must not contain user information")
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def is_same_origin(url: str, origin: str) -> bool:
    """Return whether ``url`` belongs exactly to ``origin`` by scheme and netloc."""

    try:
        expected = urlparse(normalize_origin(origin))
        candidate = urlparse(url.strip())
    except (TypeError, ValueError):
        return False

    if candidate.scheme.lower() != expected.scheme.lower():
        return False
    if candidate.netloc.lower() != expected.netloc.lower():
        return False
    return True


def canonical_same_origin_url(url: str, origin: str) -> str:
    """Return a safe same-origin URL without query/fragment.

    Raises ``ValueError`` for off-origin or malformed URLs.
    """

    if not is_same_origin(url, origin):
        raise ValueError("URL does not belong to the configured Avito origin")

    parsed = urlparse(url.strip())
    return f"{normalize_origin(origin)}{parsed.path or '/'}"


async def has_authenticated_marker(page: Page) -> bool:
    """Check for one of the authenticated DOM markers observed in the user's session."""

    selectors = ", ".join(f'[data-marker="{marker}"]' for marker in AUTHENTICATED_MARKERS)
    return await page.locator(selectors).count() > 0
