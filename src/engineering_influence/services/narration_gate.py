# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The checks that keep a narrator's bad output out of a book, and the loudness that makes the rest match."""

from array import array
from math import isfinite, log10, sqrt
from typing import ClassVar

from engineering_influence.models.narration import Narration
from engineering_influence.services.interfaces.narration_gate_interface import (
    NarrationGateInterface,
)


class NarrationGate(NarrationGateInterface):
    """What it refuses: audio with a sample that is not a number in -1 to 1 (a reported local-MLX fault gives NaN or
    silence), a run of silence longer than ``SILENCE_SECONDS``, and a pace outside ``MIN_WORDS_A_MINUTE`` to
    ``MAX_WORDS_A_MINUTE`` for the words it was given. A narrator that goes quiet or races through a chapter is caught
    here, not heard in the book.

    What it does: levels the audio to ``TARGET_RMS_DB`` (average loudness) and lowers the gain, never raises the peaks,
    so the highest peak stays under ``PEAK_CEILING`` (-1 dBFS). A chapter that is quiet already is raised; a loud one is
    lowered; nothing is compressed.
    """

    SILENCE_LEVEL: ClassVar[float] = 0.001
    SILENCE_SECONDS: ClassVar[float] = 2.0
    MIN_WORDS_A_MINUTE: ClassVar[float] = 90.0
    MAX_WORDS_A_MINUTE: ClassVar[float] = 220.0
    TARGET_RMS_DB: ClassVar[float] = -19.0
    PEAK_CEILING: ClassVar[float] = 0.891

    def problems(self, narration: Narration, words: int) -> tuple[str, ...]:
        """Every reason the audio must not be kept; an empty tuple when it may be."""
        samples = narration.samples
        if len(samples) == 0:
            return ("the narrator returned no audio",)
        if not all(isfinite(sample) and -1.0 <= sample <= 1.0 for sample in samples):
            return ("the narrator returned samples that are not numbers between -1 and 1",)
        problems: list[str] = []
        silence = self._longest_silence(samples) / narration.sample_rate
        if silence > self.SILENCE_SECONDS:
            problems.append(f"{silence:.1f} seconds of silence in a row")
        pace = words * 60.0 / narration.seconds()
        if not self.MIN_WORDS_A_MINUTE <= pace <= self.MAX_WORDS_A_MINUTE:
            problems.append(
                f"{pace:.0f} words a minute is outside {self.MIN_WORDS_A_MINUTE:.0f} to "
                f"{self.MAX_WORDS_A_MINUTE:.0f}"
            )
        return tuple(problems)

    def normalise(self, narration: Narration) -> Narration:
        """The audio at the target loudness, with the gain lowered if the peaks would pass the ceiling."""
        samples = narration.samples
        count = len(samples)
        energy = sum(sample * sample for sample in samples)
        if count == 0 or energy == 0.0:
            return narration
        rms = sqrt(energy / count)
        peak = max(abs(sample) for sample in samples)
        gain = 10 ** ((self.TARGET_RMS_DB - 20 * log10(rms)) / 20)
        if peak * gain > self.PEAK_CEILING:
            gain = self.PEAK_CEILING / peak
        return Narration(narration.sample_rate, array("f", (sample * gain for sample in samples)))

    def _longest_silence(self, samples: array) -> int:  # type: ignore[type-arg]
        longest = run = 0
        for sample in samples:
            if -self.SILENCE_LEVEL < sample < self.SILENCE_LEVEL:
                run += 1
                longest = max(longest, run)
            else:
                run = 0
        return longest
