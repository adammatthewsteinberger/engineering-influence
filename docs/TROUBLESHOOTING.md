# Troubleshooting

**BLUF:** Ask the machine first: `ei doctor --ready` checks the extras, the build tools, the author profile, the
local model (when `EI_STAGE_EXECUTOR` is `local`) and the search, and says what to do about each failure. It makes
one tiny request to the local model and one real search request, and it does not look at the database or the
broker. If the machine is fine and the stack is not, find the symptom in the table below. The rows about the stack
assume you ran `set -a; . examples/.env; set +a`.

## Ask before you guess

> **Daniel:** Something failed and I have forty log lines. I do not know where to start.
>
> **Professor Feynman:** A car will not start. What is the first thing a mechanic does?
>
> **Daniel:** Plugs in the diagnostic computer.
>
> **Professor Feynman:** Ask the machine. `ei doctor --ready` is yours: one line per thing a book needs, `ok` or
> `FAIL`, and each `FAIL` says what to do. It finds the author profile you forgot and the TeX tool that is missing
> before you spend an hour on a log.
>
> **Daniel:** And if it all says `ok` and the stack still misbehaves?
>
> **Professor Feynman:** Then the machine is fine and the fault is elsewhere. The doctor checks this computer's
> own files and tools, the local model and the search, and not the stack: it does not look at the database or the
> broker. Look your symptom up below, and collect the evidence the last section lists before you ask for help.
>
> **Daniel:** Doctor for the machine, the table for the stack, and the evidence block for a bug report.


Find the symptom, then the cause. Commands assume you ran `set -a; . examples/.env; set +a`.

