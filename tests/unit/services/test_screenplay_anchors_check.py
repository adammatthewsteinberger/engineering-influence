# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayAnchorsCheck: the sections are present, the spine is one sentence, the images show, All Is Lost says why,
and a structural mode is named."""

from engineering_influence.services.screenplay_anchors_check import ScreenplayAnchorsCheck

GOOD = """## Dramatic spine

Adam hides the colony's failing air from the crew until the stack cracks.

## Opening image

A flat amber line falls across a pressure gauge in an empty bunk room.

## Closing image

The crew stands in the airlock and the light comes on.

## All Is Lost

The stack cracks, the beds die, and the reserve is lost, because Adam kept the number secret.

## Cannot lose

The stack. The page 61 photocopy.

## Can lose

The Iowa letters.

## Structural mode

Kubrick, for progressive revelation of the air supply.
"""


def check(text: str) -> tuple[str, ...]:
    return ScreenplayAnchorsCheck().problems(text)


def test_complete_anchors_have_no_problems() -> None:
    assert check(GOOD) == ()


def test_a_missing_section_is_named() -> None:
    assert any("'## Can lose' section" in p for p in check(GOOD.replace("## Can lose", "## Lose")))


def test_a_spine_of_two_sentences_is_a_problem() -> None:
    text = GOOD.replace("the stack cracks.", "the stack cracks. Then nothing.")
    assert any("one sentence" in p for p in check(text))


def test_thought_in_the_opening_image_is_a_problem() -> None:
    text = GOOD.replace("falls across a pressure gauge", "falls; Mara knows it is over")
    assert any("opening image" in p and "thought or V.O." in p for p in check(text))


def test_a_voice_over_in_the_closing_image_is_a_problem() -> None:
    text = GOOD.replace("The crew stands in the airlock", "V.O. The crew stands in the airlock")
    assert any("closing image" in p for p in check(text))


def test_a_structural_mode_must_be_named() -> None:
    assert any("Jackson, Kubrick or Coppola" in p for p in check(GOOD.replace("Kubrick", "Linear")))


def test_all_is_lost_must_say_what_and_why() -> None:
    text = GOOD.replace("because Adam kept the number secret", "by chance")
    assert any("what is lost and why" in p for p in check(text))


def test_text_before_the_first_section_is_not_judged() -> None:
    assert check("A preface before the sections.\n" + GOOD) == ()
