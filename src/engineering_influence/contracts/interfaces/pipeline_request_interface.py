# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PipelineRequest."""

from abc import ABC


class PipelineRequestInterface(ABC):
    """Validated request naming the project whose pipeline should start."""

    __slots__ = ()
