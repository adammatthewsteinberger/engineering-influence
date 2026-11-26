# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Estimates what a book will cost from its brief and the model's prices."""

from collections.abc import Mapping
from typing import ClassVar

from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.cost_estimate import CostEstimate
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.interfaces.cost_estimator_interface import (
    CostEstimatorInterface,
)
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.novel_recipes import NovelRecipes
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes


class CostEstimator(CostEstimatorInterface):
    """A first-pass model of the calls each stage makes, priced with the model's own rates.

    **These constants are guesses until real runs fix them.** They are the rough shape of a book (how many chapters, how
    many tokens a word is, how much a planning answer, a draft chapter and an edit read and write), chosen to be
    plausible and to be easy to correct. Each finished run's ``quality-report.json`` records the figure the estimate gave
    for its brief beside what it really spent, which is how they are to be calibrated; no claim is made here about
    how close they are.

    A book of ``target_words`` is ``target_words / WORDS_PER_CHAPTER`` chapters, between ``MIN_CHAPTERS`` and ``MAX_CHAPTERS``. A
    planning stage reads ``PLANNING_INPUT_TOKENS`` and writes ``PLANNING_OUTPUT_PERCENT`` of its recipe's output cap (a stage
    with tools makes ``TOOL_TURNS`` calls of that size). A draft chapter reads a context pack that grows with the chapters
    before it and writes the chapter, then makes a short summary call. An editing pass reads each chapter with its
    instructions and writes it again. Assembling, auditing and building call no model.
    """

    DEFAULT_TARGET_WORDS: ClassVar[int] = 20_000
    WORDS_PER_CHAPTER: ClassVar[int] = 2_500
    MIN_CHAPTERS: ClassVar[int] = 3
    MAX_CHAPTERS: ClassVar[int] = 30
    TOKENS_PER_WORD: ClassVar[float] = 1.6
    PLANNING_INPUT_TOKENS: ClassVar[int] = 2_000
    PLANNING_OUTPUT_PERCENT: ClassVar[int] = 70
    DEFAULT_PLANNING_OUTPUT: ClassVar[int] = 2_000
    TOOL_TURNS: ClassVar[int] = 4
    CONTEXT_BASE_TOKENS: ClassVar[int] = 3_000
    CONTEXT_PER_CHAPTER_TOKENS: ClassVar[int] = 200
    SUMMARY_OUTPUT_TOKENS: ClassVar[int] = 250
    EDIT_INSTRUCTION_TOKENS: ClassVar[int] = 1_500
    # The editing passes of either kind: optional, and priced as one call per chapter.
    EDITING_STAGES: ClassVar[frozenset[str]] = frozenset(
        (
            *NonfictionRecipes.REVISION_STAGES,
            NonfictionRecipes.FACT_STAGE,
            *NovelRecipes.REVISION_STAGES,
        )
    )
    NO_MODEL: ClassVar[frozenset[str]] = frozenset(
        {
            NonfictionRecipes.ASSEMBLE_STAGE,
            NonfictionRecipes.AUDIT_STAGE,
            NonfictionRecipes.BUILD_STAGE,
            NonfictionRecipes.AUDIOBOOK_STAGE,
            NonfictionRecipes.NARRATION_STAGE,
        }
    )
    # Optional stages: a run that runs out of money leaves them out. The ACX export is one of them.
    OPTIONAL_STAGES: ClassVar[frozenset[str]] = frozenset(
        {NonfictionRecipes.AUDIOBOOK_STAGE, NonfictionRecipes.NARRATION_STAGE}
    )

    def __init__(
        self,
        descriptor: ProviderDescriptor,
        recipes: Mapping[BookKind, StageRecipesInterface],
        plans: Mapping[BookKind, StagePlan],
    ) -> None:
        self._descriptor = descriptor
        self._recipes = dict(recipes)
        self._plans = dict(plans)

    def estimate(self, brief: BookBrief) -> CostEstimate:
        """The expected cost of every stage of the plan for the brief's kind of book."""
        plan = self._plans[brief.kind]
        words = brief.target_words or self.DEFAULT_TARGET_WORDS
        chapters = max(
            self.MIN_CHAPTERS, min(self.MAX_CHAPTERS, round(words / self.WORDS_PER_CHAPTER))
        )
        chapter_tokens = round(words / chapters * self.TOKENS_PER_WORD)
        stages = []
        for stage in plan.stages:
            cost = self._stage(brief.kind, stage, chapters, chapter_tokens)
            stages.append(
                (
                    stage,
                    cost,
                    stage not in self.EDITING_STAGES and stage not in self.OPTIONAL_STAGES,
                )
            )
        return CostEstimate(tuple(stages))

    # A screenplay's drafting is one call per scene: the scene count is not known until the cards exist, so the
    # estimate assumes the three-hour target (about 180 scenes), a planning figure the budget cap then enforces.
    SCREENPLAY_SCENES: ClassVar[int] = 180
    SCENE_INPUT_TOKENS: ClassVar[int] = 4_000
    SCENE_OUTPUT_TOKENS: ClassVar[int] = 1_500

    def _stage(self, kind: BookKind, stage: str, chapters: int, chapter_tokens: int) -> int:
        if stage in self.NO_MODEL:
            return 0
        if kind is BookKind.SCREENPLAY and stage == ScreenplayRecipes.DRAFT_STAGE:
            return self.SCREENPLAY_SCENES * self._call(
                self.SCENE_INPUT_TOKENS, self.SCENE_OUTPUT_TOKENS
            )
        if stage == NonfictionRecipes.DRAFT_STAGE:
            return sum(
                self._call(
                    self.CONTEXT_BASE_TOKENS + self.CONTEXT_PER_CHAPTER_TOKENS * number,
                    chapter_tokens,
                )
                + self._call(chapter_tokens, self.SUMMARY_OUTPUT_TOKENS)
                for number in range(chapters)
            )
        if stage in self.EDITING_STAGES:
            return chapters * self._call(
                chapter_tokens + self.EDIT_INSTRUCTION_TOKENS, chapter_tokens
            )
        try:
            recipe = self._recipes[kind].recipe(stage)
        except (KeyError, ValueError):
            output, turns = self.DEFAULT_PLANNING_OUTPUT, 1
        else:
            output = recipe.max_output_tokens * self.PLANNING_OUTPUT_PERCENT // 100
            turns = self.TOOL_TURNS if recipe.tools else 1
        return turns * self._call(self.PLANNING_INPUT_TOKENS, output)

    def _call(self, input_tokens: int, output_tokens: int) -> int:
        return self._descriptor.cost_micro_usd(ModelUsage(input_tokens, output_tokens))
