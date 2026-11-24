# Compatibility: what is promised, and how a change to it is caught

**BLUF:** Ten public contracts are frozen: each has a snapshot file, and a test fails the moment the real thing
differs from its snapshot. Before 1.0.0 a minor version may still break one, and the changelog will say so. From
1.0.0 a changed snapshot needs a reason, a changelog entry and, if it is not compatible, a new schema version.

The package follows [ADR 0004](adr/0004-versioning-compatibility-and-deprecation.md). **Before 1.0.0 a minor version may break any
contract below, and the changelog says so.** What exists today is the guard that makes a break visible: every contract in this
page is committed as a snapshot in `tests/contracts/snapshots/`, and a test fails the moment the real thing differs from it. From
1.0.0 a snapshot that changes is a change that needs a reason, a changelog entry and, if it is not compatible, a new schema version.

## How a promise is kept by a file

> **Daniel:** I am building on the REST API. How do I know you will not rename a field next month?
>
> **Professor Feynman:** How does a locksmith know a new key will still open your door?
>
> **Daniel:** He keeps the old key and cuts the new one against it.
>
> **Professor Feynman:** A snapshot is the old key. The shape of every contract is written to a file. A test
> regenerates the shape from the code and compares. If someone renames your field, the comparison fails and the
> build goes red before it reaches you.
>
> **Daniel:** They could just regenerate the file and commit it.
>
> **Professor Feynman:** They could, and then the change is sitting in the pull request as a diff with a name on
> it. That is the point: a break cannot happen by accident, only on purpose and in plain sight. The limit: the
> file records the shape, not the meaning. A field that keeps its name and changes what it means would slip past.
>
> **Daniel:** So I am protected from accidents, the changelog tells me about decisions, and before 1.0 I should
> still pin a version.

## The contracts

| Contract | Where it is defined | Snapshot (`tests/contracts/snapshots/`) |
|---|---|---|
| The brief a run starts from | `contracts/brief/v1` (`BookBriefV1`) | `brief_v1_schema.json` |
| A book's config (`books/<slug>.toml`) | `contracts/book_config/v1` (`BookConfigV1`) | `book_config_v1_schema.json` |
| A run's summary | `contracts/run/v1` (`RunSummaryV1`) | `run_summary_v1_schema.json` |
| The queued job | `contracts/job_message.py` (`JobMessage`) | `job_message_v1_schema.json` |
| The REST API | the OpenAPI document the stack serves (`/openapi.json`) | `rest_openapi.json`, `rest_error_shapes.json` |
| Webhooks: the envelope, the event catalogue, the headers, the signature | `contracts/webhook/v1` (`WebhookEventV1`) | `webhook_v1.json` |
| The command line | the `ei` parser (every command, option, choice and default) | `cli_command_tree.json` |
| The SDK | `engineering_influence_sdk` (both clients: every public method and its signature) | `sdk_public_surface.json` |
| The MCP tools | the tools of `ei serve mcp` and their arguments | `mcp_tools.json` |
| Error codes (`RUN_NOT_FOUND`) and the issue codes a run records (`stage-failed`) | the literals in the source | `error_codes.json`, `issue_codes.json` |

Every versioned document carries a `schema_version` (the REST API carries it in the path, `/v1/`). A document with no
`schema_version` is read as version 1, so what was written before the field existed still loads. A different version is refused,
never guessed at. A new major version runs beside the old one for at least one minor release.

The snapshots leave out prose: a docstring, a help line and a name generated from a function (an OpenAPI `summary` or
`operationId`) are documentation, so rewording them is not a change to the contract.

## What counts as compatible

**Compatible (a snapshot changes, the version does not):**

- A new optional field in a brief, a config, a run summary or an event's `data`; a new event type; a receiver must ignore what it does not know.
- A new REST path, a new optional query or body field, a new response field.
- A new `ei` command or option (with a default that keeps the old behaviour), a new SDK method, a new MCP tool.
- A new error code or issue code.

**Breaking (needs a new schema version, or a major release after 1.0.0):**

- Removing or renaming anything above, changing a type, making an optional field required, or narrowing what a field accepts.
- Changing what a command exits with, what a status or code means, or how a signature is computed.
- Removing a documented error code a client may be handling.

## Changing a contract on purpose

1. Make the change. The matching test fails and says which contract moved.
2. Run `EI_UPDATE_CONTRACTS=1 uv run pytest tests/contracts`, read the diff of the snapshot, and commit it with the change.
3. Add a changelog fragment (`changelog.d/`) that says whether the change is compatible. A breaking change under a
   stable version is also listed under "Deprecated" for a minor release first, and keeps working meanwhile (ADR 0004).

## What is not promised

- **ACP** (`ei acp`, the Agent Client Protocol session surface) has tests but no snapshot and is not yet a stable contract.
- **The pipeline stages `thesis`, `book`, `novel`, `screenplay`, `hub`, `spokes`, `distribution` and `publish`** and the `/v1/pipelines`
  route, the SDK's `start_pipeline` and the MCP `start_pipeline` tool: the stage placeholders are experimental and outside the
  stable contract (ADR 0003). They are in the snapshots only so that a change to them is seen.
- **The files a run writes** (`audit.md`, `build/…`, the stage outputs): `quality-report.json` and `publication-report.json` carry a
  `schema_version` but are not snapshotted yet. Their documented fields are the intent; do not parse the rest.
- **Python imports.** Only the SDK's two clients are public Python API. Everything under `engineering_influence` moved when the
  onion layers were introduced and may move again; programs should use the REST API, the SDK, the CLI or MCP.
- **Prompt templates** are versioned and pinned separately (`docs/PROMPTS.md`), and are not an interface.
- **Webhooks are not delivered yet.** The envelope, the catalogue, the headers and the signature are frozen so that a receiver written
  now keeps working; the worker records the events but no service sends them (`docs/CONFIGURATION.md`).
- **Two error shapes.** What the application refuses is `{code, message, retryable}`; a request the framework cannot read (a missing
  field, a wrong type) is FastAPI's `{detail: [...]}`, which the OpenAPI document declares as `HTTPValidationError`.
- **CLI exit codes** are documented per command in `docs/INTERACTIONS.md` but are not in the snapshot.
