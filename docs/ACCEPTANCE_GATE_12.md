# Gate 12 acceptance record

Last reviewed: 2026-08-31.

## Scope and privacy boundary

This record covers an installed-package, real MCP-client acceptance against the
owner-controlled dedicated Chrome session. It contains no profile values,
listing values, URLs, chat IDs, message bodies, browser-session material, or
confirmation tokens. Live messages were never sent.

`avito_chat_messages` was exercised once with a one-message limit. Avito may
mark a conversation read when its page is opened; this is the documented
Avito-side read-state caveat, not a message-content mutation.

## Results

| Check | Result | Evidence boundary |
| --- | --- | --- |
| Exact historical `v0.1.0rc1` install | Server launches and reports `0.1.0rc1` | Isolated temporary virtual environment, no repository import. |
| `v0.1.0rc1` generic MCP client | All read tools returned their successful normal status; message send preparation returned confirmation-required | The client printed only statuses, counts, and result field names. No confirmation was submitted. |
| Historical diagnostic privacy | Not acceptable for promotion | `avito_selfcheck` in the published tag returned raw page metadata. This is why the old tag is not retagged. |
| Current candidate installed non-editably | All eight read tools successful; exact-URL and own-ID listing routes both exercised | `avito-ai` launched the installed sibling `avito-personal-mcp` console entry point. Results were minimized before reporting. |
| Guarded send first phase | Successful, no send | It returned only `confirmation_required`; the one-shot server process then ended without a second call. |
| CDP unavailable | Safe failure | With an unused loopback CDP port, `avito_selfcheck` returned `chrome_unreachable`. |
| MCP client restart / Chrome lifetime | Successful | Repeated short-lived MCP clients completed; a subsequent selfcheck still found the dedicated Chrome session. |
| ChatGPT direct connection | Not exercised | The owner currently uses ChatGPT Plus. Current OpenAI documentation does not list Plus for custom MCP developer-mode connections; see [CHATGPT_CONNECTION.md](CHATGPT_CONNECTION.md). |

## Listing reference contract

The acceptance exercised both supported resolution paths:

1. a bare numeric ID for an authenticated user's own rendered listing;
2. the exact same-origin URL of another listing, obtained from an observed
   result collection.

The server does not construct Avito paths from numeric IDs. An unknown bare ID
returns an explicit error explaining that an exact URL is required for another
public listing.

## Gate decision

The code candidate is ready for release as `v0.1.0rc2`; the public
`v0.1.0rc1` tag remains immutable and is not treated as the privacy-hardened
accepted artifact. Do not close [#22](https://github.com/AlexButiev/avito-personal-mcp/issues/22)
until `v0.1.0rc2` is tagged, installed in isolation, and the same sanitized
MCP-client smoke suite succeeds against that immutable tag.

No new Avito write capability is introduced by Gate 12. In particular, a live
message send remains outside this acceptance and requires immediate approval of
the exact target and text.
