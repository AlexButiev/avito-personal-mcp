# Avito Personal MCP

Unofficial MCP server for interacting with Avito through your own authenticated browser session.

> [!IMPORTANT]
> This project is independent and is not affiliated with, endorsed by, or maintained by Avito.

## What it does

Avito Personal MCP exposes a local-first MCP interface over the user's own Avito web session. The user signs in manually in a dedicated Chrome profile; the MCP server attaches to that browser over Chrome DevTools Protocol (CDP).

The project does **not** ask users to provide Avito passwords, SMS/OTP codes, cookies, authorization headers, session tokens, or exported browser storage state.

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

See [CHANGELOG.md](CHANGELOG.md) for release notes.

## License

MIT. See [LICENSE](LICENSE).
