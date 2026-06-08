# Design: add-local-mcp-server

## Architecture

The MCP package is intentionally small:

- `tools.py`: tool schema definitions.
- `adapter.py`: maps MCP tool names to service-container calls.
- `server.py`: local STDIO JSON-RPC loop and method handlers.

No SDK dependency is added in this first version because the project has no MCP
SDK installed and the first scope only needs local STDIO tools.

## Interfaces

CLI:

```powershell
agentos mcp serve
```

Tools:

- `memory_add`
- `memory_search`
- `memory_get`
- `sdd_new`
- `sdd_status`
- `skills_list`
- `policies_check`

JSON-RPC methods:

- `initialize`
- `tools/list`
- `tools/call`
- `ping`

## Safety

The server is local-only over STDIO. It does not open network ports, execute
shell commands, or expose delete operations. Policy checking is exposed as a
tool so connected agents can evaluate sensitive paths and dangerous command text
without executing it.
