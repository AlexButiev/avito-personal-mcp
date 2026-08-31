# ChatGPT connection status

Last reviewed: 2026-08-31.

## Current decision

Keep `avito-personal-mcp` as a private, local stdio server. Do not expose the
Chrome CDP port, the MCP server, or a browser profile to the Internet. When the
right ChatGPT workspace access is available, use OpenAI Secure MCP Tunnel as the
transport: its client runs on the same Mac, opens an outbound HTTPS connection
to OpenAI, and forwards MCP JSON-RPC to the installed local server. It does not
make a public plugin or public endpoint.

`avito-ai` remains the supported local fallback and is also useful for a
sanitized terminal acceptance check while direct ChatGPT connection is
unavailable.

## Availability as of this review

The owner currently uses **ChatGPT Plus**. OpenAI's current developer-mode
guidance expressly documents custom MCP read/fetch access for **Pro** and full
MCP, including modify/write actions, for **Business** and **Enterprise/Edu**.
It does not list Plus for custom MCP developer-mode connections. Therefore this
repository does not claim that ChatGPT Plus can connect to this server, and no
ChatGPT-side configuration was attempted or treated as an acceptance result.

| Needed outcome | Current availability on Plus | Project posture |
| --- | --- | --- |
| Local use through `avito-ai` or another stdio MCP client | Available | Supported and used for acceptance. |
| Direct ChatGPT custom MCP app using read/fetch tools | Not documented for Plus | Keep the server ready; re-check if the account gains Pro or a qualifying workspace. |
| Direct ChatGPT write/modify tools | Not available | Keep server-side confirmation safeguards, but do not depend on ChatGPT UI approval. |
| Public ChatGPT plugin/directory distribution | Not a tunnel use case | Deferred; would require a separate public HTTPS/OAuth architecture and threat model. |

These product limits can change. Re-check the official OpenAI documentation and
the account UI before provisioning a tunnel or changing the advertised support
level.

## Ready-to-run path when access becomes available

This is deliberately a runbook, not proof that it works on Plus:

1. Use a personal OpenAI Platform organization associated with the same account
   and obtain permission to create/use a tunnel. A tunnel requires a
   `tunnel_id`, a runtime API key for `tunnel-client`, and an associated ChatGPT
   workspace.
2. Install `tunnel-client` from OpenAI's current tunnel settings/download path.
   Keep its runtime API key in the operating-system secret mechanism or shell
   environment only; never put it in this repository, MCP configuration, or a
   browser profile.
3. Configure `tunnel-client` on the Mac with the absolute installed command for
   `avito-personal-mcp` as its local stdio command. Do not point it at a source
   checkout and do not publish CDP `127.0.0.1:9222` through the tunnel.
4. Run `tunnel-client doctor --profile <profile> --explain`, then keep
   `tunnel-client run --profile <profile>` healthy. Its loopback-only admin UI
   may be used locally for health diagnostics only.
5. In ChatGPT **on the web**, create a developer-mode app, select **Tunnel** as
   its connection, select the associated tunnel, and scan the tools. Start
   acceptance with `avito_selfcheck`, then the read tools only.

Do not include `avito_send_message` in a ChatGPT acceptance on a plan limited to
read/fetch. If a future eligible workspace enables write tools, the server's
two-phase exact-target confirmation remains mandatory and a live send still
needs immediate owner approval of the exact target and text.

## Acceptance boundary

The connection is successful only when a real ChatGPT web chat invokes
`avito_selfcheck` and the intended read tools through the installed server and
active tunnel. Tool discovery alone is not acceptance. Do not copy profile data,
listing data, chat IDs, or private message contents into issue comments,
screenshots, this document, or test fixtures. `avito_chat_messages` has the
documented Avito-side read-state caveat.

## Official references

- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [Developer mode and MCP apps in ChatGPT](https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt)
