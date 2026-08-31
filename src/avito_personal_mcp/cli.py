"""Small terminal client for Avito Personal MCP.

The CLI intentionally talks to the local MCP server over stdio instead of
calling browser helpers directly. This keeps the terminal bridge on the same
public MCP surface that other clients use.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


async def call_mcp_tool(name: str, arguments: dict[str, object] | None = None) -> Any:
    """Run one MCP tool call through a short-lived local stdio server."""

    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "avito_personal_mcp.server"],
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments=arguments or {})

    if result.is_error:
        text = "\n".join(
            block.text for block in result.content if isinstance(block, TextContent)
        )
        raise RuntimeError(text or f"MCP tool {name!r} returned an error")

    if result.structured_content is not None:
        return result.structured_content

    text_parts = [
        block.text for block in result.content if isinstance(block, TextContent)
    ]
    if len(text_parts) == 1:
        try:
            return json.loads(text_parts[0])
        except json.JSONDecodeError:
            return text_parts[0]

    return {"content": text_parts}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="avito-ai",
        description="Terminal bridge to Avito Personal MCP",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="print compact JSON for easy copy/paste",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("selfcheck", help="check Chrome/CDP connectivity")
    subparsers.add_parser("me", help="show safe profile metadata")
    subparsers.add_parser("my-listings", help="show your Avito listings")
    subparsers.add_parser("favorites", help="show saved Avito listings")
    subparsers.add_parser("chats", help="show visible Avito chats")

    search = subparsers.add_parser("search", help="search Avito")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)

    listing = subparsers.add_parser("listing", help="show one listing by id or URL")
    listing.add_argument("reference")

    messages = subparsers.add_parser("messages", help="show recent messages from one chat")
    messages.add_argument("chat_id")
    messages.add_argument("--limit", type=int, default=50)

    return parser


def command_to_tool(args: argparse.Namespace) -> tuple[str, dict[str, object]]:
    mapping = {
        "selfcheck": ("avito_selfcheck", {}),
        "me": ("avito_me", {}),
        "my-listings": ("avito_my_listings", {}),
        "favorites": ("avito_favorites", {}),
        "chats": ("avito_chats", {}),
        "search": ("avito_search", {"query": args.query, "limit": args.limit}),
        "listing": ("avito_get_listing", {"reference": args.reference}),
        "messages": (
            "avito_chat_messages",
            {"chat_id": args.chat_id, "limit": args.limit},
        ),
    }
    return mapping[args.command]


def render_result(result: Any, *, compact: bool) -> str:
    if isinstance(result, str):
        return result
    if compact:
        return json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(result, ensure_ascii=False, indent=2)


async def async_main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    tool_name, tool_arguments = command_to_tool(args)

    try:
        result = await call_mcp_tool(tool_name, tool_arguments)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "cli_error",
                    "message": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    print(render_result(result, compact=args.compact))
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
