# Design: refactor-service-container

## Architecture

Service protocols remain in `src/agentos/services/interfaces.py`. Local
implementations remain in `src/agentos/services/local.py`. The new
`src/agentos/services/container.py` owns dependency resolution for a workspace
root.

The container is lazy: each property creates the local adapter only when used.
That avoids initializing policy files, memory databases, or traces for commands
that do not need those services.

## Interfaces

Service protocols:

- `TechnicalMemoryService`
- `SDDService`
- `SkillRegistryService`
- `PolicyService`
- `TraceService`
- `ProfileService`
- `StrategicBrainService`
- `RefinerService`

Container API:

```python
container = create_service_container(root)
container.memory
container.sdd
container.skills
container.policies
container.traces
container.profiles
container.strategic_brain
container.refiner
```

CLI commands keep their existing names, arguments, and output.

## Safety

All implementations remain local-first. The refactor does not add external
network calls, autonomous command execution, or destructive operations. Strategic
brain and refiner services return TODO stub strings only.
