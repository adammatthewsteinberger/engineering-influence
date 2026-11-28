# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""DraftStageExecutor: chapters in order, each from what came before it, and nothing half-kept."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.interfaces.stage_guidance_interface import StageGuidanceInterface
from engineering_influence.models.assembled_context import AssembledContext
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.context_plan import ContextPlan
from engineering_influence.models.guidance import Guidance
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.skill import Skill
from engineering_influence.models.stage_report import StageReport
from engineering_influence.models.tool_loop_result import ToolLoopResult
from engineering_influence.services.answer_screen import AnswerScreen
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
from engineering_influence.services.no_stage_guidance import NoStageGuidance
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.outline_parser import OutlineParser
from engineering_influence.services.read_skill_tool import ReadSkillTool
from engineering_influence.services.spend_guard import SpendGuard
from engineering_influence.services.tool_registry import ToolRegistry

CAP = 5_000_000
OUTLINE = """## Chapter 1: The Hive
Purpose: Show how a colony works.
Beats:
- The queen
- The workers
Claims to source:
- A hive holds 50,000 bees
Leads to: Where to put one.

## Chapter 2: The Site
Purpose: Pick a place for the hive.
Beats:
- Sun and shade
Leads to: What to wear.

## Chapter 3: The Suit
Purpose: Dress for the work.
Beats:
- Veils
- Gloves
"""
SHORT = """## Chapter 1: The Hive
Purpose: Show how a colony works.
Beats:
- The queen

## Chapter 2: The Site
Purpose: Pick a place for the hive.
Beats:
- Sun and shade
"""
INPUTS = {
    "brief.md": "BRIEF: bees for beginners",
    "positioning.md": "POSITIONING: the calm guide",
    "research.md": "RESEARCH: colonies swarm in spring",
    "outline.md": OUTLINE,
}


class Contexts(ContextAssemblerInterface):
    """Records every plan and cap it is given and returns a prompt that names the beats."""

    def __init__(self) -> None:
        self.calls: list[tuple[ContextPlan, int]] = []

    def assemble(self, plan: ContextPlan, max_input_tokens: int) -> AssembledContext:
        self.calls.append((plan, max_input_tokens))
        return AssembledContext("SYSTEM", f"PROMPT\n{plan.beats}", 10, 0, 0, 0)


class Loop(RunToolLoopInterface):
    """Answers drafts with a numbered chapter and summaries with a short note, unless scripted."""

    def __init__(self, *scripted: ToolLoopResult) -> None:
        self.scripted = list(scripted)
        self.calls: list[tuple[SpendGuardInterface, str, str, int, ModelRequest]] = []
        self.drafts = 0

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
        if request.prompt_version.startswith("stage_summary"):
            return done("  A summary\nover two lines. ")
        self.drafts += 1
        return done(f"words here for call {self.drafts}")


class ReadingGuidance(StageGuidanceInterface):
    def __init__(self, *tools: str) -> None:
        self.tools = tools

    def for_stage(self, stage: str) -> Guidance:
        return Guidance("ADVICE: read the index", "skill_guidance@2:abc", self.tools)


class FixedGuidance(StageGuidanceInterface):
    def for_stage(self, stage: str) -> Guidance:
        return Guidance("ADVICE: be kind", "skill_guidance@1:abc")


class PassScreen(AnswerScreenInterface):
    """Lets every answer through, so the flow tests are not about length or refusal."""

    def refused(self, text: str) -> bool:
        return False

    def short(self, text: str, asked_words: int) -> bool:
        return False


def done(text: str) -> ToolLoopResult:
    return ToolLoopResult(text, True, (), 0, 1, 0, 1, ())


def cut(text: str = "partial") -> ToolLoopResult:
    issue = QualityIssue("draft", "TRUNCATED", "the answer was cut off", blocking=True)
    return ToolLoopResult(text, False, (issue,), 0, 1, 0, 1, ())


