# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The stages of a screenplay run, in order, and the recipe for each: the brief, then the Phase 8 architecture."""

from typing import ClassVar

from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_recipe import StageRecipe


class ScreenplayRecipes(StageRecipesInterface):
    """Each stage is one prompt. Each stage's answer is checked by `ScreenplayOutputChecks` before it is stored, so a
    beat sheet with a missing beat stops the run where it was written. The drafting and the production layer come in
    later stages.
    """

    RECIPES: ClassVar[tuple[StageRecipe, ...]] = (
        StageRecipe("brief", "screenplay_brief", (), 1_500),
        StageRecipe("anchors", "screenplay_anchors", ("brief",), 4_000),
        StageRecipe("audit", "screenplay_audit", ("brief", "anchors"), 8_192),
        StageRecipe("beats", "screenplay_beats", ("brief", "anchors"), 3_000),
        StageRecipe("scene_cards", "screenplay_scene_cards", ("brief", "anchors", "beats"), 8_192),
        StageRecipe("visual_grammar", "screenplay_visual_grammar", ("anchors", "beats"), 4_000),
    )

    DIGEST_STAGE: ClassVar[str] = "digest_sources"
    DRAFT_STAGE: ClassVar[str] = "draft"
    REVISE_STAGE: ClassVar[str] = "revise_scenes"
    STRUCTURE_STAGE: ClassVar[str] = "structure_scenes"
    DIALOGUE_STAGE: ClassVar[str] = "dialogue_scenes"
    ASSEMBLE_STAGE: ClassVar[str] = "assemble_script"
    LOCK_STAGE: ClassVar[str] = "lock_script"
    REPORT_STAGE: ClassVar[str] = "log_revisions"
    CANON_STAGE: ClassVar[str] = "check_canon"
    RENDER_STAGE: ClassVar[str] = "render_script"
    EPUB_STAGE: ClassVar[str] = "build_epub"

    def plan(self) -> StagePlan:
        """The stages of a screenplay run, in order: the architecture, the scenes drafted, revised and assembled, the
        script's scene numbers locked, then rendered as a PDF and as an EPUB."""
        stages = (
            self.DIGEST_STAGE,
            *(recipe.stage for recipe in self.RECIPES),
            self.DRAFT_STAGE,
            self.REVISE_STAGE,
            self.STRUCTURE_STAGE,
            self.DIALOGUE_STAGE,
            self.ASSEMBLE_STAGE,
            self.LOCK_STAGE,
            self.REPORT_STAGE,
            self.CANON_STAGE,
            self.RENDER_STAGE,
            self.EPUB_STAGE,
        )
        return StagePlan(BookKind.SCREENPLAY, stages)

    def recipe(self, stage: str) -> StageRecipe:
        """The recipe for the stage, or a ValueError when a screenplay run has none for it."""
        for recipe in self.RECIPES:
            if recipe.stage == stage:
                return recipe
        raise ValueError(f"a screenplay run has no recipe for stage {stage!r}")
