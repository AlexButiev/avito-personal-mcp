"""MCP server entry point."""

from __future__ import annotations

from mcp.server import MCPServer

from avito_personal_mcp import __version__
from avito_personal_mcp.browser import connect_to_chrome, find_avito_page, list_open_pages
from avito_personal_mcp.chat_messages import (
    ChatMessagesDiscoveryError,
    discover_chat_messages,
)
from avito_personal_mcp.chats import ChatsDiscoveryError, discover_chats
from avito_personal_mcp.config import Settings
from avito_personal_mcp.favorites import FavoritesDiscoveryError, discover_favorites
from avito_personal_mcp.listing_detail import ListingDetailError, discover_listing_detail
from avito_personal_mcp.listings import ListingsDiscoveryError, discover_own_listings
from avito_personal_mcp.profile import ProfileDiscoveryError, discover_current_profile
from avito_personal_mcp.search import SearchDiscoveryError, search_avito
from avito_personal_mcp.send_message import (
    SendMessageError,
    consume_confirmation,
    create_confirmation,
    sanitized_preview,
    send_confirmed_message,
    validate_chat_id,
    validate_message_text,
)

mcp = MCPServer("Avito Personal MCP")


@mcp.tool()
async def avito_selfcheck() -> dict[str, object]:
    """Check whether the MCP server can reach the user-controlled Chrome session.

    This diagnostic is intentionally non-invasive. It only reports aggregate
    tab counts and whether an Avito tab is currently visible; page URLs and
    titles are not returned to the MCP client.
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
    """Return details for an own listing by ID, or any listing by exact Avito URL.

    A bare numeric ID is resolved only from the authenticated user's rendered
    listings. The tool never manufactures a public Avito URL from an ID.
    """

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


@mcp.tool()
async def avito_chat_messages(chat_id: str, limit: int = 50) -> dict[str, object]:
    """Return recent visible messages from one Avito conversation read-only.

    Avito may mark a conversation as read when its page is opened. This tool does
    not send, edit, delete, react to, or otherwise intentionally mutate messages.
    """

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
            messages = await discover_chat_messages(
                page,
                settings.avito_origin,
                chat_id,
                limit,
            )
        except ChatMessagesDiscoveryError as exc:
            return {
                "status": "chat_messages_unavailable",
                "message": str(exc),
            }

        return {
            "status": "ok",
            "chat_id": chat_id,
            "count": len(messages),
            "messages": messages,
            "read_state_note": (
                "Avito may mark the conversation as read when the conversation page is opened."
            ),
        }
    finally:
        await session.close()


@mcp.tool()
async def avito_send_message(
    chat_id: str,
    text: str,
    confirmation_token: str | None = None,
) -> dict[str, object]:
    """Prepare or explicitly confirm one Avito text-message send.

    The first call must omit ``confirmation_token`` and only creates a short-lived
    confirmation. A second call with the matching one-time token performs exactly
    one UI send attempt. Opening the conversation may cause Avito to mark it read.
    """

    try:
        normalized_chat_id = validate_chat_id(chat_id)
        normalized_text = validate_message_text(text)
    except SendMessageError as exc:
        return {"status": "invalid_request", "message": str(exc)}

    if confirmation_token is None:
        token, ttl = create_confirmation(normalized_chat_id, normalized_text)
        return {
            "status": "confirmation_required",
            "chat_id": normalized_chat_id,
            "preview": sanitized_preview(normalized_text),
            "confirmation_token": token,
            "expires_in_seconds": ttl,
            "message": (
                "No message was sent. Call avito_send_message again with the same chat_id and "
                "text plus this confirmation_token to perform one send attempt."
            ),
        }

    try:
        consume_confirmation(
            confirmation_token,
            normalized_chat_id,
            normalized_text,
        )
    except SendMessageError as exc:
        return {"status": "confirmation_invalid", "message": str(exc)}

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
            return await send_confirmed_message(
                page,
                settings.avito_origin,
                normalized_chat_id,
                normalized_text,
            )
        except SendMessageError as exc:
            return {"status": "send_failed", "message": str(exc)}
    finally:
        await session.close()


def main() -> None:
    """Run the local MCP server over stdio."""

    mcp.run()


if __name__ == "__main__":
    main()
