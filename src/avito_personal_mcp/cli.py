"""Small terminal client for Avito Personal MCP.

The CLI intentionally talks to the local MCP server over stdio instead of
calling browser helpers directly. This keeps the terminal bridge on the same
public MCP surface that other clients use.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


def installed_server_command() -> str:
    """Return the installed MCP console entry point from this Python environment.

    ``avito-ai`` is an end-user bridge, so it must launch the packaged
    ``avito-personal-mcp`` command rather than importing a repository checkout
    with ``python -m``. Keeping both commands beside the active Python
    executable also avoids accidentally resolving a different installation via
    ``PATH``.
    """

    script_name = "avito-personal-mcp.exe" if os.name == "nt" else "avito-personal-mcp"
    # Do not resolve ``sys.executable``: virtual environments commonly expose
    # ``python`` as a symlink to a system interpreter, while their console
    # scripts live beside the symlink in the virtual environment's scripts dir.
    command = Path(sys.executable).with_name(script_name)
    if not command.is_file():
        raise RuntimeError(
            "Installed avito-personal-mcp console command was not found next to the "
            f"current Python executable: {command}. Install avito-personal-mcp into this "
            "environment before running avito-ai."
        )
    return str(command)


def server_parameters() -> StdioServerParameters:
    """Build the local stdio command without forwarding the user's environment.

    The MCP stdio client intentionally starts a constrained child environment.
    Forward only the one documented, non-secret server setting so ``avito-ai``
    honours an intentional loopback CDP override without passing incidental
    shell credentials or unrelated application configuration to the server.
    """

    cdp_url = os.environ.get("AVITO_MCP_CDP_URL")
    server_env = {"AVITO_MCP_CDP_URL": cdp_url} if cdp_url else None
    return StdioServerParameters(
        command=installed_server_command(),
        env=server_env,
    )


async def call_mcp_tool(name: str, arguments: dict[str, object] | None = None) -> Any:
    """Run one MCP tool call through a short-lived local stdio server."""

    server = server_parameters()

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
    search.add_argument("--min-price", type=int)
    search.add_argument("--max-price", type=int)
    search.add_argument(
        "--sort",
        choices=("default", "price_asc", "price_desc", "date_desc", "discount_desc"),
    )

    listing = subparsers.add_parser(
        "listing",
        help="show your listing by ID, or any listing by exact Avito URL",
    )
    listing.add_argument("reference")

    messages = subparsers.add_parser("messages", help="show recent messages from one chat")
    messages.add_argument("chat_id")
    messages.add_argument("--limit", type=int, default=50)

    return parser


def command_to_tool(args: argparse.Namespace) -> tuple[str, dict[str, object]]:
    """Map only the selected CLI command to one MCP tool invocation.

    Keep this branch-based rather than constructing a mapping containing every
    command. argparse only creates attributes for the selected subcommand, so
    eagerly reading attributes from other subcommands raises AttributeError.
    """

    if args.command == "selfcheck":
        return "avito_selfcheck", {}
    if args.command == "me":
        return "avito_me", {}
    if args.command == "my-listings":
        return "avito_my_listings", {}
    if args.command == "favorites":
        return "avito_favorites", {}
    if args.command == "chats":
        return "avito_chats", {}
    if args.command == "search":
        return "avito_search", {
            "query": args.query,
            "limit": args.limit,
            "min_price": args.min_price,
            "max_price": args.max_price,
            "sort": args.sort,
        }
    if args.command == "listing":
        return "avito_get_listing", {"reference": args.reference}
    if args.command == "messages":
        return "avito_chat_messages", {"chat_id": args.chat_id, "limit": args.limit}

    raise ValueError(f"Unsupported command: {args.command}")


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
