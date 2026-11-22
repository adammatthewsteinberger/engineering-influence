# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A stage that uses tools: only its own tools, and a resumed run never pays or searches twice."""

import asyncio
import dataclasses
from collections.abc import Mapping
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_recipe import StageRecipe
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.services.ask_model import AskModel
from engineering_influence.services.call_model import CallModel
from engineering_influence.services.model_stage_executor import ModelStageExecutor
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.run_tool_loop import RunToolLoop
from engineering_influence.services.spend_guard import SpendGuard
from engineering_influence.services.tool_registry import ToolRegistry
from engineering_influence.services.tool_runner import ToolRunner

DESCRIPTOR = ProviderDescriptor(
    provider="fake",
    model="fake-1",
    family="fake",
    context_window=100_000,
    max_output_tokens=8_000,
    input_micro_usd_per_mtok=1_000_000,
    output_micro_usd_per_mtok=5_000_000,
    cache_read_micro_usd_per_mtok=100_000,
    cache_write_micro_usd_per_mtok=1_250_000,
    batch_discount_percent=50,
    price_effective="2026-11-01",
    usage_policy_url="https://example.test/policy",
)
BASE = NonfictionRecipes()
CAP = 5_000_000
USAGE = ModelUsage(100, 50)
LOOKUP = ToolCall("c1", "lookup", {"topic": "bees"})


class Recipes(StageRecipesInterface):
    """The non-fiction recipes, with the brief stage allowed the tools it is given."""

    def __init__(self, *tools: str) -> None:
        self.tools = tools

    def plan(self) -> StagePlan:
        return BASE.plan()

    def recipe(self, stage: str) -> StageRecipe:
        return dataclasses.replace(BASE.recipe(stage), tools=self.tools)


class Lookup(ToolInterface):
    def __init__(self, name: str = "lookup") -> None:
        self.name = name
        self.calls: list[dict[str, Any]] = []

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            self.name,
            "Look a topic up.",
            {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]},
        )

    def invoke(self, arguments: Mapping[str, Any]) -> str:
        self.calls.append(dict(arguments))
        return f"facts about {arguments['topic']}"


class Script(ModelInterface):
    """Answers from a script. An exception in the script is raised instead of answered."""

    def __init__(self, *script: ModelResponse | Exception) -> None:
        self.script = list(script)
        self.requests: list[ModelRequest] = []

    def describe(self) -> ProviderDescriptor:
        return DESCRIPTOR

    def availability(self) -> ModelAvailability:
        return ModelAvailability.AVAILABLE

    def count_tokens(self, request: ModelRequest) -> int:
        return 10

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def says(text: str, *calls: ToolCall) -> ModelResponse:
    return ModelResponse(text, USAGE, "fake-1-snap", "tool_use" if calls else "end_turn", calls)


class World:
    """One run's worth of state that survives a restart: the journal and the artifact store."""

    def __init__(self) -> None:
        self.journal = InMemoryJournal()
        self.store = InMemoryArtifactStore()
        self.tool = Lookup()
        self.secret = Lookup("secret")
        self.run = BookRun(
            "run-1",
            BookBrief(BookKind.NONFICTION, "How to keep bees", CAP),
            BASE.plan(),
            Budget(cap=CAP),
            stage="brief",
        )
        self.runners: list[ToolRunner] = []

    def executor(self, model: Script, *tools: str, offered: bool = True) -> ModelStageExecutor:
        registry = ToolRegistry((self.tool, self.secret) if offered else ())
        limits = ToolLoopLimits()
        runner = ToolRunner(registry, self.journal, limits)
        self.runners.append(runner)
        loop = RunToolLoop(AskModel(CallModel(model, self.journal), model), runner, limits)
        return ModelStageExecutor(
            Recipes(*tools), TomlPromptLibrary(), self.store, loop, registry, SpendGuard
        )

    def go(self, executor: ModelStageExecutor) -> None:
        asyncio.run(executor.execute(self.run, 1))

    def close(self) -> None:
        for runner in self.runners:
            runner.close()


