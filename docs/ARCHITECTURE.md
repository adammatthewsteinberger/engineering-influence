# Architecture

engineering-influence is a **modular monolith**. Interactions call controllers; controllers
call services; services depend on pure domain types and ports; repositories and
infrastructure adapters implement those ports and point inward. The rules are enforced by
tests and by `import-linter`, not by convention.

## Layers

```text
interaction/  REST · MCP · CLI · webhooks     transports: parse input, call a controller
controllers/  ProjectController, PublishingController
services/     StartPipeline, RunPhase, ProcessJob, DispatchOutbox, ReadinessProbe
domain/       Project, PhaseRun, Gate, Artifact, PipelineStage, GoverningPostulates   (pure)
interfaces/   ports: Ledger, Queue, Runner, Gate, Outbox, WebhookDelivery, Secrets, …
repositories/ SQLModel ledger and outbox (Postgres)
infrastructure/ RabbitMQ queue and consumer, in-memory adapters, security, observability, vibey adapters
runtime/      settings loader, API and worker entry points
publishing/   the book toolchain behind `ei book` (optional `publishing` extra)
```

Dependencies only point inward. `services` and `controllers` never import adapters or
transports (contract: "Services and controllers never touch adapters or transports"). Run
`uv run lint-imports` to check; the architecture tests under `tests/architecture` add
one-class-per-file, interfaces-in-`interfaces/` and no-loose-production-functions rules.

## One request, end to end

```text
client ──POST /v1/pipelines──▶ ApiGuard (rate limit by address, verify key, rate limit by key)
                                  │
                       ProjectController.start ─▶ StartPipeline
                                  │   ├─ ledger: append PipelineStarted
                                  │   └─ queue:  enqueue "pipeline.<first stage>" + remaining stages
                                  ▼
RabbitMQ  engineering-influence.jobs ──▶ worker (RabbitMqJobConsumer)
                                  │
                       ProcessJob ─▶ RunPhase ─▶ Runner (produces) ─▶ Gate (accepts?)
                                  │   ├─ accepted: ledger phase.completed, enqueue next stage
                                  │   │            (after the last: pipeline.completed)
                                  │   └─ human or rejecting gate: ledger gate.awaiting, stop
                                  ▼
          malformed or failing job ─▶ rejected without requeue ─▶ engineering-influence.jobs.dead
```

The correlation id travels the whole way: request, queued job, worker log lines and outbound webhooks.

## Design decisions

- **Ports first.** Queue, ledger, gate, runner, outbox, clock and secrets are ports. The
  application does not know which LLM runner or queue it runs on.
- **vibey stays behind a boundary.** [ADR 0001](adr/0001-vibey-integration-boundary.md) records
  why: vibey 4.5.0 does not expose worker extension points, so the worker uses an
  application-owned RabbitMQ consumer and keeps vibey as an adapter.
- **Fail closed.** A missing key, secret or setting stops the process or refuses the request.
- **Bounded, idempotent, observable, recoverable** side effects: every external effect has a
  timeout or budget, a ledger entry and a path back after a crash.
- **The domain is pure.** `PhaseRun` is a state machine; nothing in `domain/` performs I/O.

## Data

- **Ledger** (`ledgereventrecord`): append-only events (`pipeline.started`, `phase.completed`,
  `gate.awaiting`, `pipeline.completed`) with JSON payloads.
- **Outbox**: webhook intents with attempt counts and `dead_at`. Dispatch isolates failures per event.
- **Queues**: `EI_QUEUE_NAME` (default `engineering-influence.jobs`) and its `.dead` companion.

`create_all()` creates tables at start-up; there is no migration tool yet.

## Trust boundaries

| Boundary | Control |
|---|---|
| Internet → API | API key, per-address and per-key rate limit, input validation, request ids sanitised |
| API/worker → Postgres, RabbitMQ | credentials from the environment, never logged (field-name masking) |
| Platform → webhook receiver | HMAC-SHA256 over timestamp and body, replay window, public-HTTPS-only destinations (SSRF policy) |
| Uploads and paths | `AttachmentUploadInspector`, `ConfinedPathGuard` confinement (building blocks; no upload route yet) |
| MCP and CLI | local processes, unauthenticated by design; never expose them |

## Extension points

To add an integration, write a **port**, an **adapter**, an ADR when the choice is
architectural, and failure/recovery tests (see [CONTRIBUTING.md](../CONTRIBUTING.md)).
Typical swaps: a model-backed `RunnerPort` and rubric `GatePort` in place of the placeholders;
another `QueuePort`; another `LedgerPort`.

## Not built yet

An importer entry-point plugin layer, an OpenAPI snapshot and webhook event catalog as
published contracts, the other MCP tools, an inbound webhook route, the methodology stages
P1 to P14 with autonomy modes and budget guards, and integration tests against real
containers. [CHANGELOG.md](../CHANGELOG.md) records what has landed.
