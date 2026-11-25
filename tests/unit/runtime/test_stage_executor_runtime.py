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
from engineering_influence.services.novel_recipes import NovelRecipes
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


# A draft long enough that the screen does not call it short: the asked length is 2,500 words by default.
DRAFT = " ".join(["Words from the model."] + ["filler"] * 1_300)


@contextmanager
def provider(text: str, drafts: str | None = None) -> Iterator[tuple[str, Provider]]:
    """Answers ``text``; a draft request (a chapter or section) gets ``drafts`` when one is given."""
    seen = Provider()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            seen.seen.append((self.path, {k.lower(): v for k, v in self.headers.items()}, body))
            drafting = "Write section" in json.dumps(body) or "Write chapter" in json.dumps(body)
            answer = drafts if drafts is not None and drafting else text
            if self.path.endswith("/count_tokens"):
                reply: Any = {"input_tokens": 50}
            elif self.path == "/v1/messages":
                reply = {
                    "content": [{"type": "text", "text": answer}],
                    "stop_reason": "end_turn",
                    "model": "claude-snap",
                    "usage": {"input_tokens": 50, "output_tokens": 9},
                }
            else:
                reply = {
                    "model": "gpt-snap",
                    "choices": [
                        {
                            "message": {"role": "assistant", "content": answer},
                            "finish_reason": "stop",
                        }
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


def test_the_free_local_model_is_the_default() -> None:
    rt = runtime({})
    assert isinstance(build(rt), StageExecutorRouter)
    rt.close()
    assert isinstance(build(runtime({"EI_STAGE_EXECUTOR": "local"})), StageExecutorRouter)


def test_the_offline_placeholder_is_there_when_asked_for() -> None:
    assert isinstance(
        build(runtime({"EI_STAGE_EXECUTOR": "deterministic"})), DeterministicStageExecutor
    )


def test_a_profile_file_alone_does_not_switch_to_your_own_model(tmp_path: Path) -> None:
    with provider("The brief.") as (url, seen):
        environment = files(tmp_path, url=url)
        del environment["EI_STAGE_EXECUTOR"]
        environment["EI_LOCAL_URL"] = url
        rt = runtime(environment)
        executor = build(rt)
        asyncio.run(executor.execute(run_for("brief"), 1))
        rt.close()
    assert seen.seen[-1][2]["model"] == "gpt-oss:20b"


def test_an_unknown_executor_name_is_refused() -> None:
    error = refused(runtime({"EI_STAGE_EXECUTOR": "Model"}))
    assert (error.code, error.http_status) == ("STAGE_EXECUTOR_UNKNOWN", 503)
    assert "'Model'" in error.message
    assert "use 'local', 'model' or 'deterministic'" in error.message


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
    with provider("Words from the model.", drafts=DRAFT) as (url, seen):
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
    assert (store.get("run-1", "chapter_02.md") or b"").startswith(
        b"# Chapter 2: The Site\n\nWords from the model."
    )
    assert store.get("run-1", "summary_02.md") == b"Words from the model."
    index = store.get("run-1", "draft.md")
    assert index is not None and b"Total:" in index
    sent = [json.dumps(body) for _, _, body in seen.seen]
    # The chapters open with different headings, so the second summary asks something new: four calls.
    assert len(sent) == 4
    assert "Chapter 2: The Site" in sent[2] and "the positioning" in sent[2]


LISTING = (
    "Title: Hive Mind\nSubtitle: A calm guide\nDescription:\n"
    + " ".join(["Bees are easier to keep than most people think."] * 10)
    + "\nKeywords:\n"
    + "".join(f"- keyword {n}\n" for n in range(7))
    + "Categories:\n- Books > Science & Math\n"
)
PROFILE_TOML = (
    'author = "Ann Author"\npublisher = "Pub House"\nedition = "First Edition"\n'
    'author_bio = "Ann writes."\nyear = 2031\n'
)


def assemble(tmp_path: Path, **extra: str) -> tuple[InMemoryArtifactStore, list[Any]]:
    outline = "## Chapter 1: The Hive\nPurpose: How a colony works.\nBeats:\n- The queen\n"
    with provider("unused") as (url, seen):
        rt = runtime({**files(tmp_path, url=url), **extra})
        store = InMemoryArtifactStore()
        store.put("run-1", "outline.md", outline.encode())
        store.put("run-1", "metadata.md", LISTING.encode())
        store.put("run-1", "fact_01.md", b"Chapter 1: The Hive\n\nBees live in colonies.")
        executor = rt.build(store, InMemoryJournal())
        asyncio.run(executor.execute(run_for("assemble"), 1))
        rt.close()
    return store, seen.seen


def test_a_novel_is_assembled_from_its_draft_and_keeps_the_dashes_its_prose_has(
    tmp_path: Path,
) -> None:
    outline = "## Chapter 1: The Road\nPurpose: Ana leaves.\nBeats:\n- Ana packs\n"
    brief = BookBrief(BookKind.NOVEL, "A walk to the sea", 5_000_000)
    run = BookRun("run-1", brief, NovelRecipes().plan(), Budget(cap=5_000_000), stage="assemble")
    with provider("unused") as (url, seen):
        rt = runtime(files(tmp_path, url=url))
        store = InMemoryArtifactStore()
        store.put("run-1", "outline.md", outline.encode())
        store.put("run-1", "metadata.md", LISTING.encode())
        store.put(
            "run-1",
            "copy_01.md",
            "# Chapter 1: The Road\n\n\u201cWait\u2014\u201d she said.".encode(),
        )
        asyncio.run(rt.build(store, InMemoryJournal()).execute(run, 1))
        rt.close()
    assert seen.seen == []
    chapter = (store.get("run-1", "manuscript/src/chapter_01.md") or b"").decode()
    assert chapter == "# The Road\n\n\u201cWait\u2014\u201d she said.\n"
    assert b'kind = "novel"' in (store.get("run-1", "manuscript/books/hive-mind.toml") or b"")


def test_an_editing_stage_is_routed_to_the_reviser_and_stores_the_edited_chapter(
    tmp_path: Path,
) -> None:
    outline = "## Chapter 1: The Hive\nPurpose: How a colony works.\nBeats:\n- The queen\n"
    with provider("Words from the model.") as (url, seen):
        rt = runtime(files(tmp_path, url=url))
        store = InMemoryArtifactStore()
        store.put("run-1", "outline.md", outline.encode())
        store.put("run-1", "positioning.md", b"the calm guide")
        store.put("run-1", "structure_01.md", b"Bees live in colonies.")
        executor = rt.build(store, InMemoryJournal())
        asyncio.run(executor.execute(run_for("revise_lines"), 1))
        rt.close()
    assert store.get("run-1", "lines_01.md") == b"Words from the model."
    assert (store.get("run-1", "revise_lines.md") or b"").startswith(b"# Revision: revise_lines")
    sent = json.dumps(seen.seen[-1][2])
    assert "the calm guide" in sent and "Bees live in colonies." in sent and "untrusted" in sent


def test_an_assembled_book_with_an_author_profile_passes_the_real_audit(tmp_path: Path) -> None:
    profile = tmp_path / "author.toml"
    profile.write_text(PROFILE_TOML, encoding="utf-8")
    environment = {**files(tmp_path), "EI_AUTHOR_PROFILE": str(profile)}
    store, _ = assemble(tmp_path, EI_AUTHOR_PROFILE=str(profile))
    rt = runtime(environment)
    asyncio.run(rt.build(store, InMemoryJournal()).execute(run_for("audit"), 1))
    rt.close()
    summary = (store.get("run-1", "audit.md") or b"").decode()
    assert summary.startswith("# Audit\n\nStatus: pass\n\n## Errors\n\nNone.")
    assert "ebook-price-missing" in summary
    for name in ("manuscript-audit.json", "release-readiness.json", "publication-report.json"):
        assert store.get("run-1", f"audit/{name}") is not None


def test_an_assembled_book_without_an_author_profile_still_passes_with_a_warning(
    tmp_path: Path,
) -> None:
    store, _ = assemble(tmp_path)
    rt = runtime(files(tmp_path))
    asyncio.run(rt.build(store, InMemoryJournal()).execute(run_for("audit"), 1))
    rt.close()
    assert "missing-author" in (store.get("run-1", "audit.md") or b"").decode()


def test_the_assemble_stage_is_routed_to_the_assembler_and_calls_no_model(tmp_path: Path) -> None:
    store, requests = assemble(tmp_path)
    assert store.get("run-1", "manuscript/src/chapter_01.md") == (
        b"# The Hive\n\nBees live in colonies.\n"
    )
    config = store.get("run-1", "manuscript/books/hive-mind.toml")
    assert config is not None and b'title = "Hive Mind"' in config and b"author" not in config
    assert requests == []


def test_the_author_profile_the_environment_names_goes_into_the_config(tmp_path: Path) -> None:
    profile = tmp_path / "author.toml"
    profile.write_text(PROFILE_TOML, encoding="utf-8")
    store, requests = assemble(tmp_path, EI_AUTHOR_PROFILE=str(profile))
    config = store.get("run-1", "manuscript/books/hive-mind.toml")
    assert config is not None
    assert b'author = "Ann Author"' in config and b"year = 2031" in config
    assert requests == []


def test_a_named_author_profile_that_is_missing_or_wrong_stops_the_process_at_start(
    tmp_path: Path,
) -> None:
    missing = refused(
        runtime({**files(tmp_path), "EI_AUTHOR_PROFILE": str(tmp_path / "none.toml")})
    )
    assert (missing.code, missing.http_status) == ("AUTHOR_PROFILE_MISSING", 503)
    bad = tmp_path / "bad.toml"
    bad.write_text('author = "A"\n', encoding="utf-8")
    assert refused(runtime({**files(tmp_path), "EI_AUTHOR_PROFILE": str(bad)})).code == (
        "AUTHOR_PROFILE_INVALID"
    )


def test_an_author_profile_nobody_named_is_not_looked_for(tmp_path: Path, monkeypatch: Any) -> None:
    (tmp_path / "author.toml").write_text('author = "A"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert build(runtime(files(tmp_path))) is not None


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


def local_environment(url: str, **extra: str) -> dict[str, str]:
    return {"EI_LOCAL_URL": url, "EI_SEARXNG_URL": "http://127.0.0.1:1", **extra}


def test_the_local_default_runs_a_stage_free_with_no_key_and_low_reasoning() -> None:
    with provider("The brief, written locally.") as (url, seen):
        rt = runtime(local_environment(url))
        store = InMemoryArtifactStore()
        asyncio.run(rt.build(store, InMemoryJournal()).execute(run_for("brief"), 1))
        rt.close()
    assert store.get("run-1", "brief.md") == b"The brief, written locally."
    path, headers, body = seen.seen[-1]
    assert path == "/v1/chat/completions"
    assert "authorization" not in headers
    assert (body["model"], body["reasoning_effort"]) == ("gpt-oss:20b", "low")


def test_another_model_may_be_named_for_the_local_default() -> None:
    with provider("Written.") as (url, seen):
        rt = runtime(local_environment(url, EI_LOCAL_MODEL="  qwen3:14b  "))
        asyncio.run(
            rt.build(InMemoryArtifactStore(), InMemoryJournal()).execute(run_for("brief"), 1)
        )
        rt.close()
    assert seen.seen[-1][2]["model"] == "qwen3:14b"


def test_a_blank_local_setting_means_the_default() -> None:
    with provider("Written.") as (url, seen):
        rt = runtime(local_environment(url, EI_LOCAL_MODEL="  "))
        asyncio.run(
            rt.build(InMemoryArtifactStore(), InMemoryJournal()).execute(run_for("brief"), 1)
        )
        rt.close()
    assert seen.seen[-1][2]["model"] == "gpt-oss:20b"


def test_an_unusable_local_address_stops_the_process_at_start() -> None:
    error = refused(runtime({"EI_LOCAL_URL": "ftp://example.test"}))
    assert (error.code, error.http_status) == ("STAGE_LOCAL_MODEL_INVALID", 503)
    assert "EI_LOCAL_URL" in error.message


def test_the_local_default_needs_no_search_setting() -> None:
    rt = runtime({})
    build(rt)
    rt.close()
    assert StageExecutorRuntime.LOCAL_SEARXNG == "http://127.0.0.1:8888"


def search_for(environment: dict[str, str], **secrets: str) -> Any:
    rt = runtime(environment, **secrets)
    build(rt)
    client = httpx.Client()
    try:
        return rt._search(client)
    finally:
        client.close()
        rt.close()


def test_the_local_default_searches_the_local_searxng_only_when_nothing_else_is_set() -> None:
    assert isinstance(search_for({"EI_STAGE_EXECUTOR": "local"}), SearxngSearchProvider)
    assert isinstance(search_for({"EI_SEARXNG_URL": "http://127.0.0.1:1"}), SearxngSearchProvider)
    assert isinstance(search_for({}, BRAVE_SEARCH_API_KEY="brave-key"), BraveSearchProvider)
    both = search_for({"EI_SEARXNG_URL": "http://127.0.0.1:1"}, BRAVE_SEARCH_API_KEY="brave-key")
    assert isinstance(both, FallbackSearchProvider)


def novel_run(stage: str, **changes: Any) -> BookRun:
    brief = BookBrief(BookKind.NOVEL, "A night nurse meets her brother", 5_000_000, **changes)
    return BookRun("run-1", brief, NovelRecipes().plan(), Budget(cap=5_000_000), stage=stage)


NOVEL_BIBLE = json.dumps({"premise": "A reunion.", "characters": [{"name": "Mara", "age": 34}]})
NOVEL_OUTLINE = "## Chapter 1: The Car Park\nPurpose: They meet.\nBeats:\n- Mara leaves her shift\n"


def execute(rt: StageExecutorRuntime, store: InMemoryArtifactStore, run: BookRun) -> None:
    asyncio.run(rt.build(store, InMemoryJournal()).execute(run, 1))
    rt.close()


def test_a_novel_run_uses_the_novel_prompts_and_carries_the_content_levels() -> None:
    with provider("The novel brief.") as (url, seen):
        store = InMemoryArtifactStore()
        execute(
            runtime(local_environment(url)), store, novel_run("brief", violence="mild", heat="none")
        )
    assert store.get("run-1", "brief.md") == b"The novel brief."
    body = seen.seen[-1][2]
    sent = json.dumps(body)
    assert "fiction imprint" in sent and "Violence: mild. Heat: none." in sent
    assert "A night nurse meets her brother" in sent and "untrusted" in sent


def test_a_novel_brief_with_no_levels_says_not_given() -> None:
    with provider("Written.") as (url, seen):
        execute(runtime(local_environment(url)), InMemoryArtifactStore(), novel_run("brief"))
    assert "Violence: not given. Heat: not given." in json.dumps(seen.seen[-1][2])


def test_the_story_bible_stage_reads_the_brief_and_stores_a_bible_that_parses() -> None:
    with provider(NOVEL_BIBLE) as (url, seen):
        store = InMemoryArtifactStore()
        store.put("run-1", "brief.md", b"the novel brief")
        execute(runtime(local_environment(url)), store, novel_run("story_bible"))
    assert store.get("run-1", "story_bible.md") == NOVEL_BIBLE.encode()
    sent = json.dumps(seen.seen[-1][2])
    assert "continuity editor" in sent and "the novel brief" in sent


def test_a_story_bible_that_cannot_be_read_stops_the_run_and_stores_nothing() -> None:
    with provider("Sorry, no.") as (url, _):
        store = InMemoryArtifactStore()
        store.put("run-1", "brief.md", b"the novel brief")
        rt = runtime(local_environment(url))
        with pytest.raises(ApplicationError) as caught:
            asyncio.run(rt.build(store, InMemoryJournal()).execute(novel_run("story_bible"), 1))
        rt.close()
    assert caught.value.code == "STORY_BIBLE_INVALID"
    assert store.get("run-1", "story_bible.md") is None


def test_the_beats_and_the_outline_stages_read_what_came_before() -> None:
    with provider("1. Mara meets Daniel.") as (url, seen):
        store = InMemoryArtifactStore()
        for name, text in (("brief.md", "the brief"), ("story_bible.md", NOVEL_BIBLE)):
            store.put("run-1", name, text.encode())
        execute(runtime(local_environment(url)), store, novel_run("beats", heat="sweet"))
    sent = json.dumps(seen.seen[-1][2])
    assert "story editor" in sent and "the brief" in sent and "A reunion." in sent
    assert "Heat: sweet." in sent
    with provider(NOVEL_OUTLINE) as (url, seen):
        store = InMemoryArtifactStore()
        for name, text in (
            ("brief.md", "b"),
            ("story_bible.md", NOVEL_BIBLE),
            ("beats.md", "the beats"),
        ):
            store.put("run-1", name, text.encode())
        execute(runtime(local_environment(url)), store, novel_run("outline"))
    assert store.get("run-1", "outline.md") == NOVEL_OUTLINE.encode()
    assert "developmental editor for novels" in json.dumps(seen.seen[-1][2])


def test_a_brief_the_local_model_is_not_recorded_as_allowing_is_refused_before_any_call() -> None:
    with provider("never sent") as (url, seen):
        rt = runtime(local_environment(url))
        with pytest.raises(ApplicationError) as caught:
            asyncio.run(
                rt.build(InMemoryArtifactStore(), InMemoryJournal()).execute(
                    novel_run("brief", violence="graphic"), 1
                )
            )
        rt.close()
    assert caught.value.code == "CONTENT_LEVEL_NOT_ALLOWED"
    assert "set max_violence" in caught.value.message
    assert seen.seen == []


def test_a_nonfiction_run_still_uses_the_nonfiction_prompts_by_default() -> None:
    with provider("The brief.") as (url, seen):
        execute(runtime(local_environment(url)), InMemoryArtifactStore(), run_for("brief"))
    sent = json.dumps(seen.seen[-1][2])
    assert "editor in chief of a non-fiction publishing project" in sent
    assert "fiction imprint" not in sent


def test_a_novel_draft_goes_to_the_novel_drafter_and_records_continuity_findings() -> None:
    outline = "## Chapter 1: The Car Park\nPurpose: They meet.\nBeats:\n- Mara leaves\n"
    bible = json.dumps({"premise": "A reunion.", "characters": [{"name": "Katherine"}]})
    long_draft = " ".join(["Katharine waited in the car park."] + ["filler"] * 1_300)
    with provider("Katharine waited in the car park.", drafts=long_draft) as (url, seen):
        store = InMemoryArtifactStore()
        for name, text in (
            ("brief.md", "the brief"),
            ("story_bible.md", bible),
            ("beats.md", "the beats"),
            ("outline.md", outline),
        ):
            store.put("run-1", name, text.encode())
        rt = runtime(local_environment(url))
        report = asyncio.run(
            rt.build(store, InMemoryJournal()).execute(novel_run("draft", violence="mild"), 1)
        )
        rt.close()
    assert b"Katharine waited in the car park." in (store.get("run-1", "chapter_01.md") or b"")
    assert [item.code for item in report.issues] == ["CONTINUITY_NAME"]
    assert not report.issues[0].blocking
    first = json.dumps(seen.seen[0][2])
    assert "novelist drafting one chapter" in first and "violence mild, heat not given" in first
    assert "the beats" in first and "Katherine" in first


def test_a_novel_draft_the_model_is_not_recorded_as_allowing_is_refused_before_any_call() -> None:
    with provider("never sent") as (url, seen):
        rt = runtime(local_environment(url))
        with pytest.raises(ApplicationError) as caught:
            asyncio.run(
                rt.build(InMemoryArtifactStore(), InMemoryJournal()).execute(
                    novel_run("draft", heat="explicit"), 1
                )
            )
        rt.close()
    assert caught.value.code == "CONTENT_LEVEL_NOT_ALLOWED"
    assert seen.seen == []


def test_a_runtime_that_uses_no_model_has_no_estimate_and_one_that_does_can_say_what_a_book_costs(
    tmp_path: Path,
) -> None:
    from engineering_influence.services.cost_estimator import CostEstimator

    placeholder = runtime({"EI_STAGE_EXECUTOR": "deterministic"})
    assert placeholder.estimator() is None
    build(placeholder)
    assert placeholder.estimator() is None
    with provider("unused") as (url, _):
        own = runtime(files(tmp_path, url=url))
        assert own.estimator() is None
        build(own)
        assert isinstance(own.estimator(), CostEstimator)
        own.close()


def test_the_model_alone_can_be_had_for_a_caller_that_only_needs_to_ask_it(tmp_path: Path) -> None:
    rt = runtime(files(tmp_path))
    try:
        assert rt.model().describe().model == "m"
        assert rt._free is False and rt._client is not None
    finally:
        rt.close()
    assert rt._client is None


def test_the_free_local_model_alone_is_the_default_one() -> None:
    rt = runtime(local_environment("http://127.0.0.1:1"))
    try:
        assert rt.model().describe().model == "gpt-oss:20b"
        assert rt._free is True
    finally:
        rt.close()


@pytest.mark.parametrize("kind", ["deterministic", "mystery"])
def test_a_placeholder_or_unknown_executor_has_no_model_to_hand_over(kind: str) -> None:
    rt = runtime({"EI_STAGE_EXECUTOR": kind})
    with pytest.raises(ApplicationError) as error:
        rt.model()
    assert error.value.code == "STAGE_EXECUTOR_UNKNOWN" and error.value.http_status == 503
