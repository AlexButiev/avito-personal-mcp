# Security Policy

## Scope

Avito Personal MCP is designed to operate against a browser session controlled by the user. Authentication material is sensitive and must remain local.

## Never commit or share

- Avito passwords
- SMS or one-time codes
- browser cookies
- session tokens
- authorization headers
- Chrome profile directories
- exported browser storage state
- private message contents captured for debugging

The repository `.gitignore` excludes common local session artifacts, but contributors are responsible for checking every commit before publishing it.

## Authentication model

Users authenticate manually in a dedicated Chrome session. The MCP server should attach to that user-controlled browser through Chrome DevTools Protocol (CDP) or another explicitly documented local mechanism.

The project must not implement CAPTCHA bypasses, credential harvesting, stealth mechanisms intended to evade platform protections, or automatic handling of SMS/OTP challenges.

## Write operations

The initial release is read-only. Future operations that change state, including sending messages or modifying favorites/listings, must be clearly separated from read operations and protected by explicit confirmation safeguards.

## Logging

Sensitive headers, cookies, tokens and credentials must be redacted. Production/default logs should contain only the minimum diagnostic information needed to identify failures.

## Reporting a vulnerability

Do not publish credentials, cookies, tokens or other sensitive reproduction data in a public GitHub issue. Open an issue containing only non-sensitive information and request a private communication channel if sensitive details are required.
