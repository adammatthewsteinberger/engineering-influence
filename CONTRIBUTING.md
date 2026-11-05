# Contributing

Thank you for helping. Read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first; report security
problems privately through [SECURITY.md](SECURITY.md).

## Set up

You need Python 3.12 or newer, [`uv`](https://docs.astral.sh/uv/), and Docker for the smoke test.

```bash
git clone https://github.com/adammatthewsteinberger/engineering-influence
cd engineering-influence
uv sync --extra test --extra runtime --extra dev --extra publishing
uv run vibey-gh install        # commit hooks: add the Made-With trailer, check subjects
```

## The checks a pull request must pass

Run them before you push (details in [docs/TESTING.md](docs/TESTING.md)):

```bash
uv run ruff check .
uv run lint-imports
uv run bandit -q -r src packages
uv run mypy --strict src packages
uv run pytest --cov --cov-branch --cov-fail-under=100
sh examples/compose_smoke.sh      # when you touch the runtime, compose file or examples
```

Coverage is 100% with branches. New code arrives with its tests.

## Architecture rules

Interactions call controllers, controllers call services, services use domain types and ports,
and adapters implement ports ([docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)). The tests enforce:

- one class per file, no loose production functions;
- interfaces live in sibling `interfaces/` folders;
- layers point inward only.

A new external integration needs a **port**, an **adapter**, an **ADR** when the choice is
architectural (`docs/adr/`), and failure and recovery tests. Every pipeline side effect must be
bounded, idempotent, observable and recoverable.

## Commits and branches

- Branch from `develop`; open the pull request against `develop`. `main` receives releases.
- Conventional Commit subjects (`feat:`, `fix:`, `docs:`, `ci:`, `chore:` …).
- Every commit carries a `Made-With:` trailer; the installed `commit-msg` hook adds it.
  Pull requests Dependabot opens are exempt from that one check.
- Use your GitHub no-reply address if you want to keep your email out of history.
- Update `CHANGELOG.md` under `## Unreleased` for anything a user would notice.

## Dependency updates

Dependabot opens pull requests for major versions too. Do not merge on a green title: read the
failing job, run the gates above on the branch, and fix the code or the version bound. Past
examples: `mcp` 2 renamed `FastMCP`; Postgres 18 moved its data directory; pytest-cov 7 stopped
measuring subprocesses.

## Documentation and examples

Examples in `examples/` are run by the test suite and must behave like real use: shell for the CLI,
`requests` or `curl` for HTTP, a real MCP client for MCP. Keep [docs/INTERACTIONS.md](docs/INTERACTIONS.md)
and the README in step with any interface change.
