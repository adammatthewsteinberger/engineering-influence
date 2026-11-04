# Contributing

Use Python 3.12 or newer and `uv`.

```sh
uv sync --extra test
uv run ruff check .
uv run mypy --strict src
uv run pytest --cov --cov-branch
```

Changes that introduce a new external integration need a port, an adapter, an
ADR when the choice is architectural, and failure/recovery tests.
