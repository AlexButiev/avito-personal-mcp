# Security Policy

## Scope

Avito Personal MCP operates against a browser session controlled by the user. Authentication material is sensitive and must remain local.

## Never commit, paste, or publish

- Avito passwords
- SMS/OTP or one-time codes
- browser cookies
- session tokens
- authorization headers
- Chrome profile directories
- exported browser storage state
- private message contents captured for debugging
- unrelated request/response bodies from an authenticated session

The repository `.gitignore` excludes common local session artifacts, but contributors are responsible for checking every commit before publishing it.

## Authentication model

Users authenticate manually in a dedicated Chrome session. The MCP server attaches to that user-controlled browser through Chrome DevTools Protocol (CDP).

CDP must remain bound to loopback (`127.0.0.1`). Do not expose the debugging port to a LAN, public tunnel, Internet-facing interface, or other untrusted network boundary.

Use a dedicated Chrome profile for this project. Do not use that profile for banking, email, work systems, password managers, or other unrelated sensitive accounts.

The project must not implement CAPTCHA bypasses, credential harvesting, stealth mechanisms intended to evade platform protections, or automatic handling of SMS/OTP challenges.

## Browser and DOM behavior

Browser-visible page state and frontend behavior observed in the user's own authenticated session are preferred over guessed private endpoints. Unexpected DOM changes should fail closed rather than silently returning misleading empty results.

Authentication expiry, login redirects, CAPTCHA, HTTP 403, HTTP 429, missing controls, or other platform restrictions must be surfaced as explicit sanitized failures rather than bypassed.

## Write operations

State-changing operations are separated from read operations and require explicit safeguards.

`avito_send_message` uses a two-step confirmation flow:

1. the first call validates the requested chat/message and creates a short-lived one-time confirmation token in process memory only;
2. the second call must supply the same chat id, the same message text, and that token before one UI send attempt is allowed.

Confirmation tokens are not written to disk, browser storage, logs, or Git. A message send is not automatically retried after the irreversible send action because a retry could create a duplicate.

Attachments, edits, deletes, reactions, calls, bulk sends, scheduled sends, and other write operations are out of scope unless separately designed and protected.

## Read-state caveat

Opening a conversation page can cause Avito itself to mark that conversation as read. Read-message tooling does not intentionally mutate message content, but normal page navigation can affect read state.

## Logging and tests

Sensitive headers, cookies, tokens, credentials, browser storage state, and private message bodies must not be logged by default. Unit tests and CI must use sanitized fixtures and must not require a real Avito account or authenticated browser session.

Live CDP acceptance tests are separate from CI and should only be run deliberately against a user-controlled session. Any live write acceptance requires explicit user approval for the target and content before the write occurs.

## Reporting a vulnerability

Do not publish credentials, cookies, tokens, private messages, or other sensitive reproduction data in a public GitHub issue. Open an issue containing only non-sensitive information and request a private communication channel if sensitive details are required.
