# Proposal: add-local-mcp-server

## Summary

Add an experimental local MCP server so MCP-compatible agents can call selected
AgentOS local capabilities through STDIO.

## Scope

- In scope:
  - `src/agentos/mcp/` package.
  - `agentos mcp serve`.
  - MCP-shaped tool schemas and service adapter.
  - JSON-RPC STDIO handlers for `initialize`, `tools/list`, and `tools/call`.
  - Tools for memory add/search/get, SDD new/status, skills list, and policies
    check.
  - Docs with Codex STDIO config and security notes.
- Out of scope:
  - Network transport.
  - Delete tools.
  - Autonomous shell execution.
  - Formal MCP SDK dependency unless adopted later.

## Risks

- Risk: stdout noise can break MCP STDIO. Startup status is written to stderr
  and JSON-RPC responses to stdout.
- Risk: exposing deletes too early. No delete operations are exposed in this
  first MCP version.
