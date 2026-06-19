# Local MCP Server

AgentOS Personal includes an experimental local MCP server over STDIO.

```powershell
agentos mcp serve
agentos mcp tools
agentos mcp status
```

The server is local-only by default. It reads JSON-RPC messages from standard
input and writes JSON-RPC responses to standard output. It does not open network
ports and does not execute shell commands.

## Codex MCP Config

Use this local STDIO configuration:

```toml
[mcp_servers.agentos]
command = "agentos"
args = ["mcp", "serve"]
startup_timeout_sec = 20
tool_timeout_sec = 60
```

If the `agentos` shim is not on PATH in the current terminal, use the direct
repository executable path instead:

```toml
[mcp_servers.agentos]
command = "C:\\Users\\aleja\\my-ai\\.venv\\Scripts\\agentos.exe"
args = ["mcp", "serve"]
startup_timeout_sec = 20
tool_timeout_sec = 60
```

## Tools

The current MCP version exposes:

- `memory_add`
- `memory_search`
- `memory_get`
- `brain_search`
- `sdd_new`
- `sdd_status`
- `skills_list`
- `policies_check`
- `models_status`
- `usage_summary`
- `agents_status`

Use `agentos mcp tools` to list the exposed tools from the same schema source
used by the STDIO server.

The following tool categories are intentionally not exposed:

- Memory deletion.
- Backup restore.
- Shell or command execution.
- Arbitrary file read/write.
- Update or uninstall commands.

`brain_search` returns bounded excerpts and document metadata, not whole
arbitrary documents. `models_status` returns provider status and environment
variable names only; it does not return API key values.

## Status

```powershell
agentos mcp status
```

The status command reports that the server is local-only, uses the custom
JSON-RPC STDIO implementation, and has deferred adoption of the official Python
MCP SDK for now.

## v0.3.0 SDK Decision

Formal adoption of the official Python MCP SDK is deferred for v0.3.0. The
current custom JSON-RPC STDIO server remains small, local-only, test-covered, and
allowlisted. Revisit SDK adoption when broader protocol compatibility or SDK tool
registration reduces net complexity without weakening the security boundary.

## Security Notes

- The MCP server is STDIO-only and local-first.
- No autonomous shell execution is available.
- `policies_check` analyzes path or command text but does not execute commands.
- Tool errors are normalized in `tools/call` responses with `isError: true` and
  JSON content. Invalid JSON-RPC shape and unknown JSON-RPC methods still return
  protocol errors.
- Sensitive values are still subject to AgentOS local policy and trace redaction
  behavior.
- Agents connected through MCP can add memories and create SDD changes, so only
  connect trusted local agents.

## Implementation Notes

No Python MCP SDK dependency is currently installed in this project. The official
Model Context Protocol Python SDK (`mcp`) remains deferred because the current
need is local-only STDIO tools and the additional dependency plus async/server
abstraction is not yet justified.

This implementation uses a small JSON-RPC STDIO adapter with MCP-shaped
`initialize`, `tools/list`, and `tools/call` handlers. Startup status is written
to stderr, JSON-RPC responses are written to stdout, and EOF shuts the server
down cleanly.

Future work can replace the STDIO server with a formal SDK-backed server while
keeping `AgentOSMCPAdapter` and the service container as the integration
boundary.

See `docs/mcp-sdk-decision.md` for the SDK decision record and adoption triggers.
