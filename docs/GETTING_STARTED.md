# Getting started

engineering-influence writes books autonomously and packages them for Amazon KDP
([what that means and what is built](BOOKS_AND_KDP.md)). This page takes you from nothing to a pipeline running on the full stack, then shows each
of the five interfaces. Every command here is run by the example tests or the compose smoke
test, so it works as written.

## Prerequisites

| Tool | Why | Check |
|---|---|---|
| Python 3.12 or newer | the package | `python3 --version` |
| [`uv`](https://docs.astral.sh/uv/) | environments and the lockfile | `uv --version` |
| Docker with `docker compose` | Postgres, RabbitMQ, API, worker | `docker compose version` |
| `curl` | the shell examples | `curl --version` |

## 1. Install for development

```bash
git clone https://github.com/adammatthewsteinberger/engineering-influence
cd engineering-influence
uv sync --extra test --extra runtime --extra api
uv run ei --version        # engineering-influence 0.1.0a1
```

## 2. Start the stack

```bash
sh examples/up.sh
```

The first run writes `examples/.env` (git-ignored, mode 600) with random database and broker
passwords and one API key, then builds the image and starts four containers: Postgres,
RabbitMQ, the API on `127.0.0.1:8000` and the worker. It waits until every container is
healthy. Nothing has a default credential, and nothing is reachable from your network.

Export the connection settings into your shell:

```bash
set -a; . examples/.env; set +a
curl -fsS "$EI_BASE_URL/health/ready"      # {"status":"ready"}
```

## 3. Start a pipeline

```bash
uv run examples/api/start_pipeline.py
```

The request body is the project: a slug, a title, governing postulates and the stages to run.

```json
{
  "slug": "sample-essay",
  "title": "A Sample Essay",
  "postulates": ["Claims must be supported by evidence.", "Persuasion must not outrun truth."],
  "stages": ["thesis", "book"]
}
```

The API answers with the job it queued: `{"job_id": "…", "project_slug": "sample-essay"}`.
The worker picks the job up, runs the `thesis` stage, records `phase.completed` in the ledger,
enqueues `book`, and finishes with `pipeline.completed`:

```bash
docker compose -f examples/docker-compose.yml --env-file examples/.env logs worker
```

## 4. Try the other interfaces

| Interface | Command | Reference |
|---|---|---|
| curl | `sh examples/api/run.sh` | [REST](INTERACTIONS.md#rest-api) |
| SDK (sync) | `uv run python examples/sdk/sync_client.py` | [SDK](INTERACTIONS.md#python-sdk) |
| SDK (async) | `uv run python examples/sdk/async_client.py` | [SDK](INTERACTIONS.md#python-sdk) |
| MCP | `uv run python examples/mcp/client.py` | [MCP](INTERACTIONS.md#mcp-server) |
| CLI | `EI="uv run ei" sh examples/cli/run.sh` | [CLI](INTERACTIONS.md#cli) |
| Observability | `uv run examples/observability/scrape.py` | [Operations](CONFIGURATION.md#observability) |
| Webhooks | see [`examples/README.md`](../examples/README.md#webhooks) | [Webhooks](INTERACTIONS.md#webhooks) |

## 5. Stop

```bash
sh examples/down.sh            # keep the data
sh examples/down.sh --volumes  # delete it
```

## Where to go next

- Run it for real: [CONFIGURATION.md](CONFIGURATION.md) lists every variable and what fails closed.
- Understand it: [ARCHITECTURE.md](ARCHITECTURE.md).
- Something went wrong: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
