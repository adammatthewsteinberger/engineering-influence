# Configuration

**BLUF:** Settings come from environment variables, a few files those variables name, and command-line flags.
Every security setting fails closed: a missing or weak value stops the process instead of opening it. To write one
book you need only an author profile. To run the stack you need a database URL, a broker URL and API keys. Every
`EI_*` variable the code reads is in one index on this page.

Book configuration is intentionally separate from author profile configuration.
The public package accepts a project title, slug, governing postulates and the
stages to run. Target formats and an autonomy policy are planned, not accepted yet. Private books repositories may add a profile that
fills the governing-postulates slot without changing the public domain model.

The book config, the brief and the run summary schemas are versioned under `contracts/` and frozen by snapshot
tests ([COMPATIBILITY.md](COMPATIBILITY.md)).

## Why a missing setting stops everything

> **Daniel:** I left the API keys blank to try it quickly and the server refused to start. Most tools just run
> open in that case. Why so strict?
>
> **Professor Feynman:** What does a shop do when the lock on the front door is broken?
>
> **Daniel:** A careless one props the door open. A careful one stays shut until the lock is fixed.
>
> **Professor Feynman:** That is fail closed. An unset key could mean 'I forgot' or 'I want no security', and a
> program cannot tell which. So this one assumes you forgot, and stays shut. It also tells you which variable is
> wrong, and never prints the value.
>
> **Daniel:** Annoying on day one.
>
> **Professor Feynman:** And it is the reason there is no day when you discover the door was open all along. The
> picture has a limit: a closed shop loses customers, and a stopped worker loses time. So a setting that is merely
> optional, like the log level, has a default instead.
>
> **Daniel:** Required things stop the process, optional things have defaults, and the error names the variable. I
> will look mine up in the index.

## Security settings

Every security control fails closed: a missing or weak setting stops the service
instead of opening it.

| Setting | Meaning |
|---|---|
| `EI_API_KEYS` | Comma-separated API keys, each at least 24 characters. Required: the REST API cannot be built without a guard, and the guard cannot be built without a key. |
| Rate limits | `TokenBucketRateLimiter(burst, per_second)`. A client address is limited before its key is compared, then each key has its own budget. |
| Webhook secret | Passed to `WebhookDelivery.deliver` and `WebhookSigner`; read it with `EnvSecretProvider().require(name)` so an absent secret raises `SECRET_MISSING` (HTTP 503). |
| Webhook tolerance | `SignedRequestVerifier(tolerance_seconds=300)`: deliveries older or newer than this are refused. |

Clients send the key as `Authorization: Bearer <key>` (what the SDK does) or
`X-API-Key: <key>`.

## Webhook signature (v1)

`X-Engineering-Influence-Signature: v1=<hex>` is `HMAC-SHA256(secret, "<timestamp>." + body)`,
and `X-Engineering-Influence-Timestamp` carries the Unix time. Verify the raw
bytes, not re-serialised JSON. A receiver must check the signature, the
timestamp window and replays, in that order: `SignedRequestVerifier` does.

## Outbound destinations

`WebhookDelivery` requires an `OutboundUrlPolicyInterface`. `PublicHttpsUrlPolicy`
allows only `https` URLs without embedded credentials whose every resolved
address is publicly routable, which blocks loopback, private ranges and cloud
metadata addresses. It resolves the name when called, so **webhook delivery is still open to DNS
rebinding**; route deliveries to untrusted URLs through an egress proxy as well. `fetch_url` and remote
MCP servers do not have this gap: they go through `PublicHttpsUrlPinner`, which resolves once and connects to
the address it checked.

## Not covered yet

- No upload or inbound-webhook HTTP route exists, so `AttachmentUploadInspector`
  and `SignedRequestVerifier` are building blocks that no endpoint uses yet.
- The MCP server (stdio) and the CLI are local processes and are not
  authenticated; do not expose them on a network.
- Request body size limits, TLS termination, and API key rotation are
  deployment concerns for the reverse proxy and are not implemented here.
- `AttachmentUploadInspector` and `ConfinedPathGuard` exist but no route uses them yet, because the service accepts no uploads.

## Observability

Wire these adapters in the process entry point. Nothing is global except what
`vibey_bootstrap` itself keeps (counters, latency statistics, alert state).

