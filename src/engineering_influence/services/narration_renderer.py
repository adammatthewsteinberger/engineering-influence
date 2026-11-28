# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads text aloud in segments with one narrator, and packs the audio as WAV. Shared by every stage that narrates."""

import io
import wave
from array import array
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.narrator_interface import NarratorInterface
from engineering_influence.models.narration import Narration
from engineering_influence.services.interfaces.narration_renderer_interface import (
    NarrationRendererInterface,
)
from engineering_influence.services.interfaces.narration_text_interface import (
    NarrationTextInterface,
)


class NarrationRenderer(NarrationRendererInterface):
    """Each segment of the text is narrated in order, with ``PAUSE_SECONDS`` of silence between segments.

    A narrator that changes its sample rate partway through a text is refused (``AUDIO_RATE_CHANGED``), and a text with
    no speakable segments is refused (``AUDIO_NO_TEXT``). The WAV is 16-bit mono PCM, little-endian, which every host
    this runs on is.
    """

    PAUSE_SECONDS: ClassVar[float] = 0.4
    FULL_SCALE: ClassVar[int] = 32767

    def __init__(self, text: NarrationTextInterface) -> None:
        """Remember the narration text to render."""
        self._text = text

    def render(self, narrator: NarratorInterface, source: str) -> Narration:
        """The text read aloud as one narration."""
        segments = self._text.segments(source)
        if not segments:
            raise ApplicationError(
                code="AUDIO_NO_TEXT",
                message="the text has no speakable words to narrate",
                http_status=422,
            )
        samples: array = array("f")  # type: ignore[type-arg]
        rate = 0
        for index, segment in enumerate(segments):
            narration = narrator.narrate(segment)
            if index == 0:
                rate = narration.sample_rate
            elif narration.sample_rate != rate:
                raise ApplicationError(
                    code="AUDIO_RATE_CHANGED",
                    message="the narrator changed its sample rate partway through a text",
                    http_status=502,
                )
            if index:
                samples.extend(array("f", [0.0]) * int(rate * self.PAUSE_SECONDS))
            samples.extend(narration.samples)
        return Narration(rate, samples)

    def wav(self, narration: Narration) -> bytes:
        """The narration as a 16-bit mono WAV file."""
        pcm = array(
            "h",
            (round(max(-1.0, min(1.0, sample)) * self.FULL_SCALE) for sample in narration.samples),
        )
        out = io.BytesIO()
        with wave.open(out, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(narration.sample_rate)
            wav.writeframes(pcm.tobytes())
        return out.getvalue()
