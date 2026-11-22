# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A non-fiction run through the real AdvanceRun, CallModel and AskModel, with a scripted model."""

import asyncio

import pytest

from engineering_influence.errors.budget_exceeded_error import BudgetExceededError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.interfaces.source_fetcher_interface import SourceFetcherInterface
from engineering_influence.models.advance_outcome import AdvanceOutcome
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.fetched_page import FetchedPage
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.search_hit import SearchHit
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.ask_model import AskModel
from engineering_influence.services.call_model import CallModel
from engineering_influence.services.failure_classifier import FailureClassifier
from engineering_influence.services.fetch_url_tool import FetchUrlTool
from engineering_influence.services.model_stage_executor import ModelStageExecutor
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.run_tool_loop import RunToolLoop
from engineering_influence.services.spend_guard import SpendGuard
from engineering_influence.services.tool_registry import ToolRegistry
from engineering_influence.services.tool_runner import ToolRunner
from engineering_influence.services.web_search_tool import WebSearchTool

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
RECIPES = NonfictionRecipes()
RUN_ID = "run-1"


class Model(ModelInterface):
    """Answers each call from a script, and keeps every request it was sent."""

    def __init__(self, *script: tuple[str, str] | tuple[str, str, tuple[ToolCall, ...]]) -> None:
        self.script = list(script)
        self.requests: list[ModelRequest] = []

    def describe(self) -> ProviderDescriptor:
        return DESCRIPTOR

    def availability(self) -> ModelAvailability:
        return ModelAvailability.AVAILABLE

    def count_tokens(self, request: ModelRequest) -> int:
        return 100

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        step = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        calls = step[2] if len(step) == 3 else ()
        return ModelResponse(step[0], ModelUsage(100, 50), "fake-1-snap", step[1], calls)


class Search(SearchProviderInterface):
    def search(self, query: str, count: int) -> tuple[SearchHit, ...]:
        return (SearchHit("https://example.test/bees", "All about bees"),)


class Fetcher(SourceFetcherInterface):
    def fetch(self, url: str) -> FetchedPage:
        return FetchedPage(url, "Bees", "A colony holds tens of thousands of bees.")


class World:
    def __init__(self, model: Model, cap: int = 5_000_000) -> None:
        self.model = model
        self.runs = InMemoryRunRepository()
        self.journal = InMemoryJournal()
        self.store = InMemoryArtifactStore()
        self.queue = InMemoryQueue()
        registry = ToolRegistry((WebSearchTool(Search()), FetchUrlTool(Fetcher())))
        limits = ToolLoopLimits()
        loop = RunToolLoop(
            AskModel(CallModel(model, self.journal), model),
            ToolRunner(registry, self.journal, limits),
            limits,
        )
        self.executor = ModelStageExecutor(
            RECIPES, TomlPromptLibrary(), self.store, loop, registry, SpendGuard
        )
        self.service = AdvanceRun(
            self.runs, self.journal, self.executor, self.queue, FailureClassifier()
        )
        self.runs.save(
            BookRun(
                RUN_ID,
                BookBrief(BookKind.NONFICTION, "How to keep bees", cap),
                RECIPES.plan(),
                Budget(cap=cap),
            )
        )

    def advance(self, stage: str, attempt: int = 1) -> AdvanceOutcome:
        return asyncio.run(self.service.advance(RUN_ID, stage, attempt))

    def run(self) -> BookRun:
        stored = self.runs.get(RUN_ID)
        assert stored is not None
        return stored


SEARCH = ToolCall("s1", "web_search", {"query": "bee colonies"})
FETCH = ToolCall("f1", "fetch_url", {"url": "https://example.test/bees"})
GOOD = (
    ("BRIEF text", "end_turn"),
    ("POSITIONING text", "end_turn"),
    ("searching", "tool_use", (SEARCH,)),
    ("reading", "tool_use", (FETCH,)),
    ("RESEARCH text", "end_turn"),
    ("OUTLINE text", "end_turn"),
)


