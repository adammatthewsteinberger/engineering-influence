# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SpendConsentNeededError."""

from abc import ABC


class SpendConsentNeededErrorInterface(ABC):
    """A call that would spend past the cap: the run waits for the person to grant more."""

    __slots__ = ()
