# Examples

Each example does what you would do for real: shell commands for the CLI, `requests` and
`curl` for HTTP, the SDK for Python, a real MCP client for MCP, and a real HTTP server for
webhooks. The test suite runs all of them (`tests/e2e/test_examples.py`), and
`compose_smoke.sh` runs the curl example against the full stack.

```text
examples/
├── up.sh · down.sh            start / stop the stack with generated credentials
├── docker-compose.yml         Postgres, RabbitMQ, API, worker (no default credentials)
├── compose_smoke.sh           end-to-end check used by CI
├── sample_project/            the project every example sends
├── cli/run.sh                 the `ei` command in a terminal
├── api/start_pipeline.py      REST with Python `requests`
├── api/run.sh                 REST with curl
├── sdk/sync_client.py         Python SDK, synchronous
├── sdk/async_client.py        Python SDK, asynchronous (three pipelines at once)
├── mcp/server.py              the MCP server over stdio
├── mcp/client.py              an MCP client that spawns it and calls the tool
├── webhooks/receiver.py       a stdlib receiver that verifies signature, time and replay
├── webhooks/send_event.py     sends valid, replayed, tampered and stale deliveries
└── observability/scrape.py    health, correlation id, Prometheus metrics
```

## Run against the stack

```bash
sh examples/up.sh                    # creates examples/.env on first run
set -a; . examples/.env; set +a      # EI_BASE_URL, EI_API_KEY, EI_WEBHOOK_SECRET
```

| Example | Command | Needs |
|---|---|---|
| REST (`requests`) | `uv run examples/api/start_pipeline.py` | `EI_API_KEY` |
| REST (curl) | `sh examples/api/run.sh` | `EI_API_KEY`, `curl` |
| SDK sync / async | `uv run python examples/sdk/sync_client.py` (or `async_client.py`) | `EI_API_KEY`, `uv sync --extra test` |
| Observability | `uv run examples/observability/scrape.py` | `EI_API_KEY` |
| MCP | `uv run python examples/mcp/client.py` | `uv sync --extra test` (no stack) |
| CLI | `EI="uv run ei" sh examples/cli/run.sh` | `uv sync --extra runtime --extra api` (no stack) |

The three scripts that import nothing from this package (`api/start_pipeline.py`,
`webhooks/send_event.py`, `observability/scrape.py`) declare their one dependency inline
([PEP 723](https://peps.python.org/pep-0723/)), so `uv run <script>` works from anywhere.

Variables: `EI_BASE_URL` (default `http://127.0.0.1:8000`), `EI_API_KEY`, `EI_WEBHOOK_SECRET`,
`EI_RECEIVER_PORT` (default `9000`), `EI_RECEIVER_URL`. A script that needs a credential and
does not find it exits with status 2 and says which variable.

## Webhooks

Two terminals, same secret:

```bash
# terminal 1
set -a; . examples/.env; set +a
python3 examples/webhooks/receiver.py
# terminal 2
set -a; . examples/.env; set +a
uv run examples/webhooks/send_event.py
```

```text
first delivery: 202 accepted
replay of the same delivery: 409 replayed
tampered body: 401 bad_signature
an hour old: 401 stale_timestamp
```

The platform does not emit webhooks yet. The sender reproduces the request it will make, so
you can build and test a receiver today. The signature format is in
[docs/INTERACTIONS.md](../docs/INTERACTIONS.md#webhooks).

## What these do not cover

`ei pipeline start` and the MCP server use in-memory adapters: they validate and plan, but
they do not queue work on the stack. To run work on the stack, use REST or the SDK.

## Stop

```bash
sh examples/down.sh --volumes
```
