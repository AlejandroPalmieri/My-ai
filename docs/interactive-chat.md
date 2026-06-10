# Interactive Chat

Running `agentos` without a subcommand shows the startup banner/dashboard, then
enters an interactive model chat loop.

```powershell
agentos
```

The default active model profile is `local-stub`, so the loop works offline
without API keys.

## Commands

```text
help
version
doctor
exit
quit
/model
/model list
/model set <profile>
/effort low|medium|high|max
/usage
/usage reset --confirm
/agents
/clear
/dashboard
/memory search <query>
```

Any other input is sent as a user message to the active model profile.

## Context And History

Conversation history is kept in memory for the current interactive session
only. It is not persisted to disk.

AgentOS estimates context usage from:

- the interactive system prompt
- session conversation history
- the latest user message
- the latest assistant response

If estimated context usage exceeds 80 percent of the active model window,
AgentOS prints a visible warning. If it exceeds 95 percent, AgentOS drops older
session messages and prints a compaction notice. It does not silently exceed the
context limit.

`agentos init` writes this setting to `.agentos/config.yaml`:

```yaml
chat:
  max_history_messages: 20
```

## Safety

Interactive chat does not automatically include technical memory, strategic
brain documents, traces, local files, or secrets. `/memory search <query>` is an
explicit lookup command and its results are displayed to the user, but they are
not added to the model prompt.

Retrieval-augmented chat is a future feature.

## Traces

Interactive chat writes local trace events:

- `interactive_message_sent`
- `interactive_message_received`
- `context_warning`
- `context_compacted`
