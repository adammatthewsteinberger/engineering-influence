"""Drafting a novel: the bible and the beats in the prompt, the levels in the instruction, continuity recorded."""

import asyncio
import json
from collections.abc import Mapping
from dataclasses import replace

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.draft_checks_interface import DraftChecksInterface
from engineering_influence.models.assembled_context import AssembledContext
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.context_plan import ContextPlan
from engineering_influence.models.draft_recipe import DraftRecipe
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.stage_report import StageReport
from engineering_influence.models.tool_loop_result import ToolLoopResult
from engineering_influence.services.answer_screen import AnswerScreen
from engineering_influence.services.continuity_checker import ContinuityChecker
from engineering_influence.services.draft_stage_executor import DraftStageExecutor
from engineering_influence.services.interfaces.answer_screen_interface import (
    AnswerScreenInterface,
)
from engineering_influence.services.interfaces.context_assembler_interface import (
    ContextAssemblerInterface,
)
from engineering_influence.services.interfaces.run_tool_loop_interface import (
    RunToolLoopInterface,
)
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface
from engineering_influence.services.no_draft_checks import NoDraftChecks
from engineering_influence.services.no_stage_guidance import NoStageGuidance
from engineering_influence.services.novel_draft_checks import NovelDraftChecks
from engineering_influence.services.novel_recipes import NovelRecipes
from engineering_influence.services.outline_parser import OutlineParser
from engineering_influence.services.spend_guard import SpendGuard
from engineering_influence.services.story_bible_parser import StoryBibleParser
from engineering_influence.services.tool_registry import ToolRegistry

CAP = 5_000_000
BIBLE = json.dumps(
    {
        "premise": "A reunion.",
        "characters": [{"name": "Katherine Marsh", "age": 34}],
        "places": ["Harborough"],
        "timeline": [{"when": 1, "label": "the fire"}, {"when": 5, "label": "the trial"}],
    }
)
OUTLINE = """## Chapter 1: The Car Park
Purpose: They meet.
Beats:
- Katherine leaves her shift

## Chapter 2: The Hearing
Purpose: The trial.
Beats:
- The court
"""
INPUTS = {
    "brief.md": "BRIEF: a reunion",
    "story_bible.md": BIBLE,
    "beats.md": "BEATS: 1. They meet.",
    "outline.md": OUTLINE,
}


class Contexts(ContextAssemblerInterface):
    def __init__(self) -> None:
        self.plans: list[ContextPlan] = []

    def assemble(self, plan: ContextPlan, max_input_tokens: int) -> AssembledContext:
        self.plans.append(plan)
        return AssembledContext("SYSTEM", f"PROMPT\n{plan.beats}", 10, 0, 0, 0)


