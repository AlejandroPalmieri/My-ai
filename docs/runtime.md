# Runtime

AgentOS runtime v0 is local-first and bounded. Agent records, traces, memory,
Strategic Brain, usage, and tool execution all stay under the local project root.

## Agent Tool Loop

`agentos agents run --tools` enables a bounded tool loop:

1. The agent receives a task.
2. The planner asks the model for a portable JSON tool-call protocol.
3. AgentOS validates each requested tool name and arguments.
4. AgentOS checks policies before execution.
5. AgentOS executes only allowlisted internal tools.
6. Tool results are returned to the planner.
7. The loop stops on final answer or `--max-steps`.

Default max tool calls per run is `5`.

## Provider Compatibility

The protocol is provider-neutral JSON:

```json
{"tool_calls":[{"name":"memory_search","arguments":{"query":"decision"}}],"final_answer":null}
```

Providers with no native tool-calling support can still participate by returning
that JSON shape. `local-stub` simulates deterministic tool calls for tests and
offline verification.

## Hard Boundaries

- No unrestricted shell execution.
- No arbitrary command execution.
- No arbitrary file read/write tools.
- No network browsing tool.
- Unknown tools are blocked.
- Review-risk tools require explicit approval.
