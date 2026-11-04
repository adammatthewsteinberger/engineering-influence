# syntax=docker/dockerfile:1
# One image runs both the API and the worker: `ei serve api` or `ei serve worker`.

FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY packages ./packages
COPY src ./src
# Locked and non-editable: the runtime image gets exactly the versions in uv.lock.
RUN uv sync --frozen --no-dev --no-editable --extra api --extra runtime

FROM python:3.13-slim
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER app
ENTRYPOINT ["ei"]
CMD ["serve", "api"]
