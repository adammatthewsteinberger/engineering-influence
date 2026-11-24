# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes the TOML config of an assembled book."""

import json
from typing import Any

from engineering_influence.models.author_profile import AuthorProfile
from engineering_influence.models.book_metadata import BookMetadata
from engineering_influence.services.interfaces.book_config_writer_interface import (
    BookConfigWriterInterface,
)


class BookConfigWriter(BookConfigWriterInterface):
    """``books/<slug>.toml``: the listing, the author's details when a profile was supplied, and the chapters.

    A hardcover price in the author's pricing makes the book a KDP hardcover too (``[release.formats]`` and ``[formats]``).
    It names the kind, the title, the subtitle, the description, the source folder (``src``), the trim size
    when the brief set one, then whatever the author profile sets (author, publisher, edition, year, bio and the
    optional rest), the release contract's keywords and categories, and one part, ``Part One``, holding every
    chapter file in order. **Without a profile it does not invent the author, the publisher, the edition or the bio**:
    the config is left without them, and the build stops and says which is missing.

    Every string is written as a JSON string, which is also a TOML basic string (with the one character JSON
    leaves bare and TOML refuses, DEL, written as an escape), so a quote, a backslash or a control
    character cannot change the shape of the file.
    """

    SOURCE = "src"
    PART = "Part One"

    def write(
        self,
        kind: str,
        metadata: BookMetadata,
        profile: AuthorProfile | None,
        trim_size: str | None,
        chapters: tuple[str, ...],
    ) -> str:
        """The config text."""
        entries: dict[str, Any] = {
            "kind": kind,
            "title": metadata.title,
            "subtitle": metadata.subtitle,
            "description": metadata.description,
            "source": self.SOURCE,
        }
        if trim_size:
            entries["trim_size"] = trim_size
        if profile is not None:
            entries.update(profile.entries())
        lines = [f"{key} = {self._value(value)}" for key, value in entries.items()]
        lines += [
            "",
            "[release]",
            f"keywords = {self._value(list(metadata.keywords))}",
            f"categories = {self._value(list(metadata.categories))}",
            "",
        ]
        if profile is not None and profile.pricing is not None:
            lines += ["[release.pricing]"]
            lines += [
                f"{key} = {self._pricing_value(value)}"
                for key, value in profile.pricing.entries().items()
            ]
            lines += [""]
            if profile.pricing.hardcover is not None:
                # A hardcover price means a KDP hardcover: the release check refuses a hardcover price with no
                # provider unless KDP is the provider, and the build makes the hardcover files only when asked.
                lines += [
                    "[release.formats]",
                    "kdp_hardcover = true",
                    "",
                    "[formats]",
                    "hardcover = true",
                    "",
                ]
        lines += [
            "[[parts]]",
            f"title = {self._text(self.PART)}",
            "chapters = [",
        ]
        lines += [f"  {self._text(name)}," for name in chapters]
        lines.append("]")
        return "\n".join(lines) + "\n"

    def _value(self, value: Any) -> str:
        if isinstance(value, list):
            return "[" + ", ".join(self._text(item) for item in value) + "]"
        return self._text(value)

    def _pricing_value(self, value: str | float) -> str:
        return self._text(value) if isinstance(value, str) else json.dumps(value)

    @staticmethod
    def _text(value: str) -> str:
        return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007f")
