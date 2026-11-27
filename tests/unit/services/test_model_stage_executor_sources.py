# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A stage whose template asks for sources gets every source file the run keeps, each under its number."""

import asyncio

from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.model_answer import ModelAnswer
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.services.interfaces.ask_model_interface import AskModelInterface
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface
from engineering_influence.services.lock_tool_grants import LockToolGrants
from engineering_influence.services.model_stage_executor import ModelStageExecutor
from engineering_influence.services.no_output_checks import NoOutputChecks
from engineering_influence.services.no_stage_guidance import NoStageGuidance
from engineering_influence.services.run_tool_loop import RunToolLoop
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes
from engineering_influence.services.spend_guard import SpendGuard
from engineering_influence.services.tool_registry import ToolRegistry
from engineering_influence.services.tool_runner import ToolRunner

CAP = 5_000_000


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
        return ModelAnswer("## S01 · a scene", True, (), 0, 1, False)


def prompt_for(store: InMemoryArtifactStore) -> str:
    recipes = ScreenplayRecipes()
    registry = ToolRegistry(())
    limits = ToolLoopLimits()
    asker = Asker()
    executor = ModelStageExecutor(
        recipes,
        TomlPromptLibrary(),
        store,
        RunToolLoop(asker, ToolRunner(registry, InMemoryJournal(), limits), limits),
        registry,
        LockToolGrants(ToolLock()),
        NoStageGuidance(),
        NoOutputChecks(),
        lambda budget: SpendGuard(Budget(cap=CAP)),
    )
    run = BookRun(
        run_id="run-1",
        brief=BookBrief(BookKind.SCREENPLAY, "a film", CAP),
        plan=recipes.plan(),
        budget=Budget(cap=CAP),
        stage="scene_cards",
    )
    asyncio.run(executor.execute(run, 1))
    return asker.requests[0].prompt


def stored(*sources: tuple[str, bytes]) -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    store.put("run-1", "brief.md", b"brief")
    store.put("run-1", "anchors.md", b"anchors")
    store.put("run-1", "beats.md", b"beats")
    for name, data in sources:
        store.put("run-1", name, data)
    return store


def test_every_source_the_run_keeps_reaches_the_prompt_under_its_number() -> None:
    prompt = prompt_for(stored(("source/002.md", b"second"), ("source/001.md", b"first")))
    assert (
        '<untrusted name="sources">\nSource 001:\nfirst\n\nSource 002:\nsecond\n</untrusted>'
        in prompt
    )


def test_with_no_source_files_the_block_says_so() -> None:
    assert '<untrusted name="sources">\nnot given\n</untrusted>' in prompt_for(stored())


def test_when_a_run_has_digests_the_digests_reach_the_prompt_instead_of_the_sources() -> None:
    prompt = prompt_for(
        stored(("source/001.md", b"the whole first source"), ("digest/001.md", b"a short digest"))
    )
    assert "Source 001:\na short digest" in prompt
    assert "the whole first source" not in prompt
