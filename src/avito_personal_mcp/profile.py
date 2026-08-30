"""Authenticated Avito profile discovery.

The implementation uses only the user's already authenticated browser session.
It does not read Chrome profile files, cookies, authorization headers, or
storage state directly.
"""

from __future__ import annotations

from typing import Any

from playwright.async_api import Page

PROFILE_LIST_PATH = "/web/1/profiles/list"


class ProfileDiscoveryError(RuntimeError):
    """Raised when Avito profile identity cannot be determined safely."""


def select_current_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the current profile from a sanitized profiles/list payload."""

    result = payload.get("result")
    if not isinstance(result, dict):
        raise ProfileDiscoveryError("Avito profile response has no result object")

    profiles = result.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ProfileDiscoveryError("No Avito profiles were returned")

    valid_profiles = [profile for profile in profiles if isinstance(profile, dict)]
    if not valid_profiles:
        raise ProfileDiscoveryError("Avito returned no valid profile objects")

    current = next(
        (profile for profile in valid_profiles if profile.get("isCurrent") is True),
        None,
    )
    if current is None and len(valid_profiles) == 1:
        current = valid_profiles[0]

    if current is None:
        raise ProfileDiscoveryError("Could not determine the current Avito profile")

    profile_id = current.get("profileId")
    if profile_id is None:
        raise ProfileDiscoveryError("Current Avito profile has no profileId")

    return {
        "profile_id": profile_id,
        "name": current.get("name"),
        "title": current.get("title"),
        "entity": current.get("entity"),
        "status": current.get("status"),
    }


async def discover_current_profile(page: Page) -> dict[str, Any]:
    """Request the profile list inside the authenticated Avito page context."""

    payload = await page.evaluate(
        """
        async (path) => {
            const response = await fetch(path, {
                method: "GET",
                credentials: "include",
                headers: {"Accept": "application/json"},
            });

            if (!response.ok) {
                return {
                    __mcp_error__: true,
                    status: response.status,
                };
            }

            return await response.json();
        }
        """,
        PROFILE_LIST_PATH,
    )

    if not isinstance(payload, dict):
        raise ProfileDiscoveryError("Avito profile endpoint returned an unexpected payload")

    if payload.get("__mcp_error__") is True:
        status = payload.get("status")
        if status in {401, 403}:
            raise ProfileDiscoveryError("Avito session is not authenticated or has expired")
        raise ProfileDiscoveryError(f"Avito profile endpoint returned HTTP {status}")

    return select_current_profile(payload)