| Concern | Use |
|---|---|
| JSON logs | `JsonLoggingConfigurator(level).configure()`: one JSON line per record on stderr, secrets masked, `correlation_id` on every line. Safe to call twice. |
| Correlation | `ContextVarCorrelation` plus `CorrelatingQueue(queue, correlation)` on the API side and `CorrelatedPhaseHandler(handler, correlation)` on the worker side. |
| Request metrics | `ApiObservability(readiness, metrics, correlation)` passed to `ApiApplication`. |
| Health | `ReadinessProbe((TcpHealthCheck("postgres", host, 5432), TcpHealthCheck("rabbitmq", host, 5672)))`. `ToolchainHealthCheck()` exists but the API does not add it, since the runtime image has no TeX. |
| Service spans | `TracedStartPipeline`, `TracedRunPhase`, `TracedDispatchOutbox` wrap the services. |
| Crash alerts | `ProcessCrashHooks().install()`, once per process. |
| Worker liveness | `WorkerHeartbeat(metrics, alerts).start()`, `.record_progress()` per job, `.stop()`. |

### Endpoints

| Path | Auth | Purpose |
|---|---|---|
| `GET /health/live` | none | Always `{"status": "alive"}` while the process runs. |
| `GET /health/ready` | none | `200 {"status": "ready"}` or `503 {"status": "unavailable"}`. It never names the failing dependency; that is in `/metrics` and the logs. |
| `GET /metrics` | API key | Prometheus text format. Give the scraper a bearer token. |

### Correlation

Every request gets one id. It is the trace id of an inbound `traceparent`, else a
well-formed `X-Request-ID` (8 to 64 characters of `A-Z a-z 0-9 . _ -`), else a new
random one. Anything else is replaced, never echoed, because the id lands in every
log line. The id is returned in `X-Request-ID`, copied into each queued job's
`correlation_id` (and a `traceparent` when it is a 32-hex trace id), restored by the
worker, and sent on outbound webhooks as `X-Request-ID` and `traceparent`.

### Alerts and dead letters

A webhook that fails is retried on every dispatch and counted. After
`max_attempts` (default 5) it is dead-lettered, which stops retries, increments
`webhook.dead_lettered` and raises an `error` alert. One bad event never blocks the
events behind it.

`vibey_bootstrap` sends only `CRITICAL` alerts at once, holds `ERROR` and `WARN`
in a digest that nothing here drains, and only records alerts when no recipients
are configured. So `BootstrapAlertDispatcher` always writes the alert to the log
first, at its own level. **Alert on those log lines** (`message` starting with
`alert:`, fields `alert_severity` and `dedup_key`) rather than relying on mail.

The outbox table gained a `dead_at` column before migrations existed. `ei db upgrade` adopts an
existing table as it is and does not add the column, so recreate any database created before that
change.

### What the observability does not tell you

- Log masking is by field name. A secret written into the message text itself is
  not masked, so pass values as `extra` fields.
- Counters and latencies are per process. Scrape every replica.
- `ToolchainHealthCheck` and `TcpHealthCheck` check presence and reachability,
  not that the dependency is healthy. There is no LLM-runner health check and no
  alert on budget exhaustion; a budget stop shows as a run awaiting consent.
- `ei serve api` and `ei serve worker` build this wiring for you. If you embed the
  application in your own process, wire the adapters above yourself.

## Running the stack

`ei serve api` and `ei serve worker` read their settings from the environment. A
missing or invalid value prints which variable is wrong and exits with status 2; it
never prints a traceback, which could carry a connection string.

