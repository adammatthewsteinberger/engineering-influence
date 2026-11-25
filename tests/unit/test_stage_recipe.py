# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""StageRecipe: what it refuses, and the file names it works out."""

from typing import Any

import pytest

from engineering_influence.models.stage_recipe import StageRecipe


def recipe(**changes: Any) -> StageRecipe:
    values: dict[str, Any] = {
        "stage": "outline",
        "template": "stage_outline",
        "inputs": ("brief", "positioning"),
        "max_output_tokens": 4_000,
    }
    values.update(changes)
    return StageRecipe(**values)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"stage": "Outline"}, "recipe's stage"),
        ({"stage": ""}, "recipe's stage"),
        ({"stage": "out line"}, "recipe's stage"),
        ({"template": "stage-outline"}, "recipe's template"),
        ({"inputs": ("brief", "Bad")}, "inputs are stage names"),
        ({"inputs": ("brief", "brief")}, "reads each stage once"),
        ({"inputs": ("outline",)}, "cannot read its own answer"),
        ({"max_output_tokens": 0}, "positive output cap"),
        ({"max_output_tokens": -5}, "positive output cap"),
    ],
)
def test_a_recipe_refuses_what_cannot_work(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        recipe(**changes)


def test_inputs_must_be_a_tuple() -> None:
    with pytest.raises(TypeError, match="tuple of stage names"):
        recipe(inputs=["brief"])


def test_a_stage_may_read_nothing() -> None:
    assert recipe(inputs=()).input_artifacts() == {}


def test_the_answer_is_kept_as_the_stage_name_with_md() -> None:
    assert recipe().output_name() == "outline.md"


def test_each_input_is_read_from_its_stage_file_under_its_own_blank() -> None:
    assert recipe().input_artifacts() == {"brief": "brief.md", "positioning": "positioning.md"}


def test_missing_lists_the_inputs_not_stored_in_order() -> None:
    held = recipe()
    assert held.missing(["brief.md", "positioning.md", "other.md"]) == ()
    assert held.missing(["brief.md"]) == ("positioning.md",)
    assert held.missing([]) == ("brief.md", "positioning.md")
    assert held.missing({"positioning.md"}) == ("brief.md",)
