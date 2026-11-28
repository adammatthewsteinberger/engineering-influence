# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mono audio from a narrator: float samples in the range -1 to 1, at a sample rate."""

from array import array
from dataclasses import dataclass

from engineering_influence.models.interfaces.narration_interface import NarrationInterface


@dataclass(frozen=True, slots=True)
class Narration(NarrationInterface):
    """Float32 samples (typecode ``f``) and their sample rate in hertz.

    Samples are not checked for range here: a narrator can return anything, and the gate that decides whether
    audio is kept is the one place that judges it.
    """

    sample_rate: int
    samples: array  # type: ignore[type-arg]

    def __post_init__(self) -> None:
        if type(self.sample_rate) is not int or self.sample_rate < 1:
            raise ValueError("a narration has a positive whole-number sample rate")
        if not isinstance(self.samples, array) or self.samples.typecode != "f":
            raise ValueError("a narration's samples are float32 (array typecode 'f')")

    def seconds(self) -> float:
        """How long the audio plays."""
        return len(self.samples) / self.sample_rate
