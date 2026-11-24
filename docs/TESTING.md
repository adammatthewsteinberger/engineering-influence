# Testing

CI (`.github/workflows/ci.yml`) is the source of truth. These are its jobs and how to run each locally.

```bash
uv sync --extra test --extra runtime --extra dev --extra publishing
```

| Gate | Command | What it enforces |
|---|---|---|
| Lint | `uv run ruff check .` | style and common errors, including `examples/` |
| Architecture | `uv run lint-imports` | inward-only layers; services and controllers never touch adapters or transports |
| Security lint | `uv run bandit -q -r src packages` | common insecure patterns |
| Dependencies | `uv run pip-audit` | known vulnerabilities (the two local packages are reported as unauditable; that is expected) |
| Types | `uv run mypy --strict src packages` | strict typing |
| Format | `uv run ruff format --check .` | one formatting, no drift |
| Tests | `uv run pytest --cov --cov-branch --cov-fail-under=100` | all tests and **100% branch coverage**, on Python 3.12, 3.13 and 3.14 |
| Integration | `eval "$(sh tests/integration/stack.sh up)"`, then `uv run pytest -m integration tests/integration` | the migrations on PostgreSQL, the stores under concurrent writers, jobs through RabbitMQ, and a book run that finishes through the stack however its workers die |
| Compose smoke | `sh examples/compose_smoke.sh` | the real stack: credentials refused, a two-stage pipeline completes, a malformed message is dead-lettered, the curl example works |
| Provenance | `vibey-gh check --ci`; on pull requests `vibey-gh provenance-check` and `conventional-check` | file headers, `Made-With:` trailers, Conventional Commit subjects |
| Leak scan | gitleaks plus a path check | no secrets and no private-content paths in history |
| Workflows | `actionlint`, `zizmor` | workflow correctness and security |
| Distribution | built in CI | wheel and sdist install and run; `py.typed` ships |
| Toolchain | `uv run pytest -m toolchain` (the CI `toolchain` job) | real LuaLaTeX, epubcheck and the book build end to end |
| Canary | `.github/workflows/canary.yml` | a daily fresh dependency resolve, to catch an upstream break early |
| Nightly evaluation | `.github/workflows/nightly-eval.yml` | `ei evaluate` against a real model; **paid**, off until `RUN_NIGHTLY_EVAL` is `true`, and never run |

## Test layout

| Directory | Contents |
|---|---|
| `tests/unit` | one module at a time, with in-memory adapters |
| `tests/architecture` | the structural rules: one class per file, interfaces folders, no loose functions |
| `tests/parity` | every interface (API, MCP, CLI, SDK) gives the same result for the same input |
| `tests/integration` | a real PostgreSQL and RabbitMQ, started by `stack.sh`; each test gets its own schema and queues |
| `tests/e2e` | real processes: the CLI, the examples against a live uvicorn server, wheel installation |

## The examples are tests

`tests/e2e/test_examples.py` runs every script in `examples/` as a subprocess. The API,
SDK, curl and observability scripts hit a real uvicorn server on a free port; the MCP client
spawns the real stdio server; the webhook sender talks to the real receiver. The compose smoke test then
runs the curl example against the full stack. If you change an interface, the examples fail first.

## Coverage notes

- The 100% gate includes branches. Code that only runs in a fresh interpreter (missing optional
  extras) is measured through `patch = ["subprocess"]` in `[tool.coverage.run]`; do not remove it.
- The `distribution`, `toolchain`, `integration` and `paid` markers are deselected by default. The default suite
  builds no real PDF or EPUB (the `toolchain` job, below, does) and makes no paid model call.

## Architecture rules

`tests/architecture/` enforces the structure of ADR 0006, and every rule holds everywhere with no
allowance for violations (`test_rules.py` asserts each count is zero, so a new class without an
interface, an import that crosses layers or a file outside the layers fails the build).
`tests/architecture/test_move_map.py` keeps `scripts/refactor/move_map.toml` complete against the
tree, and `scripts/refactor/inventory.py` prints the facts the map is built from.
Alembic scripts in `infrastructure/migrations/` are the one exempt folder (ADR 0006); a test builds
the schema from them and fails if it differs from the SQLModel models.
`tests/architecture/test_enum_protocols.py` checks each enum against its `runtime_checkable`
Protocol, because an enum cannot inherit an ABC, and `tests/architecture/test_sdk_interfaces.py`
holds the SDK package to the same interface rules.
`tests/architecture/test_no_patching.py` keeps tests from patching production code: classes take their
collaborators through their constructors, so a test passes a fake. The only patches left are
standard-library calls at the system boundary (`subprocess.run`, `sys.argv`, `sys.path`,
`zipfile.ZipFile.testzip`) and one class the test defines itself; they are listed there, and a new
patch of anything else fails the build.

