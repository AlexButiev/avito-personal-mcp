# Gate 12 acceptance record

Last reviewed: 2026-09-01.

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
| Unauthenticated Avito profile | Safe failure | A separate empty Chrome profile with an Avito tab returned `profile_unavailable`; the authorized profile stayed healthy. |
| ChatGPT direct connection | Not exercised | The owner currently uses ChatGPT Plus. Current OpenAI documentation does not list Plus for custom MCP developer-mode connections; see [CHATGPT_CONNECTION.md](CHATGPT_CONNECTION.md). |

## Listing reference contract

The acceptance exercised both supported resolution paths:

1. a bare numeric ID for an authenticated user's own rendered listing;
2. the exact same-origin URL of another listing, obtained from an observed
   result collection.

The server does not construct Avito paths from numeric IDs. An unknown bare ID
returns an explicit error explaining that an exact URL is required for another
public listing.

## Published-tag acceptance

The privacy-hardened `v0.1.0rc2` was published as a prerelease from the merged
Gate 12 candidate. It was then installed from its immutable tag in a separate
virtual environment and accepted through a generic MCP client. All eight read
tools returned their normal successful status; the listing test covered both
own-ID and exact-URL resolution; selfcheck returned no raw tab metadata; and
the guarded send path stopped at `confirmation_required` without a send.

The same tag was also checked through `avito-ai` for an unavailable CDP endpoint
and for two subsequent normal restarts. It returned `chrome_unreachable` for
the controlled failure and `ok` after each restart, leaving the dedicated
Chrome process alive. Gate 12 is therefore complete and
[#22](https://github.com/AlexButiev/avito-personal-mcp/issues/22) may be closed.

The public `v0.1.0rc1` tag remains immutable and is not treated as the
privacy-hardened accepted artifact.

No new Avito write capability is introduced by Gate 12. In particular, a live
message send remains outside this acceptance and requires immediate approval of
the exact target and text.
