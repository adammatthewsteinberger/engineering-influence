# Getting started

**BLUF:** Three commands take you from nothing to a book: install, check, write. The install is one line, the
check tells you every gap with its fix, and the book is written by a free model on your own machine. The full
stack (an API, a queue and a worker) is a separate, optional step at the end.

```bash
curl -fsSL https://raw.githubusercontent.com/adammatthewsteinberger/engineering-influence/main/install.sh | sh
ei doctor --ready
ei book create --kind nonfiction "how to keep herbs alive indoors" --budget-usd 5 \
  --out ./my-book --profile ~/.config/engineering-influence/author.toml
```

## Before you type anything

> **Daniel:** The install line pipes a script from the internet straight into my shell. My last job would have
> walked me out of the building for that.
>
> **Professor Feynman:** Good instinct. What exactly are you afraid of?
>
> **Daniel:** That I do not know what it does until it has done it.
>
> **Professor Feynman:** Then make it tell you first. Add `--dry-run`. It prints every command it would run and
> changes nothing. It is the difference between a mover carrying your piano upstairs and a mover walking the
> route with you and pointing at each doorway.
>
> **Daniel:** So I read the list, and if I dislike a doorway?
>
> **Professor Feynman:** Skip it. `--skip-model` leaves Ollama alone, `--skip-tex` leaves TeX alone,
> `--skip-search` starts no search. Or read the script itself: it is one file, with what it does written at
> the top. The walk-through has a limit, mind you. It shows the commands, not what those commands download.
>
> **Daniel:** And afterwards, how do I know it worked?
>
> **Professor Feynman:** You do not take its word. You ask a second question: `ei doctor --ready`. One line per
> thing a book needs, `ok` or `FAIL`, and every `FAIL` says what to do. Tell me what you would run first.
>
> **Daniel:** The dry run. Then the real one. Then the doctor, and I do not start a book while it says `FAIL`.

## 1. Install