## Cassettes and paid tests

A model adapter takes its `httpx.Client` through its constructor (ADR 0007), so a test hands it a
client built on a cassette transport instead of the network. The classes are in
`engineering_influence/infrastructure/cassettes/`.

| Class | What it does |
|---|---|
| `CassetteReplayTransport` | Answers from a cassette, in order. A request must match the next recorded one in method, path (with query) and JSON body, or it raises `CASSETTE_MISMATCH`. That is an `ApplicationError`, not an httpx error, so an adapter cannot take it for a network failure and retry. `finish()` fails if the code stopped asking before the cassette ran out. |
| `CassetteRecordingTransport` | Wraps a real transport. The caller gets the real answer. The cassette gets a masked copy of the method, path, JSON bodies and status, and no headers, because the API key is one. A body that is not JSON stops the recording. |
| `CassetteRedactor` | Replaces each key it is told about, and anything shaped like `sk-` plus sixteen more characters, with `[REDACTED]`. The replay masks the request the same way, so a cassette recorded under one key replays under another and a refusal never prints a key. |
| `JsonCassetteStore` | One JSON file per cassette in `tests/cassettes/`, written the same way every time. It refuses to save, and to load, a cassette that still looks like it holds a secret. |

Matching the body is deliberate. A replay that ignored the request would pass while the prompt
changed underneath it. The cost is that changing a prompt or a request field means re-recording
the cassettes that use it, and recording is the paid step.

Cassettes are made only from synthetic briefs (`CONTRIBUTING.md`). `tests/cassettes/` holds none
yet: recording spends money, so the first one waits for the maintainer's go-ahead. The cassettes
under `tests/fixtures/model_cassettes/` are different: they are hand-written from each API's
documented response shape (each says so in its `note`), and test how an adapter classifies a
reply, not what a real model said.

The `paid` marker is for a test that calls a real provider. It is deselected by default, and
`pytest -m paid` is still refused unless `EI_ALLOW_PAID=1` is set (`tests/paid_gate.py`), so
nobody spends by typing one flag. Without the variable the test errors rather than skips, so a
scheduled run that is missing it goes red. A paid test wraps its live transport in
`CassetteRecordingTransport`, so one paid run also produces the cassette later runs replay.

Two things the machinery does not do. It has not been run against a live provider, because that
spends money. And nothing in the product composes it yet: the runtime will use the replay
transport when a cassette-backed run is added.

## Contract snapshots

The evaluation harness (`ei evaluate`, [EVALUATION.md](EVALUATION.md)) is tested end to end against a scripted writing model that also plays the judge, so no test spends money; whether a real model clears the bar is only known from a paid run.

`tests/contracts/` freezes every public contract (the schemas, the OpenAPI document, the CLI tree, the SDK, the MCP tools, the error codes and the webhook catalogue) against a committed copy in `tests/contracts/snapshots/`. A failing test there means a public contract moved. If it moved on purpose, run `EI_UPDATE_CONTRACTS=1 uv run pytest tests/contracts`, read the diff, and follow [COMPATIBILITY.md](COMPATIBILITY.md). They run in the normal suite and need no extras beyond the dev install.

## The toolchain test

`tests/fixtures/fixture_book/` is a small synthetic non-fiction book at the default 6x9 trim,
`tests/fixtures/fixture_novel/` a small synthetic novel at 5.5x8.5 on cream paper, and
`tests/fixtures/fixture_pocket/` a small 5x8 book with no hardcover (original text and a strict
release contract each; the first two have a KDP hardcover). The novel has scene breaks, em-dash
dialogue and a character who says "Draft", so it exercises the rules that differ by kind. The `toolchain` CI job installs LuaLaTeX, tex4ebook and epubcheck on a pinned
`ubuntu-24.04` runner, builds each with `ei book publish <slug> --strict-release`, and compares each
result with the `expected/snapshot.json` beside its fixture. Beyond the snapshot, a test states what
the novel must show (three scene breaks in the PDF and in the EPUB, the em dashes, and no stray
`Draft` complaint) and what the sizes must produce: the interior's page size, the wrap's width
from the page count and the paper's thickness, and no hardcover files for the pocket book.

