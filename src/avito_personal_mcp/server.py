"""MCP server entry point."""

from __future__ import annotations

from mcp.server import MCPServer

from avito_personal_mcp import __version__
from avito_personal_mcp.browser import list_open_pages
from avito_personal_mcp.config import Settings

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
    """Return the authenticated Avito profile identity.

    Profile discovery is deliberately not guessed from undocumented endpoints.
    It will be implemented after observing the user's real authenticated browser
    session and identifying a stable, minimally privileged source of truth.
    """

    return {
        "status": "not_implemented",
        "message": "Profile discovery is the next implementation gate.",
    }


def main() -> None:
    """Run the local MCP server over stdio."""

    mcp.run()


if __name__ == "__main__":
    main()
