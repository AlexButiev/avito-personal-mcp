# Avito Personal MCP

Unofficial, local-first MCP server for **personal Avito accounts**. It lets an MCP-capable AI client work with your own Avito account through a dedicated browser session — **without requiring Avito Developer API credentials**.

> [!IMPORTANT]
> This project is independent and is not affiliated with, endorsed by, or maintained by Avito.

## Why this project exists

Many Avito integrations are built around official developer/business APIs or public listing parsing. Avito Personal MCP is aimed at a different use case: an ordinary user who wants an AI assistant to work with the Avito account they already use in the browser.

The user signs in to Avito manually in a dedicated Chrome profile. The MCP server then attaches to that already authenticated browser over Chrome DevTools Protocol (CDP).

**No Avito Developer `Client ID` or `Client Secret` is required.** The project also does **not** ask users to provide Avito passwords, SMS/OTP codes, cookies, authorization headers, session tokens, or exported browser storage state.

This makes the project suitable for personal-account workflows such as:

- searching Avito and inspecting individual listings;
- reviewing your own listings;
- reviewing your favorites;
- reading your Avito conversations and message history;
- preparing and explicitly confirming a message before it is sent.

It is not intended to bypass Avito authentication, CAPTCHA, anti-bot controls, account restrictions, or access controls.

## What it does

Avito Personal MCP exposes a local-first MCP interface over the user's own Avito web session. Authentication remains in the dedicated browser controlled by the user rather than being copied into MCP configuration.

## Current MCP tools

Read-only tools:

- `avito_selfcheck`
- `avito_me`
- `avito_search`
- `avito_get_listing`
- `avito_my_listings`
- `avito_favorites`
- `avito_chats`
- `avito_chat_messages`

Guarded write tools:

- `avito_send_message`

`avito_send_message` is deliberately two-step. The first call only returns a sanitized preview and a short-lived one-time confirmation token. A second call with the same chat id, the same message text, and that token performs one send attempt. The MCP does not automatically retry a send because a retry could create a duplicate message.

## Requirements

- Python 3.11, 3.12, 3.13, or 3.14
- Google Chrome or another compatible Chromium browser with CDP support
- a dedicated browser profile for this project
- manual Avito authentication by the user

## Installation

Clone the repository and install the package into a virtual environment:

```bash
git clone https://github.com/AlexButiev/avito-personal-mcp.git
cd avito-personal-mcp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

Run the MCP server over stdio:

```bash
avito-personal-mcp
```

The console entry point is installed by the package and does not require a repository-local `PYTHONPATH`.

## Dedicated Chrome session

Use a separate Chrome profile. Do not reuse a normal browser profile that also contains banking, email, work, or other sensitive accounts.

On macOS:

```bash
open -na "Google Chrome" --args \
  --user-data-dir="$HOME/.avito-personal-mcp/chrome-profile" \
  --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port=9222 \
  "https://www.avito.ru"
```

Then sign in to Avito manually inside that Chrome window. Do not put Avito credentials, cookies, tokens, or browser storage in MCP client configuration.

### CDP security

Keep CDP bound to loopback only (`127.0.0.1`). Do not expose port `9222` to the LAN, Internet, a public tunnel, or an untrusted container/network namespace. A process that can reach the CDP endpoint can potentially control the attached browser session.

## MCP client configuration

The server uses stdio. A generic MCP client configuration looks like this:

```json
{
  "mcpServers": {
    "avito": {
      "command": "/absolute/path/to/.venv/bin/avito-personal-mcp"
    }
  }
}
```

Use the actual absolute path to the installed console script on your machine. No Avito credentials or session material belong in this configuration.

Chrome and the MCP server are separate processes: start the dedicated Chrome session first, sign in manually if needed, then let the MCP client launch `avito-personal-mcp`.

## Terminal fallback: `avito-ai`

`avito-ai` is a small terminal client for the same local MCP surface. It is useful
when the AI client cannot yet attach to the MCP server directly, or when you want
to copy a compact, structured result into a chat.

```bash
avito-ai selfcheck
avito-ai --compact search "мини ПК для HomeLab" --limit 10
avito-ai listing 1234567890
avito-ai messages CHAT_ID --limit 20
```

The command launches the installed `avito-personal-mcp` console entry point from
the same Python environment, not a repository checkout or a private browser
helper. It therefore exercises the packaged MCP path while keeping Chrome, CDP,
and all Avito authentication material outside the CLI configuration. The bridge
currently exposes read-only commands only; guarded message sends remain available
only through the explicit two-phase MCP tool.

## Architecture

```text
MCP client
    |
    v
Avito Personal MCP
    |
    +-- browser/session layer
    +-- profile discovery
    +-- search/listings
    +-- favorites
    +-- chats/messages
    +-- guarded confirmations for writes
    +-- diagnostics
    |
    v
Dedicated user-controlled Chrome session (CDP on loopback)
    |
    v
avito.ru
```

The implementation prefers browser-visible page state and frontend behavior observed in the user's own authenticated session. It does not guess private endpoints and does not attempt to bypass CAPTCHA or anti-bot controls.

## Behavioral caveats

Opening an Avito conversation can cause Avito itself to mark that conversation as read. `avito_chat_messages` does not intentionally send, edit, delete, react to, or otherwise mutate messages, but normal page navigation can still affect read state.

Browser-driven operations are inherently coupled to Avito's current DOM. The project therefore treats unexpected DOM changes as errors rather than silently pretending an empty result is valid.

## Safety principles

- Local-first authentication/session state.
- No Avito Developer API credentials required for the current browser-session workflow.
- No Avito credentials committed to the repository.
- No CAPTCHA bypass, stealth circumvention, or automated OTP handling.
- CDP stays on loopback only.
- Dedicated Chrome profile only; do not use it for unrelated sensitive accounts.
- Read operations are separated from write operations.
- Write operations require explicit confirmation safeguards.
- Message sends are never automatically retried after an irreversible click.
- Logs/tests must not contain passwords, cookies, authorization headers, session tokens, browser storage state, or real private-message fixtures.

See [SECURITY.md](SECURITY.md) for the security policy.

## Troubleshooting

### `chrome_unreachable`

Confirm the dedicated Chrome instance is running with `--remote-debugging-address=127.0.0.1 --remote-debugging-port=9222` and that no firewall/container boundary prevents the local MCP process from reaching it.

### `no_avito_tab`

Open `https://www.avito.ru` in the dedicated Chrome window.

### Authentication unavailable / login redirect

Sign in manually in the dedicated Chrome window. Do not paste credentials, cookies, or tokens into MCP configuration.

### DOM mismatch / unavailable data

Avito may have changed its frontend. Fail closed and update selectors only after observing the new browser behavior. Do not guess internal APIs or weaken authentication checks.

## Development

Install development dependencies:

```bash
python -m pip install -e '.[dev]'
```

Run local checks:

```bash
pytest
ruff check .
```

GitHub Actions runs sanitized unit tests and Ruff on Python 3.11, 3.12, 3.13, and 3.14 without Avito credentials or a real browser session. Live CDP acceptance is intentionally separate from CI.

## Project status

`0.1.0rc1` is the first public release candidate. The read-only foundation and guarded message-send path are implemented, but browser-driven integrations can break when Avito changes its frontend. Treat the release candidate as experimental until the final release is promoted.

See [CHANGELOG.md](CHANGELOG.md) for release notes and
[docs/ROADMAP.md](docs/ROADMAP.md) for the capability boundary, safety model,
and planned development order.

## License

MIT. See [LICENSE](LICENSE).
