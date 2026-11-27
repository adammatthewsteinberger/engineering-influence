# syntax=docker/dockerfile:1
# One image runs both the API and the worker: `ei serve api` or `ei serve worker`.
#
#   docker build -t engineering-influence:local .                  # the slim image (default)
#   docker build --target worker-tex -t engineering-influence:tex . # the worker with the TeX toolchain
#
# The TeX image is large (the TeX Live packages alone are over a gigabyte). It does what the slim image
# does, plus the tools a book build calls: lualatex, latexmk, tex4ebook, pdftoppm, epubcheck and a Java runtime.

FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY packages ./packages
COPY src ./src
# Locked and non-editable: the runtime image gets exactly the versions in uv.lock. The publishing extra is
# here so the TeX worker can run book commands; it is a few tens of megabytes beside the TeX packages.
RUN uv sync --frozen --no-dev --no-editable --extra api --extra runtime --extra publishing --extra s3 --extra tracing

# The TeX worker. The packages are the ones the CI toolchain job installs, plus zip and tidy: the CI runners
# already have zip, and tex4ebook needs it to pack an EPUB. Recommended packages are not installed.
FROM python:3.13-slim AS worker-tex
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      latexmk texlive-luatex texlive-latex-recommended texlive-latex-extra \
      texlive-pictures texlive-fonts-recommended texlive-plain-generic \
      texlive-extra-utils poppler-utils epubcheck default-jre-headless zip tidy \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
COPY --from=build /app/.venv /app/.venv
# The container's filesystem is read-only except /tmp, and it has no home directory. luaotfload, the font
# loader, keeps its cache under TEXMFCACHE; pointing both variables at /tmp is the configuration that builds
# PDFs and EPUBs here. Other cache directories (a subfolder of /tmp, or a separate tmpfs) did not.
ENV PATH="/app/.venv/bin:${PATH}" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp TEXMFVAR=/tmp TEXMFCACHE=/tmp
USER app
ENTRYPOINT ["ei"]
CMD ["serve", "worker"]

# The slim image. Last, so it stays the default target.
FROM python:3.13-slim
# procps provides ps, which the worker uses to measure a tool's memory; the slim base does not include it.
RUN apt-get update \
 && apt-get install -y --no-install-recommends procps \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER app
ENTRYPOINT ["ei"]
CMD ["serve", "api"]
