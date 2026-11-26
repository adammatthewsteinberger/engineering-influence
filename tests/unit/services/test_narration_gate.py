# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""NarrationGate: the audio a narrator returns is refused when it is not numbers, goes silent, or races or drags; the rest is levelled."""

import math
from array import array

from engineering_influence.models.narration import Narration
from engineering_influence.services.interfaces.narration_gate_interface import (
    NarrationGateInterface,
)
from engineering_influence.services.narration_gate import NarrationGate

RATE = 1_000  # a small rate keeps the arrays small; the gate works in samples and seconds


def tone(seconds: float, level: float = 0.2) -> Narration:
    count = int(seconds * RATE)
    return Narration(RATE, array("f", (level * math.sin(i / 10) for i in range(count))))


def test_a_steady_narration_at_a_natural_pace_passes() -> None:
    # 2 seconds of speech for 6 words is 180 words a minute.
    assert NarrationGate().problems(tone(2.0), 6) == ()


def test_no_audio_is_refused() -> None:
    assert NarrationGate().problems(Narration(RATE, array("f")), 6) == (
        "the narrator returned no audio",
    )


def test_samples_that_are_not_numbers_or_are_out_of_range_are_refused() -> None:
    for bad in (math.nan, math.inf, 1.5):
        audio = Narration(RATE, array("f", [0.1, bad, 0.1]))
        assert NarrationGate().problems(audio, 1) == (
            "the narrator returned samples that are not numbers between -1 and 1",
        )


def test_silence_longer_than_the_limit_is_refused_and_a_short_pause_is_not() -> None:
    gate = NarrationGate()
    pause = array("f", [0.0] * int(3 * RATE))
    assert any("seconds of silence" in p for p in gate.problems(Narration(RATE, pause), 5))
    short = array("f", [0.2] * RATE + [0.0] * int(1 * RATE) + [0.2] * RATE)
    assert gate.problems(Narration(RATE, short), 8) == ()  # 8 words in 3 seconds is 160 a minute


def test_a_pace_outside_the_band_is_refused_both_ways() -> None:
    gate = NarrationGate()
    too_fast = gate.problems(tone(1.0), 5)  # 5 words in a second is 300 words a minute
    too_slow = gate.problems(tone(10.0), 5)  # 30 words a minute
    assert too_fast == ("300 words a minute is outside 90 to 220",)
    assert too_slow == ("30 words a minute is outside 90 to 220",)


def test_levelling_brings_the_average_to_the_target_and_keeps_the_peaks_under_the_ceiling() -> None:
    gate: NarrationGateInterface = NarrationGate()
    quiet = gate.normalise(tone(2.0, level=0.01))
    rms = math.sqrt(sum(x * x for x in quiet.samples) / len(quiet.samples))
    assert math.isclose(20 * math.log10(rms), NarrationGate.TARGET_RMS_DB, abs_tol=0.05)
    loud = gate.normalise(tone(2.0, level=0.95))
    assert max(abs(x) for x in loud.samples) <= NarrationGate.PEAK_CEILING + 1e-6


def test_silence_is_left_as_it_is_when_levelling() -> None:
    silent = Narration(RATE, array("f", [0.0] * RATE))
    assert NarrationGate().normalise(silent) is silent
    assert NarrationGate().normalise(Narration(RATE, array("f"))).samples == array("f")


def test_a_loud_peak_is_held_under_the_ceiling_even_when_the_average_is_quiet() -> None:
    # Mostly quiet with one spike: raising the average to the target would clip the spike, so the gain is lowered.
    spiky = [0.001] * (RATE * 2)
    spiky[RATE] = 0.5
    levelled = NarrationGate().normalise(Narration(RATE, array("f", spiky)))
    assert max(abs(x) for x in levelled.samples) <= NarrationGate.PEAK_CEILING + 1e-6
