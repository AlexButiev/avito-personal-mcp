"""MCP server entry point."""

from __future__ import annotations

from mcp.server import MCPServer

from avito_personal_mcp import __version__
from avito_personal_mcp.browser import connect_to_chrome, find_avito_page, list_open_pages
from avito_personal_mcp.chats import ChatsDiscoveryError, discover_chats
from avito_personal_mcp.config import Settings
from avito_personal_mcp.favorites import FavoritesDiscoveryError, discover_favorites
from avito_personal_mcp.listing_detail import ListingDetailError, discover_listing_detail
from avito_personal_mcp.listings import ListingsDiscoveryError, discover_own_listings
from avito_personal_mcp.profile import ProfileDiscoveryError, discover_current_profile
from avito_personal_mcp.search import SearchDiscoveryError, search_avito

mcp = MCPServer("Avito Personal MCP")


@mcp.tool()
async def avito_selfcheck() -> dict[str, object]:
    """Check whether the MCP server can reach the user-controlled Chrome session.

    This diagnostic is intentionally non-invasive. It only enumerates open page
    URLs/titles and reports whether an Avito tab is currently visible.
    """

    settings = Settings.from_env()
    try:
        pages = await list_open_pages(settings)
    except Exception as exc:
        return {
            "status": "chrome_unreachable",
            "version": __version__,
            "cdp_url": settings.cdp_url,
            "message": f"Could not connect to Chrome CDP: {type(exc).__name__}",
        }

    avito_pages = [page for page in pages if "avito.ru" in page["url"]]
    return {
        "status": "ok" if avito_pages else "chrome_connected_no_avito_tab",
        "version": __version__,
        "cdp_url": settings.cdp_url,
        "open_pages": len(pages),
        "avito_pages": len(avito_pages),
        "pages": avito_pages,
    }


@mcp.tool()
async def avito_me() -> dict[str, object]:
    """Return non-secret identity metadata for the authenticated Avito profile."""

    settings = Settings.from_env()
    try:
        session = await connect_to_chrome(settings)
    except Exception as exc:
        return {
            "status": "chrome_unreachable",
            "message": f"Could not connect to Chrome CDP: {type(exc).__name__}",
        }

    try:
        page = find_avito_page(session, settings.avito_origin)
        if page is None:
            return {
                "status": "no_avito_tab",
                "message": "No open Avito tab was found in the attached Chrome session.",
            }

        try:
            profile = await discover_current_profile(page)
        except ProfileDiscoveryError as exc:
            return {
                "status": "profile_unavailable",
                "message": str(exc),
            }

        return {
            "status": "ok",
            "profile": profile,
        }
    finally:
        await session.close()


@mcp.tool()
async def avito_my_listings() -> dict[str, object]:
    """Return a read-only list of the authenticated user's own Avito listings."""

    settings = Settings.from_env()
    try:
        session = await connect_to_chrome(settings)
    except Exception as exc:
        return {
            "status": "chrome_unreachable",
            "message": f"Could not connect to Chrome CDP: {type(exc).__name__}",
        }

    try:
        page = find_avito_page(session, settings.avito_origin)
        if page is None:
            return {
                "status": "no_avito_tab",
                "message": "No open Avito tab was found in the attached Chrome session.",
            }

        try:
            listings = await discover_own_listings(page, settings.avito_origin)
        except ListingsDiscoveryError as exc:
            return {
                "status": "listings_unavailable",
                "message": str(exc),
            }

        return {
            "status": "ok",
            "count": len(listings),
            "listings": listings,
        }
    finally:
        await session.close()


@mcp.tool()
async def avito_get_listing(reference: int | str) -> dict[str, object]:
    """Return read-only details for one own Avito listing by id or Avito URL."""

    settings = Settings.from_env()
    try:
        session = await connect_to_chrome(settings)
    except Exception as exc:
        return {
            "status": "chrome_unreachable",
            "message": f"Could not connect to Chrome CDP: {type(exc).__name__}",
        }

    try:
        page = find_avito_page(session, settings.avito_origin)
        if page is None:
            return {
                "status": "no_avito_tab",
                "message": "No open Avito tab was found in the attached Chrome session.",
            }

        try:
            listing = await discover_listing_detail(page, settings.avito_origin, reference)
        except (ListingDetailError, ListingsDiscoveryError) as exc:
            return {
                "status": "listing_unavailable",
                "message": str(exc),
            }

        return {
            "status": "ok",
            "listing": listing,
        }
    finally:
        await session.close()


@mcp.tool()
async def avito_search(query: str, limit: int = 10) -> dict[str, object]:
    """Search Avito read-only through the normal rendered search-results page."""

    settings = Settings.from_env()
    try:
        session = await connect_to_chrome(settings)
    except Exception as exc:
        return {
            "status": "chrome_unreachable",
            "message": f"Could not connect to Chrome CDP: {type(exc).__name__}",
        }

    try:
        page = find_avito_page(session, settings.avito_origin)
        if page is None:
            return {
                "status": "no_avito_tab",
                "message": "No open Avito tab was found in the attached Chrome session.",
            }

        try:
            results = await search_avito(page, settings.avito_origin, query, limit)
        except SearchDiscoveryError as exc:
            return {
                "status": "search_unavailable",
                "message": str(exc),
            }

        return {
            "status": "ok",
            "query": query,
            "count": len(results),
            "results": results,
        }
    finally:
        await session.close()


@mcp.tool()
async def avito_favorites() -> dict[str, object]:
    """Return the authenticated user's saved Avito listings read-only."""

    settings = Settings.from_env()
    try:
        session = await connect_to_chrome(settings)
    except Exception as exc:
        return {
            "status": "chrome_unreachable",
            "message": f"Could not connect to Chrome CDP: {type(exc).__name__}",
        }

    try:
        page = find_avito_page(session, settings.avito_origin)
        if page is None:
            return {
                "status": "no_avito_tab",
                "message": "No open Avito tab was found in the attached Chrome session.",
            }

        try:
            favorites = await discover_favorites(page, settings.avito_origin)
        except FavoritesDiscoveryError as exc:
            return {
                "status": "favorites_unavailable",
                "message": str(exc),
            }

        return {
            "status": "ok",
            "count": len(favorites),
            "favorites": favorites,
        }
    finally:
        await session.close()


@mcp.tool()
async def avito_chats() -> dict[str, object]:
    """Return the authenticated user's visible Avito chat list read-only."""

    settings = Settings.from_env()
    try:
        session = await connect_to_chrome(settings)
    except Exception as exc:
        return {
            "status": "chrome_unreachable",
            "message": f"Could not connect to Chrome CDP: {type(exc).__name__}",
        }

    try:
        page = find_avito_page(session, settings.avito_origin)
        if page is None:
            return {
                "status": "no_avito_tab",
                "message": "No open Avito tab was found in the attached Chrome session.",
            }

        try:
            chats = await discover_chats(page, settings.avito_origin)
        except ChatsDiscoveryError as exc:
            return {
                "status": "chats_unavailable",
                "message": str(exc),
            }

        return {
            "status": "ok",
            "count": len(chats),
            "chats": chats,
        }
    finally:
        await session.close()


def main() -> None:
    """Run the local MCP server over stdio."""

    mcp.run()


if __name__ == "__main__":
    main()
