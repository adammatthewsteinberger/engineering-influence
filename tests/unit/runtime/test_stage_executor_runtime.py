# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""StageExecutorRuntime: a model is used only when asked for, and a bad setup stops at start."""

import asyncio
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.deterministic_stage_executor import (
    DeterministicStageExecutor,
)
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.research.brave_search_provider import (
    BraveSearchProvider,
)
from engineering_influence.infrastructure.research.searxng_search_provider import (
    SearxngSearchProvider,
)
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime
from engineering_influence.services.fallback_search_provider import FallbackSearchProvider
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.stage_executor_router import StageExecutorRouter

TODAY = date(2026, 11, 21)
KEY = "sk-test-SECRETSECRET"
CATALOG = """
[[model]]
provider = "{provider}"
model = "m"
family = "f"
context_window = 100000
max_output_tokens = 4096
usage_policy_url = "https://example.test/policy"

[[model.price]]
effective = "{effective}"
input = 0
output = 0
cache_read = 0
cache_write = 0
batch_discount_percent = 0
"""
PROFILE = """
[[profile]]
name = "{name}"
adapter = "{adapter}"
provider = "{provider}"
model = "m"
base_url = "{url}"
{extra}
"""


class Secrets(SecretProviderInterface):
    def __init__(self, **values: str) -> None:
        self.values = values

    def require(self, name: str) -> str:
        if name not in self.values:
            raise ApplicationError(code="SECRET_MISSING", message=f"{name} is not set")
        return self.values[name]


class Provider:
    """A local provider that answers both adapters' shapes and keeps what it was sent."""

    def __init__(self) -> None:
        self.seen: list[tuple[str, dict[str, str], Any]] = []


