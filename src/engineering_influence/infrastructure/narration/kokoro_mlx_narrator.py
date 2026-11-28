# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Narrates a segment with Kokoro-82M through mlx-audio. The engine runs as its own process, so no audio library is imported here."""

import array
import sys
import tempfile
import wave
from pathlib import Path
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)
from engineering_influence.infrastructure.process.process_runner import ProcessRunner
from engineering_influence.interfaces.narrator_interface import NarratorInterface
from engineering_influence.models.narration import Narration
from engineering_influence.models.tool_limits import ToolLimits


class KokoroMlxNarrator(NarratorInterface):
    """One voice of Kokoro-82M (Apache-2.0 weights) through mlx-audio, which must be installed for this Python: the
    `audio` extra on an Apple Silicon Mac. A segment is read to a 16-bit WAV in a temporary folder, then returned as
    float samples in the range -1 to 1. Stereo is averaged to mono.
    """

    MODEL: ClassVar[str] = "mlx-community/Kokoro-82M-bf16"
    LIMITS: ClassVar[ToolLimits] = ToolLimits(
        timeout_seconds=600.0, max_memory_bytes=4 * 2**30, max_disk_bytes=2**30
    )
    FULL_SCALE: ClassVar[float] = 32768.0

    def __init__(
        self,
        voice: str = "af_heart",
        lang_code: str = "a",
        runner: ProcessRunnerInterface | None = None,
        python: str = sys.executable,
    ) -> None:
        """Remember the voice, language code, process runner and Python interpreter the narrator uses."""
        self._voice = voice
        self._lang_code = lang_code
        self._runner = runner or ProcessRunner()
        self._python = python

    def narrate(self, text: str) -> Narration:
        """Narrate the text with Kokoro through MLX audio, in a temporary folder, and return the narration."""
        with tempfile.TemporaryDirectory(prefix="kokoro-") as folder:
            command = [
                self._python,
                "-m",
                "mlx_audio.tts.generate",
                "--model",
                self.MODEL,
                "--voice",
                self._voice,
                "--lang_code",
                self._lang_code,
                "--text",
                text,
                "--output_path",
                folder,
                "--file_prefix",
                "segment",
                "--audio_format",
                "wav",
            ]
            status, _, stderr = self._runner.run(command, self.LIMITS, watch=Path(folder))
            if status != 0:
                raise self._failed(f"Kokoro exited with status {status}: {stderr.strip()[-400:]}")
            written = next(Path(folder).glob("segment*.wav"), None)
            if written is None:
                raise self._failed("Kokoro wrote no audio for the segment")
            return self._read(written)

    def _read(self, path: Path) -> Narration:
        with wave.open(str(path), "rb") as audio:
            if audio.getsampwidth() != 2:
                raise self._failed("the engine wrote audio that is not 16-bit")
            channels = audio.getnchannels()
            rate = audio.getframerate()
            pcm = array.array("h")
            pcm.frombytes(audio.readframes(audio.getnframes()))
        mono = [
            sum(pcm[index : index + channels]) / channels for index in range(0, len(pcm), channels)
        ]
        return Narration(rate, array.array("f", (sample / self.FULL_SCALE for sample in mono)))

    @staticmethod
    def _failed(reason: str) -> ApplicationError:
        return ApplicationError(
            code="NARRATION_FAILED",
            message=f"the narrator could not read a segment: {reason}",
            http_status=502,
        )
