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
from engineering_influence.models.advance_outcome import AdvanceOutcome
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.run_status import RunStatus
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.ask_model import AskModel
from engineering_influence.services.call_model import CallModel
from engineering_influence.services.failure_classifier import FailureClassifier
from engineering_influence.services.model_stage_executor import ModelStageExecutor
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.spend_guard import SpendGuard

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

    def __init__(self, *script: tuple[str, str]) -> None:
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
        text, stop = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        return ModelResponse(text, ModelUsage(100, 50), "fake-1-snap", stop)


class World:
    def __init__(self, model: Model, cap: int = 5_000_000) -> None:
        self.model = model
        self.runs = InMemoryRunRepository()
        self.journal = InMemoryJournal()
        self.store = InMemoryArtifactStore()
        self.queue = InMemoryQueue()
        self.executor = ModelStageExecutor(
            RECIPES,
            TomlPromptLibrary(),
            self.store,
            AskModel(CallModel(model, self.journal), model),
            SpendGuard,
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


GOOD = (("BRIEF text", "end_turn"), ("POSITIONING text", "end_turn"), ("OUTLINE text", "end_turn"))


def test_a_run_goes_from_brief_to_outline_and_completes_with_each_answer_stored() -> None:
    world = World(Model(*GOOD))
    outcomes = [world.advance(stage) for stage in RECIPES.plan().stages]
    assert outcomes == [AdvanceOutcome.ADVANCED, AdvanceOutcome.ADVANCED, AdvanceOutcome.COMPLETED]
    assert world.run().status is RunStatus.COMPLETED
    assert world.store.names(RUN_ID) == ["brief.md", "outline.md", "positioning.md"]
    assert world.store.get(RUN_ID, "outline.md") == b"OUTLINE text"
    assert world.run().issues == ()


def test_each_stage_is_asked_with_what_the_stages_before_it_wrote() -> None:
    world = World(Model(*GOOD))
    for stage in RECIPES.plan().stages:
        world.advance(stage)
    brief, positioning, outline = world.model.requests
    assert "How to keep bees" in brief.prompt
    assert "BRIEF text" in positioning.prompt
    assert "BRIEF text" in outline.prompt and "POSITIONING text" in outline.prompt
    assert [r.prompt_version for r in world.model.requests] == [
        "stage_brief@1",
        "stage_positioning@1",
        "stage_outline@1",
    ]


def test_spend_is_what_the_calls_cost_and_stays_under_the_cap() -> None:
    world = World(Model(*GOOD))
    for stage in RECIPES.plan().stages:
        world.advance(stage)
    budget = world.run().budget
    assert budget.spent == DESCRIPTOR.cost_micro_usd(ModelUsage(100, 50)) * 3 > 0
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
