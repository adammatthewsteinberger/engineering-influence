# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""NonfictionOutputChecks and NoOutputChecks: the outline must be readable as chapters; nothing else is parsed."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.stage_output_check_interface import (
    StageOutputCheckInterface,
)
from engineering_influence.models.outline import Outline
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)
from engineering_influence.services.no_output_checks import NoOutputChecks
from engineering_influence.services.nonfiction_output_checks import NonfictionOutputChecks
from engineering_influence.services.outline_parser import OutlineParser

GOOD = "## Chapter 1: The Hive\nPurpose: Show how a colony works.\nBeats:\n- Workers\n"


class Spy(OutlineParserInterface):
    def __init__(self) -> None:
        self.texts: list[str] = []

    def parse(self, text: str) -> Outline:
        self.texts.append(text)
        return OutlineParser().parse(GOOD)


def test_they_are_stage_output_checks() -> None:
    assert isinstance(NonfictionOutputChecks(Spy()), StageOutputCheckInterface)
    assert isinstance(NoOutputChecks(), StageOutputCheckInterface)


def test_the_outline_is_parsed_and_a_good_one_passes() -> None:
    spy = Spy()
    NonfictionOutputChecks(spy).check("outline", "the text")
    assert spy.texts == ["the text"]
    NonfictionOutputChecks(OutlineParser()).check("outline", GOOD)


def test_an_outline_that_cannot_be_read_is_refused_with_the_parsers_reason() -> None:
    with pytest.raises(ApplicationError) as error:
        NonfictionOutputChecks(OutlineParser()).check("outline", "Just a paragraph about bees.")
    assert error.value.code == "OUTLINE_INVALID" and "no chapters" in error.value.message


@pytest.mark.parametrize("stage", ["brief", "positioning", "research", "draft", "anything"])
def test_no_other_stage_is_parsed_and_any_text_passes(stage: str) -> None:
    spy = Spy()
    NonfictionOutputChecks(spy).check(stage, "no chapters here at all")
    assert spy.texts == []


def test_no_checks_accepts_everything() -> None:
    NoOutputChecks().check("outline", "not an outline")
    NoOutputChecks().check("brief", "")