class Loop(RunToolLoopInterface):
    def __init__(self, *chapters: str) -> None:
        self.chapters = list(chapters)
        self.requests: list[ModelRequest] = []

    def run(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ToolLoopResult:
        self.requests.append(request)
        text = (
            "A summary."
            if request.prompt_version.startswith("novel_summary")
            else self.chapters.pop(0)
        )
        return ToolLoopResult(text, True, (), 0, 1, 0, 1, ())


class Checks(DraftChecksInterface):
    def __init__(self, issues: tuple[QualityIssue, ...]) -> None:
        self._issues = issues
        self.seen: list[tuple[Mapping[str, str], tuple[str, ...]]] = []

    def issues(
        self, texts: Mapping[str, str], chapters: tuple[str, ...]
    ) -> tuple[QualityIssue, ...]:
        self.seen.append((texts, chapters))
        return self._issues


class PassScreen(AnswerScreenInterface):
    """Lets every answer through, so the flow tests are not about length or refusal."""

    def refused(self, text: str) -> bool:
        return False

    def short(self, text: str, asked_words: int) -> bool:
        return False


class World:
    def __init__(
        self,
        *chapters: str,
        checks: DraftChecksInterface | None = None,
        stored: dict[str, str] | None = None,
        screen: AnswerScreenInterface | None = None,
        recipe: DraftRecipe | None = None,
        **brief: str,
    ) -> None:
        self.store = InMemoryArtifactStore()
        self.contexts = Contexts()
        self.loop = Loop(*chapters)
        self.executor = DraftStageExecutor(
            self.store,
            TomlPromptLibrary(),
            OutlineParser(),
            self.contexts,
            self.loop,
            NoStageGuidance(),
            lambda budget: SpendGuard(Budget(cap=CAP)),
            200_000,
            32_000,
            ToolRegistry(()),
            recipe or NovelRecipes.DRAFT,
            checks or NovelDraftChecks(StoryBibleParser(), ContinuityChecker()),
            screen=screen or PassScreen(),
        )
        self.run = BookRun(
            "run-1",
            BookBrief(BookKind.NOVEL, "a reunion", CAP, **brief),
            NovelRecipes().plan(),
            Budget(cap=CAP),
            stage="draft",
        )
        for name, text in (INPUTS if stored is None else stored).items():
            self.store.put("run-1", name, text.encode())

    def execute(self) -> StageReport:
        return asyncio.run(self.executor.execute(self.run, 1))

    def text(self, name: str) -> str | None:
        data = self.store.get("run-1", name)
        return None if data is None else data.decode()


def test_every_chapter_is_drafted_and_summarised_with_the_novel_prompts() -> None:
    world = World(
        "# Chapter 1\n\nKatherine Marsh, 34, waited.", "# Chapter 2\n\nThe fire, then the trial."
    )
    report = world.execute()
    assert report == StageReport()
    assert world.text("chapter_01.md").startswith("# Chapter 1")  # type: ignore[union-attr]
    assert world.text("summary_02.md") == "A summary."
    drafts = [r for r in world.loop.requests if r.prompt_version.startswith("novel_context_pack")]
    summaries = [r for r in world.loop.requests if r.prompt_version.startswith("novel_summary")]
    assert (len(drafts), len(summaries)) == (2, 2)
    assert drafts[0].prompt_version == "novel_context_pack@2"


def test_the_prompt_is_built_from_the_brief_the_bible_the_beats_and_the_outline() -> None:
    world = World("one", "two", violence="mild", heat="sweet")
    world.execute()
    plan = world.contexts.plans[0]
    assert plan.style == f"The author's brief:\nBRIEF: a reunion\n\nThe story bible:\n{BIBLE}"
    assert (
        plan.grounding
        == "The chapter titles:\nChapter 1: The Car Park\nChapter 2: The Hearing\n\nThe beats of the whole novel:\nBEATS: 1. They meet."
    )
    assert "violence mild, heat sweet" in plan.instruction
    assert plan.instruction.startswith("Write section 1 of 1 of chapter 1 of 2 now")


def test_levels_not_given_are_said_so_in_the_instruction() -> None:
    world = World("one", "two")
    world.execute()
    assert "violence not given, heat not given" in world.contexts.plans[0].instruction


def test_a_chapter_is_asked_for_the_default_length_when_the_brief_gives_none() -> None:
    world = World("one", "two")
    world.execute()
    assert "in about 2500 words" in world.contexts.plans[0].instruction


def test_the_stage_names_only_the_inputs_a_novel_reads_when_one_is_missing() -> None:
    stored = {k: v for k, v in INPUTS.items() if k != "story_bible.md"}
    with pytest.raises(ApplicationError) as caught:
        World("a", "b", stored=stored).execute()
    assert caught.value.code == "STAGE_INPUT_MISSING"
    assert "story_bible.md" in caught.value.message
    assert "positioning" not in caught.value.message and "research" not in caught.value.message


def test_a_draft_that_agrees_with_the_bible_has_no_findings_and_no_continuity_file() -> None:
    world = World(
        "# Chapter 1\n\nKatherine Marsh, 34, waited. The fire.", "# Chapter 2\n\nThe trial."
    )
    report = world.execute()
    assert report.issues == ()
    assert world.text("continuity.md") is None
    assert "Continuity" not in (world.text("draft.md") or "")


def test_a_finding_is_recorded_without_blocking_the_run() -> None:
    world = World("# Chapter 1\n\nKatharine Marsh waited.", "# Chapter 2\n\nShe left.")
    report = world.execute()
    (issue,) = report.issues
    assert (issue.stage, issue.code, issue.blocking) == ("draft", "CONTINUITY_NAME", False)
    assert issue.detail == "chapter 1 (name): the chapter writes Katharine; the bible has Katherine"
    assert world.text("continuity.md") == f"# Continuity\n\n- {issue.detail}\n"
    assert "Continuity: 1 findings, in continuity.md" in (world.text("draft.md") or "")


def test_the_checks_read_every_chapter_in_order_and_the_inputs() -> None:
    checks = Checks(())
    world = World("first chapter", "second chapter", checks=checks)
    world.execute()
    ((texts, chapters),) = checks.seen
    assert chapters == (
        "# Chapter 1: The Car Park\n\nfirst chapter",
        "# Chapter 2: The Hearing\n\nsecond chapter",
    )
    assert texts["story_bible"] == BIBLE and set(texts) == {
        "brief",
        "story_bible",
        "beats",
        "outline",
    }


def test_the_finding_count_in_the_index_has_thousands_separators() -> None:
    many = tuple(QualityIssue("draft", "CONTINUITY_NAME", f"finding {n}") for n in range(1_234))
    world = World("a", "b", checks=Checks(many))
    world.execute()
    assert "Continuity: 1,234 findings, in continuity.md" in (world.text("draft.md") or "")


def test_at_most_fifty_issues_are_reported_but_the_file_keeps_all() -> None:
    many = tuple(QualityIssue("draft", "CONTINUITY_NAME", f"finding {n}") for n in range(60))
    world = World("a", "b", checks=Checks(many))
    report = world.execute()
    assert len(report.issues) == 50 == DraftStageExecutor.REPORTED_ISSUES
    assert (world.text("continuity.md") or "").count("\n- finding") == 60
    assert "Continuity: 60 findings" in (world.text("draft.md") or "")


def test_a_redelivered_stage_does_the_same_again_without_a_second_charge() -> None:
    world = World("# Chapter 1\n\nKatharine waited.", "# Chapter 2\n\nShe left.")
    first = world.execute()
    calls = len(world.loop.requests)
    second = world.execute()
    assert second == first
    assert len(world.loop.requests) == calls


def test_no_draft_checks_find_nothing() -> None:
    assert NoDraftChecks().issues({"story_bible": BIBLE}, ("a", "b")) == ()


def test_the_novel_checks_turn_each_finding_into_one_issue_of_its_kind() -> None:
    chapters = ("Katharine arrived. Katherine Marsh, 50, at Harborogh.", "The trial.", "The fire.")
    found = NovelDraftChecks(StoryBibleParser(), ContinuityChecker()).issues(
        {"story_bible": BIBLE}, chapters
    )
    assert [item.code for item in found] == [
        "CONTINUITY_NAME",
        "CONTINUITY_PLACE",
        "CONTINUITY_AGE",
        "CONTINUITY_TIMELINE",
    ]
    assert all(item.stage == "draft" and not item.blocking for item in found)
    assert found[3].detail.startswith("chapter 3 (timeline): ")


def test_a_novel_chapter_far_short_of_its_length_is_reported_as_draft_short() -> None:
    long_two = " ".join(["word"] * 1_300)
    world = World(
        "Tiny.",
        "Tiny again.",
        "A summary of one.",
        long_two,
        "A summary of two.",
        screen=AnswerScreen(),
    )
    report = world.execute()
    (issue,) = [item for item in report.issues if item.code == "DRAFT_SHORT"]
    assert issue.detail == "chapter 1 section 1 has 2 words where about 2500 were asked"
    assert not issue.blocking


def test_an_unsectioned_novel_chapter_is_drafted_in_one_call_and_screened_as_a_whole() -> None:
    whole = replace(NovelRecipes.DRAFT, sectioned=False)
    long_two = " ".join(["word"] * 1_300)
    world = World("Tiny.", "Tiny again.", long_two, recipe=whole, screen=AnswerScreen())
    report = world.execute()
    assert [issue.detail for issue in report.issues if issue.code == "DRAFT_SHORT"] == [
        "chapter 1 has 2 words where about 2500 were asked"
    ]
    first_calls = [r for r in world.loop.requests if r.prompt_version == "novel_context_pack@2"]
    assert len(first_calls) == 2  # one first call per chapter; the retry is its own request