def test_a_run_goes_from_brief_to_outline_and_completes_with_each_answer_stored() -> None:
    world = World(Model(*GOOD))
    outcomes = [world.advance(stage) for stage in RECIPES.plan().stages]
    assert outcomes == [AdvanceOutcome.ADVANCED] * 3 + [AdvanceOutcome.COMPLETED]
    assert world.run().status is RunStatus.COMPLETED
    assert world.store.names(RUN_ID) == ["brief.md", "outline.md", "positioning.md", "research.md"]
    assert world.store.get(RUN_ID, "research.md") == b"RESEARCH text"
    assert world.store.get(RUN_ID, "outline.md") == b"OUTLINE text"
    assert world.run().issues == ()


def test_each_stage_is_asked_with_what_the_stages_before_it_wrote() -> None:
    world = World(Model(*GOOD))
    for stage in RECIPES.plan().stages:
        world.advance(stage)
    brief, positioning, searching, reading, research, outline = world.model.requests
    assert "How to keep bees" in brief.prompt
    assert "BRIEF text" in positioning.prompt
    assert "BRIEF text" in research.prompt and "POSITIONING text" in research.prompt
    assert "BRIEF text" in outline.prompt and "POSITIONING text" in outline.prompt
    assert "RESEARCH text" in outline.prompt
    assert [r.prompt_version for r in world.model.requests] == [
        "stage_brief@1",
        "stage_positioning@1",
        "stage_research@1",
        "stage_research@1",
        "stage_research@1",
        "stage_outline@2",
    ]
    assert [len(r.transcript) for r in (searching, reading, research)] == [0, 1, 2]
    assert [t.name for t in searching.tools] == ["web_search", "fetch_url"]
    assert all(r.tools == () for r in (brief, positioning, outline))


def test_what_the_research_tools_return_reaches_the_model_marked_as_untrusted() -> None:
    world = World(Model(*GOOD))
    for stage in RECIPES.plan().stages:
        world.advance(stage)
    final = world.model.requests[4]
    searched, fetched = final.transcript
    found = searched.result_for("s1").content
    assert found.startswith('<untrusted name="tool:web_search">\n1. All about bees')
    assert "https://example.test/bees" in found and found.endswith("</untrusted>")
    page = fetched.result_for("f1").content
    assert page.startswith('<untrusted name="tool:fetch_url">\nSource: https://example.test/bees')
    assert "tens of thousands of bees" in page


def test_spend_is_what_the_calls_cost_and_stays_under_the_cap() -> None:
    world = World(Model(*GOOD))
    for stage in RECIPES.plan().stages:
        world.advance(stage)
    budget = world.run().budget
    assert budget.spent == DESCRIPTOR.cost_micro_usd(ModelUsage(100, 50)) * 6 > 0
    assert (budget.reserved, budget.spent <= budget.cap) == (0, True)


def test_asking_again_for_a_stage_that_already_has_its_answer_costs_nothing() -> None:
    world = World(Model(*GOOD))
    world.advance("brief")
    spent = world.run().budget.spent
    run = world.run()
    brief_run = BookRun(RUN_ID, run.brief, run.plan, Budget(cap=run.budget.cap), stage="brief")
    asyncio.run(world.executor.execute(brief_run, 2))
    assert len(world.model.requests) == 1
    assert sum(e.cost_micro_usd for e in world.journal.entries(RUN_ID)) == spent


def test_a_redelivered_stage_does_not_call_the_model_again() -> None:
    world = World(Model(*GOOD))
    world.advance("brief")
    assert world.advance("brief") is AdvanceOutcome.REPAIRED
    assert len(world.model.requests) == 1


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_a_refused_or_cut_off_answer_fails_the_run_and_builds_nothing_on_it(stop: str) -> None:
    world = World(Model(("no", stop)))
    assert world.advance("brief") is AdvanceOutcome.FAILED
    run = world.run()
    assert run.status is RunStatus.FAILED
    assert [(i.code, i.blocking) for i in run.issues] == [("stage-failed", True)]
    assert run.issues[0].detail.startswith("ApplicationError: brief: ")
    assert world.store.names(RUN_ID) == []
    assert world.queue.jobs == []
    assert run.budget.spent > 0


def test_a_cap_too_small_for_the_worst_case_stops_the_run_before_any_call() -> None:
    world = World(Model(*GOOD), cap=10)
    assert world.advance("brief") is AdvanceOutcome.FAILED
    assert world.model.requests == []
    assert world.run().budget.spent == 0
    assert BudgetExceededError.__name__ in world.run().issues[0].detail
