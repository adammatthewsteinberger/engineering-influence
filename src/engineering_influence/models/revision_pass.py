# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One pass of editing over every chapter of a book."""

import re
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.revision_pass_interface import (
    RevisionPassInterface,
)


@dataclass(frozen=True, slots=True)
class RevisionPass(RevisionPassInterface):
    """The stage, its prompt template, the files it reads and writes, what the prompt is told, and the length it may keep.

    A pass reads ``<source>_NN.md`` for each chapter and writes ``<output>_NN.md``. ``blanks`` are the pieces the
    prompt is filled from, each one of ``voice``, ``outline``, ``summaries``, ``beats``, ``chapter``, ``words`` (the chapter's
    length), and ``floor`` and ``ceiling`` (the length the model is asked to stay between), and ``chapter`` is always one of
    them. A revised chapter whose length, in words, is not between ``min_ratio`` and ``max_ratio`` of the
    chapter it was made from is not kept (see ``RevisionStageExecutor``).
    """

    NAME: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]*")
    KNOWN: ClassVar[frozenset[str]] = frozenset(
        {"voice", "outline", "summaries", "beats", "chapter", "words", "floor", "ceiling"}
    )

    stage: str
    template: str
    source: str
    output: str
    blanks: tuple[str, ...]
    min_ratio: float
    max_ratio: float

    def __post_init__(self) -> None:
        for label, value in (
            ("stage", self.stage),
            ("template", self.template),
            ("source", self.source),
            ("output", self.output),
        ):
            if not isinstance(value, str) or not self.NAME.fullmatch(value):
                raise ValueError(f"a pass's {label} is lowercase letters, digits and underscores")
        if self.source == self.output:
            raise ValueError("a pass writes different files from the ones it reads")
        if not isinstance(self.blanks, tuple) or "chapter" not in self.blanks:
            raise ValueError("a pass is told the chapter it revises")
        if len(set(self.blanks)) != len(self.blanks) or not set(self.blanks) <= self.KNOWN:
            raise ValueError(f"a pass's blanks are some of {sorted(self.KNOWN)}, each once")
        if not 0 < self.min_ratio < 1 < self.max_ratio:
            raise ValueError(
                "a pass may shorten a chapter and lengthen it, so its ratios straddle 1"
            )
