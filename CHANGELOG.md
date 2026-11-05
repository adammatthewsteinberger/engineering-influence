# Changelog

## Unreleased

- Documentation now states the purpose everywhere: fully autonomous writing of fiction and non-fiction books, packaged ready to self-publish on Amazon KDP. Added `docs/BOOKS_AND_KDP.md` (what a KDP-ready package contains, what is built, what is not); package descriptions updated.
- Restored a green `develop` after the Dependabot major bumps: the MCP server uses `mcp.server.mcpserver.MCPServer` (`mcp` 2.x renamed `FastMCP`) and the bounds now require `mcp>=2,<3`; the compose file mounts `/var/lib/postgresql` for PostgreSQL 18; coverage measures child processes itself (`patch = ["subprocess"]`) now that pytest-cov 7 does not.
- Pull requests opened by Dependabot are exempt from the `Made-With:` provenance check (it cannot add the trailer); Conventional Commit checking still applies.
- Rewrote the examples to behave like real use: `requests` and `curl` against a running API, a real MCP stdio client and server, and a stdlib webhook receiver with a sender, plus `examples/up.sh` and `down.sh` to run the stack. The example tests run them against real sockets.
- Documentation overhaul: README, getting started, interfaces reference, architecture, troubleshooting, testing, contributing, agent guidance and `llms.txt`.
- The release workflow can be started by hand for an existing tag (`workflow_dispatch`), and the guard now verifies the commit of the tag being released instead of the commit that started the run.
- CI can be started by hand.

## 0.1.0a1

- Established the orphan FOSS package and initial domain boundaries.
- Recorded the vibey integration boundary and fallback adapter decision.
- Added fail-closed security adapters: API key authentication, per-address and per-key rate limiting, timestamped webhook signatures with replay defence, an outbound URL policy that blocks SSRF, path confinement, and upload inspection. The REST API now requires a guard.
- `ApplicationError` stays immutable but no longer blocks `__traceback__`, which crashed it when raised on a worker thread.
- Added observability: JSON logs with secret masking, a correlation id carried from request to queue to worker to webhook, request counters, `/health/live`, `/health/ready` and an authenticated Prometheus `/metrics`, service latency tracing, crash alert hooks and a worker heartbeat with a silence watchdog.
- Webhook dispatch now isolates failures per event, counts attempts, and dead-letters with an alert after repeated failure. Previously one rejected or unreachable destination blocked every event behind it. The outbox table gained `dead_at`.
- Added `ei serve api` and `ei serve worker`, a Dockerfile, and `examples/docker-compose.yml` (Postgres, RabbitMQ, API, worker) with a smoke test. All settings fail closed and the compose file has no default credentials.
- Added a worker that consumes jobs from RabbitMQ, runs each stage, records it in the ledger and enqueues the next, with malformed and failing jobs dead-lettered. `StartPipeline` now tells a job which stages follow it.
- Fixed the RabbitMQ publisher silently dropping messages when the queue had not been declared yet.
- Added release automation: a tag-triggered workflow that guards the tag, builds and installs the real artifacts, attests build provenance, creates the GitHub release with checksums and an SBOM, and publishes to PyPI behind an approval gate. See `docs/RELEASING.md`.
- The version is now defined once, in `__version__`, and read by `pyproject.toml`, `ei --version` and the API. Builds are reproducible.
- The wheel now ships `py.typed`, and the source distribution no longer includes local tool caches, git hooks or agent configuration. Added project URLs, classifiers and an SDK README.
- `ei serve` without the `api` and `runtime` extras now says which extras to install instead of failing with a traceback.
- Pinned every GitHub Action to a commit SHA, restricted job permissions, and added `actionlint` and `zizmor` checks.

