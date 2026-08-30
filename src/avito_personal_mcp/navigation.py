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


class PrivatePageStateError(RuntimeError):
    """Raised when an authenticated Avito page is unavailable or structurally unexpected."""


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


def validate_private_page_state(
    *,
    pathname: object,
    expected_path_prefix: str,
    authenticated: bool,
    has_expected_structure: bool,
) -> None:
    """Validate a private-page snapshot without reading authentication secrets.

    ``authenticated`` is derived only from previously observed DOM markers such as
    ``header/menu-profile``. ``has_expected_structure`` must be derived from markers
    specific to the target page. A legitimate empty collection is therefore allowed
    only when the surrounding private page structure is still present.
    """

    if not isinstance(pathname, str) or not pathname.startswith(expected_path_prefix):
        raise PrivatePageStateError(
            "Avito private page is unavailable or navigation left the expected path"
        )
    if not authenticated:
        raise PrivatePageStateError(
            "Avito authentication is unavailable or the browser session has expired"
        )
    if not has_expected_structure:
        raise PrivatePageStateError(
            "Avito private page structure did not match the observed DOM"
        )


async def has_authenticated_marker(page: Page) -> bool:
    """Check for one of the authenticated DOM markers observed in the user's session."""

    selectors = ", ".join(f'[data-marker="{marker}"]' for marker in AUTHENTICATED_MARKERS)
    return await page.locator(selectors).count() > 0
