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

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.deterministic_stage_executor import (
    DeterministicStageExecutor,
)
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime
from engineering_influence.services.model_stage_executor import ModelStageExecutor
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes

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
        assert isinstance(executor, ModelStageExecutor)
        asyncio.run(executor.execute(run_for("brief"), 1))
        rt.close()
    assert store.get("run-1", "brief.md") == b"The brief, written by the model."
    path, headers, body = seen.seen[-1]
    assert path == "/v1/chat/completions"
    assert "authorization" not in headers
    sent = json.dumps(body)
    assert "How to keep bees" in sent and "untrusted" in sent


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
        rt.close()
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
