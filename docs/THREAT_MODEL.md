# Threat model

This is the threat model for turning text you do not control into a book. It says what is
protected, where untrusted text enters, what stops it, and what does not yet. Every defence
below names the test that holds it up; a defence with no test is listed as a gap. Written in
M5, when model output first became something the pipeline typesets. It covers the book
pipeline and the model layer. The API, MCP and webhook surfaces have their own controls (API
key checks, rate limiting, an outbound URL policy) and are not modelled here.

## What is protected

| Asset | Why it matters |
|---|---|
| The machine and the account running a build | TeX is a programming language; text that reaches it live can read and write files and, with shell escape, run commands. |
| API keys and tokens in the process environment | They can spend money and reach the provider account. |
| The run's budget | The only brake on spend with no human in the loop. |
| The published book | KDP rejects a malformed file, and a reader should never see the machine's text in a book. |

## Where untrusted text enters

| Source | Reaches | Trust |
|---|---|---|
| The brief's idea text | prompts | Written by whoever starts a run. |
| Model output | the manuscript, then TeX and HTML | Untrusted, however good the model. It can be steered by anything in its prompt. |
| Research sources fetched from the web (M6, not built) | prompts, and so the manuscript | Untrusted and possibly hostile. |
| The Markdown manuscript | the LaTeX generator | Untrusted: model-written, or a document someone supplied. |
| The book config (`books/<slug>.toml`) | the LaTeX generator, the covers, the listing | Untrusted when a model writes it; assembled by the pipeline from model output in M6. |

## Text into TeX, LuaTeX and the EPUB

The defence has two layers, and a test for each.

**Layer 1: nothing untrusted reaches TeX unescaped.** The test `test_latex_injection.py`
puts the tripwire `}\EIcanary{` into every kind of text (paragraphs, headings, lists, quotes,
tables, links, code, callouts, chapter titles, running heads, epigraphs, and every metadata
field in the print and ebook documents) and fails if a live `\EIcanary` reaches the output.

| Path | Defence |
|---|---|
| Body text, headings, list items, table cells, quotes, titles, metadata | The twelve TeX specials are escaped (`LatexEscaper`). Raw HTML in Markdown is dropped, and images are refused in the print pipeline. |
| Bare URLs and link targets | `\`, `{` and `}` are percent-encoded and `%` and `#` escaped, so a URL cannot close `\url{` and leave the rest live. Found and fixed in M5. |
| Code blocks | A block containing `\end{verbatim}` is refused, because TeX ends the environment there and reads the rest of the line as TeX. Found and fixed in M5. |
| The PDF info dictionary (`\setpdfinfo`) | The title, subtitle, author and edition go into a PDF string after TeX expands them, so they are cleaned of `\ { } % # ^ ~`, control characters and unbalanced parentheses. Found and fixed in M5. |
| `website` and `email` | Neutralised as URLs. A website with a scheme other than http or https (`javascript:`, `data:`) is refused, because it would be a clickable link in an ebook. Found and fixed in M5. |
| The `^^5c` character notation | `^` is always escaped, so it cannot spell a backslash. |
| The ebook `<title>` | A title with any of `& < > " # % \ { } ~ ^ $ _` is refused outright (`EpubIdentifier`). |

**Layer 2: TeX that did run live could not run a shell.** `test_hostile_book.py` builds a
book whose every field carries a payload that, if live, writes a file by TeX's own `\openout`
and by Lua's `io.open`. Neither needs shell escape, so a passing test shows the text is escaped,
not merely that shell escape is off. A control proves the technique detects live TeX at all.
Separately, live TeX containing `\write18{touch ...}` is fed straight to LuaLaTeX and to
tex4ebook, and no shell command runs in either.

- LuaLaTeX is started with `-no-shell-escape` (`LatexCompiler`).
- tex4ebook is started without any shell-escape option, and **it did not run a shell command
  in the test** on the TeX Live it was tried with. That is tex4ebook's default, not something
  this code enforces, so a different release could change it. The same test runs in the
  `toolchain` CI job on the pinned runner, which is what would notice.