class World:
    def __init__(
        self,
        *scripted: ToolLoopResult,
        stored: dict[str, str] | None = None,
        outline: str = OUTLINE,
        target_words: int | None = None,
        window: int = 200_000,
        model_max: int = 32_000,
        guidance: StageGuidanceInterface | None = None,
        tools: ToolRegistry | None = None,
        screen: AnswerScreenInterface | None = None,
    ) -> None:
        self.store = InMemoryArtifactStore()
        self.contexts = Contexts()
        self.loop = Loop(*scripted)
        self.budgets: list[Budget] = []
        self.guard = SpendGuard(Budget(cap=CAP))
        self.executor = DraftStageExecutor(
            self.store,
            TomlPromptLibrary(),
            OutlineParser(),
            self.contexts,
            self.loop,
            guidance or NoStageGuidance(),
            self._guard,
            window,
            model_max,
            tools or ToolRegistry(()),
            screen=screen or PassScreen(),
        )
        self.run = BookRun(
            run_id="run-1",
            brief=BookBrief(BookKind.NONFICTION, "bees", CAP, target_words=target_words),
            plan=NonfictionRecipes().plan(),
            budget=Budget(cap=CAP, spent=7),
            stage="draft",
        )
        for name, text in ({**INPUTS, "outline.md": outline} if stored is None else stored).items():
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

    def kinds(self) -> list[str]:
        return [
            "summary" if call[4].prompt_version.startswith("stage_summary") else "draft"
            for call in self.loop.calls
        ]


def test_it_is_a_stage_executor() -> None:
    assert isinstance(World().executor, StageExecutorInterface)
    assert DraftStageExecutor.STAGE == "draft"


def test_each_chapter_is_drafted_then_summarised_in_order() -> None:
    world = World()
    assert world.execute() == StageReport()
    assert world.kinds() == [
        "draft",
        "draft",
        "summary",
        "draft",
        "summary",
        "draft",
        "draft",
        "summary",
    ]
    assert sorted(world.store.names("run-1")) == sorted(
        [
            *INPUTS,
            "chapter_01.md",
            "chapter_01_s01.md",
            "chapter_01_s02.md",
            "chapter_02.md",
            "chapter_02_s01.md",
            "chapter_03.md",
            "chapter_03_s01.md",
            "chapter_03_s02.md",
            "summary_01.md",
            "summary_02.md",
            "summary_03.md",
            "draft.md",
        ]
    )
    assert world.text("chapter_02.md") == "# Chapter 2: The Site\n\nwords here for call 3"
    assert world.text("summary_03.md") == "  A summary\nover two lines. "


def test_the_index_lists_each_chapter_with_its_length_and_the_total() -> None:
    world = World()
    world.execute()
    assert world.text("draft.md") == (
        "# Draft\n\n"
        "- Chapter 1: The Hive (15 words)\n"
        "- Chapter 2: The Site (10 words)\n"
        "- Chapter 3: The Suit (15 words)\n\n"
        "Total: 40 words\n"
    )


def test_one_spend_guard_started_from_the_runs_budget_serves_every_call() -> None:
    world = World()
    world.execute(attempt=4)
    assert world.budgets == [world.run.budget]
    assert {call[0] for call in world.loop.calls} == {world.guard}
    assert {call[1:4] for call in world.loop.calls} == {("run-1", "draft", 4)}


def test_the_first_chapter_has_no_summaries_and_no_tail() -> None:
    world = World()
    world.execute()
    plan = world.contexts.calls[0][0]
    assert plan.prior_summaries == ()
    assert plan.previous_tail == ""


def test_a_later_chapter_is_given_every_earlier_summary_and_the_last_chapters_end() -> None:
    world = World()
    world.execute()
    plan = world.contexts.calls[3][0]
    assert plan.prior_summaries == (
        "Chapter 1: A summary over two lines.",
        "Chapter 2: A summary over two lines.",
    )
    assert plan.previous_tail == "# Chapter 2: The Site\n\nwords here for call 3"


def test_the_plan_carries_the_voice_the_grounding_and_this_chapters_beats() -> None:
    world = World()
    world.execute()
    plan = world.contexts.calls[2][0]
    chapter = OutlineParser().parse(OUTLINE).chapter(2)
    assert "BRIEF: bees for beginners" in plan.style
    assert "POSITIONING: the calm guide" in plan.style
    assert "RESEARCH: colonies swarm in spring" in plan.grounding
    assert "Chapter 3: The Suit" in plan.grounding
    assert plan.beats == chapter.render()


