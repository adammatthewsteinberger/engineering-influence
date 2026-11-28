# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ModelStageExecutor offers a stage its recipe's tools and the locked tools the lock grants it, no others."""

import asyncio
import dataclasses
from collections.abc import Mapping
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.model_answer import ModelAnswer
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_recipe import StageRecipe
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.services.interfaces.ask_model_interface import AskModelInterface
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface
from engineering_influence.services.lock_tool_grants import LockToolGrants
from engineering_influence.services.model_stage_executor import ModelStageExecutor
from engineering_influence.services.no_output_checks import NoOutputChecks
from engineering_influence.services.no_stage_guidance import NoStageGuidance
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.run_tool_loop import RunToolLoop
from engineering_influence.services.spend_guard import SpendGuard
from engineering_influence.services.tool_registry import ToolRegistry
from engineering_influence.services.tool_runner import ToolRunner

BASE = NonfictionRecipes()
A = "a" * 64


class Named(ToolInterface):
    def __init__(self, name: str) -> None:
        self.name = name

    def definition(self) -> ToolDefinition:
        return ToolDefinition(self.name, f"The {self.name} tool.", {"type": "object"})

    def invoke(self, arguments: Mapping[str, Any]) -> str:
        return self.name


class Asker(AskModelInterface):
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def ask(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ModelAnswer:
        self.requests.append(request)
        return ModelAnswer("A fine answer.", True, (), 0, 1, False)


class Recipes(StageRecipesInterface):
    def __init__(self, *tools: str) -> None:
        self.tools = tools

    def plan(self) -> StagePlan:
        return BASE.plan()

    def recipe(self, stage: str) -> StageRecipe:
        return dataclasses.replace(BASE.recipe(stage), tools=self.tools)


def lock(*grants: tuple[str, str, tuple[str, ...]]) -> ToolLock:
    """One server per name, each granting the given tools to the given stage."""
    names: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
    for server, stage, tools in grants:
        names.setdefault(server, []).append((stage, tools))
    servers = []
    for server, stages in names.items():
        every = tuple(sorted({tool for _, tools in stages for tool in tools}))
        servers.append(
            McpServerLock(
                name=server,
                command=("/usr/bin/s",),
                files=(("/usr/bin/s", A),),
                env=(),
                server_name="s",
                server_version="1",
                tool_names=every,
                tools_hash=A,
                grants=tuple(sorted((s, t) for s, t in stages)),
            )
        )
    return ToolLock(tuple(servers))


def offered(
    recipe_tools: tuple[str, ...],
    tool_lock: ToolLock,
    stage: str = "research",
    registered: tuple[str, ...] = (),
    servers: tuple[str, ...] | None = None,
) -> tuple[list[str], Asker]:
    names = registered or ("native", "files__read", "files__write", "other__x")
    registry = ToolRegistry(tuple(Named(name) for name in names))
    limits = ToolLoopLimits()
    asker = Asker()
    loop = RunToolLoop(asker, ToolRunner(registry, InMemoryJournal(), limits), limits)
    store = InMemoryArtifactStore()
    for artifact in ("brief.md", "positioning.md"):
        store.put("run-1", artifact, b"text")
    executor = ModelStageExecutor(
        Recipes(*recipe_tools),
        TomlPromptLibrary(),
        store,
        loop,
        registry,
        LockToolGrants(tool_lock),
        NoStageGuidance(),
        NoOutputChecks(),
        SpendGuard,
    )
    run = BookRun(
        "run-1",
        BookBrief(BookKind.NONFICTION, "How to keep bees", 5_000_000),
        BASE.plan(),
        Budget(cap=5_000_000),
        stage=stage,
        servers=servers,
    )
    asyncio.run(executor.execute(run, 1))
    return [tool.name for tool in asker.requests[0].tools], asker


def test_a_stage_with_no_grant_is_offered_only_its_recipes_tools() -> None:
    assert offered(("native",), ToolLock())[0] == ["native"]


def test_a_stage_is_offered_its_recipes_tools_then_what_the_lock_grants_it() -> None:
    names, _ = offered(("native",), lock(("files", "research", ("read", "write"))))
    assert names == ["native", "files__read", "files__write"]


def test_a_granted_tool_the_recipe_already_names_is_offered_once() -> None:
    names, _ = offered(("files__read",), lock(("files", "research", ("read", "write"))))
    assert names == ["files__read", "files__write"]


def test_a_stage_with_no_recipe_tools_can_still_be_granted_some() -> None:
    names, _ = offered((), lock(("files", "research", ("read",))))
    assert names == ["files__read"]


def test_a_grant_to_another_stage_offers_nothing_here() -> None:
    names, _ = offered(("native",), lock(("files", "outline", ("read",))), stage="research")
    assert names == ["native"]


def test_grants_from_several_servers_are_all_offered_in_server_name_order() -> None:
    tool_lock = lock(("other", "research", ("x",)), ("files", "research", ("read",)))
    names, _ = offered((), tool_lock)
    assert names == ["files__read", "other__x"]


def test_a_granted_tool_nobody_registered_stops_the_stage_before_anything_is_asked() -> None:
    with pytest.raises(ApplicationError) as error:
        offered((), lock(("files", "research", ("read",))), registered=("native",))
    assert (error.value.code, error.value.http_status) == ("STAGE_TOOL_UNKNOWN", 500)
    assert "files__read" in error.value.message


def test_a_run_that_selected_some_servers_is_offered_only_their_granted_tools() -> None:
    tool_lock = lock(("files", "research", ("read",)), ("other", "research", ("x",)))
    names, _ = offered((), tool_lock, servers=("other",))
    assert names == ["other__x"]


def test_a_run_that_selected_no_servers_is_offered_no_locked_tools() -> None:
    names, _ = offered(("native",), lock(("files", "research", ("read",))), servers=())
    assert names == ["native"]
