# ChatGPT and Codex connection status

Last reviewed: 2026-09-05.

## Current decision

Keep `avito-personal-mcp` private and local-first. Neither the Chrome CDP port,
the MCP server, nor the dedicated browser profile is exposed to the LAN or the
Internet. `avito-ai` remains the supported terminal fallback and a useful
sanitized acceptance client.

There are two distinct ways to use the same installed server:

1. **This Mac: Codex, ChatGPT desktop app, or a compatible IDE client.** These
   local clients support stdio MCP servers and share the Codex host's MCP
   configuration. This is the immediate path for natural-language Avito work on
   the Mac, and does not need a tunnel or an Avito developer credential.
2. **ChatGPT on the web: a private developer-mode app over Secure MCP Tunnel.**
   The tunnel client runs inside the same local trust boundary as Chrome and
   opens only an outbound HTTPS connection to OpenAI. It forwards MCP JSON-RPC
   to the private local server; it must never forward CDP `127.0.0.1:9222`.

The second path is private testing and use, not public plugin distribution. A
public plugin would need a separate, stable public HTTPS endpoint and its own
authentication/threat model.

## What is available now

| Needed outcome | Status | Safety boundary |
| --- | --- | --- |
| `avito-ai` and another local stdio MCP client | Supported | Dedicated Chrome profile, CDP on loopback only. |
| Codex or ChatGPT desktop app on this Mac | Supported configuration path | The app must restart after adding the server, then list `avito` in `/mcp`. |
| ChatGPT web through Secure MCP Tunnel | Officially documented architecture; not yet accepted for this account | Requires a Platform tunnel, a runtime API key, target-workspace association, and ChatGPT developer-mode access. |
| Sending a message | Deliberately guarded | The server still requires its two-phase exact-target confirmation; host approvals are defence in depth, not a replacement. |
| Public plugin/directory distribution | Deferred | A tunnel is private-only and must not become a public gateway for the browser session. |

The account currently uses ChatGPT Plus. OpenAI describes developer-mode access
as plan- and workspace-specific; do not infer eligibility from the plan name or
from this document. The only authoritative check is whether the signed-in
ChatGPT account exposes developer mode and whether the matching Platform
organization permits the required tunnel actions. If the web route is not
available, that does not limit the local desktop route or the project's
development.

## Immediate local-desktop setup

Install the package, start the dedicated Chrome session, and add this local
server to the Codex host configuration at `~/.codex/config.toml` (use the real
absolute path for this Mac):

```toml
[mcp_servers.avito]
command = "/absolute/path/to/.venv/bin/avito-personal-mcp"
startup_timeout_sec = 20
tool_timeout_sec = 60
enabled = true
default_tools_approval_mode = "prompt"

# Safe examples: enable routine read tools without a prompt.
[mcp_servers.avito.tools.avito_search]
approval_mode = "auto"

[mcp_servers.avito.tools.avito_favorites]
approval_mode = "auto"
```

Keep the default approval mode for `avito_send_message`. Also keep it for
`avito_chat_messages` unless the user accepts Avito's normal read-state effect:
opening a conversation can mark it read even though the MCP itself does not
send, edit, or delete a message.

Restart the local client after saving the configuration. In the Codex terminal
UI or desktop composer, `/mcp` should show the enabled `avito` server. Begin
acceptance with `avito_selfcheck`, then use a normal language request such as
“find three laptops under 70,000 roubles” or “show my current listings.” Do not
put passwords, cookies, OAuth values, or browser-storage exports in the config.

## Web ChatGPT route when the account UI permits it

This is a runbook, not evidence that the route is enabled for a particular
account:

1. In the personal OpenAI Platform organization associated with the target
   ChatGPT account, create or select an MCP tunnel. The account needs the
   appropriate **Tunnels Read + Manage** permission to create/edit it and
   **Tunnels Read + Use** to operate/select it.
2. Associate that tunnel with both the personal Platform organization and the
   target ChatGPT workspace. A personal organization by itself does not make a
   tunnel appear in another workspace.
3. Download the current `tunnel-client` from the OpenAI tunnel settings. Keep
   its runtime API key in the operating-system secret store or a transient shell
   environment only — never in this repository, an MCP config, a browser
   profile, a screenshot, or a command history.
4. Configure `tunnel-client` on this Mac to launch the absolute installed
   `avito-personal-mcp` command over stdio. Validate with
   `tunnel-client doctor --profile <profile> --explain`, then keep
   `tunnel-client run --profile <profile>` healthy. Its local admin UI is a
   loopback-only diagnostic surface.
5. In ChatGPT on the web, enable developer mode if that setting is available.
   At **Plugins**, create a developer-mode app, select **Tunnel**, and choose
   the associated tunnel (or enter its `tunnel_id`).
6. Start with `avito_selfcheck` and a deliberately small read-only request.
   Tool discovery alone is not acceptance. A successful web acceptance means a
   real ChatGPT web chat receives the result through the active tunnel and the
   installed local MCP server.

Do not expose CDP, change the server into a public listener, or put a browser
session token into the tunnel configuration. If Developer Mode, tunnel creation,
or the expected workspace association is absent, stop at that UI boundary and
record the exact visible limitation; do not attempt a workaround.

## Acceptance and privacy boundary

For desktop, acceptance means the restarted client discovers `avito`, invokes
`avito_selfcheck`, and completes the intended safe read tool through the
installed package. For the web route, it additionally requires the active
`tunnel-client` and a real developer-mode ChatGPT invocation.

Do not place profile data, listing data, chat IDs, private message contents,
runtime keys, or browser-session material in issues, logs, screenshots,
fixtures, or this document. Never send a real message merely to test a
connection.

## Official references

- [MCP in Codex and the ChatGPT desktop app](https://learn.chatgpt.com/docs/extend/mcp)
- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