def test_the_instruction_holds_numbers_and_nothing_a_model_wrote() -> None:
    world = World(target_words=3_000)
    world.execute()
    instruction = world.contexts.calls[2][0].instruction
    assert instruction == (
        "Write section 1 of 1 of chapter 2 of 3 now, covering beat 1 above, in about 1000 words. "
        "Write only this section."
    )


def test_the_draft_request_is_the_assembled_prompt_with_the_context_pack_version() -> None:
    world = World(target_words=3_000)
    world.execute()
    request = world.loop.calls[0][4]
    assert request.system == "SYSTEM"
    assert request.prompt.startswith("PROMPT\nChapter 1: The Hive")
    assert request.prompt_version == "context_pack@3"
    assert request.max_output_tokens == 5_200
    assert request.tools == ()


def test_a_section_is_the_target_shared_across_the_chapters_and_its_beats() -> None:
    world = World(target_words=9_000)
    world.execute()
    # 9,000 words over 3 chapters is 3,000 a chapter; chapter 1 has two beats, so 1,500 a section.
    assert "about 1500 words" in world.contexts.calls[0][0].instruction


def test_with_no_target_a_section_is_twelve_hundred_and_fifty_words() -> None:
    world = World()
    world.execute()
    assert "about 1250 words" in world.contexts.calls[0][0].instruction
    assert world.loop.calls[0][4].max_output_tokens == 5_200


@pytest.mark.parametrize(
    ("target", "words"),
    [
        (30, 150),
        (900, 150),
        (901, 150),
        (1_200, 200),
        (18_000, 3_000),
        (90_000, 3_000),
    ],
)
def test_a_section_is_never_under_150_or_over_3000_words(target: int, words: int) -> None:
    world = World(target_words=target)
    world.execute()
    assert f"about {words} words" in world.contexts.calls[0][0].instruction


def test_the_output_cap_never_passes_what_the_model_allows() -> None:
    world = World(target_words=18_000, model_max=3_000)
    world.execute()
    assert world.loop.calls[0][4].max_output_tokens == 3_000


def test_the_input_budget_is_what_the_window_leaves_after_the_output_and_a_margin() -> None:
    world = World(target_words=3_000, window=10_000)
    world.execute()
    assert {cap for _, cap in world.contexts.calls} == {10_000 - 5_200 - 512}


def test_skills_for_the_stage_take_room_from_the_input_budget_and_ride_the_prompt() -> None:
    world = World(target_words=3_000, window=10_000, guidance=FixedGuidance())
    world.execute()
    assert world.contexts.calls[0][1] == 10_000 - 5_200 - 512 - len("ADVICE: be kind") // 3
    request = world.loop.calls[0][4]
    assert request.prompt.endswith("\n\nADVICE: be kind")
    assert request.prompt_version == "context_pack@3+skill_guidance@1:abc"


def test_the_summary_request_gives_the_chapter_as_an_untrusted_block() -> None:
    world = World(guidance=FixedGuidance())
    world.execute()
    request = world.loop.calls[2][4]
    assert request.prompt_version == "stage_summary@1"
    assert request.max_output_tokens == 1_000
    assert "# Chapter 1: The Hive" in request.prompt
    assert "ADVICE" not in request.prompt
    assert "untrusted" in request.system


def test_a_window_too_small_for_the_chapter_stops_before_any_call() -> None:
    world = World(target_words=3_000, window=2_400)
    error = world.refused()
    assert (error.code, error.http_status) == ("STAGE_MODEL_TOO_SMALL", 422)
    assert "2400" in error.message
    assert world.loop.calls == []
    assert world.budgets == []


def test_a_window_with_no_room_at_all_left_for_input_is_too_small() -> None:
    world = World(target_words=3_000, window=5_712)
    assert world.refused().code == "STAGE_MODEL_TOO_SMALL"
    assert world.loop.calls == []


def test_a_window_that_only_just_fits_is_used() -> None:
    world = World(target_words=3_000, window=5_713)
    world.execute()
    assert world.contexts.calls[0][1] == 1


