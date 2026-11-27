# engineering-influence

**Give it an idea. Get back a book you can publish.**

**BLUF:** engineering-influence writes a complete book, non-fiction or a novel, with nobody in the loop, and
hands you the files Amazon KDP asks for: interior PDF, EPUB, covers, listing and a quality report. One command
installs it, one command writes a book, and a free model on your own machine does the writing.

```bash
# 1. Install everything a book needs (macOS with Homebrew, or Linux with apt-get)
curl -fsSL https://raw.githubusercontent.com/adammatthewsteinberger/engineering-influence/main/install.sh | sh

# 2. Write a book
ei book create --kind nonfiction "how to keep herbs alive indoors" --budget-usd 5 \
  --out ./my-book --profile ~/.config/engineering-influence/author.toml
```

The book lands in `./my-book/run/book/`. Nothing is uploaded: you read it, then you upload it to KDP yourself.

## The idea in one minute

> **Daniel:** I have a book idea and no free months. Everyone says an AI can write it. I asked a chatbot and got
> eleven pages of mush that forgot its own first chapter.
>
> **Professor Feynman:** Of course it did. You asked one cook to make a wedding dinner in one go, from memory,
> without a kitchen. What does a real kitchen have?
>
> **Daniel:** Stations. Somebody preps, somebody cooks, somebody checks the plate before it goes out.
>
> **Professor Feynman:** That is the whole design. A book here goes through stations in order: a brief, research,
> an outline, a draft of each chapter, three editing passes, then typesetting. Each station has one job and
> writes down what it made. So what happens if the power goes out halfway through the draft?
>
> **Daniel:** You would lose the night's work. Unless the finished plates were already on the shelf.
>
> **Professor Feynman:** They are on the shelf. Run the same command with `--resume` and it starts at the next
> station. Nothing finished is cooked twice, and nothing is paid for twice.
>
> **Daniel:** And the last station is the one that checks the plate.
>
> **Professor Feynman:** It builds the real PDF and EPUB and refuses a book that does not pass. The comparison
> stops there, though: a kitchen has a chef who tastes. This has checks, not taste. A person still reads the
> book before it is published. That person is you.
>
> **Daniel:** So it is a kitchen that never loses a plate, and I am still the one who tastes the dinner.

## What you get

| In `my-book/` | What it is |
|---|---|
| `run/book/<slug>.pdf` | The paperback interior, typeset with LaTeX to KDP's trim, margins and gutter |
| `run/book/<slug>.epub` | The ebook, checked for structure and links |
| `run/book/<slug>-ebook.jpg`, `<slug>-paperback-wrap.pdf` | The ebook cover, and the paperback wrap at the exact page count |
| `run/book/listing.md` | Title, subtitle, description and seven keywords, ready to paste |
| `run/book/MANIFEST.json` | What is in the bundle, with a checksum of every file |
| `run/quality-report.json` | Pass or fail, every error and warning, and what was spent against the estimate |
| `src/chapter_NN.md`, `books/*.toml` | The manuscript and its settings, to edit and rebuild with `ei book build` |

[What a KDP-ready package is, exactly](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/BOOKS_AND_KDP.md).

## Three commands worth knowing

```bash
ei doctor --ready                      # can this machine make a book now? every gap, with the fix
ei book create --out ./my-book --resume  # carry on after a crash, a closed laptop or a provider at capacity
ei book create --out ./my-book --resume --approve-spend   # allow the extra budget a stopped run asked for
```

`ei book create` exits `0` when the book is written, `1` when the run failed (what it made is kept, and a failed run is final), `2` when
it could not start, and `3` when it stopped to ask for more budget.

## Let another AI drive it

Claude Code, or any agent with a shell, can run all of this for you. The shortest route:

```bash
curl -fsSL https://raw.githubusercontent.com/adammatthewsteinberger/engineering-influence/main/install.sh | sh -s -- --with-claude-skill
```

That adds a skill to `~/.claude/skills/`. Then say: *"Use engineering-influence to write a non-fiction book
about indoor herbs. My author profile is at ~/.config/engineering-influence/author.toml and the budget is 5
dollars."* The agent checks the machine, starts the run in the background, reads the exit code, and asks you
before it approves any extra spend.
[Driving it from an agent, step by step](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/AGENTS_DRIVING.md).

