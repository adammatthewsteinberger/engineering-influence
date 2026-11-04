"""Loads a Book from its TOML config and manuscript directory."""

import tomllib
from pathlib import Path
from typing import Any

from engineering_influence.publishing.path_relativizer import PathRelativizer
from engineering_influence.publishing.typesetting.book import Book
from engineering_influence.publishing.typesetting.chapter import Chapter
from engineering_influence.publishing.typesetting.chapter_loader import ChapterLoader
from engineering_influence.publishing.typesetting.manuscript_error import ManuscriptError


class BookLoader:
    """Reads every configured file, numbers the chapters, and rejects unlisted sources."""

    def __init__(self, root: Path, strict: bool = True) -> None:
        self._root = root
        self._relativizer = PathRelativizer(root)
        self._loader = ChapterLoader(self._relativizer, strict)

    def load(self, config_path: Path) -> Book:
        """Return the book described by the config."""
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        source = self._root / config["source"]
        book = Book(slug=config_path.stem, meta=config)
        book.front = self._entries(source, config.get("front", []), "front")
        for part in config.get("parts", []):
            book.parts.append((part["title"], self._entries(source, part["chapters"], "chapter")))
        book.back = self._entries(source, config.get("back", []), "back")
        # Only the main argument receives chapter numbers. Back matter stays unnumbered so the
        # scholarly apparatus reads as apparatus, not as a continuation of the narrative.
        number = 0
        for _, chapters in book.parts:
            for chapter in chapters:
                number += 1
                chapter.number = number
        listed = {c.path.name for c in book.front + book.back} | {
            c.path.name for _, chapters in book.parts for c in chapters
        }
        ignored = set(config.get("not_in_book", []))
        for path in sorted(source.glob("*.md")):
            if path.name not in listed and path.name not in ignored:
                raise ManuscriptError(
                    f"{self._relativizer.relative(path)} is not listed in {config_path.name}"
                )
        return book

    def _entries(self, source: Path, items: list[Any], kind: str) -> list[Chapter]:
        chapters = []
        for item in items:
            entry = {"file": item} if isinstance(item, str) else item
            chapters.append(
                self._loader.load(
                    source / entry["file"], kind, entry.get("style", "prose"), entry.get("short")
                )
            )
        return chapters
