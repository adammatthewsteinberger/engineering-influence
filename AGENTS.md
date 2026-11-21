# Guidance for coding agents and contributors

This project writes complete books (fiction and non-fiction) autonomously and packages them
for Amazon KDP. Keep that purpose in mind: every change should serve an unattended run that
ends in a verified, KDP-ready package, and docs must stay honest about what is built
(`docs/BOOKS_AND_KDP.md`). Read `README.md`, `docs/ARCHITECTURE.md` and `docs/adr/` before changing models, services or
infrastructure code. `llms.txt` lists the documents.

## Rules

- Keep `models/` pure. External effects go behind an interface in `interfaces/` with an adapter in
  `infrastructure/` or `repositories/`.
- One class per file; no loose production functions; interfaces in sibling `interfaces/` folders.
- Layers point inward: transports call controllers, controllers call services. `uv run lint-imports` enforces it.
- Only `runtime/` builds concrete classes: interactions, controllers and services receive their collaborators as interfaces. (A few pure helpers are still built where they are used, such as the audit classes in `PublishingController` and the checks inside `EpubVerifier`. Anything a test has to replace is injected, adapters always are, and `tests/architecture/test_no_patching.py` holds that line.)
- The structure of `docs/adr/0006-onion-layers-and-interfaces.md` is in place and every rule in `tests/architecture/` holds with no exceptions: fix a violation rather than allowing it. `scripts/refactor/move_map.toml` records where each class moved from.
- Every pipeline side effect must be bounded, idempotent, observable and recoverable.
- Fail closed: missing keys, secrets and settings stop the process; they never open it.
- Never log or print secrets; pass them as `extra` fields so masking applies.

## Before you finish

```bash
uv sync --extra test --extra runtime --extra dev --extra publishing
uv run ruff check . && uv run ruff format --check . && uv run lint-imports
uv run bandit -q -r src packages && uv lock --check
uv run mypy --strict src packages
uv run pytest --cov --cov-branch --cov-fail-under=100
sh examples/compose_smoke.sh     # if you changed the runtime, compose file or an example
# if you changed persistence, the broker or how runs advance; then `sh tests/integration/stack.sh down`
eval "$(sh tests/integration/stack.sh up)" && uv run pytest -m integration tests/integration
```

Check each command's real exit status; do not trust a pipe. For a user-visible change add a
`changelog.d/<slug>.md` fragment and leave `CHANGELOG.md` alone (`changelog.d/README.md`). Commits use Conventional Commit subjects and carry a
`Made-With:` trailer (`uv run vibey-gh install` adds the hook).

## Do not

- Merge a dependency bump because its title looks routine; run the gates (see `CONTRIBUTING.md`).
- Rewrite history on `main` or `develop`, publish to PyPI, or change repository visibility.
- Expose the MCP server or the CLI on a network: they are unauthenticated local processes.
- Add examples that fake their transport. Examples must behave like real use and are run by the tests.
