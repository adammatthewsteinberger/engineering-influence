# Architecture

**BLUF:** It is one program built in layers that only point inward: transports call controllers, controllers call
services, and services depend on plain models and on interfaces. Everything that touches the outside world sits
behind an interface. Tests and an import checker enforce the rules, so they cannot quietly rot. Read this before
changing models, services or infrastructure.

engineering-influence writes complete books autonomously and packages them for Amazon KDP
([purpose and status](BOOKS_AND_KDP.md)); this page describes the machinery that does it
unattended. It is a **modular monolith**. Interactions call controllers; controllers
call services; services depend on pure models, contracts and interfaces; repositories and
infrastructure adapters implement those interfaces and point inward; and only `runtime/`
wires concrete classes together. [ADR 0006](adr/0006-onion-layers-and-interfaces.md) records
the rules. They are enforced by tests and by `import-linter`, not by convention.

## Why the layers point one way

> **Daniel:** I want to swap RabbitMQ for another queue. In my last codebase that meant touching forty files.
>
> **Professor Feynman:** Where does the electricity in this room come from?
>
> **Daniel:** The wall socket. I do not know or care which power station.
>
> **Professor Feynman:** Because the lamp depends on the shape of the socket, not on the station. Here a service
> asks for 'something that can queue a job', an interface. RabbitMQ is one thing plugged into that socket. Write
> another plug and the service never notices.
>
> **Daniel:** And what stops someone importing RabbitMQ straight into a service on a bad day?
>
> **Professor Feynman:** A checker that fails the build. The inner layers are forbidden to import the outer ones,
> and `runtime/` is where the plugging in is done. The picture stops being true in one respect: a socket hides
> nothing important, and an interface can hide a slow or failing dependency. That is why every side effect here
> must also be bounded and recoverable.
>
> **Daniel:** One new adapter, a few lines in `runtime/` where each process is wired, and the services stay as
> they are. Not forty files.

## Layers

```text
runtime/         composition roots (CLI, API, worker, MCP, local book, evaluation), settings loader, entry points
interactions/    REST · MCP · CLI · ACP               transports: parse input, call a controller
controllers/     ProjectController, RunController, PublishingController
repositories/    SQLModel ledger and outbox; book and chapter loaders; release evidence files
infrastructure/  RabbitMQ queue and consumer, LaTeX, EPUB, PDF and image tools, cover painters,
                 webhook delivery, security, observability, vibey adapters, in-memory adapters
services/        StartPipeline, RunPhase, ProcessJob, DispatchOutbox, ReadinessProbe, and the book
                 checks, audits, EPUB and typesetting logic and release steps
interfaces/      what services need from the outside: Ledger, Queue, Runner, Gate, Outbox,
                 WebhookDelivery, Secrets, …
contracts/       wire and config schemas (pydantic): JobMessage, HealthStatus, …
models/          Project, PhaseRun, Gate, Artifact, PipelineStage, GoverningPostulates, and the
                 book, EPUB, cover and QA value types                                   (pure)
errors/          exception classes                                        (innermost, stdlib only)
covers/          the public cover-plugin API (`engineering_influence.covers`): a facade over classes
                 that live in the layers, so a private project's imports survive moves
```

The book toolchain behind `ei book` (optional `publishing` extra) has no layer of its own. Its
checks and audits are in `services/publishing/`, typesetting in `<layer>/typesetting/`, EPUB in
`<layer>/epub/`, covers in `<layer>/covers/`, page QA in `<layer>/qa/` and release evidence in
`<layer>/release/`. The bundled LaTeX classes and fonts are in `infrastructure/publishing/assets/`.

Dependencies only point inward. `services` and `controllers` never import adapters or
transports (contract: "Services and controllers never touch adapters or transports"). Run
`uv run lint-imports` to check. The architecture tests under `tests/architecture` add the rest,
and every one of them holds with no exceptions:

- **One class per file**, no loose production functions, and every file inside the layers.
- **Every class has an interface.** Every folder has an `interfaces/` folder, `x/foo.py` defining
  `Foo` pairs with `x/interfaces/foo_interface.py` defining `FooInterface`, and `Foo` inherits it.
  An interface is an ABC with `__slots__ = ()` that declares methods only. An enum cannot inherit an
  ABC, so it gets a `runtime_checkable` Protocol and a test instead.
- **Purity.** `models/` imports only `errors` and the standard library. Image, PDF, archive, process
  and file libraries never appear in `models`, `contracts` or `services`; an adapter provides them.
- **Injection.** Collaborators arrive through constructors, so a test passes a fake instead of
  patching production code. The only patches left are standard-library calls at the system boundary
  (see [TESTING.md](TESTING.md)).

`scripts/refactor/move_map.toml` records where every class moved from, and a test keeps it complete.

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

- **Interfaces first.** Queue, ledger, gate, runner, outbox and secrets are interfaces. The
  application does not know which LLM runner or queue it runs on.
- **vibey stays behind a boundary.** [ADR 0001](adr/0001-vibey-integration-boundary.md) records
  why: vibey-engine 0.4 does not expose worker extension points, so the worker uses an
  application-owned RabbitMQ consumer and keeps vibey as an adapter.
- **Fail closed.** A missing key, secret or setting stops the process or refuses the request.
- **Bounded, idempotent, observable, recoverable** side effects: every external effect has a
  timeout or budget, a ledger entry and a path back after a crash.
- **Models are pure.** `PhaseRun` is a state machine; nothing in `models/` performs I/O.

## Data

- **Ledger** (`ledgereventrecord`): append-only events (`pipeline.started`, `phase.completed`,
  `gate.awaiting`, `pipeline.completed`) with JSON payloads.
- **Outbox**: webhook intents with attempt counts and `dead_at`. Dispatch isolates failures per event.
- **Queues**: `EI_QUEUE_NAME` (default `engineering-influence.jobs`) and its `.dead` companion.

- **Runs** (`bookrunrecord`), the **run journal** (`journalrecord`) and **artifacts** (`artifactrecord`)
  back resumable book runs. The worker writes them when it advances a `run.advance` job; `ei run create`,
  `POST /v1/runs` and the MCP and SDK `create_run` start one, and `ei run grant`, `deny`, `resume` and `cancel` change it.
  The API and `ei run status` read them (`RunSummaryV1`).

The schema is owned by Alembic. The migrations ship in the wheel
(`infrastructure/migrations/`), `ei db upgrade` applies them to `EI_DATABASE_URL`, and the compose
stack runs it once in a `migrate` service that the API and the worker wait for. The API and the
worker never create tables: they check the revision at start-up and refuse to run on a database that
is not at the latest one, so two processes can no longer race to create the schema. Databases made by
the earlier `create_all()` are adopted in place; the baseline creates only the tables that are missing.

## Trust boundaries

| Boundary | Control |
|---|---|
| Internet → API | API key, per-address and per-key rate limit, input validation, request ids sanitised |
| API/worker → Postgres, RabbitMQ | credentials from the environment, never logged (field-name masking) |
| Platform → webhook receiver | HMAC-SHA256 over timestamp and body, replay window, public-HTTPS-only destinations (SSRF policy) |
| Uploads and paths | `AttachmentUploadInspector`, `ConfinedPathGuard` confinement (building blocks; no upload route yet) |
| MCP and CLI | local processes, unauthenticated by design; never expose them |

## Extension points

To add an integration, write an **interface**, an **adapter**, an ADR when the choice is
architectural, and failure/recovery tests (see [CONTRIBUTING.md](../CONTRIBUTING.md)).
Typical swaps: a model-backed `RunnerInterface` and rubric `GateEvaluatorInterface` in place of the placeholders;
another `QueueInterface`; another `LedgerInterface`.

## Not built yet

An importer entry-point plugin layer, an inbound webhook route, and the methodology stages
P1 to P14 with autonomy modes. [CHANGELOG.md](../CHANGELOG.md) records what has landed.
