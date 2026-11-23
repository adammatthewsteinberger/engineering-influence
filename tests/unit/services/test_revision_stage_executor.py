# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""RevisionStageExecutor: every chapter is edited in order, only plausible edits are kept, and nothing is redone."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.interfaces.stage_guidance_interface import StageGuidanceInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.guidance import Guidance
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.revision_pass import RevisionPass
from engineering_influence.models.stage_report import StageReport
from engineering_influence.models.tool_loop_result import ToolLoopResult
from engineering_influence.services.interfaces.run_tool_loop_interface import (
    RunToolLoopInterface,
)
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface
from engineering_influence.services.no_stage_guidance import NoStageGuidance
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.nonfiction_revision_passes import NonfictionRevisionPasses
from engineering_influence.services.outline_parser import OutlineParser
from engineering_influence.services.revision_stage_executor import RevisionStageExecutor
from engineering_influence.services.spend_guard import SpendGuard

CAP = 5_000_000
STRUCTURE, LINES, COPY = NonfictionRevisionPasses.PASSES
OUTLINE = """## Chapter 1: The Hive
Purpose: Show how a colony works.
Beats:
- The queen

## Chapter 2: The Site
Purpose: Pick a place for the hive.
Beats:
- Sun and shade

## Chapter 3: The Suit
Purpose: Dress for the work.
Beats:
- Veils
"""
SOURCES = {n: f"Chapter {n} text. " + "bees " * 40 for n in (1, 2, 3)}
SUMMARIES = {1: "Colonies work as one.\n", 2: "Put it in the sun.", 3: "Wear a veil."}


def done(text: str) -> ToolLoopResult:
    return ToolLoopResult(text, True, (), 0, 1, 0, 1, ())


def cut(text: str = "partial") -> ToolLoopResult:
    issue = QualityIssue("revise", "TRUNCATED", "the answer was cut off", blocking=True)
    return ToolLoopResult(text, False, (issue,), 0, 1, 0, 1, ())


