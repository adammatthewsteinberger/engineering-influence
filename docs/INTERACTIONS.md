# Interfaces reference

Every interface starts or drives the same thing: an autonomous book-writing run that ends in a
KDP-ready package ([details](BOOKS_AND_KDP.md)). Five interfaces sit over the same controller layer, so they accept the same request and
return the same result. Pick by who is calling.

| Interface | Process | Authenticated | Reaches the stack |
|---|---|---|---|
| [REST API](#rest-api) | `ei serve api` | API key | yes |
| [Python SDK](#python-sdk) | your code | API key | yes (it calls the REST API) |
| [MCP server](#mcp-server) | stdio child process | no (local only) | no (in-memory) |
| [CLI](#cli) | `ei` | no (local only) | `serve` and `book` yes; `pipeline start` no |
| [Webhooks](#webhooks) | outbound HTTPS | HMAC signature | yes |

## The request

Every start request is a **project**:

| Field | Type | Rules |
|---|---|---|
| `slug` | string | required, at least 1 character |
| `title` | string | required, at least 1 character |
| `postulates` | list of strings | required, at least 1: the claims the pipeline must stay within |
| `stages` | list of strings | required, at least 1, from `thesis`, `book`, `novel`, `screenplay`, `hub`, `spokes`, `distribution`, `publish` |

The result is `{"job_id": "<id>", "project_slug": "<slug>"}`: the job queued for the first stage.
The worker runs the stages in the order given.

## REST API

Run it with `ei serve api` (see [CONFIGURATION.md](CONFIGURATION.md#running-the-stack)); the
compose stack publishes it on `127.0.0.1:8000`.

| Method and path | Auth | Purpose |
|---|---|---|
| `POST /v1/pipelines` | key | Start a pipeline. Body: a project. `200` with the result. |
| `GET /health/live` | none | `{"status":"alive"}` while the process runs. |
| `GET /health/ready` | none | `200 {"status":"ready"}` or `503 {"status":"unavailable"}`. |
| `GET /metrics` | key | Prometheus text format. |
| `GET /docs`, `/openapi.json` | none | FastAPI's generated schema for this build. |

**Authentication.** Send `Authorization: Bearer <key>` or `X-API-Key: <key>`. Keys come from
`EI_API_KEYS`. There is no unauthenticated mode.

**Correlation.** Send `X-Request-ID` (8 to 64 characters of `A-Z a-z 0-9 . _ -`) or a W3C
`traceparent`; otherwise one is generated. It is echoed in the `X-Request-ID` response header,
copied into the queued job, restored by the worker and sent on outbound webhooks.

**Errors.** Application errors are `{"code", "message", "retryable"}`:

| Status | `code` | Meaning | Retry? |
|---|---|---|---|
| 401 | `UNAUTHORIZED` | Missing or wrong key | no |
| 429 | `RATE_LIMITED` | Per-address or per-key budget spent | yes, with backoff |
| 422 | n/a | Body failed validation (FastAPI's `detail` list) | no, fix the body |
| 503 | `SECRET_MISSING` | A required secret is not configured | after fixing configuration |

Python with `requests`:

```python
import os, requests

base, key = os.environ["EI_BASE_URL"], os.environ["EI_API_KEY"]
reply = requests.post(
    f"{base}/v1/pipelines",
    headers={"Authorization": f"Bearer {key}"},
    json={
        "slug": "sample-essay",
        "title": "A Sample Essay",
        "postulates": ["Claims must be supported by evidence."],
        "stages": ["thesis"],
    },
    timeout=10,
)
reply.raise_for_status()
print(reply.json())  # {'job_id': '…', 'project_slug': 'sample-essay'}
```

Full scripts: [`examples/api/start_pipeline.py`](../examples/api/start_pipeline.py),
[`examples/api/run.sh`](../examples/api/run.sh).

## Python SDK

`packages/engineering-influence-sdk` is a thin typed wrapper over `httpx` for the one
operation the API has. It ships in this repository and in each release.

```python
from engineering_influence_sdk import EngineeringInfluenceClient

client = EngineeringInfluenceClient("http://127.0.0.1:8000", api_key)
started = client.start_pipeline(
    "sample-essay", "A Sample Essay", ("Claims must be supported by evidence.",), ("thesis", "book")
)
client.close()
```

`AsyncEngineeringInfluenceClient` has the same signature with `await` (and `await client.close()`).
Any non-2xx answer raises `httpx.HTTPStatusError`; the API's error document is in
`error.response`. Scripts: [`examples/sdk/`](../examples/sdk).

## MCP server

`McpApplication(ledger, queue).build()` returns an `MCPServer` (from the official `mcp` 2.x SDK)
with one tool:

| Tool | Arguments | Returns |
|---|---|---|
| `start_pipeline` | `slug`, `title`, `postulates` (list), `stages` (list) | `{"job_id", "project_slug"}` |

Run it over stdio with [`examples/mcp/server.py`](../examples/mcp/server.py) and point an MCP host at
that command (the file shows a Claude Desktop entry). [`examples/mcp/client.py`](../examples/mcp/client.py)
is a client that spawns it, lists the tools and calls one. The server is a local process: it
is not authenticated and the example uses in-memory adapters, so do not expose it on a network.

## CLI

```text
ei --version
ei pipeline start --slug S --title T --postulate P [--postulate P …] [--stage STAGE …]
ei serve api|worker
ei book [--root DIR] audit|build|epub|covers|qa|publish …
```

| Command | What it does | Exit status |
|---|---|---|
| `ei pipeline start` | Validates a project and prints the result as JSON. In-memory only: it does not queue work on the stack. `--stage` defaults to `thesis`. | `0`; `2` on a usage error |
| `ei serve api` / `worker` | Runs the API or the worker from `EI_*` settings. | `2` and one line naming the bad variable; never a traceback |
| `ei book …` | Audit, build and publish books (needs the `publishing` extra and, for PDFs, a TeX toolchain). Reads `engineering-influence.toml` in `--root`. | `0` ok; `1` a build or audit failure; `2` bad arguments |

`python -m engineering_influence` is the same program. Walk-through: [`examples/cli/run.sh`](../examples/cli/run.sh).

## Webhooks

Deliveries are `POST` requests with a JSON body `{"id", "type", "data"}` (compact, sorted keys) and these headers:

| Header | Value |
|---|---|
| `X-Engineering-Influence-Signature` | `v1=` + hex `HMAC-SHA256(secret, "<timestamp>." + raw body)` |
| `X-Engineering-Influence-Timestamp` | Unix seconds |
| `X-Engineering-Influence-Event` / `-Event-Id` | event name and id |
| `X-Request-ID`, `traceparent` | present when the event has a correlation id |

A receiver must, in order: check the signature over the **raw bytes**, check the timestamp is
within 300 seconds, and refuse a signature it has already seen. Answer `2xx` to acknowledge;
anything else is retried and, after `max_attempts` (default 5), dead-lettered with an alert.
Destinations must be public `https` URLs; loopback, private ranges and cloud metadata addresses are refused.

[`examples/webhooks/receiver.py`](../examples/webhooks/receiver.py) is a stdlib receiver and
[`examples/webhooks/send_event.py`](../examples/webhooks/send_event.py) sends it valid, replayed,
tampered and stale deliveries. **No service emits webhooks yet**; the sender reproduces the
request the platform will make so you can build a receiver now.
