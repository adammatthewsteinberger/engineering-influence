# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FountainBlock: an element of a screenplay has a known kind and at least one line."""

import pytest

from engineering_influence.models.fountain_block import FountainBlock


def test_a_block_joins_its_lines() -> None:
    assert FountainBlock("dialogue", ("I wait.", "Still.")).text() == "I wait.\nStill."


def test_an_unknown_kind_is_refused() -> None:
    with pytest.raises(ValueError, match="Fountain block is one of"):
        FountainBlock("camera", ("CLOSE ON",))


def test_a_block_has_at_least_one_line() -> None:
    with pytest.raises(ValueError, match="at least one line"):
        FountainBlock("action", ())
