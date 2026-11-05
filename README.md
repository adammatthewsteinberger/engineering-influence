# engineering-influence

**engineering-influence writes complete books, fiction and non-fiction, fully autonomously, and produces files and metadata that are ready to self-publish on Amazon KDP.**

You give it a project (a title, governing postulates, the stages to run). It drafts through
ordered stages with typed gates, records every step in a ledger, survives crashes because the
work lives on a queue, and ends with a verified KDP package: paperback and hardcover interior
PDFs, EPUB, covers, listing metadata and a release-readiness report. See
[docs/BOOKS_AND_KDP.md](docs/BOOKS_AND_KDP.md) for exactly what that includes.

The same behavior is reachable five ways, all over one controller layer: a **REST API**,
an **MCP server**, a **CLI**, a **Python SDK** (sync and async) and **signed webhooks**.

> **Status: alpha (`0.1.0a1`).** The orchestration and the KDP packaging and verification are
> built and tested. The *writing* is not yet autonomous: the runner and gate that ship are
> deterministic placeholders, so a pipeline runs end to end but produces fixed text until a
> model-backed runner is plugged in. Nothing uploads to KDP for you (KDP has no API); a person
> reviews and uploads. See [Limitations](#limitations).

This repository holds the method and the software only. Author-owned manuscripts, profiles
and private publishing configuration live in a separate private repository.

## Try it in five minutes

You need Docker with the compose plugin, [`uv`](https://docs.astral.sh/uv/) and `python3`.

```bash
git clone https://github.com/adammatthewsteinberger/engineering-influence
cd engineering-influence
sh examples/up.sh                      # Postgres + RabbitMQ + API + worker, with generated credentials
set -a; . examples/.env; set +a        # exports EI_BASE_URL, EI_API_KEY, EI_WEBHOOK_SECRET
uv run examples/api/start_pipeline.py  # start a pipeline over REST
```

```text
ready: 200 ready
without a key: 401
started: 200 {"job_id": "6c05b79f-…", "project_slug": "sample-essay"}
```

Then watch the worker run it: `docker compose -f examples/docker-compose.yml --env-file examples/.env logs -f worker`.
Stop with `sh examples/down.sh --volumes`.

## Choose your interface

| You are… | Use | Start here |
|---|---|---|
| Calling from any language | REST API | [`examples/api/`](examples/api) (Python `requests`, `curl`) |
| Writing Python | SDK, sync or async | [`examples/sdk/`](examples/sdk) |
| Wiring an AI host or agent | MCP server (stdio) | [`examples/mcp/`](examples/mcp) |
| At a terminal | `ei` CLI | [`examples/cli/run.sh`](examples/cli/run.sh) |
| Receiving events | Signed webhooks | [`examples/webhooks/`](examples/webhooks) |
| Operating it | Health, metrics, logs | [`examples/observability/`](examples/observability) |

Install the package without the repository: `pip install "engineering-influence[api,runtime]"`
(pre-release; PyPI publication is not enabled yet, so use the
[GitHub release](https://github.com/adammatthewsteinberger/engineering-influence/releases) assets).
Optional extras: `api`, `runtime`, `cli`, `mcp`, `publishing`.

## Documentation

| Read | For |
|---|---|
| [docs/BOOKS_AND_KDP.md](docs/BOOKS_AND_KDP.md) | What a finished book package is, what is built and what is not |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Install, run the stack, your first pipeline |
| [docs/INTERACTIONS.md](docs/INTERACTIONS.md) | Reference for the REST API, SDK, MCP tool, CLI and webhooks |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Every environment variable, security setting and operational limit |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layers, request flow, the worker, and the extension points |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Symptoms, causes and fixes |
| [docs/TESTING.md](docs/TESTING.md) | The gates CI enforces and how to run them |
| [docs/RELEASING.md](docs/RELEASING.md) | Cutting and verifying a release |
| [docs/adr/](docs/adr) | Architecture decisions |
| [CHANGELOG.md](CHANGELOG.md) | What changed |

## Limitations

Read these before you depend on it:

- The writing is not autonomous yet: the runner and gate are placeholders (`DeterministicRunner`, `NonEmptyArtifactGate`).
- Delivery is at least once: a crash between the ledger write and the acknowledgement re-runs a stage.
- There is no read API and no endpoint to resolve a human gate; progress is in the ledger table and the logs.
- No service emits webhooks yet, although signing, the outbox and a verifier exist.
- `ei pipeline start` and the MCP server use in-memory adapters; they plan work but do not reach the stack.
- There is no database migration tool; recreate databases created by an earlier build.

Details and the full list: [docs/CONFIGURATION.md](docs/CONFIGURATION.md#limits-to-know).

## Contributing, security, support

[CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) (report privately) ·
[SUPPORT.md](SUPPORT.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## License

MIT. See [LICENSE](LICENSE).
