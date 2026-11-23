# The worker image and the TeX toolchain

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

Not verified: a full book, the compose stack running the TeX worker, and the CI job that builds this target. The
project's compose file still runs the slim image.

## The TeX cache

LuaTeX's font loader (luaotfload) stops with "no writeable cache path" unless `TEXMFCACHE` points at a directory it can
use. Pointing it at `/tmp` works. Pointing it at a subfolder of `/tmp`, or at a separate tmpfs, did not. The reason is
not understood, so the image uses the working setting and says so in the `Dockerfile`.
