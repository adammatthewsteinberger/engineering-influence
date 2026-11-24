# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EvaluationVerdict."""

from abc import ABC


class EvaluationVerdictInterface(ABC):
    """Whether a release meets the bar, and every reason it does not."""

    __slots__ = ()
