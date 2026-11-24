# Research: web search and methodology skills

**BLUF:** The research stage gives the model two tools: `web_search` and `fetch_url`. It is told to state a fact
only if a page it read says it, and never to invent a source. That is an instruction, not a check: nothing yet
compares a chapter with its sources. It needs a search provider: a SearXNG you run (free, and one ships in
`examples/searxng/`) or a Brave Search key. `ei doctor --search` sends one real query to each and tells you which
answer.

The research stage of a non-fiction run reads the brief, the positioning and anything the author supplied, then uses two tools,
`web_search` (titles and links) and `fetch_url` (one page), to write research notes that cite only pages it read
([PROMPTS.md](PROMPTS.md), [THREAT_MODEL.md](THREAT_MODEL.md)). This page is how to make that real, and how to check it.

## Cite only what you read

> **Daniel:** Language models invent sources. A confident footnote to a paper that does not exist. How is this any
> different?
>
> **Professor Feynman:** What is the rule for a student writing an essay in a library?
>
> **Daniel:** You may cite a book you took off the shelf and read. Not one you remember hearing about.
>
> **Professor Feynman:** That rule is the stage's instruction. The model can search, which gives it titles and
> links, and it can fetch, which reads one page. It is told to read at most six, and the hard stop is sixteen tool
> calls. It is told to state a fact only if a page it read says it, and never to invent a source, a statistic or a
> link.
>
> **Daniel:** And the page itself could be nonsense.
>
> **Professor Feynman:** It could. And notice what I said: told, not forced. A librarian can check your bag at
> the door; nothing here checks the notes against the pages. That is the limit, and it is why a person still reads
> the book. A claim checker that compares a sentence with the page it cites is not built.
>
> **Daniel:** So the model has real pages in front of it and firm instructions, the checking is still mine, and
> I should confirm a search works before the run with `ei doctor --search`.

## 1. A search that answers

The stage needs a search provider, set in the environment of the process that runs it:

| Variable | |
|---|---|
| `EI_SEARXNG_URL` | A [SearXNG](https://docs.searxng.org/) instance you run or trust, for example `http://127.0.0.1:8888` (the one in `examples/searxng/`). Tried first. |
| `BRAVE_SEARCH_API_KEY` | A Brave Search key, tried behind SearXNG if both are set. |

`examples/searxng/` is a Docker Compose file and a `settings.yml` for a local instance with the one setting this needs:
`json` under `search.formats`, without which SearXNG answers 403.

**Check it before a run spends anything on a model:**

```bash
ei doctor --search
ei doctor --search --query "beekeeping manuals"
```

It sends **one real search to each configured provider**, one at a time (so a SearXNG that is down is not hidden by a Brave key
behind it), and prints a line each: how many links came back and the host of the first. It never prints a title or an address
from the web. The query leaves your machine, to your SearXNG (which passes it to the engines it uses) or to Brave, so the default is
one harmless sentence (`open source book publishing`). Exit `0` all answered, `1` one did not, `2` the setting is unusable
(`EI_SEARXNG_URL` is not an address). With nothing configured it checks the SearXNG a local-model run falls back to (`http://127.0.0.1:8888`); with
`EI_STAGE_EXECUTOR=model` and nothing configured it says how to set one up and exits `1`.

What it does not check: that the results are *good*, that a page fetch works (the fetch tool is pinned to public https
addresses and is separate), or that a Brave key has quota left beyond what one search shows.

The [live smoke test](LIVE_SMOKE_TEST.md) needs this too, and a run with `EI_STAGE_EXECUTOR=model` and no provider stops at start with a clear message. A run on the free local model falls back to the SearXNG at its default address.

## 2. Methodology skills for the research stage

A research methodology is long, which is what reference skills are for ([SKILLS.md](SKILLS.md)): the stage's prompt carries an index of
section titles and the model reads a section only when it needs it, through the locked `read_skill` tool. They are **not shipped with
this project**: they are the author's, so you install them from your own copies, into your own lock, pinned by hash.

From a `SKILL.md` folder:

```bash
ei skills import path/to/research-methodology --reference --out research_methodology.toml
ei skills add research_methodology.toml
ei skills enable research_methodology research
```

From a Claude Code plugin folder that bundles several skills ([PLUGINS.md](PLUGINS.md)):

```bash
ei plugins import path/to/plugin --out my_research.toml
ei plugins show my_research.toml          # read it
ei plugins add my_research.toml           # locks its skills, enabled for no stage
ei skills enable research_methodology research
```

Read the generated file before locking it: its text will be added to a prompt. A section longer than 20,000 characters is refused
with the lengths listed, and you choose around it with `--section`. Enabling a skill for `research` makes the stage offer
`read_skill` with an index, and nothing else changes: the skill grants no tool, and the stage's search and fetch tools are the same.

## 3. Putting it together

```bash
ei doctor --models --probe       # the model profile is usable
ei doctor --search               # the search answers
ei skills list                   # the research stage has its methodology
```

A test in this repository runs the research stage with a synthetic reference skill and a local search server together: the model
reads a section, searches, and both answers come back as untrusted tool output. It has not been run with a live model, and `ei doctor --search`
itself has only been run against local servers written for the tests (the adapter it uses was run once by hand against the compose example, see
[CONFIGURATION.md](CONFIGURATION.md)). No methodology text is bundled to test with.

## What is not built

- A claim-checking stage and a fact tracker across chapters (the research notes list "Not found" claims for a person to source).
- Search for any stage but research. The metadata stage could look for comparable titles; that is a separate decision.
- Any check of how good a methodology skill makes the notes.