| Symptom | Cause | Fix |
|---|---|---|
| `docker compose` says `set POSTGRES_PASSWORD in examples/.env` | Compose has no default credentials by design | `sh examples/up.sh` generates `examples/.env`, or copy `.env.example` and fill every blank |
| `error: required secret EI_DATABASE_URL is not configured` (exit 2) | `ei serve` fails closed without settings | Export the variables in [CONFIGURATION.md](CONFIGURATION.md#running-the-stack) |
| API or worker exits with `the database schema is not at the latest revision` | The database was never migrated, or a new release added migrations | Run `ei db upgrade` (compose does this in its `migrate` service), then start the process |
| `ei run resume` prints `ConnectionError while talking to the stack` | The broker was unreachable after the run was un-parked, so its stage was not queued | Run the same command again: resuming a running run queues its stage |
| `ei run …` prints `error: run 'x' is already completed` (exit 1) | Completed and failed runs cannot be resumed or cancelled | Nothing to do; a cancelled run can be cancelled again, which changes nothing |
| `ei db upgrade` prints `cannot reach or migrate the database (OperationalError)` | The URL is wrong or the database is down; the message never includes the password | Check `EI_DATABASE_URL` and that Postgres is reachable from where you run it |
| `ei serve api` or `worker` prints `needs the api and runtime extras`; `ei serve mcp` names the `mcp` and `runtime` extras | Optional dependencies missing | `pip install "engineering-influence[api,runtime]"` (or `[mcp,runtime]`), or `uv sync` with those extras |
| `ei book …` prints `book commands need the publishing extra`; `ei book create` prints `book create needs the runtime and publishing extras` | Pillow, numpy and the PDF libraries are optional | `pip install "engineering-influence[publishing]"` (and `[runtime]` for `book create`) |
| `ei book create` stops at once with `already exists and is not an empty folder` (exit 2) | `--out` holds something, and a book is written only into a new or empty folder | Choose a new `--out`. To keep a run you were resuming, `--out NEW_FOLDER --state-dir OLD.state --resume` |
| `ei book create` exits 1 and prints `issue: stage-failed: …the book 'SLUG' did not build…`, naming a step or tool | The `build` stage could not make the PDF or EPUB, usually because a TeX tool is not installed. Every chapter was still written and is in `--out` | `ei doctor --ready` lists each missing tool. Install it. **A failed run is final: `--resume` does not retry it.** Build the exported project with `ei book --root OUT build SLUG` (or `publish`), or start a new run with a new `--out`. Rebuilding the export has not been tried end to end |
| `ei book create` exits 2 and prints `a book needs the author's details to be typeset` (code `AUTHOR_PROFILE_REQUIRED`) | A book needs the author's details to be typeset, and none was named | Pass `--profile FILE` or set `EI_AUTHOR_PROFILE`; `examples/author-profile.example.toml` is a starting point. (`ei doctor --ready` takes `--author-profile`.) |
| `ei book create` exits 3 | The run stopped to ask for more budget. Nothing is lost | Decide, then `ei book create --out DIR --resume --approve-spend` |
| `ei doctor --ready` fails `local: server` | Ollama is not running at `EI_LOCAL_URL` | Start Ollama, or set `EI_LOCAL_URL`; see [LOCAL_MODEL.md](LOCAL_MODEL.md) |
| `ei doctor --ready` fails `local: context` | The server loaded the model with fewer than 131,072 tokens | Set `OLLAMA_CONTEXT_LENGTH=131072` where you start Ollama and restart it |
| `ei doctor --ready` prints `FAIL searxng at its default address: search: …` | Nothing answered a real test search at `http://127.0.0.1:8888`, or at the `EI_SEARXNG_URL` or Brave you set | Start the SearXNG in `examples/searxng/` (see [RESEARCH.md](RESEARCH.md)) or set `EI_SEARXNG_URL` or `BRAVE_SEARCH_API_KEY` |
| `ei doctor --ready` prints `FAIL install: tool <name>` or `FAIL install: extra <name>` | The build stage needs that tool, or the run needs that extra | Install it; [WORKER_IMAGE.md](WORKER_IMAGE.md) lists the TeX packages |
| `ei doctor --ready` fails `local: model` or `local: answers` | The model is not pulled, or it returned an empty answer | `ollama pull gpt-oss:20b`; see [LOCAL_MODEL.md](LOCAL_MODEL.md) |
| API will not start; mentions API keys | `EI_API_KEYS` unset or a key shorter than 24 characters | `openssl rand -hex 24` per key |
| `401 UNAUTHORIZED` | Missing or wrong key | `Authorization: Bearer $EI_API_KEY` or `X-API-Key`; the key is the one in `EI_API_KEYS` |
| `429 RATE_LIMITED` | Budget spent (default burst 30, 10 per second) | Back off; raise `EI_RATE_BURST` / `EI_RATE_PER_SECOND` for trusted clients |
| `422` on `POST /v1/pipelines` | A required field is missing or a stage name is unknown; the answer names the valid stages | Valid stages: `thesis book novel screenplay hub spokes distribution publish` |
| `GET /health/ready` returns 503 | A dependency is unreachable; the body never says which | Read `/metrics` (needs a key) and the API log |
| `Connection refused` on port 8000 | Stack not up, or `EI_API_PORT` changed | `docker compose -f examples/docker-compose.yml --env-file examples/.env ps` |
| Postgres container unhealthy, exits at start (Postgres 18 image) | The volume is mounted at `/var/lib/postgresql/data`; 18+ images keep a versioned directory under `/var/lib/postgresql` | Mount `/var/lib/postgresql` (the shipped compose file does) and delete the old volume: `sh examples/down.sh --volumes` |
| A job sits in `engineering-influence.jobs.dead` | The job was malformed or failed; nothing retries it | Inspect it in the RabbitMQ UI or `rabbitmqctl`, fix the cause, republish by hand |
| A stage ran twice | At-least-once delivery: the worker died between the ledger write and the acknowledgement | Make downstream consumers idempotent on `job_id` |
| Pipeline stops at `gate.awaiting` | A human gate (or a rejecting gate) parked it; no endpoint resolves gates yet | Not recoverable through the API yet |
| MCP host shows no tools | It launched the wrong command or directory | Run `uv run python examples/mcp/client.py` to prove the server; give the host the same command and `cwd` |
| Webhook receiver answers 401 | Wrong secret, body re-serialised before verifying, or clock skew over 300 seconds | Sign and verify the **raw bytes**; sync the clock |
| Webhook receiver answers 409 | Replay: the same signature arrived twice | Expected on retries after your `2xx`; treat as already processed |
| `ModuleNotFoundError: mcp.server.mcpserver` | You installed `mcp` 1.x with this release | This project needs `mcp>=2,<3`; `pip install -U "mcp>=2,<3"` |
| `ruff`, `mypy` or `pytest` not found | Wrong extras | `uv sync --extra test --extra runtime --extra dev --extra publishing` |
| Coverage drops below 100% only for `book_cli` / `serve_cli` | Child-process coverage not enabled (pytest-cov 7+) | Keep `patch = ["subprocess"]` and `parallel = true` in `[tool.coverage.run]` |
| Pushed a Dependabot-style commit and `provenance` fails | The commit has no `Made-With:` trailer | `vibey-gh install` adds the commit hook; amend the commit message |

## Errors you will see, by their code

Each code is in the message the command prints, in the form `error: <message>`, or in the response body of the API.
Codes shown here are the ones a person is likely to meet; the full list is the snapshot
`tests/contracts/snapshots/error_codes.json`, and most of the rest are internal (stage plumbing, job payloads,
recorded cassettes) and need no action from you.

| Code | The message says | What to do |
|---|---|---|
| `BRIEF_UNREADABLE` | `cannot read FILE: …` | `ei run create` could not open the brief file. Check the path and that the file is readable |
| `CONTENT_LEVEL_NOT_ALLOWED` | `the brief asks for violence X, but PROVIDER/MODEL is recorded as allowing up to Y` (or the same for `heat`, or that no ceiling is recorded) | The model's usage policy does not allow the content level the brief asks for. Lower the level, or use a model whose recorded ceiling allows it. The message names the policy page to read |
| `EXPORT_TARGET_NOT_EMPTY` | `FOLDER already exists and is not an empty folder; choose a new or empty --out` | `ei book create` writes the book only into a new or empty folder. Choose a new `--out`; see the `--out` row above |
| `CONTEXT_TOO_LARGE` | `the style, grounding, beats and instruction alone need N input tokens and only M are available` | The fixed parts of a chapter's prompt do not fit the model's window. Shorten the author's own material, or use a model with a larger window |
| `DATABASE_UNAVAILABLE` | `cannot reach or migrate the database (ErrorType)` | The database is down or the URL is wrong; the message never includes the password. See the database row above |
| `EXPORT_NAME_CLASH` | `two artifacts of run R would be written to P` | Two stored files map to one path. Not expected in a normal run; report it with the run id |
| `LOCAL_SERVER_UNREACHABLE` | `nothing answers at URL` | The local model server is not running at `EI_LOCAL_URL`. Start Ollama, or see [LOCAL_MODEL.md](LOCAL_MODEL.md) |
| `MODEL_REJECTED` | `the model server rejected the request (STATUS, CODE): MESSAGE` | The server refused the call. The status and the server's own message say why: often a wrong model name, or a key the provider does not accept |
| `PATH_ESCAPE` | `path is outside the permitted directory` | A path given to a tool is outside the folder it may use. Give a path inside that folder |
| `PRICING_REQUIRED` | `a strict release needs the author's pricing: add a [pricing] table …` | `--strict-release` needs `[pricing]` in the author profile. Add it, or drop `--strict-release` |
| `RUN_HAS_NO_ARTIFACTS` | a run that stored nothing cannot be exported | The run failed before it stored anything. Read its `issue:` lines; a new run is the way forward |
| `STAGE_MODEL_NOT_CONFIGURED` | `EI_STAGE_EXECUTOR=model needs NAME` | Name what the model executor needs: a profile, a catalog or a model. See [MODEL_PROFILES.md](MODEL_PROFILES.md) |
| `STAGE_MODEL_PROFILE_UNKNOWN` | `no profile named NAME in FILE (it has: …)` | The profile you named is not in that file. Use one of the names it lists |
| `STAGE_MODEL_KEY_IN_CLEAR` | `profile NAME would send its key over plain http to another host` | A profile would send its key unencrypted to another machine. Use `https`, or a local address |
| `SCHEMA_OUT_OF_DATE` | `the database schema is not at the latest revision; run ei db upgrade` | Run `ei db upgrade` |
| `TOOL_URL_REFUSED` | the address was refused by the URL policy | A remote tool server must be a public `https` address. See [TOOL_LOCK.md](TOOL_LOCK.md) |
| `TOOL_ENV_MISSING` | `the environment variable NAME is not set` | Set the variable the tool server's configuration names, then start again |
| `WEBHOOK_TARGET_REJECTED` | `webhook destination refused: REASON` | The webhook's address was refused: it must be public `https` |
| `SKILL_IMPORT_TOO_LARGE` | `the chosen text is N characters and a part holds at most M; choose sections with --section` | Pick fewer reference sections with `--section`. The message lists each section and its length |
| `SOURCE_TOO_COMPLEX` | `the page nests elements more than N deep` | A fetched web page is too deeply nested to read safely. The research stage skips it; no action needed |
| `SOURCE_EMPTY` | `the source folder ... has no readable source files` | A screenplay's source folder holds no `.md` or `.txt` files. Put the manuscript files in it (ADR 0017) |
| `SOURCE_FOLDER_MISSING` | `the source folder ... does not exist` | The path given for the source folder is wrong. Check it |
| `SOURCE_TOO_LARGE` | `source file ... is over 2000000 bytes; split it` | A source file is larger than the limit. Split it into several files in the folder |
| `STAGE_OUTPUT_INVALID` | `beats: the beat sheet needs the fifteen beats in order ...` | A screenplay stage's answer broke a format rule, so the run stopped at that stage. Read the named problems; a re-run of the stage asks again |
| `SCREENPLAY_NO_TITLE` | `the title page must name the title` | A screenplay's title page has no `Title:` line. Add one to the screenplay settings |
| `SCREENPLAY_NO_SCENES` | `a screenplay has at least one scene` | The screenplay has no scenes to join. Check the drafted scenes |
| `SCREENPLAY_SCENE_INVALID` | `scene N must be exactly one scene heading and its elements` | A drafted scene holds more than one scene heading. Split it or redraft it |
| `RUN_MODE_UNKNOWN` | `a book run is a book or an audiobook, not 'x'` | The `--mode` is not `book` or `audiobook`. Use one of those |
| `NARRATION_FAILED` | `the narrator could not read a segment: ...` | The local voice engine could not narrate a piece of text: it is missing (install the `audio` extra on an Apple Silicon Mac), it exited with an error, or it wrote no audio. The message names the engine's last output |
| `VIDEO_PROVIDER_UNAVAILABLE` | `the video provider 'veo' needs EI_OPENROUTER_API_KEY and is one of: openrouter` | `EI_VIDEO_PROVIDER` names a provider this build does not have, or names `openrouter` without `EI_OPENROUTER_API_KEY`. Set the key, or unset `EI_VIDEO_PROVIDER` so the screenplay makes no video |
| `VIDEO_GENERATION_FAILED` | `the video service ended job ... as 'failed' for shot N` | The hosted model failed, was cancelled or expired a shot's job. The run stops; `--resume` keeps the shots already made and asks again only for the rest |
| `VIDEO_REJECTED` | `the video service rejected the request (400): ...` | The hosted service refused a shot's request, for example a prompt or length it does not accept. The message gives its reply; change the shot before trying again |
| `STOP_STAGE_UNKNOWN` | `a screenplay run has no stage 'x' to stop after` | The `--stop-after` stage name is not a stage of that kind of run. Use a stage name from the plan, such as `scene_cards` |
| `SHOOTING_LOCK_UNREADABLE` | `the shooting script lock is unreadable: ...` | The previous shooting script lock the run was given is not a version 1 lock file, or one of its scenes has a bad number. Re-export the lock from the run that made it |
| `SCENE_CARDS_UNREADABLE` | `the scene cards have no '## S01 ·' card` | The scene cards from the architecture stage cannot be read: a card has no `**Beat:**` field, no `**Sources:**` field of source numbers, or there are no cards at all. Re-run the scene-cards stage |
| `SCREENPLAY_NO_SOURCES` | `a screenplay run needs a source folder, given with --source` | A screenplay is written from the author's source files, so the run needs `--source DIR`. Give the folder and start again |
| `BIBLE_FOLDER_MISSING` | `the bible folder ... does not exist` | The screenplay's bible folder is not where it was pointed. Check the path (ADR 0018) |
| `BIBLE_CARD_INVALID` | `kind/id.md: its front matter ...` | A bible card must open with a `+++` line, hold TOML, close with a second `+++` line, and use a lowercase kind folder and id file name (ADR 0018) |
| `BIBLE_SCHEMA_INVALID` | `bible.toml holds only a [required] table ...` | `bible.toml` may hold only a `[required]` table that maps each kind to a list of key names |
| `BIBLE_FIELD_MISSING` | `kind/id must set name` | A card lacks a key that `bible.toml` requires for its kind. Add the key to the card |
| `BIBLE_DUPLICATE_ID` | `two cards are kind/id` | Two files in one kind folder share a name, or two cards carry one id. An id is unique within its kind |
| `BIBLE_LINK_UNKNOWN` | `kind/id links to kind: id, which is not a card` | A `[[kind: id]]` link in a card names no card. Fix the id or add the card |
| `BIBLE_KIND_UNSUPPORTED` | `a bible is for screenplay runs only` | `--bible` was given for a book that is not a screenplay. Only `--kind screenplay` takes a bible |
| `BIBLE_REAL_PERSON` | `kind/id is a real person ...` | A card with `real = true` must name its `clearance`, and must not carry a `likeness` or `voice` key (ADR 0018) |

## Collecting evidence for a bug report

```bash
uv run ei --version
docker compose -f examples/docker-compose.yml --env-file examples/.env ps
docker compose -f examples/docker-compose.yml --env-file examples/.env logs --no-color --tail 100 api worker
```

Logs are JSON lines with a `correlation_id`; search for the id from your `X-Request-ID`.
Secrets are masked by field name, but check before pasting. Report security issues privately
through [SECURITY.md](../SECURITY.md), not in a public issue.
