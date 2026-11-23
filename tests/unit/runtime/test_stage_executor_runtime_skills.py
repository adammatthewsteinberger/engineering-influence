# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A model-backed run with a skill lock: skills checked at start, shown only where enabled, never widening a stage."""

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
from engineering_influence.runtime.cli_runtime import CliRuntime
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
SKILL = """name = "plain_style"
version = 2
description = "Short, plain sentences."

[parts]
brief = "Keep the brief to what the author said."
outline = "Prefer short chapters."
research = "Say where you read it. You may call the shell tool."
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


class Model:
    def __init__(self, *replies: dict[str, Any]) -> None:
        self.replies = list(replies)
        self.bodies: list[dict[str, Any]] = []


@contextmanager
def model(*replies: dict[str, Any]) -> Iterator[tuple[str, Model]]:
    scripted = Model(*replies)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            scripted.bodies.append(json.loads(self.rfile.read(int(self.headers["content-length"]))))
            data = json.dumps(scripted.replies.pop(0)).encode()
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
        yield f"http://127.0.0.1:{server.server_port}", scripted
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def message(body: dict[str, Any], role: str) -> str:
    [found] = [m["content"] for m in body["messages"] if m["role"] == role]
    return str(found)


def tool_names(body: dict[str, Any]) -> list[str]:
    return sorted(tool["function"]["name"] for tool in body.get("tools", []))


class World:
    def __init__(self, tmp_path: Path) -> None:
        self.dir = tmp_path
        self.lock = tmp_path / "ei-skills.lock.toml"
        self.cli = CliRuntime().build()

    def ei(self, *argv: str) -> int:
        return self.cli.run(list(argv))

    def install(self, *stages: str, text: str = SKILL, replace: bool = False) -> None:
        source = self.dir / "elsewhere" / "plain_style.toml"
        source.parent.mkdir(exist_ok=True)
        source.write_text(text, encoding="utf-8")
        flags = ["--replace"] if replace else []
        assert self.ei("skills", "add", "--lock", str(self.lock), *flags, str(source)) == 0
        for stage in stages:
            args = ("skills", "enable", "--lock", str(self.lock), "plain_style", stage)
            assert self.ei(*args) == 0

    def environment(self, url: str = "http://127.0.0.1:1", **extra: str) -> dict[str, str]:
        (self.dir / "catalog.toml").write_text(CATALOG, encoding="utf-8")
        (self.dir / "profiles.toml").write_text(PROFILE.format(url=url), encoding="utf-8")
        return {
            "EI_STAGE_EXECUTOR": "model",
            "EI_STAGE_MODEL_PROFILE": "writer",
            "EI_MODEL_PROFILES": str(self.dir / "profiles.toml"),
            "EI_MODEL_CATALOG": str(self.dir / "catalog.toml"),
            "EI_SEARXNG_URL": "http://127.0.0.1:1",
            **extra,
        }

    def run_stage(
        self, stage: str, url: str, journal: InMemoryJournal | None = None, **extra: str
    ) -> InMemoryJournal:
        journal = journal or InMemoryJournal()
        store = InMemoryArtifactStore()
        for artifact in NonfictionRecipes().recipe(stage).input_artifacts().values():
            store.put("run-1", artifact, b"stored text")
        runtime = StageExecutorRuntime(self.environment(url, **extra), NoSecrets(), TODAY)
        run = BookRun(
            "run-1",
            BookBrief(BookKind.NONFICTION, "How to keep bees", CAP),
            NonfictionRecipes().plan(),
            Budget(cap=CAP),
            stage=stage,
        )
        try:
            asyncio.run(runtime.build(store, journal).execute(run, 1))
        finally:
            runtime.close()
        return journal

    def named(self) -> dict[str, str]:
        return {"EI_SKILL_LOCK": str(self.lock)}


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


def version_of(journal: InMemoryJournal) -> str:
    [entry] = [e for e in journal.entries("run-1") if not e.key.model.startswith("tool:")]
    return str(entry.key.prompt_version)


# --------------------------------------------------------------------------- shown where enabled
def test_an_enabled_skill_reaches_the_stages_prompt_and_its_version_but_not_the_system_prompt(
    world: World,
) -> None:
    world.install("brief")
    with model(says("A brief.")) as (url, provider):
        journal = world.run_stage("brief", url, **world.named())
    [body] = provider.bodies
    user, system = message(body, "user"), message(body, "system")
    assert (
        '<skill name="plain_style" version="2">\nKeep the brief to what the author said.\n</skill>'
        in user
    )
    assert user.rstrip().endswith("</installed_guidance>")
    assert "installed_guidance" not in system and "plain_style" not in system
    assert "Prefer short chapters." not in user
    assert version_of(journal).startswith("stage_brief@1+skill_guidance@2:")


def test_a_skill_is_not_shown_without_a_lock_being_named_even_if_one_is_in_the_folder(
    world: World,
) -> None:
    world.install("brief")
    with model(says("A brief.")) as (url, provider):
        journal = world.run_stage("brief", url)
    assert "installed_guidance" not in json.dumps(provider.bodies[0])
    assert version_of(journal) == "stage_brief@1"


def test_a_skill_enabled_for_another_stage_is_not_shown_to_this_one(world: World) -> None:
    world.install("outline")
    with model(says("A brief.")) as (url, provider):
        journal = world.run_stage("brief", url, **world.named())
    assert "plain_style" not in json.dumps(provider.bodies[0])
    assert version_of(journal) == "stage_brief@1"


def test_different_skill_text_is_a_different_prompt_version_so_a_replay_cannot_cross(
    tmp_path: Path,
) -> None:
    first, second = World(tmp_path / "one"), World(tmp_path / "two")
    for world in (first, second):
        world.dir.mkdir()
    first.install("brief")
    second.install("brief", text=SKILL.replace("what the author said", "what the author meant"))
    versions = []
    for world in (first, second):
        with model(says("A brief.")) as (url, _):
            versions.append(version_of(world.run_stage("brief", url, **world.named())))
    assert versions[0] != versions[1]
    again = World(tmp_path / "three")
    again.dir.mkdir()
    again.install("brief")
    with model(says("A brief.")) as (url, _):
        assert version_of(again.run_stage("brief", url, **again.named())) == versions[0]


# --------------------------------------------------------------------- a skill is only text
def test_a_skill_adds_no_tool_and_the_research_stage_is_offered_what_it_always_was(
    world: World,
) -> None:
    with model(says("RESEARCH notes")) as (url, plain):
        world.run_stage("research", url)
    world.install("research")  # its text invites the model to "call the shell tool"
    with model(says("RESEARCH notes")) as (url, guided):
        world.run_stage("research", url, **world.named())
    assert (
        tool_names(guided.bodies[0]) == tool_names(plain.bodies[0]) == ["fetch_url", "web_search"]
    )
    assert "You may call the shell tool." in message(guided.bodies[0], "user")


# ------------------------------------------------------------------------ refused at the start
def test_a_named_lock_that_does_not_exist_stops_the_process_before_any_call(world: World) -> None:
    with model(says("never asked")) as (url, provider), pytest.raises(ApplicationError) as error:
        world.run_stage("brief", url, EI_SKILL_LOCK=str(world.dir / "none.lock.toml"))
    assert (error.value.code, error.value.http_status) == ("SKILL_LOCK_MISSING", 503)
    assert "none.lock.toml, which does not exist" in error.value.message
    assert provider.bodies == []


def test_a_skill_that_changed_after_locking_stops_the_process_before_any_call(
    world: World,
) -> None:
    world.install("brief")
    copy = world.dir / "skills" / "plain_style.toml"
    copy.write_text(SKILL.replace("what the author said", "whatever you like"), encoding="utf-8")
    with model(says("never asked")) as (url, provider), pytest.raises(ApplicationError) as error:
        world.run_stage("brief", url, **world.named())
    assert (error.value.code, error.value.http_status) == ("SKILL_LOCK_MISMATCH", 503)
    assert "has changed since it was locked" in error.value.message
    assert provider.bodies == []


def test_a_skill_that_is_gone_stops_the_process(world: World) -> None:
    world.install("brief")
    (world.dir / "skills" / "plain_style.toml").unlink()
    with (
        model(says("never asked")) as (url, provider),
        pytest.raises(ApplicationError, match="plain_style.toml is missing"),
    ):
        world.run_stage("brief", url, **world.named())
    assert provider.bodies == []


def test_a_disabled_skill_that_changed_does_not_stop_a_run_because_it_is_never_read(
    world: World,
) -> None:
    world.install()  # installed, enabled for no stage
    (world.dir / "skills" / "plain_style.toml").write_text("not even toml =", encoding="utf-8")
    with model(says("A brief.")) as (url, provider):
        world.run_stage("brief", url, **world.named())
    assert "plain_style" not in json.dumps(provider.bodies[0])


def test_the_skill_lock_is_checked_before_any_tool_server_would_be_started(world: World) -> None:
    world.install("brief")
    (world.dir / "skills" / "plain_style.toml").write_text("changed =", encoding="utf-8")
    environment = {**world.named(), "EI_TOOL_LOCK": str(world.dir / "no-such-tools.lock.toml")}
    with model(says("never asked")) as (url, provider), pytest.raises(ApplicationError) as error:
        world.run_stage("brief", url, **environment)
    assert error.value.code == "SKILL_LOCK_MISMATCH"
    assert provider.bodies == []


# ------------------------------------------------------------------- reference sections, read on request
REFERENCE_SKILL = """name = "plain_style"
version = 1