def test_the_stage_needs_all_four_earlier_files_and_names_the_ones_missing() -> None:
    world = World(stored={"brief.md": "b", "outline.md": OUTLINE})
    error = world.refused()
    assert (error.code, error.http_status) == ("STAGE_INPUT_MISSING", 409)
    assert "positioning.md, research.md" in error.message
    assert world.loop.calls == []


def test_an_unreadable_outline_stops_the_stage_with_the_parsers_refusal() -> None:
    world = World(stored={**INPUTS, "outline.md": "just prose"})
    error = world.refused()
    assert (error.code, error.http_status) == ("OUTLINE_INVALID", 422)
    assert world.loop.calls == []


def test_a_finished_chapter_is_not_drafted_or_summarised_again() -> None:
    world = World(
        stored={
            **INPUTS,
            "chapter_01.md": "kept one",
            "summary_01.md": "kept note",
        }
    )
    world.execute()
    assert world.kinds() == ["draft", "summary", "draft", "draft", "summary"]
    assert world.text("chapter_01.md") == "kept one"
    assert world.contexts.calls[0][0].prior_summaries == ("Chapter 1: kept note",)
    assert world.contexts.calls[0][0].previous_tail == "kept one"


def test_a_chapter_with_no_summary_is_only_summarised_from_its_stored_text() -> None:
    world = World(stored={**INPUTS, "chapter_01.md": "stored words"})
    world.execute()
    assert world.kinds() == ["summary", "draft", "summary", "draft", "draft", "summary"]
    assert "stored words" in world.loop.calls[0][4].prompt
    assert world.text("chapter_01.md") == "stored words"
    assert world.text("summary_01.md") == "  A summary\nover two lines. "


def test_a_draft_that_will_not_finish_stores_nothing_for_its_chapter() -> None:
    world = World(done("one"), done("note"), cut(), outline=SHORT)
    error = world.refused()
    assert (error.code, error.http_status) == ("STAGE_ANSWER_UNUSABLE", 502)
    assert error.message == "draft: chapter 2 section 1: TRUNCATED: the answer was cut off"
    assert world.text("chapter_01.md") == "# Chapter 1: The Hive\n\none"
    assert world.text("summary_01.md") == "note"
    assert world.text("chapter_02.md") is None
    assert world.text("draft.md") is None


def test_a_blank_draft_is_refused_and_says_the_model_returned_no_text() -> None:
    world = World(done("  \n "), outline=SHORT)
    error = world.refused()
    assert error.message == "draft: chapter 1 section 1: the model returned no text"
    assert world.text("chapter_01.md") is None


def test_a_summary_that_will_not_finish_keeps_the_chapter_and_a_redelivery_only_summarises() -> (
    None
):
    world = World(done("chapter one text"), cut(), outline=SHORT)
    error = world.refused()
    assert error.message == "draft: summary 1: TRUNCATED: the answer was cut off"
    assert world.text("chapter_01.md") == "# Chapter 1: The Hive\n\nchapter one text"
    assert world.text("summary_01.md") is None
    world.loop.scripted.clear()
    world.execute(attempt=2)
    assert world.kinds()[2:] == ["summary", "draft", "summary"]
    assert world.text("chapter_01.md") == "# Chapter 1: The Hive\n\nchapter one text"


def test_a_window_or_an_output_limit_below_one_is_not_a_model() -> None:
    for window, limit in ((0, 10), (10, 0)):
        with pytest.raises(ValueError, match="window and an output limit"):
            DraftStageExecutor(
                InMemoryArtifactStore(),
                TomlPromptLibrary(),
                OutlineParser(),
                Contexts(),
                Loop(),
                NoStageGuidance(),
                lambda budget: SpendGuard(budget),
                window,
                limit,
                ToolRegistry(()),
            )


def test_the_index_writes_long_chapters_with_thousands_separators() -> None:
    long_chapter = " ".join(["word"] * 1_234)
    world = World(done(long_chapter), done("note"), done("two"), done("note"), outline=SHORT)
    world.execute()
    index = world.text("draft.md")
    assert index is not None
    assert "(1,239 words)" in index
    assert "Total: 1,245 words" in index


def reading_tools() -> ToolRegistry:
    skill = Skill("research_methodology", 1, (), sections=(("Source Evaluation", "Use SIFT."),))
    return ToolRegistry((ReadSkillTool((skill,)),))


