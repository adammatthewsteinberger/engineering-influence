# engineering-influence

**engineering-influence writes complete books, fiction and non-fiction, fully autonomously, and produces files and metadata that are ready to self-publish on Amazon KDP.**

You give it a project (a title, governing postulates, the stages to run). It drafts through
ordered stages with typed gates, records every step in a ledger, survives crashes because the
work lives on a queue, and ends with a verified KDP package: paperback and hardcover interior
PDFs, EPUB, covers, listing metadata and a release-readiness report. See
[docs/BOOKS_AND_KDP.md](docs/BOOKS_AND_KDP.md) for exactly what that includes.

The same behavior is reachable five ways, all over one controller layer: a **REST API**,
an **MCP server**, a **CLI**, a **Python SDK** (sync and async) and **signed webhooks**.

> **Status: alpha (`0.1.0a2`).** The orchestration, the KDP packaging and verification, and the
> writing stages are built and tested: `ei book create` takes an idea to a built KDP package with a
> free local model or a configured one. The writing has only been run against scripted servers, never
> a live provider, and no real model has been measured against the quality bar yet. Nothing uploads to
> KDP for you (KDP has no API); a person reviews and uploads. See [Limitations](#limitations).

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
| Wiring an AI host or agent | MCP server (stdio, `ei serve mcp`) | [`examples/mcp/`](examples/mcp) |
| At a terminal | `ei` CLI | [`examples/cli/run.sh`](examples/cli/run.sh) |
| Receiving events | Signed webhooks | [`examples/webhooks/`](examples/webhooks) |
| Operating it | Health, metrics, logs | [`examples/observability/`](examples/observability) |

Install the package without the repository: `pip install "engineering-influence[api,runtime]"`
(pre-release; PyPI publication is not enabled yet, so use the
[GitHub release](https://github.com/adammatthewsteinberger/engineering-influence/releases) assets).
Optional extras: `api`, `webhooks`, `runtime`, `mcp`, `publishing` (and `test` and `dev` for contributors).

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
| [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) | What is promised to callers, and the snapshots that catch a change to it |
| [docs/EVALUATION.md](docs/EVALUATION.md) | `ei evaluate`: the paid evaluation that measures the 1.0 quality and cost bars |
| [docs/RELEASING.md](docs/RELEASING.md) | Cutting and verifying a release |
| [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) | What is protected, from whom, and what is not |
| [docs/NOVELS.md](docs/NOVELS.md) | The novel stages, from brief to a built book |
| [docs/PROMPTS.md](docs/PROMPTS.md) | The prompt templates, their versions and the lock |
| [docs/LOCAL_MODEL.md](docs/LOCAL_MODEL.md) | The free local model the worker uses by default |
| [docs/MODEL_PROFILES.md](docs/MODEL_PROFILES.md), [docs/MODEL_CATALOG.md](docs/MODEL_CATALOG.md), [docs/MODEL_CALLS.md](docs/MODEL_CALLS.md) | Choosing, pricing and calling a model |
| [docs/LIVE_SMOKE_TEST.md](docs/LIVE_SMOKE_TEST.md) | The capped test against a real model |
| [docs/RESEARCH.md](docs/RESEARCH.md), [docs/TOOL_LOCK.md](docs/TOOL_LOCK.md) | Web search and fetch for the research stage, and the tool lock |
| [docs/SKILLS.md](docs/SKILLS.md), [docs/PLUGINS.md](docs/PLUGINS.md) | Skills and plugin bundles |
| [docs/WORKER_IMAGE.md](docs/WORKER_IMAGE.md) | The worker image and the TeX toolchain |
| [docs/adr/](docs/adr) | Architecture decisions |
| [CHANGELOG.md](CHANGELOG.md) | What changed |

## Limitations

Read these before you depend on it:

- The writing is built but unproven: it has run only against scripted servers, never a live provider. The placeholder runner and gate (`DeterministicRunner`, `NonEmptyArtifactGate`) apply only to the `/v1/pipelines` stage pipeline and to `EI_STAGE_EXECUTOR=deterministic`.
- Delivery is at least once: a crash between the ledger write and the acknowledgement re-runs a stage.
- There is no endpoint to resolve a pipeline's human gate (a run's spend consent is answered with `ei run grant` and `deny`, `POST /v1/runs/{id}/grant` and `deny`, or the MCP tools). A book run can be read with `GET /v1/runs/{id}` and `ei run status`, but pipeline progress is still only in the ledger table and the logs.
- No service emits webhooks yet, although signing, the outbox and a verifier exist.
- `ei pipeline start` and the example MCP server (`examples/mcp/server.py`) use in-memory adapters; they plan work but do not reach the stack. `ei serve mcp` does.
- The schema is managed by `ei db upgrade`; run it before starting a new release. A database created before the outbox gained its `dead_at` column must be recreated, because the baseline migration does not add it.

Details and the full list: [docs/CONFIGURATION.md](docs/CONFIGURATION.md#limits-to-know).

## About the author and the vibey ecosystem

**BLUF: Krypton and the vibey engine are an open-source Claude Code and OpenAI Codex killer—engineered to replace both completely free of charge, 100% open to everyone, and censorship-free.** Unlike agents that produce unvetted AI slop, the vibey toolchain writes and verifies code the way a Principal Software Engineer does: architected with rigor, backed by 100% branch test coverage, sealed in an append-only cryptographic ledger, and built on an architecture designed for sovereign AGI with superintelligence coming soon.

### Who this is for

Per [ADR 0002](docs/adr/0002-audience-priority-and-sovereign-agent-doctrine.md), engineering-influence and the vibey ecosystem prioritize audiences in this strict order:

1. **FOSS developers.** Free and open-source engineers building and running autonomous tools with no subscriptions or telemetry walls.
2. **Freelancers.** Independent operators and consultants delivering Principal-grade fixed-scope client projects with sovereign tools.
3. **Universities and academia.** Researchers and scholars using open, verifiable, and cited methodologies.
4. **Governments and militaries.** Public-sector and defense teams needing air-gapped models, verifiable provenance, and tamper-evident audit trails.
5. **Non-profit orgs.** Mission-driven teams that need budget-preserving, durable software.
6. **Industry teams.** Commercial teams and enterprises seeking production-grade agent infrastructure.

## Contributing, security, support

[CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) (report privately) ·
[SUPPORT.md](SUPPORT.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## License

MIT. See [LICENSE](LICENSE).
