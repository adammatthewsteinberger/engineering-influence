# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: the mechanical checks on a screenplay's visual grammar."""

from abc import ABC, abstractmethod


class ScreenplayVisualGrammarCheckInterface(ABC):
    """The mechanical checks on the visual grammar (prompt 08, step 8e)."""

    __slots__ = ()

    @abstractmethod
    def problems(self, text: str) -> tuple[str, ...]:
        """Every way the visual grammar breaks the format, or nothing when it passes."""
