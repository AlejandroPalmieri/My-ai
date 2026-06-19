# Apply Progress: add-local-mcp-server

## Changes Applied

- Added `src/agentos/mcp/` package.
- Added MCP tool schemas for the requested local capabilities.
- Added `AgentOSMCPAdapter` over the service container.
- Added STDIO JSON-RPC handler and loop.
- Added `agentos mcp serve`.
- Added MCP tests for schema, adapter calls, JSON-RPC, and CLI EOF startup.
- Added `docs/mcp.md` and updated README/architecture/status/roadmap/Windows docs.
- Prompt 6 follow-up deferred formal `mcp` SDK adoption and documented the decision.
- Expanded the current custom MCP allowlist to include `brain_search`, `models_status`,
  `usage_summary`, and `agents_status` while keeping destructive tools blocked.
- Added `agentos mcp tools` and `agentos mcp status`.
- Normalized tool execution failures returned by JSON-RPC `tools/call` as
  `isError: true` content while preserving protocol errors for invalid request shape.
- Added tests for exact registration, selected tool execution, blocked tool names,
  normalized unknown-tool errors, and new MCP CLI commands.
- Hardened JSON-RPC message shape validation so non-object valid JSON returns
  `Invalid Request` instead of terminating the STDIO server.
- Sanitized MCP policy reasons and normalized tool error messages to avoid echoing
  secret-bearing commands, local paths, or internal exception details.
- Added regression tests for non-object JSON-RPC messages, policy reason redaction,
  sanitized tool errors, and all production blocked MCP tool names.

## Open Issues

- None for the requested experimental MCP scope.
