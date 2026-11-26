# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Plain, speakable text from a manuscript chapter: markdown taken out, sentences kept whole."""

import re
from typing import ClassVar

from engineering_influence.services.interfaces.narration_text_interface import (
    NarrationTextInterface,
)


class NarrationText(NarrationTextInterface):
    """Headings become sentences, links keep their words, emphasis and footnote marks go, and paragraphs are kept.

    A segment is at most ``MAX_CHARACTERS`` long and ends at a sentence where it can; a sentence that is longer
    than that is cut at its last space. Segments never split a word.
    """

    MAX_CHARACTERS: ClassVar[int] = 900
    LINK: ClassVar[re.Pattern[str]] = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
    FOOTNOTE: ClassVar[re.Pattern[str]] = re.compile(r"\[\^[^\]]*\]")
    EMPHASIS: ClassVar[re.Pattern[str]] = re.compile(r"(\*\*|__|\*|_|`)")
    SENTENCE_END: ClassVar[re.Pattern[str]] = re.compile(r"(?<=[.!?])\s+")

    def segments(self, markdown: str) -> tuple[str, ...]:
        """The speakable segments of the chapter, in order."""
        out: list[str] = []
        for paragraph in re.split(r"\n\s*\n", markdown):
            text = self._plain(paragraph)
            if text:
                out.extend(self._cut(text))
        return tuple(out)

    def _plain(self, paragraph: str) -> str:
        text = "\n".join(line.lstrip("#").strip() for line in paragraph.splitlines())
        text = self.LINK.sub(r"\1", text)
        text = self.FOOTNOTE.sub("", text)
        text = self.EMPHASIS.sub("", text)
        return " ".join(text.split())

    def _cut(self, text: str) -> list[str]:
        """Sentences packed into segments up to the limit, with any over-long sentence cut at spaces."""
        segments: list[str] = []
        current = ""
        for sentence in self.SENTENCE_END.split(text):
            for piece in self._fit(sentence):
                if current and len(current) + 1 + len(piece) > self.MAX_CHARACTERS:
                    segments.append(current)
                    current = piece
                else:
                    current = f"{current} {piece}".strip()
        segments.append(current)
        return segments

    def _fit(self, sentence: str) -> list[str]:
        pieces: list[str] = []
        rest = sentence
        while len(rest) > self.MAX_CHARACTERS:
            cut = rest.rfind(" ", 0, self.MAX_CHARACTERS + 1)
            cut = cut if cut > 0 else self.MAX_CHARACTERS
            pieces.append(rest[:cut].strip())
            rest = rest[cut:].strip()
        pieces.append(rest)
        return pieces
