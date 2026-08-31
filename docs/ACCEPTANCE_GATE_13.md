# Gate 13 acceptance record

Last reviewed: 2026-09-01.

## Scope and privacy boundary

This record covers the first useful read-only search slice in `0.1.0rc3`:
plain-text search, optional price bounds, and one of the fixed supported sort
orders. It was exercised through the installed `avito-ai` console client
against the owner-controlled dedicated Chrome session.

The acceptance output was reduced to status, result count, the requested
logical filter values, and the names of fields in each result. It contains no
listing titles, URLs, IDs, prices, locations, profile information, cookies, or
browser-session material. No saved search, favorite, message, listing edit, or
other Avito write was performed.

## Results

| Check | Result | Evidence boundary |
| --- | --- | --- |
| Input validation | Passed | Unit tests reject negative/non-integer price values, inverted bounds, and unsupported sort names. |
| CLI/MCP parameter forwarding | Passed | Unit tests cover `avito-ai search` mapping and `avito_search` forwarding of price bounds and sort. |
| Installed-package smoke | Passed | A non-editable installation reported `0.1.0rc3`; both console entry points launch. |
| Live search with price + sort | Passed | `avito-ai` returned `ok`, the requested bounds and `price_asc` in `applied`, and three normalized result schemas. |
| Avito price layouts | Passed | Live DOM observation confirmed both a compact popup/confirmation layout and an expanded input/Enter layout. The implementation supports both. |
| Sort state reused by Avito | Handled | The rendered menu exposes the active option using `aria-checked`; an already selected requested order is accepted without waiting for a non-existent refresh. |
| Chrome after acceptance | Passed | A following sanitized `avito_selfcheck` returned normal availability and aggregate tab counts. |

## Contract and deferred work

The public MCP contract deliberately accepts only these logical sort names:
`default`, `price_asc`, `price_desc`, `date_desc`, and `discount_desc`. It does
not accept raw DOM selectors, Avito `params[...]` keys, or handcrafted query
URLs. Every supported action uses the visible rendered control and waits for an
observed SERP refresh when a change is needed.

Location, category-dependent parameters, and pagination were visible during
research but are query- and category-specific. They are not part of this
release: exposing them now would require unstable generic parameter passthrough
or guessed internal state. Their narrow follow-up is recorded as Gate 13b in
[ROADMAP.md](ROADMAP.md).
