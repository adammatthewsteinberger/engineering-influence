# Changelog

## Unreleased

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

