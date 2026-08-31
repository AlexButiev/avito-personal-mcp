# Changelog

All notable changes to Avito Personal MCP are documented here.

The project follows semantic versioning. Release candidates use the `rc` prerelease suffix.

## [Unreleased]

### Added

- `avito-ai`, a read-only terminal bridge that calls the same installed MCP
  surface as other MCP clients.
- Installed-package release smoke coverage for both console commands.

### Changed

- `avito-ai` launches the installed `avito-personal-mcp` console command from
  its active Python environment instead of importing a repository checkout.

## [0.1.0rc1] - 2026-08-31

First public release candidate.

### Added

- Local MCP server over stdio using the MCP Python SDK.
- Connection to a user-controlled dedicated Chrome session over loopback CDP.
- `avito_selfcheck` diagnostics.
- Safe profile discovery with `avito_me`.
- Own-listing discovery with `avito_my_listings`.
- Listing detail retrieval with `avito_get_listing`.
- Public Avito search with `avito_search`.
- Favorites retrieval with `avito_favorites`.
- Conversation discovery with `avito_chats`.
- Conversation message retrieval with `avito_chat_messages`.
- Guarded two-phase message sending with `avito_send_message`.
- Short-lived one-time in-memory confirmation tokens for message sends.
- Process-local browser-operation serialization and conservative pacing.
- GitHub Actions CI for Python 3.11, 3.12, 3.13, and 3.14.
- MIT license and security policy.

### Safety and reliability

- Avito credentials, cookies, authorization headers, session tokens, and browser storage state are not accepted as MCP configuration or persisted by the project.
- Authentication is performed manually by the user in the dedicated Chrome profile.
- CDP is intended to remain bound to `127.0.0.1` only.
- Private-page operations fail closed on authentication loss or unexpected DOM structure.
- Same-origin URL validation prevents navigation to lookalike/off-origin hosts discovered in page content.
- Empty private-page results are accepted only when expected authenticated page structure is present.
- Message sends are never automatically retried after an irreversible send attempt.
- An uncertain browser result after a send attempt is reported as uncertain rather than retried.
- No CAPTCHA bypass, stealth circumvention, or automated OTP handling is implemented.

### Known limitations

- The integration is unofficial and depends on Avito's current web frontend and observed browser behavior.
- Avito frontend changes can require selector updates.
- Opening a conversation can cause Avito itself to mark that conversation as read.
- Live browser/CDP acceptance requires the user's own authenticated session and is intentionally not part of CI.
- `0.1.0rc1` is a prerelease and should be treated as experimental.