| Variable | Needed by | Meaning |
|---|---|---|
| `EI_DATABASE_URL` | both | SQLAlchemy URL, for example `postgresql+psycopg://user:pw@host:5432/db`. Required. |
| `EI_RABBITMQ_URL` | both | `amqp://user:pw@host:5672/`. Required. |
| `EI_API_KEYS` | API | Comma-separated keys, each at least 24 characters. Required: with none, the API will not start. |
| `EI_QUEUE_NAME` | both | Job queue name. Default `engineering-influence.jobs`; the dead-letter queue is that name plus `.dead`. |
| `EI_HOST`, `EI_PORT` | API | Default `127.0.0.1` and `8000`. A bare run is never reachable from the network. |
| `EI_LOG_LEVEL` | both | `DEBUG` to `CRITICAL`. Default `INFO`. |
| `EI_RATE_BURST`, `EI_RATE_PER_SECOND` | API | Token-bucket limits, default 30 and 10. |
| `EI_MAX_RUN_BUDGET_MICRO_USD` | API, `ei run`, MCP, ACP | **The most any one run may be given, in micro-dollars, at its start and after every grant.** Not set by default (no ceiling). A bigger brief, or a grant that would take a cap over it, is refused with `BUDGET_ABOVE_LIMIT` (HTTP 422) before anything is saved or queued. |
| `EI_MAX_OUTSTANDING_BUDGET_MICRO_USD` | API, `ei run`, MCP, ACP | **The most unspent budget all runs may hold together**: each unfinished run's cap less what it has spent (a parked or waiting run still counts; a completed, failed or cancelled one does not). Not set by default. A new run or a grant that would take the total over it is refused with `OUTSTANDING_BUDGET_EXCEEDED` (422). A client that starts many runs, or is granted more again and again, runs out of room instead of out of money. A check and the save that follows it are one locked step, so many requests at once to one API or MCP process cannot each pass against the same total; two *processes* (the API and a command line, say) each hold their own lock, so across processes it is a check with a window of a few milliseconds. `ei book create` runs on your own machine and is not held to it. |
| `EI_MCP_MAX_RUN_BUDGET_MICRO_USD` | MCP server | The most a run started over MCP may be given, in micro-dollars (default 5,000,000, five dollars). A bigger brief is refused with `BUDGET_ABOVE_LIMIT`. It bounds one run, not how many an agent starts. |
| `EI_MCP_ALLOW_SPEND` | MCP server | `1`, `true` or `yes` lets `ei serve mcp` offer `grant_run` and `deny_run`, so an agent can answer a run's request for more budget. Off by default: an agent can then start, watch, resume, cancel and read runs, but cannot raise a run's cap. |

### Every variable, and where it is described

A test (`tests/unit/test_docs_match_code.py`) fails when the code reads an `EI_*` variable that is not in this index, or
when this index names one nothing uses. The two `compose only` rows are read by Docker Compose, not by the program.

