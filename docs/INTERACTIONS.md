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
| `GET /v1/runs/{run_id}` | key | A book run: status, stage, plan, budget in micro-dollars, issues and the names of its artifacts. `200` with a `RunSummaryV1`. |
| `GET /v1/runs/{run_id}/artifacts/{name}` | key | One stored artifact, byte for byte, as `application/octet-stream` with `nosniff` and `no-store`. Names may contain `/`. |
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
| 404 | `RUN_NOT_FOUND` | No run has that id | no |
| 404 | `ARTIFACT_NOT_FOUND` | The run has no such artifact; a name that could never be stored (absolute, `..`, backslash) gets the same answer | no |
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

`McpApplication(controller).build()` returns an `MCPServer` (from the official `mcp` 2.x SDK)
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
ei db upgrade
ei run status|resume|cancel RUN_ID
ei book [--root DIR] audit|build|epub|covers|qa|publish …
ei tools add [--lock PATH] [--env VAR …] [--replace] NAME -- COMMAND [ARG …]
ei tools add [--lock PATH] [--bearer-env VAR] [--replace] --url URL NAME
ei tools list [--lock PATH]
ei tools verify [--lock PATH] [NAME …]
ei tools grant [--lock PATH] NAME STAGE TOOL …
ei tools revoke [--lock PATH] NAME STAGE [TOOL …]
ei skills add [--lock PATH] [--replace] FILE
ei skills enable|disable [--lock PATH] NAME STAGE
ei skills remove [--lock PATH] NAME
ei skills list|verify [--lock PATH]
ei plugins show FILE
ei plugins add [--lock PATH] [--skill-lock PATH] FILE
ei plugins list [--lock PATH]
ei plugins verify|remove … [--lock PATH] [--skill-lock PATH]
```

| Command | What it does | Exit status |
|---|---|---|
| `ei pipeline start` | Validates a project and prints the result as JSON. In-memory only: it does not queue work on the stack. `--stage` defaults to `thesis`. | `0`; `2` on a usage error |
| `ei serve api` / `worker` | Runs the API or the worker from `EI_*` settings. | `2` and one line naming the bad variable; never a traceback |
| `ei db upgrade` | Applies the database migrations to `EI_DATABASE_URL` and prints the revision reached. Needs the `runtime` extra. | `0`; `1` extra missing; `2` and one line for a missing setting or an unreachable database |
| `ei run status RUN_ID` | Prints the run as one line of JSON (the same `RunSummaryV1` the API returns). Needs only `EI_DATABASE_URL`. | `0`; `1` unknown run; `2` setup trouble |
| `ei run resume RUN_ID` | Moves a parked run back to running and queues its current stage; on a run that is already running it only queues the stage again, which repairs a resume that died half-way. Reads `EI_DATABASE_URL` and `EI_RABBITMQ_URL`. | `0`; `1` unknown run, finished run or a run that kept changing; `2` setup trouble |
| `ei run cancel RUN_ID` | Stops a run for good; cancelling twice is fine, and a completed or failed run is refused. Needs only `EI_DATABASE_URL`. | same |
| `ei book …` | Audit, build and publish books (needs the `publishing` extra and, for PDFs, a TeX toolchain). Reads `engineering-influence.toml` in `--root`. | `0` ok; `1` a build or audit failure; `2` bad arguments |
| `ei tools add NAME -- COMMAND …` | **Runs** an MCP server once, under limits and with a bare environment, and records what it is in the tool lock: its files' hashes, the name and version it reported and a hash of its tools. Options go before `NAME`. Refuses a launcher (`npx`, `uvx`, `docker`, …) and a relative script path before anything is run. See [TOOL_LOCK.md](TOOL_LOCK.md). | `0`; `2` on a refusal or an unusable lock |
| `ei tools add --url URL NAME` | **Contacts** a remote MCP server once and records its address, the name and version it reported and a hash of its tools. Only https to a public address is allowed; the token, if any, is the variable named by `--bearer-env`. The server's code is not locked, only what it advertises. See [TOOL_LOCK.md](TOOL_LOCK.md#remote-servers-http). | `0`; `2` on a refusal or an unusable lock |
| `ei tools list` | Shows the locked servers. Starts nothing. | `0`; `2` an unusable lock |
| `ei tools verify [NAME …]` | **Runs** each locked server (a server whose files changed is not started) and compares it with the lock. | `0` all match; `1` one does not; `2` setup trouble or an unknown name |
| `ei tools grant NAME STAGE TOOL …` | Lets a stage call some of a locked server's tools: edits the lock, runs nothing. The tools must be ones the lock lists; no wildcards. A stage with no grant gets none. | `0`; `2` on a refusal or an unusable lock |
| `ei tools revoke NAME STAGE [TOOL …]` | Takes tools back from a stage, or all of them if none are named. A stage with no grant is an error. | same |
| `ei skills add FILE` | Reads a skill file once, checks it strictly (no key but `name`, `version`, `description` and `[parts]`; no invisible or control characters) and records the SHA-256 of its bytes in the skill lock, keeping a copy in `skills/` beside it. **Enables nothing**; prints each part so you can read what will be added to prompts. `--replace` locks it again and clears its stages. Starts nothing. See [SKILLS.md](SKILLS.md). | `0`; `2` on a refusal or an unusable lock |
| `ei skills enable NAME STAGE` | Lets a stage's prompt carry a skill: checks the file against its hash and refuses a stage the skill has no text for. At most four skills per stage. | same |
| `ei skills disable NAME STAGE` | Stops a stage carrying a skill. | same |
| `ei skills remove NAME` | Unlocks a skill and deletes its copy. | same |
| `ei skills list` | Shows the locked skills with their short hash and stages. Reads no skill file. | `0`; `2` an unusable lock |
| `ei skills verify` | Re-hashes every locked skill, enabled or not, against the lock. | `0` all match; `1` one does not; `2` setup trouble |
| `ei plugins show FILE` | Reads a plugin file and says what installing it would do: its skills (with their text), and the `ei tools add` command for each server. Changes nothing. See [PLUGINS.md](PLUGINS.md). | `0`; `2` on a refusal |
| `ei plugins add FILE` | Locks the bundle's skills (each enabled for **no** stage), keeps a copy of the bundle, and records its SHA-256 in the plugin lock. **Starts nothing, contacts nothing, grants nothing:** the commands for its servers are printed for you to review and run. Refuses a plugin that is installed or skills that are already locked, before writing anything. | `0`; `2` on a refusal or an unusable lock |
| `ei plugins list` | Shows the installed plugins, the skills installed and the servers described. | `0`; `2` an unusable lock |
| `ei plugins verify` | Re-hashes each kept bundle and checks that its skills are still locked as installed. | `0` all match; `1` one does not; `2` setup trouble |
| `ei plugins remove NAME` | Uninstalls a plugin and the skills it installed that are still exactly what it installed; a skill locked again since is left. | `0`; `2` on a refusal |

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