@contextmanager
def provider(text: str) -> Iterator[tuple[str, Provider]]:
    seen = Provider()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            seen.seen.append((self.path, {k.lower(): v for k, v in self.headers.items()}, body))
            if self.path.endswith("/count_tokens"):
                reply: Any = {"input_tokens": 50}
            elif self.path == "/v1/messages":
                reply = {
                    "content": [{"type": "text", "text": text}],
                    "stop_reason": "end_turn",
                    "model": "claude-snap",
                    "usage": {"input_tokens": 50, "output_tokens": 9},
                }
            else:
                reply = {
                    "model": "gpt-snap",
                    "choices": [
                        {"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}
                    ],
                    "usage": {"prompt_tokens": 50, "completion_tokens": 9},
                }
            data = json.dumps(reply).encode()
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
        yield f"http://127.0.0.1:{server.server_port}", seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def files(
    tmp_path: Path,
    *,
    adapter: str = "openai_compatible",
    provider_name: str = "local",
    url: str = "http://127.0.0.1:1",
    extra: str = "",
    effective: str = "2026-01-01",
) -> dict[str, str]:
    catalog = tmp_path / "catalog.toml"
    catalog.write_text(CATALOG.format(provider=provider_name, effective=effective))
    profiles = tmp_path / "profiles.toml"
    profiles.write_text(
        PROFILE.format(name="writer", adapter=adapter, provider=provider_name, url=url, extra=extra)
    )
    return {
        "EI_STAGE_EXECUTOR": "model",
        "EI_STAGE_MODEL_PROFILE": "writer",
        "EI_MODEL_PROFILES": str(profiles),
        "EI_MODEL_CATALOG": str(catalog),
        "EI_SEARXNG_URL": "http://127.0.0.1:1",
    }


def runtime(environment: dict[str, str], **secrets: str) -> StageExecutorRuntime:
    return StageExecutorRuntime(environment, Secrets(**secrets), TODAY)


def build(rt: StageExecutorRuntime) -> Any:
    return rt.build(InMemoryArtifactStore(), InMemoryJournal())


def refused(rt: StageExecutorRuntime) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        build(rt)
    return error.value


def test_the_offline_placeholder_is_the_default() -> None:
    assert isinstance(build(runtime({})), DeterministicStageExecutor)
    assert isinstance(
        build(runtime({"EI_STAGE_EXECUTOR": "deterministic"})), DeterministicStageExecutor
    )


def test_a_profile_file_alone_does_not_switch_to_a_model(tmp_path: Path) -> None:
    environment = files(tmp_path)
    del environment["EI_STAGE_EXECUTOR"]
    assert isinstance(build(runtime(environment)), DeterministicStageExecutor)


def test_an_unknown_executor_name_is_refused() -> None:
    error = refused(runtime({"EI_STAGE_EXECUTOR": "Model"}))
    assert (error.code, error.http_status) == ("STAGE_EXECUTOR_UNKNOWN", 503)
    assert "'Model'" in error.message


@pytest.mark.parametrize(
    "name", ["EI_STAGE_MODEL_PROFILE", "EI_MODEL_PROFILES", "EI_MODEL_CATALOG"]
)
@pytest.mark.parametrize("blank", [None, "", "  "])
def test_a_model_needs_each_setting(tmp_path: Path, name: str, blank: str | None) -> None:
    environment = files(tmp_path)
    if blank is None:
        del environment[name]
    else:
        environment[name] = blank
    error = refused(runtime(environment))
    assert (error.code, error.http_status) == ("STAGE_MODEL_NOT_CONFIGURED", 503)
    assert name in error.message


def test_a_profile_that_is_not_in_the_file_is_refused_with_the_ones_that_are(
    tmp_path: Path,
) -> None:
    environment = files(tmp_path)
    environment["EI_STAGE_MODEL_PROFILE"] = "other"
    error = refused(runtime(environment))
    assert error.code == "STAGE_MODEL_PROFILE_UNKNOWN"
    assert "'other'" in error.message
    assert "it has: writer" in error.message


def test_a_key_that_would_cross_a_network_in_clear_is_refused(tmp_path: Path) -> None:
    environment = files(tmp_path, url="http://models.example.test", extra='api_key_env = "K_ENV"')
    error = refused(runtime(environment, K_ENV=KEY))
    assert (error.code, error.http_status) == ("STAGE_MODEL_KEY_IN_CLEAR", 503)
    assert KEY not in error.message


def test_a_model_with_no_price_in_force_today_is_refused(tmp_path: Path) -> None:
    error = refused(runtime(files(tmp_path, effective="2027-01-01")))
    assert error.code == "MODEL_UNPRICED"


def test_a_missing_key_is_refused_by_the_secret_provider(tmp_path: Path) -> None:
    environment = files(tmp_path, extra='api_key_env = "K_ENV"')
    assert refused(runtime(environment)).code == "SECRET_MISSING"


def run_for(stage: str) -> BookRun:
    brief = BookBrief(BookKind.NONFICTION, "How to keep bees", 5_000_000)
    return BookRun("run-1", brief, NonfictionRecipes().plan(), Budget(cap=5_000_000), stage=stage)


def test_an_openai_compatible_profile_runs_a_stage_against_a_real_server(tmp_path: Path) -> None:
    with provider("The brief, written by the model.") as (url, seen):
        rt = runtime(files(tmp_path, url=url))
        store = InMemoryArtifactStore()
        executor = rt.build(store, InMemoryJournal())
        assert isinstance(executor, StageExecutorRouter)
        asyncio.run(executor.execute(run_for("brief"), 1))
        rt.close()
    assert store.get("run-1", "brief.md") == b"The brief, written by the model."
    path, headers, body = seen.seen[-1]
    assert path == "/v1/chat/completions"
    assert "authorization" not in headers
    sent = json.dumps(body)
    assert "How to keep bees" in sent and "untrusted" in sent


def test_the_draft_stage_is_routed_to_the_drafter_and_writes_every_chapter(
    tmp_path: Path,
) -> None:
    outline = (
        "## Chapter 1: The Hive\nPurpose: How a colony works.\nBeats:\n- The queen\n\n"
        "## Chapter 2: The Site\nPurpose: Where to put it.\nBeats:\n- Sun\n"
    )
    with provider("Words from the model.") as (url, seen):
        rt = runtime(files(tmp_path, url=url))
        store = InMemoryArtifactStore()
        for name, text in (
            ("brief.md", "the brief"),
            ("positioning.md", "the positioning"),
            ("research.md", "the research"),
            ("outline.md", outline),
        ):
            store.put("run-1", name, text.encode())
        executor = rt.build(store, InMemoryJournal())
        asyncio.run(executor.execute(run_for("draft"), 1))
        rt.close()
    assert store.get("run-1", "chapter_02.md") == b"Words from the model."
    assert store.get("run-1", "summary_02.md") == b"Words from the model."
    index = store.get("run-1", "draft.md")
    assert index is not None and b"Total: 8 words" in index
    sent = [json.dumps(body) for _, _, body in seen.seen]
    # The provider says the same words every time, so the second summary asks exactly what the first
    # did and is replayed from the journal: three calls, not four.
    assert len(sent) == 3
    assert "Chapter 2: The Site" in sent[2] and "the positioning" in sent[2]


def test_an_anthropic_profile_runs_a_stage_and_sends_its_key_only_as_a_header(
    tmp_path: Path,
) -> None:
    with provider("An anthropic brief.") as (url, seen):
        environment = files(
            tmp_path,
            adapter="anthropic",
            provider_name="anthropic",
            url=url,
            extra='api_key_env = "K_ENV"',
        )
        rt = runtime(environment, K_ENV=KEY)
        store = InMemoryArtifactStore()
        asyncio.run(rt.build(store, InMemoryJournal()).execute(run_for("brief"), 1))
        rt.close()
    assert store.get("run-1", "brief.md") == b"An anthropic brief."
    assert [path for path, _, _ in seen.seen] == ["/v1/messages/count_tokens", "/v1/messages"]
    for _, headers, body in seen.seen:
        assert headers["x-api-key"] == KEY
        assert KEY not in json.dumps(body)


def test_closing_is_safe_before_a_model_was_built_and_twice_after(tmp_path: Path) -> None:
    rt = runtime({})
    rt.close()
    with provider("x") as (url, _):
        rt = runtime(files(tmp_path, url=url))
        build(rt)
        runner = rt._runner
        assert runner is not None  # the tool threads belong to the runtime
        rt.close()
        assert rt._runner is None  # and are let go with it
        assert runner._pool._shutdown  # after being told to stop, not just forgotten
        rt.close()


def test_the_profiles_output_cap_field_is_the_one_the_server_receives(tmp_path: Path) -> None:
    with provider("Capped.") as (url, seen):
        environment = files(tmp_path, url=url, extra='output_cap_field = "max_completion_tokens"')
        rt = runtime(environment)
        asyncio.run(
            rt.build(InMemoryArtifactStore(), InMemoryJournal()).execute(run_for("brief"), 1)
        )
        rt.close()
    body = seen.seen[-1][2]
    assert "max_completion_tokens" in body
    assert "max_tokens" not in body


# ------------------------------------------------------------------- which search is used
BRAVE = "brave-test-key-0123456789"  # gitleaks:allow


def search_of(environment: dict[str, str], **secrets: str) -> Any:
    rt = runtime(environment, **secrets)
    client = httpx.Client()
    try:
        return rt._search(client)
    finally:
        client.close()


def test_a_local_searxng_alone_is_the_search_when_there_is_no_brave_key(tmp_path: Path) -> None:
    found = search_of(files(tmp_path))
    assert isinstance(found, SearxngSearchProvider)


def test_brave_alone_is_the_search_when_there_is_no_searxng_address(tmp_path: Path) -> None:
    environment = files(tmp_path)
    del environment["EI_SEARXNG_URL"]
    assert isinstance(search_of(environment, BRAVE_SEARCH_API_KEY=BRAVE), BraveSearchProvider)


def test_with_both_searxng_is_tried_first_and_brave_is_the_backup(tmp_path: Path) -> None:
    found = search_of(files(tmp_path), BRAVE_SEARCH_API_KEY=BRAVE)
    assert isinstance(found, FallbackSearchProvider)
    assert isinstance(found._primary, SearxngSearchProvider)
    assert isinstance(found._backup, BraveSearchProvider)


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_a_blank_searxng_address_counts_as_none(tmp_path: Path, blank: str | None) -> None:
    environment = files(tmp_path)
    if blank is None:
        del environment["EI_SEARXNG_URL"]
    else:
        environment["EI_SEARXNG_URL"] = blank
    assert isinstance(search_of(environment, BRAVE_SEARCH_API_KEY=BRAVE), BraveSearchProvider)


def test_a_blank_brave_key_counts_as_none(tmp_path: Path) -> None:
    assert isinstance(search_of(files(tmp_path), BRAVE_SEARCH_API_KEY="  "), SearxngSearchProvider)


def test_no_web_search_at_all_is_refused_at_start_and_says_what_to_set(tmp_path: Path) -> None:
    environment = files(tmp_path)
    del environment["EI_SEARXNG_URL"]
    error = refused(runtime(environment))
    assert (error.code, error.http_status) == ("STAGE_SEARCH_NOT_CONFIGURED", 503)
    assert "EI_SEARXNG_URL" in error.message and "BRAVE_SEARCH_API_KEY" in error.message


def test_a_searxng_address_that_cannot_be_used_is_refused_at_start(tmp_path: Path) -> None:
    environment = files(tmp_path)
    environment["EI_SEARXNG_URL"] = "ftp://search.example"
    error = refused(runtime(environment))
    assert (error.code, error.http_status) == ("STAGE_SEARXNG_URL_INVALID", 503)
    assert "EI_SEARXNG_URL is not usable" in error.message


def test_the_research_client_is_closed_with_the_runtime(tmp_path: Path) -> None:
    with provider("x") as (url, _):
        rt = runtime(files(tmp_path, url=url))
        build(rt)
        research = rt._research_client
        assert research is not None and not research.is_closed
        rt.close()
        assert research.is_closed and rt._research_client is None
