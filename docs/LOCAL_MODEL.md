# The free local model

**BLUF:** By default the book is written by `gpt-oss:20b`, an open-source model running on your own machine
through Ollama. It costs nothing per word and needs no key, and your prompts and manuscript stay on the machine
(the research stage still sends search queries out and fetches public pages). It uses about 13 GB of memory when
loaded and needs a context of 32,768 tokens; `ei doctor --local` checks the server, the model, one tiny answer and
the context it really loaded.

With nothing configured, a run is written by an open-source model on your own machine. It costs nothing per token
and needs no key. The model itself sends nothing off the machine; the research stage's search and page fetches do.

| | |
|---|---|
| Model | `gpt-oss:20b`, Apache 2.0, about 13 GB |
| Server | [Ollama](https://ollama.com) at `http://127.0.0.1:11434` |
| Search for research | a [SearXNG](RESEARCH.md) at `http://127.0.0.1:8888` (the compose example in `examples/searxng`) |
| Context | 32,768 tokens, which the server must really offer |

## Why the context size is checked

> **Daniel:** The model is pulled and it answers. Why does the doctor also fuss about a number called context?
>
> **Professor Feynman:** How much of a long letter can you keep in your head while you write the reply?
>
> **Daniel:** Most of it. If it were fifty pages I would lose the start.
>
> **Professor Feynman:** The context is how much the model can hold at once: its instructions, the outline, what
> came before. This project packs a prompt to fit 32,768 tokens. If the server quietly offers fewer, it does not
> complain. It cuts the prompt short.
>
> **Daniel:** And whatever was cut might be the instructions, or the outline.
>
> **Professor Feynman:** You would not know which. You would get a chapter that reads well and ignores part of
> what it was given, and you would blame the model. So the doctor asks the server what it really loaded. The
> picture is imperfect: you know when you have lost the start of a letter. The model does not.
>
> **Daniel:** So a wrong context fails silently, and the check is the only way I would find out. I will run it
> before the first book.

## Set it up

```bash
ollama pull gpt-oss:20b
OLLAMA_CONTEXT_LENGTH=32768 ollama serve
```

The second line matters. Ollama's own default context is much smaller, and a prompt is assembled to fit the 32,768
tokens this project assumes, so a server that quietly offers less would cut a prompt short. Set the variable wherever
you start Ollama (the macOS app reads it from `launchctl setenv OLLAMA_CONTEXT_LENGTH 32768`), then run
`ei doctor --local` to confirm. A model on a laptop with 24 GB of memory used about 13 GB loaded.

## Use another model or server

`EI_LOCAL_MODEL` names another model and `EI_LOCAL_URL` another server that speaks the OpenAI chat shape (Ollama,
llama.cpp's `llama-server`, vLLM, LM Studio). Both are trimmed, and blank means the default. A model other than the
default is yours to vet: the cost is zero by construction, but the 32,768 window and the `low` reasoning effort are
still what a run assumes.

A model you pay for is `EI_STAGE_EXECUTOR=model` with your own profile and price catalog
([MODEL_PROFILES.md](MODEL_PROFILES.md), [MODEL_CATALOG.md](MODEL_CATALOG.md)); `EI_STAGE_EXECUTOR=deterministic` calls
no model at all.

## Why this model

It was picked by running the four candidates already installed on the author's 24 GB Apple Silicon laptop over three
book-copy tasks (a non-fiction section, a line edit, a fiction scene), each told to use no em or en dashes and none of
six filler words. `gpt-oss:20b` kept to the instruction on every task; `qwen3:14b` (also Apache 2.0) used dashes in
two of three. That is a small test of one person's machine on one afternoon, run while the machine was busy, so its
speeds (12 to 20 tokens a second) are not a benchmark, and it says nothing about quality beyond rule-following. Two
of the other candidates, `gemma4:26b` and `llama3.1:8b`, did not finish the comparison and are not ranked. The licence
matters too: Apache 2.0 is open source, while Gemma's terms and the Llama community licence are open-weight but not.

## Reasoning

`gpt-oss` thinks before it answers, and the thinking counts against a stage's token cap. With the cap at 1,200 tokens
a line edit came back empty, because the thinking used all of it. The default profile therefore sends
`reasoning_effort: low`, which answered the same task in 40 tokens. If you point at a reasoning model of your own, set
`reasoning_effort` in its profile for the same reason.

## Check it: `ei doctor --local`

```bash
ei doctor --local
```

It makes four checks and stops at the first thing that makes the rest pointless:

| Check | Passes when | If it fails |
|---|---|---|
| `server` | something answers at `EI_LOCAL_URL` | install and start Ollama, or set `EI_LOCAL_URL` |
| `model` | the model is pulled | `ollama pull <model>` |
| `answers` | one tiny real completion comes back non-empty | the model spent its whole cap before writing a word |
| `context` | the loaded context is at least 32,768 tokens | set `OLLAMA_CONTEXT_LENGTH` and restart Ollama |

In more detail:

1. **server**: something answers at `EI_LOCAL_URL`. Ollama is recognised by `/api/tags`; another server that speaks the
   chat shape (`llama-server`, vLLM, LM Studio) passes with a note; the `model` and `context` checks are skipped and `answers` still runs.
2. **model**: the model is pulled; if not, it names `ollama pull <model>`.
3. **answers**: one tiny real completion, free and on this machine. An empty reply fails, because a reasoning model
   can spend its whole cap before it writes a word.
4. **context**: the context length Ollama loaded the model with is at least the 32,768 a prompt is assembled to fit.
   If not, it names `OLLAMA_CONTEXT_LENGTH`. Ollama would otherwise cut a prompt short without saying so.

Exit 0 when all held, 1 when one failed, 2 when a setting cannot be used. The first call loads the model into memory,
so it can take a minute. It was run once against the author's Ollama, which loaded the model with a 131,072 context.

## What is not checked yet

Nothing here has been run through a whole book. The first run on a real topic will show whether a 20-billion
parameter model holds a chapter together, and the checks that read a draft (the dash and filler scans, the
continuity checker for novels) catch some of what it gets wrong, not all.
