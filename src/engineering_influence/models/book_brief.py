# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a person asks for: the seed of a book and the money they will spend on it."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.interfaces.book_brief_interface import BookBriefInterface
from engineering_influence.models.run_input import RunInput
from engineering_influence.models.typesetting.trim_size import TrimSize


@dataclass(frozen=True, slots=True)
class BookBrief(BookBriefInterface):
    """An idea, a kind of book and a spending cap; everything else has a default.

    ``budget_micro_usd`` is required so that no run can start without a cap. It is whole
    micro-dollars, the same unit as ``Budget``. ``inputs`` are blocks of text the person gave the run (notes, an
    excerpt, reference material): at most ``MAX_INPUTS``, each name once, ``MAX_INPUT_CHARS`` characters in all.
    They are untrusted data, and a brief with none is exactly what it was before they existed.
    """

    MAX_INPUTS: ClassVar[int] = 8
    MAX_INPUT_CHARS: ClassVar[int] = 200_000

    kind: BookKind
    idea: str
    budget_micro_usd: int
    title_hint: str | None = None
    audience: str | None = None
    target_words: int | None = None
    trim_size: str | None = None
    language: str = "en"
    inputs: tuple[RunInput, ...] = ()

    def __post_init__(self) -> None:
        if not self.idea.strip():
            raise ValueError("a brief needs an idea")
        if self.budget_micro_usd <= 0:
            raise ValueError("a brief needs a positive budget")
        if self.target_words is not None and self.target_words <= 0:
            raise ValueError("target words must be positive")
        if not self.language.strip():
            raise ValueError("a brief needs a language")
        if self.trim_size is not None and self.trim_size not in TrimSize.names():
            raise ValueError(f"trim size must be one of {', '.join(TrimSize.names())}")
        for text in (self.title_hint, self.audience):
            if text is not None and not text.strip():
                raise ValueError("optional brief text cannot be blank")
        self._check_inputs()

    def _check_inputs(self) -> None:
        if not isinstance(self.inputs, tuple) or any(
            not isinstance(item, RunInput) for item in self.inputs
        ):
            raise TypeError("a brief's inputs are a tuple of run inputs")
        if len(self.inputs) > self.MAX_INPUTS:
            raise ValueError(f"a brief has at most {self.MAX_INPUTS} inputs")
        names = [item.name for item in self.inputs]
        if len(set(names)) != len(names):
            raise ValueError("a brief names each input once")
        if sum(len(item.text) for item in self.inputs) > self.MAX_INPUT_CHARS:
            raise ValueError(
                f"a brief's inputs hold at most {self.MAX_INPUT_CHARS:,} characters in all"
            )
