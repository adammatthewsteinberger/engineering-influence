# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes the TOML config of an assembled book."""

import json

from engineering_influence.services.interfaces.book_config_writer_interface import (
    BookConfigWriterInterface,
)


class BookConfigWriter(BookConfigWriterInterface):
    """``books/<slug>.toml``: what is known after drafting, and nothing the author has not given.

    It names the kind, the title, the source folder (``src``), the trim size when the brief set one, and one
    part, ``Part One``, holding every chapter file in order. It does **not** invent the author, the
    publisher, the edition, the year or the bio; those are the author's, and the build stops and says which one is
    missing until they are added.

    Every string is written as a JSON string, which is also a TOML basic string (with the one character JSON
    leaves bare and TOML refuses, DEL, written as an escape), so a quote, a backslash or a control
    character in a title cannot change the shape of the file.
    """

    SOURCE = "src"
    PART = "Part One"

    def write(self, kind: str, title: str, trim_size: str | None, chapters: tuple[str, ...]) -> str:
        """The config text."""
        lines = [
            f"kind = {self._text(kind)}",
            f"title = {self._text(title)}",
            f"source = {self._text(self.SOURCE)}",
        ]
        if trim_size:
            lines.append(f"trim_size = {self._text(trim_size)}")
        lines += ["", "[[parts]]", f"title = {self._text(self.PART)}", "chapters = ["]
        lines += [f"  {self._text(name)}," for name in chapters]
        lines.append("]")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _text(value: str) -> str:
        return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007f")