| Variable | For | Described in |
|---|---|---|
| `EI_ALLOW_PAID` | lets `ei evaluate` spend money; without it the command refuses | [EVALUATION.md](EVALUATION.md) |
| `BRAVE_SEARCH_API_KEY` (not an `EI_` variable) | a Brave Search key, the backup search | [RESEARCH.md](RESEARCH.md) |
| `EI_API_KEYS` | the API's keys | [Security settings](#security-settings) |
| `EI_API_PORT` (compose only) | the host port the API is published on, default 8000 | `examples/.env.example`, [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| `EI_AUTHOR_PROFILE` | the author's own details file; a run reads it only when this names it | [The author profile](#the-author-profile-your-own-details) |
| `EI_BUILD_STRICT_RELEASE` | makes any release warning fail a run's `build` stage | [Limits to know](#limits-to-know) |
| `EI_DATABASE_URL` | the database | [Running the stack](#running-the-stack) |
| `EI_EVAL_JUDGE_PROFILE` | the model profile that judges books in `ei evaluate` | [EVALUATION.md](EVALUATION.md) |
| `EI_HOST`, `EI_PORT` | where the API listens | [Running the stack](#running-the-stack) |
| `EI_LOCAL_MODEL`, `EI_LOCAL_URL` | the free local model's name and address | [LOCAL_MODEL.md](LOCAL_MODEL.md) |
| `EI_LOG_LEVEL` | log verbosity | [Running the stack](#running-the-stack) |
| `EI_MAX_OUTSTANDING_BUDGET_MICRO_USD` | the most unspent budget all runs may hold together | [Running the stack](#running-the-stack) |
| `EI_MAX_RUN_BUDGET_MICRO_USD` | the most any one run may be given | [Running the stack](#running-the-stack) |
| `EI_MCP_ALLOW_SPEND` | lets `ei serve mcp` offer `grant_run` and `deny_run` | [Running the stack](#running-the-stack) |
| `EI_MCP_MAX_RUN_BUDGET_MICRO_USD` | the most a run started over MCP may be given | [Running the stack](#running-the-stack) |
| `EI_MODEL_CATALOG`, `EI_MODEL_PROFILES` | the model price list and the profiles file | [MODEL_PROFILES.md](MODEL_PROFILES.md) |
| `EI_PLUGIN_LOCK` | the plugin lock file | [The plugin lock](#the-plugin-lock-installed-bundles) |
| `EI_QUEUE_NAME` | the job queue's name | [Running the stack](#running-the-stack) |
| `EI_RABBITMQ_URL` | the broker | [Running the stack](#running-the-stack) |
| `EI_RATE_BURST`, `EI_RATE_PER_SECOND` | the API's rate limit | [Running the stack](#running-the-stack) |
| `EI_SEARXNG_PORT` (compose only) | the host port of the local search container, default 8888 | [A free local web search](#a-free-local-web-search-searxng) |
| `EI_WEBHOOK_URLS` | the receivers of a run's events: a comma-separated list of `https://` addresses. Empty by default, which sends nothing | [Webhooks](WEBHOOKS.md) |
| `EI_WEBHOOK_SECRET` | the secret that signs each delivery. Required when `EI_WEBHOOK_URLS` is set; never printed or logged | [Webhooks](WEBHOOKS.md) |
| `EI_WEBHOOK_INTERVAL_SECONDS` | how often the worker delivers queued events, in seconds (at least 0.01; default 5) | [Webhooks](WEBHOOKS.md) |
| `EI_NARRATOR` | the narrator for the locally narrated (non-Audible) audiobook; none is built in yet, so a name is refused | [Audiobooks](AUDIOBOOKS.md) |
| `EI_SEARXNG_URL` | the SearXNG address the research stage searches through | [A free local web search](#a-free-local-web-search-searxng) |
| `EI_SKILL_LOCK` | the skill lock file | [The skill lock](#the-skill-lock-installed-prompt-text) |
| `EI_STAGE_EXECUTOR` | what writes a run's stages: `local`, `model` or `deterministic` | [Limits to know](#limits-to-know) |
| `EI_STAGE_MODEL_PROFILE` | the profile the `model` executor uses | [MODEL_PROFILES.md](MODEL_PROFILES.md) |
| `EI_TOOL_LOCK` | the tool lock file | [The tool lock](#the-tool-lock-third-party-tool-servers) |

```bash
cp examples/.env.example examples/.env     # fill in the three blank values
docker compose -f examples/docker-compose.yml --env-file examples/.env up -d --build --wait
```

The database schema is created by `ei db upgrade`, which reads `EI_DATABASE_URL` and is safe to
run again. The compose file runs it once in a `migrate` service that the API and the worker wait
for. Outside compose, run it yourself before starting either process; they check the schema
revision at start-up and exit with `the database schema is not at the latest revision` if it is not
current. Upgrade before you roll out a new release, then start the new processes.

`examples/compose_smoke.sh` does all of this with throwaway credentials, runs a
two-stage pipeline, checks that a malformed message is dead-lettered, and tears the
stack down. It needs Docker and `curl`.

The compose file has no default credentials and refuses to start without them. Ports
are published on `127.0.0.1` only, and the containers run as a non-root user with a
read-only filesystem and no capabilities.

### What the worker does

For each `pipeline.<stage>` job it runs the phase, appends `phase.completed` to the
ledger, and enqueues the next stage, or appends `pipeline.completed` after the last. A
human gate, or an automatic gate that rejects, appends `gate.awaiting` and stops the
pipeline there.

For each `run.advance` job (payload `{run_id, stage, attempt}`) it advances a book run one
stage: it executes the run's current stage, saves the run, and queues the next stage. Redelivered
messages are safe. A message for a stage the run already passed is skipped, a transient failure
re-queues the stage with the next attempt up to three, running out of credit parks the run on
its stage, and any other failure ends the run with a blocking issue. Every change to the run is
a compare-and-swap, so two overlapping deliveries cannot overwrite each other. The worker routes
by the prefix before the first dot: `pipeline.*` and `run.*` are handled, and any other kind is
dead-lettered.

A run that parks for lack of credit stays parked: further `run.advance` messages for it are
skipped until `ei run resume RUN_ID` moves it back to running and queues its stage. `ei run cancel
RUN_ID` ends a run for good; a stage already executing is not interrupted, but its result cannot
be stored, so the run stays cancelled and nothing more is queued. Both commands change the same
stored run the worker does, through the same compare-and-swap, and refuse a run that is already
completed or failed.

A job that is malformed, or that fails, is rejected without requeue and lands in the
`.dead` queue, with an alert for failures. Nothing retries it automatically: inspect it
and republish it by hand. Stopping the worker finishes the job in flight first.

A failed run carries one blocking issue that says why: `stage-failed` (a failure that cannot be retried),
`retries-exhausted` (three transient failures in a row) or `budget-exceeded` (the journal holds more than the cap).

### Limits to know

- **A run starts from `ei run create BRIEF.TOML`.** It saves the run and queues its first stage on the broker, and the
  worker does the stages, as `resume` does. A run can also be started with `POST /v1/runs`, the SDK's `create_run`, the MCP `create_run` tool, or `ei book create` (in one process); `ei run runs` lists them.
- **The worker's default is a free local model.** `EI_STAGE_EXECUTOR` is `local` unless set:
  an open-source model (`gpt-oss:20b`, Apache 2.0) on this machine through Ollama, no key, no cost, and a SearXNG at
  `http://127.0.0.1:8888` for research. Nothing is contacted when the worker starts; [LOCAL_MODEL.md](LOCAL_MODEL.md) says how to
  set it up and check it (`ei doctor --local`) and how to point at another model (`EI_LOCAL_MODEL`, `EI_LOCAL_URL`). `deterministic` is the offline
  placeholder, which writes `<stage>.md` from the brief's idea at no cost and calls no model; the example compose stack
  uses it because a container cannot reach the host's `127.0.0.1`. With
  `EI_STAGE_EXECUTOR=model` a model of your own does the stages instead, and the worker refuses to start
  unless `EI_STAGE_MODEL_PROFILE` (a profile's name), `EI_MODEL_PROFILES` and `EI_MODEL_CATALOG`
  (the files `ei doctor --models` checks, see [MODEL_PROFILES.md](MODEL_PROFILES.md)) are set,
  the profile exists, a price is in force today, and its key is available. A profile file being
  present never switches it on, because this spends money. Non-fiction and novel runs have stages from the
  brief to a built book ([BOOKS_AND_KDP.md](BOOKS_AND_KDP.md)). An answer that is refused, cut off or empty stops the run, and so does an
  outline that cannot be read as numbered chapters (`OUTLINE_INVALID`; see [PROMPTS.md](PROMPTS.md#the-outline-is-a-format-not-just-prose)).
  Nothing has been run against a live provider.
- **`EI_EVAL_JUDGE_PROFILE`** (required by `ei evaluate`): the name of the profile, in `EI_MODEL_PROFILES`, of the model that scores the
  evaluation's books. It is named separately; nothing stops you naming the writer's own profile, so do not. `ei evaluate` refuses to start without it
  (`EVALUATION_JUDGE_REQUIRED`) and spends only when `EI_ALLOW_PAID=1` ([EVALUATION.md](EVALUATION.md)).
- **`EI_BUILD_STRICT_RELEASE`** (optional, default off): `1`, `true` or `yes` makes a run's `build` stage build a strict release,
  so any readiness warning (for example a missing price or its source and date) fails the run. Off, those are warnings in
  the run's `quality-report.json`. The build needs the TeX worker image ([WORKER_IMAGE.md](WORKER_IMAGE.md)).
- **Web search for the research stage.** The research stage gives the model two tools, `web_search`
  and `fetch_url`, so a model-backed run needs a search. Set `EI_SEARXNG_URL` to a
  [SearXNG](https://github.com/searxng/searxng) instance (free; `examples/searxng/` runs one locally,
  see below) and it is tried first. Set `BRAVE_SEARCH_API_KEY` and Brave is the backup: it is asked
  only when SearXNG fails, is refused, is rate-limited or finds nothing, so a query reaches Brave
  only then. With only one of the two set, that one is the search. With neither, the process stops
  at start (`STAGE_SEARCH_NOT_CONFIGURED`) before anything is spent. A search sends the query to
  the instance (which sends it on to its engines) or to Brave. `fetch_url` reads public https
  pages only. Neither search adapter has been run against a live service, and nothing here has
  touched the live internet.
- **Retries are immediate.** A transient failure is re-queued with no delay, because the
  queue port has none yet.
- **The runner and gate are placeholders.** `DeterministicRunner` returns a fixed line
  of text and `NonEmptyArtifactGate` accepts anything non-blank. They let the whole
  pipeline run offline; a model-backed runner and rubric gates implement the same interfaces.
- **Delivery is at least once.** A worker that dies between writing the ledger and
  acknowledging the job runs it again and records the stage twice.
- **Nothing resolves a human gate yet.** There is no endpoint for it, so a pipeline that
  reaches one stays parked.
- **No webhook is emitted.** The outbox, signing and dispatch exist, but no service
  creates outbox intents, and the worker does not run the dispatcher.
- **The read API covers book runs only.** `GET /v1/runs/{id}` and `ei run status` show a run;
  pipeline progress is still visible only in the ledger table and the logs.
- **The base images are tags, not digests**, and the worker has no container
  healthcheck; it logs a heartbeat and raises a critical alert if it stalls.

## A free local web search (SearXNG)

`examples/searxng/` runs SearXNG on your machine, so the research stage can search without an account or
a key. It is published on `127.0.0.1` only, refuses to start without a secret, and its `settings.yml`
turns on the `json` format the adapter asks for (without it SearXNG answers 403).

```sh
export SEARXNG_SECRET="$(openssl rand -hex 32)"
docker compose -f examples/searxng/docker-compose.yml up -d --wait
export EI_SEARXNG_URL=http://127.0.0.1:8888
```

What is and is not checked: the compose file is validated by `docker compose config` and its settings are
pinned by tests, and it has been started once by hand: the container went healthy and the adapter ran
against it for real (queries, validation, and the 403 a default instance gives when `json` is not enabled).
That is not run by the project's tests or CI. The image is pinned by digest to the build it was tested with
(2026-11-21), so it does not get SearXNG updates until someone moves the digest: pull a newer image, check a
search works against it, then replace the digest in the compose file. SearXNG passes your queries to the
public search engines it is set to use, and those engines can throttle or block a local instance, which is
what the Brave backup is for. The port is `EI_SEARXNG_PORT` (default 8888).

Check that it answers with `ei doctor --search` (one real search per provider; see [RESEARCH.md](RESEARCH.md)).

## The tool lock (third-party tool servers)

`ei tools add`, `list` and `verify` read and write one lock file: `--lock PATH`, else `EI_TOOL_LOCK`, else
`ei-tools.lock.toml` in the current directory. **`add` and `verify` start the server's code**, so run them
only on servers you mean to run. Each server is started with a bare environment (see
[TOOL_LOCK.md](TOOL_LOCK.md)) and, for one look, at most **two minutes, 2 GiB of memory and 1 GiB of disk**.
These are fixed in the command, not settings. A **remote** server (`add --url`) is contacted, not started: it
is held to https and a public address, with a 30-second request limit, and its token is the variable named by
`--bearer-env`, read from the environment when the connection is made.

**A run reads a lock only when `EI_TOOL_LOCK` names it** (the file in the current directory is not read).
Its servers are then started and verified when the stage executor is built, a changed one stops the process
(`TOOL_LOCK_MISMATCH`), a named file that does not exist is `TOOL_LOCK_MISSING`, and a stage is offered only the
locked tools the lock grants it (`ei tools grant`). For the life of the process each server may use four
hours, 2 GiB of memory and 1 GiB of disk. See [TOOL_LOCK.md](TOOL_LOCK.md#in-a-run).

## The skill lock (installed prompt text)

`ei skills add`, `enable`, `disable`, `remove`, `list` and `verify` read and write one lock file: `--lock PATH`,
else `EI_SKILL_LOCK`, else `ei-skills.lock.toml` in the current directory, with the skill files in a `skills/`
folder beside it. Nothing here starts a process or opens a connection; a skill is text.

**A run reads a skill lock only when `EI_SKILL_LOCK` names it** (the file in the current directory is not read).
Each skill enabled for some stage is read and hashed once when the stage executor is built, before any tool
server is started: a skill that changed is `SKILL_LOCK_MISMATCH`, a named file that does not exist is
`SKILL_LOCK_MISSING`, and a stage's prompt carries only the skills the lock enables for it. A file is at most
64 KiB, a part at most 8,000 characters, and a stage at most four skills; these are fixed in the code, not
settings. See [SKILLS.md](SKILLS.md#in-a-run).

## The plugin lock (installed bundles)

`ei plugins show`, `add`, `list`, `verify` and `remove` read and write the plugin lock: `--lock PATH`, else
`EI_PLUGIN_LOCK`, else `ei-plugins.lock.toml` in the current directory, with the bundles kept in a `plugins/` folder
beside it. `add`, `verify` and `remove` also use the skill lock (`--skill-lock`, else `EI_SKILL_LOCK`, else
`ei-skills.lock.toml`). Nothing here starts a process or opens a connection.

**A run never reads the plugin lock.** It is a record for `verify` and `remove`; what a run may do is in the tool lock
and the skill lock. A bundle is at most 512 KiB, with at most 16 servers and 16 skills; these are fixed in the code,
not settings. See [PLUGINS.md](PLUGINS.md).

`ei plugins search INDEX` and `fetch INDEX NAME` take an index that is **a file on disk or an `https://` address**. They are
the only commands that can use a network, only for an `https://` address, with no setting for a proxy or a
credential. An index may be up to 512 KiB and list 500 plugins, a download is at most 512 KiB, and a request has 30
seconds; these are fixed in the code. Downloading needs the `runtime` extra (`pip install 'engineering-influence[runtime]'`),
which a local index file does not. A run never contacts a marketplace.

## The author profile (your own details)

A book's title page, copyright page and about-the-author page need things only the author can say. They go in a small TOML
file you keep yourself, outside this repository, and **a run reads it only when `EI_AUTHOR_PROFILE` names it** (a file in
the current directory is not read). The assemble stage writes it into the book's config; it is never sent to a model.

```toml
author = "Ann Author"            # required
publisher = "Pub House"          # required
edition = "First Edition"        # required; has to say "Edition"
author_bio = "Ann writes."       # required; paragraphs allowed
year = 2031                      # optional
website = "https://pub.example"  # optional
email = "ann@pub.example"        # optional
isbn = "978-0-0000-0000-0"       # optional
ebook_isbn = "978-0-0000-0001-7" # optional
dedication = "For you."          # optional
copyright_notes = "Notes."       # optional
also_by = ["Earlier Book"]       # optional, at most 20

[pricing]                        # optional; needed for a strict release
verified_on = "2026-11-19"       # the day you checked the prices (an ISO date)
source_url = "https://kdp.amazon.com/en_US/help/topic/G201834170"  # a page that shows the print costs
ebook = 4.99
paperback = 12.99
hardcover = 22.99                # optional; a price here makes the book a KDP hardcover too
```

The prices are yours: a run never invents them. They go into the book's `[release.pricing]`, which is what a strict release
checks (`EI_BUILD_STRICT_RELEASE`, or `--strict-release` on `ei book create`). Without a `[pricing]` table a missing price is a
warning in the run's `quality-report.json`, and a strict release fails.

Any other key is refused, a missing file stops the process at start (`AUTHOR_PROFILE_MISSING`), and a bad one stops it with
the reason (`AUTHOR_PROFILE_INVALID`). The file is at most 64 KiB. A one-line field is at most 200 characters with no space at either end; `author_bio`,
`dedication` and `copyright_notes` are at most 4,000; `year` is 1000 to 9999; `email` has an `@` and no space; an ISBN
is digits and hyphens ending in a digit or `X`; `also_by` has at most 20 titles; and no field may hold a control or
invisible character. `[pricing]` needs `verified_on` (an ISO date), `source_url` (http or https), and `ebook` and
`paperback` above zero; `hardcover` is optional. Without a
profile the assembled book loads but does not build, and the build says which of these is missing. Em and en dashes are
refused in non-fiction when the book is built, and the profile is not rewritten, so leave them out of your own text.

