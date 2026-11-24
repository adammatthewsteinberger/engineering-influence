# Driving it from another AI

**BLUF:** Any agent with a shell (Claude Code, or another LLM that can run commands) can write a book for you
with one command, `ei book create`. Install the skill and ask in plain words; the agent checks the machine,
starts the run in the background, reads the exit code, and comes back to you before it spends anything extra.
Use the MCP server only when a stack is already running.

```bash
curl -fsSL https://raw.githubusercontent.com/adammatthewsteinberger/engineering-influence/main/install.sh | sh -s -- --with-claude-skill
```

Then, in Claude Code:

> Use engineering-influence to write a non-fiction book about keeping herbs alive indoors. My author profile is
> at ~/.config/engineering-influence/author.toml and the budget is 5 dollars.

## Why the command line, and not a server

> **Daniel:** I wired three MCP servers into my agent last month and spent a weekend on credentials. Is this a
> fourth weekend?
>
> **Professor Feynman:** What does your agent already know how to do without being taught?
>
> **Daniel:** Run a command and read what comes back.
>
> **Professor Feynman:** Then give it a command. Think of a vending machine against a restaurant. The restaurant
> needs a kitchen, staff and a table before you get a sandwich. The machine needs a coin and a button. For one
> book, `ei book create` is the machine: one process, a file for its memory, no server, no key.
>
> **Daniel:** A vending machine tells me nothing while it works. How does the agent know what happened?
>
> **Professor Feynman:** By the number the command leaves behind. Zero: the book is written. One: it failed,
> and what it made is kept. Two: it never started. Three: it stopped to ask for more money. An agent can
> branch on four numbers far more reliably than it can read a paragraph.
>
> **Daniel:** Three is the one that worries me. I do not want an agent deciding to spend.
>
> **Professor Feynman:** Nor do I. On three, nothing more is spent until someone runs it again with
> `--approve-spend`, and the skill tells the agent to ask you first. That is the limit of the comparison, by
> the way: a machine keeps your coin. This one stops and waits.
>
> **Daniel:** So the restaurant is for when I am feeding a crowd.
>
> **Professor Feynman:** Many runs, several machines, other programs calling in. Then you run the stack, and
> the agent talks to it over MCP. Until then, it is a weekend you do not need to spend.
>
> **Daniel:** One command, four numbers, and it asks me before it spends. I will start with the machine.

## The quick path: the skill

The skill is one Markdown file,
[`examples/claude-code/engineering-influence/SKILL.md`](../examples/claude-code/engineering-influence/SKILL.md).
The installer copies it to `~/.claude/skills/engineering-influence/SKILL.md` when you pass `--with-claude-skill`.
To add it by hand:

```bash
mkdir -p ~/.claude/skills/engineering-influence
curl -fsSL -o ~/.claude/skills/engineering-influence/SKILL.md \
  https://raw.githubusercontent.com/adammatthewsteinberger/engineering-influence/main/examples/claude-code/engineering-influence/SKILL.md
```

It teaches the agent the five steps below and four rules: never invent an author profile, never approve spend
without your yes, never run a paid evaluation unasked, and never call a book finished unless the exit code
was `0`.

## For any other agent: paste this

An agent without the skill needs only these instructions. They are complete.

```text
You can write a book with the `ei` command. Follow these steps exactly.

1. Run `ei doctor --ready`. If it exits non-zero, stop and tell me each FAIL line. Do not start a run.
2. Ask me for: the idea, the kind (nonfiction or novel), the path to my author profile, and a budget in
   dollars. Never write an author profile yourself.
3. Start the run in the background, because it takes a long time:
     ei book create --kind KIND "IDEA" --budget-usd N --out ./BOOK --profile PROFILE > ./BOOK.log 2>&1
   --out must be a new or empty folder.
4. When it ends, read the exit code:
     0  the book is written: the files are in ./BOOK/run/book/ and the report is ./BOOK/run/quality-report.json
     1  the run failed, and a failed run is final: tell me the `issue:` lines in ./BOOK.log. What it made is
        still in ./BOOK/
     2  it could not start: tell me the error message
     3  it stopped to ask for more budget: ASK ME. Only if I say yes, run
          ei book create --out ./BOOK --resume --approve-spend
5. To continue a run that was interrupted (a crash, a closed terminal):
     ei book create --out ./BOOK --resume
   Finished stages are never run or paid for again. A run that ended in failure (exit 1) is final and
   --resume will not retry it: tell me, and start a new run with a new --out if I ask.

Never pass --approve-spend or --ignore-estimate unless I agreed to that spend in this conversation.
Never set EI_ALLOW_PAID or run `ei evaluate` unless I asked for a paid evaluation.
Report what the quality report says, warnings included. Nothing is uploaded anywhere.
```

