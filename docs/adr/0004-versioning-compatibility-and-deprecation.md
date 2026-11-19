# ADR 0004: Versioning, compatibility and deprecation

Status: accepted

## Context

Several interfaces are public: the REST API, the webhook payloads, the job message, the CLI, the
SDK, the MCP tools and the book and brief configuration files. None has a stability promise yet.

## Decision

- The package follows Semantic Versioning from 1.0.0. Before 1.0.0, minor versions may break
  contracts, and the changelog says so.
- The public contracts are those listed in criterion A7 of ADR 0003. Anything else, including
  internal modules, is not covered.
- Every contract carries a `schema_version` (the REST API carries it in the path, `/v1/`).
  A new major schema version runs beside the old one for at least one minor release.
- A feature scheduled for removal is deprecated for at least one minor release first: it keeps
  working, logs a warning once, and appears under "Deprecated" in the changelog.
- Pre-releases follow the plan: alpha while contracts are still moving, beta (`b`) once
  `ei book create` works end to end, release candidate (`rc`) once the contracts are frozen.
- The core package and the SDK share one version number and release together.
- Only the latest minor release receives fixes, until a support table in `SECURITY.md` says more.

## Consequences

- Contract changes after the freeze need a snapshot test update and a changelog entry.
- The release workflow keeps refusing a tag whose core and SDK versions differ.
