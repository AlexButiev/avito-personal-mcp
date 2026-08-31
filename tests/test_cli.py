from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from avito_personal_mcp import cli
from avito_personal_mcp.cli import (
    build_parser,
    command_to_tool,
    installed_server_command,
    render_result,
    server_parameters,
)


def parse(*argv: str) -> argparse.Namespace:
    return build_parser().parse_args(list(argv))


def test_search_maps_to_mcp_tool() -> None:
    args = parse("search", "мини ПК Ryzen 7840HS", "--limit", "20")
    assert command_to_tool(args) == (
        "avito_search",
        {
            "query": "мини ПК Ryzen 7840HS",
            "limit": 20,
            "min_price": None,
            "max_price": None,
            "sort": None,
        },
    )


def test_search_maps_price_and_sort_options_to_mcp_tool() -> None:
    args = parse(
        "search",
        "мини ПК Ryzen 7840HS",
        "--min-price",
        "10000",
        "--max-price",
        "100000",
        "--sort",
        "price_asc",
    )
    assert command_to_tool(args) == (
        "avito_search",
        {
            "query": "мини ПК Ryzen 7840HS",
            "limit": 10,
            "min_price": 10_000,
            "max_price": 100_000,
            "sort": "price_asc",
        },
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


def test_installed_server_command_uses_sibling_console_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scripts_dir = tmp_path / "bin"
    scripts_dir.mkdir()
    python_executable = scripts_dir / "python"
    python_executable.touch()
    server_command = scripts_dir / "avito-personal-mcp"
    server_command.touch()
    monkeypatch.setattr(cli.sys, "executable", str(python_executable))

    assert installed_server_command() == str(server_command)


def test_installed_server_command_fails_when_entry_point_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scripts_dir = tmp_path / "bin"
    scripts_dir.mkdir()
    python_executable = scripts_dir / "python"
    python_executable.touch()
    monkeypatch.setattr(cli.sys, "executable", str(python_executable))

    with pytest.raises(RuntimeError, match="Install avito-personal-mcp"):
        installed_server_command()


def test_server_parameters_forwards_only_documented_cdp_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AVITO_MCP_CDP_URL", "http://127.0.0.1:9333")
    monkeypatch.setenv("UNRELATED_SECRET_LIKE_VALUE", "must-not-be-forwarded")
    monkeypatch.setattr(
        "avito_personal_mcp.cli.installed_server_command",
        lambda: "/tmp/avito-personal-mcp",
    )

    server = server_parameters()

    assert server.command == "/tmp/avito-personal-mcp"
    assert server.env == {"AVITO_MCP_CDP_URL": "http://127.0.0.1:9333"}


def test_server_parameters_does_not_create_environment_without_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AVITO_MCP_CDP_URL", raising=False)
    monkeypatch.setattr(
        "avito_personal_mcp.cli.installed_server_command",
        lambda: "/tmp/avito-personal-mcp",
    )

    assert server_parameters().env is None
