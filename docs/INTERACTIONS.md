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
| `GET /v1/runs` | key | Every saved run, as run summaries (the artifact list is empty here; `GET /v1/runs/{run_id}` lists a run's artifacts). `200`. Present only when the API is wired with run management. |
| `POST /v1/runs/{run_id}/resume` | key | Un-park a parked run and queue its current stage. `200` with the run; `404` unknown; `409` finished. Present only with run management. |
| `POST /v1/runs/{run_id}/cancel` | key | Stop a run for good. `200` with the run; `404` unknown. Present only with run management. |
| `POST /v1/runs/{run_id}/grant` | key | Give a run more budget and continue it. Body `{"micro_usd": N}` or none: a run waiting for consent gets exactly the amount it asked for (a different amount is `409`); a parked run needs `micro_usd`. `200` with the run; `404` unknown; `409` not waiting or parked, or changed meanwhile. Present only with run management. |
| `POST /v1/runs/{run_id}/deny` | key | Refuse a run's request for more budget; the run parks and nothing is queued. `200` with the run; `404` unknown; `409` not waiting for consent. Present only with run management. |
| `POST /v1/runs` | key | Start a book run from a brief (the brief contract v1, the same body `ei run create` reads as TOML). `201` with the new run, pending at its first stage; `422` when the body is not a brief or the kind is not one this build can start. Present only when the API is wired with run creation. |
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

`packages/engineering-influence-sdk` is a thin typed wrapper over `httpx` for the operations the API
has: starting a pipeline, creating a book run from a brief (`create_run`), and listing, resuming and cancelling runs
(`list_runs`, `resume_run`, `cancel_run`). It ships in this repository
and in each release.

```python
from engineering_influence_sdk import EngineeringInfluenceClient

client = EngineeringInfluenceClient("http://127.0.0.1:8000", api_key)
started = client.start_pipeline(
    "sample-essay", "A Sample Essay", ("Claims must be supported by evidence.",), ("thesis", "book")
)
run = client.create_run(
    {
        "schema_version": 1,
        "kind": "nonfiction",
        "idea": "Windowsill herbs",
        "budget_micro_usd": 5000000,
    }
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
| `list_runs` | none | every saved run as run summaries (present only with run management) |
| `resume_run` | `run_id` | the run after un-parking it (present only with run management) |
| `cancel_run` | `run_id` | the run after cancelling it (present only with run management) |
| `create_run` | `brief` (an object: the brief contract v1) | the new run as a `RunSummaryV1`, pending at its first stage. Present only when the server is built with a run creator |

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
ei run status|resume|cancel|export RUN_ID
ei run create BRIEF.TOML
ei run runs
ei book [--root DIR] audit|build|epub|covers|qa|package|publish …
ei book create --kind nonfiction|novel IDEA --budget-usd N --out DIR --profile FILE [--resume]
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
ei plugins search INDEX [TEXT]
ei plugins fetch INDEX NAME [--output DIR]
```

| Command | What it does | Exit status |
|---|---|---|
| `ei pipeline start` | Validates a project and prints the result as JSON. In-memory only: it does not queue work on the stack. `--stage` defaults to `thesis`. | `0`; `2` on a usage error |
| `ei serve api` / `worker` | Runs the API or the worker from `EI_*` settings. | `2` and one line naming the bad variable; never a traceback |
| `ei db upgrade` | Applies the database migrations to `EI_DATABASE_URL` and prints the revision reached. Needs the `runtime` extra. | `0`; `1` extra missing; `2` and one line for a missing setting or an unreachable database |
| `ei run status RUN_ID` | Prints the run as one line of JSON (the same `RunSummaryV1` the API returns). Needs only `EI_DATABASE_URL`. | `0`; `1` unknown run; `2` setup trouble |
| `ei run create BRIEF.TOML` | Starts a book run from a brief file (TOML, the brief contract v1: `kind`, `idea`, `budget_micro_usd` and the optional keys). The run is saved pending with the brief's cap as its budget and its first stage is queued for the worker; a file that is not a brief, or a kind this build cannot start, is refused on one line and nothing is saved. Needs the database and the broker, like `resume`. |
| `ei run runs` | Lists every saved run, one line each: its id, status and current stage. Needs only the database. |
| `ei run resume RUN_ID` | Moves a parked run back to running and queues its current stage; on a run that is already running it only queues the stage again, which repairs a resume that died half-way. Reads `EI_DATABASE_URL` and `EI_RABBITMQ_URL`. | `0`; `1` unknown run, finished run or a run that kept changing; `2` setup trouble |
| `ei run cancel RUN_ID` | Stops a run for good; cancelling twice is fine, and a completed or failed run is refused. Needs only `EI_DATABASE_URL`. | same |
| `ei run grant RUN_ID [--micro-usd N]` | Gives a run more budget and continues it. A run waiting for consent gets exactly the amount it asked for (passing another amount is refused); a parked run needs `--micro-usd` and gets exactly that. The stage is queued. Needs `EI_DATABASE_URL` and `EI_RABBITMQ_URL`. | `0`; `1` the run is not waiting for consent or parked, or it changed while being answered; `2` setup trouble |
| `ei run deny RUN_ID` | Refuses a run's request for more budget. The run parks, and nothing is queued; it can be granted more later. Needs only `EI_DATABASE_URL`. | same |
| `ei run export RUN_ID DIRECTORY` | Writes what a run produced to a **new or empty** folder: the book as a project at the top (`books/<slug>.toml` and `src/chapter_NN.md`, as the book commands expect) and every other artifact under `run/` (the stage outputs and the `audit/` reports). It reads the run and changes nothing in it. Nothing is overwritten, and either every file is written or none is. A folder that holds anything is refused, as is a run that has stored nothing. Needs only `EI_DATABASE_URL`. | `0`; `1` unknown run, a run with nothing stored, or a folder that is not empty; `2` setup trouble |
| `ei book create --kind KIND IDEA --budget-usd N --out DIR --profile FILE` | **Makes a whole book from an idea, in this process, with nobody in the loop.** It runs every stage of the plan for the kind (brief to build; see [BOOKS_AND_KDP.md](BOOKS_AND_KDP.md)) with the models and search the environment names (`EI_STAGE_EXECUTOR` and its settings, as for a worker), then writes the book to `--out` (a new or empty folder): the project at the top (`books/`, `src/`) and every artifact under `run/`, so the finished PDF, EPUB, covers, listing and manifest are in `run/book/`, the readiness reports in `run/build/`, and `run/quality-report.json` says how it came out. `--budget-usd` has no default, and `--profile` (or `EI_AUTHOR_PROFILE`) is required, because the author's details are needed to typeset the book: both are checked **before anything is spent**. Optional: `--title`, `--audience`, `--target-words`, `--trim-size`, and `--strict-release` (fails the build on any release warning; needs `[pricing]` in the profile). The run is kept in a SQLite file in `OUT.state/` (`--state-dir` to move it), so a process that dies loses nothing that was paid for: `--resume` continues it, and a model call already made is replayed, not paid for again. When the run asks for more budget it stops and writes nothing; `--resume --approve-spend` grants exactly what it asked for. A failed run is final, but what it made is still written to `--out`. | `0` the book is written; `1` the run failed or a needed extra is missing; `2` the command could not start (a missing idea, kind, budget or profile, a bad profile, a folder that already holds a run); `3` the run stopped to ask for budget |
| `ei book …` | Audit, build and publish books (needs the `publishing` extra and, for PDFs, a TeX toolchain). `package SLUG` writes the KDP release bundle (`build/SLUG/release/kdp`, see [BOOKS_AND_KDP.md](BOOKS_AND_KDP.md#the-release-bundle)) and refuses a failing release. Reads `engineering-influence.toml` in `--root`. | `0` ok; `1` a build or audit failure; `2` bad arguments |
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
| `ei plugins search INDEX [TEXT]` | Lists the plugins in a marketplace index (a file on disk or an `https://` address), or those whose name or description has the text. May use a network for an `https://` index; installs nothing. See [PLUGINS.md](PLUGINS.md#marketplace-indexes). | `0`; `2` on a refusal |
| `ei plugins fetch INDEX NAME [--output DIR]` | Downloads one plugin file from an index, **checks its SHA-256 against the index's before reading it**, checks it is the plugin and version listed, and saves it as `NAME.toml` (never over an existing file). **Installs nothing:** it prints the `show` and `add` commands to run next. | `0`; `2` on a refusal, a hash that differs or a download that fails |
| `ei acp` | Serves the Agent Client Protocol (stable, version 1) over stdin and stdout, for an editor or agent client. Each line is one JSON-RPC message; only protocol messages go to stdout, and logs and errors go to stderr. Needs the `runtime` extra and `EI_DATABASE_URL`. See [Agent Client Protocol](#agent-client-protocol). | `0` when the input ends; `1` the runtime extra is missing; `2` setup trouble |

`python -m engineering_influence` is the same program. Walk-through: [`examples/cli/run.sh`](../examples/cli/run.sh).

## Agent Client Protocol

`ei acp` speaks the Agent Client Protocol, version 1 of the stable specification, so an editor or agent client can start book runs the way `ei run create` does. Only the parts below are implemented; anything else is refused with `ACP_METHOD_NOT_FOUND`.

- `initialize` agrees version 1, reports `loadSession: true` and no authentication methods.
- `session/load` takes a `sessionId` this agent stored, and an absolute `cwd`. It re-attaches the session, so a client can reconnect to a new `ei acp` process. It sends one `session/update` notice with the run's current state (if the session has a run), then replies with no result. A run that has finished is replayed but not followed.
- `session/new` takes an absolute `cwd` and returns a `sessionId`. `mcpServers` must be empty: this agent does not connect MCP servers yet.
- `session/prompt` takes text content blocks, joined by newlines and read as a brief in TOML, the same contract `ei run create` reads. The first prompt of a session starts its run, a second prompt in the same session is refused, and the turn ends with `stopReason: end_turn` once the run is saved and its first stage queued. The stages themselves run in the worker, not in the session. Before the turn ends the agent sends one `session/update` notice naming the run and its stage.
- `session/cancel` is a notification. It stops the session's run and gets no reply.

Sessions are stored in the database beside the runs, so any `ei acp` process can load one. A run outlives its session, so `ei run status RUN_ID` and `ei run cancel RUN_ID` still work after the client disconnects. The session store needs migration `0002`: run `ei db upgrade` first. While a session is open, the agent follows its run. Every second it reads the run's saved state, and it sends a `session/update` notice when the status or the stage changes, once per change. A finished run (completed, failed or cancelled) is reported once and then no longer followed; a parked run is still followed, because it can be resumed. A notice is written between replies and never inside one. A failed read is one line on stderr, and the following goes on. A run that would spend past its cap does not fail: its next model call is refused before it spends, and the run stops in `awaiting_consent` with the amount the call needs. An open session is asked, with a `session/request_permission` request that offers `grant` (allow exactly that amount) and `deny` (the run parks). The answer decides the run; a cancelled answer leaves it waiting. The same decision is available from the command line with `ei run grant` and `ei run deny` for any run, including one with no open session. A parked run waiting for no decision continues with `ei run grant RUN_ID --micro-usd N`.

Not yet implemented: MCP servers in a session.

Refusals are JSON-RPC errors: `-32700` for a line that is not JSON, `-32600` for a message that is not a JSON-RPC 2.0 request, `-32601` for a method this agent does not implement, and `-32602` for invalid parameters, including a prompt that is not valid TOML (`BRIEF_INVALID`) or a kind this build cannot start. An unexpected failure is `-32603` with the message `internal error`; only the exception's class name is written to stderr, because a message can carry a connection string.

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
