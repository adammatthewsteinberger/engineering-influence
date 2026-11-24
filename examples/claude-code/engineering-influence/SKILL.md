---
name: engineering-influence
description: Write a complete book (non-fiction or a novel) with the `ei` command and get a KDP-ready package (interior PDF, EPUB, covers, listing, quality report). Use when the user asks to write, draft, resume or build a book with engineering-influence, or to check that the machine is ready to.
---

# Writing a book with `ei`

`ei book create` runs every stage in one process and writes the book to a folder. It needs no database,
no server and no API key. A book takes a long time, so run it in the background and read its output.

## 1. Check the machine first

```bash
ei doctor --ready
```

Exit 0 means ready. Otherwise each `FAIL` line says what is missing and what to do. Do not start a run
while a check fails: a run that lacks a TeX tool writes every chapter and then fails at the last stage.
If `ei` is not installed, tell the user the one command and let them run it:
`curl -fsSL https://raw.githubusercontent.com/adammatthewsteinberger/engineering-influence/main/install.sh | sh`

## 2. Ask the user for what only they can give

- The idea, in a sentence or two, and the kind: `nonfiction` or `novel`.
- The path to their author profile (their name, imprint and bio, in TOML). Never invent one, and never
  write the user's details yourself. `ei doctor --ready` reports whether one is named.
- A budget in dollars. It is required even with the free local model, where it is only a cap.

## 3. Start the run, in the background

```bash
ei book create --kind nonfiction "IDEA" --budget-usd 5 --out ./BOOK --profile /path/to/author.toml \
  > ./BOOK.log 2>&1
```

`--out` must be a new or empty folder. Optional: `--title`, `--audience`, `--target-words N`,
`--trim-size 5x8|5.5x8.5|6x9`, `--strict-release` (needs `[pricing]` in the profile).
The log gets an `estimate:` line, then one `stage: outcome` line per stage, then a summary.

## 4. Read the exit code

| Exit | Meaning | What to do |
|---|---|---|
| 0 | The book is written | The files are in `BOOK/run/book/`; read `BOOK/run/quality-report.json` |
| 1 | The run failed; what it made is still in `BOOK/` | Read the `issue: CODE: detail` lines in the log and tell the user |
| 2 | It could not start | The message says why: a missing idea, kind, budget or profile, or a budget below the estimate |
| 3 | It stopped to ask for more budget; nothing was lost | **Ask the user.** Only if they agree: `ei book create --out ./BOOK --resume --approve-spend` |

## 5. Continue a run that stopped

```bash
ei book create --out ./BOOK --resume
```

Finished stages are never paid for again. Use this after a crash, a closed terminal or a fixed problem.

## Rules

- Never pass `--approve-spend` or `--ignore-estimate` unless the user said yes to that spend in this conversation.
- Never set `EI_ALLOW_PAID`, and never run `ei evaluate`, unless the user asked for a paid evaluation.
- Report what the quality report says, including warnings. Do not call a book finished if the exit code was not 0.
- Nothing is uploaded anywhere: a person reviews the files and uploads them to KDP.

## If a stack is running instead

With a database, a broker and a worker already running, the same runs are available over MCP:
register `ei serve mcp` as a stdio server with `EI_DATABASE_URL` and `EI_RABBITMQ_URL` set, then use
`create_run`, `get_run`, `list_runs`, `resume_run`, `cancel_run` and `read_artifact`. `docs/INTERACTIONS.md`
has the details and the limits.
