# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayOutputChecks: each architecture stage's answer is checked, the brief is not, and a broken answer stops the run
with the problems named."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.services.screenplay_output_checks import ScreenplayOutputChecks

BAD_BEATS = (
    "| Beat | Pages | Scenes | Scene | Central character | Function |\n|---|---|---|---|---|---|\n"
)


def test_the_brief_is_not_checked() -> None:
    ScreenplayOutputChecks().check("brief", "anything at all", None)


def test_a_broken_beat_sheet_stops_the_stage_with_its_problems() -> None:
    with pytest.raises(ApplicationError) as error:
        ScreenplayOutputChecks().check("beats", BAD_BEATS, None)
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert error.value.message.startswith("beats: the beat sheet needs the fifteen beats")


def test_a_broken_anchors_document_is_refused() -> None:
    with pytest.raises(ApplicationError) as error:
        ScreenplayOutputChecks().check("anchors", "# Anchors\n", None)
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert "'## Dramatic spine' section" in error.value.message


def test_broken_scene_cards_are_refused() -> None:
    with pytest.raises(ApplicationError):
        ScreenplayOutputChecks().check("scene_cards", "no cards here", None)


def test_a_scene_card_with_a_tone_that_is_not_a_tone_stops_the_stage() -> None:
    text = "## S01 · a scene\n**What changes:** x\n**Beat:** Set-Up\n**Storyline:** A\n**Sources:** 001\n**Tone:** angry\n"
    with pytest.raises(ApplicationError) as error:
        ScreenplayOutputChecks().check("scene_cards", text, None)
    assert "tone 'angry' is not warm, conflict or neutral" in error.value.message


def test_the_message_shows_at_most_five_problems() -> None:
    with pytest.raises(ApplicationError) as error:
        ScreenplayOutputChecks().check("anchors", "", None)
    assert error.value.message.count(";") == 4


def test_an_audit_that_breaks_its_format_is_refused_as_invalid_output() -> None:
    with pytest.raises(ApplicationError) as error:
        ScreenplayOutputChecks().check("audit", "## Source verdicts\n", None)
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert error.value.message.startswith("audit: ")


def test_a_visual_grammar_that_breaks_its_format_is_refused_as_invalid_output() -> None:
    with pytest.raises(ApplicationError) as error:
        ScreenplayOutputChecks().check("visual_grammar", "## Primary sets\n", None)
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert error.value.message.startswith("visual_grammar: ")
