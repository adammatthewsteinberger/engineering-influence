# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for JournalEntry."""

from abc import ABC


class JournalEntryInterface(ABC):
    """One finished model call, recorded so a resumed run does not pay for it again."""

    __slots__ = ()