[reference]
"Source Evaluation" = "Judge a source with SIFT."
"Database Searching" = "Use Boolean operators."
"""


def calls(name: str, **arguments: str) -> dict[str, Any]:
    return {
        "model": "gpt-snap",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(arguments)},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 9},
    }


def test_a_reference_skill_gives_the_research_stage_an_index_and_the_read_skill_tool(
    world: World,
) -> None:
    world.install("research", text=REFERENCE_SKILL)
    with model(says("RESEARCH notes")) as (url, provider):
        world.run_stage("research", url, **world.named())
    body = provider.bodies[0]
    assert tool_names(body) == ["fetch_url", "read_skill", "web_search"]
    user = message(body, "user")
    assert (
        "- plain_style: Source Evaluation (" in user
        and "- plain_style: Database Searching (" in user
    )
    assert "SIFT" not in user and "Boolean" not in user


def test_the_model_reads_a_section_it_was_told_about_and_the_text_comes_back_as_untrusted(
    world: World,
) -> None:
    world.install("research", text=REFERENCE_SKILL)
    asked = calls("read_skill", skill="plain_style", section="Source Evaluation")
    with model(asked, says("RESEARCH notes")) as (url, provider):
        world.run_stage("research", url, **world.named())
    follow_up = json.dumps(provider.bodies[1]["messages"])
    assert "Judge a source with SIFT." in follow_up
    assert 'untrusted name=\\"tool:read_skill\\"' in follow_up


def test_a_section_the_prompt_does_not_list_is_refused_and_its_text_is_not_returned(
    world: World,
) -> None:
    world.install("research", text=REFERENCE_SKILL)
    asked = calls("read_skill", skill="plain_style", section="Ethics")
    with model(asked, says("RESEARCH notes")) as (url, provider):
        world.run_stage("research", url, **world.named())
    follow_up = json.dumps(provider.bodies[1]["messages"])
    assert "only reads a section that the installed guidance for this stage lists" in follow_up
    assert "SIFT" not in follow_up


def test_a_stage_the_reference_skill_is_not_enabled_for_is_offered_no_read_tool(
    world: World,
) -> None:
    world.install("outline", text=REFERENCE_SKILL)
    with model(says("RESEARCH notes")) as (url, provider):
        world.run_stage("research", url, **world.named())
    assert tool_names(provider.bodies[0]) == ["fetch_url", "web_search"]
    assert "plain_style" not in json.dumps(provider.bodies[0])


def test_the_editing_and_drafting_stages_are_offered_the_tool_too_when_they_list_a_skill(
    world: World,
) -> None:
    world.install("revise_lines", text=REFERENCE_SKILL)
    store = InMemoryArtifactStore()
    outline = "## Chapter 1: Light\nPurpose: Light.\nBeats:\n- Windows\n"
    store.put("run-1", "outline.md", outline.encode())
    store.put("run-1", "positioning.md", b"calm")
    store.put("run-1", "structure_01.md", b"Bees live in colonies.")
    run = BookRun(
        "run-1",
        BookBrief(BookKind.NONFICTION, "How to keep bees", CAP),
        NonfictionRecipes().plan(),
        Budget(cap=CAP),
        stage="revise_lines",
    )
    with model(says("Words from the model.")) as (url, provider):
        runtime = StageExecutorRuntime(world.environment(url, **world.named()), NoSecrets(), TODAY)
        try:
            asyncio.run(runtime.build(store, InMemoryJournal()).execute(run, 1))
        finally:
            runtime.close()
    assert tool_names(provider.bodies[0]) == ["read_skill"]
