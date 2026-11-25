"""DraftRecipe: what a kind of book reads to draft a chapter, and the one instruction it gives the model."""

from typing import Any

import pytest

from engineering_influence.models.draft_recipe import DraftRecipe
from engineering_influence.services.draft_stage_executor import DraftStageExecutor
from engineering_influence.services.novel_recipes import NovelRecipes


def recipe(**changes: Any) -> DraftRecipe:
    values: dict[str, Any] = {
        "inputs": ("brief", "outline"),
        "style": (("The brief", "brief"),),
        "grounding": (("The outline", "outline"),),
        "context_template": "context_pack",
        "summary_template": "stage_summary",
        "instruction": "Write chapter {number} of {count} in {words} words.",
    }
    values.update(changes)
    return DraftRecipe(**values)


TEXTS = {"brief": "BRIEF", "outline": "OUTLINE"}


def test_the_voice_and_the_grounding_are_each_labelled_input_in_order() -> None:
    value = recipe(
        style=(("The brief", "brief"), ("The outline again", "outline")),
        grounding=(("The outline", "outline"), ("The brief again", "brief")),
    )
    assert value.style_text(TEXTS) == "The brief:\nBRIEF\n\nThe outline again:\nOUTLINE"
    assert value.grounding_text(TEXTS) == "The outline:\nOUTLINE\n\nThe brief again:\nBRIEF"


def test_the_instruction_fills_its_blanks_from_numbers_and_levels() -> None:
    value = recipe(instruction="Chapter {number}/{count}, {words} words, {violence} and {heat}.")
    assert (
        value.instruction_text(2, 9, 700, "mild", "none")
        == "Chapter 2/9, 700 words, mild and none."
    )


def test_an_instruction_may_leave_the_levels_out() -> None:
    assert (
        recipe().instruction_text(1, 3, 500, "mild", "none") == "Write chapter 1 of 3 in 500 words."
    )


def test_the_nonfiction_recipe_gives_the_same_words_the_drafter_always_gave() -> None:
    texts = {"brief": "B", "positioning": "P", "research": "R", "outline": "O"}
    value = DraftStageExecutor.NONFICTION
    assert value.style_text(texts) == "The author's brief:\nB\n\nThe positioning:\nP"
    assert value.grounding_text(texts) == "The whole outline:\nO\n\nThe research notes:\nR"
    assert value.instruction_text(2, 5, 800, "not given", "not given") == (
        "Write chapter 2 of 5 now, following the beats above, in about 800 words. "
        "Begin with the chapter's heading line."
    )
    assert (value.context_template, value.summary_template) == ("context_pack", "stage_summary")


def test_the_novel_recipe_reads_the_bible_and_the_beats_and_carries_the_levels() -> None:
    value = NovelRecipes.DRAFT
    assert value.inputs == ("brief", "story_bible", "beats", "outline")
    texts = {"brief": "B", "story_bible": "S", "beats": "T", "outline": "O"}
    assert value.style_text(texts) == "The author's brief:\nB\n\nThe story bible:\nS"
    assert (
        value.grounding_text(texts) == "The whole outline:\nO\n\nThe beats of the whole novel:\nT"
    )
    sentence = value.instruction_text(3, 12, 2500, "mild", "none")
    assert sentence.startswith(
        "Write chapter 3 of 12 now, following the beats above, in about 2500 words."
    )
    assert "violence mild, heat none" in sentence
    assert "Keep to the story bible's names, ages, places and order of events." in sentence
    assert "not given means mild violence and sweet heat." in sentence
    assert (value.context_template, value.summary_template) == (
        "novel_context_pack",
        "novel_summary",
    )


def test_a_draft_reads_the_outline() -> None:
    with pytest.raises(ValueError, match="reads the outline, and each input once"):
        recipe(
            inputs=("brief",), style=(("The brief", "brief"),), grounding=(("The brief", "brief"),)
        )


def test_a_draft_reads_each_input_once() -> None:
    with pytest.raises(ValueError, match="each input once"):
        recipe(inputs=("brief", "outline", "brief"))


@pytest.mark.parametrize("field", ["style", "grounding"])
def test_a_draft_needs_a_voice_and_a_grounding(field: str) -> None:
    with pytest.raises(ValueError, match="needs a voice and a grounding"):
        recipe(**{field: ()})


@pytest.mark.parametrize("field", ["style", "grounding"])
@pytest.mark.parametrize(
    "pair", [("", "brief"), ("  ", "brief"), ("a\nb", "brief"), ("Label", "research")]
)
def test_a_label_is_printable_text_and_names_an_input(field: str, pair: tuple[str, str]) -> None:
    with pytest.raises(ValueError, match="printable text and names an input"):
        recipe(**{field: (pair,)})


@pytest.mark.parametrize("field", ["context_template", "summary_template"])
def test_a_draft_needs_both_templates(field: str) -> None:
    with pytest.raises(ValueError, match="context template and a summary template"):
        recipe(**{field: "  "})


@pytest.mark.parametrize(
    "instruction",
    [
        "Write chapter {number} of {count}.",
        "Write chapter {number} in {words} words.",
        "Write {count} chapters in {words} words.",
        "Write chapter {number} of {count} in {words} words, {mood}.",
        "No blanks at all.",
    ],
)
def test_the_instruction_has_the_three_numbers_and_no_other_blank(instruction: str) -> None:
    with pytest.raises(ValueError, match="number, count and words, and no other blank"):
        recipe(instruction=instruction)
