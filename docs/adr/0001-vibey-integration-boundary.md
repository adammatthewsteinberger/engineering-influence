# ADR 0001: Isolate vibey behind ports

Status: accepted for the alpha architecture

## Context

The pipeline needs durable jobs, leases, gates, recovery, and workflow
orchestration. The target runtime is vibey-engine 0.4 (`>=0.4,<0.5`; 4.5.0, which this ADR was first written
against, was removed from PyPI).

The 4.5.0 source was inspected at release commit `f1cd3fe0`, and the claim below was
re-checked against 0.4.0 on 2026-11-18 (no entry-point group, no handler-registration hook).
The worker
has a `JobDispatcher` that routes string job kinds to handlers, but the handler
mapping is assembled inside `vibey.bootstrap.build_worker` and the package does
not expose a third-party entry point for registering handlers or workflow
definitions. Vibey's skills plugins are context assets, not worker-extension
hooks.

## Decision

Engineering-influence will depend on application-owned ports for queueing,
ledger persistence, workflows, gates, runners, and skills. Vibey integration
will be an infrastructure adapter, never a domain or service dependency.

The first supported queue adapter will use the vibey-compatible PostgreSQL
ledger/outbox and RabbitMQ transport through `aio-pika` when a custom worker
kind cannot be registered with the installed vibey release. A future vibey
release may receive a native adapter without changing the application core.

## Consequences

- Pipeline phases can use domain-specific job kinds without modifying vibey.
- Crash recovery and at-least-once event delivery (consumers must deduplicate) remain explicit contracts of
  the engineering-influence adapters.
- The adapter must preserve lease, retry, dead-letter, and gate semantics and
  must be covered by integration tests against PostgreSQL and RabbitMQ. Those tests do not exist yet; today only `examples/compose_smoke.sh` exercises the real stack (milestone M1 of the 1.0 plan adds them).
- Native vibey worker registration remains an optimization, not an architectural
  prerequisite.
