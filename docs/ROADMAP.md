# Product roadmap and integration decision

This document records the product boundary and the next development order for
Avito Personal MCP. It is deliberately narrower than the full set of things an
Avito business API may expose: this project is for an ordinary person's existing
browser session, not an unattended storefront operator.

Last reviewed: 2026-09-01.

## Product boundary

The supported authentication path is a manually signed-in, dedicated Chrome
profile controlled by the user. The MCP process attaches to Chrome only through
loopback CDP and never receives passwords, OTPs, cookies, or exported browser
storage.

The [official Avito API catalog](https://www.avito.ru/developers/api-catalog)
is useful research for capabilities available to eligible developer accounts,
but it is not a transparent replacement for the personal browser-session path:
it has its own authorization and product-access requirements. An official-API
adapter may be considered later as a separately configured opt-in for eligible
accounts. It must never silently replace the local browser session or require
personal users to give this project developer credentials.

## Chosen interaction model

1. **Immediate target: local Codex and ChatGPT desktop use.** A local stdio
   MCP configuration is necessary but does not automatically expose tools in an
   ordinary ChatGPT chat. Package and install the local plugin, then require a
   fresh-chat tool invocation as the acceptance proof before calling this path
   usable.
2. **Web target: ChatGPT with a private MCP connection.** OpenAI's
   [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
   can forward an existing local stdio MCP server through an outbound-only
   connection without opening the user's CDP port or MCP server to the Internet.
   This means the current local-first architecture should be validated before a
   custom remote server is built.
3. **Reliable fallback: direct stdio clients and `avito-ai`.** The packaged CLI
   stays useful where ChatGPT developer-mode access, a tunnel, or a compatible
   workspace is unavailable. It invokes the same public MCP tools rather than
   importing internal browser helpers.
4. **No public ChatGPT plugin yet.** Public distribution requires a stable
   public HTTPS MCP endpoint and OAuth; a tunnel is intentionally only for
   private connections. Building a public gateway before the personal-session
   permission model is proven would increase the attack surface without helping
   the current user.
5. **Optional UI only after tool acceptance.** ChatGPT can render optional
   [MCP Apps UI resources](https://developers.openai.com/plugins/build/chatgpt-ui)
   for comparison and confirmation flows. Every operation must remain usable as
   a structured tool result, since the UI is not guaranteed in every MCP host.

The OpenAI surface is evolving. In particular, account plan, developer-mode,
and write-action availability must be verified at connection time rather than
treated as a permanent product promise. See OpenAI's
[developer-mode guidance](https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt).
The owner-facing status and a future tunnel runbook are kept in
[CHATGPT_CONNECTION.md](CHATGPT_CONNECTION.md); they deliberately distinguish
account/UI eligibility from project readiness rather than treating a plan name
as a permanent product limit.

## Capability map

| User capability | Current state | Operation class | Priority | Preconditions / limits |
| --- | --- | --- | --- | --- |
| Connection and safe diagnostics | `avito_selfcheck` | Read | Complete foundation | Returns aggregate tab state only, never tab URLs or titles; CDP must stay loopback-only. |
| Current profile | `avito_me` | Read | Complete foundation | Fails closed on unavailable authentication. |
| Search and result cards | `avito_search` | Read | First useful slice complete | Text query, non-negative price bounds, and a fixed observed sort set (`default`, price asc/desc, date, discount) are supported through visible UI controls. Location, category-specific filters, and pagination remain deferred until separately observed and accepted. |
| Listing detail | `avito_get_listing` | Read | Complete foundation | A bare numeric ID is intentionally limited to the user's own listings; another listing requires its exact supplied same-origin URL. The server never constructs a URL from an ID. |
| Own listing overview | `avito_my_listings` | Read | Complete foundation | Listing lifecycle, editing, reactivation, and price changes remain deferred writes. |
| Favorites overview | `avito_favorites` | Read | Complete foundation | Add/remove favorites is valuable but must be a separately guarded write. |
| Chat list and message history | `avito_chats`, `avito_chat_messages` | Read with caveat | Complete foundation | Opening a chat can make it read on Avito; no private messages belong in tests or issue reports. |
| Text message | `avito_send_message` | Irreversible external write | Complete guarded path | Two calls, short-lived one-time token, exact text binding, no automatic retry after click. |
| Saved-search monitoring | Not implemented | Background read / notification | Medium | Requires an explicit local state, deduplication, retention, scheduling, and a user-visible stop control. Prefer Avito-native saved-search notifications where sufficient. |
| Favorite add/remove | Not implemented | Reversible external write | High after filtered search | Must show target listing and requested change, require a fresh confirmation, and verify once without retries. |
| Own-listing price or lifecycle changes | Not implemented | Public/account write | Medium | Implement only after live DOM observation and with per-item preview, confirmation, idempotency/uncertain-result handling, and audit-safe local receipts. |
| Publication, deletion, paid promotion, orders, delivery, or payments | Not implemented | Financial, public, or destructive write | Explicitly deferred | Do not automate until a dedicated threat model, capability-specific confirmation, and live acceptance exist. Purchases and payments are out of the current roadmap. |
| CAPTCHA, OTP, stealth, or bypass mechanisms | Never implement | Unsafe / prohibited | Excluded | The user completes authentication and platform challenges manually. |

## Confirmation and retry policy

Read tools must disclose any unavoidable Avito-side effect, such as a chat being
marked read. Write tools are never inferred from a read request and never batch
multiple unrelated targets.

For every write tool:

1. The first call validates target and payload, then returns a minimized preview
   and an in-memory, short-lived, single-use confirmation token.
2. The confirmation token binds exact operation, target, and payload. A changed
   listing, chat, price, or text requires a new preview.
3. The second call performs at most one UI action. If the browser result is
   ambiguous after the action begins, report `*_uncertain` and do not retry.
4. Financial, publication, destructive, or irreversible actions need an
   operation-specific risk review even if ChatGPT also displays an approval UI.

Host-level approval is useful defence in depth, but it cannot replace server-side
binding and idempotency controls: the server is the final authority on what it
will execute against the user's browser session.

## Development order

### Gate 12 — packaged-client acceptance — complete in `v0.1.0rc2`

The published `v0.1.0rc2` tag was installed in isolation and accepted through a
generic MCP client and the direct CLI fallback, without a repository import.
All current read tools, the guarded send preparation path, CDP-unavailable and
unauthenticated-session failures, and MCP-client restart behavior were checked
without putting private Avito data into project artifacts. See
[ACCEPTANCE_GATE_12.md](ACCEPTANCE_GATE_12.md).

### Gate 13 — useful read-only search — first slice complete in `0.1.0rc3`

The first stable cross-query controls were implemented and accepted against the
rendered Avito UI: text query, optional `min_price` / `max_price`, and a fixed
logical sort set. The implementation supports both observed price layouts: a
compact popup with an explicit confirmation control and an expanded filter pane
that applies on Enter. It waits for an observed SERP refresh and never
constructs internal search URLs. Plain-text search remains the fallback. See
[ACCEPTANCE_GATE_13.md](ACCEPTANCE_GATE_13.md).

### Gate 13b — query-aware search extensions

Research location, category-specific filters, and bounded pagination one at a
time. Each must be exposed as a narrow logical parameter only after its exact
rendered control and successful refresh state are observed in the applicable
query/category. Do not expose generic `params[...]` passthrough values,
ambiguous toggles, or guessed URL fields.

### Gate 14 — favorite a selected result

Add a two-phase, one-listing-at-a-time favorite mutation after Gate 13 returns
reliable result identities. This unlocks the natural flow “compare these, then
save the second one” without widening into publishing or buying.

### Gate 15 — comparison and monitoring

Return model-friendly normalized comparison data first. Add an optional ChatGPT
card/list UI only after the private tunnel workflow has been accepted. Design a
local monitoring service separately from one-shot MCP calls, with explicit
start/status/stop operations, bounded retention, deduplication, and no hidden
always-on process.

### Gate 16 — carefully scoped seller operations

Consider one own-listing operation at a time, beginning with the most valuable
and safely verifiable operation found in live UI research. Publishing, deletion,
promotion, payments, and purchase workflows remain separate proposals rather
than extensions of a generic “edit listing” tool.

## Acceptance requirements for every gate

- Unit tests use sanitized data only; no browser profiles, cookies, messages, or
  authenticated network recordings are committed.
- Ruff and the supported Python test matrix pass.
- At least one installed-package smoke path is exercised when console entry
  points or packaging change.
- Live checks occur only on the user's dedicated browser session and are
  reported without private payloads.
- The release notes, README, and this roadmap match the capabilities actually
  shipped; an untested UI selector is never presented as supported.
