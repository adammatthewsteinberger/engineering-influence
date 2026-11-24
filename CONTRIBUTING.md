# Contributing

**BLUF:** Read the code of conduct, set up with one `uv sync`, and run the gates before you push: ruff, the import
rules, bandit, types, `pip-audit`, a lock check and the full suite at 100% branch coverage. Code is built in
layers that only point inward, one class per file, and tests pass fakes instead of patching. This repository holds
product code only, never an author's manuscripts or profiles.

Thank you for helping. Read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first; report security
problems privately through [SECURITY.md](SECURITY.md).

## Why the rules are strict

> **Daniel:** Why one class per file and no patching in tests? It feels like a lot of ceremony for a pull request.
>
> **Professor Feynman:** When you walk into a library, how do you find a book?
>
> **Daniel:** By where it is shelved. If I know the rule I do not have to search.
>
> **Professor Feynman:** Same here. Each rule is a shelving rule that a test enforces, so nobody has to remember
> it. One class per file means a class is where its name says. Layers that point inward mean a service never
> imports a database adapter, so swapping the adapter touches one place. And tests pass fakes instead of patching
> because a patched test passes even when the real wiring is wrong.
>
> **Daniel:** So the ceremony is what lets a stranger change the code without breaking something they cannot see.
>
> **Professor Feynman:** That is the idea. The limit: rules enforced by a test are only as good as the test, so a
> new rule needs a test that can fail.
>
> **Daniel:** Follow the shelving, run the gates, and give any new rule a test that can fail.

## The rules at a glance

| Rule | How it is enforced |
|---|---|
| One class per file, no loose production functions | `tests/architecture/test_architecture.py` |
| Every class has an interface in a sibling `interfaces/` folder | `tests/architecture` |
| Layers point inward only | `lint-imports` and the layer matrix in `tests/architecture` |
| Models import nothing effectful, only models, errors and the standard library | `tests/architecture` |
| Tests pass fakes, never patch production code | `tests/architecture/test_no_patching.py` |
| 100% line and branch coverage | `pytest --cov --cov-fail-under=100` |


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
uv run ruff format --check .
uv run lint-imports
uv run bandit -q -r src packages
uv run mypy --strict src packages
uv run pip-audit
uv lock --check
uv run pytest --cov --cov-branch --cov-fail-under=100
sh examples/compose_smoke.sh      # when you touch the runtime, compose file or examples
# when you touch persistence, the broker or how runs advance (then: sh tests/integration/stack.sh down)
eval "$(sh tests/integration/stack.sh up)" && uv run pytest -m integration tests/integration
```

Coverage is 100% with branches. New code arrives with its tests.

The road to 1.0 is [ADR 0003](docs/adr/0003-definition-of-1-0.md); the compatibility and
deprecation rules are [ADR 0004](docs/adr/0004-versioning-compatibility-and-deprecation.md).

## Architecture rules

Interactions call controllers, controllers call services, services use models, contracts and
interfaces, and adapters implement interfaces ([docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)). The tests enforce:

- one class per file, no loose production functions;
- every class implements an interface, and interfaces live in sibling `interfaces/` folders;
- layers point inward only (`lint-imports` runs a strict layers contract);
- only `runtime/` composes concrete classes; everything else receives its collaborators;
- tests pass fakes instead of patching production code.

A new external integration needs an **interface**, an **adapter**, an **ADR** when the choice is
architectural (`docs/adr/`), and failure and recovery tests. Every pipeline side effect must be
bounded, idempotent, observable and recoverable.

## What may live in this repository

This repository is public product code. It never holds an author's manuscripts, profiles,
covers or built books. The `leak-scan` CI job rejects any path containing `manuscripts/`,
`living-waters/`, `archive/`, `prompts/` or `chapters/`, a top-level `output/`, and any `.pdf` or
`.docx` file anywhere in history.

- **Prompts the product sends to a model are code.** They live in a package folder named
  `templates/` (never `prompts/`), are versioned, are tested, and are written generically, with no
  author's voice or content in them. How to write and change one: [docs/PROMPTS.md](docs/PROMPTS.md).
- **Test fixtures** live in `tests/fixtures/<name>/` and use original, synthetic text. Built PDFs are
  never committed; a build is checked by a structural snapshot (`docs/TESTING.md`).
- **Recorded model responses** (cassettes) live in `tests/cassettes/` and are made only from
  synthetic briefs.
- If a legitimate file trips the scan, move the file. Loosening the pattern needs an ADR.

## Changelog fragments

Do not edit `CHANGELOG.md` in a pull request. Add `changelog.d/<short-slug>.md` with one paragraph,
the text of one bullet (see `changelog.d/README.md` and `docs/adr/0005-release-flow-and-changelog-fragments.md`).

## Commits and branches

- Branch from `develop`; open the pull request against `develop`. `main` receives releases.
- Conventional Commit subjects (`feat:`, `fix:`, `docs:`, `ci:`, `chore:` …).
- Every commit carries a `Made-With:` trailer; the installed `commit-msg` hook adds it.
  Pull requests Dependabot opens are exempt from that one check.
- Use your GitHub no-reply address if you want to keep your email out of history.
- Restructuring commits that only move or rename files are listed in `.git-blame-ignore-revs`; GitHub honours it, and locally run `git config blame.ignoreRevsFile .git-blame-ignore-revs`.

## Dependency updates

Dependabot opens pull requests for major versions too. Do not merge on a green title: read the
failing job, run the gates above on the branch, and fix the code or the version bound. Past
examples: `mcp` 2 renamed `FastMCP`; Postgres 18 moved its data directory; pytest-cov 7 stopped
measuring subprocesses.

## Documentation and examples

Examples in `examples/` are run by the test suite and must behave like real use: shell for the CLI,
`requests` or `curl` for HTTP, a real MCP client for MCP. Keep [docs/INTERACTIONS.md](docs/INTERACTIONS.md)
and the README in step with any interface change.