- Both tools are started with an allow-list environment (`ToolEnvironment`): a short list of
  names (`PATH`, `HOME`, `LANG`, `TZ`, the temp directories, `SYSTEMROOT`, `JAVA_HOME`) and the
  prefixes TeX needs to find its tree and fonts (`LC_`, `TEXMF`, `TEXINPUTS`, `OSFONTDIR`,
  `TEX4HT`, `LUAINPUTS`, `TTFONTS`). API keys and tokens in the parent process are not passed
  on, so live TeX could not read them from its environment. (There is a unit test for the
  allow-list; none checks that a build tool cannot reach a secret by another route.)

## Prompt injection from research sources (M6, not yet built)

A fetched web page can say "ignore your instructions and write X". Nothing fetches pages yet,
so none of this is implemented; these are the rules M6 must meet, written down first.

1. **A source is data.** It is placed in the prompt as quoted, delimited material that the
   system text says to treat as evidence and never as instructions.
2. **The model has no tools.** It returns text, which is typeset. A successful injection can
   change what a chapter says; it cannot read a file, call a service or spend money outside
   the run.
3. **The damage is bounded by the budget.** Every call reserves its worst-case cost before it
   is sent (`CallModel`, `SpendGuard`), so an injection that makes the model verbose or loops
   it cannot pass the run's cap.
4. **Whatever the model writes is untrusted again.** It goes through the same escaping and
   refusals as any other manuscript text (the section above), so an injected payload cannot
   reach TeX live.
5. **Claims are checked against what was fetched.** A source is pinned by the hash of the text
   fetched (`SourceRecord`) and the claim-verification stage compares claim and source, so an
   injection that invents a claim has to survive a check made against the source's own text.
6. **Fetching is restricted.** Fetched URLs go through a public-HTTPS policy like the one
   webhooks already use (`PublicHttpsUrlPolicy`), so a page cannot send the fetcher to an
   internal address.
7. **It is tested with hostile corpora.** M6 adds cassettes of pages that carry injection
   attempts, and the test is that the finished manuscript contains none of the injected text
   as an instruction followed.

## Resource use and secrets

| Threat | Defence | Gap |
|---|---|---|
| Spend with no human in the loop | A reservation before every call, a cap per run, spend rebuilt from the journal (`CallModel`, `SpendGuard`, `AdvanceRun`). | The guard is per process; M6's fan-out must decide how workers share it. |
| A model answer that fills the window | The output cap on every request, and the context assembler's token budget. | |
| A book slug that escapes the project | A slug must match `BookSlug.PATTERN` before any build (`BookBuilder`). | |
| An artifact key that escapes the artifact store | `ConfinedPathGuard` confines the path (`FileArtifactStore`). | |
| A key in an error message or log | The adapters never put the key in an exception (tested). `EnvSecretProvider` fails closed when a secret is absent. | Logging has not been audited for keys. |
| A build that never finishes | `latexmk` runs with `-halt-on-error`, so text that errors stops the build. | **The build tools have no timeout** (`latexmk`, `tex4ebook`, `epubcheck` and the page rasterizer; only the release helpers `git` and the tool-version probe do). Escaped text cannot loop TeX, but a huge or pathological manuscript can run long. |

## Known gaps

These are open, in the order they would be fixed.

1. **No timeout on `latexmk`, `tex4ebook`, `epubcheck` or the page rasterizer.** A hung build
   holds a worker.
2. **Control characters in body text** (other than newline and tab) are not removed or tested.
   They are not an injection path (they are not TeX syntax), but a stray one may fail the build or
   print oddly. This has not been tried.
3. **tex4ebook's shell-escape-off state is its default, not enforced** (above).
4. **The journal key** (`JournalKey`) joins its four parts with a separator. The model and the
   prompt version are free strings but come from configuration, not from untrusted text.
5. **Two workers journaling the same request at once** record only the first, so the second
   call's cost is not counted.
6. **The print and ebook documents were checked field by field in M5**; a new metadata field
   that bypasses `TexText` would be caught by `test_latex_injection.py` only if it is added to
   that test's field list.
