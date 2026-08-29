# Avito Personal MCP

Unofficial MCP server for interacting with Avito through your own authenticated browser session.

> [!IMPORTANT]
> This project is independent and is not affiliated with, endorsed by, or maintained by Avito.

## Goal

Provide a local-first MCP interface for a user's own Avito web session without requiring users to share their Avito password, SMS codes, browser cookies, or other credentials with the MCP client.

The initial implementation is intentionally **read-only**. Write actions will only be considered after the authentication/session layer and read operations are stable, and will require explicit confirmation safeguards.

## Planned MCP tools

### Phase 1 — read-only

- `avito_selfcheck`
- `avito_me`
- `avito_search`
- `avito_get_listing`
- `avito_my_listings`
- `avito_favorites`
- `avito_chats`
- `avito_chat_messages`

### Later — guarded write actions

- `avito_send_message`
- `avito_add_favorite`
- `avito_remove_favorite`
- selected operations for the user's own listings

## Architecture

```text
MCP client
    |
    v
Avito Personal MCP
    |
    +-- session/auth layer
    +-- profile discovery
    +-- search/listings
    +-- favorites
    +-- chats/messages
    +-- rate limiting
    +-- diagnostics
    |
    v
User-controlled Chrome session (CDP)
    |
    v
avito.ru
```

The browser remains under the user's control. Authentication is performed manually by the user in Chrome. The project must not ask users to paste passwords, SMS codes, cookies, or session tokens into configuration files.

## Project status

**Pre-alpha / architecture stage.**

The repository is being initialized. Do not rely on it for production use yet.

## Safety principles

- Local-first authentication/session state.
- No Avito credentials committed to the repository.
- No CAPTCHA bypass or anti-bot circumvention.
- Conservative request rate limiting.
- Detect and surface authentication expiry, CAPTCHA, HTTP 403 and HTTP 429 instead of trying to evade them.
- Read-only by default.
- Explicit confirmation before future state-changing operations.
- Logs must not contain passwords, cookies, authorization headers, session tokens, or message contents unless explicitly required for local debugging and redacted by default.

See [SECURITY.md](SECURITY.md) for the security policy.

## Development roadmap

1. Repository and security foundation.
2. Chrome/CDP session discovery and diagnostics.
3. `avito_selfcheck` and `avito_me`.
4. Public search and listing reads.
5. User listings and favorites.
6. Chats and message reads.
7. Cross-platform packaging and installation documentation.
8. Guarded write actions only after the read-only foundation is stable.

## License

MIT. See [LICENSE](LICENSE).
