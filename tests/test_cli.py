from __future__ import annotations

import argparse

from avito_personal_mcp.cli import build_parser, command_to_tool, render_result


def parse(*argv: str) -> argparse.Namespace:
    return build_parser().parse_args(list(argv))


def test_search_maps_to_mcp_tool() -> None:
    args = parse("search", "мини ПК Ryzen 7840HS", "--limit", "20")
    assert command_to_tool(args) == (
        "avito_search",
        {"query": "мини ПК Ryzen 7840HS", "limit": 20},
    )


def test_listing_maps_to_mcp_tool() -> None:
    args = parse("listing", "123456789")
    assert command_to_tool(args) == (
        "avito_get_listing",
        {"reference": "123456789"},
    )


def test_messages_maps_to_mcp_tool() -> None:
    args = parse("messages", "chat-123", "--limit", "7")
    assert command_to_tool(args) == (
        "avito_chat_messages",
        {"chat_id": "chat-123", "limit": 7},
    )


def test_argumentless_commands_do_not_read_other_subcommand_attributes() -> None:
    expected = {
        "selfcheck": ("avito_selfcheck", {}),
        "me": ("avito_me", {}),
        "my-listings": ("avito_my_listings", {}),
        "favorites": ("avito_favorites", {}),
        "chats": ("avito_chats", {}),
    }
    for command, mapping in expected.items():
        assert command_to_tool(parse(command)) == mapping


def test_compact_output_is_valid_compact_json() -> None:
    assert render_result({"status": "ok", "count": 2}, compact=True) == (
        '{"status":"ok","count":2}'
    )


def test_pretty_output_preserves_unicode() -> None:
    output = render_result({"query": "мини ПК"}, compact=False)
    assert "мини ПК" in output
    assert "\\u" not in output
