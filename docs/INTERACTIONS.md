# Interfaces reference

**BLUF:** Every interface drives the same thing, a book run that ends in a KDP-ready package, so learn one and you
know them all. To write one book, use the CLI (`ei book create`). To serve many, run the stack and call it over
REST, the SDK, MCP or the Agent Client Protocol. This page is the contract for each: requests, replies, flags,
exit codes and the error codes a caller meets most.

Every interface starts or drives the same thing: an autonomous book-writing run that ends in a
KDP-ready package ([details](BOOKS_AND_KDP.md)). Six interfaces sit over the same controller layer, so they accept the same request and
return the same result. Pick by who is calling.

| Interface | Process | Authenticated | Reaches the stack |
|---|---|---|---|
| [REST API](#rest-api) | `ei serve api` | API key | yes |
| [Python SDK](#python-sdk) | your code | API key | yes (it calls the REST API) |
| [MCP server](#mcp-server) | stdio child process | no (local only) | yes with `ei serve mcp`; the example server is in-memory |
| [CLI](#cli) | `ei` | no (local only) | `serve`, `run` and `book` yes; `pipeline start` no |
| [Agent Client Protocol](#agent-client-protocol) | `ei acp` (stdio) | no (local only) | yes |
| [Webhooks](#webhooks) | outbound HTTPS | HMAC signature | yes |

## One counter, several windows

> **Daniel:** Six ways in. REST, an SDK, MCP, a CLI, ACP, webhooks. Do I have to learn six products?
>
> **Professor Feynman:** Think of a bank. You can walk to the counter, use the machine outside, or phone. How many
> banks is that?
>
> **Daniel:** One. The same account, the same rules, whichever way I ask.
>
> **Professor Feynman:** Same here. Each interface is a window; behind all of them is one counter, the controller
> layer. A window translates your request and hands it over. The rules about runs and money live behind the
> counter. A window may be stricter, never looser: the MCP window caps a run at five dollars and cannot grant more
> budget unless you allow it.
>
> **Daniel:** So if the API refuses a budget above the operator's limit, the MCP tool refuses it too.
>
> **Professor Feynman:** For the same reason, though not in the same words. REST gives you a code,
> `BUDGET_ABOVE_LIMIT`. MCP and ACP give you the message. Now the limit of the picture: not every window is open
> to the street. The REST API checks a key. The CLI, the MCP server and ACP check nothing, because they are meant
> to run on your own machine, so they must never be put on a network.
>
> **Daniel:** Then I pick the window by who is calling, and I read one set of rules. I will start at the table
> below.

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

A **book run** starts from a **brief** instead (`POST /v1/runs`, `ei run create`, the SDK and MCP `create_run`, and
`ei book create`, which builds one from its flags). Any key not in this table is refused:

| Field | Rules |
|---|---|
| `schema_version` | `1`, the default |
| `kind` | required: `nonfiction` or `novel` |
| `idea` | required, not blank |
| `budget_micro_usd` | required: a whole number above 0, in millionths of a dollar |
| `title_hint`, `audience` | optional, not blank |
| `target_words` | optional, above 0 |
| `trim_size` | optional: `5x8`, `5.5x8.5` or `6x9` |
| `language` | default `en` |
| `inputs` | at most 8 of `{name, text, origin}`; `origin` is `pasted` (the default) or `file`; names unique; 200,000 characters in all |
| `violence` | novels only: `none`, `mild`, `moderate` or `graphic` |
| `heat` | novels only: `none`, `sweet`, `steamy` or `explicit` |

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
| 409 | `RUN_FINISHED` | The run is completed, failed or cancelled, so it cannot be resumed or cancelled | no |
| 409 | `RUN_CHANGED` | The run changed while it was being answered | yes |
| 409 | `CONSENT_NOT_PENDING` | A grant or a denial for a run that is not waiting for one | no |
| 422 | `BUDGET_ABOVE_LIMIT` | The budget asked for is above the operator's limit for one run | no, ask for less |
| 422 | `OUTSTANDING_BUDGET_EXCEEDED` | All unfinished runs together would hold more unspent budget than the operator allows | later, when runs finish |
| 422 | `RUN_KIND_UNSUPPORTED` | This build cannot start that kind of book | no |
| 422 | `RUN_REVISION_INVALID` | A revision is numbered from 1 to 9 | no |
| 503 | `SECRET_MISSING` | A required secret is not configured | after fixing configuration |

These are the codes a caller of the API meets most. Every code the package can raise is frozen in
`tests/contracts/snapshots/error_codes.json`; most of the rest stop a process at start and are described beside the
setting they concern in [CONFIGURATION.md](CONFIGURATION.md).

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
(`list_runs`, `resume_run`, `cancel_run`), answering a run's request for more budget (`grant_run`, `deny_run`), and reading a run (`get_run`) and the files it stored (`get_artifact`, as bytes). It ships in this repository
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
status = client.get_run(run["run_id"])  # status, stage, budget and the names of its artifacts
pdf = client.get_artifact(run["run_id"], "book/my-book.pdf")  # bytes, once the run has built it
client.close()
```

`AsyncEngineeringInfluenceClient` has the same signature with `await` (and `await client.close()`).
Any non-2xx answer raises `httpx.HTTPStatusError`; the API's error document is in
`error.response`. Scripts: [`examples/sdk/`](../examples/sdk).

## MCP server

`ei serve mcp` runs the stack's MCP server over stdio, for an MCP host (Claude Desktop, an agent runtime) to start as a child
process. It needs `EI_DATABASE_URL` and `EI_RABBITMQ_URL` like the API (and a migrated database: `ei db upgrade`), offers the
same runs the REST API does, and needs no API key because the host that starts it already holds the stack's credentials. Standard
output carries the protocol, so logs (JSON) go to standard error only. A host entry looks like:

```json
{"mcpServers": {"engineering-influence": {"command": "ei", "args": ["serve", "mcp"],
  "env": {"EI_DATABASE_URL": "postgresql+psycopg://...", "EI_RABBITMQ_URL": "amqp://..."}}}}
```

**The server does not offer `grant_run` or `deny_run` unless the operator sets `EI_MCP_ALLOW_SPEND=1`.** Granting a run budget is
the person's decision, and an agent that could raise its own run's cap would have no cap. Without the setting an agent can
start a run, watch it, resume or cancel it and read what it made; a run that needs more budget shows as `awaiting_consent` in
`get_run`, and the person answers it with `ei run grant`.

**A run an agent starts is held to `EI_MCP_MAX_RUN_BUDGET_MICRO_USD`** (default 5,000,000, five dollars): `create_run` refuses a brief
with a bigger `budget_micro_usd` (`BUDGET_ABOVE_LIMIT`), so an agent cannot open a run with a cap of its own choosing. That bounds one
run, **not how many runs an agent starts**. For that, set the stack-wide ceilings below (`EI_MAX_OUTSTANDING_BUDGET_MICRO_USD`), which
hold every way into the stack, MCP included.

`McpApplication(controller).build()` returns an `MCPServer` (from the official `mcp` 2.x SDK)
with one tool when built bare, and the rest when it is given the services (`grant_run` and `deny_run` only with
`allow_spend=True`):

| Tool | Arguments | Returns |
|---|---|---|
| `start_pipeline` | `slug`, `title`, `postulates` (list), `stages` (list) | `{"job_id", "project_slug"}` |
| `list_runs` | none | every saved run as run summaries (present only with run management) |
| `resume_run` | `run_id` | the run after un-parking it (present only with run management) |
| `cancel_run` | `run_id` | the run after cancelling it (present only with run management) |
| `get_run` | `run_id` | a run's `RunSummaryV1`: status, stage, budget and the names of its stored artifacts (present only when the server is built with a run reader) |
| `read_artifact` | `run_id`, `name` (such as `book/my-book.pdf`) | `{name, bytes, encoding, content}`: the text when the file is UTF-8, base64 when it is not. A file over 1 MiB is refused (`ARTIFACT_TOO_LARGE`) and the message names the `GET /v1/runs/{id}/artifacts/{name}` address that downloads any size (present with `get_run`) |
| `create_run` | `brief` (an object: the brief contract v1) | the new run as a `RunSummaryV1`, pending at its first stage. Present only when the server is built with a run creator |
| `grant_run` | `run_id`, optional `micro_usd` | the run after allowing it more budget. Present only with `allow_spend=True` (`ei serve mcp` sets it from `EI_MCP_ALLOW_SPEND`) |
| `deny_run` | `run_id` | the run after refusing it more budget; it parks. Present only with `allow_spend=True` |

[`examples/mcp/server.py`](../examples/mcp/server.py) is the bare server over in-memory adapters, for trying the tool shapes
without a stack, and [`examples/mcp/client.py`](../examples/mcp/client.py) is a client that spawns it, lists the tools and calls one.
The server is a local process: it is not authenticated, so do not expose it on a network.

## CLI

```text
ei --version
ei pipeline start --slug S --title T --postulate P [--postulate P …] [--stage STAGE …]
ei serve api|worker|mcp
ei db upgrade
ei run status|resume|cancel RUN_ID
ei run export RUN_ID DIRECTORY
ei run create BRIEF.TOML
ei run grant RUN_ID [--micro-usd N]
ei run deny RUN_ID
ei doctor (--ready | --models | --search | --local) [--author-profile FILE] [--catalog FILE] [--profiles FILE] [--query Q] [--probe]
ei acp
ei run runs
ei book [--root DIR] audit [--json] [--strict-release] [SLUG …]
ei book [--root DIR] build [--hardcover] [--tex-only] [--no-verify] [SLUG …]
ei book [--root DIR] epub [--tex-only] [--no-verify] [SLUG …]
ei book [--root DIR] covers [--preview] [--hardcover-pdf PATH] [SLUG …]
ei book [--root DIR] qa PDF [--output DIR] [--dpi N]
ei book [--root DIR] package [SLUG …]
ei book [--root DIR] publish [--audit-only] [--no-render] [--strict-release] [--dpi N] [--report-dir DIR] [SLUG …]
ei book create --kind nonfiction|novel IDEA --budget-usd N --out DIR --profile FILE [--source DIR] [--bible DIR] [--resume] [--no-keep-awake]
ei evaluate --out DIR --budget-usd N --judge-budget-usd N [--profile FILE] [--baseline FILE] [--set FILE] [--rubric FILE] [--release LABEL]
ei tools add [--lock PATH] [--env VAR …] [--replace] NAME -- COMMAND [ARG …]
ei tools add [--lock PATH] [--bearer-env VAR] [--replace] --url URL NAME
ei tools list [--lock PATH]
ei tools verify [--lock PATH] [NAME …]
ei tools grant [--lock PATH] NAME STAGE TOOL …
ei tools revoke [--lock PATH] NAME STAGE [TOOL …]
ei skills add [--lock PATH] [--replace] FILE
ei skills import SOURCE (--stage STAGE [--stage STAGE …] | --reference) [--section TITLE …] [--name NAME] [--version N] [--out FILE]
ei skills enable|disable [--lock PATH] NAME STAGE
ei skills remove [--lock PATH] NAME
ei skills list|verify [--lock PATH]
ei plugins show FILE
ei plugins import FOLDER [--name NAME] [--version N] [--out FILE]
ei plugins add [--lock PATH] [--skill-lock PATH] FILE
ei plugins list [--lock PATH]
ei plugins verify|remove … [--lock PATH] [--skill-lock PATH]
ei plugins search INDEX [TEXT]
ei plugins fetch INDEX NAME [--output DIR]
```

| Command | What it does | Exit status |
|---|---|---|
| `ei pipeline start` | Validates a project and prints the result as JSON. In-memory only: it does not queue work on the stack. `--stage` defaults to `thesis`. | `0`; `2` on a usage error |
| `ei serve api` / `worker` / `mcp` | Runs the API, the worker or the stdio MCP server from `EI_*` settings (see [MCP server](#mcp-server)). | `0` on a clean stop; `1` an extra is missing (the message names which); `2` and one line naming the bad variable; never a traceback |
| `ei doctor` | Checks that this installation is ready, never asking a paid model to answer. **`--ready` answers whether this machine can make a book now**: the extras, the tools the `build` stage calls, the author profile (`--author-profile FILE`, else `EI_AUTHOR_PROFILE`), then the local model and the search, every check made and printed in one run. The others check one thing: `--models` the model profiles and catalog (`--probe` adds one model-list request per profile), `--search` one real search through each configured provider, `--local` the free local model. See [MODEL_PROFILES.md](MODEL_PROFILES.md) and [LOCAL_MODEL.md](LOCAL_MODEL.md). | `0` ready; `1` a check failed; `2` setup trouble |
| `ei db upgrade` | Applies the database migrations to `EI_DATABASE_URL` and prints the revision reached. Needs the `runtime` extra. | `0`; `1` extra missing; `2` and one line for a missing setting or an unreachable database |
| `ei run status RUN_ID` | Prints the run as one line of JSON (the same `RunSummaryV1` the API returns). Needs only `EI_DATABASE_URL`. | `0`; `1` unknown run, or the `runtime` extra is missing (true of every `ei run` command); `2` setup trouble |
| `ei run create BRIEF.TOML` | Starts a book run from a brief file (TOML, the brief contract v1: `kind`, `idea`, `budget_micro_usd` and the optional keys). The run is saved pending with the brief's cap as its budget and its first stage is queued for the worker; a file that is not a brief, or a kind this build cannot start, is refused on one line and nothing is saved. Needs the database and the broker, like `resume`. | `0`; `1` a file that cannot be read or is not a brief, or a kind this build cannot start; `2` setup trouble, or a budget an operator ceiling refuses |
| `ei run runs` | Lists every saved run, one line each: its id, status and current stage. Needs only the database. | `0`; `2` setup trouble |
| `ei run resume RUN_ID` | Moves a parked run back to running and queues its current stage; on a run that is already running it only queues the stage again, which repairs a resume that died half-way. Reads `EI_DATABASE_URL` and `EI_RABBITMQ_URL`. | `0`; `1` unknown run, finished run or a run that kept changing; `2` setup trouble |
| `ei run cancel RUN_ID` | Stops a run for good; cancelling twice is fine, and a completed or failed run is refused. Needs only `EI_DATABASE_URL`. | same |
| `ei run grant RUN_ID [--micro-usd N]` | Gives a run more budget and continues it. A run waiting for consent gets exactly the amount it asked for (passing another amount is refused); a parked run needs `--micro-usd` and gets exactly that. The stage is queued. Needs `EI_DATABASE_URL` and `EI_RABBITMQ_URL`. | `0`; `1` the run is not waiting for consent or parked, or it changed while being answered; `2` setup trouble, or a grant an operator ceiling refuses |
| `ei run deny RUN_ID` | Refuses a run's request for more budget. The run parks, and nothing is queued; it can be granted more later. Needs only `EI_DATABASE_URL`. | same |
| `ei run export RUN_ID DIRECTORY` | Writes what a run produced to a **new or empty** folder: the book as a project at the top (`books/<slug>.toml` and `src/chapter_NN.md`, as the book commands expect) and every other artifact under `run/` (the stage outputs and the `audit/` reports). It reads the run and changes nothing in it. Nothing is overwritten, and either every file is written or none is. A folder that holds anything is refused, as is a run that has stored nothing. Needs only `EI_DATABASE_URL`. | `0`; `1` unknown run, a run with nothing stored, or a folder that is not empty; `2` setup trouble |
| `ei book create --kind KIND IDEA --budget-usd N --out DIR --profile FILE` | **Makes a whole book from an idea, in this process, with nobody in the loop.** It runs every stage of the plan for the kind (brief to build; see [BOOKS_AND_KDP.md](BOOKS_AND_KDP.md)) with the models and search the environment names (`EI_STAGE_EXECUTOR` and its settings, as for a worker), then writes the book to `--out` (a new or empty folder): the project at the top (`books/`, `src/`) and every artifact under `run/`, so the finished PDF, EPUB, covers, listing and manifest are in `run/book/`, the readiness reports in `run/build/`, and `run/quality-report.json` says how it came out. `--budget-usd` has no default, and `--profile` (or `EI_AUTHOR_PROFILE`) is required, because the author's details are needed to typeset the book: both are checked **before anything is spent**. **Before anything is spent it says what the book is expected to cost with the priced model** (`estimate: about 6.00 USD for the whole book (4.00 before editing), against a budget of 5.00: tight`) and grades the budget: `short` (below what the essential stages are expected to cost: refused, with the budget that would do, unless `--ignore-estimate`), `tight` (may stop to ask for more), `lean` (an editing pass that runs out of money is skipped) or `ample`. With the free local model the estimate is still printed, from a price of zero; with the offline placeholder there is no estimate. Optional: `--title`, `--audience`, `--target-words`, `--trim-size`, `--source DIR` (a folder of `.md` or `.txt` source files, numbered in name order and kept in the run as `source/NNN.md`; an empty or missing folder is refused before anything is spent), `--bible DIR` (a screenplay run only: a bible folder of TOML cards, checked before anything is spent and kept in the run as `bible/kind/id.json`; each scene is handed the cards it names, by name or id; another kind of run is refused before anything is saved), `--mode book|audiobook` (`audiobook` narrates a finished nonfiction manuscript given with `--source`, one chapter per file: the outline is built from the chapters, with no model call, and the chapters are narrated by the narrator `EI_NARRATOR` names; the cost estimate shown is the whole book's, not the audiobook's), `--stop-after STAGE` (the run ends after that stage and runs nothing after it, for example `scene_cards`; a stage the kind of run does not have is refused before anything is saved), `--previous-lock FILE` (a screenplay run only: the `shooting_lock.json` of an earlier run, read as text and kept in the run as `previous_shooting_lock.json`, so every scene keeps the number it was given; another kind of run, or a build that cannot keep run files, is refused before anything is saved), `--previous-script FILE` (a screenplay run only: the earlier run's `shooting_script.fountain`, read as text and kept as `previous_shooting_script.fountain`, the baseline the changed scenes are marked against; see [SCREENPLAYS.md](SCREENPLAYS.md)), `--revision N` (with `--previous-script`: this run's revision number, 1 for Blue through 9; any other number is refused before anything is saved), `--ignore-estimate`, and `--strict-release` (fails the build on any release warning; needs `[pricing]` in the profile). The run is kept in a SQLite file in `OUT.state/` (`--state-dir` to move it), so a process that dies loses nothing that was paid for: `--resume` continues it, and a model call already made is replayed, not paid for again. When the run asks for more budget it stops and writes nothing; `--resume --approve-spend` grants exactly what it asked for. A failed run is final, but what it made is still written to `--out`. | `0` the book is written; `1` the run failed or a needed extra is missing; `2` the command could not start (a missing idea, kind, budget or profile, a bad profile, a folder that already holds a run, or a budget below the estimate without `--ignore-estimate`); `3` the run stopped to ask for budget, or parked because the provider is at capacity |
| `ei book …` | Audit, build and publish books (needs the `publishing` extra and, for PDFs, a TeX toolchain). With no `SLUG` a subcommand works on every configured book. `--dpi` defaults to 90, and below 36 is refused (exit `2`). `package SLUG` writes the KDP release bundle (`build/SLUG/release/kdp`, see [BOOKS_AND_KDP.md](BOOKS_AND_KDP.md#the-release-bundle)) and refuses a failing release. Reads `engineering-influence.toml` in `--root`. | `0` ok; `1` a build or audit failure; `2` bad arguments |
| `ei evaluate --out DIR --budget-usd N --judge-budget-usd N` | **Spends real money.** Makes every book of the evaluation set (`evaluation/set.toml`) with the stack's own pipeline, has the judge model (`EI_EVAL_JUDGE_PROFILE`) score each finished book on the rubric (`evaluation/rubric.toml`), and checks the release against the 1.0 bar: every book finished, every dimension's mean at least 3.5, none fallen by more than 0.2 from `--baseline`, and the cost estimate within 30% of what was spent. Refuses to start unless `EI_ALLOW_PAID=1`. `--budget-usd` is the most each book may spend and `--judge-budget-usd` the most the judge may spend in all; neither has a default. `--out` must be a new or empty folder; `evaluation.json` is written there beside the books, and is the next release's baseline. See [EVALUATION.md](EVALUATION.md). | `0` the release meets the bar; `1` it does not (each reason is printed) or a needed extra is missing; `2` the command could not run (not paid for, a bad budget, a folder that is not empty, a bad rubric or set, no judge named, or a judge that failed) |
| `ei tools add NAME -- COMMAND …` | **Runs** an MCP server once, under limits and with a bare environment, and records what it is in the tool lock: its files' hashes, the name and version it reported and a hash of its tools. Options go before `NAME`. Refuses a launcher (`npx`, `uvx`, `docker`, …) and a relative script path before anything is run. See [TOOL_LOCK.md](TOOL_LOCK.md). | `0`; `2` on a refusal or an unusable lock |
| `ei tools add --url URL NAME` | **Contacts** a remote MCP server once and records its address, the name and version it reported and a hash of its tools. Only https to a public address is allowed; the token, if any, is the variable named by `--bearer-env`. The server's code is not locked, only what it advertises. See [TOOL_LOCK.md](TOOL_LOCK.md#remote-servers-http). | `0`; `2` on a refusal or an unusable lock |
| `ei tools list` | Shows the locked servers. Starts nothing. | `0`; `2` an unusable lock |
| `ei tools verify [NAME …]` | **Runs** each locked server (a server whose files changed is not started) and compares it with the lock. | `0` all match; `1` one does not; `2` setup trouble or an unknown name |
| `ei tools grant NAME STAGE TOOL …` | Lets a stage call some of a locked server's tools: edits the lock, runs nothing. The tools must be ones the lock lists; no wildcards. A stage with no grant gets none. | `0`; `2` on a refusal or an unusable lock |
| `ei tools revoke NAME STAGE [TOOL …]` | Takes tools back from a stage, or all of them if none are named. A stage with no grant is an error. | same |
| `ei skills add FILE` | Reads a skill file once, checks it strictly (no key but `name`, `version`, `description` and `[parts]`; no invisible or control characters) and records the SHA-256 of its bytes in the skill lock, keeping a copy in `skills/` beside it. **Enables nothing**; prints each part so you can read what will be added to prompts. `--replace` locks it again and clears its stages. Starts nothing. See [SKILLS.md](SKILLS.md). | `0`; `2` on a refusal or an unusable lock |
| `ei skills import SOURCE …` | Turns a `SKILL.md` (a `---` block of `key: value` lines, then markdown) into a skill file (`--out`) and prints what it kept and set aside, to be reviewed and then added. It does not touch the lock. See [SKILLS.md](SKILLS.md#importing-a-skillmd). | `0`; `2` an unreadable source or a bad option |
| `ei skills enable NAME STAGE` | Lets a stage's prompt carry a skill: checks the file against its hash and refuses a stage the skill has no text for. At most four skills per stage. | same |
| `ei skills disable NAME STAGE` | Stops a stage carrying a skill. | same |
| `ei skills remove NAME` | Unlocks a skill and deletes its copy. | same |
| `ei skills list` | Shows the locked skills with their short hash and stages. Reads no skill file. | `0`; `2` an unusable lock |
| `ei skills verify` | Re-hashes every locked skill, enabled or not, against the lock. | `0` all match; `1` one does not; `2` setup trouble |
| `ei plugins show FILE` | Reads a plugin file and says what installing it would do: its skills (with their text), and the `ei tools add` command for each server. Changes nothing. See [PLUGINS.md](PLUGINS.md). | `0`; `2` on a refusal |
| `ei plugins import FOLDER` | Turns a plugin folder written for Claude Code into a bundle file (`--out`), to be shown and then added. It does not touch the lock. See [PLUGINS.md](PLUGINS.md). | `0`; `2` an unreadable folder or a bad option |
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

Refusals are JSON-RPC errors: `-32700` for a line that is not JSON, `-32600` for a message that is not a JSON-RPC 2.0 request, `-32601` for a method this agent does not implement, and `-32602` for invalid parameters, including a prompt that is not valid TOML (`BRIEF_INVALID`) or a kind this build cannot start. An unexpected failure is `-32603` with the message `internal error`; only the exception's class name is written to stderr, because a message can carry a connection string. A refusal with no JSON-RPC code of its own, such as a brief above `EI_MAX_RUN_BUDGET_MICRO_USD`, is also `-32603`, with the refusal's own message.

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

### Keeping the computer awake during `ei book create`

A book takes hours on a local model, so `ei book create` holds the computer awake for the whole run. On macOS it runs
`caffeinate -i` for the life of the process; on Linux it runs `systemd-inhibit` around a `sleep`. Pass `--no-keep-awake`
to turn that off. Where neither tool is found, the run continues and a warning says the computer may sleep; a run that
is stopped by sleep is continued with `--resume` and pays for nothing twice.

The hold prevents idle sleep. A closed laptop lid on battery still sleeps on both platforms, and nothing the program
does can prevent that: keep the lid open, or plug in, for a long run.
