# Guidance for coding agents and contributors

Read `README.md`, `docs/ARCHITECTURE.md` and `docs/adr/` before changing domain or
infrastructure code. `llms.txt` lists the documents.

## Rules

- Keep `domain/` pure. External effects go behind a port in `interfaces/` with an adapter in
  `infrastructure/` or `repositories/`.
- One class per file; no loose production functions; interfaces in sibling `interfaces/` folders.
- Layers point inward: transports call controllers, controllers call services. `uv run lint-imports` enforces it.
- Every pipeline side effect must be bounded, idempotent, observable and recoverable.
- Fail closed: missing keys, secrets and settings stop the process; they never open it.
- Never log or print secrets; pass them as `extra` fields so masking applies.

## Before you finish

```bash
uv sync --extra test --extra runtime --extra dev --extra publishing
uv run ruff check . && uv run lint-imports && uv run bandit -q -r src packages
uv run mypy --strict src packages
uv run pytest --cov --cov-branch --cov-fail-under=100
sh examples/compose_smoke.sh     # if you changed the runtime, compose file or an example
```

Check each command's real exit status; do not trust a pipe. Add a `CHANGELOG.md` line under
`## Unreleased` for user-visible changes. Commits use Conventional Commit subjects and carry a
`Made-With:` trailer (`uv run vibey-gh install` adds the hook).

## Do not

- Merge a dependency bump because its title looks routine; run the gates (see `CONTRIBUTING.md`).
- Rewrite history on `main` or `develop`, publish to PyPI, or change repository visibility.
- Expose the MCP server or the CLI on a network: they are unauthenticated local processes.
- Add examples that fake their transport. Examples must behave like real use and are run by the tests.
