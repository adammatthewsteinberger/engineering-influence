# Architecture

engineering-influence is a modular monolith. Interactions call controllers;
controllers call services; services depend on pure domain types and ports;
repositories and infrastructure adapters point inward.

The first public slice establishes the domain boundary. The planned runtime
adds API, MCP, CLI, webhook, and SDK interactions over the same controllers.
Queue, ledger, gate, runner, blob, clock, and skill ports keep the application
independent of vibey and of any one LLM runner.

See [ADR 0001](adr/0001-vibey-integration-boundary.md) for the vibey boundary.