def test_a_draft_is_offered_the_tools_its_guidance_asks_for_and_the_summary_is_not() -> None:
    world = World(guidance=ReadingGuidance("read_skill"), tools=reading_tools())
    world.execute()
    drafts = [c[4] for c in world.loop.calls if not c[4].prompt_version.startswith("stage_summary")]
    summaries = [c[4] for c in world.loop.calls if c[4].prompt_version.startswith("stage_summary")]
    assert [[t.name for t in r.tools] for r in drafts] == [["read_skill"]] * 5
    assert all(r.tools == () for r in summaries)


def test_a_draft_with_no_guidance_tools_is_offered_none() -> None:
    world = World(guidance=FixedGuidance(), tools=reading_tools())
    world.execute()
    assert all(call[4].tools == () for call in world.loop.calls)


def test_guidance_that_asks_for_a_tool_nobody_registered_stops_the_stage_before_the_call() -> None:
    world = World(guidance=ReadingGuidance("read_skill"))
    error = world.refused()
    assert (error.code, error.http_status) == ("STAGE_TOOL_UNKNOWN", 500)
    assert "read_skill" in error.message and world.loop.calls == []


def test_a_stored_section_is_kept_and_the_next_section_is_given_its_text() -> None:
    world = World(stored={**INPUTS, "chapter_01_s01.md": "kept section"})
    world.execute()
    assert world.kinds()[0] == "draft"
    assert world.contexts.calls[0][0].previous_tail == "kept section"
    assert (
        world.text("chapter_01.md")
        == "# Chapter 1: The Hive\n\nkept section\n\nwords here for call 1"
    )


def test_a_section_is_stored_as_it_is_written_so_a_redelivery_skips_it() -> None:
    world = World(done("first section"), cut())
    with pytest.raises(ApplicationError):
        world.execute()
    assert world.text("chapter_01_s01.md") == "first section"
    assert world.text("chapter_01.md") is None


LONG = " ".join(["word"] * 1_300)


def one_chapter_world(
    *scripted: ToolLoopResult, screen: AnswerScreenInterface | None = None
) -> "World":
    return World(
        *scripted, outline="## Chapter 1: Only\nPurpose: One.\nBeats:\n- The beat\n", screen=screen
    )


def test_a_refusal_is_asked_again_in_other_words_and_the_second_answer_is_kept() -> None:
    world = one_chapter_world(
        done("I'm sorry, but I can't write that."), done(LONG), screen=AnswerScreen()
    )
    report = world.execute()
    drafting = world.loop.calls[:2]
    assert drafting[1][4].prompt_version.endswith("+reworded")
    assert DraftStageExecutor.REFUSAL_NOTE in drafting[1][4].prompt
    assert world.store.get("run-1", "chapter_01_s01.md") == LONG.encode("utf-8")
    assert report.issues == ()


def test_a_second_refusal_stops_the_stage_and_names_the_section() -> None:
    world = one_chapter_world(
        done("I cannot help with this."), done("I'm not able to do that."), screen=AnswerScreen()
    )
    error = world.refused()
    assert error.code == "DRAFT_REFUSED"
    assert "chapter 1 section 1" in error.message
    assert world.store.get("run-1", "chapter_01.md") is None


def test_a_short_section_is_asked_again_for_its_length_and_the_longer_answer_is_kept() -> None:
    world = one_chapter_world(done("A short bit."), done(LONG), screen=AnswerScreen())
    report = world.execute()
    assert world.loop.calls[1][4].prompt_version.endswith("+longer")
    assert world.store.get("run-1", "chapter_01_s01.md") == LONG.encode("utf-8")
    assert report.issues == ()


def test_a_section_that_stays_short_is_kept_and_reported_as_draft_short() -> None:
    world = one_chapter_world(done("A short bit."), done("Tiny."), screen=AnswerScreen())
    report = world.execute()
    assert world.store.get("run-1", "chapter_01_s01.md") == b"A short bit."
    (issue,) = report.issues
    assert (issue.code, issue.blocking) == ("DRAFT_SHORT", False)
    assert issue.detail == "chapter 1 section 1 has 3 words where about 2500 were asked"
