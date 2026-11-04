# Changelog

## Unreleased

- Established the orphan FOSS package and initial domain boundaries.
- Recorded the vibey integration boundary and fallback adapter decision.
- Added fail-closed security adapters: API key authentication, per-address and per-key rate limiting, timestamped webhook signatures with replay defence, an outbound URL policy that blocks SSRF, path confinement, and upload inspection. The REST API now requires a guard.
- `ApplicationError` stays immutable but no longer blocks `__traceback__`, which crashed it when raised on a worker thread.
