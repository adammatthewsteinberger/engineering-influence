# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""NonfictionOutputChecks and NoOutputChecks: the outline and the metadata must be readable; nothing else is parsed."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.stage_output_check_interface import (
    StageOutputCheckInterface,
)
from engineering_influence.models.book_metadata import BookMetadata
from engineering_influence.models.outline import Outline
from engineering_influence.services.dash_rewriter import DashRewriter
from engineering_influence.services.interfaces.metadata_parser_interface import (
    MetadataParserInterface,
)
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)
from engineering_influence.services.metadata_parser import MetadataParser
from engineering_influence.services.no_output_checks import NoOutputChecks
from engineering_influence.services.nonfiction_output_checks import NonfictionOutputChecks
from engineering_influence.services.outline_parser import OutlineParser

GOOD_METADATA = (
    "Title: Hive Mind\nSubtitle: A calm guide\nDescription:\n"
    + " ".join(["Bees are easier to keep than most people think."] * 10)
    + "\nKeywords:\n"
    + "".join(f"- keyword {n}\n" for n in range(7))
    + "Categories:\n- Books > Science & Math\n"
)
GOOD = "## Chapter 1: The Hive\nPurpose: Show how a colony works.\nBeats:\n- Workers\n"


class MetadataSpy(MetadataParserInterface):
    def __init__(self) -> None:
        self.texts: list[str] = []

    def parse(self, text: str) -> BookMetadata:
        self.texts.append(text)
        return MetadataParser(DashRewriter()).parse(GOOD_METADATA)


class Spy(OutlineParserInterface):
    def __init__(self) -> None:
        self.texts: list[str] = []

    def parse(self, text: str) -> Outline:
        self.texts.append(text)
        return OutlineParser().parse(GOOD)


def test_they_are_stage_output_checks() -> None:
    assert isinstance(NonfictionOutputChecks(Spy(), MetadataSpy()), StageOutputCheckInterface)
    assert isinstance(NoOutputChecks(), StageOutputCheckInterface)


def test_the_outline_is_parsed_and_a_good_one_passes() -> None:
    spy = Spy()
    NonfictionOutputChecks(spy, MetadataSpy()).check("outline", "the text")
    assert spy.texts == ["the text"]
    NonfictionOutputChecks(OutlineParser(), MetadataSpy()).check("outline", GOOD)


def test_an_outline_that_cannot_be_read_is_refused_with_the_parsers_reason() -> None:
    with pytest.raises(ApplicationError) as error:
        NonfictionOutputChecks(OutlineParser(), MetadataSpy()).check(
            "outline", "Just a paragraph about bees."
        )
    assert error.value.code == "OUTLINE_INVALID" and "no chapters" in error.value.message


def test_the_metadata_is_parsed_and_a_good_one_passes() -> None:
    spy = MetadataSpy()
    NonfictionOutputChecks(Spy(), spy).check("metadata", "the text")
    assert spy.texts == ["the text"]
    NonfictionOutputChecks(OutlineParser(), MetadataParser(DashRewriter())).check(
        "metadata", GOOD_METADATA
    )


def test_a_listing_that_cannot_be_read_is_refused_with_the_parsers_reason() -> None:
    checks = NonfictionOutputChecks(OutlineParser(), MetadataParser(DashRewriter()))
    with pytest.raises(ApplicationError) as error:
        checks.check("metadata", "A paragraph about bees.")
    assert error.value.code == "METADATA_INVALID" and "has no 'Title:'" in error.value.message


@pytest.mark.parametrize(
    "stage", ["brief", "positioning", "research", "draft", "assemble", "anything"]
)
def test_no_other_stage_is_parsed_and_any_text_passes(stage: str) -> None:
    spy, metadata = Spy(), MetadataSpy()
    NonfictionOutputChecks(spy, metadata).check(stage, "no chapters here at all")
    assert spy.texts == [] and metadata.texts == []


def test_no_checks_accepts_everything() -> None:
    NoOutputChecks().check("outline", "not an outline")
    NoOutputChecks().check("brief", "")
