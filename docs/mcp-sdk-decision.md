# MCP SDK Decision

## Current MCP Implementation Summary

AgentOS currently uses a small custom local JSON-RPC STDIO MCP implementation:

- `src/agentos/mcp/tools.py` defines the exposed tool schemas.
- `src/agentos/mcp/adapter.py` maps tool calls to local service-container behavior.
- `src/agentos/mcp/server.py` handles `initialize`, `tools/list`, `tools/call`, and `ping` over STDIO.
- `agentos mcp serve` starts the local STDIO server. It does not open network ports.

The implementation exposes only selected local, non-destructive tools:

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

It intentionally does not expose memory deletion, backup restore, shell execution,
arbitrary file read/write, update commands, or uninstall commands.

## Candidate SDK and Dependency

The candidate dependency is the official Model Context Protocol Python SDK:

- Package: `mcp`
- Documentation/library reference: `/modelcontextprotocol/python-sdk`

The SDK provides MCP server abstractions, FastMCP-style tool registration, and
STDIO support.

## Pros

- Better alignment with the official MCP protocol surface.
- Less custom protocol code to maintain as MCP evolves.
- Built-in server abstractions and tool registration patterns.
- Easier future expansion if AgentOS needs richer MCP features.

## Cons

- Adds a new runtime dependency before AgentOS needs the broader SDK surface.
- Introduces async/server abstractions into a currently simple local-only STDIO path.
- Expands the dependency and maintenance surface for a security-sensitive boundary.
- May require larger refactors around the current service-container adapter.

## Security Implications

Deferring SDK adoption keeps the MCP boundary narrow and auditable. The current
server remains STDIO-only, local-only, and expose-by-allowlist. It does not add a
network listener and does not expose destructive or arbitrary execution tools.

If the SDK is adopted later, security review must confirm that the transport is
still local-only by default, tool registration remains allowlisted, errors do not
leak secrets, and no SDK defaults expose additional capabilities.

## Packaging Implications

No MCP SDK dependency is added for this prompt. The Python dependency list in
`pyproject.toml` remains unchanged by the MCP decision.

Adopting the SDK later would add `mcp` to the Python package dependencies and
would require validating editable installs, packaging metadata, and CLI startup
behavior on supported environments.

## Test Implications

The current custom implementation is covered by tests for:

- Exact tool registration.
- Selected tool execution.
- Blocked tools not being exposed.
- JSON-RPC `tools/call` normalized tool errors.
- CLI `agentos mcp tools` and `agentos mcp status` smoke behavior.

If the SDK is adopted later, equivalent tests must continue to assert the same
security boundary and should add SDK-specific initialization and transport tests.

## Recommendation

Recommendation: `defer`.

Formal SDK adoption is deferred because AgentOS currently needs only local STDIO
tools, and the SDK dependency plus async/server abstraction is not yet justified.
The existing custom implementation is small, local-only, testable, and aligned
with the current MVP security model.

Adopt the official SDK later when at least one of these triggers is true:

- AgentOS needs broader MCP protocol features that would be risky to maintain by hand.
- Multiple MCP clients require stricter compatibility than the current minimal server provides.
- The tool surface grows enough that SDK registration and validation reduce net complexity.
- A future transport is explicitly approved and reviewed without weakening local-first defaults.