@pytest.fixture
def world() -> Any:
    made = World()
    yield made
    made.close()


def test_a_stage_with_no_tools_offers_none() -> None:
    made = World()
    try:
        model = Script(says("The brief."))
        made.go(made.executor(model))
        assert model.requests[0].tools == ()
    finally:
        made.close()


def test_a_stage_is_offered_exactly_the_tools_its_recipe_names(world: World) -> None:
    model = Script(says("The brief."))
    world.go(world.executor(model, "lookup"))
    assert [t.name for t in model.requests[0].tools] == ["lookup"]


def test_a_recipe_that_names_a_tool_nobody_registered_stops_before_anything_is_asked(
    world: World,
) -> None:
    model = Script(says("never asked"))
    with pytest.raises(ApplicationError) as error:
        world.go(world.executor(model, "lookup", offered=False))
    assert (error.value.code, error.value.http_status) == ("STAGE_TOOL_UNKNOWN", 500)
    assert "'lookup'" in error.value.message
    assert model.requests == []
    assert world.store.names("run-1") == []


def test_a_tool_round_happens_and_the_final_text_is_what_the_stage_keeps(world: World) -> None:
    model = Script(says("checking", LOOKUP), says("The brief, with facts."))
    world.go(world.executor(model, "lookup"))
    assert world.tool.calls == [{"topic": "bees"}]
    assert world.store.get("run-1", "brief.md") == b"The brief, with facts."
    [turn] = model.requests[1].transcript
    assert turn.result_for("c1").content == (
        '<untrusted name="tool:lookup">\nfacts about bees\n</untrusted>'
    )


def test_a_registered_tool_the_stage_was_not_given_is_refused_and_never_runs(
    world: World,
) -> None:
    model = Script(says("", ToolCall("c1", "secret", {"topic": "bees"})), says("Done without it."))
    world.go(world.executor(model, "lookup"))
    assert (world.secret.calls, world.tool.calls) == ([], [])
    [turn] = model.requests[1].transcript
    assert turn.result_for("c1").is_error
    assert turn.result_for("c1").content == "no tool named 'secret' is available here"


def test_a_tool_name_the_model_made_up_is_refused_the_same_way(world: World) -> None:
    model = Script(says("", ToolCall("c1", "ghost", {})), says("Done without it."))
    world.go(world.executor(model, "lookup"))
    [turn] = model.requests[1].transcript
    assert turn.result_for("c1").content == "no tool named 'ghost' is available here"
    assert world.store.get("run-1", "brief.md") == b"Done without it."


def test_a_restart_replays_every_turn_and_tool_call_for_nothing(world: World) -> None:
    first = Script(says("checking", LOOKUP), says("The brief, with facts."))
    world.go(world.executor(first, "lookup"))
    spent = sum(entry.cost_micro_usd for entry in world.journal.entries("run-1"))
    assert spent > 0
    world.store = InMemoryArtifactStore()  # the answer is lost; the journal is not
    restarted = Script()
    world.go(world.executor(restarted, "lookup"))
    assert restarted.requests == []
    assert len(world.tool.calls) == 1
    assert world.store.get("run-1", "brief.md") == b"The brief, with facts."
    assert sum(entry.cost_micro_usd for entry in world.journal.entries("run-1")) == spent


def test_a_run_that_stopped_mid_loop_goes_on_from_the_turn_it_had_not_finished(
    world: World,
) -> None:
    broken = Script(says("checking", LOOKUP), TransientStageError("the provider timed out"))
    with pytest.raises(TransientStageError):
        world.go(world.executor(broken, "lookup"))
    assert len(world.tool.calls) == 1
    resumed = Script(says("The brief, with facts."))
    world.go(world.executor(resumed, "lookup"))
    assert len(resumed.requests) == 1  # turn one was replayed; only turn two was asked
    assert len(resumed.requests[0].transcript) == 1
    assert len(world.tool.calls) == 1  # the lookup was replayed, not run again
    assert world.store.get("run-1", "brief.md") == b"The brief, with facts."
