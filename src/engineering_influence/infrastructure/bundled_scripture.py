# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads verses from the translations bundled with the product."""

import gzip
from pathlib import Path
from typing import ClassVar

from engineering_influence.interfaces.scripture_index_interface import ScriptureIndexInterface
from engineering_influence.models.verse_ref import VerseRef


class BundledScripture(ScriptureIndexInterface):
    """The six bundled translations, each read once from its gzipped file the first time it is asked for.

    A verse the translation does not contain (a passage that is left out of a modern text, such as Mark 16:9 in the
    Berean Standard Bible) is ``None``, so the caller knows the translation has nothing to say about it.
    """

    FOLDER: ClassVar[Path] = Path(__file__).resolve().parent / "scripture_texts"
    NAMES: ClassVar[tuple[str, ...]] = ("asv", "bsb", "dra", "kjv", "web", "ylt")

    def __init__(self, folder: Path = FOLDER) -> None:
        """Remember the folder holding the bundled translations."""
        self._folder = folder
        self._verses: dict[str, dict[str, str]] = {}

    def translations(self) -> tuple[str, ...]:
        """The six translations, by short name."""
        return self.NAMES

    def text(self, translation: str, refs: tuple[VerseRef, ...]) -> str | None:
        """The verses in order, joined by a space, or None when the translation lacks one of them."""
        if translation not in self.NAMES:
            raise ValueError(f"{translation!r} is not a bundled translation")
        verses = self._load(translation)
        parts = [verses.get(ref.label()) for ref in refs]
        if not parts or any(part is None for part in parts):
            return None
        return " ".join(part for part in parts if part is not None)

    def _load(self, translation: str) -> dict[str, str]:
        if translation not in self._verses:
            verses: dict[str, str] = {}
            with gzip.open(self._folder / f"{translation}.txt.gz", "rt", encoding="utf-8") as lines:
                for line in lines:
                    label, _, text = line.rstrip("\n").partition("\t")
                    verses[label] = text
            self._verses[translation] = verses
        return self._verses[translation]