## Choose your interface

One controller layer, reached six ways.

| You are… | Use | Start here |
|---|---|---|
| At a terminal, wanting a book | `ei book create` | The two commands above |
| An AI agent with a shell | The CLI and the skill | [docs/AGENTS_DRIVING.md](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/AGENTS_DRIVING.md) |
| Calling from any language | REST API | [`examples/api/`](https://github.com/adammatthewsteinberger/engineering-influence/tree/main/examples/api) |
| Writing Python | SDK, sync or async | [`examples/sdk/`](https://github.com/adammatthewsteinberger/engineering-influence/tree/main/examples/sdk) |
| Wiring an AI host to a running stack | MCP server (stdio, `ei serve mcp`) | [`examples/mcp/`](https://github.com/adammatthewsteinberger/engineering-influence/tree/main/examples/mcp) |
| Receiving events | Signed webhooks | [`examples/webhooks/`](https://github.com/adammatthewsteinberger/engineering-influence/tree/main/examples/webhooks) |
| Operating it | Health, metrics, logs | [`examples/observability/`](https://github.com/adammatthewsteinberger/engineering-influence/tree/main/examples/observability) |

The REST API, the SDK, the MCP server and the webhooks need the stack (a database, a broker and a worker):
`sh examples/up.sh` starts one with generated credentials
([Getting started](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/GETTING_STARTED.md#run-the-stack)).
`ei book create` needs none of that.

Prefer to install by hand? `uv tool install "engineering-influence[runtime,publishing,mcp] @ git+https://github.com/adammatthewsteinberger/engineering-influence"`
installs `ei` alone. It is not on PyPI yet. The extras are `api`, `webhooks`, `runtime`, `mcp` and `publishing`
(and `test` and `dev` for contributors).

## Documentation

| Read | For |
|---|---|
| [Getting started](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/GETTING_STARTED.md) | Install, check, write your first book, then run the stack |
| [Driving it from an agent](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/AGENTS_DRIVING.md) | Claude Code or another LLM as the driver |
| [Books and KDP](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/BOOKS_AND_KDP.md) | What a finished package is, what is built and what is not |
| [Novels](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/NOVELS.md) | The novel stages, from brief to a built book |
| [Interfaces](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/INTERACTIONS.md) | Reference for the REST API, SDK, MCP tools, CLI and webhooks |
| [Configuration](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/CONFIGURATION.md) | Every environment variable, security setting and limit |
| [The local model](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/LOCAL_MODEL.md) | The free model that writes by default |
| [Model profiles](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/MODEL_PROFILES.md), [catalog](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/MODEL_CATALOG.md), [calls](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/MODEL_CALLS.md) | Choosing, pricing and calling a model you pay for |
| [Research](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/RESEARCH.md), [tool lock](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/TOOL_LOCK.md) | Web search for the research stage, and approving tool servers |
| [Audiobooks](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/AUDIOBOOKS.md) | The optional ACX text export for Virtual Voice, and a locally narrated audiobook for other stores |
| [Webhooks](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/WEBHOOKS.md) | The events the worker sends to your receivers, the signature, and the delivery rules |
| [Screenplays](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/SCREENPLAYS.md) | The author's source and bible folders, and the card format |
| [Skills](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/SKILLS.md), [plugins](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/PLUGINS.md), [prompts](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/PROMPTS.md) | Adding guidance to a stage, and how the prompts are versioned |
| [Architecture](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/ARCHITECTURE.md) | Layers, request flow, the worker and the extension points |
| [Threat model](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/THREAT_MODEL.md) | What is protected, from whom, and what is not |
| [Evaluation](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/EVALUATION.md), [live smoke test](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/LIVE_SMOKE_TEST.md) | The paid runs that measure quality and cost |
| [Worker image](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/WORKER_IMAGE.md) | The container and the TeX toolchain |
| [Kubernetes deployment](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/DEPLOYMENT.md) | The Helm chart, its Secret and the install steps |
| [Running on minikube](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/MINIKUBE.md) | The whole stack on a local cluster, and the traps it has hit |
| [Test and CI performance](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/TEST_PERFORMANCE.md) | The baseline, what parallel runs changed, and what is still to do |
| [Troubleshooting](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/TROUBLESHOOTING.md) | Symptoms, causes and fixes |
| [Testing](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/TESTING.md), [compatibility](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/COMPATIBILITY.md), [releasing](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/RELEASING.md) | The gates, what is promised to callers, and cutting a release |
| [The documentation site](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/DOCUMENTATION_SITE.md) | How these pages become a website, and how to publish it |
| [How these documents are written](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/STYLE.md) | The page pattern, and who the Professor and Daniel are |
| [Decision records](https://github.com/adammatthewsteinberger/engineering-influence/tree/main/docs/adr), [changelog](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/CHANGELOG.md) | Why it is built this way, and what changed |

## Limitations

Read these before you depend on it.

- **The writing is unproven.** It has run only against scripted servers, never a live model. No real model has
  been measured against the quality bar.
- **A person must read the book.** Checks catch a broken file, not a dull chapter. A fact-check stage accepts a claim
  only when it finds a quotation in a page it read; a claim no page supports is softened or removed, and reported in the
  quality report. It does not judge whether a page is right, so a wrong fact can still pass.
- **Nothing uploads to KDP.** KDP has no publishing API. You upload the files and paste the listing.
- **The first run needs a big download**: about 13 GB for the model and several GB for TeX.
- **A novel gets three editing passes** (story, lines and copy) before its audit and build. It has no continuity repair
  pass yet.
- **On the stack**, delivery is at least once (a crash can re-run a stage), run events go to any receivers you
  configure (see [WEBHOOKS.md](docs/WEBHOOKS.md)), but a failed run sends no event, and the example compose file runs the worker on placeholder text
  (`EI_STAGE_EXECUTOR=deterministic`) until you point it at a model. A worker started any other way uses the free
  local model by default. `ei pipeline start` and the example MCP server only plan work; `ei serve mcp` reaches the stack.
- **The schema is managed by `ei db upgrade`**; run it before starting a new release on the stack.

The full list: [Configuration](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/CONFIGURATION.md).

## About the author and the vibey ecosystem

**BLUF: Krypton and the vibey engine are an open-source Claude Code and OpenAI Codex killer—engineered to replace both completely free of charge, 100% open to everyone, and censorship-free.** Unlike agents that produce unvetted AI slop, the vibey toolchain writes and verifies code the way a Principal Software Engineer does: architected with rigor, backed by 100% branch test coverage, sealed in an append-only cryptographic ledger, and built on an architecture designed for sovereign AGI with superintelligence coming soon.

### Who this is for

Per [ADR 0002](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/docs/adr/0002-audience-priority-and-sovereign-agent-doctrine.md), engineering-influence and the vibey ecosystem prioritize audiences in this strict order:

1. **FOSS developers.** Free and open-source engineers building and running autonomous tools with no subscriptions or telemetry walls.
2. **Freelancers.** Independent operators and consultants delivering Principal-grade fixed-scope client projects with sovereign tools.
3. **Universities and academia.** Researchers and scholars using open, verifiable, and cited methodologies.
4. **Governments and militaries.** Public-sector and defense teams needing air-gapped models, verifiable provenance, and tamper-evident audit trails.
5. **Non-profit orgs.** Mission-driven teams that need budget-preserving, durable software.
6. **Industry teams.** Commercial teams and enterprises seeking production-grade agent infrastructure.

## Contributing, security, support

[CONTRIBUTING.md](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/CONTRIBUTING.md) · [SECURITY.md](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/SECURITY.md) (report privately) ·
[SUPPORT.md](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/SUPPORT.md) · [CODE_OF_CONDUCT.md](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/CODE_OF_CONDUCT.md)

## The book

The author's book on the thinking behind this project is *Engineering Influence: A Playbook for the Remnant to Bring Christian Culture Back to America*: [buy it on Amazon](https://www.amazon.com/dp/B0HPWQFD3Y).

## License

MIT. See [LICENSE](https://github.com/adammatthewsteinberger/engineering-influence/blob/main/LICENSE).