You need macOS with [Homebrew](https://brew.sh), or Linux with `apt-get`. See what it will do first:

```bash
curl -fsSL https://raw.githubusercontent.com/adammatthewsteinberger/engineering-influence/main/install.sh | sh -s -- --dry-run
```

Then run it:

```bash
curl -fsSL https://raw.githubusercontent.com/adammatthewsteinberger/engineering-influence/main/install.sh | sh
```

| Step | What it installs | Size | Skip with |
|---|---|---|---|
| 1 | [`uv`](https://docs.astral.sh/uv/) if missing, then `ei` with the `runtime`, `publishing` and `mcp` extras | small | |
| 2 | [Ollama](https://ollama.com) and the model `gpt-oss:20b` | about 13 GB | `--skip-model` |
| 3 | The TeX tools that build the PDF and the EPUB | several GB | `--skip-tex` |
| 4 | A local SearXNG for the research stage, if Docker with compose is present | a container | `--skip-search` |
| 5 | A starter author profile at `~/.config/engineering-influence/author.toml` | a file | never written over |
| 6 | Runs `ei doctor --ready` and prints the command that writes a book | | |

Other options: `--with-claude-skill` puts the [Claude Code skill](AGENTS_DRIVING.md) in `~/.claude/skills/`, and
`--version REF` installs a tag, branch or commit instead of `main`. Options go after `sh -s --`, because the
script itself is arriving on standard input.

The script asks no questions, because a piped script has no keyboard. A step that needs administrator rights
runs `sudo`, which asks for your password itself. Run it twice and the second run changes nothing already in
place.

**What is not verified:** the script has been run for real only as a dry run on macOS. The Linux path is tested
against stand-in tools. On Linux it prints how to set Ollama's context size and does not set it. On a Mac
without Homebrew it stops and tells you to install Homebrew. It installs from `main`, which gets the script with
the next release.

By hand instead: `uv tool install "engineering-influence[runtime,publishing,mcp] @ git+https://github.com/adammatthewsteinberger/engineering-influence"`,
then the tools in [WORKER_IMAGE.md](WORKER_IMAGE.md) and the model in [LOCAL_MODEL.md](LOCAL_MODEL.md).

## 2. Check the machine

```bash
ei doctor --ready
```

```text
ok   install: extra runtime: installed
ok   install: tool lualatex: /Library/TeX/texbin/lualatex
FAIL install: author profile: none named: set EI_AUTHOR_PROFILE or pass --author-profile FILE (…)
ok   local: model: gpt-oss:20b is pulled
ok   local: context: 131072 tokens, at least the 131072 a prompt is assembled to fit
…
1 of 14 checks failed
```

| It checks | Why it matters |
|---|---|
| The `runtime` and `publishing` extras | Without them a run stops at once |
| `lualatex`, `latexmk`, `tex4ebook`, `zip`, and `pdftoppm` or `mutool` | Without them every chapter is written and then the last stage, `build`, fails |
| `epubcheck` (optional) | Only a strict release needs it; without it the EPUB gets the built-in checks |
| The author profile | A book cannot be typeset without the author's name, imprint and bio |
| The local model: the server, the model, one tiny answer, the context size | It is what writes the book |
| The search | The research stage needs one |

It exits `0` when everything passed, `1` when a check failed and `2` on setup trouble. It sends one tiny
completion to the local model, which stays on your machine, and one search request to each search you have
configured.

## 3. Fill in your author profile

Open `~/.config/engineering-influence/author.toml` and replace every value with your own. It is the title page,
the copyright page and the about-the-author page. It is never sent to a model.

```toml
author = "Your Name"
publisher = "Your Imprint"
edition = "First Edition"
author_bio = "One or two sentences about you, as you want them printed in the book."
```

The other keys, and the `[pricing]` table a strict release needs, are in
[CONFIGURATION.md](CONFIGURATION.md#the-author-profile-your-own-details).

## 4. Write a book

```bash
ei book create --kind nonfiction "how to keep herbs alive indoors" --budget-usd 5 \
  --out ./my-book --profile ~/.config/engineering-influence/author.toml
```

It prints an estimate, then one line per stage as each finishes, then a summary. `--kind novel` writes a novel.
`--out` must be a new or empty folder. `--budget-usd` is required even with the free model, where it is only a
cap. A whole book takes a long time; how long on your machine is not yet measured.

`--source DIR` gives the run a folder of source files (`.md` and `.txt`, hidden files skipped, at most 2,000,000 bytes each). They are read when the run is created, numbered in name order, and kept inside the run as `source/NNN.md`, so the run never reads the folder again and the folder may be moved or deleted afterwards. An empty or missing folder is refused before any money is spent.

| Exit | Meaning | What to do |
|---|---|---|
| `0` | The book is written | Open `my-book/run/book/` and read `my-book/run/quality-report.json` |
| `1` | The run failed, and a failed run is final; what it made is still in `my-book/` | Read the `issue:` lines it printed, fix the cause, and start a new run with a new `--out` |
| `2` | It could not start | The message says why |
| `3` | It stopped to ask for more budget; nothing is lost | `ei book create --out ./my-book --resume --approve-spend` |

If it is interrupted (a crash, a closed laptop, a provider that was out of capacity), carry on:

```bash
ei book create --out ./my-book --resume
```

Finished stages are never run or paid for again. The run is kept in `my-book.state/`. A run that ended in failure (exit 1) is final: `--resume` returns it as it is and does not try again. A failed run's chapters are still in `my-book/`.

What is in the folder, and every flag: [INTERACTIONS.md](INTERACTIONS.md#cli) and
[BOOKS_AND_KDP.md](BOOKS_AND_KDP.md).

## Run the stack

Everything above is one process and needs no server. The stack is for many runs, other machines and other
programs: a REST API, a queue, a worker, the SDK, the MCP server and webhooks. You need a clone of the
repository, Docker with compose, [`uv`](https://docs.astral.sh/uv/) and `python3`.

```bash
git clone https://github.com/adammatthewsteinberger/engineering-influence
cd engineering-influence
sh examples/up.sh
set -a; . examples/.env; set +a
curl -fsS "$EI_BASE_URL/health/ready"      # {"status":"ready"}
uv run examples/api/start_pipeline.py
```

The first run writes `examples/.env` (git-ignored, mode 600) with random database and broker passwords and one
API key, then builds the image and starts five services: Postgres, RabbitMQ, a one-shot database migration, the
API on `127.0.0.1:8000` and the worker. It waits until every container is healthy. Nothing has a default
credential, and nothing is reachable from your network.

```text
ready: 200 ready
without a key: 401
started: 200 {"job_id": "6c05b79f-…", "project_slug": "sample-essay"}
```

**This demo proves the plumbing, not the writing.** The example worker runs `EI_STAGE_EXECUTOR=deterministic`,
which writes placeholder text, and `start_pipeline` is the older stage pipeline. To write real books on the
stack, give the worker a model and the TeX image: [WORKER_IMAGE.md](WORKER_IMAGE.md) and
[CONFIGURATION.md](CONFIGURATION.md#running-the-stack).

| Interface | Command | Reference |
|---|---|---|
| curl | `sh examples/api/run.sh` | [REST](INTERACTIONS.md#rest-api) |
| SDK (sync) | `uv run python examples/sdk/sync_client.py` | [SDK](INTERACTIONS.md#python-sdk) |
| SDK (async) | `uv run python examples/sdk/async_client.py` | [SDK](INTERACTIONS.md#python-sdk) |
| MCP | `uv run python examples/mcp/client.py` | [MCP](INTERACTIONS.md#mcp-server) |
| CLI | `EI="uv run ei" sh examples/cli/run.sh` | [CLI](INTERACTIONS.md#cli) |
| Observability | `uv run examples/observability/scrape.py` | [Operations](CONFIGURATION.md#observability) |
| Webhooks | see [`examples/README.md`](../examples/README.md#webhooks) | [Webhooks](INTERACTIONS.md#webhooks) |

Watch the worker: `docker compose -f examples/docker-compose.yml --env-file examples/.env logs -f worker`.
Stop with `sh examples/down.sh` (keep the data) or `sh examples/down.sh --volumes` (delete it).

## Work on the code

```bash
git clone https://github.com/adammatthewsteinberger/engineering-influence
cd engineering-influence
uv sync --extra test --extra runtime --extra api --extra dev --extra publishing
uv run ei --version        # engineering-influence 1.0.0
```

The gates a change must pass are in [CONTRIBUTING.md](../CONTRIBUTING.md) and [TESTING.md](TESTING.md).

## Where to go next

- Let an AI agent run it for you: [AGENTS_DRIVING.md](AGENTS_DRIVING.md).
- Something went wrong: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
- Every variable and what fails closed: [CONFIGURATION.md](CONFIGURATION.md).
- How it is built: [ARCHITECTURE.md](ARCHITECTURE.md).