## What the agent sees

| Where | What |
|---|---|
| Standard output | An `estimate:` line, then one `stage: outcome` line as each stage finishes, then a summary line |
| Standard error | Errors, and one `issue: CODE: detail` line for each issue the run recorded |
| `BOOK/run/quality-report.json` | The machine-readable result: `status`, errors, warnings, the files with checksums, and a `spend` block |
| `BOOK.state/` | The run's memory. It is what `--resume` reads. Leave it alone |

There is no `--json` flag on `ei book create`: the quality report is the structured output. Every flag and the
full meaning of each exit code is in [INTERACTIONS.md](INTERACTIONS.md#cli).

**Long runs.** A book takes longer than most agents let a foreground command run (Claude Code stops one at ten
minutes), so the run goes in the background and the agent reads the log.

## When a stack is running: MCP

`ei serve mcp` runs the stack's MCP server over stdio. It offers the same runs the REST API does.

**What must already be true:**

1. A database and a broker are running and reachable from the machine the agent is on.
2. The database is migrated: `ei db upgrade`. The MCP server checks this and does not migrate.
3. A worker is running: `ei serve worker`. The MCP server only saves a run and queues it.
4. The worker has a model, a search, an author profile and the TeX tools, or its books will not build.

Register it with the host. For Claude Code:

```bash
claude mcp add engineering-influence \
  --env EI_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB \
  --env EI_RABBITMQ_URL=amqp://USER:PASSWORD@HOST:5672/ \
  -- ei serve mcp
```

For a host that reads a JSON file:

```json
{"mcpServers": {"engineering-influence": {"command": "ei", "args": ["serve", "mcp"],
  "env": {"EI_DATABASE_URL": "postgresql+psycopg://...", "EI_RABBITMQ_URL": "amqp://..."}}}}
```

| Tool | What the agent does with it |
|---|---|
| `create_run` | Starts a book run from a brief: `{"schema_version": 1, "kind": "nonfiction", "idea": "…", "budget_micro_usd": 5000000}` |
| `get_run`, `list_runs` | Watches a run. Nothing is pushed, so the agent polls |
| `resume_run`, `cancel_run` | Continues a parked run, or stops one |
| `read_artifact` | Reads one stored file, up to 1 MiB |
| `grant_run`, `deny_run` | Answers a run's request for more budget. **Offered only when the operator set `EI_MCP_ALLOW_SPEND`** |
| `start_pipeline` | The older stage pipeline, not a book run |

**Limits to know before you choose this path:**

- A run started over MCP may be given at most `EI_MCP_MAX_RUN_BUDGET_MICRO_USD` (five dollars by default);
  more is refused with `BUDGET_ABOVE_LIMIT`.
- A file over 1 MiB, which a book's PDF usually is, cannot be read over MCP (`ARTIFACT_TOO_LARGE`). Fetch it
  with `GET /v1/runs/{id}/artifacts/{name}` and an API key, or with `ei run export RUN_ID DIRECTORY`.
- The example stack (`sh examples/up.sh`) publishes only the API's port, so a server started on your own
  machine cannot reach its database or broker. Point the server at a database and broker you can reach.
- The server has no authentication. It is a local child process of the host and must never be put on a network.
- This path has been tested with scripted clients, not with Claude Code against a live stack.

The full tool reference is in [INTERACTIONS.md](INTERACTIONS.md#mcp-server), and the settings in
[CONFIGURATION.md](CONFIGURATION.md#running-the-stack).

## An editor that speaks the Agent Client Protocol

`ei acp` serves the Agent Client Protocol over standard input and output, with pushed progress and a spend
question the client answers. It also needs the database and the broker. Claude Code is an MCP host, not an ACP
client, so this is for editors that speak ACP: [INTERACTIONS.md](INTERACTIONS.md#agent-client-protocol).
