# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for DashRewriter."""

from abc import ABC, abstractmethod


class DashRewriterInterface(ABC):
    """Takes out the em and en dashes the typesetter refuses in non-fiction."""

    __slots__ = ()

    @abstractmethod
    def rewrite(self, text: str) -> str:
        """The text with no em dash and no en dash in it."""
