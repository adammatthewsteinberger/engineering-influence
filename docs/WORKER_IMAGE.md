# The worker image and the TeX toolchain

**BLUF:** There are two images. The slim `runtime` image runs the API and the worker. The `worker-tex` image adds
the TeX toolchain a book's last stage, `build`, needs to make the PDF and EPUB. A slim worker still writes every
chapter; only `build` fails, naming the missing tool, and what the earlier stages wrote stays in the run.

## A kitchen with no oven

> **Daniel:** I started the stack, a run went through nine stages, and then it failed at `build`. Everything
> before it looked fine. What did I do wrong?
>
> **Professor Feynman:** Imagine a kitchen that can chop, mix and season, but has no oven. What can it make?
>
> **Daniel:** Everything up to the baking. And then it stops.
>
> **Professor Feynman:** That is the slim worker. It does every writing stage. The `build` stage typesets the book
> with LaTeX and packs an EPUB, which needs the tools in the TeX image. Without them it fails with `BUILD_FAILED`
> and names the missing tool, and the earlier work stays in the run.
>
> **Daniel:** So I lose nothing, I just cannot finish.
>
> **Professor Feynman:** You lose nothing. Switch the worker to the `worker-tex` image and run the last stage
> again. One limit: the TeX image is about 2.9 GB, and only a short test book has been built in it. A full-length
> book has not.
>
> **Daniel:** Slim for writing, TeX for building, and a failed build does not cost me the chapters.


The `Dockerfile` has two images, and `docker build` without a target makes the slim one.

| Target | Command | Size (measured) | For |
|---|---|---|---|
| `runtime` (default) | `docker build -t engineering-influence:local .` | about 1.2 GB | the API and the worker, as `examples/docker-compose.yml` runs them |
| `worker-tex` | `docker build --target worker-tex -t engineering-influence:tex .` | about 2.9 GB | a worker that can build books: LuaLaTeX, latexmk, tex4ebook, pdftoppm, epubcheck, a Java runtime, zip and tidy |

The TeX image has the same packages the CI toolchain job installs, plus `zip` and `tidy` (the CI runners already have
`zip`, but `tex4ebook` needs it to pack an EPUB). Recommended TeX packages are not installed.

## Running it

The container's filesystem is read-only. Only `/tmp` is writable, and the image points TeX's cache there (`HOME`,
`TEXMFVAR` and `TEXMFCACHE` are all `/tmp`). Run it with `--read-only --tmpfs /tmp`, and mount the book project where
the build can write it:

```bash
docker run --rm --read-only --tmpfs /tmp --cap-drop ALL \
  -v "$PWD/my-book:/work" -w /work engineering-influence:tex \
  build demo
```

## What was verified, and what was not

Verified in the image, with the read-only filesystem and all capabilities dropped: every tool runs; `ei book build`
produces `output/demo.pdf` and `ei book epub` produces `output/demo.epub`, and both pass the built-in checks (the EPUB
through epubcheck); `ei book covers` builds the covers. The test book was one short chapter.

A run's own book was built in this image too: the scripted rehearsal of the whole non-fiction plan ends in the `build`
stage, which produced the interior PDF, the EPUB (checked by epubcheck), the ebook, paperback and hardcover covers, the
listing and the release manifest. That check is `tests/toolchain/test_run_builds_book.py`, which the CI toolchain job runs.

Not verified: a full-length book, and the two workflows that build this target (`nightly-eval.yml` and the release `images` job), which have never run.

## Running a stack whose worker builds books

A run's last stage, `build`, calls the TeX tools, so the worker that runs it needs this image. The default compose file
keeps the slim one. Add the override to switch only the worker:

```bash
docker compose -f examples/docker-compose.yml -f examples/docker-compose.tex.yml \
  --env-file examples/.env up -d --build --wait
```

A slim worker still does every writing stage. Only `build` fails (`BUILD_FAILED`), naming the missing tool, and what the
earlier stages wrote stays in the run.

## The TeX cache

LuaTeX's font loader (luaotfload) stops with "no writeable cache path" unless `TEXMFCACHE` points at a directory it can
use. Pointing it at `/tmp` works. Pointing it at a subfolder of `/tmp`, or at a separate tmpfs, did not. The reason is
not understood, so the image uses the working setting and says so in the `Dockerfile`.
