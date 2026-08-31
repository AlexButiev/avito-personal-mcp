# Changelog

All notable changes to Avito Personal MCP are documented here.

The project follows semantic versioning. Release candidates use the `rc` prerelease suffix.

## [Unreleased]

## [0.1.0rc3] - 2026-09-01

Third public release candidate. It adds the first stable structured-search
slice after live DOM research in a user-controlled browser.

### Added

- Optional `min_price`, `max_price`, and fixed logical `sort` arguments to
  `avito_search` and the `avito-ai search` terminal fallback.
- Price-range and sort validation, CLI mapping coverage, and server forwarding
  coverage for the new search parameters.

### Safety and reliability

- Price and sort are applied only through observed rendered Avito controls,
  supporting both compact and expanded price-filter layouts.
- Search waits for a real visible SERP refresh after a filter or sort action;
  it never manually constructs Avito's undocumented search state or accepts
  arbitrary frontend selectors from MCP clients.
- Location, category-specific filters, and pagination remain deferred rather
  than being guessed from unstable category-dependent controls.

## [0.1.0rc2] - 2026-08-31

Second public release candidate. It promotes the packaged-client and
data-minimization fixes after the first public tag was exercised through a real
MCP client.

### Added

- `avito-ai`, a read-only terminal bridge that calls the same installed MCP
  surface as other MCP clients.
- Installed-package release smoke coverage for both console commands.
- Gate 12 acceptance record with a non-secret, client-level test boundary.

### Changed

- `avito-ai` now forwards only the documented non-secret
  `AVITO_MCP_CDP_URL` override to its local stdio server, so an intentional
  loopback CDP port change behaves exactly like direct server use.
- `avito-ai` launches the installed `avito-personal-mcp` console command from
  its active Python environment instead of importing a repository checkout.
- `avito_selfcheck` now returns aggregate tab state only, not browser tab URLs
  or titles.
- A bare `avito_get_listing` / `avito-ai listing` ID is now explicitly
  documented and reported as an own-listing-only lookup; another public listing
  requires its exact Avito URL, which is never guessed from an ID.
- Added the current ChatGPT Plus availability boundary and a private Secure MCP
  Tunnel runbook for a future eligible workspace; no unsupported Plus setup is
  presented as validated.

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
