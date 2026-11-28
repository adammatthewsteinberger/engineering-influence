# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Narration: float32 mono samples at a positive whole-number rate, and how long they play."""

from array import array

import pytest

from engineering_influence.models.interfaces.narration_interface import NarrationInterface
from engineering_influence.models.narration import Narration


def test_a_narration_knows_how_long_it_plays() -> None:
    assert Narration(4, array("f", [0.0] * 10)).seconds() == 2.5


@pytest.mark.parametrize("rate", [0, -1, 24.0])
def test_the_sample_rate_is_a_positive_whole_number(rate: float) -> None:
    with pytest.raises(ValueError, match="sample rate"):
        Narration(rate, array("f"))  # type: ignore[arg-type]


def test_the_samples_are_float32_and_nothing_else() -> None:
    with pytest.raises(ValueError, match="float32"):
        Narration(1, array("h", [1]))
    with pytest.raises(ValueError, match="float32"):
        Narration(1, [0.1])  # type: ignore[arg-type]


def test_it_is_a_narration() -> None:
    assert isinstance(Narration(1, array("f")), NarrationInterface)
