"""The brief reader: TOML is parsed and checked the same way for a file and for a prompt."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.book_kind import BookKind
from engineering_influence.services.brief_reader import BriefReader


def test_a_valid_brief_is_read() -> None:
    text = 'kind = "nonfiction"\nidea = "Windowsill herbs"\nbudget_micro_usd = 5000000\n'
    brief = BriefReader().read_text(text, "brief.toml")
    assert (brief.kind, brief.idea, brief.budget_micro_usd) == (
        BookKind.NONFICTION,
        "Windowsill herbs",
        5_000_000,
    )


def test_toml_that_does_not_parse_names_its_source() -> None:
    with pytest.raises(ApplicationError) as caught:
        BriefReader().read_text("kind = ", "brief.toml")
    assert caught.value.code == "BRIEF_INVALID"
    assert caught.value.http_status == 422
    assert caught.value.message.startswith("brief.toml is not valid TOML")


def test_toml_that_is_not_a_brief_names_its_source_and_the_problem() -> None:
    with pytest.raises(ApplicationError) as caught:
        BriefReader().read_text('idea = "no kind here"\n', "the prompt")
    assert caught.value.code == "BRIEF_INVALID"
    assert caught.value.message.startswith("the prompt is not a brief: ")
