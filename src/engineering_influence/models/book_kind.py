# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The kinds of book the 1.0 pipeline produces."""

from enum import StrEnum


class BookKind(StrEnum):
    """Whether a book is argued from sources or told as a story."""

    NONFICTION = "nonfiction"
    NOVEL = "novel"