class Loop(RunToolLoopInterface):
    """Answers each request with the chapter it was given plus one word, unless scripted."""

    def __init__(self, *scripted: ToolLoopResult) -> None:
        self.scripted = list(scripted)
        self.calls: list[tuple[SpendGuardInterface, str, str, int, ModelRequest]] = []

    def run(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ToolLoopResult:
        self.calls.append((guard, run_id, stage, attempt, request))
        if self.scripted:
            return self.scripted.pop(0)
        source = next(text for text in SOURCES.values() if text in request.prompt)
        return done(source + " edited")


class FixedGuidance(StageGuidanceInterface):
    def for_stage(self, stage: str) -> Guidance:
        return Guidance("ADVICE: be kind", "skill_guidance@1:abc")


class World:
    def __init__(
        self,
        editing: RevisionPass = STRUCTURE,
        *scripted: ToolLoopResult,
        stored: dict[str, str] | None = None,
        window: int = 200_000,
        model_max: int = 32_000,
        guidance: StageGuidanceInterface | None = None,
    ) -> None:
        self.editing = editing
        self.store = InMemoryArtifactStore()
        self.loop = Loop(*scripted)
        self.budgets: list[Budget] = []
        self.guard = SpendGuard(Budget(cap=CAP))
        self.executor = RevisionStageExecutor(
            editing,
            self.store,
            TomlPromptLibrary(),
            OutlineParser(),
            self.loop,
            guidance or NoStageGuidance(),
            self._guard,
            window,
            model_max,
        )
        self.run = BookRun(
            run_id="run-1",
            brief=BookBrief(BookKind.NONFICTION, "bees", CAP),
            plan=NonfictionRecipes().plan(),
            budget=Budget(cap=CAP, spent=7),
            stage=editing.stage,
        )
        files = (
            {
                "outline.md": OUTLINE,
                "positioning.md": "POSITIONING: the calm guide",
                **{f"{editing.source}_{n:02d}.md": text for n, text in SOURCES.items()},
                **{f"summary_{n:02d}.md": text for n, text in SUMMARIES.items()},
            }
            if stored is None
            else stored
        )
        for name, text in files.items():
            self.store.put("run-1", name, text.encode("utf-8"))

    def _guard(self, budget: Budget) -> SpendGuardInterface:
        self.budgets.append(budget)
        return self.guard

    def execute(self, attempt: int = 1) -> StageReport:
        return asyncio.run(self.executor.execute(self.run, attempt))

    def refused(self) -> ApplicationError:
        with pytest.raises(ApplicationError) as error:
            self.execute()
        return error.value

    def text(self, name: str) -> str | None:
        data = self.store.get("run-1", name)
        return None if data is None else data.decode("utf-8")

    def out(self, number: int) -> str | None:
        return self.text(f"{self.editing.output}_{number:02d}.md")


def test_it_is_a_stage_executor() -> None:
    assert isinstance(World().executor, StageExecutorInterface)


def test_each_chapter_is_revised_in_order_and_stored_under_the_passes_output_name() -> None:
    world = World()
    assert world.execute() == StageReport()
    assert len(world.loop.calls) == 3
    assert [world.out(n) for n in (1, 2, 3)] == [SOURCES[n] + " edited" for n in (1, 2, 3)]
    assert world.text("chapter_01.md") == SOURCES[1]


def test_the_list_gives_each_chapters_length_before_and_after() -> None:
    world = World()
    world.execute()
    assert world.text("revise_structure.md") == (
        "# Revision: revise_structure\n\n"
        "- Chapter 1: The Hive (43 to 44 words)\n"
        "- Chapter 2: The Site (43 to 44 words)\n"
        "- Chapter 3: The Suit (43 to 44 words)\n"
    )


def test_one_spend_guard_from_the_runs_budget_serves_every_call() -> None:
    world = World()
    world.execute(attempt=4)
    assert world.budgets == [world.run.budget]
    assert {call[0] for call in world.loop.calls} == {world.guard}
    assert {call[1:4] for call in world.loop.calls} == {("run-1", "revise_structure", 4)}


def test_the_structure_pass_is_given_the_outline_what_the_others_say_this_chapters_plan_and_the_chapter() -> (
    None
):
    world = World()
    world.execute()
    request = world.loop.calls[1][4]
    assert request.prompt_version == "stage_revise_structure@1"
    assert "## Chapter 3: The Suit" in request.prompt
    assert "Chapter 1: Colonies work as one." in request.prompt
    assert "Chapter 3: Wear a veil." in request.prompt
    assert "Chapter 2: Put it in the sun." not in request.prompt
    assert "Chapter 2: The Site\nPurpose: Pick a place for the hive." in request.prompt
    assert request.prompt.count("Purpose: Pick a place for the hive.") == 2
    assert "Chapter 1: Colonies work as one.\nChapter 3: Wear a veil." in request.prompt
    assert SOURCES[2] in request.prompt
    assert "POSITIONING" not in request.prompt
    assert "untrusted" in request.system and request.tools == ()


def test_the_lines_pass_is_given_the_voice_and_the_chapter_and_not_the_outline() -> None:
    world = World(LINES)
    world.execute()
    request = world.loop.calls[0][4]
    assert "POSITIONING: the calm guide" in request.prompt and SOURCES[1] in request.prompt
    assert "Purpose:" not in request.prompt and "Colonies work as one" not in request.prompt
    assert [world.out(n) for n in (1, 2, 3)] == [SOURCES[n] + " edited" for n in (1, 2, 3)]


def test_the_copy_pass_is_given_only_the_chapter() -> None:
    world = World(
        COPY, stored={"outline.md": OUTLINE, **{f"lines_{n:02d}.md": t for n, t in SOURCES.items()}}
    )
    world.execute()
    request = world.loop.calls[0][4]
    assert SOURCES[1] in request.prompt
    assert "Purpose:" not in request.prompt and "POSITIONING" not in request.prompt
    assert world.out(3) == SOURCES[3] + " edited"


def test_the_output_cap_is_the_chapters_words_at_the_passes_top_ratio_plus_room_within_the_models_limit() -> (
    None
):
    world = World()
    world.execute()
    assert world.loop.calls[0][4].max_output_tokens == int(43 * 1.6 * 1.2) + 400
    small = World(model_max=450)
    small.execute()
    assert small.loop.calls[0][4].max_output_tokens == 450


def test_skills_ride_the_prompt_and_name_themselves_in_the_version() -> None:
    world = World(guidance=FixedGuidance())
    world.execute()
    request = world.loop.calls[0][4]
    assert request.prompt.endswith("\n\nADVICE: be kind")
    assert request.prompt_version == "stage_revise_structure@1+skill_guidance@1:abc"


def test_a_chapter_that_is_done_is_not_revised_again_and_the_rest_are() -> None:
    world = World()
    world.store.put("run-1", "structure_01.md", b"already revised")
    world.execute()
    assert len(world.loop.calls) == 2
    assert world.out(1) == "already revised"
    assert world.out(2) == SOURCES[2] + " edited"


@pytest.mark.parametrize(
    ("editing", "low", "high"), [(STRUCTURE, 80, 120), (LINES, 90, 110), (COPY, 95, 105)]
)
def test_the_length_bounds_are_exact_for_each_pass(
    editing: RevisionPass, low: int, high: int
) -> None:
    source = "word " * 100
    for words, kept in ((low - 1, False), (low, True), (high, True), (high + 1, False)):
        answer = "other " * words
        world = World(
            editing,
            done(answer),
            stored={
                "outline.md": OUTLINE.split("\n\n")[0],
                "positioning.md": "p",
                "summary_01.md": "s",
                f"{editing.source}_01.md": source,
            },
        )
        world.execute()
        assert world.out(1) == (answer if kept else source), (editing.stage, words)


@pytest.mark.parametrize(
    "answer", ["", "   \n ", "A short essay about the chapter.", "word " * 400]
)
def test_an_edit_that_is_blank_or_the_wrong_length_is_not_kept_and_the_chapter_passes_through(
    answer: str,
) -> None:
    world = World(STRUCTURE, done(answer))
    report = world.execute()
    assert world.out(1) == SOURCES[1]
    assert world.out(2) == SOURCES[2] + " edited"
    assert report.issues == (
        QualityIssue(
            "revise_structure",
            "revision-unchanged",
            "chapter 1 came back from revise_structure unchanged",
            blocking=False,
        ),
    )
    assert "- Chapter 1: The Hive (43 to 43 words, unchanged)" in (
        world.text("revise_structure.md") or ""
    )


def test_an_edit_that_changed_nothing_is_reported_even_though_it_was_plausible() -> None:
    world = World(STRUCTURE, done(SOURCES[1]))
    assert [i.detail for i in world.execute().issues] == [
        "chapter 1 came back from revise_structure unchanged"
    ]


def test_a_redelivered_stage_reports_the_same_unchanged_chapters_without_calling_again() -> None:
    world = World(STRUCTURE, done("too short"))
    first = world.execute()
    calls = len(world.loop.calls)
    assert world.execute().issues == first.issues
    assert len(world.loop.calls) == calls


def test_an_answer_that_did_not_finish_stops_the_stage_and_keeps_the_chapters_before_it() -> None:
    world = World(STRUCTURE, done(SOURCES[1] + " edited"), cut())
    error = world.refused()
    assert (error.code, error.http_status) == ("STAGE_ANSWER_UNUSABLE", 502)
    assert error.message == "revise_structure: chapter 2: TRUNCATED: the answer was cut off"
    assert world.out(1) == SOURCES[1] + " edited"
    assert world.out(2) is None and world.text("revise_structure.md") is None


def test_missing_inputs_are_named_for_each_pass() -> None:
    error = World(stored={}).refused()
    assert (error.code, error.http_status) == ("STAGE_INPUT_MISSING", 409)
    assert "outline.md" in error.message
    lines = World(LINES, stored={"outline.md": OUTLINE}).refused()
    assert "positioning.md" in lines.message
    copy = World(COPY, stored={"outline.md": OUTLINE, "lines_02.md": "x"}).refused()
    assert "lines_01.md, lines_03.md" in copy.message and "lines_02.md" not in copy.message
    no_summaries = World(
        stored={
            "outline.md": OUTLINE,
            **{f"chapter_{n:02d}.md": t for n, t in SOURCES.items()},
            "summary_02.md": "s",
        }
    ).refused()
    assert "summary_01.md, summary_03.md" in no_summaries.message
    assert World(STRUCTURE, stored={"outline.md": OUTLINE}).refused().code == "STAGE_INPUT_MISSING"


def test_an_unreadable_outline_stops_the_stage_before_any_call() -> None:
    world = World(stored={"outline.md": "just prose", "positioning.md": "p"})
    assert world.refused().code == "OUTLINE_INVALID"
    assert world.loop.calls == []


def test_a_window_too_small_for_the_prompt_and_the_answer_stops_before_the_call() -> None:
    world = World(window=1_000)
    error = world.refused()
    assert (error.code, error.http_status) == ("STAGE_MODEL_TOO_SMALL", 422)
    assert error.message.startswith(
        "revise_structure: the model's window of 1000 tokens leaves 6 for the prompt "
        "after room for a 482 token answer, and this chapter's prompt is about "
    )
    assert world.loop.calls == []


def test_a_window_smaller_than_the_answer_and_the_margin_reports_no_room_at_all() -> None:
    error = World(window=500).refused()
    assert "window of 500 tokens leaves 0 for the prompt" in error.message


def test_a_window_that_fits_the_biggest_prompt_exactly_is_used_and_one_less_is_not() -> None:
    probe = World()
    probe.execute()
    needed = max((len(c[4].system) + len(c[4].prompt)) // 3 + 1 for c in probe.loop.calls)
    cap = probe.loop.calls[0][4].max_output_tokens
    exact = needed + cap + 512
    World(window=exact).execute()
    with pytest.raises(ApplicationError):
        World(window=exact - 1).execute()


def test_a_window_or_an_output_limit_below_one_is_not_a_model() -> None:
    for window, limit in ((0, 10), (10, 0)):
        with pytest.raises(ValueError, match="window and an output limit"):
            RevisionStageExecutor(
                STRUCTURE,
                InMemoryArtifactStore(),
                TomlPromptLibrary(),
                OutlineParser(),
                Loop(),
                NoStageGuidance(),
                SpendGuard,
                window,
                limit,
            )
