# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Checks that a scene's dialogue does not copy its sources: research is spoken as dialogue, not read out of a file."""

import re
from typing import ClassVar

from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)
from engineering_influence.services.interfaces.screenplay_dialogue_source_check_interface import (
    ScreenplayDialogueSourceCheckInterface,
)

WORD = re.compile(r"[a-z0-9']+")


class ScreenplayDialogueSourceCheck(ScreenplayDialogueSourceCheckInterface):
    """A speech is flagged when it holds a run of `MIN_RUN_WORDS` words that the sources also hold, in the same order,
    ignoring case and punctuation. Action is not checked: a description may name what the sources say."""

    MIN_RUN_WORDS: ClassVar[int] = 12
    SHOWN_WORDS: ClassVar[int] = 6

    def __init__(self, parser: FountainParserInterface) -> None:
        self._parser = parser

    def problems(self, scene: str, sources: str) -> tuple[str, ...]:
        """One problem per speech that repeats a run of source words, quoting the start of the run."""
        known = self._runs(WORD.findall(sources.lower()))
        found: list[str] = []
        for block in self._parser.blocks(scene):
            if block.kind != "dialogue":
                continue
            run = self._first_shared_run(WORD.findall(block.text().lower()), known)
            if run is not None:
                shown = " ".join(run[: self.SHOWN_WORDS])
                found.append(f'dialogue repeats source text: "{shown} ..."')
        return tuple(found)

    def _runs(self, words: list[str]) -> set[tuple[str, ...]]:
        size = self.MIN_RUN_WORDS
        return {tuple(words[i : i + size]) for i in range(len(words) - size + 1)}

    def _first_shared_run(
        self, words: list[str], known: set[tuple[str, ...]]
    ) -> tuple[str, ...] | None:
        size = self.MIN_RUN_WORDS
        for i in range(len(words) - size + 1):
            window = tuple(words[i : i + size])
            if window in known:
                return window
        return None
