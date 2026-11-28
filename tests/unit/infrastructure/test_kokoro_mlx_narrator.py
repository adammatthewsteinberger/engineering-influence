# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""KokoroMlxNarrator: the segment is read from the WAV the engine writes, converted to float samples, and a failed or
silent-of-output engine is refused."""

import array
import wave
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.narration.kokoro_mlx_narrator import KokoroMlxNarrator
from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)
from engineering_influence.models.tool_limits import ToolLimits


def write_wav(path: Path, samples: list[int], channels: int = 1, rate: int = 24_000) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(array.array("h", samples).tobytes())


class FakeEngine(ProcessRunnerInterface):
    """Runs nothing: it writes the given samples into the folder the narrator watches, and returns the given status."""

    def __init__(
        self, status: int = 0, samples: list[int] | None = None, channels: int = 1, stderr: str = ""
    ) -> None:
        self.status = status
        self.samples = samples
        self.channels = channels
        self.stderr = stderr
        self.commands: list[list[str]] = []

    def run(
        self,
        command: list[str],
        limits: ToolLimits,
        cwd: Path | None = None,
        env: object = None,
        watch: Path | None = None,
    ) -> tuple[int, str, str]:
        self.commands.append(command)
        assert watch is not None
        if self.samples is not None:
            write_wav(watch / "segment_000.wav", self.samples, self.channels)
        return self.status, "", self.stderr


def test_a_segment_is_narrated_as_float_samples_at_the_engines_rate() -> None:
    engine = FakeEngine(samples=[0, 16384, -32768, 32767])
    narration = KokoroMlxNarrator("af_heart", runner=engine).narrate("Hello.")
    assert narration.sample_rate == 24_000
    assert list(narration.samples) == pytest.approx([0.0, 0.5, -1.0, 32767 / 32768])
    assert "--voice" in engine.commands[0] and "af_heart" in engine.commands[0]
    assert "Hello." in engine.commands[0]


def test_stereo_is_averaged_to_mono() -> None:
    engine = FakeEngine(samples=[16384, 0, 0, 16384], channels=2)
    narration = KokoroMlxNarrator(runner=engine).narrate("Hi.")
    assert list(narration.samples) == pytest.approx([0.25, 0.25])


def test_an_engine_that_exits_with_an_error_is_refused_with_its_message() -> None:
    engine = FakeEngine(status=1, stderr="Import error: misaki is missing")
    with pytest.raises(ApplicationError) as error:
        KokoroMlxNarrator(runner=engine).narrate("Hi.")
    assert error.value.code == "NARRATION_FAILED"
    assert "misaki is missing" in error.value.message


def test_an_engine_that_writes_no_audio_is_refused() -> None:
    with pytest.raises(ApplicationError) as error:
        KokoroMlxNarrator(runner=FakeEngine(samples=None)).narrate("Hi.")
    assert error.value.code == "NARRATION_FAILED"


def test_audio_that_is_not_sixteen_bit_is_refused() -> None:
    class EightBit(FakeEngine):
        def run(
            self,
            command: list[str],
            limits: ToolLimits,
            cwd: Path | None = None,
            env: object = None,
            watch: Path | None = None,
        ) -> tuple[int, str, str]:
            assert watch is not None
            with wave.open(str(watch / "segment_000.wav"), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(1)
                audio.setframerate(24_000)
                audio.writeframes(bytes([128, 129]))
            return 0, "", ""

    with pytest.raises(ApplicationError) as error:
        KokoroMlxNarrator(runner=EightBit()).narrate("Hi.")
    assert "not 16-bit" in error.value.message
