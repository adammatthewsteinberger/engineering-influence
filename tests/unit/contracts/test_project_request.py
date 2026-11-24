# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The project request refuses a stage that does not exist, at the door every interface comes through."""

import pytest
from pydantic import ValidationError

from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.models.pipeline_stage import PipelineStage


def request(*stages: str) -> ProjectRequest:
    return ProjectRequest(slug="s", title="T", postulates=("p",), stages=stages)


def test_every_stage_the_pipeline_has_is_accepted_in_the_order_given() -> None:
    every = tuple(stage.value for stage in PipelineStage)

    assert request(*every).stages == every
    assert request("book", "thesis").stages == ("book", "thesis")


@pytest.mark.parametrize("bad", ["bogus", "Thesis", "", " book", "thesis,book"])
def test_a_stage_that_does_not_exist_is_refused_and_the_real_ones_are_named(bad: str) -> None:
    with pytest.raises(ValidationError) as caught:
        request("thesis", bad)

    (problem,) = caught.value.errors()
    assert problem["loc"] == ("stages",)
    assert (
        f"unknown stage {bad!r}: use one of thesis, book, novel, screenplay, hub, spokes"
        in (problem["msg"])
    )


def test_the_first_unknown_stage_is_the_one_reported() -> None:
    with pytest.raises(ValidationError) as caught:
        request("nope", "book", "also-nope")

    (problem,) = caught.value.errors()
    assert "unknown stage 'nope'" in problem["msg"] and "also-nope" not in problem["msg"]
