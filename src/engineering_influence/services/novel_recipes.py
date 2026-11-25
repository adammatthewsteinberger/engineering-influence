# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The stages a novel run can do so far, and the recipe for each."""

from typing import ClassVar

from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.draft_recipe import DraftRecipe
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_recipe import StageRecipe


class NovelRecipes(StageRecipesInterface):
    """Brief, story bible, beats, chapter outline and metadata are one prompt each, none with tools; ``draft`` is the loop over the chapters.

    A novel is not argued from sources, so there is no research stage and no tool. The story bible is JSON that
    ``StoryBibleParser`` reads and the chapter outline is the same markdown ``OutlineParser`` reads, so the stages
    after them (drafting, which checks each chapter against the bible) walk the same chapters a non-fiction book has.
    The metadata stage writes the store listing in the format ``MetadataParser`` reads, so ``assemble`` can write the
    book's config. After the draft the plan assembles, audits and builds the book. **There are no editing passes for a
    novel yet**: what the draft stage wrote is what is built, so the book is as good as its draft.
    """

    DRAFT_STAGE = "draft"
    ASSEMBLE_STAGE = "assemble"
    AUDIT_STAGE = "audit"
    BUILD_STAGE = "build"
    DRAFT: ClassVar[DraftRecipe] = DraftRecipe(
        ("brief", "story_bible", "beats", "outline"),
        (("The author's brief", "brief"), ("The story bible", "story_bible")),
        (("The chapter titles", "outline"), ("The beats of the whole novel", "beats")),
        "novel_context_pack",
        "novel_summary",
        "Write chapter {number} of {count} now, following the beats above, in about {words} words. "
        "Begin with the chapter's heading line. Keep to the story bible's names, ages, places and order "
        "of events. Content limits: violence {violence}, heat {heat}; never go above them, and not given "
        "means mild violence and sweet heat.",
    )
    RECIPES: ClassVar[tuple[StageRecipe, ...]] = (
        StageRecipe("brief", "novel_brief", (), 1_500),
        StageRecipe("story_bible", "novel_story_bible", ("brief",), 4_000),
        StageRecipe("beats", "novel_beats", ("brief", "story_bible"), 3_000),
        StageRecipe("outline", "novel_outline", ("brief", "story_bible", "beats"), 8_192),
        StageRecipe("metadata", "novel_metadata", ("brief", "story_bible", "outline"), 2_500),
    )

    def plan(self) -> StagePlan:
        """The stages of a novel run, in order."""
        stages = (
            *(recipe.stage for recipe in self.RECIPES),
            self.DRAFT_STAGE,
            self.ASSEMBLE_STAGE,
            self.AUDIT_STAGE,
            self.BUILD_STAGE,
        )
        return StagePlan(BookKind.NOVEL, stages)

    def recipe(self, stage: str) -> StageRecipe:
        """The recipe for the stage, or a ValueError when a novel run has none for it."""
        for recipe in self.RECIPES:
            if recipe.stage == stage:
                return recipe
        raise ValueError(f"a novel run has no recipe for stage {stage!r}")
