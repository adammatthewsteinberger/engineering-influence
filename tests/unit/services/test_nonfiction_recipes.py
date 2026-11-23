# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""NonfictionRecipes: the plan and the recipes agree, and every prompt treats outside text as data."""

import pytest

from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.stage_recipe import StageRecipe
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes

FROM_THE_BRIEF = {"idea", "audience", "title_hint", "target_words", "language"}
TRUSTED = {"target_words"}
RECIPES = NonfictionRecipes()


def test_it_is_a_set_of_recipes() -> None:
    assert isinstance(RECIPES, StageRecipesInterface)


def test_the_plan_is_the_recipes_stages_in_order() -> None:
    plan = RECIPES.plan()
    assert plan.kind is BookKind.NONFICTION
    assert plan.stages == (
        "brief",
        "positioning",
        "research",
        "outline",
        "metadata",
        "draft",
        "assemble",
        "audit",
    )
    assert plan.stages[:-3] == tuple(recipe.stage for recipe in NonfictionRecipes.RECIPES)


def test_the_stages_that_are_not_one_prompt_are_in_the_plan_and_have_no_recipe() -> None:
    assert RECIPES.plan().stages[-3:] == ("draft", "assemble", "audit")
    assert (
        NonfictionRecipes.DRAFT_STAGE,
        NonfictionRecipes.ASSEMBLE_STAGE,
        NonfictionRecipes.AUDIT_STAGE,
    ) == ("draft", "assemble", "audit")
    for stage in ("draft", "assemble", "audit"):
        with pytest.raises(ValueError, match=f"no recipe for stage '{stage}'"):
            RECIPES.recipe(stage)


def test_the_metadata_stage_reads_the_brief_the_positioning_and_the_outline() -> None:
    recipe = RECIPES.recipe("metadata")
    assert (recipe.template, recipe.inputs, recipe.tools) == (
        "stage_metadata",
        ("brief", "positioning", "outline"),
        (),
    )


def test_a_recipe_is_found_by_stage() -> None:
    assert RECIPES.recipe("positioning").template == "stage_positioning"
    assert RECIPES.recipe("outline").inputs == ("brief", "positioning", "research")
    assert RECIPES.recipe("research").template == "stage_research"
    assert RECIPES.recipe("research").inputs == ("brief", "positioning")


def test_a_stage_with_no_recipe_is_refused() -> None:
    with pytest.raises(ValueError, match="no recipe for stage 'drafting'"):
        RECIPES.recipe("drafting")


def test_only_research_has_tools_and_they_are_search_and_page_reading() -> None:
    tools = {recipe.stage: recipe.tools for recipe in NonfictionRecipes.RECIPES}
    assert tools == {
        "brief": (),
        "positioning": (),
        "research": ("web_search", "fetch_url"),
        "outline": (),
        "metadata": (),
    }


@pytest.mark.parametrize("recipe", NonfictionRecipes.RECIPES, ids=lambda r: r.stage)
def test_a_stage_reads_only_stages_that_run_before_it(recipe: StageRecipe) -> None:
    before = RECIPES.plan().stages[: RECIPES.plan().stages.index(recipe.stage)]
    assert set(recipe.inputs) <= set(before)


@pytest.mark.parametrize("recipe", NonfictionRecipes.RECIPES, ids=lambda r: r.stage)
def test_each_prompt_uses_only_blanks_the_stage_supplies_and_reads_every_input(
    recipe: StageRecipe,
) -> None:
    template = TomlPromptLibrary().get(recipe.template)
    used = {blank for text in template.parts.values() for blank in template.BLANK.findall(text)}
    assert used <= FROM_THE_BRIEF | set(recipe.inputs)
    assert set(recipe.inputs) <= set(template.BLANK.findall(template.parts["user"]))
    assert set(recipe.input_artifacts()) == set(recipe.inputs)


@pytest.mark.parametrize("recipe", NonfictionRecipes.RECIPES, ids=lambda r: r.stage)
def test_every_blank_filled_from_outside_the_template_is_untrusted(recipe: StageRecipe) -> None:
    template = TomlPromptLibrary().get(recipe.template)
    used = {blank for text in template.parts.values() for blank in template.BLANK.findall(text)}
    assert used - TRUSTED <= template.untrusted


def test_the_research_prompt_names_its_tools_and_says_what_comes_from_them_is_untrusted() -> None:
    template = TomlPromptLibrary().get("stage_research")
    system = template.parts["system"]
    assert "web_search" in system and "fetch_url" in system
    assert "<untrusted>" in system and "everything a tool returns" in system
    assert "SHA-256" in system and "never invent a source" in system
    assert template.untrusted == frozenset({"brief", "positioning"})