- The snapshot is structural, so no PDFs live in git: page count, page size and a hash of each
  page's text for both interiors, the sha256 of every EPUB member (the repacker is deterministic),
  the cover file names, and the publication report's step results.
- It is the no-behaviour-change oracle for refactors: a change that alters any typeset page, any
  EPUB member or any gate result fails it.
- A different TeX Live release can legitimately change the snapshot, which is why the runner image is
  pinned. To accept a deliberate change, run `EI_UPDATE_SNAPSHOT=1 uv run pytest -m toolchain` on
  a machine with the same toolchain (or download the `fixture-snapshot` artifact from the failed CI
  run, which holds one `<name>.json` per book) and commit the new file.
- A machine without the tools skips the test.

`tests/toolchain/test_hostile_book.py` is the second toolchain test. It builds a copy of the
fixture book whose every text field carries a payload that would write a file if any of it reached
TeX unescaped, and checks that no file appears and that the payload prints as text. It also feeds
live TeX straight to LuaLaTeX and to tex4ebook to check that neither runs a shell command, with a
control that shows the file-writing canary does detect live TeX. It needs no snapshot, so it
cannot go stale with the TeX Live release. `tests/unit/publishing/typesetting/test_latex_injection.py`
is its fast counterpart in the default suite: it fills every field with a tripwire and fails if a live
macro reaches the generated TeX. See [THREAT_MODEL.md](THREAT_MODEL.md).

`tests/toolchain/test_build_limits.py` is the third. It makes real `latexmk` and real `tex4ebook` hang with a
document that loops forever, and makes real `lualatex` allocate far more memory than its limit and write far
more disk than its limit. It checks that each build fails at its limit and that no process it started is
left running. A hang test's document writes a marker first, so the test shows the tool reached the loop.
`tests/unit/test_process_runner.py` and `tests/unit/test_process_meter.py` cover the same stops, and the
measurements behind them, with real child processes in the default suite: a grandchild in the group, one
that left it, an interrupt, memory summed over a group, and a directory's size.

`tests/unit/test_prompt_template_lock.py` refuses a prompt edit that has no version bump, because the version is
part of the run journal's key ([PROMPTS.md](PROMPTS.md)).

## Writing tests

- Prefer a fake that implements the interface (or subclasses the class and overrides one method) over a mock or a patch.
- Anything that crosses a process boundary needs a failure and recovery test, not only the happy path.
- Property tests use `hypothesis`: the budget invariant in `test_run_control_models.py`, and a state machine over a run's whole life in `test_run_lifecycle_machine.py`. Keep strategies small, and prove a new one can fail by breaking the code it guards.

## The integration tests

They need a real PostgreSQL and RabbitMQ. `tests/integration/stack.sh` starts both in Docker with
random credentials on random `127.0.0.1` ports and prints the two settings the tests read:

```bash
eval "$(sh tests/integration/stack.sh up)"     # start, then export EI_TEST_DATABASE_URL and EI_TEST_RABBITMQ_URL
uv run pytest -m integration tests/integration
sh tests/integration/stack.sh down             # remove both containers
```

Name the directory: the integration job installs only the `test` and `runtime` extras, and a bare
`pytest -m integration` would still try to import every other test module and fail on the ones that
need the `publishing` extra. `stack.sh env` prints the exports again for a stack that is already running. Without the settings
the tests skip; with `EI_REQUIRE_INTEGRATION=1`, which the `integration` CI job sets, a missing stack
fails them instead, so the job cannot pass with nothing tested. Each test gets its own PostgreSQL
schema (dropped afterwards) and its own queue names, so they can run against one stack.

What they cover that the unit tests cannot: the migrations build exactly what the models describe on
PostgreSQL (a timezone mistake that SQLite hid was found this way), several threads racing to change
one run, record one journal entry or store one artifact, large binary artifacts, jobs through the
broker including dead-lettering and redelivery of a message a dead worker never acknowledged, and a
book run driven through both services while workers die before storing a change, before queueing the
next stage and before acknowledging. A death closes the broker connection with the message
unacknowledged, as a killed process does. The run must finish with every artifact byte-identical, the
spend exactly the journal's total, and nothing in the dead-letter queue.
