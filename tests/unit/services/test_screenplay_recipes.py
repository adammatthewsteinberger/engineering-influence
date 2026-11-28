# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayRecipes: the stages of a screenplay run in order, and one recipe each."""

import pytest

from engineering_influence.models.book_kind import BookKind
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes


def test_the_plan_is_the_brief_and_the_architecture_in_order() -> None:
    plan = ScreenplayRecipes().plan()
    assert plan.kind is BookKind.SCREENPLAY
    assert tuple(plan.stages) == (
        "digest_sources",
        "brief",
        "anchors",
        "audit",
        "beats",
        "scene_cards",
        "visual_grammar",
        "draft",
        "revise_scenes",
        "structure_scenes",
        "dialogue_scenes",
        "assemble_script",
        "lock_script",
        "log_revisions",
        "check_canon",
        "render_script",
        "build_epub",
        "video",
    )


def test_each_stage_has_its_template_and_inputs() -> None:
    beats = ScreenplayRecipes().recipe("beats")
    assert beats.template == "screenplay_beats"
    assert beats.inputs == ("brief", "anchors")


def test_a_stage_with_no_recipe_is_refused() -> None:
    with pytest.raises(ValueError, match="no recipe for stage 'drafts'"):
        ScreenplayRecipes().recipe("drafts")
