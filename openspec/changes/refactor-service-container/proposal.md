# Proposal: refactor-service-container

## Summary

Refactor AgentOS Personal around clean service interfaces and a lazy local
service container. This prepares the CLI for future MCP, Engram, GBrain, Hermes,
and Continual Harness integrations without changing user-facing behavior.

## Scope

- In scope:
  - Add missing `TraceService` and `ProfileService` protocols.
  - Make service protocols runtime-checkable for container tests.
  - Add local trace/profile service adapters.
  - Add a lazy `ServiceContainer`.
  - Refactor CLI command handlers to resolve services through the container.
  - Keep strategic brain and refiner as explicit TODO stubs.
  - Add tests for container initialization and stubs.
  - Add service interface documentation.
- Out of scope:
  - External MCP server implementation.
  - Network calls.
  - Functional GBrain or Continual Harness engines.
  - User-facing CLI output changes.

## Risks

- Risk: accidentally changing CLI output while refactoring dependencies. Mitigate
  with the existing CLI smoke suite.
- Risk: eager service initialization creating unrelated local files. Mitigate
  with lazy container properties.
