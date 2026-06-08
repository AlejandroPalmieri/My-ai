# Service Interfaces

AgentOS Personal routes local behavior through typed service interfaces under
`src/agentos/services/`. The goal is to keep CLI commands stable while future
MCP, Engram, GBrain, Hermes, and Continual Harness integrations attach behind
the same boundaries.

## Container

`create_service_container(root)` returns a lazy `ServiceContainer` for one
workspace root. Services are created only when accessed.

```text
CLI command
  -> ServiceContainer(root)
      -> TechnicalMemoryService
      -> SDDService
      -> SkillRegistryService
      -> PolicyService
      -> TraceService
      -> ProfileService
      -> StrategicBrainService
      -> RefinerService
```

## Interfaces

- `TechnicalMemoryService`: add, search, list, get, delete, import, and export
  technical memories.
- `SDDService`: create, list, inspect, advance, and archive SDD/OpenSpec
  changes.
- `SkillRegistryService`: scan, list, show, and validate local skills.
- `PolicyService`: check paths and commands, list rules, and explain policy
  behavior.
- `TraceService`: start, complete, fail, list, read, tail, and export local
  JSONL trace events.
- `ProfileService`: create, load, set active, validate, and resolve the default
  memory project from the active profile.
- `StrategicBrainService`: local document ingest/search/list/show behavior plus
  a TODO synthesis stub for future GBrain retrieval and synthesis.
- `RefinerService`: stub for future Continual Harness trace analysis.

## Local-First Adapters

Local implementations live in `src/agentos/services/local.py`. They call the
existing SQLite memory store, SDD generator, skill scanner, policy checker,
trace logger, and profile loader. They do not perform network calls.

The strategic brain service is functional for local `.md` and `.txt` indexing,
but synthesis remains a TODO stub. The refiner service intentionally returns a
TODO stub message.

## Migration Notes

New CLI commands should resolve dependencies through `create_service_container`
instead of instantiating local adapters directly. New non-CLI integrations should
depend on protocols from `services/interfaces.py`, not concrete local classes.

Future MCP adapters can wrap the same service interfaces without changing the
CLI command handlers. Future Engram, GBrain, Hermes, and Continual Harness
implementations should replace or decorate the local services behind the
container while preserving method signatures.
