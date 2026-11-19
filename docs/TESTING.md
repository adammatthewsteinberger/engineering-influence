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
| Tests | `uv run pytest --cov --cov-branch --cov-fail-under=100` | all tests and **100% branch coverage** |
| Compose smoke | `sh examples/compose_smoke.sh` | the real stack: credentials refused, a two-stage pipeline completes, a malformed message is dead-lettered, the curl example works |
| Provenance | `vibey-gh check --ci`; on pull requests `vibey-gh provenance-check` and `conventional-check` | file headers, `Made-With:` trailers, Conventional Commit subjects |
| Leak scan | gitleaks plus a path check | no secrets and no private-content paths in history |
| Workflows | `actionlint`, `zizmor` | workflow correctness and security |
| Distribution | built in CI | wheel and sdist install and run; `py.typed` ships |

## Test layout

| Directory | Contents |
|---|---|
| `tests/unit` | one module at a time, with in-memory adapters |
| `tests/architecture` | the structural rules: one class per file, interfaces folders, no loose functions |
| `tests/parity` | every interface (API, MCP, CLI, SDK) gives the same result for the same input |
| `tests/e2e` | real processes: the CLI, the examples against a live uvicorn server, wheel installation |

## The examples are tests

`tests/e2e/test_examples.py` runs every script in `examples/` as a subprocess. The API,
SDK, curl and observability scripts hit a real uvicorn server on a free port; the MCP client
spawns the real stdio server; the webhook sender talks to the real receiver. The compose smoke test then
runs the curl example against the full stack. If you change an interface, the examples fail first.

## Coverage notes

- The 100% gate includes branches. Code that only runs in a fresh interpreter (missing optional
  extras) is measured through `patch = ["subprocess"]` in `[tool.coverage.run]`; do not remove it.
- The `distribution` and `toolchain` markers are deselected by default. The default suite builds no
  real PDF or EPUB; the `toolchain` job (below) does.

## Architecture ratchets

`tests/architecture/` enforces the structure of ADR 0006. Rules the tree already satisfies are strict.
Rules it does not satisfy yet (every class has an interface, every folder an `interfaces/` folder,
`publishing/` split across the layers, and so on) are ratchets: `tests/architecture/ratchet.json`
holds each one's violation count, a count may only go down, and a change that lowers one must record
the new number (`EI_UPDATE_RATCHET=1 uv run pytest tests/architecture/test_ratchets.py` does it).
`tests/architecture/test_move_map.py` keeps `scripts/refactor/move_map.toml` complete against the
tree, and `scripts/refactor/inventory.py` prints the facts the map is built from.

## The toolchain test

`tests/fixtures/fixture_book/` is a small synthetic book (original text, a strict release contract,
a KDP hardcover). The `toolchain` CI job installs LuaLaTeX, tex4ebook and epubcheck on a pinned
`ubuntu-24.04` runner, builds it with `ei book publish fixture --strict-release`, and compares the
result with `tests/fixtures/fixture_book/expected/snapshot.json`.

- The snapshot is structural, so no PDFs live in git: page count, page size and a hash of each
  page's text for both interiors, the sha256 of every EPUB member (the repacker is deterministic),
  the cover file names, and the publication report's step results.
- It is the no-behaviour-change oracle for refactors: a change that alters any typeset page, any
  EPUB member or any gate result fails it.
- A different TeX Live release can legitimately change the snapshot, which is why the runner image is
  pinned. To accept a deliberate change, run `EI_UPDATE_SNAPSHOT=1 uv run pytest -m toolchain` on
  a machine with the same toolchain (or download the `fixture-snapshot` artifact from the failed CI
  run) and commit the new file.
- A machine without the tools skips the test.

## Writing tests

- Prefer a fake adapter behind a port over a mock of a library.
- Anything that crosses a process boundary needs a failure and recovery test, not only the happy path.
- `hypothesis` is a declared test dependency, but no property tests exist yet; keep strategies small when adding them.
