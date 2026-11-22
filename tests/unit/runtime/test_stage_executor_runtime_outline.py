# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A model-backed run: the outline must be readable as chapters, or the run stops before it is stored."""

import asyncio
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes

TODAY = date(2026, 11, 22)
CAP = 5_000_000
CATALOG = """
[[model]]
provider = "local"
model = "m"
family = "f"
context_window = 100000
max_output_tokens = 4096
usage_policy_url = "https://example.test/policy"

[[model.price]]
effective = "2026-01-01"
input = 0
output = 0
cache_read = 0
cache_write = 0
batch_discount_percent = 0
"""
PROFILE = """
[[profile]]
name = "writer"
adapter = "openai_compatible"
provider = "local"
model = "m"
base_url = "{url}"
"""
OUTLINE = """## Chapter 1: The Hive
Purpose: Show how a colony works.
Beats:
- Workers, drones and the queen
- Winter
Claims to source:
- A colony holds up to 60,000 bees
Leads to: From the hive to the apiary.

## Chapter 2: The Apiary
Purpose: Choose where hives go.
Beats:
- Sun and shelter
Claims to source:
"""


class NoSecrets(SecretProviderInterface):
    def require(self, name: str) -> str:
        raise ApplicationError(code="SECRET_MISSING", message=f"{name} is not set")


def says(text: str) -> dict[str, Any]:
    return {
        "model": "gpt-snap",
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 9},
    }


@contextmanager
def model(*replies: dict[str, Any]) -> Iterator[str]:
    queue = list(replies)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["content-length"]))
            data = json.dumps(queue.pop(0)).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def execute(tmp_path: Path, stage: str, url: str) -> InMemoryArtifactStore:
    (tmp_path / "catalog.toml").write_text(CATALOG, encoding="utf-8")
    (tmp_path / "profiles.toml").write_text(PROFILE.format(url=url), encoding="utf-8")
    environment = {
        "EI_STAGE_EXECUTOR": "model",
        "EI_STAGE_MODEL_PROFILE": "writer",
        "EI_MODEL_PROFILES": str(tmp_path / "profiles.toml"),
        "EI_MODEL_CATALOG": str(tmp_path / "catalog.toml"),
        "EI_SEARXNG_URL": "http://127.0.0.1:1",
    }
    store = InMemoryArtifactStore()
    for artifact in NonfictionRecipes().recipe(stage).input_artifacts().values():
        store.put("run-1", artifact, b"stored text")
    runtime = StageExecutorRuntime(environment, NoSecrets(), TODAY)
    run = BookRun(
        "run-1",
        BookBrief(BookKind.NONFICTION, "How to keep bees", CAP),
        NonfictionRecipes().plan(),
        Budget(cap=CAP),
        stage=stage,
    )
    try:
        asyncio.run(runtime.build(store, InMemoryJournal()).execute(run, 1))
    finally:
        runtime.close()
    return store


def test_an_outline_that_reads_as_chapters_is_stored(tmp_path: Path) -> None:
    with model(says(OUTLINE)) as url:
        store = execute(tmp_path, "outline", url)
    assert store.get("run-1", "outline.md") == OUTLINE.encode("utf-8")


def test_an_outline_that_does_not_read_as_chapters_stops_the_run_and_is_not_stored(
    tmp_path: Path,
) -> None:
    store = InMemoryArtifactStore()
    with (
        model(says("Here are some thoughts about bees.")) as url,
        pytest.raises(ApplicationError) as error,
    ):
        store = execute(tmp_path, "outline", url)
    assert (error.value.code, error.value.http_status) == ("OUTLINE_INVALID", 422)
    assert "each chapter starts with a heading like '## Chapter 1: Title'" in error.value.message
    assert store.names("run-1") == []


def test_a_stage_whose_text_nothing_parses_accepts_prose(tmp_path: Path) -> None:
    with model(says("Just some prose, no chapters.")) as url:
        store = execute(tmp_path, "positioning", url)
    assert store.get("run-1", "positioning.md") == b"Just some prose, no chapters."
