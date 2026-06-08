# Local MCP Server

AgentOS Personal includes an experimental local MCP server over STDIO.

```powershell
agentos mcp serve
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

The first MCP version exposes:

- `memory_add`
- `memory_search`
- `memory_get`
- `sdd_new`
- `sdd_status`
- `skills_list`
- `policies_check`

Delete operations are intentionally not exposed.

## Security Notes

- The MCP server is STDIO-only and local-first.
- No autonomous shell execution is available.
- `policies_check` analyzes path or command text but does not execute commands.
- Sensitive values are still subject to AgentOS local policy and trace redaction
  behavior.
- Agents connected through MCP can add memories and create SDD changes, so only
  connect trusted local agents.

## Implementation Notes

No Python MCP SDK dependency is currently installed in this project. To avoid
adding network-installed dependencies or overengineering the first version, this
implementation uses a small JSON-RPC STDIO adapter with MCP-shaped
`initialize`, `tools/list`, and `tools/call` handlers.

Future work can replace the STDIO server with a formal SDK-backed server while
keeping `AgentOSMCPAdapter` and the service container as the integration
boundary.
